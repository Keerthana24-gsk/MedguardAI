import os
from .evidence_agent import verify_text
DISC = "This report is informational and not medical advice. Please discuss all findings with a qualified pharmacist or doctor before changing any medication."
def template(s):
    m = [f for f in s["interactions"] if f["status"] == "match"]
    L = ["# Medication Safety Report", "", f"- Medication records reviewed: {len(s['meds'])}",
         f"- Database interaction matches: {len(m)}", f"- Reconciliation flags: {len(s['reconciliation'])}",
         f"- Entries needing confirmation: {sum(not x['confirmed'] for x in s['meds'])}", "", "## Potential interactions"]
    for f in m:
        r = f["record"]
        L += [f"### {f['pair'][0].title()} + {f['pair'][1].title()} ({r['risk']})", f"- Interaction: {r['interaction']}",
              f"- Mechanism: {r['mechanism']}", f"- Management (reference): {r['management']}", f"- Source: {r['source']}"]
    if not m: L.append("No database matches found.")
    L += ["", "## Pairs with no record"] + [f"- {f['pair'][0]} + {f['pair'][1]}: {f['message']} (this does not mean the combination is safe)"
                                           for f in s["interactions"] if f["status"] == "no_record"]
    L += ["", "## Reconciliation flags"] + [f"- **{x['kind']}** ({x['subject']}): {x['note']}" for x in s["reconciliation"]]
    L += ["", "## Limitations", "Pairwise checking cannot capture multi-drug, dose, age, allergy, or kidney/liver factors.", "", DISC]
    return "\n".join(L)
def run(state):
    text = template(state)
    key = os.getenv("GEMINI_API_KEY")
    if key and state.get("use_llm", True):
        try:
            from google import genai
            prompt = ("Rewrite this medication safety report in simple patient-friendly language. Use ONLY facts in the text; "
                      "add no new medical claims, never say a combination is safe, keep the disclaimer.\n\n" + text)
            out = genai.Client(api_key=key).models.generate_content(model="gemini-2.0-flash", contents=prompt).text
            if not verify_text(out, state): text = out
            else: state.setdefault("warnings", []).append("LLM rewrite contained unsupported claims; template report used.")
        except Exception as e:
            state.setdefault("warnings", []).append(f"Gemini unavailable ({type(e).__name__}); template report used.")
    state["report"] = text
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "reports", "latest_report.md")
    open(p, "w", encoding="utf-8").write(text)
    return state
