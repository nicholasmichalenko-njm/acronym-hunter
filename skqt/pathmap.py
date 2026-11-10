"""The Effort Dashboard as the map (3.96.0; canvas "Navigation", board 2): the five steps as cards (where each stands, a
bar for how far along, what is left), Your next step, large, with one button, and This week's dates with each meeting's
notes. Each card opens its step. navsteps holds the rules; nothing leaves the PC."""
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

import diag
import navsteps as NS
from . import design as D
from .navrail import ClickFrame

WORD = {"done": "DONE", "now": "NOW", "next": "NEXT", "later": "LATER"}


class StepCard(ClickFrame):
    def __init__(self, host, key):
        super().__init__("stepCard")
        self.host, self.key = host, key
        self.setMinimumHeight(118)
        v = QVBoxLayout(self); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(6)
        self.cap = QLabel(""); self.cap.setObjectName("cardCap")
        self.name = QLabel(NS.NAME[key]); self.name.setObjectName("cardName")
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setTextVisible(False); self.bar.setFixedHeight(6)
        self.text = QLabel(""); self.text.setObjectName("cardText"); self.text.setWordWrap(True)
        for x in (self.cap, self.name, self.bar, self.text):
            x.setAttribute(Qt.WA_TransparentForMouseEvents); v.addWidget(x)
        v.addStretch(1)
        self.clicked.connect(lambda: host.rail_go(key))

    def set(self, s):
        t = D.tokens()
        col = {"done": t["ok"], "now": t["accent"]}.get(s["state"], t["faint"])
        soft = {"done": t["ok_soft"], "now": t["accent_soft"]}.get(s["state"], t["border"])
        self.cap.setText(f"{s['n']}  {WORD[s['state']]}")
        self.bar.setValue(int(round(100 * s["progress"])))
        self.text.setText(s["summary"])
        bd = f"2px solid {t['accent']}" if s["state"] == "now" else f"1px solid {t['border']}"
        self.setStyleSheet(f"QFrame#stepCard{{background:{t['surface']};border:{bd};border-radius:10px;}}"
                           f"QLabel#cardCap{{color:{col};font-size:11px;font-weight:700;letter-spacing:1px;background:transparent;}}"
                           f"QLabel#cardName{{font-size:16px;font-weight:600;color:{t['text']};background:transparent;}}"
                           f"QLabel#cardText{{color:{t['muted']};background:transparent;}}"
                           f"QProgressBar{{background:{soft};border:none;border-radius:3px;}}"
                           f"QProgressBar::chunk{{background:{col};border-radius:3px;}}")


class PathMap(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page = page
        host = page.host
        self.host = host
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["m"])
        row = QGridLayout(); row.setSpacing(D.SPACE["m"]); v.addLayout(row)
        self.cards = {}
        for i, (k, _n, _w) in enumerate(NS.STEPS):
            c = StepCard(host, k); row.addWidget(c, 0, i); row.setColumnStretch(i, 1); self.cards[k] = c
        low = QHBoxLayout(); low.setSpacing(D.SPACE["m"]); v.addLayout(low)
        t = D.tokens()
        self.next_box = QFrame(); self.next_box.setObjectName("nextBox")
        self.next_box.setStyleSheet(f"QFrame#nextBox{{background:{t['surface']};border:1px solid {t['border_strong']};border-radius:10px;}}"
                                    f"QFrame#nextBox QLabel{{background:transparent;}}")
        nv = QVBoxLayout(self.next_box); nv.setContentsMargins(20, 16, 20, 16); nv.setSpacing(8)
        cap = QLabel("YOUR NEXT STEP"); cap.setStyleSheet(f"color:{t['accent']};font-size:11px;font-weight:700;letter-spacing:1px;")
        nv.addWidget(cap)
        self.next_title = QLabel(""); self.next_title.setStyleSheet("font-size:20px;font-weight:600;"); self.next_title.setWordWrap(True)
        nv.addWidget(self.next_title)
        self.next_why = D.label("", "muted"); nv.addWidget(self.next_why)
        br = QHBoxLayout(); br.setSpacing(D.SPACE["s"])
        self.next_btn = D.button("", "primary", lambda: self.go_next()); br.addWidget(self.next_btn)
        self.next_then = D.label("", "faint"); br.addWidget(self.next_then, 1)
        nv.addLayout(br); nv.addStretch(1)
        low.addWidget(self.next_box, 3)
        self.week = D.Card("This week", "")
        self.week_box = QVBoxLayout(); self.week_box.setSpacing(4); self.week.body.addLayout(self.week_box)
        low.addWidget(self.week, 2)
        self.next_now = None

    def refresh(self):
        h = self.host
        from . import navrail
        sts = navrail.refresh_steps(h)
        f = getattr(h, "path_facts", None)
        self.setVisible(bool(sts) and f is not None)
        if not sts or f is None:
            return None
        for s in sts:
            self.cards[s["key"]].set(s)
        n = self.next_now = NS.next_step(sts, f)
        self.next_title.setText(n["title"]); self.next_why.setText(n["why"])
        self.next_btn.setText(n["button"] + "  →"); self.next_then.setText(n["then"])
        self.fill_week()
        return n

    def go_next(self):
        return self.host.rail_go(self.next_now["go"]) if self.next_now else None

    def fill_week(self, today=None):
        while self.week_box.count():
            it = self.week_box.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
            elif it.layout() is not None:
                while it.layout().count():
                    x = it.layout().takeAt(0)
                    if x.widget() is not None:
                        x.widget().setParent(None)
        today = today or datetime.date.today()
        rows = []
        try:
            st = self.page.state
            cal = st.calendar(first=today, last=today + datetime.timedelta(days=6), mine=self.page.my_zone_key(), who="",
                              stages=self.page._stages_on()) if st is not None else {}
            for d in sorted(cal):
                for _k, text in cal[d]:
                    rows.append((d, text, None))
            rec = self.page.rec
            for e in (rec.data.get("events", []) if rec is not None else []):
                try:
                    d = datetime.date.fromisoformat(e["date"])
                except (KeyError, ValueError):
                    continue
                if today <= d <= today + datetime.timedelta(days=6):
                    rows = [r for r in rows if not (r[0] == d and e["title"] in r[1])]
                    rows.append((d, e["title"], e["id"]))
        except Exception:  # noqa: BLE001
            diag.swallowed()
        rows.sort(key=lambda r: r[0])
        if not rows:
            self.week_box.addWidget(D.label("Nothing on the calendar this week.", "muted"))
        from . import meetnotes as MN
        for d, text, eid in rows[:8]:
            r = QHBoxLayout(); r.setSpacing(D.SPACE["s"])
            day = "Today" if d == today else d.strftime("%a") if (d - today).days < 7 else d.strftime("%b %d")
            lab = D.label(day, "faint", wrap=False); lab.setFixedWidth(56); r.addWidget(lab, 0, Qt.AlignTop)
            r.addWidget(D.label(text, None), 1)
            if eid:
                r.addWidget(D.button(MN.mark(self.page.rec, eid) or "Notes", "ghost",
                                     lambda _=False, i=eid: MN.open_notes(self.page, self.page.rec, i)), 0, Qt.AlignTop)
            self.week_box.addLayout(r)
        self.week_box.addWidget(D.label("Deliverables, the Effort Record and Meetings are tabs of this page.", "muted"))
        return rows
