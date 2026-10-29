"""2.82.0 Read shows its progress and runs once, offscreen: pressing Read shows a panel with a bar, the file and the
page within it, a running clock and Stop, and a bar in the window's status bar; Read, Add files and the ticks are locked
while it runs and a second Read does nothing (one matrix, one read); a page left alone for a minute says it is still
working; it ends green with what it read; a file that cannot be read stops the read in red, names the file, writes no
matrix, and Read works again; Stop ends it amber with nothing written; an error while building the matrix is shown, not
silent; switching effort or closing the window during a read asks first and throws the read away."""
import os, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import compliance as C, compliance_read as CR, docversions as DV, effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, progress as PG
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
reg = E.Registry(os.path.join(cfg, "efforts.json"))
files = {}
for ef in ("Heron", "Osprey"):
    ED = os.path.join(tmp, ef); os.makedirs(ED)
    LIST = os.path.join(ED, f"{ef}_Effort_List.xlsx"); L = E.EffortList(LIST, ef); L.pending = True; L.save()
    reg.put(ef, path=LIST)
    files[ef] = []
    for n in ("Section L.docx", "Section M.docx", "SOW.docx"):
        p = os.path.join(ED, n); open(p, "wb").write(n.encode() * 50); files[ef].append(p)
    lib = DV.Library(W.Workspace(W.data_dir_for(LIST), ef).p("documents")).load()
    for p in files[ef]:
        lib.add(p, [{"x": "The Offeror shall comply.", "l": "1"}], doc_name=os.path.basename(p))

gate = threading.Event()
mode = {"fail": None, "slow": False}


def chunks_of(path, say=None):
    name = os.path.basename(path)
    for pg in range(1, 5):
        if say:
            say(f"[1/1] {name} - PDF page {pg}/4...")
        if mode["slow"]:
            gate.wait(20)
    if mode["fail"] == name:
        raise ValueError("damaged file")
    return [("Page 1", f"The Offeror shall describe item {name}. The Offeror shall provide the schedule for {name}.")]


app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
rp = w.read_page
rp.chunks_of = chunks_of
check("the customer documents are ticked, Read is ready", len(rp.boxes) == 3 and rp.read_btn.isEnabled() and all(cb.isEnabled() for cb in rp.boxes))


def wait(cond, secs=30):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


# 0. ticking many at once
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
rp.tick(False)
check("Untick all: none ticked, Read waits", rp.chosen() == [] and not rp.read_btn.isEnabled() and rp.count.text() == "0 of 3 ticked")
rp.boxes[0].setSelected(True); rp.boxes[2].setSelected(True)
rp.tree.setFocus(); QTest.keyClick(rp.tree, Qt.Key_Space); app.processEvents()
check("select several, Space ticks them all", [r.isChecked() for r in rp.boxes] == [True, False, True] and rp.read_btn.isEnabled(),
      [r.isChecked() for r in rp.boxes])
rp.boxes[0].setChecked(False); app.processEvents()
check("unticking one selected row unticks every selected row", [r.isChecked() for r in rp.boxes] == [False, False, False])
check("Tick all", rp.tick(True) == 3 and len(rp.chosen()) == 3 and rp.count.text() == "3 of 3 ticked")
rp.tree.clearSelection()

# 1. a file that cannot be read
mode.update(fail="Section M.docx", slow=False)
out = os.path.join(tmp, "Heron", "Heron_Compliance_Matrix.xlsx")
rp.read(files["Heron"], out)
wait(lambda: rp.worker is None)
check("a file that cannot be read: red, names the file, says nothing was made", rp.panel.state == "failed" and rp.panel.isVisible()
      and "Section M.docx" in rp.panel.detail.text() and "No compliance matrix was made" in rp.panel.detail.text(), rp.panel.detail.text())
check("and says what to do", "Read again" in rp.panel.hint.text(), rp.panel.hint.text())
check("no matrix was written, and Read works again", w.review is None and not os.path.exists(out) and rp.read_btn.isEnabled()
      and rp.read_btn.text() == "Read" and not w.task.running())
# 2. running: progress, locks, one read at a time
mode.update(fail=None, slow=True); gate.clear()
rp.refresh()
first = rp.read(files["Heron"], out)
app.processEvents()
check("Read starts: the panel, the bar in the status bar", first is not None and rp.panel.state == "running" and rp.panel.isVisible()
      and w.task.running() and rp.panel.stop_btn.isVisible())
check("Read, Add files, the start choice and the ticks are locked", not rp.read_btn.isEnabled() and rp.read_btn.text() == "Reading..."
      and not rp.add_btn.isEnabled() and not rp.start.isEnabled() and all(not cb.isEnabled() for cb in rp.boxes))
second = rp.read(files["Heron"], out + ".2.xlsx")
check("a second Read does nothing: one read, one matrix", second is None and rp.worker is first)
rp.refresh(); app.processEvents()
check("moving between pages keeps it locked", not rp.read_btn.isEnabled() and all(not cb.isEnabled() for cb in rp.boxes))
wait(lambda: "page" in rp.panel.detail.text(), 5)
check("the file and the page within it", rp.panel.detail.text().startswith("File 1 of 3: Section L.docx (page"), rp.panel.detail.text())
rp.panel.moved -= PG.QUIET_S + 5; rp.panel._tick()
check("a step quiet for a minute says it is still working", "Still working" in rp.panel.hint.text(), rp.panel.hint.text())
check("the clock runs", ":" in rp.panel.clock.text())
gate.set()
wait(lambda: rp.worker is None)
check("it ends green with what it read", rp.panel.state == "done" and rp.panel.bar.value() == PG.SCALE and "sentences" in rp.panel.detail.text(),
      rp.panel.detail.text())
check("the matrix is made once, and the status bar clears", w.review is not None and os.path.isfile(out) and not os.path.exists(out + ".2.xlsx")
      and not w.task.running())
check("the lock comes off", not rp.running())
# 3. Stop
mode.update(slow=True); gate.clear()
w.go("read"); rp.refresh()
n_before = len(w.review.M.items)
newf = os.path.join(tmp, "Heron", "Attachment J.docx"); open(newf, "wb").write(b"J" * 99)
rp.read([newf])
app.processEvents()
rp.panel.stop_btn.click(); app.processEvents()
check("Stop says it stops after this file", "Stopping" in rp.panel.stop_btn.text() and not rp.panel.stop_btn.isEnabled())
gate.set()
wait(lambda: rp.worker is None)
check("stopped: amber, nothing written", rp.panel.state == "stopped" and len(w.review.M.items) == n_before
      and "Nothing was written" in rp.panel.detail.text())
# 4. an error after reading is shown, not silent
mode.update(slow=False)
real = CR.add_read
CR.add_read = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
rp.read([newf])
wait(lambda: rp.worker is None)
CR.add_read = real
check("an error while building: red, the matrix as it was", rp.panel.state == "failed" and "as it was before Read" in rp.panel.detail.text()
      and len(w.review.M.items) == n_before and not rp.running() and rp.read_btn.text() == "Read", rp.panel.detail.text())
# 5. switching effort during a read
mode.update(slow=True); gate.clear()
rp.read([newf])
app.processEvents()
check("switching effort: asked first; No keeps reading", rp.confirm_stop(answer=False) is False and rp.running())
ok = w.open_effort("Osprey")
check("Yes (tests): the read is thrown away and the other effort opens", ok and w.effort_name == "Osprey" and not rp.running()
      and rp.panel.state == "stopped")
gate.set()
from skqt import readpage as RP
wait(lambda: not RP._ORPHANS)
app.processEvents()
check("the thrown-away read writes nothing", w.effort_name == "Osprey" and w.review is None and len(C.Matrix(out).load().items) == n_before)
src = open(os.path.join(A.BASE_DIR, "skqt", "mainwin.py"), encoding="utf-8").read()
check("closing the window during a read asks, then waits for it", "self.read_page.confirm_stop()" in src and "wk.wait(" in src)
w.close()
n = sum(checks)
print(f"QT READ PROGRESS PASS ({n}/{len(checks)})" if n == len(checks) else f"QT READ PROGRESS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
