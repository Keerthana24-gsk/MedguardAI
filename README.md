# MediGuard AI
Run: `pip install -r requirements.txt && streamlit run app.py` (API: `uvicorn api:app`). Optional: set GEMINI_API_KEY in .env.
- `database/ddinter.csv` is a **tiny SAMPLE**. Replace with the DDInter 2.0 export (check its terms of use) and adapt column names in `agents/common.py`.
- `database/medicine_mapping.csv` is illustrative; verify every brand mapping against product formulations and extend with Indian brands.
- Orchestration: LangGraph (falls back to sequential). Human confirmation sits between stage1 and stage2.
- "No record" never means "safe". Not for clinical use.

## Handwritten prescription OCR
See `HANDWRITING_OCR_UPDATE.md`. Gemini Vision is optional and is used only as a transcription candidate generator; PaddleOCR is the fallback. Every OCR-derived medicine must be checked and explicitly confirmed by a human before analysis. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` only if you want the cloud option.
