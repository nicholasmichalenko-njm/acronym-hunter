"""The acronym set (3.61.0): your own files on this PC with the terms each should give, scored each build.

The set lives outside the repository, in %USERPROFILE%\\Stationkeeper Acronym Set (or SK_ACRONYM_SET), with an
answer key, ground_truth.csv, in the format tools\\evaluate.py reads (File, Term, Expect found or absent, Note) plus
Where (typed or picture). Acronym Finder > Save as the answer key writes it from a scan you decided: every term you
approved, added or gave a meaning is found; every term you called Not a term is absent; a term you added by hand is
found in any file. tools\\acreval.py scores the set and logs numbers only (house rule 4).

default_folder() / key_rows(session) / save_key(session, folder) / read_key(folder) / score(results, rows, files)"""
import csv, os

import app_gui as A

KEY = "ground_truth.csv"
COLS = ["File", "Term", "Expect", "Where", "Note"]


def default_folder():
    return os.environ.get("SK_ACRONYM_SET") or os.path.join(os.path.expanduser("~"), "Stationkeeper Acronym Set")


def _where(locs, fname):
    mine = [l for l in locs if l.startswith(fname)]
    return "picture" if mine and all(A.loc_kind(l) == "figure" for l in mine) else "typed"


def _kept(d):
    st = (d.get("status") or "").upper()
    return (d.get("effort") in ("Approved", "Proposed", "Needs author") or bool(d.get("selected_definition")) or "MANUALLY" in st) \
        and not d.get("excluded") and not d.get("plural_of") and not d.get("form_of") \
        and not str(d.get("selected_definition", "")).startswith("[")


def key_rows(session):
    """[{File, Term, Expect, Where, Note}] from the decided scan: one row per file a kept term was found in."""
    rows = []
    for term, d in sorted((session.results or {}).items()):
        if A.status_kind(d.get("status", "")) == "error" or term.startswith("["):
            continue
        rejected = d.get("effort") == "Rejected" or "NOT A TERM" in (d.get("status") or "").upper()
        if not (rejected or _kept(d)):
            continue
        files = sorted({A._file_of(l) for l in d.get("locations") or [] if l})
        expect = "absent" if rejected else "found"
        if not files:
            rows.append({"File": "*", "Term": term, "Expect": expect, "Where": "typed", "Note": "added by hand"})
        for f in files:
            rows.append({"File": f, "Term": term, "Expect": expect, "Where": _where(d.get("locations") or [], f), "Note": ""})
    return rows


def read_key(folder):
    p = os.path.join(folder, KEY)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def save_key(session, folder=None):
    """Write the answer key for the files of this scan into the set folder, keeping other files' rows. Returns
    (path, rows written for this scan)."""
    folder = folder or default_folder()
    os.makedirs(folder, exist_ok=True)
    new = key_rows(session)
    mine = {r["File"] for r in new} | {os.path.basename(p) for p in (getattr(session, "scanned_paths", None) or {})}
    keep = [r for r in read_key(folder) if r.get("File") not in mine and r.get("File") != "*"]
    p = os.path.join(folder, KEY)
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in keep + new:
            w.writerow({c: r.get(c, "") for c in COLS})
    return p, len(new)


def _reported(res, term, fname):
    d = res.get(term)
    if not d or d.get("excluded"):
        return False
    return fname == "*" or any(l.startswith(fname) for l in d.get("locations") or [])


def score(res, rows, files=()):
    """Recall on found rows (all, typed, picture, per file), false alarms on absent rows. Numbers and paths only."""
    want = [r for r in rows if (r.get("Expect") or "").strip().lower() == "found"]
    avoid = [r for r in rows if (r.get("Expect") or "").strip().lower() == "absent"]
    got = [r for r in want if _reported(res, r["Term"], r["File"])]
    alarms = [r for r in avoid if _reported(res, r["Term"], r["File"])]

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else None
    by = {}
    for w in ("typed", "picture"):
        ws = [r for r in want if (r.get("Where") or "typed") == w]
        by[w] = {"expected": len(ws), "found": sum(1 for r in ws if r in got), "recall": pct(sum(1 for r in ws if r in got), len(ws))}
    per = []
    for p in files:
        n = os.path.basename(p)
        ws = [r for r in want if r["File"] == n]
        if ws:
            k = sum(1 for r in ws if r in got)
            per.append({"path": p, "expected": len(ws), "found": k, "recall": pct(k, len(ws))})
    return {"expected": len(want), "found": len(got), "recall": pct(len(got), len(want)), "absent": len(avoid),
            "alarms": len(alarms), "by_where": by, "files": per,
            "missed": [r for r in want if r not in got]}
