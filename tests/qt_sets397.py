"""3.97.0 offscreen: Make templates > What goes in (canvas "Libraries and Sets", boards 6 and 9). The profile being edited
picks style sets in order, the Setup styles and a part set; the document starts with pages from Parts, each also in the
Quick Parts gallery unless its switch is off; the checks before it is made. Nothing is edited there; the choice is kept
with the profile. Fictional (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import partlib as PT, sectiondesigns as SDZ, stylelib as SL, templatelib as TL, templatesets as TS
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make(path, body, styles=""):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}<w:sectPr/></w:body></w:document>')
        z.writestr("word/styles.xml", f'<w:styles {WNS}><w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>{styles}</w:styles>')
    return path


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
lib = TL.Library(cfg)
src = make(os.path.join(tmp, "Kestrel Styles.dotx"), "<w:p/>",
           '<w:style w:type="paragraph" w:customStyle="1" w:styleId="KBody"><w:name w:val="Kestrel Body"/><w:rPr><w:sz w:val="22"/></w:rPr></w:style>')
rfp = SL.new_set(lib, "RFP volume"); setup = SL.new_set(lib, "Setup")
rows = SL.against(lib, SL.read_styles(src))
for r in rows:
    r["keep"] = r["name"] == "Kestrel Body"
SL.bring_in(lib, rows, src, set_of={"Kestrel Body": rfp["id"]})
cover = SDZ.add(cfg, "cover", make(os.path.join(tmp, "Kestrel Cover.docx"), "<w:p><w:r><w:t>Kestrel Ground Segment</w:t></w:r></w:p>"))
lib = TL.Library(cfg)
parts = SL.new_set(lib, "Kestrel parts", kind="part")
PT.add_to_set(cfg, lib, parts["id"], ["d:" + cover["id"]])

app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
from skqt.maketemplates import MakeTemplatesDialog
md = MakeTemplatesDialog(sp); app.processEvents()
gi = md.goes_in
check("What goes in is the first tab, beside the template in full", md.right_tabs.tabText(0) == "What goes in"
      and md.right_tabs.tabText(1) == "The template in full")
check("nothing picked yet: the profile's own values, as before", gi.sets.count() == 0 and "No sets picked" in gi.checks_box.itemAt(0).widget().text())
m = gi.add_menu(run=False)
check("Add a set lists the style sets", [a.text() for a in m.actions()] == ["RFP volume", "Setup"])
gi.add_set(rfp["id"]); app.processEvents()
check("a style set picked is kept with the profile being edited", TS.recipe(sp.work)["style_sets"] == [rfp["id"]] and sp.dirty)
gi.setup.setCurrentIndex(gi.setup.findData(setup["id"])); gi.parts.setCurrentIndex(gi.parts.findData(parts["id"])); app.processEvents()
check("the Setup styles and the part set", TS.recipe(sp.work)["setup_set"] == setup["id"] and TS.recipe(sp.work)["part_set"] == parts["id"])
gi.add_page("cover"); app.processEvents()
check("the document starts with: a cover from Parts, also in the gallery", TS.recipe(sp.work)["starts"] == [{"kind": "cover", "part": cover["id"], "gallery": True}]
      and gi.starts.rowCount() == 1)
gi.starts.cellWidget(0, 2).setChecked(False); app.processEvents()
check("... its switch takes it out of the gallery", TS.recipe(sp.work)["starts"][0]["gallery"] is False)
check("the checks before it is made", [w_ for _s, w_, _m in gi.checks_now][:1] == ["1 style, 1 as Word wrote it"]
      and any("starting page" in w_ for _s, w_, _m in gi.checks_now), gi.checks_now)
gi.remove_page(0); gi.sets.setCurrentRow(0); gi.take_out(); app.processEvents()
check("Remove and Take out", TS.recipe(sp.work)["starts"] == [] and TS.recipe(sp.work)["style_sets"] == [])
md.radios["etype"].setChecked(True); app.processEvents()
check("every volume of an effort type: each profile's own choice, read only", not gi.setup.isEnabled())
w.close()
print(f"QT SETS 397 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
