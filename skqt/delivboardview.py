"""The deliverables board in Qt (2.87.0): one card per deliverable, the ones needing attention first, and everything
about the one you pick beside them: its requirements, what changed, its checks, its context and its files. The rules
are delivboard's. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
from . import design as D
from .adaptive import FlowLayout

TONE = {"crit": "crit", "warn": "warn", "ok": "ok", "info": "accent"}
HEALTH = {"crit": "Needs action", "warn": "Needs attention", "ok": "On track"}


class Card(QFrame):
    def __init__(self, c, on_pick, current=False):
        super().__init__()
        self.c, self.on_pick = c, on_pick
        self.setObjectName("dcard")
        self.setFixedWidth(300)
        self.setCursor(Qt.PointingHandCursor)
        t = D.tokens()
        edge = t[TONE[c["health"]]]
        self.setStyleSheet(f"QFrame#dcard{{background:{t['surface']};border:1px solid {t['accent'] if current else t['border']};"
                           f"border-left:4px solid {edge};border-radius:{D.RADIUS['card']}px;}} QFrame#dcard QLabel{{background:transparent;}}")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["s"]); v.setSpacing(4)
        top = QHBoxLayout(); v.addLayout(top)
        title = D.label(c["name"], "title"); title.setWordWrap(True); top.addWidget(title, 1)
        top.addWidget(D.Pill(HEALTH[c["health"]], TONE[c["health"]]), 0, Qt.AlignTop)
        v.addWidget(D.label(f"{c['kind'] or 'Deliverable'}  ·  {c['owner'] or 'no owner'}  ·  {c['status']}", "muted"))
        if c["limit"] or c["pages"] is not None:
            bar = QProgressBar(); bar.setMaximumHeight(8); bar.setTextVisible(False)
            import subreq as SR
            n = SR._limit_n(c["limit"]) or 0
            bar.setRange(0, max(n, c["pages"] or 0, 1)); bar.setValue(c["pages"] or 0)
            col = t["crit"] if c["over"] else t["ok"]
            bar.setStyleSheet(f"QProgressBar{{background:{t['surface2']};border:none;border-radius:3px}} QProgressBar::chunk{{background:{col};border-radius:3px}}")
            v.addWidget(bar)
            v.addWidget(D.label((f"{c['pages']} pages" if c["pages"] is not None else "pages not counted yet") + (f" of {c['limit']}" if c["limit"] else ""),
                                "crit" if c["over"] else "muted"))
        if c["volume"]:
            v.addWidget(D.label(f"{c['volume']}: {c['reqs']} requirements, {c['owned']} with an author"
                                + (f", {c['context']} context" if c["context"] else ""), None))
        shown = c["missing"][:3]
        for k, text in shown:
            lab = D.label(("● " if k != "info" else "") + text, None)
            lab.setStyleSheet(f"color:{t[TONE[k]]};")
            v.addWidget(lab)
        if len(c["missing"]) > 3:
            v.addWidget(D.label(f"and {len(c['missing']) - 3} more", "muted"))
        if not c["missing"]:
            v.addWidget(D.label("Nothing missing.", "muted"))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda cid=self.c["id"], f=self.on_pick: f(cid))   # the board refills; not while this card handles the click
            e.accept()
            return
        super().mouseReleaseEvent(e)


class Board(QWidget):
    """The cards, wrapping to the window's width."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.flow = FlowLayout(self, D.SPACE["m"])
        self.cards = {}

    def fill(self, cards, current=None):
        while self.flow.count():
            it = self.flow.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        self.cards = {}
        for c in cards:
            w = Card(c, self.page.pick, current == c["id"])
            self.cards[c["id"]] = w
            self.flow.addWidget(w)
        self.updateGeometry()


class Detail(QScrollArea):
    """Everything about one deliverable."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setWidgetResizable(True); self.setMinimumWidth(420)
        w = QWidget(); self.setWidget(w)
        self.v = QVBoxLayout(w); self.v.setAlignment(Qt.AlignTop); self.v.setSpacing(D.SPACE["s"])
        self.show_card(None)

    def _clear(self):
        while self.v.count():
            it = self.v.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
            elif it.layout() is not None:
                while it.layout().count():
                    x = it.layout().takeAt(0)
                    if x.widget() is not None:
                        x.widget().setParent(None)

    def show_card(self, c):
        self._clear()
        self.c = c
        if c is None:
            self.v.addWidget(D.EmptyState("Pick a deliverable", "Click a card to see its requirements, what changed, its checks, "
                                          "its context and its files."))
            return
        pg = self.page
        top = QHBoxLayout(); self.v.addLayout(top)
        top.addWidget(D.label(c["name"], "title"), 1)
        top.addWidget(D.Pill(HEALTH[c["health"]], TONE[c["health"]]))
        self.v.addWidget(D.label(f"{c['kind'] or 'Deliverable'}  ·  owner {c['owner'] or 'nobody yet'}  ·  {c['status']}"
                                 + ("  ·  done for this stage" if c["done_here"] else ""), "muted"))
        row = FlowLayout(None, D.SPACE["s"]); self.v.addLayout(row)
        row.addWidget(D.button("Edit...", "primary", lambda: pg.edit(c["id"])))
        row.addWidget(D.button("Done for this stage", None, lambda: pg.mark_stage(c["id"])))
        if c["file"]:
            row.addWidget(D.button("Check this volume", None, lambda: pg.check_volume(c["id"]), "Submission check on its file"))
        # missing
        self.v.addWidget(D.SectionTitle("What is missing" if c["missing"] else "Nothing missing"))
        t = D.tokens()
        for k, text in c["missing"]:
            lab = D.label(("● " if k != "info" else "") + text); lab.setStyleSheet(f"color:{t[TONE[k]]};"); self.v.addWidget(lab)
        # the volume
        self.v.addWidget(D.SectionTitle("Volume in the response structure"))
        heads = pg.volume_heads()
        if heads:
            cb = QComboBox(); cb.addItem("(not linked)", "")
            for h in heads:
                cb.addItem(h, h)
            cb.setCurrentIndex(max(0, cb.findData(c["volume"])))
            cb.activated.connect(lambda _i, cb=cb: pg.link_volume(c["id"], cb.currentData()))
            self.vol_combo = cb
            self.v.addWidget(cb)
        else:
            self.v.addWidget(D.label("The response structure has no volumes yet (Structure, or Volumes... in Assign).", "muted"))
        # requirements
        rr = c.get("req_rows") or []
        if c["volume"]:
            self.v.addWidget(D.SectionTitle(f"Requirements in {c['volume']} ({len(rr)})"))
            tb = QTableWidget(len(rr), 4); tb.setHorizontalHeaderLabels(["ID", "Section", "Author", "State"])
            tb.verticalHeader().setVisible(False); tb.setEditTriggers(QTableWidget.NoEditTriggers); tb.setMinimumHeight(min(320, 40 + 26 * max(1, len(rr))))
            for i, x in enumerate(rr):
                state = "awaiting the owner" if x["awaiting"] else (x["new"] or "")
                for col, val in enumerate((x["id"], x["section"], x["owner"] or "no author", state)):
                    it = QTableWidgetItem(val); it.setToolTip(x["text"])
                    if col == 2 and not x["owner"] or col == 3 and x["awaiting"]:
                        it.setForeground(D.color("warn"))
                    tb.setItem(i, col, it)
            tb.cellDoubleClicked.connect(lambda r, _c, rr=rr: pg.open_requirement(rr[r]["id"]))
            self.req_table = tb
            self.v.addWidget(tb)
            self.v.addWidget(D.label("Double-click one to open it in Assign.", "muted"))
        # changes
        if c["changed"] or c["awaiting"] or c["changed_reqs"]:
            self.v.addWidget(D.SectionTitle("What changed"))
            for x in c["changed"]:
                self.v.addWidget(D.label(x[0].upper() + x[1:]))
            if c["changed_reqs"]:
                self.v.addWidget(D.label(f"{len(c['changed_reqs'])} requirement(s) changed by a customer version: " + ", ".join(c["changed_reqs"][:8])))
            self.v.addWidget(D.button("Open Changes", None, lambda: pg.host.go("compare")), 0, Qt.AlignLeft)
        # checks
        self.v.addWidget(D.SectionTitle("Submission check"))
        if c["checked"]:
            self.v.addWidget(D.label(f"First-use problems: {c['first_use']}   Banned words: {c['banned']}   "
                                     f"Acronym list entries to finish: {c['list_open']}"))
        else:
            self.v.addWidget(D.label("Not in the latest Submission check." if c["file"] else "Link its Word file (Edit...) to check it.", "muted"))
        # context
        if c["context"]:
            self.v.addWidget(D.SectionTitle("Context from the library"))
            self.v.addWidget(D.label(f"{c['context']} sentence(s) from library documents are attached to its sections; they print in "
                                     "Response Setup under each section."))
        # files
        self.v.addWidget(D.SectionTitle("Files"))
        self.v.addWidget(D.label(f"Our file: {c['file'] or 'none linked yet'}"))
        if c["form"]:
            f = c["form"]
            self.v.addWidget(D.label(f"Customer form: {f['doc']} (working on {f['working'] or 'not chosen'}; newest {f['latest']})",
                                     "crit" if f["newer"] else None))
