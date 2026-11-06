"""3.71.0 offscreen: Setup > From an outline workbook... (the columns guessed, the looks of a mixed column with the setup
style each takes, the preview drawing each block in its setup style's look and marking hidden text, the problems),
Use this structure into an effort with no compliance matrix yet (one is made), and Setup > Setup styles... (name, font,
size, color, bold, italic, hidden; a sample; Save for this effort; Use for every effort; Put them in this effort's
template). Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, workspace as W, prodrules as PRL, setupdoc as SD, compliance as C
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
import test_outline371 as T                                  # its fictional workbook (its own checks run too)
xl = T.make_outline(os.path.join(tmp, "Kestrel Outline.xlsx"))
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
pg = w.setups_page
check("no compliance matrix yet", w.review is None)
# the window, without accepting it
pg.from_outline(xl, accept=False)
dlg = pg.outline_dialog
roles = {dlg.cols.item(i, 0).text(): dlg.cols.cellWidget(i, 1).currentData() for i in range(dlg.cols.rowCount())}
check("columns guessed from the headings", roles["Compliance Requirement"] == "requirement" and roles["Supporting RFP Content"] == "support"
      and roles["Response Section Number"] == "section_number" and len(roles) == 7, roles)
rr = {dlg.rules.cellWidget(i, 1).text().split("(")[-1].split(")")[0]: dlg.rules.cellWidget(i, 3) for i in range(dlg.rules.rowCount())}
check("the looks of the mixed column, each with the setup style it takes", dlg.rules.rowCount() == 2 and set(rr) == {"italic black", "#6B21A8"}, list(rr))
rr["#6B21A8"].setCurrentIndex(rr["#6B21A8"].findData("customer")); app.processEvents()
htm = dlg.preview.toHtml()
check("the preview draws the structure and every block with its reference", "1.1 Ground Segment Architecture" in htm
      and "L.4.2.1: The offeror shall describe its ground segment architecture." in htm)
check("customer text now in its style's color", "#6b21a8" in htm.lower(), htm[:400])
check("hidden text is marked with a gray band", "background-color:#ECEEF3" in dlg.html and "Hidden text shows on a gray band" in dlg.top.text())
check("the problems are listed", any("again after" in dlg.problems.item(i).text() for i in range(dlg.problems.count())))
check("the columns and rules are saved for next time", dlg.save_profile("Kestrel outline") == "Kestrel outline")
dlg.close()
# use it
n = pg.from_outline(xl, accept=True)
check("Use this structure: a compliance matrix is made and holds the structure and the placed requirements",
      n and w.review is not None and [C.outline_label(o) for o in w.review.M.outline][1] == "1.1 Ground Segment Architecture"
      and len(SD.placed_in(w.review.M)["1.1 Ground Segment Architecture"]) == 6, n)
check("the saved rules were used again (the customer text has its own kind)", any(it.get("decision") == "Customer" for it in w.review.M.items))
# setup styles
sd = pg.styles(modal=False)
r = sd.rows["rfp"]
r["style"].setText("Compliance Requirement"); r["style"].textEdited.emit("Compliance Requirement")
r["bold"].setChecked(True); r["color"].setText("7030A0"); r["color"].textEdited.emit("7030A0")
s = sd.rows["support"]; s["style"].setText("Supporting RFP Text"); s["italic"].setChecked(True); s["color"].setText("000000")
check("the sample shows the look as it is set", "font-weight:bold" in r["sample"].text() and "font-style:italic" in s["sample"].text())
sd.save()
o = pg.setup_opts()
check("Save for this effort: the effort's setup styles", o["rfp"]["style"] == "Compliance Requirement" and o["rfp"]["bold"] is True
      and o["support"]["italic"] is True and "content_map" in ((w.ws.get("prod_std") or {}).get("over") or {}))
sd.save(team=True)
check("Use for every effort: the global standard holds them", PRL.load(cfg)["company"]["content_map"]["rfp"]["style"] == "Compliance Requirement")
names = sd.to_template()
check("Put them in this effort's template", "Supporting RFP Text" in names
      and (w.ws.get("prod_std") or {})["over"]["style_defs"]["Supporting RFP Text"]["italic"] == "on")
sd.close()

print(f"QT OUTLINE 371 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
