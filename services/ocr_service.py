"""Prescription OCR with optional Gemini Vision and PaddleOCR fallback.

Important: OCR output is a candidate transcription, never a confirmed medicine.
"""
import json
import os

# Work around a CPU oneDNN/PIR compatibility issue seen with some
# PaddlePaddle 3.3.x + PaddleOCR 3.x installations on Windows.
# These must be set BEFORE importing paddleocr / paddlex / paddle.
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
os.environ.setdefault("FLAGS_use_mkldnn", "0")


def _mime_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def gemini_handwriting_lines(data: bytes):
    """Return transcription lines from Gemini Vision, or [] if not configured.

    Gemini does not provide a calibrated OCR confidence score. Its confidence is
    therefore deliberately set to 0.0 so the UI requires human confirmation.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    enabled = os.getenv("USE_GEMINI_VISION", "true").lower() in {"1", "true", "yes", "on"}
    if not api_key or not enabled:
        return []

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = """Read this handwritten medical prescription. Transcribe only what is visibly written.
Do not guess, autocomplete, or substitute a medicine based on medical knowledge.
Return ONLY valid JSON in this exact shape:
{"lines": ["one complete medicine line exactly as written", ...], "unclear_regions": ["brief description"]}
Keep medicine name, strength, dosage form, frequency and duration together when visible.
If a medicine name is unreadable, write [UNREADABLE] for that name. Do not invent missing strengths or instructions.
Ignore patient names, addresses, phone numbers and unrelated personal details. Do not provide medical advice."""
    response = client.models.generate_content(
        model=os.getenv("GEMINI_VISION_MODEL", "gemini-3.8-flash"),
        contents=[prompt, types.Part.from_bytes(data=data, mime_type=_mime_type(data))],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    payload = json.loads(response.text or "{}")
    lines = payload.get("lines", [])
    return [
        {"text": str(line).strip(), "confidence": 0.0, "engine": "Gemini Vision (unscored)"}
        for line in lines if str(line).strip()
    ]


def _preprocess(data: bytes):
    import cv2
    import numpy as np

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("The uploaded file could not be decoded as an image.")

    # Upscale small photos and gently improve local contrast. Avoid aggressive
    # thresholding because it can erase thin handwritten pen strokes.
    h, w = image.shape[:2]
    if max(h, w) < 1800:
        scale = min(2.0, 1800 / max(h, w))
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    return cv2.fastNlMeansDenoisingColored(enhanced, None, 3, 3, 7, 21)


def paddle_handwriting_lines(data: bytes):
    """PaddleOCR 2.x/3.x compatible fallback. Returns [] if unavailable/no text."""
    import cv2
    from paddleocr import PaddleOCR

    image = _preprocess(data)
    try:
        # PaddleOCR 3.x
        try:
            engine = PaddleOCR(
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
            )
        except TypeError:
            # Some PaddleOCR 3.x builds do not expose enable_mkldnn in
            # the constructor; the PaddleX environment flag above remains.
            engine = PaddleOCR(
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
    except TypeError:
        # PaddleOCR 2.x
        engine = PaddleOCR(lang="en", use_angle_cls=True, show_log=False, enable_mkldnn=False)

    if hasattr(engine, "predict"):
        results = engine.predict(image)
        output = []
        for result in results or []:
            # PaddleOCR 3.x Result is dict-like with parallel arrays.
            try:
                texts = result.get("rec_texts", [])
                scores = result.get("rec_scores", [])
            except AttributeError:
                data_dict = getattr(result, "json", {}) or {}
                data_dict = data_dict.get("res", data_dict)
                texts = data_dict.get("rec_texts", [])
                scores = data_dict.get("rec_scores", [])
            for text, score in zip(texts, scores):
                if str(text).strip():
                    output.append({"text": str(text).strip(), "confidence": float(score), "engine": "PaddleOCR"})
        return output

    # PaddleOCR 2.x output: [[box, (text, score)], ...]
    results = engine.ocr(image, cls=True)
    output = []
    for page in results or []:
        for item in page or []:
            try:
                text, score = item[1]
                if str(text).strip():
                    output.append({"text": str(text).strip(), "confidence": float(score), "engine": "PaddleOCR"})
            except (TypeError, ValueError, IndexError, KeyError):
                continue
    return output


def ocr_lines(data: bytes):
    """Try Gemini Vision first when configured; otherwise use PaddleOCR.

    Returns list[dict]: text, confidence, engine. Raises a useful error rather
    than silently hiding dependency/API failures.
    """
    if os.getenv("GEMINI_API_KEY") and os.getenv("USE_GEMINI_VISION", "true").lower() in {"1", "true", "yes", "on"}:
        try:
            lines = gemini_handwriting_lines(data)
            if lines:
                return lines
        except Exception as exc:
            gemini_error = f"Gemini Vision failed ({type(exc).__name__}: {exc})."
        else:
            gemini_error = "Gemini Vision returned no readable medicine lines."
    else:
        gemini_error = None

    try:
        lines = paddle_handwriting_lines(data)
        if lines:
            return lines
    except Exception as exc:
        paddle_error = f"PaddleOCR failed ({type(exc).__name__}: {exc})."
    else:
        paddle_error = "PaddleOCR did not detect readable text."

    details = " ".join(x for x in (gemini_error, paddle_error) if x)
    raise RuntimeError(details or "No OCR engine returned text.")
