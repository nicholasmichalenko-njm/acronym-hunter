"""3.2.0 writing support, offscreen: Effort Home's Win themes card (+ Theme..., change, Check the drafts against the Word
files in the Volumes folder); Deliver > Storyboards (pick a section, write it, it saves, the status shows in the list,
Export the volume makes a Word file). 3.14.2: there is no sample effort."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortrec as RR, themes as TH, storyboard as SB, docxw, effortfolders as EF, branding as BR
import office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def wait(cond, secs=90):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("home"); app.processEvents()
# 3.14.2: no sample effort in the program; the test makes its own effort (fictional test data)
check("there is no sample effort button", not hasattr(w.home_page.start, "sample_btn") and not hasattr(w.home_page.start, "try_sample"))
import datahome, shutil as _sh
name = "Writing Test"
made = w.settings_page.new_effort({"name": name, "path": EF.new_list_path(datahome.efforts_dir(A.DATA_DIR), name, {})[0]})
check("an effort to write in", made == name and w.effort_name == name)
w.ws.set("outline_text", "Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management\nVolume II Management\n2.1 Schedule\n2.2 Staffing")
rec = RR.Record(w.ws.root)
TH.add(rec, "Flight-proven thermal design lowers risk to orbit",
       "Our design has flown on four missions with margin to spare, so the Government carries less schedule risk.",
       discriminator="The only design with on-orbit thermal data at this power class",
       proof=["Four missions, zero thermal anomalies"], sections=["1.1 Thermal Design", "1.2 Risk Management"], who="test")
cust = EF.folder(w.effort_path, "customer"); os.makedirs(cust, exist_ok=True)
rfp = os.path.join(cust, "Section_L_print.pdf")
_sh.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf"), rfp)
w.read_page.read([rfp], w.out_path("compliance_matrix"), identities="suggested", start="typed")
check("... its RFP read into Review", wait(lambda: w.review is not None and len(w.review.M.items) > 10), len(w.review.M.items) if w.review else 0)
labels = w.review.labels()
# themes card (3.61.0: win themes are set aside; shown here so their code stays tested)
from skqt import modes
modes.save(show_set_aside=True)
w.go("home"); app.processEvents()
hp = w.home_page
hp.apply_layout(); hp.refresh(); app.processEvents()
check("Overview shows the win themes under the header (3.12.0)", hp.strips["themes"].isVisibleTo(w) and len(hp.themes_now) == 1
      and "Win themes   1" in hp.strips["themes"].title_label.text())
tid = hp.theme_dialog(None, {"title": "Program office close to the customer", "kind": "Discriminator", "statement": "",
                             "discriminator": "", "proof": [], "sections": [labels[-1]], "hot": "", "words": ["Colorado"]})
check("+ Theme... adds one", tid in hp.themes_now and TH.get(RR.Record(w.ws.root), tid)["kind"] == "Discriminator")
vdir = EF.folder(w.effort_path, "volumes")
d = docxw.Doc(); d.heading(labels[1], 2); d.para("Our flight-proven design has on-orbit data at this power class.")
d.heading(labels[-1], 2); d.para("Staffing comes later.")
d.save(os.path.join(vdir, "Volume I Technical.docx"))
check("the drafts are the Word files in the Volumes folder", [n for n, _p in hp.theme_drafts()] == ["Volume I Technical"], hp.theme_drafts())
res = hp.check_themes()
first = TH.items(RR.Record(w.ws.root))[0]["id"]
check("Check the drafts: where each theme is said, and where a linked section never says it", res[first]["found"].get("Volume I Technical")
      and res[tid]["missing"] == [labels[-1]], {k: (v["found"], v["missing"]) for k, v in res.items()})
# storyboards
check("Storyboards is in Plan with Setup (3.53.0 spaces; 3.74.0 the Structure Builder in Setup)", __import__("skqt.mainwin", fromlist=["x"]).RAIL_OF["storyboards"] == "setups")
w.go("storyboards"); app.processEvents()
sp = w.storyboards_page
check("the sections of the volume, each with its status", sp.tree.topLevelItemCount() >= 1 and sp.label in labels, sp.label)
sp.vol.setCurrentIndex(0); app.processEvents()
target = labels[1]
it = sp.tree.findItems(target, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MatchRecursive | __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MatchExactly, 0)[0]
sp.tree.setCurrentItem(it); app.processEvents()
check("picking a section shows what the structure says and the linked themes ticked", sp.label == target and target in sp.title.text()
      and sp.theme_checks[first].isChecked(), sp.title.text())
sp.message.setText("Least risk to orbit"); sp.approach.setPlainText("Step one.\nStep two.")
sp.add_feature(); sp.feat.item(0, 0).setText("Loop heat pipes"); sp.feat.item(0, 1).setText("Margin"); sp.feat.item(0, 2).setText("Test data")
sp.status.setCurrentText("Drafting")
sp.save()
sb = SB.get(RR.Record(w.ws.root), target)
check("what the author writes saves into the effort record", sb["message"] == "Least risk to orbit" and sb["features"][0]["feature"] == "Loop heat pipes"
      and sb["status"] == "Drafting" and first in sb["themes"])
check("... and the status shows in the list", it.text(1) == "Drafting")
w.go("home"); w.go("storyboards"); app.processEvents()
check("coming back shows it again", sp.message.text() == "Least risk to orbit" or sp.label != target)
out = sp.export(True, os.path.join(tmp, "vol.docx"))
x = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
check("Export the volume: one Word file, a page per section", x.count("Storyboard: ") == len(sp.labels()) and "Loop heat pipes" in x, x.count("Storyboard: "))
check("the export has a name in Folders and file names", "Storyboard" in w.out_path("storyboards", Doc="Volume_I"))
w.close()
n = sum(checks)
print(f"QT WRITING {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
modes.save(show_set_aside=False)   # 3.61.0: the settings file is shared by the tests on the PC
sys.exit(0 if n == len(checks) else 1)
