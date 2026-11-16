"""4.47.0 offscreen, UX decisions 36 and 59: the Production Datum's mark is in the top bar on every page and opens one
panel with three states: nothing installed (one sentence, Connect), installed (number, date, what it holds), a newer one
ready (what will change, then Install). Connect is two actions. Fictional values."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_THEME"] = "light"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import datum as DT, globalfile as GX, globalfolder as GF, globalstd as GS
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, datummark as DM
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


other = os.path.join(tmp, "other pc", "config"); os.makedirs(other)          # the PC of someone who keeps the Datum
F = os.path.join(tmp, "Shared", "Production Datum"); os.makedirs(F)
with open(os.path.join(other, "rules.json"), "w") as f:
    json.dump({"rules": {"RU1": {"on": True}}}, f)
GF.update(other, F, by="Ada", note="The first set")
GX.write(F, 1)

cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
vis = lambda b: b.isVisibleTo(w)
mk = w.datum_mark
check("nothing installed: the mark says so, in the top bar", mk._plain == "No Production Datum installed" and vis(mk), mk._plain)
seen = []
for page in ("settings", "efforts", "tools", "globalstd"):
    w.go(page); app.processEvents(); seen.append(vis(mk))
check("... on every page, and nothing dismisses it", all(seen) and not hasattr(mk, "close_btn"), seen)
p = DM.open_panel(w); app.processEvents()
check("the panel: one sentence and one button, Connect", [r.text() for r in p.rows] == [DT.NOTHING] and p.main.text() == "Connect", [r.text() for r in p.rows])
m = p.connect_menu(); app.processEvents()
check("Connect is two actions: from a file, to a folder", [a.text() for a in m.actions()] == ["Connect from a file...", "Connect to a folder..."])
m.close(); p.close()
check("nothing is restricted and nothing asked: Settings and Global Standards open as before", w.stack.currentWidget() is not None)

said = DM.connect_file(w, os.path.join(F, GX.file_name(1))); app.processEvents()
check("Connect from a file... installs it; the mark reads Production Datum 1", GS.state(cfg)["version"] == 1 and mk._plain == "Production Datum 1", (said, mk._plain))
p = DM.open_panel(w); app.processEvents()
rows = [r.text() for r in p.rows]
check("installed: when, and what it holds, one line each with a count", rows[0].startswith("Installed 20") and any(x.startswith("Global Standards: ") for x in rows)
      and any(x.startswith("Acronym database: ") for x in rows) and any(x.startswith("Custom dictionaries: ") for x in rows), rows)
check("... Connect stays, smaller, and the panel explains nothing and holds no settings", p.main.text() == "Connect" and p.said["small"] and len(rows) == 4)
p.close()
check("the window's title carries the number", "Production Datum 1" in w.windowTitle(), w.windowTitle())

with open(os.path.join(other, "rules.json"), "w") as f:
    json.dump({"rules": {"RU1": {"on": False}}}, f)
GF.update(other, F, by="Ada", note="Rule 1 off")
GF.set_folder(F); w.title(); app.processEvents()
check("a newer one in the connected folder: Production Datum 1, 2 is ready", mk._plain == "Production Datum 1, 2 is ready", mk._plain)
p = DM.open_panel(w); app.processEvents()
rows = [r.text() for r in p.rows]
check("the panel says what will change, in counts, and that the person's work is not touched",
      rows[0].startswith("1 part will change: ") and rows[-1] == DT.NOT_TOUCHED and p.main.text() == "Install Production Datum 2", (rows, p.main.text()))
check("... and nothing has happened yet", GS.state(cfg)["version"] == 1)
p.take(); app.processEvents()
check("Install Production Datum 2 installs it", GS.state(cfg)["version"] == 2 and mk._plain == "Production Datum 2", mk._plain)
k = sum(checks)
print(f"QT DATUM 4470 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
