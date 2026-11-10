"""4.1.0 offscreen: picking a document in Shred extracts it (claude/stationkeeper-shred-plan-4.1.md, step 3). Shred has
no Extract tab; its document list names every customer document that builds the matrix, the ones not extracted yet
marked so; picking one extracts it at once in the background, with no question, showing its progress on Shred, and
opens it when done; a second one adds to the matrix; Documents' Shred it does the same; context documents still read
beside the structure. Fictional (the rfp_walk set)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import docintake as DI
import docversions as DV
import effort as E
import workspace as W
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
asked = []
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.Yes)
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: asked.append(a) or ("", ""))
from skqt import design as D
from skqt import shredpick as SP
from skqt.mainwin import MainWindow, TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
B = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk")
lib0 = DV.Library(ws.p("documents")).load()
pL = os.path.join(B, "Section_L_print.pdf")
dL, _v = lib0.add(pL, DI.read(pL), doc_name="Section L", role="matrix", initial="L", dtype="Section L")
pM = os.path.join(B, "SOW.pdf")
dM, _v = lib0.add(pM, DI.read(pM), doc_name="Second document", role="matrix", initial="M", dtype="Section M")
pS = os.path.join(B, "Section_L.docx")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=90):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("Shred's tabs: no Extract", "read" not in [k for k, _t in TABS["assign"]] and TABS["assign"][0][0] == "assign", TABS["assign"])
w.open_effort("Kestrel"); app.processEvents()
pg = w.assign_page
check("an effort with nothing extracted opens on Shred", w.stack.currentWidget() is pg)
w.go("read"); app.processEvents()
check("go('read') lands on Shred", w.stack.currentWidget() is pg)
items = [pg.files.itemText(i) for i in range(pg.files.count()) if pg.files.itemText(i)]
check("the document list names the customer documents not extracted yet", items == ["Section L" + SP.TAIL, "Second document" + SP.TAIL], items)
check("... nothing is picked until you pick; the page says how", pg.files.currentIndex() == -1 and "Pick a customer document" in pg.note.text(),
      (pg.files.currentIndex(), pg.note.text()))
pg.files.setCurrentText("Section L" + SP.TAIL); app.processEvents()
check("picking it extracts it at once, with no question", w.read_page.running() and not asked, asked)
check("... its progress and Stop show on Shred", w.read_page.panel.parent() is not None and w.read_page.panel.isVisibleTo(pg)
      and "Extracting Section L" in pg.note.text(), pg.note.text())
check("... and it opens in Shred when done", wait(lambda: w.review is not None and pg.file == "Section_L_print.pdf"), pg.file)
check("... the matrix lives where Settings > Folders and file names puts it", os.path.isfile(w.review.M.path), w.review.M.path)
items = [pg.files.itemText(i) for i in range(pg.files.count()) if pg.files.itemText(i)]
check("... the list now holds it, and the other still to extract", "Section_L_print.pdf" in items and "Second document" + SP.TAIL in items, items)
check("the Shred button is Mark shredded", pg.done_btn.text() == "Mark shredded", pg.done_btn.text())
pg.mark_reviewed(); app.processEvents()
check("... marked: Shredded", pg.done_btn.text().startswith("Shredded"), pg.done_btn.text())
n0 = len(w.review.M.items)
pg.files.setCurrentText("Second document" + SP.TAIL); app.processEvents()
check("picking a second one adds it to the matrix, every decision kept",
      wait(lambda: not w.read_page.running() and pg.file == os.path.basename(pM)) and len(w.review.M.items) > n0, pg.file)
check("... nothing left to extract", not SP.pending(w))
w.rail_go("library"); app.processEvents()
lp0 = w.library_page
lp0.refresh(); lp0.select(dL["id"]); lp0.show_doc(); app.processEvents()
rows = {r[0]: r[1] for r in lp0.status_now}
check("Documents' panel counts its pieces and how many are not sorted (4.1.0)", rows.get("Pieces", "").endswith("not sorted")
      or rows.get("Pieces", "").endswith("all sorted"), rows)
# Documents' Shred it, on a document added later
lib = DV.Library(ws.p("documents")).load()
pX = os.path.join(tmp, "Section_C.docx")
import shutil; shutil.copy(pS, pX)
dX, _v = lib.add(pX, DI.read(pX), doc_name="Section C", role="matrix", initial="C", dtype="SOW")
w.rail_go("library"); app.processEvents()
lp = w.library_page
lp.refresh(); lp.select(dX["id"]); lp.show_doc(); app.processEvents()
check("Documents: its next thing is Shred it", lp.b_read.text() == "Shred it", lp.b_read.text())
lp.review_selected(); app.processEvents()
check("... which extracts it now and opens Shred", w.stack.currentWidget() is pg and (w.read_page.running() or w.review is not None))
check("... and opens it there when done", wait(lambda: not w.read_page.running() and pg.file == "Section_C.docx"), pg.file)
check("still no question asked", not asked, asked)
w.close()
print(f"QT EXTRACT 410 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
