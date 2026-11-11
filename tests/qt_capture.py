"""2.70.0 in Qt, offscreen: the lead-in before a list has its own box in Assign; Add missed text: the button turns on
area mode, a drag on the page reads the text inside (the PDF's own text), the person checks it, and it is added as a
sentence in its place with a box, here as a compliance requirement in the target; Esc leaves area mode."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
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
# 3.19.0: text whose words are not in the PDF's text (OCR, a fixed wording, a header band) is boxed by its area
pg.ask_text = lambda got, how: ("The Offeror shall describe the approach (wording fixed by hand)", False)
far_area = area.translated(0, 60)
fixed = pg.capture_area(far_area)
app.processEvents()
check("3.19.0: added text its words cannot be found for still gets a box, from its area", fixed is not None and fixed["id"] in pg.view.boxes
      and fixed.get("area", "").startswith(f"{fixed['page']}:") and pg.view.boxes[fixed["id"]].zValue() > 0, fixed and fixed.get("area"))
pg.view.scene().clearSelection(); pg.select(fixed["id"]); app.processEvents()
check("... and it selects", [x["id"] for x in pg.selected()] == [fixed["id"]])
import tempfile as _tf, compliance as _C
_p = os.path.join(_tf.mkdtemp(), "m.xlsx"); _old = M.path; M.path = _p; M.save(); M.path = _old
_Y = _C.Matrix(_p); _Y.load()
check("... the area is kept in the matrix workbook", next(x for x in _Y.items if x["id"] == fixed["id"]).get("area") == fixed["area"])
pg.toggle_capture(True)
QTest.keyClick(pg.view, Qt.Key_Escape); app.processEvents()
check("Esc leaves area mode", not pg.view.capturing)
# 3.15.1: pan the page: the Pan tool (H), Space and drag, a middle-button drag
pg.view.zoom = 1.0; pg.view.resetTransform(); pg.view.scale(2.5, 2.5); app.processEvents()
vs, hs = pg.view.verticalScrollBar(), pg.view.horizontalScrollBar()
vs.setValue(vs.maximum() // 2); hs.setValue(hs.maximum() // 2); app.processEvents()
sel0 = len(pg.view.scene().selectedItems())


def drag(button, a, b, mod=Qt.NoModifier):
    QTest.mousePress(pg.view.viewport(), button, mod, a)
    ev_pos = b
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPointF, QEvent
    me = QMouseEvent(QEvent.MouseMove, QPointF(ev_pos), QPointF(pg.view.viewport().mapToGlobal(ev_pos)), Qt.NoButton, button, mod)
    app.sendEvent(pg.view.viewport(), me)
    QTest.mouseRelease(pg.view.viewport(), button, mod, b)
    app.processEvents()


from PySide6.QtCore import QPoint
v0, h0 = vs.value(), hs.value()
drag(Qt.MiddleButton, QPoint(400, 400), QPoint(340, 300))
check("a middle-button drag moves the page", vs.value() == v0 + 100 and hs.value() == h0 + 60, (v0, vs.value(), h0, hs.value()))
QTest.keyClick(pg.view, Qt.Key_H); app.processEvents()
check("H turns on the Pan tool", pg.view.pan_tool and pg.pan_btn.isChecked())
v0 = vs.value()
drag(Qt.LeftButton, QPoint(400, 300), QPoint(400, 380))
check("with the Pan tool a left drag moves the page and selects nothing", vs.value() == v0 - 80
      and len(pg.view.scene().selectedItems()) == sel0, (v0, vs.value()))
pg.toggle_capture(True)
check("Add missed text turns the Pan tool off", pg.view.capturing and not pg.view.pan_tool and not pg.pan_btn.isChecked())
pg.toggle_capture(False)
QTest.keyPress(pg.view, Qt.Key_Space); app.processEvents()
v0 = vs.value()
drag(Qt.LeftButton, QPoint(400, 380), QPoint(400, 330))
QTest.keyRelease(pg.view, Qt.Key_Space); app.processEvents()
check("Space and drag moves the page; letting go of Space ends it", vs.value() == v0 + 50 and not pg.view._space, (v0, vs.value()))
# 3.15.1: authors on a selection: on requirements and context, with the reason shown for the rest
from PySide6.QtWidgets import QLabel
und = [it for it in M.items if not it.get("decision")][:2]
pg.show_card(und); app.processEvents()
txt = " ".join(x.text() for x in pg.card.findChildren(QLabel))
check("undecided sentences: the author field says to decide them first", not pg.authors.btn.isEnabled()
      and "Decide the sentence first" in txt)
keep = [it for it in M.items if it.get("decision") == "Keep"][:2]
pg.show_card(keep + und[:1]); app.processEvents()
txt = " ".join(x.text() for x in pg.card.findChildren(QLabel))
check("a mixed selection: Choose is on, for the requirement and context sentences", pg.authors.btn.isEnabled()
      and f"Authors go on the {len(keep)} requirement" in txt, txt[-200:])
w.authors.add("Ann Writer", efforts=["Heron"]); w.authors.add("Bo Author", efforts=["Heron"])
got = pg.authors.choose(answer=["Ann Writer", "Bo Author"])
check("many authors on many sentences at once", got == ["Ann Writer", "Bo Author"]
      and all(it.get("owner") == "Ann Writer, Bo Author" for it in keep) and not und[0].get("owner"), [it.get("owner") for it in keep])
w.close()
n = sum(checks)
print(f"QT CAPTURE PASS ({n}/{len(checks)})" if n == len(checks) else f"QT CAPTURE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
