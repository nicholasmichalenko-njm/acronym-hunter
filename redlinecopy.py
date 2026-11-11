"""The clean Word copy of a customer PDF for redlining (4.8.0; claude/stationkeeper-redline-plan-4.6.md, step 1;
claude/stationkeeper-redline-decisions-2026-11-10.md, decision 2).

The copy is made from the text the shred already reads (pagesent), with Fix text's decisions applied (lines set aside,
headings forced on or off, headings split off their text):
- a heading becomes Heading N, N the depth of its number (L.3.5.2 is 4; a heading without a number is 1); the number
  stays typed text, never Word's list numbering;
- the lines of a paragraph are joined, across page breaks too; a word broken by a hyphen at a line end is joined;
- running headers, footers, page numbers and the lines set aside are left out;
- a list item ((a), 1., a bullet) keeps its marker as text and is indented;
- a table (rows of text whose pieces line up in columns) becomes a Word table, its widths from where the columns start
  (4.11.0, redlinetables).
It uses Word's built-in Normal and Heading styles. A sidecar <copy>.skredline.json keeps the source PDF's SHA-256, the
date, the source's name, the copy's paragraphs and the lines set aside, for the checks (redlinecheck). Rules only (No
AI); nothing leaves the PC."""
import datetime, hashlib, json, os, re

import pagesent as PS
import redlinetables as RT

FORMAT = 1                                   # formats.py "redline copy"
SIDE = ".skredline.json"
_DEPTH = re.compile(r"^\s*(?:(?:SECTION|Section|PART|Part|ARTICLE|Article)\s+)?([A-Z](?=\.\d))?\.?((?:\d+)(?:\.\d+)*)\.?(?=\s)")
_LETTER = re.compile(r"^\s*([A-Z])\.\s")


def depth(text):
    """Heading N from the number typed at its start: L.3.5.2 -> 4, 3.1 -> 2, C. -> 1, none -> 1. At most 9."""
    m = _DEPTH.match(text or "")
    if m:
        n = len(m.group(2).split(".")) + (1 if m.group(1) else 0)
        return max(1, min(9, n))
    return 1


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def join_lines(texts):
    """A paragraph's lines as one: a hyphen at a line end joins the word; otherwise one space."""
    out = ""
    for t in texts:
        t = " ".join(t.split())
        if not t:
            continue
        if out.endswith("-") and len(out) > 1 and out[-2].isalpha() and t[:1].islower():
            out = out[:-1] + t
        else:
            out = (out + " " + t) if out else t
    return out


def plan(pdf, name=None):
    """The copy's paragraphs: [{"kind": "heading"|"list"|"text", "level", "text", "page"}], and the lines set aside
    [(page, text)]. Fix text's decisions apply."""
    name = name or os.path.basename(pdf)
    doc = PS.doc_of(pdf)
    extra, force = PS.decided(pdf, name)
    sp = PS.split_decided(pdf, name)
    auto = set(doc.get("skip") or ())
    if sp:
        import verifysplit as SPL
        doc, remap, heads, bodies = SPL.split_doc(doc, sp)
        skip = {remap[k] for k in ((auto - set(force)) | set(extra)) if k in remap}
        set_aside = {remap[k] for k in set(extra) if k in remap}
        force = {remap[k]: v for k, v in force.items() if k in remap}
        force.update({k: True for k in heads}); force.update({k: False for k in bodies})
    else:
        skip = (auto - set(force)) | set(extra)
        set_aside = set(extra)
    import redlinelayout as RL
    tables = RL.tables(pdf, doc, skip)             # 4.11.0: tables become Word tables; 4.13.0: from their borders first
    in_tables = {x for t in tables for x in t["lines"]}
    paras = PS.paragraphs(doc, skip | in_tables, force)
    out = []
    for p in paras:
        texts = [doc["pages"][pi]["lines"][li]["text"] for pi, li in p["lines"]]
        text = join_lines(texts)
        if not text:
            continue
        if p["kind"] == "heading":
            first = doc["pages"][p["lines"][0][0]]["lines"][p["lines"][0][1]]
            out.append({"kind": "heading", "level": depth(text), "text": text, "page": p["page"],
                        "size": round(first.get("size") or 0, 1), "bold": bool(first.get("bold"))})   # 4.13.0: as set
        elif PS._LIST.match(text):
            out.append({"kind": "list", "level": 0, "text": text, "page": p["page"]})
        else:
            out.append({"kind": "text", "level": 0, "text": text, "page": p["page"]})
        out[-1]["at"] = p["lines"][0] if p["lines"] else (p["page"] - 1, 0)
    for t in tables:
        out.append({"kind": "table", "level": 0, "text": RL.text_of(t["grid"]), "page": t["page"] + 1, "grid": t["grid"],
                    "at": t["lines"][0]})
    out.sort(key=lambda p: tuple(p.get("at") or (0, 0)))
    for p in out:
        p.pop("at", None)
    aside = [(pi + 1, doc["pages"][pi]["lines"][li]["text"].strip()) for pi, li in sorted(set_aside)
             if pi < len(doc["pages"]) and li < len(doc["pages"][pi]["lines"])]
    keep = {(pi, li) for pi, p in enumerate(doc["pages"]) for li in range(len(p["lines"])) if (pi, li) not in skip}
    return out, aside, RL.setup(doc, keep, tables)


def copy_name(pdf, when=None):
    stem = os.path.splitext(os.path.basename(pdf))[0]
    return f"{stem} - redline copy - {(when or datetime.date.today()).isoformat()}.docx"


def build(pdf, out, name=None):
    """Write the clean copy to out (a .docx) and its sidecar. Returns {"path", "paragraphs", "headings", "set_aside"}.
    Raises ValueError for a PDF with no typed text (a scanned page): read it with OCR first (Fix text)."""
    import docxw
    import redlinedocx as RD
    import redlinelayout as RL
    paras, aside, pages = plan(pdf, name)
    if not paras:
        raise ValueError("The PDF has no typed text the copy could be made from.")
    d = docxw.Doc()
    doc = PS.doc_of(pdf)
    d.font = RL.body_font(pdf)                      # 4.13.0: the PDF's own body font and size
    d.half_points = int(round(2 * PS._body_size(doc))) or 22
    gi = 0                                          # 4.13.0: each run of pages keeps its size, orientation and margins
    for p in paras:
        while gi + 1 < len(pages) and p.get("page", 1) > pages[gi]["pages"][1]:
            RD.section(d, pages[gi])
            gi += 1
        if p["kind"] == "heading":
            RD.heading(d, p["text"], p["level"], p.get("size"), p.get("bold", True))
        elif p["kind"] == "list":
            d.rich([(p["text"], {})], indent=360)
        elif p["kind"] == "table":
            RD.table(d, p["grid"], RD.room(pages[gi]) if pages else 9360)
        else:
            d.para(p["text"])
    if pages:
        d.final_sect = RD.final(pages[gi])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    d.save(out)
    side = {"format": FORMAT, "source": os.path.basename(pdf), "source_sha256": _sha(pdf),
            "made": datetime.datetime.now().isoformat(timespec="seconds"), "paragraphs": paras,
            "set_aside": [list(x) for x in aside]}
    with open(out + SIDE, "w", encoding="utf-8") as f:
        json.dump(side, f, indent=1, ensure_ascii=False)
    return {"path": out, "paragraphs": len(paras), "headings": sum(1 for p in paras if p["kind"] == "heading"),
            "tables": sum(1 for p in paras if p["kind"] == "table"), "set_aside": len(aside)}


def sidecar(copy):
    try:
        with open(copy + SIDE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def copies(folder, pdf_name=None):
    """The redline copies in a folder (newest first), or those of one PDF."""
    try:
        fs = [f for f in os.listdir(folder) if f.lower().endswith(".docx") and " - redline copy - " in f and not f.startswith("~$")]
    except OSError:
        return []
    if pdf_name:
        stem = os.path.splitext(pdf_name)[0]
        fs = [f for f in fs if f.startswith(stem + " - redline copy - ")]
    return [os.path.join(folder, f) for f in sorted(fs, reverse=True)]
