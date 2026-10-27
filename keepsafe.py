"""Exports kept and backups (2.46.0). Rules only (No AI); nothing leaves the PC except to folders the person picks.

1. Every export is also kept, dated, in the effort's folder: "<effort> - exports (Stationkeeper)" beside the effort
   list, with the date and time in each file name ("Kestrel_Response_Setup 2026-10-27 0840.docx"). Nothing there is ever
   overwritten. The app notices exports at its save windows (any save window, and folder windows for exports), so
   every export is covered, including future ones.
2. A backup location outside the app's folder (File > Backup location), one folder per effort:
   - "<effort> - latest.skpkg": the whole effort as an effort package (File > Import effort package restores it exactly;
     it also holds the readable copy, so it can be unzipped and read without the app); refreshed a few minutes after
     changes and when the effort closes;
   - "<effort> <date>.skpkg": one per day, kept 30 days;
   - "Readable copy" and "Exports": mirrors of the effort's readable copy and its dated exports;
   - beside the effort folders, "Stationkeeper settings and team lists <date>.zip": the app's config folder (master
     database, banned words, keyword knowledge, settings), one per day, kept 30 days.
"""
import datetime, os, re, shutil, time, zipfile

EXPORTS_SUFFIX = " - exports (Stationkeeper)"
KEEP_DAYS = 30


def _safe(s):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", s or "").strip().rstrip(".")
    return re.sub(r"\s+", " ", s)[:90] or "Effort"


# ------------------------------------------------------------------ exports kept in the effort's folder
def exports_folder(list_path, effort_name=""):
    d, n = os.path.split(os.path.abspath(list_path))
    return os.path.join(d, _safe(effort_name or os.path.splitext(n)[0]) + EXPORTS_SUFFIX)


def dated_name(path, when=None):
    """'Kestrel_Setup.docx' -> 'Kestrel_Setup 2026-10-27 0840.docx'."""
    stem, ext = os.path.splitext(os.path.basename(path))
    return f"{stem} {(when or datetime.datetime.now()):%Y-%m-%d %H%M}{ext}"


def _free(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    k = 2
    while os.path.exists(f"{stem} ({k}){ext}"):
        k += 1
    return f"{stem} ({k}){ext}"


def keep_file(src, folder, when=None):
    """A dated copy of an exported file in the exports folder. Returns its path, or None."""
    if not os.path.isfile(src):
        return None
    os.makedirs(folder, exist_ok=True)
    dst = _free(os.path.join(folder, dated_name(src, when)))
    shutil.copy2(src, dst)
    return dst


def _snapshot(src_dir, cap=20000):
    """The folder's files and their times before an export writes into it (None when the folder is very large)."""
    snap = {}
    for dp, dns, fns in os.walk(src_dir):
        for f in fns:
            p = os.path.join(dp, f)
            try:
                snap[os.path.normcase(p)] = os.path.getmtime(p)
            except OSError:
                continue
            if len(snap) > cap:
                return None
    return snap


def _new_files(src_dir, since, skip=(), before=None):
    """Files an export wrote into a folder: new or changed since the folder was picked (or since `since`), leaving out
    the app's own folders and files."""
    out = []
    for dp, dns, fns in os.walk(src_dir):
        dns[:] = [x for x in dns if not x.endswith((EXPORTS_SUFFIX, " - readable copy (Stationkeeper)", " - app data"))]
        for f in fns:
            p = os.path.join(dp, f)
            if f.startswith("~$") or f.endswith(".tmp") or os.path.normcase(p) in skip:
                continue
            try:
                m = os.path.getmtime(p)
            except OSError:
                continue
            if before is not None:
                if before.get(os.path.normcase(p)) != m:
                    out.append((p, m))
            elif m >= since - 2:
                out.append((p, m))
    return out


def keep_tree(src_dir, folder, since, when=None, skip=(), before=None):
    """A dated copy of what an export wrote into a folder (files changed since `since`). Returns the copies."""
    out = []
    if not os.path.isdir(src_dir):
        return out
    new = _new_files(src_dir, since, skip, before)
    if not new:
        return out
    base = _free(os.path.join(folder, f"{_safe(os.path.basename(os.path.normpath(src_dir)))} export {(when or datetime.datetime.now()):%Y-%m-%d %H%M}"))
    for p, _m in new:
        dst = os.path.join(base, os.path.relpath(p, src_dir))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
        out.append(dst)
    return out


def _inside(p, folder):
    a, b = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(folder))
    return a == b or a.startswith(b + os.sep)


SKIP_TITLES = ("where should",)                   # save windows that create the effort's own working files
DIR_TITLES = ("folder for the setup", "folder for the export", "folder for the lists", "folder for the acronym lists",
              "folder for one .txt")


class Watch:
    """Exports seen at save windows, copied into the exports folder once they are written and have stopped changing."""

    def __init__(self):
        self.pending = []                         # [{"kind", "path", "t", "size"}]

    def saw_file(self, path, title="", folder="", skip=()):
        """A save window returned a path. folder: the open effort's exports folder (none: not kept). skip: the effort's
        own working files."""
        if not (path and folder) or any((title or "").lower().startswith(t) for t in SKIP_TITLES):
            return False
        p = os.path.abspath(path)
        if _inside(p, folder) or os.path.normcase(p) in {os.path.normcase(os.path.abspath(x)) for x in skip if x}:
            return False
        self.pending.append({"kind": "file", "path": p, "folder": folder, "t": time.time(), "size": None})
        return True

    def saw_dir(self, path, title="", folder="", skip=()):
        if not (path and folder) or not any((title or "").lower().startswith(t) for t in DIR_TITLES):
            return False
        p = os.path.abspath(path)
        if _inside(p, folder):
            return False
        self.pending.append({"kind": "dir", "path": p, "folder": folder, "t": time.time(), "size": None,
                             "skip": [os.path.normcase(os.path.abspath(x)) for x in skip if x], "before": _snapshot(p)})
        return True

    def process(self, now=None, settle=3.0, give_up=900.0):
        """Copy what is ready into each export's effort folder. Returns the copies made."""
        now = now or time.time()
        made, keep = [], []
        for e in self.pending:
            p, folder = e["path"], e["folder"]
            if now - e["t"] > give_up:
                continue
            if e["kind"] == "file":
                try:
                    st = os.stat(p)
                except OSError:
                    keep.append(e)                # not written yet
                    continue
                sig = (st.st_size, st.st_mtime)
                if st.st_mtime < e["t"] - 2:      # an old file: the export has not written it yet
                    keep.append(e)
                    continue
                if sig != e["size"] or now - st.st_mtime < settle:
                    e["size"] = sig
                    keep.append(e)
                    continue
                try:
                    made.append(keep_file(p, folder))
                except OSError:
                    keep.append(e)
            else:
                new = _new_files(p, e["t"], e.get("skip", ()), e.get("before"))
                count, newest = len(new), max((m for _p, m in new), default=0)
                if not count or now - newest < settle or (count, newest) != e["size"]:
                    e["size"] = (count, newest) if count else None
                    keep.append(e)
                    continue
                try:
                    made += keep_tree(p, folder, e["t"], skip=e.get("skip", ()), before=e.get("before"))
                except OSError:
                    keep.append(e)
        self.pending = keep
        return [m for m in made if m]


# ------------------------------------------------------------------ the backup location
def default_backup_dir():
    """Documents\\Stationkeeper backups (Documents may sit under OneDrive)."""
    home = os.path.expanduser("~")
    for docs in (os.path.join(home, "Documents"), os.path.join(home, "OneDrive", "Documents")):
        if os.path.isdir(docs):
            return os.path.join(docs, "Stationkeeper backups")
    return os.path.join(home, "Stationkeeper backups")


def synced(path):
    """Whether a folder looks cloud-synced (OneDrive, SharePoint, Dropbox, Box, Google Drive)."""
    p = (path or "").lower()
    return any(k in p for k in ("onedrive", "sharepoint", "dropbox", "\\box\\", "/box/", "google drive", "googledrive"))


def _prune(folder, prefix, ext, today=None):
    today = today or datetime.date.today()
    rx = re.compile(re.escape(prefix) + r" (\d{4}-\d{2}-\d{2})" + re.escape(ext) + "$")
    for f in os.listdir(folder):
        m = rx.match(f)
        if m:
            try:
                d = datetime.date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if (today - d).days > KEEP_DAYS:
                try:
                    os.remove(os.path.join(folder, f))
                except OSError:
                    pass


def _mirror(src, dst):
    """Copy new and changed files from src into dst (never deletes in dst: a backup keeps what it had)."""
    n = 0
    if not os.path.isdir(src):
        return n
    for dp, _dns, fns in os.walk(src):
        for f in fns:
            if f.endswith(".tmp") or f.startswith("~$"):
                continue
            s = os.path.join(dp, f)
            d = os.path.join(dst, os.path.relpath(s, src))
            try:
                if os.path.isfile(d) and os.path.getsize(d) == os.path.getsize(s) and os.path.getmtime(d) >= os.path.getmtime(s):
                    continue
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
                n += 1
            except OSError:
                continue
    return n


README = """Stationkeeper backups

Written by Stationkeeper to a folder you picked (File > Backup location), so the work survives if the app's folder
or an effort's folder is deleted or damaged. One folder per effort:

  <effort> - latest.skpkg     The whole effort as it was at the last backup: stages, gate goals, notes, tasks,
                              deliverables, the timeline, customer documents and their versions, submission
                              requirements, the compliance matrix and every decision, acronyms, keywords, our volumes
                              and the readable copy. To restore: Stationkeeper > File > Restore from a backup
                              folder... (every effort and the settings at once), or File > Import effort package.
                              Without the app: copy it, rename .skpkg to .zip, unzip, open the readable folder.
  <effort> <date>.skpkg       One package per day, kept {days} days.
  Readable copy\\              The effort's readable copy (CSV and text files; READ ME FIRST.txt explains them).
  Exports\\                    Every export made from the effort, dated.

Beside the effort folders:
  Stationkeeper settings and team lists <date>.zip
                              The app's config folder: the Acronyms, Abbreviations, Units and Symbols Master Database,
                              banned words, keyword knowledge and settings. To restore, unzip it into the app's config
                              folder (next to Stationkeeper.exe) while the app is closed, or use File > Restore from a backup folder...

Nothing here leaves this PC unless the folder itself is synced (for example by OneDrive). Keep proposal data only in
folders your company allows for it.
"""


def backup_effort(backup_dir, effort_name, list_path, data_dir, matrix_path="", customer_dir="", volumes_dir="",
                  readable_dir="", exports_dir="", extra_files=(), info=None, stage="", app_version="", config_dir="",
                  settings_file="", when=None):
    """Write the backup for one effort. Returns {"latest", "dated", "readable", "exports", "settings"}."""
    import effortpkg as P
    when = when or datetime.datetime.now()
    root = os.path.join(backup_dir, _safe(effort_name))
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(backup_dir, "READ ME.txt"), "w", encoding="utf-8") as f:
        f.write(README.format(days=KEEP_DAYS))
    out = {}
    man = P.save(os.path.join(root, f"{_safe(effort_name)} - latest"), effort_name, list_path, data_dir, info=info or {},
                 matrix_path=matrix_path, customer_dir=customer_dir, volumes_dir=volumes_dir, customer=bool(customer_dir),
                 volumes=bool(volumes_dir), stage=stage, app_version=app_version, extra_files=extra_files,
                 readable_dir=readable_dir)
    out["latest"] = man["path"]
    dated = os.path.join(root, f"{_safe(effort_name)} {when:%Y-%m-%d}{P.EXT}")
    shutil.copy2(man["path"], dated)              # today's copy follows the latest until the day ends
    out["dated"] = dated
    _prune(root, _safe(effort_name), P.EXT, when.date())
    out["readable"] = _mirror(readable_dir, os.path.join(root, "Readable copy")) if readable_dir else 0
    out["exports"] = _mirror(exports_dir, os.path.join(root, "Exports")) if exports_dir else 0
    if config_dir and os.path.isdir(config_dir):
        z = os.path.join(backup_dir, f"Stationkeeper settings and team lists {when:%Y-%m-%d}.zip")
        tmp = z + ".tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for dp, dns, fns in os.walk(config_dir):
                dns[:] = [x for x in dns if x not in ("logs", "__pycache__", "temp")]
                for f in fns:
                    if not f.endswith(".tmp"):
                        p = os.path.join(dp, f)
                        zf.write(p, os.path.relpath(p, config_dir))
            if settings_file and os.path.isfile(settings_file):
                zf.write(settings_file, "app settings/" + os.path.basename(settings_file))
        os.replace(tmp, z)
        _prune(backup_dir, "Stationkeeper settings and team lists", ".zip", when.date())
        out["settings"] = z
    return out


# ------------------------------------------------------------------ restoring from a backup folder
def find_backups(backup_dir):
    """The efforts in a backup folder: [{"name", "package", "saved_at", "stage", "saved_by", "original_list"}], newest
    first. Each effort's latest package (or, when it is missing, its newest dated one)."""
    import effortpkg as P
    out = []
    if not backup_dir or not os.path.isdir(backup_dir):
        return out
    for d in sorted(os.listdir(backup_dir)):
        root = os.path.join(backup_dir, d)
        if not os.path.isdir(root):
            continue
        pk = [f for f in os.listdir(root) if f.lower().endswith(P.EXTS) and not f.endswith(".tmp")]
        if not pk:
            continue
        latest = [f for f in pk if f.endswith(" - latest" + os.path.splitext(f)[1])]
        pick = latest[0] if latest else max(pk, key=lambda f: os.path.getmtime(os.path.join(root, f)))
        path = os.path.join(root, pick)
        try:
            man = P.read_manifest(path)
        except Exception:
            continue
        out.append({"name": man.get("effort") or d, "package": path, "saved_at": man.get("saved_at", ""),
                    "stage": man.get("stage", ""), "saved_by": man.get("saved_by", ""),
                    "original_list": (man.get("info") or {}).get("path", "") or ""})
    out.sort(key=lambda b: b["saved_at"], reverse=True)
    return out


def latest_settings(backup_dir):
    """The newest 'Stationkeeper settings and team lists <date>.zip' in a backup folder, or ''."""
    if not backup_dir or not os.path.isdir(backup_dir):
        return ""
    z = sorted(f for f in os.listdir(backup_dir) if f.startswith("Stationkeeper settings and team lists ") and f.endswith(".zip"))
    return os.path.join(backup_dir, z[-1]) if z else ""


def restore_settings(zip_path, config_dir, settings_file=""):
    """Put the app's config folder (and the settings file) back from a settings zip. Nothing outside those two is
    written; files already there are replaced. Returns the number of files restored."""
    n = 0
    croot = os.path.abspath(config_dir)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.startswith("app settings/"):
                if not settings_file:
                    continue
                target = os.path.abspath(settings_file)
            else:
                target = os.path.abspath(os.path.join(croot, *[p for p in name.split("/") if p not in ("", ".", "..")]))
                if not (target == croot or target.startswith(croot + os.sep)):
                    continue                          # nothing outside the config folder
            os.makedirs(os.path.dirname(target), exist_ok=True)
            tmp = target + ".tmp"
            with zf.open(info) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst)
            os.replace(tmp, target)
            n += 1
    return n
