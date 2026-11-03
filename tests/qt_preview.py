"""3.31.0 the Structure Builder's live preview, offscreen, and the rest of 3.31.0: the volume's pages planned from the
structure, the page budget and Production Standards (a cover, front matter numbered i, ii, iii, the response from 1,
appendices A-1, a landscape section turned, element pages with their entries); a click on a page selects its section;
the preview follows a change; elements keep their pages when the limit is spread; Settings > Units of measurement and
the Unit capture fill the Units of Measurement table."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, outline_ops as O, responseelements as RE, setupdoc as SD
import pagebudget as PB, pageplan as PP, units as UN, excerpts as EX, effortrec as RR, setuptemplate as ST
OP.available = lambda: False
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.add_or_update("ATP", Definition="Acceptance Test Procedure", Status="Approved"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None))
M = w.review.M
M.outline = []
vol = O.add_volume(M, "Technical")
t1 = O.add(M, "Technical Approach", parent=vol)
t2 = O.add(M, "Test Campaign", parent=t1)
O.add(M, "Management", after=t1)
SD.set_volumes(M, "several", "", [vol])
RE.apply_kit(M, RE.load(cfg), ["toc", "lot", "acr", "exec", "uom"], vol)
O.add_part_item(M, "appendix", "Resumes", vol)
PB.set_pages(M, t1, 3)
O.set_break(M, t2, "landscape")
check("an element takes its pages into the page budget (Acronyms: 2)", PB.pages(M, "Acronyms and Abbreviations") == 2)
bl = [l for l in O.in_volume(M, vol) if l in ("Executive Summary", t1)]
check("a response element (Executive Summary) leads the response", bl == ["Executive Summary", t1], bl)
std = {"pagination": {"parts": [{"key": "front", "numbers": {"fmt": "lowerRoman"}},
                                {"key": "body", "numbers": {"fmt": "decimal"}, "header": "{volume_name}"},
                                {"key": "appendix", "numbers": {"fmt": "decimal", "chapter_level": 7}}]},
       "variables": {"volume_name": "Volume I Technical", "marking": "CUI"},
       "hf_layouts": {"body": {"footer": {"center": "{page}", "marking": True}}}}
pages = PP.plan(M, vol, std, {"acronyms": [("ATP", "Acceptance Test Procedure")]})
kinds = [(p["part"], p["num"]) for p in pages]
check("the plan: the template's cover first", pages[0]["kind"] == "cover", kinds)
front = [p["num"] for p in pages if p["part"] == "front"]
check("front matter numbered i, ii, iii...", front[:3] == ["i", "ii", "iii"], front)
body = [p for p in pages if p["part"] == "body"]
check("the response numbered from 1, with its header", body[0]["num"] == "1" and body[0]["header"]["center"] == "Volume I Technical", body[0])
check("a section with 3 pages takes 3", [p["label"] for p in body].count(t1) == 3, [p["label"] for p in body])
check("a landscape section is turned", any(p["orient"] == "landscape" and p["label"] == t2 for p in pages))
check("the footer carries the page number and the marking", body[0]["footer"]["center"] == "1" and body[0]["marking"] == "CUI")
app_p = [p["num"] for p in pages if p["part"] == "appendix"]
check("appendices numbered A-1", app_p[0] == "A-1", app_p)
toc = next(p for p in pages if p["label"] == "Table of Contents")
check("the TOC page lists the response's headings", (t1, "toc") in toc["lines"])
acr = next(p for p in pages if p["label"] == "Acronyms and Abbreviations")
check("the Acronyms page lists the approved acronyms", ("ATP  Acceptance Test Procedure", "row") in acr["lines"])
# ---------------------------------------------------------------- the page budget keeps element pages
parts = PB.parts(M, O.in_volume(M, vol))
got = PB.split(M, parts, 20)
check("spreading a 20-page limit: the Executive Summary keeps its 2 pages, the rest share 18",
      got.get("Executive Summary") == 2 and abs(sum(v for k, v in got.items() if k != "Executive Summary") - 18) < 0.01, got)
# ---------------------------------------------------------------- the Builder's Preview tab
b = w.structure_page
w.go("structure"); app.processEvents()
b.volume = vol; b.refresh()
b.mid_tabs.setCurrentIndex(1); app.processEvents()
check("the Preview tab draws the volume's pages", len(b.preview.pages) >= 8 and "page(s) planned" in b.preview_sum.text(), b.preview_sum.text())
r = next(rr for rr, p in zip(b.preview.rects, b.preview.pages) if p["label"] == "2 Management")
got_lab = []
b.preview.page_clicked.connect(lambda lab: got_lab.append(lab))
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import QEvent
pos = r.center()
b.preview.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, pos, b.preview.mapToGlobal(pos.toPoint()), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
app.processEvents()
check("a click on a page selects its section", got_lab == ["2 Management"] and b.sel == "2 Management", (got_lab, b.sel))
n0 = len(b.preview.pages)
b.answer = "Transition"
b.add_below(); app.processEvents()
check("the preview follows a change: a new first-level section, a new page", len(b.preview.pages) == n0 + 1, (n0, len(b.preview.pages)))
img = b.preview.grab()
if os.environ.get("SK_SHOT"):
    w.grab().save(os.environ["SK_SHOT"])
check("it paints", not img.isNull() and img.width() > 100)
# ---------------------------------------------------------------- units
d = w.settings_page.units(run=False)
d.add({"unit": "m/s", "meaning": "meters per second", "system": "SI", "always": True})
d.add({"unit": "ft", "meaning": "feet", "system": "US customary", "always": False})
d.save()
check("Settings > Units of measurement: kept", [u["unit"] for u in UN.load(cfg)] == ["m/s", "ft"])
pg = w.assign_page
w.go("assign"); app.processEvents()
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
ids = [i for i in pg.view.order if len(pg.view.words.get(i, [])) >= 6]
pg.select(ids[1]); app.processEvents()
pg.show_grab(ids[1], 0, 0, final=True)
check("Unit of measurement is a capture (under More...)", "unit" in pg.more_actions)
xu = pg.do_bin("unit", answer={"bin": "unit", "value": "kilogram", "note": "SI", "sections": []})
rows = UN.for_effort(cfg, RR.Record(w.ws.root))
check("the Units table: the team's every-table units, then the effort's captured ones", rows[0] == ("m/s", "meters per second", "SI")
      and len(rows) == 2 and rows[1][1] == "kilogram", rows)
paths = w.setup_page.export(os.path.join(tmp, "plain"))
xml = zipfile.ZipFile(paths[0]).read("word/document.xml").decode("utf-8")
check("the setup's Units of Measurement table carries them", ">m/s<" in xml and ">meters per second<" in xml and ">kilogram<" in xml)
import teamdata as TD
check("the Our data file carries the units, the response elements and Review's decisions and captures",
      {"units", "elements", "reviewitems"} <= set(TD.PARTS))
w.close()
n = sum(checks)
print(f"QT PREVIEW {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
os._exit(0 if n == len(checks) else 1)
