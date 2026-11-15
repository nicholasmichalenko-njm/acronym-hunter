"""4.28.2 offscreen: a template is its own named thing (answer 23); an effort picks one for each volume; Team defaults
is on the Team page (answer 12). The Template entry opens the templates you name; the ones the Effort Profiles make are
the next tab. Fictional (Osprey)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E
import namedtemplates as NT
import roleaccess as RA
import stylelib as SL
import templatelib as TL
import templatesetup as TS
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D, mainwin as MW
from skqt.pagetitles import TITLES

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); os.makedirs(ED)
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
app = QApplication([]); D.apply(app)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
check("Template's tabs: Templates, From profiles, Effort Profiles (4.29.1: Template Studio is Setup's)", MW.TABS["templates"] == [("templates", "Templates"), ("tplprofiles", "From profiles"),
                                                                                                           ("profiles", "Effort Profiles")])
check("the page's title and the role that has it", TITLES["templates"][0] == "Template" and "tplprofiles" in TITLES and RA.allowed("Production", "tplprofiles")
      and MW.GROUP_OF.get("tplprofiles") == "Templates" and "tplprofiles" in MW.MainWindow.NO_EFFORT)
w.rail_go("templates"); app.processEvents()
pg = w.named_page
check("the Template entry opens the templates you name, with no effort open", w.stack.currentWidget() is pg and w.ws is None)
check("empty: one way in", pg.empty.isVisibleTo(w) and not pg.t.isVisibleTo(w) and not pg.b_make.isEnabled())
check("one main button; five commands or fewer", pg.bar.main is pg.b_new and len(pg.bar.commands) <= 5)
w.go("tplprofiles"); app.processEvents()
check("From profiles is the list the Effort Profiles make", w.stack.currentWidget() is w.templates_page)
w.go("templates"); app.processEvents()
lib = TL.Library(cfg)
s1, _ = SL.new_style(lib, "Body Text", "paragraph", {"font": "Arial", "size": 11})
k = SL.new_set(lib, "RFP volume"); SL.add_to_set(lib, k["id"], [s1["id"]])
t = pg.new("Page-limited RFP, Volume I")
check("New template... adds a row and selects it", t and pg.t.rowCount() == 1 and pg.current() == t["id"] and pg.t.isVisibleTo(w) and not pg.empty.isVisibleTo(w))
check("... not made yet, and it says what goes in", pg.t.item(0, 2).text() == NT.NEW and pg.t.item(0, 1).text().startswith("Nothing picked yet"))
check("the same name is refused", pg.new("page-limited rfp, volume i") is None and pg.t.rowCount() == 1)
dlg = pg.goes_in()
check("What goes in... opens the picker on this template", dlg is not None and dlg.goes_in.editable and dlg.windowTitle() == "What goes in: Page-limited RFP, Volume I")
dlg.goes_in.add_set(k["id"]); app.processEvents()
check("a style set picked is kept at once and shown on the row", NT.get(cfg, t["id"])["sets"]["style_sets"] == [k["id"]]
      and pg.t.item(0, 1).text() == "Styles: RFP volume", pg.t.item(0, 1).text())
dlg.close()
check("4.29.1: making templates is on for everyone, with nothing to turn on", RA.preview_on(cfg, "template"))
pg._allowed = lambda: True
job = pg.make()
check("Make it writes the .dotx and the row says Ready", job is not None and os.path.isfile(job.copy) and pg.t.item(0, 2).text() == NT.READY
      and "version 1" in pg.t.item(0, 3).text(), pg.t.item(0, 3).text())
m = pg.row_menu(run=False)
check("a right-click holds the rest", [a.text() for a in m.actions() if a.text()] == ["What goes in...", "Make it", "Open in Word", "Rename...", "Remove"])
check("Rename", pg.rename(name="Page-limited RFP Volume") and pg.t.item(0, 0).text() == "Page-limited RFP Volume")

# ---- an effort picks one for each volume
w.open_effort("Osprey"); app.processEvents()
w.go("setups"); app.processEvents()
sp = w.setups_page
check("Setup's More has Templates for the volumes...", sp.bar.action("Templates for the volumes...") is not None)
from skqt.namedtplpage import volume_templates
d0 = volume_templates(sp)
check("no volumes yet: it says to add them first", d0.t.rowCount() == 0 and "add the volumes" in d0.note.text(), d0.note.text())
sp.use_headings("Volume I Technical\n  1 Ground Segment\n    1.1 Antenna Sites\n  2 Mission Operations"); app.processEvents()
sp.builder.add_volume("Management"); app.processEvents()
vols = sp.volume_names()
d1 = volume_templates(sp)
check("each volume has a row, on the effort's own formatting", len(vols) == 2 and d1.t.rowCount() == 2 and all(b.currentText() == d1.OWN for b in d1.boxes.values()), vols)
got = d1.pick(vols[0], t["id"])
M = sp._M()
fv = TS.for_volume(M, vols[0], w.effort_path or "")
check("a pick is kept on the effort as that volume's template file", got and got["name"] == "Page-limited RFP Volume" and fv is not None
      and os.path.basename(fv[0]) == os.path.basename(job.copy) and NT.picks(w.ws)[vols[0]]["id"] == t["id"], fv)
check("... the other volume keeps the effort's own", TS.for_volume(M, vols[1], w.effort_path or "") is None and d1.boxes[vols[1]].currentText() == d1.OWN)
check("... and the box shows it", d1.boxes[vols[0]].currentData() == t["id"])
import effortfolders as EF
check("the template's file is kept with the effort", os.path.isfile(os.path.join(EF.root(w.effort_path), "Templates", os.path.basename(job.copy))))
pg.make(t["id"])
d2 = volume_templates(sp)
check("made again since: the dialog says a newer version waits", "newer version (2)" in d2.note.text(), d2.note.text())
d2.pick(vols[0], "")
check("back to the effort's own formatting", TS.for_volume(sp._M(), vols[0], w.effort_path or "") is None and NT.picks(w.ws) == {})
# 4.41.0: the effort type names its templates
import efforttemplates as ET, prodrules as PRL
from skqt import efforttplview as ETV
d3 = volume_templates(sp)
check("4.41.0: an effort with no effort type is offered nothing", not d3.b_type.isVisibleTo(d3) and d3.b_type.isHidden())
pid = PRL.effort_type_of(PRL.load(cfg), "rfp_limited")["profiles"][0]
td = ETV.templates(w, cfg, "rfp_limited", run=False)
check("Effort types... > Templates...: a row for each profile, on no template", td.t.rowCount() == 1 and td.boxes[pid].currentText() == ETV.NONE
      and td.windowTitle() == "Templates for Page-limited RFP response", td.windowTitle())
check("... picking one names it for the effort type", td.pick(pid, t["id"]) and ET.of(PRL.load(cfg), "rfp_limited") == {pid: t["id"]}
      and td.boxes[pid].currentData() == t["id"])
w.ws.set("prod_std", {"effort_type": "rfp_limited", "type": pid})
d4 = volume_templates(sp)
check("the volumes with no template are offered the effort type's", not d4.b_type.isHidden() and "The effort type names a template for" in d4.note.text()
      and "Page-limited RFP Volume" in d4.note.text(), d4.note.text())
done = ETV.use_type(d4)
check("Use the effort type's templates picks it for each of them", len(done) == 2 and all(NT.picks(w.ws)[v]["id"] == t["id"] for v in vols)
      and d4.b_type.isHidden() and all(b.currentData() == t["id"] for b in d4.boxes.values()), done)
d4.pick(vols[1], "")
check("one volume can still go its own way", vols[1] not in NT.picks(w.ws) and NT.picks(w.ws)[vols[0]]["id"] == t["id"])
w.go("home"); app.processEvents()
f = w.home_page.start
f.etype.setCurrentIndex(f.etype.findData("rfp_limited")); app.processEvents()
check("the start form says what the effort type starts with", f.brings.text().startswith("It starts with: ") and "Page-limited RFP Volume" in f.brings.text()
      and not f.brings.isHidden(), f.brings.text())
f.etype.setCurrentIndex(f.etype.findData("rfp")); app.processEvents()
check("... and how to set it for a type that names none", f.brings.text().startswith("This effort type names no templates yet."), f.brings.text())
f.etype.setCurrentIndex(0); app.processEvents()
check("... and nothing with no effort type", f.brings.isHidden())
from skqt.efforttypes import manage
md = manage(f, cfg, run=False)
check("Effort types... has Templates...", "templates" in md.btns and md.btns["templates"].text() == "Templates..." and md.templates(run=False) is not None)

# ---- Team defaults moved
w.go("team"); app.processEvents()
check("Team defaults is on the Team page", getattr(w.team_page, "team_card", None) is not None and w.team_page.team_card.isVisibleTo(w))
w.go("settings"); app.processEvents()
st = w.settings_page
names = [n for n, _c in st.SECTIONS]
check("... and not in Settings", "team_card" not in [c for _n, cs in st.SECTIONS for c in cs] and not st.team_card.isVisibleTo(w), names)
# 4.39.0: the selected template, seen whole
w.close_effort() if w.ws is not None else None
w.go("templates"); app.processEvents(); pg.fill(); pg.select(t["id"]); app.processEvents()
tp = pg.tp_table
check("4.39.0: under the list, the selected template's five components", tp.isVisibleTo(w) and tp.rowCount() == 5
      and [tp.item(r, 0).text() for r in range(5)] == ["Styles", "Quick Parts", "Page layout", "Numbering", "Starting pages"]
      and pg.tp_title.text() == f"{NT.get(cfg, t['id'])['name']} is made of", [tp.item(r, 0).text() for r in range(tp.rowCount())])
check("... where each comes from and what it holds", tp.item(0, 1).text() == "Style set: RFP volume" and tp.item(0, 2).text() == "1 style"
      and tp.item(2, 1).text() == "From the standards, the same for every template" and tp.item(2, 2).text().startswith("Letter, 1 in margins"),
      [tp.item(r, 1).text() for r in range(5)])
check("... and one line: ready to make", pg.tp_line.text() == "Ready to make. The five components fit each other.", pg.tp_line.text())
from skqt import tplparts as TPV
check("double-click a component: the page that changes it opens", TPV.open_part(pg, 0) == "styles" and w.stack.currentWidget() is w.styles_page)
w.go("templates"); app.processEvents()
check("removed: off the list", pg.remove(t["id"], ask=False) and pg.t.rowCount() == 0)
check("with no template the card is gone", not pg.tp_table.isVisibleTo(w) and not pg.tp_line.isVisibleTo(w))
w.close()
n = sum(checks)
print(f"QT NAMED 4282 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
