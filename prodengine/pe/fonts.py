"""Font compliance: the RFP's minimum sizes and named fonts (FontRules), checked on the font and size every run of
text actually shows, and where that value comes from.

scan(pkg, std)  -> [RunFont]    read only
audit(runs, std)-> [Finding]    area "fonts"
op_fonts(pkg, std)        Fix all: removes hand formatting (direct font and size) that breaks a rule, where the
                          style underneath complies; the text then shows its style's font and size. Formatting only.
op_font_styles(pkg, std, names)   for review: sets a style that breaks a rule to the scope's first permitted font
                          and minimum size

Resolution order (as Word applies it): document defaults < table style < paragraph style chain < character style
chain < direct run formatting. Theme fonts (+Body, +Headings) resolve through the theme part.

Scopes: body, table, caption, header_footer, footnote, graphic (text boxes). A blank rule value is not examined
(v1.43). Skipped: hidden text, field codes, deleted text, symbol fonts, equations, empty runs.
"""
import re
from dataclasses import dataclass

from lxml import etree
from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q, local, ensure, remove
from prodengine.pe.sections import canon_style

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
SYMBOL_FONTS = {"symbol", "wingdings", "wingdings 2", "wingdings 3", "webdings", "marlett", "mt extra"}
SCOPES = ("body", "heading", "table", "caption", "header_footer", "footnote", "graphic")
SCOPE_LABEL = {"body": "Body", "heading": "Headings", "table": "Table", "caption": "Caption",
               "header_footer": "Header and footer", "footnote": "Footnote", "graphic": "Graphic text"}
HEADING_STYLES = {f"Heading {k}" for k in range(1, 10)} | {"Title", "Subtitle", "TOC Heading"}


@dataclass
class RunFont:
    story: str
    para: int
    scope: str
    font: str
    size: float
    font_src: str          # direct | char:<style> | para:<style> | table:<style> | default
    size_src: str
    chars: int
    style: str             # paragraph style name
    el: object = None
    under_font: str = ""   # what the run shows without its direct formatting
    under_size: float = 0


def _theme_fonts(pkg):
    t = pkg.word_part("/theme")
    out = {"minor": "Calibri", "major": "Calibri Light"}
    if t:
        root = pkg.tree(t)
        for kind in ("minor", "major"):
            el = root.find(f".//{{{A}}}{kind}Font/{{{A}}}latin")
            if el is not None and el.get("typeface"):
                out[kind] = el.get("typeface")
    return out


def _font_of(rpr, theme):
    if rpr is None:
        return None
    rf = rpr.find("w:rFonts", NS)
    if rf is None:
        return None
    if rf.get(q("ascii")):
        return rf.get(q("ascii"))
    th = rf.get(q("asciiTheme"))
    if th:
        return theme["major" if th.startswith("major") else "minor"]
    return None


def _size_of(rpr):
    if rpr is None:
        return None
    sz = rpr.find("w:sz", NS)
    return int(sz.get(q("val"))) / 2 if sz is not None and sz.get(q("val")) else None


class Styles:
    def __init__(self, pkg):
        self.theme = _theme_fonts(pkg)
        sp = pkg.word_part("/styles")
        self.root = pkg.tree(sp)
        self.by_id = {s.get(q("styleId")): s for s in self.root.findall("w:style", NS)}
        self.name = {k: canon_style(s.find("w:name", NS).get(q("val"))) for k, s in self.by_id.items()
                     if s.find("w:name", NS) is not None}
        dd = self.root.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
        self.default_font = _font_of(dd, self.theme) or self.theme["minor"]
        self.default_size = _size_of(dd) or 10.0
        self.default_para = next((k for k, s in self.by_id.items() if s.get(q("type")) == "paragraph"
                                  and s.get(q("default")) in ("1", "true")), "Normal")
        self._cache = {}

    def chain(self, sid):
        out, seen = [], set()
        while sid and sid in self.by_id and sid not in seen:
            seen.add(sid)
            out.append(sid)
            b = self.by_id[sid].find("w:basedOn", NS)
            sid = b.get(q("val")) if b is not None else None
        return out

    def resolved(self, sid):
        """(font, font source style id, size, size source style id) from a style chain, or Nones."""
        if sid in self._cache:
            return self._cache[sid]
        f = fs = s = ss = None
        for k in self.chain(sid):
            rpr = self.by_id[k].find("w:rPr", NS)
            if f is None and _font_of(rpr, self.theme):
                f, fs = _font_of(rpr, self.theme), k
            if s is None and _size_of(rpr):
                s, ss = _size_of(rpr), k
        self._cache[sid] = (f, fs, s, ss)
        return self._cache[sid]


def _scope(part_kind, p, style_name, std):
    if part_kind in ("hdr", "ftr"):
        return "header_footer"
    if part_kind in ("footnotes", "endnotes"):
        return "footnote"
    if next(p.iterancestors(q("txbxContent")), None) is not None:
        return "graphic"
    if style_name in std["fonts"].get("caption_styles", ("Caption",)) or style_name.startswith(("PE Table Caption", "PE Figure Caption")):
        return "caption"
    if next(p.iterancestors(q("tbl")), None) is not None:
        return "table"
    if style_name in HEADING_STYLES:
        return "heading"       # RFPs usually rule body text; a heading rule is set only when the RFP has one
    return "body"


def scan(pkg, std):
    S = Styles(pkg)
    out = []
    for story in pkg.stories():
        root = pkg.tree(story)
        kind = local(root)
        if kind in ("comments", "glossaryDocument"):
            continue
        for pi, p in enumerate(root.iter(q("p"))):
            ps = p.find("w:pPr/w:pStyle", NS)
            psid = ps.get(q("val")) if ps is not None else S.default_para
            pname = S.name.get(psid, psid)
            tbl = next(p.iterancestors(q("tbl")), None)
            tsid = None
            if tbl is not None:
                ts = tbl.find("w:tblPr/w:tblStyle", NS)
                tsid = ts.get(q("val")) if ts is not None else None
            pf, pfs, psz, pszs = S.resolved(psid)
            tf, tfs, tsz, tszs = S.resolved(tsid) if tsid else (None, None, None, None)
            scope = _scope(kind, p, pname, std)
            depth = 0
            for r in p.iter(q("r")):
                if next(r.iterancestors(q("p")), None) is not p:
                    continue                                   # a text box paragraph is its own paragraph
                fc = r.find("w:fldChar", NS)
                if fc is not None:
                    t = fc.get(q("fldCharType"))
                    depth += {"begin": 1, "end": -1}.get(t, 0)
                    continue
                if r.find("w:instrText", NS) is not None:
                    continue
                if next(r.iterancestors(q("del")), None) is not None:
                    continue
                text = "".join(t.text or "" for t in r.findall("w:t", NS))
                if not text.strip() or r.find("w:sym", NS) is not None:
                    continue
                rpr = r.find("w:rPr", NS)
                if rpr is not None and rpr.find("w:vanish", NS) is not None and rpr.find("w:vanish", NS).get(q("val"), "1") not in ("0", "false"):
                    continue
                rs = rpr.find("w:rStyle", NS) if rpr is not None else None
                rsid = rs.get(q("val")) if rs is not None else None
                cf, cfs, csz, cszs = S.resolved(rsid) if rsid else (None, None, None, None)
                df, dsz = _font_of(rpr, S.theme), _size_of(rpr)
                font, fsrc = next(((v, s) for v, s in ((df, "direct"), (cf, f"char:{S.name.get(cfs, cfs)}"),
                                                       (pf, f"para:{S.name.get(pfs, pfs)}"), (tf, f"table:{S.name.get(tfs, tfs)}"))
                                   if v), (S.default_font, "default"))
                size, ssrc = next(((v, s) for v, s in ((dsz, "direct"), (csz, f"char:{S.name.get(cszs, cszs)}"),
                                                       (psz, f"para:{S.name.get(pszs, pszs)}"), (tsz, f"table:{S.name.get(tszs, tszs)}"))
                                   if v), (S.default_size, "default"))
                if font.lower() in SYMBOL_FONTS:
                    continue
                uf = next((v for v in (cf, pf, tf) if v), S.default_font)
                us = next((v for v in (csz, psz, tsz) if v), S.default_size)
                out.append(RunFont(story, pi, scope, font, size, fsrc, ssrc, len(text), pname, r, uf, us))
    return out


def _rule(std, scope):
    return std["fonts"].get(scope) or {}


def audit(runs, std):
    from prodengine.pe.docmap import Finding
    groups = {}
    for rf in runs:
        rule = _rule(std, rf.scope)
        fonts = rule.get("fonts")
        mn = rule.get("min_size")
        if fonts and rf.font not in fonts:
            groups.setdefault(("F1", rf.scope, rf.font, rf.font_src), []).append(rf)
        if mn and rf.size < mn:
            groups.setdefault(("F2", rf.scope, rf.size, rf.size_src), []).append(rf)
    out = []
    for (rule, scope, val, src), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], str(kv[0][2]))):
        r0 = _rule(std, scope)
        n, chars = len({(x.story, x.para) for x in rs}), sum(x.chars for x in rs)
        where = "hand formatting" if src == "direct" else ("the style " + src.split(":", 1)[1] if ":" in src else "the document default")
        if rule == "F1":
            what = f"{SCOPE_LABEL[scope]}: {n} paragraph{'s' if n > 1 else ''} ({chars:,} characters) in {val}, from {where}; " \
                   f"the RFP permits {', '.join(r0['fonts'])}"
        else:
            what = f"{SCOPE_LABEL[scope]}: {n} paragraph{'s' if n > 1 else ''} ({chars:,} characters) at {val:g} pt, from {where}; " \
                   f"the RFP minimum is {r0['min_size']:g} pt"
        if src == "direct":
            fix = "op_fonts" if _style_ok(rs, std, rule) else "op_font_styles"
        elif src.startswith(("para:", "char:", "table:")):
            fix = "op_font_styles"
        else:
            fix = ""
        out.append(Finding("fonts", "error", rule if src == "direct" else rule + "s", what, rs[0].para, fix,
                           f"{rule}:{scope}:{val}:{src}"))
    return out


def _style_ok(rs, std, rule):
    """After removing the hand formatting, would every run comply? (the next source down the chain)"""
    r0 = _rule(std, rs[0].scope)
    if rule == "F1":
        return all(x.under_font in r0["fonts"] for x in rs)
    return all(x.under_size >= r0["min_size"] for x in rs)


# ---------------------------------------------------------------- fixes
FONTS_ALLOWED = ()


def op_fonts(pkg, std):
    """Remove direct font or size where it breaks a rule and the style underneath complies."""
    runs = scan(pkg, std)
    changed = 0
    for rf in runs:
        rule = _rule(std, rf.scope)
        rpr = rf.el.find("w:rPr", NS)
        if rpr is None:
            continue
        under_f, under_s = rf.under_font, rf.under_size
        touched = False
        if rf.font_src == "direct" and rule.get("fonts") and rf.font not in rule["fonts"] and under_f in rule["fonts"]:
            rfonts = rpr.find("w:rFonts", NS)
            for a in ("ascii", "hAnsi", "asciiTheme", "hAnsiTheme", "cs", "cstheme"):
                if rfonts.get(q(a)) is not None:
                    del rfonts.attrib[q(a)]
            if not [a for a in rfonts.attrib if not a.endswith("}hint")]:
                rpr.remove(rfonts)
            touched = True
        if rf.size_src == "direct" and rule.get("min_size") and rf.size < rule["min_size"] and under_s >= rule["min_size"]:
            remove(rpr, "sz", "szCs")
            touched = True
        if touched:
            pkg.touch(rf.story)
            pkg.mark(next(rf.el.iterancestors(q("p"))))
            if len(rpr) == 0:
                rf.el.remove(rpr)
            changed += 1
    return {"runs_changed": changed, "checks": []}


def op_font_styles(pkg, std, names=None):
    """Set each style that is the source of a broken rule to the scope's first permitted font and minimum size.
    names: limit to these style names. Report-only findings (document default) are not changed here."""
    from prodengine.engine.ops.word_ops import find_style
    runs = scan(pkg, std)
    todo = {}
    for rf in runs:
        rule = _rule(std, rf.scope)
        for src, bad, val, kind in ((rf.font_src, rule.get("fonts") and rf.font not in rule["fonts"], (rule.get("fonts") or [None])[0], "font"),
                                    (rf.size_src, rule.get("min_size") and rf.size < rule["min_size"], rule.get("min_size"), "size")):
            if bad and ":" in src:
                nm = src.split(":", 1)[1]
                if names and nm not in names:
                    continue
                todo.setdefault(nm, {})[kind] = val if kind == "font" else max(val, todo.get(nm, {}).get("size", 0))
    sp = pkg.word_part("/styles")
    pkg.touch(sp)
    root = pkg.tree(sp)
    done = []
    for nm, want in todo.items():
        st = find_style(root, nm)
        if st is None:
            continue
        pkg.mark(st)
        rpr = ensure(st, "rPr")
        if "font" in want:
            rf = ensure(rpr, "rFonts")
            for a in list(rf.attrib):
                del rf.attrib[a]
            rf.set(q("ascii"), want["font"]); rf.set(q("hAnsi"), want["font"]); rf.set(q("cs"), want["font"])
        if "size" in want:
            v = str(int(round(want["size"] * 2)))
            ensure(rpr, "sz").set(q("val"), v)
            ensure(rpr, "szCs").set(q("val"), v)
        done.append(nm)
    return {"styles": done, "checks": []}
