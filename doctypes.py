"""Document types (2.94.0): the kinds of customer document the team works with, each with its default initial, set once
in Settings > Document types, kept in the config folder (doc_types.json) and carried by a team pack.

Each type: its name, its initial (the letter that starts the document's references: R-L-4.2.1), whether its documents
are numbered (Amendment: A1, A2...), whether it builds the matrix by default, and words in a file name that suggest it
(for a type of the team's own; the built-in ones are recognised as before). Renaming a type keeps the old name as an
alias, so documents already filed under it follow. "Other" always stays: a document of no listed type is Other.
Standard library only.
"""
import json, os, re

FILE = "doc_types.json"
BUILT_IN = [
    {"name": "RFP", "initial": "R", "numbered": False, "matrix": True, "words": ""},
    {"name": "Amendment", "initial": "A", "numbered": True, "matrix": True, "words": ""},
    {"name": "SOW", "initial": "S", "numbered": False, "matrix": True, "words": ""},
    {"name": "SOO", "initial": "O", "numbered": False, "matrix": True, "words": ""},
    {"name": "PWS", "initial": "P", "numbered": False, "matrix": True, "words": ""},
    {"name": "Section L", "initial": "L", "numbered": False, "matrix": True, "words": ""},
    {"name": "Section M", "initial": "M", "numbered": False, "matrix": True, "words": ""},
    {"name": "Q&A", "initial": "Q", "numbered": False, "matrix": False, "words": ""},
    {"name": "Attachment", "initial": "J", "numbered": False, "matrix": False, "words": ""},
    {"name": "CDRL", "initial": "C", "numbered": False, "matrix": False, "words": ""},
    {"name": "DD 254", "initial": "D", "numbered": False, "matrix": False, "words": ""},
    {"name": "Other", "initial": "X", "numbered": False, "matrix": False, "words": ""},
]


def _clean(s, n=40):
    return " ".join(str(s or "").split())[:n]


def clean_initial(text):
    return re.sub(r"[^A-Za-z0-9]", "", text or "").upper()[:6]


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
            out.append(f"{n} needs an initial (letters and digits, up to 6)")
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
    apply(config_dir)
    return load(config_dir)


def apply(config_dir):
    """Hand the types to the document library (once at start, and after a change)."""
    import docversions as DV
    T = load(config_dir)["types"]
    DV.set_types(T)
    return T
