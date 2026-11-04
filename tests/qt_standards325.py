"""3.25.0 Production Standards, offscreen: the menu across the top in the order a document is built; each section's own
Import from a file (one item, some or all; Use here and Keep in the library); Allowed styles ticked from a list, sorted
and shown by kind; the checks in the sections they check; headers and footers built as a table or from a Quick Part;
Fields; the two Editing boxes (effort type, volume) and This effort only; Make templates with every template read in
full before it is made."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import prodrules as PRL, templatelib as TL, templatedetails as TDET
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
import roleaccess as _RA
for _k in _RA.PREVIEW:
    _RA.set_preview(cfg, _k, True)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
sys.path.insert(0, HERE)
from _qpfixture import with_glossary
SRC = os.path.join(tmp, "Team Master.dotx")
with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), SRC, table_hdr=True)
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
from skqt.prodstdpage import GROUPS, SECTIONS, IMPORT_KINDS

# ---------------------------------------------------------------- the menu across the top
check("the menus across the top, in the order a document is built (3.26.0: Document parts first)",
      [sp.group_bar.tabText(i) for i in range(sp.group_bar.count())] == ["Template profile", "Document parts", "Pages", "Styles", "Numbering", "Tables", "Content", "Check", "Library"])
check("no column of sections down the side", not sp.nav.isVisible() and sp.section_bar.isVisible())
names = [t for _k, t in SECTIONS]
check("the sections have their plain names", {"Base fonts and sizes", "Styles", "Allowed styles", "Heading numbering", "Row looks",
      "How rows are recognized", "Page sizes and margins", "Pagination and covers", "Fields", "Words to avoid and fix"} <= set(names)
      and "Check options" not in names and "Style library" not in names and "Format variables" not in names, names)
sp.group_bar.setCurrentIndex(4); app.processEvents()     # 3.33.0: Template profile comes first
check("a menu shows its sections and opens the first", [sp.section_bar.tabText(i) for i in range(sp.section_bar.count())]
      == ["Heading numbering", "Lists", "Captions"] and sp.section_key() == "headnum")
sp.section_bar.setCurrentIndex(2); app.processEvents()
check("a section opens its page", sp.section_key() == "captions" and sp.stack.currentIndex() == [k for k, _t in SECTIONS].index("captions"))
sp.nav.setCurrentRow([k for k, _t in SECTIONS].index("hf")); app.processEvents()
check("going to a section moves the menu with it", sp.group_bar.tabText(sp.group_bar.currentIndex()) == "Pages"
      and sp.section_bar.tabText(sp.section_bar.currentIndex()) == "Headers and footers")
check("Heading numbering is its own section", "heading_levels" in sp.tables and sp.stack.widget([k for k, _t in SECTIONS].index("headnum"))
      .findChild(type(sp.tables["heading_levels"]["w"])) is sp.tables["heading_levels"]["w"])

# ---------------------------------------------------------------- the checks where they belong
paths = {tuple(it["path"]) for it in sp.binder.items}
check("Check options' checks sit in the sections they check", {("checks", "toc_forbid"), ("checks", "page_numbers"), ("checks", "caption_fields"),
      ("checks", "table_caption_position"), ("checks", "landscape_ok")} <= paths and "checks" not in [k for k, _t in SECTIONS])
toc_page = sp.pages["toc"]
check("the TOC section has What Check reports", any(it["path"] == ("checks", "toc_forbid") and toc_page.isAncestorOf(it["w"]) for it in sp.binder.items))

# ---------------------------------------------------------------- each section imports its own items
from PySide6.QtWidgets import QPushButton
for k in ("headnum", "styledefs", "hf", "quickparts", "setups"):
    btns = [b.text() for b in sp.pages[k].findChildren(QPushButton)]
    check(f"{dict(SECTIONS)[k]} has its own Import from a file", "Import from a file..." in btns)
check("sections with nothing to import have none", "Import from a file..." not in [b.text() for b in sp.pages["terms"].findChildren(QPushButton)])
lib = TL.Library(cfg)
before = len(lib.items)
d = sp.import_file(SRC, section="quickparts", run=False)
kinds = {it["kind"] for c in d.cards for it in c.items}
check("a section's Import shows only that section's items", kinds == {"quickpart"} and len(d.cards) == 1, kinds)
check("Use here and Keep in the library both start on", d.use_here.isChecked() and d.keep_lib.isChecked())
d.keep_lib.setChecked(False)
for r in range(d.t.rowCount()):                          # take one item only
    d.t.item(r, 0).setCheckState(Qt.Checked if d.t.item(r, 1).text() == "Table header" else Qt.Unchecked)
d.take()
lib.load()
qp = [e["name"] for e in sp.work["quick_parts"]["entries"]]
check("one item taken: it goes into what is being edited, and the library is left alone", qp == ["Table header"] and len(lib.items) == before, qp)
d2 = sp.import_file(SRC, section="styledefs", run=False)
check("the Styles section's Import shows styles (and the theme and fonts)", {it["kind"] for c in d2.cards for it in c.items} <= {"style", "theme", "font"}
      and any(it["kind"] == "style" for c in d2.cards for it in c.items))
d2.use_here.setChecked(False)
d2.take()
lib.load()
check("Keep in the library only: the styles go to the library", len(lib.shelf("style")) > 0)
dall = sp.import_file(SRC, run=False)
check("Import from a file at the top reads everything", len({it["kind"] for c in dall.cards for it in c.items}) > 3)
dall.reject()
check("the Template library's Import keeps in the library only", not sp.collect(SRC, run=False).use_here.isChecked())

# ---------------------------------------------------------------- Allowed styles: ticked from a list
sp.nav.setCurrentRow([k for k, _t in SECTIONS].index("styles")); app.processEvents()
sp.fill_allowed()
t = sp.allow_t
rows = [t.item(i, 0).text() for i in range(t.rowCount())]
check("Allowed styles lists this standard's styles and the library's", "Normal" in rows and any(t.item(i, 4).text() != "This standard" for i in range(t.rowCount())), rows[:8])
check("off by default: any style is allowed", not sp.allow_only.isChecked() and not t.isEnabled())
sp.allow_only.setChecked(True); app.processEvents()
al = (sp.work.get("styles") or {}).get("allowed") or []
check("on: this standard's styles start ticked", "Normal" in al and all(n in rows for n in al), al[:6])
gi = next(i for i in range(sp.allow_show.count()) if sp.allow_show.itemText(i) == "Group: Headings")
sp.allow_show.setCurrentIndex(gi); app.processEvents()
shown = [t.item(i, 0).text() for i in range(t.rowCount()) if not t.isRowHidden(i)]
check("Show one kind: headings only", shown and all(n.lower().startswith(("heading", "title")) for n in shown), shown)
sp.tick_allowed(False)
al2 = sp.work["styles"]["allowed"]
check("Clear all shown untick only the shown ones", not any(n.lower().startswith("heading") for n in al2) and "Normal" in al2)
t.sortItems(1)
check("sorted by a column heading", t.isSortingEnabled())

# ---------------------------------------------------------------- headers and footers: a table, or a Quick Part
hfs = sp.tables["hf"]; ht = hfs["w"]
cols = [f for f, _h, _k in hfs["cols"]]
bi = next(i for i in range(ht.rowCount()) if ht.cellWidget(i, 0).text() == "body")
ht.cellWidget(bi, cols.index("h_table")).setText("4.5, 2"); ht.cellWidget(bi, cols.index("h_table")).textEdited.emit("4.5, 2")
b = ht.cellWidget(bi, cols.index("borders")); b.setCurrentIndex(b.findData("bottom")); app.processEvents()
bh = sp.work["hf_layouts"]["body"]["header"]
check("Header as a table: column widths in inches and the borders kept", bh.get("table") == {"widths_in": [4.5, 2.0], "borders": "bottom"}, bh)
from prodengine.engine.pkg import Package
from prodengine.pe import hf as H
import prodtemplate as PT
std = PRL.engine_ready(sp.work); std["name"] = "HF table"
std["variables"].update({"volume_name": "Volume I Technical", "solicitation": "FA8810-26-R-0042"})
job = PT.make(std, os.path.join(tmp, "out"), "", parts_dir=sp.parts_dir())
z = zipfile.ZipFile(job.copy)
hdrs = [z.read(n).decode("utf-8") for n in z.namelist() if n.startswith("word/header")]
tbl_hdr = [x for x in hdrs if "<w:tbl>" in x or "<w:tbl " in x]
check("the guarded write takes the table header", not [st for st in job.steps if st.get("key") == "hf_build" and st.get("refused")],
      [st.get("refused") for st in job.steps if st.get("key") == "hf_build"])
check("Make writes that header as a one-row table at 4.5 and 2 inches, a line under it", tbl_hdr
      and 'w:w="6480"' in tbl_hdr[0] and 'w:w="2880"' in tbl_hdr[0] and 'w:bottom w:val="single"' in tbl_hdr[0], len(hdrs))
check("the table's cells carry the left and right text with their fields", tbl_hdr and "STYLEREF" in tbl_hdr[0])
import prodwordgate as WG
if WG.available():                                  # the build PC: Word opens the template with its table header
    oc = WG.open_check(job.copy)
    print("WORD OPEN:", oc)
    check("Word opens the template with the header built as a table", oc.get("ok") and oc.get("pages", 0) >= 1, oc)
dz = sp.hf_from_quick_part("appendix", "header", "Table header")
check("Use a Quick Part as a header: kept exactly as built, its table at its widths",
      dz and 'w:w="5760"' in sp.work["hf_designs"]["appendix"]["header"] and "<w:tbl>" in sp.work["hf_designs"]["appendix"]["header"])
check("the kept design shows under Headers and footers", "appendix" in sp.hf_designs_lab.text())

# ---------------------------------------------------------------- Fields
check("Fill-ins are now Fields", dict(SECTIONS)["fillins"] == "Fields")

# ---------------------------------------------------------------- the two Editing boxes
sp.save(quiet=True)
etypes = PRL.load(cfg)["effort_types"]
e0 = etypes[0]
sp.etype_pick.setCurrentIndex(sp.etype_pick.findData(e0["id"])); sp.picked(fill_volumes=True); app.processEvents()
check("an effort type, any volume: every volume in it", sp.scope == "etype" and sp.etype_id == e0["id"])
vols = [sp.vol_pick.itemData(i) for i in range(1, sp.vol_pick.count())]
check("the Volume box lists that effort type's volumes", vols == e0["profiles"], vols)
sp.vol_pick.setCurrentIndex(1); sp.picked(); app.processEvents()
check("an effort type and a volume: that volume in it", sp.scope == "etp" and sp.type_id == vols[0])
sp.etype_pick.setCurrentIndex(0); sp.picked(fill_volumes=True); sp.vol_pick.setCurrentIndex(0); sp.picked(); app.processEvents()
check("any and any: the team standard", sp.scope == "team")
sp.vol_pick.setCurrentIndex(1); sp.picked(); app.processEvents()
check("any effort type, one volume: that volume", sp.scope == "type")
sp.scope_box.setCurrentIndex(0); app.processEvents()
check("the boxes follow the layer when it changes elsewhere", sp.etype_pick.currentIndex() == 0 and sp.vol_pick.currentIndex() == 0)

# ---------------------------------------------------------------- Make templates: read in full first
from skqt.maketemplates import MakeTemplatesDialog
md = MakeTemplatesDialog(sp)
check("Make templates opens on what you are editing, one template listed", md.choice() == "this" and md.list.count() == 1)
h = md.show_details()
check("the full view: every section of the template, before any file is written",
      all(f">{s}</h3>" in h for s in ("Styles", "Pages and margins", "Pagination by part", "Headers and footers", "Heading numbering",
                                      "Tables", "Captions", "Quick Parts", "Fields", "Fonts")), h[:200])
check("numbers read as they look in the view, never %1", "%1" not in h)
md.radios["etype"].setChecked(True); app.processEvents()
md.etype.setCurrentIndex(md.etype.findData(e0["id"])); app.processEvents()
check("every volume of an effort type: one template each, each read in full", md.list.count() == len(e0["profiles"]) and md.show_details())
check("this effort's volumes need an open effort with a structure", not md.radios["effort"].isEnabled())
md.radios["this"].setChecked(True); app.processEvents()
md.name.setEditText("Team standard test")
job2 = md.make(word=False)
check("Make writes the .dotx, named and versioned", job2 is not None and os.path.isfile(job2.copy) and "Team standard test" in os.path.basename(job2.copy))
check("the et row no longer has its own Make button", "Make templates for every volume..." not in [b.text() for b in sp.findChildren(QPushButton)])
check("one Make templates button at the top", [b.text() for b in sp.findChildren(QPushButton)].count("Make templates...") == 1)

secs = dict(TDET.sections(PRL.engine_ready(PRL.COMPANY)))
check("the details module: the team standard's pagination reads in words", "chapter (level 1) then page" in secs["Pagination by part"])
w.close()
n = sum(checks)
print(f"QT STANDARDS 325 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
