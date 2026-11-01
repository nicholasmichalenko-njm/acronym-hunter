"""List numbering definitions (3.9.0): the bullets and numbers each list style shows, level by level, as the team's
template defines them: the bullet character (and its font) or the number format and text, and where the number and
the text sit. The standard holds them as std["list_numbering"]:

  {"on": bool, "lists": [{"name": "Bullets", "levels": [{"style": "List Bullet", "fmt": "bullet", "text": "•",
                                                         "font": "", "left": 0.25, "hanging": 0.25}, ...]},
                         {"name": "Numbers", "levels": [{"style": "List Number", "fmt": "decimal", "text": "%1.", ...}]}]}

read_levels(pkg, styles)      what each list style shows now: {style: {fmt, text, font, left, hanging}} (inches)
differences(pkg, std)         [(style, what differs)]: the comparison is by what shows, not by how the file
                              stores it (one multilevel list or one list per style read the same)
op_list_numbering(pkg, std)   one multilevel list per list of the standard, each level linked to its style (styles
                              made when missing); styles that already show their level are left alone, so a second
                              run changes nothing
"""
import random

from lxml import etree
from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q, ensure, remove
from prodengine.engine.ops.word_ops import find_style, new_style, styles_root

TW = 1440.0
FORMATS = ("bullet", "decimal", "lowerLetter", "upperLetter", "lowerRoman", "upperRoman", "decimalZero")
LIST_ALLOWED = ()          # styles.xml and numbering.xml are not story parts: no story facet may change


def _numbering_root(pkg):
    part = pkg.word_part("/numbering")
    return part, (pkg.tree(part) if part else None)


def _level_of(nb, num_id, ilvl):
    num = next((n for n in nb.findall("w:num", NS) if n.get(q("numId")) == str(num_id)), None)
    if num is None or num.find("w:abstractNumId", NS) is None:
        return None
    ov = num.find(f"w:lvlOverride[@w:ilvl='{ilvl}']/w:lvl", NS)
    if ov is not None:
        return ov
    aid = num.find("w:abstractNumId", NS).get(q("val"))
    a = next((x for x in nb.findall("w:abstractNum", NS) if x.get(q("abstractNumId")) == aid), None)
    if a is None:
        return None
    link = a.find("w:numStyleLink", NS)
    if link is not None:                    # a list style: follow it to the list that defines the levels
        return None
    return next((l for l in a.findall("w:lvl", NS) if l.get(q("ilvl")) == str(ilvl)), None)


def _style_numpr(sroot, s):
    by_id = {x.get(q("styleId")): x for x in sroot.findall("w:style", NS)}
    seen = set()
    while s is not None and id(s) not in seen:
        seen.add(id(s))
        np_ = s.find("w:pPr/w:numPr", NS)
        if np_ is not None and np_.find("w:numId", NS) is not None:
            il = np_.find("w:ilvl", NS)
            return np_.find("w:numId", NS).get(q("val")), int(il.get(q("val"))) if il is not None else 0
        b = s.find("w:basedOn", NS)
        s = by_id.get(b.get(q("val"))) if b is not None else None
    return None, 0


def describe(lvl):
    f = lvl.find("w:numFmt", NS)
    t = lvl.find("w:lvlText", NS)
    ind = lvl.find("w:pPr/w:ind", NS)
    rf = lvl.find("w:rPr/w:rFonts", NS)
    left = int((ind.get(q("left")) or ind.get(q("start")) or "0")) / TW if ind is not None else 0.0
    hang = int(ind.get(q("hanging")) or "0") / TW if ind is not None else 0.0
    return {"fmt": f.get(q("val")) if f is not None else "decimal", "text": t.get(q("val")) if t is not None else "",
            "font": (rf.get(q("ascii")) or "") if rf is not None else "", "left": round(left, 3), "hanging": round(hang, 3)}


def read_levels(pkg, styles, strict=False):
    """{style: level description} for each style that is in the file and shows a list level. strict: only levels
    that name the style themselves (a style borrowing another list's level, such as a heading's, is left out)."""
    sroot = styles_root(pkg)
    _p, nb = _numbering_root(pkg)
    out = {}
    if nb is None:
        return out
    for name in styles:
        s = find_style(sroot, name)
        if s is None:
            continue
        nid, ilvl = _style_numpr(sroot, s)
        if not nid or nid == "0":
            continue
        lvl = _level_of(nb, nid, ilvl)
        if lvl is not None:
            ps = lvl.find("w:pStyle", NS)
            if strict and ps is not None and ps.get(q("val")) != s.get(q("styleId")):
                continue
            out[name] = describe(lvl)
    return out


def _same(have, want):
    if have is None:
        return False
    for k in ("fmt", "text"):
        if str(have.get(k, "")) != str(want.get(k, "")):
            return False
    if (want.get("font") or "") and str(have.get("font", "")).lower() != str(want["font"]).lower():
        return False
    return all(abs(float(have.get(k, 0)) - float(want.get(k) or 0)) < 0.01 for k in ("left", "hanging"))


def differences(pkg, std):
    ln = std.get("list_numbering") or {}
    if not ln.get("on"):
        return []
    out = []
    for lst in ln.get("lists") or []:
        cur = read_levels(pkg, [lv["style"] for lv in lst.get("levels") or []])
        for lv in lst.get("levels") or []:
            have = cur.get(lv["style"])
            if not _same(have, lv):
                what = "no list numbering" if have is None else ", ".join(
                    f"{k} {have.get(k)!r} (standard {lv.get(k)!r})" for k in ("fmt", "text", "font", "left", "hanging")
                    if (k != "font" or lv.get("font")) and str(have.get(k)) != str(lv.get(k)) and
                    not (k in ("left", "hanging") and abs(float(have.get(k, 0)) - float(lv.get(k) or 0)) < 0.01))
                out.append((lv["style"], what))
    return out


def _abstract(sroot, levels, nsid, aid):
    a = etree.Element(q("abstractNum")); a.set(q("abstractNumId"), str(aid))
    ensure(a, "nsid", {"val": nsid}); ensure(a, "multiLevelType", {"val": "multilevel" if len(levels) > 1 else "singleLevel"})
    for ilvl, lv in enumerate(levels):
        st = find_style(sroot, lv["style"])
        l = etree.SubElement(a, q("lvl")); l.set(q("ilvl"), str(ilvl))
        ensure(l, "start", {"val": 1})
        ensure(l, "numFmt", {"val": lv.get("fmt") or "decimal"})
        ensure(l, "pStyle", {"val": st.get(q("styleId"))})
        ensure(l, "lvlText", {"val": lv.get("text") or ""})
        ensure(l, "lvlJc", {"val": "left"})
        ppr = ensure(l, "pPr")
        left, hang = float(lv.get("left") or 0), float(lv.get("hanging") or 0)
        tabs = ensure(ppr, "tabs")
        t = etree.SubElement(tabs, q("tab")); t.set(q("val"), "num"); t.set(q("pos"), str(int(round(left * TW))))
        ensure(ppr, "ind", {"left": int(round(left * TW)), "hanging": int(round(hang * TW))})
        if lv.get("font"):
            rpr = ensure(l, "rPr")
            rf = ensure(rpr, "rFonts")
            for k in ("ascii", "hAnsi"):
                rf.set(q(k), lv["font"])
            rf.set(q("hint"), "default")
    return a


def op_list_numbering(pkg, std):
    ln = std.get("list_numbering") or {}
    if not ln.get("on"):
        return {"unchanged": "list numbering is not set in the standard", "checks": []}
    sroot = styles_root(pkg)
    part, nb = _numbering_root(pkg)
    if nb is None:
        raise ValueError("the file has no numbering part")
    pkg.touch(part)
    made, lists_built, checks = [], 0, []
    for lst in ln.get("lists") or []:
        levels = [lv for lv in (lst.get("levels") or []) if lv.get("style")]
        if not levels:
            continue
        cur = read_levels(pkg, [lv["style"] for lv in levels])
        if all(_same(cur.get(lv["style"]), lv) for lv in levels):
            continue
        for lv in levels:
            if find_style(sroot, lv["style"]) is None:
                s = new_style(sroot, lv["style"], "paragraph", "Normal")
                pkg.mark(s)
                made.append(lv["style"])
        abs_ids = [int(a.get(q("abstractNumId"))) for a in nb.findall("w:abstractNum", NS)]
        num_ids = [int(n.get(q("numId"))) for n in nb.findall("w:num", NS)]
        nsids = {a.find("w:nsid", NS).get(q("val")) for a in nb.findall("w:abstractNum", NS) if a.find("w:nsid", NS) is not None}
        aid, nid = max(abs_ids + [-1]) + 1, max(num_ids + [0]) + 1
        rnd = random.Random()
        nsid = "%08X" % rnd.getrandbits(32)
        while nsid in nsids:
            nsid = "%08X" % rnd.getrandbits(32)
        a = _abstract(sroot, levels, nsid, aid)
        first_num = nb.find("w:num", NS)
        if first_num is not None:
            first_num.addprevious(a)
        else:
            nb.append(a)
        n = etree.SubElement(nb, q("num")); n.set(q("numId"), str(nid))
        an = etree.SubElement(n, q("abstractNumId")); an.set(q("val"), str(aid))
        pkg.mark(a); pkg.mark(n)
        for ilvl, lv in enumerate(levels):
            st = find_style(sroot, lv["style"])
            pkg.mark(st)
            sppr = ensure(st, "pPr")
            numpr = ensure(sppr, "numPr")
            for ch in list(numpr):
                numpr.remove(ch)
            il = etree.SubElement(numpr, q("ilvl")); il.set(q("val"), str(ilvl))
            ni = etree.SubElement(numpr, q("numId")); ni.set(q("val"), str(nid))
            remove(sppr, "ind")                       # the list level owns the positions
            checks.append({"expr": f"doc.Styles({lv['style']!r}).ListTemplate.ListLevels({ilvl + 1}).NumberFormat",
                           "expect": lv.get("text", "")})
        lists_built += 1
    return {"lists": lists_built, "styles_made": made, "checks": checks}


def learn(pkg, std):
    """The list numbering the file's list styles show, as the standard's lists (bullets, numbers), or None."""
    lists_std = std.get("lists") or {}
    out = []
    for name, styles in (("Bullets", lists_std.get("bullet_styles") or []), ("Numbers", lists_std.get("number_styles") or [])):
        cur = read_levels(pkg, styles, strict=True)
        levels = [dict(cur[s], style=s) for s in styles if s in cur]
        if levels:
            out.append({"name": name, "levels": levels})
    return {"on": True, "lists": out} if out else None
