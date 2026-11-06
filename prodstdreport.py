"""What retiring Production Standards would lose (3.68.0, Template Studio decision 6: "Production Standards retires after
a one-time nothing-lost comparison"). Production Standards (Advanced) is the full editor over production_standards.json:
the global standard, the volume profiles and the effort types. The newer pages edit most of it; this report says, for
each of its sections, where those values are edited now and which of this PC's own values sit in a section with no other
editor. It also lists the places in the app that still open Production Standards. Nothing is changed.

SECTIONS        (key, title, data keys, where now, status): status is "moved", "partly" or "only here"
report(config_dir) -> {"rows": [...], "links": [...], "verdict", "ready": bool}
Each row: {key, title, status, where, values: [(layer, what)], note}. Rules only; nothing leaves the PC."""
import copy

import prodrules as PRL

MOVED, PARTLY, ONLY = "moved", "partly", "only here"
# key, title, the data keys it edits, where they are edited now, status, what stays only here
SECTIONS = [
    ("profile_parts", "Parts and versions", (), "Effort Profiles (each profile's slots); Template Studio > Anatomy", MOVED, ""),
    ("content_map", "Content map", ("content_map",), "", ONLY, "Which style each kind of placed item takes (the setup "
     "template reads it)"),
    ("variables", "Base fonts and sizes", ("variables",), "Formatting Standards > Font sets; Effort Profiles (base fonts); "
     "Effort Formatting", MOVED, ""),
    ("styledefs", "Styles", ("style_defs", "style_roles"), "Formatting Standards > Paragraph styles and Character styles",
     PARTLY, "Style roles (which style holds the cover title, the legends) that Rule 2 reads"),
    ("fonts", "Font rules", ("fonts",), "Effort Profiles and Effort Formatting: the smallest sizes (the RFP's limits)",
     PARTLY, "Allowed fonts and largest sizes"),
    ("styles", "Allowed styles", ("styles",), "", ONLY, "The allowed styles, hiding unused built-in styles, removing unused "
     "custom styles and the template to merge styles from (Fix a Copy reads them)"),
    ("headnum", "Heading numbering", ("heading_numbering",), "Formatting Standards > Heading numbering", MOVED, ""),
    ("lists", "Lists", ("list_numbering", "lists"), "Formatting Standards > Lists", MOVED, ""),
    ("setups", "Page setups", ("page_setups",), "Formatting Standards > Page setups", MOVED, ""),
    ("quickparts", "Quick Parts", ("quick_parts",), "Quick Parts", MOVED, ""),
    ("ttypes", "Table types", ("table_types",), "Layout > Table looks; Effort Formatting", MOVED, ""),
    ("rows", "Row looks", ("row_types",), "Layout > Table looks", MOVED, ""),
    ("rules", "How rows are recognized", ("row_rules",), "Fix a Copy > How rows are recognized", MOVED, ""),
    ("captions", "Captions", ("captions",), "Layout > Captions; Effort Formatting", MOVED, ""),
    ("hf", "Headers and footers", ("hf_layouts", "hf_designs"), "Layout > Headers and footers; Effort Formatting", MOVED, ""),
    ("toc", "Table of contents", ("toc",), "Layout > Table of contents and lists", MOVED, ""),
    ("fillins", "Fields", ("fill_ins",), "", ONLY, "The fill-in fields a template asks for (Rules > Field recipes holds field "
     "codes, not these)"),
    ("part_cover", "Cover", (), "A view of the values in Sections in order, Headers and footers and Page setups; Layout > Covers; Layout > Sections and section designs", MOVED, ""),
    ("part_front", "Front matter", (), "A view of the values in Sections in order, Headers and footers and Page setups; Template Studio > Parts and numbering; Layout > Sections and section designs", MOVED, ""),
    ("part_body", "Response", (), "A view of the values in Sections in order, Headers and footers and Page setups; Template Studio > Parts and numbering; Layout > Sections and section designs", MOVED, ""),
    ("part_appendix", "Appendices", (), "A view of the values in Sections in order, Headers and footers and Page setups; Template Studio > Parts and numbering; Layout > Sections and section designs", MOVED, ""),
    ("part_backer", "Back cover", (), "A view of the values in Sections in order, Headers and footers and Page setups; Layout > Back covers; Layout > Sections and section designs", MOVED, ""),
    ("pages", "Sections in order", ("pagination", "page_parts"), "Formatting Standards > Pagination schemes; Layout > "
     "Sections; Template Studio > Parts and numbering", MOVED, ""),
    ("terms", "Words to avoid and fix", ("terms",), "Team References > Banned phrases (banned phrases); Technical Edit",
     PARTLY, "Misspellings to fix, trademark and registered marks, and employee names that Fix a Copy reads"),
    ("graphics", "Graphics", ("graphics",), "", ONLY, "The graphics checks (smallest text, resolution, widths, alt text) "
     "Fix a Copy reads"),
    ("office", "Excel and PowerPoint", ("office",), "", ONLY, "The Excel and PowerPoint checks Fix a Copy reads"),
    ("tlibrary", "Template library", (), "Formatting Standards, Quick Parts and Layout (the three libraries)", MOVED, ""),
]
# the places in the app that still open Production Standards, and what each needs before it retires
LINKS = [
    ("Setup page: Make templates and setup...", "Builds the templates through Production Standards' maker; it needs a home "
     "in Templates or Template Studio."),
    ("Effort Formatting: the full editor for this effort", "Opens Production Standards on the effort's own layer for values "
     "Effort Formatting does not name."),
    ("Rules: Edit in Production Standards", "Opens the section a rule reads (cover, styles)."),
    ("Fix a Copy: Production Standards button", "Opens the standard Fix a Copy uses."),
    ("Assignments: Edit the rules in Production Standards", "Opens the rules."),
    ("Formatting Standards: Put in a standard...", "Carries a library item into the global standard, a profile or an "
     "effort type."),
]


def _layers(data):
    """[(layer name, values the person set there)]: the global standard's changes, each volume profile's, each effort
    type's (shared and per profile)."""
    out = [("Global standard", PRL.diff(data["company"], PRL.COMPANY))]
    for t in data.get("types") or []:
        out.append((f"Volume profile {t.get('name', '')}", PRL.layer_of(t)))
    for e in data.get("effort_types") or []:
        out.append((f"Effort type {e.get('name', '')}", PRL.effort_layer_of(e)))
        for pid, lay in (e.get("profile_over") or {}).items():
            out.append((f"Effort type {e.get('name', '')}, {PRL.type_of(data, pid).get('name', '')}", lay or {}))
    return out


def _what(key, v):
    if isinstance(v, dict):
        return f"{key}: {len(v)} value(s)"
    if isinstance(v, list):
        return f"{key}: {len(v)} entr(ies)"
    return f"{key}: {v}"


def report(config_dir, data=None):
    """Every section of Production Standards, where it is edited now, and this PC's own values in it."""
    data = copy.deepcopy(data) if data is not None else PRL.load(config_dir)
    layers = _layers(data)
    rows = []
    for key, title, dkeys, where, status, stays in SECTIONS:
        vals = [(ln, _what(k, lay[k])) for ln, lay in layers for k in dkeys if lay.get(k) not in (None, {}, [], "")]
        rows.append({"key": key, "title": title, "status": status, "where": where or "Nowhere else", "stays": stays,
                     "values": vals, "at_risk": status != MOVED and bool(vals)})
    only = [r for r in rows if r["status"] == ONLY]
    risk = [r for r in rows if r["at_risk"]]
    ready = not only and not [r for r in rows if r["status"] == PARTLY]
    if ready:
        verdict = "Nothing is lost: every section is edited somewhere else. The links below need new homes first."
    else:
        verdict = (f"Not yet. {len(only)} section(s) have no other editor and {sum(1 for r in rows if r['status'] == PARTLY)} "
                   f"are only partly elsewhere. {len(risk)} of them hold values set on this PC, which would be kept but could "
                   "no longer be changed. Move those sections first; then Production Standards can retire.")
    return {"rows": rows, "links": LINKS, "verdict": verdict, "ready": ready, "at_risk": len(risk)}
