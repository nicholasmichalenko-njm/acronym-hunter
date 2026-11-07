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
import effort as E, openpyxl
L = E.EffortList(os.path.join(tmp, "Kestrel_Effort_List.xlsx"), "Kestrel"); L.add_or_update("KTV", Definition="Kestrel Test Vehicle"); L.save()
_wb = openpyxl.load_workbook(L.path, read_only=True)       # read-only books hold the file on Windows until closed
ab = {r[0]: r[1] for r in _wb["About"].iter_rows(values_only=True) if r}
_wb.close()
check("effort acronym list", ab.get("Format") == F.number("effort acronym list") == E.FORMAT, ab)
# format 1 (before 3.52.0) wrote SS Approver: it reads the same, and the next save writes Approver
wb = openpyxl.load_workbook(L.path); ws = wb["Effort List"]
col = [c.value for c in ws[1]].index("Approver") + 1
ws.cell(row=1, column=col).value = "SS Approver"; ws.cell(row=2, column=col).value = "R. Diaz"; wb.save(L.path); wb.close()
old = E.EffortList(L.path, "Kestrel").load()
check("an acronym list saved before 3.52.0 reads its approvers", old.rows["KTV"]["Approver"] == "R. Diaz", old.rows.get("KTV"))
old.save()
_wb = openpyxl.load_workbook(L.path, read_only=True)
hdr = [c.value for c in _wb["Effort List"][1]]
_wb.close()
check("... and the next save writes Approver", "Approver" in hdr and "SS Approver" not in hdr, hdr)
import effortrelink as ER                                  # 3.68.0: the marker in an effort's folder
mk = ER.write_marker(L.path, "Kestrel")
check("effort marker", json.load(open(mk, encoding="utf-8"))["format"] == F.number("effort marker"))
import outlinelayouts as OLY                               # 3.73.0: outline layouts set ahead of time
OLY.save(cfg, OLY.load(cfg))
check("outline layouts", json.load(open(os.path.join(cfg, OLY.FILE), encoding="utf-8"))["format"] == F.number("outline layouts") == OLY.FORMAT)
from skqt import usage as UG                                # 3.74.0: button use on this PC
UG.save(cfg, UG.load(cfg))
check("button use", json.load(open(os.path.join(cfg, UG.FILE), encoding="utf-8"))["format"] == F.number("button use") == UG.FORMAT)
check("every kind is checked here", len(F.FORMATS) == 13, len(F.FORMATS))
n = sum(checks)
print(f"FORMATS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
