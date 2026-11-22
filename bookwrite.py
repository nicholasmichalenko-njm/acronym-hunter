"""4.58.0: a standards workbook WRITTEN under the plain column names (release B of the plan for the workbook in the shared
shape; claude/stationkeeper-column-lists-for-both-tools.md, Nicholas 2026-11-19 and 2026-11-22).

bookshape (4.57.0) reads the plain shape back into the one the rest of the app knows. This module is its other half: it
takes the rows standardsbook makes (by the app's own column names) and turns them into the plain shape just before
they go into the file:
- each tab's own column names, with their units (List numbering and Page setups no longer say "Left indent (pt)" for
  inches);
- every column of a tab always there, in the agreed order, in groups that fold;
- choices in Word's own words (Justified, Exactly, "1, 2, 3", Portrait), a switch as TRUE, FALSE or blank, and a
  drop-down on each choice and switch (the same lists as the Stationkeeper Macros' New Workbook);
- an edge as "0.5, 8EA9DB";
- a table type's kinds of row as "Has ... row" columns, and a kind it changes as a look of its own on Table looks,
  named after the type and the kind of row ("Shaded header"; Nicholas 2026-11-22 12:01); two types with the same change
  share one look;
- a page setup's two switches as columns;
- Fonts allowed as one row per font, with Used for; rows the app did not change are written as the workbook had them;
- names separated by semicolons on Authors and Document types.
Rules only (No AI); nothing leaves the PC."""
import json, uuid

import bookshape as BS

# The columns of each tab after the twelve organizing columns (and Volume), in the agreed order.
STYLE_GROUPS = (
    ("Font", ("Font", "Theme font", "Size (pt)", "Bold", "Italic", "Underline", "All caps", "Small caps", "Hidden text",
              "Strikethrough", "Double strikethrough", "Superscript or subscript", "Color (hex)", "Character spacing (pt)",
              "Kerning from (pt)", "Character shading (hex, or none)", "Do not check spelling")),
    ("Paragraph", ("Type", "Based on", "Next style", "Alignment", "Outline level", "Keep with next", "Keep lines together",
                   "Page break before", "Widow control", "No hyphenation")),
    ("Spacing", ("Space before (pt)", "Space after (pt)", "Line spacing (lines, or pt if exact)", "Line rule",
                 "No space between paragraphs of the same style")),
    ("Indents", ("Left indent (pt)", "Right indent (pt)", "First line (pt)", "Hanging (pt)", "Tab stops")),
    ("Borders and shading", ("Border above", "Border below", "Border left", "Border right", "Shading (hex, or none)")),
    ("Other", ("Automatically update", "Linked style", "Locked", "Show in the Styles gallery", "Semi-hidden",
               "Unhide when used", "Order in the gallery")),
)
HAS_COLS = tuple(n for n, _r in BS.HAS)
LOOK_COLS = tuple(n for n, _r in BS.LOOKS)
SWITCH_COLS = tuple(n for n, _k in BS.SWITCHES)
FULL = {
    "Styles": ("Required",) + tuple(c for _g, cs in STYLE_GROUPS for c in cs),
    "Fonts allowed": ("Used for", "Min size (pt)", "Max size (pt)", "RFP reference"),
    "Table looks": ("Row style", "Font", "Size (pt)", "Bold", "Italic", "Color (hex)", "Alignment", "Vertical alignment",
                    "Repeat as header row", "One cell across the table", "Space before (pt)", "Space after (pt)",
                    "Left indent (pt)", "Right indent (pt)", "Edge above", "Edge below", "Edge left", "Edge right",
                    "Edge between columns", "Shading (hex, or none)", "Recognized by", "Tab stops"),
    "Table types": ("Alignment", "Width (%)", "Cell margin top (pt)", "Cell margin bottom (pt)", "Cell margin left (pt)",
                    "Cell margin right (pt)", "Caption position", "Rows may break across pages") + HAS_COLS + LOOK_COLS,
    "Heading numbering": ("Number format", "Number text", "Number at (in)", "Text at (in)", "Restart", "Style"),
    "List numbering": ("List", "Level", "Number format", "Number text", "Font", "Left indent (in)", "Hanging (in)", "Style"),
    "Captions": ("Label", "Part", "Position", "Chapter level", "Separator", "Identifier", "After number", "Style",
                 "Action style"),
    "Page setups": ("Paper width (in)", "Paper height (in)", "Orientation", "Top margin (in)", "Bottom margin (in)",
                    "Left margin (in)", "Right margin (in)", "Header distance (in)", "Footer distance (in)") + SWITCH_COLS,
}
GROUP_OF = {"Styles": {c: g for g, cs in STYLE_GROUPS for c in cs},
            "Table types": dict({c: "Kinds of row" for c in HAS_COLS}, **{c: "Looks" for c in LOOK_COLS})}
# the plain name of each column the app writes today, per tab ("Edge inside, vertical" is only ever read)
PLAIN = {sheet: {old: new for new, old in m.items() if new != "Edge inside, vertical"} for sheet, m in BS.NAMES.items()}
# Word's own words for a choice, by (tab, plain column)
_FMT_OUT = {v: k for k, v in BS._FMT.items()} | {"bullet": "Bullet"}
_ALIGN_OUT = {"left": "Left", "center": "Centered", "right": "Right", "both": "Justified"}
_LOWER_OUT = {"top": "Top", "center": "Center", "bottom": "Bottom", "portrait": "Portrait", "landscape": "Landscape"}
_RULE_OUT = {"exact": "Exactly", "atLeast": "At least"}
WORDS_OUT = {("Heading numbering", "Number format"): _FMT_OUT, ("List numbering", "Number format"): _FMT_OUT,
             ("Styles", "Alignment"): _ALIGN_OUT, ("Table looks", "Alignment"): _ALIGN_OUT,
             ("Table types", "Alignment"): _ALIGN_OUT, ("Styles", "Line rule"): _RULE_OUT,
             ("Table looks", "Vertical alignment"): _LOWER_OUT, ("Page setups", "Orientation"): _LOWER_OUT}
# the drop-downs: the same lists as the macros' New Workbook (SKW_Workbooks.ChoicesFor and SWITCHES, 1.25.0)
SWITCHES = {"Show in menu", "Required", "Bold", "Italic", "All caps", "Small caps", "Hidden text", "Strikethrough",
            "Double strikethrough", "Do not check spelling", "Keep with next", "Keep lines together", "Page break before",
            "Widow control", "No hyphenation", "No space between paragraphs of the same style", "Automatically update",
            "Locked", "Show in the Styles gallery", "Semi-hidden", "Unhide when used", "Repeat as header row",
            "One cell across the table", "Rows may break across pages"} | set(HAS_COLS) | set(SWITCH_COLS)
USE_WORDS = {"body": "body", "heading": "heading", "table": "table", "caption": "caption",
             "header_footer": "header and footer", "footnote": "footnote", "graphic": "graphic"}
KIND_WORDS = {"caption": "caption", "header": "header", "header2": "second header", "subhead": "subhead", "body": "body",
              "subtotal": "subtotal", "total": "total", "note": "notes"}


def choices(sheet, column):
    if column in SWITCHES:
        return ("TRUE", "FALSE")
    c = column.casefold()
    if c == "status":
        return ("Approved", "Draft", "Retired")
    if c == "alignment":
        return ("Left", "Centered", "Right") if sheet == "Table types" else ("Left", "Centered", "Right", "Justified")
    if c == "line rule":
        return ("Multiple", "Exactly", "At least")
    if c == "orientation":
        return ("Portrait", "Landscape")
    if c == "used for":
        return tuple(USE_WORDS.values()) + ("any",)
    return ()


def plain_name(sheet, old):
    return PLAIN.get(sheet, {}).get(old, old)


# ------------------------------------------------------------------ cells
def _edge_out(v):
    if isinstance(v, (list, tuple)) and len(v) == 2:
        try:
            return f"{float(v[0]):g}, {str(v[1]).lstrip('#').upper()}"
        except (TypeError, ValueError):
            return v
    return v


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _flat(d):
    import standardsbook as SB
    return SB._flat(d or {})


# ------------------------------------------------------------------ table types and their looks
def _table_types(book, label):
    """Roles and Override as the plain columns; a kind a type changes becomes a look of its own on Table looks."""
    looks = book.get("Table looks") or []
    by_name = {str(r.get("Name") or "").strip().casefold(): r for r in looks}
    tl = {k: label("Table looks", k) for k in BS.KEYS["Table looks"]}
    made = {}                                                      # look values -> its name, so two types share one
    for r in book.get("Table types") or []:
        roles = r.pop(label("Table types", "roles"), None)
        over = r.pop(label("Table types", "override"), None) or {}
        if isinstance(roles, str):
            roles = json.loads(roles or "null")
        if isinstance(over, str):
            over = json.loads(over or "{}")
        for col, role in BS.HAS:
            r[col] = None if roles is None else role in roles     # no list: every kind (a blank cell, as before)
        display = str(r.get("Name (value)") or r.get("Name") or "").strip()
        for col, role in BS.LOOKS:
            diff = _flat(over.get(role))
            if not diff:
                r[col] = None
                continue
            base = by_name.get(role) or {}                          # in an effort's workbook: only what it changes
            vals = {tl[k]: base.get(tl[k]) for k in BS.KEYS["Table looks"] if base.get(tl[k]) is not None}
            for k, v in diff.items():
                if k in tl:
                    vals[tl[k]] = "none" if v is None and k.startswith("edges.") else v
            sig = json.dumps(vals, sort_keys=True, default=str)
            name = made.get(sig)
            if name is None:
                name = f"{display} {KIND_WORDS[role]}".strip()
                name = name[:1].upper() + name[1:]
                n, have = 2, by_name.get(name.casefold())
                while have is not None and have.get("_made_by") not in (None, sig):
                    name, n = f"{display} {KIND_WORDS[role]} {n}", n + 1
                    have = by_name.get(name.casefold())
                row = have if have is not None else {"ID": uuid.uuid4().hex[:10], "Name": name, "Status": "Approved"}
                for k in BS.KEYS["Table looks"]:
                    row[tl[k]] = vals.get(tl[k])
                row["_made_by"] = sig
                if have is None:
                    looks.append(row)
                    by_name[name.casefold()] = row
                made[sig] = name
            r[col] = name
    for r in looks:
        r.pop("_made_by", None)
    book["Table looks"] = looks


def _page_setups(book, label):
    for r in book.get("Page setups") or []:
        rules = r.pop(label("Page setups", "rules"), None) or {}
        if isinstance(rules, str):
            rules = json.loads(rules or "{}")
        for col, key in BS.SWITCHES:
            r[col] = rules.get(key)


def _sig(fonts, lo, hi, rfp):
    if isinstance(fonts, str):
        fonts = json.loads(fonts or "[]") if fonts.strip()[:1] == "[" else [fonts]
    return (tuple(str(f).strip() for f in fonts or ()), _num(lo), _num(hi), (str(rfp).strip() or None) if rfp else None)


ORG_KEEP = ("Category", "Changed", "Used on", "Set", "Menu group", "Show in menu", "Notes", "Tags", "Owner")


def _fonts(book, meta, label):
    """One row per font with its use. A use the app did not change since it read the workbook keeps the rows the
    workbook had (with their own sizes, notes and IDs); a use it changed gets a row per font, each with the use's sizes
    and the notes and ID of the row it had before, if any. A Draft or Retired font row is always written as it was."""
    L = lambda k: label("Fonts allowed", k)                              # noqa: E731
    plain_rows = list(meta.get("_plain_rows") or [])
    seen = {}
    for k, s in (meta.get("_plain_seen") or {}).items():
        v, _sep, u = k.partition(BS.SEP)
        seen[(v, u)] = _sig(*s)
    model, held = {}, []
    for r in book.get("Fonts allowed") or []:
        key = (str(r.get("Volume") or ""), str(r.get("Name") or "").strip())
        sig = _sig(r.get(L("fonts")), r.get(L("min_size")), r.get(L("max_size")), r.get(L("rfp_ref")))
        if str(r.get("Status") or "Approved") == "Approved":
            model[key] = (sig, r)
        else:
            held.append((key, sig, r))
    same = {k for k, (sig, _r) in model.items() if seen.get(k) == sig}

    def font_of(pr):
        return str(pr.get("Name") or "").strip().casefold()

    def uses_of(pr):
        u = " ".join(str(pr.get("Used for") or "any").split()).casefold()
        v = str(pr.get("Volume") or "")
        return {(v, x) for x in (BS.ALL_USES if u in ("any", "") else (BS.USES.get(u),)) if x}

    out, kept, old = [], set(), {}
    for pr in plain_rows:
        for k in uses_of(pr):
            old.setdefault((font_of(pr),) + k, pr)
        if str(pr.get("Status") or "Approved").strip().casefold() not in ("approved", ""):
            out.append(dict(pr))
            continue
        uses = uses_of(pr)
        if uses and uses <= same:
            out.append(dict(pr))
        elif uses & same:                                               # "any", and some of its uses changed
            for k in sorted(uses & same, key=lambda k: BS.ALL_USES.index(k[1])):
                out.append(dict(pr, **{"Used for": USE_WORDS[k[1]], "ID": uuid.uuid4().hex[:10]}))
        else:
            continue
        kept |= {(font_of(pr),) + k for k in uses & same}
    fresh = [(k, sig, r, "Approved") for k, (sig, r) in model.items() if k not in same] + \
        [(k, sig, r, str(r.get("Status"))) for k, sig, r in held]
    for (vol, use), sig, r, status in fresh:
        for font in sig[0]:
            if (font.casefold(), vol, use) in kept:
                continue
            was = old.get((font.casefold(), vol, use)) or {}
            row = {k: r.get(k) for k in ORG_KEEP if r.get(k) not in (None, "")}
            row.update({k: v for k, v in was.items() if k not in ("Min size (pt)", "Max size (pt)", "RFP reference", "Used for")})
            row.update({"ID": was.get("ID") or uuid.uuid4().hex[:10], "Name": font, "Status": status,
                        "Used for": USE_WORDS.get(use, use), "Min size (pt)": sig[1], "Max size (pt)": sig[2],
                        "RFP reference": sig[3]})
            if vol or "Volume" in r:
                row["Volume"] = vol
            out.append(row)
    book["Fonts allowed"] = out


# ------------------------------------------------------------------ the whole book
def convert(book, metas, label, effort=False):
    """book: {tab: [row dict by the app's column names]}, in place: the plain shape. metas: {tab: book_meta}.
    label(tab, key): the app's column name for a key."""
    _table_types(book, label)
    _page_setups(book, label)
    _fonts(book, metas.get("Fonts allowed") or {}, label)
    for sheet, rows in book.items():
        if sheet == "Fonts allowed":
            continue
        for i, r in enumerate(rows):
            new = {}
            for h, v in r.items():
                p = plain_name(sheet, h)
                if p.startswith("Edge "):
                    v = _edge_out(v)
                w = WORDS_OUT.get((sheet, p))
                if w and isinstance(v, str):
                    v = w.get(v, v)
                new[p] = v
            if sheet == "Styles" and not effort and new.get("Line rule") in (None, "") and \
                    new.get("Line spacing (lines, or pt if exact)") not in (None, ""):
                new["Line rule"] = "Multiple"                       # today's blank, where the style sets a spacing
            rows[i] = new
        if sheet in ("Table types", "Page setups") and all(str(r.get("Name (value)") or "") in ("", str(r.get("Name") or ""))
                                                           for r in rows):
            for r in rows:                                          # one visible Name per row (148), where nothing is lost
                r.pop("Name (value)", None)
    return book


def header(sheet, org, rows, other, own):
    """The tab's columns: the organizing ones, every agreed column in order, any other value the app holds, Other Word
    settings, then the person's own columns that are not agreed ones."""
    full = [c for c in FULL.get(sheet, ()) if c not in org]
    seen = set(org) | set(full) | {other} | set(own)
    extra = []
    for r in rows:
        for h in r:
            if h not in seen and h not in extra and not h.startswith("_"):
                extra.append(h)
    if "Name (value)" in extra:                                     # kept only where it differs from the Name
        extra.remove("Name (value)")
        full = ["Name (value)"] + full
    return list(org) + full + extra + [other] + [h for h in own if h not in full and h not in extra and h not in org]


def group_of(sheet, column, key=None):
    import standardsbook as SB
    g = GROUP_OF.get(sheet, {}).get(column)
    if g:
        return g
    return SB.group_of(key) if key else "Other"


def dress(ws, sheet, head, start):
    """Drop-downs on every choice and switch column, and the agreed columns grouped so they fold."""
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    for i, h in enumerate(head, 1):
        ch = choices(sheet, str(h))
        if not ch:
            continue
        dv = DataValidation(type="list", formula1='"' + ",".join(ch) + '"', allow_blank=True)
        dv.error, dv.errorTitle, dv.showErrorMessage = "Pick one from the list, or leave it blank.", sheet, False
        ws.add_data_validation(dv)
        dv.add(f"{get_column_letter(i)}2:{get_column_letter(i)}5000")
    runs, cur = [], None
    for i, h in enumerate(head[start - 1:], start):
        g = GROUP_OF.get(sheet, {}).get(h) if sheet in GROUP_OF else ("Values" if h in FULL.get(sheet, ()) else None)
        if g and cur and cur[0] == g and cur[2] == i - 1:
            cur[2] = i
        else:
            cur = [g, i, i]
            if g:
                runs.append(cur)
    for _g, a, b in runs:
        ws.column_dimensions.group(get_column_letter(a), get_column_letter(b), outline_level=1)
