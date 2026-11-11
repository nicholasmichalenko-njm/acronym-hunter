"""The word-for-word checks of a redline (4.8.0; claude/stationkeeper-redline-plan-4.6.md, step 2; decisions 3 and 7).

faithful(pdf, copy): the PDF's words (every line but the running headers, footers and page numbers) against the copy's
words. Each difference is listed as Added, Dropped or Changed, with its page and the heading above it. A line the person
set aside in Fix text is listed as "Set aside on purpose", not as dropped. Word cannot check its own conversion.

returned(copy, redline): the returned redline with every tracked change rejected, against the clean copy's words. Any
difference is an edit made with Track Changes off, which Word cannot see; each is listed with the heading above it.

Words are compared as written (case and punctuation kept; spaces and line breaks are not words). Rules only (No AI);
nothing leaves the PC."""
import difflib, re

import pagesent as PS
import redlinecopy as RC

_W = re.compile(r"\S+")


def words(text):
    return _W.findall(text or "")


def _diff(a, b, where_a, where_b):
    """[{"kind": "Added"|"Dropped"|"Changed", "was", "now", "page", "heading"}] from two word lists. where_x(i) -> (page,
    heading) of word i."""
    out = []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        kind = {"insert": "Added", "delete": "Dropped", "replace": "Changed"}[tag]
        page, head = where_a(i1) if i1 < len(a) else where_b(j1)
        out.append({"kind": kind, "was": " ".join(a[i1:i2]), "now": " ".join(b[j1:j2]), "page": page, "heading": head})
    return out


def _index(paras):
    """Words of a paragraph list, with each word's (page, heading above)."""
    ws, where, head = [], [], ""
    for p in paras:
        if p.get("kind") == "heading":
            head = p["text"]
        for w in words(p["text"]):
            ws.append(w)
            where.append((p.get("page", 0), head))
    return ws, where


def pdf_words(pdf, name=None):
    """The PDF's words in reading order (running headers, footers and page numbers left out), with (page, heading), and
    the lines set aside on purpose."""
    name = name or pdf.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    doc = PS.doc_of(pdf)
    extra, force = PS.decided(pdf, name)
    auto = set(doc.get("skip") or ())
    skip = auto - set(force)                               # the set-asides stay in: they are listed apart below
    paras = PS.paragraphs(doc, skip, force)
    plist = []
    aside = set(extra)
    for p in paras:
        kept = [(pi, li) for pi, li in p["lines"] if (pi, li) not in aside]
        if not kept:
            continue
        plist.append({"kind": p["kind"], "page": p["page"],
                      "text": RC.join_lines([doc["pages"][pi]["lines"][li]["text"] for pi, li in kept])})
    gone = [(pi + 1, doc["pages"][pi]["lines"][li]["text"].strip()) for pi, li in sorted(aside)
            if pi < len(doc["pages"]) and li < len(doc["pages"][pi]["lines"])]
    return plist, gone


def docx_paragraphs(path, reject=False):
    """[{"kind", "text", "level"}] of a Word file: its heading styles kept; reject=True reads it with every tracked
    change rejected (insertions left out, deletions kept)."""
    import zipfile
    from lxml import etree
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    out = []
    for p in root.iter(W + "p"):
        sty = p.find(f"{W}pPr/{W}pStyle")
        sid = sty.get(W + "val") if sty is not None else ""
        parts = []
        for x in p.iter(W + "t", W + "delText", W + "tab"):
            anc = {a.tag for a in x.iterancestors()}
            if x.tag == W + "delText" and not reject:
                continue
            if reject and W + "ins" in anc:
                continue
            if W + "moveFrom" in anc and not reject:
                continue
            if reject and W + "moveTo" in anc:
                continue
            parts.append("\t" if x.tag == W + "tab" else (x.text or ""))
        text = "".join(parts)
        m = re.match(r"(?i)heading\s*(\d)", sid or "")
        out.append({"kind": "heading" if m else "text", "level": int(m.group(1)) if m else 0, "text": text, "style": sid})
    return out


def faithful(pdf, copy, name=None):
    """{"differences": [...], "set_aside": [(page, text)], "tables": n, "words": (pdf, copy)}."""
    src, gone = pdf_words(pdf, name)
    a, wa = _index(src)
    cp = [p for p in docx_paragraphs(copy) if p["text"].strip()]
    b, wb = _index(cp)
    diffs = _diff(a, b, lambda i: wa[i] if i < len(wa) else (0, ""), lambda j: wb[j] if j < len(wb) else (0, ""))
    tables = sum(1 for p in src if re.search(r"\S\s{3,}\S", p["text"]) or "\t" in p["text"])
    return {"differences": diffs, "set_aside": gone, "tables": tables, "words": (len(a), len(b))}


def returned(copy, redline):
    """{"differences": edits made with Track Changes off, "words": (copy, redline)}. The clean copy's words come from its
    sidecar when it is there (so the copy may have been edited since), else from the copy itself."""
    side = RC.sidecar(copy)
    clean = side["paragraphs"] if side else [p for p in docx_paragraphs(copy) if p["text"].strip()]
    a, wa = _index(clean)
    back = [p for p in docx_paragraphs(redline, reject=True) if p["text"].strip()]
    b, wb = _index(back)
    diffs = _diff(a, b, lambda i: wa[i] if i < len(wa) else (0, ""), lambda j: wb[j] if j < len(wb) else (0, ""))
    return {"differences": diffs, "words": (len(a), len(b))}
