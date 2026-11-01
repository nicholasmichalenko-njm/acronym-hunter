"""Word table styles (3.10.0): the table styles a profile carries whole (borders, shading, the header row, banding,
the first column, every conditional part), kept as the style's own XML by name.

  std["table_styles"] = {name: {"xml": "<w:style w:type='table' ...>", "based_on": name or ""}}
  std["table_types"][key]["word_style"] = name     a table type's tables use this Word table style

capture(pkg)                  {name: entry} for the table styles the file uses or defines (not Word's Normal Table)
differences(pkg, std)         [(name, "not in the file" | "differs")], compared without Word's revision ids
op_table_styles(pkg, std)     each style of the profile written by name (replaced when it differs, added when missing);
                              a style that already matches is left alone, so a second run changes nothing
"""
import copy as _copy
import re

from lxml import etree
from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q
from prodengine.engine.ops.word_ops import find_style, norm, styles_root

W = NS["w"]
TABLE_STYLES_ALLOWED = ()          # styles.xml is not a story part
SKIP = {"normal table", "table normal"}


def _name(s):
    n = s.find("w:name", NS)
    return n.get(q("val")) if n is not None else ""


def _clean(el):
    """A copy without what Word changes on its own (revision ids) and without its own id and base (kept by name)."""
    e = _copy.deepcopy(el)
    for x in e.iter():
        for a in list(x.attrib):
            if a.endswith("}rsid") or "rsid" in a.split("}")[-1].lower():
                del x.attrib[a]
    for tag in ("rsid",):
        for x in e.findall(f"w:{tag}", NS):
            e.remove(x)
    e.attrib.pop(q("styleId"), None)
    for tag in ("basedOn", "next", "link"):
        for x in e.findall(f"w:{tag}", NS):
            e.remove(x)
    return e


def _sig(el):
    return etree.tostring(_clean(el), method="c14n")


def capture(pkg):
    root = styles_root(pkg)
    used = set()
    for story in pkg.stories():
        for el in pkg.tree(story).iter(q("tblStyle")):
            used.add(el.get(q("val")))
    by_id = {s.get(q("styleId")): s for s in root.findall("w:style", NS)}
    out = {}
    for s in root.findall("w:style", NS):
        if s.get(q("type")) != "table":
            continue
        name = _name(s)
        if not name or norm(name) in SKIP:
            continue
        if not (s.get(q("styleId")) in used or s.get(q("customStyle")) in ("1", "true")):
            continue
        b = s.find("w:basedOn", NS)
        base = _name(by_id[b.get(q("val"))]) if b is not None and b.get(q("val")) in by_id else ""
        out[name] = {"xml": etree.tostring(_clean(s), encoding="unicode"), "based_on": base}
    return out


def differences(pkg, std):
    want = std.get("table_styles") or {}
    if not want:
        return []
    root = styles_root(pkg)
    out = []
    for name, entry in want.items():
        s = find_style(root, name)
        if s is None:
            out.append((name, "not in the file"))
            continue
        try:
            new = etree.fromstring(entry["xml"])
        except (etree.XMLSyntaxError, KeyError, TypeError):
            continue
        if _sig(s) != _sig(new):
            out.append((name, "differs"))
    return out


def op_table_styles(pkg, std):
    want = std.get("table_styles") or {}
    root = styles_root(pkg)
    changed, added = [], []
    ids = {s.get(q("styleId")) for s in root.findall("w:style", NS)}
    for name, entry in want.items():
        try:
            new = etree.fromstring(entry["xml"])
        except (etree.XMLSyntaxError, KeyError, TypeError):
            raise ValueError(f"the table style {name} in the standard is not readable")
        if new.get(q("type")) != "table":
            raise ValueError(f"{name} in the standard is not a table style")
        cur = find_style(root, name)
        if cur is not None and _sig(cur) == _sig(new):
            continue
        if cur is not None:
            sid = cur.get(q("styleId"))
        else:
            sid = re.sub(r"[^A-Za-z0-9]", "", name) or "TableStyle"
            base, i = sid, 1
            while sid in ids:
                i += 1
                sid = f"{base}{i}"
            ids.add(sid)
        new.set(q("styleId"), sid)
        if entry.get("based_on"):
            b = find_style(root, entry["based_on"])
            if b is not None:
                el = etree.Element(q("basedOn")); el.set(q("val"), b.get(q("styleId")))
                nm = new.find("w:name", NS)
                (nm.addnext(el) if nm is not None else new.insert(0, el))
        if cur is not None:
            pkg.mark(cur)
            cur.addprevious(new)
            root.remove(cur)
            changed.append(name)
        else:
            root.append(new)
            added.append(name)
        pkg.mark(new)
    return {"changed": changed, "added": added, "checks": [{"expr": f"doc.Styles({n!r}).Type", "expect": 3} for n in changed + added]}


def style_id(pkg, name):
    s = find_style(styles_root(pkg), name)
    return s.get(q("styleId")) if s is not None and s.get(q("type")) == "table" else None
