"""4.16.0 offscreen: the PDF's comments on the Redline page. Make the Word copy of an Acrobat-commented PDF says how many
comments came in, as what, and how many were placed by position; More has Make it without the PDF's comments; Check
lists every comment under the differences (none) with what it became and its page; Exceptions reads the copy's tracked
changes and comments as rows. Fictional content (Kestrel)."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
src = os.path.join(A.BASE_DIR, "test_samples", "comments", "C01_prose_commented.pdf")
P = os.path.join(CD, "Kestrel_Section_L_reviewed.pdf"); shutil.copy2(src, P)
lib0 = DV.Library(ws.p("documents")).load()
lib0.add(P, DI.read(P), doc_name="Section L reviewed", role="matrix", initial="L", dtype="Section L")
for _d in lib0.all:                                   # 4.25.3: Prepare for Redline lists what is marked Return it, redlined
    lib0.set_returns(_d["id"], ["redline"])
app = QApplication([]); theme.apply(app)
toasts = []
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
w.toast = lambda msg, *a, **k: toasts.append(msg)
w.go("redline"); app.processEvents()
pp = w.redline_page
pp.refresh(); app.processEvents()
check("4.22.0: no More menu; the bar has one command, for a Word file you already have", not pp.bar.more_menu.actions()
      and pp.bar.labels() == ["Put its comments into my Word file..."], pp.bar.labels())
copy = pp.make(); app.processEvents()
said = toasts[-1] if toasts else ""
check("Prepare says what the PDF's comments became", copy and "comment(s) from the PDF" in said
      and "tracked change(s)" in said and "Word comment(s)" in said and "placed by position" in said, said)
w.go("rcheck"); cp = w.rcheck_page; cp.refresh(); app.processEvents()
res = cp.check_copy(copy)
rows = [cp.table.item(r, 0).text() for r in range(cp.table.rowCount())]
check("Check: no difference, and every comment listed", res and not res["differences"] and len(rows) == len(res["comments"])
      and all(t.startswith("PDF ") for t in rows) and "comment(s) from the PDF" in cp.say.text(), (rows[:3], cp.say.text()))
check("... each with what it became and its page", any("replacement: three" in cp.table.item(r, 2).text() for r in range(cp.table.rowCount()))
      and all(cp.table.item(r, 3).text() for r in range(cp.table.rowCount())))
check("... one placed by position says so", any(t.endswith("by position") for t in rows), rows)
w.go("exceptions"); ex = w.exceptions_page if hasattr(w, "exceptions_page") else None
if ex is None:
    from skqt.redlinepage import ExceptionsPage
    ex = ExceptionsPage(w)
got = ex.read(copy)
kinds = {r["Kind"] for r in got}
check("Exceptions: the copy's tracked changes and comments are rows", {"Replaced", "Deleted", "Inserted", "Comment"} <= kinds
      and "comment(s)" in ex.say.text(), (kinds, ex.say.text()))
plain = pp.make(comments=False); app.processEvents()
check("Prepare it without the comments: a clean copy", plain and "comment(s) from the PDF" not in toasts[-1], toasts[-1])
k = sum(checks)
print(f"QT REDLINE 4160 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
w.close(); app.quit()
sys.exit(0 if k == len(checks) else 1)
