"""4.2.0 offscreen: Shred's continuous page is drawn as it scrolls (pagecanvas): every page placed at once (the page
tops and the boxes are there for all), only the pages in view and one each side drawn, about eight kept; Page Down
goes a page at a time; One page at a time fits a page in the view. Fictional (a twelve-page Osprey SOW)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, workspace as W, pdfmini
from PySide6.QtWidgets import QApplication, QGraphicsPixmapItem, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt import pagecanvas as PC
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
WORK = ["antenna maintenance", "telemetry archiving", "command uplink tests", "orbit determination", "anomaly response",
        "spares inventory", "network security patching", "operator training", "pass scheduling", "data distribution",
        "facility power checks", "monthly status reporting"]
pages = [["Body text on this page follows.", f"The contractor shall perform {wk} for the ground station.",
          f"The contractor shall record {wk} results in the station log."] for wk in WORK]
PDF = os.path.join(tmp, "SOW.pdf"); pdfmini.write(PDF, pages, size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
w.read_page.read([PDF], os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx"))
check("extracted", wait(lambda: w.review is not None and not w.read_page.running()))
pg = w.assign_page
w.go("assign"); app.processEvents()
pg.open_file("SOW.pdf"); app.processEvents()
for _ in range(10):
    app.processEvents(); time.sleep(0.02)
pix = lambda: [i for i in pg.view.scene().items() if isinstance(i, QGraphicsPixmapItem)]      # noqa: E731
check("every page placed at once: twelve page tops", len(pg.tops) == 12, len(pg.tops))
check("... the boxes for every page's pieces are there", len(pg.view.boxes) >= 12, len(pg.view.boxes))
check("only the pages in view are drawn (never all twelve)", 0 < len(pix()) < 12 and 0 in pg.canvas.pix, sorted(pg.canvas.pix))
pg.view.verticalScrollBar().setValue(pg.view.verticalScrollBar().maximum()); app.processEvents()
check("scrolled to the end: the last page drawn, about eight kept", wait(lambda: 11 in pg.canvas.pix, 5) and len(pg.canvas.pix) <= PC.KEEP,
      sorted(pg.canvas.pix))
pg.canvas.go_page(1); app.processEvents()
n0 = pg.canvas.page_now()
pg.canvas.step(1); app.processEvents()
check("Page Down: the next page", pg.canvas.page_now() == n0 + 1, (n0, pg.canvas.page_now()))
pg.page_mode_act.setChecked(True); app.processEvents()
check("One page at a time: a page fills the view", pg.canvas.single and pg.canvas.page_now() >= 1)
# a drag at the bottom edge scrolls the view (picking words across a page break)
from PySide6.QtCore import QEvent, QPointF, Qt as _Qt
from PySide6.QtGui import QMouseEvent
pg.page_mode_act.setChecked(False); pg.canvas.go_page(1); app.processEvents()
vp = pg.view.viewport()
sb = pg.view.verticalScrollBar(); v0 = sb.value()
at = QPointF(vp.width() / 2, vp.height() - 5)
pg.edge_scroll.eventFilter(vp, QMouseEvent(QEvent.MouseMove, at, vp.mapToGlobal(at.toPoint()).toPointF(), _Qt.NoButton, _Qt.LeftButton, _Qt.NoModifier))
check("a drag held at the bottom edge scrolls the page on", wait(lambda: sb.value() > v0 + 30, 3), (v0, sb.value()))
pg.edge_scroll.eventFilter(vp, QMouseEvent(QEvent.MouseButtonRelease, at, vp.mapToGlobal(at.toPoint()).toPointF(), _Qt.LeftButton, _Qt.NoButton, _Qt.NoModifier))
check("... and stops when the button is let go", not pg.edge_scroll.timer.isActive())
w.close()
print(f"QT CANVAS 420 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
