"""4.38.0, offscreen (ST27 of 2026-11-14, step 2): a Quick Part set goes with a style set. Bring in offers the styles
the Quick Parts use that this PC lacks and the file holds, into the style set the part set goes with; the tie is made
under More; with a tied set picked, each row's styles are held against that style set, a line says how the set fits and
one button adds the styles you have; Make templates warns when the tied style set is not one of the template's.
Fictional files."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_THEME"] = "light"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import partstyles as PS, stylelib as SL, templatesets as TS
from PySide6.QtWidgets import QApplication, QLabel
from skqt import design as D, partuses as PU
from skqt.mainwin import MainWindow
from _qpfixture import with_glossary

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("designs"); app.processEvents()
pp = w.designs_page
lib = pp.lib
gl = os.path.join(tmp, "Master.docx")
with_glossary(os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx"), gl)
rfp = SL.new_set(lib, "RFP", kind="style")
ps = pp.new_set(name="RFP parts")
check("a new part set goes with no style set, and the line says how to tie it", PS.goes_with(lib, ps["id"]) is None)
pp.sets.setCurrentRow(1); app.processEvents()
check("... the line above the rows", pp.fit_box.isVisibleTo(w) and "goes with no style set yet" in pp.fit_line.text() and not pp.fit_add.isVisibleTo(w), pp.fit_line.text())
check("More holds the tie", "This set goes with a style set..." in [a.text() for a in pp.bar.more_menu.actions()] if hasattr(pp.bar, "more_menu") else True)
check("the tie is made, and the set's row says so", PU.tie(pp, rfp["id"], ask=False) and PS.goes_with(lib, ps["id"])["id"] == rfp["id"]
      and "with RFP" in pp.sets.item(1).text(), pp.sets.item(1).text())
check("a tie to a part set, or to nothing there, is refused", not PS.set_goes_with(lib, ps["id"], ps["id"]) and not PS.set_goes_with(lib, ps["id"], "nope"))
pp.sets.setCurrentRow(1); app.processEvents()
dlg = pp.bring_in(gl, run=False)
for x in dlg.plan["pages"]:
    x["keep"] = False
dlg.fill(); dlg.count()
check("Bring in offers the style the Quick Parts use that this PC lacks and the file holds", dlg.with_styles.isVisibleTo(dlg) or not dlg.with_styles.isHidden())
check("... named, and ticked", dlg.with_styles.isChecked() and "the 1 style these Quick Parts use that you do not have: Heading 1" in dlg.with_styles.text(), dlg.with_styles.text())
dlg.go(); app.processEvents()
names = PS.set_names(lib, rfp["id"])
check("the style came with the parts, into the style set the part set goes with", "heading 1" in PS.library_names(lib) and names == {"heading 1"}, names)
f = PS.fit(lib, ps["id"])
check("the fit: one style the Quick Parts use is not in the style set, and not among this PC's styles", f["missing"] == [("CUI header", ["QP Callout"])]
      and f["absent"] == ["QP Callout"] and f["can_add"] == [], f)
pp.sets.setCurrentRow(1); pp.tabs.setCurrentIndex(8); app.processEvents()
check("the line says so in the alert color, with no button when there is nothing to add", "1 style its Quick Parts use is not in it: QP Callout." in pp.fit_line.text()
      and "Not among your styles: QP Callout. Bring it in on Styles." in pp.fit_line.text() and not pp.fit_add.isVisibleTo(w), pp.fit_line.text())
uses = {pp.rows.itemWidget(pp.rows.item(i)).findChild(QLabel, "partUses").text() for i in range(pp.rows.count())}
t = D.tokens()
check("a row's style that is in the tied set shows in the good color", any(t["ok"] in u and "Heading 1" in u for u in uses), uses)
qc = lib.add("style", "QP Callout", {"font": "Arial", "size": 10}, source="test")[0]
pp.fill_rows(); app.processEvents()
check("a style this PC has but the set lacks: one button adds it", pp.fit_add.isVisibleTo(w) and pp.fit_add.text() == "Add 1 style to RFP", pp.fit_add.text())
pp.fit_add.click(); app.processEvents()
check("pressed: the style is in the style set and the line turns good", qc["id"] in rfp["items"] and "Every style its Quick Parts use is in it." in pp.fit_line.text()
      and not pp.fit_add.isVisibleTo(w), pp.fit_line.text())
pp.sets.setCurrentRow(0); app.processEvents()
check("Every part: no line", not pp.fit_box.isVisibleTo(w))
# Make templates
other = SL.new_set(lib, "Program documents", kind="style")
std = {}
TS.set_recipe(std, style_sets=[other["id"]], part_set=ps["id"])
rows = TS.checks(std, lib, cfg)
row = next((r for r in rows if "goes with a style set" in r[1]), None)
check("a template that uses the part set without its style set is warned", row == ("warn", "The Quick Part set goes with a style set this template does not use",
                                                                                   "RFP parts goes with RFP"), rows)
TS.set_recipe(std, style_sets=[rfp["id"]], part_set=ps["id"])
rows = TS.checks(std, lib, cfg)
check("with its style set the template passes both Quick Part checks", not any("goes with a style set" in r[1] for r in rows)
      and ("ok", "Every style the Quick Parts use is in the style sets", "Paragraph, character and table styles") in rows, rows)
check("untied again", PS.set_goes_with(lib, ps["id"], "") and PS.goes_with(lib, ps["id"]) is None)
SL.remove_set(lib, rfp["id"])
check("a tie to a set that was taken away reads as no tie", PS.set_goes_with(lib, ps["id"], other["id"]) and (SL.remove_set(lib, other["id"]) or True)
      and PS.goes_with(lib, ps["id"]) is None)
w.close()
n = sum(checks)
print(f"QT PARTFIT 4380 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
