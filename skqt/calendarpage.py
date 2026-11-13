"""Calendar (4.27.1; Nicholas's recording 2026-11-12 08:20: "the calendar is very important ... I want it before the
fold"; answer 2: a menu entry of its own). The month with every dated thing marked, the picked day's list, and the next
dated things beside it. It reads the effort's calendar (the due date, questions due, stages, gate goals, tasks,
reviews and meetings); nothing is stored here. The Dashboard's calendar card on All cards is the same data.
Rules only (No AI); nothing leaves the PC."""
import datetime
import html

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QTextCharFormat
from PySide6.QtWidgets import QCalendarWidget, QHBoxLayout, QLabel, QVBoxLayout, QWidget

import diag
import overview as OV
from . import design as D
from .commandbar import CommandBar

TONE = {"due": "crit", "deadline": "warn", "questions": "cust", "meeting": "ctx", "stage": "accent", "task": "warn", "goal": "accent"}


def _clear(lay):
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.setParent(None); w.deleteLater()


class CalendarPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        self.cal_data = {}
        self.day = datetime.date.today()
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.bar.primary("Today", lambda: self.pick(datetime.date.today()), "This month, and today's list")
        v.addWidget(self.bar)
        self.empty = D.EmptyState("No effort open", "Open an effort to see its dates.", "All Efforts", lambda: host.go("efforts"))
        v.addWidget(self.empty, 1)
        self.body = QWidget(); v.addWidget(self.body, 1)
        h = QHBoxLayout(self.body); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["m"])
        self.cal = QCalendarWidget(); self.cal.setGridVisible(False); self.cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.cal.setFirstDayOfWeek(Qt.Monday); self.cal.setMinimumHeight(320)
        plain = QTextCharFormat(); plain.setForeground(D.color("text"))
        for wd in (Qt.Saturday, Qt.Sunday):
            self.cal.setWeekdayTextFormat(wd, plain)
        self.cal.clicked.connect(lambda d: self.pick(d.toPython()))
        self.cal.currentPageChanged.connect(lambda _y, _m: self.paint())
        h.addWidget(self.cal, 3)
        right = QVBoxLayout(); right.setSpacing(D.SPACE["m"]); h.addLayout(right, 2)
        self.day_card = D.Card("Today")
        self.day_box = QVBoxLayout(); self.day_box.setSpacing(2); self.day_card.body.addLayout(self.day_box)
        right.addWidget(self.day_card)
        self.next_card = D.Card("Coming up", "The next dated things, soonest first.")
        self.next_box = QVBoxLayout(); self.next_box.setSpacing(2); self.next_card.body.addLayout(self.next_box)
        right.addWidget(self.next_card, 1)
        self._painted = []

    def load(self, today=None):
        h = self.host
        if h.ws is None:
            return {}
        import effortstate as ES
        today = today or datetime.date.today()
        try:
            st = ES.State(h.ws, h.effort_path, h.review.M if getattr(h, "review", None) is not None else None)
            return st.calendar(first=today - datetime.timedelta(days=365), last=today + datetime.timedelta(days=730))
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return {}

    def refresh(self, today=None):
        on = self.host.ws is not None
        self.empty.setVisible(not on); self.body.setVisible(on); self.bar.setVisible(on)
        if not on:
            return None
        self.today = today or datetime.date.today()
        self.cal_data = self.load(self.today)
        self.paint()
        self.show_day()
        _clear(self.next_box)
        t = D.tokens()
        ahead = OV.dates(self.cal_data, self.today)
        for _d, wh, kind, text in ahead:
            lab = QLabel(f"<b>{html.escape(wh)}</b> &nbsp;<span style='color:{t['muted']}'>{html.escape(kind)}</span> &nbsp;{html.escape(text)}")
            lab.setTextFormat(Qt.RichText); lab.setWordWrap(True)
            self.next_box.addWidget(lab)
        if not ahead:
            self.next_box.addWidget(D.label("Nothing dated ahead. Set the due date on the Overview and it shows here.", "muted"))
        self.next_box.addStretch(1)
        self.ahead = ahead
        diag.activity("qt_calendar_shown")
        return self.cal_data

    def paint(self):
        """Mark every day of the month shown that has something on it, in the color of what matters most that day."""
        for qd in self._painted:
            self.cal.setDateTextFormat(qd, QTextCharFormat())
        self._painted = []
        order = ("due", "questions", "deadline", "meeting", "stage", "goal", "task")
        for d, items in self.cal_data.items():
            kinds = [k for k, _t in items if k not in ("done", "event")]
            if not kinds or d is None:
                continue
            k = next((x for x in order if x in kinds), kinds[0])
            f = QTextCharFormat(); f.setFontWeight(700); f.setForeground(D.color(TONE.get(k, "accent")))
            f.setToolTip("\n".join(f"{OV.KIND_WORDS.get(kk, kk.capitalize())}: {tx}" for kk, tx in items if kk not in ("done", "event")))
            qd = QDate(d.year, d.month, d.day)
            self.cal.setDateTextFormat(qd, f); self._painted.append(qd)
        return len(self._painted)

    def pick(self, day):
        self.day = day
        self.cal.setSelectedDate(QDate(day.year, day.month, day.day))
        return self.show_day()

    def show_day(self):
        _clear(self.day_box)
        t = D.tokens()
        d = self.day
        today = getattr(self, "today", datetime.date.today())
        self.day_card.title.setText("Today" if d == today else f"{d.strftime('%A')}, {d.strftime('%b')} {d.day}, {d.year}")
        items = [(k, tx) for k, tx in self.cal_data.get(d, [])]
        for k, tx in items:
            word = {"done": "Done", "event": "Happened"}.get(k, OV.KIND_WORDS.get(k, k.capitalize()))
            lab = QLabel(f"<span style='color:{t[TONE.get(k, 'muted')]}'>{html.escape(word)}</span> &nbsp;{html.escape(tx)}")
            lab.setTextFormat(Qt.RichText); lab.setWordWrap(True)
            self.day_box.addWidget(lab)
        if not items:
            self.day_box.addWidget(D.label("Nothing on this day.", "muted"))
        return items
