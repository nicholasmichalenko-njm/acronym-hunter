"""Strip setup (3.60.0): a clean copy of a volume with the setup taken out, before it goes out. Make the setup writes
hidden reference text into each section (the RFP's words, PM direction, captures, notes, the Lead and Due line) in the
SK styles, and file properties naming the matrix; authors write around them. This removes every paragraph in an SK
setup style, the SK styles themselves once nothing uses them, and the Stationkeeper file properties, and says how many.
Bookmarks, comment anchors and section breaks inside a removed paragraph are kept (moved to the paragraph beside it),
so the TOC's bookmarks and the page layout stay whole. The volume read is never changed: the result is a new file.

strip(src, out=None) -> {"out", "paragraphs", "styles", "properties", "by_style": {style name: n}, "comments": n}
3.86.0: the references and notes for authors Make the setup put on the headings as Word comments (by Stationkeeper)
come out too; a person's own comments stay."""
import os, re, zipfile

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_SETUP = re.compile(r"^SK ?(RFP|Customer|Library|PM|Setup|Capture|Topic)")
_KEEP_TAGS = (W + "bookmarkStart", W + "bookmarkEnd", W + "commentRangeStart", W + "commentRangeEnd")


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


def _setup_styles(styles_root):
    """{style id: name} of the setup's styles."""
    out = {}
    if styles_root is None:
        return out
    for s in styles_root.iter(W + "style"):
        sid = s.get(W + "styleId") or ""
        nm = s.find(W + "name")
        name = nm.get(W + "val") if nm is not None else sid
        if _SETUP.match(name or "") or _SETUP.match(sid):
            out[sid] = name
    return out


def _strip_tree(root, ids, counts):
    """Remove the setup's paragraphs from one part (the body, a header, a footer). Returns how many."""
    n = 0
    for p in list(root.iter(W + "p")):
        ps = p.find(f"{W}pPr/{W}pStyle")
        sid = ps.get(W + "val") if ps is not None else ""
        if sid not in ids and not (sid and _SETUP.match(sid)):    # defined, or only named in the paragraph
            continue
        parent = p.getparent()
        keep = [el for el in p.iter() if el.tag in _KEEP_TAGS]
        sect = p.find(f"{W}pPr/{W}sectPr")
        if sect is not None:                              # a section break: keep the paragraph, drop its text and style
            for ch in list(p):
                if ch.tag != W + "pPr":
                    p.remove(ch)
            ps.getparent().remove(ps)
            for el in keep:
                p.append(el)
        else:
            sib = p.getnext()
            while sib is not None and sib.tag != W + "p":
                sib = sib.getnext()
            prev = p.getprevious()
            while prev is not None and prev.tag != W + "p":
                prev = prev.getprevious()
            for el in keep:
                if el.tag.endswith("Start") and sib is not None:
                    ppr = sib.find(W + "pPr")
                    (ppr.addnext(el) if ppr is not None else sib.insert(0, el))
                elif prev is not None:
                    prev.append(el)
                elif sib is not None:
                    sib.append(el)
            parent.remove(p)
            if parent.tag == W + "tc" and parent.find(W + "p") is None:     # a table cell keeps one paragraph
                etree.SubElement(parent, W + "p")
        nm = ids.get(sid, sid)
        counts[nm] = counts.get(nm, 0) + 1
        n += 1
    return n


def strip(src, out=None):
    import filesafety as FS
    out = out or FS.new_path(src, "stripped")
    FS.guard(out, src)
    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        data = {n: zin.read(n) for n in names}
    styles_root = etree.fromstring(data["word/styles.xml"], parser=_parser()) if "word/styles.xml" in data else None
    ids = _setup_styles(styles_root)
    counts, total = {}, 0
    parts = [n for n in names if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]
    still = set()
    for n in parts:
        root = etree.fromstring(data[n], parser=_parser())
        total += _strip_tree(root, ids, counts)
        for ps in root.iter(W + "pStyle"):
            still.add(ps.get(W + "val"))
        data[n] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    gone_styles = 0
    if styles_root is not None:
        for s in list(styles_root.iter(W + "style")):
            sid = s.get(W + "styleId")
            if sid in ids and sid not in still:
                s.getparent().remove(s); gone_styles += 1
        data["word/styles.xml"] = etree.tostring(styles_root, xml_declaration=True, encoding="UTF-8", standalone=True)
    import setupcomments as SCM                          # 3.86.0: the references for authors, as Word comments
    comments = SCM.strip_tree(data)
    props = 0
    if "docProps/custom.xml" in data:
        croot = etree.fromstring(data["docProps/custom.xml"], parser=_parser())
        for pr in list(croot):
            if (pr.get("name") or "").startswith("Stationkeeper"):
                croot.remove(pr); props += 1
        for i, pr in enumerate(croot, 2):                 # property ids stay 2, 3, 4... as Word expects
            pr.set("pid", str(i))
        data["docProps/custom.xml"] = etree.tostring(croot, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, data[n])
    os.replace(tmp, out)
    return {"out": out, "paragraphs": total, "styles": gone_styles, "properties": props, "by_style": counts, "comments": comments}
