"""3.98.0 offscreen: Change a part (canvas "Libraries and Sets", board 5). On Parts, a Quick Part's row: Change it... opens
the three ways: the style first (the styles it names; typed formatting and Let the styles decide), Make a variant
(padding, widths, row height, a paragraph style swapped, named, into a set), and in Word (Open in Word, Bring back as a
new version). Each is a new version on the part's row; the one before stays. Quick Parts are by kind (Tables, Callouts,
Headers and footers); the Quick Parts tab is gone from Standards. Styles: Every value... opens Formatting on the style.
Fictional (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import partvariant as PV
import stylelib as SL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow, TABS
from _qpfixture import with_glossary

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
src = os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx")
gl = os.path.join(tmp, "Kestrel Master.dotx"); with_glossary(src, gl, table_hdr=True)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("Standards has no Quick Parts tab: they are in Parts", "qpstd" not in [k for v in TABS.values() for k, _t in v])   # 4.28.0: Quick Parts is its own menu entry
w.go("designs"); app.processEvents()
pp = w.designs_page
ps = pp.new_set(name="Page-limited RFP")
dlg = pp.bring_in(gl, run=False)
_d, items = dlg.go(); app.processEvents()
th = next(i for i in items if i["name"] == "Table header")
k = next(i for i in range(pp.tabs.count()) if pp.tabs.tabData(i) == "hf")
pp.tabs.setCurrentIndex(k); app.processEvents()
check("Headers and footers lists the table header", "q:" + th["id"] in pp.row_ids, pp.row_ids)
cd = pp.change("q:" + th["id"], run=False)
check("Change it...: three ways", cd.windowTitle() == "Change Table header" and cd.table is not None and cd.width.value() == 6.5
      and cd.cols.text() == "4, 2.5")
check("1 the style first: no typed formatting here", not cd.typed_box.isVisibleTo(cd) and cd.n_typed == 0)
cd.pad["top"].setValue(0.02); cd.pad["bottom"].setValue(0.02); cd.width.setValue(6.0); cd.cols.setText("3.5, 2.5")
cd.label.setText("compact"); cd.into.setCurrentIndex(cd.into.findData(ps["id"]))
new = cd.save_variant(); app.processEvents()
t2 = PV.table_of(*PV.source_of(pp.lib, new))
check("2 Make a variant: a new version with the padding and widths", new["family"] == th["family"] and t2["width"] == 6.0
      and t2["padding"]["top"] == 0.02 and t2["columns"] == [3.5, 2.5], t2)
check("... named, in the set, shown on its row", new["label"] == "compact" and "q:" + new["id"] in SL.get_set(pp.lib, ps["id"])["items"]
      and pp.cur == "q:" + new["id"])
check("... the version before stays as it was", PV.table_of(*PV.source_of(pp.lib, pp.lib.get(th["id"])))["width"] == 6.5)
cd2 = pp.change("q:" + new["id"], run=False)
check("Nothing different: nothing saved", cd2.save_variant() is None)
out = cd2.open_word()
check("3 Open in Word: the part on its own", out and out.endswith(".docx") and os.path.isfile(out))
back = cd2.bring_back(out); app.processEvents()
check("... Bring back as a new version", back is not None and back["family"] == th["family"] and int(back["version"]) == 3)
pp.rows.clearSelection(); pp.rows.item(pp.row_ids.index(pp.cur)).setSelected(True)
check("the row's menu", [a.text() for a in pp.row_menu(run=False).actions()][:2] == ["Change it...", "Open in Word"])
# Styles: Every value...
w.go("styles"); app.processEvents()
st = w.styles_page
sid = SL.new_style(st.lib, "Kestrel Body", "paragraph", {"font": "Arial", "size": 11})[0]["id"]
st.refresh(); app.processEvents()
ok = st.every_value(sid); app.processEvents()
check("Styles > Every value... opens Formatting on the style", ok and w.stack.currentWidget() is w.formatstd_page
      and w.formatstd_page.current() and w.formatstd_page.current()["id"] == sid)
w.close()
print(f"QT CHANGE 398 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
