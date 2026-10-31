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

CAL_TONE = {"due": "crit", "deadline": "warn", "questions": "cust", "meeting": "ctx", "stage": "accent", "task": "warn", "done": "ok", "event": "muted"}
CAL_ORDER = ("due", "deadline", "questions", "meeting", "stage", "task", "done", "event")
CAL_WORDS = (("due", "Proposal due"), ("deadline", "Due dates"), ("questions", "Questions due"), ("meeting", "Reviews and meetings"), ("stage", "Stages"), ("task", "Tasks due"),
             ("done", "Tasks done"), ("event", "What happened"))
KIND_WORDS = {"customer": "CUSTOMER", "ours": "OURS", "stage": "STAGE", "note": "NOTE", "task": "TASK", "assign": "PEOPLE",
              "requirement": "REQUIREMENT", "effort": "EFFORT", "qa": "QA/QC", "compliance": "COMPLIANCE", "deliverable": "DELIVERABLE", "gate": "GATE", "review": "REVIEW",
              "graphic": "GRAPHIC"}


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
        self.scroll = scroll
        # 3.0.3: with no effort open, Effort Home is where you start one: the short form, right here
        from .starteffort import StartEffort
        self.start_wrap = QScrollArea(); self.start_wrap.setWidgetResizable(True); self.start_wrap.setFrameShape(QFrame.NoFrame)
        sw = QWidget(); sw.setObjectName("page"); swl = QVBoxLayout(sw)
        swl.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        self.start = StartEffort(host); swl.addWidget(self.start); swl.addStretch(1)
        self.start_wrap.setWidget(sw); self.start_wrap.setVisible(False)
        outer.addWidget(self.start_wrap)
        inner = QWidget(); inner.setObjectName("page"); scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        # 2.88.0: the effort banner, then this person's layout
        from .brandview import EffortBanner
        self.banner = EffortBanner(self); v.addWidget(self.banner)
        self.due = self.banner.due
        self.deliv = self.banner.page_deliv
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.role_pill = D.Pill("", "head"); top.addWidget(self.role_pill)
        top.addWidget(D.button("Customize Home...", "ghost", lambda: self.customize(), "Your role's layout; show, hide and order the "
                                                                                       "sections. Yours alone, on this PC."))
        top.addStretch(1)
        top.addWidget(D.label("Show tasks and questions for", "muted", wrap=False))
        self.who = QComboBox(); self.who.setMinimumWidth(180); self.who.addItem("Everyone")
        self.who.activated.connect(lambda _i: self.refresh())
        top.addWidget(self.who)
        top.addWidget(D.button("Export tasks and questions...", None, lambda: self.export_tq(),
                               "A workbook of the tasks and questions for the person shown (or the full team), dated and named for them"))
        # 2.92.0: when one person is picked, their name, large, says the page is theirs
        self.for_box = QFrame(); self.for_box.setObjectName("forBox")
        fb = QHBoxLayout(self.for_box); fb.setContentsMargins(D.SPACE["l"], D.SPACE["s"], D.SPACE["l"], D.SPACE["s"])
        self.for_name = QLabel(""); self.for_name.setObjectName("forName"); fb.addWidget(self.for_name, 1)
        fb.addWidget(D.button("Show everyone", None, lambda: (self.who.setCurrentText("Everyone"), self.refresh())))
        t0 = D.tokens()
        self.for_box.setStyleSheet(f"QFrame#forBox{{background:{t0['accent_soft']};border-radius:{D.RADIUS['card']}px;}}"
                                   f"QLabel#forName{{font-size:18pt;font-weight:700;color:{t0['accent']};background:transparent;}}")
        self.for_box.setVisible(False)
        v.addWidget(self.for_box)
        # the stage track
        self.move_btn = D.button("Move stage...", "primary", self.move_dialog, "Move the effort to its next stage")
        self.track = D.Card("Stage", "Where the effort is. The stage moves only when you move it.",
                            actions=[D.button("Edit stages...", None, lambda: self.edit_stages(),
                                              "Rename, add, remove and reorder this effort's stages, with dates and gates"),
                                     self.move_btn])
        self.track_row = QHBoxLayout(); self.track_row.setSpacing(D.SPACE["xs"]); self.track.body.addLayout(self.track_row)
        self.deliv_card = D.Card("Deliverables", actions=[D.button("Open the board", None, lambda: self.host.go("deliverables"))])
        self.deliv_box = QVBoxLayout(); self.deliv_box.setSpacing(D.SPACE["xs"]); self.deliv_card.body.addLayout(self.deliv_box)
        self.mywork = D.Card("My work", "What is assigned to you in this effort.")
        self.mywork_box = QVBoxLayout(); self.mywork_box.setSpacing(D.SPACE["xs"]); self.mywork.body.addLayout(self.mywork_box)
        self.goals = D.Card("Gate goals", actions=[D.button("+ Goal", None, lambda: self.goal_dialog()),
                                                   D.button("Defaults...", "ghost", lambda: self.save_defaults(),
                                                            "Save this stage's goals as the default for new efforts")])
        self.tasks = D.Card("Tasks", actions=[D.button("+ Task", None, lambda: self.task_dialog())])
        self.notes = D.Card("Notes and open questions", actions=[D.button("+ Note", None, lambda: self.note_dialog()),
                                                                 D.button("+ Question", None, lambda: self.note_dialog(question=True))])
        from .calview import CalendarFiles                           # 2.88.0: the calendar as a file
        self.calfiles = CalendarFiles(self)
        self.cal_card = D.Card("Calendar", "Due dates, stages, tasks, reviews and meetings, and what happened. Pick a day to see it.",
                               actions=self.calfiles.buttons())
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
        self.cal_card.body.addLayout(self.calfiles.file_row())
        from .adaptive import FlowLayout                             # 3.0.4: the key wraps, so Home fits a 1440 screen
        leg = FlowLayout(None, D.SPACE["m"])
        t = D.tokens()
        for kind, word in CAL_WORDS:
            leg.addWidget(D.label(f"<span style='color:{t[CAL_TONE[kind]]}'>■</span> {word}", "muted", wrap=False))
        self.cal_card.body.addLayout(leg)
        self.day_box = QVBoxLayout(); self.day_box.setSpacing(2); self.cal_card.body.addLayout(self.day_box)
        self.info = D.Card("Customer information", "Names, e-mails, phone numbers and addresses from the customer documents.",
                           actions=[D.button("+ Add...", None, lambda: self.info_dialog())])
        self.timeline = D.Card("Timeline", "The effort's paper trail, newest first.")
        self.sub_card = D.Card("Submission instructions", "How and when the proposal goes in, as the customer documents say "  # 2.96.0
                               "it.", actions=[D.button("Submission rules", "ghost", lambda: self.host.go("requirements"))])
        self.fmt_card = D.Card("Formatting requirements", "What the customer documents require for format and files, and "     # 2.94.0
                               "what they leave unsaid.", actions=[D.button("+ Add...", None, lambda: self.format_dialog()),
                                                                   D.button("Submission rules", "ghost", lambda: self.host.go("requirements"))])
        self.qa_card = D.Card("Customer Q&A", "The questions we submit to the customer, and their answers.",          # 2.98.0
                              actions=[D.button("Customer Q&&A", "ghost", lambda: self.host.go("custqa"))])
        self.focus_card = D.Card("Evaluation and hot buttons", "How the customer will judge the proposal, and what their "   # 2.99.0
                                 "documents stress. Capture them in Review (More captures).")
        self.gfx_card = D.Card("Graphic needs", "Concepts and things that need a graphic, tagged in Review (Graphic need, P) "  # 3.0.4
                               "or from a note.", actions=[D.button("+ Graphic need...", None, lambda: self.graphic_dialog()),
                                                           D.button("Export...", "ghost", lambda: self.export_graphics(),
                                                                    "A dated workbook of the graphic needs, for the graphics team")])
        self.body = QVBoxLayout(); self.body.setSpacing(D.SPACE["m"]); v.addLayout(self.body)
        v.addStretch(1)
        self.cards = {"stage": self.track, "deliverables": self.deliv_card, "mywork": self.mywork, "goals": self.goals,
                      "notes": self.notes, "tasks": self.tasks, "calendar": self.cal_card, "info": self.info, "timeline": self.timeline,
                      "formatting": self.fmt_card, "submission": self.sub_card, "custqa": self.qa_card,
                      "custfocus": self.focus_card, "graphics": self.gfx_card}
        self.lay = None
        self.apply_layout()
        self.sections = {k: QVBoxLayout() for k in ("goals", "tasks", "notes", "info", "timeline", "formatting", "submission", "custqa", "custfocus",
                                                    "graphics")}
        for k, card in (("goals", self.goals), ("tasks", self.tasks), ("notes", self.notes), ("info", self.info),
                        ("timeline", self.timeline), ("formatting", self.fmt_card), ("submission", self.sub_card),
                        ("custqa", self.qa_card), ("custfocus", self.focus_card), ("graphics", self.gfx_card)):
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
        self.setEnabled(True)
        self.scroll.setVisible(h.ws is not None)
        self.start_wrap.setVisible(h.ws is None)                   # 3.0.3: no effort open: Start an effort, here
        if h.ws is None:
            self.state = None
            for lay in list(self.sections.values()) + [self.track_row, self.day_box]:
                clear(lay)
            return
        self.state = ES.State(h.ws, h.effort_path, h.review.M if h.review is not None else None)
        r = self.rec
        keep = self.who.currentText()
        people = self.state.people()
        self.who.clear(); self.who.addItems(["Everyone"] + people)
        me = self.my_name()
        if not getattr(self, "_who_set", False) and self.lay["role"] == "Author" and me in people:
            keep = me                                               # 2.88.0: an author starts on their own tasks
        self._who_set = True
        self.who.setCurrentText(keep if keep in people else "Everyone")
        p = self.person()
        self.for_box.setVisible(bool(p))
        self.for_name.setText(f"{p}: tasks and questions" if p else "")
        L = h.record_page.effort_list()
        try:
            stage = (r.stage() or {}).get("name", "")
        except Exception:
            stage = ""
        self.banner.fill(r, L, stage)                               # 2.88.0: the effort banner
        self.cards_now = []
        try:                                                        # 2.87.0: the deliverables in one line
            import delivboard as DB
            from .custdocs import Ctx
            c = Ctx(h)
            self.cards_now = DB.board(c.rec, c.reg.rows(), c.lib, c.volumes(), h.review.M if h.review is not None else None, h.ws.root,
                                      getattr(getattr(h.acronym_page, "session", None), "volume_report", None))
            self.deliv.setText(DB.summary_line(self.cards_now) + "  \u203a")
        except Exception:
            diag.swallowed()
            self.deliv.setText("Deliverables  \u203a")
        self.draw_deliverables()
        self.draw_mywork()
        self.calfiles.refresh()
        checks = self.checks = self.state.checks()
        self.draw_track(r)
        self.draw_formatting(r)
        self.draw_submission(r)
        self.draw_custqa(r)
        self.draw_focus(r)
        self.draw_graphics(r)
        self.draw_goals(r, checks)
        self.draw_tasks(r)
        self.draw_notes(r)
        self.draw_info(r)
        self.draw_timeline(r)
        self.paint_calendar()
        self.show_day()

    def changed(self):
        self.refresh()

    # ------------------------------------------------------------ 2.88.0: this person's layout
    def my_name(self):
        from .modes import settings
        return (settings() or {}).get("my_name", "")

    def apply_layout(self):
        import branding as BR
        from .modes import settings
        import teampack as TP
        self.team_roles = TP.roles(self.host.config_dir)              # 2.89.0: the team's layout for each role
        self.lay = BR.layout(settings(), self.team_roles)
        while self.body.count():                                     # take the cards out without deleting them
            it = self.body.takeAt(0)
            if it.layout() is not None:
                lay = it.layout()
                while lay.count():
                    x = lay.takeAt(0)
                    if x.widget() is not None:
                        x.widget().setParent(None)
                    elif x.layout() is not None:
                        while x.layout().count():
                            y = x.layout().takeAt(0)
                            if y.widget() is not None:
                                y.widget().setParent(None)
                        x.layout().deleteLater()
                lay.deleteLater()
            elif it.widget() is not None:
                it.widget().setParent(None)
        for c in self.cards.values():
            c.setParent(None)
        self.shown = BR.shown(self.lay)
        for row in BR.rows(self.shown):
            if len(row) == 1 and BR.WIDTH[row[0]] == "wide":
                self.body.addWidget(self.cards[row[0]])
            else:
                hl = QHBoxLayout(); hl.setSpacing(D.SPACE["m"])
                for k in row:                                     # a column each: the card at its full height, then space
                    col = QVBoxLayout(); col.setSpacing(0)
                    col.addWidget(self.cards[k]); col.addStretch(1)
                    hl.addLayout(col, 1)
                if len(row) == 1:
                    hl.addStretch(1)
                self.body.addLayout(hl)
        for k, c in self.cards.items():
            c.setVisible(k in self.shown)
        self.role_pill.setText(f"Home for: {self.lay['role']}" + ("  (customized)" if self.lay["custom"] else ""))
        return self.shown

    def customize(self, answer=None):
        """Customize Home. answer (tests): {role, order, hidden, me}."""
        import branding as BR
        from .modes import save
        if answer is None:
            from .brandview import CustomizeDialog
            names = self.state.people() if self.state is not None else []
            if not names and getattr(self.host, "authors", None) is not None:
                try:
                    names = self.host.authors.names()
                except Exception:
                    names = []
            dlg = CustomizeDialog(self, self.lay, names, self.my_name(), self.team_roles, self.host.config_dir)
            if dlg.exec() != QDialog.Accepted:
                return False
            answer = dlg.values()
        lay = BR.custom_layout(answer.get("role", self.lay["role"]), answer.get("order", self.lay["order"]), answer.get("hidden", []),
                               self.team_roles)
        kv = {"home_layout": BR.to_json(lay)}
        if "me" in answer:
            kv["my_name"] = answer["me"]
        save(**kv)
        diag.activity("qt_home_customized")
        self._who_set = False
        self.apply_layout()
        if self.host.ws is not None:
            self.refresh()
        return True

    def draw_deliverables(self):
        import delivboard as DB
        clear(self.deliv_box)
        cards = getattr(self, "cards_now", [])
        if not cards:
            self.deliv_box.addWidget(D.label("No deliverables yet. Add them on the board.", "muted"))
            return
        self.deliv_box.addWidget(D.label(DB.summary_line(cards), None))
        from .delivboardview import HEALTH, TONE
        for c in cards[:5]:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            row.addWidget(D.Pill(HEALTH[c["health"]], TONE[c["health"]]))
            row.addWidget(D.label(f"<b>{c['name']}</b>  " + (c["missing"][0][1] if c["missing"] else "Nothing missing"), None), 1)
            row.addWidget(D.button("Open", "ghost", lambda _=False, i=c["id"]: (self.host.go("deliverables"), self.host.deliverables_page.pick(i))))
            self.deliv_box.addLayout(row)
        if len(cards) > 5:
            self.deliv_box.addWidget(D.label(f"and {len(cards) - 5} more on the board", "muted"))

    def my_items(self):
        """(requirement rows, my tasks, my questions) for the person this Home is for."""
        me = self.my_name() or (self.person() or "")
        reqs, tasks, qs = [], [], []
        if not me:
            return me, reqs, tasks, qs
        h = self.host
        if h.review is not None:
            import setupdoc as SD
            wait = set()
            try:
                import changereview as CR
                wait = set(CR.Review(h.ws.root).load().awaiting())
            except Exception:
                diag.swallowed()
            for it in h.review.M.items:
                if it.get("decision") == "Keep" and (SD.owner_of(h.review.M, it) or "").casefold() == me.casefold():
                    reqs.append({"id": it["id"], "section": it.get("map", ""), "text": it.get("text", ""), "awaiting": it["id"] in wait})
        r = self.rec
        tasks = [t for t in r.tasks() if (t.get("owner") or "").casefold() == me.casefold() and t.get("status") != "Done"] if r else []
        try:
            qs = [n for n in r.notes() if n.get("question") and not n.get("resolved") and (n.get("assignee") or "").casefold() == me.casefold()]
        except Exception:
            qs = []
        return me, reqs, tasks, qs

    def draw_mywork(self):
        clear(self.mywork_box)
        if "mywork" not in getattr(self, "shown", []):
            return
        me, reqs, tasks, qs = self.my_items()
        if not me:
            self.mywork_box.addWidget(D.label("Customize Home > I am: pick your name, and what is assigned to you shows here.", "muted"))
            return
        wait = [x for x in reqs if x["awaiting"]]
        self.mywork_box.addWidget(D.label(f"<b>{me}</b>: {plural(len(reqs), 'requirement')} to answer"
                                          + (f", {len(wait)} changed by a customer version and waiting for you" if wait else "")
                                          + f", {plural(len(tasks), 'open task')}, {plural(len(qs), 'open question')}.", None))
        for x in (wait + [y for y in reqs if not y["awaiting"]])[:8]:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            if x["awaiting"]:
                row.addWidget(D.Pill("Confirm it", "warn"))
            row.addWidget(D.label(f"<b>{x['id']}</b>  {x['section']}", None), 1)
            row.addWidget(D.button("Open", "ghost", lambda _=False, i=x["id"]: self.host.deliverables_page.open_requirement(i)))
            self.mywork_box.addLayout(row)
        if len(reqs) > 8:
            self.mywork_box.addWidget(D.label(f"and {len(reqs) - 8} more in Review", "muted"))

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
                when = (when + "\n" if when else "") + R.GATES.get(r.gate_id(s), "gate").split(":")[0]   # 2.93.0: the team's name for it
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

    def edit_stages(self, run=True):
        """2.92.0: the stage table, here on Effort Home (the same as Effort Record's). run=False (tests): the dialog."""
        if self.host.ws is None:
            return None
        from .stagesedit import StagesDialog
        dlg = StagesDialog(self)
        if not run:
            return dlg
        dlg.exec()
        if dlg.saved:
            self.refresh()
        return dlg.saved

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
            gid = r.gate_id()                                          # 2.93.0: a team gate says its own name
            head = ("Hard gate" if hard else "Soft gate") if gid in ("soft", "hard") else \
                f"{R.GATES.get(gid, 'Gate').split(':')[0]} ({'held' if hard else 'logged'})"
            gate.setText((f"{head}: {r.stage()['name']} has {plural(n, 'open goal')}. Moving on is held until they are met; "
                          "the proposal manager can override it with a reason.") if hard else
                         (f"{head}: {plural(n, 'open goal')}. Moving on is allowed and logged with the open goals."))
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
    # ------------------------------------------------------------ 2.94.0 formatting requirements
    def draw_formatting(self, r):
        import formatreq as FR
        lay = self.sections["formatting"]; clear(lay)
        c = getattr(self.banner, "fmt", None) or FR.card([], r.data.get("page_limited", ""))
        self.fmt_now = c
        t = D.tokens()
        pl = c["page_limited"]
        head = D.label(FR.flag_text(c), "title" if pl is not None else None)
        head.setStyleSheet(f"font-weight:700;color:{t['warn' if pl else ('ok' if pl is False else 'muted')]};")
        lay.addWidget(head)
        for x in c["limits"][:6]:
            lay.addWidget(D.label((f"{x['subject']}: " if len(c["limits"]) > 1 or x["subject"] != "Proposal" else "") + x["value"]
                                  + (f"  ·  {x['where']}" if x["where"] else ""), "muted"))
        req = sum(1 for x in c["lines"] if x["required"])
        lay.addWidget(D.label(f"{req} of {len(c['lines'])} formatting rules required by the documents", "label"))
        for x in c["lines"]:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            lab = D.label(x["label"], None, wrap=False); lab.setMinimumWidth(170); row.addWidget(lab, 0, Qt.AlignTop)
            if x["required"]:
                col = QVBoxLayout(); col.setSpacing(0)
                val = ClickLabel(f"Required: {x['value']}", lambda: self.host.go("requirements"))
                val.setToolTip("Open Submission rules: the sentence, its history, edit or confirm")
                val.setStyleSheet(f"color:{t['text']};font-weight:600;")
                col.addWidget(val)
                if x["where"]:
                    col.addWidget(D.label(x["where"], "muted"))
                row.addLayout(col, 1)
                rr = x["row"]
                if rr is not None and rr.get("manual"):
                    row.addWidget(D.button("Remove", "ghost", lambda _=False, k=rr["key"]: self.format_remove(k)), 0, Qt.AlignTop)
                elif rr is not None:
                    row.addWidget(D.button("Not required", "ghost", lambda _=False, k=rr["key"]: self.format_hide(k),
                                           "The documents do not really require this (it stays in Submission rules, hidden)"), 0, Qt.AlignTop)
            else:
                row.addWidget(D.label("Not specified in the documents", "muted"), 1)
            lay.addLayout(row)

    def draw_submission(self, r):
        """2.96.0: due dates, delivery, copies and contacts, each with where it was found."""
        import formatreq as FR
        lay = self.sections["submission"]; clear(lay)
        try:
            lines = FR.submission(self._register().rows())
        except Exception:
            diag.swallowed()
            lines = []
        self.sub_now = lines
        if not lines:
            lay.addWidget(D.label("None found yet. Read the customer documents, or capture an instruction in Review "
                                  "(select the sentence, then Capture > Submission).", "muted"))
        t = D.tokens()
        for x in lines[:12]:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            lab = D.label(x["label"], None, wrap=False); lab.setMinimumWidth(130); row.addWidget(lab, 0, Qt.AlignTop)
            col = QVBoxLayout(); col.setSpacing(0)
            v = ClickLabel(x["value"], lambda: self.host.go("requirements")); v.setStyleSheet(f"color:{t['text']};font-weight:600;")
            col.addWidget(v)
            if x["where"]:
                col.addWidget(D.label(x["where"], "muted"))
            row.addLayout(col, 1)
            lay.addLayout(row)

    def draw_custqa(self, r):
        """2.98.0: how many questions are where, when questions are due, and the ones still open."""
        import custqa as Q
        from .custqapage import questions_due
        lay = self.sections["custqa"]; clear(lay)
        self.qa_now = Q.counts(r)
        due = questions_due(r)
        lay.addWidget(D.label(Q.summary(r) + (f"  \u00b7  Questions due {due}" if due else ""), None))
        open_ = [q for q in Q.items(r) if q.get("status") != "Answered"]
        t = D.tokens()
        for q in open_[:5]:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            row.addWidget(D.Pill(q.get("status", ""), {"Draft": "head", "Approved": "accent", "Submitted": "warn"}.get(q.get("status"), "head")), 0, Qt.AlignTop)
            v = ClickLabel(f"{q.get('n')}. {q.get('question') or q.get('quote')}"[:140], lambda: self.host.go("custqa"))
            v.setStyleSheet(f"color:{t['text']};"); v.setWordWrap(True)
            row.addWidget(v, 1)
            lay.addLayout(row)
        if not Q.items(r):
            lay.addWidget(D.label("In Review, select a sentence and press Capture > Question to quote it.", "muted"))

    def draw_focus(self, r):
        """2.99.0: the evaluation factors (subfactors under them) with their relative importance, then the hot buttons."""
        import custfocus as F
        lay = self.sections["custfocus"]; clear(lay)
        fs, hs = F.factors(r), F.hot_buttons(r)
        self.focus_now = {"factors": [f["name"] for f in fs], "hot": [h["text"] for h in hs]}
        if not fs and not hs:
            lay.addWidget(D.label("None yet. In Review, select the sentence and press More captures > Evaluation factor or Hot button.", "muted"))
            return
        for f in fs:
            imp = f.get("importance", "Not stated")
            lab = D.label(("    \u2022 " if f.get("parent") else "") + f["name"] + (f"  \u00b7  {imp}" if imp != "Not stated" else "")
                          + (f"  \u00b7  {f['doc']}" if f.get("doc") and not f.get("parent") else ""), None)
            lab.setToolTip(f.get("text", ""))
            lay.addWidget(lab)
        if hs:
            lay.addWidget(D.label("Hot buttons", "label"))
            for h in hs:
                lab = D.label("\u2022  " + h["text"], None); lab.setToolTip(h.get("quote", "")); lay.addWidget(lab)

    def _register(self):
        import docversions as DV
        import subreq as SR
        return SR.Register(DV.Library(self.host.ws.p("documents")).load())

    def format_dialog(self, answer=None):
        """+ Add...: a formatting rule the documents set that the app did not find (or one the team must follow).
        answer (tests): (rule, value)."""
        if self.host.ws is None:
            return None
        if answer is None:
            import formatreq as FR
            from PySide6.QtWidgets import QDialog, QDialogButtonBox
            d = QDialog(self); d.setWindowTitle("Formatting requirement"); f = QFormLayout(d)
            what = QComboBox(); what.setEditable(True); what.addItems([s for _k, s in FR.ASPECTS] + ["Page limit", "Headers and footers",
                                                                                                    "Page numbering", "Graphics and tables"])
            val = QLineEdit(); val.setPlaceholderText("12-point Times New Roman")
            f.addRow("Rule", what); f.addRow("Required", val)
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            f.addRow(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = (what.currentText(), val.text())
        rule, value = answer
        kind = "Page limit" if rule.strip().lower() == "page limit" else ("File" if rule.strip() in ("File format", "File naming") else "Format")
        k = self._register().add(kind, rule if kind != "Page limit" else "Proposal", value)
        if k:
            diag.activity("qt_format_rule_added")
            self.changed()
        return k

    def format_hide(self, key):
        ok = self._register().hide(key)
        diag.activity("qt_format_rule_hidden")
        self.changed()
        return ok

    def format_remove(self, key):
        ok = self._register().remove_manual(key)
        self.changed()
        return ok

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
            meta = [x for x in (g.get("owner", ""), ("due " + R.when_text(g["due"])) if g.get("due") else "") if x]   # 2.93.0
            late = bool(g.get("due")) and not done and (R.parse_when(g["due"], True) or datetime.datetime.max) < datetime.datetime.now()
            if meta:
                ml = D.label(" | ".join(meta) + ("  (late)" if late else ""), "muted", wrap=False)
                if late:
                    ml.setStyleSheet(f"color:{D.tokens()['crit']};")
                row.addWidget(ml, 0, Qt.AlignTop)
            row.addWidget(D.label("by the app" if auto else ("by hand" + (f": {g['by']}" if g.get("by") and done else "")),
                                  "muted", wrap=False), 0, Qt.AlignTop)
            lay.addLayout(row)

    def set_goal(self, gid, on):
        self.rec.set_goal(self.rec.data["stage"], gid, on)
        diag.activity("qt_goal_set")
        self.changed()

    def goal_dialog(self, gid=None, text=None, action=None, due=None, owner=None):
        """Add a goal, or (2.86.0) change one: its wording, remove it, or tick it by hand instead of the app's check;
        (2.93.0) its deadline and owner. action (tests): 'remove' or 'manual'. A deadline outside the stage's dates is
        refused: self.goal_problem says why."""
        r = self.rec
        if r is None:
            return None
        self.goal_problem = ""
        g = next((x for x in r.stage()["goals"] if x["id"] == gid), None) if gid else None
        if text is None and action is None and due is None and owner is None:
            got = self._goal_box(g)
            if got is None:
                return None
            text, action, due, owner = got
            if g is not None and text is None and action is None and due == g.get("due", "") and owner == g.get("owner", ""):
                return None
        if due is not None or owner is not None:
            if g is None:
                nid = r.add_goal(r.data["stage"], text)
                if not nid:
                    return None
                g, gid, text = next(x for x in r.stage()["goals"] if x["id"] == nid), nid, None
            why = r.set_goal_deadline(r.data["stage"], gid, due if due is not None else g.get("due", ""), owner)
            if why:
                self.goal_problem = why
                self.host.status(why)
            diag.activity("qt_goal_deadline")
            if text is None and action is None:
                self.changed()
                return gid
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

    def _goal_box(self, g, run=True):
        """(new wording or None, 'remove' | 'manual' | None, deadline, owner) from a small dialog about one goal (g None:
        a new one), or None when cancelled. A deadline outside the stage's dates keeps the dialog open with the reason."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
        from .people import combo_name, name_combo
        from .stagesedit import DeadlineRow, window_hint
        r = self.rec
        d = QDialog(self); d.setWindowTitle("Gate goal" if g else "New gate goal"); d.setMinimumWidth(560)
        v = QVBoxLayout(d)
        v.addWidget(D.label("What has to be true before the effort leaves this stage:", "muted"))
        ed = QLineEdit(g["text"] if g else ""); v.addWidget(ed)
        if g and g.get("auto"):
            v.addWidget(D.label("The app checks this one. Tick it by hand instead if the check does not fit this effort.", "muted"))
        form = QFormLayout(); v.addLayout(form)
        owner = name_combo(self.host, g.get("owner", "") if g else ""); form.addRow("Owner", owner)
        dl = DeadlineRow(g.get("due", "") if g else ""); form.addRow("Deadline", dl)
        v.addWidget(D.label(window_hint(r, r.data["stage"]), "muted"))
        err = D.label("", "muted"); err.setStyleSheet(f"color:{D.tokens()['crit']};"); err.hide(); v.addWidget(err)
        out = {"action": None}
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if g:
            rm = bb.addButton("Remove it", QDialogButtonBox.DestructiveRole)
            rm.clicked.connect(lambda: (out.update(action="remove"), d.accept()))
        if g and g.get("auto"):
            mb = bb.addButton("Tick it by hand", QDialogButtonBox.ActionRole)
            mb.clicked.connect(lambda: (out.update(action="manual"), d.accept()))

        def check():
            due = dl.value()
            why = "The time was not understood (write it like 2:00 PM)." if due is None else r.due_problem(r.data["stage"], due)
            if not g and not " ".join(ed.text().split()):
                why = "Write what has to be true first."
            err.setText(why); err.setVisible(bool(why))
            if not why:
                d.accept()
            return why
        bb.accepted.connect(check); bb.rejected.connect(d.reject)
        v.addWidget(bb)
        d.api = {"text": ed, "owner": owner, "deadline": dl, "error": err, "check": check, "out": out}
        if not run:
            return d
        if d.exec() != QDialog.Accepted:
            return None
        t = " ".join(ed.text().split())
        if not g:
            return t, None, dl.value() or "", combo_name(owner)
        return (t if t and t != g["text"] else None), out["action"], dl.value() or "", combo_name(owner)

    def save_defaults(self, answer=None):
        """2.86.0: this stage's goals become the default for the same stage in new efforts (this PC; team defaults later)."""
        r = self.rec
        if r is None:
            return None
        import teampack as TP
        if TP.locked(self.host.config_dir, "goals"):               # 2.89.0: the team pack set them
            self.host.status("The team pack set the default gate goals. They change when the team sends a new pack.")
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
            b = ClickLabel(t["title"], lambda tid=t["id"]: self.task_dialog(tid))     # 3.0.4: a long title wraps
            b.setToolTip("Open the task"); b.setMinimumWidth(120); row.addWidget(b, 1)
            row.addWidget(D.label(" | ".join(x for x in (t["owner"], ("due " + R.when_text(t["due"])) if t["due"] else "") if x),
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
        from .stagesedit import DeadlineRow, window_hint          # 2.93.0: a time too, kept inside the stage's dates
        dl = DeadlineRow(t["due"] if t and t.get("due") else (due or ""), "Due")
        status = QComboBox(); status.addItems(R.TASK_STATUS); status.setCurrentText(t["status"] if t else R.TASK_STATUS[0])
        stage = QComboBox()
        for s in r.stages:
            stage.addItem(s["name"], s["id"])
        stage.setCurrentIndex(stage.findData(t["stage"] if t else r.data["stage"]))
        hint = D.label("", "muted")
        stage.currentIndexChanged.connect(lambda _i: hint.setText(window_hint(r, stage.currentData())))
        hint.setText(window_hint(r, stage.currentData()))
        notes = QPlainTextEdit(t.get("notes", "") if t else ""); notes.setFixedHeight(80)
        form.addRow("Task", title); form.addRow("Owner", owner); form.addRow("Stage", stage); form.addRow("Deadline", dl)
        form.addRow("", hint); form.addRow("Status", status); form.addRow("Notes", notes)
        err = D.label("", "muted"); err.setStyleSheet(f"color:{D.tokens()['crit']};"); err.hide(); form.addRow(err)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if t:
            rm = bb.addButton("Remove", QDialogButtonBox.DestructiveRole)
            rm.clicked.connect(lambda: (self.remove_task(tid), dlg.reject()))

        def problem():
            v = dl.value()
            if v is None:
                return "The time was not understood (write it like 2:00 PM)."
            return r.due_problem(stage.currentData(), v)

        def check():
            why = problem()
            err.setText(why); err.setVisible(bool(why))
            if not why:
                dlg.accept()
            return why
        bb.accepted.connect(check); bb.rejected.connect(dlg.reject)
        form.addRow(bb)

        def values():
            return {"title": title.text(), "owner": combo_name(owner), "due": dl.value() or "",
                    "status": status.currentText(), "stage": stage.currentData(), "notes": notes.toPlainText()}
        dlg.api = {"title": title, "owner": owner, "has_due": dl.has, "when": dl.date, "time": dl.time, "deadline": dl,
                   "status": status, "stage": stage, "notes": notes, "values": values, "check": check, "problem": problem,
                   "error": err}
        if not run:
            return dlg
        if dlg.exec() == QDialog.Accepted:
            return self.save_task(tid, values())
        return None

    def save_task(self, tid, values):
        """Adds or changes a task. A deadline outside its stage's dates is refused (None; self.task_problem says why)."""
        r = self.rec
        self.task_problem = r.due_problem(values.get("stage") or r.data["stage"], values.get("due", ""))
        if self.task_problem:
            self.host.status(self.task_problem)
            return None
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
        import graphics as GX
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
            elif not GX.for_note(r, n["id"]):                          # 3.0.4: a note that needs a graphic
                row.addWidget(D.button("Graphic", "ghost", lambda _=False, nid=n["id"]: self.graphic_from_note(nid),
                                       "List this note under Graphic needs"), 0, Qt.AlignTop)
            row.addWidget(D.button("Remove", "ghost", lambda _=False, nid=n["id"]: self.remove_note(nid)), 0, Qt.AlignTop)
            lay.addLayout(row)
        if len(qs) + len(others) > 14:
            lay.addWidget(D.label(f"and {len(qs) + len(others) - 14} more", "muted"))
        if not qs and not others:
            lay.addWidget(D.label("No notes yet." if not who else f"No open questions for {who}.", "muted"))

    # ------------------------------------------------------------ 3.0.4 graphic needs
    def draw_graphics(self, r):
        import graphics as GX
        lay = self.sections["graphics"]; clear(lay)
        who = self.person()
        gs = [g for g in GX.items(r) if not who or g.get("owner") == who]
        self.gfx_now = [g["id"] for g in gs]
        n_open = sum(1 for g in gs if g.get("status") != "Done")
        self.gfx_card.title.setText(f"Graphic needs   {n_open} open" + (f" for {who}" if who else ""))
        if not gs:
            lay.addWidget(D.label("None yet. In Review, select a sentence (or drag across the words) and press Graphic need "
                                  "(P); or press Graphic on a note." if not who else f"No graphic needs for {who}.", "muted"))
            return
        for g in gs[:14]:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            tone = {"Needed": "warn", "In work": "accent", "Done": "ok"}.get(g.get("status"), "head")
            p = D.Pill(g.get("status", "").upper(), tone); p.setFixedWidth(96); row.addWidget(p, 0, Qt.AlignTop)
            col = QVBoxLayout(); col.setSpacing(0)
            t = ClickLabel(g["concept"], lambda gid=g["id"]: self.graphic_dialog(gid)); t.setToolTip("Change it, or mark it in work or done")
            t.setMinimumWidth(120); col.addWidget(t)
            col.addWidget(D.label(" | ".join(x for x in (g.get("kind", ""), g.get("section", ""), g.get("owner", ""), GX.where_text(g)) if x), "muted"))
            row.addLayout(col, 1)
            if g.get("sid"):
                row.addWidget(D.button("Open", "ghost", lambda _=False, sid=g["sid"]: self.open_sentence(sid),
                                       "Open the sentence in Review"), 0, Qt.AlignTop)
            lay.addLayout(row)
        if len(gs) > 14:
            lay.addWidget(D.label(f"and {len(gs) - 14} more (Export... lists them all)", "muted"))

    def open_sentence(self, sid):
        h = self.host
        if h.review is None or h.review.item(sid) is None:
            h.status("That sentence is no longer in the matrix.")
            return False
        h.go("assign")
        h.assign_page.select(sid)
        return True

    def graphic_dialog(self, gid=None, answer=None):
        """+ Graphic need... (gid None) or change one. answer (tests): {"concept", "kind", "section", "owner", "status"} or
        {"remove": True}. Returns the id (or True when removed)."""
        import graphics as GX
        r = self.rec
        if r is None:
            return None
        g = GX.get(r, gid) if gid else None
        if answer is None:
            d = QDialog(self); d.setWindowTitle("Graphic need" if g else "New graphic need"); d.setMinimumWidth(520)
            f = QFormLayout(d)
            if g and g.get("quote"):
                f.addRow(D.label("From: " + g["quote"][:300], "muted"))
            concept = QLineEdit(g["concept"] if g else ""); f.addRow("Graphic needed", concept)
            kind = QComboBox(); kind.setEditable(True); kind.addItems(list(GX.KINDS)); kind.setCurrentText(g.get("kind", "") if g else "")
            f.addRow("Kind", kind)
            sec = QComboBox(); sec.setEditable(True); sec.addItems([""] + (self.host.review.labels() if self.host.review is not None else []))
            sec.setCurrentText(g.get("section", "") if g else ""); f.addRow("Section", sec)
            from .people import name_combo, combo_name
            own = name_combo(self.host, g.get("owner", "") if g else ""); f.addRow("Owner", own)
            st = QComboBox(); st.addItems(list(GX.STATUS)); st.setCurrentText(g.get("status", "Needed") if g else "Needed"); f.addRow("Status", st)
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            gone = []
            if g:
                rm = bb.addButton("Remove", QDialogButtonBox.DestructiveRole)
                rm.clicked.connect(lambda: (gone.append(True), d.accept()))
            f.addRow(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = {"remove": True} if gone else {"concept": concept.text(), "kind": kind.currentText(), "section": sec.currentText(),
                                                     "owner": combo_name(own), "status": st.currentText()}
        if answer.get("remove") and g:
            ok = GX.remove(r, g["id"])
            diag.activity("graphic_removed")
            self.changed()
            return ok
        if g:
            GX.update(r, g["id"], **{k: v for k, v in answer.items() if k in ("concept", "kind", "section", "owner", "status")})
            out = g["id"]
        else:
            out = GX.add(r, answer.get("concept", ""), kind=answer.get("kind", ""), section=answer.get("section", ""),
                         owner=answer.get("owner", ""))
            if out and answer.get("status") in ("In work", "Done"):
                GX.update(r, out, status=answer["status"])
        if out:
            diag.activity("graphic_saved")
            self.changed()
        return out

    def graphic_from_note(self, nid):
        import graphics as GX
        r = self.rec
        n = next((x for x in r.notes() if x["id"] == nid), None) if r is not None else None
        if n is None:
            return ""
        gid = GX.add(r, n["text"], note_id=nid, source={"text": n["text"]})
        if gid:
            diag.activity("graphic_from_note")
            self.host.toast("Listed under Graphic needs")
            self.changed()
        return gid

    def export_graphics(self, path=None):
        import graphics as GX
        r = self.rec
        if r is None:
            return None
        if path is None:
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(self, "Export the graphic needs", self.host.out_path("graphic_needs"), "Excel (*.xlsx)")
            if not path:
                return None
        GX.export_excel(path, r, self.host.effort_name)
        diag.activity("graphics_exported", n=len(GX.items(r)))
        self.host.toast("Graphic needs exported")
        return path

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
        people = r.contacts()                                            # 2.96.0: points of contact, captured in Review
        self.info.title.setText(f"Customer information   {len(people)} contact(s), {len(info)} other")
        t = D.tokens()
        for c in people:
            box = QFrame(); box.setObjectName("contact")
            box.setStyleSheet(f"QFrame#contact{{border:1px solid {t['border']};border-radius:{D.RADIUS['card']}px;}}")
            bv = QVBoxLayout(box); bv.setContentsMargins(D.SPACE["s"], D.SPACE["xs"], D.SPACE["s"], D.SPACE["xs"]); bv.setSpacing(0)
            top = QHBoxLayout()
            nm = D.label(" · ".join(x for x in (c.get("name"), c.get("title")) if x) or c.get("email") or "Contact", None)
            nm.setStyleSheet("font-weight:700;"); top.addWidget(nm, 1)
            top.addWidget(D.button("Remove", "ghost", lambda _=False, cid=c["id"]: self.remove_contact(cid)))
            bv.addLayout(top)
            for k in ("org", "email", "phone", "address"):
                if c.get(k):
                    bv.addWidget(D.label(c[k]))
            for o in c.get("other", []):
                bv.addWidget(D.label(f"{o['label']}: {o['value']}"))
            if c.get("sources"):
                s0 = c["sources"][-1]
                bv.addWidget(D.label("From " + ", ".join(x for x in (s0.get("doc"), s0.get("loc")) if x), "muted"))
            lay.addWidget(box)
        if not info and not people:
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

    def remove_contact(self, cid):
        ok = self.rec.remove_contact(cid)
        diag.activity("qt_contact_removed")
        self.changed()
        return ok

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
                                   last=first.replace(day=CAL.monthrange(y, m)[1]) + datetime.timedelta(days=14), mine=self.my_zone_key())

    def export_tq(self, path=None):
        """2.92.0: the tasks and questions for the person shown, or the full team, in a dated workbook named for them."""
        import effortfolders as EF
        import tqexport as TQ
        import branding as BR
        h = self.host
        if h.ws is None:
            return ""
        who = self.person() or ""
        if path is None:
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(self, "Export tasks and questions", h.out_path("tasks_questions", Person=__import__("re").sub(r"[^A-Za-z0-9]+", "_", who).strip("_") if who else "Full_Team"),
                                                  "Excel (*.xlsx)")
        if not path:
            return ""
        r = R.Record(h.ws.root)
        _p, nt, nq = TQ.export(r, path, h.effort_name, who, sensitivity=BR.identity(r)["sensitivity"] if BR.marking(BR.identity(r)["sensitivity"]) else "")
        diag.activity("qt_tq_exported", n=nt + nq)
        h.toast(f"Tasks and questions for {who or 'the full team'}: {nt} task(s), {nq} question(s)")
        return path

    def my_zone_key(self):
        import tzones as TZ
        from .modes import settings
        return TZ.my_zone(settings())

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
        items = self.state.calendar(first=d, last=d, mine=self.my_zone_key()).get(d, [])
        self.day_box.addWidget(D.label(d.strftime("%A, %B %d, %Y").replace(" 0", " "), "title"))
        t = D.tokens()
        for kind, text in items or [("event", "Nothing on this day.")]:
            self.day_box.addWidget(D.label(f"<span style='color:{t[CAL_TONE.get(kind, 'muted')]}'>■</span> {text}"))
        import html as _h
        import effortcal as EC
        for e in [e for e in self.rec.data.get("events", []) if e["date"] == d.isoformat()]:      # 2.88.0: the details
            bits = [x for x in (e.get("kind", ""), EC.entry_times(e, self.my_zone_key()),
                                f"Owner: {e['owner']}" if e.get("owner") else "", f"Stage: {e['stage']}" if e.get("stage") else "",
                                e.get("details", "")) if x]
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            row.addWidget(D.label(f"<b>{_h.escape(e['title'])}</b>  " + _h.escape("  ·  ".join(bits)), "muted"), 1)
            from .calview import entry_dialog
            row.addWidget(D.button("Edit", "ghost", lambda _=False, x=dict(e): entry_dialog(self, entry=x)), 0, Qt.AlignTop)
            row.addWidget(D.button("Remove", "ghost", lambda _=False, i=e["id"]: self.remove_event(i)), 0, Qt.AlignTop)
            self.day_box.addLayout(row)
        add = QHBoxLayout()
        add.addWidget(D.button("+ Task due this day", None, lambda: self.task_dialog(due=d.isoformat())))
        from .calview import entry_dialog
        add.addWidget(D.button("+ Due date this day", None, lambda: entry_dialog(self, "Due", day=d)))
        add.addWidget(D.button("+ Event this day", None, lambda: entry_dialog(self, "Meeting", day=d)))
        add.addStretch(1)
        self.day_box.addLayout(add)
        return items

    def remove_event(self, eid):
        import effortcal as EC
        ok = EC.remove_event(R.Record(self.host.ws.root), eid)
        self.refresh()
        return ok

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
