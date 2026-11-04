"""Word draws the page (3.40.0): a kept cover, title page or back cover laid out by Word on this PC and shown as a
picture, exactly as it prints. Word saves a PDF of the page (exactpreview.lay_out: macros off, no prompts, only the Word
this job started is ended) and its first page becomes a PNG. Pictures are kept by the page's fingerprint, so a page is
drawn once until it changes. Without Word the app's sketch is shown, labelled as a sketch. Offline: no network."""
import hashlib, os, shutil, tempfile

import exactpreview as XP

SUB = "previews"


def fingerprint(data):
    return hashlib.sha256(data or b"").hexdigest()[:16]


def available():
    return XP.available()


def cached(parts_dir, data):
    """The PNG Word drew for these bytes, or ''."""
    p = os.path.join(parts_dir, SUB, fingerprint(data) + ".png")
    return p if os.path.isfile(p) else ""


def pdf_to_png(pdf, png, width_px=900):
    """The PDF's first page as a PNG, width_px wide. Returns png or ''."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        try:
            page = doc[0]
            w, _h = page.get_size()
            img = page.render(scale=max(0.5, width_px / max(1.0, w))).to_pil()
            img.save(png, "PNG")
        finally:
            doc.close()
        return png
    except Exception:  # noqa: BLE001  an unreadable PDF gives no picture
        return ""


def draw(parts_dir, data, runner=None, timeout=300):
    """Word lays out the page and the first page becomes a PNG kept beside the parts. Returns {"ok", "png"} or
    {"ok": False, "why"}. runner (tests): passed to exactpreview.lay_out."""
    if not data:
        return {"ok": False, "why": "No page to draw."}
    have = cached(parts_dir, data)
    if have:
        return {"ok": True, "png": have, "cached": True}
    if runner is None and not available():
        return {"ok": False, "why": "Word on this PC draws the exact page; this is the app's sketch."}
    work = tempfile.mkdtemp(prefix="sk_page_")
    try:
        docx, pdf = os.path.join(work, "page.docx"), os.path.join(work, "page.pdf")
        with open(docx, "wb") as f:
            f.write(data)
        res = XP.lay_out(docx, pdf, runner=runner, timeout=timeout)
        if not res.get("ok"):
            return {"ok": False, "why": res.get("why", "Word could not draw the page.")}
        os.makedirs(os.path.join(parts_dir, SUB), exist_ok=True)
        png = os.path.join(parts_dir, SUB, fingerprint(data) + ".png")
        if not pdf_to_png(pdf, png + ".tmp.png"):
            return {"ok": False, "why": "Word's page could not be turned into a picture."}
        os.replace(png + ".tmp.png", png)
        return {"ok": True, "png": png, "cached": False}
    finally:
        shutil.rmtree(work, ignore_errors=True)
