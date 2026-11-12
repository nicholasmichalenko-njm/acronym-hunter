"""The comments on a PDF, read and pinned to the words they mark (4.16.0; claude/stationkeeper-pdf-comments-plan-4.16.html).

read(pdf): every comment Acrobat (or another PDF reader) left on the pages, through PDFium: its kind, its boxes
(QuadPoints), its note, the reviewer, the date, the comment it answers (IRT), its group (Acrobat's Replace text joins a
cross-out and an insert with RT /Group), a review status (State), a callout's tip.

pin(pdf, comments, stream): where each comment sits in the copy's words. stream is the copy's words in order (the PDF's
paragraphs as redlinecheck.pdf_words or redlineslides.plan read them), each word with its page. A markup's letters are
the letters whose middle lies in one of its boxes; they are found among the stream's words by their letters and the
letters around them (the same words twice on a page are told apart by their neighbours). An insert's caret marks the
gap between two letters. A note, text box, shape or stamp has no words: the nearest words are used ("position"). A mark
on a line the copy leaves out (a running header, a line set aside) goes to the page's first words ("left out").
Each pin is (first word, letter in it, last word, letter after the end) in the stream. Rules only (No AI); nothing
leaves the PC."""
import ctypes, datetime, math, re

KINDS = {"HIGHLIGHT": "highlight", "UNDERLINE": "underline", "SQUIGGLY": "squiggly", "STRIKEOUT": "strike",
         "CARET": "caret", "TEXT": "note", "FREETEXT": "textbox", "SQUARE": "shape", "CIRCLE": "shape",
         "POLYGON": "shape", "POLYLINE": "shape", "INK": "shape", "LINE": "shape", "STAMP": "stamp",
         "FILEATTACHMENT": "attachment", "SOUND": "attachment"}
MARKUPS = ("highlight", "underline", "squiggly", "strike")
CONTEXT = 60                                     # letters each side that tell two of the same words apart


def _norm(s):
    return "".join(ch for ch in s.casefold() if ch.isalnum())


def _wstr(fn, *args):
    n = fn(*args, None, 0)
    if not n or n <= 2:
        return ""
    import pypdfium2.raw as R
    buf = ctypes.create_string_buffer(n)
    fn(*args, ctypes.cast(buf, ctypes.POINTER(R.FPDF_WCHAR)), n)
    return buf.raw[:n - 2].decode("utf-16-le", "replace")


def pdf_date(s):
    """D:20261103091500-07'00' -> 2026-11-03T09:15:00Z: the reviewer's own clock, the way Word writes its dates (Word
    shows the time as written); "" when it cannot be read."""
    m = re.match(r"D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", s or "")
    if not m:
        return ""
    y, mo, d, h, mi, se = (int(m.group(i) or dflt) for i, dflt in ((1, 0), (2, 1), (3, 1), (4, 0), (5, 0), (6, 0)))
    try:
        return datetime.datetime(y, mo, d, h, mi, se).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ""


def _tip(ap, rect):
    """A callout's tip from its appearance: the end of its line farthest from its box (top-down, None if none)."""
    nums = r"(-?\d+(?:\.\d+)?)"
    boxes = [tuple(map(float, m)) for m in re.findall(rf"{nums}\s+{nums}\s+{nums}\s+{nums}\s+re", ap or "")]
    pts = [tuple(map(float, m)) for m in re.findall(rf"{nums}\s+{nums}\s+[ml]\b", ap or "")]
    if not boxes or not pts:
        return None
    bx, by, bw, bh = max(boxes, key=lambda b: abs(b[2] * b[3]))
    cx, cy = bx + bw / 2, by + bh / 2
    return max(pts, key=lambda p: math.hypot(p[0] - cx, p[1] - cy))


def read(pdf):
    """[{"page" (from 1), "n" (its number on the page), "kind", "author", "date", "note", "subject", "quads": [(l, t, r,
    b)], "rect": (l, t, r, b), "reply_to": (page, n) or None, "group": bool, "state", "hidden", "tip": (x, y) or None,
    "name"}], y from the top of the page. Popups, links and form fields are not comments."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as R
    sub_of = {getattr(R, "FPDF_ANNOT_" + k): v for k, v in KINDS.items() if hasattr(R, "FPDF_ANNOT_" + k)}
    out = []
    doc = pdfium.PdfDocument(pdf)
    try:
        for pi in range(len(doc)):
            page = doc[pi]
            h = page.get_size()[1]
            n = R.FPDFPage_GetAnnotCount(page.raw)
            for i in range(n):
                a = R.FPDFPage_GetAnnot(page.raw, i)
                if not a:
                    continue
                try:
                    kind = sub_of.get(R.FPDFAnnot_GetSubtype(a))
                    if not kind:
                        continue
                    sv = lambda key: _wstr(R.FPDFAnnot_GetStringValue, a, key.encode())      # noqa: E731
                    r = R.FS_RECTF()
                    R.FPDFAnnot_GetRect(a, ctypes.byref(r))
                    rect = (min(r.left, r.right), h - max(r.top, r.bottom), max(r.left, r.right), h - min(r.top, r.bottom))
                    quads = []
                    for q in range(R.FPDFAnnot_CountAttachmentPoints(a)):
                        qp = R.FS_QUADPOINTSF()
                        if R.FPDFAnnot_GetAttachmentPoints(a, q, ctypes.byref(qp)):
                            xs, ys = (qp.x1, qp.x2, qp.x3, qp.x4), (qp.y1, qp.y2, qp.y3, qp.y4)
                            quads.append((min(xs), h - max(ys), max(xs), h - min(ys)))
                    reply_to = None
                    lk = R.FPDFAnnot_GetLinkedAnnot(a, b"IRT")
                    if lk:
                        j = R.FPDFPage_GetAnnotIndex(page.raw, lk)
                        R.FPDFPage_CloseAnnot(lk)
                        if j >= 0:
                            reply_to = (pi + 1, j)
                    tip = None
                    if kind in ("textbox", "shape") and sv("IT") in ("FreeTextCallout", "LineArrow"):
                        t = _tip(_wstr(R.FPDFAnnot_GetAP, a, R.FPDF_ANNOT_APPEARANCEMODE_NORMAL), rect)
                        tip = (t[0], h - t[1]) if t else None
                    out.append({"page": pi + 1, "n": i, "kind": kind, "author": sv("T"), "date": pdf_date(sv("M") or sv("CreationDate")),
                                "note": sv("Contents"), "subject": sv("Subj"), "quads": quads, "rect": rect,
                                "reply_to": reply_to, "group": sv("RT") == "Group", "state": sv("State"),
                                "hidden": bool(R.FPDFAnnot_GetFlags(a) & 2), "tip": tip, "name": sv("Name"), "sy": sv("Sy")})
                finally:
                    R.FPDFPage_CloseAnnot(a)
    finally:
        doc.close()
    return out


def letters(pdf, pi):
    """A page's letters: (text, [(l, t, r, b)] y from the top) through PDFium."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        page = doc[pi]
        h = page.get_size()[1]
        tp = page.get_textpage()
        try:
            n = tp.count_chars()
            text = tp.get_text_range(0, n) if n else ""
            boxes = []
            for k in range(min(n, len(text))):
                try:
                    l, b, r, t = tp.get_charbox(k)
                except Exception:  # noqa: BLE001  a letter with no box is never picked
                    l = b = r = t = -1
                boxes.append((l, h - t, r, h - b))
            return text, boxes
        finally:
            tp.close()
    finally:
        doc.close()


def picked(text, boxes, quads, pad=0.6):
    """The letters a markup covers: each letter whose middle lies in one of its boxes. Spaces and breaks are not
    letters."""
    out = []
    for k, (l, t, r, b) in enumerate(boxes):
        if r <= l or k >= len(text) or text[k].isspace():
            continue
        cx, cy = (l + r) / 2, (t + b) / 2
        if any(q[0] - pad <= cx <= q[2] + pad and q[1] - pad <= cy <= q[3] + pad for q in quads):
            out.append(k)
    return out


def inside(text, boxes, rect, share=0.5):
    """Letters a shape covers (at least half of each letter's box inside it)."""
    out = []
    for k, (l, t, r, b) in enumerate(boxes):
        if r <= l or k >= len(text) or text[k].isspace():
            continue
        w = max(0.0, min(r, rect[2]) - max(l, rect[0])) * max(0.0, min(b, rect[3]) - max(t, rect[1]))
        if w >= share * (r - l) * (b - t):
            out.append(k)
    return _whole_words(text, out)


def _whole_words(text, ks):
    if not ks:
        return ks
    s = set(ks)
    for k in list(ks):
        j = k - 1
        while j >= 0 and not text[j].isspace() and j not in s:
            s.add(j); j -= 1
        j = k + 1
        while j < len(text) and not text[j].isspace() and j not in s:
            s.add(j); j += 1
    return sorted(s)


def nearest(text, boxes, x, y):
    """The word nearest a point: its letters."""
    best, bd = None, None
    for k, (l, t, r, b) in enumerate(boxes):
        if r <= l or k >= len(text) or text[k].isspace():
            continue
        dx = 0 if l <= x <= r else min(abs(x - l), abs(x - r))
        dy = 0 if t <= y <= b else min(abs(y - t), abs(y - b))
        d = math.hypot(dx, dy * 1.5)
        if bd is None or d < bd:
            best, bd = k, d
    return _whole_words(text, [best]) if best is not None else []


def gap(text, boxes, rect):
    """The letter an insert's caret goes before: (k, "before") or (k, "after") for the last letter of a line."""
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    cand = []
    for k, (l, t, r, b) in enumerate(boxes):
        if r <= l or k >= len(text) or text[k].isspace():
            continue
        dy = 0 if t - 1 <= cy <= b + 4 else min(abs(cy - (t - 1)), abs(cy - (b + 4)))
        cand.append((dy, k))
    if not cand:
        return None
    m = min(c[0] for c in cand)
    line = sorted((k for d, k in cand if d <= m + 1.0), key=lambda k: boxes[k][0])
    best = None
    for i, k in enumerate(line):
        l, r = boxes[k][0], boxes[k][2]
        for edge, where in ((l, "before"), (r, "after")):
            d = abs(cx - edge)
            if best is None or d < best[0] - 0.01:
                best = (d, k, where)
    _d, k, where = best
    if where == "after":                                 # after a letter = before the next one in the same word
        if k + 1 < len(text) and not text[k + 1].isspace() and boxes[k + 1][2] > boxes[k + 1][0]:
            return k + 1, "before"
    return k, where


class Stream:
    """The copy's words in order, with their pages, and their letters for finding a piece of text."""
    def __init__(self, paras):
        self.words, self.pages, self.para = [], [], []
        for pi, p in enumerate(paras):
            for w in re.findall(r"\S+", p.get("text") or ""):
                self.words.append(w); self.pages.append(p.get("page", 0)); self.para.append(pi)
        self.norm, self.at = [], []
        for wi, w in enumerate(self.words):
            for ci, ch in enumerate(w):
                for c in ch.casefold():
                    if c.isalnum():
                        self.norm.append(c); self.at.append((wi, ci))
        self.norm = "".join(self.norm)

    def first_of_page(self, page):
        for wi, pg in enumerate(self.pages):
            if pg >= page:
                return wi
        return max(0, len(self.words) - 1)

    def find(self, quote, before, after, page):
        """(start, end) letters in self.norm for quote, the one whose neighbours match best (and on its page)."""
        if not quote:
            return None
        best = None
        i = self.norm.find(quote)
        while i >= 0:
            j = i + len(quote)
            b = self.norm[max(0, i - len(before)):i]
            a = self.norm[j:j + len(after)]
            sb = 0
            while sb < min(len(b), len(before)) and b[-1 - sb] == before[-1 - sb]:
                sb += 1
            sa = 0
            while sa < min(len(a), len(after)) and a[sa] == after[sa]:
                sa += 1
            wp = self.pages[self.at[i][0]]
            score = sb + sa + (1000 if wp in (page, page - 1) else 0) + (1 if wp == page else 0)
            if best is None or score > best[0]:
                best = (score, i, j)
            i = self.norm.find(quote, i + 1)
        return (best[1], best[2]) if best else None


def _context(text, a, b):
    before = _norm(text[max(0, a - 3 * CONTEXT):a])[-CONTEXT:]
    after = _norm(text[b:b + 3 * CONTEXT])[:CONTEXT]
    return before, after


def locate(stream, text, ks, page):
    """Letters ks of a page's text to a pin in the stream: (w0, c0, w1, c1) with c1 one past the last letter, or None."""
    if not ks:
        return None
    a, b = ks[0], ks[-1] + 1
    sel = "".join(text[k] for k in ks)
    quote = _norm(sel)
    if not quote:
        return None
    before, after = _context(text, a, b)
    hit = stream.find(quote, before, after, page)
    if hit is None:
        return None
    (w0, c0), (w1, c1) = stream.at[hit[0]], stream.at[hit[1] - 1]
    c1 += 1
    lead = len(sel) - len(sel.lstrip("".join(ch for ch in sel if not ch.isalnum())))
    trail = len(sel) - len(sel.rstrip("".join(ch for ch in sel if not ch.isalnum())))
    w = stream.words[w0]
    while lead and c0 > 0 and not w[c0 - 1].isalnum():
        c0 -= 1; lead -= 1
    w = stream.words[w1]
    while trail and c1 < len(w) and not w[c1].isalnum():
        c1 += 1; trail -= 1
    return (w0, c0, w1, c1)


def _left_out(doc, pi, ks):
    """True when the letters sit on lines the copy leaves out (running headers, footers, lines set aside)."""
    if doc is None or not ks:
        return False
    skip = doc.get("_out") or set()
    lines = doc["pages"][pi]["lines"] if pi < len(doc["pages"]) else []
    for li, ln in enumerate(lines):
        if (pi, li) in skip and ln.get("a", -1) <= ks[0] < ln.get("b", -1):
            return True
    return False


def pin(pdf, comments, paras, doc=None):
    """Each comment with "pin" (w0, c0, w1, c1) in the stream of paras, "point" ("before"/"after" a letter for an
    insert), "how" ("words", "position", "left out", "not placed") and "marked" (the PDF letters it marks)."""
    stream = Stream(paras)
    pages = {}
    for c in comments:
        pi = c["page"] - 1
        if pi not in pages:
            pages[pi] = letters(pdf, pi)
        text, boxes = pages[pi]
        c["pin"], c["how"], c["marked"] = None, "not placed", ""
        if c["kind"] in MARKUPS:
            ks, how = picked(text, boxes, c["quads"] or [c["rect"]]), "words"
        elif c["kind"] == "caret":
            g = gap(text, boxes, c["rect"])
            c["point"] = g[1] if g else "before"
            if g:                                       # its word is found; the caret's letter is counted inside it
                ks = _whole_words(text, [g[0]])
                c["_at"] = ks.index(g[0])
            else:
                ks = []
            how = "words"
        elif c["kind"] == "shape" and c.get("tip") is None:
            ks, how = inside(text, boxes, c["rect"]), "position"
            if not ks:
                ks = nearest(text, boxes, *_mid(c["rect"]))
        elif c.get("tip"):
            ks, how = nearest(text, boxes, *c["tip"]), "position"
        else:
            r = c["rect"]
            ks, how = nearest(text, boxes, r[0], (r[1] + r[3]) / 2) if c["kind"] == "note" else nearest(text, boxes, *_mid(r)), "position"
        if not ks:
            ks, how = nearest(text, boxes, *_mid(c["rect"])), "position"
        c["marked"] = _spaced(text, ks)
        if _left_out(doc, pi, ks):
            w = stream.first_of_page(c["page"])
            if stream.words:
                c["pin"], c["how"] = (w, 0, w, len(stream.words[w])), "left out"
            continue
        p = locate(stream, text, ks, c["page"])
        if p is None:
            w = stream.first_of_page(c["page"])
            if stream.words:
                c["pin"], c["how"] = (w, 0, w, len(stream.words[w])), "position"
            continue
        if "_at" in c and p[0] == p[2]:
            w = stream.words[p[0]]
            ci = min(len(w) - 1, p[1] + c.pop("_at"))
            p = (p[0], ci, p[0], ci + 1)
        c["pin"], c["how"] = p, how
    return comments, stream


def _mid(r):
    return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def _spaced(text, ks):
    """The letters as the reader sees them: one space where the page has space or a break between them."""
    out, last = [], None
    for k in ks:
        if last is not None and k != last + 1 and any(ch.isspace() for ch in text[last + 1:k]):
            out.append(" ")
        elif last is not None and k != last + 1:
            out.append(" ")
        out.append(text[k])
        last = k
    return "".join(out)
