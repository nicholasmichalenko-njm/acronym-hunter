"""3.2.0 writing support, offscreen: Effort Home's Win themes card (+ Theme..., change, Check the drafts against the Word
files in the Volumes folder); Deliver > Storyboards (pick a section, write it, it saves, the status shows in the list,
Export the volume makes a Word file); Try the sample effort makes the fictional Kestrel Thermal effort and reads its RFP."""
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
from skqt import theme
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
check("Try the sample effort is on the start form", w.home_page.start.sample_btn.isVisibleTo(w))
name = w.home_page.start.try_sample()
check("it makes the fictional Kestrel Thermal effort and opens it", name == "Kestrel Thermal (sample)" and w.effort_name == name
      and (w.efforts.get(name) or {}).get("sample"))
check("... and reads its RFP into Review", wait(lambda: w.review is not None and len(w.review.M.items) > 10), len(w.review.M.items) if w.review else 0)
rec = RR.Record(w.ws.root)
check("... with a structure, a due date, a proposal manager, tasks, a theme and deliverables", [o.get("title") for o in w.review.M.outline][:2]
      and rec.data["due"] and BR.identity(rec)["pm"] == "A. Rivera" and len(rec.tasks()) == 3 and len(TH.items(rec)) == 1
      and len(rec.data.get("deliverables", [])) == 2, [o for o in w.review.M.outline][:2])
check("... its people show only in the sample", "J. Garcia" in w.authors.for_effort(name) and "J. Garcia" not in w.authors.for_effort("Other"))
check("a second sample gets its own name", __import__("skqt.sample", fromlist=["x"]).free_name(w.efforts) == "Kestrel Thermal (sample 2)")
labels = w.review.labels()
# themes card
w.go("home"); app.processEvents()
hp = w.home_page
check("Effort Home shows the Win themes card", hp.themes_card.isVisibleTo(w) and len(hp.themes_now) == 1)
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
check("Storyboards sits in Deliver, after Response Setup", [k for g, items in RAIL if g == "Deliver" for k, _l in items] == ["matrix", "setup", "storyboards", "postsub"])
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
sys.exit(0 if n == len(checks) else 1)
