"""3.0.3 starting an effort, offscreen: with no effort open, Effort Home is the Start an effort form; a name alone makes
a working effort (its folders made in the team's layout, opened on Effort Home); the picture (chosen or dropped), the
client, solicitation, due date with its time zone and the proposal manager land where Effort Home shows them; the
effort picture on Effort Home also takes a dropped file; + Add an Effort with an effort open uses the same form."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortrec as RR, branding as BR
from PIL import Image
from PySide6.QtCore import QMimeData, QPoint, QPointF, QUrl, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow
from skqt import starteffort as SE

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
patch = os.path.join(tmp, "patch.png"); Image.new("RGB", (800, 800), (15, 30, 70)).save(patch)
patch2 = os.path.join(tmp, "patch2.jpg"); Image.new("RGB", (600, 600), (160, 40, 40)).save(patch2)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def drop(widget, path):
    md = QMimeData(); md.setUrls([QUrl.fromLocalFile(path)])
    ev = QDropEvent(QPointF(10, 10), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
    widget.dropEvent(ev)
    app.processEvents()


w.go("home"); app.processEvents()
hp = w.home_page; f = hp.start
check("no effort open: Effort Home is the Start an effort form", f.isVisibleTo(w) and not hp.scroll.isVisibleTo(w))
check("... Create effort waits for a name", not f.create_btn.isEnabled())
f.name.setText("Kestrel Thermal"); app.processEvents()
check("a name fills in where the effort will live, in Stationkeeper Data\\Efforts", f.create_btn.isEnabled()
      and "Kestrel" in f.path.text() and f.path.text().endswith(".xlsx") and os.path.join("Stationkeeper Data", "Efforts") in f.path.text(), f.path.text())
drop(f.pic, patch)
check("a picture dropped on the form is taken", os.path.normcase(f.pic.path) == os.path.normcase(os.path.normpath(patch)), f.pic.path)
f.client.setText("U.S. Space Force, Space Systems Command"); f.sol.setText("FA8810-26-R-0042")
f.due.setText("December 15, 2026, 2:00 PM"); f.zone.setCurrentIndex(f.zone.findData("ET"))
f.pm.setCurrentText("A. Rivera")
name = f.create()
app.processEvents()
check("Create effort makes it and opens it on Effort Home", name == "Kestrel Thermal" and w.effort_name == "Kestrel Thermal"
      and w.stack.currentWidget() is hp and hp.scroll.isVisibleTo(w) and not hp.start_wrap.isVisibleTo(w))
root = w.ws.root
rec = RR.Record(root)
check("... with its picture, proposal manager and due date in the submission's time zone", BR.has_picture(root)
      and BR.identity(rec)["pm"] == "A. Rivera" and rec.data["due"].startswith("2026-12-15T14:00") and rec.zone_key() == "ET",
      (rec.data.get("due"), rec.zone_key()))
reg = w.efforts.get("Kestrel Thermal")
check("... the client and solicitation, and its own folders", reg.get("client", "").startswith("U.S. Space Force")
      and reg.get("solicitation") == "FA8810-26-R-0042" and os.path.isdir(reg.get("customer_dir", "")) and os.path.isdir(reg.get("volumes_dir", "")))
check("... and Effort Home shows them", "Kestrel Thermal" in hp.banner.name.text())
check("the form is empty again for the next one", f.name.text() == "" and f.pic.path == "")
drop(hp.banner.pic, patch2)
check("the effort picture on Effort Home takes a dropped picture", Image.open(BR.picture_path(root)).convert("RGB").getpixel((5, 5))[0] > 120)
# + Add an Effort with an effort open: the same form, in a window
dlg = SE.StartDialog(w)
dlg.form.name.setText("Osprey")
made = dlg.form.create()
app.processEvents()
check("+ Add an Effort with one open: the same form in a window; a name is enough", made == "Osprey" and dlg.made == "Osprey"
      and w.effort_name == "Osprey" and "Osprey" in w.efforts.names())
bad = SE.StartDialog(w); bad.form.name.setText("Osprey")
check("a name already used is refused, and says why", bad.form.create() is None and bad.form.err.text() != "", bad.form.err.text())
w.close_effort(); app.processEvents()
w.go("home"); app.processEvents()
check("closing the effort brings the form back on Effort Home", hp.start_wrap.isVisibleTo(w))
check("All Efforts' + Add an Effort, with none open, goes to the form", w.efforts_page.add_effort() is None and w.stack.currentWidget() is hp)
n = sum(checks)
print(f"QT START {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
