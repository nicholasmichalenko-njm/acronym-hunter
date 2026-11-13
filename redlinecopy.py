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


COVER_CHARS = 600      # a page with fewer letters than this, no numbered heading and no table reads as a cover


def _cover_lines(paras, table_pages=()):
    """4.24.0 (Nicholas 2026-11-12, answer 26): a cover's large lines are plain paragraphs that look the same (their
    size, weight, color and font), not headings: a heading shows in Word's navigation pane and in a table of contents,
    and a title, a date and a company name do not belong there. A cover: a page with little text, no numbered heading
    and no table. The paragraphs are changed in place."""
    by_page = {}
    for p in paras:
        by_page.setdefault(p["page"], []).append(p)
    n = 0
    for page, ps in by_page.items():
        heads = [p for p in ps if p["kind"] == "heading"]
        if not heads or page in table_pages or any(_DEPTH.match(p["text"] or "") for p in heads):
            continue
        if sum(len(p["text"]) for p in ps) >= COVER_CHARS:
            continue
        for p in heads:
            p["kind"], p["level"], p["cover"] = "text", 0, True
            if not p.get("bold"):
                p.pop("bold", None)
            n += 1
    return n


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
    import redlinepics as RP
    tables = RL.tables(pdf, doc, skip)             # 4.11.0: tables become Word tables; 4.13.0: from their borders first
    in_tables = {x for t in tables for x in t["lines"]}
    kept0 = {(pi, li) for pi, p in enumerate(doc["pages"]) for li in range(len(p["lines"])) if (pi, li) not in skip}
    regs, rules = RP.regions(pdf, doc, skip | in_tables, tables, RL.setup(doc, kept0, tables))   # 4.22.0: the pictures
    in_pics = {(pi, li) for pi, rs in regs.items() for r in rs for li in r["lines"]}
    paras = PS.paragraphs(doc, skip | in_tables | in_pics, force)
    scans = RP.scanned(pdf, doc)                   # 4.22.0: pages read from a picture
    if scans:
        paras = _join_read_lines(doc, paras, scans, skip | in_tables | in_pics)
    starts = [(p["lines"][0][0], doc["pages"][p["lines"][0][0]]["lines"][p["lines"][0][1]].get("a", 0)) for p in paras if p["lines"]]
    how = RL.styles(pdf, starts)                   # 4.22.0: each paragraph's own font, slant and color
    body_font, body_size = RL.body_font(pdf), PS._body_size(doc)
    out = []
    for p in paras:
        texts = [doc["pages"][pi]["lines"][li]["text"] for pi, li in p["lines"]]
        text = join_lines(texts)
        if not text:
            continue
        if p["kind"] == "heading":
            first = doc["pages"][p["lines"][0][0]]["lines"][p["lines"][0][1]]
            bold, color = RL.line_style(pdf, p["lines"][0][0], first.get("a", 0))
            out.append({"kind": "heading", "level": depth(text), "text": text, "page": p["page"],      # 4.13.0: as set
                        "size": round(first.get("size") or 0, 1), "bold": bold or bool(first.get("bold")), "color": color})
        elif PS._LIST.match(text):
            out.append({"kind": "list", "level": 0, "text": text, "page": p["page"]})
        else:
            out.append({"kind": "text", "level": 0, "text": text, "page": p["page"]})
        out[-1]["at"] = p["lines"][0] if p["lines"] else (p["page"] - 1, 0)
        out[-1]["_lines"] = list(p["lines"])
        if p["lines"]:
            ln0 = doc["pages"][p["lines"][0][0]]["lines"][p["lines"][0][1]]
            st = how.get((p["lines"][0][0], ln0.get("a", 0))) or {}
            if p["lines"][0][0] in scans:           # words read from a picture carry no font or size of their own
                out[-1]["scan"] = True
                out[-1].pop("size", None)
                continue
            if st.get("font") and st["font"] != body_font:
                out[-1]["font"] = st["font"]
            if st.get("italic"):
                out[-1]["italic"] = True
            if out[-1]["kind"] != "heading":
                if st.get("bold") or ln0.get("bold"):
                    out[-1]["bold"] = True
                if st.get("color"):
                    out[-1]["color"] = st["color"]
                if ln0.get("size") and abs(ln0["size"] - body_size) > 0.6:
                    out[-1]["size"] = round(ln0["size"], 1)
    _cover_lines(out, {t["page"] + 1 for t in tables})
    for t in tables:
        box = t.get("box")
        if box is None:
            bx = [doc["pages"][pi]["lines"][li]["box"] for pi, li in t["lines"] if pi == t["page"]]
            box = (min(b[0] for b in bx), min(b[1] for b in bx), max(b[2] for b in bx), max(b[3] for b in bx)) if bx else (0, 0, 0, 0)
        out.append({"kind": "table", "level": 0, "text": RL.text_of(t["grid"]), "page": t["page"] + 1, "grid": t["grid"],
                    "at": t["lines"][0], "_box": box})
    behind = {}
    for pi, rs in sorted(regs.items()):            # 4.22.0: pictures in the flow are items; the others ride on a page
        ls = doc["pages"][pi]["lines"]
        for r in rs:
            if r["where"] == "flow":
                below = [li for li, ln in enumerate(ls) if (pi, li) not in (skip | in_pics) and ln["box"][1] >= r["box"][1] - 1]
                words = " ".join(ls[li]["text"].strip() for li in r["lines"])
                out.append({"kind": "picture", "level": 0, "text": "", "page": pi + 1, "at": (pi, (min(below) if below else len(ls)) - 0.5),
                            "_box": r["box"], "box": list(r["box"]), "words": words})
            elif not r.get("furniture"):
                behind.setdefault(pi, []).append(r)
    for pi in behind:
        if not any(p["page"] == pi + 1 for p in out):
            out.append({"kind": "blank", "level": 0, "text": "", "page": pi + 1, "at": (pi, -1), "_box": (0, 0, 0, 0)})
    out.sort(key=lambda p: tuple(p.get("at") or (0, 0)))
    out = _across_pages(doc, out)
    seen = set()
    for p in out:                                  # the first thing on a page holds the pictures behind that page
        pi = p["page"] - 1
        if pi in behind and pi not in seen:
            seen.add(pi)
            p["behind"] = [{"box": list(r["box"]), "under_text": bool(r["under_text"]),
                            "words": " ".join(doc["pages"][pi]["lines"][li]["text"].strip() for li in r["lines"])} for r in behind[pi]]
    keep = {(pi, li) for pi, p in enumerate(doc["pages"]) for li in range(len(p["lines"])) if (pi, li) not in skip}
    pages = RL.setup(doc, keep, tables)
    RL.geometry(doc, out, pages)                   # 4.13.0: where each paragraph and table sits on its page
    grp = {n: g for g in pages for n in range(g["pages"][0], g["pages"][1] + 1)}
    for p in out:                                  # a picture's place between the margins
        if p["kind"] == "picture" and p.get("geo") is not None:
            g = grp.get(p["page"]) or {"w": 612, "margins": (72, 72, 72, 72)}
            lo, hi = g["margins"][3], g["w"] - g["margins"][1]
            b = p["box"]
            if abs((b[0] + b[2]) / 2 - (lo + hi) / 2) < 6:
                p["geo"]["align"] = "center"
            else:
                p["geo"]["left"] = round(max(0.0, b[0] - lo), 1)
    furn = {}
    for pi, rs in regs.items():
        for r in rs:
            if r.get("furniture"):
                furn.setdefault(pi, []).append({"box": list(r["box"]), "where": r["where"]})
    for g in pages:
        g["furniture"] = {pi: furn[pi] for pi in furn if g["pages"][0] <= pi + 1 <= g["pages"][1]}
        g["rules"] = {pi: [list(b) for b in rules[pi]] for pi in rules if g["pages"][0] <= pi + 1 <= g["pages"][1]}
    import redlinehf as HF                         # 4.22.0: the running headers and footers become Word's own
    HF.plan(doc, skip - set_aside, pages, lambda pi, a: RL.styles(pdf, [(pi, a)]).get((pi, a)), lambda pi: _words(pdf, pi))
    for g in pages:                                # read from a picture: the header and footer in the body's font
        hf = g.get("hf")
        if hf and hf["page"] in scans:
            for zone in ("header", "footer"):
                hf[zone] = [(dict(r, size=9), parts, None, border) for r, parts, _st, border in hf[zone]]
    for p in out:
        for k in ("at", "_lines", "_box"):
            p.pop(k, None)
    aside = [(pi + 1, doc["pages"][pi]["lines"][li]["text"].strip()) for pi, li in sorted(set_aside)
             if pi < len(doc["pages"]) and li < len(doc["pages"][pi]["lines"])]
    return out, aside, pages


def _join_read_lines(doc, paras, scans, out_lines):
    """On a page read from a picture, the reader gives each line its own box, so a paragraph comes apart at every line.
    Two text lines are one paragraph when the first reaches the right edge of the text, the next sits one line below
    it and starts at the same left edge (or further left: the first was indented)."""
    import statistics
    edge = {}
    for pi in scans:
        ls = [ln for li, ln in enumerate(doc["pages"][pi]["lines"]) if (pi, li) not in out_lines]
        tops = sorted(ln["box"][1] for ln in ls)
        steps = [b - a for a, b in zip(tops, tops[1:]) if b - a > 2]
        if ls and steps:
            edge[pi] = (min(ln["box"][0] for ln in ls), max(ln["box"][2] for ln in ls), statistics.median(steps))
    out = []
    for p in paras:
        prev = out[-1] if out else None
        if prev is not None and p["kind"] == "text" and prev["kind"] == "text" and p["lines"] and prev["lines"]:
            (pa, la), (pb, lb) = prev["lines"][-1], p["lines"][0]
            if pa == pb and pa in edge:
                left, right, pitch = edge[pa]
                a, b = doc["pages"][pa]["lines"][la], doc["pages"][pb]["lines"][lb]
                width = max(1.0, right - left)
                if 0 < b["box"][1] - a["box"][1] <= 1.35 * pitch and a["box"][2] >= right - 0.06 * width \
                        and b["box"][0] <= a["box"][0] + 0.03 * width and not PS._LIST.match(b["text"].strip()):
                    prev["lines"].extend(p["lines"])
                    continue
        out.append(p)
    return out


def _words(pdf, pi):
    """The words of one page with their boxes (pdfobjects), [] when the page cannot be read."""
    import pypdfium2 as pdfium
    import pdfobjects as PO
    try:
        d = pdfium.PdfDocument(pdf)
    except Exception:  # noqa: BLE001
        return []
    try:
        page = d[pi]
        try:
            return PO.words(page)
        finally:
            page.close()
    finally:
        d.close()


def _across_pages(doc, out):
    """4.22.0: a paragraph the PDF broke at the foot of a page is one paragraph: the last text of a page that ends
    without a full stop, low on its page, and the first text of the next page, set the same way, are joined."""
    res = []
    for p in out:
        a = res[-1] if res else None
        if (a is not None and a["kind"] == "text" and p["kind"] == "text" and p["page"] == a["page"] + 1
                and a.get("_lines") and p.get("_lines")
                and all(a.get(k) == p.get(k) for k in ("font", "size", "bold", "italic", "color"))
                and not re.search(r"[.?!:;\u201d\")\]]\s*$", a["text"])):
            pi, li = a["_lines"][-1]
            pg = doc["pages"][pi]
            if pg["lines"][li]["box"][3] > 0.78 * (pg.get("h") or 792):
                a["_lines"] = a["_lines"] + p["_lines"]
                a["text"] = join_lines([doc["pages"][x]["lines"][y]["text"] for x, y in a["_lines"]])
                continue
        res.append(p)
    return res


def copy_name(pdf, when=None):
    stem = os.path.splitext(os.path.basename(pdf))[0]
    return f"{stem} - redline copy - {(when or datetime.date.today()).isoformat()}.docx"


def layout_of(pdf):
    """4.15.0: "slides" for a deck saved as PDF (redlineslides.is_slides), else "document"."""
    import redlineslides as SL
    try:
        return "slides" if SL.is_slides(pdf) else "document"
    except Exception:  # noqa: BLE001  a PDF that cannot be looked at is laid out as a document
        return "document"


def build(pdf, out, name=None, layout=None, comments=True):
    """Write the clean copy to out (a .docx) and its sidecar. Returns {"path", "paragraphs", "headings", "set_aside"}
    and, when the PDF has comments (4.16.0), "comments": what each became. comments=False leaves them out.
    Raises ValueError for a PDF with no typed text (a scanned page): read it with OCR first (Fix text)."""
    lay = layout or layout_of(pdf)
    if lay == "slides":                               # 4.15.0: one Word page a slide, its picture behind, text in frames
        import redlineslides as SL
        res = SL.build(pdf, out, name, FORMAT)
    else:
        res = _build_document(pdf, out, name)
    if comments:
        res.update(bring_comments(pdf, out, name, lay))
    return res


def bring_comments(pdf, out, name=None, layout="document"):
    """4.16.0: the PDF's comments into the copy as tracked changes, Word comments and replies (pdfcomments,
    redlinemarks); the sidecar keeps what each became. {} when the PDF has none."""
    import pdfcomments as PC
    import redlinemarks as RM
    try:
        found = PC.read(pdf)
    except Exception:  # noqa: BLE001  a PDF whose comments cannot be read is copied without them
        import diag
        diag.swallowed()
        return {}
    if not found:
        return {}
    if layout == "slides":
        import redlineslides as SL
        src = SL.plan(pdf, name)[1]
        doc = None
    else:
        import redlinecheck as CK
        src = CK.pdf_words(pdf, name)[0]
        d = PS.doc_of(pdf)
        extra, force = PS.decided(pdf, name or os.path.basename(pdf))
        doc = {"pages": d["pages"], "_out": ((set(d.get("skip") or ()) - set(force)) | set(extra))}
    pinned, stream = PC.pin(pdf, found, src, doc)
    recs = RM.apply(out, pinned, stream, src)
    side = sidecar(out) or {}
    side["comments"] = recs
    with open(out + SIDE, "w", encoding="utf-8") as f:
        json.dump(side, f, indent=1, ensure_ascii=False)
    became = [r["became"] for r in recs]
    return {"comments": recs, "changes": sum(1 for b in became if b in ("deletion", "insertion", "replacement")),
            "word_comments": sum(1 for b in became if b == "comment"),
            "by_position": sum(1 for r in recs if r["how"] in ("position", "left out", "nearby words"))}


def _build_document(pdf, out, name=None):
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
    worded = [p for p in paras if p["kind"] in ("text", "heading", "list")]
    if worded and all(p.get("scan") for p in worded):   # 4.22.0: read from a picture: no font to keep
        d.font, d.half_points = "Times New Roman", 22
    d.ppr_default = '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'   # 4.15.0: Word's own otherwise adds space
    import redlinepack as RK
    import redlinepics as RP
    media, n_pic = [], 0
    want = {}                                       # page index -> the boxes to draw, with the page's text and without
    for p in paras:
        if p["kind"] == "picture":
            want.setdefault((p["page"] - 1, False), []).append(tuple(p["box"]))
        for b in p.get("behind") or ():
            want.setdefault((p["page"] - 1, b["under_text"]), []).append(tuple(b["box"]))
    drawn = {}
    for (pi, bare), boxes in want.items():
        for box, blob in zip(boxes, RP.draw(pdf, pi, boxes, without_text=bare)):
            drawn[(pi, bare, box)] = blob

    def pic(pi, bare, box, behind):
        nonlocal n_pic
        n_pic += 1
        rid, name = f"rIdPic{n_pic}", f"picture{n_pic}.png"
        media.append((rid, name, drawn[(pi, bare, tuple(box))], "document"))
        return RP.anchor(rid, n_pic, box) if behind else RP.inline(rid, n_pic, box[2] - box[0], box[3] - box[1])

    import redlinehf as HF
    hf_parts = []
    for k, g in enumerate(pages, start=1):          # 4.22.0: each run of pages' header and footer
        hf = g.get("hf")
        if not hf:
            continue
        for zone in ("header", "footer"):
            boxes = hf["pictures"][zone]
            if not (hf[zone] or boxes):
                continue
            name, rid, runs = f"{zone}{k}.xml", f"rId{zone.capitalize()}{k}", ""
            for box, blob in zip(boxes, RP.draw(pdf, hf["page"], [tuple(b) for b in boxes])):
                n_pic += 1
                media.append((f"rIdPic{n_pic}", f"picture{n_pic}.png", blob, name))
                runs += RP.anchor(f"rIdPic{n_pic}", n_pic, box)
            hf_parts.append((rid, zone, name, HF.parts(g, zone, runs)))
            g["hdr" if zone == "header" else "ftr"] = rid
    gi = 0                                          # 4.13.0: each run of pages keeps its size, orientation and margins
    for p in paras:
        while gi + 1 < len(pages) and p.get("page", 1) > pages[gi]["pages"][1]:
            RD.section(d, pages[gi])
            gi += 1
        geo = p.get("geo")
        lead = "".join(pic(p["page"] - 1, b["under_text"], b["box"], True) for b in p.get("behind") or ())
        st = {k: p[k] for k in ("font", "size", "bold", "italic", "color") if p.get(k)}
        if p["kind"] == "heading":
            RD.heading(d, p["text"], p["level"], p.get("size"), p.get("bold", True), geo, p.get("color", ""),
                       p.get("font", ""), bool(p.get("italic")), lead)
        elif p["kind"] == "picture":
            RD.picture(d, pic(p["page"] - 1, False, p["box"], False), geo, lead)
        elif p["kind"] == "blank":
            RD.holder(d, lead, bool(geo and geo.get("break")))
        elif p["kind"] == "table":
            if lead:
                RD.holder(d, lead, bool(geo and geo.get("break")))
                geo = dict(geo or {}, **{"break": False})
            RD.spacer(d, geo)
            RD.table(d, p["grid"], RD.room(pages[gi]) if pages else 9360)
        elif geo:
            RD.para(d, p["text"], geo, st, lead)
        elif p["kind"] == "list":
            d.rich([(p["text"], {})], indent=360)
        else:
            d.para(p["text"])
    if d.body and d.body[-1].endswith("</w:tbl>"):
        d.body.append("<w:p/>")                     # Word ends a document with a paragraph
    if pages:
        d.final_sect = RD.final(pages[gi])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    d.save(out)
    RK.add(out, media, hf_parts)
    side = {"format": FORMAT, "layout": "document", "source": os.path.basename(pdf), "source_sha256": _sha(pdf),
            "made": datetime.datetime.now().isoformat(timespec="seconds"), "paragraphs": paras,
            "set_aside": [list(x) for x in aside]}
    with open(out + SIDE, "w", encoding="utf-8") as f:
        json.dump(side, f, indent=1, ensure_ascii=False)
    return {"path": out, "paragraphs": len(paras), "headings": sum(1 for p in paras if p["kind"] == "heading"),
            "tables": sum(1 for p in paras if p["kind"] == "table"), "set_aside": len(aside), "pictures": n_pic,
            "headers": sum(1 for _r, z, _n, _x in hf_parts if z == "header"), "footers": sum(1 for _r, z, _n, _x in hf_parts if z == "footer")}


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
