"""3.25.0: everything a template will carry, read from the standard before any file is made.

Make templates opens on this view: styles, page setups and margins, pagination by part, headers and footers, heading
and list numbering (as the numbers look), table types and looks, captions, the table of contents, cover and back
cover, Quick Parts, fields, theme and fonts, and what must be fixed first. Read only: nothing here writes a file.
"""
import html

import numtext as NT
import prodrules as PRL
from prodengine.pe import rules as PR

SECTIONS = ("Fix first", "Styles", "Pages and margins", "Pagination by part", "Headers and footers", "Heading numbering",
            "List numbering", "Tables", "Captions", "Table of contents", "Cover and back cover", "Quick Parts", "Fields",
            "Theme", "Fonts")
FMT = {"decimal": "1, 2, 3", "lowerRoman": "i, ii, iii", "upperRoman": "I, II, III", "lowerLetter": "a, b, c",
       "upperLetter": "A, B, C", "bullet": "Bullet", "decimalZero": "01, 02, 03"}
RESTART = {"part": "at the start of the part", "each": "at each chapter", "never": "continues"}
STYLE_KEYS = (("font", "Font"), ("size", "Size"), ("bold", "Bold"), ("italic", "Italic"), ("caps", "Caps"), ("color", "Color"),
              ("align", "Align"), ("before", "Before"), ("after", "After"), ("line", "Line"), ("left", "Left"),
              ("hanging", "Hanging"), ("keep_next", "Keep with next"), ("hidden", "Hidden"), ("based_on", "Based on"))


def _e(x):
    return html.escape("" if x is None else str(x))


def _v(std, x):
    return PR.value(std, x)


def _num(x, unit=""):
    if x in (None, ""):
        return ""
    try:
        f = float(x)
        return (f"{f:g}" + unit)
    except (TypeError, ValueError):
        return str(x)


def _table(head, rows):
    if not rows:
        return "<p class='none'>None.</p>"
    h = "".join(f"<th>{_e(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>"


def sections(std, problems=(), installed_fonts=None):
    """[(title, html)] for each section, in order. std: the standard in force (engine-ready)."""
    out = []
    pr = list(problems or [])
    out.append(("Fix first", "<p class='none'>Nothing. The template can be made.</p>" if not pr else
                "<ul>" + "".join(f"<li>{_e(p)}</li>" for p in pr) + "</ul>"))
    spec = PRL.style_spec(std)
    rows = []
    for name in sorted(spec, key=str.casefold):
        d = spec[name]
        rows.append([name] + [("yes" if d.get(k) is True else "no" if d.get(k) is False else _num(d.get(k)) if k in
                               ("size", "before", "after", "left", "hanging") else d.get(k, "")) for k, _h in STYLE_KEYS])
    hidden = [n for n, d in spec.items() if d.get("hidden")]
    out.append(("Styles", f"<p>{len(spec)} style(s) defined" + (f"; hidden text: {_e(', '.join(sorted(hidden)))}" if hidden else "")
                + ".</p>" + _table(["Style"] + [h for _k, h in STYLE_KEYS], rows)))
    ps = std.get("page_setups") or {}
    out.append(("Pages and margins", _table(["Page setup", "Size (in)", "Orientation", "Top", "Bottom", "Left", "Right", "Header", "Footer"],
                [[p.get("name") or k, f"{_num(p.get('w'))} x {_num(p.get('h'))}", p.get("orient", ""),
                  *[_num(_v(std, p.get(m)), " in") for m in ("top", "bottom", "left", "right", "header", "footer")]]
                 for k, p in ps.items()])))
    pg = std.get("pagination") or {}
    rows = []
    for p in pg.get("parts") or []:
        n = p.get("numbers") or {}
        st = p.get("starts") or {}
        start = ("the first section" if st.get("first_section") else "the last section" if st.get("last_section")
                 else st.get("style") or ", ".join(st.get("styles") or []))
        if n:
            num = FMT.get(n.get("fmt"), n.get("fmt", ""))
            if n.get("chapter_level"):
                num += f", chapter (level {n['chapter_level']}) then page, {PR.SEPARATORS.get(n.get('separator', 'hyphen'), '-')} between"
            num += f"; restarts {RESTART.get(n.get('restart', 'part'), n.get('restart', ''))} at {n.get('start_at', 1)}"
        else:
            num = "No page numbers"
        rows.append([p.get("name") or p.get("key"), start, num, "yes" if p.get("linked") else "no"])
    out.append(("Pagination by part", f"<p>{_e(pg.get('name', ''))}</p>" + _table(["Part", "Starts at", "Page numbers", "Linked to the part before"], rows)))
    hf, des = std.get("hf_layouts") or {}, std.get("hf_designs") or {}
    rows = []
    for k, lay in hf.items():
        h, f = lay.get("header") or {}, lay.get("footer") or {}
        if k in des:
            rows.append([k, "kept design (as built)", "kept design (as built)", ""])
            continue
        rows.append([k, " | ".join(h.get(s, "") for s in ("left", "center", "right")).strip(" |") + (" (rule below)" if h.get("rule_below") else ""),
                     " | ".join(f.get(s, "") for s in ("left", "center", "right")).strip(" |"), "yes" if f.get("marking") else ""])
    for k in des:
        if k not in hf:
            rows.append([k, "kept design (as built)", "kept design (as built)", ""])
    out.append(("Headers and footers", _table(["Part", "Header (left | center | right)", "Footer (left | center | right)", "Marking"], rows)))
    hn = std.get("heading_numbering") or {}
    lv = hn.get("levels") or []
    fm = [x.get("fmt") or "decimal" for x in lv]
    out.append(("Heading numbering", f"<p>{'Set when fixing and in templates' if hn.get('on') else 'Off: headings keep the numbering the template gives them'}.</p>"
                + _table(["Style", "Format", "Number reads", "Number at", "Text at", "Restarts after level"],
                         [[x.get("style"), FMT.get(x.get("fmt"), x.get("fmt", "")), NT.show(x.get("text") or "", fm),
                           _num(x.get("number_at"), " in"), _num(x.get("text_at"), " in"), x.get("restart") or ""] for x in lv])))
    ln = std.get("list_numbering") or {}
    rows = []
    for l in ln.get("lists") or []:
        lf = [x.get("fmt") or "decimal" for x in l.get("levels") or []]
        for x in l.get("levels") or []:
            rows.append([l.get("name"), x.get("style"), FMT.get(x.get("fmt"), x.get("fmt", "")),
                         x.get("text") if x.get("fmt") == "bullet" else NT.show(x.get("text") or "", lf), x.get("font") or "",
                         _num(x.get("left"), " in"), _num(x.get("hanging"), " in")])
    out.append(("List numbering", _table(["List", "Style", "Format", "Shows", "Bullet font", "Text at", "Number before the text"], rows)))
    rows = []
    for k, t in (std.get("table_types") or {}).items():
        if t.get("width_unit") == "in" or t.get("width_in"):
            w = _num(t.get("width_in"), " in")
        else:
            w = _num(t.get("width_pct"), "%")
        cm = t.get("cell_margins") or {}
        rows.append([t.get("name") or k, w, ", ".join(_num(x) for x in (t.get("col_widths_in") or [])), t.get("align", ""),
                     " / ".join(_num(cm.get(s), " pt") for s in ("top", "bottom", "left", "right")), t.get("word_style", "")])
    looks = []
    for role, rt in (std.get("row_types") or {}).items():
        looks.append([role, rt.get("tag_style", ""), _v(std, rt.get("font")), _num(_v(std, rt.get("size")), " pt"),
                      "yes" if rt.get("bold") else "", rt.get("fill") or "", rt.get("align", "")])
    out.append(("Tables", "<h4>Table types</h4>" + _table(["Table type", "Width", "Column widths (in)", "Align", "Cell padding (top / bottom / left / right)", "Word table style"], rows)
                + "<h4>Row looks</h4>" + _table(["Row role", "Style", "Font", "Size", "Bold", "Fill", "Align"], looks)
                + (f"<p>Word table styles carried whole: {_e(', '.join(sorted(std.get('table_styles'))))}</p>" if std.get("table_styles") else "")))
    rows = []
    for c in std.get("captions") or []:
        num = (f"chapter (level {c['chapter_level']}) {c.get('separator', '-')} sequence" if c.get("chapter_level") else "sequence only")
        rows.append([c.get("label"), c.get("part", ""), c.get("position", ""), FMT.get(c.get("number_format") or "decimal", "1, 2, 3"),
                     num, c.get("style", ""), c.get("identifier", "")])
    out.append(("Captions", _table(["Label", "Part", "Position", "Number shows as", "Numbered by", "Style", "Field identifier"], rows)))
    toc = std.get("toc") or {}
    out.append(("Table of contents", f"<p>Levels: {_e(', '.join(f'{s} (level {n})' for s, n in toc.get('levels') or []))}. "
                f"Switches: {_e(' '.join(toc.get('switches') or []))}. Title style: {_e(toc.get('title_style', ''))}.</p>"
                + (f"<p>Lists: {_e(', '.join(l.get('title', '') for l in toc.get('lists') or []))}.</p>" if toc.get("lists") else "")
                + _table(["Entry style", "Number at", "Text at", "Right indent", "Tab"],
                         [[k, _num(s.get("number_at"), " in"), _num(s.get("text_at"), " in"), _num(s.get("right_indent"), " in"),
                           f"{_num((s.get('tab') or [None])[0], ' in')} {(s.get('tab') or [None, None, ''])[2] or ''}".strip()]
                          for k, s in (toc.get("entry_styles") or {}).items()])))
    pp = std.get("page_parts") or {}
    out.append(("Cover and back cover", "<p>" + ("; ".join(f"{'Cover' if k == 'cover' else 'Back cover'}: {_e(v)} (kept as built)" for k, v in pp.items())
                                               or "The Stationkeeper base cover and back cover.") + "</p>"))
    qp = std.get("quick_parts") or {}
    out.append(("Quick Parts", ("<p>All in one Quick Parts gallery, by category.</p>" if qp.get("one_gallery") else "")
                + _table(["Quick Part", "Category", "From"], [[e.get("name"), e.get("category", ""), e.get("source", "")] for e in qp.get("entries") or []])))
    import fillins as FI
    out.append(("Fields", _table(["Key", "Name", "How it works", "Where it sits", "Value"],
                [[f"{{{f['key']}}}", f["name"], dict(FI.KINDS)[f["kind"]], f["style"] or f["property"], f["value"]]
                 for f in FI.custom(std)])))
    th = std.get("theme") or {}
    out.append(("Theme", f"<p>{_e(th.get('name'))} (colors and fonts carried whole).</p>" if th.get("name") else "<p class='none'>Word's default theme.</p>"))
    fonts = sorted({d.get("font") for d in spec.values() if d.get("font")}, key=str.casefold)
    if installed_fonts is not None:
        inst = {f.casefold() for f in installed_fonts}
        frows = [[f, "installed on this PC" if f.casefold() in inst else "NOT installed on this PC"] for f in fonts]
    else:
        frows = [[f, ""] for f in fonts]
    out.append(("Fonts", _table(["Font", "On this PC"], frows)))
    return out


CSS = ("body{font-family:Segoe UI,Arial,sans-serif;font-size:10pt} h3{margin:14px 0 4px 0} h4{margin:8px 0 2px 0}"
       " table{border-collapse:collapse;margin:4px 0} th,td{border:1px solid #c8cdd6;padding:3px 6px;text-align:left;vertical-align:top}"
       " th{background:#eef1f6} p.none{color:#6b7280}")


def html_of(std, title="", problems=(), installed_fonts=None):
    """The whole view as one page of HTML (for the Make templates dialog)."""
    parts = [f"<style>{CSS}</style>"] + ([f"<h2>{_e(title)}</h2>"] if title else [])
    for t, h in sections(std, problems, installed_fonts):
        parts.append(f"<h3><a name='{_e(t)}'></a>{_e(t)}</h3>{h}")
    return "".join(parts)
