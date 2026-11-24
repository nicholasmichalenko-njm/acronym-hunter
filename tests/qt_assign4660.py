"""4.66.0 offscreen: Matrix opens on Assign. The pieces kept in Shred beside the outline; Assign to section, Also in
this section, Take out, Take the suggestions; Place on the customer's page under More. Fictional (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import assignlinks as AL, effort as E, workspace as W, setupdoc as SD
from PySide6.QtCore import QItemSelectionModel
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
check("Matrix's tabs: Assign first; Place is off the tabs", [k for k, _t in MW.TABS["matrix"]] == ["assignto", "linkcheck", "matrix"])
w.read_page.read(PDFS, os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
pg = w.assignto_page
w.step_btns["matrix"].click(); app.processEvents()
check("the Matrix entry opens Assign", w.stack.currentWidget() is pg and w.step_btns["matrix"].isChecked() and w.page_tabs.tabText(0) == "Assign"
      and w.page_title.text() == "Matrix", w._tab_keys)
check("with nothing kept in Shred: one sentence and Open Shred, no bar", pg.none.isVisibleTo(w) and not pg.bar.isVisibleTo(w) and not pg.body.isVisibleTo(w)
      and [b.text() for b in pg.findChildren(QPushButton) if b.isVisibleTo(w)] == ["Open Shred"])
kept = [it for it in M.items if it.get("suggest") != "Drop"][:10]
for it in kept:
    it["decision"] = "Keep"
labs = SD.labels(M)
w.go("assignto"); app.processEvents()
check("the kept pieces are listed, none assigned", pg.body.isVisibleTo(w) and pg.table.rowCount() == 10 and pg.said.text() == "10 of 10 not assigned.", pg.said.text())
check("the outline beside them, a row a section", [pg.tree.topLevelItem(i).data(0, 0x0100) for i in range(pg.tree.topLevelItemCount())] == labs)
check("the bar: one main button and three more; nothing can be assigned until pieces and a section are picked",
      pg.bar.main is pg.b_assign and len(pg.bar.commands) == 4 and not pg.b_assign.isEnabled() and not pg.b_out.isEnabled())
pg.table.selectRow(0); pg.table.selectionModel().select(pg.table.model().index(1, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
pg.tree.setCurrentItem(pg.tree.topLevelItem(1)); app.processEvents()
ids = pg.picked()
check("two pieces and a section picked: Assign to section is ready", len(ids) == 2 and pg.section() == labs[1] and pg.b_assign.isEnabled())
n = pg.assign()
check("Assign to section links them; they leave Not assigned; the section counts two", n == 2 and all(SD.by_id(M)[i]["map"] == labs[1] for i in ids)
      and pg.table.rowCount() == 8 and pg.tree.topLevelItem(1).text(1) == "2" and pg.said.text() == "8 of 10 not assigned." and M.pending, pg.said.text())
check("... and the section stays picked", pg.section() == labs[1])
pg.show_box.setCurrentIndex(2); app.processEvents()
check("In the section picked shows the two", pg.table.rowCount() == 2 and {d["id"] for d in pg.data} == set(ids))
pg.tree.setCurrentItem(pg.tree.topLevelItem(2)); app.processEvents()
check("... and follows the section picked", pg.table.rowCount() == 0)
pg.show_box.setCurrentIndex(1); app.processEvents()
row = next(i for i, d in enumerate(pg.data) if d["id"] == ids[0])
pg.table.selectRow(row); app.processEvents()
check("Also in this section adds a second section", pg.also() == 1 and SD.item_sections(M, SD.by_id(M)[ids[0]]) == [labs[1], labs[2]]
      and pg.data[row]["sections"] == [labs[1], labs[2]], pg.data[row]["sections"])
pg.table.selectRow(row); app.processEvents()
check("Take out (with All showing) takes it out of every section", pg.take_out() == 2 and SD.item_sections(M, SD.by_id(M)[ids[0]]) == [])
pg.show_box.setCurrentIndex(0); app.processEvents()
word = max(pg.data[-1]["text"].split(), key=len).lower().strip(".,;:()")
before = pg.table.rowCount()
pg.find.setText(word); app.processEvents()
check("Find narrows the list", 0 < pg.table.rowCount() <= before and all(word in d["text"].lower() for d in pg.data), (word, pg.table.rowCount()))
pg.find.setText(""); app.processEvents()
want = sum(1 for d in pg.data if d["suggested"])
got = pg.take_suggestions()
check("Take the suggestions places every piece that has one", got == want and (want == 0 or "placed in the section suggested" in w.statusBar().currentMessage()), (got, want))
check("More has Place on the customer's page", pg.bar.action("Place on the customer's page...") is not None)
pg.bar.action("Place on the customer's page...").trigger(); app.processEvents()
check("... which opens the customer's page with the outline, under Matrix", w.stack.currentWidget() is w.assign_page and w.assign_page.place_mode
      and w.step_btns["matrix"].isChecked())
w.close()
print(f"QT ASSIGN 4660 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
