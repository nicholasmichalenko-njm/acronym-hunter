"""3.5.0 Production, offscreen: the Production group sits before Effort Files; Format Check lists the Volumes folder's
drafts and a file added from anywhere, reads them against the standard (the originals unchanged), fills the tiles and
the findings, exports; Production Standards saves a document type and a new one, and fills the effort's own values from
the RFP's formatting rules, which Format Check then uses."""
import hashlib, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortfolders as EF, prodstd as PS, prod_fixture as FX
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow, RAIL
from skqt.custdocs import Ctx

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def fp(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest(), os.stat(p).st_mtime_ns


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey"); f.sol.setText("FA8810-26-R-0042"); f.create(); app.processEvents()
groups = [g for g, _it in RAIL]
check("Production sits before Effort Files, with Format Check and Production Standards",
      groups.index("Production") == groups.index("Effort Files") - 1
      and [k for g, it in RAIL if g == "Production" for k, _l in it] == ["format", "prodstd"], groups)
vol = FX.build(os.path.join(EF.folder(w.effort_path, "volumes"), "Volume I Technical.docx"))
os.makedirs(os.path.join(tmp, "elsewhere")); other = FX.build(os.path.join(tmp, "elsewhere", "Annex.docx"))
before = (fp(vol), fp(other))
w.go("format"); app.processEvents()
pg = w.format_page
names = [pg.files.item(i).text() for i in range(pg.files.count())]
check("Format Check lists the Volumes folder's drafts", "Volume I Technical.docx" in names or "Volume I Technical" in names, names)
check("the standard in words", pg.std_lbl.text().startswith("Proposal volume: body Times New Roman 12 pt, tables Arial 10 pt, margins 1 in, Letter"),
      pg.std_lbl.text())
pg.add_file(other)
res = pg.run(); app.processEvents()
check("Check reads every listed draft", len(res) == 2 and all(not r["error"] for r in res), [r["error"] for r in res])
check("the findings table and the tiles", pg.table.rowCount() == sum(len(r["findings"]) for r in res) and pg.tiles.count() == len(PC_AREAS := [a for a in pg.area_checks])
      and "2 drafts read" in pg.summary.text(), (pg.table.rowCount(), pg.summary.text()))
check("THE GATE: neither original changed", (fp(vol), fp(other)) == before)
pg.area_checks["Fonts"].setChecked(False)
res2 = pg.run()
check("an area left unchecked is not read", not any(f_["area"] == "Fonts" for r in res2 for f_ in r["findings"]) and pg.tiles.count() == len(PC_AREAS) - 1)
pg.area_checks["Fonts"].setChecked(True)
pg.files.item(1).setCheckState(Qt.Unchecked); w.go("home"); w.go("format"); app.processEvents()
check("an added file and an unchecked draft are kept when the page comes back", pg.files.count() == 2 and pg.files.item(1).checkState() == Qt.Unchecked)
x = pg.export(os.path.join(tmp, "fc.xlsx"))
check("Export...", os.path.isfile(x))
# the standards
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
check("Production Standards shows the built-in type and this effort's card", sp.type.currentText() == "Proposal volume" and sp.font_rows["body"][0].text() == "Times New Roman"
      and not sp.eff.isHidden())
sp.font_rows["table"][1].setValue(9); sp.margins.setValue(0.75); sp.save()
check("Save keeps the team's type", PS.load(cfg)["types"][0]["fonts"]["table"]["min"] == 9 and PS.load(cfg)["types"][0]["margins_in"] == 0.75)
check("a new document type, copied from the one shown", sp.add_type("Cost volume") == "Cost volume" and sp.type.currentText() == "Cost volume"
      and [t["name"] for t in PS.load(cfg)["types"]] == ["Proposal volume", "Cost volume"])
check("a name already used is refused", sp.add_type("Cost volume") == "")
reg = Ctx(w).reg
reg.add("Format", "Font", "11-point Arial"); reg.add("Format", "Margins", "1-inch margins")
over = sp.fill_from_rfp()
check("Fill from the RFP's formatting rules", over.get("fonts", {}).get("body", {}).get("font") == "Arial" and over.get("margins_in") == 1.0
      and "From the RFP: Font: 11-point Arial" in sp.eff_text.text(), (over, sp.eff_text.text()))
w.go("format"); app.processEvents()
check("Format Check now uses the effort's values", pg.std_lbl.text().startswith("Proposal volume + this effort: body Arial 11 pt") and "margins 1 in" in pg.std_lbl.text(),
      pg.std_lbl.text())
w.go("prodstd"); sp.clear_effort(); w.go("format"); app.processEvents()
check("Clear goes back to the document type", pg.std_lbl.text().startswith("Proposal volume: body Times New Roman") and "margins 0.75 in" in pg.std_lbl.text(), pg.std_lbl.text())
check("THE GATE, at the end", (fp(vol), fp(other)) == before)
n = sum(checks)
print(f"QT PROD {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
