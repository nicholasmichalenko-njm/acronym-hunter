"""2.45.0 original layout: on a PDF page, every review sentence is found where it sits (boxes in reading order);
headings are section titles; a sentence missing from the review is text not in the review; list markers and a
trailing "; and" are not text; a sentence split across a page break is found in parts; the boxes take the decision
colors and the selected sentence is heavier; a click finds the sentence or the red line."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_OCR_ENGINE", "tesseract")
import layout as L, compliance as C, pdfmini


def run():
    import app_gui as A
    d = tempfile.mkdtemp()
    p = pdfmini.write(os.path.join(d, "RFP.pdf"), [
        ["SECTION L - INSTRUCTIONS TO OFFERORS", "L.4 TECHNICAL VOLUME", "The Offeror shall describe its thermal design approach.",
         "The Offeror shall provide a risk register as Attachment J-3.", "For each risk, the Offeror shall:",
         "(a) identify its owner; and", "(b) describe the mitigation.", "Oral presentations will be held at the"],
        ["Government site in Colorado Springs.", "The Offeror shall submit three past performance references."]])
    heads = []
    items = C.extract([("RFP.pdf", A.typed_chunks(p))], heads)
    assert L.page_count(p) == 2
    gone = next(it for it in items if "risk register" in it["text"])
    rest = [it for it in items if it is not gone]
    m1 = L.page_map(p, 1, rest, heads)
    ids1 = [x["id"] for x in m1["items"]]
    on1 = [it["id"] for it in rest if L._page_of(it) == 1]
    assert ids1 == on1 and all(x["rects"] for x in m1["items"]), (ids1, on1)
    assert m1["size"] == (612.0, 792.0) and m1["pages"] == 2 and m1["headings"]
    assert [x["text"] for x in m1["missing"]] == ["The Offeror shall provide a risk register as Attachment J-3"], m1["missing"]
    # boxes sit in reading order down the page (top of each box below the one before)
    tops = [min(r[1] for r in x["rects"]) for x in m1["items"]]
    assert tops == sorted(tops), tops
    m2 = L.page_map(p, 2, items, heads)
    assert not m2["missing"] and len(m2["items"]) == len([it for it in items if L._page_of(it) == 2])
    # a sentence the review holds as one, across the page break: its start at the bottom of page 1, its end at the top of page 2
    joined = dict(next(it for it in items if it["text"].startswith("Oral")))
    joined.update(id="X-1", text="Oral presentations will be held at the Government site in Colorado Springs.", page=1)
    others = [it for it in items if not it["text"].startswith(("Oral", "Government site"))]
    a = L.page_map(p, 1, others + [joined], heads)
    b = L.page_map(p, 2, others + [joined], heads)
    pa = next(x for x in a["items"] if x["id"] == "X-1")
    pb = next(x for x in b["items"] if x["id"] == "X-1")
    assert pa["part"] == "start" and pb["part"] == "end" and not any("Oral" in x["text"] for x in a["missing"]) \
        and not any("Government" in x["text"] for x in b["missing"]), (a["missing"], b["missing"])
    # colors and the selected sentence; hits
    img = L.render(p, 1, 1.5)
    dec = {it["id"]: "Keep" for it in rest}
    sel = m1["items"][0]["id"]
    out = L.overlay(img, m1, dec, 1.5, selected=sel)
    assert out.size == img.size and out.getpixel((5, 5)) == img.getpixel((5, 5))
    l, t, r, bt = m1["items"][0]["rects"][0]
    px = out.getpixel((int((l + r) / 2 * 1.5), int(t * 1.5) - 1))
    assert px[1] > px[0] and px[1] > px[2], px                            # green edge for a compliance requirement
    assert L.hit(m1, (l + r) / 2, (t + bt) / 2) == ("item", sel)
    ml, mt, mr, mb = m1["missing"][0]["rects"][0]
    assert L.hit(m1, (ml + mr) / 2, (mt + mb) / 2) == ("missing", 0) and L.hit(m1, (ml + mr) / 2, (mt + mb) / 2, show_missing=False) is None
    assert L.hit(m1, 600, 780) is None
    print("original layout ok")


if __name__ == "__main__":
    run()
