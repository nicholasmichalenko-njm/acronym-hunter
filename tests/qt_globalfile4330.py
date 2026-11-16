"""4.33.0 step 2b, as 4.34.0 reshaped it (ST21, ST22) and 4.47.0 renamed it, offscreen: setting a PC up is Settings >
Where the Production Datum comes from. A PC that is not connected says so in one sentence; Connect from a file... takes a
version; with the shared folder chosen the file buttons leave. No What changed... Fictional values."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_THEME"] = "light"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import globalfile as GX, globalfolder as GF, globalstd as GS
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, globalview as GV
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


other = os.path.join(tmp, "other pc", "config"); os.makedirs(other)          # the PC of someone who updates
F = os.path.join(tmp, "Shared", "Global Standards"); os.makedirs(F)
with open(os.path.join(other, "rules.json"), "w") as f:
    json.dump({"rules": {"RU1": {"on": True}}}, f)
GF.update(other, F, by="Ada", note="The first set")
with open(os.path.join(other, "rules.json"), "w") as f:
    json.dump({"rules": {"RU1": {"on": False}}}, f)
GF.update(other, F, by="Ada", note="Rule 1 off")
GX.write(F, 1); GX.write(F, 2)                                   # 4.34.0: a file is written when asked for

cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("settings"); app.processEvents()
sp = w.settings_page                                             # 4.34.0 (ST21): setting a PC up is Settings; the Global Standards page has no setup
vis = lambda b: not b.isHidden()
check("Settings has the heading Where the Production Datum comes from, with the three ways named plainly",
      sp.gsl_card.title.text() == "Where the Production Datum comes from" and sp.gs_link.text() == "Connect to a folder..."
      and sp.gs_install.text() == "Connect from a file..." and sp.gs_save.text() == "Save a file to send...")
check("not connected: it says so in one sentence", "No Production Datum is installed" in sp.gsl_folder.text() and vis(sp.gs_install), sp.gsl_folder.text())
w.go("globalstd"); app.processEvents()
gp = w.globalstd_page
check("the Global Standards page says the same sentence with one way to Settings, and nothing else to set up",
      "No Production Datum is installed" in gp.gs_folder.text() and vis(gp.gs_setup) and not hasattr(gp, "gs_link") and not hasattr(gp, "gs_install"), gp.gs_folder.text())
gp.gs_setup.click(); app.processEvents()
check("... and that button opens Settings", w.stack.currentWidget() is sp)
seen = []; real = w.status; w.status = lambda t: (seen.append(t), real(t))
bad = os.path.join(tmp, "notes.skgs"); open(bad, "w").write("hello")
check("a file of another kind is refused in words", GV.install(sp, bad) == "" and any("was not installed" in t and "not a Global Standards file" in t for t in seen), seen)
said = GV.install(sp, os.path.join(F, GX.file_name(1))); app.processEvents()
check("Connect from a file... takes the version, and says who changed it", "Production Datum 1, changed by Ada" in said and GS.state(cfg)["version"] == 1
      and "installed from a file" in sp.gsl_text.text(), (said, sp.gsl_text.text()))
check("the PC is then on what it was given, not connected to a folder", "not connected to a folder" in sp.gsl_folder.text() and "No Production Datum is installed" not in sp.gsl_folder.text(), sp.gsl_folder.text())
GV.install(sp, os.path.join(F, GX.file_name(2))); app.processEvents()
check("a later file is taken the same way; the number is in the title", GS.state(cfg)["version"] == 2 and "Production Datum 2" in (w.title(), w.windowTitle())[1], w.windowTitle())
check("there is no What changed... and no notice on screen (ST22)", not hasattr(GV, "changed_dialog") and not hasattr(sp, "gs_changed") and not hasattr(gp, "gs_notice"))
GV.link(sp, F); app.processEvents()
check("with the shared folder chosen, the file buttons leave: the folder carries it", not vis(sp.gs_install) and not vis(sp.gs_save) and "Shared folder: " in sp.gsl_folder.text(), sp.gsl_folder.text())
words = (sp.gsl_folder.text() + sp.gsl_card.title.text() + sp.gs_link.text() + sp.gs_install.text() + sp.gs_save.text() + GV.NOT_CONNECTED).lower()
check("the words: no publish, no draft, no link a folder, no install, no starter set", not any(x in words for x in ("publish", "draft", "link a folder", "install a file", "starter set", "built-in starter")), words)
w.close()
n = sum(checks)
print(f"QT GLOBALFILE 4330 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
