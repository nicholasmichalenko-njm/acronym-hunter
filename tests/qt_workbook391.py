"""3.91.0 offscreen: Setup > Bring in a file with a workbook opens Setup from a workbook (the workbook on the left with
its column tags, the page Word gets on the right, the styles in a row above). A column's tag changes what it is and its
place in the order; text gets a character style, its own paragraph, or is left out; a paragraph on the page moves for
every section or one; Find it in the workbook; a style's look changed here; the template; Make the setup in Word; Use this
structure; the settings back with the layout next time. Settings > Appearance. Fictional content (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ.pop("SK_THEME", None)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
import effort as E
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import workbooksetup as WB

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


sys.argv = [sys.argv[0]]
src = open(os.path.join(HERE, "test_workbook391.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(HERE, "test_workbook391.py")}
exec(src.split("\n\ntmp = tempfile.mkdtemp()")[0], ns)      # only its fictional workbook, not its checks
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
xl = ns["make_book"](os.path.join(tmp, "Kestrel Outline.xlsx"))
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
pg = w.setups_page
check("a workbook brought in opens the page", pg.bring_in(xl) == "outline" and getattr(pg, "workbook_page", None) is not None)
dlg = pg.workbook_page; app.processEvents()
check("one main button and at most five commands", dlg.bar.main is dlg.b_make and len(dlg.bar.commands) <= 5, dlg.bar.labels())
left = dlg.left.toHtml(); right = dlg.right.toPlainText()
check("the left shows the workbook with numbered tags", "1 Heading" in left and "2 Guidance" in left and "3 Source" in left and "4 RFP text" in left, left[:400])
check("the right shows the page: headings, guidance after them, the source at the start of the text",
      "1.1 Ground Segment Architecture" in right and "L.4.2.1, p. 41 The Offeror shall describe" in right
      and right.index("Lead with the dual-site failover") < right.index("The Offeror shall describe"), right[:500])
check("the styles in use sit in a row", "SK Compliance Char" in dlg.style_buttons and "SK RFP Requirement" in dlg.style_buttons, list(dlg.style_buttons))

# a column's tag: the guidance later in the order (every section)
gi = dlg.book["headers"].index("Management Guidance")
for _ in range(2):
    dlg.tag_menu(gi, act=("later", None))
check("the guidance tag moved later goes with its rows", dlg.pg["order"][:4] == ["heading", "source", "rfp", "guidance"], dlg.pg["order"])
t = dlg.right.toPlainText()
check("on the page the guidance follows the RFP text", t.index("The Offeror shall describe its ground") < t.index("Lead with the dual-site failover"))
dlg.tag_menu(gi, act=("earlier", None)); dlg.tag_menu(gi, act=("earlier", None))
check("and back right after the heading", dlg.pg["order"][:2] == ["heading", "guidance"], dlg.pg["order"])
# the source: its own line always
si = dlg.book["headers"].index("Source")
dlg.tag_menu(si, act=("place", "line"))
check("the source on its own line", any(p["tag"] == "source" and p["runs"][0][0] == "L.4.2.1, p. 41" for p in dlg.paras))
dlg.tag_menu(si, act=("place", "inline"))
# text: the supporting italic left out, then its own paragraph after the RFP text, then back
li = dlg.book["headers"].index("Section L Content")
dlg.text_menu(li, "-Iauto", act=("char", "-"))
check("text left out leaves the page", "including the two station sites" not in dlg.right.toPlainText())
dlg.text_menu(li, "-Iauto", act=("own", "rfp"))
own = [p for p in dlg.paras if p.get("own")]
check("text made its own paragraph follows the RFP text", own and own[0]["runs"][0][0].startswith("including the two"), [p["runs"] for p in own])
dlg.text_menu(li, "-Iauto", act=("inside", None))
check("and back inside its cell", not any(p.get("own") for p in dlg.paras))
# a new character style for the compliance language, its look changed here
red = next(lk for _t, lk in dlg.book["rows"][1]["cells"][li] if "FF0000" in lk)
dlg.new_style("character", "AA Compliance")
dlg.text_menu(li, red, act=("char", "AA Compliance"))
dlg.edit_style("AA Compliance", "character", {"font": "", "size": 0, "color": "6B21A8", "bold": True, "italic": False, "underline": False, "hidden": True})
check("the new style is in the row and drawn in its look", "AA Compliance" in dlg.style_buttons and "6b21a8" in dlg.right.toHtml().lower())
# the page: move the RFP text earlier in 1.2 only, then find a paragraph in the workbook
n12 = next(n for n, p in enumerate(dlg.paras) if p["section"] == "1.2" and p["tag"] == "rfp")
dlg.right_click(f"para:{n12}", act=("earlier1", None))
check("one section's own order, marked on the page", "1.2" in dlg.pg["sections"] and "own order" in dlg.right.toPlainText())
nb = next(n for n, p in enumerate(dlg.paras) if p["section"] == "1.2" and p["tag"] == "heading")
dlg.right_click(f"para:{nb}", act=("back", None))
check("back to every section", not dlg.pg["sections"])
n11 = next(n for n, p in enumerate(dlg.paras) if p["tag"] == "rfp")
dlg.right_click(f"para:{n11}", act=("find", None))
check("Find it in the workbook selects its text there", dlg.sel and dlg.sel[0] in ("look", "col") and dlg.sel[1] == li, dlg.sel)
# make the setup
out = dlg.make(os.path.join(tmp, "Kestrel setup.docx"))
with zipfile.ZipFile(out) as z:
    doc = z.read("word/document.xml").decode(); sty = z.read("word/styles.xml").decode()
check("Make the setup in Word writes the page with its styles", "Lead with the dual-site failover" in doc and "AACompliance" in doc
      and 'w:type="character"' in sty)
check("the settings are kept with the layout", WB.saved(cfg, dlg.layout_name).get("chars", {}).get(WB.key("Section L Content", red)) == "AA Compliance")
# a second time: the page opens as it was left
dlg.close()
pg.bring_in(xl); d2 = pg.workbook_page; app.processEvents()
check("the next time the page opens as it was left", d2 is not dlg and "AA Compliance" in d2.style_buttons)
# use this structure
n = d2.use(accept=True)
check("Use this structure brings the sections into the effort", n and n.get("requirements", 0) >= 1 and w.review is not None, n)
# Settings > Appearance
w.go("settings"); app.processEvents()
sp = w.settings_page
check("Settings has Appearance: Follow Windows, Light, Dark", [sp.look.itemData(i) for i in range(sp.look.count())] == ["windows", "light", "dark"])
sp.section("You"); app.processEvents()
check("... shown under Settings > You (4.4.0: it had no section)", sp.look_card.isVisibleTo(w) and sp.look.isVisibleTo(w))
_placed = {k for _n, ks in sp.SECTIONS for k in ks} | {"db"}          # db: Team References holds the database (3.77.0)
_lost = [k for k, x in vars(sp).items() if isinstance(x, D.Card) and k not in _placed]
check("every Settings card sits in a section", not _lost, _lost)
check("Dark is used now and kept on this PC", sp.set_look("dark") is True and D.is_dark() and (A.load_settings() or {}).get("appearance") == "dark")
check("Light is used now", sp.set_look("light") is False and not D.is_dark())
sp.set_look("windows")
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
