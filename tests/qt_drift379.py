"""3.79.0 the drift report on screen, offscreen (3.82.0: its home is Draft Status, tested in qt_answers382); it lists every dated
copy beside a draft with the changes taken up, still to take or in a passage that changed, the newest copy's changes,
and exports to Excel. Fictional content (the Kestrel technical volume)."""
import datetime, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import wordlab as WL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("applyword"); app.processEvents()
pg = w.applyword_page if hasattr(w, "applyword_page") else w.pages["applyword"]
check("3.82.0: Drift report... has one home, Draft Status (not Apply in Word)", not any(b.text() == "Drift report..." for b in pg.findChildren(QPushButton)))
draft = os.path.join(tmp, "Kestrel Volume II.docx")
shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), draft)
paras = WL.docx_paragraphs(draft)
s = paras[6].index("w/o")
WL.to_copy(draft, [{"para": 6, "start": s, "end": s + 3, "hit": "w/o", "fix": "without", "on": True, "rule": "plain words", "why": ""}],
           when=datetime.datetime(2026, 11, 6, 21, 30))
from skqt import driftview as DVW
dlg = DVW.show(pg, draft, run=False)
check("the report lists the copy with its change still to take", dlg.table.rowCount() == 1 and dlg.table.item(0, 3).text() == "1"
      and dlg.changes.rowCount() == 1 and dlg.changes.item(0, 3).text() == "Still to take")
out = dlg.export(os.path.join(tmp, "drift.xlsx"))
check("... and exports to Excel", out and os.path.isfile(out))
empty = os.path.join(tmp, "Other.docx"); shutil.copy2(draft, empty)
dlg2 = DVW.show(pg, empty, run=False)
check("a draft with no copies says how to make one", dlg2.table.rowCount() == 0)
w.close()
n = sum(checks)
print(f"QT DRIFT 379 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
