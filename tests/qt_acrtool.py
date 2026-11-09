"""3.50.0 where an acronym was found, shown again, and Acronym Finder in its own window, offscreen.

The card shows the place: a PDF page drawn whole with the typed find boxed (and stepping through finds and places),
typed text in Word or PowerPoint with the find highlighted, and a picture inside a file drawn with the reader's lines
boxed (the reader is stood in for: no OCR engine in the test container). Acronym Finder opens from Home (Your Tools) and
alone (--acronyms), keeps its own list apart from every effort, scans, exports the list (Word, Excel, CSV) and checks
first use in Word files. Fictional content."""
import csv, io, os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


SAMPLES = os.path.join(A.BASE_DIR, "test_samples")
paths = {f: os.path.join(SAMPLES, f) for f in os.listdir(SAMPLES)}
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
from skqt.foundview import FoundView, PicView
# ---- a PDF page: the page drawn, the typed find boxed
fv = FoundView("SOW", ["Kestrel_Program_Manual.pdf (p.1)", "Kestrel_PDR_Briefing.pptx (Slide 2)"], lambda n: paths.get(n))
fv.resize(760, 640); fv.show(); app.processEvents()
st = fv.wait()
check("a PDF page is drawn with the typed find boxed and selected", st == "picture" and any(k == "sel" for _b, k in fv.view.boxes)
      and any(k == "typed" for _b, k in fv.view.boxes) and fv.where.text().startswith("Place 1 of 2"), (st, fv.info.text()))
img = fv.view.grab().toImage()
check("the picture shows (not blank)", len({img.pixel(x, y) for x in range(5, img.width() - 5, 7) for y in range(5, img.height() - 5, 7)}) > 3)
fv.step(1); app.processEvents(); fv.wait()
check("Find > past the last find goes to the next place: typed text with the find highlighted", fv.state == "text"
      and "SOW" in fv.text.toPlainText() and "Slide 2" in fv.text.toPlainText() and fv.where.text().startswith("Place 2 of 2"))
fv.step(-1); app.processEvents(); fv.wait()
check("Find < comes back to the page, the find selected", fv.state == "picture" and fv.k == 0)
big = fv.enlarge(run=False); big.wait()
check("Enlarge: the same place in a big window", big.k == 0 and big.state == "picture" and big.stack.minimumHeight() >= 560)
fv.show_place(1); fv.wait()
check("clicking a place in the list shows it", fv.k == 1 and fv.state == "text")
fv2 = FoundView("SOW", ["Kestrel_Technical_Volume.docx (para 3)"], lambda n: paths.get(n)); fv2.show(); app.processEvents()
check("a Word paragraph shows the passage with the find highlighted", fv2.wait() == "text" and "SOW" in fv2.text.toPlainText())

# ---- a picture inside a file: drawn whole, the reader's lines boxed (reader stood in for)
real = A.scan_readings                                 # 3.61.0: the preview boxes the scan's own readings
LOW = max(0.0, A.ocr_cutoff() - 0.2)                   # below the reader's cutoff, whichever reader this PC has
A.scan_readings = lambda b: [((20, 20, 220, 50), "EPS power budget", 0.99, "read"), ((20, 70, 200, 100), "ADCS trade", LOW, "read"),
                             ((20, 120, 200, 150), "thermal margin", 0.99, "second reader")]
fv3 = FoundView("EPS", ["Kestrel_System_Diagram.png (Image)"], lambda n: paths.get(n)); fv3.resize(700, 600); fv3.show(); app.processEvents()
fv3.wait()
kinds = sorted(k for _b, k in fv3.view.boxes)
check("a picture is drawn whole: the term boxed in yellow, other readings green, low confidence red", fv3.state == "picture"
      and "sel" in kinds and "find" in kinds and "low" in kinds and "line" in kinds, (fv3.state, kinds, fv3.info.text()))
A.scan_readings = lambda b: (_ for _ in ()).throw(RuntimeError("no reader"))
from skqt import foundview as FVM
FVM._CACHE.clear()
fv4 = FoundView("EPS", ["Kestrel_System_Diagram.png (Image)"], lambda n: paths.get(n)); fv4.show(); app.processEvents(); fv4.wait()
check("when the reader cannot run, the picture still shows and says why", fv4.state == "picture" and "could not run" in fv4.info.text())
A.scan_readings = real
fv5 = FoundView("SOW", ["Elsewhere.pdf (p.2)"], lambda n: None); fv5.show(); app.processEvents()
check("a file no longer on this PC says so", fv5.state == "missing" and "not on this PC" in fv5.text.toPlainText())

# ---- Acronym Finder
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
import skqt.toolshome as TH                                     # 3.53.0: the tools are on Home (Your Tools)
check("Acronym Finder is a tool on Home", "acrfinder" in TH.TOOLS and TH.TOOLS["acrfinder"][2] == "window")
tw = w.open_tool("acronyms"); app.processEvents()
check("it is a window of its own, with its own list apart from every effort", tw.isVisible() and tw is not w
      and tw.page.session is not None and tw.host.ws.root.startswith(cfg) and not tw.page.b_cust.isVisibleTo(tw))
check("opening it again brings the same window forward", w.open_tool("acronyms") is tw)
files = [paths["Kestrel_Technical_Volume.docx"], paths["Kestrel_Program_Manual.pdf"]]
tw.page.scan(files)
t0 = time.time()
while tw.page.worker is not None and time.time() - t0 < 300:
    app.processEvents(); time.sleep(0.05)
s = tw.page.session
check("Scan files: the terms are listed with their meanings", s.results and tw.page.table.rowCount() > 0 and "SOW" in s.results)
tw.page.select("SOW"); app.processEvents()
wv = tw.page.where_view; wv.wait()
check("selecting a term shows where it was found", wv.state in ("picture", "text"))
# ---- symbols: Greek, sub- and superscripts, accents, units in the definition box
from skqt import symbols as SYM
from PySide6.QtWidgets import QLineEdit
card_box = tw.page.typed
check("the definition box has the Symbols button and the right-click menu", getattr(card_box, "_sk_symbols", False))
card_box.setText("H2O"); card_box.setSelection(1, 1)
SYM.convert("sub", card_box)
check("Make the selection subscript: H₂O", card_box.text() == "H₂O")
card_box.setText("m2"); card_box.setCursorPosition(2)
SYM.convert("sup", card_box)
check("superscript with nothing selected takes the character before the cursor: m²", card_box.text() == "m²")
SYM.convert("normal", card_box)
check("Make normal text puts it back: m2", card_box.text() == "m2")
card_box.setText("m"); card_box.setCursorPosition(1)
SYM.insert("\u0307", card_box)
check("an accent attaches to the letter before it: ṁ", card_box.text() == "ṁ")
card_box.setText("Velocity "); card_box.setCursorPosition(9)
pk = SYM.open_picker(card_box); app.processEvents()
SYM._focused(card_box)
pk.tabs.setCurrentIndex([pk.tabs.tabText(i) for i in range(pk.tabs.count())].index("Greek")); app.processEvents()
delta = next(b for c, b in pk.buttons if c == "Δ")
delta.click(); app.processEvents()
check("the picker inserts into the box last used: Velocity Δ", card_box.text() == "Velocity Δ")
pk.q.setText("sub 2"); app.processEvents()
check("search finds a symbol by name (sub 2: ₂)", [c for c, _b in pk.buttons] == ["₂"])
check("Recent keeps what was used", SYM._recent and SYM._recent[0] == "Δ")
pk.close()
wv2 = tw.page.where_view
if wv2.state == "text":
    cur = wv2.text.textCursor(); cur.select(cur.SelectionType.WordUnderCursor); cur.setPosition(0); cur.movePosition(cur.MoveOperation.EndOfWord, cur.MoveMode.KeepAnchor)
    wv2.text.setTextCursor(cur)
    got_sel = tw.page.use_selected()
    check("Use the selected words: the passage's words go in the definition box", got_sel and card_box.text() == got_sel)
from skqt.acrtool import list_rows, export_list
rows = list_rows(s)
check("the list: each term and its meaning, no excluded or decided-away rows", rows and all(not t.startswith("[") for t, _m in rows))
out = {}
for ext in ("docx", "xlsx", "csv"):
    out[ext] = tw.export(os.path.join(tmp, f"list.{ext}"))
doc = zipfile.ZipFile(out["docx"]).read("word/document.xml").decode("utf-8")
got = list(csv.reader(open(out["csv"], encoding="utf-8-sig")))
check("Export the list: a Word table, an Excel sheet and a CSV", "<w:tbl" in doc and "SOW" in doc and got[0] == ["Acronym", "Meaning"]
      and len(got) - 1 == len(rows) and os.path.getsize(out["xlsx"]) > 0)
rep = tw.first_use([paths["Kestrel_Technical_Volume.docx"]], run=False)
check("Check first use: a row for each acronym in the Word file", rep is not None and rep.get("first_use"), rep and rep.get("summary"))
from skqt.acrtool import FirstUseDialog
d = FirstUseDialog(tw, rep)
check("the first use report shows and exports", d.table.rowCount() == len(rep["first_use"]) and d.export(os.path.join(tmp, "fu.xlsx")))
check("3.88.0: each volume's Acronyms table is its own tab", isinstance(rep.get("tables"), list)
      and d.tables_tab.rowCount() == len(rep["tables"]))
# 3.88.0: the easy ones in one click, named, and the card's suggestions with source and why
pg = tw.page
fake = {"definition": "Kestrel Support Facility", "where": "RFP p. 41 (L.3.6)", "sentence": "Kestrel Support Facility (KSF)"}
pg.session.results["KSF"] = {"status": "", "count": 1, "locations": [], "definitions": ["Kestrel Support Facility"],
                             "customer_definitions": ["Kestrel Support Facility"], "custdef_all": [fake], "custdef_source": fake}
pg.session.results["L-3"] = {"status": "", "count": 1, "locations": [], "definitions": []}
pg.fill()
check("the link names the terms one click adds and why", pg.bulk.isVisibleTo(tw) and "KSF" in pg.bulk.text() and "one customer definition" in pg.bulk.text(),
      pg.bulk.text())
pg.select("KSF"); app.processEvents()
check("the card: the customer's definition first, with where it was spelled out", pg.suggest_rows
      and pg.suggest_rows[0]["source"] == "Customer" and "RFP p. 41" in pg.suggest_rows[0]["why"], getattr(pg, "suggest_rows", None))
check("Add them: each with its customer definition", "KSF" in pg.add_one_customer()
      and pg.session.results["KSF"].get("effort") == "In the list")
check("Start a new list clears it", tw.new_list() and not tw.page.session.results)
from skqt.acronympage import AcronymPage
check("Acronyms (in an effort) has Open in its own window", w.acronym_page.b_window.text() == "Open in its own window")
# ---- First Use Check: one document on its own
def make_docx(path, paras):
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>' for t in paras)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f'<w:body>{body}<w:sectPr/></w:body></w:document>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("word/document.xml", doc)
    return path


fu_doc = make_docx(os.path.join(tmp, "Kestrel Volume I.docx"), [
    "The PDR schedule is set and the team is ready for the PDR.",
    "The Preliminary Design Review (PDR) was held in March with the full team present.",
    "The Critical Design Review (CDR) follows the PDR by six months.",
    "After the Critical Design Review (CDR) the build starts, and the CDR closes the design.",
    "The EPS margin is positive and the EPS mass is within the allocation.",
    "The Attitude Determination and Control System (ADCS) points the payload; the ADCS meets every pointing requirement."])
check("First Use Check is a tool on Home, and on Submission Check", TH.TOOLS["firstuse"][2] == "window"
      and w.qa_page.b_firstuse.text().startswith("First Use Check"))
fw = w.open_tool("firstuse"); app.processEvents()
check("First Use Check is a window of its own", fw.isVisible() and fw is not w)
fw.set_files([fu_doc])
rep2 = fw.check(wait=True)
by = {r["term"]: r for r in (rep2 or {}).get("first_use", [])}
check("used before it is defined: a fix, with where it is spelled out", by.get("PDR", {}).get("level") == "bad"
      and "spelled out later" in by["PDR"]["state"], by.get("PDR"))
check("defined more than once: listed with where it is spelled out again", by.get("CDR") and by["CDR"]["also_defined"], by.get("CDR"))
check("never defined: a fix", by.get("EPS", {}).get("level") == "bad" and "Never defined" in by["EPS"]["state"], by.get("EPS"))
check("defined at first use: fine", by.get("ADCS", {}).get("state", "").startswith("Defined at first use"), by.get("ADCS"))
check("Problems shows the fixes and checks only", fw.t.rowCount() == len([r for r in rep2["first_use"] if r["level"] in ("bad", "warn")])
      and fw.t.rowCount() >= 2)
fw.t.setCurrentCell(0, 0); app.processEvents()
check("selecting a row shows its first use in the document", fw.fv is not None and fw.fv.wait() == "text"
      and fw.fv.where.text().startswith("Place 1 of"), fw.fv and (fw.fv.state, fw.fv.where.text()))
check("the report exports", fw.export(os.path.join(tmp, "first_use_check.xlsx")))
# 3.51.0: a table of contents entry is never the first use; the person can choose the first use
toc_doc = os.path.join(tmp, "Kestrel Volume II.docx")
make_docx(toc_doc, ["Contents", "The CDRL schedule overview", "The Contract Data Requirements List (CDRL) names every deliverable.",
                    "Each CDRL item has a due date and the CDRL is updated monthly."])
import zipfile as _z
with _z.ZipFile(toc_doc) as zz:
    parts = {n: zz.read(n) for n in zz.namelist()}
doc_xml = parts["word/document.xml"].decode()
doc_xml = doc_xml.replace('<w:p><w:r><w:t xml:space="preserve">The CDRL schedule overview', '<w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:t xml:space="preserve">The CDRL schedule overview')
parts["word/document.xml"] = doc_xml.encode()
with _z.ZipFile(toc_doc, "w") as zz:
    for n, b in parts.items():
        zz.writestr(n, b)
fw.set_files([toc_doc])
rep3 = fw.check(wait=True)
cd = next((r for r in rep3["first_use"] if r["term"] == "CDRL"), {})
check("a table of contents entry is never the first use: the first use is where it is defined", cd.get("state", "").startswith("Defined at first use")
      and "contents" not in cd.get("loc", ""), cd)
fw.show_box.setCurrentIndex(fw.show_box.findData("all")); app.processEvents()
row_i = next(i for i, r in enumerate(fw.shown) if r["term"] == "CDRL")
fw.t.setCurrentCell(row_i, 0); app.processEvents(); fw.fv.wait()
later = next(l for l in fw.session.results["CDRL"]["locations"] if l != cd["loc"])       # the contents entry, chosen on purpose
rep4 = fw.set_here(later)
cd2 = next((r for r in rep4["first_use"] if r["term"] == "CDRL"), {})
check("This place is the first use: the chosen place counts, and an earlier spell-out is reported", cd2.get("loc") == later
      and cd2.get("level") in ("bad", "warn", "info"), cd2)
check("the chosen first use is kept for the next check", fw.session.first_use_set.get("CDRL"))
fw.close()
tw.close(); w.close()
n = sum(checks)
print(f"QT ACRONYM FINDER {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
