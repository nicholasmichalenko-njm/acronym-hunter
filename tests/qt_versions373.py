"""3.73.0 offscreen: the first outline workbook is version 1; the next one opens New version of the outline (every change
listed, Accept waits until each change in both has a pick, only-in-both filter), accepted with the picks; Outline
versions lists both, compares v1 with v2, and writes the workbook back out. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, outlinelayouts as OL, outlineversions as OV, setupdoc as SD
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
import test_versions373 as TV                                  # its workbook maker and rows (its own checks run too)
lay = OL.load(cfg)[OL.STARTING]
lay["rules"]["support"].append({"color": "6B21A8", "italic": None, "bold": None, "kind": "customer"})
OL.put(cfg, OL.STARTING, lay)
x1 = TV.build(os.path.join(tmp, "Kestrel Outline.xlsx"), TV.V1)
x2 = TV.build(os.path.join(tmp, "Kestrel Outline 2.xlsx"), TV.V2)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
pg = w.setups_page
pg.from_outline(x1, accept=True)
M = w.review.M
check("the first workbook is version 1, kept with the effort", OV.current(M)["v"] == 1
      and os.path.isfile(os.path.join(ED, "Outline Versions", "Kestrel Outline v1.xlsx")))
S = SD.setup_of(M)
id1 = next(i for i, r in S["refs"].items() if r == "L.4.2.1")
S["notes"][id1] = "Lead with the dual-site design; cite the 2024 test."
pg.from_outline(x2, accept=False)                              # the import window, not used yet
od = pg.outline_dialog
pg.use_outline(od.parsed, os.path.basename(x2), path=x2, headers=od.book["headers"], layout=od.profile["name"], accept=False)
od.close()
dlg = pg.version_dialog
kinds = [dlg.table.item(r, 0).text() for r in range(dlg.table.rowCount())]
check("New version of the outline lists every change", any(k.startswith("Moved") for k in kinds) and any(k.startswith("Added") for k in kinds)
      and any("changed in both" in k for k in kinds), kinds)
check("Accept waits for the pick on the change in both", not dlg.b_ok.isEnabled() and "wait for your pick" in dlg.wait.text())
dlg.only.setChecked(True); app.processEvents()
check("only the changes in both, when asked", dlg.table.rowCount() == 1)
both = next(c for c in dlg.changes if c["both"])
dlg.table.combos[both["i"]].setCurrentIndex(dlg.table.combos[both["i"]].findData("ours")); app.processEvents()
check("picked: Accept is ready", dlg.b_ok.isEnabled() and dlg.table.picks()[both["i"]] == "ours")
dlg.only.setChecked(False); app.processEvents()
check("the pick holds when every change shows again", dlg.table.picks()[both["i"]] == "ours" and dlg.table.rowCount() == len(dlg.changes))
res = dlg.apply(); dlg.close()
B = SD.by_id(M)
check("accepted: version 2, ids kept, ours kept the app's note", res and OV.current(M)["v"] == 2 and id1 in B
      and "2024 test" in SD.setup_of(M)["notes"][id1] and B[next(i for i, r in SD.setup_of(M)["refs"].items() if r == "L.4.2.2")]["map"] == "1.4 Cybersecurity")
h = pg.versions(modal=False); app.processEvents()
check("Outline versions lists both, and compares v1 with v2", h.list.rowCount() == 2 and h.table.rowCount() >= 5 and "v1 to v2" in h.sum.text(), h.sum.text())
out = os.path.join(tmp, "Kestrel Outline (next).xlsx")
wr = h.write_back(out)
check("Write the workbook back out", wr and os.path.isfile(out) and wr["rows"] >= 6)
h.close()

print(f"QT VERSIONS 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
