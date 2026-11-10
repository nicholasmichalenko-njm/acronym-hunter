"""3.66.0 Template Studio I, offscreen: Production > Template Studio (the volume, the profile, Anatomy read from the
profile's picks with Field recipes and Parts and numbering in it, this effort's own formatting, Parts and numbering
edited and saved, double-click opens the owner); Rules > Field recipes (add, change, save, remove, put back, Read a
template with each field against the recipes, Make a recipe from it, this effort's own code). Fictional content."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, workspace as W, deliverables as DL, fieldrecipes as FR, partplan as PP, office_pdf as OP
OP.available = lambda: False
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
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
DL.add(RR.Record(ws0.root), "Volume I Technical", "Volume")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
check("Template Studio is in the Team space (3.75.0)", "studio" in __import__("skqt.mainwin", fromlist=["x"]).TEAM and "studio" in w.team_page.refresh())
w.go("studio"); app.processEvents()
st = w.studio_page
check("the volume list holds the effort's volumes", "Volume I Technical" in [st.vol.itemText(i) for i in range(st.vol.count())])
st.vol.setCurrentText("Volume I Technical"); st.fill(); app.processEvents()
what = [r[1] for r in st.anatomy_now]
check("Anatomy: each part of the profile, then Parts and numbering and Field recipes", "Header and footer" in what and "Table of contents" in what
      and "Parts and numbering" in what and "Field recipes" in what, what)
check("... this effort's own formatting is summed up", st.own.text() != "")
st.tabs.setCurrentIndex(1); app.processEvents()
check("Parts and numbering: the usual parts at first", st.ptab.rowCount() == 4 and st.ptab.item(3, 2).text().startswith("A-1"))
st.ptab.selectRow(2); app.processEvents()
v = st.part_values(); v.update(paper="11x17", orient="Landscape", foldout=2)
st.save_part(v)
check("save a part: the plan is kept for this effort", PP.plan_of(RR.Record(ws0.root), "Volume I Technical")[2]["paper"] == "11x17"
      and "landscape 11x17" in st.sample.text())
pid = st.add_part("Foldouts", "Body")
check("+ Part after the one picked", [p["name"] for p in PP.plan_of(RR.Record(ws0.root), "Volume I Technical")][3] == "Foldouts")
st.move(1)
check("Up and Down move it", [p["name"] for p in PP.plan_of(RR.Record(ws0.root), "Volume I Technical")][4] == "Foldouts")
st.remove()
check("Remove takes it out", "Foldouts" not in [p["name"] for p in PP.plan_of(RR.Record(ws0.root), "Volume I Technical")])
row = next(i for i, r in enumerate(st.anatomy_now) if r[1] == "Field recipes")
st.open_owner(row); app.processEvents()
check("Field recipes opens Rules > Field recipes", w.stack.currentWidget() is w.rules_page and w.rules_page.stack.currentIndex() == 2)
rv = w.rules_page.recipes
check("the recipes are listed, the starters first", rv.table.rowCount() == 8 and rv.table.item(0, 0).text() == "Response table of contents")
rid = rv.new({"name": "Volume title", "where": "Header or footer", "codes": ["DOCPROPERTY VolumeTitle"]})
check("+ Recipe adds one, saved at once", any(r["id"] == rid for r in FR.load(w.config_dir)))
vals = rv.values(); vals.update(name="Volume title in the footer", codes=["DOCPROPERTY VolumeTitle \\* MERGEFORMAT"])
rv.save(vals)
check("Save the recipe keeps the change", next(r for r in FR.load(w.config_dir) if r["id"] == rid)["name"] == "Volume title in the footer")
rv.table.selectRow(0); app.processEvents()
rv.effort_own(['TOC \\o "1-2" \\h \\z \\b Response'])
check("This effort's own code: the open effort uses it, the team's stays", "(this effort's own)" in rv.table.item(0, 0).text()
      and FR.load(w.config_dir)[0]["codes"] == ['TOC \\o "1-3" \\h \\z \\b Response'])
rv.effort_own([])
W_ = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
doc = os.path.join(tmp, "trusted.dotx")
with zipfile.ZipFile(doc, "w") as z:
    z.writestr("word/document.xml", f'<w:document {W_}><w:body><w:p><w:fldSimple w:instr="SEQ Exhibit \\* ARABIC"/></w:p>'
               f'<w:p><w:fldSimple w:instr="STYLEREF 1 \\s"/></w:p></w:body></w:document>')
found = rv.read_file(doc)
check("Read a template: each field against the recipes", len(found) == 2 and rv.ftable.rowCount() == 2
      and {r["status"] for r in found} == {"matches", "no recipe"} and "2 field(s)" in rv.found_lab.text(), [r["status"] for r in found])
i = next(n for n, r in enumerate(found) if r["status"] == "no recipe")
new = rv.from_found(i)
check("Make a recipe from it", next(r for r in FR.load(w.config_dir) if r["id"] == new)["codes"] == ["SEQ Exhibit \\* ARABIC"]
      and next(r for r in FR.load(w.config_dir) if r["id"] == new)["where"] == "Caption")
rv.table.selectRow([r["id"] for r in rv.rows].index(new)); rv.remove()
check("Remove a recipe", not any(r["id"] == new for r in FR.load(w.config_dir)))

print(f"QT STUDIO 366 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
