"""3.92.2 offscreen: Setup from a workbook, the clicks: a left click selects (Ctrl adds), a style clicked in the row goes to what is selected, No character style clears it, a paragraph clicked on the page is selected, a paragraph dragged above or below another moves its kind of text (every section or that section only), a tag dropped on another takes its place. Before 3.92.2: 3.91.0 offscreen: Setup > Bring in a file with a workbook opens Setup from a workbook (the workbook on the left with
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

from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
li = dlg.book["headers"].index("Section L Content")
red = next(lk for _t, lk in dlg.book["rows"][1]["cells"][li] if "FF0000" in lk)
ital = next(lk for _t, lk in dlg.book["rows"][1]["cells"][li] if lk.startswith("-I"))
got = dlg.pick(f"run:{li}:{red}")
check("a left click selects the text (no menu)", got == ("look", li, red) and dlg.sels == [("look", li, red)])
dlg.pick(f"run:{li}:{ital}", add=True)
check("Ctrl or Shift adds to the selection", dlg.sels == [("look", li, red), ("look", li, ital)])
check("both are highlighted in the workbook", dlg.left.toHtml().lower().count("#cfe1fb") >= 2)
n = dlg.style_clicked("SK Compliance Char", "character")
check("a style clicked in the row goes to everything selected", n == 2 and dlg.pg["chars"][f"Section L Content|{red}"] == "SK Compliance Char"
      and dlg.pg["chars"][f"Section L Content|{ital}"] == "SK Compliance Char")
dlg.pick(f"run:{li}:{ital}")
dlg.style_buttons["No character style"].click(); app.processEvents()
check("No character style clears it", dlg.pg["chars"][f"Section L Content|{ital}"] == "")
dlg.style_clicked("SK RFP Support Char", "character")
nm = dlg.new_style_for_selection("AA Supporting", "character")
check("New style... makes a style and gives it to the selection", nm == "AA Supporting" and dlg.pg["chars"][f"Section L Content|{ital}"] == "AA Supporting"
      and "AA Supporting" in dlg.style_buttons)
gi = dlg.book["headers"].index("Management Guidance")
dlg.pick(f"tag:{gi}")
n = dlg.assign("AA Guidance", "paragraph")
check("a paragraph style clicked with a column's tag selected goes to that kind of text", n == 1 and dlg.pg["styles"]["guidance"] == "AA Guidance")
check("a character style needs text: said in plain words", dlg.assign("SK Compliance Char", "character") == 0)
# the page: a click selects a paragraph
dlg.resize(1400, 900); app.processEvents()
k = next(n for n, p in enumerate(dlg.paras) if p["tag"] == "rfp")
it = dlg.right.item(k)
QTest.mouseClick(dlg.right.viewport(), Qt.LeftButton, Qt.NoModifier, dlg.right.visualItemRect(it).center()); app.processEvents()
check("a paragraph clicked on the page is selected", dlg.sel == ("para", k), dlg.sel)
# drag: the guidance dropped below the RFP text, every section
g = next(n for n, p in enumerate(dlg.paras) if p["section"] == "1.1" and p["tag"] == "guidance")
r = next(n for n, p in enumerate(dlg.paras) if p["section"] == "1.1" and p["tag"] == "rfp")
order = dlg.drop_para(g, r, below=True, scope="every")
check("a paragraph dropped below another moves its kind of text there, every section", dlg.pg["order"].index("guidance") > dlg.pg["order"].index("rfp"), dlg.pg["order"])
t11 = [p["tag"] for p in dlg.paras if p["section"] == "1.1"]
check("... and the page shows it", t11.index("guidance") > t11.index("rfp"), t11)
g = next(n for n, p in enumerate(dlg.paras) if p["section"] == "1.2" and p["tag"] == "rfp")
h = next(n for n, p in enumerate(dlg.paras) if p["section"] == "1.2" and p["tag"] == "heading")
dlg.drop_para(g, h, below=True, scope="one")
check("dropped in one section only, that section gets its own order", "1.2" in dlg.pg["sections"] and dlg.pg["sections"]["1.2"][1] == "rfp"
      and dlg.pg["order"][1] != "rfp", (dlg.pg["sections"], dlg.pg["order"]))
other = next(n for n, p in enumerate(dlg.paras) if p["section"] == "1.1" and p["tag"] == "rfp")
check("a drop into another section is refused", dlg.drop_para(g, other, scope="every") is None)
hd = next(n for n, p in enumerate(dlg.paras) if p["tag"] == "heading")
check("headings keep the workbook's order", dlg.drop_para(hd, other, scope="every") is None)
# a tag dropped on another tag
si = dlg.book["headers"].index("Source")
before = list(dlg.pg["order"])
dlg.drop_tag(si, li)
check("a tag dropped on another takes its place in the order", dlg.pg["order"].index("source") == before.index("rfp"), (before, dlg.pg["order"]))
check("a tag dropped on the heading is refused", dlg.drop_tag(si, dlg.book["headers"].index("Response Section Name")) is None)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
