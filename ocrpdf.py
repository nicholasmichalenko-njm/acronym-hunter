"""Page copies with words you can select (2.96.0): a picture (PNG, JPG, TIFF...) or a scanned PDF becomes a PDF copy
whose pages are the original pictures with the words laid invisibly over them, where they are on the page, so Read RFP
cuts sentences from it and Assign boxes them exactly as on a typed PDF (the way a "searchable PDF" works).

- A typed page keeps its own words (from the PDF's text layer), so nothing is read twice or changed.
- A page that is a picture is read by the OCR reader (AI and ML: the reader this PC uses for scanned pages), line by
  line, with each line's place; a line's words share its box in proportion to their letters.
- The copy is made once per file contents (the copy's name carries a fingerprint) in the effort's page copies folder;
  the original is never changed.
- Old Word, Excel and PowerPoint files (.doc, .xls, .ppt) have no reader of their own: their PDF copy from Microsoft
  Office (office_pdf) is read instead.
Writes a plain PDF (images as JPEG, an invisible Courier text layer). Rules only for the writing; nothing leaves the PC.
"""
import hashlib, io, os, re, zlib

IMAGES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif")
LEGACY = (".doc", ".xls", ".ppt")
DPI = 200


def is_image(path):
    return (path or "").lower().endswith(IMAGES)


def is_legacy(path):
    return (path or "").lower().endswith(LEGACY)


def _sha8(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:10]


def copy_path(path, folder):
    stem = re.sub(r"[^A-Za-z0-9 _.-]+", "_", os.path.splitext(os.path.basename(path))[0])[:80]
    return os.path.join(folder, f"{stem} (words) {_sha8(path)}.pdf")


def scanned_pages(pdf):
    """Page numbers (from 1) of a PDF that have no typed words."""
    import pagesent as PS
    try:
        doc = PS.doc_of(pdf)                       # kept while the file is unchanged
    except Exception:
        return []
    return [i + 1 for i, p in enumerate(doc["pages"]) if not p["lines"]]


def needs_copy(path):
    if is_image(path):
        return True
    if (path or "").lower().endswith(".pdf"):
        return bool(scanned_pages(path))
    return False


# ------------------------------------------------------------------ reading the words of a picture
def ocr_lines(img):
    """[(x0, y0, x1, y1, text)] in the picture's pixels, from the OCR reader this PC uses (empty when it cannot run)."""
    import app_gui
    import numpy as np
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    clean = app_gui.enhance_image_for_ocr(buf.getvalue())
    if clean is None:
        return []
    sx = img.width / clean.shape[1]
    sy = img.height / clean.shape[0]
    try:
        got = app_gui._ocr_lines(np.ascontiguousarray(clean))
    except Exception:
        return []
    out = []
    for t in got:
        x0, y0, x1, y1, text = t[:5]
        if str(text).strip():
            out.append((x0 * sx, y0 * sy, x1 * sx, y1 * sy, " ".join(str(text).split())))
    out.sort(key=lambda t: (round(t[1] / 12), t[0]))
    return out


def typed_lines(pdf, index, scale):
    """The typed lines of a PDF page as [(x0, y0, x1, y1, text)] in the rendered picture's pixels."""
    import pagesent as PS
    doc = PS.read(pdf)
    out = []
    for ln in doc["pages"][index]["lines"]:
        l, t, r, b = ln["box"]
        out.append((l * scale, t * scale, r * scale, b * scale, " ".join(ln["text"].split())))
    return out


# ------------------------------------------------------------------ writing the PDF
def _esc(s):
    s = s.encode("cp1252", "replace").decode("latin-1")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write(out, pages):
    """pages: [(PIL image, [(x0, y0, x1, y1, text)] in its pixels, dpi)] -> a PDF at out."""
    objs = []

    def add(b):
        objs.append(b)
        return len(objs)
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
    kids = []
    pages_id = len(objs) + 1 + 0                       # placeholder, fixed below
    page_objs = []
    for img, lines, dpi in pages:
        k = 72.0 / dpi
        W, H = img.width * k, img.height * k
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=82)
        data = buf.getvalue()
        im = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 "
                 b"/Filter /DCTDecode /Length %d >>\nstream\n" % (img.width, img.height, len(data)) + data + b"\nendstream")
        ops = [f"q {W:.2f} 0 0 {H:.2f} 0 0 cm /Im0 Do Q", "BT 3 Tr"]
        for x0, y0, x1, y1, text in lines:
            if not text or x1 <= x0 or y1 <= y0:
                continue
            size = max(2.0, (y1 - y0) * k * 0.86)
            width = (x1 - x0) * k
            tz = max(1.0, min(1000.0, 100.0 * width / (0.6 * size * max(1, len(text)))))
            base = H - y1 * k + (y1 - y0) * k * 0.18
            ops.append(f"/F1 {size:.2f} Tf {tz:.2f} Tz 1 0 0 1 {x0 * k:.2f} {base:.2f} Tm ({_esc(text)}) Tj")
        ops.append("ET")
        content = zlib.compress("\n".join(ops).encode("latin-1"))
        ct = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(content) + content + b"\nendstream")
        page_objs.append((im, ct, W, H))
    pages_id = len(objs) + len(page_objs) + 1
    for im, ct, W, H in page_objs:
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] /Resources << /Font << /F1 %d 0 R >> "
                        b"/XObject << /Im0 %d 0 R >> >> /Contents %d 0 R >>" % (pages_id, W, H, font, im, ct)))
    pid = add(b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % x for x in kids) + b"] /Count %d >>" % len(kids))
    assert pid == pages_id
    cat = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pid)
    outb = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(outb))
        outb += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(outb)
    outb += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        outb += b"%010d 00000 n \n" % o
    outb += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, cat, xref)
    tmp = out + ".part"
    with open(tmp, "wb") as f:
        f.write(bytes(outb))
    os.replace(tmp, out)
    return out


def make(path, folder, lines_of=None, progress=None):
    """The copy with words of a picture or a scanned PDF (made when missing). Returns its path."""
    from PIL import Image, ImageSequence
    os.makedirs(folder, exist_ok=True)
    out = copy_path(path, folder)
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    lines_of = lines_of or ocr_lines
    pages = []
    if is_image(path):
        with Image.open(path) as im:
            frames = [f.copy() for f in ImageSequence.Iterator(im)]
        for n, fr in enumerate(frames, 1):
            if progress:
                progress(f"Picture page {n}/{len(frames)}")
            fr = fr.convert("RGB")
            dpi = DPI
            try:
                dpi = int(round(float((fr.info.get("dpi") or (DPI, DPI))[0]))) or DPI
            except (TypeError, ValueError):
                dpi = DPI
            dpi = max(72, min(600, dpi))
            pages.append((fr, lines_of(fr), dpi))
    else:
        import pypdfium2 as pdfium
        scanned = set(scanned_pages(path))
        pdf = pdfium.PdfDocument(path)
        try:
            for i in range(len(pdf)):
                if progress:
                    progress(f"PDF page {i + 1}/{len(pdf)}")
                page = pdf[i]
                img = page.render(scale=DPI / 72).to_pil().convert("RGB")
                page.close()
                lines = lines_of(img) if (i + 1) in scanned else typed_lines(path, i, DPI / 72)
                pages.append((img, lines, DPI))
        finally:
            pdf.close()
    return write(out, pages)


def page_copy(path, folder, progress=None):
    """The PDF to read and show for a file: a copy with words for a picture or a scanned PDF, the Office copy for an old
    Word, Excel or PowerPoint file, else None (the file is read as it is)."""
    if not folder:
        return None
    if needs_copy(path):
        return make(path, folder, progress=progress)
    if is_legacy(path):
        import office_pdf as OP
        return OP.make(path, folder)
    return None
