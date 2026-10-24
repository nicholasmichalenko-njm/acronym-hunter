"""Content-free diagnostics: errors, quiet failures and a feature activity trail.

What a log line may hold (enforced here and by tools/check_diag.py in the build):
    time, app version, level, area, a fixed message written in our source code, the exception TYPE,
    code locations (our file name, line, function), and whitelisted counts / file extensions.
What it never holds:
    file names, paths, folder names, document text, found terms, definitions, database or Effort List entries,
    OCR readings, exception MESSAGES, user names.

Files (all in logs\\ next to the program, never sent anywhere by the app):
    events.jsonl     errors and warnings, one JSON object per line (rotated at 5 MB, 3 files kept)
    activity.jsonl   feature actions with counts (rotated the same way)
    crash_raw.txt    written by Python's faulthandler only on a hard crash; converted to a content-free event at
                     the next start and then deleted (it contains file paths, so it is never exported)
"""
import datetime, faulthandler, json, os, re, sys, threading, traceback

VERSION = "?"
LOG_DIR = None
_lock = threading.Lock()
_seen = {}                 # (level, area, msg, type, top frame) -> count, so a loop cannot flood the log
_flushed = {}              # same key -> count already written as a repeat line
_where = {}                # same key -> full code locations of the first occurrence
_scan = None               # per-scan counters while a scan runs
_recent = []               # last activity actions (for feedback context)
_crash_fh = None
MAX_BYTES = 5 * 1024 * 1024
KEEP = 3

# Count fields a caller may attach. Values must be ints, or a file extension for "ext".
COUNT_KEYS = {"n", "files", "pages", "slides", "sheets", "pictures", "rows", "terms", "seconds", "ms", "exit_code",
              "chars", "items", "added", "removed", "choices", "warnings", "errors", "passes", "dpi", "width", "height"}
_EXT = re.compile(r"^\.[a-z0-9]{1,6}$")
_AREA = re.compile(r"^[a-z][a-z0-9_]{0,30}$")


def setup(log_dir, version):
    """Call once at start: hooks for uncaught errors in any thread, hard-crash capture, old crash conversion."""
    global LOG_DIR, VERSION, _crash_fh
    LOG_DIR, VERSION = log_dir, version
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError:
        return
    _convert_old_crash()
    def _hook(t, e, tb):
        error("app", "Uncaught error", exc=(t, e, tb))
        if not getattr(sys, "frozen", False):
            sys.__excepthook__(t, e, tb)      # developers still see the traceback in the console
    sys.excepthook = _hook
    def _thook(a):
        error("thread", "Uncaught error in a background task", exc=(a.exc_type, a.exc_value, a.exc_traceback))
        if not getattr(sys, "frozen", False):
            threading.__excepthook__(a)
    threading.excepthook = _thook
    try:
        _crash_fh = open(os.path.join(LOG_DIR, "crash_raw.txt"), "w", encoding="utf-8")
        faulthandler.enable(_crash_fh, all_threads=True)
    except Exception:
        _crash_fh = None


def shutdown():
    """Normal exit: flush repeat counts, remove the empty crash file."""
    try:
        _flush_repeats()
        if _crash_fh is not None:
            faulthandler.disable(); _crash_fh.close()
            p = os.path.join(LOG_DIR, "crash_raw.txt")
            if os.path.isfile(p) and os.path.getsize(p) == 0:
                os.remove(p)
    except Exception:
        pass


# ---------------------------------------------------------------- recording
def error(area, msg, exc=None, **counts):
    _record("error", area, msg, exc, counts)


def warning(area, msg, exc=None, **counts):
    _record("warning", area, msg, exc, counts)


def swallowed(area=None):
    """Call inside an `except` block that recovers on purpose. Logs the error type and where, once per place."""
    t, e, tb = sys.exc_info()
    if t is None or issubclass(t, FileNotFoundError):    # a missing optional file is a normal first-run state
        return
    if area is None:
        f = sys._getframe(1)
        area = _clean_area(f.f_code.co_name)
    _record("warning", area, "Recovered from an error", (t, e, tb), {})


def activity(action, **counts):
    """A feature action: 'scan_started', 'apply_choice', 'fix_ocr_saved'... with counts only."""
    if not _AREA.match(action or ""):
        action = "other"
    entry = {"time": _now(), "version": VERSION, "action": action, **_counts(counts)}
    with _lock:
        _recent.append(entry); del _recent[:-200]
        if _scan is not None and action != "scan_finished":
            _scan["actions"] += 1
    _write("activity.jsonl", entry)


def recent_activity(n=20):
    with _lock:
        return list(_recent[-n:])


# ---------------------------------------------------------------- per-scan health
def scan_started(files, exts):
    global _scan
    with _lock:
        _scan = {"t0": datetime.datetime.now(), "errors": 0, "warnings": 0, "actions": 0}
    activity("scan_started", files=files, **{f"ext_{e.strip('.')}": c for e, c in exts.items() if _EXT.match(e)})


def scan_finished(cancelled=False, **counts):
    global _scan
    with _lock:
        s, _scan = _scan, None
    if s is None:
        return
    secs = int((datetime.datetime.now() - s["t0"]).total_seconds())
    activity("scan_cancelled" if cancelled else "scan_finished", seconds=secs, errors=s["errors"],
             warnings=s["warnings"], **counts)
    _flush_repeats()


def issues_this_session():
    with _lock:
        return sum(c for k, c in _seen.items() if k[0] in ("error", "warning"))


# ---------------------------------------------------------------- internals
def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _clean_area(name):
    name = re.sub(r"[^a-z0-9_]", "_", (name or "app").lower()).strip("_") or "app"
    return name[:30] if _AREA.match(name[:30]) else "app"


def _counts(counts):
    out = {}
    for k, v in (counts or {}).items():
        if k == "ext":
            if isinstance(v, str) and _EXT.match(v.lower()):
                out["ext"] = v.lower()
        elif (k in COUNT_KEYS or re.match(r"^ext_[a-z0-9]{1,6}$", k)) and isinstance(v, int) and not isinstance(v, bool):
            out[k] = v
    return out


def _frames(tb):
    """Code locations only: file NAME (never its folder), line number, function name."""
    out = []
    for fr in traceback.extract_tb(tb)[-8:]:
        out.append(f"{os.path.basename(fr.filename)}:{fr.lineno}:{fr.name}")
    return out


def _record(level, area, msg, exc, counts):
    area = area if isinstance(area, str) and _AREA.match(area) else "app"
    msg = msg if isinstance(msg, str) else "?"
    entry = {"time": _now(), "version": VERSION, "level": level, "area": area, "msg": msg[:160]}
    if exc is not None:
        t, _e, tb = exc
        entry["type"] = getattr(t, "__name__", "Error")
        entry["where"] = _frames(tb)
    entry.update(_counts(counts))
    key = (level, area, entry["msg"], entry.get("type"), (entry.get("where") or [""])[-1])
    with _lock:
        n = _seen.get(key, 0) + 1
        _seen[key] = n
        if n == 1:
            _where[key] = entry.get("where", [])
        if _scan is not None:
            _scan["errors" if level == "error" else "warnings"] += 1
    if n == 1:
        _write("events.jsonl", entry)


def _flush_repeats():
    with _lock:
        rep = [(k, c) for k, c in _seen.items() if c > 1 and _flushed.get(k) != c]
        for k, c in rep:
            _flushed[k] = c
    for (level, area, msg, typ, where), c in rep:
        _write("events.jsonl", {"time": _now(), "version": VERSION, "level": level, "area": area, "msg": msg,
                                "type": typ, "where": _where.get((level, area, msg, typ, where), [where] if where else []),
                                "repeats": c})


def _write(name, entry):
    if not LOG_DIR:
        return
    p = os.path.join(LOG_DIR, name)
    try:
        with _lock:
            if os.path.isfile(p) and os.path.getsize(p) > MAX_BYTES:
                for i in range(KEEP - 1, 0, -1):
                    a, b = f"{p}.{i}", f"{p}.{i + 1}"
                    if os.path.exists(a):
                        os.replace(a, b)
                os.replace(p, p + ".1")
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


_FH_LINE = re.compile(r'File "(?P<f>[^"]+)", line (?P<l>\d+) in (?P<fn>\S+)')


def _convert_old_crash():
    """A previous run crashed hard: keep only file name, line and function from faulthandler's dump."""
    p = os.path.join(LOG_DIR, "crash_raw.txt")
    try:
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            raw = open(p, encoding="utf-8", errors="replace").read()
            where = [f"{os.path.basename(m['f'].replace(chr(92), '/'))}:{m['l']}:{m['fn']}" for m in _FH_LINE.finditer(raw)][:12]
            kind = "Fatal error"
            for k in ("Segmentation fault", "access violation", "Fatal Python error", "Aborted"):
                if k.lower() in raw.lower():
                    kind = k
            _write("events.jsonl", {"time": _now(), "version": VERSION, "level": "crash", "area": "app",
                                    "msg": "The previous session crashed", "type": kind, "where": where})
        if os.path.isfile(p):
            os.remove(p)
    except Exception:
        pass
