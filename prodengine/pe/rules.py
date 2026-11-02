"""ProposalEngine standards model: the rule tables of v1.43, as one readable structure the app owns.

Layers (later wins): company -> template type -> effort (this RFP). A layer holds only what it changes;
a blank (None) value means "not set here", and a value that no layer sets means "do not examine, do not write"
(the v1.43 rule). Row looks are shared by every table type; a table type may override single values of a role.

Everything here is plain data (dicts, lists, str, int, float, bool, None) so it saves as JSON, exports to
Excel for review, and diffs cleanly. Nothing is guessed: every value comes from a layer.
"""
import copy
import json

ROLES = ("caption", "header", "header2", "subhead", "body", "subtotal", "total", "note", "keep")
EDGES = ("top", "bottom", "left", "right", "inside_v")

# ---------------------------------------------------------------- company standard (sample values from the brief)
COMPANY = {
    "id": "company",
    "name": "Company standard",
    "variables": {           # format variables; each drives styles (see VARIABLE_TARGETS)
        "body_font": "Times New Roman", "body_size": 11, "table_font": "Arial", "table_size": 9,
        "caption_font": "Arial", "caption_size": 10, "space_after_body": 6, "line_spacing": "single",
        "margin_top": 1.0, "margin_bottom": 1.0, "margin_left": 1.0, "margin_right": 1.0,
        "paper": "Letter", "heading1_size": 14,
    },
    "row_types": {           # shared look of every table row role
        "caption": {"tag_style": "PE Table Caption", "font": "=caption_font", "size": "=caption_size", "bold": True,
                    "align": "left", "before": 3, "after": 3, "fill": None, "valign": "center", "repeat": True,
                    "merge": True, "edges": {"top": None, "bottom": [1.0, "1F3864"], "left": None, "right": None,
                                             "inside_v": None}},
        "header": {"tag_style": "PE Table Header", "font": "=table_font", "size": "=table_size", "bold": True,
                   "align": "left", "before": 2, "after": 2, "fill": "1F3864", "color": "FFFFFF", "valign": "center",
                   "repeat": True, "merge": False,
                   "edges": {"top": [1.0, "1F3864"], "bottom": [1.0, "1F3864"], "left": [0.5, "1F3864"],
                             "right": [0.5, "1F3864"], "inside_v": [0.5, "FFFFFF"]}},
        "header2": {"tag_style": "PE Table Header 2", "font": "=table_font", "size": "=table_size", "bold": True,
                    "align": "left", "before": 1, "after": 1, "fill": "D9E2F3", "valign": "center", "repeat": True,
                    "merge": False, "edges": {"top": [0.5, "8EA9DB"], "bottom": [0.5, "8EA9DB"],
                                              "left": [0.5, "8EA9DB"], "right": [0.5, "8EA9DB"],
                                              "inside_v": [0.5, "8EA9DB"]}},
        "subhead": {"tag_style": "PE Table Subhead", "font": "=table_font", "size": "=table_size", "bold": True,
                    "align": "left", "before": 1, "after": 1, "fill": "D9D9D9", "valign": "center", "repeat": False,
                    "merge": None, "edges": {"top": [0.5, "8EA9DB"], "bottom": [0.5, "8EA9DB"],
                                             "left": [0.5, "8EA9DB"], "right": [0.5, "8EA9DB"],
                                             "inside_v": [0.5, "8EA9DB"]}},
        "body": {"tag_style": "PE Table Text", "font": "=table_font", "size": "=table_size", "bold": False,
                 "align": "left", "before": 1, "after": 1, "fill": None, "valign": "top", "repeat": False,
                 "merge": False, "edges": {"top": [0.5, "8EA9DB"], "bottom": [0.5, "8EA9DB"],
                                           "left": [0.5, "8EA9DB"], "right": [0.5, "8EA9DB"],
                                           "inside_v": [0.5, "8EA9DB"]}},
        "subtotal": {"tag_style": "PE Table Subtotal", "font": "=table_font", "size": "=table_size", "bold": True,
                     "align": "left", "before": 1, "after": 1, "fill": None, "valign": "top", "repeat": False,
                     "merge": False, "edges": {"top": [0.75, "1F3864"], "bottom": [0.5, "8EA9DB"],
                                               "left": [0.5, "8EA9DB"], "right": [0.5, "8EA9DB"],
                                               "inside_v": [0.5, "8EA9DB"]}},
        "total": {"tag_style": "PE Table Total", "font": "=table_font", "size": "=table_size", "bold": True,
                  "align": "left", "before": 1, "after": 1, "fill": "E8EEF7", "valign": "top", "repeat": False,
                  "merge": False, "edges": {"top": [1.5, "1F3864"], "bottom": [1.0, "1F3864"],
                                            "left": [0.5, "8EA9DB"], "right": [0.5, "8EA9DB"],
                                            "inside_v": [0.5, "8EA9DB"]}},
        "note": {"tag_style": "PE Table Note", "font": "=table_font", "size": 8, "bold": False, "italic": True,
                 "align": "left", "before": 1, "after": 1, "fill": None, "valign": "top", "repeat": False,
                 "merge": True, "edges": {"top": [1.0, "1F3864"], "bottom": None, "left": None, "right": None,
                                          "inside_v": None}},
    },
    "table_types": {         # what differs between table types: columns, special rows, overrides of a role
        "std": {"name": "Standard data table", "width_pct": 100, "align": "center",
                "cell_margins": {"top": 2, "bottom": 2, "left": 5, "right": 5}, "roles": list(ROLES), "override": {}},
        "kp": {"name": "Key personnel table", "width_pct": 100, "align": "center",
               "cell_margins": {"top": 3, "bottom": 3, "left": 6, "right": 6},
               "roles": ["caption", "header", "body", "note"],
               "override": {"header": {"fill": "D9E2F3", "color": "000000"}}},
        "cm": {"name": "Compliance matrix", "width_pct": 100, "align": "center",
               "cell_margins": {"top": 1, "bottom": 1, "left": 4, "right": 4}, "roles": list(ROLES),
               "override": {"header": {"fill": "404040"}, "body": {"size": 8}}},
        "fig": {"name": "Figure table", "width_pct": 100, "align": "center",
                "cell_margins": {"top": 0, "bottom": 0, "left": 0, "right": 0},
                "roles": ["body", "caption"], "caption_position": "below", "override": {
                    "caption": {"tag_style": "PE Figure Caption", "align": "center",
                                "edges": {"top": None, "bottom": None, "left": None, "right": None, "inside_v": None}},
                    "body": {"tag_style": "PE Figure", "edges": {"top": None, "bottom": None, "left": None,
                                                                 "right": None, "inside_v": None}}}},
    },
    # Row classification, in order. kind: what the rule looks at. sure=True applies it; sure=False asks.
    # Position rules only where they are reliable (caption row 1, header row 2, note last row), as decided.
    "row_rules": [
        {"key": "R10", "kind": "caption_row", "role": "caption", "sure": True,
         "why": "Row 1 holds a caption (a Table or Figure label with a SEQ field or a number)"},
        {"key": "R20", "kind": "header_row", "role": "header", "sure": True,
         "why": "The row right after the caption row, marked to repeat or bold"},
        {"key": "R25", "kind": "header_row2", "role": "header2", "sure": True,
         "why": "Directly under the header, also marked to repeat"},
        {"key": "R30", "kind": "fill_in", "value": ["D9D9D9", "BFBFBF", "EDEDED"], "role": "subhead", "sure": True,
         "why": "Gray fill"},
        {"key": "R40", "kind": "first_cell_starts", "value": ["Subtotal"], "role": "subtotal", "sure": True,
         "why": "First text cell starts with Subtotal"},
        {"key": "R41", "kind": "first_cell_starts", "value": ["Total", "Grand total"], "role": "total", "sure": True,
         "why": "First text cell starts with Total"},
        {"key": "R45", "kind": "first_cell_contains_word", "value": ["total"], "role": "subtotal", "sure": False,
         "why": "Says total but not at the start; could be a subtotal or a total"},
        {"key": "R50", "kind": "first_cell_starts", "value": ["Note", "Notes", "Source", "*"], "role": "note",
         "sure": True, "why": "Starts with Note, Notes or Source"},
        {"key": "R55", "kind": "last_row_merged", "role": "note", "sure": False,
         "why": "The last row is one merged cell but does not start with Note or Source"},
        {"key": "R90", "kind": "single_merged_cell", "role": "subhead", "sure": False,
         "why": "One cell across the table with no fill: a subhead without the gray fill?"},
        {"key": "R91", "kind": "bold_row", "role": "subhead", "sure": False,
         "why": "Only bold text: a subhead without the gray fill?"},
        {"key": "R99", "kind": "other", "role": "body", "sure": True, "why": "A data row"},
    ],
    "captions": [            # v1.43 Captions table
        {"label": "Table", "part": "body", "position": "above", "chapter_level": 1, "separator": "-",
         "identifier": "Table", "after_number": "period_tab", "style": "Caption"},
        {"label": "Table", "part": "appendix", "position": "above", "chapter_level": 7, "separator": "-",
         "identifier": "TableApp", "after_number": "period_tab", "style": "Caption"},
        {"label": "Figure", "part": "body", "position": "below", "chapter_level": 1, "separator": "-",
         "identifier": "Figure", "after_number": "period_tab", "style": "Caption"},
        {"label": "Figure", "part": "appendix", "position": "below", "chapter_level": 7, "separator": "-",
         "identifier": "FigureApp", "after_number": "period_tab", "style": "Caption"},
    ],
    "toc": {
        "levels": [["Heading 1", 1], ["Heading 2", 2], ["Heading 3", 3], ["Heading 7", 1], ["Heading 8", 2]],
        "switches": ["\\h", "\\z"], "title_style": "TOC Heading",
        "entry_styles": {   # TabsLists rows for TOC styles: number at, text at, right indent, tab stop (in)
            "TOC 1": {"number_at": 0.0, "text_at": 0.4, "right_indent": 0.5, "tab": [6.5, "right", "dot"]},
            "TOC 2": {"number_at": 0.2, "text_at": 0.7, "right_indent": 0.5, "tab": [6.5, "right", "dot"]},
            "TOC 3": {"number_at": 0.4, "text_at": 1.0, "right_indent": 0.5, "tab": [6.5, "right", "dot"]},
            "Table of Figures": {"number_at": 0.0, "text_at": 1.0, "right_indent": 0.5, "tab": [6.5, "right", "dot"]},
        },
        "lists": [{"title": "List of Tables", "identifiers": ["Table", "TableApp"]},
                  {"title": "List of Figures", "identifiers": ["Figure", "FigureApp"]}],
    },
    # FontRules (v1.43): blank values are not examined; the effort lead types them from each RFP
    "fonts": {k: {"min_size": None, "fonts": None, "rfp_ref": ""} for k in
              ("body", "heading", "table", "caption", "header_footer", "footnote", "graphic")},
}


# ---------------------------------------------------------------- pages, sections, headers and footers
# A pagination scheme is an ordered list of parts. Each part says how it is found, how its pages are numbered,
# and what its header and footer carry. Any mix is possible: roman caps front matter then continuous, straight
# through, chapter-page per Heading 1, appendix letter-page per Heading 7, numbered sections.
# starts: how the part's first section is recognised
#   {"first_section": True} | {"style": "TOC Heading"} | {"style": "Heading 1"} | {"bookmark": "_PEPNCV"}
# numbers: None (no page number) or {"fmt": decimal|lowerRoman|upperRoman|upperLetter|lowerLetter,
#   "restart": "part" (at the part's first section) | "each" (at every section that starts with chapter_style)
#   | "never", "start_at": 1, "chapter_level": None|1..9, "separator": hyphen|period|colon|emDash|enDash}
# chapter_style: the heading that starts a chapter in this part (each chapter is its own section when restart is each)
PAGE_FORMATS = ("decimal", "lowerRoman", "upperRoman", "lowerLetter", "upperLetter")
SEPARATORS = {"hyphen": "-", "period": ".", "colon": ":", "enDash": "\u2013", "emDash": "\u2014"}

PAGINATION_PRESETS = {
    "team": {"name": "Team standard: i, 1-1, A-1", "parts": [
        {"key": "cover", "name": "Cover", "starts": {"first_section": True}, "numbers": None,
         "header": "", "footer_marking": False, "linked": False},
        {"key": "front", "name": "Front matter", "starts": {"style": "TOC Heading"},
         "numbers": {"fmt": "lowerRoman", "restart": "part", "start_at": 1, "chapter_level": None},
         "header": "{volume_name}", "footer_marking": True, "linked": False},
        {"key": "body", "name": "Response", "starts": {"style": "Heading 1"}, "chapter_style": "Heading 1",
         "numbers": {"fmt": "decimal", "restart": "each", "start_at": 1, "chapter_level": 1, "separator": "hyphen"},
         "header": "{volume_name}", "footer_marking": True, "linked": False},
        {"key": "appendix", "name": "Appendices", "starts": {"style": "Heading 7"}, "chapter_style": "Heading 7",
         "numbers": {"fmt": "decimal", "restart": "each", "start_at": 1, "chapter_level": 7, "separator": "hyphen"},
         "header": "{volume_name}", "footer_marking": True, "linked": True}]},
    "caps_roman_continuous": {"name": "I, II front matter, then 1, 2, 3 through", "parts": [
        {"key": "cover", "name": "Cover", "starts": {"first_section": True}, "numbers": None, "header": "",
         "footer_marking": False, "linked": False},
        {"key": "front", "name": "Front matter", "starts": {"style": "TOC Heading"},
         "numbers": {"fmt": "upperRoman", "restart": "part", "start_at": 1, "chapter_level": None},
         "header": "{volume_name}", "footer_marking": True, "linked": False},
        {"key": "body", "name": "Response and appendices", "starts": {"style": "Heading 1"},
         "numbers": {"fmt": "decimal", "restart": "part", "start_at": 1, "chapter_level": None},
         "header": "{volume_name}", "footer_marking": True, "linked": False}]},
    "straight": {"name": "Straight through: 1, 2, 3", "parts": [
        {"key": "all", "name": "Whole volume", "starts": {"first_section": True},
         "numbers": {"fmt": "decimal", "restart": "part", "start_at": 1, "chapter_level": None},
         "header": "{volume_name}", "footer_marking": True, "linked": False}]},
}

PAGE_SETUPS = {   # PageSetup table of v1.43 (inches)
    "portrait": {"name": "Letter portrait, 1 in", "w": 8.5, "h": 11, "orient": "portrait",
                 "top": "=margin_top", "bottom": "=margin_bottom", "left": "=margin_left", "right": "=margin_right",
                 "header": 0.5, "footer": 0.5},
    "landscape": {"name": "Letter landscape, 1 in", "w": 11, "h": 8.5, "orient": "landscape",
                  "top": 1, "bottom": 1, "left": 1, "right": 1, "header": 0.5, "footer": 0.5,
                  "rules": {"restart": False, "linked": True}},
    "tabloid": {"name": "Tabloid landscape foldout", "w": 17, "h": 11, "orient": "landscape",
                "top": 0.75, "bottom": 0.75, "left": 0.75, "right": 0.75, "header": 0.4, "footer": 0.4,
                "rules": {"restart": False, "linked": True}},
}

# ---------------------------------------------------------------- lists (TabsLists list rows)
LISTS = {
    "bullet_styles": ["List Bullet", "List Bullet 2", "List Bullet 3"],
    "number_styles": ["List Number", "List Number 2", "List Number 3"],
    "typed_bullets": ["\u2022", "\u00b7", "\u25aa", "\u25e6", "o", "-", "\u2013", "*", "\u27a2", "\u2023", "\uf0b7"],
    "number_levels": {"decimal": 1, "letter": 2, "roman": 3},    # typed 1. -> List Number, a. -> 2, i. -> 3
    "indent_levels": [0.25, 0.5, 0.75],                           # left indent (in) of levels 1..3, for a guess
    "restart_after_heading": True,                                # a list after a heading always starts at 1
    "heading_styles": ["Heading 1", "Heading 2", "Heading 3", "Heading 4", "Heading 5", "Heading 6",
                       "Heading 7", "Heading 8", "Heading 9"],
    "skip_styles": ["Caption", "TOC 1", "TOC 2", "TOC 3", "Table of Figures", "TOC Heading", "Title"],
}

# ---------------------------------------------------------------- terms (banned, auto-replace, marks, dictionaries)
TERMS = {
    "banned": [   # find: word or phrase (case-insensitive, whole words); suggest: "" = report only
        {"find": "world-class", "suggest": "", "why": "Unsupported claim; show the evidence instead"},
        {"find": "best-in-class", "suggest": "", "why": "Unsupported claim"},
        {"find": "seamless", "suggest": "", "why": "Unsupported claim"},
        {"find": "utilize", "suggest": "use", "why": "Plain language"},
        {"find": "in order to", "suggest": "to", "why": "Plain language"},
        {"find": "we will strive to", "suggest": "we will", "why": "Weak commitment"},
    ],
    "replace": [  # applied with Fix all; case "exact" or "match" (keeps the first capital)
        {"find": "recieve", "replace": "receive", "case": "match", "why": "Common misspelling"},
        {"find": "seperate", "replace": "separate", "case": "match", "why": "Common misspelling"},
        {"find": "acheive", "replace": "achieve", "case": "match", "why": "Common misspelling"},
    ],
    "dictionaries": {   # exported for Word: .dic files are words Word accepts; the .lex file is words Word flags
        "PE_Team.dic": {"kind": "accept", "lists": ["team_terms"]},
        "PE_Names.dic": {"kind": "accept", "lists": ["employee_names"]},
        "PE_Acronyms.dic": {"kind": "accept", "lists": ["acronyms"]},
        "ExcludeDictionaryEN0409.lex": {"kind": "exclude", "lists": ["banned_words"]},
    },
    "lists": {
        "team_terms": [],          # the team's custom dictionaries are added for each run
        "employee_names": [],      # the author list is added for each run
        "acronyms": ["CDRL", "IMS", "WBS", "SOW", "PWS", "CONOPS"],
        "banned_words": [],    # filled from single-word banned entries at export
    },
    "name_check": True,        # flag near misses of employee names (one letter off)
}

COMPANY["pagination"] = PAGINATION_PRESETS["team"]
COMPANY["hf_layouts"] = {   # per part of the scheme; tokens: {volume_name} {solicitation} {company} {page} {pages}
    "cover": {"header": {}, "footer": {}},
    "front": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True},
              "footer": {"marking": True, "center": "{page}"}},
    "body": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True},
             "footer": {"marking": True, "center": "{page}"}},
    "appendix": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True},
                 "footer": {"marking": True, "center": "{page}"}},
}
COMPANY["page_setups"] = PAGE_SETUPS
COMPANY["lists"] = LISTS
COMPANY["terms"] = TERMS
COMPANY["variables"].update({"volume_name": "Volume I Technical", "solicitation": "EX-26-R-0001",
    "marking": "Use or disclosure of data contained on this page is subject to the restriction on the title page of this proposal."})

TEMPLATE_TYPES = {
    "dod_tech": {"id": "dod_tech", "name": "DoD technical volume",
                 "variables": {"table_font": "Arial Narrow", "space_after_body": 8, "heading1_size": 16}},
    "nasa": {"id": "nasa", "name": "NASA proposal volume", "variables": {"body_size": 12}},
    "cost": {"id": "cost", "name": "Cost volume", "variables": {"table_size": 8},
             "table_types": {"std": {"override": {"total": {"fill": "D9E2F3"}}}}},
}

# which styles each variable drives (shown in the app; used when variables are injected into a template)
VARIABLE_TARGETS = {
    "body_font": ["Normal", "PE Body Text", "List Bullet", "List Number"],
    "body_size": ["Normal", "PE Body Text", "List Bullet", "List Number"],
    "table_font": ["PE Table Header", "PE Table Header 2", "PE Table Subhead", "PE Table Text", "PE Table Subtotal",
                   "PE Table Total", "PE Table Note"],
    "table_size": ["PE Table Header", "PE Table Header 2", "PE Table Subhead", "PE Table Text", "PE Table Subtotal",
                   "PE Table Total"],
    "caption_font": ["Caption", "PE Table Caption", "PE Figure Caption"],
    "caption_size": ["Caption", "PE Table Caption", "PE Figure Caption"],
    "space_after_body": ["PE Body Text"], "heading1_size": ["Heading 1"],
    "margin_top": ["page setup"], "margin_bottom": ["page setup"], "margin_left": ["page setup"],
    "margin_right": ["page setup"], "paper": ["page setup"], "line_spacing": ["Normal", "PE Body Text"],
}


def deep_merge(base, over):
    """over wins; a None in over means 'not set here' and keeps base; lists are replaced whole."""
    if not isinstance(base, dict) or not isinstance(over, dict):
        return copy.deepcopy(base if over is None else over)
    out = copy.deepcopy(base)
    for k, v in over.items():
        if v is None:
            continue
        out[k] = deep_merge(out.get(k), v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def resolve(company=COMPANY, template_type=None, effort=None):
    """The standards in force, plus where each variable came from."""
    std = copy.deepcopy(company)
    source = {k: company.get("name", "company") for k in company["variables"]}
    for layer in (template_type, effort):
        if not layer:
            continue
        for k, v in (layer.get("variables") or {}).items():
            if v is not None:
                source[k] = layer.get("name", layer.get("id", "?"))
        std = deep_merge(std, {k: v for k, v in layer.items() if k not in ("id", "name")})
    std["variable_source"] = source
    return std


def value(std, v):
    """A row-type value may name a variable ('=table_font')."""
    if isinstance(v, str) and v.startswith("="):
        return std["variables"].get(v[1:])
    return v


def row_look(std, role, table_type):
    """The full look of a role in a table type: the shared row type with the table type's override on top."""
    base = std["row_types"][role]
    tt = std["table_types"].get(table_type, {})
    look = deep_merge(base, (tt.get("override") or {}).get(role, {}))
    return {k: (value(std, v) if k != "edges" else v) for k, v in look.items()}


def validate(std):
    """Problems a person must fix before the standards are used. Empty list = ok."""
    out = []
    for role, rt in std["row_types"].items():
        if role not in ROLES:
            out.append(f"row type {role}: unknown role")
        if not rt.get("tag_style"):
            out.append(f"row type {role}: no tag style")
        for e in EDGES:
            v = (rt.get("edges") or {}).get(e)
            if v is not None and not (isinstance(v, list) and len(v) == 2 and 0 < float(v[0]) <= 6
                                      and isinstance(v[1], str) and len(v[1]) == 6):
                out.append(f"row type {role}: edge {e} must be [width pt, RRGGBB] or empty")
    tags = [rt["tag_style"] for rt in std["row_types"].values()]
    if len(set(tags)) != len(tags):
        out.append("two row types share a tag style (the style is what marks a row's role)")
    for k, tt in std["table_types"].items():
        for r in tt.get("roles", []):
            if r not in std["row_types"] and r != "keep":
                out.append(f"table type {k}: role {r} has no row type")
        for r in (tt.get("override") or {}):
            if r not in std["row_types"]:
                out.append(f"table type {k}: override for unknown role {r}")
    keys = [r["key"] for r in std["row_rules"]]
    if len(set(keys)) != len(keys):
        out.append("two row rules share a key")
    if std["row_rules"][-1]["kind"] != "other":
        out.append("the last row rule must be 'other' so every row gets an outcome")
    for c in std["captions"]:
        if c["position"] not in ("above", "below"):
            out.append(f"caption {c['label']}/{c['part']}: position must be above or below")
    return out


def save(std, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(std, f, indent=1, ensure_ascii=False)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
