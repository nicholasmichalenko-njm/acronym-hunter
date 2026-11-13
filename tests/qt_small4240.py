"""4.24.0 in Qt, offscreen (Nicholas 2026-11-12, answers 10 and 16): a type box starts with Add a type... and no longer
offers Other (a document that has it keeps it); a new type is saved to the team's types before Other and picked;
cancelling goes back to the type that was picked; Settings > Document types has no Numbered column and the built-in
initials are the short names; an initial keeps its letters as typed (Sec L) and two that differ only in capitals are
the same; a term with no definition is exported with an empty definition. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.LOG_DIR = os.path.join(tmp, "logs")
import doctypes as DT, docversions as DV
from PySide6.QtWidgets import QApplication
from skqt import design as D
from skqt import doctypeui as TU
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
texts = lambda cb: [cb.itemText(i) for i in range(cb.count())]
cb = TU.type_box("")
check("a type box starts with Add a type... and does not offer Other", texts(cb)[0] == TU.ADD and "Other" not in texts(cb)
      and cb.currentText() == "RFP", texts(cb))
check("a document that is Other keeps it in its own box", "Other" in texts(TU.type_box("Other")) and TU.type_box("Other").currentText() == "Other")
seen = []
cb.currentTextChanged.connect(seen.append)
cb.setCurrentIndex(cb.findText("SOW")); TU.picked(cb)
cb.setCurrentIndex(0)
check("Add a type..., cancelled: back to the type that was picked", TU.picked(cb, answer=()) == "" and cb.currentText() == "SOW" and seen[-1] == "SOW")
cb.setCurrentIndex(0)
got = TU.picked(cb, answer=("Wage determination", ""))
T = DT.load(cfg)["types"]
check("Add a type...: saved to the team's types before Other, with its short name, and picked", got == "Wage determination"
      and cb.currentText() == "Wage determination" and [t["name"] for t in T][-2:] == ["Wage determination", "Other"]
      and next(t for t in T if t["name"] == "Wage determination")["initial"] == "WD" and DV.TYPE_INITIAL["Wage determination"] == "WD"
      and seen[-1] == "Wage determination", (cb.currentText(), [t["name"] for t in T][-2:]))
cb.setCurrentIndex(0)
check("a name already listed is picked, not added twice", TU.picked(cb, answer=("wage determination", "X9")) == "Wage determination"
      and len([t for t in DT.load(cfg)["types"] if t["name"].lower() == "wage determination"]) == 1)
check("a new box offers it", "Wage determination" in texts(TU.type_box("")))
check("a short name is its own initial; a long one takes its words' first letters", TU.short_name("Annex") == "Annex" and TU.short_name("Pricing instructions") == "PI")
dc = w.settings_page.doctypes_card
dc.fill()
ini = {dc.table.item(i, 0).text(): dc.table.item(i, 1).text() for i in range(dc.table.rowCount())}
check("Settings > Document types: no Numbered column; the initials are the short names", dc.table.isColumnHidden(2)
      and (ini["RFP"], ini["SOW"], ini["Section L"], ini["Section M"], ini["Amendment"], ini["PWS"]) == ("RFP", "SOW", "Sec L", "Sec M", "Amd", "PWS"), ini)
check("... saving keeps Amendment numbered from the first, though the column is gone", dc.save()
      and next(t for t in DT.load(cfg)["types"] if t["name"] == "Amendment")["numbered"])
check("an initial keeps its letters as typed; small letters alone become capitals; marks go", DT.clean_initial("Sec  L") == "Sec L"
      and DT.clean_initial("r-2!") == "R2" and DT.clean_initial("Amd") == "Amd" and DT.clean_initial("Section L") == "Sectio"
      and DV.clean_initial("Sec L10") == "Sec L10")
lib = DV.Library(os.path.join(tmp, "documents"))
check("a second document of a type is numbered by itself; an amendment from the first", lib.suggest_initial("RFP") == "RFP"
      and lib.suggest_initial("RFP", taken=("RFP",)) == "RFP2" and lib.suggest_initial("Section L", taken=("sec l",)) == "Sec L2"
      and lib.suggest_initial("Amendment") == "Amd1" and lib.suggest_initial("Amendment", taken=("Amd1",)) == "Amd2")
# a term with no definition is exported with an empty definition
import effort as E, acrrules
LIST = os.path.join(tmp, "Heron", "Heron_Effort_List.xlsx"); os.makedirs(os.path.dirname(LIST))
L = E.EffortList(LIST, "Heron"); L.save()
w.settings_page.new_effort({"name": "Heron", "path": LIST, "first_use": "volume"}); app.processEvents()
w.go("acrlist"); app.processEvents()
lp = w.acrlist_page
sess = lp.session
ok, info = False, ""
if sess is not None and sess.effort is not None:
    for t, dfn in (("KGS", "Kestrel Ground Station"), ("LRIP", "")):
        sess.effort.add_or_update(t, Definition=dfn, Status=E.IN)
    rows = {r["Term"]: r.get("Definition", "") for r in sess._list_rows()}
    info = rows
    ok = (rows.get("LRIP") == "" and rows.get("KGS") == "Kestrel Ground Station" and "LRIP" not in {r["Term"] for r in sess._list_rows(True)}
          and not lp.approved_only.isChecked())
check("a term with no definition is in the exported list with an empty definition (Only terms with a definition is off)", ok, info)
w.close()
n = sum(checks)
print(f"QT SMALL 4240 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
