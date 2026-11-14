"""4.33.0, step 2b, offscreen: Settings > Global Standards. A PC with no link and no version says it runs on the
built-in starter and offers Link a folder... and Install a file...; Install a file... takes a version; the card then
says what the version changed, What changed... lists it, Mark as seen closes it. Fictional values."""
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

cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("settings"); app.processEvents()
sp = w.settings_page
vis = lambda b: not b.isHidden()
check("no link, no version: the card says the built-in starter and names the two ways in", "built-in starter" in sp.gs_folder.text()
      and "Link a folder..." in sp.gs_folder.text() and "Install a file..." in sp.gs_folder.text() and vis(sp.gs_link) and vis(sp.gs_install), sp.gs_folder.text())
check("nothing to see yet: no notice, no What changed...", not vis(sp.gs_notice) and not vis(sp.gs_changed))
seen = []; real = w.status; w.status = lambda t: (seen.append(t), real(t))
bad = os.path.join(tmp, "notes.skgs"); open(bad, "w").write("hello")
check("a file of another kind is refused in words", GV.install(sp, bad) == "" and any("was not installed" in t and "not a Global Standards file" in t for t in seen), seen)
said = GV.install(sp, os.path.join(F, GX.file_name(1))); app.processEvents()
check("Install a file... takes the version", "version 1" in said and GS.state(cfg)["version"] == 1 and "installed from a file" in sp.gs_text.text(), (said, sp.gs_text.text()))
check("the card is no longer on the starter", "built-in starter" not in sp.gs_folder.text() and "Not linked to a folder" in sp.gs_folder.text(), sp.gs_folder.text())
check("the card says the version was taken, with who and when", vis(sp.gs_notice) and "took version 1, updated by Ada" in sp.gs_notice.text() and vis(sp.gs_changed), sp.gs_notice.text())
GV.install(sp, os.path.join(F, GX.file_name(2))); app.processEvents()
check("a later version: the card counts what it changed here", "Version 2, updated by Ada" in sp.gs_notice.text() and "changed 1 thing" in sp.gs_notice.text(), sp.gs_notice.text())
dlg = GV.changed_dialog(sp, run=False)
row = [dlg.table.item(0, c).text() for c in range(4)]
check("What changed... lists the change: part, what, it was, it is now", dlg.table.rowCount() == 1 and row == ["Rules", "rules.RU1.on", "True", "False"], row)
check("... with the note", 'Note: "Rule 1 off"' in dlg.head.text(), dlg.head.text())
dlg.b_seen.click(); app.processEvents()
check("Mark as seen: the notice leaves the card", not vis(sp.gs_notice) and not vis(sp.gs_changed) and GX.notice(cfg) is None)
check("with nothing to show, What changed... opens nothing", GV.changed_dialog(sp, run=False) is None)
check("the card's words: no publish, no draft", not any(x in (sp.gs_folder.text() + sp.gs_install.text() + sp.gs_changed.text() + GV.STARTER).lower() for x in ("publish", "draft")))
w.close()
n = sum(checks)
print(f"QT GLOBALFILE 4330 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
