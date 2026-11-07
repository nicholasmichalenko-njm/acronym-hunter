"""3.4.0 Deliver > Final Checks, offscreen: the package folder is remembered and the required list fills from the
deliverables; Check the package lists each PDF with its problems and what is missing; Check the drafts finds numbering
and reference problems in the Volumes folder's drafts; Compare two drafts counts the changes by heading and exports a
redline; each check exports its file."""
import os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortrec as RR, deliverables as DL, docxw, effortfolders as EF
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, RAIL, TABS as MW_TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey"); f.sol.setText("FA8810-26-R-0042"); f.create(); app.processEvents()
rec = RR.Record(w.ws.root)
DL.add(rec, "Volume I Technical", kind="Volume"); DL.add(rec, "SF 33", kind="Form")
check("Final Checks is a tab of Final Check in Check and Submit, after Submission Check (3.58.0)",
      [k for g, it in RAIL if g == "Submit" for k, _l in it][:1] == ["finalcheck"] and [k for k, _t in MW_TABS["finalcheck"]] == ["finalcheck", "qa", "checks"])   # 3.75.0: Submit
vdir = EF.folder(w.effort_path, "volumes")
d = docxw.Doc(); d.heading("1.1 Approach", 2); d.para("See Figure 2."); d.para("Figure 1. The bus")
d.save(os.path.join(vdir, "Volume I Technical v1.docx"))
d = docxw.Doc(); d.heading("1.1 Approach", 2); d.para("See Figure 1 for the bus."); d.para("Figure 1. The bus")
d.save(os.path.join(vdir, "Volume I Technical v2.docx"))
w.go("checks"); app.processEvents()
pg = w.checks_page
check("the required list fills from the deliverables, the name rule from the solicitation", pg.required.toPlainText().splitlines()
      == ["Volume I Technical", "SF 33"] and pg.contain.text() == "FA8810-26-R-0042", (pg.required.toPlainText(), pg.contain.text()))
pk = os.path.join(tmp, "Final"); os.makedirs(pk)
shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp_hard", "Hard_RFP.pdf"), os.path.join(pk, "FA8810-26-R-0042_Volume_I_Technical.pdf"))
pg.choose_folder(pk)
r = pg.check_package()
check("Check the package: each PDF, and what is missing", pg.pkg_table.rowCount() == 2 and r["missing"] == ["SF 33"]
      and "1 problem" in pg.pkg_sum.text(), (r["missing"], pg.pkg_sum.text()))
check("the package folder is remembered for the effort", w.ws.get("final_dir") == pk)
check("Export... the package check", os.path.isfile(pg.export_package(os.path.join(tmp, "p.xlsx"))))
out = pg.check_xref()
kinds = [pg.x_table.item(k, 1).text() for k in range(pg.x_table.rowCount())]
check("Check the drafts: numbering and references in the Volumes folder's drafts", len(out) == 2 and "Figure not found" in kinds
      and "Figure never mentioned" in kinds, kinds)
check("Export... the cross-reference check", os.path.isfile(pg.export_xref(os.path.join(tmp, "x.xlsx"))))
pg.older.setCurrentIndex(pg.older.findText("Volume I Technical v1")); pg.newer.setCurrentIndex(pg.newer.findText("Volume I Technical v2"))
c = pg.compare()
check("Compare two drafts: the changes, by heading", c and c["counts"]["changed"] == 1 and "1.1 Approach" in pg.c_sum.text(), pg.c_sum.text())
rl = pg.export_redline(os.path.join(tmp, "red.docx"))
check("Export the redline: a Word file", "w:strike" in zipfile.ZipFile(rl).read("word/document.xml").decode("utf-8"))
check("the exports have names in Folders and file names", "Final_Package_Check" in w.out_path("package_check")
      and "Cross_Reference_Check" in w.out_path("xref_check") and "Draft_Redline" in w.out_path("draft_redline", Doc="V"))
w.close()
n = sum(checks)
print(f"QT CHECKS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
