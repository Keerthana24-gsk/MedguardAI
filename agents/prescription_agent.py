import re
from .common import STRENGTH, FREQ
from services.ocr_service import ocr_lines

NOISE = re.compile(r"(?i)\b(tab|tablet|cap|capsule|syp|syrup|inj)\b\.?")


def parse_line(text, conf, source, engine="Manual"):
    raw = str(text).strip()
    if not raw or "[UNREADABLE]" in raw.upper():
        return None
    strength = STRENGTH.search(raw)
    frequency = FREQ.search(raw)
    name = NOISE.sub("", STRENGTH.sub("", FREQ.sub("", raw))).strip(" .-,:;")
    if len(name) < 3:
        return None
    try:
        confidence = float(conf)
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "name": name,
        "raw_text": raw,
        "strength": strength.group(0) if strength else None,
        "frequency": frequency.group(0) if frequency else None,
        "source": source,
        "ocr_engine": engine,
        "confidence": round(confidence, 2),
        "confirmed": False,
    }


def run(state):
    meds = []
    warnings = state.setdefault("warnings", [])
    for fname, data in state.get("files", []):
        try:
            lines = ocr_lines(data)
            if not lines:
                warnings.append(f"No readable medicine lines found in {fname}; enter medicines manually.")
                continue
            for item in lines:
                med = parse_line(item.get("text", ""), item.get("confidence", 0.0), fname, item.get("engine", "OCR"))
                if med:
                    meds.append(med)
            if not any(m["source"] == fname for m in meds):
                warnings.append(f"No medicine names could be extracted from {fname}; please enter them manually.")
        except Exception as exc:
            warnings.append(f"Could not read {fname}: {exc} Please enter its medicines manually.")

    for line in state.get("manual", []):
        med = parse_line(line, 0.0, state.get("manual_source", "Manual"), "Manual entry")
        if med:
            meds.append(med)

    state["meds"] = meds
    return state
