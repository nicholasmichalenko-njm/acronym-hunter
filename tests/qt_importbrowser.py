"""3.44.0 the import browser and the template library as a page, offscreen. Import from a file shows everything the
file holds at once, by layer (Building blocks, Components, Sections), each item New, Same as the library or Differs
(and what differs), with a picture of the selected one; Take the ticked takes items from every group in one go; the
file's Word sections can be kept as sections; the template library is a section of Production Standards with pictures,
a search and where each item is used. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import templatelib as TL
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
sys.path.insert(0, HERE)
from _qpfixture import with_glossary
QP_SRC = os.path.join(tmp, "Kestrel Master.dotx")
with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), QP_SRC, table_hdr=True)
import prodrules as PRL, prodtemplate as PT, shutil
_std = PRL.for_effort(tempfile.mkdtemp()); _std["variables"]["marking"] = "Kestrel restriction"
SRC = os.path.join(tmp, "Kestrel Volume.dotx")
shutil.copyfile(PT.make(_std, tempfile.mkdtemp(), "").copy, SRC)       # a template with sections, headers and footers
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page

d = sp.import_file(SRC, run=False)
tops = [d.tree.topLevelItem(i).text(0) for i in range(d.tree.topLevelItemCount())]
check("3.49.0: one browser of the file, by the library each item lands in", [t.split(" (")[0] for t in tops] == ["Formatting Standards", "Layout"]
      or [t.split(" (")[0] for t in tops] == ["Formatting Standards", "Quick Parts", "Layout"], tops)
secs = [it for it in d.items if it["kind"] == "section"]
check("each Word section of the file is offered as a section, with its page setup", secs and all(it["values"]["page"]["w"] for it in secs)
      and all(it["library"] == "layout" and it["category"] == "sections" for it in secs) and "in" in secs[0]["summary"],
      [it["summary"] for it in secs][:2])
check("everything starts New against an empty library, ticked, to add", all(it["state"] == "new" and it["take"] and it["action"] == "add" for it in d.items))
d.select("lib:formatting"); app.processEvents()
check("a library shows every item of its categories", d.t.rowCount() == sum(1 for it in d.items if it["library"] == "formatting"))
d.select("cat:formatting:para_styles"); app.processEvents()
check("a category shows its items with their badge and what to do", d.t.rowCount() > 0 and d.t.item(0, 2).text().startswith("New")
      and d.t.cellWidget(0, 3).currentData() == "add")
d.t.setCurrentCell(0, 1); app.processEvents()
check("the picture shows the selected style", d.picture.it is d.shown[0] and not d.picture.grab().isNull())
d.select("cat:layout:sections"); app.processEvents(); d.t.setCurrentCell(0, 1); app.processEvents()
check("a section is drawn as a page", d.picture.it["kind"] == "section" and not d.picture.grab().isNull())
sec1 = next((it for it in secs if it["values"].get("footer")), secs[-1])
check("a section carries its header and footer kept whole", bool(sec1["values"].get("footer")))
paras = [it for it in d.items if it["category"] == "para_styles"]
for it in d.items:
    it["take"] = it in paras or it is sec1
d.use_here.setChecked(False)
d.count()
check("the count says how many are ticked across every group", f"{len(paras) + 1} item(s)" in d.count_lab.text(), d.count_lab.text())
got = d.take()
lib = TL.Library(cfg)
check("Take the ticked keeps them in the library in one go, as Draft", got["new"] == len(paras) + 1 and len(lib.shelf("section")) == 1
      and lib.shelf("style") and all(i.get("status") == "draft" for i in lib.items), got)
check("Undo this import is offered", d.undo_btn.isVisibleTo(d) and d.report and len(d.report["added"]) == len(paras) + 1)
d.reject()

d2 = sp.import_file(SRC, run=False)
st2 = [it for it in d2.items if it["category"] == "para_styles"]
check("imported again: what the library holds is Same and starts unticked", all(it["state"] == "same" and not it["take"] for it in st2))
d2.filter.setCurrentIndex(d2.filter.findData("same")); d2.select("cat:formatting:para_styles"); app.processEvents()
check("the filter shows only the Same ones", d2.t.rowCount() == len(st2))
d2.t.setCurrentCell(0, 1)
check("Show me: the library item it is the same as", "holds these values already" in (d2.show_match(run=False) or ""))
d2.reject()
hit = lib.shelf("style")[0]
vals = dict(lib.values(hit)); vals["size"] = 31.0
lib.update(hit["id"], vals)
d3 = sp.import_file(SRC, run=False)
var = [it for it in d3.items if it["state"] == "variant"]
check("Differs says what differs, and starts as a new version", var and "size" in var[0]["differs"] and "31" in var[0]["differs"]
      and var[0]["action"] == "version", [it.get("differs") for it in var][:2])
d3.reject()

d4 = sp.import_file(SRC, section="setups", run=False)
check("the page setup section's Import offers the file's sections", any(it["kind"] == "section" for it in d4.items))
first_sec = next(it for it in d4.items if it["kind"] == "section")
for it in d4.items:
    it["take"] = it is first_sec
d4.keep_lib.setChecked(False)
d4.take()
check("Use here: the section's page setup goes into the standard", any(k.startswith("section") or "section 1" in str(v.get("name", "")).lower()
      for k, v in sp.work["page_setups"].items()), list(sp.work["page_setups"]))
d4.reject()

# ---------------------------------------------------------------- the library as a page
lv = sp.library(run=True)
app.processEvents()
check("the template library is a section of Production Standards", sp.section_key() == "tlibrary" and lv.isVisible())
lv.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("style")); app.processEvents()
n_styles = lv.t.rowCount()
check("the Styles shelf lists the kept styles", n_styles == len(TL.Library(cfg).shelf("style")) and n_styles > 0)
lv.pictures.setChecked(True); app.processEvents()
check("Pictures shows each item as a card with its picture", lv.grid.isVisible() and lv.grid.count() == n_styles
      and not lv.grid.item(0).icon().isNull())
lv.grid.setCurrentRow(0); app.processEvents()
check("selecting a picture selects the item", lv.selected() == lv.grid.item(0).data(Qt.UserRole))
lv.search.setText(lv.grid.item(0).text().split("\n")[0][:6]); app.processEvents()
check("the search narrows the shelf", 0 < lv.grid.count() <= n_styles)
lv.search.setText(""); app.processEvents()
lv.layer.setCurrentIndex(lv.layer.findData("sections")); app.processEvents()
shown = [lv.shelves.item(i).data(Qt.UserRole) for i in range(lv.shelves.count()) if not lv.shelves.item(i).isHidden()]
check("the layer filter shows that layer's shelves", "section" in shown and "style" not in shown, shown)
lv.layer.setCurrentIndex(0); app.processEvents()
lv.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("section")); app.processEvents()
lv.pictures.setChecked(False); lv.t.setCurrentCell(0, 0)
said = lv.use_it(category="appendix")
check("Use in this standard: a section's page setup and its header and footer on the part chosen", "page setup" in said
      and "appendix" in said, said)
lv.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("style")); app.processEvents(); lv.t.setCurrentCell(0, 0)
nm = TL.Library(cfg).get(lv.selected())["name"]
sp.work.setdefault("style_defs", {})[nm] = {"size": 11}
lv.show_preview()
check("where it is used: the standards that carry it", "used in" in lv.where.text().lower(), lv.where.text())

w.close()
n = sum(checks)
print(f"QT IMPORT BROWSER {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
