"""Learn a document type from a template or a finished document (3.7.0).

Reads a Word file (once, into memory; it is never opened for writing) and returns the values it carries, area by
area, as layers of the production standard:
  styles             every paragraph and character style the file uses or defines, with its whole definition
                     (font, size, bold, italic, underline, caps, color, alignment, spacing, line spacing, indents,
                     keep with next, keep lines together, page break before, widow control, based on, next style)
  variables          body, table and caption font and size, Heading 1 size, space after body text, line spacing,
                     margins and paper, from the styles and the body pages
  tables             each row role's look from the file's tables (tag style, fill, text color, every border edge,
                     vertical alignment, header rows repeating) and each table type's width, alignment and cell margins
  pages              the page setups (portrait and landscape margins, header and footer distances)
  headers            each part's header and footer layout (left, center, right, the rule below, the page number,
                     the volume values read from the cover, the restriction marking)
  heading_numbering  the nine heading levels: number format, number text, number and text positions
  toc                the TOC field's switches and heading levels
The person picks which areas to take; nothing is saved until they do."""
import copy, os, re
from collections import OrderedDict

from prodengine.engine.pkg import Package, NS
from prodengine.engine.ordered import q
from prodengine.engine.ops import word_ops as WO
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import sections as S, tables as T, hf as H

TW = 1440.0
AREAS = OrderedDict([("styles", "Styles (every style's full definition)"), ("variables", "Format variables (fonts, sizes, spacing, margins)"),
                     ("tables", "Table looks by row role and table type"), ("pages", "Page setups"),
                     ("headers", "Headers and footers"), ("heading_numbering", "Heading numbering"), ("toc", "Table of contents")])
LINE_NAMES = {1.0: "single", 1.15: "1.15", 1.5: "1.5", 2.0: "double"}
ALWAYS = ("Normal", "Heading 1", "Heading 2", "Heading 3", "Heading 4", "Heading 5", "Heading 6", "Heading 7", "Heading 8",
          "Heading 9", "Caption", "TOC Heading", "TOC 1", "TOC 2", "TOC 3", "Table of Figures", "Header", "Footer", "Title")


class Learned:
    def __init__(self, path):
        self.path = path
        self.areas = OrderedDict()      # key -> {"label", "summary": [lines], "layer": {...}}
        self.error = ""

    def add(self, key, layer, summary):
        if layer:
            self.areas[key] = {"label": AREAS[key], "summary": summary, "layer": layer}

    def layer(self, keys=None):
        """The chosen areas as one layer."""
        out = {}
        for k, a in self.areas.items():
            if keys is None or k in keys:
                for top, v in a["layer"].items():
                    if isinstance(v, dict) and isinstance(out.get(top), dict):
                        out[top].update(copy.deepcopy(v))
                    else:
                        out[top] = copy.deepcopy(v)
        return out


# ------------------------------------------------------------------ styles
def _font(root, s, theme):
    """The style's font, theme fonts resolved (+Body, +Headings) to the font they stand for."""
    f = WO.effective(root, s, "font", theme)
    if f:
        return f
    defaults = root.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
    for st in list(WO._chain(root, s)) + [None]:
        rpr = st.find("w:rPr", NS) if st is not None else defaults
        rf = rpr.find("w:rFonts", NS) if rpr is not None else None
        if rf is not None and (rf.get(q("asciiTheme")) or rf.get(q("ascii"))):
            th = rf.get(q("asciiTheme")) or ""
            if th:
                return theme.get("major" if th.startswith("major") else "minor", "")
            return rf.get(q("ascii"))
    return theme.get("minor", "")


def _numbered(root, s):
    return any(st.find("w:pPr/w:numPr", NS) is not None for st in WO._chain(root, s))


def style_definition(root, s, theme=None):
    """{prop: value} for every property of a style as Word shows it (through its base styles and the defaults).
    A numbered style's indents belong to its numbering (heading numbering), so they are not part of the style."""
    theme = theme or {}
    d = {"type": s.get(q("type"))}
    numbered = _numbered(root, s)
    for k in WO.STYLE_PROPS:
        if d["type"] == "character" and k not in WO.RUN_PROPS + ("based_on",):
            continue
        if numbered and k in ("left", "first", "hanging"):
            continue
        v = _font(root, s, theme) if k == "font" else WO.effective(root, s, k)
        if v is None or v == "" or (k in ("tabs", "border_top", "border_bottom", "border_left", "border_right", "shading")
                                    and v in ([], "none")):
            continue
        if isinstance(v, float):
            v = round(v, 2)
        d[k] = v
    if d.get("line_rule") == "auto":
        d.pop("line_rule")
    return d


def learn_styles(pkg):
    root = WO.styles_root(pkg)
    theme = WO.theme_fonts(pkg)
    used = WO.styles_in_use(pkg)
    out = {}
    for s in root.findall("w:style", NS):
        if s.get(q("type")) not in ("paragraph", "character"):
            continue
        n = s.find("w:name", NS)
        if n is None:
            continue
        name = n.get(q("val"))
        name = {"heading 1": "Heading 1"}.get(name, name)
        name = re.sub(r"^heading (\d)$", r"Heading \1", name)
        name = re.sub(r"^toc (\d)$", r"TOC \1", name)
        name = {"caption": "Caption", "header": "Header", "footer": "Footer", "table of figures": "Table of Figures",
                "toc heading": "TOC Heading", "title": "Title"}.get(name, name)
        custom = s.get(q("customStyle")) in ("1", "true")
        defined = s.find("w:rPr", NS) is not None or s.find("w:pPr", NS) is not None
        if not (custom or s.get(q("styleId")) in used or name in ALWAYS or defined):
            continue
        if s.get(q("default")) in ("1", "true") and s.get(q("type")) == "character":
            continue                                      # Default Paragraph Font: Word's own, not a style to set
        if name.endswith(" Char") and s.get(q("type")) == "character" and s.find("w:link", NS) is not None:
            continue                                      # Word keeps linked character styles in step by itself
        out[name] = style_definition(root, s, theme)
    return out


def _line_name(v):
    return LINE_NAMES.get(round(float(v), 2), "") if v is not None else ""


def learn_variables(styles, sm):
    v = {}
    body = styles.get("Body Text") if styles.get("Body Text") and "Normal" not in styles else styles.get("Normal")
    for src, fv, sv in ((body, "body_font", "body_size"), (styles.get("PE Table Text"), "table_font", "table_size"),
                        (styles.get("Caption"), "caption_font", "caption_size")):
        if src:
            if src.get("font"):
                v[fv] = src["font"]
            if src.get("size"):
                v[sv] = src["size"]
    if styles.get("Heading 1", {}).get("size"):
        v["heading1_size"] = styles["Heading 1"]["size"]
    if body:
        if body.get("after") is not None:
            v["space_after_body"] = body["after"]
        ln = _line_name(body.get("line")) if body.get("line_rule", "auto") == "auto" else ""
        if ln:
            v["line_spacing"] = ln
    sec = next((s for s in sm.sections if s.part == "body"), sm.sections[0] if sm.sections else None)
    if sec is not None:
        for side in ("top", "bottom", "left", "right"):
            v["margin_" + side] = round(sec.margins[side], 2)
        if sec.paper in ("Letter", "A4", "Legal", "Tabloid"):
            v["paper"] = sec.paper
    return v


# ------------------------------------------------------------------ tables
def _edge(tcpr, side):
    b = tcpr.find(f"w:tcBorders/w:{side}", NS) if tcpr is not None else None
    if b is None or b.get(q("val")) in ("nil", "none"):
        return None
    return [round(int(b.get(q("sz"), "4")) / 8, 2), (b.get(q("color")) or "000000").upper().replace("AUTO", "000000")]


def learn_tables(pkg, std, styles=None):
    names = T.style_name_map(WO.styles_root(pkg))
    root = pkg.tree(pkg.main)
    roles, types, counts = {}, {}, {}
    for tbl in root.iter(q("tbl")):
        if any(True for _ in tbl.iterancestors(q("tbl"))):
            continue
        ttype = "fig" if T.is_figure_table(tbl) else "std"
        decs = T.classify(tbl, std, ttype, names)
        if any(d.status == "ask" for d in decs):
            continue                                      # only tables whose every row is sure
        trs = T.rows(tbl)
        for d, tr in zip(decs, trs):
            if d.role in roles or d.role in ("keep",) or d.role not in std["row_types"]:
                continue
            cs = T.cells(tr)
            if not cs:
                continue
            first, last = cs[0], cs[-1]
            tcpr = first.find("w:tcPr", NS)
            look = {}
            ps = next((p.find("w:pPr/w:pStyle", NS) for p in T.own_paras(first) if p.find("w:pPr/w:pStyle", NS) is not None), None)
            if ps is not None and names.get(ps.get(q("val"))):
                look["tag_style"] = names[ps.get(q("val"))]
            shd = tcpr.find("w:shd", NS) if tcpr is not None else None
            look["fill"] = (shd.get(q("fill")).upper() if shd is not None and shd.get(q("fill")) not in (None, "auto") else None)
            va = tcpr.find("w:vAlign", NS) if tcpr is not None else None
            look["valign"] = va.get(q("val")) if va is not None else "top"
            trpr = tr.find("w:trPr", NS)
            look["repeat"] = trpr is not None and trpr.find("w:tblHeader", NS) is not None
            ltc = last.find("w:tcPr", NS)
            mid = cs[1].find("w:tcPr", NS) if len(cs) > 2 else (ltc if len(cs) > 1 else None)
            look["edges"] = {"top": _edge(tcpr, "top"), "bottom": _edge(tcpr, "bottom"), "left": _edge(tcpr, "left"),
                             "right": _edge(ltc if ltc is not None else tcpr, "right"),
                             "inside_v": _edge(mid, "left") if mid is not None else None}
            sd = (styles or {}).get(look.get("tag_style", ""), {})
            for k_look, k_style in (("font", "font"), ("size", "size"), ("bold", "bold"), ("italic", "italic"), ("color", "color"),
                                    ("align", "jc"), ("before", "before"), ("after", "after")):
                if sd.get(k_style) is not None:
                    look[k_look] = sd[k_style]
            if look.get("color") == "AUTO":
                look.pop("color")
            roles[d.role] = look
            counts[d.role] = counts.get(d.role, 0) + 1
        if ttype not in types:
            tp = tbl.find("w:tblPr", NS)
            t = {}
            tw = tp.find("w:tblW", NS) if tp is not None else None
            if tw is not None and tw.get(q("type")) == "pct":
                t["width_pct"] = round(int(tw.get(q("w"), "5000")) / 50)
            jc = tp.find("w:jc", NS) if tp is not None else None
            if jc is not None:
                t["align"] = jc.get(q("val"))
            cm = tp.find("w:tblCellMar", NS) if tp is not None else None
            if cm is not None:
                mar = {}
                for sd, alt in (("top", "top"), ("bottom", "bottom"), ("left", "start"), ("right", "end")):
                    el = cm.find(f"w:{sd}", NS)
                    el = el if el is not None else cm.find(f"w:{alt}", NS)
                    mar[sd] = round(int(el.get(q("w"), "0")) / 20, 1) if el is not None else 0
                t["cell_margins"] = mar
            if t:
                types[ttype] = t
    return roles, types


# ------------------------------------------------------------------ headers and footers
def _slots(p_els, names):
    """A header or footer paragraph as left / center / right slots, fields as tokens."""
    rev = {v: k for k, v in H.SOURCE_STYLES.items()}
    slots, cur, in_instr, instr, rule = [], "", False, "", False
    for p in p_els:
        ppr = p.find("w:pPr", NS)
        if ppr is not None and ppr.find("w:pBdr/w:bottom", NS) is not None:
            rule = True
        for el in p.iter():
            tag = el.tag.split("}")[-1]
            if tag == "fldChar":
                t = el.get(q("fldCharType"))
                if t == "begin":
                    in_instr, instr = True, ""
                elif t == "separate":
                    in_instr = False
                    word = (instr.split() or [""])[0].upper()
                    m = re.search(r'STYLEREF\s+"?([^"\\]+?)"?\s*(\\|$)', instr.strip(), re.I)
                    if word == "PAGE":
                        cur += "{page}"
                    elif word in ("SECTIONPAGES", "NUMPAGES"):
                        cur += "{pages}"
                    elif word == "STYLEREF" and m and m.group(1).strip() in rev:
                        cur += "{" + rev[m.group(1).strip()] + "}"
                    elif word == "STYLEREF" and m and m.group(1).strip().lower() in ("1", "heading 1"):
                        cur += "{chapter}"
                    cur += "\x00"                          # result text that follows is the field's: skip it
                elif t == "end":
                    cur = cur.replace("\x00", "")
            elif tag == "instrText" and in_instr:
                instr += el.text or ""
            elif tag == "t" and "\x00" not in cur:
                cur += el.text or ""
            elif tag == "tab" and el.getparent() is not None and el.getparent().tag.endswith("}r"):
                slots.append(cur); cur = ""
        slots.append(cur); cur = ""
        break                                             # the first paragraph with content carries the layout
    slots = [x.strip() for x in slots]
    if len(slots) == 1:
        out = {"left": slots[0]} if slots[0] else {}
    elif len(slots) == 2:
        out = {"left": slots[0], "right": slots[1]}
    else:
        out = {"left": slots[0], "center": slots[1], "right": slots[-1]}
    out = {k: v for k, v in out.items() if v}
    if rule:
        out["rule_below"] = True
    return out


def _hf_layout(pkg, part, kind, marking):
    if not part:
        return {}
    root = pkg.tree(part)
    paras = [p for p in root.iter(q("p")) if visible_text(p).strip() or p.find(".//w:fldChar", NS) is not None]
    lay, mark = {}, ""
    for p in paras:
        t = visible_text(p).strip()
        if kind == "footer" and len(t) > 50 and not p.findall(".//w:fldChar", NS):
            mark = t
            continue
        if not lay:
            lay = _slots([p], {})
    if kind == "footer" and mark:
        lay["marking"] = True
    return lay, mark


def learn_headers(pkg, sm):
    layouts, marking, seen = {}, "", set()
    for s in sm.sections:
        if not s.part or s.part in seen:
            continue
        seen.add(s.part)
        head = _hf_layout(pkg, s.headers["default"].part, "header", "")
        foot = _hf_layout(pkg, s.footers["default"].part, "footer", "")
        h = head[0] if head else {}
        f, m = (foot if foot else ({}, ""))
        marking = marking or m
        layouts[s.part] = {"header": h, "footer": f}
    return layouts, marking


# ------------------------------------------------------------------ heading numbering and the TOC
def learn_heading_numbering(pkg):
    sroot = WO.styles_root(pkg)
    h1 = WO.find_style(sroot, "Heading 1")
    nid = h1.find("w:pPr/w:numPr/w:numId", NS) if h1 is not None else None
    nbp = pkg.word_part("/numbering")
    if nid is None or not nbp:
        return None
    nb = pkg.tree(nbp)
    num = next((n for n in nb.findall("w:num", NS) if n.get(q("numId")) == nid.get(q("val"))), None)
    if num is None or num.find("w:abstractNumId", NS) is None:
        return None
    aid = num.find("w:abstractNumId", NS).get(q("val"))
    absn = next((a for a in nb.findall("w:abstractNum", NS) if a.get(q("abstractNumId")) == aid), None)
    if absn is None:
        return None
    ids = {s.get(q("styleId")): s.find("w:name", NS).get(q("val")) for s in sroot.findall("w:style", NS) if s.find("w:name", NS) is not None}
    levels = []
    for lvl in absn.findall("w:lvl", NS):
        ps = lvl.find("w:pStyle", NS)
        if ps is None:
            continue
        name = re.sub(r"^heading (\d)$", r"Heading \1", ids.get(ps.get(q("val")), ""))
        if not re.fullmatch(r"Heading \d", name):
            continue
        ind = lvl.find("w:pPr/w:ind", NS)
        left = int((ind.get(q("left")) or ind.get(q("start")) or "0") if ind is not None else 0) / TW
        hang = int(ind.get(q("hanging")) or 0) / TW if ind is not None else 0
        rs = lvl.find("w:lvlRestart", NS)
        levels.append({"style": name, "fmt": (lvl.find("w:numFmt", NS).get(q("val")) if lvl.find("w:numFmt", NS) is not None else "decimal"),
                       "text": lvl.find("w:lvlText", NS).get(q("val")) if lvl.find("w:lvlText", NS) is not None else "",
                       "number_at": round(left - hang, 2), "text_at": round(left, 2),
                       "restart": int(rs.get(q("val"))) if rs is not None else None})
    return {"on": True, "levels": levels} if len(levels) >= 3 else None


def learn_toc(pkg):
    from prodengine.engine.fingerprint import fields
    for f in fields(pkg.tree(pkg.main)):
        if f.split() and f.split()[0].upper() == "TOC" and "\\c" not in f and "\\a" not in f:
            sw = sorted(set(re.findall(r"\\[hzuwnp]", f)))
            out = {"switches": sw}
            m = re.search(r'\\o\s+"(\d)-(\d)"', f)
            if m:
                out["levels"] = [[f"Heading {k}", k] for k in range(int(m.group(1)), int(m.group(2)) + 1)]
            return out
    return None


# ------------------------------------------------------------------ the whole file
def learn(path, std, data=None):
    """Read the file once and return what it carries, area by area (Learned)."""
    out = Learned(path)
    try:
        raw = data if data is not None else open(path, "rb").read()
        pkg = Package.from_bytes(raw, os.path.basename(path))
    except Exception as e:  # noqa: BLE001
        out.error = f"The file could not be read ({type(e).__name__})."
        return out
    if not pkg.is_word:
        out.error = "Learning reads Word files (.docx, .dotx and their macro forms)."
        return out
    styles = learn_styles(pkg)
    out.add("styles", {"style_defs": styles}, [f"{len(styles)} styles: " + ", ".join(sorted(styles)[:12]) + (" ..." if len(styles) > 12 else "")])
    try:
        sm = S.map_sections(pkg, std)
    except Exception:  # noqa: BLE001
        sm = None
    if sm is not None:
        v = learn_variables(styles, sm)
        out.add("variables", {"variables": v}, [f"{k.replace('_', ' ')}: {val}" for k, val in v.items()])
        setups = {}
        for s in sm.sections:
            key = "landscape" if s.orient == "landscape" else "portrait"
            if key not in setups:
                setups[key] = {k: round(s.margins[k], 2) for k in ("top", "bottom", "left", "right", "header", "footer")}
        if "portrait" in setups:          # portrait margins follow the format variables when they match
            vv = out.areas.get("variables", {}).get("layer", {}).get("variables", {})
            for side in ("top", "bottom", "left", "right"):
                if vv.get("margin_" + side) == setups["portrait"][side]:
                    setups["portrait"][side] = "=margin_" + side
        out.add("pages", {"page_setups": setups}, [f"{k}: margins {', '.join(f'{a} {b}' for a, b in v.items())}" for k, v in setups.items()])
        lay, mark = learn_headers(pkg, sm)
        layer = {"hf_layouts": lay}
        if mark:
            layer["variables"] = {"marking": mark}
        out.add("headers", layer if any(x["header"] or x["footer"] for x in lay.values()) else {},
                [f"{k}: header {x['header'] or 'empty'}; footer {x['footer'] or 'empty'}" for k, x in lay.items()] +
                ([f"marking: {mark[:80]}"] if mark else []))
    roles, types = learn_tables(pkg, std, styles)
    if roles:
        layer = {"row_types": roles}
        if types:
            layer["table_types"] = types
        out.add("tables", layer, [f"{r}: {lk.get('tag_style', '')}, fill {lk.get('fill') or 'none'}" for r, lk in roles.items()])
    hn = learn_heading_numbering(pkg)
    if hn:
        out.add("heading_numbering", {"heading_numbering": hn}, [f"{l['style']}: {l['text']} ({l['fmt']})" for l in hn["levels"]])
    toc = learn_toc(pkg)
    if toc:
        out.add("toc", {"toc": toc}, [f"switches {' '.join(toc['switches'])}" + (f", headings 1-{len(toc['levels'])}" if toc.get("levels") else "")])
    return out
