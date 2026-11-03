"""Quick Parts in a standard (3.22.0): the building blocks a template made from the standard carries.

Picked from any template or Word document (.dotx, .dotm, .docx), which is read once and never written; macros never run,
only the XML is read. A copy of the source file is kept with this PC's standards (<config>\\production_parts, the same
folder as covers and back covers, never the program folder), so the standard can put the entries into every template it
makes. Make a template copies them in with their pictures and styles and, when the standard says so, puts every one in
the Quick Parts gallery under its category (Word lists them by category, then name)."""
import copy, hashlib, os, re, shutil

import prodparts as PP
from lxml import etree
from prodengine.engine.pkg import Package, NS, PR
from prodengine.engine.ops import glossary as G

QUICK_GALLERY = "docParts"            # Word's Quick Parts gallery
QP_ALLOWED = ("word/glossary/*", "package|parts")     # the guarded write lets this op change the glossary and add its parts only


def gallery_name(g):
    return G.GALLERIES.get(g or "", g or "no gallery")


def read(path):
    """[{name, category, gallery, description, text, pictures}] of a file's Quick Parts; [] when it has none."""
    pkg = Package(path)
    return [{k: e[k] for k in ("name", "category", "gallery", "description", "text", "pictures")} for e in G.entries(pkg)]


def keep_source(config_dir, path):
    """A copy of the source file in the standards' parts folder (once per distinct file). Returns its file name."""
    with open(path, "rb") as f:
        data = f.read()
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(os.path.basename(path))[0])[:40] or "quickparts"
    ext = os.path.splitext(path)[1].lower() if os.path.splitext(path)[1].lower() in (".dotx", ".dotm", ".docx") else ".dotx"
    name = f"qp_{stem}_{hashlib.sha256(data).hexdigest()[:8]}{ext}"
    folder = PP.parts_dir(config_dir)
    os.makedirs(folder, exist_ok=True)
    dst = os.path.join(folder, name)
    if not os.path.isfile(dst):
        shutil.copyfile(path, dst)
    return name


def op_quick_parts(pkg, entries, parts_dir, one_gallery=True):
    """Copy the standard's Quick Parts into the template from their kept sources; in one gallery when asked, each under
    its category. A missing source or a name already in the template is reported, never guessed."""
    by_src, missing = {}, []
    for e in entries or []:
        src = os.path.join(parts_dir or "", e.get("source") or "")
        if not e.get("name") or not os.path.isfile(src):
            missing.append(e.get("name") or "(no name)")
            continue
        by_src.setdefault(src, []).append(e)
    copied, skipped = [], []
    for src, es in by_src.items():
        try:
            r = G.op_provision(pkg, src, [e["name"] for e in es])
        except G.Refused as ex:
            skipped += [(e["name"], str(ex)) for e in es]
            continue
        copied += [n for n in r.get("copied", [])]
        skipped += list(r.get("skipped", []))
    want = {e["name"]: e for e in entries or [] if e.get("name") in copied}
    if want and G.gloss_part(pkg):
        pkg.touch(G.gloss_part(pkg))
        for dp in pkg.tree(G.gloss_part(pkg)).iter(f"{{{NS['w']}}}docPart"):
            pr = dp.find("w:docPartPr", NS)
            nm = pr.find("w:name", NS)
            name = nm.get(f"{{{NS['w']}}}val") if nm is not None else None
            if name not in want:
                continue
            pkg.mark(dp)
            if want[name].get("category"):
                G._set(pr, ["category", "name"], want[name]["category"])
            if one_gallery:
                G._set(pr, ["category", "gallery"], QUICK_GALLERY)
        G.check_unique(pkg)
    styles = sync_styles(pkg) if copied else {}
    return {"copied": copied, "skipped": skipped, "missing": missing, "styles_added": styles.get("added", []),
            "styles_matched": styles.get("matched", 0)}


STYLES_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"
STYLES_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"


def _w(tag):
    return f"{{{NS['w']}}}{tag}"


def sync_styles(pkg):
    """3.22.0: the template's styles drive its Quick Parts. Every style a Quick Part uses (and the styles it is based on)
    takes the template's own definition in the Quick Parts' styles part too, so a part looks the same in the gallery and
    where it is put, whenever it was added. A style the template does not have is added to the template from the part
    and reported. Returns {"added": [style names], "matched": n}."""
    g = G.gloss_part(pkg)
    main_s = pkg.word_part("/styles")
    if not g or not main_s:
        return {"added": [], "matched": 0}
    gs = next((t for (typ, t, mode) in pkg.rels_of(g).values() if typ.endswith("/styles") and mode != "External"), None)
    if gs is None:                                    # the Quick Parts had no styles of their own: they take the template's
        gs = "word/glossary/styles.xml"
        pkg.add_part(gs, copy.deepcopy(pkg.tree(main_s)), STYLES_CT)
        rels = G._rels_tree(pkg, g)
        r = etree.SubElement(rels, f"{{{PR}}}Relationship")
        r.set("Id", G._new_rid(rels)); r.set("Type", STYLES_REL); r.set("Target", "styles.xml")
    pkg.touch(gs); pkg.touch(main_s)
    groot, mroot = pkg.tree(gs), pkg.tree(main_s)
    sid = _w("styleId")
    mby = {x.get(sid): x for x in mroot.findall("w:style", NS)}
    gby = {x.get(sid): x for x in groot.findall("w:style", NS)}
    todo = {el.get(_w("val")) for el in pkg.tree(g).iter(_w("pStyle"), _w("rStyle"), _w("tblStyle"))}
    seen, added, matched = set(), [], 0
    while todo:
        k = todo.pop()
        if not k or k in seen:
            continue
        seen.add(k)
        src = mby.get(k)
        if src is None and k in gby:                  # a style the template lacks: the template takes the part's
            src = copy.deepcopy(gby[k])
            mroot.append(src); pkg.mark(src); mby[k] = src
            nm = src.find("w:name", NS)
            added.append(nm.get(_w("val")) if nm is not None else k)
        if src is None:
            continue
        new = copy.deepcopy(src)
        if k in gby:
            gby[k].addprevious(new); groot.remove(gby[k])
        else:
            groot.append(new)
        pkg.mark(new); gby[k] = new; matched += 1
        for tag in ("basedOn", "next", "link"):
            x = src.find(f"w:{tag}", NS)
            if x is not None:
                todo.add(x.get(_w("val")))
    return {"added": added, "matched": matched}


def as_design(path, name, kind="header"):
    """3.25.0: a Quick Part made into a part's header or footer, kept whole (its tables at their inch widths, tab stops,
    pictures and fields): {kind: xml, kind + "_media": [pictures]}, the shape the standard's hf_designs keep. The
    source file is only read. None when the Quick Part is not in it."""
    import base64
    import posixpath
    pkg = Package(path)
    hit = next((e for e in G.entries(pkg) if e["name"] == name), None)
    if hit is None:
        return None
    W = NS["w"]
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    root = etree.Element(f"{{{W}}}{'hdr' if kind == 'header' else 'ftr'}", nsmap={"w": W, "r": R})
    body = hit["el"].find("w:docPartBody", NS)
    for ch in body:
        if etree.QName(ch).localname == "sectPr":
            continue
        root.append(copy.deepcopy(ch))
    if not len(root) or etree.QName(root[-1]).localname != "p":
        etree.SubElement(root, f"{{{W}}}p")              # Word needs a header or footer to end with a paragraph
    xml = etree.tostring(root, encoding="unicode")
    used = set(re.findall(r'r:(?:embed|id|link)="([^"]+)"', xml))
    g = G.gloss_part(pkg)
    media = []
    for rid, (typ, t, mode) in pkg.rels_of(g).items():
        if rid in used and mode != "External" and typ.endswith("/image") and t in pkg.raw:
            media.append({"rid": rid, "name": posixpath.basename(t), "type": typ, "ct": pkg.content_type("/" + t),
                          "b64": base64.b64encode(pkg.raw[t]).decode("ascii")})
    return {kind: xml, kind + "_media": media}
