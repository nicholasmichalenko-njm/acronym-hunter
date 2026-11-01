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
from skqt import theme
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest(), os.stat(p).st_mtime_ns


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey"); f.sol.setText("FA8810-26-R-0042"); f.create(); app.processEvents()
check("Production holds Format Check, Fix a Copy and Production Standards",
      [k for g, it in RAIL if g == "Production" for k, _l in it] == ["format", "fixcopy", "prodstd"])
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
check("nothing was written beside the original", sorted(os.listdir(os.path.dirname(vol))) == ["Volume I Technical.docx"],
      os.listdir(os.path.dirname(vol)))
check("the result shows found before and left after, and every fix", pg.res_card.isVisibleTo(pg) and pg.res_table.rowCount() == 9
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
check("Standards opens on this effort, with every section", sp.scope == "effort" and sp.nav.count() == 14)
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
sp.scope_box.setCurrentIndex(sp.scope_box.findData("effort:")); app.processEvents()
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
check("Format Check reads the same standard", w.format_page.std_lbl.text().startswith("Cost volume + this effort: body Arial 11 pt"),
      w.format_page.std_lbl.text())
x = sp.export(os.path.join(tmp, "std.xlsx"))
check("Export for review", os.path.isfile(x))
check("THE GATE, at the end", sha(vol) == before)
n = sum(checks)
print(f"QT PRODFIX {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
