"""3.30.1 Make templates builds what the Structure Builder set, offscreen: the structure's front matter takes the place
of the template's fixed TOC block (a TOC field with the appendix headings in it, the caption lists, the List of
Appendices, Acronyms and Abbreviations filled from the effort's approved acronyms, the compliance matrix); divider and
placeholder pages; unnumbered headings; a landscape Word section; a Quick Part where it was placed; the appendices on
their own heading styles. The plain setup export builds the same."""
import os, re, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, outline_ops as O, responseelements as RE, setupdoc as SD
import setuptemplate as ST, structparts as SP
OP.available = lambda: False
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
L = E.EffortList(LIST, "Kestrel")
L.add_or_update("CDRL", Definition="Contract Data Requirements List", Status="Approved")
L.add_or_update("ATP", Definition="Acceptance Test Procedure", Status="Approved")
L.add_or_update("ZZQ", Definition="Not approved yet", Status="Proposed")
L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


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
data = RE.load(cfg)
RE.apply_kit(M, data, ["toc", "lof", "lot", "loa", "acr", "matrix", "exec", "appendices"], vol)
ex = next(l for l in O.labels(M) if l == "Executive Summary")
app1 = O.add_part_item(M, "appendix", "Resumes", vol)
O.add(M, "Key Personnel Resumes", parent=app1)
O.set_break(M, t2, "landscape")
O.set_kind(M, "2 Management", "unnumbered")
O.place_lib(M, t1, {"id": "q1", "kind": "quickpart", "name": "Org chart block"})
div = O.add(M, "Supporting Material", after=t1)
O.set_kind(M, div, "divider")
a = M.items[2]; a["decision"] = "Keep"; SD.place(M, a["id"], t1)
SD.set_volumes(M, "several", "", [vol])
w.review.M.pending = True
check("the structure: elements, an appendix, a landscape section, an unnumbered heading, a divider", "Table of Contents" in O.labels(M)
      and "Appendix A Resumes" in O.labels(M), O.labels(M))
# ---------------------------------------------------------------- Make templates
out = w.setup_page.make_on_templates(opts=ST.options(M), go=True)
check("one template and its setup", out and len(out) == 1 and os.path.isfile(out[0]["setup"]), out)
z = zipfile.ZipFile(out[0]["setup"])
doc = z.read("word/document.xml").decode("utf-8")
sty = z.read("word/styles.xml").decode("utf-8")
check("the template's fixed TOC block gives way to the structure's front matter: one TOC heading per element",
      doc.count(">Table of Contents<") == 1 and ">List of Figures<" in doc and ">List of Tables<" in doc, doc.count(">Table of Contents<"))
check("the TOC field takes the standard's design, with the appendix headings in it", re.search(r'TOC \\t "[^"]*Appendix Heading 1,1', doc) is not None)
check("List of Figures and List of Tables: caption lists", 'TOC \\h \\z \\c "Figure"' in doc and 'TOC \\h \\z \\c "Table"' in doc)
check("List of Appendices: a list of the appendix headings", 'TOC \\h \\z \\t "Appendix Heading 1,1"' in doc)
acr = doc[doc.find(">Acronyms and Abbreviations<"):]
check("Acronyms and Abbreviations: the effort's approved acronyms, in order, with their definitions",
      "ATP" in acr[:4000] and "CDRL" in acr[:4000] and acr.find(">ATP<") < acr.find(">CDRL<") and "ZZQ" not in doc
      and "Acceptance Test Procedure" in acr[:4000], acr[:300])
check("the compliance matrix element: each requirement and where we answer it", ">Compliance matrix<" in doc and f">{a['id']}<" in doc)
check("the front matter sits in the front matter section (before the response)", doc.find(">List of Tables<") < doc.find(">1 Technical Approach<"))
check("a divider page: page breaks around its title", re.search(r'w:type="page"/></w:r></w:p><w:p><w:pPr><w:spacing w:before="4000"[^>]*/>'
                                                                r'<w:outlineLvl w:val="0"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/></w:rPr>'
                                                                r'<w:t xml:space="preserve">Supporting Material', doc) is not None)
check("a placeholder: an unnumbered heading and its pages", '<w:numId w:val="0"/></w:numPr></w:pPr><w:r><w:t xml:space="preserve">Executive Summary' in doc
      and "[Placeholder:" in doc)
check("an unnumbered heading: numbering off", '<w:numId w:val="0"/></w:numPr></w:pPr><w:r><w:t xml:space="preserve">Management' in doc)
check("a landscape Word section: a section break turned landscape", doc.count('w:orient="landscape"') == 1 and "SKSectionMark" not in doc
      and "start:landscape" not in doc)
land = re.search(r'<w:pgSz [^>]*w:orient="landscape"[^>]*/>', doc).group(0)
wv, hv = int(re.search(r'w:w="(\d+)"', land).group(1)), int(re.search(r'w:h="(\d+)"', land).group(1))
check("... wider than tall", wv > hv, land)
check("the Quick Part where it was placed (an AUTOTEXT field)", 'AUTOTEXT "Org chart block"' in doc)
check("the appendices on their own heading styles, which the template now has", 'w:val="AppendixHeading1"' in doc and 'w:val="AppendixHeading2"' in doc
      and 'w:styleId="AppendixHeading1"' in sty and 'Appendix Heading 1' in sty)
check("the template itself is untouched (read only)", os.path.isfile(out[0]["template"]))
# ---------------------------------------------------------------- the plain setup
paths = w.setup_page.export(os.path.join(tmp, "plain"))
pdoc = zipfile.ZipFile(paths[0]).read("word/document.xml").decode("utf-8")
check("the plain setup builds them too: TOC field, acronyms, landscape, appendix styles", "TOC \\t" in pdoc and ">CDRL<" in pdoc
      and 'w:orient="landscape"' in pdoc and 'w:val="AppendixHeading1"' in pdoc)
w.close()
n = sum(checks)
print(f"QT ELEMENTS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
os._exit(0 if n == len(checks) else 1)
