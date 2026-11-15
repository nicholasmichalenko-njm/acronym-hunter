"""The styles a Quick Part uses (4.37.0; ST27 of 2026-11-14, step 1). A Quick Part is written in styles: its paragraphs,
its runs and its tables each name one. A template made from a Quick Part set and style sets that lack one of those
styles takes the style from the Quick Part's own file, as that file had it, outside the standards
(prodquickparts.sync_styles). This module reads which styles each Quick Part uses, from its kept source file, only read:
of_file (every entry of a file), of_item (one Quick Part of the library), state (each used style and whether a group of
style names has it), missing (a template's Quick Parts against its style sets). Names are compared without regard to
case ("heading 1" is Heading 1) and shown as Word shows them. Nothing is saved; one read per file is remembered while
the program runs. Nothing leaves the PC.

4.38.0 (ST27 step 2): a Quick Part set goes with one style set ("goes_with" on the part set, an optional key): fit says
which styles the set's Quick Parts use that the style set lacks, which of those the library holds (add_missing puts them
in the style set) and which it does not; offer names the styles a file's own styles hold that the Quick Parts being
brought in use and the library lacks, so parts and styles arrive together."""
import os

from prodengine.engine.pkg import Package, NS
from prodengine.engine.ops import glossary as G

BUILT_IN = ("normal", "default paragraph font", "table normal", "no list")   # every Word file has these
_SEEN = {}                                                                   # {path: (mtime, size, {key: [names]})}


def _w(tag):
    return f"{{{NS['w']}}}{tag}"


def _shown(name):
    import prodlearn
    return prodlearn.shown_style_name(name)


def _names(pkg, g):
    """{style id: name} for the Quick Parts' own styles part, then the document's for an id only it has."""
    out = {}
    own = next((t for (typ, t, mode) in pkg.rels_of(g).values() if typ.endswith("/styles") and mode != "External"), None)
    for part in (pkg.word_part("/styles"), own):                     # the Quick Parts' own names win
        if not part:
            continue
        for s in pkg.tree(part).findall("w:style", NS):
            nm = s.find("w:name", NS)
            if nm is not None and s.get(_w("styleId")):
                out[s.get(_w("styleId"))] = nm.get(_w("val")) or s.get(_w("styleId"))
    return out


def key(name, category=""):
    return f"{name or ''}\n{category or ''}"


def of_file(path):
    """{key(entry name, category): [style names in the order first used]} for a file's Quick Parts; {} when it has none
    or cannot be read."""
    try:
        st = os.stat(path)
    except OSError:
        return {}
    hit = _SEEN.get(path)
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    out = {}
    try:
        pkg = Package(path)
        g = G.gloss_part(pkg)
        names = _names(pkg, g) if g else {}
        for e in (G.entries(pkg) if g else []):
            used = []
            for el in e["el"].iter(_w("pStyle"), _w("rStyle"), _w("tblStyle")):
                nm = _shown(names.get(el.get(_w("val")), el.get(_w("val")) or ""))
                if nm and nm.casefold() not in BUILT_IN and nm not in used:
                    used.append(nm)
            out[key(e["name"], e["category"])] = used
    except Exception:  # noqa: BLE001  a file this reader cannot open uses no style it can name
        out = {}
    _SEEN[path] = (st.st_mtime, st.st_size, out)
    return out


def of_item(lib, it):
    """The style names one Quick Part of the library uses; [] when its kept file is gone."""
    v = lib.values(it) or {}
    src = v.get("source") or ""
    if not src:
        return []
    by = of_file(lib.source_path(src))
    return list(by.get(key(v.get("entry") or lib.base_of(it), v.get("category") or ""))
                or by.get(key(v.get("entry") or lib.base_of(it), "")) or [])


def library_names(lib):
    """Every style name the library holds, in lower case."""
    return {lib.base_of(i).casefold() for i in lib.items if i["kind"] == "style"}


def state(lib, it, names):
    """[(style name, True when names holds it)] for one Quick Part; names are lower case."""
    return [(n, n.casefold() in names) for n in of_item(lib, it)]


def missing(lib, parts, names):
    """[(Quick Part name, [style names it uses that names lacks])] for the template's Quick Parts
    (templatesets.quick_parts rows); names are lower case."""
    out = []
    for e in parts:
        it = lib.get(e["id"])
        lost = [n for n, ok in (state(lib, it, names) if it else []) if not ok]
        if lost:
            out.append((e["name"], lost))
    return out


def words(pairs, limit=4):
    """'Callout Text (Callout Box), Table Text Small (Risk Table)' for missing()'s result."""
    bits = [f"{n} ({part})" for part, lost in pairs for n in lost]
    return ", ".join(bits[:limit]) + (f" and {len(bits) - limit} more" if len(bits) > limit else "")


# ------------------------------------------------------------------ 4.38.0: a Quick Part set goes with a style set
def goes_with(lib, part_sid):
    """The style set this part set goes with, or None."""
    k = lib.kit(part_sid) if part_sid else None
    g = lib.kit(k.get("goes_with")) if k and k.get("goes_with") else None
    return g if g is not None and g.get("kind", "style") == "style" else None


def set_goes_with(lib, part_sid, style_sid):
    """Ties the part set to a style set ('' or None unties). False for a set that is not there or of the wrong kind."""
    k = lib.kit(part_sid) if part_sid else None
    g = lib.kit(style_sid) if style_sid else None
    if k is None or k.get("kind") != "part" or (style_sid and (g is None or g.get("kind", "style") != "style")):
        return False
    if style_sid:
        k["goes_with"] = style_sid
    else:
        k.pop("goes_with", None)
    lib.save()
    return True


def set_names(lib, style_sid):
    """The style names a style set holds, in lower case."""
    k = lib.kit(style_sid) if style_sid else None
    return {lib.base_of(i).casefold() for i in (lib.get(x) for x in (k or {}).get("items", [])) if i is not None}


def names_for(lib, part_sid):
    """(names to hold the Quick Parts against, True when they are a tied style set's): the tied set's styles, or
    every style of the library when the part set is tied to none."""
    g = goes_with(lib, part_sid)
    return (set_names(lib, g["id"]), True) if g else (library_names(lib), False)


def _held(lib, name):
    """The library's style of this name to offer a set: the Latest of its first version line; None when it has none."""
    import stylehistory as SH
    hits = [i for i in lib.items if i["kind"] == "style" and lib.base_of(i).casefold() == name.casefold()]
    if not hits:
        return None
    first = next((i for i in hits if not SH.line_of(i)), hits[0])
    return SH.top(lib, first["id"]) or first


def fit(lib, part_sid):
    """How a part set's Quick Parts fit the style set it goes with: {"style_set" (or None), "missing": [(Quick Part,
    [style names])], "can_add": [library items], "absent": [names the library lacks]}."""
    g = goes_with(lib, part_sid)
    k = lib.kit(part_sid) if part_sid else None
    out = {"style_set": g, "missing": [], "can_add": [], "absent": []}
    if g is None or k is None:
        return out
    names = set_names(lib, g["id"])
    seen = set()
    for pid in k["items"]:
        it = lib.get(pid[2:]) if pid.startswith("q:") else None
        lost = [n for n, ok in (state(lib, it, names) if it else []) if not ok]
        if lost:
            out["missing"].append((lib.base_of(it), lost))
        for n in lost:
            if n.casefold() in seen:
                continue
            seen.add(n.casefold())
            have = _held(lib, n)
            out["can_add"].append(have) if have else out["absent"].append(n)
    return out


def add_missing(lib, part_sid):
    """Puts the styles the library holds into the style set the part set goes with. Returns how many went in."""
    import stylelib as SL
    f = fit(lib, part_sid)
    if f["style_set"] is None or not f["can_add"]:
        return 0
    SL.add_to_set(lib, f["style_set"]["id"], [i["id"] for i in f["can_add"]])
    return len(f["can_add"])


def offer(lib, path, gallery):
    """The styles to bring in with a file's Quick Parts: stylelib.read_styles rows for the styles the kept entries use,
    that the library lacks and the file's own styles hold. [] when there are none or the file cannot be read."""
    import stylelib as SL
    by = of_file(path)
    have = library_names(lib)
    want = []
    for e in gallery:
        if e.get("keep"):
            for n in by.get(key(e["name"], e.get("category") or ""), []):
                if n.casefold() not in have and n.casefold() not in {w.casefold() for w in want}:
                    want.append(n)
    if not want:
        return []
    try:
        mine = {s["name"].casefold(): s for s in SL.read_styles(path)}
    except Exception:  # noqa: BLE001  a file whose styles this reader cannot open offers none
        return []
    return [mine[n.casefold()] for n in want if n.casefold() in mine]
