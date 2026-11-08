"""3.82.0 the review form's answers, offscreen: Move stage... is the Effort Dashboard's main button; the stage table is
plain rows with the selected stage edited beside it; an effort type hides and shows captures as well as decisions
(Settings lists them, Review's capture bar follows); Scan files... on Acronyms asks the Library folder for each new
file; Draft Status's Drift report... checks every draft at once. Fictional content (Heron, the Kestrel set)."""
import datetime, json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, docversions as DV, effortrec as RR, reviewitems as RI
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import wordlab as WL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


# ---- the rules first: an RFI hides Evaluation factor; a saved choice for an effort type keeps capture keys
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
data = RI.load(cfg)
check("an RFI hides Evaluation factor, and other types show it", not RI.capture_on(data, "factor", "rfi")
      and RI.capture_on(data, "factor", "") and RI.capture_on(data, "contact", "rfi"))
data["captures"]["unit"]["shown"] = False
data["show"]["rfi"] = ["I", "unit"]; data["hide"]["rfi"] = ["L", "M", "C", "factor", "hot"]
RI.save(cfg, data)
d2 = RI.load(cfg)
check("... an effort type can show a capture hidden for the rest, and hide another", RI.capture_on(d2, "unit", "rfi")
      and not RI.capture_on(d2, "unit", "") and not RI.capture_on(d2, "hot", "rfi") and d2["hide"]["rfi"][-1] == "hot", d2["hide"])
check("... and the decisions follow the type as before", [x["code"] for x in RI.decisions_for(d2, "rfi")] == ["I", "ctx", "cust", "ignore"])

# ---- an effort
TOP = os.path.join(tmp, "Heron"); os.makedirs(TOP)
CD = os.path.join(TOP, "Customer Documents"); os.makedirs(CD)
LIST = os.path.join(TOP, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron"); w.go("home"); app.processEvents()
hp = w.home_page
rec = RR.Record(w.ws.root)
check("Move to the next stage is the dashboard's main button, at the right of the bar", hp.bar.main is hp.move_btn
      and hp.move_btn.text() == f"Move to {rec.stages[1]['name']}...", hp.move_btn.text())
check("... and the Stage card no longer holds it", hp.move_btn.parent() is hp.bar
      and not any(b.text().startswith("Move") for b in hp.track.findChildren(QPushButton)))

# ---- the stage table: one row at a time
w.go("record"); app.processEvents()
rp = w.record_page
t = rp.stage_table
check("the stage table is plain rows, no picker on any row", t.rowCount() == len(rec.stages)
      and all(t.cellWidget(i, c) is None for i in range(t.rowCount()) for c in range(5)))
rp.set_stage(2, start=("2030-03-02", "9:00 AM"), end=("2030-03-06", ""), gate="hard", name="Pink team")
check("... the panel changes the selected row, and the row says it", t.item(2, 0).text() == "Pink team"
      and t.item(2, 1).text() == "Mar 2, 2030, 9:00 AM" and t.item(2, 3).text() == RR.GATES["hard"], [t.item(2, c).text() for c in range(4)])
t.setCurrentCell(0, 0); app.processEvents()
check("... picking another stage shows it in the panel", rp.stage_panel.name.text() == rec.stages[0]["name"]
      and rp.stage_panel.start.value() == ("", ""))
t.setCurrentCell(2, 0); app.processEvents()
check("... and back again, with what was set", rp.stage_panel.start.value() == ("2030-03-02", "09:00")
      and rp.stage_panel.gate.currentData() == "hard")
check("Save stages keeps what the panel set", rp.save_stages() and RR.Record(w.ws.root).stages[2]["name"] == "Pink team"
      and RR.Record(w.ws.root).stages[2]["planned_time"] == "09:00" and RR.Record(w.ws.root).gate_of(RR.Record(w.ws.root).stages[2]) == "hard")
rp.stage_table.setCurrentCell(2, 0); rp.move_row(-1)
check("Earlier moves the row with its values", rp.stage_table.item(1, 0).text() == "Pink team" and rp.stage_panel.name.text() == "Pink team"
      and rp._stage_values(1)[2] == ("2030-03-02", "09:00"))
rp.refresh()

# ---- Review's capture bar follows the effort's type
ap = w.assign_page
ap.items_cfg = RI.load(cfg)
w.ws.set("prod_std", {"effort_type": ""}); ap.build_captures()
check("a plain effort: Evaluation factor is offered", "factor" in ap.more_actions)
w.ws.set("prod_std", {"effort_type": "rfi"}); ap.build_captures()
check("an RFI: Evaluation factor and Hot button are not; Unit of measurement is", "factor" not in ap.more_actions
      and "hot" not in ap.more_actions and "unit" in ap.more_actions, list(ap.more_actions))
w.ws.set("prod_std", {"effort_type": ""})
from skqt.reviewitemsview import ReviewItemsDialog
dlg = ReviewItemsDialog(w, w)
dlg.et.setCurrentIndex(dlg.et.findData("rfi")); app.processEvents()
names = [dlg.et_hide.item(i).text() for i in range(dlg.et_hide.count())]
check("Settings: an effort type's hides list names the captures too", "Capture: Evaluation factor" in names, names[-5:])
dlg.close()

# ---- Scan files...: the Library folder for each new file
from skqt import acrbridge as AB
w.go("acronyms"); app.processEvents()
acr = w.acronym_page
pic = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Large_Diagram.png")
doc = os.path.join(tmp, "Heron Briefing.docx"); shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), doc)
lib = DV.Library(w.ws.p("documents")).load()
fd = AB.FolderDialog(acr, lib, [pic, doc])
check("the folder offered at first: Graphics for a picture, Our Documents for the rest", fd.choice() == {pic: "graphics", doc: "ours"},
      fd.choice())
fd.boxes[doc].setCurrentIndex(fd.boxes[doc].findData("bidders"))
check("... and each can be changed", fd.choice()[doc] == "bidders")
n = AB.add_first(acr, [pic, doc], answer=fd.choice())
lib = DV.Library(w.ws.p("documents")).load()
cats = {d["name"]: d["category"] for d in lib.all}
check("the files go where they were sent", n == 2 and any(v == "graphics" and k.startswith("Kestrel Large") for k, v in cats.items())
      and any(v == "bidders" and k.startswith("Heron Briefing") for k, v in cats.items()), cats)
check("... and Scan without adding adds none", AB.add_first(acr, [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Interface_Diagram.svg")],
                                                         answer=False) == 0)

# ---- Draft Status: the drift report over every draft
d1 = os.path.join(TOP, "Heron Volume I.docx"); d2_ = os.path.join(TOP, "Heron Volume II.docx")
for d in (d1, d2_):
    shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), d)
for d, when in ((d1, datetime.datetime(2026, 11, 6, 21, 30)), (d2_, datetime.datetime(2026, 11, 7, 8, 15))):
    paras = WL.docx_paragraphs(d)
    s = paras[6].index("w/o")
    WL.to_copy(d, [{"para": 6, "start": s, "end": s + 3, "hit": "w/o", "fix": "without", "on": True, "rule": "plain words", "why": ""}], when=when)
w.go("drafts"); app.processEvents()
ds = w.drafts_page
ds.pick(d1); ds.pick(d2_)
dlg = ds.drift(run=False)
check("Drift report... on Draft Status: every draft's copies at once", dlg is not None and dlg.table.rowCount() == 2
      and {os.path.basename(r["draft"]) for r in dlg.reports} == {"Heron Volume I.docx", "Heron Volume II.docx"}, dlg and dlg.reports)
dlg.table.setCurrentCell(1, 0); app.processEvents()
check("... the selected copy's changes show below", dlg.changes.rowCount() == 1 and dlg.changes.item(0, 3).text() == "Still to take")
out = dlg.export(os.path.join(tmp, "drift.xlsx"))
check("... and it exports to Excel", out and os.path.isfile(out))
w.close()
n = sum(checks)
print(f"QT ANSWERS 382 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
