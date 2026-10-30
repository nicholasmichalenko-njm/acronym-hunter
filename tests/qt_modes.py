"""2.79.0 work modes and hand-offs exactly as you see them, offscreen: the first-start question sets Offline (2.97.0;
Secured before) or Connected and the title shows it; each mode lists its steps; Secured flags a backup folder that OneDrive uploads;
Connected sends backups to the team folder, marks who has an effort open and warns before opening one someone else has
open; Save to the team folder writes a package carrying the author names and the revision; a second PC opens it where
the sender was, with the same names in the pickers; the import says which copy is newer (newer, older, both changed)
and what differs in the matrix; a package from a newer Stationkeeper waits for the update."""
import json, os, sys, tempfile, time, zipfile
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
OD = os.path.join(tmp, "OneDrive - Sierra Space"); os.makedirs(OD)
os.environ["OneDriveCommercial"] = OD
import compliance as C, effort as E, lineage as LG, workmode as WM, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import modes as MO
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def make_effort(root, name):
    d = os.path.join(root, name); os.makedirs(os.path.join(d, "Customer documents"))
    lp = os.path.join(d, f"{name}_Effort_List.xlsx")
    L = E.EffortList(lp, name); L.pending = True; L.save()
    M = C.Matrix(os.path.join(d, f"{name}_Compliance_Matrix.xlsx"), name)
    M.items = C.extract([("Section L.docx", [("Page 1", "L.4 Technical. The Offeror shall describe the thermal design. "
                                                        "The Offeror shall provide the schedule. The Offeror shall list the risks.")])])
    M.outline = C.parse_outline("1.1 Technical Approach\n1.2 Schedule")
    M.save()
    W.Workspace(W.data_dir_for(lp), name).set("compliance_path", M.path)
    return lp


cfgA = os.path.join(tmp, "configA"); os.makedirs(cfgA)
LIST = make_effort(os.path.join(tmp, "PC1"), "Heron")
E.Registry(os.path.join(cfgA, "efforts.json")).put("Heron", path=LIST, customer_dir=os.path.join(os.path.dirname(LIST), "Customer documents"))
app = QApplication([]); D.apply(app)
a = MainWindow(app, cfgA, A.APP_VERSION); a.resize(1500, 950); a.show()
check("no mode yet: no badge; the suggestion follows OneDrive for work", MO.mode() == "" and "Offline" not in a.windowTitle()
      and WM.suggest() == WM.CONNECTED and a.mode_chip.text() == "Mode not set")
MO.ask_mode(a, answer="offline")
check("Offline: the title and the chip say so; the steps say nothing leaves this PC", "Offline" in a.windowTitle()
      and a.mode_chip.text() == "Offline"
      and "nothing leaves this PC except files you save" in a.settings_page.mode.steps.text() if (a.settings_page.mode.fill() or True) else False)
check("2.97.0: a setting of Secured from before 2.97 reads as Offline (never locked for anyone)", WM.get({"work_mode": "secured"}) == WM.OFFLINE)
a.safety.test_dir = None
os.environ.pop("AH_TEST")
MO.save(backup_dir=os.path.join(OD, "Backups"))
check("Offline: a backup folder that OneDrive uploads is flagged", "leave this PC" in a.safety.status_text(), a.safety.status_text())
MO.save(backup_dir="")
TEAM = os.path.join(OD, "Proposal Center - Efforts")
a.settings_page.mode.choose(WM.CONNECTED)
a.settings_page.mode.choose_team(TEAM)
check("Connected: the title says so; backups go to the team folder", "Connected" in a.windowTitle()
      and a.safety.backup_dir() == os.path.join(TEAM, "Backups"))
os.environ["AH_TEST"] = "1"
a.safety.test_dir = os.path.join(TEAM, "Backups")
# someone else has it open
os.makedirs(os.path.join(TEAM, WM.WORKING))
json.dump({"effort": "Heron", "user": "jgarcia", "computer": "PC-9", "since": time.strftime("%Y-%m-%dT%H:%M")},
          open(WM.marker_path(TEAM, "Heron"), "w"))
a.presence_answer = "cancel"
check("someone else has it open: warned, and Cancel leaves it closed", a.open_effort("Heron") is False and a.ws is None
      and "jgarcia has Heron open on PC-9" in a.statusBar().currentMessage())
a.presence_answer = "open"
check("Open anyway opens it, and the marker says it is open here now", a.open_effort("Heron") and WM.who(TEAM, "Heron")["user"] != "jgarcia")
a.authors.merge([("Joe G.", None), ("M. Chen", None)], default=["Heron"])
R = a.review
s1, s2, s3 = R.M.items
R.req([s1], "1.1 Technical Approach"); a.changed(); a.save_now(); time.sleep(1.1)
a.go("assign"); a.assign_page.set_target("1.2 Schedule"); a.assign_page.select(s2["id"]); app.processEvents()
a.safety.revise()
man = a.record_page.save_to_team()
pk1 = man["path"]
check("Save to the team folder: named with the effort, stage, who and when", os.path.dirname(pk1) == WM.packages_dir(TEAM, "Heron")
      and os.path.basename(pk1).startswith("Heron "), os.path.basename(pk1))
check("the package carries the author names for the effort and the revision", [x["name"] for x in man["extra"]["authors"]] == ["Joe G.", "M. Chen"]
      and man["extra"]["revision"]["rev"] >= 2)
# a second PC opens it
cfgB = os.path.join(tmp, "configB"); os.makedirs(cfgB)
b = MainWindow(app, cfgB, A.APP_VERSION); b.resize(1500, 950); b.show(); b.safety.test_dir = os.path.join(tmp, "B backups")
b.presence_answer = "open"
gotB = b.import_package(pk1, dest=os.path.join(tmp, "PC2"), mode="both")
check("the second PC opens it where the sender was", gotB and b.stack.currentWidget() is b.assign_page and b.assign_page.cur == s2["id"]
      and b.assign_page.target == "1.2 Schedule", (b.assign_page.cur, b.assign_page.target))
check("with the same names in the pickers", b.people() == ["Joe G.", "M. Chen"])
# B works on it and hands it back: newer
b.review.req([b.review.item(s2["id"])], "1.2 Schedule"); b.changed(); b.save_now(); time.sleep(1.1); b.safety.revise()
pk2 = b.record_page.save_package(os.path.join(tmp, "from B.skpkg"))["path"]
a.presence_answer = "open"
gotA = a.import_package(pk2, dest=os.path.join(tmp, "PC1"), mode="replace")
check("back on the first PC: 'newer than your copy', with what differs", gotA and gotA["compare"]["relation"] == "newer"
      and "newer than your copy" in gotA["compare"]["text"] and "1 sentence(s) decided, assigned or noted differently" in gotA["compare"]["text"],
      gotA and gotA["compare"]["text"])
check("and the work is there", a.review.item(s2["id"]).get("decision") == "Keep")
# both change: diverged
a.review.req([a.review.item(s3["id"])], "1.1 Technical Approach"); a.changed(); a.save_now(); time.sleep(1.1); a.safety.revise()
b.review.req([b.review.item(s3["id"])], "1.2 Schedule"); b.changed(); b.save_now(); time.sleep(1.1); b.safety.revise()
pk3 = b.record_page.save_package(os.path.join(tmp, "from B 2.skpkg"))["path"]
c = MO and __import__("skqt.pkgimport", fromlist=["compare_with"]).compare_with(a, "Heron", pk3, json.loads(zipfile.ZipFile(pk3).read("manifest.json")))
check("both changed since the hand-off: said so, keep both suggested", c["relation"] == "diverged" and "both changed" in c["text"]
      and "Keep both" in c["text"], c["text"])
c2 = __import__("skqt.pkgimport", fromlist=["compare_with"]).compare_with(a, "Heron", pk1, json.loads(zipfile.ZipFile(pk1).read("manifest.json")))
check("an old package: older than your copy", c2["relation"] == "older" and "older than your copy" in c2["text"], c2["text"])
# a package from a newer Stationkeeper
newer = os.path.join(tmp, "newer.skpkg")
with zipfile.ZipFile(pk1) as zi, zipfile.ZipFile(newer, "w") as zo:
    for n in zi.namelist():
        data = zi.read(n)
        if n == "manifest.json":
            m = json.loads(data); m["app"] = "9.0.0"; data = json.dumps(m).encode()
        zo.writestr(n, data)
check("a package from a newer Stationkeeper waits for the update", a.import_package(newer, dest=os.path.join(tmp, "PC1"), mode="both") is None
      and "Install the update pack for 9.0.0" in a.statusBar().currentMessage())
a.close_effort()
check("closing removes this PC's marker", WM.who(TEAM, "Heron") is None)
check("lineage: a different effort with the same name is unrelated", LG.compare({"lineage": "x", "history": [{"rev": 1, "id": "a"}]},
                                                                              {"lineage": "y", "history": [{"rev": 1, "id": "b"}]})["relation"] == "unrelated")
a.close(); b.close()
n = sum(checks)
print(f"QT MODES PASS ({n}/{len(checks)})" if n == len(checks) else f"QT MODES FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
