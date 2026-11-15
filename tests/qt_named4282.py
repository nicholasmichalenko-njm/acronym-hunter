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
check("the page's title and the role that has it", TITLES["templates"][0] == "Templates" and "tplprofiles" in TITLES and RA.allowed("Production", "tplprofiles")
      and MW.GROUP_OF.get("tplprofiles") == "Templates" and "tplprofiles" in MW.MainWindow.NO_EFFORT)
w.rail_go("templates"); app.processEvents()
pg = w.named_page
check("the Template entry opens the templates you name, with no effort open", w.stack.currentWidget() is pg and w.ws is None)
check("empty: one way in", pg.empty.isVisibleTo(w) and not pg.area.isVisibleTo(w) and pg.cards == {})
check("one main button; five commands or fewer", pg.bar.main is pg.b_new and len(pg.bar.commands) <= 5)
w.go("tplprofiles"); app.processEvents()
check("From profiles is the list the Effort Profiles make", w.stack.currentWidget() is w.templates_page)
w.go("templates"); app.processEvents()
lib = TL.Library(cfg)
s1, _ = SL.new_style(lib, "Body Text", "paragraph", {"font": "Arial", "size": 11})
k = SL.new_set(lib, "RFP volume"); SL.add_to_set(lib, k["id"], [s1["id"]])
bd = pg.new()
check("New template... opens the builder with nothing picked; no template exists yet", bd is not None and bd.tid is None and bd.windowTitle() == "New template"
      and NT.every(cfg) == [] and bd.tiles["style_sets"].pick.text().startswith("None"))
check("... a template needs a name", bd.save() is None and "name" in bd.said.text() and NT.every(cfg) == [])
bd.name.setText("Page-limited RFP, Volume I")
bd.toggle_style_set(k["id"]); app.processEvents()
check("a style set picked shows on its tile, and nothing is kept until Save", bd.tiles["style_sets"].pick.text() == "RFP volume"
      and bd.tiles["style_sets"].holds.text() == "1 style" and NT.every(cfg) == [])
tid = bd.save()
t = NT.get(cfg, tid)
check("Save makes the template, adds its card and selects it", t and len(pg.cards) == 1 and pg.current() == t["id"] and pg.area.isVisibleTo(w) and not pg.empty.isVisibleTo(w)
      and t["sets"]["style_sets"] == [k["id"]])
card = pg.cards[t["id"]]
check("... not made yet, and the card says what it is made of", card.state.text().startswith(NT.NEW) and card.parts[0].text() == "Styles: RFP volume", card.state.text())
b2 = pg.new(); b2.name.setText("page-limited rfp, volume i")
check("the same name is refused", b2.save() is None and len(pg.cards) == 1)
dlg = pg.open_builder()
check("a double-click opens the builder on this template", dlg is not None and dlg.tid == t["id"] and dlg.windowTitle() == "Template: Page-limited RFP, Volume I"
      and dlg.tiles["style_sets"].pick.text() == "RFP volume")
dlg.close()
check("4.29.1: making templates is on for everyone, with nothing to turn on", RA.preview_on(cfg, "template"))
pg._allowed = lambda: True
job = pg.make()
card = pg.cards[t["id"]]
check("Export writes the .dotx and the card says Ready", job is not None and os.path.isfile(job.copy) and card.state.text().startswith(NT.READY)
      and "version 1" in card.state.text(), card.state.text())
check("... and that the file holds what was picked", card.proof.text().startswith("The file holds what was picked") and not card.proof.isHidden(), card.proof.text())
m = pg.row_menu(run=False)
check("a right-click holds the rest", [a.text() for a in m.actions() if a.text()] == ["Open in the builder", "Export", "Open in Word", "Duplicate", "Rename...", "Archive...", "Remove"])
check("Rename", pg.rename(name="Page-limited RFP Volume") and pg.cards[t["id"]].name.text() == "Page-limited RFP Volume")

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
# 4.43.0: the gallery
w.close_effort() if w.ws is not None else None
w.go("templates"); app.processEvents(); pg.fill(); pg.select(t["id"]); app.processEvents()
card = pg.cards[t["id"]]
check("4.43.0: the card names the five components", [p.text().split(":")[0] for p in card.parts] == ["Styles", "Quick Parts", "Page layout", "Numbering", "Starting pages"]
      and card.parts[2].text() == "Page layout: From the standards, the same for every template", [p.text() for p in card.parts])
d = pg.duplicate(t["id"])
check("Duplicate: Copy of ..., the same picks, not made, selected", d and d["name"] == "Copy of Page-limited RFP Volume" and d["sets"] == NT.get(cfg, t["id"])["sets"]
      and not d.get("made") and len(pg.cards) == 2 and pg.current() == d["id"], d)
check("Archive: off the gallery, and the Archived view appears", pg.archive(d["id"]) and len(pg.cards) == 1 and not pg.b_arch.isHidden() and pg.b_arch.text() == "Archived (1)"
      and [x["name"] for x in NT.shown(cfg)] == ["Page-limited RFP Volume"])
pg.show_archived(True)
check("the Archived view holds it, with Restore", list(pg.cards) == [d["id"]] and [a.text() for a in pg.row_menu(run=False).actions() if a.text()] == ["Restore", "Remove"]
      and not pg.cards[d["id"]].b_export.isEnabled())
check("Restore: back in the gallery, and the Archived view goes", pg.archive(d["id"], on=False) and len(pg.cards) == 2 and pg.b_arch.isHidden() and not pg.archived)
check("removed: off the gallery", pg.remove(d["id"], ask=False) and pg.remove(t["id"], ask=False) and pg.cards == {})
check("with no template: one way in again", pg.empty.isVisibleTo(w) and not pg.area.isVisibleTo(w))
w.close()
n = sum(checks)
print(f"QT NAMED 4282 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
