import difflib
import re
from .common import mapping
from services.rxnorm_service import ingredients as rxnorm


def lookup(name):
    table = {r["brand"].lower(): r for r in mapping()}
    n = name.lower().strip()
    base = re.sub(r"[\d\s]+$", "", n).strip()
    for key in (n, base):
        if key in table:
            return table[key], 1.0
    match = difflib.get_close_matches(base, list(table), n=1, cutoff=0.75)
    if match:
        score = difflib.SequenceMatcher(None, base, match[0]).ratio()
        return table[match[0]], score
    return None, 0.0


def run(state):
    for med in state.get("meds", []):
        row, score = lookup(med["name"])
        if row:
            med["ingredients"] = [x.strip().lower() for x in row["ingredients"].split(";") if x.strip()]
            med["class"] = row["therapeutic_class"]
            med["match_status"] = "Exact reference match" if score == 1.0 else "Possible fuzzy match"
        else:
            med["ingredients"] = rxnorm(med["name"]) if state.get("use_rxnorm", True) else []
            med["class"] = ""
            med["match_status"] = "Unmatched — enter/verify ingredient manually"

        med["match_score"] = round(score, 2)
        # Never auto-confirm an OCR or fuzzy-matched medicine. A human must
        # review the image, name, ingredient, strength and formulation in app.py.
        med["confirmed"] = False
    return state
