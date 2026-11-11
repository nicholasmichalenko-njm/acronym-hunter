"""3.34.1 a new effort and switching efforts, offscreen: Start an effort with only its name opens it with no error, it
is in the effort box and the All Efforts list at once; every page then shows nothing of the effort open before (Review's
page and queue, Structure Builder, Matrix, L/M Crosswalk); the effort box switches back and forth with no error."""
import os, sys, tempfile, time, traceback
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
A.DATA_DIR = os.path.join(tmp, "data")
import effort as E, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import skqt.mainwin as MW
from skqt.mainwin import MainWindow
from skqt.starteffort import StartDialog

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


errors = []
sys.excepthook = lambda t, v, tb: errors.append("".join(traceback.format_exception(t, v, tb))[-600:])
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


PAGES = list(dict.fromkeys([k for _g, xs in MW.RAIL for k, _t in xs] + [k for xs in MW.TABS.values() for k, _t in xs]))


def visit():
    bad = []
    for p in PAGES:
        try:
            w.go(p); app.processEvents()
        except Exception:  # noqa: BLE001
            bad.append(p)
    return bad


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("Kestrel has its matrix", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
n0 = len(w.review.M.items)
check("every page opens on Kestrel", not visit() and not errors, errors[-1:] if errors else "")
w.go("assign"); app.processEvents()
check("Review shows Kestrel's page", len(w.assign_page.view.boxes) > 10 and w.matrix_page.model.rowCount() >= 0)
w.go("efforts"); app.processEvents()
dlg = StartDialog(w); dlg.form.name.setText("Osprey"); app.processEvents()
try:
    made = dlg.form.create(); app.processEvents()
except Exception:  # noqa: BLE001
    made = None; errors.append(traceback.format_exc()[-600:])
check("Start an effort with only its name: no error, and it opens", made == "Osprey" and w.effort_name == "Osprey"
      and not dlg.form.err.text() and not errors, errors[-1:] if errors else dlg.form.err.text())
check("the new effort is in the effort box, chosen", "Osprey" in [w.effort_box.itemText(i) for i in range(w.effort_box.count())]
      and w.effort_box.currentText() == "Osprey")
w.go("efforts"); app.processEvents()
check("and in All Efforts", "Osprey" in w.efforts_page.cards)
check("every page opens on the new effort", not visit() and not errors, errors[-1:] if errors else "")
ap = w.assign_page
check("Review shows nothing of Kestrel: no page, no files, no queue", w.review is None and not ap.view.boxes and ap.files.count() == 0
      and not ap.queue_lbl.text() and not ap.file)
check("Structure Builder, Matrix and L/M Crosswalk show nothing of Kestrel", w.structure_page.btree.topLevelItemCount() == 0
      and w.matrix_page.model.rowCount() == 0 and w.crosswalk_page.table.rowCount() == 0)


def pick(name):
    i = [w.effort_box.itemText(k) for k in range(w.effort_box.count())].index(name)
    w.effort_box.setCurrentIndex(i); w.effort_box.activated.emit(i); app.processEvents()


pick("Kestrel")
check("the effort box switches back to Kestrel, all of it", w.effort_name == "Kestrel" and w.review is not None
      and len(w.review.M.items) == n0 and not errors, errors[-1:] if errors else "")
pick("Osprey")
check("and to the new effort again, with no error and nothing of Kestrel", w.effort_name == "Osprey" and w.review is None
      and not ap.view.boxes and not errors, errors[-1:] if errors else "")
w.close()
n = sum(checks)
print(f"QT EFFORT SWITCH PASS ({n}/{len(checks)})" if n == len(checks) else f"QT EFFORT SWITCH FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
