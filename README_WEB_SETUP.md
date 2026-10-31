# MedGuard Flask Website - Add-on

This add-on creates a responsive Flask website while keeping the existing `agents/`, `services/`, `database/`, `.env`, and Streamlit `app.py` files intact.

## 1. Copy the files
Extract/copy these items into the existing `MediGuard_AI` project folder:
- `web_app.py`
- `templates/` (the complete folder)
- `static/` (the complete folder)

Do not replace or delete your existing `.env` file. Do not replace your existing `app.py`.

## 2. Install Flask
Open VS Code Terminal in the `MediGuard_AI` folder and run:

```powershell
python -m pip install Flask
```

If your other project dependencies are not installed yet, run:

```powershell
python -m pip install -r requirements.txt
```

## 3. Start the website

```powershell
python web_app.py
```

Open the local address printed in the terminal (normally `http://127.0.0.1:5000`).

## Website flow
1. Create a profile with username, full name, age and phone/email contact.
2. Upload prescription images (PNG/JPG/WEBP) or enter medicines manually.
3. Review and correct extracted names, strengths, frequencies and active ingredients.
4. Confirm only medicines checked against the original prescription; then run screening.
5. Review the findings and download a Markdown report.

## Important prototype limitations
- Profile data is stored locally in `data/medguard_profiles.db`. Username lookup is not secure authentication; there is no password or account protection.
- Uploaded files are saved under `uploads/` and workflow state is held in memory while the Flask process runs.
- This first web version accepts image files only. PDF upload can be added in a later step.
- This is a local demonstration prototype, not a production health-record system. Do not deploy it publicly or enter real patient contact/medical information without proper authentication, encryption, consent, access controls and security review.
- OCR output must be checked by a human. A missing interaction match does not mean a medicine combination is safe. The app is not medical advice.

## Design
The interface uses a soft off-white background (#f6f8f6), white cards and deep teal accents.
