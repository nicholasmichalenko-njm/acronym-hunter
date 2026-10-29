"""The effort dashboard (2.62.0): the effort on one screen. Days to the due date and to each stage, gate goals met,
requirements assigned and placed, coverage by volume, open questions, acronym and banned-word counts, and everything
past due, with who has what. Counts from the effort's own files by rules (No AI); click a number to go where it is
worked. Nothing leaves the PC."""
import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QHeaderView, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import effortrec as R
import effortstate as ES
from . import design as D
from .homepage import clear, plural


def _table(cols, widths=(), stretch=0):
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setSelectionMode(QTableWidget.NoSelection)
    t.setAlternatingRowColors(True)
    t.setFocusPolicy(Qt.NoFocus)
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    for i, w in enumerate(widths):
        if i != stretch:
            t.setColumnWidth(i, w)
    return t


def _fit(t, most=12):
    """Show every row (up to most) without an inner scroll bar."""
    h = t.horizontalHeader().height() + 4 + sum(t.rowHeight(i) for i in range(min(t.rowCount(), most)))
    t.setFixedHeight(max(h, t.horizontalHeader().height() + 34))


def _cell(t, r, c, text, tone=None):
    it = QTableWidgetItem(str(text))
    it.setToolTip(str(text))
    if tone:
        it.setForeground(D.color(tone))
    if c:
        it.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    t.setItem(r, c, it)
    return it


class DashPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.data = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        inner = QWidget(); inner.setObjectName("page"); scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.empty = D.EmptyState("No effort open", "Pick an effort in the top bar; its dashboard shows here.")
        v.addWidget(self.empty)
        go = self.host.go
        self.tiles = {
            "due": D.Tile("-", "days to the due date", "accent", lambda: go("home"), "Effort home: the stage track and the calendar"),
            "goals": D.Tile("-", "gate goals met", "accent", lambda: go("home"), "Effort home: the gate goals of this stage"),
            "placed": D.Tile("-", "requirements placed in a section", "accent", lambda: go("assign"), "Assign"),
            "owned": D.Tile("-", "requirements with an owner", "accent", lambda: go("assign"), "Assign: People..."),
            "questions": D.Tile("-", "open questions", "accent", lambda: go("home"), "Effort home: notes and open questions"),
            "late": D.Tile("-", "tasks late", "accent", lambda: go("home"), "Effort home: tasks"),
            "review": D.Tile("-", "customer changes to review", "accent", lambda: go("compare"),
                             "Customer Documents: versions and requirements to review"),
            "library": D.Tile("-", "library roles to confirm", "accent", lambda: go("library"),
                              "Library: documents whose role is only suggested (2.83.0)")}
        self.tile_row = QWidget()
        tg = QGridLayout(self.tile_row); tg.setContentsMargins(0, 0, 0, 0); tg.setSpacing(D.SPACE["m"])
        for i, t in enumerate(self.tiles.values()):
            tg.addWidget(t, 0, i); tg.setColumnStretch(i, 1)
        v.addWidget(self.tile_row)
        self.body = QWidget()
        grid = QGridLayout(self.body); grid.setContentsMargins(0, 0, 0, 0); grid.setSpacing(D.SPACE["m"])
        grid.setColumnStretch(0, 3); grid.setColumnStretch(1, 2)
        # compliance review
        self.comp = D.Card("Compliance review", actions=[D.button("Assign", None, lambda: go("assign")),
                                                          D.button("Prove", None, lambda: go("prove"))])
        self.comp_bar = D.StackBar(16); self.comp.add(self.comp_bar)
        self.comp_legend = QVBoxLayout(); self.comp.body.addLayout(self.comp_legend)
        self.comp_text = self.comp.add(D.label("", "muted"))
        # coverage by volume
        self.vol = D.Card("Coverage by volume", "Compliance requirements and context placed in each volume's sections.",
                          actions=[D.button("Response Setup", None, lambda: go("setup"))])
        self.vol_table = _table(["Volume", "Sections", "Requirements", "With an owner", "", "Context"], (0, 80, 100, 110, 140, 80))
        self.vol.add(self.vol_table)
        # stages
        self.stages = D.Card("Stages", "Planned dates against today.")
        self.stage_table = _table(["Stage", "Planned", "Where it stands", "Gate goals"], (150, 140, 0, 80), stretch=2)
        self.stages.add(self.stage_table)
        # past due
        self.late = D.Card("Past due")
        self.late_box = QVBoxLayout(); self.late_box.setSpacing(D.SPACE["xs"]); self.late.body.addLayout(self.late_box)
        # acronyms and QA/QC
        self.acr = D.Card("Acronyms and QA/QC", "The effort's acronym list, and the last check of the drafts.")
        self.acr_bar = D.StackBar(12); self.acr.add(self.acr_bar)
        self.acr_legend = QVBoxLayout(); self.acr.body.addLayout(self.acr_legend)
        self.qa_row = QHBoxLayout(); self.qa_row.setSpacing(D.SPACE["m"]); self.acr.body.addLayout(self.qa_row)
        self.qa_text = self.acr.add(D.label("", "muted"))
        # who has what
        self.people = D.Card("Who has what", "Sections led or shared, compliance requirements owned, tasks and questions.")
        self.people_table = _table(["Person", "Sections", "Requirements", "Open tasks", "Late", "Open questions"], (0, 80, 100, 90, 60, 110))
        self.people.add(self.people_table)
        grid.addWidget(self.comp, 0, 0); grid.addWidget(self.stages, 0, 1, 2, 1, Qt.AlignTop)
        grid.addWidget(self.vol, 1, 0, Qt.AlignTop)
        grid.addWidget(self.acr, 2, 0, Qt.AlignTop); grid.addWidget(self.late, 2, 1, Qt.AlignTop)
        grid.addWidget(self.people, 3, 0, 1, 2)
        v.addWidget(self.body)
        v.addStretch(1)

    def refresh(self, today=None):
        h = self.host
        on = h.ws is not None
        self.empty.setVisible(not on); self.tile_row.setVisible(on); self.body.setVisible(on)
        if not on:
            self.data = None
            return None
        st = ES.State(h.ws, h.effort_path, h.review.M if h.review is not None else None)
        d = self.data = st.dashboard(today or datetime.date.today())
        self.fill_tiles(d)
        self.fill_compliance(d)
        self.fill_volumes(d)
        self.fill_stages(d)
        self.fill_late(d)
        self.fill_acronyms(d)
        self.fill_people(d)
        diag.activity("qt_dashboard_shown")
        return d

    # ------------------------------------------------------------ the numbers on top
    def fill_tiles(self, d):
        T = self.tiles
        n = d["days_to_due"]
        if n is None:
            T["due"].set("-", "days to the due date (none set yet)", "head")
        else:
            T["due"].set(n if n >= 0 else f"{-n}", ("days to the due date " + f"({d['due']})" if n >= 0 else "days past the due date"),
                         "crit" if n <= 3 else "warn" if n <= 10 else "accent")
        T["goals"].set(f"{d['goals_met']} of {d['goals']}", f"gate goals met in {d['stage']}",
                       "ok" if d["goals"] and d["goals_met"] == d["goals"] else "accent")
        q = d["reqs"]
        if q:
            T["placed"].set(f"{q['placed']} of {q['reqs']}", "requirements placed in a section", "ok" if q["placed"] == q["reqs"] else "warn")
            T["owned"].set(f"{q['owned']} of {q['reqs']}", "requirements with an owner", "ok" if q["owned"] == q["reqs"] else "warn")
        else:
            T["placed"].set("-", "requirements placed (no matrix yet)", "head")
            T["owned"].set("-", "requirements with an owner (no matrix yet)", "head")
        T["questions"].set(d["questions"], "open questions" + (f" ({d['questions_unassigned']} not assigned)" if d["questions_unassigned"] else ""),
                           "warn" if d["questions"] else "ok")
        T["late"].set(d["tasks_late"], f"tasks late of {d['tasks_open']} open", "crit" if d["tasks_late"] else "ok")
        try:                                       # 2.85.0: changes still to decide in Compare, and owners to confirm
            import changereview as CHR
            crv = CHR.Review(self.host.ws.root).load()
            und = sum(n for _a, _b, n in crv.undecided())
            wait = len(crv.awaiting())
        except Exception:
            diag.swallowed()
            und = wait = 0
        if und or wait:
            T["review"].set(und + d["to_review"], "customer changes to decide" + (f" ({wait} awaiting the owner)" if wait else ""), "warn")
        else:
            T["review"].set(d["to_review"], "customer changes to review", "warn" if d["to_review"] else "ok")
        try:                                       # 2.83.0: the library
            import docversions as DV
            lib = DV.Library(self.host.ws.p("documents")).load()
            und = len(lib.undecided())
            T["library"].set(und, f"library roles to confirm of {len(lib.all)} documents" if lib.all else "documents in the library (none yet)",
                             "warn" if und else "ok" if lib.all else "head")
        except Exception:
            diag.swallowed()

    def fill_compliance(self, d):
        clear(self.comp_legend)
        q = d["reqs"]
        if not q:
            self.comp_bar.set([])
            self.comp_text.setText("No compliance matrix yet. Read RFP brings the customer's documents in.")
            return
        segs = [(q["placed"], "req", "Requirements placed"), (q["reqs"] - q["placed"], "warn", "Requirements not placed"),
                (q["context"], "ctx", "Supporting context"), (q["customer"], "cust", "The customer's"),
                (q["dropped"], "border_strong", "Ignored"), (q["undecided"], "faint", "Not decided yet")]
        self.comp_bar.set(segs)
        self.comp_legend.addWidget(D.legend([s for s in segs if s[0]]))
        rv = d.get("review")
        self.comp_text.setText(f"{q['decided']} of {q['sentences']} sentences decided ({q['pct']}%). "
                               + (f"{plural(q['undecided'], 'sentence')} still to decide in Assign." if q["undecided"] else "Every sentence is decided.")
                               + (f"\n{rv[0]} review: {rv[1]['Compliant']} compliant, {rv[1]['Partly']} partly, {rv[1]['Not compliant']} not "
                                  f"compliant, {rv[1]['Not addressed']} not addressed, {rv[1]['not_reviewed']} not reviewed." if rv else ""))

    def fill_volumes(self, d):
        t = self.vol_table
        rows = d["volumes"]
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            loose = r["volume"] == "Not in a section"
            _cell(t, i, 0, r["volume"], "warn" if loose else None)
            _cell(t, i, 1, r["sections"] if not loose else "")
            _cell(t, i, 2, r["reqs"])
            _cell(t, i, 3, f"{r['owned']} of {r['reqs']}" if r["reqs"] else "-", "warn" if r["owned"] < r["reqs"] else None)
            bar = D.StackBar(8); bar.set([(r["owned"], "ok", "With an owner"), (r["reqs"] - r["owned"], "warn", "No owner")])
            t.setCellWidget(i, 4, bar)
            _cell(t, i, 5, r["context"])
        if not rows:
            t.setRowCount(1); _cell(t, 0, 0, "Set the response structure (Structure) to see coverage by volume.", "muted")
        _fit(t)

    def fill_stages(self, d):
        t = self.stage_table
        rows = d["stages"]
        t.setRowCount(len(rows))
        for i, s in enumerate(rows):
            plan = " to ".join(x for x in (R.short_date(s["start"].isoformat()) if s["start"] else "",
                                           R.short_date(s["end"].isoformat()) if s["end"] else "") if x) or "not planned"
            if s["state"] == "done":
                where, tone = "Done" + (f" {R.short_date(s['ended'].isoformat())}" if s["ended"] else ""), "ok"
            elif s["state"] == "current":
                where, tone = ("Now: " + (f"{plural(s['over'], 'day')} past plan" if s["over"] else
                                          f"{plural(s['left'], 'day')} left" if s["left"] is not None else "under way")), \
                    "warn" if s["over"] else "accent"
            elif s["late_start"]:
                where, tone = f"{plural(-s['days_to_start'], 'day')} late to start", "crit"
            elif s["days_to_start"] is not None:
                where, tone = f"Starts in {plural(s['days_to_start'], 'day')}", None
            else:
                where, tone = "Ahead", "muted"
            _cell(t, i, 0, s["name"], "accent" if s["state"] == "current" else None)
            _cell(t, i, 1, plan, "muted" if plan == "not planned" else None)
            _cell(t, i, 2, where, tone)
            _cell(t, i, 3, f"{s['goals_met']} of {s['goals']}" if s["goals"] else "-", "ok" if s["goals"] and s["goals_met"] == s["goals"] else None)
        if d["days_to_due"] is not None:
            n = t.rowCount(); t.setRowCount(n + 1)
            _cell(t, n, 0, "Submission"); _cell(t, n, 1, R.short_date(d["due_date"].isoformat())).setToolTip(d["due"])
            _cell(t, n, 2, (f"In {plural(d['days_to_due'], 'day')}" if d["days_to_due"] >= 0 else f"{plural(-d['days_to_due'], 'day')} ago"),
                  "crit" if d["days_to_due"] <= 3 else None)
            _cell(t, n, 3, "")
        _fit(t, 14)

    def fill_late(self, d):
        clear(self.late_box)
        items = d["past_due"]
        self.late.title.setText(f"Past due   {len(items)}")
        if not items:
            self.late_box.addWidget(D.label("Nothing is past due.", "muted"))
        for kind, text, when in items[:14]:
            row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
            p = D.Pill({"task": "TASK", "stage": "STAGE", "questions": "QUESTIONS"}.get(kind, kind.upper()), "crit" if kind == "task" else "warn")
            p.setFixedWidth(100); row.addWidget(p, 0, Qt.AlignTop)
            row.addWidget(D.label(text), 1)
            if when:
                row.addWidget(D.label(R.short_date(when.isoformat()), "muted", wrap=False), 0, Qt.AlignTop)
            self.late_box.addLayout(row)
        if len(items) > 14:
            self.late_box.addWidget(D.label(f"and {len(items) - 14} more", "muted"))

    def fill_acronyms(self, d):
        clear(self.acr_legend); clear(self.qa_row)
        a = d["acronyms"]
        segs = [(a["Approved"], "ok", "Approved"), (a["Proposed"], "accent", "Proposed"), (a["Needs author"], "warn", "Needs author"),
                (a["Rejected"], "border_strong", "Rejected")]
        self.acr_bar.set(segs)
        self.acr_legend.addWidget(D.legend(segs) if a["total"] else D.label("No acronyms in the effort's list yet.", "muted"))
        q = d["qa"]
        if q is None:
            self.qa_text.setText("QA/QC has not checked the drafts yet: QA/QC, Check Word files.")
            return
        for val, cap, bad in ((q["banned"], "banned words", q["banned"]), (q["avoid"], "words to avoid", q["avoid"]),
                              (q["first_use"], "first-use fixes", q["first_use"]), (q["pages_over"], "volumes over the page limit", q["pages_over"])):
            if cap.startswith(("banned", "words")) and not q["banned_checked"]:
                continue
            self.qa_row.addWidget(D.Tile(val, cap, "crit" if bad and cap.startswith(("banned", "volumes")) else "warn" if bad else "ok"))
        self.qa_text.setText(f"Last QA/QC check: {plural(q['volumes'], 'volume')}"
                             + ("" if q["banned_checked"] else "; banned words were not checked") + ".")

    def fill_people(self, d):
        t = self.people_table
        rows = d["people"]
        t.setRowCount(len(rows))
        for i, p in enumerate(rows):
            _cell(t, i, 0, p["person"]); _cell(t, i, 1, p["sections"]); _cell(t, i, 2, p["reqs"]); _cell(t, i, 3, p["tasks"])
            _cell(t, i, 4, p["late"], "crit" if p["late"] else None); _cell(t, i, 5, p["questions"], "warn" if p["questions"] else None)
        if not rows:
            t.setRowCount(1); _cell(t, 0, 0, "Nobody named yet: name section leads in Assign (People...) or give tasks an owner.", "muted")
        _fit(t, 16)
