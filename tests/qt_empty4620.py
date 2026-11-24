"""4.62.0 offscreen (Nicholas 2026-11-23): a page with nothing on it yet is one sentence and one button, with no bar,
Find or filter until there is something to list (Documents, Graphics, Deliverables, Redlining, Matrix, Outline);
Documents' panel on the right is closed and opens from a document's right-click > Details. Fictional (Petrel)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, docclean as DC
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Petrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Petrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Petrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Petrel", path=LIST, customer_dir=CD)
W.Workspace(W.data_dir_for(LIST), "Petrel")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Petrel"); app.processEvents()


def seen(page, T=QPushButton):
    return [b.text() for b in page.findChildren(T) if b.isVisibleTo(w) and b.text()]


# Documents, empty
w.go("library"); app.processEvents()
lp = w.library_page
check("Documents with no document: one button on the page", seen(lp) == ["Add documents..."], seen(lp))
check("... no bar, no Find, no chips, no panel on the right", not lp.bar.isVisibleTo(w) and not lp.search.isVisibleTo(w)
      and not any(b.isVisibleTo(w) for b in lp.side_btns.values()) and not lp.side_area.isVisibleTo(w))
check("... the effort's folder is said under the button, not across the top", lp.empty_folder.isVisibleTo(w) and "Effort folder" in lp.empty_folder.text()
      and not lp.folder_lbl.isVisibleTo(w), lp.empty_folder.text())

# Graphics, Deliverables, Redlining, Matrix, Outline, empty
w.go("graphics"); app.processEvents()
gp = w.graphics_page
check("Graphics with none: one Add graphics..., no Find, no filter", seen(gp) == ["Add graphics..."] and not gp.search.isVisibleTo(w) and not gp.flt.isVisibleTo(w), seen(gp))
w.go("deliverables"); app.processEvents()
dp = w.deliverables_page
check("Deliverables with none: the sentence and + Deliverable..., nothing else", seen(dp) == ["+ Deliverable..."] and dp.none.isVisibleTo(w)
      and not dp.view.isVisibleTo(w) and not dp.detail.isVisibleTo(w), seen(dp))
w.go("redline"); app.processEvents()
rp = w.redline_page
check("Redlining with nothing marked: one line, one button, no tab bar for one tab", seen(rp) == ["Choose a document..."] and w._tab_keys == []
      and not w.page_tabs_box.isVisibleTo(w), (seen(rp), w._tab_keys))
w.go("matrix"); app.processEvents()
mp = w.matrix_page
check("Matrix with nothing shredded: the sentence and Open Shred, which can be pressed", seen(mp) == ["Open Shred"] and mp.none.isVisibleTo(w)
      and not mp.bar.isVisibleTo(w) and mp.isEnabled(), seen(mp))
w.go("outline"); app.processEvents()
op = w.outline_page
check("Outline with nothing shredded: the sentence and Open Shred, no bar", op.none.isVisibleTo(w) and not op.bar.isVisibleTo(w)
      and "Open Shred" in seen(op) and "+ Volume" not in seen(op), seen(op))
next(b for b in op.findChildren(QPushButton) if b.text() == "Open Shred").click(); app.processEvents()
check("... and Open Shred goes to Shred", w.step_btns["assign"].isChecked())

# with a document
P = os.path.join(tmp, "Petrel_SOW.pdf"); shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "SOW.pdf"), P)
w.go("library"); app.processEvents()
lp.add(paths=[P], choices={"Petrel_SOW.pdf": {"choice": "new", "role": "reference", "name": "Statement of Work", "category": "customer", "initial": "S", "type": "SOW"}})
t0 = time.time()
while (lp.worker is not None or not lp.lib.all) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
lp.refresh(); app.processEvents()
check("with a document, the bar, Find and the chips are back", len(lp.lib.all) == 1 and lp.bar.isVisibleTo(w) and lp.search.isVisibleTo(w)
      and lp.table.isVisibleTo(w) and not lp.empty.isVisibleTo(w), len(lp.lib.all))
check("... the effort's folder is over the list again", lp.folder_lbl.isVisibleTo(w) and not lp.empty_folder.isVisibleTo(w))
lp.table.selectRow(0); app.processEvents()
check("the panel on the right stays closed when a document is picked", not lp.side_area.isVisibleTo(w))
m = __import__("skqt.docstatus", fromlist=["x"]).row_menu(lp, run=False)
acts = {a.text(): a for a in m.actions()}
check("the right-click has Details, not ticked", "Details" in acts and acts["Details"].isCheckable() and not acts["Details"].isChecked(), list(acts))
acts["Details"].trigger(); app.processEvents()
check("Details opens the panel, on the document picked", lp.side_area.isVisibleTo(w) and lp.details_open and "Statement of Work" in lp.d_name.text(), lp.d_name.text())
lp.fill(); app.processEvents()
check("... and it stays open while the list is filled again", lp.side_area.isVisibleTo(w))
DC.toggle_details(lp); app.processEvents()
check("Details again closes it", not lp.side_area.isVisibleTo(w))
w.close()
print(f"QT EMPTY 4620 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
