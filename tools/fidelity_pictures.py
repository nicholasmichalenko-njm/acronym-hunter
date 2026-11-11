"""How alike Redline's copy and its PDF look (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, step 1).

Pairs <stem>.pdf (the customer's) with <stem> - copy.pdf (the copy, saved as PDF by Word on the build PC), draws each
page in grey at DPI and scores it with SSIM (1.0 is the same picture; text that moved a line scores lower than one
whose words changed a pixel). Also: the page counts. Run on the build PC after tools/fidelity_pdfs.ps1 and
fidelity.py --keep: python tools/fidelity_pictures.py <pdf folder> <copies folder>. Rules only (No AI)."""
import os, sys

import numpy as np

DPI = 60
C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2


def pages(path):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        out = []
        for i in range(len(pdf)):
            img = pdf[i].render(scale=DPI / 72, grayscale=True).to_pil().convert("L")
            out.append(np.asarray(img, dtype=np.float64))
        return out
    finally:
        pdf.close()


def _box(a, k=7):
    """Mean over k x k windows (valid part), by sums."""
    s = np.cumsum(np.cumsum(np.pad(a, ((1, 0), (1, 0))), 0), 1)
    return (s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]) / (k * k)


def ssim(a, b):
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a, b = a[:h, :w], b[:h, :w]
    ma, mb = _box(a), _box(b)
    va, vb = _box(a * a) - ma * ma, _box(b * b) - mb * mb
    cov = _box(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cov + C2)) / ((ma * ma + mb * mb + C1) * (va + vb + C2))
    return float(s.mean())


def compare(pdf, copy_pdf):
    a, b = pages(pdf), pages(copy_pdf)
    scores = [ssim(x, y) for x, y in zip(a, b)]
    return {"pages": (len(a), len(b)), "ssim": scores, "mean": sum(scores) / len(scores) if scores else 0.0}


if __name__ == "__main__":
    src, cps = sys.argv[1], sys.argv[2]
    tot = []
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(".pdf"):
            continue
        stem = f[:-4]
        cp = os.path.join(cps, stem + " - copy.pdf")
        if not os.path.isfile(cp):
            continue
        r = compare(os.path.join(src, f), cp)
        tot.append(r["mean"])
        print(f"{stem:24s} pages {r['pages'][0]}/{r['pages'][1]}  look alike {r['mean']:.3f}  "
              + " ".join(f"{s:.2f}" for s in r["ssim"]))
    if tot:
        print(f"{'Mean':24s} {sum(tot) / len(tot):.3f}")
