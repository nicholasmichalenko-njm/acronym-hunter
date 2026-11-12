"""Change review (2.85.0): what each change touches (tag_rows) and Requirement history. 3.89.0: the page itself is
comparepage (Compare on the page) and the decisions are in its decide bar (comparebar); the strip, side by side and the
decide panel retired with the table. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)
import diag
import changereview as CR
from . import design as D

COLORS = {"changed": "warn", "added": "ok", "removed": "crit"}
TAG_NAMES = {"req": "REQ", "rule": "RULE", "deliv": "DELIV", "term": "TERM", "new": "NEW"}


def _words(s):
    import re
    return set(re.findall(r"[A-Za-z0-9&]+", s or ""))


def tag_rows(rows, links, impact):
    """What each change touches: req (a compliance requirement), new (an added sentence not in the matrix), rule (a
    submission rule), deliv (a deliverable), term (a term new in this version). [tuple of tags] aligned with rows."""
    rules = (impact or {}).get("requirements", [])
    dels = (impact or {}).get("deliverables", [])
    terms = {t["term"] if isinstance(t, dict) else t for t in ((impact or {}).get("acronyms") or {}).get("new", [])}
    out = []
    for i, r in enumerate(rows):
        if r["kind"] == "same":
            out.append(())
            continue
        tg = []
        txt = (r.get("new") or "") + " " + (r.get("old") or "")
        if i < len(links) and links[i]:
            tg.append("req")
        elif r["kind"] == "added":
            tg.append("new")
        rule_hit = r.get("submission") or any(q.get("sentence") and q["sentence"] in txt for q in rules)
        if rule_hit:
            tg.append("rule")
            if dels and any(("page" in txt.lower() and "limit" in " ".join(d_["why"]).lower()) or d_["name"].lower() in txt.lower()
                            for d_ in dels):
                tg.append("deliv")
        elif any(d_["name"].lower() in txt.lower() for d_ in dels):
            tg.append("deliv")
        if terms and (_words(r.get("new")) & terms):
            tg.append("term")
        out.append(tuple(tg))
    return out


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ====================================================================== requirement history
class HistoryDialog(QDialog):
    """Every requirement a version changed, removed or added, with its history; confirm that the answer still fits."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.setWindowTitle("Requirement history"); self.resize(1100, 560)
        self.rv = CR.Review(page.host.ws.root).load()
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each requirement a customer version touched: what it said, what it says now, which version did it, "
                            "and whether its owner has confirmed the answer still fits.", "muted"))
        bar = QHBoxLayout(); v.addLayout(bar)
        self.only = QComboBox(); self.only.addItems(["Every requirement with a history", "Awaiting the owner"])
        self.only.currentIndexChanged.connect(lambda _i: self.fill()); bar.addWidget(self.only); bar.addStretch(1)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Requirement", "What happened", "By", "Was", "Now", "Owner confirmed", "When"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(True)
        for c, wdt in ((0, 90), (1, 110), (2, 150), (5, 150), (6, 110)):
            self.table.setColumnWidth(c, wdt)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch); self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        v.addWidget(self.table, 1)
        row = QHBoxLayout(); v.addLayout(row)
        self.count = D.label("", "muted", wrap=False); row.addWidget(self.count); row.addStretch(1)
        row.addWidget(D.button("Confirm it still fits", "primary", lambda: self.confirm(), "The owner checked the answer against the new wording"))
        row.addWidget(D.button("Open in Shred", None, lambda: self.open()))
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); row.addWidget(bb)
        self.fill()

    def fill(self):
        wait = set(self.rv.awaiting())
        rows = []
        for rid, es in self.rv.lineage.items():
            if self.only.currentIndex() == 1 and rid not in wait:
                continue
            for e in es:
                rows.append((rid, e))
        self.rows = rows
        self.table.setRowCount(len(rows))
        names = {"updated": "Wording changed", "removed": "Removed", "added": "Added"}
        for k, (rid, e) in enumerate(rows):
            vals = (rid, names.get(e["kind"], e["kind"]), f"{e.get('doc', '')} {e.get('label', '')}", e.get("old", ""), e.get("new", ""),
                    e.get("confirmed", "") or ("awaiting the owner" if e["kind"] in ("updated", "removed") else ""), e.get("when", "")[:10])
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 5 and not e.get("confirmed") and e["kind"] in ("updated", "removed"):
                    it.setForeground(D.color("warn"))
                self.table.setItem(k, c, it)
        self.table.resizeRowsToContents()
        self.count.setText(f"{len(wait)} awaiting the owner")
        return len(rows)

    def current(self):
        k = self.table.currentRow()
        return self.rows[k][0] if 0 <= k < len(self.rows) else None

    def confirm(self, rid=None):
        rid = rid or self.current()
        if rid and self.rv.confirm(rid):
            M = self.page.host.review.M if self.page.host.review is not None else None
            it = self.page.host.review.item(rid) if M is not None else None
            if it is not None and (it.get("new") or "").endswith("owner to confirm"):
                it["new"] = it["new"].replace("owner to confirm", "owner confirmed")
                M.pending = True
                self.page.host.changed()
            diag.activity("change_confirmed")
            self.fill()
            return True
        return False

    def open(self):
        rid = self.current()
        if rid:
            self.accept()
            self.page.open_item(rid)


def history_dialog(page, run=True):
    if page.host.ws is None:
        return None
    dlg = HistoryDialog(page)
    if run:
        dlg.exec()
    return dlg
