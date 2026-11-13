"""What a piece of the customer's text is (4.1.0; claude/stationkeeper-steps-decisions-2026-11-10.md, decisions 2, 13, 14,
17; claude/stationkeeper-shred-plan-4.1.md). The shred says what each piece IS; only Matrix & Outline decides whether it
goes in the matrix and where.

The nine piece types (4.19.0: Structure, the piece that sets our response structure), the team's to rename, recolor, rekey or hide (config piece_types.json): Requirement, Instruction,
Rule, Date, Evaluation, Deliverable, Information, Not applicable, Structure.

Each type lands on one of Shred's four tabs (Requirements, Rules & Dates, Evaluation; Acros & Abs holds the acronym
list, not a type) and says whether Place offers it (only what the proposal must answer: Requirement, Instruction,
Evaluation, Deliverable).

A piece's type is kept on the item as "piece" (the matrix workbook's Piece column: additive, no format change). An item
from before 4.1.0 has none; type_of works it out from what the review already said: a requirement's L or M
(Instruction, Evaluation, else Requirement), support and the customer's (Information), ignore (Not applicable), and the
captures on the sentence (a submission or formatting rule, a page limit: Rule; a key date: Date; a deliverable;
an evaluation factor or hot button: Evaluation). Nothing is rewritten until someone sets a type.

Rules only (No AI); nothing leaves the PC."""
import copy
import json
import os

# key, name, shortcut, color, tab, placed (offered on Matrix & Outline > Place)
TYPES = (("requirement", "Requirement", "R", "#0D9488", "requirements", True),
         ("instruction", "Content Instruction", "L", "#16A34A", "requirements", True),
         ("rule", "Format & Submission", "U", "#B45309", "rules", False),
         ("date", "Key Date", "D", "#1E6B3A", "rules", False),
         ("evaluation", "Evaluation Criterion", "E", "#EA580C", "evaluation", True),
         ("deliverable", "Deliverable", "V", "#0369A1", "requirements", True),
         ("information", "Information", "G", "#64748B", "requirements", False),
         ("not_applicable", "Not applicable", "X", "#64748B", "requirements", False),
         ("structure", "Response Structure", "O", "#7C3AED", "requirements", False))     # 4.19.0: sets our response structure (structfrom)
KEYS = tuple(t[0] for t in TYPES)
TABS = (("requirements", "Requirements"), ("rules", "Submission Checklist"), ("evaluation", "Evaluation Criteria"), ("acros", "Acronyms"))
FILE = "piece_types.json"
FORMAT = 1
FIELD = "piece"

# what a capture on a sentence says the sentence is (reviewitems.CAPTURES keys)
CAPTURE_TYPE = {"submit": "rule", "format": "rule", "pagelimit": "rule", "written": "rule", "other": "rule",
                "keydate": "date", "deliverable": "deliverable", "factor": "evaluation", "hot": "evaluation"}


def _path(config_dir):
    return os.path.join(config_dir, FILE) if config_dir else ""


def load(config_dir=None):
    """{key: {key, name, short, color, tab, placed, shown}} in order, with the team's changes."""
    saved = {}
    p = _path(config_dir)
    if p and os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            saved = d.get("types", {}) if isinstance(d, dict) else {}
        except (OSError, ValueError):
            saved = {}
    out = {}
    for key, name, short, color, tab, placed in TYPES:
        t = {"key": key, "name": name, "short": short, "color": color, "tab": tab, "placed": placed, "shown": True}
        t.update({k: v for k, v in (saved.get(key) or {}).items() if k in ("name", "short", "color", "shown")})
        out[key] = t
    return out


def save(config_dir, types):
    """Keep only what differs from the built-in types (names, shortcuts, colors, shown)."""
    base = load(None)
    diff = {}
    for k, t in types.items():
        if k in base:
            ch = {f: t[f] for f in ("name", "short", "color", "shown") if f in t and t[f] != base[k][f]}
            if ch:
                diff[k] = ch
    p = _path(config_dir)
    if not p:
        return diff
    os.makedirs(config_dir, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, "types": diff}, f, indent=1)
    os.replace(tmp, p)
    _team_dirty(p)
    return diff


def from_review(it, captures=()):
    """The type an item had before 4.1.0, from its decision, its L or M and the captures on it; "" when undecided."""
    d = it.get("decision") or ""
    if d == "Keep":
        lm = it.get("lm") or ""
        if lm == "L":
            return "instruction"
        if lm == "M":
            return "evaluation"
        for c in captures:
            if CAPTURE_TYPE.get(c) == "deliverable":
                return "deliverable"
        return "requirement"
    if d == "Drop":
        return "not_applicable"
    kinds = [CAPTURE_TYPE[c] for c in captures if c in CAPTURE_TYPE]
    for k in ("rule", "date", "evaluation", "deliverable"):
        if k in kinds:
            return k
    if d in ("Context", "Customer"):
        return "information"
    return ""


SEP = ";"                                             # 4.5.0: several types on one piece, "requirement;date"
ALONE = "not_applicable"                              # Not applicable clears the others; any other type clears it


def _keys(v):
    return [k for k in dict.fromkeys(x.strip() for x in str(v or "").split(SEP)) if k in KEYS]


def types_of(it, captures=()):
    """4.5.0: every type the piece has, in the order set; else the one the review gave it; else [] (not sorted yet)."""
    got = _keys(it.get(FIELD))
    if got:
        return got
    t = from_review(it, captures)
    return [t] if t else []


def has(it, key, captures=()):
    return key in types_of(it, captures)


def type_of(it, captures=()):
    """The piece's first type: the one set in the shred, else the one the review gave it, else "" (not sorted yet)."""
    got = types_of(it, captures)
    return got[0] if got else ""


def tabs_of(it, captures=()):
    """Every Shred tab the piece's types reach (an unsorted piece is on Requirements, where pieces start)."""
    return list(dict.fromkeys(tab_of(t) for t in types_of(it, captures))) or ["requirements"]


def placed_any(keys):
    """Place offers the piece when any of its types is one Place takes."""
    return any(placed(k) for k in keys)


def combine(keys, key, on):
    """The set after putting key on or taking it off: Not applicable stands alone."""
    keys = [k for k in keys if k in KEYS]
    if not on:
        return [k for k in keys if k != key]
    if key == ALONE:
        return [ALONE]
    return [k for k in keys if k != ALONE and k != key] + [key]


def tab_of(key):
    for k, _n, _s, _c, tab, _p in TYPES:
        if k == key:
            return tab
    return "requirements"                                  # not sorted yet: the Requirements tab, where pieces start


def placed(key):
    """Matrix & Outline > Place offers it: what the proposal must answer."""
    return any(k == key and p for k, _n, _s, _c, _t, p in TYPES)


def counts(items, captures_of=lambda it: ()):
    """{tab: {"total", "unsorted"}} and {type: n} for a set of pieces. 4.5.0: a piece counts once in each tab its types
    reach, and once for each of its types."""
    by_tab = {k: {"total": 0, "unsorted": 0} for k, _n in TABS}
    by_type = {k: 0 for k in KEYS}
    for it in items:
        ts = types_of(it, captures_of(it))
        if not ts:
            by_tab["requirements"]["total"] += 1
            by_tab["requirements"]["unsorted"] += 1
            continue
        for tab in dict.fromkeys(tab_of(t) for t in ts):
            by_tab[tab]["total"] += 1
        for t in ts:
            by_type[t] += 1
    return by_tab, by_type


def set_type(items, key, log=None):
    """Say what the pieces are (one type, replacing the rest). Returns how many changed."""
    if key not in KEYS and key != "":
        raise ValueError(key)
    return set_types(items, [key] if key else [], log)


def set_types(items, keys, log=None):
    """4.5.0: the pieces have exactly these types ([] is not sorted). Returns how many changed."""
    keys = [k for k in dict.fromkeys(keys) if k in KEYS]
    if ALONE in keys:
        keys = [ALONE]
    val = SEP.join(keys)
    n = 0
    for it in items:
        if (it.get(FIELD) or "") != val:
            it[FIELD] = val
            n += 1
            if log is not None:
                log(it.get("id", ""), f"shred: {', '.join(keys) or 'no type'}")
    return n


def toggle(items, key, captures_of=lambda it: (), log=None):
    """4.5.0: put the type on every piece, or take it off when every piece has it already. Returns (on, {id: keys})."""
    if key not in KEYS:
        raise ValueError(key)
    on = not all(has(it, key, captures_of(it)) for it in items)
    after = {}
    for it in items:
        keys = combine(types_of(it, captures_of(it)), key, on)
        set_types([it], keys, log)
        after[it.get("id", "")] = keys
    return on, after


def merged(types):
    """A deep copy, for a settings dialog to edit."""
    return copy.deepcopy(types)


def _team_dirty(path):
    """4.7.1: the team library's workbook follows a list saved here."""
    try:
        import teamlib
        teamlib.mark_dirty_file(path)
    except Exception:  # noqa: BLE001
        pass
