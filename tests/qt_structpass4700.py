"""4.70.0 and 4.71.0: the Response Structure pass on the screen. Shred's first tab; the bar beside a piece has Volume and Heading
1 to 3 (keys 1 to 4), Not needed (X) and Ask a question; a mark fills the outline tree beside the page at once; a near
match asks once; Enter takes a suggestion and goes on; the other Shred tabs are as they were. Fictional (Kestrel)."""
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
import structmark as SM, shredtypes as ST
from skqt import structpass as SP, shredselbar as SSB
pg = w.assign_page


def bar():
    SSB.refresh(pg); app.processEvents()
    return pg.sel_bar


def labels():
    return [C.outline_label(o) for o in M.outline]


check("Shred's tabs: Response Structure first, the others as they were", [k for k, _t in MW.TABS["assign"]] ==
      ["structpass", "comppass", "assign", "requirements", "evalcrit", "acronyms"] and list(k for k in w.stepper.chips if ":" not in k)[0] == "structpass")
check("on Requirements the pass's pane is not there", not getattr(pg, "struct_panel", None) or not pg.struct_panel.isVisibleTo(pg))
before_outline = labels()
w.go("structpass"); app.processEvents()
check("the tab opens the Shred page in the pass, titled Shred", w.stack.currentWidget() is pg and pg.focus == "struct" and w.page_title.text() == "Shred"
      and w.step_btns["assign"].isChecked(), (pg.focus, w.page_title.text()))
check("the outline is beside the page as a tree; the piece pane and This document is shredded are not", pg.struct_panel.isVisibleTo(pg)
      and not pg.page_side.isVisibleTo(pg) and not pg.shred_check.isVisibleTo(pg))
check("this document's state: Not looked at, with Nothing of this kind in this document", "Not looked at" in pg.struct_state.text()
      and pg.struct_none.isVisibleTo(pg) and not pg.struct_none.isChecked(), pg.struct_state.text())
rows = [it for it in pg.R.rows_of(pg.file) if it.get("type") != "Heading"]
a, b_, c_, d_ = rows[0], rows[1], rows[2], rows[3]
for x, t in ((a, "Volume I Technical"), (b_, "Technical Approach"), (c_, "Technical Approach Overview"), (d_, "Risk Management")):
    x["text"] = t; x["lead"] = ""
M.outline[:] = []
pg.select(a["id"]); app.processEvents()
f = bar()
check("a piece selected: the bar has the four levels with their numbers, Not needed and Ask a question, and no type chips",
      f is not None and [b.text() for b in f.levels.values()] == ["1   Volume", "2   Heading 1", "3   Heading 2", "4   Heading 3"]
      and f.x.text() == "Not needed  X" and f.ask.text() == "Ask a question  A" and f.setup.text() == "For the setup  S" and not hasattr(f, "chips"), f and [b.text() for b in f.levels.values()])
QTest.keyClick(pg.view, Qt.Key_1); app.processEvents()
check("1: Volume. The outline has it at once, and the tree shows it", labels() == ["Volume I Technical"] and pg.struct_tree.topLevelItemCount() == 1
      and pg.struct_tree.topLevelItem(0).text(0) == "Volume I Technical" and SM.level_of(M, a) == "volume", labels())
check("... the tree says which piece required it; the document Has finds (1)", a["id"] in pg.struct_tree.topLevelItem(0).text(1)
      and "Has finds (1)" in pg.struct_state.text() and not pg.struct_none.isVisibleTo(pg), pg.struct_state.text())
f = bar()
check("... the bar shows the level it has, and Take the mark off", f.levels["volume"].isChecked() and f.off is not None)
pg.select(b_["id"]); app.processEvents(); bar()
QTest.keyClick(pg.view, Qt.Key_2); app.processEvents()
check("2: Heading 1, under the volume", labels() == ["Volume I Technical", "1 Technical Approach"] and pg.struct_tree.topLevelItem(0).childCount() == 1, labels())
pg.select(c_["id"]); app.processEvents(); bar()
QTest.keyClick(pg.view, Qt.Key_2); app.processEvents()
f = bar()
check("a near match changes nothing and asks on the bar: Same as ...? Attach or Add as new", labels() == ["Volume I Technical", "1 Technical Approach"]
      and f.attach is not None and f.new is not None and not f.levels and pg._struct_ask[0] == c_["id"], labels())
QTest.keyClick(pg.view, Qt.Key_Return); app.processEvents()
check("Enter takes Attach: no heading added, the piece is marked", labels() == ["Volume I Technical", "1 Technical Approach"]
      and SM.level_of(M, c_) == "h1" and pg._struct_ask is None, labels())
u_ = rows[4]                                   # a piece left as the document has it (Undo draws the boxes again from the page)
pg.select(u_["id"]); app.processEvents(); f = bar()
f.levels["h2"].click(); app.processEvents()
check("a click on Heading 2 puts it under the Heading 1 above", len(M.outline) == 3 and M.outline[2]["level"] == M.outline[1]["level"] + 1
      and M.outline[2].get("req") == u_["id"] and M.outline[2]["num"] == "1.1", labels())
pg.do_undo(); app.processEvents()
M = pg.R.M
byid = {x["id"]: x for x in M.items}
a, b_, c_, d_, u_ = (byid[x["id"]] for x in (a, b_, c_, d_, u_))
rows = [byid[x["id"]] for x in rows]
check("Undo takes the heading back out, and the piece stays selected", labels() == ["Volume I Technical", "1 Technical Approach"] and SM.level_of(M, u_) == ""
      and [x["id"] for x in pg.selected()] == [u_["id"]], (labels(), SM.level_of(M, u_)))
bar()
QTest.keyClick(pg.view, Qt.Key_X); app.processEvents()
check("X: Not needed. No heading, and the bar shows it", labels() == ["Volume I Technical", "1 Technical Approach"] and SM.level_of(M, u_) == "x" and bar().x.isChecked())
QTest.keyClick(pg.view, Qt.Key_X); app.processEvents()
check("X again opens it again", SM.level_of(M, u_) == "")
bar().levels["h1"].click(); app.processEvents()
check("Heading 1 on it: a second heading under the volume", len(M.outline) == 3 and M.outline[2].get("req") == u_["id"])
f = bar(); f.off.click(); app.processEvents()
check("Take the mark off: its own empty heading goes", labels() == ["Volume I Technical", "1 Technical Approach"] and u_["id"] not in SM.marks(M), labels())
it0 = pg.struct_tree.topLevelItem(0)
pg.view.scene().clearSelection(); pg.struct_tree.itemClicked.emit(it0, 0); app.processEvents()
check("a heading's row selects the piece that required it", [x["id"] for x in pg.selected()] == [a["id"]])
# Enter takes a suggestion and goes on
e1, e2 = rows[5], rows[7]
e1["text"] = "The proposal shall be organized as follows: (1) Management Plan; (2) Staffing; (3) Transition."; e1["lead"] = ""
e2["text"] = "The Offeror shall submit two volumes: Volume II (Management) and Volume III (Cost)."; e2["lead"] = ""
SP.fill(pg)
check("the hint counts what the app reads as setting the structure", len(SM.suggestions(M)) >= 2 and "Enter takes one" in pg.struct_hint.text(), pg.struct_hint.text())
pg.select(e1["id"]); app.processEvents(); f = bar()
check("a piece that lists several sections shows each item as a ticked line", [c.text() for c in f.lines] == ["Management Plan", "Staffing", "Transition"]
      and all(c.isChecked() for c in f.lines) and f.lead is not None, [c.text() for c in f.lines])
f.lines[1].setChecked(False); app.processEvents()
n0 = len(M.outline)
QTest.keyClick(pg.view, Qt.Key_Return); app.processEvents()
got = [o["title"] for o in M.outline]
check("Enter takes the suggestion: the ticked lines become headings, the unticked one does not", "Management Plan" in got and "Transition" in got
      and "Staffing" not in got and len(M.outline) == n0 + 2, got)
check("... and goes to the next piece the pass suggests", [x["id"] for x in pg.selected()] == [SM.next_suggestion(M, e1["id"])["id"]] or
      [x["id"] for x in pg.selected()] == [e2["id"]], [x["id"] for x in pg.selected()])
pg.select(a["id"]); app.processEvents()
QTest.keyClick(pg.view, Qt.Key_N); app.processEvents()
check("N goes to the next suggestion without marking", pg.selected() and pg.selected()[0]["id"] in [x["id"] for x in SM.suggestions(M)] and pg.selected()[0]["id"] not in SM.marks(M))
QTest.keyClick(pg.view, Qt.Key_O); app.processEvents()
check("a type's own key marks nothing in this pass", pg.selected()[0]["id"] not in SM.marks(M))
# the other document, and out of the pass
other = [fn for fn in pg.R.files() if fn != pg.file]
if other:
    pg.open_file(other[0]); app.processEvents(); SP.fill(pg)
    pg.struct_none.click(); app.processEvents()
    check("the other document: one click says Nothing of this kind here", [d["state"] for d in SM.docs(M) if d["file"] == other[0]] == ["Nothing of this kind here"]
          and pg.struct_none.isChecked(), SM.docs(M))
# 4.71.0: the count, For the setup, A, Not required by the customer, a heading dragged
pg.open_file([fn for fn in pg.R.files() if "Section_L" in fn][0]); app.processEvents(); SP.fill(pg)
nmark = sum(1 for m in SM.marks(M).values() if m.get("level") in SM.DEPTH)
check("4.71.0: the tab's own count is right as he marks", w.stepper.chips["structpass"].ct.text() == f"{nmark} marked", w.stepper.chips["structpass"].ct.text())
pg.select(rows[10]["id"]); app.processEvents(); f = bar()
names = [x.text().strip() for x in f.setup_menu.actions()]
check("For the setup lists the outline's headings", names == [C.outline_label(o) for o in M.outline] and len(names) >= 2, names)
QTest.keyClick(pg.view, Qt.Key_S); app.processEvents()
check("S opens that list beside the piece (and splits nothing)", getattr(pg, "_struct_menu", None) is not None and len(pg._struct_menu.actions()) == len(names))
pg._struct_menu.close()
target = C.outline_label(M.outline[1])
[x for x in pg._struct_menu.actions() if x.text().strip() == target][0].trigger(); app.processEvents()
check("a pick sends the piece there as text for the author: the customer's own, in that section", rows[10]["map"] == target and rows[10]["decision"] == "Customer"
      and SM.level_of(M, rows[10]) == "s" and bar().setup.isChecked(), (rows[10].get("map"), rows[10].get("decision")))
asked = []
import skqt.typechips as TCZ
keep_ask = TCZ.ask; TCZ.ask = lambda page: asked.append(page.selected()[0]["id"])
QTest.keyClick(pg.view, Qt.Key_A); app.processEvents()
TCZ.ask = keep_ask
check("A asks a question about the selected piece", asked == [rows[10]["id"]], asked)
check("Not required by the customer shows, unticked", pg.struct_closed.isVisibleTo(pg) and not pg.struct_closed.isChecked())
pg.struct_closed.click(); app.processEvents()
check("one click closes the pass: the tree stays, the hint and the tab say so", SM.closed(M) and pg.struct_closed.isChecked() and pg.struct_hint.text().startswith("Closed")
      and pg.struct_tree.topLevelItemCount() >= 1, pg.struct_hint.text())
QTest.keyClick(pg.view, Qt.Key_N); app.processEvents()
check("... N goes nowhere while it is closed", [x["id"] for x in pg.selected()] == [rows[10]["id"]])
pg.struct_closed.click(); app.processEvents()
check("... and one click opens it again", not SM.closed(M) and not pg.struct_closed.isChecked())
lab_before = [C.outline_label(o) for o in M.outline]
kids = [C.outline_label(o) for o in M.outline if o["level"] == 2]
if len(kids) >= 2:
    new = SP.moved(pg, kids[-1], kids[0], "into"); app.processEvents()
    o = M.outline[[C.outline_label(x) for x in M.outline].index(new)]
    check("a heading dragged into another goes under it; the tree is drawn again", new is not None and o["level"] == 3
          and pg.struct_tree.topLevelItem(0).child(0).childCount() >= 1, [C.outline_label(x) for x in M.outline])
    pg.do_undo(); app.processEvents(); M = pg.R.M
    check("Undo puts it back", [C.outline_label(o) for o in M.outline] == lab_before, [C.outline_label(o) for o in M.outline])
    byid = {x["id"]: x for x in M.items}; rows = [byid[x["id"]] for x in rows]
check("the tree takes a drag", pg.struct_tree.dragDropMode() == pg.struct_tree.DragDropMode.InternalMove)
w.go("assign"); app.processEvents()
check("back on Requirements: the piece pane, the type chips and no outline pane", pg.focus == "shred" and not pg.struct_panel.isVisibleTo(pg)
      and pg.page_side.isVisibleTo(pg))
pg.select(rows[9]["id"]); app.processEvents(); f = bar()
check("... the bar there has the types, as before", f is not None and hasattr(f, "chips") and "requirement" in f.chips)
QTest.keyClick(pg.view, Qt.Key_1); app.processEvents()
check("... and 1 marks nothing there", rows[9]["id"] not in SM.marks(M))
w.go("place"); app.processEvents()
check("Place is as it was", pg.focus == "place" and not pg.struct_panel.isVisibleTo(pg))
w.go("structpass"); app.processEvents()
check("back in the pass, the tree is as it was left", pg.struct_tree.topLevelItemCount() >= 1 and pg.struct_tree.topLevelItem(0).text(0) == "Volume I Technical")
w.close()
print(f"QT STRUCTPASS 4700 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
