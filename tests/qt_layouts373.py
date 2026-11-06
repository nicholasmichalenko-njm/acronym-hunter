"""3.73.0 offscreen: Setup > Outline layouts... (the starting layout's names, another name added, a rule by color added
with a sample in its look, saved), then an outline workbook with a renamed column and an extra one: the import uses the
layout (the purple text already customer requirement text, by the rule), says which columns are new, and what the
person picks for one is remembered. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, outlinelayouts as OL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
import test_layouts373 as TL                                  # its workbook maker (its own checks run too)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
pg = w.setups_page
dlg = pg.layouts(modal=False); app.processEvents()
check("the starting layout: the column names given", dlg.pick.currentText() == OL.STARTING
      and dlg.names["requirement"].toPlainText() == "Compliance Requirement" and dlg.rules.rowCount() == 1)
dlg.names["requirement"].setPlainText("Compliance Requirement\nL Requirement")
i = dlg.add_rule("support", {"color": "6B21A8", "italic": None, "bold": None, "kind": "customer"}); app.processEvents()
check("a rule by color with a sample in its look", "#6B21A8" in dlg.rules.cellWidget(i, 5).text(), dlg.rules.cellWidget(i, 5).text())
dlg.save(); dlg.close()
lay = OL.load(cfg)[OL.STARTING]
check("saved: another name, and the rule", "L Requirement" in lay["names"]["requirement"]
      and OL.rule_kind(lay, "support", "--6B21A8") == "customer")
renamed = TL.GIVEN[:3] + ["L Requirement"] + TL.GIVEN[4:] + ["Volume"]
xl = TL.make(os.path.join(tmp, "Kestrel Outline v2.xlsx"), renamed)
pg.from_outline(xl, accept=False)
od = pg.outline_dialog
roles = {od.cols.item(r, 0).text(): od.cols.cellWidget(r, 1).currentData() for r in range(od.cols.rowCount())}
check("the import uses the layout: the renamed column known by its other name", roles["L Requirement"] == "requirement", roles)
check("it says which column is new", "Volume" in od.new_cols.text() and "L Requirement" not in od.new_cols.text(), od.new_cols.text())
kinds = {od.rules.cellWidget(r, 1).text().split("(")[-1].split(")")[0]: od.rules.cellWidget(r, 3).currentData() for r in range(od.rules.rowCount())}
check("the purple text is customer requirement text by the rule, before anyone picks", kinds.get("#6B21A8") == "customer"
      and kinds.get("italic black") == "support", kinds)
row = next(r for r in range(od.cols.rowCount()) if od.cols.item(r, 0).text() == "Volume")
cb = od.cols.cellWidget(row, 1)
check("the new column takes a guess meanwhile, and Remember these columns is offered", cb.currentData() == "ignore" and od.b_keep_new.isVisibleTo(od))
cb.setCurrentIndex(cb.findData("authors")); app.processEvents()
check("what the person picks for the new column is remembered", "Every column is in the layout" in od.new_cols.text()
      and OL.role_of(OL.load(cfg)[OL.STARTING], "Volume") == "authors" and not od.b_keep_new.isVisibleTo(od))
od.close()
L3 = OL.load(cfg); L3[OL.STARTING]["names"]["authors"].remove("Volume"); OL.save(cfg, L3)
pg.from_outline(xl, accept=True)
check("Use this structure remembers a new column as it was guessed (the guess was right: leave it out)",
      OL.role_of(OL.load(cfg)[OL.STARTING], "Volume") == "ignore")

print(f"QT LAYOUTS 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
