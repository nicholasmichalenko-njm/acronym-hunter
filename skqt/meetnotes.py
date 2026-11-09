"""Notes on a calendar event (3.92.1; claude/stationkeeper-navigation-3.93.md): click Notes beside a meeting on the
Effort Dashboard's calendar and its notes open, made from the event the first time (title, date, times, who). The notes
save as you type; the lines marked Action, Decision, Topic (or bullets) are offered as topics, each followed until it is
done, as on Effort Record > Meetings. meetings.py holds the rules; nothing leaves the PC."""
import html

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QVBoxLayout)

import diag
import meetings as MT
from . import design as D

STATUS = {"open": "Open", "considered": "Done", "not_needed": "Not needed"}


class MeetingNotes(QDialog):
    def __init__(self, page, rec, mid):
        super().__init__(page)
        self.page, self.rec, self.mid = page, rec, mid
        m = MT.get(rec, mid)
        self.setWindowTitle(f"Notes: {m['title']}")
        self.resize(760, 620)
        v = QVBoxLayout(self)
        when = " ".join(x for x in (m.get("date", ""), m.get("start", "") and f"{m['start']} to {m.get('end', '')}".rstrip(" to")) if x)
        v.addWidget(D.label(f"<b>{html.escape(m['title'])}</b>  " + html.escape(when)
                            + (f"  ·  {html.escape(', '.join(m.get('participants') or []))}" if m.get("participants") else ""), None))
        v.addWidget(D.label("Notes, saved as you type. A line that starts with Action:, Decision: or Topic: (or a bullet) is "
                            "offered as a topic below.", "muted"))
        self.notes = QPlainTextEdit(m.get("notes", "")); v.addWidget(self.notes, 3)
        self.timer = QTimer(self, singleShot=True, interval=600, timeout=self.save)
        self.notes.textChanged.connect(lambda: (self.timer.start(), self.fill_offers()))
        v.addWidget(D.SectionTitle("Topics from these notes"))
        self.offers = QListWidget(); v.addWidget(self.offers, 1)
        self.offers.itemDoubleClicked.connect(lambda it: self.keep(it.text()))
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Keep as a topic", None, lambda: self.keep_current()))
        row.addWidget(D.button("Done", None, lambda: self.set_done()))
        row.addStretch(1)
        self.topics = QListWidget(); v.addWidget(self.topics, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.close_save); v.addWidget(bb)
        self.fill_offers(); self.fill_topics()

    def save(self):
        MT.update_meeting(self.rec, self.mid, notes=self.notes.toPlainText())
        return True

    def close_save(self):
        self.timer.stop(); self.save()
        self.reject()

    def kept(self):
        return {t["text"] for t in (MT.get(self.rec, self.mid) or {}).get("topics", [])}

    def fill_offers(self):
        have = self.kept()
        self.offers.clear()
        for x in MT.topics_from_notes(self.notes.toPlainText()):
            if x not in have:
                QListWidgetItem(x, self.offers)
        return self.offers.count()

    def fill_topics(self):
        self.topics.clear()
        for t in (MT.get(self.rec, self.mid) or {}).get("topics", []):
            it = QListWidgetItem(f"{t['text']}    {STATUS.get(t.get('status'), 'Open')}", self.topics)
            it.setData(256, t["id"])
        return self.topics.count()

    def keep(self, text):
        self.save()
        tid = MT.add_topic(self.rec, self.mid, text)
        diag.activity("meeting_topic_kept")
        self.fill_offers(); self.fill_topics()
        return tid

    def keep_current(self):
        it = self.offers.currentItem() or (self.offers.item(0) if self.offers.count() else None)
        return self.keep(it.text()) if it is not None else None

    def set_done(self):
        it = self.topics.currentItem()
        if it is None:
            return None
        tid = it.data(256)
        MT.set_status(self.rec, self.mid, tid, "considered")
        self.fill_topics()
        return tid


def open_notes(page, rec, event_id, run=True):
    """The notes of a calendar event (made the first time). Returns the window."""
    mid = MT.for_event(rec, event_id, who=getattr(page.host, "my_name", None) or None)
    if mid is None:
        return None
    dlg = MeetingNotes(page, rec, mid)
    page.notes_window = dlg
    if run:
        dlg.exec()
        try:
            page.show_day()
        except Exception:                       # noqa: BLE001  the page has gone on
            diag.swallowed()
    return dlg


def mark(rec, event_id):
    """'Notes · 2 topics' for an event with notes, '' for one without."""
    m = MT.of_event(rec, event_id)
    if m is None:
        return ""
    n = len(m.get("topics") or [])
    return "Notes" + (f" · {n} topic{'s' if n != 1 else ''}" if n else "")
