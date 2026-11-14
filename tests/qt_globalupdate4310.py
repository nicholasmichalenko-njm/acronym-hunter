"""4.31.0, step 2a, offscreen: Settings > Global Standards. Link a folder; someone who can write to it sees Update Global
Standards with the changes waiting on the PC, Put back, a note and Update to version N...; a PC on an older version is
told the new one is ready and takes it with Use it now, or by itself when the app opens. No effort may be open for an
update. The words are update and changes waiting. Fictional values."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_THEME"] = "light"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import globalfolder as GF, globalstd as GS
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, globalview as GV
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def put(rel, obj):
    with open(os.path.join(cfg, rel), "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj))


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
F = os.path.join(tmp, "Shared", "Global Standards"); os.makedirs(F)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("settings"); app.processEvents()
sp = w.settings_page
vis = lambda b: not b.isHidden()
check("not linked: the card says so and offers Link a folder...; nothing to use, no update", "Not linked to a folder" in sp.gs_folder.text()
      and vis(sp.gs_link) and not vis(sp.gs_use) and not vis(sp.gs_update), sp.gs_folder.text())
check("the card's words: no publish, no draft", not any(x in (sp.gs_text.text() + sp.gs_folder.text() + sp.gs_card.title.text() + sp.gs_update.text()).lower()
                                                      for x in ("publish", "draft")))
GV.link(sp, F); app.processEvents()
check("linked to a folder this PC can write to: it says so and shows Update Global Standards...", GF.folder() == F and "You can update" in sp.gs_folder.text()
      and vis(sp.gs_update), sp.gs_folder.text())
put("banned_words.csv", "word\nsynergy\n")
put("rules.json", {"format": 1, "rules": [{"id": "r1", "limit": 11}]})
dlg = GV.update_dialog(sp, run=None)
check("the dialog lists the changes waiting and names the next version on its button", dlg.table.rowCount() == len(dlg.rows) >= 2
      and dlg.b_go.text() == "Update to version 1..." and dlg.b_go.isEnabled() and not dlg.b_back.isEnabled(), dlg.b_go.text())
dlg.note.setText("First version"); dlg.b_go.click(); app.processEvents()
check("Update writes version 1 with the note; this PC is on it", GF.current(F)["version"] == 1 and GF.current(F)["note"] == "First version"
      and GS.state(cfg)["version"] == 1 and "version 1, updated from this PC" in sp.gs_text.text(), sp.gs_text.text())
put("rules.json", {"format": 1, "rules": [{"id": "r1", "limit": 12}]})
put("banned_words.csv", "word\nsynergy\nleverage\n")
dlg = GV.update_dialog(sp, run=None)
whats = [dlg.table.item(i, 1).text() for i in range(dlg.table.rowCount())]
check("a changed value is a row with the version's value and this PC's", "rules.r1.limit" in whats and dlg.table.item(whats.index("rules.r1.limit"), 2).text() == "11"
      and dlg.table.item(whats.index("rules.r1.limit"), 3).text() == "12" and dlg.b_go.text() == "Update to version 2...", whats)
dlg.table.selectRow(whats.index("banned_words.csv")); dlg.b_back.click(); app.processEvents()
check("Put back drops that change: the file is as the version has it and the row is gone", open(os.path.join(cfg, "banned_words.csv")).read() == "word\nsynergy\n"
      and dlg.table.rowCount() == 1, dlg.table.rowCount())
w.effort_name = "Heron"
check("with an effort open the update is refused: close the effort first", GV.update_dialog(sp, run=False, note="x") is None and GF.versions(F) == [1])
w.effort_name = ""
man = GV.update_dialog(sp, run=False, note="Limit 12")
check("with no effort open it goes through: version 2", man["version"] == 2 and GF.versions(F) == [1, 2])

# the same PC, set back to version 1 as another PC would be: told, then Use it now
GS.take(cfg, 1, GS.LINKED); put("rules.json", {"format": 1, "rules": [{"id": "r1", "limit": 11}]})
GS.take(cfg, 1, GS.LINKED)
sp.refresh(); app.processEvents()
check("a PC on version 1 is told version 2 is ready, with who and the note, and Use it now", "version 2 is ready" in sp.gs_ready.text()
      and "Limit 12" in sp.gs_ready.text() and vis(sp.gs_use), sp.gs_ready.text())
check("the tick says it once and takes nothing", "version 2 is ready" in GV.watch(w) and GV.watch(w) == "" and GS.state(cfg)["version"] == 1)
said = GV.use_now(sp); app.processEvents()
check("Use it now takes it: the PC is on version 2 and nothing is ready", GS.state(cfg)["version"] == 2 and "version 2" in said and not vis(sp.gs_use)
      and json.load(open(os.path.join(cfg, "rules.json")))["rules"][0]["limit"] == 12, said)
GS.take(cfg, 1, GS.LINKED); put("rules.json", {"format": 1, "rules": [{"id": "r1", "limit": 11}]}); GS.take(cfg, 1, GS.LINKED)
real = GF.can_update
GF.can_update = lambda f: False                        # a PC whose account cannot write to the folder
sp.refresh(); app.processEvents()
check("a PC that cannot write to the folder sees no Update, and takes the new version by itself when the app opens",
      not vis(sp.gs_update) and "reads versions" in sp.gs_folder.text() and "version 2" in GV.at_open(w) and GS.state(cfg)["version"] == 2, sp.gs_folder.text())
check("... and it cannot open the update", GV.update_dialog(sp, run=False, note="x") is None and GF.versions(F) == [1, 2])
GF.can_update = real
GS.take(cfg, 1, GS.LINKED); put("rules.json", {"format": 1, "rules": [{"id": "r1", "limit": 9}]})
said = GV.at_open(w)
check("a PC that can update and has changes waiting is not moved by itself: it is told what Use it now replaces", GS.state(cfg)["version"] == 1
      and "replaces the changes waiting" in said and json.load(open(os.path.join(cfg, "rules.json")))["rules"][0]["limit"] == 9, said)
sp.refresh(); said = GV.use_now(sp)
check("Use it now then says what it replaced and where the backup is", "replaced this PC's own changes in: Rules" in said and "Global Standards backups" in said, said)
w.close()
n = sum(checks)
print(f"QT GLOBAL UPDATE 4310 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
