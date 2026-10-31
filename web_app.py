"""MedGuard Flask website. Local prototype; not a production clinical system."""
import os, uuid, sqlite3, base64
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from agents.orchestrator import stage1, stage2

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "medguard_profiles.db"
UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-local-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
app.jinja_env.filters["b64encode"] = lambda value: base64.b64encode(value).decode("ascii")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
# Prototype state is held in memory per browser session. Restarting Flask clears an in-progress analysis.
WORKFLOWS = {}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            contact TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")


def current_profile():
    pid = session.get("profile_id")
    if not pid:
        return None
    with db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
    return dict(row) if row else None


def require_profile(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_profile():
            flash("Please create or select your profile first.", "info")
            return redirect(url_for("profile"))
        return fn(*args, **kwargs)
    return wrapped


def sid():
    if "workflow_id" not in session:
        session["workflow_id"] = uuid.uuid4().hex
    return session["workflow_id"]


def workflow():
    return WORKFLOWS.setdefault(sid(), {"state": None, "done": False})


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    if current_profile():
        return redirect(url_for("dashboard"))
    return redirect(url_for("profile"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    existing = current_profile()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        contact = request.form.get("contact", "").strip()
        try:
            age = int(request.form.get("age", ""))
        except ValueError:
            age = 0
        if not all([username, full_name, contact]) or not (1 <= age <= 120):
            flash("Enter a username, full name, valid age and contact detail.", "error")
            return render_template("profile.html", profile=existing)
        try:
            with db() as conn:
                if existing:
                    conn.execute("UPDATE profiles SET username=?, full_name=?, age=?, contact=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                 (username, full_name, age, contact, existing["id"]))
                    pid = existing["id"]
                else:
                    cur = conn.execute("INSERT INTO profiles(username, full_name, age, contact) VALUES(?,?,?,?)",
                                       (username, full_name, age, contact))
                    pid = cur.lastrowid
            session["profile_id"] = pid
            flash("Your profile has been saved on this computer.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("That username is already in use. Choose another username.", "error")
    return render_template("profile.html", profile=existing)


@app.route("/switch-profile", methods=["GET", "POST"])
def switch_profile():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        with db() as conn:
            row = conn.execute("SELECT id FROM profiles WHERE username=?", (username,)).fetchone()
        if row:
            session["profile_id"] = row["id"]
            flash("Profile loaded.", "success")
            return redirect(url_for("dashboard"))
        flash("No saved profile found for that username.", "error")
    return render_template("switch_profile.html")


@app.route("/logout")
def logout():
    session.pop("profile_id", None)
    flash("You have left this profile. Your saved profile remains on this computer.", "info")
    return redirect(url_for("switch_profile"))


@app.route("/dashboard")
@require_profile
def dashboard():
    wf = workflow()
    return render_template("dashboard.html", profile=current_profile(), has_upload=bool(wf.get("state")))


@app.route("/upload", methods=["GET", "POST"])
@require_profile
def upload():
    if request.method == "POST":
        files = request.files.getlist("prescriptions")
        manual_text = request.form.get("manual_medicines", "")
        valid_files = []
        folder = UPLOAD_DIR / sid()
        folder.mkdir(parents=True, exist_ok=True)
        for f in files:
            if f and f.filename:
                if not allowed_file(f.filename):
                    flash(f"Unsupported file: {f.filename}. Use PNG, JPG or WEBP for this prototype.", "error")
                    return render_template("upload.html", profile=current_profile())
                safe = secure_filename(f.filename)
                stored = folder / f"{uuid.uuid4().hex[:8]}_{safe}"
                f.save(stored)
                valid_files.append((f.filename, stored.read_bytes()))
        manual = [line.strip() for line in manual_text.splitlines() if line.strip()]
        if not valid_files and not manual:
            flash("Upload at least one prescription image or enter medicine names manually.", "error")
            return render_template("upload.html", profile=current_profile())
        state = stage1({"files": valid_files, "manual": manual, "manual_source": "Manual entry"})
        workflow().update(state=state, done=False)
        flash("Extraction finished. Please review every medicine before analysis.", "success")
        return redirect(url_for("review"))
    return render_template("upload.html", profile=current_profile())


@app.route("/review", methods=["GET", "POST"])
@require_profile
def review():
    wf = workflow(); state = wf.get("state")
    if not state:
        flash("Upload a prescription or enter medicines first.", "info")
        return redirect(url_for("upload"))
    if request.method == "POST":
        names = request.form.getlist("name[]")
        strengths = request.form.getlist("strength[]")
        frequencies = request.form.getlist("frequency[]")
        ingredients = request.form.getlist("ingredients[]")
        confirms = request.form.getlist("confirmed[]")
        confirmed_indices = {int(x) for x in confirms if x.isdigit()}
        reviewed = []
        for i, name in enumerate(names):
            name = name.strip()
            if not name: continue
            ing = [x.strip().lower() for x in ingredients[i].split(";") if x.strip()] if i < len(ingredients) else []
            is_confirmed = i in confirmed_indices
            if is_confirmed and not ing:
                flash(f"Add and verify the active ingredient for {name} before confirming it.", "error")
                return render_template("review.html", profile=current_profile(), meds=state.get("meds", []), state=state)
            reviewed.append({"name": name, "strength": strengths[i].strip() or None if i < len(strengths) else None,
                "frequency": frequencies[i].strip() or None if i < len(frequencies) else None,
                "ingredients": ing, "source": "User reviewed", "raw_text": "", "ocr_engine": "Reviewed entry",
                "class": "", "confidence": 0.0, "confirmed": is_confirmed,
                "match_status": "Human reviewed" if is_confirmed else "Needs confirmation"})
        if not any(m["confirmed"] for m in reviewed):
            flash("Confirm at least one medicine after checking its name and active ingredient.", "error")
            return render_template("review.html", profile=current_profile(), meds=state.get("meds", []), state=state)
        state["meds"] = reviewed
        wf["state"] = stage2(state)
        wf["done"] = True
        flash("Screening completed. Review the findings and report carefully.", "success")
        return redirect(url_for("analysis"))
    return render_template("review.html", profile=current_profile(), meds=state.get("meds", []), state=state)


@app.route("/analysis")
@require_profile
def analysis():
    wf = workflow()
    if not wf.get("done"):
        flash("Complete medicine review before viewing analysis.", "info")
        return redirect(url_for("review" if wf.get("state") else "upload"))
    return render_template("analysis.html", profile=current_profile(), state=wf["state"])


@app.route("/report")
@require_profile
def report():
    wf = workflow()
    if not wf.get("done"):
        flash("Complete the screening first.", "info")
        return redirect(url_for("upload"))
    return render_template("report.html", profile=current_profile(), state=wf["state"])


@app.route("/download-report")
@require_profile
def download_report():
    wf = workflow()
    if not wf.get("done"):
        return redirect(url_for("upload"))
    path = DATA_DIR / f"medguard_report_{sid()}.md"
    path.write_text(wf["state"].get("report", "No report generated."), encoding="utf-8")
    return send_file(path, as_attachment=True, download_name="MedGuard_Medication_Safety_Report.md")


@app.errorhandler(413)
def too_large(_):
    flash("File too large. Maximum upload size is 12 MB.", "error")
    return redirect(url_for("upload"))


init_db()
if __name__ == "__main__":
    app.run(debug=True)
