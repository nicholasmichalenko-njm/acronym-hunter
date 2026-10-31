"""3.3.0 Deliver > Wall of Truth, offscreen: + Truth adds one to the table; changing its value keeps the old one; Check
the drafts reads the Volumes folder and lists findings with volume, section and sentence; Right as written leaves one
out; Save to the team's wall and Add the team's facts carry a fact to another effort; Export the wall and the findings."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortrec as RR, walloftruth as WT, docxw, effortfolders as EF
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey"); f.create(); app.processEvents()
check("Wall of Truth sits in Deliver, after Storyboards", [k for g, it in RAIL if g == "Deliver" for k, _l in it] == ["matrix", "setup", "storyboards", "truth", "postsub"])
w.go("truth"); app.processEvents()
pg = w.truth_page
check("an empty wall says how to start", pg.table.rowCount() == 0 and "+ Truth" in pg.note.text())
a = pg.truth_dialog(None, {"label": "Cleared staff", "kind": "Number", "value": "142", "context": "cleared staff, cleared employees",
                           "wrong": "", "owner": "", "source": "HR", "notes": ""})
b = pg.truth_dialog(None, {"label": "Customer", "kind": "Term", "value": "the Government", "context": "", "wrong": "the client",
                           "owner": "", "source": "", "notes": ""})
check("+ Truth adds rows to the wall", pg.table.rowCount() == 2 and pg.table.item(0, 2).text() == "142")
pg.truth_dialog(a, {"label": "Cleared staff", "kind": "Number", "value": "145", "context": "cleared staff, cleared employees", "wrong": "",
                    "owner": "", "source": "HR", "notes": ""})
check("changing the value keeps the old one (shown under Not)", pg.table.item(0, 2).text() == "145" and "142" in pg.table.item(0, 4).text())
vdir = EF.folder(w.effort_path, "volumes")
d = docxw.Doc(); d.heading("Staffing", 2); d.para("We bring 142 cleared staff. We have supported the client for years.")
d.save(os.path.join(vdir, "Volume II Management.docx"))
got = pg.check()
check("Check the drafts lists each disagreement with volume and sentence", len(got) == 2 and pg.found.rowCount() == 2
      and pg.found.item(0, 1).text() == "Volume II Management" and "2 places disagree" in pg.summary.text(), [x["problem"] for x in got])
pg.ignore([1])
check("Right as written leaves one out, now and next time", pg.found.rowCount() == 1 and len(pg.check()) == 1)
x = pg.export_findings(os.path.join(tmp, "f.xlsx"))
check("Export... the findings", os.path.isfile(x))
y = pg.export_wall(os.path.join(tmp, "wall.docx"))
check("Export the wall... a Word page", "Cleared staff" in zipfile.ZipFile(y).read("word/document.xml").decode("utf-8"))
pg.table.selectRow(0)
check("Save to the team's wall", pg.to_team() == 1 and WT.team_load(cfg)[0]["label"] == "Cleared staff")
check("Confirm dates the selected truth today", pg.confirm() == 1)
w.go("home"); app.processEvents()
w.close_effort(); w.go("home"); app.processEvents()
f.name.setText("Falcon"); f.create(); app.processEvents()
w.go("truth"); app.processEvents()
check("another effort is told the team's wall has a fact for it", "1 more" in pg.note.text(), pg.note.text())
check("Add the team's facts brings it in", pg.add_team() == 1 and pg.table.item(0, 1).text() == "Cleared staff")
pg.table.selectRow(0)
check("Remove", pg.remove() == 1 and pg.table.rowCount() == 0)
w.close()
n = sum(checks)
print(f"QT TRUTH {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
