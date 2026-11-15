"""4.40.0, offscreen (ST28 of 2026-11-14): a Quick Part's versions on the Parts page. Change it... makes a new Latest and
every set that used the Quick Part gets it; the row shows the Latest; Versions... lists the history with the sets and
restores an earlier one as a new version; Create another version... is for the part sets ticked, and the row then has
one tab per version, named for its sets; a set left on an earlier version is told and moved. Fictional files."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_THEME"] = "light"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import parthistory as PH, partlib as PT, partvariant as PV, stylelib as SL
from PySide6.QtWidgets import QApplication, QPushButton
from skqt import design as D, partversions as PVW
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
with_glossary(os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx"), gl, table_hdr=True)
dlg = pp.bring_in(gl, run=False)
for x in dlg.plan["pages"]:
    x["keep"] = False
dlg.fill(); dlg.count(); _d, items = dlg.go(); app.processEvents()
th = next(i for i in items if lib.base_of(i) == "Table header")
rfp = pp.new_set(name="RFP parts"); pd = pp.new_set(name="Program parts"); pl = pp.new_set(name="Page-limited parts")
PT.add_to_set(cfg, lib, rfp["id"], ["q:" + th["id"]]); PT.add_to_set(cfg, lib, pd["id"], ["q:" + th["id"]])
pp.tabs.setCurrentIndex(6); app.processEvents()
pp.select("q:" + th["id"]); app.processEvents()
acts = [a.text() for a in pp.row_menu(run=False).actions()]
check("a Quick Part's row holds Versions... and Create another version...", "Versions..." in acts and "Create another version..." in acts, acts)
ch = pp.change("q:" + th["id"], run=False)
ch.width.setValue(6.0)
new = ch.save_variant(label="narrow"); app.processEvents()
lib = pp.lib
rfp, pd, pl = (SL.get_set(lib, k["id"]) for k in (rfp, pd, pl))
check("Change it...: a new Latest, and every set that used the Quick Part has it", new is not None and new["id"] != th["id"]
      and rfp["items"] == ["q:" + new["id"]] and pd["items"] == ["q:" + new["id"]] and sorted(ch.moved) == ["Program parts", "RFP parts"], (rfp["items"], ch.moved))
check("the row shows the Latest, one row, no tabs for earlier versions", "q:" + new["id"] in pp.row_ids and "q:" + th["id"] not in pp.row_ids
      and pp.cur == "q:" + new["id"], pp.row_ids)
vd = PVW.versions(pp, new["id"], run=False)
rows = [[vd.table.item(r, c).text() for c in range(5)] for r in range(vd.table.rowCount())]
check("Versions...: Latest first, with the sets that use it", len(rows) == 2 and rows[0][0] == "2  Latest" and rows[0][4] == "RFP parts, Program parts"
      and rows[1][0] == "1" and rows[1][3] == "The first version" and "in RFP parts, Program parts" in vd.head.text(), (rows, vd.head.text()))
check("Restore is off for the Latest", not vd.b_restore.isEnabled())
vd.table.selectRow(1); app.processEvents()
check("... and on for an earlier version", vd.b_restore.isEnabled())
vd.b_restore.click(); app.processEvents()
lib = pp.lib
top = PH.top(lib, th["id"])
check("Restore this version: a new version on top, nothing removed, and the sets get it", vd.table.rowCount() == 3 and vd.table.item(0, 3).text() == "Restored from version 1"
      and SL.get_set(lib, rfp["id"])["items"] == ["q:" + top["id"]] and lib.get(new["id"]) is not None and PV.table_of(lib.source_path(lib.values(top)["source"]), "Table header")["width"] == 6.5,
      [vd.table.item(r, 3).text() for r in range(vd.table.rowCount())])
ad = PVW.another(pp, top["id"], run=False)
check("Create another version...: a box for each part set; the ones that use it say so", [c.text() for c in ad.boxes]
      == ["RFP parts  (uses this one now)", "Program parts  (uses this one now)", "Page-limited parts"], [c.text() for c in ad.boxes])
ad.boxes[2].setChecked(True); ad.b_go.click(); app.processEvents()
lib = pp.lib
other = ad.made
check("... made for the ticked set, which now holds it; the others keep theirs", other is not None and SL.get_set(lib, pl["id"])["items"] == ["q:" + other["id"]]
      and SL.get_set(lib, rfp["id"])["items"] == ["q:" + top["id"]] and PH.line_of(other) != PH.line_of(top))
pp.sets.setCurrentRow(0); pp.tabs.setCurrentIndex(6); app.processEvents()
row = next(pp.rows.itemWidget(pp.rows.item(i)) for i in range(pp.rows.count()) if pp.row_ids[i] in ("q:" + top["id"], "q:" + other["id"]))
tabs = [b.text() for b in row.findChildren(QPushButton, "verTab")]
check("the row has one tab for each version of the name, named for its sets", tabs == ["for RFP parts, Program parts", "for Page-limited parts"], tabs)
legacy = pp.new_set(name="Legacy parts"); SL.get_set(pp.lib, legacy["id"])["items"].append("q:" + th["id"]); pp.lib.save()
pp.sets.setCurrentRow(0); pp.fill_rows(); app.processEvents()
check("a set left on an earlier version: the page says so", "1 Quick Part in Legacy parts is on an earlier version." in pp.fit_line.text() and pp.fit_box.isVisibleTo(w), pp.fit_line.text())
check("More > Use the latest Quick Parts in every set moves it", "Use the latest Quick Parts in every set" in [a.text() for a in pp.bar.more_menu.actions()]
      and PVW.use_latest(pp) == 1 and SL.get_set(pp.lib, legacy["id"])["items"] == ["q:" + top["id"]] and PVW.notice(pp) == "")
w.close()
n = sum(checks)
print(f"QT PARTVERSIONS 4400 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
