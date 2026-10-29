"""2.81.0 help without sending data, offscreen: the support file holds versions, the logs and checks, and no paths,
names, file names or document text even when a log line carries one; two starts in a row that never finished make the
next start safe, and a finished start clears it; what's new shows once after an update, with the versions since the
last one; Ctrl+K finds a page, an effort, a sentence and a person and goes there; F1 lists the shortcuts; Settings has
Help and support."""
import json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.LOG_DIR = os.path.join(tmp, "logs"); os.makedirs(A.LOG_DIR)
import compliance as C, effort as E, workspace as W, supportfile as SF
from PySide6.QtWidgets import QApplication, QMessageBox, QLabel
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import helpcenter as HC
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); os.makedirs(ED)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
M = C.Matrix(os.path.join(ED, "Heron_Compliance_Matrix.xlsx"), "Heron")
M.items = C.extract([("Section L.docx", [("Page 1", "The Offeror shall describe the thermal design. The Offeror shall provide the schedule.")])])
M.save(); W.Workspace(W.data_dir_for(LIST), "Heron").set("compliance_path", M.path)
with open(os.path.join(A.LOG_DIR, "events.jsonl"), "w") as f:
    f.write(json.dumps({"time": "2026-10-29T10:00:00", "kind": "error", "message": "matrix save failed", "where": ["compliance.py:1274 save"]}) + "\n")
    f.write(json.dumps({"time": "2026-10-29T10:01:00", "kind": "error", "message": "C:\\Users\\nmich\\Heron\\secret.docx", "who": "nick@sierraspace.com"}) + "\n")
with open(os.path.join(A.LOG_DIR, "activity.jsonl"), "w") as f:
    f.write(json.dumps({"time": "2026-10-29T10:02:00", "action": "qt_effort_opened"}) + "\n")
A.save_settings({"work_mode": "connected", "team_dir": "C:\\Users\\nmich\\OneDrive - Sierra Space\\Team", "backup_dir": "D:\\Backups"})
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
out = os.path.join(tmp, "support.zip")
res = HC.make_support_file(w, out)
z = zipfile.ZipFile(out)
blob = "\n".join(z.read(n).decode("utf-8", "replace") for n in z.namelist())
about = json.loads(z.read("about.json"))
check("the support file: versions, logs, checks", about["app_version"] == A.APP_VERSION and about["work_mode"] == "connected"
      and about["backups_on"] is True and "logs/events.jsonl" in z.namelist() and "matrix save failed" in blob, z.namelist())
check("and no paths, names, addresses or file names, even from a log line that carried one", "nmich" not in blob and "secret.docx" not in blob
      and "sierraspace" not in blob and "OneDrive" not in blob and "Backups" not in blob and "Heron" not in blob, blob[:400])
# safe start
sd = os.path.join(tmp, "sandbox")
check("two starts that never finished make the third safe", SF.begin(sd) is False and SF.begin(sd) is False and SF.begin(sd) is True)
SF.started(sd)
check("a finished start clears it", SF.begin(sd) is False)
src = open(os.path.join(A.BASE_DIR, "skqt_main.py"), encoding="utf-8").read()
check("the program counts starts and skips the last effort in a safe start", "SF.begin(A.SANDBOX_DIR)" in src and "Safe start:" in src
      and "SF.started(A.SANDBOX_DIR)" in src)
# what's new
st = A.load_settings(); st["last_version"] = "2.78.0"; A.save_settings(st)
d = HC.after_update(w, run=False)
check("what's new once after an update, with each version since the last one", d is not None and [v for v, _n in d.notes][0] == A.APP_VERSION and "2.79.0" in [v for v, _n in d.notes]
      and "2.78.0" not in [v for v, _n in d.notes] and HC.after_update(w, run=False) is None)
check("a first start shows nothing", SF.whats_new("", A.APP_VERSION) == [])
# Ctrl+K
f = HC.open_finder(w, run=False)
f.box.setText("record"); app.processEvents()
f.go()
check("Ctrl+K: a page", w.stack.currentWidget() is w.record_page)
f = HC.open_finder(w, run=False); f.box.setText("thermal"); app.processEvents()
act = f.go()
check("Ctrl+K: a sentence by its words, selected on the page", act[0] == "sentence" and w.stack.currentWidget() is w.assign_page
      and w.assign_page.cur == act[1])
f = HC.open_finder(w, run=False); f.box.setText("heron effort"); app.processEvents()
check("Ctrl+K: an effort", f.list.count() >= 1 and f.list.item(0).data(0x0100)[0] == "effort")
w.authors.merge([("Joe G.", None)], default=["Heron"])
f = HC.open_finder(w, run=False); f.box.setText("joe"); app.processEvents()
check("Ctrl+K: a person", f.go()[0] == "person")
sh = HC.show_shortcuts(w, run=False)
check("F1: the keyboard shortcuts", sh.table.rowCount() == len(HC.SHORTCUTS) and any(r[1] == "Ctrl+K" for r in HC.SHORTCUTS))
w.go("settings"); app.processEvents()
check("Settings: Help and support", "Create a support file" in " ".join(b.text() for b in w.settings_page.help.findChildren(type(w.settings_page.help.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton)[0]))))
w.close()
n = sum(checks)
print(f"QT HELP PASS ({n}/{len(checks)})" if n == len(checks) else f"QT HELP FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
