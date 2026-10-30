"""2.89.0 team defaults, offscreen: one PC makes a team pack (author list, matrix design, banned words, default gate goals,
logos, Effort Home layouts by role, sensitivity markings, team topics; logos and the design locked); another PC sees what
installing does, installs it (adds what it lacks, keeps its own, locked parts replace and cannot be changed), and Undo puts
everything back; a damaged or altered pack is refused."""
import json, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import authorlist as AL, branding as BR, teampack as TP, matrixdesign as MD, effortrec as R
from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def pic(name, col):
    p = os.path.join(tmp, name); Image.new("RGB", (300, 100), col).save(p); return p


# ---- PC A: the proposal manager's PC
cfgA = os.path.join(tmp, "pcA"); os.makedirs(cfgA)
la = AL.load(cfgA)
for n in ("A. Lee", "Dana Ruiz", "Sam Ortiz"):
    la.add(n)
d = MD.default(); d["columns"] = d["columns"][:5]; MD.save_team(cfgA, d)
open(os.path.join(cfgA, "banned_words.csv"), "w").write("Phrase,Level,Why\nworld-class,bad,Unsupported claim\nbest-in-class,bad,Unsupported\n")
json.dump({"stages": {"Intake": ["Kickoff held", "docs_added"], "Red team": ["Packets sent"]}}, open(os.path.join(cfgA, "stage_goals.json"), "w"))
BR.add_logo(cfgA, pic("a1.png", (200, 30, 40))); BR.add_logo(cfgA, pic("a2.png", (20, 90, 160)))
TP._write(os.path.join(cfgA, "team_roles.json"), {"Author": ["mywork", "calendar", "tasks"]})
TP.save_markings(cfgA, ["CUI//SP-PROPIN", "Proprietary"])
TP.save_topics(cfgA, ["Thermal", "Schedule", "Key personnel"])
import postsub as PS
PS.save_default(cfgA, [{"text": "Archive the final volumes", "owner": "Production", "days": 1}])
import process as PR
PR.save(cfgA, gates=PR.load(cfgA)["gates"] + [{"name": "Color team sign-off", "behavior": "hard", "about": "Signed by the capture lead"}],
        roles=["Proposal Manager", "Book Boss"])
import doctypes as DT
DT.save(cfgA, DT.load(cfgA)["types"] + [{"name": "Pricing Instructions", "initial": "PI"}])
have = TP.available(cfgA)
check("the maker's PC lists what it can share", set(have) == set(TP.PARTS), have)
pack = os.path.join(tmp, f"Team{TP.EXT}")
info = TP.make(cfgA, pack, TP.PARTS, lock=("logos", "design"), name="Sierra team", notes="First pack")
check("a team pack carries the ticked parts and locks", info["parts"] == list(TP.PARTS) and info["locks"] == ["design", "logos"]
      and "SharePoint" in info["handling"])
# ---- PC B: an author's PC, with things of its own
cfgB = os.path.join(tmp, "config"); os.makedirs(cfgB)
lb = AL.load(cfgB); lb.add("Zed Quinn")
open(os.path.join(cfgB, "banned_words.csv"), "w").write("Phrase,Level,Why\nsynergy,warn,Vague\n")
json.dump({"stages": {"Intake": ["My own goal"]}}, open(os.path.join(cfgB, "stage_goals.json"), "w"))
own_logo = BR.add_logo(cfgB, pic("b1.png", (30, 140, 60)))
MD.save_team(cfgB, MD.default())
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfgB, A.APP_VERSION); w.resize(1500, 950); w.show()
tc = w.settings_page.team_card
said = dict(tc.install(pack, confirm=False))
check("the preview says what installing does, part by part", "1" not in said["authors"] or "3 name(s) added" in said["authors"], said)
check("the preview: locked parts replace, the rest add", "Replaces" in said["logos"] and "Replaces" in said["design"]
      and "2 banned" in said["banned"] and "added" in said["goals"], said)
check("nothing changes before Install", AL.load(cfgB).names() == ["Zed Quinn"] and not TP.installed(cfgB))
tc.install(pack, confirm=True)
names = AL.load(cfgB).names()
check("names the PC lacked are added; its own stay", names == ["A. Lee", "Dana Ruiz", "Sam Ortiz", "Zed Quinn"], names)
check("the window's pickers see the new names", "Dana Ruiz" in w.authors.names())
bw = open(os.path.join(cfgB, "banned_words.csv")).read()
check("banned phrases are added to the PC's own", "synergy" in bw and "world-class" in bw and "best-in-class" in bw)
g = json.load(open(os.path.join(cfgB, "stage_goals.json")))["stages"]
check("default gate goals are added, the PC's own kept", g["Intake"] == ["My own goal", "Kickoff held", "docs_added"] and g["Red team"] == ["Packets sent"], g)
check("new efforts start from them", R.CUSTOM_GOALS.get("Red team") == ["Packets sent"])
lg = BR.logos(cfgB)
check("locked logos replace the PC's own, at the top of the menu", len(lg) == 2 and Image.open(lg[0]).getpixel((5, 5)) == (200, 30, 40)
      and len(w.rail_brand.paths) == 2)
bc = w.settings_page.branding_card
check("locked logos cannot be changed on the PC", not bc.add_logo(pic("b2.png", (1, 2, 3))) and len(BR.logos(cfgB)) == 2
      and "Set by the team pack Sierra team" in bc.note.text())
check("the locked matrix design replaces the PC's", len(MD.load_team(cfgB)["columns"]) == 5)
w.matrix_page.d = MD.default()
check("and cannot be saved over", w.matrix_page.team_save() is None and len(MD.load_team(cfgB)["columns"]) == 5)
check("the team's role layouts reach Customize Home", BR.preset("Author", TP.roles(cfgB))["order"][:3] == ["mywork", "calendar", "tasks"])
w.home_page.customize({"role": "Author", "order": BR.preset("Author", TP.roles(cfgB))["order"], "hidden": BR.preset("Author", TP.roles(cfgB))["hidden"]})
check("an author on this PC gets the team's layout", w.home_page.shown == ["mywork", "calendar", "tasks"], w.home_page.shown)
check("markings and topics are added", TP.markings(cfgB) == ["CUI//SP-PROPIN", "Proprietary"] and TP.topics(cfgB) == ["Thermal", "Schedule", "Key personnel"])
check("a CUI marking of the team's own shows in the CUI color", BR.tone("CUI//SP-PROPIN") == "cui" and BR.marking("CUI//SP-PROPIN")[0] == "CUI//SP-PROPIN")
check("Settings says what is installed and what the team locked", "Sierra team" in tc.state.text() and "Company logos" in tc.state.text()
      and not tc.undo_btn.isHidden(), tc.state.text())
# ---- undo
tc.undo()
check("Undo puts the author list back", AL.load(cfgB).names() == ["Zed Quinn"], AL.load(cfgB).names())
check("Undo puts the logos back and lifts the lock", [Image.open(p).getpixel((5, 5)) for p in BR.logos(cfgB)] == [(30, 140, 60)]
      and not TP.locked(cfgB, "logos") and bc.add_logo(pic("b3.png", (9, 9, 9))))
check("Undo puts the design, banned words and goals back", len(MD.load_team(cfgB)["columns"]) == len(MD.default()["columns"])
      and "world-class" not in open(os.path.join(cfgB, "banned_words.csv")).read()
      and json.load(open(os.path.join(cfgB, "stage_goals.json")))["stages"] == {"Intake": ["My own goal"]})
check("Undo removes the team's lists the PC did not have", TP.roles(cfgB) == {} and TP.markings(cfgB) == [] and not TP.installed(cfgB))
# ---- a pack that is not sound
bad = os.path.join(tmp, "bad.skteam"); shutil.copy2(pack, bad)
with zipfile.ZipFile(pack) as zi, zipfile.ZipFile(bad, "w") as zo:
    for e in zi.infolist():
        b = zi.read(e.filename)
        zo.writestr(e.filename, b.replace(b"world-class", b"world-klass") if e.filename == "banned_words.csv" else b)
check("an altered pack is refused", tc.install(bad, confirm=True) is None and not TP.installed(cfgB))
extra = os.path.join(tmp, "extra.skteam"); shutil.copy2(pack, extra)
with zipfile.ZipFile(extra, "a") as z:
    z.writestr("run_me.cmd", "echo hi")
try:
    TP.read(extra); ok = False
except ValueError as e:
    ok = "Unexpected file" in str(e)
check("a pack with a file it should not hold is refused", ok)
w.close()
n = sum(checks)
print(f"QT TEAM PASS ({n}/{len(checks)})" if n == len(checks) else f"QT TEAM FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
