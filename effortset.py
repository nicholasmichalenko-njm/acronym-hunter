"""Effort Standards (4.32.0, Standards step 3; Nicholas's decisions ST3 and ST4 of 2026-11-14): an effort's own set
of standards. The set is taken from the Global Standards on this PC the first time the effort opens after this
release (or when it is made) and is independent from then on: a change made on a standards page while the effort is
open changes the effort's set and nothing else. The Global Standards are changed with no effort open.

How: the set is a folder in the effort's working folder holding the same files, under the same names, as the config
folder holds for the parts in OWN. While an effort is open in this program, every module that keeps one of those files
asks base(config_dir) where it is and gets the effort's folder. Nothing is copied back and forth, so a second window
with another effort open, or a crash, cannot mix two sets. Code that means the Global Standards themselves (the
workbook, Update Global Standards) reads inside `with as_global():`.

    OWN                      the parts an effort owns (the others are this PC's lists and what it has learned)
    base(config_dir)         where the OWN files are now: the open effort's set, or the config folder
    enter(config_dir, root)  the effort opens: its set is made when it has none, and is the one in use
    leave()                  the effort closes: the config folder is the one in use again
    info(root)               {"from_version", "taken", "files"}: what the set was when it was taken
    changed(config_dir, root)   the effort's own changes since then, one row a change
    offer(config_dir, root)     what the Global Standards on this PC would change in the set, one row a change
    take(config_dir, root, files=None)   take those changes (every one when None) into the effort's set
    give(config_dir, root, files=None)   the effort's own changes become changes waiting in the Global Standards

Standard library only. Rules only (No AI); nothing leaves the PC."""
import contextlib, datetime, json, os, shutil, threading

import globalstd as GS

FOLDER = "effort_standards"
FILE = "set.json"
FORMAT = 1                                      # formats.py "effort standards"
# what a document is produced to. Left with the PC: the acronym list, dictionaries, fixes, people and the other lists.
OWN = ("standards", "library", "rules", "named", "sections", "outline", "recipes")
_ACTIVE = {}                                    # {"config": abspath, "dir": the open effort's set}
_local = threading.local()


def set_dir(root):
    return os.path.join(root, FOLDER)


def base(config_dir):
    """Where the OWN files are now."""
    if _ACTIVE and not getattr(_local, "glob", 0) and os.path.abspath(config_dir) == _ACTIVE["config"]:
        return _ACTIVE["dir"]
    return config_dir


@contextlib.contextmanager
def as_global():
    """Inside it, on this thread, base() is the config folder: the Global Standards on this PC."""
    _local.glob = getattr(_local, "glob", 0) + 1
    try:
        yield
    finally:
        _local.glob -= 1


def active():
    """The open effort's set folder ("" when no effort is open)."""
    return _ACTIVE.get("dir", "")


def _members(where):
    """{file under the folder, with forward slashes: path} of the OWN parts kept in a config-shaped folder."""
    import teamdata as TD
    out = {}
    specs = GS._specs()
    for k in OWN:
        if k in specs:
            for m, p in TD._members(where, k, specs[k]).items():
                if m.startswith("config/"):
                    out[m[7:]] = p
    return out


def _part_of(rel):
    specs = GS._specs()
    for k in OWN:
        _n, _v, files, folders, _d = specs[k]
        if rel in files or any(rel.startswith(f + "/") for f in folders):
            return specs[k][0]
    return ""


def _shas(where):
    return {m: GS._sha_file(p) for m, p in _members(where).items()}


def _copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst + ".tmp")
    os.replace(dst + ".tmp", dst)


def info(root):
    """What the set was when it was taken ({} when the effort has no set)."""
    try:
        with open(os.path.join(set_dir(root), FILE), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get("files"), dict) else {}
    except (OSError, ValueError):
        return {}


def _save_info(root, d):
    p = os.path.join(set_dir(root), FILE)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(p + ".tmp", p)


def has(root):
    return bool(info(root))


def start(config_dir, root, when=None):
    """Give the effort its set: the OWN files as the config folder holds them now. An effort that has one keeps it."""
    if has(root):
        return info(root)
    for m, p in _members(config_dir).items():
        _copy(p, os.path.join(set_dir(root), m.replace("/", os.sep)))
    d = {"format": FORMAT, "from_version": GS.state(config_dir)["version"],
         "taken": (when or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"), "files": _shas(set_dir(root))}
    _save_info(root, d)
    return d


def enter(config_dir, root, when=None):
    """The effort opens. Returns its info; {} (and nothing is in use but the config folder) when the set cannot be kept."""
    leave()
    try:
        d = start(config_dir, root, when)
    except OSError:
        return {}
    _ACTIVE.update(config=os.path.abspath(config_dir), dir=set_dir(root))
    return d


def leave():
    _ACTIVE.clear()


def _rows(old_of, new_of, names):
    """One row a change between two {file: path} maps (only the files in names)."""
    import globalfolder as GF
    rows = []
    for m in sorted(names):
        a, b = old_of.get(m), new_of.get(m)
        part = _part_of(m)
        vals = GF._values(a, b) if a and b and m.endswith(".json") else None
        if vals:
            rows += [{"part": part, "file": m, "what": w, "old": GF._say(o), "new": GF._say(n)} for w, o, n in vals]
        else:
            rows.append({"part": part, "file": m, "what": os.path.basename(m),
                         "old": "" if a else "(not there)", "new": "changed" if a and b else ("added" if b else "removed")})
    return rows


def changed(config_dir, root):
    """The files the effort itself changed since its set was taken (their names)."""
    was, now = info(root).get("files") or {}, _shas(set_dir(root))
    return sorted(m for m in set(was) | set(now) if was.get(m) != now.get(m))


def offer(config_dir, root):
    """What the Global Standards on this PC would change in the effort's set: {"version", "rows", "files",
    "also_here": the files the effort changed too}. rows is empty when the Global Standards are as the set took them."""
    was = info(root).get("files") or {}
    glob = _members(config_dir)
    gsha = {m: GS._sha_file(p) for m, p in glob.items()}
    mine = _members(set_dir(root))
    files = sorted(m for m in set(was) | set(gsha) if was.get(m) != gsha.get(m)
                   and gsha.get(m) != (GS._sha_file(mine[m]) if m in mine else None))
    return {"version": GS.state(config_dir)["version"], "files": files, "rows": _rows(mine, glob, files),
            "also_here": [m for m in files if m in changed(config_dir, root)]}


def take(config_dir, root, files=None, when=None):
    """Take the Global Standards' changes into the effort's set: every offered file, or the ones named. A file the
    effort changed too is replaced (the offer names it first). Returns how many files changed."""
    of = offer(config_dir, root)
    glob = _members(config_dir)
    d = info(root)
    n = 0
    for m in of["files"]:
        if files is not None and m not in files:
            continue
        dst = os.path.join(set_dir(root), m.replace("/", os.sep))
        if m in glob:
            _copy(glob[m], dst)
            d["files"][m] = GS._sha_file(dst)
        else:
            try:
                os.remove(dst)
            except OSError:
                pass
            d["files"].pop(m, None)
        n += 1
    if n:
        if files is None or not offer_left(config_dir, root, d):
            d["from_version"] = of["version"]
        d["taken"] = (when or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M")
        _save_info(root, d)
    return n


def give(config_dir, root, files=None):
    """The effort's own changes (every one, or the files named) become changes waiting in the Global Standards on this
    PC: the one way a change made in an effort reaches the others, and it is asked for by name. Returns how many."""
    d = info(root)
    mine = _members(set_dir(root))
    n = 0
    for m in changed(config_dir, root):
        if files is not None and m not in files:
            continue
        dst = os.path.join(config_dir, m.replace("/", os.sep))
        if m in mine:
            _copy(mine[m], dst)
            d["files"][m] = GS._sha_file(dst)
        else:
            try:
                os.remove(dst)
            except OSError:
                pass
            d["files"].pop(m, None)
        n += 1
    if n:
        _save_info(root, d)
        try:
            __import__("teamlib").mark_dirty(config_dir)          # the workbook follows
        except Exception:                                         # noqa: BLE001  the workbook is a copy
            pass
    return n


def offer_left(config_dir, root, d):
    """True when, with this info, the Global Standards would still change something."""
    was = d.get("files") or {}
    gsha = {m: GS._sha_file(p) for m, p in _members(config_dir).items()}
    return any(was.get(m) != gsha.get(m) for m in set(was) | set(gsha))


def line(config_dir, root):
    """The effort's set in one sentence."""
    d = info(root)
    if not d:
        return "This effort has no set of its own yet."
    n = d.get("from_version") or 0
    src = f"Global Standards version {n}" if n else "the Global Standards on this PC"
    k = len(changed(config_dir, root))
    return (f"This effort's standards are its own set, taken from {src} on {d.get('taken', '')}."
            + (f" The effort has changed {k} file{'s' if k != 1 else ''} since." if k else ""))
