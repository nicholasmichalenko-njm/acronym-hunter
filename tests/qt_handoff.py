"""2.82.0 no blank pause after an update, offscreen: the old version shows 'Updated to X. Starting the new version'
from the moment the files are swapped until the new version's window is up (it says so through _update\\started.json),
and tells the person what to do if the new one is slow; the new version reopens the last effort under a cover that says
what is happening step by step (checking the files, loading the matrix, setting up the pages, back where you were) and
that nothing is lost, then says the effort is open as it was left; questions and what's new wait until the work is
back on screen."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import compliance as C, effort as E, workspace as W, updatepack as U
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, updates as UPD
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); os.makedirs(ED)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
M = C.Matrix(os.path.join(ED, "Heron_Compliance_Matrix.xlsx"), "Heron")
M.items = C.extract([("Section L.docx", [("Page 1", "The Offeror shall describe the thermal design. The Offeror shall provide the schedule.")])])
M.save(); W.Workspace(W.data_dir_for(LIST), "Heron").set("compliance_path", M.path)
app = QApplication([]); D.apply(app)
# the old version's hand-over
folder = os.path.join(tmp, "prog"); os.makedirs(folder)
U.clear_handoff(folder)
h = UPD.Handoff(folder, "2.82.0", "update")
h.show(); app.processEvents()
check("the old version: 'Updated to 2.82.0. Starting the new version' and that the work reopens",
      "Updated to 2.82.0" in h.title.text() and "reopens where you left off" in h.detail.text() and h.bar.maximum() == 0)
h.poll()
check("it waits while the new version starts", h.state == "waiting" and h.isVisible())
check("the new version says its window is up", U.signal_started(folder, "2.82.0") and U.started_seen(folder))
h.poll()
check("and the old one closes", h.state == "started" and not h.isVisible())
U.clear_handoff(folder)
h2 = UPD.Handoff(folder, "2.81.0", "undo"); h2.show(); h2.t0 -= UPD.HANDOFF_WAIT_S + 1; h2.poll()
check("a slow start says what to do, never hangs", h2.state == "slow" and "taking longer" in h2.title.text()
      and "start Stationkeeper.exe" in h2.detail.text() and not h2.ok.isHidden() and "Back to 2.81.0" not in h2.title.text())
h2.close()
src = open(os.path.join(A.BASE_DIR, "skqt", "updates.py"), encoding="utf-8").read()
check("installing and undoing show it until the new window is up", "Handoff(folder, to, kind)" in src and '"--after-update"' in src
      and "U.clear_handoff(folder)" in src)
# the new version reopens the work under a cover
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
seen = []
from skqt import progress as PG
real_step = PG.Overlay.step
PG.Overlay.step = lambda self, f, t="": (seen.append((round(f, 2), t, self.isVisible(), self.title.text())), real_step(self, f, t))
ok = w.open_with_progress("Heron", f"Stationkeeper {A.APP_VERSION} is ready. Reopening your work")
PG.Overlay.step = real_step
texts = [t for _f, t, _v, _ti in seen]
check("the cover is up while it opens, with its title", seen and all(v for _f, _t, v, _ti in seen)
      and seen[0][3].startswith(f"Stationkeeper {A.APP_VERSION} is ready"), seen[:1])
check("step by step: the files, the matrix, the pages, where you were", any("checking" in t for t in texts) and any("matrix" in t for t in texts)
      and any("pages" in t for t in texts) and any("where you were" in t for t in texts), texts)
check("the bar only moves forward", [f for f, *_ in seen] == sorted(f for f, *_ in seen))
check("it says nothing is lost", "Nothing is lost" in w.overlay.safe.text())
check("then the cover goes and the effort is open as left", ok and not w.overlay.isVisible() and w.effort_name == "Heron"
      and w.review is not None and "as you left it" in w.statusBar().currentMessage(), w.statusBar().currentMessage())
check("the effort opened is remembered, so the next start (after an update too) reopens it",
      E.Registry(os.path.join(cfg, "efforts.json")).current == "Heron")
w.resize(1000, 700); w.overlay.begin("x"); app.processEvents()
check("the cover fills the window when it changes size", w.overlay.geometry() == w.rect()); w.overlay.finish()
msrc = open(os.path.join(A.BASE_DIR, "skqt_main.py"), encoding="utf-8").read()
check("start: the new version signals, then reopens under the cover; questions wait", "signal_started(" in msrc
      and "w.open_with_progress(cur, title)" in msrc and "def then():" in msrc and msrc.index("signal_started(") < msrc.index("open_with_progress"))
tsrc = open(os.path.join(A.BASE_DIR, "skqt_training.py"), encoding="utf-8").read()
check("Training signals too", "signal_started(" in tsrc)
check("a start reopens the effort last open, or the only one (Unfiled aside)", "w.efforts.current or len(_real(w)) == 1" in msrc and "def _real(w)" in msrc)
w.close()
n = sum(checks)
print(f"QT HANDOFF PASS ({n}/{len(checks)})" if n == len(checks) else f"QT HANDOFF FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
