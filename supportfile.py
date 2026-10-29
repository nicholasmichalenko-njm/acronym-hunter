"""Help without sending data (2.81.0): the support file, the safe start and what's new.

Support file: one zip for whoever maintains Stationkeeper, made by the person and sent by the person. It holds versions
(the app, Python, Qt, Windows), the content-free logs (events and activity: fixed messages, code locations, counts),
the counts from Check program files, the effort health problems by kind, and which settings are switched on. It holds
no document text, terms, names, file names or folder paths: every value is checked before it goes in, and anything that
looks like a path, an e-mail address or a name is left out.

Safe start: each start is counted until the window has been up for a few seconds; after two starts in a row that did
not get that far, the next one opens without the last effort, and says why.

What's new: after an update, one card lists what changed in this version.
Standard library only; nothing leaves the PC except the zip the person saves.
"""
import datetime, json, os, platform, re, sys, zipfile

START_FILE = "start_state.json"
SAFE_AFTER = 2
_PATHLIKE = re.compile(r"([A-Za-z]:[\\/])|(\\\\)|(/[^ ]+/)|(@[A-Za-z0-9.-]+\.)")
_SETTINGS_KEEP = {"work_mode", "advanced", "usage_logging", "ocr_sandbox_required", "theme", "text_size"}

WHATS_NEW = {
    "2.82.0": ["Moving between pages is fast with many documents: version changes and submission requirements are worked "
               "out once, in the background, and kept until something changes.",
               "Read shows its progress: the file and page, a running clock, Stop, and a clear message if a file cannot be "
               "read. Read is locked while it runs, so there is never a second read or a second matrix.",
               "Read RFP: tick all, tick selected, or tick one type; select several rows with Shift or Ctrl.",
               "After an update the new version shows each step while it reopens your work, so a pause never looks "
               "like lost work.",
               "Assign: the decision buttons (Requirement, L, M, Support, Customer's, Not used) sit beside the response "
               "structure, under the section they put sentences into."],
    "2.81.0": ["Help and support in Settings: create a support file (no document content), the keyboard shortcuts, and this card.",
               "Ctrl+K searches pages, efforts, sentences and people from anywhere.",
               "After two starts in a row that did not finish, Stationkeeper opens without the last effort and says why."],
    "2.80.0": ["Your data lives in 'Stationkeeper Data' beside the program folder; updates never touch it.",
               "Effort health is checked when an effort opens; a damaged list or matrix is put back from its newest good copy.",
               "Stationkeeper asks before overwriting a matrix another copy saved, and waits out OneDrive holding a file."],
    "2.79.0": ["Work modes: Secured (SCIF or closed network) or Connected (OneDrive team folder). Offline in both.",
               "Packages open where the sender was, with the same names, and say which copy is newer."],
    "2.78.0": ["Automatic backups, a recovery copy after a crash, Effort record > Restore, and each effort reopens where you were."],
    "2.77.0": ["One author list in Settings for every name, with the efforts each name shows in."],
    "2.76.0": ["Update packs: install once, then update with one signed file."],
}


def vt(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


# ---------------------------------------------------------------- safe start
def _start_path(folder):
    return os.path.join(folder, START_FILE)


def begin(folder):
    """Count this start. Returns True when this start should be safe (the last two never finished starting)."""
    p = _start_path(folder)
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    pending = int(d.get("pending", 0) or 0)
    safe = pending >= SAFE_AFTER
    try:
        os.makedirs(folder, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"pending": pending + 1, "at": datetime.datetime.now().isoformat(timespec="seconds")}, f)
    except OSError:
        pass
    return safe


def started(folder):
    """The window has been up for a few seconds: this start counts as good."""
    try:
        with open(_start_path(folder), "w", encoding="utf-8") as f:
            json.dump({"pending": 0, "at": datetime.datetime.now().isoformat(timespec="seconds")}, f)
    except OSError:
        pass


# ---------------------------------------------------------------- what's new
def whats_new(last, current):
    """The notes for the versions after last up to current, newest first ([] when nothing new or a first start)."""
    if not last or vt(last) >= vt(current):
        return []
    out = []
    for v in sorted(WHATS_NEW, key=vt, reverse=True):
        if vt(last) < vt(v) <= vt(current):
            out.append((v, WHATS_NEW[v]))
    return out


# ---------------------------------------------------------------- the support file
def _clean(v):
    """A value that may go in: numbers, booleans, short words without paths, names or addresses; else None."""
    if isinstance(v, bool) or isinstance(v, (int, float)) or v is None:
        return v
    if isinstance(v, str) and len(v) <= 60 and not _PATHLIKE.search(v):
        return v
    return None


def _scrub_line(line):
    """A log line kept only when every string value in it is clean (the logs are content-free by design; this checks)."""
    try:
        d = json.loads(line)
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    out = {}
    for k, v in d.items():
        if isinstance(v, list):
            v = [x for x in (_clean(i) if not isinstance(i, (list, dict)) else None for i in v) if x is not None]
            out[k] = v
            continue
        if isinstance(v, dict):
            continue
        c = _clean(v)
        if c is not None or v is None:
            out[k] = c
    return json.dumps(out, ensure_ascii=True)


def make(out_path, app_version, log_dir, settings=None, program_check=None, health=None, data_why="", qt_version=""):
    """Write the support file. Returns {"path", "files"} (the names inside)."""
    info = {"app_version": app_version, "python": platform.python_version(), "qt": qt_version or "",
            "windows": platform.release() + " " + platform.version() if sys.platform == "win32" else platform.platform(terse=True),
            "made": datetime.datetime.now().isoformat(timespec="minutes"), "data_location": data_why or "",
            "settings_on": sorted(k for k, v in (settings or {}).items() if k in _SETTINGS_KEEP and v not in (None, "", False)),
            "work_mode": (settings or {}).get("work_mode", "") if (settings or {}).get("work_mode", "") in ("secured", "connected") else "",
            "backups_on": bool((settings or {}).get("backup_dir")),
            "health": sorted({i.get("kind", "") for i in (health or []) if _clean(i.get("kind", ""))})}
    if program_check is not None:
        info["program_files"] = {"version": _clean(program_check.get("version", "")), "ok": program_check.get("ok", 0),
                                 "changed": len(program_check.get("changed", [])), "missing": len(program_check.get("missing", [])),
                                 "extra": len(program_check.get("extra", []))}
    files = ["about.json"]
    tmp = out_path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("about.json", json.dumps(info, indent=1))
        for name in ("events.jsonl", "activity.jsonl"):
            p = os.path.join(log_dir or "", name)
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    lines = [x for x in (_scrub_line(l) for l in f.readlines()[-5000:]) if x]
                z.writestr("logs/" + name, "\n".join(lines) + "\n")
                files.append("logs/" + name)
        z.writestr("READ ME.txt", "Stationkeeper support file\r\n\r\nVersions, content-free logs and checks, for whoever maintains "
                                  "Stationkeeper. It holds no document text, terms, names, file names or folder paths.\r\n")
        files.append("READ ME.txt")
    os.replace(tmp, out_path)
    return {"path": out_path, "files": files}
