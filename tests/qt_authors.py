"""2.77.0 the author list in Qt, offscreen: the first start seeds it from the efforts' teams (nothing disappears);
Settings > Author list with no effort says to create or select one first; names typed or imported (only new names
are added, names already there keep their efforts); Joe G. set to Effort A shows in Effort A's pickers and not in
Effort B's; All efforts; the Assign author picker, a section's lead and contributors, a task's owner and a
deliverable's owner offer only the list's names for the open effort and are never typed; a name already assigned
that is not on the list stays, marked; with no effort open a picker says to select or create one first; export."""
import os, sys, tempfile, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.LOG_DIR = os.path.join(tmp, "logs")
import authorlist as AL
import compliance as C
import effort as E
import effortrec as RR
import setupdoc as SD
import workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox, QComboBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D
from skqt import people as PP
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


# ---------------------------------------------------------------- no effort yet
cfg0 = os.path.join(tmp, "config0"); os.makedirs(cfg0)
app = QApplication([]); D.apply(app)
w0 = MainWindow(app, cfg0, A.APP_VERSION); w0.show()
card0 = w0.settings_page.authors
w0.go("settings"); w0.settings_page.refresh(); app.processEvents()
check("no effort yet: Settings says to create or select an effort first", card0.banner.isVisible()
      and "Create or select an effort first" in card0.banner.text(), card0.banner.text())
res = card0.add_names("Joe G.\nM. Chen")
check("names can still be added: they show in all efforts", res["added"] == ["Joe G.", "M. Chen"] and w0.authors.find("Joe G.")["efforts"] == AL.ALL)
check("choosing efforts with none: create or select an effort first", card0.choose_efforts(["Joe G."]) is None
      and "Create or select an effort first" in w0.statusBar().currentMessage())
check("a picker with no effort open: select or create an effort first", PP.pick_names(w0, [], answer=["Joe G."]) is None
      and w0.statusBar().currentMessage() == PP.NO_EFFORT and w0.people() == [])
w0.close()

# ---------------------------------------------------------------- two efforts with teams from before 2.77.0
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
reg = E.Registry(os.path.join(cfg, "efforts.json"))
for name, team in (("Effort A", ["A. Lee", "K. Park"]), ("Effort B", ["K. Park", "R. Diaz"])):
    d = os.path.join(tmp, name); os.makedirs(os.path.join(d, "Customer documents"))
    lp = os.path.join(d, f"{name}_Effort_List.xlsx")
    L = E.EffortList(lp, name); L.pending = True; L.save()
    reg.put(name, path=lp, customer_dir=os.path.join(d, "Customer documents"))
    r = RR.Record(W.data_dir_for(lp)); os.makedirs(r.folder, exist_ok=True); r.set_team([(n, "") for n in team])
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("first start: the list starts from the efforts' teams", sorted(w.authors.names()) == ["A. Lee", "K. Park", "R. Diaz"]
      and w.authors.find("K. Park")["efforts"] == ["Effort A", "Effort B"] and os.path.isfile(os.path.join(cfg, AL.FILE)))
w.open_effort("Effort A")
sp = w.settings_page; card = sp.authors
w.go("settings"); sp.refresh(); app.processEvents()
check("the card lists every name and says how many show here", card.table.rowCount() == 3 and "2 show in Effort A" in card.info.text()
      and not card.banner.isVisible(), card.info.text())
card.add_names("Joe G.", efforts=["Effort A"])
check("Joe G. on Effort A only: in A's pickers", "Joe G." in w.people())
w.open_effort("Effort B")
check("and not in Effort B's", "Joe G." not in w.people() and w.people() == ["K. Park", "R. Diaz"])
txt = os.path.join(tmp, "update.txt"); open(txt, "w").write("Joe G.\nS. Patel\nT. Nguyen\n")
res = card.import_list(txt, efforts=AL.ALL)
check("an updated list: only new names added; Joe G. keeps Effort A only", res["added"] == ["S. Patel", "T. Nguyen"] and res["kept"] == ["Joe G."]
      and w.authors.find("Joe G.")["efforts"] == ["Effort A"] and "Imported: 2 new name(s) added; 1 already on the list" in w.statusBar().currentMessage())
check("All efforts: S. Patel shows in both", "S. Patel" in w.people() and "S. Patel" in w.authors.for_effort("Effort A"))
card.select(["T. Nguyen"])
check("Not in this effort (a name in all efforts stays in the others)", card.this_effort(False, ["T. Nguyen"]) == 1
      and "T. Nguyen" not in w.people() and "T. Nguyen" in w.authors.for_effort("Effort A"))
check("Shows in...: set the efforts for a name", card.choose_efforts(["R. Diaz"], answer=["Effort A", "Effort B"]) == ["Effort A", "Effort B"]
      and "R. Diaz" in w.authors.for_effort("Effort A"))
ex = os.path.join(tmp, "Author list.xlsx")
check("export the list for the rest of the team", card.export(ex) == len(w.authors.people) and len(AL.read_file(ex)) == len(w.authors.people))
check("rename and remove", card.rename("S. Patel", "Sam Patel") and card.remove(["Sam Patel"], answer="yes") == 1)

# ---------------------------------------------------------------- the pickers offer only the list
w.open_effort("Effort A")
CDIR = os.path.join(tmp, "Effort A", "Customer documents")
M = C.Matrix(os.path.join(tmp, "Effort A", "Matrix.xlsx"), "Effort A")
M.items = C.extract([("Section L.docx", [("Page 1", "L.4 Technical. The Offeror shall describe the thermal design. "
                                                    "The Offeror shall provide a schedule.")])])
M.outline = C.parse_outline("1.1 Technical Approach\n1.2 Schedule")
M.save()
w.ws.set("compliance_path", M.path)
w.open_effort("Effort A")
pg = w.assign_page
it = next(x for x in w.review.M.items if "thermal" in x["text"])
w.review.req([it], "1.1 Technical Approach"); pg.load(); pg.select(it["id"]); app.processEvents()
names_a = w.people()
got = pg.authors.choose(answer=["Joe G.", "R. Diaz", "Typed Stranger"])
check("Assign: authors picked from the list for this effort, never typed", got == ["Joe G.", "R. Diaz"] and it["owner"] == "Joe G., R. Diaz"
      and not hasattr(pg.authors, "setText") and pg.authors.text() == "Joe G., R. Diaz", it.get("owner"))
it["owner"] = "Old Name"; pg.select(it["id"]); app.processEvents()
check("an author already assigned who is not on the list stays, marked", "Old Name" + PP.OFF_LIST in pg.authors.lbl.text(), pg.authors.lbl.text())
d = pg.people_dialog()
lab, lead, contrib = d._api["rows"][0]
items = [lead.itemText(i) for i in range(lead.count())]
check("a section's lead: a drop-down of the list's names for this effort, not typed", not lead.isEditable() and items[1:] == names_a, items)
lead.setCurrentIndex(items.index("K. Park")); contrib.choose(answer=["A. Lee"]); d._api["save"]()
sp_ = SD.section_people(w.review.M, "1.1 Technical Approach")
check("lead and contributors saved", sp_.get("lead") == "K. Park" and sp_.get("with") == "A. Lee", sp_)
hp = w.home_page
w.go("home"); app.processEvents()
owner = hp.task_dialog(run=False).api["owner"]
check("a task's owner: the list's names for this effort, not typed", owner is not None and not owner.isEditable()
      and [owner.itemText(i) for i in range(1, owner.count())] == names_a)
cb = PP.name_combo(w, "Gone Person")
check("a single pick keeps a current name that is not on the list, marked", cb.currentData() == "Gone Person" and cb.currentText().endswith(PP.OFF_LIST))
check("an empty effort's picker points to the author list", (w.authors.set_efforts(w.authors.names(), ["Effort B"]) or True)
      and PP.pick_names(w, [], answer=[]) is None and "No names show in Effort A yet" in w.statusBar().currentMessage())
w.close()
n = sum(checks)
print(f"QT AUTHORS PASS ({n}/{len(checks)})" if n == len(checks) else f"QT AUTHORS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
