"""4.45.0 offscreen (ST45): point at a part of a sample page to see which pick made it. A part under the pointer is
named with its pick and the pick's tile is outlined; a click asks for that pick's menu; a tile under the pointer
outlines the parts it made; Word's pages name the page only, and one button goes between them and the sample pages.
Fictional (Osprey)."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import namedtemplates as NT
import pagelayouts as PGL, prodrules as PRL
import roleaccess as RA
import stylelib as SL
import templatelib as TL
import pypdfium2 as pdfium
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D, mainwin as MW
from skqt import tplbuilder as TB
from skqt.tplsample import WHERE

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def word(cmd, env, timeout):
    d = pdfium.PdfDocument.new(); d.new_page(612, 792); d.new_page(612, 792); d.save(env["SK_PDF"]); d.close()
    return json.dumps({"ok": True, "pages": 2, "heads": []})


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.rail_go("templates"); app.processEvents()
pg = w.named_page; pg._allowed = lambda: True
lib = TL.Library(cfg)
s1, _ = SL.new_style(lib, "Body Text", "paragraph", {"font": "Arial", "size": 11})
ka = SL.new_set(lib, "RFP volume"); SL.add_to_set(lib, ka["id"], [s1["id"]])
lay = PGL.new(cfg, "layout", "Letter, 0.75 in", PRL.load(cfg)["company"]); PGL.set_page(cfg, lay["id"], None, [0.75] * 4)
b = pg.new(); b.name.setText("Page-limited RFP, Volume I"); b.toggle_style_set(ka["id"]); b.set_pick("layout", lay["id"])
b.show(); app.processEvents(); b.strip.grab()
st = b.strip
parts = {part for _r, part in st.regions}
check("every part a pick makes is known to the tiles", all(k in dict((k, 1) for k, _t, _g, _s in TB.TILES) or k == "" for k, _n in WHERE.values()))
check("the pages drawn know their parts", {"paper", "margin", "number", "heading", "text", "table", "figure", "caption", "toc", "title", "list"} <= parts
      and "word" not in parts, sorted(parts))
check("before pointing, the line says how", b.where.text() == TB.POINT == "Point at a part of a page to see which pick made it.")


def first(part):
    """The first region of a part; for the margins, the left band (the header and footer sit in the top and bottom ones)."""
    rs = [r for r, p in st.regions if p == part]
    return rs[2] if part == "margin" else rs[0]


got = st.point(first("margin").center())
check("the margins come from Page Setup, by its name", got == ("layout", "margin") and b.where.text() == "Margins: from Page Setup, Letter, 0.75 in. Click to pick another.", b.where.text())
check("... and the Page Setup tile is outlined, alone", b.tiles["layout"].lit and [k for k, t in b.tiles.items() if t.lit] == ["layout"]
      and "2px solid" in b.tiles["layout"].styleSheet())
st.grab()
got = st.point(first("number").center())
check("the page number comes from Numbering", got == ("numbering", "number") and b.where.text().startswith("Page number: from Numbering, From the Global Standards.")
      and [k for k, t in b.tiles.items() if t.lit] == ["numbering"], b.where.text())
got = st.point(first("text").center())
check("body text comes from the style sets", got == ("style_sets", "text") and b.where.text() == "Body text: from Style sets, RFP volume. Click to pick another.", b.where.text())
hn = [r for r, p in st.regions if p == "hnum"]
check("a heading's number is Numbering's; the heading is the style sets'", (not hn or st.point(hn[0].center()) == ("numbering", "hnum"))
      and st.point(QPointF(first("heading").right() - 3, first("heading").center().y())) == ("style_sets", "heading"))
top = [r for r, p in st.regions if p == "margin"][0]
check("the header sits in the top margin and is named for itself", st.point(next(r for r, p in st.regions if p == "header").center())[1] == "header"
      and st.point(QPointF(top.center().x(), top.top() + 2)) == ("layout", "margin"))
got = st.point(first("list").center())
check("a part with no pick of its own says so, and no tile is outlined", got == ("", "list") and b.where.text() == "List: from the Global Standards until it gets its own pick."
      and not [k for k, t in b.tiles.items() if t.lit], b.where.text())
check("away from every page: the line says how again", st.point(QPointF(2, 2)) is None and b.where.text() == TB.POINT and st.at is None)
seen = []
st.picked.connect(seen.append)
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
QTest.mouseClick(st, Qt.LeftButton, Qt.NoModifier, first("margin").center().toPoint())
check("a click on a part asks for its pick's menu", seen == ["layout"])
m = b.point_menu("layout")
check("... the same menu its tile opens", [a.text() for a in m.actions() if a.text()][0] == "From the Global Standards" and [a.text() for a in m.actions() if a.text()][-1] == "Go to its page")
QTest.mouseClick(st, Qt.LeftButton, Qt.NoModifier, first("list").center().toPoint())
check("a click on a part with no pick asks for nothing", seen == ["layout"])
n = b.light("layout", from_tile=True)
check("a tile under the pointer outlines the parts it made", n >= 5 and st.lit == "layout" and b.where.text() == "Page Setup: outlined on the pages.", (n, b.where.text()))
st.grab()
check("a pick the pages do not show says so", b.light("part_set", from_tile=True) == 0
      and b.where.text() == "Quick Part set: nothing on the sample pages shows this pick. Draw with Word shows it in the file.", b.where.text())
check("the pointer leaves the tile: nothing outlined", b.light("", from_tile=True) == 0 and st.lit == "" and b.where.text() == TB.POINT)
check("with no kept pages the button draws with Word", b.b_exact.text() == "Draw with Word")
b.draw_exact(runner=word, wait=True); st.grab()
check("Word's pages: one region a page", st.exact and [p for _r, p in st.regions] == ["word", "word"] and b.b_exact.text() == "Show the sample pages", b.b_exact.text())
got = st.point(st.regions[0][0].center())
check("... pointing names the page only and says where the picks show", got == ("", "word") and b.where.text() == TB.WORDS_PAGE, b.where.text())
check("... a tile says the same", b.light("layout", from_tile=True) == 0 and "Word's pages do not show which part it made" in b.where.text())
check("the button goes to the sample pages", b.exact_button() == "sample" and not st.exact and b.b_exact.text() == "Show Word's pages" and b.kind.text() == TB.SKETCH)
st.grab()
check("... where pointing names picks again", st.point(first("margin").center()) == ("layout", "margin"))
check("... and back to Word's pages, with no new drawing", b.exact_button() == "word" and st.exact and b.kind.text() == TB.EXACT)
b.reject()
real = w.profile
w.profile = lambda: (RA.PROFILES[2], "set")
check("an author is in a role that only looks", not RA.builds_templates(w.profile()[0]), w.profile())
b3 = pg.open_builder(b.tid); b3.sketch = True; b3.fill(); b3.show(); app.processEvents(); b3.strip.grab()
b3.strip.point([r for r, p in b3.strip.regions if p == "margin"][2].center())
check("... sees which pick made a part, without the offer to pick another", b3.where.text() == "Margins: from Page Setup, Letter, 0.75 in.", b3.where.text())
check("... and a click's menu offers no pick", [a.isEnabled() for a in b3.point_menu("layout").actions()] == [False])
b3.reject(); w.profile = real
w.close()
n = sum(checks)
print(f"QT TPLPOINT 4450 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
