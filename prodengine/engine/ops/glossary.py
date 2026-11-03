"""Quick Parts (building blocks) in a template's glossary part, edited directly.

Word's identity for an entry is name + category + gallery. Display order is category then name,
so order is controlled with number prefixes ("03 Section Header"), not XML order.
"""
import copy
import posixpath
import uuid

from lxml import etree
from ..pkg import Package, W, R, PR, NS, Refused
from ..ordered import q, local

GLOSS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/glossaryDocument"
GLOSS_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.glossary+xml"
GALLERIES = {"docParts": "Quick Parts", "hdrs": "Headers", "ftrs": "Footers", "coverPg": "Cover Pages", "tbls": "Tables",
             "autoTxt": "AutoText", "custQuickParts": "Custom Quick Parts"}


def gloss_part(pkg):
    return pkg.word_part("/glossaryDocument")


def entries(pkg):
    g = gloss_part(pkg)
    if not g:
        return []
    out = []
    for dp in pkg.tree(g).iter(q("docPart")):
        pr = dp.find("w:docPartPr", NS)
        def v(path):
            el = pr.find(path, NS)
            return el.get(q("val")) if el is not None else None
        body = dp.find("w:docPartBody", NS)
        text = "".join(t.text or "" for t in body.iter(q("t")))
        out.append({"name": v("w:name"), "category": v("w:category/w:name"), "gallery": v("w:category/w:gallery"),
                    "description": v("w:description"), "guid": v("w:guid"), "text": text,
                    "pictures": sum(1 for _ in body.iter(q("drawing"))), "el": dp})
    return out


def find(pkg, name, category=None):
    hits = [e for e in entries(pkg) if e["name"] == name and (category is None or e["category"] == category)]
    if len(hits) != 1:
        raise Refused(f"Quick Part {name!r} found {len(hits)} times; give the category too.")
    return hits[0]


def _set(pr, path_tags, val):
    cur = pr
    for t in path_tags:
        nxt = cur.find(q(t))
        if nxt is None:
            nxt = etree.SubElement(cur, q(t))
        cur = nxt
    cur.set(q("val"), val)


def check_unique(pkg):
    seen = set()
    for e in entries(pkg):
        key = (e["name"], e["category"], e["gallery"])
        if key in seen:
            raise Refused(f"Two Quick Parts would share name, category and gallery: {key}")
        seen.add(key)


def op_rename(pkg, mapping):
    g = gloss_part(pkg); pkg.touch(g)
    done = []
    for old, new in mapping.items():
        e = find(pkg, old)
        pkg.mark(e["el"])
        _set(e["el"].find("w:docPartPr", NS), ["name"], new)
        done.append((old, new))
    check_unique(pkg)
    return {"renamed": done}


def op_recategorize(pkg, mapping):
    g = gloss_part(pkg); pkg.touch(g)
    for name, cat in mapping.items():
        e = find(pkg, name)
        pkg.mark(e["el"])
        _set(e["el"].find("w:docPartPr", NS), ["category", "name"], cat)
    check_unique(pkg)
    return {"recategorized": list(mapping.items())}


def op_describe(pkg, mapping):
    g = gloss_part(pkg); pkg.touch(g)
    for name, desc in mapping.items():
        if len(desc) > 255:
            raise Refused("A Quick Part description has 255 characters at most.")
        e = find(pkg, name)
        pkg.mark(e["el"])
        pr = e["el"].find("w:docPartPr", NS)
        d = pr.find("w:description", NS)
        if d is None:
            d = etree.Element(q("description"))
            # description comes after behaviors and before guid
            gd = pr.find("w:guid", NS)
            (gd.addprevious(d) if gd is not None else pr.append(d))
        d.set(q("val"), desc)
    return {"described": list(mapping)}


def op_delete(pkg, names):
    g = gloss_part(pkg); pkg.touch(g)
    for n in names:
        e = find(pkg, n)
        pkg.mark(e["el"])
        e["el"].getparent().remove(e["el"])
    return {"deleted": names}


def op_duplicate(pkg, name, new_name, new_category=None):
    g = gloss_part(pkg); pkg.touch(g)
    e = find(pkg, name)
    dup = copy.deepcopy(e["el"])
    pr = dup.find("w:docPartPr", NS)
    _set(pr, ["name"], new_name)
    if new_category:
        _set(pr, ["category", "name"], new_category)
    _set(pr, ["guid"], "{" + str(uuid.uuid4()).upper() + "}")
    e["el"].addnext(dup)
    pkg.mark(dup)
    check_unique(pkg)
    return {"duplicated": (name, new_name)}


# ---------------------------------------------------------------- provision across templates
def _rels_tree(pkg, part):
    rn = pkg.rels_name(part)
    if not pkg.has(rn):
        root = etree.Element(f"{{{PR}}}Relationships", nsmap={None: PR})
        pkg.add_part(rn, root, "application/vnd.openxmlformats-package.relationships+xml")
    pkg.touch(rn)
    pkg.mark_part(rn)  # a relationships part is one unit; adding a relationship changes it
    return pkg.tree(rn)


def _new_rid(rels):
    ids = {r.get("Id") for r in rels}
    i = 1
    while f"rIdPE{i}" in ids:
        i += 1
    return f"rIdPE{i}"


def _ensure_glossary(dst, src):
    """Create a glossary part in dst modelled on src's (its styles, settings, fonts travel with it)."""
    if gloss_part(dst):
        return gloss_part(dst)
    sg = gloss_part(src)
    name = "word/glossary/document.xml"
    root = copy.deepcopy(src.tree(sg))
    dps = root.find("w:docParts", NS)
    for dp in list(dps):
        dps.remove(dp)
    dst.add_part(name, root, GLOSS_CT)
    rels = _rels_tree(dst, dst.main)
    rid = _new_rid(rels)  # the document's relationships part is declared by _rels_tree
    r = etree.SubElement(rels, f"{{{PR}}}Relationship")
    r.set("Id", rid); r.set("Type", GLOSS_REL); r.set("Target", "glossary/document.xml")
    # copy the glossary's own support parts (styles, settings, fontTable, webSettings)
    srels = src.rels_of(sg)
    grels = _rels_tree(dst, name)
    for rid0, (typ, tgt, mode) in srels.items():
        if mode == "External" or typ.endswith(("/image", "/header", "/footer")):
            continue
        tname = tgt
        if dst.has(tname):
            continue
        dst.add_part(tname, src.raw[tgt], src.content_type("/" + tgt))
        rr = etree.SubElement(grels, f"{{{PR}}}Relationship")
        rr.set("Id", rid0); rr.set("Type", typ); rr.set("Target", posixpath.relpath(tname, posixpath.dirname(name)))
    return name


def _copy_story(src, dst, tgt, kind, media):
    """Copy a header or footer part (and the pictures it uses) from src into dst's glossary folder. Returns its name."""
    k = 1
    while dst.has(f"word/glossary/pe_{kind}{k}.xml"):
        k += 1
    name = f"word/glossary/pe_{kind}{k}.xml"
    dst.add_part(name, copy.deepcopy(src.tree(tgt)), src.content_type("/" + tgt))
    srels = src.rels_of(tgt)
    if srels:
        hrels = _rels_tree(dst, name)
        for rid0, (typ, t, mode) in srels.items():
            rr = etree.SubElement(hrels, f"{{{PR}}}Relationship")
            rr.set("Id", rid0); rr.set("Type", typ)
            if mode == "External":
                rr.set("Target", t); rr.set("TargetMode", "External")
                continue
            ext = t.rsplit(".", 1)[-1]
            j = 1
            while dst.has(f"word/media/pe_qp{j}.{ext}"):
                j += 1
            mname = f"word/media/pe_qp{j}.{ext}"
            dst.add_part(mname, src.raw[t], src.content_type("/" + t) or f"image/{ext}")
            rr.set("Target", posixpath.relpath(mname, posixpath.dirname(name)))
            media.append(mname)
    return name


NUM_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering"
NUM_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"


def _numbering_part(pkg, part):
    return next((t for (typ, t, mode) in pkg.rels_of(part).values() if typ.endswith("/numbering") and mode != "External"), None)


def _copy_numbering(src, sg, dst, dg, dp):
    """3.24.0: the list definitions an entry uses (w:num and its w:abstractNum) copied into the destination glossary's
    numbering part under new ids, and the entry's numId values changed to them. Returns '' or why it could not."""
    sn = _numbering_part(src, sg) or src.word_part("/numbering")
    if not sn:
        return "uses list numbering the source does not define"
    sroot = src.tree(sn)
    dn = _numbering_part(dst, dg)
    if not dn:
        k = 1
        while dst.has(f"word/glossary/numbering{k}.xml"):
            k += 1
        dn = f"word/glossary/numbering{k}.xml"
        root = etree.Element(q("numbering"), nsmap={"w": NS["w"]})
        dst.add_part(dn, root, NUM_CT)
        rels = _rels_tree(dst, dg)
        rr = etree.SubElement(rels, f"{{{PR}}}Relationship")
        rr.set("Id", _new_rid(rels)); rr.set("Type", NUM_REL); rr.set("Target", posixpath.basename(dn))
    dst.touch(dn)
    droot = dst.tree(dn)
    used_num = {int(x.get(q("numId"))) for x in droot.findall("w:num", NS)}
    used_abs = {int(x.get(q("abstractNumId"))) for x in droot.findall("w:abstractNum", NS)}
    snums = {x.get(q("numId")): x for x in sroot.findall("w:num", NS)}
    sabs = {x.get(q("abstractNumId")): x for x in sroot.findall("w:abstractNum", NS)}
    remap = {}
    for el in dp.iter(q("numId")):
        old = el.get(q("val"))
        if old in (None, "0"):
            continue
        if old not in remap:
            num = snums.get(old)
            if num is None:
                return f"list number {old} has no definition in the source"
            aid = num.find("w:abstractNumId", NS).get(q("val"))
            ab = sabs.get(aid)
            if ab is None:
                return f"list definition {aid} is missing in the source"
            na = max(used_abs | {-1}) + 1; used_abs.add(na)
            nn = max(used_num | {0}) + 1; used_num.add(nn)
            ab2 = copy.deepcopy(ab); ab2.set(q("abstractNumId"), str(na))
            for x in ab2.findall("w:nsid", NS) + ab2.findall("w:tmpl", NS):
                ab2.remove(x)
            first_num = droot.find("w:num", NS)
            (first_num.addprevious(ab2) if first_num is not None else droot.append(ab2))   # abstractNums come before nums
            dst.mark(ab2)
            num2 = copy.deepcopy(num); num2.set(q("numId"), str(nn))
            num2.find("w:abstractNumId", NS).set(q("val"), str(na))
            droot.append(num2); dst.mark(num2)
            remap[old] = str(nn)
        el.set(q("val"), remap[old])
    return ""


def op_provision(dst, src_path, names):
    """Copy Quick Parts from a source template into dst, with their pictures and styles.
    Never replaces: an entry with the same name+category+gallery stops the copy of that entry."""
    src = Package(src_path)
    sg = gloss_part(src)
    if not sg:
        raise Refused("The source template has no Quick Parts.")
    dg = _ensure_glossary(dst, src)
    dst.touch(dg)
    have = {(e["name"], e["category"], e["gallery"]) for e in entries(dst)}
    droot = dst.tree(dg)
    dparts = droot.find("w:docParts", NS)
    srels = src.rels_of(sg)
    grels = _rels_tree(dst, dg)
    # styles used by the entries, copied into the destination glossary styles if missing
    sstyles_part = next((v[1] for v in srels.values() if v[0].endswith("/styles")), None)
    dstyles_part = next((v[1] for v in dst.rels_of(dg).values() if v[0].endswith("/styles")), None)
    copied, skipped, media = [], [], []
    RNS = f"{{{R}}}"
    for n in names:
        e = find(src, n)
        key = (e["name"], e["category"], e["gallery"])
        if key in have:
            skipped.append((n, "name conflict"))
            continue
        dp = copy.deepcopy(e["el"])
        if dp.find(".//w:numPr", NS) is not None:      # 3.24.0: its list numbering comes along, renumbered
            why = _copy_numbering(src, sg, dst, dg, dp)
            if why:
                skipped.append((n, why))
                continue
        # every relationship the entry uses (r:id, r:embed, r:link ...) is copied and renumbered
        unsupported = None
        remap = {}
        for el in dp.iter():
            for attr, old in list(el.attrib.items()):
                if not attr.startswith(RNS):
                    continue
                if old not in remap:
                    if old not in srels:
                        unsupported = f"relationship {old} not found"; break
                    typ, tgt, mode = srels[old]
                    rid = _new_rid(grels)
                    rr = etree.SubElement(grels, f"{{{PR}}}Relationship")
                    rr.set("Id", rid); rr.set("Type", typ)
                    if mode == "External":
                        rr.set("Target", tgt); rr.set("TargetMode", "External")
                    elif typ.endswith("/image"):
                        ext = tgt.rsplit(".", 1)[-1]
                        k = 1
                        while dst.has(f"word/media/pe_qp{k}.{ext}"):
                            k += 1
                        mname = f"word/media/pe_qp{k}.{ext}"
                        dst.add_part(mname, src.raw[tgt], src.content_type("/" + tgt) or f"image/{ext}")
                        rr.set("Target", posixpath.relpath(mname, posixpath.dirname(dg)))
                        media.append(mname)
                    elif typ.endswith(("/header", "/footer")):
                        # 3.22.0: a part that carries its own section (a landscape or tabloid page) keeps its headers and
                        # footers: each is copied with the pictures it uses
                        rr.set("Target", posixpath.relpath(_copy_story(src, dst, tgt, typ.rsplit("/", 1)[-1], media),
                                                           posixpath.dirname(dg)))
                    else:
                        grels.remove(rr)
                        unsupported = f"embedded {typ.rsplit('/', 1)[-1]} part; not supported by provision yet"; break
                    remap[old] = rid
                el.set(attr, remap[old])
            if unsupported:
                break
        if unsupported:
            # take back any relationships added for this entry
            for rid in remap.values():
                for rr in grels.findall(f"{{{PR}}}Relationship"):
                    if rr.get("Id") == rid:
                        grels.remove(rr)
            skipped.append((n, unsupported))
            continue
        if sstyles_part and dstyles_part:
            ss, ds = src.tree(sstyles_part), dst.tree(dstyles_part)
            have_ids = {s_.get(q("styleId")) for s_ in ds.findall("w:style", NS)}
            by_id = {s_.get(q("styleId")): s_ for s_ in ss.findall("w:style", NS)}
            need = {el.get(q("val")) for el in dp.iter(q("pStyle"), q("rStyle"), q("tblStyle"))}
            todo = list(need)
            while todo:  # follow basedOn, next and link chains
                sid_ = todo.pop()
                st_ = by_id.get(sid_)
                if st_ is None or sid_ in have_ids:
                    continue
                dst.touch(dstyles_part)
                new_st = copy.deepcopy(st_)
                ds.append(new_st)
                dst.mark(new_st)
                have_ids.add(sid_)
                for tag in ("basedOn", "next", "link"):
                    x = st_.find(f"w:{tag}", NS)
                    if x is not None:
                        todo.append(x.get(q("val")))
        dparts.append(dp)
        dst.mark(dp)
        have.add(key)
        copied.append(n)
    return {"copied": copied, "skipped": skipped, "media": media}


GLOSS_ALLOWED = ("word/glossary/document.xml|*", "package|parts", "package|media")
