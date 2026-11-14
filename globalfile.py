"""Global Standards, step 2b (4.33.0; the board of 2026-11-14): a version as one file, and the notice of what a
version changed on this PC.

One file per version sits beside the version folders in the Global Standards folder (written at each update): a zip
of the version's files and its manifest. A PC with no linked folder takes a version with Install a file...; the file is
checked whole (every member against the manifest) before anything on the PC changes.

Whenever a version is put on this PC (from the folder or from a file), what it changed here is kept as a notice: each
change, who updated and when, the note. It stays on Settings > Global Standards until Mark as seen. No undo: the PC's
own changes are in the dated backup the take makes.

    file_name(n)                      "Global Standards version 13.skgs"
    write(folder, n)                  the version's file, beside its folder; returns its path
    take(config_dir, folder, ...)     globalfolder.take, with the notice kept
    install(config_dir, path)         take the version in a file; ValueError says why not
    notice(config_dir)                the notice not yet seen, or None
    mark_seen(config_dir)

Standard library only. Rules only (No AI); nothing leaves the PC."""
import json, os, shutil, tempfile, zipfile

import globalfolder as GF
import globalstd as GS
import teamdata as TD

EXT = ".skgs"
NOTICE = "global_notice.json"
FORMAT = 1                                      # formats.py "global standards notice"
MOST_BYTES = 2 * 1024 ** 3
MOST_ROWS = 400


def file_name(n):
    return f"Global Standards version {int(n)}{EXT}"


def write(folder, n):
    """The file of version n, written beside its folder. Raises OSError; ValueError when the version is not sound."""
    man = GF.read(folder, n)
    if not man:
        raise ValueError(f"Version {n} is not complete in the folder.")
    out = os.path.join(folder, file_name(n))
    with zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(folder, GF.vname(n), GF.MANIFEST), GF.MANIFEST)
        for m in sorted(man["files"]):
            z.write(GF._member_path(folder, n, m), m)
    os.replace(out + ".tmp", out)
    return out


def _unpack(path, into):
    """The file's version laid out as a Global Standards folder under `into`. Returns its number."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            if GF.MANIFEST not in names:
                raise ValueError("This is not a Global Standards file.")
            man = json.loads(z.read(GF.MANIFEST).decode("utf-8"))
            n = man.get("version") if isinstance(man, dict) else None
            if not isinstance(n, int) or n < 1 or not isinstance(man.get("files"), dict):
                raise ValueError("This is not a Global Standards file.")
            if set(names) - {GF.MANIFEST} != set(man["files"]) or not all(TD._safe_member(m) for m in man["files"]):
                raise ValueError("The file does not hold exactly what it says it holds. Nothing was changed.")
            if sum(i.file_size for i in z.infolist()) > MOST_BYTES:
                raise ValueError("The file is larger than a Global Standards version can be. Nothing was changed.")
            base = os.path.join(into, GF.vname(n))
            for m in names:
                dst = os.path.join(base, m.replace("/", os.sep))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with z.open(m) as src, open(dst, "wb") as f:
                    shutil.copyfileobj(src, f)
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError) as e:
        raise ValueError("This is not a Global Standards file.") from e
    if GF.read(into, n) is None:
        raise ValueError("The file is damaged: its contents do not match its own list. Nothing was changed.")
    return n


def _rows(config_dir, folder):
    """What the folder's version in use would change on this PC, one row a change: was (this PC), now (the version)."""
    return [{"part": r["part"], "what": r["what"], "was": r["new"], "now": r["old"]}
            for r in GF.waiting(config_dir, folder)][:MOST_ROWS]


def _keep(config_dir, man, rows, got):
    d = {"format": FORMAT, "version": man["version"], "by": man.get("by", ""), "when": man.get("when", ""),
         "note": man.get("note", ""), "rows": rows, "replaced": got.get("replaced") or [], "backup": got.get("backup", ""),
         "seen": False}
    p = os.path.join(config_dir, NOTICE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def take(config_dir, folder, source=None, when=None):
    """Put the folder's version in use on this PC and keep the notice of what it changed here. Returns what
    globalfolder.take returns."""
    man = GF.current(folder)
    rows = _rows(config_dir, folder) if man and GS.state(config_dir)["version"] else []
    got = GF.take(config_dir, folder, when=when)
    if source:
        GS.take(config_dir, got["version"], source, by=man.get("by", ""), note=man.get("note", ""), when=when)
    try:
        _keep(config_dir, man, rows, got)
    except OSError:                                              # the notice is a courtesy; the version is on the PC
        pass
    return got


def install(config_dir, path, when=None):
    """Take the version in a file. ValueError (with words for the person) when the file is not sound or not newer."""
    tmp = tempfile.mkdtemp(prefix="skgs_")
    try:
        n = _unpack(path, tmp)
        on = GS.state(config_dir)["version"]
        if n <= on:
            raise ValueError(f"This PC is on version {on}. The file holds version {n}, which is not newer. Nothing was changed.")
        return take(config_dir, tmp, source=GS.INSTALLED, when=when)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def notice(config_dir):
    """The notice of the last version taken, while it is not marked as seen; None otherwise."""
    d = GF._json(os.path.join(config_dir, NOTICE))
    return d if d and not d.get("seen") and isinstance(d.get("rows"), list) else None


def mark_seen(config_dir):
    p = os.path.join(config_dir, NOTICE)
    d = GF._json(p)
    if d:
        d["seen"] = True
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
        os.replace(p + ".tmp", p)


def notice_words(d):
    n = len(d["rows"])
    by = f" by {d['by']}" if d.get("by") else ""
    return (f"Version {d['version']}, updated{by} on {d.get('when', '')}, changed {n} thing{'s' if n != 1 else ''} on this PC."
            if n else f"This PC took version {d['version']}, updated{by} on {d.get('when', '')}.")
