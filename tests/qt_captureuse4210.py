"""4.21.0 offscreen: the pane says where a piece goes. (Scaffold of qt_struct4190.) 4.19.0: Shred's views are Page and List; List shows the shred under the customer's headings and opens a piece
on its page. A piece typed Structure (key O) feeds Start our structure: the card shows while the outline is empty and
recommends Door 1; the preview reads the headings, takes edits and puts them in with Required by; Check against the
required structure finds a rename. Door 2 drafts headings; Use it as our structure takes Draft off. Fictional (Kestrel)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, effort as E, shredtypes as ST, structfrom as SF, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import structdoors as SDR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
W.Workspace(W.data_dir_for(LIST), "Kestrel")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
src = os.path.join(tmp, "Section L.pdf"); shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "docs4170", "C01v1.pdf"), src)
lib = DV.Library(w.ws.p("documents")).load()
DI.apply(lib, DI.plan(lib, [src]), customer_dir=CD)
w.read_page.read([os.path.join(CD, "Section L.pdf")], os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while (w.review is None or w.read_page.running()) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
by = lambda s: next(x for x in M.items if s in (x.get("text") or ""))          # noqa: E731
w.go("assign"); app.processEvents()
pg = w.assign_page
pg.load_files_keep(); pg.open_file("Section L.pdf"); app.processEvents()
vol = by("Volume I holds the technical approach")
pg.select(vol["id"]); app.processEvents()
check("a piece with no type: no Goes to line", getattr(pg, "goes_label", None) is None)
from skqt import shredbar as SB
SB.toggle_piece(pg, "structure"); app.processEvents()
check("typed Structure: Goes to Matrix & Outline > Outline", pg.goes_label is not None and pg.goes_label.text().startswith("Goes to: Matrix & Outline > Outline"),
      pg.goes_label.text() if pg.goes_label else None)
late = by("shall not exceed 25 pages")
pg.select(late["id"]); app.processEvents()
SB.toggle_piece(pg, "rule"); app.processEvents()
check("typed Rule: Rules & Dates, and what makes a rule check other pages", pg.goes_label is not None and "Shred > Rules & Dates" in pg.goes_label.text()
      and "reader found on its own" in pg.goes_label.text(), pg.goes_label.text() if pg.goes_label else None)
SB.toggle_piece(pg, "requirement"); app.processEvents()
check("two types: each named", pg.goes_label.text().startswith("Goes to: Requirement: ") and "; Rule: " in pg.goes_label.text(), pg.goes_label.text())
w.go("requirements"); app.processEvents()
rp = w.stack.currentWidget()
found = []
def walk(it):
    for i in range(it.childCount()):
        c = it.child(i)
        if c.text(4):
            found.append(c.text(4))
        walk(c)
t = rp.tree
for i in range(t.topLevelItemCount()):
    walk(t.topLevelItem(i))
check("Rules & Dates: a piece typed Rule says Listed here, not a use it does not have", "Listed here" in found, found)
k = sum(checks)
print(f"QT CAPTUREUSE 4210 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
w.close(); app.quit()
sys.exit(0 if k == len(checks) else 1)
