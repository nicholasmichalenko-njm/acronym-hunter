"""3.27.0 Document parts > Cover > Edit the layout, offscreen: the kept cover drawn as a page with each piece where Word
puts it (the picture drawn in); dragging a piece and typing its place and size; the picture keeping its proportions;
a line of text set to show the volume name; Save keeps a new copy (the one before stays) as the cover; a sample in
Word; Make templates offers each volume continuing the one before."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import coverlayout as CL, prodparts as PP
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
import _coverfixture as F

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
from skqt import docparts as DP
check("no kept cover yet: Edit the layout says to import one", DP.edit_layout(sp, "cover", run=False) is None)
cov = F.make(os.path.join(tmp, "cover.docx"))
name0 = PP.save_part(sp.parts_dir(), open(cov, "rb").read(), "cover")
sp.work.setdefault("page_parts", {})["cover"] = name0
d = DP.edit_layout(sp, "cover", run=False)
check("the cover drawn as a page with its floating pieces", d is not None and len(d.items) >= 3 and d.list.count() >= 3, d.list.count() if d else None)
pic = next(it for it in d.items.values() if it.d["kind"] == "picture")
check("the picture is drawn in", pic.pix is not None)
pic.setPos(0.5 * 72, 0.25 * 72); app.processEvents()
check("dragging a piece moves it (inches from the page's corner)", d.changes[pic.d["id"]]["x"] == 0.5 and d.changes[pic.d["id"]]["y"] == 0.25)
d.list.setCurrentRow([d.list.item(i).data(0x0100) for i in range(d.list.count())].index(pic.d["id"])); app.processEvents()
d.sp["w"].setValue(4.25); app.processEvents()
check("typing a width keeps the picture's proportions", abs(d.changes[pic.d["id"]]["h"] - 4.25 * 3.4 / 8.5) < 0.01, d.changes[pic.d["id"]])
r = next(i for i in range(d.texts.rowCount()) if d.texts.item(i, 0).text() == "VOLUME I TECHNICAL")
cb = d.texts.cellWidget(r, 2); cb.setCurrentIndex(cb.findData("volume_name")); app.processEvents()
check("a line set to show the volume name", any(v.get("field") == "volume_name" for v in d.changes.values()))
smp = d.sample(open_it=False)
check("Open a sample in Word: a template with the layout as it stands", smp and smp.endswith(".dotx") and "Samples" in smp)
name1 = d.save()
check("Save keeps a new copy and makes it the cover", name1 and name1 != name0 and sp.work["page_parts"]["cover"] == name1)
check("the copy before stays", os.path.isfile(os.path.join(sp.parts_dir(), name0)))
lay = CL.read(open(os.path.join(sp.parts_dir(), name1), "rb").read())
pp = next(p for p in lay["pieces"] if p["kind"] == "picture")
check("the saved cover has the moves, sizes and field", pp["x"] == 0.5 and pp["w"] == 4.25
      and any(p.get("field") == "volume_name" for p in lay["pieces"]))
check("the Cover part says its page", name1 in sp.part_ui["cover"]["page_lab"].text())
from skqt.maketemplates import MakeTemplatesDialog
md = MakeTemplatesDialog(sp)
check("Make templates offers volumes that continue (off until ticked)", hasattr(md, "cont") and not md.cont.isChecked() and md.starts() == {})
w.close()
n = sum(checks)
print(f"QT COVER LAYOUT {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
os._exit(0 if n == len(checks) else 1)
