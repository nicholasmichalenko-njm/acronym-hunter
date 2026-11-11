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
import standardsbook as SB, teamlib as TLB, openpyxl                     # 4.7.0
bk = os.path.join(tmp, "Company Standards.xlsx"); SB.write(bk, PRL.load(cfg)["company"], [])
about = {r[0]: r[1] for r in openpyxl.load_workbook(bk)["About"].iter_rows(values_only=True)}
check("Company Standards workbook", about.get("Format") == F.number("Company Standards workbook") == SB.FORMAT, about)
TLB.mark_dirty(cfg)
check("team library state", json.load(open(os.path.join(cfg, TLB.STATE)))["format"] == F.number("team library state"))
check("update pack", UP.FORMAT == F.number("update pack"))
rec = R.Record(os.path.join(tmp, "eff")); os.makedirs(rec.folder, exist_ok=True); rec.save()
check("effort record", json.load(open(rec.path))["v"] == F.number("effort record"))
import effort as E, openpyxl
L = E.EffortList(os.path.join(tmp, "Kestrel_Effort_List.xlsx"), "Kestrel"); L.add_or_update("KTV", Definition="Kestrel Test Vehicle"); L.save()
_wb = openpyxl.load_workbook(L.path, read_only=True)       # read-only books hold the file on Windows until closed
ab = {r[0]: r[1] for r in _wb["About"].iter_rows(values_only=True) if r}
_wb.close()
check("effort acronym list", ab.get("Format") == F.number("effort acronym list") == E.FORMAT, ab)
# format 2 (3.52.0 to 3.75.0) had Approver and Approved on, and four statuses; format 1 wrote SS Approver
wb = openpyxl.load_workbook(L.path); ws = wb["Effort List"]
hd = [c.value for c in ws[1]]
ncol = len(hd) + 1
ws.cell(row=1, column=ncol).value = "SS Approver"; ws.cell(row=2, column=ncol).value = "R. Diaz"
ws.cell(row=2, column=hd.index("Status") + 1).value = "Approved"; wb.save(L.path); wb.close()
old = E.EffortList(L.path, "Kestrel").load()
check("an older list reads: Approved is In the list", old.rows["KTV"]["Status"] == "In the list", old.rows.get("KTV"))
check("... and its approver moves into the history", any("R. Diaz" in " ".join(h) for h in old.history), old.history)
old.save()
_wb = openpyxl.load_workbook(L.path, read_only=True)
hdr = [c.value for c in _wb["Effort List"][1]]
_wb.close()
check("... and the next save has no approval columns", "Approver" not in hdr and "SS Approver" not in hdr, hdr)
import effortrelink as ER                                  # 3.68.0: the marker in an effort's folder
mk = ER.write_marker(L.path, "Kestrel")
check("effort marker", json.load(open(mk, encoding="utf-8"))["format"] == F.number("effort marker"))
import outlinelayouts as OLY                               # 3.73.0: outline layouts set ahead of time
OLY.save(cfg, OLY.load(cfg))
check("outline layouts", json.load(open(os.path.join(cfg, OLY.FILE), encoding="utf-8"))["format"] == F.number("outline layouts") == OLY.FORMAT)
from skqt import usage as UG                                # 3.74.0: button use on this PC
UG.save(cfg, UG.load(cfg))
check("button use", json.load(open(os.path.join(cfg, UG.FILE), encoding="utf-8"))["format"] == F.number("button use") == UG.FORMAT)
import efftrain as ETR                                      # 3.76.0: the effort's training samples
class _S: pass
_s = _S(); _s.ws = type("W", (), {"root": cfg})(); _s.effort = object()
ETR.add(_s, "misread", "KSF", "KSE", ["Kestrel_Large_Diagram.png"])
check("training samples", json.load(open(ETR.path_of(cfg), encoding="utf-8"))["format"] == F.number("training samples") == ETR.FORMAT)
import picreadings as PRD                                     # 3.80.0: the pictures' readings with the effort
PRD.use(cfg); PRD.put("k1", [((1, 2, 30, 12), "KTV", 0.91, "read")]); PRD.flush()
check("picture readings", json.load(open(os.path.join(cfg, PRD.FILE), encoding="utf-8"))["format"] == F.number("picture readings") == PRD.FORMAT)
PRD.use(None)
import verifystate as VS, verifyroles as VRO, ocrpdf as OCP     # 3.84.0: Verify's decisions, its menu, scan readings
vs = VS.Store(cfg); vs.set_role("Kestrel SOW.pdf", ["1:0"], "h1")
check("verify", json.load(open(os.path.join(cfg, VS.FILE), encoding="utf-8"))["format"] == F.number("verify") == VS.FORMAT)
VRO.save_team(cfg, VRO.defaults())
check("verify menu", json.load(open(os.path.join(cfg, VRO.TEAM_FILE), encoding="utf-8"))["format"] == F.number("verify menu") == VRO.FORMAT)
OCP.save_readings(os.path.join(cfg, "copy.pdf"), {"1": []})
check("scan readings", json.load(open(OCP.readings_path(os.path.join(cfg, "copy.pdf")), encoding="utf-8"))["format"]
      == F.number("scan readings") == OCP.READINGS_FORMAT)
import sectiondesigns as SDZ                                   # 3.87.0: the Section designs library
SDZ._save(cfg, {"designs": []})
check("section designs", json.load(open(os.path.join(cfg, SDZ.FOLDER, "index.json"), encoding="utf-8"))["format"]
      == F.number("section designs") == SDZ.FORMAT)
import shredtypes as STY, reshred as RSH                       # 4.1.0: the piece types, the re-shred queue
STY.save(cfg, STY.load(None))
check("piece types", json.load(open(os.path.join(cfg, STY.FILE), encoding="utf-8"))["format"] == F.number("piece types") == STY.FORMAT)
rq = RSH.Queue(cfg); rq.add("a>b", "k1", "Section L", "A0001", "old words", "new words")
check("re-shred queue", json.load(open(rq.path, encoding="utf-8"))["format"] == F.number("re-shred queue") == RSH.FORMAT)
check("every kind is checked here", len(F.FORMATS) == 23, len(F.FORMATS))   # 4.7.0: the workbook and its state
n = sum(checks)
print(f"FORMATS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
