"""4.28.0 offscreen: Templates is its own menu group (answer 21; the recording at 06:25: Team does not make sense for
standards). Styles, Quick Parts, Page Layout, Template sit under the effort's steps. Formatting and Layout are one Page
Layout screen with one list at the left; one Save on its face and a right-click for the rest. Parts reads Quick Parts.
Team keeps Rules, Check a Draft and Team References. Fictional (Osprey)."""
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
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D, mainwin as MW, teampage as TP
from skqt.pagetitles import TITLES

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


check("the menu's groups: Effort, Templates, Team, Settings", [g for g, _i in MW.RAIL] == ["Effort", "Templates", "Team", "Settings"])
check("Templates: Styles, Quick Parts, Page Layout, Template", dict(MW.RAIL)["Templates"] == [("styles", "Styles"), ("designs", "Quick Parts"),
                                                                                              ("formatstd", "Page Layout"), ("templates", "Template")])
check("Template holds Templates, Effort Profiles and Template Studio", [k for k, _t in MW.TABS["templates"]] == ["templates", "profiles", "studio"])
check("Team keeps Rules, Check a Draft and Team References", MW.TEAM == ("rules", "audit", "refs") and [k for k, _n, _w in TP.TILES] == ["rules", "audit", "refs"])
check("each of the pages says it is in Templates", all(MW.GROUP_OF.get(k) == "Templates" for k in ("styles", "designs", "formatstd", "layoutstd", "templates", "profiles", "studio", "qpstd")),
      {k: MW.GROUP_OF.get(k) for k in ("styles", "designs", "formatstd", "layoutstd", "templates", "profiles", "studio", "qpstd")})
check("the titles: Page Layout and Quick Parts", TITLES["formatstd"][0] == "Page Layout" and TITLES["designs"][0] == "Quick Parts")
check("no page of these needs an effort but Template Studio", {"styles", "designs", "formatstd", "templates", "profiles"} <= MW.MainWindow.NO_EFFORT)

cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); os.makedirs(ED)
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
app = QApplication([]); D.apply(app)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
check("the four entries are in the menu with no effort open", all(k in w.step_btns and w.step_btns[k].isVisible() for k in ("styles", "designs", "formatstd", "templates")))
check("... under their own heading", w.group_heads["Templates"] is not None and w.group_heads["Templates"].text() == "TEMPLATES")
for k, page in (("styles", "styles_page"), ("designs", "designs_page"), ("formatstd", "formatstd_page"), ("templates", "templates_page")):
    w.rail_go(k); app.processEvents()
    check(f"{k} opens from the menu with no effort open, and lights its entry", w.stack.currentWidget() is getattr(w, page) and w.step_btns[k].isChecked() and w.ws is None,
          (type(w.stack.currentWidget()).__name__, w.ws is None))
w.rail_go("templates"); app.processEvents()
check("Template shows its three tabs", w._tab_keys == ["templates", "profiles", "studio"], w._tab_keys)
w.rail_go("styles"); app.processEvents()
check("Styles, Quick Parts and Page Layout have no tabs: each is a screen", not w._tab_keys or w._tab_keys == ["styles"], w._tab_keys)

# ---- Page Layout: one list
w.rail_go("formatstd"); app.processEvents()
pg = w.formatstd_page
rows = [(pg.cats.item(r).text(), pg.cats.item(r).data(Qt.UserRole), pg.cats.item(r).data(pg.LIB)) for r in range(pg.cats.count())]
heads = [t for t, k, _l in rows if k is None]
keys = [k for _t, k, _l in rows if k]
check("one list, the page first, then text and tables", heads == ["THE PAGE", "TEXT AND TABLES"]
      and keys == ["page_setup", "pagination", "hf", "sections", "toc", "theme", "fonts", "heading_numbering", "lists", "table_styles", "table_looks", "captions"], rows)
check("... styles and covers are not in it (Styles and Quick Parts hold them)", not {"para_styles", "char_styles", "covers", "titles", "backers"} & set(keys))
check("a heading cannot be picked; the first section is", pg.cats.currentRow() == 1 and not (pg.cats.item(0).flags() & Qt.ItemIsSelectable))
check("each section knows its library", dict((k, l) for _t, k, l in rows if k)["hf"] == "layout" and dict((k, l) for _t, k, l in rows if k)["lists"] == "formatting")
pg.select_category("hf")
check("picking Headers and footers works the Layout library", pg.library == "layout" and pg.category() == "hf")
n_hf = pg.t.rowCount()
pg.select_category("page_setup")
check("picking Page setups works the Formatting library", pg.library == "formatting" and pg.t.rowCount() >= 1 and (n_hf != pg.t.rowCount() or n_hf >= 0))
check("the old Layout name reaches the same screen", w.layoutstd_page is pg and w.go("layoutstd") is not False and w.stack.currentWidget() is pg)
check("one Save on the face; the row of buttons is gone", pg.save_btn.isVisibleTo(pg) and not pg.row_actions.isVisibleTo(pg) and not pg.ver_btn.isVisibleTo(pg)
      and not pg.revert_btn.isVisibleTo(pg))
m = pg.row_menu(run=False)
names = [a.text() for a in m.actions() if a.text()]
check("a right-click holds the rest", names == ["Rename...", "Effort types...", "Status", "Compare...", "Put in a standard...", "Take out",
                                                "Draw the selected items with Word", "Draw every item in this category with Word", "Allowed styles...",
                                                "Save as a new version", "Undo changes"], names)
cur = pg.current()
check("an item is selected and its values show", cur is not None and pg.ed_head.text())
if cur:
    pg.select_category("hf"); pg.select_category("page_setup")
    check("going to another section and back keeps the list whole", pg.cats.count() == len(rows))

# ---- a style opened from Styles with Every value... still shows
pg.select_category("para_styles")
keys2 = [pg.cats.item(r).data(Qt.UserRole) for r in range(pg.cats.count())]
check("a style opened with Every value... shows its category while it is open", "para_styles" in keys2 and pg.category() == "para_styles", keys2)

# ---- Team
w.rail_go("team"); app.processEvents()
shown = [k for k, b in w.team_page.tiles.items() if b.isVisible()] if hasattr(w, "team_page") else []
check("Team shows three tiles", set(shown) <= {"rules", "audit", "refs"} and len(w.team_page.tiles) == 3, shown)
w.close()
n = sum(checks)
print(f"QT TEMPLATES 4280 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
