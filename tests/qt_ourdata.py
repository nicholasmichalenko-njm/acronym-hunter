"""3.22.0 Our data and the template library, offscreen: Settings > Our data exports the team's data to one labeled file
and imports it on another PC with a preview and Undo; Production Standards has a Quick Parts section that adds entries
from a template; Collect into the library confirms what a file carries card by card and saves as it goes; Open a
sample in Word makes a small template with the card's items; the Template library shows the shelves and puts an item
into the standard being edited; a style can be hidden text."""
import hashlib, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import prodrules as PRL, teamdata as TD, templatelib as TL, customdict as CD, teampack as TP
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest(), os.stat(p).st_mtime_ns


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
import roleaccess as _RA                                   # 3.13.0: Preview tools on for this team
for _k in _RA.PREVIEW:
    _RA.set_preview(cfg, _k, True)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("home"); app.processEvents()
sys.path.insert(0, HERE)
from _qpfixture import with_glossary
SRC = os.path.join(tmp, "Team Master.dotx")
with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), SRC)

# ---------------------------------------------------------------- Production Standards: Quick Parts
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
from skqt.prodstdpage import SECTIONS
check("Production Standards has a Quick Parts section", "quickparts" in [k for k, _t in SECTIONS])
sp.nav.setCurrentRow([k for k, _t in SECTIONS].index("quickparts")); app.processEvents()
n = sp.add_quick_parts(SRC, picks=["Volume cover", "CUI header"])
check("Add from a template: the picked Quick Parts are listed to carry, from a kept copy of the file", n == 2
      and [e["name"] for e in sp.work["quick_parts"]["entries"]] == ["Volume cover", "CUI header"]
      and sp.tables["quickparts"]["w"].rowCount() == 2 and os.path.isfile(os.path.join(sp.parts_dir(), sp.work["quick_parts"]["entries"][0]["source"])))
check("one gallery is on by default", sp.work["quick_parts"]["one_gallery"] is True)
from skqt.prodstdpage import STYLE_COLS
check("the style library has Hidden text", any(c[0] == "hidden" for c in STYLE_COLS))

# ---------------------------------------------------------------- Collect into the library
d = sp.collect(SRC, run=False)
check("Collect shows the first card of what the file carries", d.cards and d.t.rowCount() > 0 and "1 of" in d.head.text(), [c.key for c in d.cards])
d.uses["RFP"].setChecked(True)
first = d.cards[0]
d.t.item(0, 1).setText("Renamed style")
d.go(1)
lib = TL.Library(cfg)
check("Keep and next saves the card at once, renamed and tagged", lib.shelf("style") and any(i["name"] == "Renamed style" for i in lib.shelf("style"))
      and all("RFP" in i["tags"]["use"] for i in lib.shelf("style")), [i["name"] for i in lib.shelf("style")][:5])
qi = next(i for i, c in enumerate(d.cards) if c.key == "quickparts")
while d.step < qi:
    d.go(1)
smp = d.sample(open_it=False)
check("Open a sample in Word: a small template with the card's items, in the Samples folder", smp and smp.endswith(".dotx")
      and os.path.basename(os.path.dirname(smp)) == "Samples" and len(__import__("prodquickparts").read(smp)) == 3, smp)
while True:
    last = d.step == len(d.cards) - 1
    d.go(1)
    if last:
        break
lib.load()
check("finishing keeps every card's items: Quick Parts, fonts, pages", lib.shelf("quickpart") and lib.shelf("font") and lib.shelf("page_setup"), {k: len(lib.shelf(k)) for k, _t in TL.SHELVES})
ld = sp.library(run=False)
ld.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("quickpart")); app.processEvents()
check("the Template library shows each shelf with its count", "Quick Parts (3)" in ld.shelves.item([k for k, _t in TL.SHELVES].index("quickpart")).text()
      and ld.t.rowCount() == 3)
ld.t.setCurrentCell(0, 0)
said = ld.use_it(category="01 Covers")
check("Use in this standard puts the item into what is being edited", said.startswith("Quick Part") and
      any(e["category"] == "01 Covers" for e in sp.work["quick_parts"]["entries"]), said)
ld.use.setCurrentIndex(ld.use.findData("RFI"))
check("the shelves filter by use case", ld.t.rowCount() == 0)

it = ld.new_style("SK PM Commentary", {"color": "C00000", "hidden": True, "italic": True}, uses=["RFP"])
check("New style: a style of your own (hidden text) kept on the Styles shelf", it and it["name"] == "SK PM Commentary"
      and TL.Library(cfg).values(it)["hidden"] is True and "hidden text" in it["summary"])
from skqt.collectview import StyleDialog
sd_ = StyleDialog(ld, "X", {"hidden": True, "size": 11.0, "color": "7030A0"})
nm_, vals_ = sd_.values()
check("the style form reads and gives back every property", vals_ == {"type": "paragraph", "hidden": True, "size": 11.0, "color": "7030A0"}, vals_)
ld.use.setCurrentIndex(0)
ld.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("style")); app.processEvents()
row = next(r for r in range(ld.t.rowCount()) if ld.t.item(r, 0).text() == "SK PM Commentary")
ld.t.setCurrentCell(row, 0)
check("Edit changes an item's values", ld.edit({"color": "C00000", "hidden": True, "size": 9.0}) and TL.Library(cfg).values(it)["size"] == 9.0)

# ---------------------------------------------------------------- 3.23.0 kits, previews, fill-ins, names and versions
ld.use.setCurrentIndex(0)
ld.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("style")); app.processEvents()
row = next(r for r in range(ld.t.rowCount()) if ld.t.item(r, 0).text() == "SK PM Commentary")
ld.t.setCurrentCell(row, 0); app.processEvents()
check("a style's preview shows it in its color, marked hidden", "color:#C00000" in ld.preview.text() and "Hidden text" in ld.preview.text(), ld.preview.text())
ld.t.selectRow(row)
k = ld.save_kit("USSF page-limited RFP")
check("Save as a kit keeps the selected items under a name", k and k["items"] and "Kits (1)" in ld.shelves.item(ld.shelves.count() - 1).text())
ld.shelves.setCurrentRow(ld.shelves.count() - 1); app.processEvents(); ld.t.setCurrentCell(0, 0)
said = ld.use_it()
check("Use in this standard on a kit puts every item in", "style" in said and "SK PM Commentary" in sp.work["style_defs"], said)
sp.nav.setCurrentRow([k_ for k_, _t in SECTIONS].index("fillins")); app.processEvents()
check("Production Standards has Fill-ins", "fillins" in [k_ for k_, _t in SECTIONS] and "fillins" in sp.tables)
sp.work["fill_ins"] = [{"key": "contract_type", "name": "Contract type", "kind": "styleref", "value": "CPFF"}]
sp.work["hf_layouts"]["body"]["header"] = {"left": "{contract_type}"}
sp.load_tables()
check("the fill-ins list shows them", sp.tables["fillins"]["w"].rowCount() == 1)
import templatereg as TR
for c_ in sp.work.get("captions", []):
    c_["number_format"] = c_.get("number_format") or "ARABIC"
j1 = sp.make_template(start_from="", word=False, name="USSF RFP Volume I")
j2 = sp.make_template(start_from="", word=False, name="USSF RFP Volume I")
check("a template made twice under one name: version 1, then 2, in the file name", j1 and j2 and "USSF RFP Volume I v1" in os.path.basename(j1.copy)
      and "USSF RFP Volume I v2" in os.path.basename(j2.copy) and TR.latest(cfg, "USSF RFP Volume I")["v"] == 2, (j1 and j1.copy, j2 and j2.copy))
rp_ = os.path.splitext(j2.copy)[0] + " - validation report.txt"
check("the validation report is saved beside the template", os.path.isfile(rp_) and "Validation report" in open(rp_, encoding="utf-8").read())
import zipfile as _z
check("the file carries its name and version", "SK Template Version" in _z.ZipFile(j2.copy).read("docProps/custom.xml").decode())

# ---------------------------------------------------------------- Settings: Our data
st = CD.Store(cfg); st.add("Space terms", ["apogee"]); st.save()
TP.save_topics(cfg, ["Thermal"])
w.go("settings"); app.processEvents()
sg = w.settings_page
check("Settings has Our data, labeled as the team's data, never GitHub", "Our data" in sg.ourdata.title.text() and "GitHub" in sg.ourdata.subtitle.text())
out = sg.export_data(os.path.join(tmp, "share", TD.file_name()), parts=["dictionaries", "topics", "library"])
check("Export our data writes one .skdata file", out and os.path.isfile(out) and out.endswith(".skdata"))
os.remove(os.path.join(cfg, "custom_dictionaries.json")); TP.save_topics(cfg, ["Schedule"])
said = sg.import_data(out, picks=["dictionaries", "topics"])
check("Import our data brings the chosen parts in, add-only", CD.Store(cfg).by_name("Space terms") is not None
      and set(TP.topics(cfg)) == {"Schedule", "Thermal"}, said)
check("Undo the last import puts it back", sg.undo_data() > 0 and CD.Store(cfg).by_name("Space terms") is None and TP.topics(cfg) == ["Schedule"])

print(f"QT OUR DATA {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.stdout.flush()
w.close()
__import__("hangguard").end(0 if all(checks) else 1)
