"""2.78.0 never lose work, in the Qt window, offscreen: every change writes a recovery copy of the matrix; a save clears
it and keeps a dated copy; if Stationkeeper stops before a save, the next opening offers the changes back and puts
them back; automatic backups go to the backup folder a few minutes after changes (latest package, today's copy, the
settings zip) and when the effort closes, and only when something changed; the effort list gets dated copies when it
changes; the effort reopens where you were (page, sentence, structure target); restore points list the copies and put
one back, keeping the current state first; the crash screen saves first; with backups off, Settings says so."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.LOG_DIR = os.path.join(tmp, "logs")
import compliance as C, effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import safety as S
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Heron"); os.makedirs(os.path.join(EDIR, "Customer documents"))
LIST = os.path.join(EDIR, "Heron_Effort_List.xlsx")
L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=os.path.join(EDIR, "Customer documents"))
M = C.Matrix(os.path.join(EDIR, "Heron_Compliance_Matrix.xlsx"), "Heron")
M.items = C.extract([("Section L.docx", [("Page 1", "L.4 Technical. The Offeror shall describe the thermal design. "
                                                    "The Offeror shall provide the schedule. The Offeror shall list the risks.")])])
M.outline = C.parse_outline("1.1 Technical Approach\n1.2 Schedule")
M.save()
W.Workspace(W.data_dir_for(LIST), "Heron").set("compliance_path", M.path)
BK = os.path.join(tmp, "SharePoint backups")
app = QApplication([]); D.apply(app)


def window():
    w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
    w.safety.test_dir = BK
    w.safety.recovery_answer = "restore"
    return w


w = window()
check("backups off: Settings says so and why", (lambda t: "Backups are off" in t)((w.safety.test_dir, setattr(w.safety, "test_dir", ""), w.safety.status_text())[-1]))
w.safety.test_dir = BK
w.open_effort("Heron")
R = w.review
a, b, c = R.M.items[0], R.M.items[1], R.M.items[2]
S.BACKUP_AFTER_S = 0
check("opening notes the state on disk: nothing to back up yet", w.safety.tick() is False and w.safety.tick() is False and not os.path.isdir(BK))
# a change: the recovery copy
R.req([a], "1.1 Technical Approach"); w.changed()
time.sleep(0.5); app.processEvents()
rp = os.path.join(w.ws.root, "recovery")
check("every change writes a recovery copy of the matrix", os.path.isdir(rp) and any(f.startswith("matrix_") for f in os.listdir(rp)))
w.save_now()
check("a save clears the recovery copy and keeps a dated copy", not any(f.startswith("matrix_") for f in os.listdir(rp))
      and len(w.ws.backups("matrix")) == 1)
# automatic backup a few minutes (here: 0) after the change
w.safety.tick(); w.safety.tick()
if w.safety.thread:
    w.safety.thread.join()
w.safety.tick()
root = os.path.join(BK, "Heron")
pk = sorted(os.listdir(root)) if os.path.isdir(root) else []
check("automatic backup: the latest package, today's copy and the settings zip", "Heron - latest.skpkg" in pk
      and f"Heron {datetime.date.today():%Y-%m-%d}.skpkg" in pk and any(f.startswith("Stationkeeper settings") for f in os.listdir(BK)), pk)
check("the last backup time is kept and shown", w.safety.last_backup() is not None and "the last one was Today" in w.safety.status_text(),
      w.safety.status_text())
m1 = os.path.getmtime(os.path.join(root, "Heron - latest.skpkg"))
check("no change, no new backup", w.safety.tick() is False and w.safety.backup_now() is False)
# where you were
w.go("assign"); w.assign_page.set_target("1.2 Schedule"); w.assign_page.select(b["id"]); app.processEvents()
# the effort list changes: a dated copy
L2 = E.EffortList(LIST).load(); L2.client = "USSF SSC"; L2.pending = True; time.sleep(1.1); L2.save()
w.safety.tick()
check("the effort list changed: a dated copy in the effort's folder", len(w.ws.backups("effort")) == 1)
# a change, then close: backed up on close, and the view kept
R.req([b], "1.2 Schedule"); w.changed(); time.sleep(1.1)
w.close_effort()
check("closing backs up what changed", os.path.getmtime(os.path.join(root, "Heron - latest.skpkg")) > m1)
w.open_effort("Heron")
check("reopens where you were: the page, the sentence, the target", w.stack.currentWidget() is w.assign_page
      and w.assign_page.cur == b["id"] and w.assign_page.target == "1.2 Schedule", (w.assign_page.cur, w.assign_page.target))
# Stationkeeper stops before a save: the next opening puts the changes back
R = w.review
c = next(x for x in R.M.items if x["id"] == c["id"])
R.req([c], "1.1 Technical Approach"); w.changed(); time.sleep(0.5); app.processEvents()
w.save_timer.stop()
time.sleep(1.1)
w.safety.snapshot()
w.ws.release_lock(); w.ws = None; w.review = None              # as if the program ended here
w.close()
w2 = window()
w2.open_effort("Heron")
cc = w2.review.item(c["id"])
check("the next opening puts the unsaved change back and saves it", cc.get("decision") == "Keep" and not w2.review.M.pending
      and "put back" in w2.statusBar().currentMessage(), (cc.get("decision"), w2.statusBar().currentMessage()))
# restore points
pts = w2.safety.points()
kinds = {p["kind"] for p in pts}
check("restore points: dated matrix and list copies and the backup packages, newest first", {"matrix", "effort", "package"} <= kinds
      and all(pts[i]["when"] >= pts[i + 1]["when"] for i in range(len(pts) - 1)), kinds)
before = len(w2.ws.backups("matrix"))
oldest = [p for p in pts if p["kind"] == "matrix"][-1]
got = w2.record_page.restore_dialog(pick=pts.index(oldest))
mm = C.Matrix(M.path).load()
check("put back the first matrix copy: the later decisions are gone, the current state kept as a copy first", got
      and mm.items[2].get("decision") != "Keep" and mm.items[1].get("decision") != "Keep" and len(w2.ws.backups("matrix")) >= before, len(w2.ws.backups("matrix")))
check("and the effort is open again", w2.ws is not None and w2.effort_name == "Heron")
# the crash screen saves first
R = w2.review
R.req([R.M.items[1]], "1.2 Schedule"); w2.changed()
w2.safety.crash_answer = "keep"
hook = w2.safety.install_crash_screen()
try:
    raise RuntimeError("test: something went wrong")
except RuntimeError:
    hook(*sys.exc_info())
check("the crash screen: the work is saved first, then you keep working", not w2.review.M.pending
      and C.Matrix(M.path).load().items[1].get("decision") == "Keep")
src = open(os.path.join(A.BASE_DIR, "skqt_main.py"), encoding="utf-8").read()
check("the program installs the crash screen", "install_crash_screen()" in src)
w2.close()
n = sum(checks)
print(f"QT SAFETY PASS ({n}/{len(checks)})" if n == len(checks) else f"QT SAFETY FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
