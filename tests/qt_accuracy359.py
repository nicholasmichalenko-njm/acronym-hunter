"""3.59.0 Shred > Accuracy, offscreen. The set folder (a setting); the RFPs in it, labeled or not; Save this effort's
Review as answer keys; Score the set (each RFP's recall and precision, the set's scores against the target, the history
by release); Read into Review's Set aside...; an Amendment added to the Library adds its acknowledgment row. Fictional content."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from skqt import mainwin as MW
check("Accuracy is one of Quick tools (4.19.0; Shred's views are Page and List)", MW.RAIL_OF["shredacc"] == "tools" and "shredacc" in __import__("skqt.toolshome", fromlist=["x"]).TOOLS)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
import unfiled as UF
w.work_on(UF.NAME); app.processEvents()
w.go("shredacc"); app.processEvents()
ap = w.accuracy_page
check("it opens on the set folder in the user's folder, said when not made yet", w.stack.currentWidget() is ap
      and "Stationkeeper Shred Set" in ap.folder.text())
SET = os.path.join(tmp, "Shred Set"); os.makedirs(SET)
rfp = shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx"), SET)
ap.choose(SET)
check("Choose the folder: the RFPs in it, not labeled yet", ap.files.rowCount() == 1 and ap.files.item(0, 1).text() == "not labeled yet")
r0 = ap.score()
check("Score with nothing labeled: says so, logs nothing", r0["labeled"] == 0 and "nothing labeled" in ap.p_recall.text() and ap.hist.rowCount() == 0)
check("Save the keys with no review open says what to do", ap.save_keys() == [])

# read the RFP into Review in the test effort, decide it
w.go("read"); app.processEvents()
rp = w.read_page
import compliance_read as CR
items, heads, src, empty = CR.read_files([rfp], A.typed_chunks)
M = CR.new_matrix(os.path.join(tmp, "Test_Compliance_Matrix.xlsx"), items, heads, src)
w.set_matrix(M, new=True)
import shredquick as SQ, compliance as C
flags = {C.text_key(r["text"]) for r in SQ.shred(rfp)["rows"]}
for it in M.items:
    it["decision"] = "Keep" if it["key"] in flags else "Context"
w.go("shredacc"); app.processEvents()
got = ap.save_keys()
check("Save this effort's Review as answer keys", got and os.path.isfile(rfp + ".answers.csv") and ap.files.item(0, 1).text() == "labeled")
r = ap.score()
check("Score the set: the RFP's scores", r["labeled"] == 1 and ap.files.item(0, 3).text() == "100%" and "of" in ap.files.item(0, 1).text())
check("... the set against the target", "100%" in ap.p_recall.text() and "target 95%" in ap.p_recall.text())
check("... by kind", "Instruction (L)" in ap.kinds.text())
check("... and the history by release", ap.hist.rowCount() == 1 and ap.hist.item(0, 1).text() == A.APP_VERSION)

# what a read set aside
check("Read into Review has Set aside...", hasattr(rp, "aside_btn") and rp.show_aside(run=False) is not None)

# an amendment added to the Library
w.go("docs"); app.processEvents()
dp = w.docs_page
dp.add([rfp], choices=[{}])
amd = os.path.join(tmp, "Kestrel_RFP_Sections_C_L_M_Amendment_1.docx")
shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx"), amd)
import docxw
d = docxw.Doc(); [d.para(t) for t in (["Amendment 1 changes the page limit for Volume I to 30 pages."] + [r["text"] for r in SQ.shred(rfp)["rows"]])]; d.save(amd)
n0 = len(M.items)
made = dp.add([amd], choices=[{}])
rows = [it for it in M.items if it.get("text", "").startswith("Acknowledge")]
check("an Amendment in the Library adds its acknowledgment row", len(rows) == 1 and len(M.items) == n0 + 1,
      ([it.get("text") for it in rows], [(x[0].get("type"), x[1].get("label")) for x in made or []]))
check("guide topic and title", "shredacc" in __import__("skqt.guide", fromlist=["TOPIC"]).TOPIC
      and "shredacc" in __import__("skqt.pagetitles", fromlist=["TITLES"]).TITLES)
w.close()
n = sum(checks)
print(f"QT ACCURACY {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
