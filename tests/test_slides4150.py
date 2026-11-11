"""4.15.0: Redline's copy of a slide deck saved as PDF (claude/stationkeeper-pdf-fidelity-plan-4.13.html). A deck is
known by the program that saved it; each slide is one Word page the slide's size, with the slide drawn without its text
behind the page and each box of text in a Word frame where it sits; the copy holds every word of the PDF, the title of
each slide first and then top to bottom, left to right; Check finds no difference and a returned redline's untracked
edit is found; a document is still made as a document; Make it as slides works on any PDF. Fictional (Kestrel decks
made with python-pptx, saved as PDF by LibreOffice here and by PowerPoint on the build PC when present)."""
import json, os, sys, tempfile, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "data"))
import redlinecheck as CK, redlinecopy as RC, redlineslides as SL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


FIX = os.path.join(ROOT, "test_samples", "fidelity")
truth = json.load(open(os.path.join(FIX, "fidelity_slides.json"), encoding="utf-8"))
tmp = tempfile.mkdtemp()
for kind in ("pdf_lo", "pdf_ppt"):
    for stem in sorted(truth):
        pdf = os.path.join(FIX, kind, stem + ".pdf")
        if not os.path.isfile(pdf):
            continue
        check(f"{kind} {stem}: known as slides", RC.layout_of(pdf) == "slides")
        out = os.path.join(tmp, f"{kind}-{stem}.docx")
        res = RC.build(pdf, out)
        with zipfile.ZipFile(out) as z:
            doc = z.read("word/document.xml").decode("utf-8")
            pics = [n for n in z.namelist() if n.startswith("word/media/")]
        n = len(truth[stem])
        check(f"{kind} {stem}: a page and a picture behind it for each slide", res.get("slides") == n and len(pics) == n
              and doc.count("pageBreakBefore") == n - 1 and doc.count('behindDoc="1"') == n, (res, len(pics)))
        check(f"{kind} {stem}: every paragraph in a frame", doc.count("<w:framePr") == res["paragraphs"])
        f = CK.faithful(pdf, out)
        check(f"{kind} {stem}: the copy holds every word of the PDF", not f["differences"], f["differences"][:3])
        side = RC.sidecar(out)
        words = " ".join(p["text"] for p in side["paragraphs"])
        ok = True
        for pi, want in enumerate(truth[stem], 1):
            got = [p["text"] for p in side["paragraphs"] if p["page"] == pi]
            flat = " ".join(got)
            pos = [flat.find(w) for w in want]
            ok = ok and got and got[0] == want[0] and all(p >= 0 for p in pos) and pos == sorted(pos)
        check(f"{kind} {stem}: each slide reads title first, then top to bottom, left to right", ok)
        back = os.path.join(tmp, f"{kind}-{stem}-back.docx")
        with zipfile.ZipFile(out) as z, zipfile.ZipFile(back, "w") as w2:
            for it in z.infolist():
                data = z.read(it.filename)
                if it.filename == "word/document.xml":
                    data = data.decode("utf-8").replace("Industry Day briefing", "Industry Day overview", 1).encode("utf-8")
                w2.writestr(it, data)
        r = CK.returned(out, back)
        check(f"{kind} {stem}: an edit made with Track Changes off is found", len(r["differences"]) == 1
              and r["differences"][0]["now"] == "overview", r["differences"])
doc_pdf = os.path.join(FIX, "pdf_lo", "F01_ruled.pdf")
check("a document is still made as a document", RC.layout_of(doc_pdf) == "document"
      and not RC.build(doc_pdf, os.path.join(tmp, "doc.docx")).get("slides"))
res = RC.build(doc_pdf, os.path.join(tmp, "doc-as-slides.docx"), layout="slides")
check("Make it as slides works on any PDF", res.get("slides") == 1
      and not CK.faithful(doc_pdf, os.path.join(tmp, "doc-as-slides.docx"))["differences"])
n = sum(checks)
print(f"SLIDES 4150 {'PASS' if n == len(checks) and checks else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if checks and n == len(checks) else 1)
