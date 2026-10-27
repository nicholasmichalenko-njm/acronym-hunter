"""Text check (2.40.0): prove that every piece of text in a customer document reached the review.

Two independent reads are compared word for word:
1. raw_text(path): the file's text read straight from its parts, separately from the program's reader: Word body,
   tables, text boxes, headers, footers, footnotes and endnotes; PowerPoint slides (shapes, tables, SmartArt) and
   speaker notes; Excel cells (shared and inline strings); PDF text on every page.
2. What the review holds: the sentences in Assign (and the headings used as sections).
check() counts the words in each, lists the lines whose words are missing, and says which of them are headings.
Text inside pictures is read only by OCR (AI and ML) and is not part of the typed text check.
Rules only (No AI); nothing leaves the PC.
"""
import collections, os, re, zipfile

WORD = re.compile(r"[A-Za-z0-9]+")
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
S_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _parse(data):
    from lxml import etree
    return etree.fromstring(data, parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False))


def _in_fallback(el):
    return any(a.tag == MC_FALLBACK for a in el.iterancestors())


def _para_text(root, p_tag, t_tags):
    out = []
    for p in root.iter(p_tag):
        if _in_fallback(p):
            continue
        # a paragraph inside a text box inside a paragraph: count it once, as its own line
        txt = "".join(t.text or "" for t in p.iter(*t_tags) if not _in_fallback(t) and _owner_para(t, p_tag) is p)
        if txt.strip():
            out.append(txt)
    return out


def _owner_para(t, p_tag):
    for a in t.iterancestors():
        if a.tag == p_tag:
            return a
    return None


def raw_text(path):
    """[(where, line)] read straight from the file."""
    ext = os.path.splitext(path)[1].lower()
    out = []
    if ext in (".docx", ".docm"):
        with zipfile.ZipFile(path) as z:
            for n in sorted(z.namelist()):
                m = re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)
                if not m:
                    continue
                root = _parse(z.read(n))
                for line in _para_text(root, f"{{{W_NS}}}p", (f"{{{W_NS}}}t",)):
                    out.append((m.group(1), line))
    elif ext in (".pptx", ".pptm"):
        with zipfile.ZipFile(path) as z:
            def num(n):
                d = re.findall(r"\d+", n)
                return int(d[-1]) if d else 0
            for n in sorted(z.namelist(), key=lambda n: (n.split("/")[1] if "/" in n else n, num(n))):
                m = re.match(r"ppt/(slides/slide|notesSlides/notesSlide|diagrams/data)(\d+)\.xml$", n)
                if not m:
                    continue
                where = {"slides/slide": "slide", "notesSlides/notesSlide": "notes", "diagrams/data": "SmartArt"}[m.group(1)] + " " + m.group(2)
                root = _parse(z.read(n))
                for line in _para_text(root, f"{{{A_NS}}}p", (f"{{{A_NS}}}t",)):
                    if where.startswith("notes") and re.fullmatch(r"\d+", line.strip()):
                        continue                              # the slide number placeholder on the notes page
                    out.append((where, line))
    elif ext in (".xlsx", ".xlsm"):
        with zipfile.ZipFile(path) as z:
            if "xl/sharedStrings.xml" in z.namelist():
                root = _parse(z.read("xl/sharedStrings.xml"))
                for si in root.iter(f"{{{S_NS}}}si"):
                    txt = "".join(t.text or "" for t in si.iter(f"{{{S_NS}}}t") if t.getparent().tag != f"{{{S_NS}}}rPh")
                    if txt.strip():
                        out.append(("cells", txt))
            for n in sorted(z.namelist()):
                if re.match(r"xl/worksheets/sheet\d+\.xml$", n):
                    root = _parse(z.read(n))
                    for is_ in root.iter(f"{{{S_NS}}}is"):
                        txt = "".join(t.text or "" for t in is_.iter(f"{{{S_NS}}}t"))
                        if txt.strip():
                            out.append((os.path.basename(n), txt))
    elif ext == ".pdf":
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(path)
        try:
            for i in range(len(pdf)):
                page = pdf[i]
                tp = page.get_textpage()
                for line in (tp.get_text_range() or "").splitlines():
                    if line.strip():
                        out.append((f"p.{i + 1}", line))
                tp.close(); page.close()
        finally:
            pdf.close()
    return out


LIST_MARK = re.compile(r"^\s*(?:\(?(?:[a-z]|[ivx]{1,4}|\d{1,3})[.)]|[-\u2022\u25aa\u25cf\u2013*])\s+", re.I)
TRAIL = re.compile(r"[;,]\s*(?:and|or)\s*$", re.I)


def norm(line):
    """What the reader keeps of a line: list markers ((a), 1., bullets) and a trailing '; and' are not text."""
    return TRAIL.sub("", LIST_MARK.sub("", line or ""))


def line_words(line):
    return [w.lower() for w in WORD.findall(norm(line))]


def words(lines):
    return collections.Counter(w for _where, t in lines for w in line_words(t))


def _looks_heading(line):
    """The compliance reader's own heading test (numbered sections, SECTION L, all-caps titles)."""
    try:
        import compliance as C
        return bool(C._is_heading(line) or C._section_from_line(line, ("", "")))
    except Exception:
        return False


TRIVIAL = {"and", "or", "the", "of", "a", "an", "to", "in", "on", "for", "by", "with"}


def _seq(raw):
    """The file's words in reading order, with where each came from: [(word, line index, start, end)] and the lines."""
    seq, lines = [], []
    for where, line in raw:
        n = norm(line)
        li = len(lines)
        lines.append((where, n.strip(), n))
        for m in WORD.finditer(n):
            seq.append((m.group(0).lower(), li, m.start(), m.end()))
    return seq, lines


def check(path, items, headings=(), reader_chunks=None):
    """Compare one file's text with what the review holds for it, word by word in reading order.
    items: the matrix rows of this file (text and lead); headings: [{num, title}] used as sections.
    Each review sentence is matched to its place in the file; headings the reader uses as section titles are marked;
    what is left is missing. Returns {"file", "words", "in_review", "in_headings", "missing", "pct",
    "lines": [(where, text, kind)], "reader_missing"}: kind "missing" (text = the words not in the review, as written)
    or "heading" (a section title)."""
    raw = raw_text(path)
    seq, lines = _seq(raw)
    words_ = [w for w, *_ in seq]
    n = len(words_)
    cover = [0] * n                                   # 0 not in the review, 1 a sentence, 2 a section title
    at = collections.defaultdict(list)
    for i, w in enumerate(words_):
        at[w].append(i)

    def mark(ws, val):
        if not ws:
            return False
        best = None
        for p in at.get(ws[0], ()):
            if words_[p:p + len(ws)] == ws:
                if any(c == 0 for c in cover[p:p + len(ws)]):
                    best = p
                    break
                best = p if best is None else best
        if best is None:
            return False
        for k in range(best, best + len(ws)):
            if cover[k] == 0:
                cover[k] = val
        return True

    leads = set()
    for it in items:
        mark(line_words(it.get("text") or ""), 1)
        ld = (it.get("lead") or "").strip()
        if ld and ld not in leads:
            leads.add(ld)
            mark(line_words(ld), 1)
    for li, (where, text, _n) in enumerate(lines):     # headings the reader uses as section titles
        if text and _looks_heading(text):
            for k, (_w, l2, _s, _e) in enumerate(seq):
                if l2 == li and cover[k] == 0:
                    cover[k] = 2
    titles = set()
    for it in items:
        titles.add(((it.get("section") or "") + " " + (it.get("section_title") or "")).strip())
    for h in headings:
        titles.add(((h.get("num") or "") + " " + (h.get("title") or "")).strip())
    for t in titles:
        mark(line_words(t), 2)
    out_lines, missing = [], 0
    by_line = collections.defaultdict(list)
    for k, (w, li, s0, e0) in enumerate(seq):
        by_line[li].append((k, w, s0, e0))
    for li, (where, text, nline) in enumerate(lines):
        ks = by_line.get(li, [])
        gap = [(k, w, s0, e0) for k, w, s0, e0 in ks if cover[k] == 0]
        real = [g for g in gap if g[1] not in TRIVIAL and not (len(g[1]) == 1 and g[1].isalpha())]
        if real:
            missing += len(real)
            out_lines.append((where, nline[gap[0][2]:gap[-1][3]].strip(), "missing"))
        elif ks and all(cover[k] == 2 for k, *_ in ks):
            out_lines.append((where, text, "heading"))
    trivial_gaps = sum(1 for k, (w, *_x) in enumerate(seq) if cover[k] == 0) - missing
    counted = n - trivial_gaps
    res = {"file": os.path.basename(path), "words": counted, "in_review": sum(1 for c in cover if c == 1),
           "in_headings": sum(1 for c in cover if c == 2), "missing": missing, "lines": out_lines,
           "pct": 100.0 if not counted else round(100.0 * (counted - missing) / counted, 1)}
    if reader_chunks is not None:                     # the program's reader against the raw read
        rd = collections.Counter(w.lower() for _l, t in reader_chunks for w in WORD.findall(t))
        res["reader_missing"] = sum((words(raw) - rd).values())
    return res


def summary_text(r):
    if not r["words"]:
        return f"{r['file']}: no typed text (pictures or a scanned file: read with OCR)."
    if not r["missing"]:
        return (f"{r['file']}: all {r['words']} words are in the review" +
                (f" ({r['in_headings']} as section headings)." if r["in_headings"] else "."))
    return f"{r['file']}: {r['missing']} of {r['words']} words are not in the review yet ({r['pct']}% covered)."
