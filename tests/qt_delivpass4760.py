"""4.76.0: the Deliverables pass on the screen. Shred's second tab: Document We Write, Form We Fill In, File We Submit,
Redline We Return on 1 to 4, each a row of the Deliverables list at once; Key date (D) onto the calendar; Customer
heading, Send to Outline, More, Not needed, Ask a question, For the setup as on Compliance. Fictional (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import compliance as C, effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Kestrel"); app.processEvents()
w.read_page.read(PDFS, os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import compmark as CM, delivmark as DM, deliverables as DL, effortrec as RR, effortcal as EC, custstruct as CS
from skqt import comppass as CP, shredselbar as SSB
pg = w.assign_page


def bar():
    SSB.refresh(pg); app.processEvents()
    return pg.sel_bar


def fresh():
    global M, rows
    M = pg.R.M
    rows = [it for it in pg.R.rows_of(pg.file) if it.get("type") != "Heading"]


def rec():
    return RR.Record(w.ws.root)


check("Shred's tabs: Compliance, Deliverables, then the others as they were", [k for k, _t in MW.TABS["assign"]] ==
      ["comppass", "delivpass", "assign", "requirements", "evalcrit", "acronyms"] and dict(MW.TABS["assign"])["delivpass"] == "Deliverables")
w.go("delivpass"); app.processEvents()
check("the tab opens the Shred page in the pass, titled Shred", w.stack.currentWidget() is pg and pg.focus == "deliv" and w.page_title.text() == "Shred")
check("nothing is beside the page; the row above says the document's state", not pg.page_side.isVisibleTo(pg) and pg.comp_state.isVisibleTo(pg)
      and "Not looked at" in pg.comp_state.text() and pg.comp_none.isVisibleTo(pg) and "handed in" in pg.comp_none.toolTip(), pg.comp_state.text())
check("the tab's count starts at none marked", w.stepper.chips["delivpass"].ct.text() == "none marked", w.stepper.chips["delivpass"].ct.text())
fresh()
a = rows[6]
pg.select(a["id"]); app.processEvents(); f = bar()
check("a piece selected: four kinds with their numbers, Key date, then the bar Compliance has", f is not None
      and [b.text() for b in f.kinds.values()] == ["1   Document We Write", "2   Form We Fill In", "3   File We Submit", "4   Redline We Return"]
      and f.keydate.text() == "Key date  D" and f.head.text() == "Customer heading  H" and f.send.text() == "Send to Outline" and f.more.text() == "More  M"
      and f.x.text() == "Not needed  X" and f.ask.text() == "Ask a question  A" and f.setup.text() == "For the setup  S" and f.on_list is None)
QTest.keyClick(pg.view, Qt.Key_2); app.processEvents(); fresh()
a = next(x for x in rows if x["id"] == a["id"])
d = DL.of_piece(rec(), a["id"])
check("2: Form We Fill In. A row of the Deliverables list at once, holding the customer's words", d is not None and d["kind"] == "Form" and d["shred_kind"] == "form"
      and d["name"] and [p["sid"] for p in d["pieces"]] == [a["id"]] and d["pieces"][0]["doc"] == pg.file, d)
check("... the piece is not made a requirement by it", not a.get("decision") and CM.kinds_of(a) == [])
check("... the tab's count and the document's state follow at once", w.stepper.chips["delivpass"].ct.text() == "1 on the list"
      and "Has finds (1)" in pg.comp_state.text() and not pg.comp_none.isVisibleTo(pg), (w.stepper.chips["delivpass"].ct.text(), pg.comp_state.text()))
f = bar()
check("... the bar shows the kind and the deliverable's name, with a way to the list", f.kinds["form"].isChecked() and f.on_list is not None
      and f.on_list.text() == "On the Deliverables list: " + d["name"] and f.open_list is not None)
w.go("deliverables"); app.processEvents()
check("the Deliverables page lists it", any(x["id"] == d["id"] for x in DL.items(rec())) and w.stack.currentWidget() is not pg)
w.go("delivpass"); app.processEvents(); fresh()
pg.select(a["id"]); app.processEvents(); bar()
QTest.keyClick(pg.view, Qt.Key_4); app.processEvents()
d = DL.of_piece(rec(), a["id"])
check("4 changes it to Redline We Return: still one row", d["shred_kind"] == "redline" and d["kind"] == "Customer file" and len(DL.items(rec())) == 1 and bar().kinds["redline"].isChecked())
QTest.keyClick(pg.view, Qt.Key_4); app.processEvents()
check("4 again takes it off the list", DL.of_piece(rec(), a["id"]) is None and DL.items(rec()) == [] and w.stepper.chips["delivpass"].ct.text() == "none marked")
b_ = rows[8]
pg.select(b_["id"]); app.processEvents(); bar()
QTest.keyClick(pg.view, Qt.Key_X); app.processEvents()
check("X: Not needed in this pass only", CM.state(M, b_, "deliv_marks") == "x" and CM.state(M, b_) == "" and bar().x.isChecked())
QTest.keyClick(pg.view, Qt.Key_X); app.processEvents()
check("X again opens it again", CM.state(M, b_, "deliv_marks") == "")
n0 = len(EC.entries(rec())) if hasattr(EC, "entries") else None
got = __import__("skqt.delivpass", fromlist=["x"]).key_date(pg, {"kind": "Questions due", "date": "2027-03-01", "start": "", "zone": "", "title": "Questions due"})
check("Key date: on the effort's calendar at once", bool(got) and (n0 is None or len(EC.entries(rec())) == n0 + 1), got)
seen = []
pg._do_capture = lambda kind, answer=None: seen.append(kind) or ""
QTest.keyClick(pg.view, Qt.Key_D); app.processEvents()
del pg._do_capture
fresh()
check("D is Key date here; the piece is not typed by it", seen == ["keydate"] and not next(x for x in rows if x["id"] == b_["id"]).get("piece"), seen)
QTest.keyClick(pg.view, Qt.Key_H); app.processEvents(); f = bar()
check("H asks for the customer heading here too", f.head_edit is not None)
CP.head_cancel(pg); app.processEvents()
pg.comp_none.click(); app.processEvents()
check("Nothing of this kind in this document is the pass's own", pg.file in (M.setup.get("deliv_none") or []) and pg.file not in (M.setup.get("comp_none") or [])
      and "Nothing of this kind here" in pg.comp_state.text(), pg.comp_state.text())
w.go("comppass"); app.processEvents()
pg.select(a["id"]); app.processEvents(); f = bar()
check("Compliance keeps its own bar and state", pg.focus == "comp" and len(f.kinds) == 3 and getattr(f, "keydate", None) is None and "Not looked at" in pg.comp_state.text(), pg.comp_state.text())
w.go("assign"); app.processEvents()
check("Requirements is the Shred as it was", pg.focus in (None, "shred") and pg.page_side.isVisibleTo(pg), pg.focus)
print(f"{sum(checks)}/{len(checks)}")
if not all(checks):
    sys.exit(1)
print("ok qt_delivpass4760")
