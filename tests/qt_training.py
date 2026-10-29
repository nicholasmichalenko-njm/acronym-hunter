"""2.72.0 Stationkeeper Training in Qt, offscreen: five steps on the rail; Gather adds past matrices and counts the lines
(with the test set); Review lists every line with its picture, filters to the test set, rejects (greyed, never taught),
accepts again, and fixes the text; Train runs Improve Reading on a worker thread (applied when the new reader reads the
held-out lines better, else nothing changes), puts back the previous reader, prepares the docTR package, and opens the
Trainer in the Training program's window; Measure fills the scorecard and an area can be left out and put back; Build
writes one .skknow; export a Knowledge Pack."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
A.TRAINING_APP = True
import corrections as CO
import compliance as CM
from PIL import Image
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); os.makedirs(A.CONFIG_DIR)
A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\nSOW,Acronym,Statement of Work,Include\nTT&C,Acronym,\"Telemetry, Tracking and Command\",Include\n")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
open(A.OCR_FIXES_FILE, "w", encoding="utf-8").write("Misread,Correct,Note\nTT8C,TT&C,\n")
CO.set_dir(os.path.join(tmp, "team_td"))
img = Image.new("RGB", (80, 24), "white")
for i in range(40):
    CO.save_sample(img, f"TT&C link {i}", f"TT8C link {i}", 0.5, "Deck.pptx (Slide 2)", (0, 0, 80, 24))
import studio as _ST                  # 2.74.0: line names carry the time, so one run in ~70 set none aside
while not any(_ST.in_test_set(x["rel"]) for x in CO.samples()) and _ST.TEST_SHARE < 100:
    _ST.TEST_SHARE += 5
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.trainingwin import TrainingWindow, FILTERS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def matrix(name, n):
    text = "L.4 Technical Volume\n" + " ".join([f"The Offeror shall describe item {i} of the thermal design." for i in range(n)] +
                                               [f"Background paragraph {i} explains the history of the office." for i in range(n)])
    M = CM.Matrix(os.path.join(tmp, name), "K")
    M.items = CM.extract([("Section L.docx", [("Page 1", text)])])
    M.outline = CM.parse_outline("Volume I\n1.1 Thermal\n1.2 History")
    for it in M.items:
        if "shall" in it["text"]:
            it["decision"], it["map"] = "Keep", "1.1 Thermal"
        elif "Background" in it["text"]:
            it["decision"] = "Drop"
    M.save()
    return M.path


app = QApplication([]); D.apply(app)
w = TrainingWindow(app); w.resize(1360, 880); w.show(); app.processEvents()
check("five steps and the Trainer on the rail", list(w.step_btns) == ["gather", "review", "train", "measure", "build", "trainer"] and w.stack.count() == 6)
res = w.gather_matrices([matrix("Kestrel_Matrix.xlsx", 20), matrix("Osprey_Matrix.xlsx", 18)])
g = w.lbl_gather.text()
check("Gather: matrices learned, lines counted with the test set", [n for _f, n in res] == [40, 36]
      and "Past compliance matrices gathered: 2" in g and "set aside as the test set" in g, g)
w.go("review"); app.processEvents()
check("Review: every line", w.table.rowCount() == 40)
w.filter.setCurrentText("Test set (set aside)"); app.processEvents()
ts = [w.table.item(r, 5).text() for r in range(w.table.rowCount())]
check("the test set shows, marked", ts and all(x == "Test set" for x in ts), len(ts))
w.filter.setCurrentText(FILTERS[0]); app.processEvents()
w.table.selectRow(0); app.processEvents()
rel = w.selected()[0]
check("a line's picture and texts on the side", w.pic.pixmap() is not None and not w.pic.pixmap().isNull()
      and "Read as: TT8C" in w.lbl_pic.text(), w.lbl_pic.text())
w.set_rejected(True, [rel])
s = next(x for x in CO.samples() if x["rel"] == rel)
check("Reject: never taught, shown as Rejected", s["rejected"] and any(w.table.item(r, 5).text() == "Rejected" for r in range(w.table.rowCount())))
w.set_rejected(False, [rel])
check("Accept puts it back", not next(x for x in CO.samples() if x["rel"] == rel)["rejected"])
check("Fix the text", w.fix_text(rel, "TT&C link fixed") and next(x for x in CO.samples() if x["rel"] == rel)["text"] == "TT&C link fixed")
w.search.setText("fixed"); app.processEvents()
check("search the text", w.table.rowCount() == 1)
w.search.setText(""); app.processEvents()
# Train
w.go("train"); app.processEvents()
check("Train says how many lines there are to teach", "40 lines to teach" in w.lbl_teach.text(), w.lbl_teach.text())


def fake_better(say):
    say("Training the new reader", 0.5)
    say("Testing it on held-out lines", 0.96)
    return {"better": True, "model": os.path.join(tmp, "model", "acronym.traineddata"), "samples": 40, "check_lines": 8,
            "words_correct_before_pct": 80.0, "words_correct_after_pct": 92.5, "chars_correct_before_pct": 95.0,
            "chars_correct_after_pct": 98.0, "date": "2026-10-28", "fixed_examples": [("TT&C link 3", "TT8C link 3")],
            "new_mistakes": []}


loaded = []
A.load_trained_models = lambda folder: loaded.append(folder) or ["acronym.traineddata"]
w.train_fn = fake_better
r = w.improve(wait=True)
check("Teach and Apply runs on a worker thread; a better reader is applied", r and r.get("better") and loaded
      and "APPLIED" in w.result.toPlainText() and "TT&C link 3" in w.result.toPlainText(), w.stage.text())
w.train_fn = lambda say: {"better": False, "samples": 40, "check_lines": 8, "words_correct_before_pct": 90.0,
                          "words_correct_after_pct": 88.0}
loaded.clear()
w.improve(wait=True)
check("not better: nothing changes", not loaded and "NOT APPLIED" in w.result.toPlainText())
w.train_fn = lambda say: (_ for _ in ()).throw(RuntimeError("lstmtraining stopped"))
w.improve(wait=True)
check("a failure says so and leaves the reader alone", "lstmtraining stopped" in w.result.toPlainText()
      and w.stage.text().startswith("Stopped") and w.btn_teach.isEnabled())
rep = w.prepare_package(show=False)
check("the docTR Training Kit package", "Training package written to" in rep, rep.splitlines()[0])
tp = w.open_trainer()
check("the Trainer is a page of this window (2.73.0)", w.stack.currentWidget() is w.trainer and tp is w.trainer)
# Measure
w.go("measure"); app.processEvents()
rows = w.measure()
by = {x["area"]: x for x in rows}
check("Measure: the scorecard", w.sc.rowCount() == len(rows) and by["fixes"]["include"] and by["compliance"]["include"]
      and "area(s) go in the pack" in w.lbl_measure.text())
check("leave an area out, put it back", w.toggle_area("acronyms") is False
      and not {x["area"]: x for x in w.score_rows}["acronyms"]["include"] and w.toggle_area("acronyms") is True)
# Build
w.go("build"); app.processEvents()
w.build_notes.setText("Kestrel and Osprey")
pack = os.path.join(tmp, "Stationkeeper Knowledge 2026-11-03.skknow")
info = w.build_pack(pack)
check("Build writes one .skknow with the areas kept", info and zipfile.is_zipfile(pack) and "In the pack:" in w.lbl_build.text(),
      w.lbl_build.text()[:120])
zp = os.path.join(tmp, "export.zip")
info2 = w.export_knowledge(zp, notes="test")
check("Export a Knowledge Pack", info2 and zipfile.is_zipfile(zp) and info2["version"])
w.close()
n = sum(checks)
print(f"QT TRAINING PASS ({n}/{len(checks)})" if n == len(checks) else f"QT TRAINING FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
