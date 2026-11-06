"""3.71.0 offscreen: the acronym scan's progress bar (where it is, how much is done, about how long is left; shown while
a scan runs, gone after), the lines the scan sends turned into a share and a time left, and the Effort Dashboard's
condensed header without the set-aside Win themes and Wall of Truth buttons. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, scanprogress as SP
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the lines the scan sends
p = SP.parse("[3/20] Figure 3.png - Running OCR on image...")
check("a line read: file 3 of 20, its name, what it is doing in plain words", p and (p["file"], p["files"], p["name"], p["what"], p["part"])
      == (3, 20, "Figure 3.png", "reading the picture", 0.0), p)
q = SP.parse("[1/2] Kestrel RFP.pdf - PDF page 41/200...")
check("a page of a long file counts toward the file", abs(q["part"] - 0.2) < 1e-9 and q["what"] == "page 41/200", q)
check("a line that is not progress is left alone", SP.parse("Stopping after the current page...") is None)
pr = SP.Progress(now=0.0)
check("before any line: starting, no time left yet", pr.where() == "Starting the scan" and pr.left(now=0.5) is None
      and SP.left_words(None) == "Working out the time left")
pr.update("[1/20] Figure 1.png - Running OCR on image...", now=0.2)
check("the first file: 0 percent, no time left yet", pr.percent() == 0 and pr.left(now=0.3) is None)
pr.update("[5/20] Figure 5.png - Running OCR on image...", now=8.0)
check("4 of 20 done in 8 seconds: 20 percent, about 30 seconds left", pr.percent() == 20 and abs(pr.left(now=8.0) - 32.0) < 0.01
      and SP.left_words(pr.left(now=8.0)) == "About 30 seconds left", (pr.percent(), pr.left(now=8.0)))
check("between lines the time left counts down", abs(pr.left(now=11.0) - 29.0) < 0.01 and pr.left(now=60) == 0.0)
pr.update("[2/20] Figure 2.png - Running OCR on image...", now=12.0)
check("the share never goes back", pr.percent() == 20)
check("time left in plain words", [SP.left_words(s) for s in (4, 47, 70, 200)] ==
      ["A few seconds left", "About 45 seconds left", "About 1 minute left", "About 3 minutes left"])
check("where it is, in words", pr.where() == "File 2 of 20: Figure 2.png, reading the picture", pr.where())
# ---- the page
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
from docx import Document
docs = []
for i in range(3):
    d = Document(); d.add_paragraph(f"The Kestrel Ground Support Equipment (GSE) and the Telemetry Processing Unit (TPU{i}) are described.")
    docs.append(os.path.join(tmp, f"Kestrel Part {i + 1}.docx")); d.save(docs[-1])
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("acronyms"); app.processEvents()
pg = w.acronym_page
check("no bar before a scan", not pg.scanbar.isVisible())
seen = []
pg.scan_pct.valueChanged.connect(lambda v: seen.append((v, pg.scan_where.text())))
wk = pg.scan(docs)
check("the bar shows while the scan runs", wk is not None and pg.scanbar.isVisible() and pg.scan_tick.isActive())
import time
t0 = time.time()
while pg.worker is not None and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
app.processEvents()
check("the bar moved file by file, naming each", any(v >= 33 and "File 2 of 3: Kestrel Part 2.docx" in t for v, t in seen)
      or any("File 3 of 3" in t for _v, t in seen), seen)
check("the scan finished and the bar is gone", pg.worker is None and not pg.scanbar.isVisible() and not pg.scan_tick.isActive()
      and "GSE" in (pg.session.results if pg.session else {}))
# a long scan, by hand: the time left after the pace is known
pg.scan_prog = SP.Progress(now=time.monotonic() - 12); pg.scanbar.show()
pg.on_progress("[11/20] Figure 11.png - Running OCR on image...")
check("half done after 12 seconds: about 10 seconds left", pg.scan_pct.value() == 50 and pg.scan_left.text() == "50% done. About 10 seconds left"
      and pg.scan_where.text() == "File 11 of 20: Figure 11.png, reading the picture", (pg.scan_pct.value(), pg.scan_left.text()))
pg._end()
# ---- the Effort Dashboard's condensed header
w.go("home"); app.processEvents()
bn = w.home_page.banner
bn.set_condensed(True, save=False); app.processEvents()
check("condensed: no Win themes or Wall of Truth buttons while they are set aside",
      all(b.isHidden() for b in bn.c_toggles.values()) and all(b.isHidden() for b in bn.toggles.values()))
bn.set_condensed(False, save=False); app.processEvents()

# ---- the preview's side wheel (3.71.0): left and right, never a zoom
from PySide6.QtCore import QPoint, QPointF, Qt as _Qt
from PySide6.QtGui import QImage, QWheelEvent
from skqt.foundview import PicView
pv = PicView(); pv.resize(300, 200); pv.show()
img = QImage(2400, 1600, QImage.Format_RGB32); img.fill(0xFFFFFF)
pv.set_picture(img, []); pv.resetTransform(); pv.scale(1.0, 1.0); app.processEvents()
sb = pv.horizontalScrollBar(); sb.setValue(sb.maximum() // 2); x0, s0 = sb.value(), pv.transform().m11()


def wheel(dx, dy):
    pv.wheelEvent(QWheelEvent(QPointF(150, 100), QPointF(150, 100), QPoint(0, 0), QPoint(dx, dy), _Qt.NoButton, _Qt.NoModifier,
                              _Qt.NoScrollPhase, False))
    app.processEvents()


wheel(-120, 0)
x1 = sb.value()
wheel(120, 0); wheel(120, 0)
check("the side wheel moves the picture right, then left, and never zooms", x1 > x0 and sb.value() < x1
      and pv.transform().m11() == s0, (x0, x1, sb.value(), pv.transform().m11()))
wheel(0, 120)
check("up and down still zoom", pv.transform().m11() > s0)
pv.fit(); app.processEvents()
def room(b):
    return b.maximum() - b.minimum()


check("fitted whole, the picture can still be dragged (room past its edges)", room(pv.horizontalScrollBar()) > 0
      and room(pv.verticalScrollBar()) > 0)
for _ in range(30):
    wheel(0, -120)
check("zooming out stops at half the fitted size, and it still drags", abs(pv.transform().m11() - pv._fit_scale() * 0.5) < 1e-6
      and room(pv.horizontalScrollBar()) > 0 and room(pv.verticalScrollBar()) > 0, (pv.transform().m11(), pv._fit_scale()))
for _ in range(40):
    wheel(0, 120)
check("zooming in stops at 16 times", abs(pv.transform().m11() - 16.0) < 1e-6, pv.transform().m11())
ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120), _Qt.NoButton, _Qt.NoModifier, _Qt.NoScrollPhase, False)
ev.ignore(); pv.wheelEvent(ev)
from skqt.foundview import PreviewText
tx = PreviewText(); tx.setPlainText("short"); ev2 = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120), _Qt.NoButton,
                                                              _Qt.NoModifier, _Qt.NoScrollPhase, False)
ev2.ignore(); tx.wheelEvent(ev2)
check("the preview keeps the wheel: the panel around it does not scroll", ev.isAccepted() and ev2.isAccepted())
pv.close()

print(f"QT SCANBAR 371 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
