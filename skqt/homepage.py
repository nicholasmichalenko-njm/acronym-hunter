"""Effort home in Qt (2.62.0): the effort's working page. The stage track (where the effort is, days left in the stage),
the gate goals of the current stage (the app ticks the ones it can check), tasks, notes and open questions, a
calendar of due dates, stages, tasks and what happened, customer information, and the latest of the timeline. One
"Show tasks and questions for" filter picks a person. Everything is kept in the effort's record (record.json), the same
file the classic window uses; one program holds an effort at a time. Rules only; nothing leaves the PC."""
import datetime
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QTextCharFormat
from PySide6.QtWidgets import (QCalendarWidget, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
                               QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPlainTextEdit, QScrollArea,
                               QMessageBox, QVBoxLayout, QWidget)
import diag
import effortrec as R
import effortstate as ES
from . import design as D

CAL_TONE = {"due": "crit", "questions": "cust", "stage": "accent", "task": "warn", "done": "ok", "event": "muted"}
CAL_ORDER = ("due", "questions", "stage", "task", "done", "event")
CAL_WORDS = (("due", "Due"), ("questions", "Questions due"), ("stage", "Stages"), ("task", "Tasks due"), ("done", "Tasks done"),
             ("event", "What happened"))
KIND_WORDS = {"customer": "CUSTOMER", "ours": "OURS", "stage": "STAGE", "note": "NOTE", "task": "TASK", "assign": "PEOPLE",
              "requirement": "REQUIREMENT", "effort": "EFFORT", "qa": "QA/QC", "compliance": "COMPLIANCE", "deliverable": "DELIVERABLE", "gate": "GATE", "review": "REVIEW"}


def clear(layout):
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif it.layout() is not None:
            clear(it.layout())


def plural(n, word, many=None):
    return f"{n} {word if n == 1 else (many or word + 's')}"


class ClickLabel(QLabel):
    """2.86.0: a goal's wording: click it to change it."""

    def __init__(self, text, on_click):
        super().__init__(text)
        self.setWordWrap(True)
        self.on_click = on_click
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.on_click()
        super().mouseReleaseEvent(e)


class HomePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.state = None
        self.day = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        inner = QWidget(); inner.setObjectName("page"); scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.due = D.Pill("", "accent"); top.addWidget(self.due)
        top.addStretch(1)
        top.addWidget(D.label("Show tasks and questions for", "muted", wrap=False))
        self.who = QComboBox(); self.who.setMinimumWidth(180); self.who.addItem("Everyone")
        self.who.activated.connect(lambda _i: self.refresh())
        top.addWidget(self.who)
        # the stage track
        self.move_btn = D.button("Move stage...", "primary", self.move_dialog, "Move the effort to its next stage")
        self.track = D.Card("Stage", "Where the effort is. The stage moves only when you move it.", actions=[self.move_btn])
        self.track_row = QHBoxLayout(); self.track_row.setSpacing(D.SPACE["xs"]); self.track.body.addLayout(self.track_row)
        v.addWidget(self.track)
        grid = QGridLayout(); grid.setSpacing(D.SPACE["m"]); v.addLayout(grid)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        self.goals = D.Card("Gate goals", actions=[D.button("+ Goal", None, lambda: self.goal_dialog()),
                                                   D.button("Defaults...", "ghost", lambda: self.save_defaults(),
                                                            "Save this stage's goals as the default for new efforts")])
        self.tasks = D.Card("Tasks", actions=[D.button("+ Task", None, lambda: self.task_dialog())])
        self.notes = D.Card("Notes and open questions", actions=[D.button("+ Note", None, lambda: self.note_dialog()),
                                                                 D.button("+ Question", None, lambda: self.note_dialog(question=True))])
        self.cal_card = D.Card("Calendar", "Due dates, stages, tasks and what happened. Pick a day to see it.")
        for c, r, col in ((self.goals, 0, 0), (self.notes, 0, 1), (self.tasks, 1, 0), (self.cal_card, 1, 1)):
            grid.addWidget(c, r, col, Qt.AlignTop)
        self.cal = QCalendarWidget(); self.cal.setGridVisible(False); self.cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.cal.setFirstDayOfWeek(Qt.Monday); self.cal.setMinimumHeight(260)
        plain = QTextCharFormat(); plain.setForeground(D.color("text"))
        for day in (Qt.Saturday, Qt.Sunday):                  # red is for due dates here, not weekends
            self.cal.setWeekdayTextFormat(day, plain)
        head = QTextCharFormat(); head.setForeground(D.color("muted")); head.setFontWeight(600)
        self.cal.setHeaderTextFormat(head)
        self.cal.clicked.connect(lambda d: self.pick_day(d.toPython()))
        self.cal.currentPageChanged.connect(lambda _y, _m: self.paint_calendar())
        self.cal_card.add(self.cal)
        leg = QHBoxLayout(); leg.setSpacing(D.SPACE["m"])
        t = D.tokens()
        for kind, word in CAL_WORDS:
            leg.addWidget(D.label(f"<span style='color:{t[CAL_TONE[kind]]}'>■</span> {word}", "muted", wrap=False))
        leg.addStretch(1)
        self.cal_card.body.addLayout(leg)
        self.day_box = QVBoxLayout(); self.day_box.setSpacing(2); self.cal_card.body.addLayout(self.day_box)
        self.info = D.Card("Customer information", "Names, e-mails, phone numbers and addresses from the customer documents.",
                           actions=[D.button("+ Add...", None, lambda: self.info_dialog())])
        v.addWidget(self.info)
        self.timeline = D.Card("Timeline", "The effort's paper trail, newest first.")
        v.addWidget(self.timeline)
        v.addStretch(1)
        self.sections = {k: QVBoxLayout() for k in ("goals", "tasks", "notes", "info", "timeline")}
        for k, card in (("goals", self.goals), ("tasks", self.tasks), ("notes", self.notes), ("info", self.info),
                        ("timeline", self.timeline)):
            self.sections[k].setSpacing(D.SPACE["xs"]); card.body.addLayout(self.sections[k])

    # ------------------------------------------------------------ the effort
    @property
    def rec(self):
        return self.state.rec if self.state is not None else None

    def person(self):
        w = self.who.currentText()
        return None if w in ("", "Everyone") else w

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            self.state = None
            for lay in list(self.sections.values()) + [self.track_row, self.day_box]:
                clear(lay)
            self.sections["goals"].addWidget(D.EmptyState("No effort open", "Pick an effort in the top bar."))
            return
        self.state = ES.State(h.ws, h.effort_path, h.review.M if h.review is not None else None)
        r = self.rec
        keep = self.who.currentText()
        people = self.state.people()
        self.who.clear(); self.who.addItems(["Everyone"] + people)
        self.who.setCurrentText(keep if keep in people else "Everyone")
        due = r.data.get("due", "")
        self.due.setText(("Due " + R.due_text(due, r.data.get("zone", "")) + "  ·  " + R.countdown_text(due)) if due
                         else "No due date set yet")
        self.due.set_tone("accent" if due else "head")
        checks = self.checks = self.state.checks()
        self.draw_track(r)
        self.draw_goals(r, checks)
        self.draw_tasks(r)
        self.draw_notes(r)
        self.draw_info(r)
        self.draw_timeline(r)
        self.paint_calendar()
        self.show_day()

    def changed(self):
        self.refresh()

    # ------------------------------------------------------------ stage track
    def draw_track(self, r):
        clear(self.track_row)
        t = D.tokens()
        for s in r.stages:
            st = r.state_of(s)
            tm = r.stage_timing(s)
            plan = (f"{R.short_date(s['planned'])} to {R.short_date(s['planned_end'])}" if s.get("planned") and s.get("planned_end")
                    else R.short_date(s.get("planned", "")))
            when = R.short_date(s["started"]) if st != "ahead" else plan
            if st == "current" and tm["end"]:
                when = (when + "\n" if when else "") + (f"{plural(tm['left'], 'day')} left" if tm["left"] is not None
                                                         else f"{plural(tm['over'], 'day')} past plan")
            bg, fg = {"done": (t["ok_soft"], t["ok"]), "current": (t["accent"], t["accent_fg"]),
                      "ahead": (t["surface2"], t["muted"])}[st]
            if st == "current" and tm["over"]:
                bg, fg = t["warn_soft"], t["warn"]
            if r.gate_of(s):                                         # 2.63.0
                when = (when + "\n" if when else "") + ("hard gate" if r.gate_of(s) == "hard" else "soft gate")
            f = QFrame(); f.setObjectName("stage")
            f.setStyleSheet(f"QFrame#stage{{background:{bg};border-radius:{D.RADIUS['card']}px;border:1px solid "
                            f"{t['border'] if st == 'ahead' else bg};}} QLabel{{background:transparent;color:{fg};}}")
            fv = QVBoxLayout(f); fv.setContentsMargins(D.SPACE["s"], D.SPACE["s"], D.SPACE["s"], D.SPACE["s"]); fv.setSpacing(0)
            name = D.label(s["name"] + ("  ✓" if st == "done" else "")); name.setAlignment(Qt.AlignCenter)
            name.setStyleSheet("font-weight:600;" if st == "current" else "")
            fv.addWidget(name)
            if when:
                w = D.label(when); w.setAlignment(Qt.AlignCenter); w.setStyleSheet(f"font-size:{D.TYPE['small']}pt;")
                fv.addWidget(w)
            met, total = r.goal_progress(s["id"], checks=self.checks if st == "current" else None)
            f.setToolTip(f"{s['name']}: {met} of {total} gate goals met")
            self.track_row.addWidget(f, 1)
        nxt = r.index() + 1
        self.move_btn.setText(f"Move to {r.stages[nxt]['name']}..." if nxt < len(r.stages) else "Move stage...")

    def move_dialog(self, run=True):
        r = self.rec
        if r is None:
            return None
        dlg = QDialog(self); dlg.setWindowTitle("Move stage")
        v = QVBoxLayout(dlg)
        v.addWidget(D.label(f"The effort is in {r.stage()['name']}. Move it to:", "title"))
        to = QComboBox()
        for s in r.stages:
            if s["id"] != r.data["stage"]:
                to.addItem(s["name"], s["id"])
        nxt = r.index() + 1
        if nxt < len(r.stages):
            to.setCurrentIndex(to.findData(r.stages[nxt]["id"]))
        v.addWidget(to)
        checks = self.checks
        open_goals = [g for g in r.stage()["goals"] if not r.goal_done(g, checks)]
        boxes = []
        if open_goals:
            v.addWidget(D.label("Open goals to carry over to the new stage:", "muted"))
            for g in open_goals:
                cb = QCheckBox(g["text"]); cb.setChecked(True); v.addWidget(cb); boxes.append((cb, g["id"]))
        gate = QLabel(); gate.setWordWrap(True); v.addWidget(gate)          # 2.63.0: the stage's gate
        reason = QLineEdit(); reason.setPlaceholderText("Reason (kept in the timeline)"); v.addWidget(reason)

        def show_gate():
            gc = r.gate_check(to.currentData(), checks)
            n = len(gc["open"])
            if not (gc["forward"] and gc["mode"] and n):
                gate.setText(""); gate.hide(); reason.hide()
                return gc
            t = D.tokens()
            hard = gc["mode"] == "hard"
            gate.setStyleSheet(f"background:{t['crit_soft' if hard else 'warn_soft']};color:{t['crit' if hard else 'warn']};"
                               f"border-radius:{D.RADIUS['control']}px;padding:8px;font-weight:600;")
            gate.setText((f"Hard gate: {r.stage()['name']} has {plural(n, 'open goal')}. Moving on is held until they are met; "
                          "the proposal manager can override it with a reason.") if hard else
                         (f"Soft gate: {plural(n, 'open goal')}. Moving on is allowed and logged with the open goals."))
            gate.show(); reason.setVisible(True)
            return gc
        to.currentIndexChanged.connect(lambda _i: show_gate())
        show_gate()
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); v.addWidget(bb)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        dlg.api = {"to": to, "carry": boxes, "gate": gate, "reason": reason, "show_gate": show_gate}
        if not run:
            return dlg
        while dlg.exec() == QDialog.Accepted:
            ok = self.move_stage(to.currentData(), [gid for cb, gid in boxes if cb.isChecked()], reason.text())
            if ok is not None:
                return ok
            reason.setFocus()                                   # held by a hard gate: a reason is needed
        return None

    def move_stage(self, sid, carry=(), reason=""):
        """Move the effort; None when a hard gate holds the move and no reason was given."""
        try:
            ok = self.rec.move_to(sid, carry=carry, reason=reason, checks=self.checks)
        except R.GateClosed as e:
            self.host.status(str(e))
            diag.activity("qt_gate_held")
            return None
        if ok:
            self.host.toast(f"Moved to {self.rec.stage()['name']}")
            diag.activity("qt_stage_moved")
            self.changed()
        return ok

    # ------------------------------------------------------------ gate goals
    def draw_goals(self, r, checks):
        lay = self.sections["goals"]; clear(lay)
        s = r.stage()
        n, total = r.goal_progress(checks=checks)
        self.goals.title.setText(f"{s['name']}: gate goals   {n} of {total}")
        bar = D.StackBar(8); bar.set([(n, "ok", "Met"), (total - n, "border", "Open")]); lay.addWidget(bar)
        if not s["goals"]:
            lay.addWidget(D.label("No goals for this stage yet. + Goal adds one.", "muted"))
        for g in s["goals"]:
            done = r.goal_done(g, checks)
            auto = bool(g.get("auto")) and checks.get(g["auto"]) is not None
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            if auto:                                                  # the app knows: a mark, not a box to tick
                cb = D.label("\u2713" if done else "\u2717", wrap=False)
                cb.setStyleSheet(f"color:{D.tokens()['ok' if done else 'crit']};font-weight:700;font-size:{D.TYPE['title']}pt;")
                cb.setFixedWidth(18); cb.setToolTip("The app checks this one")
            else:
                cb = QCheckBox(); cb.setChecked(done); cb.setToolTip("Tick when it is done")
                cb.toggled.connect(lambda on, gid=g["id"]: self.set_goal(gid, on))
            row.addWidget(cb, 0, Qt.AlignTop)
            txt = ClickLabel(g["text"] + (f"   (from {g['from']})" if g.get("from") else ""),   # 2.86.0: click to change it
                             lambda gid=g["id"]: self.goal_dialog(gid))
            txt.setToolTip("Click to change the wording, remove it, or tick it by hand")
            row.addWidget(txt, 1)
            row.addWidget(D.label("by the app" if auto else ("by hand" + (f": {g['by']}" if g.get("by") and done else "")),
                                  "muted", wrap=False), 0, Qt.AlignTop)
            lay.addLayout(row)

    def set_goal(self, gid, on):
        self.rec.set_goal(self.rec.data["stage"], gid, on)
        diag.activity("qt_goal_set")
        self.changed()

    def goal_dialog(self, gid=None, text=None, action=None):
        """Add a goal, or (2.86.0) change one: its wording, remove it, or tick it by hand instead of the app's check.
        action (tests): 'remove' or 'manual'."""
        r = self.rec
        if r is None:
            return None
        g = next((x for x in r.stage()["goals"] if x["id"] == gid), None) if gid else None
        if g is not None and text is None and action is None:
            text, action = self._goal_box(g)
            if text is None and action is None:
                return None
        if action == "remove":
            return self.remove_goal(gid)
        if action == "manual":
            ok = r.make_manual(r.data["stage"], gid)
            diag.activity("qt_goal_made_manual")
            self.changed()
            if text is None or text == g["text"]:
                return ok
        if text is None:
            text, ok = QInputDialog.getText(self, "Gate goal", "What has to be true before the effort leaves this stage:",
                                            QLineEdit.Normal, g["text"] if g else "")
            if not ok:
                return None
        if g is not None:
            r.edit_goal(r.data["stage"], gid, text)
            diag.activity("qt_goal_edited")
            self.changed()
            return gid
        nid = r.add_goal(r.data["stage"], text)
        if nid:
            diag.activity("qt_goal_added")
            self.changed()
        return nid

    def _goal_box(self, g):
        """(new wording or None, 'remove' | 'manual' | None) from a small dialog about one goal."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
        d = QDialog(self); d.setWindowTitle("Gate goal"); d.setMinimumWidth(520)
        v = QVBoxLayout(d)
        v.addWidget(D.label("What has to be true before the effort leaves this stage:", "muted"))
        ed = QLineEdit(g["text"]); v.addWidget(ed)
        if g.get("auto"):
            v.addWidget(D.label("The app checks this one. Tick it by hand instead if the check does not fit this effort.", "muted"))
        out = {"action": None}
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        rm = bb.addButton("Remove it", QDialogButtonBox.DestructiveRole)
        rm.clicked.connect(lambda: (out.update(action="remove"), d.accept()))
        if g.get("auto"):
            mb = bb.addButton("Tick it by hand", QDialogButtonBox.ActionRole)
            mb.clicked.connect(lambda: (out.update(action="manual"), d.accept()))
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        v.addWidget(bb)
        if d.exec() != QDialog.Accepted:
            return None, None
        t = " ".join(ed.text().split())
        return (t if t and t != g["text"] else None), out["action"]

    def save_defaults(self, answer=None):
        """2.86.0: this stage's goals become the default for the same stage in new efforts (this PC; team defaults later)."""
        r = self.rec
        if r is None:
            return None
        s = r.stage()
        if answer is None:
            answer = QMessageBox.question(self, "Default gate goals", f"Use these {len(s['goals'])} goals for {s['name']} in every new "
                                          "effort on this PC? Efforts already started keep their own goals.") == QMessageBox.Yes
        if not answer:
            return None
        import effortrec as ER
        keys = ER.save_default_goals(self.host.config_dir, s["name"], s["goals"])
        diag.activity("qt_goal_defaults_saved", n=len(keys))
        self.host.toast(f"New efforts start {s['name']} with these {len(keys)} goals")
        return keys

    def remove_goal(self, gid):
        ok = self.rec.remove_goal(self.rec.data["stage"], gid)
        diag.activity("qt_goal_removed")
        self.changed()
        return ok

    # ------------------------------------------------------------ tasks
    def draw_tasks(self, r):
        lay = self.sections["tasks"]; clear(lay)
        who = self.person()
        ts = r.tasks(owner=who)
        self.tasks.title.setText(f"Tasks   {sum(1 for t in ts if t['status'] != 'Done')} open")
        if who:
            M = self.state.M
            import setupdoc as SD
            secs = SD.sections_of(M, who) if M is not None else []
            reqs = sum(1 for it in M.items if it["decision"] == "Keep" and who in SD.owners_list(M, it)) if M is not None else 0
            lay.addWidget(D.label(f"{who}: {plural(len(secs), 'section')}" + (f" ({', '.join(secs[:4])}{'...' if len(secs) > 4 else ''})" if secs else "")
                                  + f", {plural(reqs, 'compliance requirement')}", "muted"))
        if not ts:
            lay.addWidget(D.label("No tasks." if not who else f"No tasks for {who}.", "muted"))
        for t in ts[:14]:
            late = r.task_overdue(t)
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            tone = "ok" if t["status"] == "Done" else "crit" if late else "accent" if t["status"] == "In progress" else "head"
            p = D.Pill(t["status"] + (" (late)" if late else ""), tone); p.setFixedWidth(130); row.addWidget(p)
            b = D.button(t["title"], "ghost", lambda _=False, tid=t["id"]: self.task_dialog(tid))
            b.setStyleSheet("text-align:left;"); row.addWidget(b, 1)
            row.addWidget(D.label(" | ".join(x for x in (t["owner"], ("due " + R.nice_date(t["due"])) if t["due"] else "") if x),
                                  "muted", wrap=False))
            lay.addLayout(row)
        if len(ts) > 14:
            lay.addWidget(D.label(f"and {len(ts) - 14} more", "muted"))

    def task_dialog(self, tid=None, due="", run=True):
        r = self.rec
        if r is None:
            return None
        t = r.task(tid) if tid else None
        dlg = QDialog(self); dlg.setWindowTitle("Task" if t else "New task"); dlg.setMinimumWidth(480)
        form = QFormLayout(dlg)
        title = QLineEdit(t["title"] if t else "")
        from .people import combo_name, name_combo       # 2.77.0: owners come from the author list only
        owner = name_combo(self.host, t["owner"] if t else (self.person() or ""))
        has_due = QCheckBox("Due on")
        when = QDateEdit(); when.setCalendarPopup(True); when.setDisplayFormat("MMM d, yyyy")
        d = R.parse_date(t["due"]) if t and t.get("due") else R.parse_date(due) if due else None
        has_due.setChecked(d is not None)
        when.setDate(QDate(d) if d else QDate.currentDate().addDays(7))
        when.setEnabled(d is not None); has_due.toggled.connect(when.setEnabled)
        drow = QHBoxLayout(); drow.addWidget(has_due); drow.addWidget(when, 1)
        status = QComboBox(); status.addItems(R.TASK_STATUS); status.setCurrentText(t["status"] if t else R.TASK_STATUS[0])
        stage = QComboBox()
        for s in r.stages:
            stage.addItem(s["name"], s["id"])
        stage.setCurrentIndex(stage.findData(t["stage"] if t else r.data["stage"]))
        notes = QPlainTextEdit(t.get("notes", "") if t else ""); notes.setFixedHeight(80)
        form.addRow("Task", title); form.addRow("Owner", owner); form.addRow("Due", drow); form.addRow("Status", status)
        form.addRow("Stage", stage); form.addRow("Notes", notes)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if t:
            rm = bb.addButton("Remove", QDialogButtonBox.DestructiveRole)
            rm.clicked.connect(lambda: (self.remove_task(tid), dlg.reject()))
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        form.addRow(bb)

        def values():
            return {"title": title.text(), "owner": combo_name(owner), "due": when.date().toPython().isoformat() if has_due.isChecked() else "",
                    "status": status.currentText(), "stage": stage.currentData(), "notes": notes.toPlainText()}
        dlg.api = {"title": title, "owner": owner, "has_due": has_due, "when": when, "status": status, "stage": stage, "notes": notes,
                   "values": values}
        if not run:
            return dlg
        if dlg.exec() == QDialog.Accepted:
            return self.save_task(tid, values())
        return None

    def save_task(self, tid, values):
        r = self.rec
        if tid:
            r.update_task(tid, **values)
            diag.activity("qt_task_changed")
            self.changed()
            return tid
        nid = r.add_task(values.get("title", ""), owner=values.get("owner", ""), due=values.get("due", ""), stage=values.get("stage", ""),
                         notes=values.get("notes", ""))
        if nid and values.get("status") and values["status"] != R.TASK_STATUS[0]:
            r.update_task(nid, status=values["status"])
        if nid:
            diag.activity("qt_task_added")
            self.changed()
        return nid

    def remove_task(self, tid):
        ok = self.rec.remove_task(tid)
        diag.activity("qt_task_removed")
        self.changed()
        return ok

    # ------------------------------------------------------------ notes and questions
    def draw_notes(self, r):
        lay = self.sections["notes"]; clear(lay)
        who = self.person()
        qs = r.open_questions(assignee=who)
        others = [n for n in r.notes() if not (n["question"] and not n["resolved"])] if not who else []
        self.notes.title.setText(f"Notes and open questions   {len(qs)} open" + (f" for {who}" if who else ""))
        for n in (qs + others)[:14]:
            q = n["question"] and not n["resolved"]
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            p = D.Pill("QUESTION" if q else ("ANSWERED" if n["question"] else "NOTE"), "warn" if q else ("ok" if n["question"] else "head"))
            p.setFixedWidth(96); row.addWidget(p, 0, Qt.AlignTop)
            col = QVBoxLayout(); col.setSpacing(0)
            col.addWidget(D.label(n["text"] + (f"\nAnswer: {n['answer']}" if n.get("answer") else "")))
            col.addWidget(D.label(" | ".join(x for x in (n["label"], R.short_date(n["at"]), n["who"],
                                                          ("assigned to " + n["assignee"]) if n.get("assignee") else "") if x), "muted"))
            row.addLayout(col, 1)
            if q:
                row.addWidget(D.button("Resolve...", None, lambda _=False, nid=n["id"]: self.resolve_dialog(nid)), 0, Qt.AlignTop)
                row.addWidget(D.button("Assign...", "ghost", lambda _=False, nid=n["id"]: self.assign_dialog(nid)), 0, Qt.AlignTop)
            row.addWidget(D.button("Remove", "ghost", lambda _=False, nid=n["id"]: self.remove_note(nid)), 0, Qt.AlignTop)
            lay.addLayout(row)
        if len(qs) + len(others) > 14:
            lay.addWidget(D.label(f"and {len(qs) + len(others) - 14} more", "muted"))
        if not qs and not others:
            lay.addWidget(D.label("No notes yet." if not who else f"No open questions for {who}.", "muted"))

    def note_dialog(self, question=False, text=None, assignee=""):
        r = self.rec
        if r is None:
            return None
        if text is None:
            text, ok = QInputDialog.getMultiLineText(self, "Question" if question else "Note",
                                                     "The question for the team or the customer:" if question else "The note:")
            if not ok:
                return None
        nid = r.add_note(text, question=question)
        if nid and assignee:
            r.update_note(nid, assignee=assignee)
        if nid:
            diag.activity("qt_note_added")
            self.changed()
        return nid

    def resolve_dialog(self, nid, answer=None):
        if answer is None:
            answer, ok = QInputDialog.getMultiLineText(self, "Resolve the question", "The answer (optional):")
            if not ok:
                return False
        ok = self.rec.resolve_note(nid, answer)
        diag.activity("qt_question_resolved")
        self.changed()
        return ok

    def assign_dialog(self, nid, who=None):
        if who is None:                                  # 2.77.0: from the author list only
            from .people import pick_names
            got = pick_names(self.host, [], "Who answers the question", multi=False, parent=self)
            if not got:
                return False
            who = got[0]
        ok = self.rec.update_note(nid, assignee=who)
        diag.activity("qt_question_assigned")
        self.changed()
        return ok

    def remove_note(self, nid):
        ok = self.rec.remove_note(nid)
        diag.activity("qt_note_removed")
        self.changed()
        return ok

    # ------------------------------------------------------------ customer information
    def draw_info(self, r):
        lay = self.sections["info"]; clear(lay)
        info = r.customer_info()
        self.info.title.setText(f"Customer information   {len(info)}")
        if not info:
            lay.addWidget(D.label("None yet. + Add... files names, e-mails, phone numbers and addresses by kind.", "muted"))
        for kind in R.INFO_KINDS:
            for c in [c for c in info if c["kind"] == kind]:
                row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
                p = D.Pill(kind.upper(), "ctx"); p.setFixedWidth(150); row.addWidget(p)
                row.addWidget(D.label(c["value"]), 1)
                if c.get("source"):
                    row.addWidget(D.label(c["source"], "muted", wrap=False))
                row.addWidget(D.button("Remove", "ghost", lambda _=False, cid=c["id"]: self.remove_info(cid)))
                lay.addLayout(row)

    def info_dialog(self, text=None):
        if self.rec is None:
            return None
        if text is None:
            text, ok = QInputDialog.getText(self, "Customer information", "Name, e-mail, phone number or address (several are fine):")
            if not ok:
                return None
        added = self.rec.add_customer_info(text, source="typed in")
        diag.activity("qt_custinfo_added")
        self.changed()
        return added

    def remove_info(self, cid):
        ok = self.rec.remove_customer_info(cid)
        diag.activity("qt_custinfo_removed")
        self.changed()
        return ok

    # ------------------------------------------------------------ calendar
    def month_days(self):
        import calendar as CAL
        y, m = self.cal.yearShown(), self.cal.monthShown()
        first = datetime.date(y, m, 1)
        return self.state.calendar(first=first - datetime.timedelta(days=7),
                                   last=first.replace(day=CAL.monthrange(y, m)[1]) + datetime.timedelta(days=14))

    def paint_calendar(self):
        self.cal.setDateTextFormat(QDate(), QTextCharFormat())          # clears every marked day
        if self.state is None:
            return {}
        days = self.month_days()
        t = D.tokens()
        for d, items in days.items():
            kinds = [k for k, _t in items]
            top = next((k for k in CAL_ORDER if k in kinds), "event")
            f = QTextCharFormat()
            f.setFontWeight(700)
            f.setForeground(D.color(CAL_TONE[top]))
            f.setBackground(D.color(CAL_TONE[top] + "_soft") if CAL_TONE[top] + "_soft" in t else D.color("surface2"))
            f.setToolTip("\n".join(text for _k, text in items))
            self.cal.setDateTextFormat(QDate(d), f)
        return days

    def pick_day(self, d):
        self.day = None if d == self.day else d
        self.show_day()
        return self.day

    def show_day(self):
        clear(self.day_box)
        d = self.day
        if d is None or self.state is None:
            return []
        items = self.state.calendar(first=d, last=d).get(d, [])
        self.day_box.addWidget(D.label(d.strftime("%A, %B %d, %Y").replace(" 0", " "), "title"))
        t = D.tokens()
        for kind, text in items or [("event", "Nothing on this day.")]:
            self.day_box.addWidget(D.label(f"<span style='color:{t[CAL_TONE.get(kind, 'muted')]}'>■</span> {text}"))
        self.day_box.addWidget(D.button("+ Task due this day", None, lambda: self.task_dialog(due=d.isoformat())), 0, Qt.AlignLeft)
        return items

    # ------------------------------------------------------------ timeline
    def draw_timeline(self, r):
        lay = self.sections["timeline"]; clear(lay)
        ev = r.events(limit=15)
        if not ev:
            lay.addWidget(D.label("Nothing yet.", "muted"))
        for e in ev:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["m"])
            when = D.label(R.short_date(e["at"]) + ("  " + e["at"][11:16] if len(e["at"]) > 11 else ""), "mono", wrap=False)
            when.setFixedWidth(110); row.addWidget(when, 0, Qt.AlignTop)
            k = D.label(KIND_WORDS.get(e["kind"], e["kind"].upper()), "label", wrap=False); k.setFixedWidth(110)
            row.addWidget(k, 0, Qt.AlignTop)
            row.addWidget(D.label(e["text"]), 1)
            row.addWidget(D.label(e["who"], "muted", wrap=False), 0, Qt.AlignTop)
            lay.addLayout(row)
