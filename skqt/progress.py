"""Progress for long work (2.82.0): a panel on the page that runs the work and a bar in the window's status bar, so the
person always sees that it is running, how far along it is, how long it has run, and how it ended (done, stopped, or
the error and what to do next). The first user is Read (the compliance matrix); document intake uses it next.

TaskPanel states: hidden, running (bar, step text, elapsed time, Stop), done (green, closes itself), stopped (amber),
failed (red; stays until closed, with what happened and what to do). A running step that has not moved for a minute
says it is still working, so a long scanned file never looks frozen. Rules only (No AI); nothing leaves the PC.
"""
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout
from . import design as D

SCALE = 1000          # the bar's range: fractions of the whole job
QUIET_S = 60          # a step that has not moved this long says it is still working
DONE_HIDE_MS = 8000


def elapsed_text(s):
    s = int(max(0, s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


class TaskPanel(QFrame):
    """The page's view of one long job. on_stop: what Stop does (None hides Stop)."""

    def __init__(self, on_stop=None, host=None):
        super().__init__()
        self.host = host
        self.on_stop = on_stop
        self.setObjectName("taskpanel")
        self.state = "hidden"
        self.started = self.moved = 0.0
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["l"], D.SPACE["m"], D.SPACE["l"], D.SPACE["m"])
        v.setSpacing(D.SPACE["xs"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.title = D.label("", "title", wrap=False); top.addWidget(self.title, 1)
        self.clock = D.label("", "muted", wrap=False); top.addWidget(self.clock)
        self.stop_btn = D.button("Stop", "danger", self._stop, "Stop after the file being read now. Nothing is written.")
        top.addWidget(self.stop_btn)
        self.close_btn = D.button("Close", "ghost", self.dismiss); top.addWidget(self.close_btn)
        self.bar = QProgressBar(); self.bar.setRange(0, SCALE); self.bar.setTextVisible(True); self.bar.setFormat("%p%")
        self.bar.setMinimumHeight(18); v.addWidget(self.bar)
        self.detail = D.label("", None); v.addWidget(self.detail)
        self.hint = D.label("", "muted"); v.addWidget(self.hint)
        self.tick = QTimer(self, interval=1000, timeout=self._tick)
        self.hide_timer = QTimer(self, singleShot=True, timeout=self._auto_hide)
        self.hide()

    # ------------------------------------------------------------------ states
    def _tone(self, tone):
        t = D.tokens()
        self.setStyleSheet(f"QFrame#taskpanel{{background:{t[tone + '_soft'] if tone != 'accent' else t['surface']};"
                           f"border:1px solid {t[tone]};border-radius:{D.RADIUS['card']}px;}}"
                           f"QFrame#taskpanel QLabel{{background:transparent;}}")

    def start(self, title, detail=""):
        self.hide_timer.stop()
        self.state = "running"
        self.started = self.moved = time.time()
        self._tone("accent")
        self.title.setText(title)
        self.detail.setText(detail); self.hint.setText("")
        self.bar.setValue(0); self.bar.show()
        self.stop_btn.setVisible(self.on_stop is not None); self.stop_btn.setEnabled(True); self.stop_btn.setText("Stop")
        self.close_btn.hide()
        self.clock.setText("0:00")
        self.show()
        self.tick.start()
        if self.host is not None:
            self.host.task_start(title)

    def step(self, frac, detail=""):
        if self.state != "running":
            return
        val = int(max(0.0, min(1.0, frac)) * SCALE)
        if val != self.bar.value() or (detail and detail != self.detail.text()):
            self.moved = time.time()
            self.hint.setText("")
        self.bar.setValue(max(val, self.bar.value()))
        if detail:
            self.detail.setText(detail)
        if self.host is not None:
            self.host.task_step(self.bar.value() / SCALE, detail)

    def stopping(self):
        self.stop_btn.setEnabled(False); self.stop_btn.setText("Stopping...")
        self.hint.setText("Stopping after the file being read now. Nothing is written.")

    def _end(self, tone, title, detail, hint, keep):
        self.tick.stop()
        self.state = {"ok": "done", "warn": "stopped", "crit": "failed"}[tone]
        self._tone(tone)
        took = elapsed_text(time.time() - self.started)
        self.title.setText(title)
        self.clock.setText(f"took {took}")
        self.detail.setText(detail); self.hint.setText(hint)
        if tone == "ok":
            self.bar.setValue(SCALE)
        else:
            self.bar.hide()
        self.stop_btn.hide(); self.close_btn.show()
        self.show()
        if self.host is not None:
            self.host.task_end()
        if not keep:
            self.hide_timer.start(DONE_HIDE_MS)

    def done(self, title, detail=""):
        self._end("ok", title, detail, "", keep=False)

    def stopped(self, title, detail="", hint=""):
        self._end("warn", title, detail, hint, keep=True)

    def failed(self, title, detail="", hint=""):
        """Stays until closed: what happened (detail) and what to do (hint)."""
        self._end("crit", title, detail, hint, keep=True)

    def dismiss(self):
        self.hide_timer.stop()
        if self.state != "running":
            self.state = "hidden"
            self.hide()

    def _auto_hide(self):
        if self.state == "done":
            self.dismiss()

    def _stop(self):
        if self.on_stop is not None and self.state == "running":
            self.stopping()
            self.on_stop()

    def _tick(self):
        now = time.time()
        self.clock.setText(elapsed_text(now - self.started))
        if self.state == "running" and now - self.moved >= QUIET_S and self.stop_btn.isEnabled():
            self.hint.setText(f"Still working: nothing new for {elapsed_text(now - self.moved)}. Scanned pages and large "
                              "files take longer; the clock above shows it is running.")


class StatusTask:
    """The window's status-bar view of the running job: a small bar and a line, shown only while something runs."""

    def __init__(self, window):
        self.win = window
        self.label = QLabel(""); self.label.setProperty("role", "muted")
        self.bar = QProgressBar(); self.bar.setRange(0, SCALE); self.bar.setFixedWidth(160); self.bar.setMaximumHeight(14)
        self.bar.setTextVisible(False)
        sb = window.statusBar()
        sb.addPermanentWidget(self.label); sb.addPermanentWidget(self.bar)
        self.label.hide(); self.bar.hide()
        self.title = ""

    def start(self, title):
        self.title = title
        self.label.setText(title); self.bar.setValue(0)
        self.label.show(); self.bar.show()

    def step(self, frac, detail=""):
        self.bar.setValue(int(max(0.0, min(1.0, frac)) * SCALE))
        self.label.setText(f"{self.title}: {int(frac * 100)}%")

    def end(self):
        self.label.hide(); self.bar.hide()
        self.title = ""

    def running(self):
        return self.bar.isVisible() or bool(self.title)
