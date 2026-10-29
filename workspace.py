"""Per-effort workspace (2.11.0): everything an effort decides lives in its own folder, saved as it happens.

Folder (next to the Effort List, or config\\no_effort when no effort is open):
  settings.json   the effort's own settings (compliance matrix path, AI and ML switch, team learning)
  choices.json    Apply Choice decisions for this effort only
  session.json    the last scan's results, statuses and choices; restored on the next start
  resume.json     where you were: selected row, filters, open windows
  lock.json       who has the effort open (user, computer, process), refreshed while open
  recovery\\       a copy of unsaved work, written with every change, removed after a successful save
  backups\\        dated copies of the Effort List and compliance matrix (last 10, plus one per day for 14 days)

Nothing here is shared between efforts. The folder holds customer content: keep it on this PC or SharePoint.
Pure Python, no network.
"""
import datetime, getpass, glob, hashlib, json, os, platform, shutil, time

DATA_SUFFIX = " - app data"
LOCK_STALE_HOURS = 12
BACKUP_EVERY_S = 600          # at most one backup of a file every 10 minutes (saves happen every few seconds)
KEEP_RECENT, KEEP_DAYS = 10, 14


def replace_retry(src, dst, tries=8, wait=0.25):
    """os.replace that waits a moment when Windows refuses (2.80.0): OneDrive, a virus scanner or the search indexer can
    hold a file for a second while reading it. Excel holding the file keeps refusing, and the last PermissionError is
    raised for the caller to report."""
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(wait)


def data_dir_for(list_path):
    """The effort's folder: '<list name> - app data' beside the Effort List workbook."""
    d, n = os.path.split(os.path.abspath(list_path))
    return os.path.join(d, os.path.splitext(n)[0] + DATA_SUFFIX)


def _default(o):
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=str)
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    return str(o)


def long_path(path):
    """Windows: the extended-length form for paths near or over the 260-character limit (deep OneDrive or SharePoint
    folders), so opening a file there still works. Unchanged elsewhere."""
    p = os.path.abspath(path)
    if os.name != "nt" or len(p) < 240 or p.startswith("\\\\?\\"):
        return p
    return "\\\\?\\UNC\\" + p[2:] if p.startswith("\\\\") else "\\\\?\\" + p


def write_json(path, data):
    """Atomic write (temp file, then replace); retries while OneDrive holds the file for an upload, or has not
    finished creating a new folder (2.36.0)."""
    path = long_path(path)
    folder = os.path.dirname(path)
    tmp = path + ".tmp"
    for attempt in range(6):
        try:
            os.makedirs(folder, exist_ok=True)
            f = open(tmp, "w", encoding="utf-8")
            break
        except (FileNotFoundError, PermissionError):
            if attempt == 5:
                raise
            time.sleep(0.3)
    with f:
        json.dump(data, f, ensure_ascii=False, default=_default, separators=(",", ":"))
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    for attempt in range(6):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.3)


def read_json(path, default=None):
    try:
        with open(long_path(path), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        return default


def _key(path):
    return hashlib.sha1(os.path.normcase(os.path.abspath(path)).encode("utf-8")).hexdigest()[:12]


def _pid_alive(pid):
    """Is a process with this id running on this PC? (Windows: OpenProcess; elsewhere: signal 0.)"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259          # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return True


class Workspace:
    def __init__(self, root, name="", choices_file=None):
        self.root = root
        self.name = name
        self.choices_file = choices_file or os.path.join(root, "choices.json")
        self.locked_by = None
        self._backup_times = {}
        os.makedirs(root, exist_ok=True)

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    # ------------------------------------------------------------ settings
    def settings(self):
        d = read_json(self.p("settings.json"), {})
        return d if isinstance(d, dict) else {}

    def get(self, key, default=None):
        return self.settings().get(key, default)

    def set(self, key, value):
        d = self.settings()
        d[key] = value
        write_json(self.p("settings.json"), d)

    # ------------------------------------------------------------ choices
    def load_choices(self):
        d = read_json(self.choices_file, {})
        return d if isinstance(d, dict) else {}

    def save_choice(self, term, choice):
        d = self.load_choices()
        d[term] = choice
        write_json(self.choices_file, d)

    # ------------------------------------------------------------ excluded instances (2.13.0)
    def instance_excludes(self):
        """{term: [location labels]} excluded one by one in this effort (the term stays elsewhere)."""
        d = read_json(self.p("excluded_instances.json"), {})
        return {k: list(v) for k, v in d.items() if isinstance(v, list)} if isinstance(d, dict) else {}

    def save_instance_excludes(self, data):
        write_json(self.p("excluded_instances.json"), {k: v for k, v in data.items() if v})

    # ------------------------------------------------------------ session and resume
    def save_session(self, data):
        data = dict(data, saved_at=datetime.datetime.now().isoformat(timespec="seconds"))
        write_json(self.p("session.json"), data)

    def load_session(self):
        d = read_json(self.p("session.json"), None)
        return d if isinstance(d, dict) else None

    def save_resume(self, data):
        data = dict(data, saved_at=datetime.datetime.now().isoformat(timespec="seconds"))
        write_json(self.p("resume.json"), data)

    def load_resume(self):
        d = read_json(self.p("resume.json"), {})
        return d if isinstance(d, dict) else {}

    def last_worked(self):
        """When this effort was last saved (resume or session), or None."""
        times = [t for t in ((self.load_resume() or {}).get("saved_at"), ((self.load_session() or {}).get("saved_at")))
                 if t]
        try:
            return max(datetime.datetime.fromisoformat(t) for t in times) if times else None
        except ValueError:
            return None

    # ------------------------------------------------------------ lock (one window per effort)
    @staticmethod
    def _me():
        return {"user": getpass.getuser(), "computer": platform.node(), "pid": os.getpid()}

    def acquire_lock(self, force=False):
        """True when this window holds the effort. False when another window or person has it (self.locked_by)."""
        info = read_json(self.p("lock.json"), None)
        if info and not force:
            try:
                age_h = (datetime.datetime.now() - datetime.datetime.fromisoformat(info["time"])).total_seconds() / 3600
            except (KeyError, ValueError, TypeError):
                age_h = LOCK_STALE_HOURS + 1
            me = self._me()
            same_pc = (info.get("user"), info.get("computer")) == (me["user"], me["computer"])
            if age_h < LOCK_STALE_HOURS:
                if not same_pc or (info.get("pid") != me["pid"] and _pid_alive(info.get("pid", 0))):
                    self.locked_by = info
                    return False
        self.locked_by = None
        write_json(self.p("lock.json"), dict(self._me(), time=datetime.datetime.now().isoformat(timespec="seconds")))
        return True

    def refresh_lock(self):
        info = read_json(self.p("lock.json"), None) or {}
        me = self._me()
        if (info.get("user"), info.get("computer"), info.get("pid")) == (me["user"], me["computer"], me["pid"]):
            write_json(self.p("lock.json"), dict(me, time=datetime.datetime.now().isoformat(timespec="seconds")))

    def release_lock(self):
        info = read_json(self.p("lock.json"), None) or {}
        me = self._me()
        if (info.get("user"), info.get("computer"), info.get("pid")) == (me["user"], me["computer"], me["pid"]):
            try:
                os.remove(self.p("lock.json"))
            except OSError:
                pass

    # ------------------------------------------------------------ recovery (unsaved work)
    def write_recovery(self, kind, path, state):
        write_json(self.p("recovery", f"{kind}_{_key(path)}.json"),
                   {"kind": kind, "path": os.path.abspath(path), "time": datetime.datetime.now().isoformat(timespec="seconds"),
                    "state": state})

    def read_recovery(self, kind, path):
        """The unsaved copy for this file when it is newer than the file on disk, else None."""
        rec = read_json(self.p("recovery", f"{kind}_{_key(path)}.json"), None)
        if not isinstance(rec, dict) or "state" not in rec:
            return None
        try:
            t = datetime.datetime.fromisoformat(rec["time"]).timestamp()
        except (KeyError, ValueError):
            return None
        if os.path.isfile(path) and os.path.getmtime(path) >= t:
            self.clear_recovery(kind, path)            # the file was saved after the copy: nothing to recover
            return None
        return rec

    def clear_recovery(self, kind, path):
        try:
            os.remove(self.p("recovery", f"{kind}_{_key(path)}.json"))
        except OSError:
            pass

    # ------------------------------------------------------------ backups
    def backup(self, path, kind, force=False):
        """Copy the saved workbook into backups\\ (throttled), then prune. Returns the backup path or None."""
        if not os.path.isfile(path):
            return None
        now = time.time()
        if not force and now - self._backup_times.get(path, 0) < BACKUP_EVERY_S:
            return None
        self._backup_times[path] = now
        d = self.p("backups")
        os.makedirs(d, exist_ok=True)
        stem = os.path.splitext(os.path.basename(path))[0]
        dest = os.path.join(d, f"{kind}__{stem}__{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx")
        shutil.copy2(path, dest)
        self.prune(kind, stem)
        return dest

    def backups(self, kind=None):
        """[(path, kind, stem, datetime)] newest first."""
        out = []
        for f in glob.glob(self.p("backups", "*.xlsx")):
            parts = os.path.basename(f)[:-5].split("__")
            if len(parts) != 3 or (kind and parts[0] != kind):
                continue
            try:
                when = datetime.datetime.strptime(parts[2], "%Y%m%d-%H%M%S")
            except ValueError:
                continue
            out.append((f, parts[0], parts[1], when))
        out.sort(key=lambda r: r[3], reverse=True)
        return out

    def prune(self, kind, stem):
        rows = [r for r in self.backups(kind) if r[2] == stem]
        keep = set(r[0] for r in rows[:KEEP_RECENT])
        cutoff = datetime.datetime.now() - datetime.timedelta(days=KEEP_DAYS)
        seen_days = set()
        for r in rows:                                 # newest first: the first one of each day stays
            day = r[3].date()
            if r[3] >= cutoff and day not in seen_days:
                keep.add(r[0]); seen_days.add(day)
        for r in rows:
            if r[0] not in keep:
                try:
                    os.remove(r[0])
                except OSError:
                    pass

    def restore(self, backup_path, dest):
        """Put a backup back in place. The current file is backed up first, so a restore can be undone."""
        tmp = dest + ".restore.tmp"
        shutil.copy2(backup_path, tmp)                 # first: keeping the current file may prune the chosen copy
        try:
            if os.path.isfile(dest):
                kind = os.path.basename(backup_path).split("__")[0]
                self.backup(dest, kind, force=True)
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
