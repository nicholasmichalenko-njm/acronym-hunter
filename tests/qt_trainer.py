"""2.73.0 the Trainer in Qt, offscreen: open a picture; a drag on it (or the whole picture) is read on a worker thread;
each line the reader found shows with its confidence and a box on the picture; typing a fix picks Save as text; Save
choices keeps the text lines (one tight picture each) and the region, and a Not text reading the scanner keeps today
goes on the ignore list; whole box as one line; OCR fixes from a corrected word; undo the last save; Check in picture
outlines the line holding a term; the real reader reads a rendered line."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
A.TRAINING_APP = True
import corrections as CO
from PIL import Image, ImageDraw, ImageFont
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); os.makedirs(A.CONFIG_DIR)
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\n")
CO.set_dir(os.path.join(tmp, "td"))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.trainingwin import TrainingWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.isfile(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


PIC = os.path.join(tmp, "Deck_slide.png")
img = Image.new("RGB", (640, 160), "white")
dr = ImageDraw.Draw(img)
dr.text((20, 20), "Telemetry link budget", fill="black", font=font(34))
dr.line((20, 110, 600, 110), fill="black", width=3)
img.save(PIC)
app = QApplication([]); D.apply(app)
w = TrainingWindow(app); w.resize(1500, 900); w.show(); app.processEvents()
tp = w.open_trainer()
check("the Trainer opens as a page", w.stack.currentWidget() is tp)
check("open a picture: it shows, listed", tp.load_file(PIC) and tp.list.count() == 1 and tp.img is not None and tp.view.pix is not None)
lines = [((10, 10, 300, 50), "Telemetry 1ink budget", 0.95), ((5, 85, 620, 100), "~~~|", 0.93)]
tp.read_lines = lambda crop: lines
tp.read_one = lambda crop: ("Telemetry 1ink budget ~~~|", 0.55)
tp.run_region((10, 10, 630, 150), wait=True)
check("a box is read on a worker thread; each line shows with its confidence", len(tp.rows) == 2
      and "0.95" in tp.lines_box.findChildren(type(tp.status))[0].text(), [r["text"] for r in tp.rows])
boxes = [i for i in tp.view.scene().items() if i.data(0) == "line"]
check("boxes on the picture: the region, each line, its number", len(boxes) >= 5, len(boxes))
check("whole box as one line is offered", "Telemetry 1ink budget" in tp.lbl_one.text() and tp.entry_one.text().startswith("Telemetry"))
ent = tp.rows[0]["entry"]
ent.setFocus(); ent.selectAll()
QTest.keyClicks(ent, "Telemetry link budget")
check("typing a fix picks Save as text", tp.choice(tp.rows[0]) == "Save as text")
tp.set_choice(2, "Not text")
before = CO.training_stats()
res = tp.save_choices()
after = CO.training_stats()
ign = [r[0] for r in A.read_ocr_ignore_rows()]
check("Save choices: one text line and the region kept", res and res["text"] == 1 and res["junk"] == 1
      and after[0] == before[0] + 1 and after[1] == before[1] + 1, (before, after))
check("Not text the scanner keeps today goes on the ignore list", "~~~|" in ign and res["ignored"] == ["~~~|"], ign)
check("the saved line has the corrected text", any(s["text"] == "Telemetry link budget" and s["read"] == "Telemetry 1ink budget"
                                                  for s in CO.samples()))
check("choices go back to Skip after saving", all(tp.choice(r) == "Skip" for r in tp.rows))
tp.rows[0]["entry"].setText("Telemetry link budget")
added = tp.add_fixes()
check("OCR fixes from a corrected word", ("1ink", "link") in added and any(r[0] == "1ink" for r in A.read_ocr_fix_rows()), added)
tp.entry_one.setText("Telemetry link budget")
n0 = CO.training_stats()[0]
rel = tp.save_whole()
check("save the whole box as one sample", rel and CO.training_stats()[0] == n0 + 1)
what = tp.undo()
check("undo the last save", what and CO.training_stats()[0] == n0)
# a drag on the picture reads that box
tp.read_lines = lambda crop: [((2, 2, 50, 20), "Tele", 0.9)]
tp.view.fitInView(tp.view.pix, Qt.KeepAspectRatio); app.processEvents()
a = tp.view.mapFromScene(30, 15); b = tp.view.mapFromScene(400, 70)
QTest.mousePress(tp.view.viewport(), Qt.LeftButton, Qt.NoModifier, a)
QTest.mouseMove(tp.view.viewport(), b)
QTest.mouseRelease(tp.view.viewport(), Qt.LeftButton, Qt.NoModifier, b)
if tp.worker is not None:
    tp.worker.wait()
app.processEvents()
check("a drag on the picture reads that box", tp.region is not None and 20 < tp.region[0] < 40 and [r["text"] for r in tp.rows] == ["Tele"],
      tp.region)
# Check in picture
tp.read_lines = lambda crop: lines
ok = tp.focus_on(PIC, "Deck_slide.png (Image)", "Telemetry")
if tp.worker is not None:
    tp.worker.wait()
app.processEvents()
check("Check in picture: the line holding the term is outlined", ok and "is line 1" in tp.status.text(), tp.status.text())
tp.focus_target = tp.focus_term = None
# the real reader (on the build PC, where the Tesseract engine ships; this container has none)
tp.read_lines = tp.read_one = None
tp.load_file(PIC)
tp.run_region((10, 10, 630, 70), wait=True)
got = " ".join(r["text"] for r in tp.rows) + " " + tp.entry_one.text()
if A.TESS_DIR:
    check("the real reader reads a rendered line", "Telemetry" in got or "budget" in got, got)
else:
    check("no reader here: the Trainer says so instead of failing", "could not read" in tp.status.text(), tp.status.text())
check("How training works", "Save as text" in tp.show_help(run=False).findChildren(type(w.result))[0].toPlainText())
w.close()
n = sum(checks)
print(f"QT TRAINER PASS ({n}/{len(checks)})" if n == len(checks) else f"QT TRAINER FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
