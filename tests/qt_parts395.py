"""3.95.0 offscreen: Standards > Parts. Empty: one way in. Bring in from a document... reads a file once: its pages (one
per Word section, each guessed) and its Quick Parts gallery, a tick each, and the part set they go into. Kinds are tabs
with counts; one row per part with its versions as tabs; a version brought back from Word sits beside the first; Name
this version; part sets on the left hold one version of each part, and a set's rows open on the versions it uses; a part
in a set is not removed. Fictional files (the Kestrel set)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import partlib as PT, sectiondesigns as SDZ, stylelib as SL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from _qpfixture import with_glossary

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
STY = (f'<w:styles {WNS}><w:style w:type="paragraph" w:styleId="AACoverTitle"><w:name w:val="AA Cover Title"/></w:style></w:styles>')


def p(t, sid="", sect=""):
    st = '<w:pStyle w:val="%s"/>' % sid if sid else ""
    ps = f'<w:pPr>{st}{sect}</w:pPr>' if (sid or sect) else ""
    return f'<w:p>{ps}<w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'


def make(path, body):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}<w:sectPr/></w:body></w:document>')
        z.writestr("word/styles.xml", STY)
        z.writestr("word/settings.xml", f'<w:settings {WNS}/>')
    return path


front = make(os.path.join(tmp, "Kestrel Front Matter.docx"),
             p("Kestrel Ground Segment", "AACoverTitle") + p("Volume Name Here", "", "<w:sectPr/>")
             + p("CONTROLLED UNCLASSIFIED INFORMATION") + p("Handle per the marking on each page.", "", "<w:sectPr/>")
             + p("Table of Contents", "AACoverTitle") + p("1 Ground Segment ... 1"))
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("designs"); app.processEvents()
pp = w.designs_page
check("empty: one way in", pp.empty.isVisibleTo(w) and not pp.rows.isVisibleTo(w) and pp.bar.main.text() == "Bring in from a document...")
check("the kinds are tabs", [pp.tabs.tabText(i) for i in range(pp.tabs.count())] ==
      ["Covers", "Marking pages", "Title pages", "Front matter", "Tables", "Callouts", "Headers and footers", "Back covers", "Quick Parts"])
ps = pp.new_set(name="Page-limited RFP")
pp.sets.setCurrentRow(1); app.processEvents()
dlg = pp.bring_in(front, run=False)
check("the file's pages, each with what it most likely is", [x["kind"] for x in dlg.plan["pages"]] == ["cover", "cui", "toc"]
      and dlg.table.rowCount() == 3, [x["kind"] for x in dlg.plan["pages"]])
check("... into the set picked on the page", dlg.set_box.currentData() == ps["id"])
check("... the button says how many", dlg.b_go.text() == "Bring in 3 part(s)")
dlg.table.item(2, 0).setCheckState(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.Unchecked)
check("untick one", dlg.b_go.text() == "Bring in 2 part(s)")
designs, _q = dlg.go()
app.processEvents()
check("kept on their shelves and in the set", [d["shelf"] for d in designs] == ["cover", "cui"]
      and len(SL.get_set(pp.lib, ps["id"])["items"]) == 2)
check("the tabs count each kind", pp.tabs.tabText(0) == "Covers  1" and pp.tabs.tabText(1) == "Marking pages  1" and pp.tabs.tabText(3) == "Front matter")
pp.pick_set(None); pp.sets.setCurrentRow(0)
pp.tabs.setCurrentIndex(0); app.processEvents()
check("one row per part, with its set chip", pp.rows.count() == 1 and pp.row_ids == ["d:" + designs[0]["id"]])
check("the selected part on the right: what fills it", pp.fills.rowCount() == 2 and "Kestrel Ground Segment" in pp.title.text() + pp.thumb.text())
# a new version
v2 = make(os.path.join(tmp, "Kestrel Cover CUI.docx"), p("Kestrel Ground Segment", "AACoverTitle") + p("CUI") + p("Volume Name Here"))
y = pp.new_version("d:" + designs[0]["id"], v2, label="CUI")
check("brought back as a new version: still one row, two version tabs, the new one shown", pp.rows.count() == 1
      and pp.row_ids == ["d:" + y["id"]] and len(pp.rows.itemWidget(pp.rows.item(0)).findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton, "verTab")) == 2)
check("... named for its version", "v2: CUI" in pp.title.text(), pp.title.text())
pp.show_version("d:" + PT.family(y), "d:" + designs[0]["id"])
check("a version tab shows that version", pp.row_ids == ["d:" + designs[0]["id"]])
# the set keeps the version it uses
k = next(i for i in range(pp.sets.count()) if pp.sets.item(i).data(0x0100) == ps["id"])
pp.sets.setCurrentRow(k); app.processEvents()
check("a set's rows open on the versions it uses", pp.sid == ps["id"] and pp.row_ids == ["d:" + designs[0]["id"]])
gone = pp.add_to_set(ps["id"], ["d:" + y["id"]])
check("a set holds one version of each part", gone == ["d:" + designs[0]["id"]] and pp.row_ids == ["d:" + y["id"]])
pp.rows.item(0).setSelected(True)
acts = [a.text() for a in pp.row_menu(run=False).actions() if a.text()]
check("act on the row", acts == ["Open in Word", "Draw with Word", "Bring back as a new version...", "Name this version...",
                                 "Add to set", "Take out of this set", "Remove from the library"], acts)
check("a part in a set is not removed", pp.remove(["d:" + y["id"]]) == 0 and SDZ.get(cfg, y["id"]) is not None)
check("Name this version", pp.label_version("d:" + designs[0]["id"], "plain") and SDZ.get(cfg, designs[0]["id"])["label"] == "plain")
# Quick Parts
src = os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx")
gl = os.path.join(tmp, "Kestrel Master.dotx"); with_glossary(src, gl)
pp.sets.setCurrentRow(0); app.processEvents()
dlg = pp.bring_in(gl, run=False)
check("a template's gallery; its body is not ticked as a page", len(dlg.plan["gallery"]) == 3 and not any(x["keep"] for x in dlg.plan["pages"])
      and dlg.b_go.text() == "Bring in 3 part(s)")
_d, items = dlg.go(); app.processEvents()
check("Quick Parts by what they are (3.98.0): the CUI header under Headers and footers", pp.tabs.tabText(8) == "Quick Parts  2"
      and pp.tabs.tabText(6) == "Headers and footers  1")
pp.tabs.setCurrentIndex(8); app.processEvents()
check("Quick Parts: their own tab, one row each", pp.kind == "quick" and pp.rows.count() == 2)
pp.rows.clearSelection(); pp.rows.item(0).setSelected(True)
check("a Quick Part's row: Change it, Open in Word, Bring back, Details (3.98.0)", [a.text() for a in pp.row_menu(run=False).actions()][:4]
      == ["Change it...", "Open in Word", "Bring back as a new version...", "Details: category, gallery, pages it fills..."])
check("the right side shows no fill-ins for a Quick Part", not pp.fills.isVisibleTo(w))
again = pp.bring_in(gl, run=False)
check("met again: Already have it, unticked", all(e["state"] == "same" and not e["keep"] for e in again.plan["gallery"]))
check("one command bar, one main button", pp.bar.main.text() == "Bring in from a document...")
print(f"QT PARTS 395 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
