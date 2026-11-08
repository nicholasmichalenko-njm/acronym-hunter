"""Verify's blocks (3.84.0): a customer page cut into blocks, each with a suggested role and why.

The blocks come from the page form every customer document is read in (pagesent): its paragraphs, its headers and
footers (each its own block), and its pictures (PDFium's image objects). Each block suggests a role:
    a header or footer -> Running; "Figure 3", "Exhibit 2" -> Figure caption; "Table 4" -> Table caption;
    a heading -> H1 to H6 by its numbering ("3.1.2" is H3; "Section L" is H1), else by its font size among the headings;
    a list item -> Bullet; small type at the foot of the page -> Footnote; a picture -> Figure; the rest -> Text.
A suggestion the rules are not sure of (a heading level from its size alone, a footnote) is a flag to look at.
Every word of the page's text is counted into some block (the ledger), so a second reading of the page checks that
nothing was dropped.

blocks(pdf) -> {"pages": [{"n", "w", "h", "scanned", "blocks": [block]}]}
    block: {"key", "page", "lines", "box": (l, t, r, b) PDF points from the top, "text", "suggest", "why", "sure", "size"}
ledger(pdf, n) -> {"placed", "total", "missing": [words]}
nearest_object(blocks, caption, kind, roles) -> key of the figure or table a caption most likely names
Rules only; nothing leaves the PC."""
import os, re
from collections import Counter

import pagesent as PS

_FIG = re.compile(r"^\s*(?:Figure|Fig\.|Exhibit|Illustration|Chart|Diagram)\s*[A-Z]?\d[\w.\-]*\s*[:.\-–—]?(?:\s|$)", re.I)
_TAB = re.compile(r"^\s*Table\s*[A-Z]?\d[\w.\-]*\s*[:.\-–—]?(?:\s|$)", re.I)
_NUMS = re.compile(r"^\s*(?:(?:SECTION|Section|PART|Part|ARTICLE|Article|VOLUME|Volume)\s+[A-Z0-9IVX]+\b"
                   r"|(?P<n>(?:[A-Z]\.)?\d+(?:\.\d+)*)\.?(?=\s)|(?P<l>[A-Z])\.(?=\s))")
_CACHE = {}


def _level_of(text):
    """(level, sure) from a heading's numbering, or (0, False) with none."""
    m = _NUMS.match(text or "")
    if not m:
        return 0, False
    if m.group("n"):
        return min(6, len(m.group("n").split("."))), True
    if m.group("l"):
        return 1, False                                  # "A." could be any level
    return 1, True                                       # Section, Part, Article, Volume


def _images(pdf):
    """{page index: [(l, t, r, b)]} for the pictures on each page (not a scan that fills the page)."""
    out = {}
    try:
        import pypdfium2 as pdfium
        import pypdfium2.raw as R
        doc = pdfium.PdfDocument(pdf)
    except Exception:  # noqa: BLE001
        return out
    try:
        for i in range(len(doc)):
            page = doc[i]
            w, h = page.get_size()
            boxes = []
            for obj in page.get_objects(filter=(R.FPDF_PAGEOBJ_IMAGE,), max_depth=2):
                try:
                    l, b, r, t = obj.get_pos()
                except Exception:  # noqa: BLE001
                    continue
                bw, bh = r - l, t - b
                if bw < 24 or bh < 24 or bw * bh > 0.8 * w * h:
                    continue
                boxes.append((max(0, l), max(0, h - t), min(w, r), min(h, h - b)))
            out[i] = boxes
            page.close()
    finally:
        doc.close()
    return out


def _box(doc, lines):
    bs = [doc["pages"][pi]["lines"][li]["box"] for pi, li in lines]
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def blocks(pdf):
    """The document's pages and their blocks, in reading order (kept while the file is unchanged)."""
    doc = PS.doc_of(pdf)
    try:
        st = os.stat(pdf)
        key = (os.path.abspath(pdf), st.st_size, int(st.st_mtime))
    except OSError:
        key = (pdf, 0, 0)
    if key in _CACHE:
        return _CACHE[key]
    body = PS._body_size(doc)
    skip, paras = doc.get("skip") or set(), doc.get("paras") or []
    pages = [{"n": i + 1, "w": p["w"], "h": p["h"], "scanned": not p["lines"], "blocks": []} for i, p in enumerate(doc["pages"])]
    heads = []
    for para in paras:
        pi = para["lines"][0][0]
        lines = [li for p_, li in para["lines"] if p_ == pi]          # a block stays on its page; the rest is its own
        rest = [li for p_, li in para["lines"] if p_ != pi]
        for page_i, lis in ((pi, lines), (pi + 1, rest)):
            if not lis:
                continue
            ls = [(page_i, li) for li in lis]
            text = " ".join(doc["pages"][page_i]["lines"][li]["text"].strip() for li in lis)
            size = max(doc["pages"][page_i]["lines"][li]["size"] or 0 for li in lis)
            b = {"key": f"{page_i + 1}:{lis[0]}", "page": page_i + 1, "lines": lis, "box": _box(doc, ls), "text": text,
                 "size": size, "kind": para["kind"] if page_i == pi else "text"}
            pages[page_i]["blocks"].append(b)
            if b["kind"] == "heading":
                heads.append(b)
    for pi, li in sorted(skip):
        ln = doc["pages"][pi]["lines"][li]
        pages[pi]["blocks"].append({"key": f"{pi + 1}:{li}", "page": pi + 1, "lines": [li], "box": ln["box"],
                                    "text": ln["text"].strip(), "size": ln["size"], "kind": "running"})
    for pi, boxes in _images(pdf).items():
        for k, bx in enumerate(boxes):
            pages[pi]["blocks"].append({"key": f"{pi + 1}:img{k}", "page": pi + 1, "lines": [], "box": bx, "text": "",
                                        "size": 0, "kind": "picture"})
    sizes = sorted({round(b["size"] or 0, 1) for b in heads}, reverse=True)
    for p in pages:
        h = p["h"] or 792
        for b in p["blocks"]:
            b.update(_suggest(b, body, sizes, h))
            b.pop("kind", None)
        p["blocks"].sort(key=lambda b: (round(b["box"][1] / 4), b["box"][0]))
    out = {"pages": pages}
    if len(_CACHE) > 6:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def _suggest(b, body, sizes, h):
    t, kind = b["text"], b["kind"]
    if kind == "running":
        return {"suggest": "running", "why": "Repeats at the top or bottom of the pages, or is a page number", "sure": True}
    if kind == "picture":
        return {"suggest": "figure", "why": "A picture on the page", "sure": True}
    if _TAB.match(t) and len(t.split()) <= 30:
        return {"suggest": "tabcap", "why": "Starts with Table and a number", "sure": True}
    if _FIG.match(t) and len(t.split()) <= 30:
        return {"suggest": "figcap", "why": "Starts with Figure (or Exhibit) and a number", "sure": True}
    if kind == "heading":
        lvl, sure = _level_of(t)
        if lvl:
            return {"suggest": f"h{lvl}", "why": f"Numbered {t.split()[0]}: level {lvl}", "sure": sure}
        rank = sizes.index(round(b["size"] or 0, 1)) + 1 if round(b["size"] or 0, 1) in sizes else len(sizes)
        lvl = max(1, min(6, rank))
        return {"suggest": f"h{lvl}", "why": f"No number; its type is the {_nth(rank)} largest of the headings", "sure": False}
    if PS._LIST.match(t):
        return {"suggest": "bullet", "why": "Starts like a list item", "sure": True}
    if b["size"] and b["size"] <= body * 0.85 and b["box"][1] > 0.72 * h:
        return {"suggest": "footnote", "why": "Small type at the foot of the page", "sure": False}
    return {"suggest": "text", "why": "Running text", "sure": True}


def _nth(n):
    return {1: "first", 2: "second", 3: "third"}.get(n, f"{n}th")


def ledger(pdf, n):
    """Every word of the page's own text against the words in its blocks: what a second reading found unplaced."""
    doc = PS.doc_of(pdf)
    if not (1 <= n <= len(doc["pages"])):
        return {"placed": 0, "total": 0, "missing": []}
    p = doc["pages"][n - 1]
    whole = Counter(w.lower() for w in PS.WORD.findall(p["text"]))
    got = Counter()
    for b in blocks(pdf)["pages"][n - 1]["blocks"]:
        got.update(w.lower() for w in PS.WORD.findall(b["text"]))
    missing = whole - got
    total = sum(whole.values())
    return {"placed": total - sum(missing.values()), "total": total, "missing": sorted(missing.elements())[:40]}


def nearest_object(page_blocks, cap, kind, roles, next_blocks=()):
    """The figure or table (kind) a caption names: the closest one above or below it on its page, else the first on
    the next page. roles: {key: role id} as decided (the suggestion where none). Returns a block key or None."""
    obj = {"figure": "figure", "table": "table"}[kind]

    def objs(bl):
        return [b for b in bl if roles.get(b["key"], b["suggest"]) == obj]
    here = objs(page_blocks)
    if here:
        cy = (cap["box"][1] + cap["box"][3]) / 2
        return min(here, key=lambda b: min(abs(b["box"][1] - cy), abs(b["box"][3] - cy)))["key"]
    there = objs(next_blocks)
    return there[0]["key"] if there else None
