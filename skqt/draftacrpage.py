"""Drafts > Acronyms (4.4.0; claude/stationkeeper-drafts-plan-4.4.md, step 3; decision 7). Each volume's newest draft
checked against the effort's acronym list (acrfix.check): used before it is spelled out, spelled out again, not in the
list, and the volume's Acronyms table. Fix in a copy opens the 3.92.0 check on the selected volume (fixes go into a copy as
tracked changes; the draft is never changed). A term not in the list goes back to Shred > Acros & Abs, marked From our
drafts: <volume>, and is shown here until it is decided there. Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QListWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

import diag
import draftvols as DV
from . import design as D
from .commandbar import CommandBar

COLS = ["Volume", "Draft", "Used before it is spelled out", "Spelled out again", "Not in the list", "Acronyms table"]


class DraftAcrPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        bar = self.bar = CommandBar()
        self.b_check = bar.primary("Check the drafts", lambda: self.check(), "Each volume's newest draft against the "
                                   "effort's acronym list. A term not in the list goes to Acros & Abs to decide.")
        self.b_fix = bar.add("Fix in a copy...", lambda: self.fix(), "The selected volume's findings, one at a time; "
                             "fixes go into a copy as tracked changes")
        bar.more("Decide them in Acros & Abs", lambda: self.host.go("acronyms"), "Shred > Acros & Abs, where the terms "
                 "from our drafts wait to be decided")
        v.addWidget(bar)
        self.card = D.Card("Each volume against the list", "The newest Word file in each volume's folder (Status > "
                           "Volume folders...). Nothing in a draft is changed.")
        t = self.table = QTableWidget(0, len(COLS)); t.setHorizontalHeaderLabels(COLS)
        t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); t.setMinimumHeight(160)
        t.doubleClicked.connect(lambda _i: self.fix())
        self.card.add(t)
        self.said = self.card.add(D.label("Not checked yet.", "muted"))
        v.addWidget(self.card)
        self.p_card = D.Card("From our drafts, still to decide", "Terms our drafts use that are not in the list. Decide each "
                             "on Shred > Acros & Abs: in the list with its meaning, or Not a term.")
        self.pending_list = QListWidget(); self.pending_list.setMinimumHeight(120)
        self.p_card.add(self.pending_list)
        v.addWidget(self.p_card, 1)

    # ------------------------------------------------------------ state
    def M(self):
        R = getattr(self.host, "review", None)
        return R.M if R is not None else None

    def session(self):
        ap = getattr(self.host, "acronym_page", None)
        if ap is None:
            return None
        if ap.session is None and self.host.ws is not None:
            try:
                ap.load()
            except Exception:  # noqa: BLE001
                diag.swallowed()
        return ap.session

    def refresh(self):
        self.setEnabled(self.host.ws is not None)
        if self.host.ws is None:
            return
        if not self.rows:
            self.rows = [dict(d, report=None, said="") for d in DV.drafts(self.host.ws, self.M())]
        self.fill()

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)

    # ------------------------------------------------------------ the check
    def check(self):
        M, s = self.M(), self.session()
        if self.host.ws is None or M is None or not M.outline:
            self.said.setText("Build the response structure first (Matrix & Outline > Outline): the drafts are by volume.")
            return None
        from .acrlayout import list_entries
        import acrpage as P
        self.rows = DV.check_acronyms(self.host.ws, M, list_entries(s) if s is not None else [])
        added = 0
        for r in self.rows:
            rep = r["report"]
            if rep is None:
                continue
            if s is not None:
                added += DV.send_unlisted(s, r["volume"], rep)
                use = dict(s.ws.get("acronym_volume_use", {}) or {})        # each term's uses in this volume (Where it goes)
                for t, n in rep["use"].items():
                    use.setdefault(t, {})[r["volume"]] = n
                s.ws.set("acronym_volume_use", use)
                P.note(s.ws, f"{r['volume']} checked", to_fix=sum(1 for f in rep["findings"] if f["kind"] != "unlisted"))
        got = sum(1 for r in self.rows if r["report"] is not None)
        self.said.setText(f"{got} of {len(self.rows)} volume(s) checked."
                          + (f" {added} term(s) not in the list went to Acros & Abs, marked {DV.FROM}." if added else ""))
        try:
            ap = self.host.acronym_page
            ap.fill()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.fill()
        diag.activity("draft_acronyms_checked", n=got, added=added)
        return self.rows

    def fill(self):
        t = self.table
        keep = t.currentRow()
        t.setRowCount(0)
        for r in self.rows:
            i = t.rowCount(); t.insertRow(i)
            n = DV.acr_counts(r["report"]) if r["report"] is not None else None
            if n is None:
                vals = (r["volume"], os.path.basename(r["file"]) if r["file"] else (r.get("said") or DV._why_not(r)), "", "", "", "")
            else:
                vals = (r["volume"], os.path.basename(r["file"]), str(n["before"]), str(n["again"]), str(n["unlisted"]),
                        "none found" if n["table"] is None else ("matches" if n["table"] == 0 else f"{n['table']} to fix"))
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if 2 <= c <= 4:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                t.setItem(i, c, it)
        if self.rows:
            t.selectRow(min(max(keep, 0), len(self.rows) - 1))
        pend = DV.pending(self.session())
        self.pending_list.clear()
        for term in sorted(pend, key=str.lower):
            self.pending_list.addItem(f"{term}   {DV.FROM}: {', '.join(pend[term])}")
        self.p_card.setVisible(bool(pend))
        return len(pend)

    def current(self):
        i = self.table.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def fix(self, path=None):
        """The 3.92.0 check on the selected volume: Fix in the copy, Leave it, the Acronyms table."""
        r = self.current()
        path = path or (r or {}).get("file")
        ap = getattr(self.host, "acronym_page", None)
        if not path or ap is None:
            self.host.status("Pick a volume with a draft: Check the drafts first.")
            return None
        self.session()
        from .acrdrafts import open_drafts
        return open_drafts(ap, path)
