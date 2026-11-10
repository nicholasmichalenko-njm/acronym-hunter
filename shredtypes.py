"""What a piece of the customer's text is (4.1.0; claude/stationkeeper-steps-decisions-2026-11-10.md, decisions 2, 13, 14,
17; claude/stationkeeper-shred-plan-4.1.md). The shred says what each piece IS; only Matrix & Outline decides whether it
goes in the matrix and where.

The eight piece types, the team's to rename, recolor, rekey or hide (config piece_types.json): Requirement, Instruction,
Rule, Date, Evaluation, Deliverable, Information, Not applicable.

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
TYPES = (("requirement", "Requirement", "1", "#0D9488", "requirements", True),
         ("instruction", "Instruction", "2", "#16A34A", "requirements", True),
         ("rule", "Rule", "3", "#B45309", "rules", False),
         ("date", "Date", "4", "#1E6B3A", "rules", False),
         ("evaluation", "Evaluation", "5", "#EA580C", "evaluation", True),
         ("deliverable", "Deliverable", "6", "#2563EB", "requirements", True),
         ("information", "Information", "7", "#64748B", "requirements", False),
         ("not_applicable", "Not applicable", "X", "#94A3B8", "requirements", False))
KEYS = tuple(t[0] for t in TYPES)
TABS = (("requirements", "Requirements"), ("rules", "Rules & Dates"), ("evaluation", "Evaluation"), ("acros", "Acros & Abs"))
FILE = "piece_types.json"
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
        json.dump({"format": 1, "types": diff}, f, indent=1)
    os.replace(tmp, p)
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


def type_of(it, captures=()):
    """The piece's type: the one set in the shred, else the one the review gave it, else "" (not sorted yet)."""
    t = it.get(FIELD) or ""
    return t if t in KEYS else from_review(it, captures)


def tab_of(key):
    for k, _n, _s, _c, tab, _p in TYPES:
        if k == key:
            return tab
    return "requirements"                                  # not sorted yet: the Requirements tab, where pieces start


def placed(key):
    """Matrix & Outline > Place offers it: what the proposal must answer."""
    return any(k == key and p for k, _n, _s, _c, _t, p in TYPES)


def counts(items, captures_of=lambda it: ()):
    """{tab: {"total", "unsorted"}} and {type: n} for a set of pieces."""
    by_tab = {k: {"total": 0, "unsorted": 0} for k, _n in TABS}
    by_type = {k: 0 for k in KEYS}
    for it in items:
        t = type_of(it, captures_of(it))
        tab = tab_of(t)
        by_tab[tab]["total"] += 1
        if t:
            by_type[t] += 1
        else:
            by_tab[tab]["unsorted"] += 1
    return by_tab, by_type


def set_type(items, key, log=None):
    """Say what the pieces are. Returns how many changed. The review's own decision is left for Place (4.2.0) except
    Not applicable, which takes a piece out of the answer as Ignore did."""
    if key not in KEYS and key != "":
        raise ValueError(key)
    n = 0
    for it in items:
        if (it.get(FIELD) or "") != key:
            it[FIELD] = key
            n += 1
            if log is not None:
                log(it.get("id", ""), f"shred: {key or 'not sorted'}")
    return n


def merged(types):
    """A deep copy, for a settings dialog to edit."""
    return copy.deepcopy(types)
