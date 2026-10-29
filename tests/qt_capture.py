"""2.70.0 in Qt, offscreen: the lead-in before a list has its own box in Assign; Add missed text: the button turns on
area mode, a drag on the page reads the text inside (the PDF's own text), the person checks it, and it is added as a
sentence in its place with a box, here as a compliance requirement in the target; Esc leaves area mode."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Heron"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Heron_Effort_List.xlsx")
L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Heron").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
PDF = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
LEAD = "The description shall address the following:"
app = QApplication([])
theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION)
w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Heron")
w.read_page.read([PDF], os.path.join(EDIR, "Heron_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
pg = w.assign_page
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
lead = next(it for it in M.items if it["text"] == LEAD)
check("the lead-in before the bullets has its own box", lead["id"] in pg.view.boxes)
# pretend an older read missed it: take it out, then add it back from the page
area = pg.view.boxes[lead["id"]].path().boundingRect().adjusted(-2, -2, 2, 2)
M.items.remove(lead); pg.build_boxes(); app.processEvents()
check("without it, that text has no box", lead["id"] not in pg.view.boxes)
pg.set_target("1.1 Technical Approach")
seen = {}


def answer(got, how):
    seen["got"], seen["how"] = got, how
    return got, True


pg.ask_text = answer
pg.cap_btn.click(); app.processEvents()
check("Add missed text turns on area mode", pg.view.capturing and pg.cap_btn.isChecked())
pg.view.ensureVisible(area); app.processEvents()
a, b = pg.view.mapFromScene(area.topLeft()), pg.view.mapFromScene(area.bottomRight())
QTest.mousePress(pg.view.viewport(), Qt.LeftButton, Qt.NoModifier, a)
QTest.mouseMove(pg.view.viewport(), b)
QTest.mouseRelease(pg.view.viewport(), Qt.LeftButton, Qt.NoModifier, b)
app.processEvents()
check("a drag reads the text inside, from the PDF's own text", seen.get("how") == "pdf" and seen.get("got") == LEAD, seen)
new = next((it for it in M.items if it["text"] == LEAD), None)
check("it is added as a sentence with a box, a requirement in the target", new is not None and new["id"] in pg.view.boxes
      and new["decision"] == "Keep" and new["map"] == "1.1 Technical Approach", new and (new["id"], new["decision"], new["map"]))
nxt = M.items[M.items.index(new) + 1]
check("in its place: just before the list it leads", nxt.get("lead") == LEAD, nxt["text"][:40])
check("area mode ends after one area", not pg.view.capturing and not pg.cap_btn.isChecked())
pg.toggle_capture(True)
QTest.keyClick(pg.view, Qt.Key_Escape); app.processEvents()
check("Esc leaves area mode", not pg.view.capturing)
w.close()
n = sum(checks)
print(f"QT CAPTURE PASS ({n}/{len(checks)})" if n == len(checks) else f"QT CAPTURE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
