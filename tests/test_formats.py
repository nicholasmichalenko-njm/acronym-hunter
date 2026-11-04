"""3.38.1 every saved file still writes the format number formats.py lists, so a format change cannot slip in without
raising the number, adding the step that reads the old one and a golden set (see formats.py)."""
import json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "data")
import app_gui as A  # noqa: F401
import formats as F, prodrules as PRL, rulebook as RB, templatelib as TL, authorlist as AL, effortpkg as P, teamdata as TD
import teampack as TP, updatepack as UP, effortrec as R

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
PRL.save(cfg, PRL.load(cfg))
check("production standards", json.load(open(os.path.join(cfg, PRL.FILE)))["version"] == F.number("production standards"))
RB.set_on(cfg, 3, False)
check("rules", json.load(open(os.path.join(cfg, RB.FILE)))["format"] == F.number("rules") == RB.FORMAT)
lib = TL.Library(cfg); lib.save()
idx = next(os.path.join(d, f) for d, _ds, fs in os.walk(cfg) for f in fs if f == "index.json")
check("template library", json.load(open(idx))["format"] == F.number("template library"))
check("author list", AL.FORMAT == F.number("author list"))
check("effort package", P.FORMAT == F.number("effort package"))
check("team pack", TP.FORMAT == F.number("team pack"))
check("Stationkeeper Data file", TD.FORMAT == F.number("Stationkeeper Data file"))
check("update pack", UP.FORMAT == F.number("update pack"))
rec = R.Record(os.path.join(tmp, "eff")); os.makedirs(rec.folder, exist_ok=True); rec.save()
check("effort record", json.load(open(rec.path))["v"] == F.number("effort record"))
check("every kind is checked here", len(F.FORMATS) == 9, len(F.FORMATS))
n = sum(checks)
print(f"FORMATS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
