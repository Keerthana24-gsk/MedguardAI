import re
RISK_WORDS = {"fatal", "death", "contraindicated", "severe", "bleeding", "hypotension", "hyperkalemia", "myopathy"}
def label_check(a, b, timeout=5):
    """Optional openFDA label cross-check; returns snippet or None."""
    try:
        import requests
        q = f'drug_interactions:"{a}"+AND+openfda.generic_name:"{b}"'
        r = requests.get("https://api.fda.gov/drug/label.json", params={"search": q, "limit": 1}, timeout=timeout).json()
        txt = " ".join(r["results"][0].get("drug_interactions", []))
        return txt[:300] if txt else None
    except Exception:
        return None
def run(state):
    for f in state["interactions"]:
        if f["status"] != "match": continue
        r = f["record"]
        f["evidence"] = dict(source=r["source"], fields_present=all(r[k] for k in ("interaction", "risk", "mechanism", "management")),
                             label_snippet=label_check(*f["pair"]) if state.get("use_openfda") else None)
    return state
def verify_text(text, state):
    """Flag sentences with risk claims not backed by retrieved records, or calling a combination safe."""
    corpus = " ".join(" ".join(f["record"].values()).lower() for f in state["interactions"] if f["status"] == "match")
    bad = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        low = s.lower(); hit = {w for w in RISK_WORDS if w in low}
        if "safe combination" in low or "is safe" in low or (hit and not all(w in corpus for w in hit)):
            bad.append(s)
    return bad
