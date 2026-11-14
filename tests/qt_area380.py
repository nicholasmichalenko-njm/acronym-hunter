"""3.80.0 the acronym preview, offscreen: the scan's readings of each picture are kept with the effort, so the preview
draws them without reading again (after a restart too) and the next term's first picture is drawn ahead; a plain drag
draws a box, every reading inside it is highlighted with the text read there, a right-button drag moves the picture;
Read this area again reads only the box; Add as a term... adds a term the scan missed, with its place, to the scan's
terms and the effort's list; every fix keeps the picture's part as a training sample's crop, and Learn from an effort
copies the crops. The reader is stood in for. Fictional content (the Kestrel set)."""
import io, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import picreadings as PR
import pictures as PIC

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
SAMPLES = os.path.join(A.BASE_DIR, "test_samples")
paths = {f: os.path.join(SAMPLES, f) for f in os.listdir(SAMPLES)}
A.OCR_FIXES_FILE = os.path.join(tmp, "ocr_corrections.csv")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
calls = [0]


def readings(b):
    calls[0] += 1
    w, h = Image.open(io.BytesIO(b)).size
    return [((w - 150, 20, w - 4, 50), "EPS power budget", 0.95, "read"),
            ((20, h // 2, 200, h // 2 + 30), "ADC5 trade", 0.9, "lines removed"),
            ((20, h - 40, 220, h - 10), "thermal margin", 0.9, "second reader")]


A.scan_readings = readings
PIC.read_region_lines = lambda crop: [((0, 0, crop.width, crop.height), "ADCS trade", 0.93)]
from skqt import foundview as FV
LOC = "Kestrel_PDR_Briefing.pptx (Slide 4, image 'Picture 2' image1.png)"
keep = os.path.join(tmp, "Kestrel app data"); os.makedirs(keep)
PR.use(keep)


def view(term="EPS", **kw):
    fv = FV.FoundView(term, [LOC], lambda n: paths.get(n), **kw)
    fv.resize(760, 640); fv.show(); app.processEvents(); fv.wait(); app.processEvents()
    return fv


fv = view()
check("the first preview of a picture reads it once", fv.state == "picture" and calls[0] == 1, calls)
check("... and its readings are kept with the effort", os.path.isfile(os.path.join(keep, PR.FILE)))
FV._CACHE.clear()
fv2 = view()
check("the next preview draws the kept readings without reading again", fv2.state == "picture" and calls[0] == 1
      and len(fv2.lines) == 3, calls)
PR.use(None); PR.use(keep); FV._CACHE.clear()                    # a restart: the readings come from the effort's folder
fv3 = view()
check("... after a restart too", calls[0] == 1 and len(fv3.lines) == 3, calls)
FV._CACHE.clear()
check("4.30.5: drawing the next picture ahead is off (it ran the PDF reader on a second thread and ended the program)",
      FV.PREFETCH is False and FV.prefetch("EPS", [LOC], lambda n: paths.get(n)) is None and not FV._ALIVE)
FV.PREFETCH = True                                       # the path stays tested for when it is made safe
w = FV.prefetch("EPS", [LOC], lambda n: paths.get(n))
t0 = time.time()
while w is not None and w.isRunning() and time.time() - t0 < 30:
    app.processEvents(); time.sleep(0.02)
app.processEvents()
check("the next term's first picture is drawn ahead (prefetch)", w is not None and any(k[0] == paths["Kestrel_PDR_Briefing.pptx"] for k in FV._CACHE))
check("... and a term with no picture place has nothing to draw ahead", FV.prefetch("SOW", ["Kestrel_Technical_Volume.docx (para 3)"], lambda n: paths.get(n)) is None)

# ---- the box
added = {}
fv = view(on_add_term=lambda t, loc, read, crop: added.update(t=t, loc=loc, read=read, crop=crop))
r2 = fv.lines[1][0]
vp = fv.view.viewport()
p0 = fv.view.mapFromScene(QPointF(r2[0] - 6, r2[1] - 6)); p1 = fv.view.mapFromScene(QPointF(r2[2] + 6, r2[3] + 6))
QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, p0)
QTest.mouseMove(vp, QPoint((p0.x() + p1.x()) // 2, (p0.y() + p1.y()) // 2))
QTest.mouseMove(vp, p1)
QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, p1)
app.processEvents()
check("a plain drag draws a box on the picture", fv.view.area is not None, fv.view.area)
check("... every reading inside it is highlighted with the text read there", fv.reading.text() == "ADC5 trade"
      and len(fv.view._marks) == 1 and fv.area_read == "ADC5 trade", fv.reading.text())
check("... and Read this area again and Add as a term... show", fv.b_readarea.isVisibleTo(fv) and fv.b_addterm.isVisibleTo(fv))
crop = fv.area_crop()
bx = fv.view.area
check("the box's part of the picture", crop is not None and abs(crop.width - (bx[2] - bx[0])) <= 2 and abs(crop.height - (bx[3] - bx[1])) <= 2,
      (crop.size if crop else None, bx))
fv.read_area(wait=True)
check("Read this area again reads only the box", fv.reading.text() == "ADCS trade", fv.reading.text())
fv.view.zoom(4.0); app.processEvents()
hb, vb = fv.view.horizontalScrollBar(), fv.view.verticalScrollBar()
before = (hb.value(), vb.value())
c = vp.rect().center()
QTest.mousePress(vp, Qt.RightButton, Qt.NoModifier, c)
QTest.mouseMove(vp, c + QPoint(60, 40))
QTest.mouseRelease(vp, Qt.RightButton, Qt.NoModifier, c + QPoint(60, 40))
check("a right-button drag moves the picture, and draws no box", (hb.value(), vb.value()) != before and fv.view.area == bx,
      (before, hb.value(), vb.value()))
fv.add_term()
check("Add as a term...: the box's text, with this place and its crop", added.get("t") == "ADCS trade" and added.get("loc") == LOC
      and added.get("read") == "ADC5 trade" and added.get("crop") is not None, added)
A.scan_readings = readings

# ---- on the Acronyms page, in an effort
from skqt import mainwin as MW
import effort as E
import efftrain as ET
cfg = os.path.join(tmp, "config"); os.makedirs(cfg, exist_ok=True)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); w.go("acronyms"); app.processEvents()
ap = w.acronym_page
ap.scan([paths["Kestrel_Technical_Volume.docx"]])
t0 = time.time()
while ap.worker is not None and time.time() - t0 < 240:
    app.processEvents(); time.sleep(0.05)
s = ap.session
check("the effort's scan keeps the pictures' readings in its working folder", PR._state["folder"] == s.ws.root)
from skqt import acrpart as APT
import skqt.acrfast as _AF; _AF.AT_ONCE = True     # 4.30.3: this check reads the workbook straight after a decision
said = APT.missed(ap, "KZQT", LOC, "KZ0T", crop)
check("a missed term joins the scan's terms and the effort's list, with its place", "KZQT" in s.results
      and s.results["KZQT"]["locations"] == [LOC] and E.EffortList(LIST).load().rows.get("KZQT", {}).get("Status") == "In the list", said)
smp = [x for x in ET.load(s.ws.root) if x["kind"] == "missed"]
check("... and a training sample with the right text and the crop", smp and smp[0]["right"] == "KZQT" and smp[0]["read"] == "KZ0T"
      and smp[0]["crop"].startswith("training_crops/") and os.path.isfile(os.path.join(s.ws.root, *smp[0]["crop"].split("/"))), smp)
from skqt.trainingwin import TrainingWindow
tw = TrainingWindow(app)
got = tw.learn_effort(s.ws.root, ask=False)
import glob
check("Learn from an effort copies the crops with the samples", got and got["new"] >= 1
      and glob.glob(os.path.join(A.DATA_DIR if hasattr(A, "DATA_DIR") else A.BASE_DIR, "training_data", "from_efforts_crops", "*.png")), got)
tw.close()
w.close()
PR.use(None)
n = sum(checks)
print(f"QT AREA 380 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
