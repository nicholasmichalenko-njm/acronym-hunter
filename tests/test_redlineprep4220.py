"""4.22.0: Prepare for redline. The Word copy reads like its PDF (pictures, headers and footers as Word's own, each
paragraph's font, text that flows with no text boxes); a PDF's comments go into a Word file the person already has,
beside the comments it holds; a picture is read from its page copy with words and comes out as text that flows with
its figure; the state of a prepared document. Fictional content (the Kestrel program;
tools/make_redline_fixtures.py)."""
import hashlib, json, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "data"))
import ocrpdf, redlinecheck as CK, redlinecopy as RC, redlinemarks as RM, redlinepack as RK, redlineprep as RP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def part(docx, name):
    with zipfile.ZipFile(docx) as z:
        return z.read(name).decode("utf-8") if name in z.namelist() else ""


tmp = tempfile.mkdtemp()
BASE = os.path.join(ROOT, "test_samples", "redline", "R01_cover_figure.pdf")
COM = os.path.join(ROOT, "test_samples", "comments")

# ---- route 1: a PDF becomes a Word file that reads like it
f1 = os.path.join(tmp, "one"); os.makedirs(f1)
res = RP.prepare(BASE, f1)
out = res["path"]
doc = part(out, "word/document.xml")
check("the copy is in the folder, named for its document", os.path.isfile(out) and os.path.basename(out).startswith("R01_cover_figure - redline copy - "))
check("its pictures are kept: the cover's banner, logo, picture and band, and the figure", res["pictures"] >= 4 and RK.pictures(out) >= 4,
      (res["pictures"], RK.pictures(out)))
check("the text flows: no text boxes, no frames", "txbxContent" not in doc and "w:framePr" not in doc)
check("the running header is Word's own header, the solicitation at the left and the section at the right",
      res["headers"] == 1 and "Solicitation KGS-26-R-0007" in part(out, "word/header1.xml")
      and "Section L: Instructions to Offerors" in part(out, "word/header1.xml") and "<w:tab/>" in part(out, "word/header1.xml"))
ft = part(out, "word/footer1.xml")
check("the footer's page number is a field that counts, with the logo", res["footers"] == 1 and " PAGE " in ft and "Page " in ft and "<w:drawing>" in ft, ft[:200])
check("the header's rule is the paragraph's border", "<w:pBdr>" in part(out, "word/header1.xml"))
check("the cover keeps no header (a different first page), and the numbering starts where the PDF's does",
      "<w:titlePg/>" in doc and "w:pgNumType" in doc)
check("the running lines are not in the body", "Solicitation KGS-26-R-0007</w:t>" not in doc and ">Page 1<" not in doc)
check("a heading keeps its own font beside the body's", 'w:ascii="Helvetica"' in doc or 'w:ascii="Arial"' in doc, "no heading font")
check("the caption keeps its slant", "<w:i/>" in doc)
check("the table is a Word table", res["tables"] == 1 and "<w:tbl>" in doc)
brk = doc.count('<w:br w:type="page"/>') + doc.count("<w:pageBreakBefore/>")
check("a page filled to its foot flows on: one page break (after the cover), not one a page", brk == 1, brk)
paras = [p["text"] for p in CK.docx_paragraphs(out) if p["text"].strip()]
check("a paragraph cut by the page's end is one paragraph", any("operations. Paragraph 2 of the scheduling discussion" in p for p in paras),
      [p[:60] for p in paras if "Paragraph 2" in p or p.startswith("2 of")])
fa = CK.faithful(BASE, out)
check("Check: the copy holds every word of its PDF, in order", not fa["differences"], fa["differences"][:3])
check("Check says what stays inside a picture", "in_pictures" in fa)
st = RP.state(f1, BASE)
check("its state: prepared, with when", st["copy"] == out and RP.said(st).startswith("Prepared 20") and RP.said(RP.state(tmp, BASE)) == "Not prepared")

# ---- route 2: its comments, where they were made (scored comment by comment in test_comments4160)
f2 = os.path.join(tmp, "two"); os.makedirs(f2)
r2 = RP.prepare(os.path.join(COM, "R01_cover_figure_commented.pdf"), f2)
check("a commented PDF: tracked changes and Word comments, none placed by position", r2["changes"] == 2 and r2["word_comments"] == 7
      and not r2["by_position"], {k: r2.get(k) for k in ("changes", "word_comments", "by_position")})
check("... and its pictures and header are still there", RK.pictures(r2["path"]) >= 4 and r2["headers"] == 1)
check("its state counts the comments", RP.said(RP.state(f2, os.path.join(COM, "R01_cover_figure_commented.pdf"))).endswith("9 comment(s) placed"))
plain = RP.prepare(os.path.join(COM, "R01_cover_figure_commented.pdf"), os.path.join(tmp, "plain"), comments=False)
check("without the comments when asked", not plain.get("comments") and not RM.read_back(plain["path"])["comments"])

# ---- route 3: the PDF's comments into a Word file the person has
mine = os.path.join(tmp, "My section L.docx"); shutil.copyfile(os.path.join(COM, "C01_prose.docx"), mine)
before = sha(mine)
f3 = os.path.join(tmp, "three")
r3 = RP.into_word(os.path.join(COM, "C01_prose_commented.pdf"), mine, f3)
ref = RC.build(os.path.join(COM, "C01_prose_commented.pdf"), os.path.join(tmp, "ref.docx"))
key = lambda rs: [(c["page"], c["kind"], c["how"], c["became"], c["in_copy"]) for c in rs]   # noqa: E731
check("into my Word file: a dated copy of it in the folder; my file is not changed",
      os.path.basename(r3["path"]).startswith("My section L - redline copy - ") and os.path.dirname(r3["path"]) == f3 and sha(mine) == before)
check("every comment lands where it lands in the app's own copy", key(r3["comments"]) == key(ref["comments"]) and len(r3["comments"]) >= 15,
      [x for x in zip(key(r3["comments"]), key(ref["comments"])) if x[0] != x[1]][:2])
rb = RM.read_back(r3["path"])
check("... as tracked changes and Word comments", r3["changes"] == 6 and r3["word_comments"] == 13 and len(rb["deleted"]) >= 4
      and len([c for c in rb["comments"] if not c["parent"]]) == len([c for c in RM.read_back(ref["path"])["comments"] if not c["parent"]]) >= 13,
      (r3["changes"], r3["word_comments"], len(rb["deleted"]), len(rb["comments"])))
check("the Word file held all of the PDF's words", r3["words"][0] == r3["words"][1] > 400, r3["words"])
side = RC.sidecar(r3["path"])
check("its record names the PDF and the Word file", side["source"] == "C01_prose_commented.pdf" and side["into"] == "My section L.docx"
      and side["format"] == RC.FORMAT and side["paragraphs"])
check("its state says which Word file", "into My section L.docx" in RP.said(RP.state(f3, os.path.join(COM, "C01_prose_commented.pdf"))))
back = CK.returned(r3["path"], r3["path"])
check("Check the returned redline reads it", back["differences"] == [], back["differences"][:2])
# a Word file that already holds comments: they are kept, the new ones follow, every id its own
again = RP.into_word(os.path.join(COM, "C01_prose_commented.pdf"), ref["path"], os.path.join(tmp, "four"))
rb2 = RM.read_back(again["path"])
ids = [c["id"] for c in rb2["comments"]]
n0 = len(RM.read_back(ref["path"])["comments"])
check("a Word file with comments of its own keeps them", len(rb2["comments"]) > n0 and len(ids) == len(set(ids)), (n0, len(rb2["comments"])))
cx = part(again["path"], "word/comments.xml")
import re
pids = re.findall(r'w14:paraId="([0-9A-F]+)"', cx)
check("... and no two comments share a paragraph id", len(pids) == len(set(pids)), len(pids))
none = RP.into_word(BASE, mine, os.path.join(tmp, "five"))
check("a PDF with no comments writes nothing", none["path"] == "" and not none["comments"] and not os.path.isdir(os.path.join(tmp, "five")))

# ---- a picture: read from its page copy with words; text that flows, its figure kept, the page's picture left out
import pypdfium2 as pdfium
pic = os.path.join(tmp, "Section L page.png")
pd = pdfium.PdfDocument(BASE); pd[1].render(scale=200 / 72).to_pil().save(pic); pd.close()
pc = os.path.join(tmp, "page copies")
check("a picture and a PDF are sources; a Word file is not", RP.kind(pic) == "picture" and RP.kind(BASE) == "pdf" and RP.kind(mine) == "")
check("a picture not read yet has no page form until it is made", RP.page_form(pic, pc, make=False) == "")
ocrpdf.make(pic, pc, lines_of=lambda img: [t + (1.0,) for t in ocrpdf.typed_lines(BASE, 1, 200 / 72)])   # the reader's lines
rp = RP.prepare(pic, os.path.join(tmp, "six"), pc)
pp = [p["text"] for p in CK.docx_paragraphs(rp["path"]) if p["text"].strip()]
check("a picture's lines are joined into paragraphs", any(p.startswith("The Offeror shall submit its proposal") and p.rstrip().endswith("of this solicitation.") for p in pp),
      [p[:50] for p in pp[:4]])
check("... its figure is a picture in the flow, and the picture of the page is left out", rp["pictures"] == 1 and RK.pictures(rp["path"]) == 1,
      (rp["pictures"], RK.pictures(rp["path"])))
check("... in a plain font, not the reader's", 'w:ascii="Times New Roman"' in part(rp["path"], "word/styles.xml") and "Courier" not in part(rp["path"], "word/document.xml"))
sp = RC.sidecar(rp["path"])
check("its record names the picture, and the page copy it was read from", sp["source"] == "Section L page.png" and "(words)" in sp.get("read_from", ""))
check("its state is found by the picture's name", RP.state(os.path.join(tmp, "six"), pic)["copy"] == rp["path"])

k = sum(checks)
print(f"REDLINE PREP 4220 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
