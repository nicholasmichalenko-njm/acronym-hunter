"""Document types (2.94.0): the kinds of customer document the team works with, each with its default initial, set once
in Settings > Document types, kept in the config folder (doc_types.json) and carried by a team pack.

Each type: its name, its initial (4.24.0: the type's short name, which starts the document's references: RFP-L-4.2.1),
whether its documents are numbered from the first (Amendment: Amd1, Amd2...; kept in the file, no longer a column:
a second document of any type is numbered by itself), whether it builds the matrix by default, and words in a file name that suggest it
(for a type of the team's own; the built-in ones are recognised as before). Renaming a type keeps the old name as an
alias, so documents already filed under it follow. "Other" always stays: a document of no listed type is Other.
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
    {"name": "Other", "initial": "X", "numbered": False, "matrix": False, "words": ""},
]


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
