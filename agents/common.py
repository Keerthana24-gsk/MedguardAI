import csv, os, re
from functools import lru_cache
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
def _rows(f):
    with open(os.path.join(DB, f), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
@lru_cache
def mapping(): return _rows("medicine_mapping.csv")
@lru_cache
def ddi_index():
    # Column names are configurable: adapt here if your DDInter export differs.
    return {frozenset((r["drug_a"].lower(), r["drug_b"].lower())): r for r in _rows("ddinter.csv")}
STRENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)\b", re.I)
FREQ = re.compile(r"\b(od|bd|bid|tds|tid|qid|hs|once daily|twice daily|thrice daily|1-0-1|1-1-1|1-0-0|0-0-1)\b", re.I)
