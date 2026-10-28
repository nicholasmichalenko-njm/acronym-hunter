"""Sentences cut from the page (2.57.0): one source of truth for the compliance review.

Every customer document is read in its page form: the PDF itself, or the PDF copy Microsoft Office makes of a Word,
Excel or PowerPoint file (office_pdf.py). From PDFium's text layer:
- lines in reading order, each with its box, font size and weight;
- headers and footers (running(): repeated near the top or bottom of pages, page numbers, short lines standing apart
  in the margins) are page furniture: never in the review, never boxed in Page view, never part of a selection;
- headings: a line in a larger font than the body, or bold and short, or numbered like a section, stays its own
  paragraph (the compliance rules then give it its number and title);
- paragraphs: lines that follow each other closely; a list item, a heading or a line ending in ':' starts or ends one;
  a paragraph that runs to the next page (no closing punctuation, the next page goes on in lower case) continues.
The paragraphs go through the compliance reader's own rules (compliance.extract), so sentences, list items, lead-ins,
types and sections are cut exactly as before; then each sentence is placed on its own characters in the same text,
in order, so every sentence knows its exact place on the page: it["places"] = [[page, first char, end char], ...].
Nothing is matched across two different readings of the file. Rules only (No AI); nothing leaves the PC.
"""
import re, statistics

WORD = re.compile(r"[A-Za-z0-9]+")
_NUM = re.compile(r"^\s*(?:(?:SECTION|Section|PART|Part|ARTICLE|Article)\s+[A-Z0-9]+|[A-Z]?\d+(?:\.\d+)*\.?|[A-Z]\.\d+(?:\.\d+)*|[A-Z]\.)\s+\S")
_REQ_WORD = re.compile(r"\b(?:shall|must|will|should|may)\b", re.I)      # a numbered line that says one is a sentence
_SECNO = re.compile(r"^\s*(?:[A-Z]\.)?\d+(?:\.\d+)*\.?(?=\s)|^\s*[A-Z]\.\d+(?:\.\d+)*\.?(?=\s)|^\s*\(?[A-Z]\.?\d*\)(?=\s)")
_TRAIL = re.compile(r"[;,]\s*(?:and|or)\s*$", re.I)       # "; and" at the end of a list item is not text
_LIST = re.compile(r"^\s*(?:\(?(?:[a-z]|[ivx]{1,4}|\d{1,2})[.)]|[-•▪●–*])\s+", re.I)


def _norm(s):
    return re.sub(r"\d+", "#", " ".join((s or "").split())).lower()


def read(path):
    """{"pages": [{"w", "h", "text", "lines": [{"a", "b", "text", "box": (l, t, r, b) from the top, "size", "bold"}]}]}"""
    import pypdfium2 as pdfium
    import pypdfium2.raw as R
    pdf = pdfium.PdfDocument(path)
    pages = []
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            w, h = page.get_size()
            tp = page.get_textpage()
            n = tp.count_chars()
            t = (tp.get_text_range(0, n) if n else "").replace("￾", "-")
            lines = []
            for m in re.finditer(r"[^\r\n]+", t):
                a, b = m.start(), m.end()
                if not t[a:b].strip():
                    continue
                boxes, sizes, bold = [], [], 0
                for k in range(a, b):
                    if t[k].isspace():
                        continue
                    try:
                        l, bo, r, tt = tp.get_charbox(k)
                    except Exception:
                        continue
                    if r > l:
                        boxes.append((l, h - tt, r, h - bo))
                    sizes.append(R.FPDFText_GetFontSize(tp.raw, k))
                    bold += R.FPDFText_GetFontWeight(tp.raw, k) >= 600
                if not boxes:
                    continue
                box = (min(x[0] for x in boxes), min(x[1] for x in boxes), max(x[2] for x in boxes), max(x[3] for x in boxes))
                lines.append({"a": a, "b": b, "text": t[a:b], "box": box,
                              "size": statistics.median(sizes) if sizes else 0, "bold": bold > len(sizes) / 2})
            pages.append({"w": w, "h": h, "text": t, "lines": lines})
            tp.close()
            page.close()
    finally:
        pdf.close()
    return {"pages": pages}


HEAD_BAND, FOOT_BAND = 0.09, 0.91                 # the page's top and bottom margins (a 1-inch margin on Letter)
_PAGE_NO = re.compile(r"^\s*(?:page\s+)?[-\u2013(]?\s*[0-9ivxlc]{1,4}\s*[-\u2013)]?(?:\s+of\s+\d+)?\s*$", re.I)


def running(doc):
    """{(page index, line index)} of headers and footers: page furniture, never text of the review and never part of
    a selection (user, 2026-10-28). A line is furniture when it is near the top or bottom of its page and
    - repeats near the top or bottom of two or more pages (digits ignored: "Page 3 of 12" counts), or
    - is a page number ("7", "Page 7", "- 7 -", "Page 7 of 12"), or
    - is short, sits inside the top or bottom margin and stands apart from the text (a clear gap to the body), and
      is not a sentence (it does not start in lower case, say shall, must, will, should or may, or end like one).
    Body text near the edge of a page with narrow margins stays: it has no gap to the lines next to it."""
    where, out = {}, set()
    for pi, p in enumerate(doc["pages"]):
        h = p["h"] or 792
        ls = p["lines"]
        for li, ln in enumerate(ls):
            top, bot = ln["box"][1], ln["box"][3]
            lh = max(6.0, bot - top)
            txt = ln["text"].strip()
            nw = len(txt.split())
            edge = top < 0.12 * h or bot > 0.9 * h
            if not edge or nw > 40:
                continue
            where.setdefault(_norm(txt), []).append((pi, li))      # repeated on other pages: a legend, a running title
            if _PAGE_NO.match(txt):
                out.add((pi, li))
                continue
            if nw > 12 or txt[:1].islower() or _REQ_WORD.search(txt) or (nw > 4 and re.search(r"[.?!]$", txt)):
                continue                                             # a sentence, not a header or footer
            others = [o["box"] for k, o in enumerate(ls) if k != li]
            if bot < HEAD_BAND * h + 4:
                below = [o[1] for o in others if o[1] > top + lh * 0.5]
                if not below or min(below) - bot >= 1.2 * lh:
                    out.add((pi, li))
            elif top > FOOT_BAND * h - 4:
                above = [o[3] for o in others if o[3] < bot - lh * 0.5]
                if not above or top - max(above) >= 1.2 * lh:
                    out.add((pi, li))
    for spots in where.values():
        if len({pi for pi, _li in spots}) >= 2:
            out |= set(spots)
    return out


def view_lines(doc, skip=None):
    """The document's text for the text view: [("p.N", line)] without headers and footers."""
    skip = skip if skip is not None else running(doc)
    return [(f"p.{pi + 1}", ln["text"]) for pi, p in enumerate(doc["pages"]) for li, ln in enumerate(p["lines"])
            if (pi, li) not in skip]


def furniture(doc, page_no, skip=None):
    """Boxes (PDF points from the top) of the headers and footers on one page, drawn grey in Page view."""
    skip = skip if skip is not None else running(doc)
    p = doc["pages"][page_no - 1]
    return [ln["box"] for li, ln in enumerate(p["lines"]) if (page_no - 1, li) in skip]


def _body_size(doc):
    sizes = [ln["size"] for p in doc["pages"] for ln in p["lines"] if ln["size"]]
    return statistics.median(sizes) if sizes else 11.0


def paragraphs(doc, skip=None):
    """[{"page", "lines": [(page, line index)], "kind": "heading"|"text"}] in reading order."""
    skip = skip if skip is not None else running(doc)
    body = _body_size(doc)
    paras, cur = [], None
    for pi, p in enumerate(doc["pages"]):
        prev = None
        for li, ln in enumerate(p["lines"]):
            if (pi, li) in skip:
                continue
            txt = ln["text"].strip()
            words = len(txt.split())
            heading = (ln["size"] >= body * 1.12 and words <= 16) or (ln["bold"] and words <= 12 and not txt.endswith(".")) \
                or (bool(_NUM.match(txt)) and words <= 10 and not re.search(r"[.;:]$", txt)
                    and not _REQ_WORD.search(txt) and not re.search(r"[.;:]\s+[A-Z]", txt[_SECNO.match(txt).end():] if _SECNO.match(txt) else txt))
            starts = heading or bool(_LIST.match(txt)) or cur is None or cur["kind"] == "heading"
            if not starts and prev is not None:
                gap = ln["box"][1] - prev["box"][3]
                lh = max(4.0, prev["box"][3] - prev["box"][1])
                ends = re.search(r"[.:;?!]\s*$", prev["text"]) is not None
                if gap > 0.9 * lh or (ends and gap > 0.45 * lh) or prev["text"].rstrip().endswith(":"):
                    starts = True
                elif gap < -0.3 * lh:
                    starts = True                     # side by side on one row: table cells
                elif len(prev["text"].split()) <= 6 and not ends and txt[:1].isupper() | txt[:1].isdigit():
                    starts = True                     # a short line with no closing mark: a table cell or a label
                elif abs(ln["box"][0] - prev["box"][0]) > 0.5 * p["w"]:
                    starts = True                     # a different column or a table cell far across
            if prev is None and cur is not None and not heading:  # first line of a page: does the last paragraph go on?
                last = doc["pages"][cur["lines"][-1][0]]["lines"][cur["lines"][-1][1]]["text"].rstrip()
                if cur["kind"] == "text" and last and not re.search(r"[.:;?!)]$", last) and txt[:1].islower():
                    starts = False
                else:
                    starts = True
            if starts:
                cur = {"page": pi + 1, "lines": [], "kind": "heading" if heading else "text"}
                paras.append(cur)
            cur["lines"].append((pi, li))
            prev = ln
    return paras


def stream(doc, paras, name):
    """The paragraphs as chunks for compliance.extract (one chunk per page, paragraphs on their own lines), and the
    word places of that text in order: [(word lower, page, char a, char b)]."""
    chunks, places = [], []
    run, run_page = [], None

    def flush():
        if run:
            chunks.append((f"{name} (p.{run_page})", "\n".join(run)))
    for para in paras:
        text = " ".join(doc["pages"][pi]["lines"][li]["text"].strip() for pi, li in para["lines"])
        # a heading stays its own line: the compliance rules give it its number and title (or keep it as a sentence),
        # exactly as they do for any reader
        for pi, li in para["lines"]:
            ln = doc["pages"][pi]["lines"][li]
            for m in WORD.finditer(ln["text"]):
                places.append((m.group(0).lower(), pi + 1, ln["a"] + m.start(), ln["a"] + m.end()))
        if run_page is not None and para["page"] != run_page:
            flush()
            run = []
        run_page = para["page"]
        run.append(text)
    flush()
    return chunks, places


def place(items, places):
    """Each sentence (in reading order) on its own words, in order: it["places"] = [[page, a, b], ...] (one per page it
    runs over); a list's lead-in is placed with the list's first item (it["lead_places"]). Returns the ids not placed."""
    words = [w for w, *_x in places]
    n = len(words)
    used = [False] * n
    cur = 0
    missed = []

    def find(ws, start):
        k = len(ws)
        if not k:
            return None
        for p in range(start, n - k + 1):
            if words[p] == ws[0] and words[p:p + k] == ws and not any(used[p:p + k]):
                return p
        for p in range(0, min(start, n - k + 1)):        # out of order (rare): anywhere still free
            if words[p] == ws[0] and words[p:p + k] == ws and not any(used[p:p + k]):
                return p
        return None

    def spans(p, k):
        out = []
        for q in range(p, p + k):
            _w, pg, a, b = places[q]
            if out and out[-1][0] == pg:
                out[-1][2] = b
            else:
                out.append([pg, a, b])
        return out
    def find_before(ws, lo, hi):
        """The last free copy of ws between lo and hi (a list's lead-in just before its first item)."""
        k = len(ws)
        for p in range(min(hi, n) - k, max(lo, 0) - 1, -1):
            if words[p:p + k] == ws and not any(used[p:p + k]):
                return p
        return None
    for it in items:
        ld = [w.lower() for w in WORD.findall(it.get("lead") or "")]
        ws = [w.lower() for w in WORD.findall(it.get("text") or "")]
        p = find(ws, cur)
        if p is None:
            it["places"] = []
            missed.append(it.get("id"))
            continue
        if ld and p >= cur:
            q = find_before(ld, max(cur, p - len(ld) - 12), p)
            if q is not None:
                for r in range(q, q + len(ld)):
                    used[r] = True
                it["lead_places"] = spans(q, len(ld))
        for q in range(p, p + len(ws)):
            used[q] = True
        it["places"] = spans(p, len(ws))
        cur = p + len(ws)
    for it in items:
        it["place"] = place_text(it.get("places"))
        it["lead_place"] = place_text(it.get("lead_places"))
        it.pop("places", None)
        it.pop("lead_places", None)
    return missed


def chunks_for(path, name):
    """(chunks, places) for the compliance reader from a PDF's page form, or None when a page has no typed text (a
    scanned page: the program's reader with its page OCR reads that file instead)."""
    doc = doc_of(path)
    if not doc["pages"] or any(not p["lines"] for p in doc["pages"]):
        return None
    return stream(doc, paragraphs(doc, doc.get("skip")), name)


def read_review(path, name, extract):
    """The review's sentences of one document read from its page form, each with its places. extract: the compliance
    reader (compliance.extract). Returns (items, headings, info) with info = {"pages", "running", "missed"}."""
    doc = read(path)
    skip = running(doc)
    paras = paragraphs(doc, skip)
    chunks, places = stream(doc, paras, name)
    heads = []
    items = extract([(name, chunks)], heads)
    missed = place(items, places)
    return items, heads, {"pages": len(doc["pages"]), "running": len(skip), "missed": missed}


def place_text(spans):
    """[[page, a, b], ...] -> "1:117-218;2:0-30" (kept in the matrix's hidden Place column)."""
    return ";".join(f"{pg}:{a}-{b}" for pg, a, b in (spans or []))


def parse_place(s):
    out = []
    for part in (s or "").split(";"):
        m = re.match(r"^\s*(\d+):(\d+)-(\d+)\s*$", part)
        if m:
            out.append([int(m.group(1)), int(m.group(2)), int(m.group(3))])
    return out


_DOCS = {}


def doc_of(pdf):
    """read(pdf), kept while the file is unchanged."""
    import os
    try:
        st = os.stat(pdf)
    except OSError:
        return {"pages": []}
    key = (os.path.abspath(pdf), st.st_size, int(st.st_mtime))
    if key not in _DOCS:
        if len(_DOCS) > 6:
            _DOCS.clear()
        d = read(pdf)
        d["skip"] = running(d)
        d["paras"] = paragraphs(d, d["skip"])
        _DOCS[key] = d
    return _DOCS[key]


def has_text(doc):
    return sum(len(p["lines"]) for p in doc["pages"]) >= 3


def place_map(pdf, page_no, items, headings=()):
    """The page map Page view draws, from the sentences' own places (nothing matched again): {"size", "items": [{"id",
    "rects", "words", "part"}], "headings": [rects], "missing": [{"text", "rects"}], "furniture": [boxes], "chars"}.
    Headers and footers get no box and are never "missing": they cannot be clicked, dragged over or added."""
    import pypdfium2 as pdfium
    doc = doc_of(pdf)
    skip = doc.get("skip", set())
    pd = pdfium.PdfDocument(pdf)
    try:
        page = pd[page_no - 1]
        w, h = page.get_size()
        tp = page.get_textpage()
        n = tp.count_chars()

        def rects(a, b):
            out = []
            for i in range(tp.count_rects(a, max(0, b - a))):
                l, bot, r, top = tp.get_rect(i)
                out.append((l, h - top, r, h - bot))
            return out
        t = (tp.get_text_range(0, n) if n else "").replace("\ufffe", "-")
        out = {"size": (w, h), "items": [], "headings": [], "missing": [], "chars": n,
               "furniture": furniture(doc, page_no, skip)}
        covered = []
        for it in items:
            spans = parse_place(it.get("place"))
            mine = [(a, b) for pg, a, b in spans if pg == page_no]
            covered += [(a, b) for pg, a, b in parse_place(it.get("lead_place")) if pg == page_no] + mine
            if not mine:
                continue
            rs, ws = [], []
            for a, b in mine:
                rs += rects(a, b)
                for m in WORD.finditer(t[a:b]):
                    r = rects(a + m.start(), a + m.end())
                    if r:
                        ws.append(r[0])
            out["items"].append({"id": it["id"], "rects": rs, "words": ws, "part": "" if spans[0][0] == page_no else "end"})
        titles = set()
        for x in headings or ():
            num, title = (x.get("num") or "").strip(), (x.get("title") or "").strip()
            titles |= {_norm(f"{num} {title}"), _norm(title)} - {""}
        heads = set()
        for para in doc.get("paras") or ():
            if para["kind"] == "heading":
                heads |= {li for pi, li in para["lines"] if pi == page_no - 1}
        pg = doc["pages"][page_no - 1] if page_no - 1 < len(doc["pages"]) else {"lines": []}
        for li, ln in enumerate(pg["lines"]):
            if (page_no - 1, li) in skip:
                continue
            if (li in heads or _norm(ln["text"]) in titles) and not any(x < ln["b"] and y > ln["a"] for x, y in covered):
                out["headings"] += rects(ln["a"], ln["b"])
                continue
            run = None
            lm = _LIST.match(ln["text"]) or _SECNO.match(ln["text"])      # list marks and paragraph numbers are not text
            tr = _TRAIL.search(ln["text"])
            lo, hi = (lm.end() if lm else 0), (tr.start() if tr else len(ln["text"]))
            for m in WORD.finditer(ln["text"]):
                a, b = ln["a"] + m.start(), ln["a"] + m.end()
                if m.start() < lo or m.start() >= hi or any(x <= a and b <= y for x, y in covered):
                    if run:
                        out["missing"].append({"text": t[run[0]:run[1]], "rects": rects(*run)})
                    run = None
                elif run:
                    run[1] = b
                else:
                    run = [a, b]
            if run:
                out["missing"].append({"text": t[run[0]:run[1]], "rects": rects(*run)})
        tp.close()
        page.close()
        return out
    finally:
        pd.close()


def merge_places(items):
    """The places of several sentences combined into one (in page and character order)."""
    spans = sorted((sp for it in items for sp in parse_place(it.get("place"))), key=lambda x: (x[0], x[1]))
    return place_text(spans)


def word_stream(pdf):
    """The document's words in reading order without headers and footers: [(word lower, page, a, b)] (cached)."""
    doc = doc_of(pdf)
    if "words" not in doc:
        doc["words"] = stream(doc, doc.get("paras") or paragraphs(doc, doc.get("skip")), "")[1]
    return doc["words"]


def place_all(pdf, items):
    """Where each review sentence of this file is on the PDF: {id: (place, lead place)}. A sentence's own place
    (read from the page, 2.57.0; several pieces for sentences combined from lines that are not next to each other) is
    kept while the words there are still its words; any other sentence (split, combined, added, fixed, read before
    2.57.0, or a Word, Excel or PowerPoint file shown through its PDF copy) is found by its exact words in reading
    order after the sentence before it, in up to four pieces. Not found: no place (not boxed)."""
    places = word_stream(pdf)
    words = [w for w, *_x in places]
    n = len(words)
    at = {(pg, a): i for i, (_w, pg, a, _b) in enumerate(places)}
    first = {}
    for i, w in enumerate(words):
        first.setdefault(w, []).append(i)
    used = [False] * n
    out = {}

    def idx_of(place, ws):
        """The word positions of a stored place, when they still hold exactly these words."""
        sp = parse_place(place)
        if not sp or not ws:
            return None
        idx = []
        for pg, a, b in sp:
            i = at.get((pg, a))
            if i is None:
                return None
            while i < n and places[i][1] == pg and places[i][3] <= b:
                idx.append(i)
                i += 1
        if [words[i] for i in idx] != ws or any(used[i] for i in idx):
            return None
        return idx

    def spans(idx):
        res = []
        for q in idx:
            _w, pg, a, b = places[q]
            if res and res[-1][0] == pg and res[-1][3] == q - 1:
                res[-1][2], res[-1][3] = b, q
            else:
                res.append([pg, a, b, q])
        return place_text([r[:3] for r in res])

    def find(ws, start, hi=None):
        k = len(ws)
        if not k:
            return None
        for p in first.get(ws[0], ()):
            if p >= start and (hi is None or p < hi) and words[p:p + k] == ws and not any(used[p:p + k]):
                return p
        if hi is None:
            for p in first.get(ws[0], ()):
                if p >= start:
                    break
                if words[p:p + k] == ws and not any(used[p:p + k]):
                    return p
        return None

    def pieces(ws, start):
        """ws found in up to four runs in order (a sentence combined from lines apart), else None."""
        idx, pos, i = [], start, 0
        while i < len(ws):
            best = None
            for p in first.get(ws[i], ()):
                if p < pos or used[p]:
                    continue
                k = 0
                while i + k < len(ws) and p + k < n and words[p + k] == ws[i + k] and not used[p + k]:
                    k += 1
                if best is None or k > best[1]:
                    best = (p, k)
                if k == len(ws) - i:
                    break
            if best is None or (best[1] < 3 and len(ws) - i > best[1]):
                return None
            idx += list(range(best[0], best[0] + best[1]))
            pos, i = best[0] + best[1], i + best[1]
            if len({0} | {j for j in range(1, len(idx)) if idx[j] != idx[j - 1] + 1}) > 4:
                return None
        return idx
    ws_of = {it["id"]: [w.lower() for w in WORD.findall(it.get("text") or "")] for it in items}
    kept = {}
    for it in items:                                     # first the sentences whose own place still holds
        idx = idx_of(it.get("place"), ws_of[it["id"]])
        if idx:
            kept[it["id"]] = idx
            for q in idx:
                used[q] = True
    cur = 0
    for it in items:
        ws = ws_of[it["id"]]
        idx = kept.get(it["id"])
        if idx is None:
            p = find(ws, cur)
            idx = list(range(p, p + len(ws))) if p is not None else (pieces(ws, cur) if len(ws) >= 6 else None)
            if not idx:
                continue
            for q in idx:
                used[q] = True
        lp = ""
        ld = [w.lower() for w in WORD.findall(it.get("lead") or "")]
        if ld:
            lidx = idx_of(it.get("lead_place"), ld)
            if lidx is None:
                k, p0 = len(ld), idx[0]
                q = next((q for q in range(p0 - k, max(cur, p0 - k - 12) - 1, -1)
                          if q >= 0 and words[q:q + k] == ld and not any(used[q:q + k])), None)
                lidx = list(range(q, q + k)) if q is not None else None
            if lidx:
                for q in lidx:
                    used[q] = True
                lp = spans(lidx)
        out[it["id"]] = (spans(idx), lp)
        cur = max(cur, idx[-1] + 1)
    return out
