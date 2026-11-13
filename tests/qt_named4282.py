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
check("Template's tabs: Templates, From profiles, Effort Profiles, Template Studio", MW.TABS["templates"] == [("templates", "Templates"), ("tplprofiles", "From profiles"),
                                                                                                           ("profiles", "Effort Profiles"), ("studio", "Template Studio")])
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
check("Making templates is a Preview tool until it is turned on", pg.make() is None)
RA.set_preview(cfg, "template", True) if hasattr(RA, "set_preview") else None
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

# ---- Team defaults moved
w.go("team"); app.processEvents()
check("Team defaults is on the Team page", getattr(w.team_page, "team_card", None) is not None and w.team_page.team_card.isVisibleTo(w))
w.go("settings"); app.processEvents()
st = w.settings_page
names = [n for n, _c in st.SECTIONS]
check("... and not in Settings", "team_card" not in [c for _n, cs in st.SECTIONS for c in cs] and not st.team_card.isVisibleTo(w), names)
check("removed: off the list", pg.remove(t["id"], ask=False) and pg.t.rowCount() == 0)
w.close()
n = sum(checks)
print(f"QT NAMED 4282 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
