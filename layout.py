"""Original layout (2.45.0): a PDF customer document page as it looks, with every review sentence on it boxed.

page_map(path, page_no, items, headings) reads the page's text with PDFium (the same PDF engine the reader uses) and
finds where each sentence of the review sits, word by word in reading order, with the text check's own rules
(textcheck.py): list markers, a trailing "; and", single letters and filler words are not text; lines the compliance
reader treats as headings are section titles. A sentence that runs onto the next page is found in parts. What is left
is text not in the review, shown so nothing is missed. Positions are in PDF points from the page's top left.
Rules only (No AI); nothing leaves the PC.
"""
import re
import textcheck as T

WORD = T.WORD


def _lines(t):
    """[(start, end)] of each line in the page text (PDFium ends generated lines with \\r\\n)."""
    out, s = [], 0
    for m in re.finditer(r"\r\n|\n|\r", t):
        out.append((s, m.start()))
        s = m.end()
    out.append((s, len(t)))
    return out


def _words(t):
    """[(word, start, end, line)] in reading order, list markers and trailing connectors dropped like the text check."""
    out = []
    for li, (a, b) in enumerate(_lines(t)):
        line = t[a:b]
        keep = T.norm(line)
        lead = len(line) - len(T.LIST_MARK.sub("", line, count=1)) if T.LIST_MARK.match(line) else 0
        body = line[lead:lead + len(keep)] if keep else ""
        for m in WORD.finditer(body):
            out.append((m.group(0).lower(), a + lead + m.start(), a + lead + m.end(), li))
    return out


def page_count(path):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        return len(pdf)
    finally:
        pdf.close()


def page_map(path, page_no, items, headings=()):
    """{"size": (w, h) in points, "pages": n, "items": [{"id", "rects", "part"}], "headings": [rects],
    "missing": [{"text", "rects"}]} for one page. items: the review sentences of this file (id, text, lead, section,
    section_title, loc); only those on this page and its neighbours are looked for."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        page = pdf[page_no - 1]
        w, h = page.get_size()
        tp = page.get_textpage()
        n = tp.count_chars()
        t = tp.get_text_range(0, n) if n else ""
        seq = _words(t)
        words = [x[0] for x in seq]
        cover = [None] * len(words)               # None: not in the review; item id; "#h" a heading

        def rects(a, b):
            out = []
            for i in range(tp.count_rects(a, max(0, b - a))):
                l, bot, r, top = tp.get_rect(i)
                out.append((l, h - top, r, h - bot))
            return out

        def mark(ws, val, at_start=False, at_end=False):
            k = len(ws)
            if not k or k > len(words):
                return None
            spots = [0] if at_start else [len(words) - k] if at_end else range(len(words) - k + 1)
            best = None
            for p in spots:
                if words[p:p + k] == ws:
                    if any(c is None for c in cover[p:p + k]):
                        best = p
                        break
                    best = p if best is None else best
            if best is None:
                return None
            for q in range(best, best + k):
                if cover[q] is None:
                    cover[q] = val
            return best, best + k
        found = {}
        here = [it for it in items if _page_of(it) in (page_no - 1, page_no, page_no + 1)]
        for it in sorted(here, key=lambda it: abs((_page_of(it) or page_no) - page_no)):
            ws = T.line_words(it.get("text") or "")
            span = mark(ws, it["id"])
            part = ""
            if span is None and len(ws) >= 4:            # runs over a page break: its end at the top, or its start at the bottom
                for k in range(len(ws) - 1, 2, -1):
                    span = mark(ws[-k:], it["id"], at_start=True) if _page_of(it) == page_no - 1 or _page_of(it) == page_no else None
                    if span:
                        part = "end"
                        break
                    span = mark(ws[:k], it["id"], at_end=True) if _page_of(it) in (page_no, page_no + 1) else None
                    if span:
                        part = "start"
                        break
            if span is not None:
                found.setdefault(it["id"], []).append((span, part))
            ld = (it.get("lead") or "").strip()
            if ld:
                lspan = mark(T.line_words(ld), it["id"])
                if lspan is not None:
                    found.setdefault(it["id"], []).append((lspan, "lead"))
        heads = []
        for li, (a, b) in enumerate(_lines(t)):           # section titles: the reader's heading test, then the headings used
            if t[a:b].strip() and T._looks_heading(t[a:b].strip()):
                ks = [q for q, x in enumerate(seq) if x[3] == li and cover[q] is None]
                for q in ks:
                    cover[q] = "#h"
                if ks:
                    heads.append((seq[ks[0]][1], seq[ks[-1]][2]))
        titles = {((it.get("section") or "") + " " + (it.get("section_title") or "")).strip() for it in items}
        titles |= {((x.get("num") or "") + " " + (x.get("title") or "")).strip() for x in headings}
        for title in titles:
            span = mark(T.line_words(title), "#h")
            if span:
                heads.append((seq[span[0]][1], seq[span[1] - 1][2]))
        out = {"size": (w, h), "pages": len(pdf), "items": [], "headings": [], "missing": [], "chars": n}
        for iid, spans in found.items():
            rs = []
            parts = set()
            for (a, b), part in spans:
                rs += rects(seq[a][1], seq[b - 1][2])
                parts.add(part)
            out["items"].append({"id": iid, "rects": rs, "part": "end" if "end" in parts else "start" if "start" in parts else ""})
        out["headings"] = [r for a, b in heads for r in rects(a, b)]
        run = []                                           # text not in the review, line by line, as the text check counts it
        def flush():
            real = [x for x in run if x[0] not in T.TRIVIAL and not (len(x[0]) == 1 and x[0].isalpha())]
            if real:
                a, b = run[0][1], run[-1][2]
                out["missing"].append({"text": " ".join(t[a:b].split()), "rects": rects(a, b)})
        last_line = None
        for q, x in enumerate(seq):
            if cover[q] is None and (not run or x[3] == last_line):
                run.append(x)
            else:
                if run:
                    flush()
                run = [x] if cover[q] is None else []
            last_line = x[3]
        if run:
            flush()
        return out
    finally:
        pdf.close()


def _page_of(it):
    try:
        return int(it.get("page"))
    except (TypeError, ValueError):
        m = re.search(r"\(p\.(\d+)", it.get("loc", "") or "")
        return int(m.group(1)) if m else None


def render(path, page_no, scale=2.0):
    """The page as a PIL image (RGB) at scale pixels per point."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        return pdf[page_no - 1].render(scale=scale).to_pil().convert("RGB")
    finally:
        pdf.close()


COLORS = {"Keep": ((22, 163, 74), "Compliance requirement"), "Context": ((37, 99, 235), "Context"),
          "Customer": ((126, 34, 206), "Customer's"), "Drop": ((100, 116, 139), "Not used"), "": ((217, 119, 6), "Not decided yet")}
MISSING = ((220, 38, 38), "Not in the review")


def overlay(img, pmap, decisions, scale, selected="", show_missing=True):
    """The page picture with each sentence boxed in its decision's color (selected one heavier) and, when asked, the
    text not in the review boxed in red. decisions: {id: decision}."""
    from PIL import Image, ImageDraw
    base = img.convert("RGBA")
    over = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)

    def box(r, rgb, fill_a, width):
        l, t, rr, b = r
        d.rectangle([l * scale - 2, t * scale - 2, rr * scale + 2, b * scale + 2], fill=rgb + (fill_a,), outline=rgb + (255,), width=width)
    for it in pmap["items"]:
        rgb = COLORS.get(decisions.get(it["id"], ""), COLORS[""])[0]
        on = it["id"] == selected
        for r in it["rects"]:
            box(r, rgb, 90 if on else 38, 4 if on else 2)
    if show_missing:
        for m in pmap["missing"]:
            for r in m["rects"]:
                box(r, MISSING[0], 50, 3)
    return Image.alpha_composite(base, over).convert("RGB")


def hit(pmap, x, y, show_missing=True):
    """What is at a point (PDF points): ("item", id), ("missing", index) or None."""
    for it in pmap["items"]:
        for l, t, r, b in it["rects"]:
            if l - 2 <= x <= r + 2 and t - 2 <= y <= b + 2:
                return ("item", it["id"])
    if show_missing:
        for k, m in enumerate(pmap["missing"]):
            for l, t, r, b in m["rects"]:
                if l - 2 <= x <= r + 2 and t - 2 <= y <= b + 2:
                    return ("missing", k)
    return None
