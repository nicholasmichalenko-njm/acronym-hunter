"""4.43.0 offscreen (ST39 to ST44): the template builder. It picks and never changes a piece; a pick is seen at once
on its tile and in the sample pages, labelled Approximate; nothing is kept until Save; Export saves, writes the file
and ticks it against the picks; Go to its page leaves for the piece's own page. Fictional (Osprey)."""
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
import pagelayouts as PGL, prodrules as PRL
from skqt import tplbuilder as TB
app = QApplication([]); D.apply(app)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
check("the menu reads Templates, Page Layout, Styles, Quick Parts", [t for _k, t in dict(MW.RAIL)["Formatting"]] == ["Templates", "Page Layout", "Styles", "Quick Parts"])
w.rail_go("templates"); app.processEvents()
pg = w.named_page
check("Templates opens the gallery, with New template... as its one main button", w.stack.currentWidget() is pg and pg.bar.main is pg.b_new
      and pg.b_new.text() == "New template..." and len(pg.bar.commands) <= 5 and pg.b_arch.isHidden())
lib = TL.Library(cfg)
s1, _ = SL.new_style(lib, "Body Text", "paragraph", {"font": "Arial", "size": 11})
ka = SL.new_set(lib, "RFP volume"); SL.add_to_set(lib, ka["id"], [s1["id"]])
kb = SL.new_set(lib, "Page-limited")
lay = PGL.new(cfg, "layout", "Letter, 0.75 in", PRL.load(cfg)["company"]); PGL.set_page(cfg, lay["id"], None, [0.75] * 4)
b = pg.new()
check("six tiles in three groups, in the menu's order", list(b.tiles) == ["layout", "numbering", "style_sets", "setup_set", "part_set", "starts"]
      and [g for _k, _t, g, _s in TB.TILES] == ["Page Layout", "Page Layout", "Styles", "Styles", "Quick Parts", "Quick Parts"])
check("the builder holds no control that changes a piece: a name, tiles, and Close, Export, Save", b.findChildren(type(b.name)) == [b.name]
      and [x.text() for x in (b.b_close, b.b_export, b.b_save)] == ["Close", "Export", "Save"])
check("the sample pages are there from the start, labelled Approximate", [p["key"] for p in b.strip.pages] == ["front", "body", "landscape", "appendix"]
      and b.kind.text().startswith("Approximate: drawn by Stationkeeper") and b.strip.pages[0]["m"] == [1.0] * 4)
check("one line says the picks fit", b.line.text() == "Ready to make. The five components fit each other.", b.line.text())
m = b.tile_menu("style_sets")
check("a tile's menu lists what is saved, then Go to its page", [a.text() for a in m.actions() if a.text()] == ["RFP volume    1 style", "Page-limited    0 styles", "Go to its page"], [a.text() for a in m.actions()])
b.toggle_style_set(ka["id"]); b.toggle_style_set(kb["id"])
check("style sets join in the order picked", b.rec["style_sets"] == [ka["id"], kb["id"]] and b.tiles["style_sets"].pick.text() == "RFP volume, then Page-limited")
b.toggle_style_set(ka["id"])
check("... and one leaves", b.rec["style_sets"] == [kb["id"]])
b.toggle_style_set(kb["id"]); b.toggle_style_set(ka["id"])
b.set_pick("layout", lay["id"])
check("a page setup picked changes the sample pages at once", all(p["m"] == [0.75] * 4 for p in b.strip.pages if p["key"] != "landscape")
      and b.tiles["layout"].holds.text().startswith("Letter, 0.75 in margins"))
ms = b.tile_menu("starts")
check("Starting pages: Add a page and Take a page out, with nothing to take out yet", [a.text() for a in ms.actions() if a.text()] == ["Add a page", "Take a page out", "Go to its page"]
      and not ms.actions()[1].menu().isEnabled())
check("nothing is kept until Save: Close leaves no template", NT.every(cfg) == [])
b.reject()
check("... still none", NT.every(cfg) == [] and pg.cards == {})
b = pg.new(); b.name.setText("Page-limited RFP, Volume I"); b.toggle_style_set(ka["id"]); b.set_pick("layout", lay["id"])
pg._allowed = lambda: True
job = b.export()
t = NT.get(cfg, b.tid)
check("Export saves, writes the .dotx and says so", job is not None and os.path.isfile(job.copy) and t and t["made"]["version"] == 1
      and b.said.text().startswith("Exported ") and "The file holds what was picked (3 of 3 checks)" in b.said.text(), b.said.text())
check("... with a tick for each pick checked", [x["state"] for x in b.proof] == ["ok", "ok", "ok", "skip"] and not b.ticks.isHidden()
      and "In the file</b></span> Page Setup" in b.ticks.text() and "Not checked</b></span> Quick Parts" in b.ticks.text(), b.ticks.text())
b.set_pick("layout", "")
check("a pick changed after the export: the ticks go until it is exported again", b.proof == [] and b.ticks.isHidden())
b.set_pick("layout", lay["id"])
check("... and come back with the saved picks", len(b.proof) == 4)
b.name.setText("Page-limited RFP, Technical")
check("Save keeps a new name", b.save() == t["id"] and NT.get(cfg, t["id"])["name"] == "Page-limited RFP, Technical" and pg.cards[t["id"]].name.text() == "Page-limited RFP, Technical")
check("Go to its page on Style sets leaves for Styles", b.go_to("style_sets") == "styles" and w.stack.currentWidget() is w.styles_page)
w.close()
n = sum(checks)
print(f"QT TPLBUILDER 4430 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
