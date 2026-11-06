"""3.61.0 Acronym Findings and the dashboard cleanup, offscreen. The preview boxes the scan's own readings, pages through
every picture in the file, centers a find even at the picture's edge, shows what a clicked box read, fixes the reading
and uses it as the meaning; the term's card is lighter (meaning, the find as text, the definition box, actions, preview,
details folded); Why is a term missing? gives the reasons; the acronym set's answer key is written and scored; the
dashboard's stages, gate goals, win themes, All overviews and Evaluation card are set aside; the calendar keeps the wheel
for the page, jumps to today and lists one person's day. The reader is stood in for. Fictional content."""
import csv, datetime, io, os, sys, tempfile, time
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
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
SAMPLES = os.path.join(A.BASE_DIR, "test_samples")
paths = {f: os.path.join(SAMPLES, f) for f in os.listdir(SAMPLES)}
A.OCR_FIXES_FILE = os.path.join(tmp, "ocr_corrections.csv")
os.makedirs(A.CONFIG_DIR, exist_ok=True)


def readings(b):
    w, h = Image.open(io.BytesIO(b)).size
    return [((w - 150, 20, w - 4, 50), "EPS power budget", 0.95, "read"),
            ((20, h // 2, 200, h // 2 + 30), "ADC5 trade", 0.9, "lines removed"),
            ((20, h - 40, 220, h - 10), "thermal margin", 0.9, "second reader")]


real = A.scan_readings
A.scan_readings = readings
from skqt.foundview import FoundView
got = {}
LOC = "Kestrel_PDR_Briefing.pptx (Slide 4, image 'Picture 2' image1.png)"
fv = FoundView("EPS", [LOC], lambda n: paths.get(n), on_meaning=lambda t: got.setdefault("meaning", t),
               on_find_text=lambda t: got.__setitem__("find", t))
fv.resize(760, 640); fv.show(); app.processEvents(); fv.wait(); app.processEvents()
check("the preview boxes the scan's own readings (the same reader and passes)", fv.state == "picture"
      and sorted(k for _b, k in fv.view.boxes).count("line") == 3 and "sel" in [k for _b, k in fv.view.boxes], fv.info.text())
box = fv.finds[0]
c = fv.view.mapToScene(fv.view.viewport().rect().center())
cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
check("a find at the picture's edge sits in the middle of the view", abs(c.x() - cx) < 30 and abs(c.y() - cy) < 30, (c, cx, cy))
check("the find's line shows as text (It read, and the card's find line)", fv.reading.text() == "EPS power budget"
      and got.get("find") == "EPS power budget")
r2 = fv.lines[1][0]
fv.clicked(QPointF((r2[0] + r2[2]) / 2, (r2[1] + r2[3]) / 2))
check("click a box: what the scan read there", fv.reading.text() == "ADC5 trade" and fv.view._mark is not None)
fv.reading.setText("ADCS trade")
check("Fix the reading: kept for every later scan on this PC", fv.fix_reading() == "ADCS trade"
      and any(r[0] == "ADC5 trade" and r[1] == "ADCS trade" for r in A.read_ocr_fix_rows()))
fv.reading.setText("Electrical Power Subsystem")
check("Use as the meaning: the words go to the card's definition box", fv.use_meaning() == "Electrical Power Subsystem"
      and got.get("meaning") == "Electrical Power Subsystem")
check("Page < and >: on for a file with more than one picture", fv.b_pnext.isEnabled())
k = fv.page_step(1); fv.wait(); app.processEvents()
check("Page >: the file's next picture, even with no find on it", k == 1 and fv.state == "picture" and "2 of 2" in fv.where.text(), fv.where.text())
fv.page_step(-1); fv.wait()
check("Page <: back to the first", fv.page_k == 0 and "1 of 2" in fv.where.text())
fv.step(1); fv.wait()
check("Find > past the last find leaves the paging and goes back to the place", fv.page_k is None and fv.k == 0)
A.scan_readings = real

# ---- the term's card on Acronym Findings
from skqt import mainwin as MW
import effort as E
cfg = os.path.join(tmp, "config"); os.makedirs(cfg, exist_ok=True)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
from skqt import modes as _modes
_modes.save(show_set_aside=False)   # 3.61.0: a test before may have left the pages set aside showing
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); w.go("acronyms"); app.processEvents()
ap = w.acronym_page
ap.scan([paths["Kestrel_Technical_Volume.docx"]])
t0 = time.time()
while ap.worker is not None and time.time() - t0 < 240:
    app.processEvents(); time.sleep(0.05)
s = ap.session
ap.select("SOW"); app.processEvents()
check("the card: the status and the meaning up top, the find as text, the definition box",
      ap.card.title.text() == "SOW" and hasattr(ap, "find_text") and ap.find_text.isReadOnly() and ap.typed is not None)
check("... details folded (pills, counts, every place)", not ap.details_btn.parentWidget() is None
      and ap.details_btn.text() == "Show details" and not ap.places.isVisibleTo(ap.card))
ap.details_btn.click(); app.processEvents()
check("Show details opens them", ap.details_btn.text() == "Hide details" and ap.places.isVisibleTo(ap.card))
if ap.where_view is not None:
    ap.where_view.wait()
    ap.where_view.reading.setText("Statement of Work")
    ap.where_view.text.setTextCursor(ap.where_view.text.textCursor())
    ap.where_view.b_usemean.click(); app.processEvents()
    check("Use as the meaning fills the definition box", ap.typed.text() == "Statement of Work")

# ---- Why is a term missing?
import acrwhy as WH
from skqt import acrcheck as AC
s.exclude(["SOW"], True)
check("why: omitted in this effort", any("omitted in this effort" in x for x in WH.why(s, "SOW")["reasons"]))
s.exclude(["SOW"], False)
out = WH.why(s, "QQZ")
check("why: never read in these files", out["verdict"].endswith("not in the results.") and any("never read" in x for x in out["reasons"]), out)
cache = s.last_scan["cache"]
first = next(iter(cache.values()))
first["chunks"].append(["Kestrel_Technical_Volume.docx (para 99)", "the ZZQ unit"])
first["chunks"].append(["Kestrel_System_Diagram.png (Image)", "EP5 budget"])
out = WH.why(s, "ZZQ")
check("why: read in typed text but not taken as a term", out["read"]["typed"] == 1 and any("did not take it" in x for x in out["reasons"]), out)
out = WH.why(s, "EPZ")
check("why: near misses read in pictures, with how to fix the reading", "EP5" in out["near"] and any("Fix the reading" in x for x in out["reasons"]), out)
ap.f_search.setText("QQZ"); app.processEvents()
dlg = AC.why_window(ap, run=False)
check("Why is a term missing? opens with the search's term and answers", "QQZ" in dlg.answer.toPlainText() and dlg.result_["reasons"])
ap.f_search.setText(""); app.processEvents()

# ---- the acronym set's answer key
import acreval as AE
s.choose("SOW", "Statement of Work") if "SOW" in s.results else None
s.set_status(["TBD"], "Rejected") if "TBD" in s.results else None
SET = os.path.join(tmp, "Acronym Set"); os.makedirs(SET)
p = AC.save_key(ap, SET)
rows = AE.read_key(SET)
check("Save as the answer key: found rows for decided terms, the file named, Where kept", p and any(r["Term"] == "SOW" and r["Expect"] == "found"
      and r["File"] == "Kestrel_Technical_Volume.docx" and r["Where"] in ("typed", "picture") for r in rows), rows[:3])
sc = AE.score(s.results, rows, [paths["Kestrel_Technical_Volume.docx"]])
check("the set scores: recall overall, typed and pictures, and per file", sc["recall"] == 100.0 and sc["files"] and sc["by_where"]["typed"]["expected"] >= 1, sc)
less = {k: v for k, v in s.results.items() if k != "SOW"}
sc2 = AE.score(less, rows, [paths["Kestrel_Technical_Volume.docx"]])
check("... a term the scan dropped lowers the score and is listed as missed", sc2["recall"] < 100 and any(m["Term"] == "SOW" for m in sc2["missed"]))
AE.save_key(s, SET)
check("saving again for the same files replaces their rows (no doubles)", len(AE.read_key(SET)) == len(rows))

# ---- the dashboard's set-asides and the calendar
import menufocus as MF
import effortrec as RR, workspace as W
check("set aside: stages, gate goals, win themes, All overviews, the Evaluation card",
      {"stages", "gategoals", "winthemes", "alloverviews", "evalcard"} <= MF.hidden({}))
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
rec = RR.Record(ws0.root)
today = datetime.date.today()
rec.add_task("Send the kickoff notes", owner="A. Lee", due=today.isoformat())
rec.add_task("Draft the management volume", owner="K. Park", due=today.isoformat())
rows_ = [(st["id"], st["name"], today.isoformat()) for st in rec.stages]
rec.edit_stages(rows_)
cal = rec.calendar(first=today, last=today, who="A. Lee")
check("calendar for one person: their tasks only", [t for k, t in cal.get(today, []) if k == "task"] == ["Send the kickoff notes (A. Lee)"], cal)
cal2 = rec.calendar(first=today, last=today, stages=False)
check("stages set aside: no stage items on the calendar", not any(k == "stage" for k, _t in cal2.get(today, [])) and
      any(k == "stage" for k, _t in rec.calendar(first=today, last=today).get(today, [])))
w.go("home"); app.processEvents()
hp = w.home_page
hp.refresh(); app.processEvents()
check("the dashboard: no Stages card, no stage pill, no All overviews", not hp.banner.all_ov.isVisibleTo(w) if hasattr(hp.banner, "all_ov") else True)
check("A day's list for: everyone on the effort", {"A. Lee", "K. Park"} <= {hp.day_who.itemText(i) for i in range(hp.day_who.count())})
m0 = (hp.cal.yearShown(), hp.cal.monthShown())
ev = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, -120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
QApplication.sendEvent(hp.cal, ev); app.processEvents()
check("the wheel over the calendar never changes the month", (hp.cal.yearShown(), hp.cal.monthShown()) == m0)
hp.cal.setCurrentPage(2001, 1)
hp.jump_today(); app.processEvents()
check("Jump to today: this month and today's list", (hp.cal.yearShown(), hp.cal.monthShown()) == (today.year, today.month)
      and hp.day == today)
hp.day_who.setCurrentText("K. Park"); items = hp.show_day(); app.processEvents()
txt = " ".join(t for _k, t in items)
check("a day's list for one person", "Draft the management volume" in txt and "Send the kickoff notes" not in txt, items)

print(f"QT FINDINGS 361 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
