"""2.76.0 update packs and the security explanation in Qt, offscreen: Settings has Updates and About and security (why no
admin password: asInvoker, its own folder, the sandbox only takes rights away, running is not approval); a signed pack
shows what it changes, saves and closes the effort, installs and restarts; the user's data stays; Undo last update goes
back; a pack someone else signed is refused and nothing changes; Check program files; Stationkeeper Training has the
same cards; --apply-update, --check-program and --undo-update work with no window (IT, and the release build's test)."""
import os, sys, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\nSOW,Acronym,Statement of Work,Include\n")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.LOG_DIR = os.path.join(tmp, "logs")
import edsign
import updatepack as U
import effort as E
from PySide6.QtWidgets import QApplication, QMessageBox, QLabel
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import updates as UP
from skqt.mainwin import MainWindow
import skqt_main

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


KEY = bytes(range(32))
U.PUBLIC_KEYS = [edsign.public_key(KEY).hex()]


def build(folder, version, exe, extra=None):
    files = {"Stationkeeper.exe": exe, "_internal/python311.dll": "python", "_internal/base_library.zip": "lib " + version,
             "README.txt": "readme " + version}
    files.update(extra or {})
    for rel, text in files.items():
        p = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
    return U.write_manifest(folder, "Stationkeeper", version)


APP = os.path.join(tmp, "Stationkeeper")
M76 = build(APP, "2.76.0", "exe 2.76")
os.makedirs(os.path.join(APP, "config")); open(os.path.join(APP, "config", "app_settings.json"), "w").write('{"mine": 1}')
open(os.path.join(APP, "acronym_database.csv"), "w").write("Term\nMY ROW\n")
B77 = os.path.join(tmp, "b77"); build(B77, "2.77.0", "exe 2.77")
PACK = os.path.join(tmp, "Stationkeeper_US_Update_2.77.0.skupdate")
U.make_pack(B77, PACK, KEY, [M76], notes="Authors from one list")
BAD = os.path.join(tmp, "bad.skupdate")
U.make_pack(B77, BAD, bytes(range(1, 33)), [M76])
UP.app_dir = lambda: APP


def files():
    return {rel: open(os.path.join(APP, *rel.split("/")), "rb").read() for rel in
            ("Stationkeeper.exe", "README.txt", "acronym_database.csv", "config/app_settings.json")}


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Heron"); CDIR = os.path.join(EDIR, "Customer documents"); os.makedirs(CDIR)
LIST = os.path.join(EDIR, "Heron_Effort_List.xlsx")
L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CDIR)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
sp = w.settings_page
w.go("settings"); sp.refresh(); app.processEvents()
texts = " ".join(l.text() for l in sp.findChildren(QLabel))
check("Settings: Updates and About and security", "Install Stationkeeper once" in texts and "Why Stationkeeper runs without an administrator password" in texts)
check("the explanation: asInvoker, its own folder, the sandbox only takes rights away, running is not approval",
      all(t in UP.WHY_NO_ADMIN for t in ("asInvoker", "writes only inside its own folder", "AppContainer", "takes rights away",
                                          "Running does not mean approved", "AppLocker", "SECURITY.md", "Check program files")))
check("the version line", "Version 2.76.0" in sp.up.lbl.text(), sp.up.lbl.text())
before = files()
check("a pack someone else signed: refused, nothing changes", sp.install_update(BAD, answer="install", restart=lambda: None) is None
      and "not signed by the Stationkeeper publisher" in w.statusBar().currentMessage() and files() == before and w.ws is not None)
restarted = []
r = sp.install_update(PACK, answer="install", restart=lambda: restarted.append(1))
after = files()
check("a signed pack: the effort saved and closed, program files 2.77.0, restarted", r and r["to"] == "2.77.0" and restarted
      and w.ws is None and after["Stationkeeper.exe"] == b"exe 2.77", r)
check("the user's database and settings stay", after["acronym_database.csv"] == before["acronym_database.csv"]
      and after["config/app_settings.json"] == before["config/app_settings.json"])
check("the version line offers Undo", "Version 2.77.0" in sp.up.lbl.text() and "Undo last update goes back to 2.76.0" in sp.up.lbl.text(), sp.up.lbl.text())
rc = UP.check_program(w, show=False)
check("Check program files: all match", rc and not (rc["changed"] or rc["missing"] or rc["extra"]) and "All 4 program files match" in w.statusBar().currentMessage())
w.open_effort("Heron")
u = sp.undo_update(answer="undo", restart=lambda: restarted.append(2))
check("Undo last update: 2.76.0 back, data untouched", u and u["to"] == "2.76.0" and files() == before and restarted == [1, 2])
check("nothing more to undo", sp.undo_update(answer="undo", restart=lambda: None) is None)
w.close()
# Stationkeeper Training has the same cards on its Build step
A.TRAINING_APP = True
from skqt.trainingwin import TrainingWindow
tw = TrainingWindow(app); tw.show(); tw.go("build"); app.processEvents()
tt = " ".join(l.text() for l in tw.findChildren(QLabel))
check("Stationkeeper Training: Updates and About and security on Build", "Install Stationkeeper once" in tt and "asInvoker" in tt
      and UP.program_name() == "StationkeeperTraining")
tw.close()
A.TRAINING_APP = False
# no window: IT can push a pack; the build's own test uses these
U.recover(APP)
log = os.path.join(A.LOG_DIR, "update.txt")
rc1 = skqt_main.main(["Stationkeeper.exe", "--apply-update", PACK])
rc2 = skqt_main.main(["Stationkeeper.exe", "--check-program"])
rc3 = skqt_main.main(["Stationkeeper.exe", "--apply-update", PACK])
rc4 = skqt_main.main(["Stationkeeper.exe", "--undo-update"])
lg = open(log, encoding="utf-8").read()
check("--apply-update, --check-program, --undo-update with no window", (rc1, rc2, rc3, rc4) == (0, 0, 2, 0) and "UPDATE OK 2.76.0 -> 2.77.0" in lg
      and "CHECK OK" in lg and "already has version 2.77.0" in lg and "UNDO OK 2.77.0 -> 2.76.0" in lg and files() == before, lg)
src = open(os.path.join(A.BASE_DIR, "skqt_main.py"), encoding="utf-8").read()
check("the program puts back a stopped update before anything else loads", src.index("_recover_update()") < src.index("import app_gui as A"))
shutil.rmtree(tmp, ignore_errors=True)
n = sum(checks)
print(f"QT UPDATE PASS ({n}/{len(checks)})" if n == len(checks) else f"QT UPDATE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
