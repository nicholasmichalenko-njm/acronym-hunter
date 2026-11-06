"""Outline layouts, set ahead of time (3.73.0, claude/stationkeeper-versions-decisions-2026-11-06.md decision 9).

A layout says, for each kind of column, the heading names it may carry ("Compliance Requirement", "Requirement",
"L Requirement"), and the formatting rules for a column whose cells mix kinds of text, picked by color, italic and bold
("black italic is supporting RFP text"), with no workbook needed. On import the layout that recognizes the most of the
workbook's headings is used (names matched with case, spacing and trailing punctuation ignored); a column no layout
knows is asked about once and remembered as another name (or as a column to leave out). 3.71.0's saved columns and rules
(outline_profiles.json) are read as layouts.

Kept in <config>\\outline_layouts.json: {"format": 1, "layouts": {name: {"names": {role: [heading]}, "skip": [heading],
"rules": {role: [{"color", "italic", "bold", "kind"}]}}}}. The team's data, never in the program folder. Rules only."""
import json, os, re

import outlinexl as OX

FILE = "outline_layouts.json"
FORMAT = 1
STARTING = "Our outline"
STARTING_NAMES = {"section_number": ["Response Section Number"], "section_name": ["Response Section Name"],
                  "reference": ["RFPL Number"], "requirement": ["Compliance Requirement"],
                  "support": ["Supporting RFP Content"], "authors": ["Authors"], "guidance": ["Management Guidance"]}
STARTING_RULES = {"support": [{"color": "auto", "italic": True, "bold": None, "kind": "support"}]}
MIXED = ("requirement", "support", "guidance")


def norm(h):
    """A heading as it is matched: lower case, one space, no trailing colon or period."""
    return " ".join(str(h or "").casefold().replace("\n", " ").split()).rstrip(":.").strip()


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def _from_profile(p):
    """A 3.71.0 saved profile (columns by heading, rules by look key) as a layout."""
    names, rules = {}, {}
    for h, role in (p.get("columns") or {}).items():
        if role and role != "ignore":
            names.setdefault(role, []).append(h)
    for h, by_look in (p.get("rules") or {}).items():
        role = (p.get("columns") or {}).get(h)
        for look, kind in (by_look or {}).items():
            if role and len(look) >= 3:
                rules.setdefault(role, []).append({"color": look[2:], "italic": look[1] == "I", "bold": look[0] == "B", "kind": kind})
    return {"names": names, "skip": [h for h, r in (p.get("columns") or {}).items() if r == "ignore"], "rules": rules}


def load(config_dir):
    """{name: layout}. The starting layout (the column names given) when nothing is saved yet; 3.71.0's profiles read in."""
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    out = {k: v for k, v in (d.get("layouts") or {}).items() if isinstance(v, dict)}
    for name, p in OX.load_profiles(config_dir).items():
        out.setdefault(name, _from_profile(p))
    if not out:
        out[STARTING] = {"names": {k: list(v) for k, v in STARTING_NAMES.items()}, "skip": [],
                         "rules": {k: [dict(r) for r in v] for k, v in STARTING_RULES.items()}}
    return out


def save(config_dir, layouts):
    os.makedirs(config_dir, exist_ok=True)
    p = _path(config_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, "layouts": layouts}, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return layouts


def put(config_dir, name, layout):
    d = load(config_dir)
    key = " ".join(str(name).split()) or STARTING
    d.pop(key, None)                                    # the newest saved comes last: it wins a tie
    d[key] = layout
    return save(config_dir, d)


def known_names(config_dir):
    """Every heading name the saved layouts give (as matched), for finding the header row."""
    return {norm(h) for lay in load(config_dir).values() for hs in (lay.get("names") or {}).values() for h in hs} | \
           {norm(h) for lay in load(config_dir).values() for h in lay.get("skip") or []}


def role_of(layout, header):
    """The role a layout gives a heading: a role, "ignore" (a column it leaves out), or None (it does not know it)."""
    h = norm(header)
    for role, hs in (layout.get("names") or {}).items():
        if h in {norm(x) for x in hs}:
            return role
    if h in {norm(x) for x in layout.get("skip") or []}:
        return "ignore"
    return None


def best(config_dir, headers):
    """(name, layout, known count) of the layout that recognizes the most headings; a tie goes to the newest saved."""
    hs = [h for h in headers if h]
    top = (None, None, -1)
    for name, lay in load(config_dir).items():
        n = sum(1 for h in hs if role_of(lay, h) is not None)
        if n >= top[2]:
            top = (name, lay, n)
    return top


def rule_kind(layout, role, look):
    """The setup kind a look takes in a column with this role, by the layout's rules: the most specific rule that fits
    (a rule names a color, italic or bold; what it leaves out fits anything); between rules as specific, the one listed
    last. None when no rule fits."""
    bold, ital, color = look[0] == "B", look[1] == "I", look[2:]
    fits = []
    for n, r in enumerate((layout.get("rules") or {}).get(role) or []):
        c = (r.get("color") or "").upper().lstrip("#")
        c = "AUTO" if c == "000000" else c
        if c and c != "AUTO" and c != color.upper():
            continue
        if c.upper() == "AUTO" and color != "auto":
            continue
        if r.get("italic") is not None and bool(r["italic"]) != ital:
            continue
        if r.get("bold") is not None and bool(r["bold"]) != bold:
            continue
        fits.append((sum(1 for k in ("color", "italic", "bold") if r.get(k) not in (None, "")), n, r["kind"]))
    return max(fits)[2] if fits else None


def profile(config_dir, book):
    """The import's profile for this workbook from the best layout: {"name", "columns": {heading: role}, "rules":
    {heading: {look: kind}}, "unknown": [headings no layout knows]}. Unknown headings take the 3.71.0 guess, marked."""
    name, lay, _n = best(config_dir, book["headers"])
    lay = lay or {"names": {}, "rules": {}}
    cols, unknown, rules = {}, [], {}
    for h in [h for h in book["headers"] if h]:
        r = role_of(lay, h)
        if r is None:
            unknown.append(h)
            r = OX.guess_one(h)
        cols[h] = r
    for h, role in cols.items():
        if role in MIXED:
            for x in OX.looks(book, h):
                k = rule_kind(lay, role, x["look"])
                if k:
                    rules.setdefault(h, {})[x["look"]] = k
    return {"name": name or "", "columns": cols, "rules": rules, "unknown": unknown}


def remember(config_dir, name, header, role):
    """A heading a layout did not know, kept as another name for its role (or as a column to leave out)."""
    d = load(config_dir)
    lay = d.setdefault(name or STARTING, {"names": {}, "skip": [], "rules": {}})
    for hs in (lay.get("names") or {}).values():
        hs[:] = [x for x in hs if norm(x) != norm(header)]
    lay["skip"] = [x for x in lay.get("skip") or [] if norm(x) != norm(header)]
    if role == "ignore":
        lay["skip"].append(header)
    else:
        lay.setdefault("names", {}).setdefault(role, []).append(header)
    save(config_dir, d)
    return lay


def from_profile(config_dir, name, prof):
    """3.71.0's Save these columns and rules... as a layout: the headings as names, the looks seen as rules."""
    return put(config_dir, name, _from_profile(prof))


def look_key(color, italic, bold):
    """A rule as the look key the workbook reader writes (for showing a sample)."""
    c = (color or "auto").lstrip("#")
    return ("B" if bold else "-") + ("I" if italic else "-") + ("auto" if c.lower() in ("auto", "000000", "") else c.upper())
