"""3.73.0 offscreen: Compliance matrix > Export the matrix... keeps a version with the effort; Bring the edited matrix
back... lists what the team filled in, waits for the pick on a change in both, and brings the values in; Merge another
copy's matrix... keeps ours unless theirs is taken. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, matrixdesign as MD, matrixversions as MV, setupdoc as SD
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
import test_matrixver373 as TM                                  # its outline and workbook editor (its own checks run too)
x1 = TM.TV.build(os.path.join(tmp, "Kestrel Outline.xlsx"), TM.TV.V1)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
w.setups_page.from_outline(x1, accept=True)
w.go("matrix"); app.processEvents()
mp = w.matrix_page
mp.d = MD.default("outline")
out = os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx")
mp.export(out)
M = w.review.M
check("Export the matrix keeps a version with the effort", MV.versions(M) and MV.versions(M)[-1]["v"] == 1
      and os.path.isfile(os.path.join(ED, "Matrix Versions", "Kestrel_Compliance_Matrix v1.xlsx")))
SD.set_progress(M, "1.2 Telemetry, Tracking and Command", 10)
H = {k: MD.heading_of(k) for k in MD.OUTLINE_KEYS}
TM.edit(out, {("Response Section No. Item", "1.1 Ground", H["assigned_to"]): "R. Diaz, K. Lee",
              ("Response Section No. Item", "1.2 Telemetry", H["pct_complete"]): "25%"})
mp.bring_back(out, accept=False)
dlg = mp.back_dialog
check("the edited matrix: every value listed, the change in both waits", dlg.table.rowCount() == 2 and not dlg.b_ok.isEnabled()
      and "wait for your pick" in dlg.wait.text(), [dlg.table.item(r, 0).text() for r in range(dlg.table.rowCount())])
both = next(c["i"] for c in dlg.changes if c["both"])
dlg.table.pick(both, "theirs")
check("picked: ready", dlg.b_ok.isEnabled())
n = dlg.apply(); dlg.close()
check("the values are in", n == 2 and SD.section_people(M, "1.1 Ground Segment Architecture")["with"] == "K. Lee"
      and SD.progress_of(M, "1.2 Telemetry, Tracking and Command") == 25)
theirs = os.path.join(tmp, "Their_Matrix.xlsx")
MD.export(M, theirs, MD.default("outline"), "Kestrel")
TM.edit(theirs, {("Response Section No. Item", "1.3 Mission", H["assigned_to"]): "S. Patel"})
n2 = mp.bring_back(theirs, merge=True, accept=True)
check("another copy merged with no pick: ours kept (the lead it inherits)", n2 == 0 and SD.section_people(M, "1.3 Mission Operations")["lead"] == "R. Diaz")
mp.bring_back(theirs, merge=True, accept=False)
md = mp.back_dialog
check("in a merge every difference starts as ours, and Bring is ready", md.b_ok.isEnabled() and all(v == "ours" for v in md.table.values.values()))
md.table.pick(md.changes[0]["i"], "theirs")
check("theirs taken: in", md.apply() == 1 and SD.section_people(M, "1.3 Mission Operations")["lead"] == "S. Patel")
md.close()
said = []
w.status = lambda m, *a, **k: said.append(m)
check("a workbook in another design is refused in plain words", mp.bring_back(x1, accept=True) is None and any("design" in m for m in said), said)

print(f"QT MATRIX BACK 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
