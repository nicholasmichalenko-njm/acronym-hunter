"""4.69.0: the Matrix tab. A switch on the page, By section or By requirement (the choice Design > Rows already made);
the L/M crosswalk off the tabs, whole, under Matrix > More. Fictional (Kestrel)."""
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
pg = w.matrix_page
import matrixdesign as MD
check("Matrix's tabs: Assign, Check, Matrix", [k for k, _t in MW.TABS["matrix"]] == ["assignto", "linkcheck", "matrix"])
w.go("matrix"); app.processEvents()
check("the Matrix tab is showing, with three tabs", w.stack.currentWidget() is pg and w._tab_keys == ["assignto", "linkcheck", "matrix"])
check("the switch: By section and By requirement, on the page with the design closed",
      [b.text() for b in pg.layout_btns.values()] == ["By section", "By requirement"] and all(b.isVisible() for b in pg.layout_btns.values())
      and not pg.design_w.isVisible())
check("it starts on the layout the design holds", pg.layout_btns[pg.d["layout"]].isChecked() and sum(b.isChecked() for b in pg.layout_btns.values()) == 1)
start = pg.d["layout"]; other = "sentences" if start == "outline" else "outline"
pg.layout_btns[other].click(); app.processEvents(); pg.preview()
check("a click changes the layout, kept with the matrix", pg.d["layout"] == other and MD.of_matrix(M)["layout"] == other and pg.layout_btns[other].isChecked()
      and not pg.layout_btns[start].isChecked())
check("... the table is that layout's own columns", [pg.model.horizontalHeaderItem(i).text() for i in range(pg.model.columnCount())]
      == [c["heading"] for c in MD.default(other)["columns"]])
check("... and Design > Rows says the same", pg.layout_box.currentData() == other)
n_other = pg.model.rowCount()
pg.layout_btns[other].click(); app.processEvents()
check("a click on the one showing leaves it showing", pg.d["layout"] == other and pg.layout_btns[other].isChecked())
pg.layout_box.setCurrentIndex(pg.layout_box.findData(start)); app.processEvents(); pg.preview()
check("changed in Design > Rows, the switch follows", pg.d["layout"] == start and pg.layout_btns[start].isChecked() and not pg.layout_btns[other].isChecked())
check("the two layouts are not the same table", pg.model.columnCount() != len(MD.default(other)["columns"]) or pg.model.rowCount() != n_other
      or [c["key"] for c in MD.default(start)["columns"]] != [c["key"] for c in MD.default(other)["columns"]])
names = [a.text() for a in pg.bar.more_menu.actions() if a.text()] if hasattr(pg.bar, "more_menu") else []
check("More has The L/M crosswalk...", "The L/M crosswalk..." in names, names)
[a for a in pg.bar.more_menu.actions() if a.text() == "The L/M crosswalk..."][0].trigger(); app.processEvents()
import crosswalk as X
check("it opens the crosswalk whole: its rows, with Matrix lit and no tab of its own", w.crosswalk_page.isVisibleTo(w.assign_page)
      and w.crosswalk_page.table.rowCount() == len(X.build(M)) and w.step_btns["matrix"].isChecked() and "crosswalk" not in w._tab_keys, w._tab_keys)
check("... titled L/M Crosswalk", "Crosswalk" in w.page_title.text(), w.page_title.text())
w.go("matrix"); app.processEvents()
check("back on Matrix", w.stack.currentWidget() is pg)
w.close()
print(f"QT MATRIX 4690 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
