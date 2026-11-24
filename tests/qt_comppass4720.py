"""4.72.0: the Compliance pass on the screen. Shred's second tab; nothing beside the page but the bar: Work Requirement
(SOW), Response Instruction (L), Evaluation Criterion (M) on 1 to 3, In Matrix under with the suggested section, Not
needed, Ask a question, For the setup; a mark is a row of the matrix at once; Enter takes what is suggested and goes on.
Fictional (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import assignlinks as AL, compliance as C, effort as E, workspace as W, setupdoc as SD
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
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
M = w.review.M
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import compmark as CM, shredtypes as ST, setupdoc as SDZ, assignlinks as ALZ
from skqt import comppass as CP, shredselbar as SSB
pg = w.assign_page


def bar():
    SSB.refresh(pg); app.processEvents()
    return pg.sel_bar


def fresh():
    global M, rows
    M = pg.R.M
    rows = [it for it in pg.R.rows_of(pg.file) if it.get("type") != "Heading"]


check("Shred's tabs: Response Structure, Compliance, then the others as they were", [k for k, _t in MW.TABS["assign"]] ==
      ["structpass", "comppass", "assign", "requirements", "evalcrit", "acronyms"])
M.outline[:] = C.parse_outline("Volume I Technical\n1 Technical Approach\n1.1 Thermal Design\n2 Management")
w.go("comppass"); app.processEvents()
check("the tab opens the Shred page in the pass, titled Shred", w.stack.currentWidget() is pg and pg.focus == "comp" and w.page_title.text() == "Shred")
check("nothing is beside the page: no piece pane, no outline tree, no This document is shredded", not pg.page_side.isVisibleTo(pg)
      and not pg.struct_panel.isVisibleTo(pg) and not pg.shred_check.isVisibleTo(pg))
check("the row above the page says the document's state, with Nothing of this kind in this document", pg.comp_state.isVisibleTo(pg)
      and "Not looked at" in pg.comp_state.text() and pg.comp_none.isVisibleTo(pg), pg.comp_state.text())
fresh()
a = rows[6]
pg.select(a["id"]); app.processEvents(); f = bar()
check("a piece selected: three kinds with their numbers, then Not needed, Ask a question, For the setup; no type chips",
      f is not None and [b.text() for b in f.kinds.values()] == ["1   Work Requirement (SOW)", "2   Response Instruction (L)", "3   Evaluation Criterion (M)"]
      and f.x.text() == "Not needed  X" and f.ask.text() == "Ask a question  A" and f.setup.text() == "For the setup  S" and not hasattr(f, "chips"))
n0 = CM.count(M)
QTest.keyClick(pg.view, Qt.Key_2); app.processEvents(); fresh()
a = next(x for x in rows if x["id"] == a["id"])
check("2: Response Instruction (L). The piece is a requirement of the matrix at once, marked L", CM.kinds_of(a) == ["instruction"] and a["decision"] == "Keep"
      and a.get("lm") == "L" and CM.count(M) == n0 + 1, (CM.kinds_of(a), a.get("decision"), a.get("lm")))
check("... the tab's count and the document's state follow at once", w.stepper.chips["comppass"].ct.text() == f"{CM.count(M)} in the matrix"
      and "Has finds" in pg.comp_state.text() and not pg.comp_none.isVisibleTo(pg), (w.stepper.chips["comppass"].ct.text(), pg.comp_state.text()))
f = bar()
check("... the bar shows the kind it has, and In Matrix under", f.kinds["instruction"].isChecked() and f.where is not None and f.where.text().startswith("In Matrix under")
      and f.pick is not None and [x.text().strip() for x in f.pick_menu.actions()] == [C.outline_label(o) for o in M.outline])
[x for x in f.pick_menu.actions() if x.text().strip() == "1.1 Thermal Design"][0].trigger(); app.processEvents(); fresh()
a = next(x for x in rows if x["id"] == a["id"])
check("Pick another section puts it there", SDZ.item_sections(M, a) == ["1.1 Thermal Design"] and "1.1 Thermal Design" in bar().where.text(), SDZ.item_sections(M, a))
check("... Matrix > Assign reads the same link", [r["sections"] for r in ALZ.rows(M, "all") if r["id"] == a["id"]] == [["1.1 Thermal Design"]])
QTest.keyClick(pg.view, Qt.Key_2); app.processEvents(); fresh()
a = next(x for x in rows if x["id"] == a["id"])
check("2 again takes the kind off", CM.kinds_of(a) == [] and CM.count(M) == n0)
b_ = rows[8]
pg.select(b_["id"]); app.processEvents(); bar()
QTest.keyClick(pg.view, Qt.Key_X); app.processEvents()
check("X: Not needed in this pass. The piece is not dropped from the shred", CM.state(M, b_) == "x" and not b_.get("decision") and bar().x.isChecked())
check("... it is out of the pass's next", b_["id"] not in [x["id"] for x in CM.open_rows(M, pg.file)])
QTest.keyClick(pg.view, Qt.Key_X); app.processEvents()
check("X again opens it again", CM.state(M, b_) == "")
f = bar()
[x for x in f.setup_menu.actions() if x.text().strip() == "2 Management"][0].trigger(); app.processEvents(); fresh()
b_ = next(x for x in rows if x["id"] == b_["id"])
check("For the setup: the customer's own, in the section picked, out of the pass's next", b_["decision"] == "Customer" and b_["map"] == "2 Management"
      and CM.state(M, b_) == "s" and bar().setup.isChecked(), (b_.get("decision"), b_.get("map")))
# Enter: the suggested kind, the suggested section, and on
c_ = next((x for x in rows if CP._suggested_kind(pg, x)), None)
check("the app suggests a kind for some piece here", c_ is not None)
if c_ is not None:
    pg.select(c_["id"]); app.processEvents(); f = bar()
    sug = CP._suggested_kind(pg, c_)
    want = CM.suggested_section(M, c_)
    check("the suggested kind leads the bar", f.lead is f.kinds[sug] and (f.take is None) == (not want), (sug, want))
    QTest.keyClick(pg.view, Qt.Key_Return); app.processEvents(); fresh()
    c2 = next(x for x in rows if x["id"] == c_["id"])
    check("Enter takes the kind (and the suggested section when there is one)", sug in CM.kinds_of(c2) and (not want or SDZ.item_sections(M, c2) == [want]),
          (CM.kinds_of(c2), SDZ.item_sections(M, c2)))
    sel = [x["id"] for x in pg.selected()]
    check("... and goes to the next piece the pass has not dealt with", sel and sel[0] != c_["id"] and sel[0] in [x["id"] for x in CM.open_rows(M, pg.file)], sel)
    pg.do_undo(); app.processEvents(); fresh()
before = [x["id"] for x in pg.selected()]
QTest.keyClick(pg.view, Qt.Key_N); app.processEvents()
check("N goes on without marking", pg.selected() and [x["id"] for x in pg.selected()] != before and not CM.kinds_of(pg.selected()[0]))
other = [fn for fn in pg.R.files() if fn != pg.file]
if other:
    pg.open_file(other[0]); app.processEvents(); CP.fill(pg)
    if pg.comp_none.isVisibleTo(pg):
        pg.comp_none.click(); app.processEvents()
        check("the other document: one click says Nothing of this kind here", [d["state"] for d in CM.docs(pg.R.M) if d["file"] == other[0]] == ["Nothing of this kind here"])
check("the pass keeps a wider margin for its bar, and the bar is inside it", pg.view.viewportMargins().right() == CP.WIDE
      and (bar() is None or pg.sel_bar.geometry().right() <= pg.view.width()), pg.view.viewportMargins().right())
w.go("structpass"); app.processEvents()
check("... the other tabs keep the margin they had", pg.view.viewportMargins().right() == SSB.GUTTER, pg.view.viewportMargins().right())
check("Response Structure is as it was: its tree, its own bar", pg.focus == "struct" and pg.struct_panel.isVisibleTo(pg) and not pg.comp_state.isVisibleTo(pg))
w.go("assign"); app.processEvents()
check("Requirements is as it was: the piece pane, the type chips", pg.focus == "shred" and pg.page_side.isVisibleTo(pg) and not pg.comp_state.isVisibleTo(pg)
      and not pg.struct_panel.isVisibleTo(pg))
w.close()
print(f"QT COMPPASS 4720 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
