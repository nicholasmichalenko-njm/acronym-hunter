"""4.5.0: one PDFium call at a time (pdflock). Every FPDF function in pypdfium2.raw is wrapped once; documents, pages
and text still read the same; two threads reading PDFs together (the extraction beside the page on screen) finish
with the same text as one thread alone. Fictional fixtures (rfp_walk)."""
import os, sys, threading
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pdflock as PL
import pypdfium2 as pdfium
import pypdfium2.raw as raw

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


n = PL.install()
check("every PDFium function is wrapped, once", n > 100 and PL.install() == 0 and hasattr(raw.FPDFText_LoadPage, "__wrapped__"), n)
FILES = [os.path.join(ROOT, "test_samples", "rfp_walk", f) for f in ("SOW.pdf", "Section_L_print.pdf")]


def text_of(path):
    d = pdfium.PdfDocument(path)
    out = []
    for i in range(len(d)):
        pg = d[i]
        tp = pg.get_textpage()
        out.append(tp.get_text_range())
        pg.render(scale=0.5).to_pil()
        tp.close(); pg.close()
    d.close()
    return "\n".join(out)


alone = {p: text_of(p) for p in FILES}
check("documents, pages, text and pictures read as before", all(len(t) > 100 for t in alone.values()), {p: len(t) for p, t in alone.items()})
got, errs = [], []


def work(p):
    try:
        for _ in range(15):
            got.append(text_of(p) == alone[p])
    except Exception as e:  # noqa: BLE001
        errs.append(repr(e))


ts = [threading.Thread(target=work, args=(FILES[i % 2],)) for i in range(4)]
for t in ts:
    t.start()
for t in ts:
    t.join()
check("four threads reading together: no crash, the same text every time", not errs and len(got) == 60 and all(got), (errs[:2], len(got)))
print(f"PDFLOCK {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
