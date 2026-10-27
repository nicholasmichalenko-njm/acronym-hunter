"""2.47.0 no page of a customer PDF is left out of the compliance review: a scanned page (a picture with no typed text)
is read whole by OCR and comes in with its page number, between the typed pages; pictures inside typed pages are still
not read for the review; Original layout knows the scanned page has no text to box."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_OCR_ENGINE", "tesseract")
import pdfmini


def make(d):
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw, ImageFont
    a = pdfmini.write(os.path.join(d, "a.pdf"), [["L.4 TECHNICAL VOLUME", "The Offeror shall describe its thermal design approach."]])
    c = pdfmini.write(os.path.join(d, "c.pdf"), [["L.6 PAST PERFORMANCE", "The Offeror shall list three contracts."]])
    img = Image.new("RGB", (1700, 2200), "white")
    dr = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 44)
    except OSError:
        f = ImageFont.load_default()
    dr.text((150, 300), "L.5 MANAGEMENT VOLUME", fill="black", font=f)
    dr.text((150, 400), "The Offeror shall provide a staffing plan.", fill="black", font=f)
    b = os.path.join(d, "b.pdf")
    img.save(b, "PDF", resolution=200)
    out = pdfium.PdfDocument.new()
    for p in (a, b, c):
        src = pdfium.PdfDocument(p)
        out.import_pages(src)
        src.close()
    path = os.path.join(d, "RFP_with_scan.pdf")
    out.save(path)
    out.close()
    return path


def run():
    import app_gui as A, layout as LY
    d = tempfile.mkdtemp()
    path = make(d)
    try:                                              # the container has no bundled OCR engine: stand in for it
        A._ocr_raw(A._pil_png(__import__("PIL.Image", fromlist=["Image"]).new("RGB", (50, 50), "white")))
    except Exception:
        A._ocr_raw = lambda _b: "L.5 MANAGEMENT VOLUME\nThe Offeror shall provide a staffing plan."
    typed = A.typed_chunks(path)
    got = A.rfp_chunks(path)
    lab = [l for l, _t in got]
    assert lab == ["RFP_with_scan.pdf (p.1)", "RFP_with_scan.pdf (p.2)", "RFP_with_scan.pdf (p.3)"], lab
    t2 = dict(got)["RFP_with_scan.pdf (p.2)"]
    assert "staffing plan" in t2.lower(), t2
    assert "staffing" not in dict(typed).get("RFP_with_scan.pdf (p.2)", "").lower(), "the typed-only read leaves the scan empty"
    assert LY.page_count(path) == 3
    assert LY.page_map(path, 2, [])["chars"] == 0 and LY.page_map(path, 1, [])["chars"] > 0
    print("scanned pages ok")


if __name__ == "__main__":
    run()
