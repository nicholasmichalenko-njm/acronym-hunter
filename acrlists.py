"""Named lists in Acronym Finder (3.51.0, brought back from the classic window's scan projects): several saved scans side
by side, each with its own files, results, choices and list, kept on this PC under <config>\\acronym_tool.

The first list is the folder itself (what 3.50.0 kept); every other list is <config>\\acronym_tool\\lists\\<name>.
names(root) / folder(root, name) / create(root, name) / rename(root, old, new) / last(root) / remember(root, name)
add_files(paths, more) / gone_terms(session) / clear_gone(session). Nothing leaves the PC."""
import os
import re

FIRST = "First list"
SUB = "lists"
_LAST = "last_list.txt"
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean(name):
    """A list name that is also a folder name; '' when nothing usable is left."""
    n = " ".join(_BAD.sub(" ", str(name or "")).split()).strip(" .")
    return n[:60]


def folder(root, name):
    return root if (not name or name == FIRST) else os.path.join(root, SUB, name)


def names(root):
    """The first list, then every named list, sorted."""
    d = os.path.join(root, SUB)
    more = sorted((n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))), key=str.casefold) if os.path.isdir(d) else []
    return [FIRST] + [n for n in more if n != FIRST]


def create(root, name):
    """Makes a new, empty list. Returns its name, or '' when the name is empty or taken."""
    n = clean(name)
    if not n or n.casefold() in (x.casefold() for x in names(root)):
        return ""
    os.makedirs(folder(root, n), exist_ok=True)
    return n


def rename(root, old, new):
    """Renames a named list (the first list keeps its name). Returns the new name or ''."""
    n = clean(new)
    if not n or old == FIRST or old not in names(root) or n.casefold() in (x.casefold() for x in names(root) if x != old):
        return ""
    os.rename(folder(root, old), folder(root, n))
    if last(root) == old:
        remember(root, n)
    return n


def last(root):
    """The list open when the window last closed (the first list when none is known or it is gone)."""
    try:
        with open(os.path.join(root, _LAST), encoding="utf-8") as f:
            n = f.read().strip()
    except OSError:
        return FIRST
    return n if n in names(root) else FIRST


def remember(root, name):
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, _LAST), "w", encoding="utf-8") as f:
        f.write(name or FIRST)


def add_files(paths, more):
    """The last scan's files that are still there, then the new ones, each once."""
    out, seen = [], set()
    for p in list(paths or []) + list(more or []):
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen and os.path.isfile(p):
            seen.add(k); out.append(p)
    return out


def gone_terms(session):
    """Terms in the list that the last scan no longer found anywhere (Scan status 'No longer found in ...')."""
    import effort as E
    eff = getattr(session, "effort", None)
    if eff is None:
        return []
    out = []
    for t, row in eff.rows.items():
        st = row.get("Scan status") or ""
        d = session.results.get(t) or {}
        if st.startswith(E.SCAN_GONE) and (not d or d.get("gone")) and not d.get("manual"):
            out.append(t)
    return out


def clear_gone(session):
    """Takes the terms no longer found off the list (the files are untouched). Returns the terms taken off."""
    terms = gone_terms(session)
    if not terms:
        return []
    for t in terms:
        session.effort.remove(t)
        d = session.results.get(t)
        if d is not None and d.get("gone"):
            del session.results[t]
    session._save_effort_list(backup=True)
    session.save()
    return terms
