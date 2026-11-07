"""Button use on this PC (3.74.0, claude/stationkeeper-simplify-decisions-2026-11-06.md decision 4): which buttons and
menu items are pressed, on which screen, counted on this PC only, so the screens keep in view what is used and move the
rest into More. Kept in <config>\\button_use.json: {"format": 1, "since": "YYYY-MM-DD", "on": true,
"counts": {screen: {words: n}}}. Never in a SCIF-ready install. Never leaves the PC: no network here or anywhere.

The words are the button's own (digits shown as #, at most 60 characters); a label that looks like a file name or a
path is counted as "(a file)", so the count holds the app's words, not the effort's."""
import datetime, json, os, re

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QAbstractButton, QApplication, QMenu

import diag

FILE = "button_use.json"
FORMAT = 1
FILEISH = re.compile(r"[\\/]|\.(docx?|dotx|dotm|xlsx?|xlsm|pdf|pptx?|csv|txt|png|jpe?g|skpkg|skeffort)\b", re.I)


def path(config_dir):
    return os.path.join(config_dir, FILE)


def load(config_dir):
    try:
        with open(path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    d.setdefault("format", FORMAT)
    d.setdefault("since", datetime.date.today().isoformat())
    d.setdefault("on", True)
    d.setdefault("counts", {})
    return d


def save(config_dir, d):
    os.makedirs(config_dir, exist_ok=True)
    p = path(config_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return d


def words(text):
    """A button's words as counted."""
    t = " ".join(str(text or "").replace("&", "").split())
    if not t:
        return ""
    if FILEISH.search(t):
        return "(a file)"
    return re.sub(r"\d+", "#", t)[:60]


def scif():
    try:
        import secure
        return bool(secure.ACTIVE)
    except Exception:  # noqa: BLE001
        return False


def rows(d):
    """[(screen, words, n)], most pressed first."""
    out = [(s, w, n) for s, ws in (d.get("counts") or {}).items() for w, n in ws.items()]
    return sorted(out, key=lambda x: (-x[2], x[0], x[1]))


class Counter(QObject):
    """Installed on the application: a left click released on an enabled button, or a menu item chosen."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.d = load(host.config_dir)
        self.dirty = 0
        self.timer = QTimer(self, singleShot=True, interval=4000, timeout=self.flush)

    def screen(self, w):
        win = w.window() if w is not None else None
        if win is not None and win is not self.host:
            return "Window: " + words(win.windowTitle() or type(win).__name__)
        pg = self.host.stack.currentWidget() if hasattr(self.host, "stack") else None
        key = next((k for k, p in getattr(self.host, "pages", {}).items() if p is pg), "")
        if w is not None and pg is not None and not pg.isAncestorOf(w):
            return "The frame"
        return key or "The frame"

    def count(self, screen, text):
        if not self.d.get("on", True) or scif():
            return False
        t = words(text)
        if not t:
            return False
        c = self.d.setdefault("counts", {}).setdefault(screen, {})
        c[t] = c.get(t, 0) + 1
        self.dirty += 1
        self.timer.start()
        return True

    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.MouseButtonRelease and getattr(ev, "button", lambda: None)() == Qt.LeftButton:
                if isinstance(obj, QMenu):
                    a = obj.activeAction()
                    if a is not None and a.isEnabled() and not a.menu():
                        self.count(self.screen(obj.parentWidget() or obj), a.text())
                elif isinstance(obj, QAbstractButton) and obj.isEnabled() and obj.rect().contains(ev.position().toPoint()):
                    self.count(self.screen(obj), obj.text() or obj.toolTip()[:40])
        except Exception:  # noqa: BLE001  counting never gets in the way
            diag.swallowed()
        return False

    def flush(self):
        if not self.dirty or scif():
            return
        try:
            save(self.host.config_dir, self.d)
            self.dirty = 0
        except OSError:
            diag.swallowed()

    def set_on(self, on):
        self.d["on"] = bool(on)
        self.dirty += 1
        self.flush()

    def clear(self):
        self.d = {"format": FORMAT, "since": datetime.date.today().isoformat(), "on": self.d.get("on", True), "counts": {}}
        self.dirty += 1
        self.flush()


def install(host):
    """At start (after the window is built). Returns the counter, or None in a SCIF-ready install."""
    if scif():
        return None
    c = Counter(host)
    QApplication.instance().installEventFilter(c)
    return c
