"""Activity (4.27.1; Nicholas 2026-11-12, answer 2: "Activity is a tab of the effort's page"). Everything that
happened in the effort, by day, newest first: who did what and when. Filter by person, by kind of thing and by how far
back. A row about a task, a graphic, a deliverable or a fact on the wall opens that thing (double-click). It reads the
effort record's timeline, which already keeps who and when; nothing new is stored. Rules only; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

import diag
import worklists as WL
from . import design as D

COLS = ["When", "Who", "Kind", "What happened"]


class ActivityPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        self.rows = []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        self.f_who = QComboBox(); self.f_who.setMinimumWidth(160)
        self.f_kind = QComboBox(); self.f_kind.setMinimumWidth(160)
        self.f_when = QComboBox()
        for k, n in WL.PERIODS:
            self.f_when.addItem(n, k)
        for w in (self.f_who, self.f_kind, self.f_when):
            w.activated.connect(lambda _i: self.fill())
            row.addWidget(w)
        row.addStretch(1)
        self.count = D.label("", "muted", wrap=False); row.addWidget(self.count)
        v.addLayout(row)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        for c in range(len(COLS)):
            hh.setSectionResizeMode(c, QHeaderView.Stretch if c == 3 else QHeaderView.Interactive)
        for c, wd in enumerate((80, 150, 150)):
            self.table.setColumnWidth(c, wd)
        self.table.doubleClicked.connect(lambda _ix: self.open_row())
        v.addWidget(self.table, 1)
        self.empty = D.label("Nothing has happened in this effort yet.", "muted"); self.empty.setAlignment(Qt.AlignCenter)
        v.addWidget(self.empty, 1)

    def events(self):
        import effortrec as RR
        return RR.Record(self.host.ws.root).events() if self.host.ws is not None else []

    def refresh(self):
        ev = self.events()
        who, kind = self.f_who.currentData(), self.f_kind.currentData()
        for box, first, items, keep in ((self.f_who, "Everyone", [(p, p) for p in WL.people(ev)], who),
                                        (self.f_kind, "Every kind", WL.kinds(ev), kind)):
            box.blockSignals(True); box.clear(); box.addItem(first, "")
            for k, n in items:
                box.addItem(n, k)
            box.setCurrentIndex(max(0, box.findData(keep or "")))
            box.blockSignals(False)
        return self.fill(ev)

    def fill(self, ev=None):
        ev = self.events() if ev is None else ev
        days = WL.activity(ev, self.f_who.currentData() or "", self.f_kind.currentData() or "", self.f_when.currentData() or "")
        t = self.table
        t.clearSpans()
        n = sum(1 + len(rows) for _d, rows in days)
        t.setRowCount(n)
        self.rows = []
        r = shown = 0
        for day, rows in days:
            it = QTableWidgetItem(f"{day}   ·   {len(rows)}")
            f = it.font(); f.setWeight(QFont.DemiBold); it.setFont(f); it.setFlags(Qt.ItemIsEnabled)
            it.setBackground(D.color("surface2"))
            t.setItem(r, 0, it)
            for c in range(1, len(COLS)):
                x = QTableWidgetItem(""); x.setFlags(Qt.ItemIsEnabled); t.setItem(r, c, x)
            t.setSpan(r, 0, 1, len(COLS))
            self.rows.append(None); r += 1
            for at, who, kind, text, ref in rows:
                for c, val in enumerate((at, who, kind, text)):
                    ci = QTableWidgetItem(val)
                    if c == 3 and WL.page_of(ref):
                        ci.setForeground(D.color("accent")); ci.setToolTip("Double-click to open it")
                    t.setItem(r, c, ci)
                self.rows.append({"ref": ref, "text": text}); r += 1; shown += 1
        self.count.setText(f"{shown} of {len(ev)}" if ev else "")
        self.empty.setVisible(not ev); t.setVisible(bool(ev))
        diag.activity("qt_activity_shown")
        return shown

    def current(self):
        r = self.table.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def open_row(self, x=None):
        """Open what the row is about. Returns the page opened, or ""."""
        x = x or self.current()
        pg = WL.page_of((x or {}).get("ref"))
        if not pg:
            return ""
        h = self.host
        h.go(pg)
        ref = x["ref"]
        try:
            if pg == "tasks" and ref.get("task"):
                h.tasks_page.set_view("effort"); h.tasks_page.select(ref["task"])
            elif pg == "graphics" and ref.get("graphic"):
                h.graphics_page.select("need:" + ref["graphic"])
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return pg
