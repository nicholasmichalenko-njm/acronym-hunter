"""3.32.0 the exact preview and prepagination, offscreen: the Structure Builder's Exact preview in Word (Word's answer
stood in for: a PDF and the page each heading starts on) shows Word's pages with the true count, a click selects the
section, a change drops it; nothing is recorded; the template library's Pages column, Pages... and Measure pages; Make
templates' prepaginated setup choice; Final Checks > Response elements."""
import json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, office_pdf as OP, outline_ops as O, responseelements as RE, setupdoc as SD
import pagebudget as PB, setuptemplate as ST, templatelib as TL, templatereg as TR, prodrules as PRL
OP.available = lambda: False
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from _qpfixture import with_glossary

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
O.add(M, "Test Campaign", parent=t1)
t2 = O.add(M, "Management", after=t1)
SD.set_volumes(M, "several", "", [vol])
RE.apply_kit(M, RE.load(cfg), ["toc", "acr"], vol)
PB.set_pages(M, t1, 3)
b = w.structure_page
w.go("structure"); app.processEvents()
b.volume = vol; b.refresh()
b.mid_tabs.setCurrentIndex(1); app.processEvents()
import exactpreview as EP, qpmeasure as QM
check("the Preview tab has Exact preview in Word (on with Word on this PC, off without it)", b.exact_btn.isVisible()
      and b.exact_btn.isEnabled() == EP.available() and not b.plan_btn.isVisible())
n_plan = len(b.preview.pages)
exports0 = len(SD.setup_of(M)["exports"])
seen = {}


def word(cmd, env, timeout):                      # Word's answer: the PDF it saves and where each heading starts
    import pypdfium2 as pdfium
    seen.update(env)
    doc = pdfium.PdfDocument.new()
    for k in range(7):
        doc.new_page(612, 792)
    doc.save(env["SK_PDF"]); doc.close()
    return json.dumps({"ok": True, "pages": 7, "heads": [{"t": "Table of Contents", "p": 2}, {"t": t1, "p": 4}, {"t": t2, "p": 7}]})


res = b.exact_preview(runner=word, wait=True)
check("Word lays out the volume's setup, made in a dated folder of the setup documents",
      res is not None and os.path.isfile(seen.get("SK_DOC", "")) and os.sep + "Exact preview" + os.sep in seen.get("SK_DOC", ""), seen.get("SK_DOC"))
check("Word's pages show, each an image", len(b.preview.pages) == 7 and all(p.get("image") is not None and not p["image"].isNull()
                                                                            for p in b.preview.pages))
check("the true page count, and the plan's beside it", f"7 page(s) in Word (the plan: {n_plan})" in b.preview_sum.text(), b.preview_sum.text())
check("Back to the plan shows", b.plan_btn.isVisible())
check("nothing recorded: no export, no template version", len(SD.setup_of(M)["exports"]) == exports0 and not TR.names(cfg), TR.names(cfg))
r = b.preview.rects[4]
got = []
b.preview.page_clicked.connect(lambda lab: got.append(lab))
pos = r.center()
b.preview.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, pos, b.preview.mapToGlobal(pos.toPoint()), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
app.processEvents()
check("a click on Word's page 5 selects its section (it started on page 4)", got == [t1] and b.sel == t1, (got, b.sel))
check("it paints", not b.preview.grab().isNull())
if os.environ.get("SK_SHOT"):
    w.grab().save(os.environ["SK_SHOT"])
b.answer = "Transition"
b.add_below(); app.processEvents()
check("a change drops Word's pages: the plan again, and it says so", b.exact is None and "from before a change" in b.preview_sum.text()
      and not b.plan_btn.isVisible(), b.preview_sum.text())
b.exact_preview(runner=word, wait=True)
b.drop_exact()
check("Back to the plan", b.exact is None and "planned" in b.preview_sum.text())
bad = b.exact_preview(runner=lambda *a: json.dumps({"ok": False, "why": "-1"}), wait=True)
check("Word failing: no preview, and the reason", bad is None and b.exact is None and b.exact_btn.isEnabled())
# ---------------------------------------------------------------- the library: Pages, Measure pages
src = os.path.join(tmp, "Boilerplate.docx")
with_glossary(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), src)
lib = TL.Library(cfg)
cards, _err = TL.collect(src, PRL.for_effort(tempfile.mkdtemp()), lib)
TL.save_collected(lib, src, [c for c in cards if c.key == "quickparts"])
d = w.prodstd_page.library(run=False)
d.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("quickpart")); app.processEvents()
check("the Pages column: a Quick Part not measured yet", d.t.columnCount() == 5 and d.t.item(0, 4).text() == "not measured")
check("Measure pages needs Word on this PC (on with it, off without it)", d.measure_btn.isEnabled() == QM.available())
d.t.selectRow(0)
check("Pages...: typed", d.type_pages(2) and d.t.item(0, 4).text() == "2 (typed)", d.t.item(0, 4).text())
d.t.selectRow(1)
res = d.measure(runner=lambda cmd, env, t: json.dumps([{"pages": 4, "why": ""}]))
check("Measure pages: Word's count kept on the selected one", list(res.values()) == [4] and d.t.item(1, 4).text() == "4 (measured)", res)
d.close()
# ---------------------------------------------------------------- Make templates: a prepaginated setup
from skqt.maketemplates import MakeTemplatesDialog
ST.set_prepaginate(M, True)
md = MakeTemplatesDialog(w.prodstd_page, start="effort")
check("Make templates offers a prepaginated setup, as last chosen", md.prepag.isChecked() and "planned pages" in md.prepag.text())
md.close()
kept = {}


def word2(cmd, env, timeout):
    import zipfile
    x = zipfile.ZipFile(env["SK_DOC"]).read("word/document.xml").decode("utf-8")
    kept["n"] = x.count("<w:p><w:pPr><w:pageBreakBefore/></w:pPr></w:p>")
    kept["next"] = "<w:pageBreakBefore/>" in x.split("Transition")[0][-300:]
    return word(cmd, env, timeout)


b.exact_preview(runner=word2, wait=True)
check("a prepaginated setup on the template: the 3-page section keeps 2 empty pages, the next starts a new page",
      kept.get("n") == 2 and kept.get("next"), kept)
# ---------------------------------------------------------------- Final Checks: the response elements
M.items.append({"id": "L-90", "text": "The proposal shall include a table of contents, a list of figures and an executive summary.",
                "decision": "Keep", "loc": "Section L (p.9)", "file": "rfp.pdf", "type": ""})
cp = w.checks_page
rows = cp.check_elements()
names = {(r["check"], r["element"]) for r in rows}
check("Final Checks > Response elements: what the RFP names that the volume lacks", {("Missing", "List of Figures"), ("Missing", "Executive Summary")} <= names
      and ("Missing", "Table of Contents") not in names, names)
check("... listed in the table, with a summary", cp.e_table.rowCount() == len(rows) and "to look at" in cp.e_sum.text())
p = cp.export_elements(os.path.join(tmp, "elements.xlsx"))
check("... and exported", os.path.isfile(p) and "Elements_Check" in w.out_path("element_check"))
w.close()
n = sum(checks)
print(f"QT EXACT {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
