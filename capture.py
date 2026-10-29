"""Add text the reader missed (2.70.0): read what is inside an area of a page (the PDF's own text first, the built-in
OCR when the page is a picture) and add it to the review as a sentence in its place, ready to assign. Also: a list's
lead-in that an older read kept only inside its items becomes a sentence of its own. Rules and the local OCR engine
only (No generative AI); nothing leaves the PC.
"""
import re
import diag
import compliance as C


def _clean(text):
    text = (text or "").replace("\r", "\n").replace("­", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)                 # a word broken at a line end
    return " ".join(text.split())


def text_in(pdf_path, page_index, rect, ocr=None):
    """The text inside rect (left, top, right, bottom in PDF points, top-left origin) of a page. Returns (text, how):
    how is "pdf" (the PDF's own text), "ocr" (read from the picture) or "" (nothing readable)."""
    import pypdfium2 as pdfium
    l, t, r, b = rect
    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[page_index]
        w, h = page.get_size()
        l, r = max(0.0, min(l, r)), min(w, max(l, r))
        t, b = max(0.0, min(t, b)), min(h, max(t, b))
        if r - l < 2 or b - t < 2:
            return "", ""
        tp = page.get_textpage()
        try:
            got = _clean(tp.get_text_bounded(left=l, bottom=h - b, right=r, top=h - t))
        finally:
            tp.close()
        if len(re.sub(r"\W", "", got)) >= 2:
            return got, "pdf"
        scale = 3.0                                          # the picture of the area, sharp enough for OCR
        img = page.render(scale=scale, crop=(l, h - b - 0, w - r, t)).to_pil().convert("RGB")
    finally:
        doc.close()
    try:
        lines = (ocr or _ocr_lines)(img)
    except Exception:
        diag.swallowed()
        return "", ""
    lines = sorted(lines, key=lambda x: (round(x[1] / 12), x[0]))
    got = _clean(" ".join(x[4] for x in lines))
    return (got, "ocr") if got else ("", "")


def _ocr_lines(img):
    import numpy as np
    import app_gui
    return app_gui._ocr_lines(np.array(img))


def add_sentence(M, file_name, text, after_id=None, page=None, how="", at_start=False):
    """Add text to the review as a sentence of file_name, right after the sentence after_id (else at the end of that
    file's sentences), in the same RFP section. Returns the new row."""
    text = " ".join((text or "").split())
    if not text:
        return None
    it = C.classify(text, "", ("", ""), "") or C.context_item(text, "", ("", ""), "")
    if not it:
        it = {"text": text, "lead": "", "section": "", "section_title": "", "actor": "", "type": "Context",
              "strength": "", "suggest": "Context", "modal": "", "xrefs": "", "compound": False}
    src = {"pdf": "the PDF's text", "ocr": "OCR", "typed": "typed"}.get(how, "the page")
    it.update({"file": file_name, "loc": f"{file_name} (p.{page}, added from {src})" if page else f"{file_name} (added from {src})",
               "page": page, "context": text[:700], "key": C.text_key(text), "decision": "", "map": "", "owner": "",
               "status": "", "notes": "", "response_page": "", "links": "", "learned": "", "context_for": "",
               "new": "Added from the page", "id": ""})
    idx = [i for i, x in enumerate(M.items) if x.get("file") == file_name]
    at = next((i + 1 for i, x in enumerate(M.items) if x.get("id") == after_id), None) if after_id else None
    if at is None:
        at = (idx[0] if at_start else idx[-1] + 1) if idx else len(M.items)
    prev = M.items[at - 1] if at > 0 and M.items[at - 1].get("file") == file_name else None
    if prev is not None:
        it["section"], it["section_title"] = prev.get("section", ""), prev.get("section_title", "")
        if page is None:
            it["page"] = prev.get("page")
    M.items.insert(at, it)
    C.assign_ids(M.items)
    M.log(it["id"], f"added from the page ({src})")
    M.pending = True
    return it


def add_lead_ins(M):
    """2.70.0: a list's lead-in ("The Offeror shall address the following:") that an older read kept only inside its
    items becomes a sentence of its own, just before the list's first item. Decisions are kept. Returns the rows added."""
    if M is None or not M.items:
        return []
    have = {(x.get("file"), C.text_key(x.get("text", ""))) for x in M.items}
    added, seen = [], set()
    i = 0
    while i < len(M.items):
        x = M.items[i]
        ld = (x.get("lead") or "").strip()
        k = (x.get("file"), C.text_key(ld))
        if ld and ld.endswith(":") and k not in have and (k, i) not in seen:
            prev = M.items[i - 1] if i else None
            if prev is None or (prev.get("lead") or "").strip() != ld or prev.get("file") != x.get("file"):
                it = C.classify(ld, "", (x.get("section", ""), x.get("section_title", "")), "") or \
                    C.context_item(ld, "", (x.get("section", ""), x.get("section_title", "")), "")
                if it:
                    it.update({"file": x.get("file", ""), "loc": x.get("loc", ""), "page": x.get("page"),
                               "context": ld[:700], "key": C.text_key(ld), "decision": "", "map": "", "owner": "",
                               "status": "", "notes": "", "response_page": "", "links": "", "learned": "",
                               "context_for": "", "new": "Lead-in, now a sentence of its own", "id": "",
                               "section": x.get("section", ""), "section_title": x.get("section_title", "")})
                    M.items.insert(i, it)
                    added.append(it)
                    have.add(k)
                    i += 1
            seen.add((k, i))
        i += 1
    if added:
        C.assign_ids(M.items)
        for it in added:
            M.log(it["id"], "lead-in made a sentence of its own")
        M.pending = True
    return added
