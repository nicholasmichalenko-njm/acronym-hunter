"""The Global Standards folder (4.31.0, step 2a of the Standards board of 2026-11-14): numbered versions that a few
people write and every PC reads.

    <folder>\\current.json            {"format", "version", "by", "when", "note"}: the version in use
    <folder>\\v0013\\manifest.json     {"format", "version", "by", "when", "note", "files": {member: sha256},
                                       "parts": {key: {"name", "files": [members]}}}
    <folder>\\v0013\\config\\...  data\\...   every file of the version, under the member name the team data file uses

The folder is a path: a SharePoint library synced to the PC, or any folder. The app makes no network connection. The
lock is the folder's own: someone who can write to it can update the Global Standards (can_update); everyone else
reads. A version folder is written whole under another name, checked, then renamed, and is never edited after. A PC
takes a version only when every file matches the manifest; a half-synced version is skipped and the PC stays on the
one it has.

Words (Nicholas 2026-11-14): update, not publish; changes waiting, not a draft.

    can_update(folder)                    True when this PC can write there
    versions(folder)                      the version numbers the folder holds, sound or not
    read(folder, n)                       the manifest of a sound version, or None
    current(folder)                       the newest sound version's manifest (current.json's when it is sound), or None
    waiting(config_dir, folder)           [{"part", "file", "what", "old", "new"}] this PC's changes against that version
    update(config_dir, folder, by, note)  writes the next version from what this PC holds; returns its manifest
    ready(config_dir, folder)             the manifest of a newer sound version than the PC is on, or None
    take(config_dir, folder, n=None)      puts a version on this PC: {"version", "replaced": [part names], "backup"}
    put_back(config_dir, folder, files)   a waiting change is dropped: those files are as the version has them again
    folder(settings) / set_folder(path)   where this PC reads versions from (Settings > Global Standards)

Standard library only. Rules only (No AI); nothing leaves the PC."""
import datetime, hashlib, json, os, re, shutil

import globalstd as GS
import teamdata as TD

FORMAT = 1
CURRENT, MANIFEST = "current.json", "manifest.json"
SETTING = "global_standards_folder"
BACKUPS = "Global Standards backups"
_VDIR = re.compile(r"^v(\d{4,})$")
MOST_VALUES = 40                       # value-by-value lines for one file; past that the file is one line


def vname(n):
    return f"v{int(n):04d}"


def can_update(folder):
    """True when a small file can be written to the folder and removed again."""
    if not folder or not os.path.isdir(folder):
        return False
    p = os.path.join(folder, f".sk-write-test-{os.getpid()}")
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write("x")
        os.remove(p)
        return True
    except OSError:
        return False


def versions(folder):
    try:
        return sorted(int(m.group(1)) for m in (_VDIR.match(n) for n in os.listdir(folder)) if m)
    except OSError:
        return []


def _json(p):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _member_path(folder, n, member):
    return os.path.join(folder, vname(n), member.replace("/", os.sep))


def read(folder, n):
    """The manifest of version n when every file it names is there and matches; None otherwise."""
    man = _json(os.path.join(folder, vname(n), MANIFEST))
    if not man or man.get("format") != FORMAT or man.get("version") != n or not isinstance(man.get("files"), dict):
        return None
    for member, sha in man["files"].items():
        if not TD._safe_member(member) or GS._sha_file(_member_path(folder, n, member)) != sha:
            return None
    return man


def current(folder):
    """The version in use: the one current.json names when it is sound, else the newest sound one."""
    if not folder or not os.path.isdir(folder):
        return None
    cur = _json(os.path.join(folder, CURRENT)) or {}
    order = ([cur["version"]] if isinstance(cur.get("version"), int) else []) + sorted(versions(folder), reverse=True)
    for n in dict.fromkeys(order):
        man = read(folder, n)
        if man:
            return man
    return None


def _members(config_dir):
    """{member: (part key, local path)} for everything of Global Standards this PC holds."""
    out = {}
    for k, (_name, members) in GS.parts(config_dir).items():
        for m, p in members.items():
            out[m] = (k, p)
    return out


def _flat(d, pre=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flat(v, f"{pre}{k}."))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            name = v.get("name") or v.get("id") if isinstance(v, dict) else None
            out.update(_flat(v, f"{pre}{name if isinstance(name, str) and name else i + 1}."))
    else:
        out[pre[:-1]] = d
    return out


def _values(old_path, new_path):
    """[(what, old, new)] between two JSON files, or None when they are not both JSON objects or differ too widely."""
    a, b = _json(old_path), _json(new_path)
    if a is None or b is None:
        return None
    fa, fb = _flat(a), _flat(b)
    rows = [(k, fa.get(k), fb.get(k)) for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]
    return rows if 0 < len(rows) <= MOST_VALUES else None


def _say(v):
    return "(not set)" if v is None else str(v)


def waiting(config_dir, folder):
    """This PC's changes against the folder's version in use, one row a change: a value of a JSON file by its name, or
    a whole file changed, added or removed. With no version in the folder yet, every file is new."""
    man = current(folder)
    names = GS.names()
    was = (man or {}).get("files") or {}
    n = (man or {}).get("version", 0)
    mine = _members(config_dir)
    rows = []
    for m in sorted(set(mine) | set(was)):
        part = names.get(mine[m][0], mine[m][0]) if m in mine else next(
            (p.get("name", k) for k, p in ((man or {}).get("parts") or {}).items() if m in (p.get("files") or [])), "")
        short = m.split("/", 1)[1]
        if m not in was:
            rows.append({"part": part, "file": short, "what": short, "old": "(not there)", "new": "added"})
        elif m not in mine:
            rows.append({"part": part, "file": short, "what": short, "old": "there", "new": "removed"})
        elif GS._sha_file(mine[m][1]) != was[m]:
            vals = _values(_member_path(folder, n, m), mine[m][1]) if m.endswith(".json") else None
            if vals:
                rows += [{"part": part, "file": short, "what": k, "old": _say(a), "new": _say(b)} for k, a, b in vals]
            else:
                rows.append({"part": part, "file": short, "what": short, "old": "as the version has it", "new": "changed"})
    return rows


def update(config_dir, folder, by="", note="", when=None):
    """Write the next version from what this PC holds and name it the one in use. Returns its manifest. Raises OSError
    when the folder cannot be written, ValueError when there is nothing to put in a version."""
    mine = _members(config_dir)
    if not mine:
        raise ValueError("This PC holds nothing of the Global Standards yet.")
    os.makedirs(folder, exist_ok=True)
    cur = _json(os.path.join(folder, CURRENT)) or {}
    n = max(versions(folder) + [cur.get("version") if isinstance(cur.get("version"), int) else 0]) + 1
    stamp = (when or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M")
    tmp = os.path.join(folder, f"{vname(n)}.writing")
    shutil.rmtree(tmp, ignore_errors=True)
    files, parts = {}, {}
    names = GS.names()
    for m, (k, p) in sorted(mine.items()):
        dst = os.path.join(tmp, m.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(p, dst)
        files[m] = GS._sha_file(dst)
        parts.setdefault(k, {"name": names.get(k, k), "files": []})["files"].append(m)
    man = {"format": FORMAT, "version": n, "by": str(by or "")[:120], "when": stamp, "note": str(note or "")[:600],
           "files": files, "parts": parts}
    with open(os.path.join(tmp, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.join(folder, vname(n)))
    if read(folder, n) is None:
        raise OSError(f"Version {n} did not read back as it was written; the version in use is unchanged.")
    ctmp = os.path.join(folder, CURRENT + ".tmp")
    with open(ctmp, "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, "version": n, "by": man["by"], "when": stamp, "note": man["note"]}, f, indent=1, ensure_ascii=False)
    os.replace(ctmp, os.path.join(folder, CURRENT))
    GS.take(config_dir, n, GS.PUBLISHED, by=by, note=note, when=when)
    return man


def ready(config_dir, folder):
    """The manifest of the folder's version in use when it is newer than the one this PC is on; None otherwise."""
    man = current(folder)
    return man if man and man["version"] > GS.state(config_dir)["version"] else None


def take(config_dir, folder, n=None, when=None):
    """Put a version on this PC. What the PC changed of the Global Standards since the version it was on is kept in a
    dated backup and replaced; a file of its own that the version does not have is in the backup too. Returns {"version", "replaced": [part names],
    "backup": folder or ""}; raises ValueError when the version is not sound."""
    man = read(folder, n) if n is not None else current(folder)
    if not man:
        raise ValueError("That version is not complete in the folder yet. This PC stays on the one it has.")
    n = man["version"]
    mine = _members(config_dir)
    names = GS.names()
    differ = [m for m in set(mine) | set(man["files"]) if m not in man["files"] or m not in mine
              or GS._sha_file(mine[m][1]) != man["files"][m]]
    on = GS.state(config_dir)["version"]
    old = ((read(folder, on) or {}).get("files") or {}) if on and on != n else {}
    had = [m for m in differ if m in mine and GS._sha_file(mine[m][1]) != old.get(m)]     # the PC's own, not the version it was on
    backup = ""
    if had:
        stamp = (when or datetime.datetime.now()).strftime("%Y-%m-%d %H%M%S")
        backup = os.path.join(TD._data_dir(config_dir), BACKUPS, f"{stamp} before version {n}")
        k = 2
        while os.path.exists(backup):                    # two in one second keep two backups
            backup = os.path.join(TD._data_dir(config_dir), BACKUPS, f"{stamp} before version {n} ({k})"); k += 1
        for m in had:
            dst = os.path.join(backup, m.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(mine[m][1], dst)
    replaced = sorted({names.get(mine[m][0], mine[m][0]) for m in had})
    for m in differ:
        if m in man["files"]:
            dst = TD._local_path(config_dir, m)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(_member_path(folder, n, m), dst + ".tmp")
            os.replace(dst + ".tmp", dst)
        else:
            try:
                os.remove(mine[m][1])
            except OSError:
                pass
    GS.take(config_dir, n, GS.LINKED, by=man.get("by", ""), note=man.get("note", ""), when=when)
    _book_follows(config_dir)
    return {"version": n, "replaced": replaced, "backup": backup}


def _book_follows(config_dir):
    """The workbook in the team library is written again from the values now on this PC (on the next tick)."""
    try:
        import teamlib
        teamlib.mark_dirty(config_dir)
    except Exception:                                             # noqa: BLE001  the workbook is a copy; the values are in
        pass


def put_back(config_dir, folder, files):
    """Drop the changes waiting in these files (as waiting() names them): each is as the version in use has it again;
    one the version does not have leaves. Returns how many files changed. The PC's version does not change."""
    man = current(folder)
    if not man:
        return 0
    mine = _members(config_dir)
    n = 0
    for m in sorted(set(mine) | set(man["files"])):
        if m.split("/", 1)[1] not in files:
            continue
        if m in man["files"]:
            if m in mine and GS._sha_file(mine[m][1]) == man["files"][m]:
                continue
            dst = TD._local_path(config_dir, m)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(_member_path(folder, man["version"], m), dst + ".tmp")
            os.replace(dst + ".tmp", dst)
            n += 1
        elif m in mine:
            os.remove(mine[m][1]); n += 1
    if n:
        _book_follows(config_dir)
    return n


def folder(settings=None):
    """The Global Standards folder this PC is linked to ("" when none)."""
    if settings is None:
        try:
            import app_gui as A
            settings = A.load_settings()
        except Exception:                                         # noqa: BLE001
            settings = {}
    return str((settings or {}).get(SETTING) or "")


def set_folder(path):
    import app_gui as A
    s = A.load_settings()
    s[SETTING] = str(path or "")
    A.save_settings(s)
    return s[SETTING]
