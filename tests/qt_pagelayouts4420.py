"""4.42.0 offscreen (ST29, way A): Template > More > Page layouts and numbering... keeps the named page layouts and
numbering; What goes in picks one of each; the component rows name them and open the window; Templates for the volumes
says when a volume's template and the volume's standards differ. Fictional (Osprey)."""
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
import pagelayouts as PGL
app = QApplication([]); D.apply(app)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("templates"); app.processEvents()
pg = w.named_page
check("More has Page layouts and numbering...; the bar still holds five or fewer", pg.bar.action("Page layouts and numbering...") is not None
      and len(pg.bar.commands) <= 5)
d = pg.layouts()
check("the window: two lists, empty, and only New... to press", [d.tabs.tabText(i) for i in range(d.tabs.count())] == ["Page layouts", "Numbering"]
      and d.lists["layout"].count() == 0 and d.btns["layout"]["new"].isEnabled() and not d.btns["layout"]["page"].isEnabled()
      and not d.btns["layout"]["remove"].isEnabled() and "page" not in d.btns["numbering"])
lay = d.new("layout", "Letter, 0.75 in", "Global Standards")
check("New... takes a page layout from the Global Standards and selects it", lay and d.lists["layout"].count() == 1 and d.current("layout") == lay["id"]
      and d.btns["layout"]["page"].isEnabled() and "taken from Global Standards" in d.said.text(), d.said.text())
check("... its row says what it holds and that no template picks it", d.lists["layout"].item(0).text().split("\n") ==
      ["Letter, 0.75 in", "Letter, 1 in margins; header and footer at 0.5 in", "No template picks it yet"], d.lists["layout"].item(0).text())
check("the same name is refused, in words", d.new("layout", "letter, 0.75 IN", "Global Standards") is None and "already used" in d.said.text())
got = d.change_page("Letter", [0.75, 0.75, 0.75, 0.75])
check("Change the page... sets the margins", got and d.lists["layout"].item(0).text().split("\n")[1].startswith("Letter, 0.75 in margins"))
check("... a margin out of range is refused, in words", d.change_page(None, [9, 1, 1, 1]) is None and "between 0 and 5" in d.said.text())
num = d.new("numbering", "Standard numbering", "Global Standards")
check("a numbering, taken the same way", num and d.lists["numbering"].count() == 1 and d.lists["numbering"].item(0).text().split("\n")[1].startswith("Headings not numbered"))
check("Rename", d.rename("numbering", "Headings plain, pages by part") and d.lists["numbering"].item(0).text().startswith("Headings plain, pages by part"))
d.close()

# ---------------------------------------------------------------- a template picks them
g = pg.new(); g.name.setText("Page-limited RFP, Volume I")
m = g.tile_menu("layout")
check("the builder has a Page Setup tile and a Numbering tile, on From the Global Standards", {"layout", "numbering"} <= set(g.tiles)
      and g.tiles["layout"].pick.text() == "From the Global Standards"
      and [a.text() for a in m.actions() if a.text()][:2] == ["From the Global Standards", "Letter, 0.75 in    Letter, 0.75 in margins"], [a.text() for a in m.actions()])
g.set_pick("layout", lay["id"]); app.processEvents()
check("a pick shows on the tile and in the sample pages at once", g.tiles["layout"].pick.text() == "Letter, 0.75 in" and g.strip.pages[0]["m"] == [0.75] * 4)
g.set_pick("numbering", num["id"]); app.processEvents()
tid = g.save(); t = NT.get(cfg, tid)
check("... and both picks are kept on Save", t["sets"]["numbering"] == num["id"] and t["sets"]["layout"] == lay["id"])
g.close()
pg.fill(); pg.select(t["id"]); app.processEvents()
card = pg.cards[t["id"]]
check("the card names the picks", card.parts[2].text() == "Page layout: Letter, 0.75 in" and card.parts[3].text() == "Numbering: Headings plain, pages by part", [p.text() for p in card.parts])
g = pg.open_builder(t["id"])
check("Go to its page on the Numbering tile opens the window on Numbering", g.go_to("numbering") == "layouts" and pg.layouts_dialog.tabs.currentIndex() == 1)
d = pg.layouts_dialog
d.lists["layout"].setCurrentRow(0)
check("a picked one says who picks it and is not removed", d.lists["layout"].item(0).text().endswith("Picked by: Page-limited RFP, Volume I")
      and not d.remove("layout") and "Pick another there first" in d.said.text() and d.lists["layout"].count() == 1, d.said.text())
d.close()

# ---------------------------------------------------------------- one answer per volume
pg._allowed = lambda: True
job = pg.make()
check("the template is made with its picks", job is not None and os.path.isfile(job.copy))
w.open_effort("Osprey"); app.processEvents()
w.go("setups"); app.processEvents()
sp = w.setups_page
sp.use_headings("Volume I Technical\n  1 Ground Segment\n    1.1 Antenna Sites\n  2 Mission Operations"); app.processEvents()
from skqt.namedtplpage import volume_templates
sp.builder.add_volume("Management"); app.processEvents()
vols = sp.volume_names()
d1 = volume_templates(sp)
check("no pick: nothing is said to differ", d1.differs == {} and d1.warn.isHidden())
d1.pick(vols[0], t["id"])
check("a volume whose template has 0.75 in margins while its standards have 1 in: it says so", list(d1.differs) == [vols[0]] and not d1.warn.isHidden()
      and d1.warn.text().startswith(f"{vols[0]}: Page-limited RFP, Volume I and this volume's standards differ on margins")
      and "The checks read the volume's standards" in d1.warn.text(), d1.warn.text())
d1.pick(vols[0], "")
check("back to the effort's own formatting: nothing to say", d1.differs == {} and d1.warn.isHidden() and d1.warn.text() == "")
w.close()
n = sum(checks)
print(f"QT PAGELAYOUTS 4420 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
