"""3.45.0 Production Standards by layer and Document sections, offscreen: the menus are Template profile, Building
blocks, Components, Document sections, Checks and Library; each built-in section has its page setup and contents
(add an element, a Quick Part, a placeholder; move; take out); Sections in order edits any section, your own too (a row
added to the page scheme gets its page setup, contents and a header built as a table); the values are the standard's.
Fictional content only."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import sectioncontents as SC, partdesigns as PD
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
from skqt.prodstdpage import GROUPS, SECTIONS
check("the menus go by layer", [sp.group_bar.tabText(i) for i in range(sp.group_bar.count())]
      == ["Template profile", "Building blocks", "Components", "Document sections", "Checks", "Library"])
check("every section has one place (27)", sp.nav.count() == 27 and len({k for k, _t in SECTIONS}) == 27)
check("building blocks hold styles, numbering and page setups; components hold Quick Parts, captions, headers and footers",
      {k for k, _t in dict(GROUPS)["Building blocks"]} >= {"styledefs", "headnum", "lists", "setups"}
      and {k for k, _t in dict(GROUPS)["Components"]} >= {"quickparts", "captions", "hf", "toc", "fillins"})
sp.nav.setCurrentRow(sp.section_index("part_body")); app.processEvents()
check("the response section is under Document sections", sp.group_bar.tabText(sp.group_bar.currentIndex()) == "Document sections")
ed = sp.part_ui["body"]["section_editor"]
ed.add_placeholder("Executive Summary", 2)
ed.add_element("lof")
check("contents added to the response: a placeholder, then an element", [r["kind"] for r in SC.items(sp.work, "body")] == ["placeholder", "element"]
      and ed.list.count() == 2 and "2 pages" in ed.list.item(0).text())
ed.list.setCurrentRow(1); ed.move(-1)
check("Up moves an item", [r["kind"] for r in SC.items(sp.work, "body")] == ["element", "placeholder"])
check("+ Quick Part with none in the standard says what to do first", ed.add_quickpart() is None)
sp.work.setdefault("quick_parts", {"one_gallery": True, "entries": []})["entries"].append({"name": "Kestrel Mission Overview", "source": "x.docx"})
ed.add_quickpart("Kestrel Mission Overview")
ed.list.setCurrentRow(0); ed.remove()
check("Take out removes the selected item", [r.get("name") or r.get("title") for r in SC.items(sp.work, "body")] == ["Executive Summary", "Kestrel Mission Overview"])
cov = sp.part_ui["cover"]["section_editor"]
check("the cover is a kept page: no contents", not cov.list.isEnabled() and "kept page" in cov.note.text())
sp.work["page_setups"]["cover_half"] = {"name": "Cover, half-inch", "w": 8.5, "h": 11, "orient": "portrait",
                                        "top": 0.5, "bottom": 0.5, "left": 0.5, "right": 0.5, "header": 0.3, "footer": 0.3}
cov.show_key("cover")
cov.setup.setCurrentIndex(cov.setup.findData("cover_half"))
check("a section's page setup is kept on its part", PD.part_of(sp.work, "cover").get("setup") == "cover_half")
cov.setup.setCurrentIndex(0)
check("By orientation takes it off", "setup" not in PD.part_of(sp.work, "cover"))
# your own section
sp.work["pagination"]["parts"].insert(3, {"key": "pastperf", "name": "Past performance", "starts": {"style": "Heading 6"},
                                          "numbers": {"fmt": "decimal", "restart": "part", "start_at": 1, "chapter_level": None},
                                          "header": "{volume_name}", "footer_marking": True, "linked": False})
sp.load_tables()
sp.nav.setCurrentRow(sp.section_index("pages")); app.processEvents()
se = sp.section_editor
se.fill()
check("Sections in order lists every section, your own included", se.pick.findData("pastperf") >= 0)
se.pick.setCurrentIndex(se.pick.findData("pastperf")); app.processEvents()
se.add_placeholder("Past Performance Citations", 3)
se.setup.setCurrentIndex(se.setup.findData("landscape"))
check("your own section takes contents and a page setup", SC.items(sp.work, "pastperf")[0]["title"] == "Past Performance Citations"
      and PD.part_of(sp.work, "pastperf")["setup"] == "landscape")
d = se.build("header", run=False)
d.cols.setCurrentRow(1); d.add_line("Past performance")
from skqt import docparts as DP
DP.finish_table(sp, "pastperf", "header", d)
check("its header is built as a table", (((sp.work.get("hf_layouts") or {}).get("pastperf") or {}).get("header") or {}).get("table", {}).get("cells"))
# 3.48.0: drag from the library onto a section
import json
from PySide6.QtCore import Qt
ed.fill_library()
libtexts = [ed.library.item(i).text() for i in range(ed.library.count())]
check("the library lists response elements and this standard's Quick Parts", any("(element)" in t for t in libtexts)
      and "Kestrel Mission Overview (Quick Part)" in libtexts, libtexts)
toc = next(ed.library.item(i) for i in range(ed.library.count()) if ed.library.item(i).data(Qt.UserRole).get("id") == "toc")
toc_title = toc.data(Qt.UserRole)["title"]
md = ed.library.mimeData([toc])
ed.list.editor.drop(json.loads(bytes(md.data("application/x-stationkeeper-section-item")).decode("utf-8")), 0)
check("a library row dropped at the top of the section goes in there", SC.items(sp.work, "body")[0] == {"kind": "element", "id": "toc",
      "title": toc_title}, SC.items(sp.work, "body"))
md2 = ed.list.mimeData([ed.list.item(0)])
ed.drop(json.loads(bytes(md2.data("application/x-stationkeeper-section-item")).decode("utf-8")), ed.list.count())
check("a content row dragged to the end moves there", SC.items(sp.work, "body")[-1]["id"] == "toc"
      and len(SC.items(sp.work, "body")) == 3)
import qpmake as QM, templatelib as TL
W_ = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
srcf = QM.make_source(tempfile.mkdtemp(), [{"name": "Kestrel Library Callout", "category": "05 Callouts", "gallery": "docParts",
                                            "xml": f'<w:p xmlns:w="{W_}"><w:r><w:t>Kestrel callout</w:t></w:r></w:p>'}])
lib = TL.Library(cfg)
TL.save_collected(lib, srcf, TL.collect(srcf, sp.work, lib)[0])
ed.fill_library()
row = next((ed.library.item(i) for i in range(ed.library.count()) if "template library" in ed.library.item(i).text()), None)
check("the template library's Quick Parts are listed to drag", row is not None and "Kestrel Library Callout" in row.text())
ed.drop([dict(row.data(Qt.UserRole))], 1)
names = [e.get("name") for e in sp.work["quick_parts"]["entries"]]
check("a template library Quick Part dropped on a section comes into the standard and the section",
      "Kestrel Library Callout" in names and SC.items(sp.work, "body")[1] == {"kind": "quickpart", "name": "Kestrel Library Callout"},
      (names, SC.items(sp.work, "body")))
check("the kept pages take no drops", not cov.library.isEnabled() and not cov.list.isEnabled())
sp.save()
import prodrules as PRL
saved = PRL.load(cfg)["company"]
check("Save keeps the contents and page setups with the standard", SC.items(saved, "body") and SC.items(saved, "pastperf")
      and PD.part_of(saved, "pastperf").get("setup") == "landscape", (saved.get("section_contents")))
w.close()
n = sum(checks)
print(f"QT SECTIONS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
