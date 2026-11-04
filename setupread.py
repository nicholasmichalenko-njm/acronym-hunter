"""Read the setup back (3.43.0): an author's filled setup document, read by the response structure's headings and the
setup's own styles, never changed. For each section of the structure the document holds:
  status       Not started (no words of the author's own), Under way, Near budget (half the page budget or more),
               Over budget (past the page budget); with no budget, Under way once words are there
  words, pages the author's own words (not headings, not the setup's reference text) and the pages they make at the
               words per page set (450 unless the effort sets another)
  removed      the requirements placed in the section whose text is no longer in the document (an author deleted the
               hidden RFP text); moved: text that now sits under another heading
Styles brought in: styles the document uses that the setup did not have (the template's styles when its file is
found, else the standard's styles, the setup's styles and Word's own): pasted text usually brings them.
read(M, path, ...) returns a report; summary() keeps a line of it in the effort record; export_xlsx() writes it.
Rules only; nothing leaves the PC."""
import datetime, os, re, zipfile

WORDS_PER_PAGE = 450
STATUSES = ("Not started", "Under way", "Near budget", "Over budget")
KEY = "setup_readback"
W_ = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# Word's own styles a document may use without anyone bringing them in
WORD_OWN = {"Normal", "Default Paragraph Font", "Normal Table", "Table Normal", "No List", "Title", "Subtitle", "Caption",
            "Header", "Footer", "Footnote Text", "Footnote Reference", "Endnote Text", "Endnote Reference", "Table Grid",
            "Hyperlink", "FollowedHyperlink", "List Paragraph", "Balloon Text", "Comment Text", "Comment Reference",
            "Comment Subject", "annotation text", "annotation reference", "annotation subject", "Page Number", "Placeholder Text",
            "TOC Heading", "Table of Figures", "header", "footer", "footnote text", "footnote reference", "caption",
            "Revision", "Strong", "Emphasis", "Quote", "Intense Quote", "No Spacing", "Body Text", "List Bullet", "List Number",
            "Bibliography", "Mention", "Unresolved Mention", "Smart Hyperlink", "Hashtag", "Smart Link"}
WORD_OWN |= {f"Heading {i}" for i in range(1, 10)} | {f"heading {i}" for i in range(1, 10)} | {f"TOC {i}" for i in range(1, 10)} \
    | {f"toc {i}" for i in range(1, 10)} | {f"List Bullet {i}" for i in range(2, 6)} | {f"List Number {i}" for i in range(2, 6)}


def _parser():
    from lxml import etree
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


def style_names(path_or_zip):
    """{style id: name} of a Word file (its styles part)."""
    from lxml import etree
    try:
        z = path_or_zip if isinstance(path_or_zip, zipfile.ZipFile) else zipfile.ZipFile(path_or_zip)
        if "word/styles.xml" not in z.namelist():
            return {}
        root = etree.fromstring(z.read("word/styles.xml"), parser=_parser())
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError):
        return {}
    out = {}
    for s in root.iter(W_ + "style"):
        nm = s.find(W_ + "name")
        out[s.get(W_ + "styleId") or ""] = nm.get(W_ + "val") if nm is not None else (s.get(W_ + "styleId") or "")
    return out


def paragraphs(path):
    """[{"text", "style" (name), "outline", "styles_used": [names of the paragraph's, runs' and tables' styles]}] in order,
    hidden text included. Word's own pages when saved: returned as the second value (None when the file does not say)."""
    from lxml import etree
    z = zipfile.ZipFile(path)
    names = style_names(z)
    root = etree.fromstring(z.read("word/document.xml"), parser=_parser())
    app = z.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in z.namelist() else ""
    m = re.search(r"<Pages>(\d+)</Pages>", app)
    out = []
    for p in root.iter(W_ + "p"):
        st = p.find(f"{W_}pPr/{W_}pStyle")
        sid = st.get(W_ + "val") if st is not None else ""
        ol = p.find(f"{W_}pPr/{W_}outlineLvl")
        used = [names.get(sid, sid)] if sid else []
        used += [names.get(r.get(W_ + "val"), r.get(W_ + "val")) for r in p.iter(W_ + "rStyle")]
        tbl = next((a for a in p.iterancestors() if a.tag == W_ + "tbl"), None)
        if tbl is not None:
            ts = tbl.find(f"{W_}tblPr/{W_}tblStyle")
            if ts is not None:
                used.append(names.get(ts.get(W_ + "val"), ts.get(W_ + "val")))
        out.append({"text": "".join(t.text or "" for t in p.iter(W_ + "t")), "style": names.get(sid, sid) if sid else "Normal",
                    "outline": int(ol.get(W_ + "val")) if ol is not None else None, "styles_used": used})
    return out, (int(m.group(1)) if m else None)


def setup_styles(M, std=None):
    """The names of the setup's own styles (the reference text kinds), as the content map sets them."""
    import setuptemplate as ST
    return {v["style"] for v in ST.options(M, std).values()} | {style for _k, _l, style, _c, _i in ST.KINDS}


def baseline(std=None, template=None, M=None):
    """The styles the setup had: the template's when its file is given, else the standard's, the setup's and Word's own."""
    out = set(WORD_OWN)
    if template and os.path.isfile(template):
        out |= set(style_names(template).values())
    out |= set(((std or {}).get("style_defs") or {}).keys())
    if M is not None:
        out |= setup_styles(M, std)
    return out


def _is_heading(par):
    s = par["style"] or ""
    return par["outline"] is not None or s.lower().startswith("heading") or s.lower() == "title"


def status_of(words, budget, wpp=WORDS_PER_PAGE):
    if not words:
        return "Not started"
    if not budget:
        return "Under way"
    pages = words / float(wpp or WORDS_PER_PAGE)
    if pages > float(budget):
        return "Over budget"
    return "Near budget" if pages >= float(budget) / 2 else "Under way"


def read(M, path, std=None, template=None, wpp=WORDS_PER_PAGE):
    """The report for one filled setup document. M: the compliance matrix (its response structure and placements)."""
    import compliance as C
    import pagebudget as PB
    import setupdoc as SD
    wpp = float(wpp or WORDS_PER_PAGE)
    paras, saved_pages = paragraphs(path)
    sk = setup_styles(M, std)
    keys = {}
    for o in M.outline:
        lab = C.outline_label(o)
        keys[SD._norm(lab)] = lab
        if o.get("title"):
            keys.setdefault(SD._norm(o["title"]), lab)
    P = SD.placed_in(M)
    B = SD.by_id(M)
    probes = [(it["id"], SD._norm(it["text"])) for it in SD.all_items(M)
              if SD.kind_of(it) == "Requirement" and len(SD._norm(it["text"])) >= 12]
    words, found, seen, styles_at = {}, {}, [], {}
    base = baseline(std, template, M)
    cur = ""
    for par in paras:
        n = SD._norm(par["text"])
        for s in par["styles_used"]:
            if s and s not in base and s not in sk:
                styles_at.setdefault(s, [0, cur])
                styles_at[s][0] += 1
        if not n:
            continue
        if n in keys and len(n) < 200 and _is_heading(par):     # the cover and the TOC repeat the words, not as headings
            cur = keys[n]
            if cur not in seen:
                seen.append(cur)
            continue
        if par["style"] in sk:
            for iid, k in probes:
                if k in n:
                    found.setdefault(iid, set()).add(cur)
            continue
        if _is_heading(par):
            continue
        hit = False
        for iid, k in probes:                       # requirement words kept as plain text: still there, not the author's
            if k in n:
                found.setdefault(iid, set()).add(cur)
                hit = True
        if hit:
            continue
        words[cur] = words.get(cur, 0) + len(re.findall(r"[A-Za-z0-9][\w'’-]*", par["text"]))
    groups = [[C.outline_label(o) for o in entries] for _n, entries in SD.volume_groups(M)]
    in_doc = [g for g in groups if any(lab in seen for lab in g)]
    scope = [lab for g in in_doc for lab in g]
    rows = []
    for lab in scope:
        req = [i for i in P.get(lab, []) if i in B and SD.kind_of(B[i]) == "Requirement"]
        removed = [i for i in req if not found.get(i)]
        moved = [i for i in req if found.get(i) and lab not in found[i]]
        wd = words.get(lab, 0)
        bud = PB.pages(M, lab)
        rows.append({"section": lab, "found": lab in seen, "words": wd, "pages": round(wd / wpp, 1), "budget": bud,
                     "status": status_of(wd, bud, wpp) if lab in seen else "Heading not found",
                     "removed": [{"id": i, "text": B[i]["text"][:200]} for i in removed],
                     "moved": [{"id": i, "to": ", ".join(sorted(x or "(before the first heading)" for x in found[i])), "text": B[i]["text"][:200]}
                               for i in moved]})
    brought = sorted(({"style": s, "count": c, "first": first or "(before the first heading)"} for s, (c, first) in styles_at.items()),
                     key=lambda r: (-r["count"], r["style"].lower()))
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    return {"file": path, "when": datetime.datetime.now().isoformat(timespec="minutes"), "wpp": wpp, "saved_pages": saved_pages,
            "sections": rows, "styles": brought, "counts": counts, "matched": bool(scope),
            "removed": sum(len(r["removed"]) for r in rows), "moved": sum(len(r["moved"]) for r in rows),
            "words": sum(r["words"] for r in rows), "template": template or ""}


def summary_line(rep):
    if not rep.get("matched"):
        return "No heading of the response structure was found in this document."
    c = rep["counts"]
    bits = [f"{len(rep['sections'])} sections: " + ", ".join(f"{c[s]} {s.lower()}" for s in STATUSES if c.get(s))]
    if rep["removed"]:
        bits.append(f"{rep['removed']} requirement(s) removed")
    if rep["moved"]:
        bits.append(f"{rep['moved']} moved")
    if rep["styles"]:
        bits.append(f"{len(rep['styles'])} style(s) brought in")
    if rep.get("saved_pages"):
        bits.append(f"{rep['saved_pages']} pages when Word last saved it")
    return "; ".join(bits) + "."


def keep(rec, rep):
    """A line of the report in the effort record (the newest per file first; ten kept)."""
    rows = [r for r in (rec.data.get(KEY) or []) if r.get("file") != rep["file"]]
    line = {"file": rep["file"], "when": rep["when"], "counts": rep["counts"], "removed": rep["removed"], "moved": rep["moved"],
            "styles": len(rep["styles"]), "words": rep["words"]}
    rec.data[KEY] = ([line] + rows)[:10]
    rec.save()
    return line


def latest(rec):
    return list(rec.data.get(KEY) or [])


def file_template(path, folder=None):
    """The template a setup document was made from, when its file can be found: the SK Template property names it; the
    file is looked for in the Templates folder beside the document (or folder)."""
    try:
        z = zipfile.ZipFile(path)
        cp = z.read("docProps/custom.xml").decode("utf-8", "replace") if "docProps/custom.xml" in z.namelist() else ""
    except (OSError, zipfile.BadZipFile):
        return ""
    m = re.search(r'name="SK Template"[^>]*>\s*<vt:lpwstr>([^<]+)</vt:lpwstr>', cp)
    if not m:
        return ""
    want = m.group(1).strip().lower()
    for d in [folder] if folder else [os.path.join(os.path.dirname(path), "Templates"), os.path.dirname(path)]:
        if d and os.path.isdir(d):
            for dp, _ds, fs in os.walk(d):
                for f in fs:
                    if f.lower().endswith((".dotx", ".dotm")) and os.path.splitext(f)[0].lower().startswith(want):
                        return os.path.join(dp, f)
    return ""


def export_xlsx(rep, path):
    """The report as a workbook: Sections, Requirements removed or moved, Styles brought in."""
    import openpyxl
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Sections"
    ws.append(["Section", "Status", "Words", f"Pages (at {int(rep['wpp'])} words)", "Page budget", "Requirements removed", "Moved"])
    for r in rep["sections"]:
        ws.append([r["section"], r["status"], r["words"], r["pages"], r["budget"] if r["budget"] is not None else "",
                   len(r["removed"]), len(r["moved"])])
    w2 = wb.create_sheet("Requirements")
    w2.append(["Section", "What happened", "Requirement", "Text"])
    for r in rep["sections"]:
        for x in r["removed"]:
            w2.append([r["section"], "Removed", x["id"], x["text"]])
        for x in r["moved"]:
            w2.append([r["section"], "Now under " + x["to"], x["id"], x["text"]])
    w3 = wb.create_sheet("Styles brought in")
    w3.append(["Style", "Times used", "First under"])
    for s in rep["styles"]:
        w3.append([s["style"], s["count"], s["first"]])
    for sh in wb.worksheets:
        for c in sh[1]:
            c.font = Font(bold=True)
        sh.freeze_panes = "A2"
    wb.save(path)
    return path
