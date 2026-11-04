"""3.50.0 previews: every kind Word can draw gets a specimen page built from the item (the style in use, a table in the
table style, the header and footer on the page without broken fields, numbered headings, a list, a TOC); Word's
picture is kept by the item's content and dropped when it changes; Quick Parts are drawn in the pass that counts their
pages; and nothing is lost from a Quick Part kept as built between the file, the library and the template. Word is
stood in for by the tests (no Word in the container). Fictional content."""
import io, json, os, re, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_TEST", "1")
import templatelib as TL, libconvert as CV, libpreview as LP, libcats as LC, prodrules as PRL, prodtemplate as PT, libimport as LI

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def doc_of(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    return z, z.read("word/document.xml").decode("utf-8")


cfg = tempfile.mkdtemp()
d = PRL.load(cfg)
d["company"]["style_defs"]["Body Text"] = {"type": "paragraph", "font": "Georgia", "size": 12}
d["company"]["style_defs"]["Kestrel Emphasis"] = {"type": "character", "italic": True, "color": "C00000"}
PRL.save(cfg, d)
CV.convert(cfg)
lib = TL.Library(cfg)
item = lambda kind, name=None: next(i for i in lib.items if i["kind"] == kind and (name is None or lib.base_of(i) == name))

body = item("style", "Body Text")
z, doc = doc_of(LP.specimen(lib, body))
check("a paragraph style's specimen: sample paragraphs in that style, a document (not a template), no Quick Parts",
      re.search(r'<w:pStyle w:val="[^"]*Body[^"]*"/>', doc) and "Body Text. Our approach" in doc
      and "document.main+xml" in z.read("[Content_Types].xml").decode() and not any(n.startswith("word/glossary") for n in z.namelist()))
emph = item("style", "Kestrel Emphasis")
_z, doc = doc_of(LP.specimen(lib, emph))
check("a character style's specimen: a run in it inside body text", "<w:rStyle " in doc and "Kestrel Emphasis in this style" in doc)
hf = item("hf", "body")
z, doc = doc_of(LP.specimen(lib, hf))
hdr = " ".join(z.read(n).decode() for n in z.namelist() if re.match(r"word/header\d+\.xml$", n))
check("a header and footer's specimen: the last section keeps the header and footer", "<w:headerReference" in doc
      and "<w:footerReference" in doc.split("<w:sectPr")[-1])
check("its style and property fields show their names, so Word shows no error", "STYLEREF" not in hdr and "[Volume Name]" in hdr, hdr[-300:])
check("the page number field stays a field", "PAGE" in " ".join(z.read(n).decode() for n in z.namelist() if "footer" in n))
_z, doc = doc_of(LP.specimen(lib, item("toc")))
check("the TOC's specimen: a TOC field and headings to fill it", "TOC" in doc and "Technical approach" in doc)
_z, doc = doc_of(LP.specimen(lib, item("heading_numbering")))
check("heading numbering's specimen: headings at three levels", doc.count("Heading") >= 3)
ln = item("list_numbering")
_z, doc = doc_of(LP.specimen(lib, ln))
check("a list's specimen: an item at each level", "an item at this level" in doc)
for k in ("variables", "page_setup", "pagination", "table_look", "captions"):
    it = item(k)
    check(f"the app draws {k.replace('_', ' ')}: no specimen", not LP.word_can(it) and LP.specimen(lib, it) is None)

# ---- Word draws (stood in for), kept by the item's content
def word(cmd, env, timeout):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument.new(); pdf.new_page(612, 792); pdf.save(env["SK_PDF"])
    return json.dumps({"ok": True, "pages": 1, "heads": []})


pics, pages = LP.draw(lib, [body["id"], hf["id"], item("variables")["id"]], runner=word)
check("Word's picture is kept for each item it can draw", pics[body["id"]].endswith(".png") and os.path.isfile(pics[body["id"]])
      and LP.cached(lib, body) == pics[body["id"]] and pics[hf["id"]].endswith(".png"))
check("an item the app draws says so", "app draws" in pics[item("variables")["id"]])
v = dict(lib.values(body)); v["size"] = 13
lib.update(body["id"], v)
check("an item that changes drops its old picture", LP.cached(lib, lib.get(body["id"])) == "")
again, _p = LP.draw(lib, [hf["id"]], runner=lambda *a: (_ for _ in ()).throw(AssertionError("Word started again")))
check("a picture already drawn is not drawn again", again[hf["id"]] == LP.cached(lib, hf))

# ---- Quick Parts: drawn in the pass that counts their pages
from _qpfixture import with_glossary
QP_SRC = os.path.join(tempfile.mkdtemp(), "Kestrel Master.dotx")
with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), QP_SRC, table_hdr=True)
items, _err = LI.stage(QP_SRC, PRL.for_effort(tempfile.mkdtemp()), lib)
for it in items:
    it["take"] = it["kind"] == "quickpart"
rep = LI.commit(lib, QP_SRC, items)
qid = next(i for i in rep["added"] if lib.get(i)["kind"] == "quickpart")
seen = {}


def qp_word(cmd, env, timeout):
    seen["pdfdir"] = env.get("SK_PDFDIR")
    import pypdfium2 as pdfium
    n = len([x for x in env["SK_LIST"].split("\n") if x])
    for k in range(1, n + 1):
        pdf = pdfium.PdfDocument.new(); pdf.new_page(612, 792); pdf.save(os.path.join(env["SK_PDFDIR"], f"qp_{k}.pdf"))
    return json.dumps([{"pages": 2, "why": ""}] * n)


pics, pages = LP.draw(lib, [qid], qp_runner=qp_word)
check("a Quick Part is drawn by Word in the pass that counts its pages", seen.get("pdfdir") and pages.get(qid) == 2
      and pics[qid].endswith(".png") and LP.cached(lib, lib.get(qid)), (pics, pages))
check("drawing never saves the library (the window keeps the pages)", not TL.Library(cfg).get(qid).get("pages"))
check("the Quick Part is in its own category", LC.place(lib, lib.get(qid))[0] == "quickparts")

# ---- nothing lost from a Quick Part kept as built
import prodquickparts as QP
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
th = next(i for i in lib.items if i["kind"] == "quickpart" and i["name"] == "Table header")
work = PRL.for_effort(cfg)
work["quick_parts"] = {"one_gallery": True, "entries": []}
TL.use_in_standard(lib, th["id"], work)
work["quick_parts"]["entries"][0]["as_built"] = True
import prodparts as PP
job = PT.make(work, tempfile.mkdtemp(), "", parts_dir=PP.parts_dir(cfg))


def part_body(path, name):
    g = zipfile.ZipFile(path).read("word/glossary/document.xml").decode("utf-8")
    m = re.search(r'<w:docPart>(?:(?!</w:docPart>).)*?<w:name w:val="' + re.escape(name) + r'"/>.*?<w:docPartBody>(.*?)</w:docPartBody>', g, re.S)
    return m.group(1) if m else None


a, b = part_body(QP_SRC, "Table header"), part_body(job.copy, "Table header")
check("a Quick Part kept as built reaches the template whole: its table, widths and field", a and b and
      re.sub(r"\s+", "", a) == re.sub(r"\s+", "", b), (a or "")[:200] + " | " + (b or "")[:200])

n = sum(checks)
print(f"LIBRARY 3.50 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
