from itertools import combinations
from .common import ddi_index
NO_REC = "No matching record found in the selected database"
def run(state):
    ings = sorted({i for m in state["active_meds"] for i in m["ingredients"]})
    idx, out = ddi_index(), []
    for a, b in combinations(ings, 2):
        r = idx.get(frozenset((a, b)))
        out.append(dict(pair=(a, b), status="match", record=r) if r else dict(pair=(a, b), status="no_record", message=NO_REC))
    state["interactions"] = out
    return state
