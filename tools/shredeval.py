"""Score the shred against the person's shred set (3.59.0) and log the numbers only.

    .\\venv\\Scripts\\python.exe tools\\shredeval.py            (the set in %USERPROFILE%\\Stationkeeper Shred Set,
                                                             or SK_SHRED_SET)
    .\\venv\\Scripts\\python.exe tools\\shredeval.py --floor    (buildrel: exit 1 below tools\\shred_floor.json)

The set stays on the PC, outside the repository. This prints and logs scores only: never a file's name or text (house
rule 4). Each RFP has its own floor, its first scored recall (so a harder RFP added later never stops the build); a floor
rises by hand when the shred gets better, and drops only with a line in DECISIONS.md."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
args = sys.argv[1:]
floor = "--floor" in args
args = [a for a in args if a != "--floor"]
folder = os.path.abspath(args[0]) if args else (os.environ.get("SK_SHRED_SET") or "")
import shredeval as SE  # noqa: E402
folder = folder or SE.default_folder()
FLOOR = os.path.join(ROOT, "tools", "shred_floor.json")
HIST = os.path.join(ROOT, "tools", "shred_history.csv")

r = SE.score_set(folder) if os.path.isdir(folder) else {"rfps": 0, "labeled": 0}
if not r["labeled"]:
    print(f"SHRED_EVAL {r['rfps']} RFP file(s), none labeled yet: no score, no floor")
    sys.exit(0)
import app_gui as A  # noqa: E402
SE.append_history(HIST, r, A.APP_VERSION)
kinds = ", ".join(f"{k} {v}%" for k, v in r["by_kind"].items() if v is not None)
print(f"SHRED_EVAL {r['labeled']} RFP(s), {r['requirements']} requirements: recall {r['recall']}%, precision {r['precision']}%, "
      f"kind right {r['kind_right']}% ({kinds}); target {SE.TARGET:g}%")
try:
    fl = json.load(open(FLOOR, encoding="utf-8"))
except (OSError, ValueError):
    fl = {}
# one floor per RFP (named by a hash of its place in the set, never its name): an RFP added later, harder than the rest,
# starts its own floor and never stops the build; one the shred now reads worse does
import hashlib  # noqa: E402
per = fl.setdefault("files", {})
below, new = [], 0
for f in r["files"]:
    if not f.get("labeled") or "error" in f or f.get("recall") is None:
        continue
    k = hashlib.sha1(os.path.relpath(f["path"], folder).lower().encode()).hexdigest()[:12]
    if k not in per:
        per[k] = f["recall"]; new += 1
    elif f["recall"] < float(per[k]):
        below.append((per[k], f["recall"]))
if fl.get("recall") is None:
    fl["recall"] = r["recall"]
fl["set"] = f"{len(per)} RFP floor(s), last set {A.APP_VERSION}"
with open(FLOOR, "w", encoding="utf-8") as fh:
    json.dump(fl, fh, indent=1)
if new:
    print(f"SHRED_FLOOR set for {new} new RFP(s)")
if floor and below:
    print(f"SHRED_BELOW_FLOOR {len(below)} RFP(s) read worse than before: " + "; ".join(f"{b}% (floor {a}%)" for a, b in below))
    sys.exit(1)
