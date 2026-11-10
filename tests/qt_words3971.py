"""3.97.1 offscreen: compliance language the same both ways (claude/stationkeeper-setup-styles-3.93.1.md). A workbook
brought into Setup takes the compliance words list, as an outline built in the app does. One order decides each piece:
what you selected, then a rule saved with the layout, then the words list, then the column's own style. Selected words,
right-click: Compliance language, Just this / Everywhere it looks like this / This word everywhere. The setup styles
live in one home, the Setup set on Styles: a look changed or a style made on the setup screen is saved there.
Fictional (the Kestrel outline of test_workbook391)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import cwords as CW
import effort as E
import stylelib as SL
import templatelib as TL
import workbooksetup as WB
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

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
w.setups_page.bring_in(xl)
dlg = w.setups_page.workbook_page; app.processEvents()
li = dlg.book["headers"].index("Section L Content")
row3 = dlg.book["rows"][-1]["row"]
tt = [p for p in dlg.paras if p["section"] == "1.2" and p["tag"] == "rfp"]
check("the words list marks the RFP text brought in from a workbook", ("shall", WB.COMPLIANCE_CHAR) in tt[0]["runs"]
      and ("describe", WB.COMPLIANCE_CHAR) in tt[0]["runs"], tt[0]["runs"] if tt else dlg.paras)
plain_look = dlg.book["rows"][-1]["cells"][li][0][1]
# Just this
dlg.words_menu("TT&C approach", li, plain_look, row3, act=("just", None)); app.processEvents()
tt = [p for p in dlg.paras if p["section"] == "1.2" and p["tag"] == "rfp"]
check("Just this: those words, in that row only", ("TT&C approach", WB.COMPLIANCE_CHAR) in tt[0]["runs"]
      and dlg.pg["picks"] == [{"row": row3, "col": li, "text": "TT&C approach", "char": WB.COMPLIANCE_CHAR}], tt[0]["runs"])
dlg.words_menu("shall", li, plain_look, row3, act=("plain", None)); app.processEvents()
tt = [p for p in dlg.paras if p["section"] == "1.2" and p["tag"] == "rfp"]
check("what you selected comes before the words list: Not compliance language, just this", ("shall", WB.COMPLIANCE_CHAR) not in tt[0]["runs"]
      and any("shall" in t and c == "" for t, c in tt[0]["runs"]), tt[0]["runs"])
# This word everywhere
dlg.words_menu("both sites", li, plain_look, row3, act=("word", None)); app.processEvents()
check("This word everywhere: it joins the compliance words list", "both sites" in CW.load(cfg)["words"])
tt = [p for p in dlg.paras if p["section"] == "1.2" and p["tag"] == "rfp"]
check("... and marks it on the page", ("both sites", WB.COMPLIANCE_CHAR) in tt[1]["runs"], tt[1]["runs"])
# Everywhere it looks like this
dlg.words_menu("TT&C", li, plain_look, row3, act=("look", None)); app.processEvents()
check("Everywhere it looks like this: a rule saved with the layout", dlg.pg["chars"][WB.key("Section L Content", plain_look)] == WB.COMPLIANCE_CHAR)
# the order
pg2 = dict(dlg.pg, picks=[], chars={WB.key("Section L Content", plain_look): "SK RFP Support Char"})
p2 = [p for p in WB.paragraphs(dlg.book, dlg.profile, pg2, CW.load(cfg)) if p["section"] == "1.2" and p["tag"] == "rfp"]
check("a rule saved with the layout comes before the words list", all(c == "SK RFP Support Char" for _t, c in p2[0]["runs"] if c != "SK Source Char"), p2[0]["runs"])
pg3 = dict(dlg.pg, picks=[], chars={}, words=False)
p3 = [p for p in WB.paragraphs(dlg.book, dlg.profile, pg3) if p["section"] == "1.2" and p["tag"] == "rfp"]
check("... and the column's own style comes last (the words list off)", all(c == "" for _t, c in p3[0]["runs"] if c != "SK Source Char"), p3[0]["runs"])
# the one home of the setup styles
dlg.edit_style("SK Compliance Char", "character", {"font": "", "size": 0, "color": "C00000", "bold": True, "italic": False,
                                                   "underline": True, "hidden": True})
lib = TL.Library(cfg)
k = WB.setup_set(lib)
names = [lib.base_of(lib.get(i)) for i in (k or {}).get("items", [])]
check("a look changed on the setup screen is saved in Styles, in the Setup set", k is not None and "SK Compliance Char" in names
      and "SK Compliance Char" not in (dlg.pg.get("looks") or {}), names)
check("... and the page shows it from there", dlg.look("SK Compliance Char").get("underline") is True)
n = dlg.new_style("character", "AA Key Term")
check("a new setup style is made in the Setup set", n == "AA Key Term" and "AA Key Term" in WB.setup_looks(cfg))
SL.new_style(lib, "Kestrel Body", "paragraph", {"font": "Arial"})
check("... a name another style has is refused", dlg.new_style("paragraph", "Kestrel Body") is None)
w.close()
print(f"QT WORDS 3971 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
