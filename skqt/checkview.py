"""Matrix > Check (4.67.0; Nicholas 2026-11-24 "Yes"). What Assign has left, as short lists: the requirements
not assigned to a section, the evaluation criteria not assigned, the sections that hold nothing, and (4.68.0) the
pieces assigned but not yet marked Addressed by a person. A row is opened
in Assign (double-click, or Open in Assign) with that piece or that section already picked. Nothing is changed here.
With nothing left it says so. How much of the customer's files was shredded (Coverage) is under More. The lists are
assignlinks.gaps. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QGridLayout, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

import assignlinks as AL
from . import design as D
from .commandbar import CommandBar

LISTS = (("requirements", "Requirements not assigned"), ("criteria", "Evaluation criteria not assigned"),
         ("empty", "Sections with nothing assigned"), ("open", "Assigned, not yet addressed"))   # 4.68.0: the fourth


class CheckView(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.g = {k: [] for k, _t in LISTS}
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.b_open = self.bar.primary("Open in Assign", lambda: self.open_row(), "The row picked, in Assign, ready to be assigned")
        self.b_done = self.bar.add("Mark Addressed", lambda: self.mark_addressed(),          # 4.68.0
                                   "The row picked under Assigned, not yet addressed: the draft answers it. Set by a person.")
        self.bar.more("How much of the customer's files was shredded...", lambda: self.host.go("prove"),
                      "Coverage: every piece of every file read and shredded, and the word-for-word text check")
        v.addWidget(self.bar)
        self.none = D.EmptyState("Nothing to check yet", "Check lists what Assign has left to link. Keep some requirements in "
                                 "Shred first.", "Open Shred", lambda: self.host.go("assign"))
        v.addWidget(self.none, 1)
        self.done = D.EmptyState("Nothing left", "Every kept requirement and criterion is in a section and marked Addressed, and "
                                 "every section holds something.", "Open the matrix", lambda: self.host.go("matrix"))
        v.addWidget(self.done, 1)
        self.body = QWidget(); row = QGridLayout(self.body); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(D.SPACE["m"])
        v.addWidget(self.body, 1)
        self.cards, self.lists = {}, {}
        for key, title in LISTS:
            card = D.Card(title)
            lw = QListWidget(); lw.setSelectionMode(QAbstractItemView.SingleSelection); lw.setWordWrap(False)
            lw.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); lw.setTextElideMode(Qt.ElideRight)
            lw.itemSelectionChanged.connect(lambda k=key: self.picked_in(k))
            lw.itemDoubleClicked.connect(lambda _it, k=key: self.open_row(k))
            card.add(lw)
            self.cards[key], self.lists[key] = card, lw
            row.addWidget(card, len(self.cards) > 3, (len(self.cards) - 1) % 3, 1, 3 if key == "open" else 1)
        self.said = D.label("", "muted"); v.addWidget(self.said)

    def _M(self):
        r = getattr(self.host, "review", None)
        return r.M if r is not None else None

    def refresh(self):
        M = self._M()
        has = M is not None and bool(M.outline) and bool(AL.pieces(M))
        self.g = AL.gaps(M) if has else {k: [] for k, _t in LISTS}
        n = sum(len(x) for x in self.g.values())
        self.none.setVisible(not has); self.done.setVisible(has and not n)
        self.body.setVisible(has and bool(n)); self.bar.setVisible(has and bool(n)); self.said.setVisible(has and bool(n))
        for key, title in LISTS:
            lw = self.lists[key]
            lw.blockSignals(True); lw.clear()
            for x in self.g[key]:
                text = x if key == "empty" else f"{x['ref']}   {' '.join(x['text'].split())}" + (f"   ({x['mark']}; {'; '.join(x['sections'])})" if key == "open" else "")
                it = QListWidgetItem(text); it.setToolTip(x if key == "empty" else x["text"])
                it.setData(Qt.UserRole, x if key == "empty" else x["id"])
                lw.addItem(it)
            lw.blockSignals(False)
            self.cards[key].title.setText(f"{title}: {len(self.g[key])}")
        self.said.setText(f"Not assigned: {len(self.g['requirements'])} requirement(s), {len(self.g['criteria'])} of the evaluation criteria. "
                          f"Sections with nothing: {len(self.g['empty'])}. Assigned, not yet addressed: {len(self.g['open'])}. "
                          "Double-click a row to open it in Assign.")
        self.b_open.setEnabled(False); self.b_done.setEnabled(False)
        return n

    def picked_in(self, key):
        """One row picked across the three lists."""
        for k, lw in self.lists.items():
            if k != key and lw.selectedItems():
                lw.blockSignals(True); lw.clearSelection(); lw.setCurrentRow(-1); lw.blockSignals(False)
        self.b_open.setEnabled(bool(self.lists[key].selectedItems()))
        self.b_done.setEnabled(key == "open" and bool(self.lists[key].selectedItems()))

    def picked(self):
        for k, lw in self.lists.items():
            if lw.selectedItems():
                return k, lw.selectedItems()[0].data(Qt.UserRole)
        return "", None

    def open_row(self, key=None):
        """The row picked, in Assign: a piece is picked in the list of Not assigned; a section is picked in the outline."""
        k, what = self.picked()
        if not k or (key and key != k):
            return None
        self.host.go("assignto")
        pg = self.host.assignto_page
        if k == "empty":
            pg.pick_section(what)
        else:
            pg.pick_piece(what, all_rows=(k == "open"))
        return k, what

    def mark_addressed(self):
        """4.68.0: the row picked under Assigned, not yet addressed is marked Addressed; it leaves the list."""
        k, what = self.picked()
        if k != "open":
            return 0
        M = self._M()
        n = AL.set_mark(M, [what], AL.DONE)
        if n:
            M.pending = True
            self.host.changed()
        self.refresh()
        self.host.status("Marked Addressed." if n else "Already Addressed.")
        return n
