"""3.35.0 offscreen: the Matrix page starts as the outline matrix (one row per outline item, Section L beside Section M),
switches to sentence rows, saves a named view and a new version, and an effort type starts with it; Review's bottom bar
sets the target item's Assigned To, Initial Page Allocation and % Complete, which the matrix shows; Production Standards:
Based on and Next style are picked from a list, the preview fits its space and holds still, what changed is folded, a
click shows the preview larger, and the preview's column is a splitter."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import compliance as C, effort as E, workspace as W, office_pdf as OP, matrixdesign as MD, setupdoc as SD, pagebudget as PB
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox, QSplitter
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
import skqt.prodstdpage as PS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
M, R = w.review.M, w.review
labs = [C.outline_label(o) for o in M.outline]
a = next(it for it in M.items if it["text"].startswith("The Offeror shall describe its technical approach"))
R.req([a], "1.1 Technical Approach"); SD.set_lm(M, [a], "L"); w.changed()
pg = w.assign_page
pg.set_target("1.1 Technical Approach"); app.processEvents()
check("Review's bottom bar shows the target item's values", pg.item_row.isVisible() and pg.item_pct.value() == -1
      and pg.item_pages.value() == 0)
check("Assigned To from the bar", pg.set_item_value("who", "Dana Ruiz") and SD.section_people(M, "1.1 Technical Approach")["lead"] == "Dana Ruiz")
check("Initial Page Allocation from the bar", pg.set_item_value("pages", 4) and PB.pages(M, "1.1 Technical Approach") == 4)
check("% Complete from the bar, and Undo puts it back", pg.set_item_value("pct", 25) and SD.progress_of(M, "1.1 Technical Approach") == 25
      and (R.undo_last() or True) and SD.progress_of(M, "1.1 Technical Approach") is None and (pg.set_item_value("pct", 25) or True))
pg.show_item_values(); app.processEvents()
check("the bar shows what was set", pg.item_who.currentText() == "Dana Ruiz" and pg.item_pages.value() == 4 and pg.item_pct.value() == 25)
w.go("matrix"); app.processEvents()
mp = w.matrix_page
heads = [mp.model.horizontalHeaderItem(i).text() for i in range(mp.model.columnCount())]
check("the Matrix page starts as the outline matrix", mp.layout_box.currentData() == "outline" and heads[0] == "Response Section No. Item"
      and "One row per outline item" in mp.info.text(), heads)
row = next(r for r in range(mp.model.rowCount()) if mp.model.item(r, 0).text().strip() == "1.1 Technical Approach")
vals = [mp.model.item(row, c).text() for c in range(mp.model.columnCount())]
check("the item's row: who, pages, % complete, its Section L content", vals[1] == "Dana Ruiz" and vals[2] == "4" and vals[3] == "25%"
      and "technical approach" in vals[5], vals[:6])
check("order and context belong to sentence rows", not mp.order.isEnabled() and not mp.context.isEnabled())
mp.layout_box.setCurrentIndex(mp.layout_box.findData("sentences")); app.processEvents(); mp.preview()
check("sentence rows: their own columns", MD.of_matrix(M)["layout"] == "sentences" and mp.order.isEnabled()
      and "Volume" in [mp.model.horizontalHeaderItem(i).text() for i in range(mp.model.columnCount())])
mp.use_view("builtin:outline"); app.processEvents()
iid = mp.save_view("Kestrel outline")
check("Save as a view: in the list, in use", iid and mp.view_box.currentData() == iid and MD.of_matrix(M)["view"]["id"] == iid
      and "From Kestrel outline." in mp.view_note.text(), mp.view_note.text())
pct = next(i for i in range(mp.cols.count()) if mp.cols.item(i).data(0x0100) == "pct_complete")
from PySide6.QtCore import Qt
mp.cols.item(pct).setCheckState(Qt.Unchecked); app.processEvents()
check("a change for this effort says so, and a new version can be saved", "changed for this effort" in mp.view_note.text() and mp.ver_btn.isEnabled())
iid2 = mp.save_version("no % complete")
check("the new version is in use; the first stays", iid2 and iid2 != iid and len(MD.views(w.config_dir)) == 2
      and "v2" in mp.view_box.currentText())
w.ws.set("prod_std", {"effort_type": "rfp", "type": "proposal"})
mp.show_view_note()
check("an effort type starts with the view", mp.type_start() and MD.type_view(w.config_dir, "rfp") == iid2
      and mp.type_btn.text() == "This effort type starts with it")
# Production Standards
w.go("prodstd"); app.processEvents()
ps = w.prodstd_page
keys = [k for k, _t in PS.SECTIONS]
ps.work["style_defs"] = {"Body": {"font": "Arial", "size": 11}, "Heading 1": {"font": "Arial", "size": 16, "bold": True},
                         "Callout": {"based_on": "Bodyy"}}
ps.show_section(keys.index("styledefs")); app.processEvents()
spec = ps.tables["styledefs"]; ps._fill_table("styledefs", spec); app.processEvents()
t = spec["w"]; cols = [c[0] for c in spec["cols"]]
cb = t.cellWidget(0, cols.index("based_on"))
names = [cb.itemText(i) for i in range(cb.count())]
check("Based on is a list: Not set, the standard's styles, Word's own", isinstance(cb, QComboBox) and names[:4] == ["Not set", "Body", "Callout", "Heading 1"]
      and "Normal  (Word)" in names and isinstance(t.cellWidget(0, cols.index("next")), QComboBox), names[:6])
bad = t.cellWidget(1, cols.index("based_on"))
check("a misspelled name kept from before is marked, not lost", bad.currentText() == "Bodyy  (not in this standard)")
bad.setCurrentIndex(bad.findData("Body")); app.processEvents()
check("picking one keeps it, and the other values stay", ps.work["style_defs"]["Callout"].get("based_on") == "Body"
      and ps.work["style_defs"]["Heading 1"].get("size") == 16, ps.work["style_defs"])
check("the preview says what it shows; what changed is folded", "drawn in its own font" in ps.std_preview.caption.text()
      and not ps.std_preview.changes_box.isVisible())
for key in ("hf", "variables", "styledefs"):
    ps.show_section(keys.index(key)); app.processEvents()
    hs = set()
    for _ in range(20):
        app.processEvents(); time.sleep(0.02); hs.add(ps.std_preview.canvas.height())
    check(f"the {key} preview holds still", len(hs) == 1, hs)
ps.show_section(keys.index("hf")); app.processEvents()
cv = ps.std_preview.canvas
check("a page preview fits the visible space", cv.height() <= ps.std_preview.scroll.viewport().height() + 2,
      (cv.height(), ps.std_preview.scroll.viewport().height()))
big = ps.std_preview.enlarge(); app.processEvents()
check("a click shows the preview larger", big.isVisible() and big.canvas.section == "hf" and big.width() >= 800)
big.close()
check("the preview's column is a splitter you drag", isinstance(ps.body_split, QSplitter) and ps.body_split.indexOf(ps.std_preview) == 1)
w.close()
n = sum(checks)
print(f"QT MATRIX VIEWS PASS ({n}/{len(checks)})" if n == len(checks) else f"QT MATRIX VIEWS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
