# MedGuard handwritten prescription OCR update

## What changed
- `services/ocr_service.py`: optional Gemini Vision handwriting transcription, PaddleOCR 2.x/3.x-compatible fallback, gentle OpenCV preprocessing, and visible error messages.
- `agents/prescription_agent.py`: preserves original OCR text and engine; unreadable text is not silently converted into a medicine.
- `agents/normalization_agent.py`: lookup suggestions are never auto-confirmed.
- `app.py`: displays uploaded original prescriptions beside editable extracted candidates; a person must confirm each medicine and ingredient before screening.
- `api.py`: does not run interaction screening until the caller has confirmed the medicine list.

## Setup on Windows / VS Code
1. Back up your current `MediGuard_AI` folder.
2. Replace the matching files with the files in this update package.
3. In the project terminal, activate your existing virtual environment.
4. Install/update dependencies:

   ```powershell
   python -m pip install --upgrade streamlit pandas python-dotenv requests opencv-python google-genai
   ```

5. Copy `.env.example` to `.env`, add your Gemini API key, and keep `.env` private. If you do not want Gemini Vision, set `USE_GEMINI_VISION=false`; PaddleOCR will be used as the fallback if installed.
6. If using PaddleOCR, install a PaddlePaddle/PaddleOCR combination supported by your Python and Windows versions using the official installation instructions. Do not assume the newest PaddleOCR works with every Python version.
7. Run:

   ```powershell
   python -m streamlit run app.py
   ```

## How to test
- Start with a clear photo of a handwritten prescription with patient-identifying information covered.
- Compare each extracted line with the original image.
- Correct medicine name, strength, formulation and active ingredient manually where needed.
- Tick `Human confirmed` only after checking the original prescription.
- Only confirmed rows are included in screening.
- Test at least 10–20 varied prescriptions and record exact medicine-name accuracy, strength accuracy, unreadable rate and manual-correction rate before reporting performance.

## Safety and privacy
- Gemini Vision is an external cloud service. Do not upload identifiable patient prescriptions without appropriate consent and privacy safeguards. Remove patient names, addresses, phone numbers, IDs and other unnecessary personal details first.
- OCR confidence from Gemini is deliberately recorded as 0.0 because it is not a calibrated confidence score.
- A matching medicine database entry is only a suggestion, not proof of identity. Human confirmation is mandatory.
- The sample medicine and interaction CSV files remain illustrative. Replace them with verified, appropriately licensed and maintained data before any real-world use.
- This is a prototype, not a clinical device or medical advice. Never tell users to start, stop or change medicines based on its output.
