from collections import defaultdict
def run(state):
    meds = [m for m in state["meds"] if m.get("confirmed") and m["ingredients"]]
    flags, by_ing, by_cls = [], defaultdict(list), defaultdict(set)
    for m in meds:
        for i in m["ingredients"]: by_ing[i].append(m)
        if m.get("class"): by_cls[m["class"]].update(m["ingredients"])
    for i, ms in by_ing.items():
        if len(ms) < 2: continue
        if len({(x["name"].lower(), x["strength"]) for x in ms}) == 1:
            kind, note = "Exact duplicate prescription", "Same medicine and strength listed more than once."
        else:
            kind = "Duplicate active ingredient"
            note = "Combined exposure should be reviewed by a pharmacist or clinician. Entries: " + \
                   ", ".join(f"{x['name']} {x['strength'] or '(strength missing)'} [{x['source']}]" for x in ms)
        flags.append(dict(kind=kind, subject=i, note=note))
    for c, ings in by_cls.items():
        if len(ings) > 1:
            flags.append(dict(kind="Therapeutic duplication", subject=c,
                              note="Different medicines of the same class: " + ", ".join(sorted(ings))))
    for m in state["meds"]:
        if not m["confirmed"]:
            flags.append(dict(kind="Needs confirmation", subject=m["name"], note="Identity or OCR confidence uncertain; excluded from analysis until confirmed."))
        elif not m["strength"] or not m["frequency"]:
            flags.append(dict(kind="Incomplete record", subject=m["name"], note="Strength or frequency missing."))
    state["reconciliation"], state["active_meds"] = flags, meds
    return state
