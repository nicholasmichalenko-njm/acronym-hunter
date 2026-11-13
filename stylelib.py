"""The Styles library (3.94.0; claude/stationkeeper-libraries-and-sets.md): every style the team keeps, each version
whole, in one place; style sets that group them by use (RFP volume, Page-limited RFP, RFI, Setup); bringing styles in
from a Word file (only styles: New, Already have it, Different from yours); a simple style made here.

A style version keeps Word's own definition of it ("_xml", exactly as the file had it) beside the readable values the
rows, previews and comparisons use; a version made here gets a definition written from its values. Nothing is
overwritten: different values are a new version under the same name. A set names the exact version it uses, one per
style; a newer version asks before a set moves to it. Kept in the template library (templatelib) on this PC, carried by
the Our data file. Rules only (No AI); nothing leaves the PC."""
import os
import re

from lxml import etree

import templatelib as TL

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
SET_COLORS = ("#3B82F6", "#F59E0B", "#14B8A6", "#EC4899", "#8B5CF6", "#22C55E", "#EF4444", "#64748B")
STATES = {"new": "New", "same": "Already have it", "variant": "Different from yours"}
# 4.30.1 (Nicholas 2026-11-13 14:30): what bringing each one in does, said on its row
DOES = {"new": "New: added to your library", "variant": "Same name, other values: added as a new version beside yours",
        "same": "Identical to yours: not added twice; it joins the set"}
LOOK = ("font", "size", "color", "bold", "italic", "underline", "hidden")


def _w(t):
    return f"{{{W}}}{t}"


# ------------------------------------------------------------------ reading a file's styles
def read_styles(path):
    """Every paragraph and character style in a Word file, only read: [{name, type, values, xml}] by name."""
    import prodlearn as PL
    from prodengine.engine.ops import word_ops as WO
    from prodengine.engine.pkg import Package
    raw = open(path, "rb").read()
    pkg = Package.from_bytes(raw, os.path.basename(path))
    defs = PL.learn_styles(pkg)
    xml = {}
    root = WO.styles_root(pkg)
    for s in root.findall("w:style", NS):
        n = s.find("w:name", NS)
        if n is not None:
            xml.setdefault(PL.shown_style_name(n.get(_w("val"))), etree.tostring(s, encoding="unicode"))
    return [{"name": k, "type": v.get("type", "paragraph"), "values": v, "xml": xml.get(k, "")} for k, v in sorted(defs.items())]


def against(lib, styles):
    """Each style read from a file against the library: state (new, same, variant), the version it matches or differs
    from, and whether it starts ticked. 4.30.1: every one does. A style identical to one you have is never added twice;
    ticked, it joins the set the import is for, so a set made from a document holds every style of that document."""
    out = []
    for s in styles:
        st, hit = lib.match("style", s["name"], s["values"])
        out.append(dict(s, state=st, words=DOES[st], mine=hit, keep=True))    # 4.30.1: one you have is ticked too, so it joins the set
    return out


def bring_in(lib, picks, path, set_of=None, tags=None, who=None):
    """Keeps the ticked styles: a new style, or a new version of one with other values; each into its set (set_of:
    {name: set id}). All or nothing. Returns {"new", "same", "variant"}."""
    counts = {"new": 0, "same": 0, "variant": 0}
    with lib.transaction():
        for p in picks:
            if not p.get("keep"):
                continue
            values = dict(p["values"], _xml=p.get("xml", ""), _from=os.path.basename(path))
            item, st = lib.add("style", p["name"], values, tags=tags, source=path, summary=TL._summary_style(p["values"]), who=who)
            counts[st] += 1
            sid = (set_of or {}).get(p["name"])
            if sid:
                add_to_set(lib, sid, [item["id"]])
    return counts


# ------------------------------------------------------------------ a style made here
def style_id(name):
    return re.sub(r"[^A-Za-z0-9]", "", name) or "Style"


def style_xml(name, v):
    """Word's definition of a style written from its values (for a style made here)."""
    typ = v.get("type", "paragraph")
    s = etree.Element(_w("style"), nsmap={"w": W})
    s.set(_w("type"), typ)
    s.set(_w("customStyle"), "1")
    s.set(_w("styleId"), style_id(name))
    etree.SubElement(s, _w("name")).set(_w("val"), name)
    if v.get("based_on"):
        etree.SubElement(s, _w("basedOn")).set(_w("val"), style_id(v["based_on"]))
    if typ == "paragraph" and v.get("next"):
        etree.SubElement(s, _w("next")).set(_w("val"), style_id(v["next"]))
    etree.SubElement(s, _w("qFormat"))
    if typ == "paragraph" and any(k in v for k in ("before", "after", "jc", "keep_next")):
        ppr = etree.SubElement(s, _w("pPr"))
        if v.get("keep_next"):
            etree.SubElement(ppr, _w("keepNext"))
        if "before" in v or "after" in v:
            sp = etree.SubElement(ppr, _w("spacing"))
            for k, a in (("before", "before"), ("after", "after")):
                if v.get(k) is not None:
                    sp.set(_w(a), str(int(round(float(v[k]) * 20))))
        if v.get("jc"):
            etree.SubElement(ppr, _w("jc")).set(_w("val"), v["jc"])
    rpr = etree.SubElement(s, _w("rPr"))
    if v.get("font"):
        rf = etree.SubElement(rpr, _w("rFonts"))
        for a in ("ascii", "hAnsi", "cs"):
            rf.set(_w(a), v["font"])
    for k, t in (("bold", "b"), ("italic", "i"), ("caps", "caps")):
        if v.get(k):
            etree.SubElement(rpr, _w(t))
    if v.get("underline"):
        etree.SubElement(rpr, _w("u")).set(_w("val"), "single")
    if v.get("hidden"):
        etree.SubElement(rpr, _w("vanish"))
    col = str(v.get("color") or "").lstrip("#").upper()
    if col and col != "AUTO":
        etree.SubElement(rpr, _w("color")).set(_w("val"), col)
    if v.get("size"):
        etree.SubElement(rpr, _w("sz")).set(_w("val"), str(int(round(float(v["size"]) * 2))))
    return etree.tostring(s, encoding="unicode")


def look_values(typ, look, marks=""):
    """A style's values from the simple look made here: font, size, color, bold, italic, underline, hidden."""
    v = {"type": "character" if typ == "character" else "paragraph"}
    for k in LOOK:
        x = look.get(k)
        if k in ("bold", "italic", "underline", "hidden"):
            v[k] = bool(x)
        elif x not in (None, ""):
            v[k] = float(x) if k == "size" else (str(x).lstrip("#").upper() if k == "color" else str(x))
    if v["type"] == "paragraph":
        v.setdefault("based_on", "Normal")
        for k in ("before", "after"):
            if look.get(k) not in (None, ""):
                v[k] = float(look[k])
    v["_made"] = "app"
    if marks:
        v["_marks"] = " ".join(str(marks).split())[:60]
    return v


def new_style(lib, name, typ, look, marks="", who=None):
    """A style made here (or, for a name the library has with other values, a new version of it). Returns (item, state)."""
    name = " ".join(str(name or "").split())[:80]
    if not name:
        return None, "no name"
    v = look_values(typ, look, marks)
    v["_xml"] = style_xml(name, v)
    return lib.add("style", name, v, source="", summary=TL._summary_style(v), who=who)


def change_style(lib, iid, look, marks=None, who=None):
    """A changed look saved as a new version (the version it came from stays). Returns (item, state)."""
    it = lib.get(iid)
    if it is None:
        return None, "missing"
    old = lib.values(it) or {}
    v = dict(old)
    v.update({k: x for k, x in look_values(old.get("type", "paragraph"), look, old.get("_marks", "") if marks is None else marks).items()
              if k in LOOK or k in ("_made", "_marks", "before", "after")})
    v["_xml"] = style_xml(lib.base_of(it), v)
    return lib.save_version(iid, v, who=who)


# ------------------------------------------------------------------ sets
def sets(lib, kind="style"):
    return [k for k in lib.kits if k.get("kind") == kind]


def new_set(lib, name, kind="style", color=None):
    """A new, empty set of this kind; its name must be free among them. Returns the set or None."""
    import uuid
    name = " ".join(str(name or "").split())[:60]
    if not name or any(k["name"].casefold() == name.casefold() for k in sets(lib, kind)):
        return None
    used = {k.get("color") for k in sets(lib, kind)}
    color = color or next((c for c in SET_COLORS if c not in used), SET_COLORS[len(used) % len(SET_COLORS)])
    k = {"id": uuid.uuid4().hex[:12], "name": name, "items": [], "tags": {}, "categories": {}, "at": TL._now(),
         "kind": kind, "color": color}
    lib.kits.append(k)
    lib.save()
    return k


def get_set(lib, sid):
    return lib.kit(sid)


def rename_set(lib, sid, name=None, color=None):
    k = lib.kit(sid)
    if k is None:
        return False
    if name:
        name = " ".join(str(name).split())[:60]
        if any(x is not k and x["name"].casefold() == name.casefold() for x in sets(lib, k.get("kind", "style"))):
            return False
        k["name"] = name
    if color:
        k["color"] = color
    lib.save()
    return True


def add_to_set(lib, sid, ids):
    """The versions go into the set; a set holds one version of a style, so another version of the same style comes out.
    Returns the ids it replaced."""
    k = lib.kit(sid)
    if k is None:
        return []
    gone = []
    for iid in ids:
        it = lib.get(iid)
        if it is None:
            continue
        for other in list(k["items"]):
            o = lib.get(other)
            if o is not None and other != iid and o.get("family") == it.get("family"):
                k["items"].remove(other); gone.append(other)
        if iid not in k["items"]:
            k["items"].append(iid)
    lib.save()
    return gone


def take_out(lib, sid, ids):
    k = lib.kit(sid)
    if k is None:
        return 0
    n = len(k["items"])
    k["items"] = [x for x in k["items"] if x not in set(ids)]
    lib.save()
    return n - len(k["items"])


def sets_of(lib, iid, kind="style"):
    """The sets that use this exact version."""
    return [k for k in sets(lib, kind) if iid in k["items"]]


def newer(lib, sid):
    """[(the version the set uses, the newest version)] for every style in the set with a newer version."""
    k = lib.kit(sid)
    out = []
    for iid in (k or {}).get("items", []):
        it = lib.get(iid)
        top = lib.latest(iid) if it else None
        if it is not None and top is not None and int(top.get("version") or 0) > int(it.get("version") or 0):
            out.append((it, top))
    return out


def move(lib, sid, old, new):
    """The set moves from one version to another of the same style."""
    k = lib.kit(sid)
    if k is None or old not in k["items"] or lib.get(new) is None:
        return False
    k["items"][k["items"].index(old)] = new
    lib.save()
    return True


def remove_set(lib, sid):
    return lib.remove_kit(sid)


# ------------------------------------------------------------------ the rows
def _n(x):
    try:
        return f"{float(x):g}"
    except (TypeError, ValueError):
        return str(x)


def color_word(col):
    import outlinexl as OX
    return OX.color_word(col)


def describe(v):
    """The row's words for a style: {font, paragraph, characters, other}."""
    font = " ".join(x for x in (str(v.get("font") or ""), f"{_n(v['size'])}" if v.get("size") else "") if x) or "As its base"
    if v.get("type") == "character":
        para = "Character style"
    else:
        bits = []
        if v.get("before") is not None or v.get("after") is not None:
            bits.append(f"{_n(v.get('before') or 0)} pt before, {_n(v.get('after') or 0)} after")
        if v.get("line"):
            bits.append(f"line {_n(v['line'])}")
        if v.get("keep_next"):
            bits.append("keep with next")
        if v.get("jc") and v["jc"] not in ("left", "start", "both"):
            bits.append({"center": "centered", "right": "right", "end": "right"}.get(v["jc"], v["jc"]))
        para = " · ".join(bits) or "As its base"
    ch = [w for k, w in (("bold", "Bold"), ("italic", "Italic"), ("underline", "Underline"), ("caps", "All caps")) if v.get(k)]
    col = str(v.get("color") or "AUTO").upper()
    ch.append("black" if col in ("AUTO", "") else color_word(col))
    if v.get("hidden"):
        ch.append("hidden")
    other = []
    if v.get("based_on"):
        other.append(f"Based on {v['based_on']}")
    if v.get("next") and v.get("next") != v.get("based_on"):
        other.append(f"Next: {v['next']}")
    if v.get("_marks"):
        other.insert(0, f"Marks {v['_marks']}")
    return {"font": font, "paragraph": para, "characters": " · ".join(ch), "other": " · ".join(other)}


def version_words(lib, it, v=None):
    v = v if v is not None else (lib.values(it) or {})
    ver = f"v{int(it.get('version') or 1)}" + (f" · {it['label']}" if it.get("label") else "")
    if v.get("_made") == "app":
        return ver + " · made in the app"
    src = v.get("_from") or it.get("source") or ""
    return ver + (f" · from {src}" if src else "")


def styles(lib, sid=None, words=""):
    """The rows: every style version (or a set's), by name, newest version first."""
    lib.fresh()
    keep = set((lib.kit(sid) or {}).get("items", [])) if sid else None
    q = (words or "").strip().casefold()
    out = [i for i in lib.items if i["kind"] == "style" and (keep is None or i["id"] in keep)
           and (not q or q in i["name"].casefold() or q in (i.get("summary") or "").casefold())]
    return sorted(out, key=lambda i: (lib.base_of(i).casefold(), -int(i.get("version") or 0)))


def rows(lib, sid=None, words="", shown=None):
    """One row per style (3.94.0, 19:16: the versions are tabs on the row): [{"family", "versions" (oldest first),
    "shown" (the version the row shows: the one picked, else the set's, else the newest)}]."""
    shown = shown or {}
    out, seen = [], set()
    for it in styles(lib, sid, words):
        fam = it.get("family") or it["id"]
        if fam in seen:
            continue
        seen.add(fam)
        vers = sorted((x for x in lib.items if x.get("family") == fam and x["kind"] == "style"), key=lambda x: int(x.get("version") or 0))
        pick = shown.get(fam)
        if pick not in [x["id"] for x in vers]:
            pick = it["id"]                 # styles() gives the set's version, or the newest, first
        out.append({"family": fam, "versions": vers, "shown": pick})
    return out


# ------------------------------------------------------------------ 4.30.1: review, change and duplicate a style on Styles
EDIT = LOOK + ("caps", "before", "after", "jc", "keep_next")      # what the style's own form on Styles sets
JC = (("", "As its base"), ("left", "Left"), ("center", "Centered"), ("right", "Right"), ("both", "Justified"))


def kind_of(v):
    return "character" if (v or {}).get("type") == "character" else "paragraph"


def _set_flag(parent, tag, on, val=None):
    for e in parent.findall(_w(tag)):
        parent.remove(e)
    if on:
        e = etree.SubElement(parent, _w(tag))
        if val is not None:
            e.set(_w("val"), val)


def patch_xml(xml, name, v):
    """Word's own definition of a style with only the values the form sets written into it; everything else it carries
    (numbering, tabs, borders, its base) stays as Word wrote it. name renames it (a duplicate). Returns the xml."""
    try:
        s = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    except (etree.XMLSyntaxError, AttributeError, ValueError):
        return style_xml(name, v)
    s.set(_w("styleId"), style_id(name))
    n = s.find(_w("name"))
    if n is None:
        n = etree.SubElement(s, _w("name")); s.insert(0, n)
    n.set(_w("val"), name)
    rpr = s.find(_w("rPr"))
    if rpr is None:
        rpr = etree.SubElement(s, _w("rPr"))
    for e in rpr.findall(_w("rFonts")):
        rpr.remove(e)
    if v.get("font"):
        rf = etree.SubElement(rpr, _w("rFonts"))
        for a in ("ascii", "hAnsi", "cs"):
            rf.set(_w(a), str(v["font"]))
    for k, t in (("bold", "b"), ("italic", "i"), ("caps", "caps"), ("hidden", "vanish")):
        _set_flag(rpr, t, bool(v.get(k)))
    _set_flag(rpr, "bCs", bool(v.get("bold"))); _set_flag(rpr, "iCs", bool(v.get("italic")))
    _set_flag(rpr, "u", bool(v.get("underline")), "single")
    col = str(v.get("color") or "").lstrip("#").upper()
    _set_flag(rpr, "color", bool(col and col != "AUTO"), col)
    sz = str(int(round(float(v["size"]) * 2))) if v.get("size") else None
    _set_flag(rpr, "sz", bool(sz), sz); _set_flag(rpr, "szCs", bool(sz), sz)
    if kind_of(v) == "paragraph":
        ppr = s.find(_w("pPr"))
        if ppr is None:
            ppr = etree.Element(_w("pPr")); rpr.addprevious(ppr)
        _set_flag(ppr, "keepNext", bool(v.get("keep_next")))
        sp = ppr.find(_w("spacing"))
        if v.get("before") is not None or v.get("after") is not None:
            if sp is None:
                sp = etree.SubElement(ppr, _w("spacing"))
            for k in ("before", "after"):
                if v.get(k) is not None:
                    sp.set(_w(k), str(int(round(float(v[k]) * 20))))
        _set_flag(ppr, "jc", bool(v.get("jc")), v.get("jc") or None)
    return etree.tostring(s, encoding="unicode")


def _edited(old, values):
    v = dict(old)
    for k in EDIT:
        if k not in values:
            continue
        x = values[k]
        if k in ("bold", "italic", "underline", "hidden", "caps", "keep_next"):
            v[k] = bool(x)
        elif x in (None, ""):
            v.pop(k, None)
        elif k in ("size", "before", "after"):
            v[k] = float(x)
        else:
            v[k] = str(x).lstrip("#").upper() if k == "color" else str(x)
    if kind_of(v) == "character":
        for k in ("before", "after", "jc", "keep_next"):
            v.pop(k, None)
    return v


def _xml_for(name, old, v):
    return patch_xml(old["_xml"], name, v) if old.get("_xml") and old.get("_made") != "app" else style_xml(name, v)


def save_edit(lib, iid, values, who=None):
    """The style's form saved: a new version with the values it sets (font, size, color, bold, italic, underline, all
    caps, hidden; for a paragraph style its alignment, space before and after, keep with next). The version it came from
    stays. A style brought in from Word keeps everything else Word wrote. Returns (item, state)."""
    it = lib.get(iid)
    if it is None:
        return None, "missing"
    old = lib.values(it) or {}
    v = _edited(old, values)
    v["_xml"] = _xml_for(lib.base_of(it), old, v)
    return lib.save_version(iid, v, who=who)


def duplicate(lib, iid, name, values=None, who=None):
    """A new style under its own name with every value of this one (4.30.1). values: changes to make on the way.
    Returns (item, state): state "taken" when the library has a style of that name."""
    it = lib.get(iid)
    name = " ".join(str(name or "").split())[:80]
    if it is None or not name:
        return None, "no name"
    if any(i["kind"] == "style" and lib.base_of(i).casefold() == name.casefold() for i in lib.items):
        return None, "taken"
    old = lib.values(it) or {}
    v = _edited(old, values or {})
    v["_xml"] = _xml_for(name, old, v)
    v["_copy_of"] = lib.base_of(it)
    return lib.add("style", name, v, source="", summary=TL._summary_style(v), who=who)
