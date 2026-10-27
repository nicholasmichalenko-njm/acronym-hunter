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
_names = {}                # id(widget) -> internal name, for usage logging
_last_action = [None]      # time of the previous activity line
usage_on = True
MAX_BYTES = 5 * 1024 * 1024
KEEP = 3

# Count fields a caller may attach. Values must be ints, or a file extension for "ext".
COUNT_KEYS = {"n", "files", "pages", "slides", "sheets", "pictures", "rows", "terms", "seconds", "ms", "exit_code",
              "chars", "items", "added", "removed", "choices", "warnings", "errors", "passes", "dpi", "width", "height",
              "effort_code"}
_EXT = re.compile(r"^\.[a-z0-9]{1,6}$")
_AREA = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
_W = re.compile(r"^[a-z][a-z0-9_.]{0,60}$")


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


def activity(action, w=None, state=None, **counts):
    """A feature action: 'scan_started', 'apply_choice', 'fix_ocr_saved'... with counts only.
    w = internal widget name for clicks (code identifiers only), state = 'disabled' for a click on a greyed-out control."""
    if not _AREA.match(action or ""):
        action = "other"
    now = datetime.datetime.now()
    entry = {"time": now.isoformat(timespec="seconds"), "version": VERSION, "action": action}
    if _last_action[0] is not None:
        entry["ms"] = min(int((now - _last_action[0]).total_seconds() * 1000), 3600000)
    _last_action[0] = now
    if isinstance(w, str) and _W.match(w):
        entry["w"] = w
    if state == "disabled":
        entry["state"] = "disabled"
    entry.update(_counts(counts))
    with _lock:
        _recent.append(entry); del _recent[:-200]
        if _scan is not None and action != "scan_finished":
            _scan["actions"] += 1
    _write("activity.jsonl", entry)


def recent_activity(n=20):
    with _lock:
        return list(_recent[-n:])


# ---------------------------------------------------------------- usage: which controls get clicked
def register(widget, name):
    """Give a widget an internal name for usage logging (a code identifier such as 'btn_again')."""
    if isinstance(name, str) and _W.match(name):
        _names[id(widget)] = name


def menu(name):
    """A menu bar command was chosen: its internal name only (e.g. 'file_select_files'), never any text or content."""
    if usage_on and isinstance(name, str) and _W.match(name):
        activity("menu", w=name)


def register_attrs(obj, prefix=""):
    """Name every widget attribute of an object after its attribute (self.btn_again -> 'btn_again')."""
    import tkinter as _tk
    for attr, val in list(vars(obj).items()):
        if isinstance(val, _tk.Misc) and re.match(r"^[a-z][a-z0-9_]{0,40}$", attr):
            register(val, prefix + attr)


def install_click_logger(root):
    """One line per click: the nearest named control (or 'dialog.<kind>'), and whether it was greyed out.
    Never the control's text, the row clicked, or anything typed."""
    def on_click(e):
        if not usage_on:
            return
        try:
            w, name, state, kind = e.widget, None, None, None
            hops = 0
            while w is not None and hops < 12:
                if type(w).__module__.startswith("customtkinter"):
                    if kind is None or kind == "ctkcanvas":
                        kind = type(w).__name__.lower()
                    try:
                        if str(w.cget("state")) == "disabled":
                            state = "disabled"
                    except Exception:
                        pass
                if id(w) in _names:
                    name = _names[id(w)]; break
                w = getattr(w, "master", None); hops += 1
            if name is None:
                name = "dialog." + (kind or type(e.widget).__name__.lower())
            activity("click", w=name[:60], state=state)
        except Exception:
            pass
    root.bind_all("<ButtonRelease-1>", on_click, add="+")


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
        name = re.sub(r"[^A-Za-z0-9_.\-]", "_", os.path.basename(fr.filename))[:57]   # "<frozen runpy>" too (2.47.0)
        if not name.endswith(".py"):
            name += ".py"
        fn = re.sub(r"[^A-Za-z0-9_<>]", "_", fr.name or "?")[:60]
        out.append(f"{name}:{fr.lineno}:{fn}")
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
