"""4.55.1 (D13, D14): the Acronym Finder keeps its decisions when its list file could not be saved, offscreen.

Reported 2026-11-17: a term added by hand was not under Added to effort list after the Finder was closed and opened
again, and finds already decided came back undecided at every reopen. Reproduced on Windows with the list file held
open by another program (as Excel, a sync tool or a virus scanner can): the decisions were kept in the list's recovery
copy, but opening again read the workbook alone. Here the holder is stood in for by a save that is refused.
Also D18: "NOT SAVED yet" is said only when a save was refused. Fictional content (the Kestrel set)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import office_pdf as OP
OP.available = lambda: False
import effort as E
import workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import acrextras as AX
from skqt import acrtool as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


# ---- the recovery copy's time: a copy made in the same second as the last good save is not thrown away
d0 = os.path.join(tmp, "same_second"); os.makedirs(d0)
ws0 = W.Workspace(d0, "x"); wb0 = os.path.join(d0, "list.xlsx")
open(wb0, "w").close()
ws0.write_recovery("effort", wb0, {"rows": {}})
check("a recovery copy written just after a save is read back", ws0.read_recovery("effort", wb0) is not None)

# ---- a refused save stands in for the list file held open by another program
HELD = {"on": False}
_save = E.EffortList.save


def save(self, *a, **k):
    if HELD["on"]:
        raise E.ListLocked(self.path)
    return _save(self, *a, **k)


E.EffortList.save = save
said = []
T.ToolHost.status = lambda self, text: said.append(str(text))

cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.show()


def pump(sec):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents(); time.sleep(0.01)


def undecided(s):
    return sorted(t for t, x in s.results.items() if not x.get("effort") and not x.get("excluded") and not x.get("plural_of")
                  and not x.get("form_of") and not x.get("part_of") and not x.get("known") and not x.get("file_error"))


def marks(s, terms):
    return {t: (s.results.get(t) or {}).get("effort") for t in terms}


tw = w.open_tool("acronyms"); pump(0.3); p = tw.page
p.scan([os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")])
while p.worker is not None and p.worker.isRunning():
    app.processEvents()
pump(2.0)
u = undecided(p.session)
check("the scan leaves finds to decide", len(u) >= 8, len(u))

# ---- D18: an add while nothing holds the file says nothing about Excel
del said[:]
p.add([u[0]], ""); pump(2.0)
check("an add that saves says nothing of NOT SAVED (D18)", said and not any("NOT SAVED" in x for x in said), said)
check("the list file is written", os.path.isfile(tw.host.effort_path))

# ---- the file is held: decide, add a term by hand, close
HELD["on"] = True
del said[:]
p.add(u[1:4], ""); p.set_status(u[4:6], "Not a term")
AX.add_term(p, "QZK", "Acronym", "Quartz Zinc Kiln", "", ["results", "list"])
pump(2.5)
check("the line says the list file could not be saved yet", "open in another program" in p.progress.text(), p.progress.text())
del said[:]
p.add([u[7]], "")
check("once a save was refused, the next add says NOT SAVED", any("NOT SAVED" in x for x in said), said)
pump(2.5)
watch = u[:6] + [u[7], "QZK"]
want = marks(p.session, watch)
check("decided before the close", want["QZK"] == "In the list" and all(want[t] for t in watch), want)
tw.close(); pump(0.5)
rows = E.EffortList(tw.host.effort_path, "x").load().rows
check("the held list file did not take them (the fault's condition)", "QZK" not in rows and u[1] not in rows, sorted(rows))

# ---- the holder lets go; open again: everything is still there (failed before 4.55.1)
HELD["on"] = False
del said[:]
tw = w.open_tool("acronyms"); pump(0.6); p = tw.page
got = marks(p.session, watch)
check("every decision is kept after a reopen (D14)", got == want, {t: (want[t], got[t]) for t in watch if want[t] != got[t]})
check("the term added by hand is under Added to effort list (D13)", got["QZK"] == "In the list"
      and "QZK" in (p.session.manual_items or {}), got["QZK"])
check("he is told the decisions were brought back", any("brought back" in x for x in said), said)
rows = E.EffortList(tw.host.effort_path, "x").load().rows
check("the list file now holds them", "QZK" in rows and all(t in rows for t in u[:6] + [u[7]]), sorted(rows))
check("the recovery copy is cleared once written", p.session.ws.read_recovery("effort", tw.host.effort_path) is None)

# ---- held at the reopen too: still shown, written later
HELD["on"] = True
p.add([u[6]], ""); pump(2.5)
tw.close(); pump(0.5)
tw = w.open_tool("acronyms"); pump(0.6); p = tw.page
check("held at the reopen too: the decision is shown", marks(p.session, [u[6]])[u[6]] == "In the list")
check("and waits to be written", p.session.list_failed and p.session.list_unsaved)
HELD["on"] = False
tw.close(); pump(0.5)
rows = E.EffortList(tw.host.effort_path, "x").load().rows
check("written at the next close once the file is free", u[6] in rows, sorted(rows))

E.EffortList.save = _save
ok = all(checks)
print("ALL PASS" if ok else f"{checks.count(False)} FAILED")
sys.exit(0 if ok else 1)
