"""3.42.0 the header and footer builder, offscreen. Document parts > Response: the footer is Rule 7's table by default
(its boxes give way to the builder and say so); Build the header as a table adds columns, lines with their alignment,
size and bold, and a logo, and the preview draws it; editing the part's other boxes keeps the table; the Headers and
footers table keeps it too; Use Rule 7's footer puts the A number, the marking and the team's line, and the page;
Save as a Quick Part adds it to the standard's Quick Parts in the Headers gallery; Back to plain text removes the table.
Fictional content only."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import hfbuild as HB
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import docparts as DP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from PIL import Image
logo = os.path.join(tmp, "kestrel_logo.png")
Image.new("RGB", (300, 100), (31, 56, 100)).save(logo, "PNG")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
sp.nav.setCurrentRow(sp.section_index("part_body")); app.processEvents()
ui = sp.part_ui["body"]; wd = ui["w"]
check("the Response footer is Rule 7's table by default", HB.is_r7(sp.work["hf_layouts"]["body"]["footer"]))
check("... its plain boxes give way to the builder, and the part says so", not wd["footer_left"].isEnabled() and wd["header_left"].isEnabled()
      and "footer" in ui["table_lab"].text() and "Rule 7" in ui["table_lab"].text(), ui["table_lab"].text())

d = DP.build_table(sp, "body", "header", run=False)
check("Build the header as a table starts with three columns", len(d.cells()) == 3 and d.cols.count() == 3)
d.cols.setCurrentRow(0); d.pick_logo(logo)
check("a logo in the first column, its height from the picture", (d.cells()[0]["logo"] or {}).get("name") == "kestrel_logo.png"
      and abs(d.cells()[0]["logo"]["h_in"] - d.cells()[0]["logo"]["w_in"] / 3) < 0.02, d.cells()[0]["logo"] and d.cells()[0]["logo"]["h_in"])
d.cols.setCurrentRow(1); d.add_line("{volume_name}")
d.lines.cellWidget(0, 3).setChecked(True); d.lines.cellWidget(0, 2).setValue(9)
check("a line in the middle column: centered, bold, 9 pt", d.cells()[1]["lines"] == [{"text": "{volume_name}", "align": "center", "size": 9.0, "bold": True}],
      d.cells()[1]["lines"])
d.cols.setCurrentRow(2); d.width.setValue(1.75)
d.borders.setCurrentIndex(d.borders.findData("below"))
check("the third column's width and a line under", d.cells()[2]["width_in"] == 1.75 and d.spec["table"]["borders"] == "below")
d.add_col(); d.del_col()
check("a column added and removed", len(d.cells()) == 3)
img = d.preview.grab()
check("the builder's preview draws", not img.isNull() and img.width() > 100)
DP.finish_table(sp, "body", "header", d)
check("OK keeps the table in the part's header", (sp.work["hf_layouts"]["body"]["header"].get("table") or {}).get("cells")
      and not wd["header_left"].isEnabled())
wd["start_at"].setValue(3); app.processEvents()
check("editing the part's other boxes keeps both tables", HB.cells_of(sp.work["hf_layouts"]["body"]["header"])
      and HB.is_r7(sp.work["hf_layouts"]["body"]["footer"]))
check("the part's preview draws the tables", not ui["preview"].grab().isNull())
sp.nav.setCurrentRow(sp.section_index("hf")); app.processEvents()
ht = sp.tables["hf"]["w"]
bi = next(i for i in range(ht.rowCount()) if ht.cellWidget(i, 0).text() == "body")
sp.tables["hf"]["w"].cellWidget(bi, 1).setText("ignored left"); sp.tables["hf"]["w"].cellWidget(bi, 1).textEdited.emit("x"); app.processEvents()
check("the Headers and footers table keeps a table built here", HB.cells_of(sp.work["hf_layouts"]["body"]["header"])
      and HB.is_r7(sp.work["hf_layouts"]["body"]["footer"]), sp.work["hf_layouts"]["body"])

d2 = sp.hf_build_table("appendix", "footer", run=False)
d2.cols.setCurrentRow(0); d2.add_line("Draft")
d2.use_r7()
mid = d2.cells()[1]["lines"]
check("Use Rule 7's footer: the A number, the marking and the team's line (blank until typed), the page",
      HB.is_r7(d2.result_spec()) and mid[0]["text"] == "{marking}" and mid[1]["text"] == "{team_line}" and "blank until" in d2.msg.text())
d2.cols.setCurrentRow(1); d2.lines.item(1, 0).setText("Kestrel standard line")
check("the team's line is typed in the builder", d2.cells()[1]["lines"][1]["text"] == "Kestrel standard line")
DP.finish_table(sp, "appendix", "footer", d2)
check("the appendix footer is Rule 7's with the team's line", sp.work["hf_layouts"]["appendix"]["footer"]["table"]["cells"][1]["lines"][1]["text"]
      == "Kestrel standard line")

d3 = DP.build_table(sp, "body", "header", run=False)
e = d3.save_qp("Kestrel header")
check("Save as a Quick Part: in the standard's Quick Parts, Headers gallery, its Word file kept with the parts", e and e["gallery"] == "hdrs"
      and any(x["name"] == "Kestrel header" for x in sp.work["quick_parts"]["entries"])
      and os.path.isfile(os.path.join(sp.parts_dir(), e["source"])), e)
check("... and the dialog says where it went", "Headers gallery" in d3.msg.text(), d3.msg.text())
d3.plain()
DP.finish_table(sp, "body", "header", d3)
check("Back to plain text removes the table and frees the boxes", not (sp.work["hf_layouts"]["body"]["header"].get("table") or {}).get("cells")
      and wd["header_left"].isEnabled())

# 3.48.0: fields by name
d4 = sp.hf_build_table("front", "header", run=False)
d4.cols.setCurrentRow(0)
d4.insert_field("solicitation")
check("Insert a field with no line chosen adds a line holding the field", d4.cells()[0]["lines"][-1]["text"] == "{solicitation}")
d4.lines.setCurrentCell(len(d4.cells()[0]["lines"]) - 1, 0)
d4.insert_field("page")
check("... and with a line chosen puts the field at its end", d4.cells()[0]["lines"][-1]["text"] == "{solicitation} {page}")
check("the builder's field menu is beside the line buttons", d4.field_btn.isEnabled() and d4.field_btn.text() == "Insert a field")
wd["fields"].last = wd["footer_center"]
wd["fields"].pick("team_line")
check("Document sections' header and footer boxes take a field where the cursor is", "{team_line}" in wd["footer_center"].text())
d4.reject()

w.close()
n = sum(checks)
print(f"QT HF BUILDER {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
