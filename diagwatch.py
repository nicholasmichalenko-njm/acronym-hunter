"""What the diagnostics could not see before 4.43.1 (ST53 of 2026-11-15), recorded with fixed words and no content:

  Qt's own messages   qInstallMessageHandler. A message is recorded by its kind (warning, critical, fatal) and by which
                      known message it is (TEMPLATES: a timer started from another thread, a child made for a parent in
                      another thread, painting outside a paint event...). The message's text is never kept: Qt puts
                      object names and paths in it. A message that is not on the list is recorded as "other".
  a window that stops answering
                      beat() is called by a timer on the window's thread. Each beat re-arms Python's own watchdog
                      (faulthandler.dump_traceback_later, which runs below Python and so fires even while the window's
                      thread is stuck inside a library). After HANG seconds with no beat, where every thread is gets
                      written to hang_raw.txt; the next beat, or the next start, keeps file name, line and function
                      only and records how long the window was away.
  errors while Python cleans up
                      sys.unraisablehook: an error in an object's cleanup, where a PDF page or document is closed.

Nothing here reads a document, and nothing leaves the PC. diag holds the files."""
import faulthandler, os, re, sys, time

import diag

HANG = 5.0                                   # seconds without a beat before the threads' places are written (Windows
BEAT_MS = 500                                # calls a window Not Responding at five seconds too)
LEVELS = {0: "debug", 1: "warning", 2: "critical", 3: "fatal", 4: "info"}
# a known Qt message, by how it starts -> its fixed name. Order matters: the first that fits.
TEMPLATES = (("QObject::startTimer: Timers cannot be started from another thread", "timer_started_from_another_thread"),
             ("QObject::killTimer: Timers cannot be stopped from another thread", "timer_stopped_from_another_thread"),
             ("QObject: Cannot create children for a parent that is in a different thread", "child_for_parent_in_another_thread"),
             ("QObject::setParent: Cannot set parent, new parent is in a different thread", "parent_in_another_thread"),
             ("QObject::moveToThread", "move_to_thread"),
             ("QBasicTimer::start", "timer_started_from_another_thread"),
             ("QPainter::begin", "painter_begin_failed"),
             ("QPainter::", "painter_not_active"),
             ("QWidget::repaint: Recursive repaint", "recursive_repaint"),
             ("QBackingStore::endPaint", "painting_outside_a_paint_event"),
             ("QPixmap: It is not safe to use pixmaps outside the GUI thread", "pixmap_outside_the_window_thread"),
             ("QPixmap::", "pixmap"), ("QImage::", "image"), ("QFont::", "font"), ("QLayout", "layout"),
             ("QThread: Destroyed while thread", "thread_destroyed_while_running"),
             ("QThread::", "thread"), ("QObject::connect", "connect_failed"), ("QObject::", "object"),
             ("QWindowsWindow::setGeometry", "window_geometry"), ("QFileSystemWatcher", "file_watcher"),
             ("This plugin does not support", "plugin_does_not_support"), ("qt.qpa.", "platform"))
NAMES = {n for _p, n in TEMPLATES} | {"other"}
_seen = {}
_state = {"fh": None, "last": None, "path": None, "on": False}


def template_of(message):
    """The fixed name of a Qt message; "other" for one that is not on the list. The text itself is never returned."""
    m = str(message or "")
    return next((name for start, name in TEMPLATES if m.startswith(start)), "other")


def qt_message(level, message):
    """Records one Qt message by kind and fixed name: the first, the tenth, the hundredth and the thousandth of each."""
    kind = LEVELS.get(int(level) if isinstance(level, int) else getattr(level, "value", 1), "warning")
    if kind in ("debug", "info"):
        return None
    tpl = template_of(message)
    key = (kind, tpl)
    _seen[key] = n = _seen.get(key, 0) + 1
    if n in (1, 10, 100, 1000) or kind == "fatal":
        diag.event("qt", "Qt reported a problem", type=kind, tpl=tpl, n=n)
    return tpl


def install_qt():
    """Qt's messages come here from now on. Returns the handler Qt had before."""
    from PySide6.QtCore import qInstallMessageHandler

    def handler(mode, _context, message):
        try:
            qt_message(mode, message)
        except Exception:  # noqa: BLE001  a problem recording a message must never stop the program
            pass
    _state["handler"] = handler                     # kept alive: Qt holds no reference of its own
    return qInstallMessageHandler(handler)


def unraisable(u):
    diag.error("cleanup", "An error while Python was cleaning up", exc=(u.exc_type, u.exc_value, u.exc_traceback))


def install_cleanup():
    sys.unraisablehook = unraisable


# ---------------------------------------------------------------- a window that stops answering
_FRAME = re.compile(r'File "(?P<f>[^"]+)", line (?P<l>\d+) in (?P<fn>\S+)')


def hang_where(raw, threads=8, frames=8):
    """Where each thread was, from faulthandler's text: file name, line and function only; the window's thread is the
    one that holds skqt_main or the event loop, listed first."""
    blocks, cur = [], None
    for line in raw.splitlines():
        head = line.strip()
        if head.startswith(("Thread ", "Current thread")) and "most recent call first" in head:
            cur = []; blocks.append(cur)
            continue
        m = _FRAME.search(line)
        if m and cur is not None:
            cur.append(f"{os.path.basename(m['f'].replace(chr(92), '/'))}:{m['l']}:{m['fn']}")
    blocks = [b for b in blocks if b]
    blocks.sort(key=lambda b: 0 if any(f.startswith("skqt_main.py:") for f in b) else 1)
    out = []
    for i, b in enumerate(blocks[:threads]):
        out += ["the window's thread:" if i == 0 and any(f.startswith("skqt_main.py:") for f in b) else "another thread:"] + b[:frames]
    return out


def collect(now=None):
    """A hang that was written down becomes one record. Returns the record's seconds, or None when there was none."""
    p = _state["path"] or (os.path.join(diag.LOG_DIR, "hang_raw.txt") if diag.LOG_DIR else None)
    try:
        if not p or not os.path.isfile(p) or os.path.getsize(p) == 0:
            return None
        fh = _state["fh"]
        if fh is not None:
            fh.flush()
        with open(p, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        if fh is not None:
            fh.seek(0); fh.truncate()
        else:
            os.remove(p)
    except OSError:
        return None
    secs = int(round((now if now is not None else time.monotonic()) - _state["last"])) if _state["last"] is not None else 0
    diag.event("hang", "The window stopped answering", type="ended" if _state["on"] else "found at start",
               seconds=max(secs, int(HANG)) if _state["on"] else 0, where=hang_where(raw))
    return secs


def start():
    """Opens the hang file and arms the watchdog. Call once the window exists; beat() then keeps it quiet."""
    if not diag.LOG_DIR or diag.OFF:
        return False
    _state["path"] = os.path.join(diag.LOG_DIR, "hang_raw.txt")
    collect()                                        # one left by a session that never answered again
    try:
        _state["fh"] = open(_state["path"], "w+", encoding="utf-8")
    except OSError:
        return False
    _state["on"] = True
    beat()
    return True


def beat():
    """The window's thread is answering: record a hang that just ended, and give the watchdog another HANG seconds."""
    if not _state["on"]:
        return
    now = time.monotonic()
    if _state["last"] is not None and now - _state["last"] >= HANG:
        collect(now)
    _state["last"] = now
    try:
        faulthandler.dump_traceback_later(HANG, repeat=False, file=_state["fh"])
    except (ValueError, RuntimeError, OSError):
        pass


def stop():
    if _state["on"]:
        try:
            faulthandler.cancel_dump_traceback_later()
            _state["fh"].close()
            if os.path.getsize(_state["path"]) == 0:
                os.remove(_state["path"])
        except (OSError, ValueError):
            pass
    _state.update(on=False, fh=None, last=None)


def install(app):
    """Everything above, for the running program: Qt's messages, cleanup errors, and the beat on the window's thread."""
    install_qt(); install_cleanup()
    if os.environ.get("AH_TEST"):                    # the tests call start() and beat() themselves
        return None
    from PySide6.QtCore import QTimer
    if start():
        t = QTimer(app); t.setInterval(BEAT_MS); t.timeout.connect(beat); t.start()
        app.aboutToQuit.connect(stop)
        _state["timer"] = t
        return t
    return None
