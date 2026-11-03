"""3.26.0 Production Standards > Document parts, offscreen: Cover, Front matter, Response, Appendices and Back cover as
the first menu; each part shows and edits the same values the other menus hold (no copies): where it starts and how its
pages are numbered, its header and footer (tab stops, a table, a Quick Part kept as built); its page, TOC or captions;
what it shares with every part; a drawn preview with the page number as it reads; Save this part as a design and Use a
saved design on another part, through the template library's Part designs."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import prodrules as PRL, templatelib as TL, partdesigns as PD
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
SRC = os.path.join(tmp, "Team Master.dotx")
with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), SRC, table_hdr=True)
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
from skqt import docparts as DP
from skqt.prodstdpage import SECTIONS

check("Document parts is the menu after Template profile (3.33.0), with every part", sp.group_bar.tabText(1) == "Document parts"
      and [sp.section_bar.tabText(i) for i in range(sp.section_bar.count())] == ["Cover", "Front matter", "Response", "Appendices", "Back cover"])
check("Production Standards opens on the cover", sp.section_key() == "part_cover")
sp.nav.setCurrentRow(sp.section_index("part_body")); app.processEvents()
ui = sp.part_ui["body"]; wd = ui["w"]
part = PD.part_of(sp.work, "body")
check("the Response part shows its own numbering", wd["fmt"].currentData() == (part.get("numbers") or {}).get("fmt")
      and wd["start"].text() == "Heading 1" and wd["chapter_level"].value() == 1)
check("the page number reads as it will in the document", DP.page_number(part["numbers"], 1) == "1-1"
      and DP.page_number({"fmt": "lowerRoman", "start_at": 1}, 3) == "iii"
      and DP.page_number({"fmt": "decimal", "chapter_level": 7, "separator": "hyphen"}, 2) == "A-2")
# edit the header here: the same value the Headers and footers section shows
wd["header_left"].setText("{volume_name} draft"); wd["header_left"].textEdited.emit("x"); app.processEvents()
check("a change here is the same value Pages > Headers and footers holds", sp.work["hf_layouts"]["body"]["header"]["left"] == "{volume_name} draft")
hfs = sp.tables["hf"]; ht = hfs["w"]
bi = next(i for i in range(ht.rowCount()) if ht.cellWidget(i, 0).text() == "body")
check("... and the Headers and footers table shows it", ht.cellWidget(bi, 1).text() == "{volume_name} draft")
wd["header_table"].setText("4.5, 2"); wd["header_table"].textEdited.emit("x")
wd["borders"].setCurrentIndex(wd["borders"].findData("bottom")); app.processEvents()
check("the header as a table, from the part", sp.work["hf_layouts"]["body"]["header"]["table"] == {"widths_in": [4.5, 2.0], "borders": "bottom"})
wd["fmt"].setCurrentIndex(wd["fmt"].findData("upperRoman")); app.processEvents()
check("numbering edited here is the pagination's", PD.part_of(sp.work, "body")["numbers"]["fmt"] == "upperRoman")
sp.nav.setCurrentRow(sp.section_index("pages")); app.processEvents()
pt = sp.tables["pages"]
row = next(i for i in range(pt["w"].rowCount()) if pt["w"].cellWidget(i, 0).text() == "body")
fcol = next(c for c, (f, _h, _k) in enumerate(pt["cols"]) if f == "fmt")
check("... and Pagination and covers shows it", pt["w"].cellWidget(row, fcol).currentData() == "upperRoman")
img = ui["preview"].grab()
check("the part's preview draws", not img.isNull() and img.width() > 100)
# a Quick Part as the appendix header
sp.add_quick_parts(SRC, picks=["Table header"])
sp.hf_from_quick_part("appendix", "header", "Table header")
DP.fill(sp, "appendix")
check("the appendix shows its kept design", "header" in sp.part_ui["appendix"]["design_lab"].text())
check("captions for the part", "Table" in sp.part_ui["appendix"]["cap_lab"].text() or "No caption rule" in sp.part_ui["appendix"]["cap_lab"].text())
check("the front matter shows its TOC", "Heading 1" in sp.part_ui["front"]["toc_lab"].text())
check("the cover says its page", "base page" in sp.part_ui["cover"]["page_lab"].text())
check("what every part shares is shown, not copied", "Margins" in ui["shared_lab"].text())
# save the appendix as a design and use it on the body
item = DP.save_design(sp, "appendix", name="Space Force appendix")
lib = TL.Library(cfg)
check("Save this part as a design: in the template library's Part designs", item and any(i["kind"] == "part" for i in lib.items)
      and dict(TL.SHELVES)["part"] == "Part designs")
said = DP.use_design(sp, "body", iid=item["id"])
check("Use a saved design on another part: its header design and numbering come over", said
      and "<w:tbl>" in sp.work["hf_designs"]["body"]["header"]
      and PD.part_of(sp.work, "body")["numbers"] == PD.part_of(sp.work, "appendix")["numbers"]
      and PD.part_of(sp.work, "body")["key"] == "body", PD.part_of(sp.work, "body"))
smp = DP.open_sample(sp, "body", open_it=False)
check("Open a sample in Word: a sample template in the Samples folder", smp and smp.endswith(".dotx") and os.path.basename(os.path.dirname(smp)) == "Samples", smp)
check("saved: Save keeps it", sp.save(quiet=True) is not False)
w.close()
n = sum(checks)
print(f"QT DOCPARTS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
os._exit(0 if n == len(checks) else 1)
