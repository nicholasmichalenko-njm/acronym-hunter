"""Section designs placed inside the setup (3.87.1, claude/stationkeeper-section-designs-2026-11-08.md): the filled
designs Setup picked go into the volume itself, each in its own Word section so its page layout stays its own.

    Before the response: CUI cover, Cover, Title page, then the front matter group (Table of Contents, Acronyms and
    Abbreviations, Units and Symbols). After the response: the back cover.
    A design's styles that the setup lacks come with it; its pictures and links come with it under new ids. Its own
    header and footer links are dropped, so a cover carries no running lines and the response keeps the template's.

place(setup_path, filled) -> [shelf placed]. filled: {shelf: path of the filled design}. Rules only; nothing leaves the PC."""
import copy, os, posixpath, zipfile

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PR = "http://schemas.openxmlformats.org/package/2006/relationships"
W = "{%s}" % NS_W
R = "{%s}" % NS_R
BEFORE = ("cui", "cover", "title", "toc", "acronyms", "units")
AFTER = ("back",)


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


def _read(path):
    with zipfile.ZipFile(path) as z:
        return z.namelist(), {n: z.read(n) for n in z.namelist()}


def _xml(b):
    return etree.fromstring(b, parser=_parser())


def _bytes(root):
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _rels(data, part="word/_rels/document.xml.rels"):
    if part in data:
        return _xml(data[part])
    return etree.Element("{%s}Relationships" % NS_PR, nsmap={None: NS_PR})


def _clean_sect(sect):
    """A design's section properties without its own header and footer links (their parts stay behind)."""
    s = copy.deepcopy(sect) if sect is not None else etree.Element(W + "sectPr")
    for tag in ("headerReference", "footerReference"):
        for el in s.findall(W + tag):
            s.remove(el)
    return s


def _break_para(sect):
    p = etree.Element(W + "p")
    ppr = etree.SubElement(p, W + "pPr")
    ppr.append(sect)
    return p


def _bring_styles(dst, src, used):
    """Style elements the setup lacks, copied from the design (with the styles they are based on)."""
    if "word/styles.xml" not in src:
        return 0
    s_src = _xml(src["word/styles.xml"])
    s_dst = _xml(dst["word/styles.xml"]) if "word/styles.xml" in dst else etree.Element(W + "styles", nsmap={"w": NS_W})
    have = {s.get(W + "styleId") for s in s_dst.iter(W + "style")}
    by = {s.get(W + "styleId"): s for s in s_src.iter(W + "style")}
    todo, n = list(used), 0
    while todo:
        sid = todo.pop()
        if sid in have or sid not in by:
            continue
        s_dst.append(copy.deepcopy(by[sid])); have.add(sid); n += 1
        for link in ("basedOn", "next", "link"):
            el = by[sid].find(W + link)
            if el is not None and el.get(W + "val"):
                todo.append(el.get(W + "val"))
    if n:
        dst["word/styles.xml"] = _bytes(s_dst)
    return n


def _bring_rels(dst, names, src, els, tag):
    """Pictures and links the design's elements point at: each target part copied under a new name, each id renumbered."""
    s_rels = {r.get("Id"): r for r in _rels(src)}
    d_rels = _rels(dst)
    ids = {r.get("Id") for r in d_rels}
    moved = {}
    for el in els:
        for node in el.iter():
            for att, rid in list(node.attrib.items()):
                if not att.startswith(R) or rid not in s_rels:
                    continue
                if rid not in moved:
                    r = s_rels[rid]
                    k = 1
                    while f"rIdD{tag}{k}" in ids:
                        k += 1
                    new = f"rIdD{tag}{k}"
                    ids.add(new)
                    nr = etree.SubElement(d_rels, "{%s}Relationship" % NS_PR)
                    nr.set("Id", new); nr.set("Type", r.get("Type"))
                    if r.get("TargetMode") == "External":
                        nr.set("Target", r.get("Target")); nr.set("TargetMode", "External")
                    else:
                        part = posixpath.normpath(posixpath.join("word", r.get("Target")))
                        if part in src:
                            stem, ext = posixpath.splitext(posixpath.basename(part))
                            dest = f"word/media/design_{tag}_{stem}{ext}"
                            dst[dest] = src[part]
                            if dest not in names:
                                names.append(dest)
                            nr.set("Target", posixpath.relpath(dest, "word"))
                            _content_type(dst, ext)
                        else:
                            nr.set("Target", r.get("Target"))
                    moved[rid] = new
                node.set(att, moved[rid])
    if moved:
        dst["word/_rels/document.xml.rels"] = _bytes(d_rels)
    return len(moved)


_CT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".emf": "image/x-emf",
       ".wmf": "image/x-wmf", ".svg": "image/svg+xml", ".bmp": "image/bmp", ".tif": "image/tiff", ".tiff": "image/tiff"}


def _content_type(dst, ext):
    ext = ext.lower()
    ct = dst["[Content_Types].xml"].decode("utf-8")
    if ext in _CT and f'Extension="{ext[1:]}"' not in ct:
        ct = ct.replace("</Types>", f'<Default Extension="{ext[1:]}" ContentType="{_CT[ext]}"/></Types>')
        dst["[Content_Types].xml"] = ct.encode("utf-8")


def _content(src_data):
    """A design's body (its own last section's properties apart) and that section's properties."""
    root = _xml(src_data["word/document.xml"])
    body = root.find(W + "body")
    sect = body.find(W + "sectPr")
    return [copy.deepcopy(el) for el in body if el is not sect], sect


def place(setup_path, filled):
    names, dst = _read(setup_path)
    droot = _xml(dst["word/document.xml"])
    body = droot.find(W + "body")
    final = body.find(W + "sectPr")
    placed = []
    head = []                                             # what goes before the response, in order
    for k, shelf in enumerate(BEFORE):
        p = (filled or {}).get(shelf)
        if not p or not os.path.isfile(p):
            continue
        _n, src = _read(p)
        els, sect = _content(src)
        used = {el.get(W + "val") for e in els for el in e.iter(W + "pStyle", W + "rStyle", W + "tblStyle") if el.get(W + "val")}
        _bring_styles(dst, src, used)
        _bring_rels(dst, names, src, els, k)
        head += els + [_break_para(_clean_sect(sect))]     # the design ends its own Word section
        placed.append(shelf)
    for el in reversed(head):
        body.insert(0, el)
    for k, shelf in enumerate(AFTER, len(BEFORE)):
        p = (filled or {}).get(shelf)
        if not p or not os.path.isfile(p):
            continue
        _n, src = _read(p)
        els, sect = _content(src)
        used = {el.get(W + "val") for e in els for el in e.iter(W + "pStyle", W + "rStyle", W + "tblStyle") if el.get(W + "val")}
        _bring_styles(dst, src, used)
        _bring_rels(dst, names, src, els, k)
        at = list(body).index(final) if final is not None else len(body)
        body.insert(at, _break_para(copy.deepcopy(final) if final is not None else etree.Element(W + "sectPr")))
        for i, el in enumerate(els, 1):                  # the response's section ends; the back cover is the last one
            body.insert(at + i, el)
        if final is not None:
            new_final = _clean_sect(sect)
            body.replace(final, new_final)
            final = new_final
        placed.append(shelf)
    if not placed:
        return []
    dst["word/document.xml"] = _bytes(droot)
    tmp = setup_path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, dst[n])
    os.replace(tmp, setup_path)
    return placed


def texts(path):
    """Every body paragraph's text, in order (for tests and the read-back)."""
    _n, d = _read(path)
    root = _xml(d["word/document.xml"])
    return ["".join(t.text or "" for t in p.iter(W + "t")) for p in root.find(W + "body").iter(W + "p")]


def sections(path):
    _n, d = _read(path)
    return len(_xml(d["word/document.xml"]).findall(f".//{W}sectPr"))


def place_in_order(path, items):
    """3.97.0 (Make templates, "the document starts with"): pages before the body in the order given, each in its own
    Word section; items [(key, path of the page's Word file)]. Returns the keys placed."""
    names, dst = _read(path)
    droot = _xml(dst["word/document.xml"])
    body = droot.find(W + "body")
    head, placed = [], []
    for k, (key, p) in enumerate(items or []):
        if not p or not os.path.isfile(p):
            continue
        _n, src = _read(p)
        els, sect = _content(src)
        used = {el.get(W + "val") for e in els for el in e.iter(W + "pStyle", W + "rStyle", W + "tblStyle") if el.get(W + "val")}
        _bring_styles(dst, src, used)
        _bring_rels(dst, names, src, els, f"s{k}")
        head += els + [_break_para(_clean_sect(sect))]
        placed.append(key)
    if not placed:
        return []
    for el in reversed(head):
        body.insert(0, el)
    dst["word/document.xml"] = _bytes(droot)
    tmp = path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, dst[n])
    os.replace(tmp, path)
    return placed
