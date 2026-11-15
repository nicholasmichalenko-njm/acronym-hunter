"""The styles a Quick Part uses (4.37.0; ST27 of 2026-11-14, step 1). A Quick Part is written in styles: its paragraphs,
its runs and its tables each name one. A template made from a Quick Part set and style sets that lack one of those
styles takes the style from the Quick Part's own file, as that file had it, outside the standards
(prodquickparts.sync_styles). This module reads which styles each Quick Part uses, from its kept source file, only read:
of_file (every entry of a file), of_item (one Quick Part of the library), state (each used style and whether a group of
style names has it), missing (a template's Quick Parts against its style sets). Names are compared without regard to
case ("heading 1" is Heading 1) and shown as Word shows them. Nothing is saved; one read per file is remembered while
the program runs. Nothing leaves the PC."""
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
