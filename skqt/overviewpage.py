"""Overview: the effort's page on one screen (4.27.0; Nicholas's recording 2026-11-12; answer 20). It is what the
Dashboard entry opens. Left: your next step with the path under it, up to four counts that each open the page that
fixes them, the deliverables one row each, and the Wall of Truth as a line that stays up. Right: the calendar's next ten
dated things (always there), the customer, and the last three things that happened. Every block reads what the effort
already keeps (overview.py); the cards the Dashboard had are one tab over, in All cards, until Tasks and Activity have
pages of their own. Rules only (No AI); nothing leaves the PC."""
import datetime
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import diag
import overview as OV
from . import design as D

TONE = {"done": "ok", "now": "accent", "next": "muted", "later": "faint"}


def _clear(lay):
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.setParent(None); w.deleteLater()
        elif it.layout() is not None:
            _clear(it.layout())


class OverviewPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        self.data = None
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        # the head: the effort, its customer, how long is left, its stage
        head = QHBoxLayout(); head.setSpacing(D.SPACE["m"])
        self.name = D.label("", "title", wrap=False); head.addWidget(self.name)
        self.sub = D.label("", "muted", wrap=False); head.addWidget(self.sub, 1)
        self.due = QPushButton(""); self.due.setObjectName("link"); self.due.setCursor(Qt.PointingHandCursor); self.due.setFlat(True)
        self.due.setToolTip("Click to set the due date")
        self.due.clicked.connect(lambda: self.set_due())
        head.addWidget(self.due)
        self.stage = D.Pill("", "head"); head.addWidget(self.stage)
        v.addLayout(head)
        self.empty = D.EmptyState("No effort open", "Open an effort to see where it stands.", "All Efforts", lambda: host.go("efforts"))
        v.addWidget(self.empty, 1)
        self.body = QWidget(); v.addWidget(self.body, 1)
        bv = QVBoxLayout(self.body); bv.setContentsMargins(0, 0, 0, 0); bv.setSpacing(D.SPACE["m"])
        cols = QHBoxLayout(); cols.setSpacing(D.SPACE["m"]); bv.addLayout(cols, 1)
        left = QVBoxLayout(); left.setSpacing(D.SPACE["m"]); cols.addLayout(left, 3)
        right = QVBoxLayout(); right.setSpacing(D.SPACE["m"]); cols.addLayout(right, 2)
        # ---- left
        self.next_card = D.Card("Your next step", key=True)
        self.next_title = self.next_card.add(D.label("", "title"))
        self.next_why = self.next_card.add(D.label("", "muted"))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        self.next_btn = D.button("", "primary", lambda: self.open_next())
        row.addWidget(self.next_btn); row.addStretch(1)
        self.next_card.body.addLayout(row)
        self.path_row = QHBoxLayout(); self.path_row.setSpacing(D.SPACE["xs"])
        self.next_card.body.addLayout(self.path_row)
        left.addWidget(self.next_card)
        self.num_row = QHBoxLayout(); self.num_row.setSpacing(D.SPACE["m"]); self.num_row.setContentsMargins(0, 0, 0, 0)
        nw = QWidget(); nw.setLayout(self.num_row); left.addWidget(nw)
        self.deliv = D.Card("Deliverables", actions=[D.button("Open the board", None, lambda: host.go("deliverables"), "Every deliverable, its owner and status")])
        self.deliv_box = QVBoxLayout(); self.deliv_box.setSpacing(2); self.deliv.body.addLayout(self.deliv_box)
        left.addWidget(self.deliv, 1)
        self.truth = QFrame(); self.truth.setObjectName("pinStrip")
        th = QHBoxLayout(self.truth); th.setContentsMargins(D.SPACE["m"], 6, D.SPACE["s"], 6); th.setSpacing(D.SPACE["s"])
        self.truth_title = D.label("Wall of Truth", "label", wrap=False); th.addWidget(self.truth_title, 0, Qt.AlignTop)
        self.truth_body = QLabel(""); self.truth_body.setWordWrap(True); self.truth_body.setTextFormat(Qt.RichText)
        self.truth_body.setTextInteractionFlags(Qt.TextSelectableByMouse); self.truth_body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        th.addWidget(self.truth_body, 1)
        th.addWidget(D.button("Open the wall", "ghost", lambda: host.go("truth"), "The approved facts, numbers, names and terms"), 0, Qt.AlignTop)
        self.truth.setMaximumHeight(72)
        left.addWidget(self.truth)
        # ---- right
        self.cal = D.Card("Calendar", "The next dated things: due dates, questions due, stages, gate goals, tasks.",
                          actions=[D.button("Open the calendar", None, lambda: self.open_calendar(), "The month, day by day")])
        self.cal_box = QVBoxLayout(); self.cal_box.setSpacing(2); self.cal.body.addLayout(self.cal_box)
        right.addWidget(self.cal, 1)
        self.cust = D.Card("Customer")
        self.cust_fold = D.button("Show", "ghost", lambda: self.fold_customer())
        self.cust_box = QVBoxLayout(); self.cust_box.setSpacing(2); self.cust_box.setContentsMargins(0, 0, 0, 0)
        self.cust_w = QWidget(); self.cust_w.setLayout(self.cust_box)
        self.cust_line = self.cust.add(D.label("", "muted"))
        self.cust.body.addWidget(self.cust_w); self.cust.body.addWidget(self.cust_fold, 0, Qt.AlignLeft)
        self.cust_open = False
        right.addWidget(self.cust)
        self.act = D.Card("Latest activity", actions=[D.button("All activity", None, lambda: host.go("activity"), "Everything that happened, by day")])
        self.act_box = QVBoxLayout(); self.act_box.setSpacing(2); self.act.body.addLayout(self.act_box)
        bv.addWidget(self.act)

    # ------------------------------------------------------------------ the data
    def gather(self, today=None):
        """Everything the page shows, or None with no effort open. Each part on its own: one that cannot be read is empty."""
        h = self.host
        if h.ws is None:
            return None
        today = today or datetime.date.today()
        import effortrec as RR
        import effortstate as ES
        from . import navrail as NR
        M = h.review.M if getattr(h, "review", None) is not None else None
        sts = NR.refresh_steps(h, force=True)
        f = getattr(h, "path_facts", None) or {}
        import navsteps as NS
        out = {"today": today, "steps": sts, "facts": f, "next": NS.next_step(sts, f) if sts else None, "path": OV.path(sts)}
        rec = RR.Record(h.ws.root)
        st = ES.State(h.ws, h.effort_path, M)
        d = {}
        try:
            d = st.dashboard(today)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        out["due"], out["days"] = d.get("due", ""), d.get("days_to_due")
        out["stage"] = d.get("stage", "")
        gl = 0
        try:
            import graphiclog as GL
            gp = getattr(h, "graphics_page", None)
            n, words, sweep, _needs = GL.counts(gp.all_rows()) if gp is not None else (0, 0, 0, 0)
            gl = sweep
        except Exception:  # noqa: BLE001
            diag.swallowed()
        out["numbers"] = OV.numbers(f, late_tasks=d.get("tasks_late", 0), graphics_left=gl, questions=d.get("questions", 0))
        try:
            import deliverables as DL
            ds = DL.items(rec)
            out["deliverables"] = OV.deliverables(ds, [DL.state(x, rec=rec) for x in ds])
        except Exception:  # noqa: BLE001
            diag.swallowed()
            out["deliverables"] = []
        try:
            import walloftruth as WT
            out["truth"] = [(x.get("label", ""), str(x.get("value", ""))) for x in WT.items(rec)]
        except Exception:  # noqa: BLE001
            diag.swallowed()
            out["truth"] = []
        try:
            out["dates"] = OV.dates(st.calendar(first=today, last=today + datetime.timedelta(days=180)), today)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            out["dates"] = []
        client = sol = ""
        try:
            import effort as E
            L = E.EffortList(h.effort_path).load() if h.effort_path else None
            client, sol = (getattr(L, "client", "") or ""), (getattr(L, "solicitation", "") or "")
        except Exception:  # noqa: BLE001
            diag.swallowed()
        out["client"], out["solicitation"] = client, sol
        out["customer"] = OV.customer(client, sol, rec.contacts(), rec.customer_info())
        out["activity"] = OV.activity(rec.events(limit=3))
        return out

    # ------------------------------------------------------------------ the page
    def refresh(self, today=None):
        h = self.host
        d = self.data = self.gather(today)
        on = d is not None
        self.empty.setVisible(not on); self.body.setVisible(on)
        for w in (self.sub, self.due, self.stage):
            w.setVisible(on)
        if not on:
            self.name.setText("Overview")
            return None
        t = D.tokens()
        self.name.setText(h.effort_name)
        self.sub.setText("  ·  ".join(x for x in (d["client"], d["solicitation"]) if x) or "Customer and solicitation not set yet")
        self.due.setText(OV.due_words(d["days"]) + (f"  ({d['due']})" if d["due"] else ""))
        late = d["days"] is not None and d["days"] <= 7
        self.due.setStyleSheet(f"QPushButton#link{{border:0;background:transparent;font-weight:600;color:{t['warn'] if late else t['text']};}}"
                               f"QPushButton#link:hover{{text-decoration:underline;}}")
        self.stage.setText(d["stage"] or "No stage"); self.stage.setVisible(bool(d["stage"]))
        # the next step, and the path
        nx = d["next"]
        self.next_title.setText(nx["title"] if nx else "Add the customer's documents")
        self.next_why.setText((nx.get("why", "") + ("  " + nx["then"].capitalize() + "." if nx.get("then") else "")) if nx else "")
        self.next_btn.setText(nx["button"] if nx else "Open Documents")
        _clear(self.path_row)
        self.path_btns = {}
        for key, n, name, badge, state in d["path"]:
            b = QPushButton(f"{n}  {name}".replace("&", "&&") + (f"   {badge}" if badge else "")); b.setCursor(Qt.PointingHandCursor)
            col = t[TONE.get(state, "muted")]
            b.setStyleSheet(f"QPushButton{{border:1px solid {t['accent'] if state == 'now' else t['border']};border-radius:6px;padding:4px 8px;"
                            f"background:{t['accent_soft'] if state == 'now' else 'transparent'};color:{col};"
                            f"font-weight:{600 if state == 'now' else 400};text-align:left;}}")
            b.setToolTip({"done": "Done", "now": "This is the step to work on", "next": "Next", "later": "Later"}.get(state, ""))
            b.clicked.connect(lambda _c=False, k=key: h.rail_go(k))
            self.path_row.addWidget(b, 1); self.path_btns[key] = b
        # the counts
        _clear(self.num_row)
        self.num_btns = []
        for n, words, go in d["numbers"]:
            b = QPushButton(f"{n}\n{words}"); b.setCursor(Qt.PointingHandCursor); b.setMinimumHeight(64)
            b.setStyleSheet(f"QPushButton{{border:1px solid {t['border']};border-radius:8px;padding:6px 12px;background:{t['surface']};"
                            f"color:{t['text']};font-size:13px;text-align:left;}}QPushButton:hover{{border-color:{t['accent']};}}")
            b.setToolTip("Open where this is fixed")
            b.clicked.connect(lambda _c=False, k=go: h.go(k))
            self.num_row.addWidget(b, 1); self.num_btns.append(b)
        if not d["numbers"]:
            self.num_row.addWidget(D.label("Nothing is waiting on a count right now.", "muted"), 1)
        # deliverables
        _clear(self.deliv_box)
        rows = d["deliverables"]
        self.deliv.title.setText(f"Deliverables   {len(rows)}")
        for did, name, owner, status, changed in rows[:OV.MOST_DELIVERABLES]:
            line = (f"<b>{html.escape(name)}</b> &nbsp;<span style='color:{t['muted']}'>{html.escape(owner)} · {html.escape(status)}</span>"
                    + (f" &nbsp;<span style='color:{t['warn']}'>{html.escape(changed)}</span>" if changed else ""))
            lab = QLabel(line); lab.setTextFormat(Qt.RichText); lab.setWordWrap(True)
            self.deliv_box.addWidget(lab)
        if len(rows) > OV.MOST_DELIVERABLES:
            self.deliv_box.addWidget(D.label(f"and {len(rows) - OV.MOST_DELIVERABLES} more on the board", "muted"))
        if not rows:
            self.deliv_box.addWidget(D.label("None yet. The board lists what the customer asks for and what you add.", "muted"))
        self.deliv_box.addStretch(1)
        # the wall
        tr = d["truth"]
        self.truth_title.setText(f"Wall of Truth   {len(tr)}")
        self.truth_body.setText(" &nbsp;·&nbsp; ".join(f"<b>{html.escape(a)}</b>: {html.escape(b)}" for a, b in tr[:12])
                                or f"<span style='color:{t['muted']}'>No facts on the wall yet.</span>")
        # the calendar
        _clear(self.cal_box)
        for _d, wh, kind, text in d["dates"]:
            lab = QLabel(f"<b>{html.escape(wh)}</b> &nbsp;<span style='color:{t['muted']}'>{html.escape(kind)}</span> &nbsp;{html.escape(text)}")
            lab.setTextFormat(Qt.RichText); lab.setWordWrap(True)
            self.cal_box.addWidget(lab)
        if not d["dates"]:
            self.cal_box.addWidget(D.label("Nothing dated ahead. Set the due date (click it above) and it shows here.", "muted"))
        self.cal_box.addStretch(1)
        # the customer
        _clear(self.cust_box)
        lines = d["customer"]
        self.cust_line.setText(d["client"] or "Not set yet")
        for a, b in lines:
            lab = QLabel(f"<span style='color:{t['muted']}'>{html.escape(a)}</span> &nbsp;{html.escape(b)}")
            lab.setTextFormat(Qt.RichText); lab.setWordWrap(True)
            self.cust_box.addWidget(lab)
        self.cust_w.setVisible(self.cust_open and bool(lines))
        self.cust_line.setVisible(not (self.cust_open and bool(lines)))
        self.cust_fold.setVisible(bool(lines)); self.cust_fold.setText("Hide" if self.cust_open else "Show")
        # activity
        _clear(self.act_box)
        for at, who, what in d["activity"]:
            lab = QLabel(f"<span style='color:{t['muted']}'>{html.escape(at)} &nbsp;{html.escape(who)}</span> &nbsp;{html.escape(what)}")
            lab.setTextFormat(Qt.RichText); lab.setWordWrap(True)
            self.act_box.addWidget(lab)
        if not d["activity"]:
            self.act_box.addWidget(D.label("Nothing has happened yet.", "muted"))
        diag.activity("qt_overview_shown")
        return d

    # ------------------------------------------------------------------ what it does
    def open_next(self):
        d = self.data or {}
        nx = d.get("next")
        return self.host.go(nx["go"] if nx else "library")

    def fold_customer(self):
        self.cust_open = not self.cust_open
        self.cust_w.setVisible(self.cust_open)
        self.cust_line.setVisible(not self.cust_open)
        self.cust_fold.setText("Hide" if self.cust_open else "Show")
        return self.cust_open

    def set_due(self, answer=None):
        """Set the due date here (the banner's dialog)."""
        try:
            got = self.host.home_page.banner.due_dialog(answer) if answer is not None else self.host.home_page.banner.due_dialog()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            got = None
        self.refresh()
        return got

    def open_calendar(self):
        """The month, day by day: the Calendar entry (4.27.1)."""
        return self.host.go("calendar")
