"""References and notes for authors as Word comments (3.86.0, claude/stationkeeper-setup-from-review-2026-11-08.md):
Make the setup puts each section's references (sectionnotes.refs) on its heading as Word comments, one comment per
reference, by "Stationkeeper" with the initials SK. No reference, no comment. Strip setup takes them out (and only
them: a person's own comments stay); Final Check warns when any is left in a volume going out.

add(path, by_heading)    by_heading: {section label: [comment text]}; matched to the heading paragraphs by their words
                         (the number may be Word's own). Returns how many comments were added.
strip_tree(data)         the docx parts in a dict, Stationkeeper's comments taken out; returns how many
count(path)              Stationkeeper's comments still in a file
Rules only; the files never leave the PC."""
import datetime, re, zipfile

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS_W
AUTHOR, INITIALS = "Stationkeeper", "SK"
REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


def _norm(t):
    t = re.sub(r"^\s*(?:[A-Z]\.)?\d+(?:\.\d+)*\.?\s+", "", t or "")
    return " ".join(re.findall(r"[a-z0-9]+", t.lower()))


def _ptext(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def _is_heading(p, heading_ids):
    ps = p.find(f"{W}pPr/{W}pStyle")
    return ps is not None and ps.get(W + "val") in heading_ids


def _heading_ids(styles_root):
    out = set()
    if styles_root is None:
        return out
    for s in styles_root.iter(W + "style"):
        nm = s.find(W + "name")
        name = (nm.get(W + "val") if nm is not None else "") or ""
        if re.match(r"(?i)^heading [1-9]$", name) or (s.find(f"{W}pPr/{W}outlineLvl") is not None):
            out.add(s.get(W + "styleId"))
    return out


def add(path, by_heading, when=None):
    by = {_norm(k): [c for c in v if (c or "").strip()] for k, v in (by_heading or {}).items()}
    by = {k: v for k, v in by.items() if k and v}
    if not by:
        return 0
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
    droot = etree.fromstring(data["word/document.xml"], parser=_parser())
    sroot = etree.fromstring(data["word/styles.xml"], parser=_parser()) if "word/styles.xml" in data else None
    hids = _heading_ids(sroot)
    if "word/comments.xml" in data:
        croot = etree.fromstring(data["word/comments.xml"], parser=_parser())
    else:
        croot = etree.Element(W + "comments", nsmap={"w": NS_W})
    used = [int(c.get(W + "id")) for c in croot.iter(W + "comment") if (c.get(W + "id") or "").isdigit()]
    for el in droot.iter(W + "commentRangeStart"):
        if (el.get(W + "id") or "").isdigit():
            used.append(int(el.get(W + "id")))
    nid = max(used, default=-1) + 1
    stamp = (when or datetime.datetime.now()).strftime("%Y-%m-%dT%H:%M:%SZ")
    added, done = 0, set()
    for p in droot.iter(W + "p"):
        if hids and not _is_heading(p, hids):
            continue
        key = _norm(_ptext(p))
        if key not in by or key in done:
            continue
        done.add(key)
        for text in by[key]:
            c = etree.SubElement(croot, W + "comment")
            c.set(W + "id", str(nid)); c.set(W + "author", AUTHOR); c.set(W + "initials", INITIALS); c.set(W + "date", stamp)
            for k, line in enumerate(text.splitlines() or [text]):
                cp = etree.SubElement(c, W + "p")
                if k == 0:
                    r0 = etree.SubElement(cp, W + "r"); etree.SubElement(r0, W + "annotationRef")
                r = etree.SubElement(cp, W + "r"); t = etree.SubElement(r, W + "t"); t.text = line
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            start = etree.Element(W + "commentRangeStart"); start.set(W + "id", str(nid))
            end = etree.Element(W + "commentRangeEnd"); end.set(W + "id", str(nid))
            ppr = p.find(W + "pPr")
            p.insert(list(p).index(ppr) + 1 if ppr is not None else 0, start)
            p.append(end)
            ref = etree.SubElement(p, W + "r"); etree.SubElement(ref, W + "commentReference").set(W + "id", str(nid))
            nid += 1
            added += 1
    if not added:
        return 0
    data["word/document.xml"] = etree.tostring(droot, xml_declaration=True, encoding="UTF-8", standalone=True)
    data["word/comments.xml"] = etree.tostring(croot, xml_declaration=True, encoding="UTF-8", standalone=True)
    if "word/comments.xml" not in names:
        names.append("word/comments.xml")
        rels = etree.fromstring(data["word/_rels/document.xml.rels"], parser=_parser())
        if not any(r.get("Type") == REL_TYPE for r in rels):
            ids = {r.get("Id") for r in rels}
            k = 1
            while f"rIdSK{k}" in ids:
                k += 1
            r = etree.SubElement(rels, "{%s}Relationship" % RELS)
            r.set("Id", f"rIdSK{k}"); r.set("Type", REL_TYPE); r.set("Target", "comments.xml")
            data["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
        ct = data["[Content_Types].xml"].decode("utf-8")
        if "/word/comments.xml" not in ct:
            ct = ct.replace("</Types>", f'<Override PartName="/word/comments.xml" ContentType="{CT}"/></Types>')
            data["[Content_Types].xml"] = ct.encode("utf-8")
    tmp = path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, data[n])
    import os
    os.replace(tmp, path)
    return added


def _ours(croot):
    return {c.get(W + "id") for c in croot.iter(W + "comment") if c.get(W + "author") == AUTHOR and c.get(W + "initials") == INITIALS}


def strip_tree(data):
    """data: {part name: bytes}. Takes Stationkeeper's comments, their ranges and references out. Returns how many."""
    if "word/comments.xml" not in data:
        return 0
    croot = etree.fromstring(data["word/comments.xml"], parser=_parser())
    ids = _ours(croot)
    if not ids:
        return 0
    for c in list(croot.iter(W + "comment")):
        if c.get(W + "id") in ids:
            croot.remove(c)
    data["word/comments.xml"] = etree.tostring(croot, xml_declaration=True, encoding="UTF-8", standalone=True)
    for n in [n for n in data if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]:
        root = etree.fromstring(data[n], parser=_parser())
        hit = False
        for tag in ("commentRangeStart", "commentRangeEnd"):
            for el in list(root.iter(W + tag)):
                if el.get(W + "id") in ids:
                    el.getparent().remove(el); hit = True
        for el in list(root.iter(W + "commentReference")):
            if el.get(W + "id") in ids:
                run = el.getparent()
                run.remove(el)
                if run.tag == W + "r" and not [x for x in run if x.tag != W + "rPr"]:
                    run.getparent().remove(run)
                hit = True
        if hit:
            data[n] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    return len(ids)


def count(path):
    try:
        with zipfile.ZipFile(path) as z:
            if "word/comments.xml" not in z.namelist():
                return 0
            return len(_ours(etree.fromstring(z.read("word/comments.xml"), parser=_parser())))
    except (OSError, zipfile.BadZipFile, etree.XMLSyntaxError):
        return 0


def comments_of(path):
    """[(author, text)] of every comment in a file (for tests and the check's detail)."""
    with zipfile.ZipFile(path) as z:
        if "word/comments.xml" not in z.namelist():
            return []
        root = etree.fromstring(z.read("word/comments.xml"), parser=_parser())
    return [(c.get(W + "author"), "\n".join(_ptext(p) for p in c.iter(W + "p"))) for c in root.iter(W + "comment")]
