import requests
def ingredients(name, timeout=5):
    """Best-effort RxNorm lookup (US terminology). Returns [] on any failure."""
    try:
        r = requests.get("https://rxnav.nlm.nih.gov/REST/approximateTerm.json",
                         params={"term": name, "maxEntries": 1}, timeout=timeout).json()
        rxcui = r["approximateGroup"]["candidate"][0]["rxcui"]
        rel = requests.get(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json",
                           params={"tty": "IN"}, timeout=timeout).json()
        return [c["name"].lower() for g in rel["relatedGroup"]["conceptGroup"]
                for c in g.get("conceptProperties", [])]
    except Exception:
        return []
