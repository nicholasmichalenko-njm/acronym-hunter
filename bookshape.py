"""4.57.0: a standards workbook under the plain column names, read beside the names the app writes today (the one-system
rule; claude/stationkeeper-column-lists-for-both-tools.md, Nicholas 2026-11-19).

The Stationkeeper Macros read both sets of names since 1.24.0 and will make a workbook under the plain ones. This module
turns a reading of such a workbook into the shape the rest of the app already knows, so nothing else has to change:
- a plain column name is taken as the older one ("Number format" as "Fmt", "Top margin (in)" as "Top");
- a choice written in Word's own words is taken as the older word ("Justified" as "both", "1, 2, 3" as "decimal");
- an edge typed as "0.5, 8EA9DB" is taken as the older bracket form;
- a table type's "Has ... row" and "... look" columns are taken as its Roles and Override;
- a page setup's two switches are taken as its Rules;
- Fonts allowed with one row per font is taken as one row per use;
- names separated by semicolons are taken as the comma lists two list sheets hold.
Where a workbook holds both the older column and the plain one, a value under the older name wins (as in the macros).
The app still WRITES the older names: the plain ones come with a later release. Nothing here writes a file.

Rules only (No AI); nothing leaves the PC."""
import json

ROLES = ("caption", "header", "header2", "subhead", "body", "subtotal", "total", "note", "keep")
FORMAT_NEWER = "This workbook was written by a newer Stationkeeper. Update this PC first."

# sheet: {plain name: the name the app writes today}
NAMES = {
    "Table looks": {"Row style": "Tag style", "Alignment": "Align", "Vertical alignment": "Valign",
                    "Repeat as header row": "Repeat", "One cell across the table": "Merge", "Edge above": "Edges: top",
                    "Edge below": "Edges: bottom", "Edge left": "Edges: left", "Edge right": "Edges: right",
                    "Edge between columns": "Edges: inside v", "Edge inside, vertical": "Edges: inside v",
                    "Shading (hex, or none)": "Fill"},
    "Table types": {"Alignment": "Align", "Width (%)": "Width pct", "Cell margin top (pt)": "Cell margins: top",
                    "Cell margin bottom (pt)": "Cell margins: bottom", "Cell margin left (pt)": "Cell margins: left",
                    "Cell margin right (pt)": "Cell margins: right"},
    "Heading numbering": {"Number format": "Fmt", "Number text": "Text", "Number at (in)": "Number at",
                          "Text at (in)": "Text at"},
    "List numbering": {"Number format": "Fmt", "Number text": "Text", "Left indent (in)": "Left indent (pt)",
                       "Hanging (in)": "Hanging (pt)"},
    "Page setups": {"Paper width (in)": "W", "Paper height (in)": "H", "Orientation": "Orient", "Top margin (in)": "Top",
                    "Bottom margin (in)": "Bottom", "Left margin (in)": "Left indent (pt)",
                    "Right margin (in)": "Right indent (pt)", "Header distance (in)": "Header",
                    "Footer distance (in)": "Footer"},
    "Fonts allowed": {"RFP reference": "Rfp ref"},
}
# the app's own keys on each sheet, for a workbook with no Columns sheet (one the macros or a person made)
KEYS = {
    "Table looks": ("tag_style", "font", "size", "bold", "italic", "color", "align", "valign", "repeat", "merge", "before",
                    "after", "left", "right", "fill", "edges.top", "edges.bottom", "edges.left", "edges.right",
                    "edges.inside_v"),
    "Table types": ("align", "name", "width_pct", "cell_margins.top", "cell_margins.bottom", "cell_margins.left",
                    "cell_margins.right", "roles", "override", "caption_position"),
    "Heading numbering": ("fmt", "text", "number_at", "text_at", "restart", "style"),
    "List numbering": ("font", "left", "hanging", "fmt", "text", "level", "style", "list"),
    "Page setups": ("left", "right", "name", "w", "h", "orient", "top", "bottom", "header", "footer", "rules"),
    "Captions": ("label", "part", "position", "chapter_level", "separator", "identifier", "after_number", "style"),
    "Fonts allowed": ("fonts", "min_size", "max_size", "rfp_ref"),
}
_FMT = {"1, 2, 3": "decimal", "I, II, III": "upperRoman", "i, ii, iii": "lowerRoman", "A, B, C": "upperLetter",
        "a, b, c": "lowerLetter"}
_ALIGN = {"left": "left", "centered": "center", "center": "center", "right": "right", "justified": "both", "both": "both"}
_LOWER = {"top": "top", "center": "center", "centered": "center", "bottom": "bottom", "portrait": "portrait",
          "landscape": "landscape"}
_RULE = {"multiple": None, "exactly": "exact", "exact": "exact", "at least": "atLeast", "atleast": "atLeast"}
# (sheet, the app's column) -> how a value in Word's words is taken
WORDS = {("Heading numbering", "Fmt"): "fmt", ("List numbering", "Fmt"): "fmt", ("Styles", "Alignment"): "align",
         ("Table looks", "Align"): "align", ("Table types", "Align"): "align", ("Styles", "Line rule"): "rule",
         ("Table looks", "Valign"): "lower", ("Page setups", "Orient"): "lower"}
HAS = (("Has caption row", "caption"), ("Has header row", "header"), ("Has second header row", "header2"),
       ("Has subhead rows", "subhead"), ("Has subtotal rows", "subtotal"), ("Has total row", "total"),
       ("Has notes row", "note"), ("Rows may be left as they are", "keep"))
LOOKS = (("Caption look", "caption"), ("Header look", "header"), ("Second header look", "header2"),
         ("Subhead look", "subhead"), ("Body look", "body"), ("Subtotal look", "subtotal"), ("Total look", "total"),
         ("Notes look", "note"))
SWITCHES = (("Page numbers restart", "restart"), ("Header and footer continue from the section before", "linked"))
MACRO_LOOKS = ("number", "short", "short text", "keep", "left as it is", "figure caption")   # kept, not applied yet
USES = {"body": "body", "heading": "heading", "headings": "heading", "table": "table", "tables": "table",
        "caption": "caption", "captions": "caption", "header and footer": "header_footer", "header_footer": "header_footer",
        "footnote": "footnote", "footnotes": "footnote", "graphic": "graphic", "graphics": "graphic"}
ALL_USES = ("body", "heading", "table", "caption", "header_footer", "footnote", "graphic")
LISTS = (("Authors", "Efforts"), ("Document types", "Words that find it"))


def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _yes(v):
    if isinstance(v, str):
        return v.strip().casefold() in ("true", "yes", "y", "1")
    return bool(v) and not _blank(v)


def _col(header, name):
    """The header as the workbook writes it, for a name in any letter case; None when it is not there."""
    want = name.casefold()
    return next((h for h in header if h and h.strip().casefold() == want), None)


def key_map(sheet):
    """{the app's column name: its key} for a sheet, with no Columns sheet to go by."""
    import standardsbook as SB
    if sheet == "Styles":
        import libstyle as LS
        return {n: k for k, n, _t in LS.PROPS}
    return {SB._label(k): k for k in KEYS.get(sheet, ())}


def _plain(book, sheet):
    book.setdefault("plain", set()).add(sheet)


def _rename(book, sheet):
    header = book["headers"].get(sheet) or []
    rows = book["sheets"].get(sheet) or []
    for plain, old in NAMES.get(sheet, {}).items():
        h = _col(header, plain)
        if h is None:
            continue
        _plain(book, sheet)
        have = _col(header, old)
        for r in rows:
            v = r.pop(h, None)
            if _blank(r.get(have or old)):                # a value under the older name wins
                r[have or old] = v
        if have is None:
            header[header.index(h)] = old
        else:
            header.remove(h)
    book["headers"][sheet] = header


def _edge(v):
    """'0.5, 8EA9DB' as the bracket form the app holds; 'none' as no line; anything else as it is."""
    if not isinstance(v, str):
        return v
    t = v.strip()
    if t.casefold() == "none":
        return None
    if t[:1] in "[{" or "," not in t:
        return v
    a, b = (x.strip() for x in t.split(",", 1))
    try:
        return json.dumps([float(a), b.lstrip("#").upper()])
    except ValueError:
        return v


def _word(kind, v):
    if not isinstance(v, str):
        return v
    t = " ".join(v.split())
    if kind == "fmt":
        return _FMT.get(t, "bullet" if t.casefold() == "bullet" else v)
    if kind == "align":
        return _ALIGN.get(t.casefold(), v)
    if kind == "lower":
        return _LOWER.get(t.casefold(), v)
    if kind == "rule":
        return _RULE.get(t.casefold(), v) if t.casefold() in _RULE else v
    return v


def _values(book, sheet):
    header = book["headers"].get(sheet) or []
    for (s, col), kind in WORDS.items():
        if s == sheet and col in header:
            for r in book["sheets"].get(sheet) or []:
                r[col] = _word(kind, r.get(col))
    if sheet == "Table looks":
        for r in book["sheets"].get(sheet) or []:
            for h in header:
                if h.startswith("Edges: "):
                    r[h] = _edge(r.get(h))


def _props(row, sheet):
    """A row's values by the app's keys, from a reading. An edge typed "none" is held as no line (None), which is not
    the same as a blank cell: a look a table type names can take a line away."""
    import standardsbook as SB
    km = key_map(sheet)
    out = {}
    for h, v in row.items():
        if h not in km or _blank(v):
            continue
        if h.startswith("Edges: "):
            v = _edge(v)
        elif (sheet, h) in WORDS:
            v = _word(WORDS[(sheet, h)], v)
        out[km[h]] = SB.from_cell(v)
    return out


def _table_types(book):
    sheet = "Table types"
    header = book["headers"].get(sheet)
    if not header:
        return
    has = [(c, role) for c, role in ((_col(header, n), role) for n, role in HAS) if c]
    look = [(c, role) for c, role in ((_col(header, n), role) for n, role in LOOKS) if c]
    if has or look:
        _plain(book, sheet)
    looks = {str(r.get("Name") or "").strip().casefold(): _props(r, "Table looks")
             for r in book["sheets"].get("Table looks") or []}
    aside = book.setdefault("aside", {}).setdefault("Table looks", set())
    for r in book["sheets"].get(sheet) or []:
        if has and _blank(r.get("Roles")):
            roles = {role for c, role in has if _yes(r.get(c))} | {"body"}
            r["Roles"] = json.dumps([x for x in ROLES if x in roles])
        if look and _blank(r.get("Override")):
            over = {}
            for c, role in look:
                name = str(r.get(c) or "").strip()
                if not name or name.casefold() == role or name.casefold() not in looks or role not in looks:
                    continue
                diff = {k: v for k, v in looks[name.casefold()].items() if looks[role].get(k) != v}
                if diff:
                    import standardsbook as SB
                    over[role] = SB._unflat(diff)
                aside.add(name.casefold())             # a look a type names is kept on its sheet, not made a kind of row
            if over:
                r["Override"] = json.dumps(over)
        for c, _role in has + look:
            r.pop(c, None)
    for c, _role in has + look:
        header.remove(c)
    for extra in (("Roles",) if has else ()) + (("Override",) if look else ()):
        if extra not in header:
            header.append(extra)


def _own_name(book, sheet):
    """The older "Name (value)" column, when a workbook under the plain names has none: the row's Name."""
    header = book["headers"].get(sheet)
    if header and "Name" in header and "Name (value)" not in header and book["sheets"].get(sheet):
        header.append("Name (value)")
        for r in book["sheets"][sheet]:
            r["Name (value)"] = r.get("Name")


def _page_setups(book):
    sheet = "Page setups"
    header = book["headers"].get(sheet)
    if not header:
        return
    sw = [(c, key) for c, key in ((_col(header, n), key) for n, key in SWITCHES) if c]
    if sw:
        _plain(book, sheet)
    for r in book["sheets"].get(sheet) or []:
        if sw and _blank(r.get("Rules")):
            rules = {key: _yes(r.get(c)) for c, key in sw if not _blank(r.get(c))}
            if rules:
                r["Rules"] = json.dumps(rules)
        for c, _k in sw:
            r.pop(c, None)
    for c, _k in sw:
        header.remove(c)
    if sw and "Rules" not in header:
        header.append("Rules")


def _fonts(book):
    """One row per font with Used for, as one row per use with its fonts. The app holds one smallest and one largest
    size for a use, so where a use's fonts differ the widest limits are taken."""
    sheet = "Fonts allowed"
    header = book["headers"].get(sheet)
    used = _col(header or [], "Used for")
    if not used:
        return
    lo_c, hi_c = _col(header, "Min size (pt)"), _col(header, "Max size (pt)")
    by_use = {}
    for r in book["sheets"].get(sheet) or []:
        font = str(r.get("Name") or "").strip()
        status = str(r.get("Status") or "Approved").strip().casefold()
        if not font or status not in ("approved", ""):
            continue
        u = " ".join(str(r.get(used) or "any").split()).casefold()
        for use in (ALL_USES if u in ("any", "") else (USES.get(u),)):
            if use:
                by_use.setdefault(use, []).append(r)
    rows = []
    for use in ALL_USES:
        got = by_use.get(use) or []
        if not got:
            continue
        lo = [float(r[lo_c]) for r in got if lo_c and isinstance(r.get(lo_c), (int, float))]
        hi = [float(r[hi_c]) for r in got if hi_c and isinstance(r.get(hi_c), (int, float))]
        rows.append({"Name": use, "Status": "Approved",
                     "Fonts": json.dumps(list(dict.fromkeys(str(r["Name"]).strip() for r in got))),
                     "Min size": min(lo) if len(lo) == len(got) else None, "Max size": max(hi) if len(hi) == len(got) else None,
                     "Rfp ref": next((r.get("Rfp ref") for r in got if not _blank(r.get("Rfp ref"))), None)})
    book["sheets"][sheet] = rows
    book["headers"][sheet] = ["Name", "Status", "Fonts", "Min size", "Max size", "Rfp ref"]
    book.setdefault("leave", set()).add(sheet)         # the app reads it and leaves the sheet as the person has it


def _lists(book):
    for sheet, col in LISTS:
        for r in book["sheets"].get(sheet) or []:
            v = r.get(col)
            if isinstance(v, str) and ";" in v:
                r[col] = ", ".join(x.strip() for x in v.split(";") if x.strip())


def format_of(book):
    """The format number a reading states (its About sheet, or a Read me sheet), or None."""
    for sheet in ("About", "Read me"):
        head = book["headers"].get(sheet) or []
        rows = [dict(zip(head, head))] + list(book["sheets"].get(sheet) or [])
        for r in rows:
            vals = [r.get(h) for h in head]
            if len(vals) > 1 and str(vals[0] or "").strip().casefold() == "format":
                try:
                    return int(float(vals[1]))
                except (TypeError, ValueError):
                    return None
    return None


def old_shape(book):
    """Turn a reading into the shape the app knows, in place, and return it. A reading under today's names is not
    changed. book["aside"]: {sheet: names kept on their sheet without being used}; book["leave"]: sheets the app reads
    and does not write; book["plain"]: sheets found under the plain names."""
    book.setdefault("aside", {})
    for sheet in list(book.get("sheets") or {}):
        if sheet in NAMES:
            _rename(book, sheet)
    _fonts(book)
    _table_types(book)                                  # before the values: it tells a line taken away from a blank
    for sheet in list(book.get("sheets") or {}):
        _values(book, sheet)
    _page_setups(book)
    for sheet in ("Table types", "Page setups"):
        if sheet in book.get("plain", ()) and _col(book["headers"].get(sheet) or [], "Name (value)") is None:
            _own_name(book, sheet)
    _lists(book)
    book["aside"].setdefault("Table looks", set()).update(MACRO_LOOKS)
    return book
