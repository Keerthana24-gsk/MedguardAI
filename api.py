from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents.orchestrator import stage1, stage2

load_dotenv()
app = FastAPI(title="MediGuard AI")

class Req(BaseModel):
    medicines: list[str]
    user_confirmed: bool = False
    # Optional user-reviewed active ingredients, keyed by the entered medicine name.
    confirmed_ingredients: dict[str, list[str]] = Field(default_factory=dict)

@app.post("/analyze")
def analyze(request: Req):
    state = stage1({"manual": request.medicines})

    if not request.user_confirmed:
        return {
            "needs_confirmation": state.get("meds", []),
            "message": "Review the medicine names and active ingredients, then submit again with user_confirmed=true and confirmed_ingredients.",
            "warnings": state.get("warnings", []),
        }

    for med in state.get("meds", []):
        reviewed = request.confirmed_ingredients.get(med["name"], [])
        if reviewed:
            med["ingredients"] = [ingredient.strip().lower() for ingredient in reviewed if ingredient.strip()]
        med["confirmed"] = bool(med.get("ingredients"))

    pending = [med for med in state.get("meds", []) if not med.get("confirmed")]
    if pending:
        return {
            "needs_confirmation": pending,
            "message": "Every confirmed medicine must have a user-verified active ingredient.",
            "warnings": state.get("warnings", []),
        }

    state = stage2(state)
    return {key: state.get(key) for key in ("interactions", "reconciliation", "report", "warnings")}
