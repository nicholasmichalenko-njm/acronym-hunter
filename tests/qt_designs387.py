"""3.87.0 offscreen: Production > Section designs, a tab beside Layout: empty, one way in; Bring in from Word... onto a
shelf; what fills it edited in its row; text other pages read; act on the row (Open in Word, Replace..., Remove); one
command bar with Bring in from Word... as its one main button. Setup > More > Section designs... picks a design per
section (None only where optional); Make the setup writes each picked design filled beside the setup. Fictional (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, sectiondesigns as SDZ, setuptemplate as ST
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow, TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
STY = (f'<w:styles {WNS}><w:style w:type="paragraph" w:styleId="AAVolumeName"><w:name w:val="AA Volume Name"/></w:style>'
       '<w:style w:type="paragraph" w:styleId="AACoverTitle"><w:name w:val="AA Cover Title"/></w:style></w:styles>')


def p(t, sid=""):
    ps = '<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % sid if sid else ""      # no backslash in an f-string (Python 3.11 on the PC)
    return f'<w:p>{ps}<w:r><w:t>{t}</w:t></w:r></w:p>'


cover = os.path.join(tmp, "Kestrel Cover.docx")
with zipfile.ZipFile(cover, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{p("Proposal Title", "AACoverTitle")}{p("Volume Name", "AAVolumeName")}'
               f'{p("Prepared for the Program Office")}<w:sectPr/></w:body></w:document>')
    z.writestr("word/styles.xml", STY)
    z.writestr("word/settings.xml", f'<w:settings {WNS}/>')
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("Section designs is a tab beside Layout", [k for k, _t in TABS["formatstd"]][-1] == "designs")
w.go("designs"); app.processEvents()
dp = w.designs_page
check("empty: one way in", dp.empty.isVisibleTo(w) and dp.bar.main.text() == "Bring in from Word...")
got = dp.bring_in(cover, shelf="cover")
check("Bring in from Word: on the Cover shelf", len(got) == 1 and SDZ.designs(cfg, "cover")[0]["id"] == got[0]["id"] and not dp.empty.isVisibleTo(w))
check("what fills it: one row per paragraph with text", dp.fills.rowCount() == 3 and dp.fills.item(1, 1).text() == "AA Volume Name")
dp.fills.item(1, 2).setText("volume_name")
check("a fill-in typed in its row is kept", SDZ.get(cfg, got[0]["id"])["map"]["1"] == "volume_name")
check("text other pages read: none here", "No header" in dp.others.text())
dp.tree.setCurrentItem(dp.tree.topLevelItem(1).child(0))
check("act on the row", [a.text() for a in dp.row_menu(run=False).actions() if a.text()] ==
      ["Open in Word", "Replace with an updated file...", "Remove from the library"])
check("Open in Word opens the library's copy", dp.open_word(got[0]["id"]).endswith(".docx"))
# Setup picks it; Make the setup fills it
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
sp = w.setups_page
sp.use_headings("Volume I Technical\n  1 Ground Segment"); app.processEvents()
check("Section designs... is in Setup's More", sp.bar.action("Section designs...") is not None)
d = sp.pick_designs(run=False)
check("a Design row per section; None only where optional", d.boxes["cover"].findData("none") < 0 and d.boxes["cui"].findData("none") >= 0
      and d.boxes["cover"].findData(got[0]["id"]) >= 0)
d.boxes["cover"].setCurrentIndex(d.boxes["cover"].findData(got[0]["id"])); d.boxes["cui"].setCurrentIndex(d.boxes["cui"].findData("none"))
d.save()
M = w.review.M
check("the picks are kept with the setup", SDZ.picked(M, "cover") == got[0]["id"] and SDZ.picked(M, "cui") == "none")
out = ST.section_designs(M, cfg, {}, "Volume I Technical", os.path.join(tmp, "out", "Kestrel_Response_Setup.docx"))
check("Make the setup writes the cover filled beside the setup", set(out) == {"cover"} and os.path.isfile(out["cover"])
      and [x["text"] for x in SDZ.read(out["cover"])["paragraphs"]][1] == "Volume I Technical")
# 3.87.1: the Design row on a section a design fills
import responseelements as RE
from PySide6.QtCore import Qt
data = RE.load(cfg)
RE.apply_kit(M, data, ["cover", "toc"], "Volume I Technical"); sp.refresh(); app.processEvents()
import compliance as C
cov_lab = next(C.outline_label(o) for o in M.outline if o.get("element") == "cover")
body_lab = next(C.outline_label(o) for o in M.outline if not o.get("element") and o.get("level", 1) > 1 or "Ground" in C.outline_label(o))
sp.pick(body_lab)
check("a response section has no Design row", not sp.design_form.isRowVisible(sp.f_design))
sp.pick(cov_lab)
check("the cover section's Design row lists the Cover shelf", sp.design_form.isRowVisible(sp.f_design)
      and sp.f_design.findData(got[0]["id"]) >= 0 and sp.f_design.findData("none") < 0, [sp.f_design.itemText(i) for i in range(sp.f_design.count())])
sp.f_design.setCurrentIndex(0)
check("picking (not set) there clears the pick; one set of records with Section designs...", sp.set_design() and SDZ.picked(M, "cover") == "")
check("picking a design there sets it", sp.set_design(got[0]["id"]) and SDZ.picked(M, "cover") == got[0]["id"])
check("Remove from the library", dp.remove(got[0]["id"]) and SDZ.designs(cfg) == [])

print(f"QT DESIGNS 387 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
