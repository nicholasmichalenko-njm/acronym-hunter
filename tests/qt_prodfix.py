"""3.6.0 Production > Fix a Copy and Production Standards, offscreen, on a Word-saved volume with planted defects:
Production holds Format Check, Fix a Copy and Production Standards; the output folder setting; Check lists every fix by
area with what it found; tables show every row's role and keys set roles; Make the fixed copy writes only a dated copy
in the output folder with its report, the original byte for byte unchanged; Production Standards edits the team, a
document type and this effort value by value (set here in bold, Reset), a row look for one table type only, the page
scheme, and saves each layer as only what it changes."""
import hashlib, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortfolders as EF, prodrules as PRL, prodcopy as PCY
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
f = w.home_page.start; f.name.setText("Osprey"); f.sol.setText("FA8810-26-R-0042"); f.create(); app.processEvents()
check("3.9: Production holds Production Standards, Audit and Fix a Copy (3.16.0: Fix a Copy last, Beta; 3.17.0: Audit)",
      list(__import__("skqt.mainwin", fromlist=["x"]).TEAM) == ["rules", "audit", "refs"])   # 3.75.0: the Team group; 3.66.0: Template Studio first; 3.38.0: Rules; 3.52.0: Production Standards under Advanced
vol = os.path.join(EF.folder(w.effort_path, "volumes"), "Volume I Technical.docx")
shutil.copy2(os.path.join(HERE, "pefix", "data", "small.docx"), vol)
before = sha(vol)
w.go("fixcopy"); app.processEvents()
pg = w.fixcopy_page
check("the default output folder is Production Copies in the data folder", pg.folder() == os.path.join(A.DATA_DIR, "Production Copies"), pg.folder())
out = os.path.join(tmp, "Copies Here")
pg.choose_folder(out)
check("the output folder setting is kept", pg.folder() == out and (A.load_settings() or {}).get("prod_output_dir") == out)
names = [pg.files.item(i).text() for i in range(pg.files.count())]
check("the Volumes folder's drafts are listed", any("Volume I Technical" in n for n in names), names)
pg.files.setCurrentRow(next(i for i, n in enumerate(names) if "Volume I Technical" in n)); app.processEvents()
check("3.6.1: the effort's solicitation shows; a draft not on the Deliverables board has no volume name yet",
      "FA8810-26-R-0042" in pg.ctx_lbl.text() and pg.vol.text() == "" and "type it" in pg.vol_src.text(), (pg.ctx_lbl.text(), pg.vol_src.text()))
chk = pg.check(wait=True)
check("3.6.1: with no volume name, headers stay off and the page says what to set", "hf_build" not in pg.plan["on"]
      and any(f["rule"] == "P11" for f in chk.findings))
pg.vol.setText("Volume I Technical"); pg.vol.textEdited.emit("Volume I Technical")
chk = pg.check(wait=True)
check("Check reads the draft: findings, tables, captions, sections", chk is not None and chk.count() > 50 and len(chk.tables) == 35
      and "35 table(s)" in pg.status.text(), pg.status.text())
fixes = {}
for i in range(pg.tree.topLevelItemCount()):
    top = pg.tree.topLevelItem(i)
    for j in range(top.childCount()):
        c = top.child(j)
        if c.data(0, Qt.UserRole):
            fixes[c.data(0, Qt.UserRole)] = c
check("every fix with work is listed and on: tables, captions, TOC, pages, headers and footers", all(k in fixes and fixes[k].checkState(0) == Qt.Checked
      for k in ("tables", "caption_typed", "caption_fields", "toc_field", "page_numbers", "hf_build")), sorted(fixes))
check("each fix lists its findings with where they are", fixes["caption_fields"].childCount() >= 6 and fixes["caption_fields"].child(0).text(2) != "")
pg.set_fix("toc_styles", False)
check("a fix can be switched off", "toc_styles" not in pg.plan["on"])
check("tables: every table with its row count", pg.tab_list.rowCount() == 35 and pg.rows.rowCount() == len(chk.tables[0]["rows"]))
n = pg.set_roles("body", rows=[2])
check("a key sets the selected rows' role, kept for the fix", n == 1 and pg.plan["table_roles"][1][chk.tables[0]["rows"][2]["i"]] == "body"
      and "(manual)" in pg.rows.item(2, 1).text())
check("broken cross-references wait for a target", pg.more_card.isVisibleTo(pg) and pg.decide.count() >= 1)
pg.word_cb.setChecked(False)
job = pg.make(wait=True, open_list=[])
check("Make the fixed copy: a dated copy in the effort's folder in the output folder", job is not None and os.path.dirname(job.copy) == os.path.join(out, "Osprey")
      and PCY.is_copy_name(job.copy) and os.path.isfile(job.copy), getattr(job, "copy", pg.status.text()))
check("its report beside it", job is not None and os.path.isfile(job.report))
import effortrec as _ER
ev = _ER.Record(w.ws.root).events(kinds=("production",))
check("3.6.1: the effort's record notes the copy", ev and os.path.basename(job.copy) in ev[0]["text"] and ev[0]["ref"]["copy"] == job.copy, ev[:1])
hdr = PCY.__name__ and __import__("zipfile").ZipFile(job.copy)
txt = " ".join(hdr.read(n).decode("utf-8", "replace") for n in hdr.namelist() if n.startswith("word/header"))
check("3.6.1: the headers name this volume and this solicitation, never a sample", "FA8810-26-R-0042" in txt and "Volume I Technical" in txt
      and "EX-26-R-0001" not in txt)
check("THE GATE: the original is byte for byte unchanged", sha(vol) == before and job.original_ok)
check("nothing was written beside the original (4.29.2: the plan's Redlines folder sits there, empty)",
      sorted(x for x in os.listdir(os.path.dirname(vol)) if os.path.isfile(os.path.join(os.path.dirname(vol), x))) == ["Volume I Technical.docx"]
      and not any(fn for _d, _s, fn in os.walk(os.path.join(os.path.dirname(vol), "Redlines"))),
      os.listdir(os.path.dirname(vol)))
check("the result shows found before and left after, and every fix", pg.res_card.isVisibleTo(pg) and pg.res_table.rowCount() == 10      # 3.17.0: Graphics
      and pg.res_steps.count() >= 8 and "original is unchanged" in pg.res_text.text(), pg.res_text.text())
tables_row = next(r for r in range(pg.res_table.rowCount()) if pg.res_table.item(r, 0).text() == "Tables")
check("tables fixed in the copy", pg.res_table.item(tables_row, 2).text() == "0", pg.res_table.item(tables_row, 2).text())
own = os.path.join(os.path.dirname(vol), "~$lume I Technical.docx"); open(own, "w").write("x")
pg.make(wait=True, open_list=[])
check("a file someone has open is not copied, and says why", "Not copied" in pg.status.text() and "owner file" in pg.status.text(), pg.status.text())
os.remove(own)
# ------------------------------------------------------------------ Production Standards
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
check("Standards opens on the team's standards, with every section (3.36.0)", sp.scope == "team" and sp.mode == "team" and sp.nav.count() == 27)   # 3.44.0: Template library   # 3.33.0: Template profile      # 3.26.0: Document parts      # 3.17.0: Graphics; 3.22.0: Quick Parts; 3.23.0: Fill-ins
sp.scope_box.setCurrentIndex(0); app.processEvents()
check("the team standard is editable", sp.scope == "team" and sp.work["variables"]["body_font"] == "Times New Roman")
tid = sp.add_type("Cost volume")
check("+ Document type adds one and opens it", sp.scope == "type" and sp.type_id == tid == "cost_volume")
it = next(i for i in sp.binder.items if i["path"] == ("variables", "table_size"))
it["w"].setValue(8.0)
check("a value set at this layer shows in bold with Reset", it["label"].font().bold() and sp.dirty)
sp.save()
d = PRL.load(cfg)
t = PRL.type_of(d, "cost_volume")
check("the document type saves only what it changes", t.get("variables") == {"table_size": 8.0} and set(t) <= {"id", "name", "variables"}, t)
sp.role_box.setCurrentIndex(sp.role_box.findData("header"))
sp.row_scope.setCurrentIndex(sp.row_scope.findData("cm"))
on, wd, col = sp.edge_widgets["left"]
on.setChecked(False)
sp.save()
t = PRL.type_of(PRL.load(cfg), "cost_volume")
check("a row look for one table type only (the compliance matrix header's left border off)",
      t["table_types"]["cm"]["override"]["header"]["edges"]["left"] is None
      and PRL.resolved_type(PRL.load(cfg), "cost_volume")["row_types"]["header"]["edges"]["left"] is not None, t.get("table_types"))
sp.preview.repaint()
check("the preview draws the table type's rows", sp.preview.table_type == "cm")
sp.nav.setCurrentRow([k for k, _t in __import__("skqt.prodstdpage", fromlist=["SECTIONS"]).SECTIONS].index("pages"))
sp.preset_box.setCurrentIndex(sp.preset_box.findData("straight"))
sp.use_preset()
check("the page scheme from a preset keeps a back cover part", [p["key"] for p in sp.work["pagination"]["parts"]] == ["all", "backer"])
sp.save()
sp.edit_effort(); app.processEvents()                    # 3.36.0: one effort's layer comes from Effort Formatting
sp.eff_type.setCurrentIndex(sp.eff_type.findData("cost_volume")); app.processEvents()
check("this effort sits on its document type", sp.base["variables"]["table_size"] == 8.0 and sp.base["pagination"]["name"].startswith("Straight"))
from skqt.custdocs import Ctx
reg = Ctx(w).reg
reg.add("Format", "Font", "11-point Arial"); reg.add("Format", "Margins", "1-inch margins")
over = sp.fill_from_rfp()
check("Fill from the RFP's formatting rules", over["variables"]["body_font"] == "Arial" and over["fonts"]["body"]["min_size"] == 11.0
      and "From the RFP" in sp.eff_said.text(), over)
eff = PRL.for_effort(cfg, w.ws)
check("the effort's standard: team, then Cost volume, then the RFP", eff["variables"]["body_font"] == "Arial" and eff["variables"]["table_size"] == 8.0
      and eff["name"] == "Cost volume" and eff.get("effort_over"))
w.go("format"); app.processEvents()
check("3.9: a link to Format Check opens Fix a Copy, reading the same standard", w.stack.currentWidget() is w.fixcopy_page
      and w.fixcopy_page.std_lbl.text().startswith("Cost volume + this effort: body Arial 11 pt"), w.fixcopy_page.std_lbl.text())
check("3.24.0: Export for review is gone", not hasattr(sp, "export"))
# ------------------------------------------------------------------ 3.7.0: document types as templates
w.go("prodstd"); app.processEvents()
sp.scope_box.setCurrentIndex(sp.scope_box.findData("type:cost_volume")); app.processEvents()
tpl = os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx")
tpl_before = sha(tpl)
got = sp.learn(tpl, keys=["styles", "variables", "heading_numbering"])
check("3.7: Learn from a file takes the chosen areas into the document type", got == ["styles", "variables", "heading_numbering"]
      and "Heading 1" in sp.work["style_defs"] and sp.work["heading_numbering"]["on"] and sp.dirty and sha(tpl) == tpl_before)
tbl = sp.tables["styledefs"]["w"]
names = [tbl.cellWidget(i, 0).text() for i in range(tbl.rowCount())]
check("3.7: the style library lists every learned style with its whole definition", "Heading 1" in names and "Normal" in names
      and tbl.columnCount() == 32, (len(names), tbl.columnCount()))      # 3.22.0: Hidden text; 3.38.0: Used on
r = names.index("Heading 2")
size_w = tbl.cellWidget(r, [c[0] for c in __import__("skqt.prodstdpage", fromlist=["STYLE_COLS"]).STYLE_COLS].index("size"))
size_w.setValue(15.0)
_cols = [c[0] for c in __import__("skqt.prodstdpage", fromlist=["STYLE_COLS"]).STYLE_COLS]
bold_w = tbl.cellWidget(r, _cols.index("bold")); bold_w.setCurrentIndex(bold_w.findData("off"))
check("3.7: a style's property edited in the library", sp.work["style_defs"]["Heading 2"]["size"] == 15.0
      and sp.work["style_defs"]["Heading 2"]["bold"] is False)
used_w = tbl.cellWidget(names.index("Normal"), _cols.index("used_on")); used_w.setCurrentIndex(used_w.findData("Body"))
check("3.38.0: a style's Used on is set in the library (Rule 5 reads it; the name decides nothing)",
      sp.work["style_defs"]["Normal"].get("used_on") == "Body", sp.work["style_defs"]["Normal"])
ab = sp.role_boxes[0]
check("3.38.0: the A number's style offers this standard's styles", ab.findData("Heading 2") >= 0, ab.count())
ab.setCurrentIndex(ab.findData("Heading 2"))
check("3.38.0: the A number's style is kept in the standard's style roles", (sp.work.get("style_roles") or {}).get("a_number") == "Heading 2",
      sp.work.get("style_roles"))
ab.setCurrentIndex(0)
sp.save()
t = PRL.type_of(PRL.load(cfg), "cost_volume")
check("3.7: the document type saves its style library", t["style_defs"]["Heading 2"]["size"] == 15.0 and "Normal" in t["style_defs"])
job = sp.make_template("", wait=True)
check("3.7: Make a template writes a dated .dotx in the output folder's Templates folder, and it passes its own check",
      job is not None and job.copy.endswith(".dotx") and " - TEMPLATE - Stationkeeper " in job.copy
      and os.path.dirname(job.copy) == os.path.join(out, "Templates") and job.check.count() == 0,
      (getattr(job, "copy", ""), [f["what"][:80] for f in getattr(getattr(job, "check", None), "findings", [])][:5]))
import zipfile as _z
st = _z.ZipFile(job.copy).read("word/styles.xml").decode("utf-8")
check("3.7: the template carries the edited style", 'w:sz w:val="30"' in st)
w.go("fixcopy"); app.processEvents()
pg.files.setCurrentRow(next(i for i in range(pg.files.count()) if "Volume I Technical" in pg.files.item(i).text())); app.processEvents()
pg.dtype.setCurrentIndex(pg.dtype.findData("cost_volume")); pg.dtype_chosen()
check("3.7: a draft takes its own document type on Fix a Copy", pg.std()["name"] == "Cost volume"
      and pg.std()["style_defs"]["Heading 2"]["size"] == 15.0 and "Cost volume" in pg.std_lbl.text(), pg.std_lbl.text())
chk = pg.check(wait=True)
check("3.7: Check lists each style that differs from the library, property by property",
      any(f["rule"] == "S4" and f["what"].startswith("Heading 2:") and "size" in f["what"] for f in chk.findings))
check("3.7: one style can be left out of the style fix from its finding", pg.set_style("Heading 2", False)
      and pg.plan["style_skip"] == ["Heading 2"] and pg.set_style("Heading 2", True) and pg.plan["style_skip"] == [])
# ------------------------------------------------------------------ 3.8.0: effort types holding document profiles
w.go("prodstd"); app.processEvents()
sp.refresh()
datas = [sp.scope_box.itemData(i) for i in range(sp.scope_box.count())]
check("3.8: Editing lists the starter effort types, each for every profile and for each profile in it",
      "etype:rfp_limited" in datas and "etp:rfp_limited:cost_volume" in datas and "etype:white_paper" in datas, datas)
sp.scope_box.setCurrentIndex(sp.scope_box.findData("etype:rfp_limited")); app.processEvents()
check("3.8: an effort type shows its profiles and default profile", sp.et_profiles.isVisibleTo(sp) and sp.et_profiles.count() == len(PRL.load(cfg)["types"]))
it = next(i for i in sp.binder.items if i["path"] == ("variables", "body_size"))
it["w"].setValue(12.0)
sp.save()
e = PRL.effort_type_of(PRL.load(cfg), "rfp_limited")
check("3.8: an effort type saves only its own rules", e.get("variables") == {"body_size": 12.0} and e["profiles"], e)
sp.scope_box.setCurrentIndex(sp.scope_box.findData("etp:rfp_limited:cost_volume")); app.processEvents()
check("3.8: the effort type's rule shows under each of its profiles", sp.work["variables"]["body_size"] == 12.0)
it = next(i for i in sp.binder.items if i["path"] == ("variables", "table_size"))
it["w"].setValue(9.0)
sp.save()
e = PRL.effort_type_of(PRL.load(cfg), "rfp_limited")
check("3.8: a change for one profile in one effort type", e["profile_over"]["cost_volume"] == {"variables": {"table_size": 9.0}}, e.get("profile_over"))
w.go("prodstd"); app.processEvents()                     # the menu: the team's standards again
sp.scope_box.setCurrentIndex(sp.scope_box.findData("type:cost_volume")); app.processEvents()
sp.match_edit.setText("cost, price"); sp.changed(); sp.save()
check("3.8: a profile says which deliverables it fits", PRL.type_of(PRL.load(cfg), "cost_volume")["match"] == ["cost", "price"])
sp.edit_effort(); app.processEvents()
sp.eff_etype.setCurrentIndex(sp.eff_etype.findData("rfp_limited")); sp.effort_etype_changed()
check("3.8: this effort takes an effort type", (w.ws.get("prod_std", {}) or {}).get("effort_type") == "rfp_limited"
      and PRL.for_effort(cfg, w.ws)["effort_type"] == "Page-limited RFP response")
costdoc = os.path.join(EF.folder(w.effort_path, "volumes"), "Volume III Cost and Price.docx")
shutil.copy2(os.path.join(HERE, "pefix", "data", "small.docx"), costdoc)
w.go("fixcopy"); app.processEvents()
pg.refresh(); app.processEvents()
pg.files.setCurrentRow(next(i for i in range(pg.files.count()) if "Cost and Price" in pg.files.item(i).text())); app.processEvents()
st8 = pg.std()
check("3.8: Fix a Copy matches the draft to its profile by name, with the effort type's rules (the RFP's own 11 pt still wins)",
      st8["name"] == "Cost volume" and st8["variables"]["table_size"] == 9.0 and st8["variables"]["body_size"] == 11.0
      and "matched by name" in pg.dtype_src.text(), (st8["name"], st8["variables"].get("table_size"), st8["variables"].get("body_size"), pg.dtype_src.text()))
w.go("prodstd"); app.processEvents()
sp.scope_box.setCurrentIndex(sp.scope_box.findData("etype:rfp_limited")); app.processEvents()
made = sp.make_templates_all()
check("3.8: Make templates for every profile in an effort type, each passing its own check",
      len(made) == len(PRL.effort_type_of(PRL.load(cfg), "rfp_limited")["profiles"]) and all(j.check.count() == 0 for j in made)
      and all(os.path.dirname(j.copy).endswith("Page-limited RFP response") for j in made), [(j.copy, j.check.count()) for j in made])
w.go("home"); app.processEvents()
f = w.home_page.start
f.name.setText("Falcon"); f.etype.setCurrentIndex(f.etype.findData("white_paper")); f.create(); app.processEvents()
check("3.8: Start an effort sets its effort type and that type's default profile",
      (w.ws.get("prod_std", {}) or {}).get("effort_type") == "white_paper" and (w.ws.get("prod_std", {}) or {}).get("type"))
# ------------------------------------------------------------------ 3.9.0: every draft at once, findings workbook
w.go("fixcopy"); app.processEvents()
pg.refresh(); app.processEvents()
before_all = {pg.files.item(i).data(Qt.UserRole): sha(pg.files.item(i).data(Qt.UserRole)) for i in range(pg.files.count())}
pg.check_all(wait=True)
t9 = pg.all_table
profs = {t9.item(r, 0).text(): t9.item(r, 1).text() for r in range(t9.rowCount())}
check("3.9: Check every draft reads each listed draft against its own profile", t9.rowCount() == pg.files.count() >= 2
      and profs.get("Volume III Cost and Price.docx") == "Cost volume" and all(int(t9.item(r, t9.columnCount() - 1).text()) > 0
                                                                               for r in range(t9.rowCount())), profs)
check("3.9: checking every draft writes nothing", all(sha(p) == h for p, h in before_all.items()))
pg.open_checked(0); app.processEvents()
check("3.9: double-click a draft to see its fixes", pg.chk is not None and pg.fix_card.isVisibleTo(pg))
xp = pg.export_findings(os.path.join(tmp, "findings.xlsx"))
from openpyxl import load_workbook
wbx = load_workbook(xp)
check("3.9: Export findings makes a workbook by draft and every finding", wbx.sheetnames == ["By draft", "Findings"]
      and wbx["By draft"].max_row - 1 >= 2 and wbx["Findings"].max_row > 20)
from tests.pefix import fixtures_tables as FT
tdoc = os.path.join(EF.folder(w.effort_path, "volumes"), "Volume IV Tables.docx")
FT.make(tdoc)
pg.refresh(); app.processEvents()
pg.files.setCurrentRow(next(i for i in range(pg.files.count()) if "Volume IV Tables" in pg.files.item(i).text())); app.processEvents()
chk9 = pg.check(wait=True)
grp = next((g for t_ in chk9.tables for g in t_["questions"] if g.startswith("R45")), None)
check("3.9: a table question to answer (a row with Total in it)", grp is not None, [g for t_ in chk9.tables for g in t_["questions"]])
rule = pg.make_rule(grp, "subtotal", "profile", recheck=False)
prof_id = pg.draft_type(pg.context()) or (w.ws.get("prod_std", {}) or {}).get("type") or PRL.load(cfg)["default"]
saved = PRL.type_of(PRL.load(cfg), prof_id).get("row_rules") or []
check("3.9: Make it a rule saves a sure rule in the draft's profile", rule is not None and rule["sure"] and rule["role"] == "subtotal"
      and any(r["key"] == rule["key"] for r in saved), (rule, [r["key"] for r in saved][:6]))
chk9b = pg.check(wait=True)
check("3.9: checked again, rows like these no longer ask", grp not in [g for t_ in chk9b.tables for g in t_["questions"]])
rule2 = pg.make_rule("R21:", "caption", "effort", recheck=False)
check("3.9: rows decided table by table (a missing caption) never become a rule", rule2 is None)
w.go("prodstd"); app.processEvents()
sp.scope_box.setCurrentIndex(sp.scope_box.findData("type:cost_volume")); app.processEvents()
ltab = sp.tables["listnum"]["w"]
check("3.9: the list numbering table shows every level of the bullets and numbers", ltab.rowCount() == 6
      and ltab.cellWidget(0, 1).text() == "List Bullet")
txt = ltab.cellWidget(1, 3); txt.setText("o"); txt.textEdited.emit("o")
fnt = ltab.cellWidget(1, 4); fnt.setText("Courier New"); fnt.textEdited.emit("Courier New")
on = next(i for i in sp.binder.items if i["path"] == ("list_numbering", "on")); on["w"].setChecked(True)
sp.save()
lnp = PRL.type_of(PRL.load(cfg), "cost_volume")["list_numbering"]
check("3.9: list numbering edited and saved in the profile", lnp["on"] and lnp["lists"][0]["levels"][1]["text"] == "o"
      and lnp["lists"][0]["levels"][1]["font"] == "Courier New" and len(lnp["lists"][1]["levels"]) == 3, lnp)
# ------------------------------------------------------------------ 3.10.0: cover and back cover pages
import docx as _docx
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Inches
cvd = _docx.Document()
cvd.add_picture(os.path.join(HERE, "pefix", "data", "Logo.png"), width=Inches(2)); cvd.add_paragraph("Program Volume", style="Title")
cvd.add_section(WD_SECTION.NEW_PAGE); cvd.add_paragraph("Introduction", style="Heading 1")
cvd.styles.add_style("Back Cover", WD_STYLE_TYPE.PARAGRAPH); cvd.add_section(WD_SECTION.NEW_PAGE)
cvd.add_paragraph("Contact", style="Back Cover")
cvp = os.path.join(tmp, "cover source.docx"); cvd.save(cvp)
w.go("prodstd"); app.processEvents()
sp.scope_box.setCurrentIndex(sp.scope_box.findData("type:cost_volume")); app.processEvents()
got10 = sp.learn(cvp, keys=["page_parts"])
check("3.10: Learn from a file takes the cover and back cover pages into the profile", got10 == ["page_parts"]
      and set(sp.work["page_parts"]) == {"cover", "backer"} and "Make a .dotx template puts it in" in sp.part_rows["cover"].text())
sp.save()
check("3.10: the profile saves its pages", set(PRL.type_of(PRL.load(cfg), "cost_volume")["page_parts"]) == {"cover", "backer"})
import prodparts as PP
tjob = sp.make_template("", wait=True)
traw = open(tjob.copy, "rb").read()
check("3.10: Make a template puts the profile's cover and back cover in", PP.signature(traw, "cover", PRL.engine_ready(sp.work))[2] == 1
      and PP.signature(traw, "backer", PRL.engine_ready(sp.work)) is not None)
sp.clear_part("backer"); sp.save()
check("3.10: a page can be cleared from the profile", set(PRL.type_of(PRL.load(cfg), "cost_volume")["page_parts"]) == {"cover"})
# ------------------------------------------------------------------ 3.11.0: Excel and PowerPoint, check only
from openpyxl import Workbook
from openpyxl.styles import Font as _XFont
xp = os.path.join(EF.folder(w.effort_path, "volumes"), "Cost Workbook.xlsx")
xwb = Workbook(); xws = xwb.active; xws.append(["Role", "Hours"]); xws.append(["Engineer", 10])
xws["A2"].font = _XFont(name="Calibri", size=11); xwb.save(xp)
xbefore = sha(xp)
w.go("fixcopy"); app.processEvents(); pg.refresh(); app.processEvents()
names = [pg.files.item(i).text() for i in range(pg.files.count())]
check("3.11: the Volumes folder's workbooks are listed with the drafts", "Cost Workbook.xlsx" in names, names)
pg.files.setCurrentRow(names.index("Cost Workbook.xlsx")); app.processEvents()
xchk = pg.check(wait=True)
tops = [pg.tree.topLevelItem(i).child(j).text(0) for i in range(pg.tree.topLevelItemCount())
        for j in range(pg.tree.topLevelItem(i).childCount())]
check("3.11: Check reads a workbook against the profile, in its own area", xchk.office == "excel" and not xchk.error
      and {f["rule"] for f in xchk.findings} >= {"X1", "X3"}, ([f["rule"] for f in xchk.findings], xchk.error))
check("3.11: its findings are listed to fix by hand in Excel", any("Fix by hand in Excel" in t for t in tops), tops)
check("3.11: Make the copy refuses a workbook (check only) and writes nothing",
      pg.make(wait=True, open_list=[]) is None and "checked only" in pg.status.text() and sha(xp) == xbefore, pg.status.text())
from pptx import Presentation as _Prs
dp = os.path.join(tmp, "Orals.pptx"); _d = _Prs(); _d.slides.add_slide(_d.slide_layouts[6]); _d.save(dp)
dbefore = sha(dp)
pg.add_file(dp); app.processEvents()
dchk = pg.check(wait=True)
check("3.11: a deck added by hand is checked as PowerPoint", dchk.office == "powerpoint" and "D7" in {f["rule"] for f in dchk.findings}
      and pg.make(wait=True, open_list=[]) is None and sha(dp) == dbefore)
w.go("prodstd"); app.processEvents()
sp.nav.setCurrentRow([k for k, _t in __import__("skqt.prodstdpage", fromlist=["SECTIONS"]).SECTIONS].index("office")); app.processEvents()
mp = next(i for i in sp.binder.items if i["path"] == ("powerpoint", "min_size"))
check("3.11: Production Standards shows the Excel and PowerPoint values", mp["w"].value() == 12)
# 3.17.0: graphics standards, previews with what changed, and Audit
SEC = [k for k, _t in __import__("skqt.prodstdpage", fromlist=["SECTIONS"]).SECTIONS]
sp.nav.setCurrentRow(SEC.index("graphics")); app.processEvents()
gp = next(i for i in sp.binder.items if i["path"] == ("graphics", "min_ppi"))
check("3.17: Production Standards has a Graphics section, with its preview", "graphics" in SEC and gp["w"] is not None
      and sp.std_preview.canvas.section == "graphics" and sp.std_preview.title.text() == "Preview: Graphics")
sp.scope_box.setCurrentIndex(sp.scope_box.count() - 1); app.processEvents()
gp = next(i for i in sp.binder.items if i["path"] == ("graphics", "min_ppi"))
gp["w"].setValue(300); app.processEvents()
rows = sp.changed_here("graphics")
check("3.17: a value set at this layer: what it was and what it is now, beside it and in the preview",
      any(w_ == 150 and n_ == 300 for _l, w_, n_ in rows) and gp["was"].isVisibleTo(sp) and gp["was"].text() == "was 150"
      and "now <b>300" in sp.std_preview.changes.text(), (rows, gp["was"].text()))
for k in SEC:                                              # every section draws without an error
    sp.nav.setCurrentRow(SEC.index(k)); app.processEvents(); sp.std_preview.canvas.grab()
check("3.17: every section has a preview", sp.std_preview.canvas.section == SEC[-1])
gp["reset"].click(); app.processEvents()
check("3.17: Reset takes it back and the was line goes", not sp.changed_here("graphics") and not gp["was"].isVisibleTo(sp))
sp.dirty = False
w.go("audit"); app.processEvents()
ap = w.audit_page
check("3.17: Audit sits in Production between Production Standards and Fix a Copy, and lists the Volumes folder",
      list(__import__("skqt.mainwin", fromlist=["x"]).TEAM) == ["rules", "audit", "refs"]
      and ap.files.count() == len([f for f in os.listdir(EF.folder(w.effort_path, "volumes")) if f.lower().endswith((".docx", ".xlsx", ".pptx"))]))
ap.add_files([vol]); app.processEvents()
vbefore = sha(vol)
res = ap.run(wait=True); app.processEvents()
check("3.17: Audit checks every file against its standard and changes nothing", res and all(c.count() >= 0 for _n, c in res.values())
      and ap.table.rowCount() == len(res) and sha(vol) == vbefore and "Nothing was changed" in ap.status.text(), ap.status.text())
xp2 = ap.export(os.path.join(tmp, "audit.xlsx"))
from openpyxl import load_workbook as _lw
check("3.17: the audit exports every finding", xp2 and _lw(xp2)["Findings"].max_row >= 2)
check("3.38.0: the export names each finding's production rule", [c.value for c in _lw(xp2)["Findings"][1]][3] == "Production rule")
ap.table.selectRow(next(i for i in range(ap.table.rowCount()) if "Volume I Technical" in ap.table.item(i, 0).text()))
ap.group_f.setCurrentIndex(ap.group_f.findData("rule")); app.processEvents()
heads = [ap.found.item(i, 0).text() for i in range(ap.found.rowCount()) if ap.found.columnSpan(i, 0) == 5]
cells = [ap.found.item(i, 1).text() for i in range(ap.found.rowCount()) if ap.found.columnSpan(i, 0) == 1 and ap.found.item(i, 1)]
check("3.38.0: Audit groups findings by production rule, each rule with its sentence, checks no rule names last",
      [h.split("  ")[0] for h in heads] == ["Rule 3", "Rule 6", "Rule 7", "Checks no rule names"] and "heading level" in heads[1]
      and any(c.startswith("Rule ") for c in cells), heads[:6])
ap.group_f.setCurrentIndex(0); app.processEvents()
check("THE GATE, at the end", sha(vol) == before)
n = sum(checks)
print(f"QT PRODFIX {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
