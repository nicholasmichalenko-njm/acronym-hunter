"""Document types (2.94.0): the kinds of customer document the team works with, each with its default initial, set once
in Settings > Document types, kept in the config folder (doc_types.json) and carried by a team pack.

Each type: its name, its initial (4.24.0: the type's short name, which starts the document's references: RFP-L-4.2.1),
whether its documents are numbered from the first (Amendment: Amd1, Amd2...; kept in the file, no longer a column:
a second document of any type is numbered by itself), whether it builds the matrix by default, and words in a file name that suggest it
(for a type of the team's own; the built-in ones are recognised as before). Renaming a type keeps the old name as an
alias, so documents already filed under it follow. "Other" always stays: a document of no listed type is Other.

4.86.0 (step I4 of claude/stationkeeper-document-intake-direction-2026-11-24.md, section 7): the built-in list is the
direction's seed (SF 33 / SF 1449, Sections B, C, H, I and K, Exhibit, Wage determination, Pricing template, Past
performance questionnaire, Comment resolution matrix, Industry Day briefing, Evaluation Notice, FPR request, RFI, Sources
Sought). A list the team saved is never changed by itself: missing_new names the new types it lacks, Settings > Document
types offers them (Add them, then Save), and leave_out keeps "Leave them out" on this PC only.
Standard library only.
"""
import json, os, re

FILE = "doc_types.json"
BUILT_IN = [
    {"name": "RFP", "initial": "RFP", "numbered": False, "matrix": True, "words": ""},
    {"name": "Amendment", "initial": "Amd", "numbered": True, "matrix": True, "words": ""},
    {"name": "SOW", "initial": "SOW", "numbered": False, "matrix": True, "words": ""},
    {"name": "SOO", "initial": "SOO", "numbered": False, "matrix": True, "words": ""},
    {"name": "PWS", "initial": "PWS", "numbered": False, "matrix": True, "words": ""},
    {"name": "Section L", "initial": "Sec L", "numbered": False, "matrix": True, "words": ""},
    {"name": "Section M", "initial": "Sec M", "numbered": False, "matrix": True, "words": ""},
    {"name": "Q&A", "initial": "QA", "numbered": False, "matrix": False, "words": ""},
    {"name": "Attachment", "initial": "Att", "numbered": False, "matrix": False, "words": ""},
    {"name": "CDRL", "initial": "CDRL", "numbered": False, "matrix": False, "words": ""},
    {"name": "DD 254", "initial": "DD254", "numbered": False, "matrix": False, "words": ""},
    {"name": "Contract", "initial": "Con", "numbered": False, "matrix": False, "words": ""},
    {"name": "Task order", "initial": "TO", "numbered": True, "matrix": True, "words": ""},
    {"name": "Delivery order", "initial": "DO", "numbered": True, "matrix": True, "words": ""},
    # 4.86.0 (step I4 of claude/stationkeeper-document-intake-direction-2026-11-24.md, section 7): the rest of the seed list
    {"name": "SF 33 / SF 1449", "initial": "SF", "numbered": False, "matrix": True, "words": ""},
    {"name": "Section B", "initial": "Sec B", "numbered": False, "matrix": False, "words": ""},
    {"name": "Section C", "initial": "Sec C", "numbered": False, "matrix": True, "words": ""},
    {"name": "Section H", "initial": "Sec H", "numbered": False, "matrix": True, "words": ""},
    {"name": "Section I", "initial": "Sec I", "numbered": False, "matrix": False, "words": ""},
    {"name": "Section K", "initial": "Sec K", "numbered": False, "matrix": False, "words": ""},
    {"name": "Exhibit", "initial": "Exh", "numbered": False, "matrix": False, "words": ""},
    {"name": "Wage determination", "initial": "WD", "numbered": False, "matrix": False, "words": ""},
    {"name": "Pricing template", "initial": "Price", "numbered": False, "matrix": False, "words": ""},
    {"name": "Past performance questionnaire", "initial": "PPQ", "numbered": False, "matrix": False, "words": ""},
    {"name": "Comment resolution matrix", "initial": "CRM", "numbered": False, "matrix": False, "words": ""},
    {"name": "Industry Day briefing", "initial": "IDay", "numbered": False, "matrix": False, "words": ""},
    {"name": "Evaluation Notice", "initial": "EN", "numbered": False, "matrix": True, "words": ""},
    {"name": "FPR request", "initial": "FPR", "numbered": False, "matrix": True, "words": ""},
    {"name": "RFI", "initial": "RFI", "numbered": False, "matrix": True, "words": ""},
    {"name": "Sources Sought", "initial": "SS", "numbered": False, "matrix": True, "words": ""},
    {"name": "Other", "initial": "X", "numbered": False, "matrix": False, "words": ""},
]
NEW_IN_4860 = ("SF 33 / SF 1449", "Section B", "Section C", "Section H", "Section I", "Section K", "Exhibit", "Wage determination",
               "Pricing template", "Past performance questionnaire", "Comment resolution matrix", "Industry Day briefing",
               "Evaluation Notice", "FPR request", "RFI", "Sources Sought")
LEFT_OUT = "doc_types_left_out.json"           # 4.86.0: on this PC only (not carried by the Global Standards)


# The built-in file name patterns, in order (the first that matches wins), for docversions.guess_type (moved here in 4.86.0)
NAME_PATTERNS = ((r"\btask[\s_-]*order\b|\bto[\s_-]?\d{2,4}\b", "Task order"),
                 (r"\bsf[\s_-]*(?:33|1449)\b", "SF 33 / SF 1449"),                        # 4.86.0: the rest of the seed list
                 (r"evaluation[\s_-]*notices?", "Evaluation Notice"),
                 (r"\bfpr\b|final[\s_-]*proposal[\s_-]*revisions?", "FPR request"),
                 (r"sources[\s_-]*sought", "Sources Sought"),
                 (r"industry[\s_-]*day", "Industry Day briefing"),
                 (r"wage[\s_-]*determination", "Wage determination"),
                 (r"past[\s_-]*perf\w*[\s_-]*question|\bppq\b", "Past performance questionnaire"),
                 (r"comment[\s_-]*resolution", "Comment resolution matrix"),
                 (r"(?:pricing|price|cost)[\s_-]*template", "Pricing template"),
                 (r"\brfi\b|request[\s_-]*for[\s_-]*information", "RFI"),
                 (r"\bdelivery[\s_-]*order\b|\bdo[\s_-]?\d{2,4}\b", "Delivery order"),
                 (r"\bidiq\b|\bbase[\s_-]*contract\b|\bcontract\b(?!.*\b(?:amend|mod)\b)", "Contract"),
                 (r"amend|\bamd\b|_amd|amd\d|\bmod\b|\bsf[\s_-]*30\b", "Amendment"), (r"\bsow\b|statement[\s_-]*of[\s_-]*work", "SOW"),
                 (r"\bsoo\b|statement[\s_-]*of[\s_-]*objectives", "SOO"), (r"\bpws\b|performance[\s_-]*work", "PWS"),
                 (r"q\s*&\s*a|questions|\bqa\b", "Q&A"), (r"cdrl", "CDRL"), (r"dd[\s_-]*254", "DD 254"),
                 (r"exhibit|\bexh\b", "Exhibit"),
                 (r"attachment|\batt\b|exhibit|\bj-\d", "Attachment"), (r"section[\s_]*l\b|52[.\s_-]*212[\s_-]*1\b", "Section L"),
                 (r"section[\s_]*m\b|52[.\s_-]*212[\s_-]*2\b", "Section M"), (r"section[\s_]*b\b|pricing[\s_-]*schedule", "Section B"),
                 (r"section[\s_]*c\b", "Section C"), (r"section[\s_]*h\b", "Section H"), (r"section[\s_]*i\b", "Section I"),
                 (r"section[\s_]*k\b|reps[\s_-]*(?:and|&)[\s_-]*certs", "Section K"), (r"\brfp\b|solicitation|\brfq\b", "RFP"))

# 4.86.0 (step I4): a change notice says the customer changed the package (an amendment's SF 30, a Q&A set, an Evaluation
# Notice, an FPR request). A file of one of these types in an add brings up the summary after it (skqt/intakesummary.py)
# even when the add brought no new version. A type the team renamed from one of them is one too.
CHANGE_NOTICES = ("Amendment", "Q&A", "Evaluation Notice", "FPR request")


def is_change_notice(dtype):
    """True for a type that says the customer changed the package (CHANGE_NOTICES), or one renamed from it."""
    import docversions as DV
    t = DV.type_of(dtype)
    if not t:
        return False
    return t in CHANGE_NOTICES or any(new == t and old in CHANGE_NOTICES for old, new in DV.TYPE_ALIAS.items())


def _clean(s, n=40):
    return " ".join(str(s or "").split())[:n]


def clean_initial(text, n=6):
    """An initial: letters, digits and single spaces, at most 6 characters (8 on a document, for its number), as typed (4.24.0: Sec L, Amd); typed all
    in small letters it becomes capitals, as before."""
    t = " ".join(re.sub(r"[^A-Za-z0-9 ]", "", text or "").split())[:n].strip()
    return t.upper() if t == t.lower() else t


def load(config_dir):
    """{"types": [{name, initial, numbered, matrix, words, aliases}]} with the built-in ones when none are saved."""
    d = {}
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    out, seen = [], set()
    for t in d.get("types", []) if isinstance(d.get("types"), list) else []:
        if not isinstance(t, dict) or not _clean(t.get("name")) or _clean(t.get("name")).casefold() in seen:
            continue
        seen.add(_clean(t["name"]).casefold())
        out.append({"name": _clean(t["name"]), "initial": clean_initial(t.get("initial")) or "X", "numbered": bool(t.get("numbered")),
                    "matrix": bool(t.get("matrix")), "words": _clean(t.get("words"), 200),
                    "aliases": [_clean(a) for a in t.get("aliases", []) if _clean(a)][:20]})
    if not out:
        out = [dict(t, aliases=[]) for t in BUILT_IN]
    if "other" not in seen and not any(t["name"] == "Other" for t in out):
        out.append({"name": "Other", "initial": "X", "numbered": False, "matrix": False, "words": "", "aliases": []})
    return {"types": out}


def problems(types):
    """Why a list cannot be saved ([] when it can)."""
    out, seen = [], {}
    for t in types:
        n = _clean(t.get("name"))
        if not n:
            continue
        if n.casefold() in seen:
            out.append(f"{n} is listed twice")
        seen[n.casefold()] = 1
        if not clean_initial(t.get("initial")):
            out.append(f"{n} needs an initial (up to 6 letters and digits)")
    if not seen:
        out.append("Keep at least one type")
    return out


def save(config_dir, types, renamed=None):
    """types: [{name, initial, numbered, matrix, words}] in order; renamed: {old name: new name} (the old name is kept as
    an alias). Returns load()."""
    cur = {t["name"]: t for t in load(config_dir)["types"]}
    renamed = renamed or {}
    out = []
    for t in types:
        n = _clean(t.get("name"))
        if not n:
            continue
        aliases = list((cur.get(n) or {}).get("aliases", []))
        for old, new in renamed.items():
            if new == n and old != n:
                aliases += [old] + list((cur.get(old) or {}).get("aliases", []))
        out.append({"name": n, "initial": clean_initial(t.get("initial")) or "X", "numbered": bool(t.get("numbered")),
                    "matrix": bool(t.get("matrix")), "words": _clean(t.get("words"), 200),
                    "aliases": list(dict.fromkeys(a for a in aliases if a and a != n))})
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, FILE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"types": out}, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    _team_dirty(p)
    apply(config_dir)
    return load(config_dir)


def _saved(config_dir):
    return os.path.isfile(os.path.join(config_dir, FILE))


def _left_out(config_dir):
    try:
        with open(os.path.join(config_dir, LEFT_OUT), encoding="utf-8") as f:
            d = json.load(f) or {}
        return {str(x) for x in d.get("names", [])}
    except (OSError, ValueError, AttributeError):
        return set()


def missing_new(config_dir, types=None):
    """4.86.0: the built-in types new in 4.86.0 that a saved list does not have (by name or an old name) and that were not
    left out on this PC, in the built-in order. [] when no list was saved (the built-in list is in use as it is)."""
    if not _saved(config_dir):
        return []
    have = set()
    for t in types if types is not None else load(config_dir)["types"]:
        have.add(_clean(t.get("name")).casefold())
        have.update(_clean(a).casefold() for a in t.get("aliases", []) or [])
    gone = {n.casefold() for n in _left_out(config_dir)}
    return [dict(t, aliases=[]) for t in BUILT_IN if t["name"] in NEW_IN_4860 and t["name"].casefold() not in have
            and t["name"].casefold() not in gone]


def leave_out(config_dir, names):
    """Remember on this PC that these new types were left out, so they are not offered again here."""
    keep = sorted(_left_out(config_dir) | {str(n) for n in names})
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, LEFT_OUT)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"format": 1, "names": keep}, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return keep


def apply(config_dir):
    """Hand the types to the document library (once at start, and after a change)."""
    import docversions as DV
    T = load(config_dir)["types"]
    DV.set_types(T)
    return T


def _team_dirty(path):
    """4.7.1: the team library's workbook follows a list saved here."""
    try:
        import teamlib
        teamlib.mark_dirty_file(path)
    except Exception:  # noqa: BLE001
        pass
