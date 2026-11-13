"""4.30.1 offscreen (Nicholas 2026-11-13 14:28 and 14:30): on Styles, double-click a style to review or change its font,
size, characters and paragraph; Duplicate makes a new style from it; the list tells paragraph styles from character
styles. Bringing styles in: every style is listed and ticked, and one you already have joins the set. Fictional."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import stylelib as SL
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, styleedit as SE
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("styles"); app.processEvents()
pg = w.styles_page
body = pg.new_style("Osprey Body", "paragraph", {"font": "Arial", "size": 11})
em = pg.new_style("Osprey Emphasis", "character", {"italic": True})
kinds = sorted({x.text() for x in pg.rows.findChildren(type(pg.count)) if x.objectName() == "styleKind"})
check("each row says its kind", kinds == ["Character style", "Paragraph style"], kinds)
pg.kind_f.setCurrentIndex(pg.kind_f.findData("character")); app.processEvents()
check("the list can show only character styles", pg.row_ids == [em["id"]], pg.row_ids)
pg.kind_f.setCurrentIndex(pg.kind_f.findData("paragraph")); app.processEvents()
check("... or only paragraph styles", pg.row_ids == [body["id"]])
pg.kind_f.setCurrentIndex(0); app.processEvents()
pg.select(body["id"])
acts = [a.text() for a in pg.row_menu(run=False).actions() if a.text()]
check("right-click a style: Review or change... and Duplicate...", "Review or change..." in acts and "Duplicate..." in acts, acts)
dlg = SE.StyleEdit(pg, pg.lib.get(body["id"]), pg.lib.values(pg.lib.get(body["id"])))
check("the form shows the style's font, size and characters, and a paragraph style's alignment, space and keep with next",
      dlg.font_own.isChecked() and dlg.size.value() == 11 and set(dlg.marks) == {"bold", "italic", "underline", "caps", "hidden"}
      and dlg.jc is not None and dlg.before is not None and dlg.keep is not None and not dlg.name.isEnabled())
dc = SE.StyleEdit(pg, pg.lib.get(em["id"]), pg.lib.values(pg.lib.get(em["id"])))
check("a character style's form has no paragraph part", dc.jc is None and dc.before is None and dc.marks["italic"].isChecked())
new = pg.review(body["id"], {"font": "Arial", "size": 12, "color": "", "bold": True, "italic": False, "underline": False, "caps": False,
                             "hidden": False, "jc": "center", "before": 6, "after": 3, "keep_next": True})
v2 = pg.lib.values(new)
check("Save keeps it as a new version with the values set; the first version stays", new["version"] == 2 and v2["size"] == 12.0 and v2["bold"]
      and v2["jc"] == "center" and v2["before"] == 6.0 and v2["keep_next"] and pg.lib.get(body["id"]) is not None, v2)
check("... and Word's definition carries them", 'w:val="center"' in v2["_xml"] and "keepNext" in v2["_xml"] and 'w:val="24"' in v2["_xml"])
cp = pg.duplicate(new["id"], "Osprey Body Compact", {"size": 10})
vc = pg.lib.values(cp)
check("Duplicate: a new style under its own name with the same values and the change made", cp is not None and pg.lib.base_of(cp) == "Osprey Body Compact"
      and vc["size"] == 10.0 and vc["jc"] == "center" and vc["bold"] and 'w:val="Osprey Body Compact"' in vc["_xml"] and cp["version"] == 1, vc)
check("... a name the library has is refused", pg.duplicate(new["id"], "Osprey Emphasis") is None)
imported = ('<w:style xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:type="paragraph" w:styleId="OspreyList">'
            '<w:name w:val="Osprey List"/><w:basedOn w:val="Normal"/><w:pPr><w:numPr><w:numId w:val="3"/></w:numPr><w:tabs><w:tab w:val="left" w:pos="720"/></w:tabs></w:pPr>'
            '<w:rPr><w:sz w:val="22"/></w:rPr></w:style>')
li, _st = pg.lib.add("style", "Osprey List", {"type": "paragraph", "size": 11.0, "_xml": imported, "_from": "Osprey.docx"})
pg.fill_rows()
n2 = pg.review(li["id"], {"font": "", "size": 10, "color": "", "bold": False, "italic": False, "underline": False, "caps": False, "hidden": False,
                           "jc": "", "before": 0, "after": 4, "keep_next": False})
x = pg.lib.values(n2)["_xml"]
check("a style brought in from Word keeps what Word wrote (its numbering and tabs) when it is changed here", "numPr" in x and "w:tabs" in x
      and 'w:sz w:val="20"' in x and 'w:after="80"' in x, x)
pg.rows.itemDoubleClicked.disconnect()
got = []
pg.rows.itemDoubleClicked.connect(lambda li_: got.append(li_.data(Qt.UserRole)))
pg.rows.itemDoubleClicked.emit(pg.rows.item(0))
check("a double-click on a row opens that style", got == [pg.rows.item(0).data(Qt.UserRole)])
# ---- bringing styles in
rows = SL.against(pg.lib, [{"name": "Osprey Emphasis", "type": "character", "values": dict(pg.lib.values(pg.lib.get(em["id"]))), "xml": ""},
                           {"name": "Osprey Note", "type": "paragraph", "values": {"type": "paragraph", "size": 9.0}, "xml": ""}])
check("every style of the file is ticked, one you already have too; each row says what bringing it in does",
      all(r["keep"] for r in rows) and [r["state"] for r in rows] == ["same", "new"] and "joins the set" in rows[0]["words"] and "added to your library" in rows[1]["words"], rows)
from skqt.styleimport import StyleImport
di = StyleImport(pg, os.path.join(tmp, "Osprey.docx"), rows)
check("the three kinds all show, and one box sets the set for the whole import", all(b.isChecked() for b in di.chips.values()) and di.table.rowCount() == 2
      and di.set_all.itemText(di.set_all.count() - 1) == "New set...")
sid = di.pick_set("__new__", name="Osprey volume")
check("New set...: made, and every row takes it, shown or not", sid and all(r["set"] == sid for r in rows) and "2 go into a set" in di.n_lab.text(), di.n_lab.text())
c = di.go()
k = SL.get_set(pg.lib, sid)
check("the style you already had is not added twice, and it is in the set with the new one", c == {"new": 1, "same": 1, "variant": 0}
      and em["id"] in k["items"] and len(k["items"]) == 2 and sum(1 for i in pg.lib.items if pg.lib.base_of(i) == "Osprey Emphasis") == 1, (c, k["items"]))
w.close()
n = sum(checks)
print(f"QT STYLES 4301 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
