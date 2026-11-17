"""Programs (4.50.0): the second kind of home for work, beside Efforts. A program holds program documents; it never shows
an effort's steps, and it has no calendar, no tasks and no owner.

A program is kept the way an effort is (an effort list workbook, its app data folder, a lock) and the registry
(config\\efforts.json) marks it program, as it marks Unfiled unfiled. Its folder is Stationkeeper Data\\Programs\\<name>,
holding <name>_Program_List.xlsx and a Program Documents folder; no proposal folder tree is made in it. Nothing about an
effort's saved files changes.

The effort type Program deliverables is no longer offered when an effort is started. An effort of that type is offered
a move into Programs and is never moved by itself: the person makes it a program, or keeps it as an effort (the answer
is kept). A program that was an effort can be made an effort again. Moving between the two changes only the registry's
marks and writes one line to the home's record; no file moves. Standard library plus the effort modules.
"""
import json
import os
import re

KEY = "program"
TYPE = "program"                     # the effort type id that no longer starts an effort
OUT = ("assign", "matrix", "setups", "drafts", "finalcheck", "calendar", "tasks")   # menu entries a program never shows
DOCS = "Program Documents"
LIST_TAIL = "_Program_List.xlsx"
KEPT = "kept"
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def _info(registry, name):
    return (registry.get(name) or {}) if name else {}


def is_program(registry, name):
    return bool(_info(registry, name).get(KEY))


def names(registry):
    """The programs not archived, A to Z (case ignored)."""
    return sorted((n for n in registry.names() if _info(registry, n).get(KEY) and not _info(registry, n).get("archived")),
                  key=str.casefold)


def effort_names(registry):
    """The homes that are efforts: not a program, not Unfiled, not archived."""
    return [n for n in registry.names() if not any(_info(registry, n).get(k) for k in (KEY, "unfiled", "archived"))]


def programs_dir(data_dir):
    import datahome
    return os.path.join(os.path.dirname(datahome.efforts_dir(data_dir)), "Programs")


def safe_name(name):
    """The name as a folder can hold it: characters a folder cannot have removed, spaces as underscores."""
    return _BAD.sub("", name or "").strip().strip(".").strip().replace(" ", "_")


def check_name(registry, name):
    """'' when the name can be used, else one plain sentence saying why not."""
    import unfiled as UF
    n = (name or "").strip()
    if not n:
        return "Give the program a name."
    if n.casefold() == UF.NAME.casefold():
        return "Unfiled is the name of the work from before. Pick another name."
    if any(x.casefold() == n.casefold() for x in registry.names()):
        return "An effort or a program already has that name. Pick another name."
    if not re.search(r"[A-Za-z0-9]", safe_name(n)):
        return "The name needs at least one letter or digit that a folder name can hold."
    return ""


def create(registry, data_dir, name):
    """Make the program: its list, its Program Documents folder, its registry entry. Returns the name. ValueError with
    check_name's sentence for a name that cannot be used."""
    import effort as E
    why = check_name(registry, name)
    if why:
        raise ValueError(why)
    name = name.strip()
    base = safe_name(name)
    root = os.path.join(programs_dir(data_dir), base)
    k = 2
    while os.path.exists(root):                     # another home's folder of the same safe name: never share it
        root = os.path.join(programs_dir(data_dir), f"{base}_{k}")
        k += 1
    path = os.path.join(root, os.path.basename(root) + LIST_TAIL)
    os.makedirs(root, exist_ok=True)
    L = E.EffortList(path, name)
    L.pending = True
    L.save()
    docs = os.path.join(root, DOCS)
    os.makedirs(docs, exist_ok=True)
    registry.put(name, path=path, program=True, customer_dir=docs, volumes_dir=docs)
    return name


def _settings(registry, name):
    import workspace as W
    path = _info(registry, name).get("path") or ""
    if not path:
        return {}
    try:
        with open(os.path.join(W.data_dir_for(path), "settings.json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def effort_type_of(registry, name):
    """The effort type id kept in that home's settings ('' when there is none or it cannot be read). No folder is made."""
    st = (_settings(registry, name).get("prod_std") or {})
    return (st.get("effort_type") or "") if isinstance(st, dict) else ""


def all_candidates(registry):
    """The efforts of the type Program deliverables, whatever was answered."""
    return [n for n in effort_names(registry) if effort_type_of(registry, n) == TYPE]


def candidates(registry):
    """The efforts of the type Program deliverables still offered the move (not kept as efforts)."""
    return [n for n in all_candidates(registry) if _info(registry, n).get("program_offer") != KEPT]


def keep_as_effort(registry, name):
    if not registry.get(name):
        return False
    registry.put(name, program_offer=KEPT)
    return True


def _log(registry, name, text, who=None):
    import effortrec as R
    import workspace as W
    path = _info(registry, name).get("path") or ""
    data = W.data_dir_for(path) if path else ""
    if data and os.path.isdir(data):
        R.Record(data).log("effort", text, who=who, save=True)


def _movable(registry, name):
    import unfiled as UF
    return bool(registry.get(name)) and not UF.is_unfiled(registry, name) and name != UF.NAME


def make_program(registry, name, who=None):
    """The effort becomes a program: the registry's marks and one line in its record. Nothing on disk moves and its
    effort type is left as it is. False for Unfiled or a name the registry does not know."""
    if not _movable(registry, name):
        return False
    registry.put(name, program=True, was_effort=True)
    _log(registry, name, "Became a program (moved from Efforts to Programs; no file moved)", who)
    return True


def make_effort(registry, name, who=None):
    """The program becomes an effort again: the registry's mark and one line in its record."""
    if not _movable(registry, name):
        return False
    registry.put(name, program=False, program_offer=KEPT)     # the person just chose: it is not offered again by itself
    _log(registry, name, "Became an effort again (moved from Programs to Efforts; no file moved)", who)
    return True


def summary(registry, name):
    """{name, documents, missing, was_effort} read from the program's files (no folder is made)."""
    import workspace as W
    info = _info(registry, name)
    path = info.get("path") or ""
    out = {"name": name, "documents": 0, "missing": not (path and os.path.isfile(path)), "was_effort": bool(info.get("was_effort"))}
    if out["missing"]:
        return out
    docs = os.path.join(W.data_dir_for(path), "documents")
    if os.path.isdir(docs):
        try:
            import docversions as DV
            out["documents"] = len(DV.Library(docs).load().all)
        except Exception:  # noqa: BLE001  a library that cannot be read counts none
            pass
    return out


def count_text(n):
    if not n:
        return "No program documents yet"
    return "1 program document" if n == 1 else f"{n} program documents"
