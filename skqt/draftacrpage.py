"""Drafts > Acronyms (4.4.0; claude/stationkeeper-drafts-plan-4.4.md, step 3; decision 7). Each volume's newest draft
checked against the effort's acronym list (acrfix.check): used before it is spelled out, spelled out again, not in the
list, and the volume's Acronyms table. Fix in a copy opens the 3.92.0 check on the selected volume (fixes go into a copy as
tracked changes; the draft is never changed). A term not in the list is decided right here (4.23.2: its meaning typed
on its row, Add to effort list or Not a term on the row); it is the same decision as on Shred > Acros & Abs, where it
also shows, marked From our drafts: <volume>. Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

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
                                   "effort's acronym list. A term not in the list is decided below.")
        self.b_fix = bar.add("Fix in a copy...", lambda: self.fix(), "The selected volume's findings, one at a time; "
                             "fixes go into a copy as tracked changes")
        # 4.23.2 (Nicholas 2026-11-12 13:51: "Why would I decide them in two places? Why would I have to move to the
        # other one?"): the jump to Acros & Abs is gone; the terms are decided on their rows below
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
        self.p_card = D.Card("From our drafts, still to decide", "Terms our drafts use that are not in the list. Type what "
                             "each means (it may stay empty), then Add to effort list, or Not a term.")
        p = self.pending_list = QTableWidget(0, 4); p.setHorizontalHeaderLabels(["Term", "In", "Means", ""])
        p.verticalHeader().setVisible(False); p.setSelectionMode(QAbstractItemView.NoSelection); p.setMinimumHeight(140)
        p.setEditTriggers(QAbstractItemView.NoEditTriggers)
        p.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        p.setColumnWidth(0, 160); p.setColumnWidth(1, 220); p.setColumnWidth(3, 280)
        self.pending_terms = []
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
                          + (f" {added} term(s) not in the list are below to decide." if added else ""))
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
        s = self.session()
        pend = DV.pending(s)
        p = self.pending_list
        self.pending_terms = sorted(pend, key=str.lower)
        p.setRowCount(len(self.pending_terms))
        for i, term in enumerate(self.pending_terms):
            p.setItem(i, 0, QTableWidgetItem(term)); p.setItem(i, 1, QTableWidgetItem(", ".join(pend[term])))
            means = QLineEdit(); means.setPlaceholderText("What it means (may stay empty)")
            got = ((s.results.get(term) or {}).get("selected_definition") or "") if s is not None else ""
            means.setText("" if got == "Keep All Possibilities" else got)
            means.returnPressed.connect(lambda t=term: self.decide(t, True))
            p.setCellWidget(i, 2, means)
            box = QWidget(); h = QHBoxLayout(box); h.setContentsMargins(4, 0, 4, 0); h.setSpacing(D.SPACE["s"])
            h.addWidget(D.button("Add to effort list", "primary", lambda _c=False, t=term: self.decide(t, True)))
            h.addWidget(D.button("Not a term", "danger", lambda _c=False, t=term: self.decide(t, False)))
            p.setCellWidget(i, 3, box)
            p.setRowHeight(i, 38)
        self.p_card.setVisible(bool(pend))
        return len(pend)

    def decide(self, term, add, definition=None):
        """4.23.2: a term from our drafts decided on its row: in the effort's list with the meaning typed, or Not a term.
        The same decision as on Acros & Abs. Returns True when it was decided."""
        s = self.session()
        if s is None or term not in s.results:
            return False
        if add:
            if definition is None and term in self.pending_terms:
                w = self.pending_list.cellWidget(self.pending_terms.index(term), 2)
                definition = w.text().strip() if w is not None else ""
            s.add([term], definition or "")
            self.host.toast(f"{term} is in the effort's list" + ("" if definition else ", with no definition yet") + ".")
        else:
            s.set_status([term], "Not a term")
            self.host.toast(f"{term}: Not a term in this effort.")
        diag.activity("draft_acronym_decided", n=1)
        try:
            self.host.acronym_page.fill()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.fill()
        return True

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
