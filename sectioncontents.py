"""What each document section holds (3.45.0): an ordered list of components at the start of the section, kept in the
standard: std["section_contents"][section key] = [item]. An item is
  {"kind": "element", "id": a response element (toc, lof, lot, loa, acr, uom, matrix, exec), "title": its heading}
  {"kind": "quickpart", "name": one of the standard's Quick Parts}
  {"kind": "placeholder", "title": a heading, "pages": the pages authors fill}
Make templates writes them at the start of the section's first Word section (op_section_contents), marked with a
bookmark so a second run leaves them alone; the setup written on the template keeps them (front matter and appendices
are written again after the setup replaces those pages). Cover, title page and back cover are kept pages: they hold
no components. Rules only."""
import copy
import re

from lxml import etree

KINDS = (("element", "Response element"), ("quickpart", "Quick Part"), ("placeholder", "Placeholder for authors"))
NO_CONTENTS = ("cover", "title", "backer")
ALLOWED = ("text", "text_len", "paragraphs", "tables", "pstyles", "para_format", "table_format", "direct_run_format",
           "fields", "bookmarks", "bookmark_context", "section_count")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def items(std, key):
    return [dict(x) for x in ((std or {}).get("section_contents") or {}).get(key) or [] if isinstance(x, dict)]


def set_items(work, key, rows):
    sc = work.setdefault("section_contents", {})
    rows = [clean(r) for r in rows or []]
    rows = [r for r in rows if r]
    if rows:
        sc[key] = rows
    else:
        sc.pop(key, None)
    return rows


def clean(r):
    k = (r or {}).get("kind")
    if k == "element" and r.get("id"):
        return {"kind": k, "id": str(r["id"]), "title": " ".join(str(r.get("title") or "").split())}
    if k == "quickpart" and str(r.get("name") or "").strip():
        return {"kind": k, "name": " ".join(str(r["name"]).split())}
    if k == "placeholder" and str(r.get("title") or "").strip():
        try:
            pages = max(1, int(r.get("pages") or 1))
        except (TypeError, ValueError):
            pages = 1
        return {"kind": k, "title": " ".join(str(r["title"]).split()), "pages": pages}
    return None


def label(r, data=None):
    """An item in plain words."""
    if r["kind"] == "element":
        import responseelements as RE
        e = RE.get(data or RE.builtins(), r["id"]) or {}
        return f"{r.get('title') or e.get('name') or r['id']} (element)"
    if r["kind"] == "quickpart":
        return f"{r['name']} (Quick Part)"
    return f"{r['title']} ({r['pages']} page{'s' if r['pages'] != 1 else ''} for authors)"


def render(std, key, ctx=None):
    """The Word content of a section's components, in order (body XML)."""
    import elementbuild as EB
    ctx = dict(ctx or {}, std=std)
    out = []
    for r in items(std, key):
        r = clean(r)
        if not r:
            continue
        if r["kind"] == "element":
            out.append(EB.element_xml({"element": r["id"], "title": r.get("title") or ""}, ctx))
        elif r["kind"] == "quickpart":
            out.append(EB.quickpart_xml(r["name"]))
        else:
            out.append(EB.placeholder_xml(r["title"], 1, r["pages"]))
    return "".join(out)


def bookmark(key):
    return "SK_Section_" + re.sub(r"[^A-Za-z0-9]", "_", key)[:30]


def _frag(xml):
    return list(etree.fromstring(f'<w:body xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                                 f'{xml}</w:body>'))


def mark(els, key, bid=9100):
    """Bookmark the first and last paragraph of the inserted content, so a second run finds it."""
    paras = [e for e in els if e.tag == f"{{{W}}}p"]
    if not paras:
        return els
    bs = etree.Element(f"{{{W}}}bookmarkStart"); bs.set(f"{{{W}}}id", str(bid)); bs.set(f"{{{W}}}name", bookmark(key))
    be = etree.Element(f"{{{W}}}bookmarkEnd"); be.set(f"{{{W}}}id", str(bid))
    first, last = paras[0], paras[-1]
    ppr = first.find(f"{{{W}}}pPr")
    (ppr.addnext(bs) if ppr is not None else first.insert(0, bs))
    last.append(be)
    return els


def has_mark(root, key):
    name = bookmark(key)
    return any(b.get(f"{{{W}}}name") == name for b in root.iter(f"{{{W}}}bookmarkStart"))


def op_section_contents(pkg, std, ctx=None):
    """Each section's components at the start of its first Word section (once; a marked section is left alone)."""
    from prodengine.pe import sections as S
    if not (std.get("section_contents") or {}):
        return {"placed": [], "checks": []}
    pkg.touch(pkg.main)
    root = pkg.tree(pkg.main)
    sm = S.map_sections(pkg, std)
    blocks = S._body_blocks(pkg)
    placed, seen, bid, fields = [], set(), 9100, []
    for s in sm.sections:
        key = s.part
        if key in seen:
            continue
        seen.add(key)
        if key in NO_CONTENTS or not items(std, key) or has_mark(root, key):
            continue
        els = blocks[s.i][2] if s.i < len(blocks) else []
        anchor = next((e for e in els), None)
        xml = render(std, key, ctx)
        if not xml or anchor is None:
            continue
        new = mark(_frag(xml), key, bid)
        bid += 1
        for e in new:
            anchor.addprevious(e)
            pkg.mark(e)
            for it in e.iter(f"{{{W}}}instrText"):           # the fields it brings, declared to the guarded write
                ins = " ".join((it.text or "").split())
                if ins:
                    fields.append((pkg.main, None, ins))
        placed.append(key)
    return {"placed": placed, "checks": [], "field_changes": fields}


def for_setup(std, ctx=None):
    """3.45.0: {section key: marked XML} for the setup written on the template (front matter and appendices are written
    again there)."""
    out = {}
    for key in ("front", "appendix"):
        xml = render(std, key, ctx)
        if xml:
            out[key] = "".join(etree.tostring(e, encoding="unicode") for e in mark(_frag(xml), key, 9200 + len(out)))
    return out


def copy_items(work, frm, to):
    set_items(work, to, copy.deepcopy(items(work, frm)))
