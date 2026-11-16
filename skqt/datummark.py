"""The Production Datum's mark in the top bar, and the panel under it (4.47.0; UX decisions 36 and 59).

The mark is on every page and cannot be dismissed. It says which of three states this PC is in: nothing installed,
installed (its number), or a newer one ready. A click opens one small panel, in the same place each time:

  nothing installed   one sentence and one button, Connect
  installed           the number and when it was installed; what it holds, one line each with a count; Connect, smaller
  a newer one ready   what will change, in counts, before anything happens; Install Production Datum N; one line
                      saying the person's work is not touched

The panel explains nothing about what a Datum is and holds no settings. Connect is two actions, Connect from a file...
and Connect to a folder... (decision 34); they are the ones Settings has. Rules only (No AI)."""
import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QDialog, QMenu, QVBoxLayout

import datum as DT
import diag
import globalfolder as GF
from . import design as D

TONE = {DT.NONE: "warn", DT.INSTALLED: "ok", DT.READY: "accent"}


def state(w):
    return DT.state(w.config_dir, GF.folder())


def install(w):
    """Put the mark in the top bar, beside the mode, and keep it current whenever the window's title is."""
    w.datum_mark = D.Pill("", "warn", dot=True)
    w.datum_mark.setCursor(Qt.PointingHandCursor)
    w.datum_mark.setToolTip("What this PC works from. Click to see it, or to connect.")
    w.datum_mark.mousePressEvent = lambda _e: open_panel(w)
    try:
        lay = w.mode_chip.parentWidget().layout()
        lay.insertWidget(lay.indexOf(w.mode_chip) + 1, w.datum_mark, 0, Qt.AlignVCenter)
    except Exception:  # noqa: BLE001  a bar laid out another way still gets its mark
        diag.swallowed()
        w.statusBar().addPermanentWidget(w.datum_mark)
    orig = w.title

    def title():
        orig()
        refresh(w)
    w.title = title
    refresh(w)
    return w.datum_mark


def refresh(w):
    try:
        st = state(w)
        w.datum_mark.set_tone(TONE[st["kind"]])
        w.datum_mark.setText(DT.mark(st))
        w.datum_mark.setVisible(True)
        return st
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def _db_file():
    try:
        import app_gui
        return app_gui.DB_FILE
    except Exception:  # noqa: BLE001
        return ""


def lines(w, st=None):
    """What the panel says, as data: {"kind", "title", "says": [lines], "main": the button's words, "small": bool}."""
    st = st or state(w)
    if st["kind"] == DT.NONE:
        return {"kind": st["kind"], "title": DT.mark(st), "says": [DT.NOTHING], "main": "Connect", "small": False}
    if st["kind"] == DT.READY:
        wc = DT.will_change(w.config_dir, GF.folder()) or {"number": st["ready"], "words": ""}
        return {"kind": st["kind"], "title": DT.mark(st), "says": [x for x in (wc["words"], DT.NOT_TOUCHED) if x],
                "main": f"Install {DT.NAME} {wc['number']}", "small": False}
    says = [f"Installed {st['taken']}" if st["taken"] else "Installed"] + [said for _n, _c, said in DT.holds(w.config_dir, _db_file())]
    return {"kind": st["kind"], "title": DT.mark(st), "says": says, "main": "Connect", "small": True}


class Panel(QDialog):
    """One small panel under the mark. It closes when a click lands outside it."""

    def __init__(self, w):
        super().__init__(w, Qt.Popup)
        self.w = w
        self.setObjectName("datumPanel")
        v = QVBoxLayout(self); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(D.SPACE["s"])
        self.said = lines(w)
        self.title = D.label(f"<b>{self.said['title']}</b>", None, wrap=False); v.addWidget(self.title)
        self.rows = []
        for s in self.said["says"]:
            lab = D.label(s, None if self.said["kind"] != DT.INSTALLED else "muted"); lab.setWordWrap(True)
            v.addWidget(lab); self.rows.append(lab)
        if self.said["kind"] == DT.READY:
            self.main = D.button(self.said["main"], "primary", lambda: self.take())
        else:
            self.main = D.button(self.said["main"], None if self.said["small"] else "primary", lambda: self.connect_menu())
        v.addWidget(self.main, 0, Qt.AlignLeft)
        self.setMinimumWidth(320)

    def connect_menu(self):
        m = QMenu(self)
        m.addAction("Connect from a file...", lambda: self.do(connect_file))
        m.addAction("Connect to a folder...", lambda: self.do(connect_folder))
        self.menu = m
        m.popup(self.main.mapToGlobal(QPoint(0, self.main.height())))
        return m

    def do(self, fn):
        self.close()
        fn(self.w)

    def take(self):
        self.close()
        return take(self.w)


def open_panel(w):
    p = Panel(w)
    at = w.datum_mark.mapToGlobal(QPoint(0, w.datum_mark.height() + 4))
    p.move(at)
    p.show()
    w.datum_panel = p
    return p


def _settings(w):
    return w.settings_page


def connect_file(w, path=None):
    """Connect from a file...: the Production Datum from a file someone sent."""
    from . import globalview as GV
    said = GV.install(_settings(w), path)
    w.title()
    return said


def connect_folder(w, path=None):
    """Connect to a folder...: the folder the Production Datum is kept in; this PC stays current from it."""
    from . import globalview as GV
    got = GV.link(_settings(w), path)
    if got and os.path.isdir(got):
        GV.at_open(w)                       # a folder that already holds one: take it now, as the app does when it opens
    w.title()
    return got


def take(w):
    """Install the newer one that is ready."""
    from . import globalview as GV
    said = GV.use_now(_settings(w))
    w.title()
    return said


def started_label(host):
    """For the effort's details: which Production Datum it was started on. Hidden when that was never recorded."""
    said = DT.started(getattr(host, "ws", None))
    lab = D.label(said, "muted")
    lab.setVisible(bool(said))
    return lab


def ready_row(host):
    """For a readiness list (Make the setup): what this PC works from. Never blocks: nothing is restricted without one."""
    return (True, DT.line(state(host)), 0)
