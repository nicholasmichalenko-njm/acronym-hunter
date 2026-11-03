"""Meetings (3.20.0, a tab of the Effort Record): a meeting's title, date and time, participants and notes, and the
topics it raised, each followed until someone marks it Considered or Not needed. A topic points at a section of the
response structure or a requirement and can name an owner. Topics from notes picks the notes' bullet lines (and Topic:,
Action:, Decision: lines) for you to keep or drop; nothing is made up. Export saves the meeting in Word. The rules are
meetings.py's; nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QSplitter, QTableWidget, QTableWidgetItem, QTimeEdit, QVBoxLayout, QWidget, QCheckBox)
import diag
import effortrec as R_
import meetings as MT
from . import design as D

TONE = {"open": "warn", "considered": "ok", "not_needed": "faint"}


class MeetingsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.mid = None
        self._loading = False
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.summary = D.label("", "muted"); top.addWidget(self.summary, 1)
        top.addWidget(D.button("+ Meeting", "primary", lambda: self.new_meeting(), "A meeting: title, date, participants, notes"))
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        split.setHandleWidth(D.SPACE["l"])            # 3.20.3: room between the list and the meeting
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, D.SPACE["s"], 0)
        lv.addWidget(D.label("Meetings", "label"))
        self.list = QListWidget(); self.list.currentItemChanged.connect(lambda c, _p: self.show(c.data(Qt.UserRole) if c else None))
        lv.addWidget(self.list, 1)
        self.open_only = QCheckBox("Show only meetings with open topics"); self.open_only.toggled.connect(lambda _b: self.refresh())
        lv.addWidget(self.open_only)
        split.addWidget(left)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(D.SPACE["l"], 0, 0, 0)
        self.empty = D.EmptyState("No meeting open", "Press + Meeting to capture one: who was there, what was said, and the "
                                  "topics to follow up.")
        rv.addWidget(self.empty)
        self.form = QWidget(); fv = QVBoxLayout(self.form); fv.setContentsMargins(0, 0, 0, 0)
        f = QFormLayout(); fv.addLayout(f)
        self.title = QLineEdit(); self.title.editingFinished.connect(lambda: self.save_fields())
        f.addRow("Meeting", self.title)
        when = QWidget(); wh = QHBoxLayout(when); wh.setContentsMargins(0, 0, 0, 0)
        self.date = QDateEdit(); self.date.setCalendarPopup(True); self.date.setDisplayFormat("yyyy-MM-dd")
        self.start = QTimeEdit(); self.start.setDisplayFormat("HH:mm"); self.end = QTimeEdit(); self.end.setDisplayFormat("HH:mm")
        for wdg in (self.date, self.start, self.end):
            wdg.editingFinished.connect(lambda: self.save_fields())
        wh.addWidget(self.date); wh.addWidget(D.label("from", "muted", wrap=False)); wh.addWidget(self.start)
        wh.addWidget(D.label("to", "muted", wrap=False)); wh.addWidget(self.end); wh.addStretch(1)
        f.addRow("When", when)
        from .people import NamesField
        self.people = NamesField(host, [], empty="(nobody yet)", title="Participants",
                                 on_change=lambda names: self.save_fields())
        f.addRow("Participants", self.people)
        # 3.20.3: the notes and the topics share the rest of the page (drag the bar between them); the notes start large
        body = QSplitter(Qt.Vertical); body.setChildrenCollapsible(False); body.setHandleWidth(D.SPACE["m"]); fv.addWidget(body, 1)
        nbox = QWidget(); nv = QVBoxLayout(nbox); nv.setContentsMargins(0, D.SPACE["s"], 0, 0); nv.setSpacing(D.SPACE["xs"])
        nh = QHBoxLayout(); nv.addLayout(nh)
        nh.addWidget(D.label("Notes", "label")); nh.addStretch(1)
        self.sel_btn = D.button("Make a topic of the selection", None, lambda: self.topic_from_selection(),
                                "Select words in the notes, then make them a topic to follow up (also on the right-click menu)")
        self.sel_btn.setEnabled(False); nh.addWidget(self.sel_btn)
        self.notes = QPlainTextEdit(); self.notes.setPlaceholderText(
            "What was said. Select any words and press Make a topic of the selection, or start a line with - or * "
            "(or Topic:, Action:, Decision:) and use Topics from notes.")
        self.notes.setMinimumHeight(220)
        self.notes.textChanged.connect(lambda: None if self._loading else self.host.status("Notes are saved when you leave the box."))
        self.notes.selectionChanged.connect(lambda: self.sel_btn.setEnabled(self.notes.textCursor().hasSelection()))
        self.notes.focusOutEvent = self._notes_out
        self.notes.setContextMenuPolicy(Qt.CustomContextMenu)
        self.notes.customContextMenuRequested.connect(self._notes_menu)
        nv.addWidget(self.notes, 1)
        body.addWidget(nbox)
        tbox = QWidget(); fv2 = QVBoxLayout(tbox); fv2.setContentsMargins(0, 0, 0, 0)
        th = QHBoxLayout(); fv2.addLayout(th)
        th.addWidget(D.label("Topics to follow up", "label")); th.addStretch(1)
        for text, fn, tip in (("+ Topic", lambda: self.add_topic(), "A topic this meeting raised"),
                              ("Topics from notes", lambda: self.from_notes(), "The notes' bullet lines as topics (you choose)"),
                              ("Considered", lambda: self.mark("considered"), "It was taken into account: who and when are kept"),
                              ("Not needed", lambda: self.mark("not_needed"), "Nothing to do: say why"),
                              ("Reopen", lambda: self.mark("open"), "Open again"),
                              ("Take out", lambda: self.remove_topic(), "Take the topic out")):
            th.addWidget(D.button(text, "ghost" if text not in ("+ Topic", "Considered") else None, fn, tip))
        self.topics = QTableWidget(0, 4); self.topics.setHorizontalHeaderLabels(["Topic", "Points at", "Owner", "Status"])
        self.topics.verticalHeader().setVisible(False); self.topics.setSelectionBehavior(QTableWidget.SelectRows)
        self.topics.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i, wdt in ((1, 200), (2, 140), (3, 190)):
            self.topics.setColumnWidth(i, wdt)
        self.topics.itemDoubleClicked.connect(lambda _i: self.edit_topic())
        fv2.addWidget(self.topics, 1)
        body.addWidget(tbox); body.setStretchFactor(0, 3); body.setStretchFactor(1, 2); body.setSizes([360, 240])
        self.body_split = body
        bot = QHBoxLayout(); fv.addLayout(bot)
        bot.addWidget(D.button("Export to Word...", None, lambda: self.export(), "The meeting, its notes and topics in Word"))
        bot.addStretch(1)
        bot.addWidget(D.button("Delete meeting", "danger", lambda: self.delete(), "Take the meeting and its topics out"))
        rv.addWidget(self.form, 1)
        split.addWidget(right); split.setSizes([320, 900])
        self.form.hide()

    # ------------------------------------------------------------ data
    def rec(self):
        return R_.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        rec = self.rec()
        self.setEnabled(rec is not None)
        keep = self.mid
        self.list.blockSignals(True)
        self.list.clear()
        if rec is None:
            self.list.blockSignals(False)
            return
        for m in MT.meetings(rec):
            n_open = sum(1 for t in m.get("topics", []) if t.get("status") == "open")
            if self.open_only.isChecked() and not n_open:
                continue
            it = QListWidgetItem(f"{m['date']}  {m['title']}" + (f"   ({n_open} open)" if n_open else ""))
            it.setData(Qt.UserRole, m["id"])
            self.list.addItem(it)
            if m["id"] == keep:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        n = MT.open_count(rec)
        self.summary.setText(f"{len(MT.meetings(rec))} meeting(s); " + (f"{n} topic(s) still open: each stays open until "
                             "someone marks it Considered or Not needed." if n else "every topic considered."))
        self.show(keep if keep and MT.get(rec, keep) else None)

    def show(self, mid):
        self.mid = mid
        rec = self.rec()
        m = MT.get(rec, mid) if (rec is not None and mid) else None
        self.form.setVisible(m is not None); self.empty.setVisible(m is None)
        if m is None:
            return
        self._loading = True
        try:
            self.title.setText(m["title"])
            self.date.setDate(QDate.fromString(m["date"], "yyyy-MM-dd"))
            self.start.setTime(QTime.fromString(m.get("start") or "09:00", "HH:mm"))
            self.end.setTime(QTime.fromString(m.get("end") or (m.get("start") or "10:00"), "HH:mm"))
            self.people.set_names(m.get("participants", []))
            self.notes.setPlainText(m.get("notes", ""))
            self.fill_topics(m)
        finally:
            self._loading = False

    def fill_topics(self, m):
        t = self.topics
        t.setRowCount(0)
        for x in m.get("topics", []):
            r = t.rowCount(); t.insertRow(r)
            st = MT.STATUS_NAME.get(x.get("status"), "") + (f" ({x['by']}, {x['at'][:10]})" if x.get("by") else "")
            for c, val in enumerate((x["text"], x.get("target", ""), x.get("owner", ""), st)):
                it = QTableWidgetItem(val); it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if c == 0:
                    it.setData(Qt.UserRole, x["id"])
                    if x.get("why"):
                        it.setToolTip(x["why"])
                if c == 3:
                    it.setForeground(D.color({"open": "warn", "considered": "ok"}.get(x.get("status"), "muted")))
                t.setItem(r, c, it)

    def _notes_out(self, e):
        QPlainTextEdit.focusOutEvent(self.notes, e)
        self.save_fields()

    def save_fields(self):
        if self._loading or not self.mid:
            return False
        rec = self.rec()
        ok = MT.update_meeting(rec, self.mid, title=self.title.text() or "Meeting", date=self.date.date().toString("yyyy-MM-dd"),
                               start=self.start.time().toString("HH:mm"), end=self.end.time().toString("HH:mm"),
                               participants=self.people.names(), notes=self.notes.toPlainText())
        if ok:
            self.host.status("Meeting saved.")
            self._relist()
        return ok

    def _relist(self):
        cur = self.list.currentItem()
        rec = self.rec()
        m = MT.get(rec, self.mid) if rec is not None else None
        if cur is not None and m is not None:
            n_open = sum(1 for t in m.get("topics", []) if t.get("status") == "open")
            cur.setText(f"{m['date']}  {m['title']}" + (f"   ({n_open} open)" if n_open else ""))

    # ------------------------------------------------------------ actions
    def new_meeting(self, title=None, date=None, participants=None):
        rec = self.rec()
        if rec is None:
            return None
        if title is None:
            title, ok = QInputDialog.getText(self, "New meeting", "What the meeting is (for example: Kickoff, Pink team debrief):")
            if not ok or not title.strip():
                return None
        mid = MT.add_meeting(rec, title, date or datetime.date.today().isoformat(), start="09:00", end="10:00",
                             participants=participants or [])
        if mid:
            diag.activity("meeting_added")
            self.mid = mid
            self.refresh()
        return mid

    def _targets(self):
        """What a topic can point at: the structure's sections and the requirements."""
        out = [""]
        R = self.host.review
        if R is not None:
            import compliance as C
            out += [C.outline_label(o) for o in R.M.outline]
            out += [it["id"] for it in R.M.items if it.get("decision") == "Keep"]
        return out

    def add_topic(self, text=None, target="", owner="", prefill=""):
        if not self.mid:
            return None
        if text is None:
            d = QDialog(self); d.setWindowTitle("A topic to follow up"); d.setMinimumWidth(560); f = QFormLayout(d)
            te = QLineEdit(prefill); f.addRow("Topic", te)
            tg = QComboBox(); tg.setEditable(True); tg.addItems(self._targets()); f.addRow("Points at", tg)
            ow = QComboBox(); ow.setEditable(True); ow.addItem(""); ow.addItems(self.host.people()); f.addRow("Owner", ow)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            f.addRow(bb)
            if d.exec() != QDialog.Accepted or not te.text().strip():
                return None
            text, target, owner = te.text(), tg.currentText(), ow.currentText()
        tid = MT.add_topic(self.rec(), self.mid, text, owner=owner, target=target)
        if tid:
            diag.activity("meeting_topic_added")
            self.refresh()
        return tid

    def selection_text(self):
        """The words selected in the notes, as one line (a bullet or Topic: in front taken off)."""
        import re
        t = self.notes.textCursor().selectedText().replace("\u2029", " ").replace("\u2028", " ")
        t = re.sub(r"\s+", " ", t).strip()
        return re.sub(r"^(?:[-*\u2022]\s*|(?:topic|action|decision)\s*:\s*)", "", t, flags=re.I).strip()

    def topic_from_selection(self, ask=True):
        """3.20.3: the selected words in the notes become a topic: the topic box opens with them, to add what it points at
        and an owner (ask=False: tests)."""
        text = self.selection_text()
        if not self.mid or not text:
            self.host.status("Select words in the notes first.")
            return None
        self.save_fields()
        tid = self.add_topic(prefill=text) if ask else self.add_topic(text)
        if tid:
            diag.activity("meeting_topic_from_selection")
        return tid

    def _notes_menu(self, at):
        m = self.notes.createStandardContextMenu()
        m.addSeparator()
        a = m.addAction("Make a topic of the selection", lambda: self.topic_from_selection())
        a.setEnabled(self.notes.textCursor().hasSelection())
        m.exec(self.notes.mapToGlobal(at))

    def from_notes(self, picked=None):
        """The notes' bullet lines as topics: each one you keep (picked: tests) becomes a topic."""
        if not self.mid:
            return 0
        self.save_fields()
        rec = self.rec()
        m = MT.get(rec, self.mid)
        have = {t["text"].casefold() for t in m.get("topics", [])}
        found = [x for x in MT.topics_from_notes(m.get("notes", "")) if x.casefold() not in have]
        if not found:
            self.host.status("No bullet lines in the notes that are not topics already. Start a line with - or Topic:.")
            return 0
        if picked is None:
            d = QDialog(self); d.setWindowTitle("Topics from notes"); d.resize(620, 420); v = QVBoxLayout(d)
            v.addWidget(D.label("Tick the lines to follow up as topics.", "muted"))
            lst = QListWidget(); v.addWidget(lst, 1)
            for x in found:
                it = QListWidgetItem(x); it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked); lst.addItem(it)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return 0
            picked = [lst.item(i).text() for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked]
        n = sum(1 for x in picked if MT.add_topic(rec, self.mid, x))
        if n:
            diag.activity("meeting_topics_from_notes", n=n)
        self.refresh()
        return n

    def selected_topic(self):
        r = self.topics.currentRow()
        it = self.topics.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it is not None else None

    def mark(self, status, why=None):
        tid = self.selected_topic()
        if not self.mid or not tid:
            self.host.status("Click a topic first.")
            return False
        if status == "not_needed" and why is None:
            why, ok = QInputDialog.getText(self, "Not needed", "Why (kept with the topic):")
            if not ok:
                return False
        ok = MT.set_status(self.rec(), self.mid, tid, status, why or "")
        if ok:
            diag.activity("meeting_topic_status")
            self.refresh()
        return ok

    def edit_topic(self):
        tid = self.selected_topic()
        t = MT.topic(self.rec(), self.mid, tid) if tid else None
        if t is None:
            return False
        d = QDialog(self); d.setWindowTitle("Topic"); d.setMinimumWidth(560); f = QFormLayout(d)
        te = QLineEdit(t["text"]); f.addRow("Topic", te)
        tg = QComboBox(); tg.setEditable(True); tg.addItems(self._targets()); tg.setCurrentText(t.get("target", "")); f.addRow("Points at", tg)
        ow = QComboBox(); ow.setEditable(True); ow.addItem(""); ow.addItems(self.host.people()); ow.setCurrentText(t.get("owner", "")); f.addRow("Owner", ow)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        f.addRow(bb)
        if d.exec() != QDialog.Accepted:
            return False
        MT.update_topic(self.rec(), self.mid, tid, text=te.text() or t["text"], target=tg.currentText(), owner=ow.currentText())
        self.refresh()
        return True

    def remove_topic(self):
        tid = self.selected_topic()
        if not tid:
            return False
        ok = MT.remove_topic(self.rec(), self.mid, tid)
        self.refresh()
        return ok

    def export(self, path=None):
        if not self.mid:
            return None
        rec = self.rec()
        m = MT.get(rec, self.mid)
        if path is None:
            import effortfolders as EF
            start = EF.folder(self.host.effort_path, "exports") if self.host.effort_path else ""
            safe = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in m["title"]).strip() or "Meeting"
            path, _ = QFileDialog.getSaveFileName(self, "Export the meeting", os.path.join(start or "", f"{m['date']}_{safe}.docx"),
                                                  "Word (*.docx)")
            if not path:
                return None
        got = MT.export_docx(rec, self.mid, path)
        if got:
            diag.activity("meeting_exported")
            self.host.status("Meeting saved to Word.")
        return got

    def delete(self, confirm=None):
        if not self.mid:
            return False
        if confirm is None:
            from PySide6.QtWidgets import QMessageBox
            confirm = QMessageBox.question(self, "Delete meeting", "Take this meeting and its topics out?") == QMessageBox.Yes
        if not confirm:
            return False
        MT.delete_meeting(self.rec(), self.mid)
        self.mid = None
        self.refresh()
        return True
