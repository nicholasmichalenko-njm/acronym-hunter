"""The Global Standards page (4.34.0; Nicholas's ST7, ST9, ST14, ST18, ST19 of 2026-11-14): one page, by that name,
outside the effort path. It opens whether or not an effort is open and always changes the Global Standards: its
buttons open the standards' own editors with the Global Standards in view (effortset.view_global), and a save is
shared at once with everyone who reads the linked folder. Who is on which version is listed from each PC's receipt.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

import diag
import globalfolder as GF
from . import design as D, globalview as GV

EDITORS = (("styles", "Styles"), ("designs", "Quick Parts"), ("formatstd", "Page Layout"), ("templates", "Templates"),
           ("prodstd", "Formatting"), ("rules", "Rules"))


class GlobalPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); outer.addWidget(sc)
        body = QWidget(); sc.setWidget(body)
        v = QVBoxLayout(body); v.setContentsMargins(D.SPACE["l"], D.SPACE["l"], D.SPACE["l"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        GV.add_card(self, v)
        self.edit_card = D.Card("Change the Global Standards", "Each opens that part of the Global Standards as it is, to change. "
                                "A change is saved as you make it; an open effort keeps its own standards and is not touched.")
        row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
        self.edit_buttons = {}
        for step, text in EDITORS:
            b = D.button(text, None, lambda _c=False, s=step: self.open(s)); h.addWidget(b); self.edit_buttons[step] = b
        h.addStretch(1); self.edit_card.add(row); v.addWidget(self.edit_card)
        self.who_count = D.button("", None, self.toggle_who, "Who is on which version. Each PC leaves its own line when it opens Stationkeeper.")
        self.gs_card.add(self.who_count)
        self.who_card = D.Card("Who has it", "People behind the latest come first. Someone with no line has not opened Stationkeeper "
                               "with the shared folder chosen.",
                               actions=[D.button("Remove the line", None, self.forget,
                                                 "For someone who has left. The line comes back if that PC opens Stationkeeper with the folder chosen.")])
        self.who = QTableWidget(0, 4); self.who.setHorizontalHeaderLabels(["Person", "PC", "Version", "When"])
        self.who.setEditTriggers(QAbstractItemView.NoEditTriggers); self.who.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.who.horizontalHeader().setStretchLastSection(True); self.who.setMinimumHeight(160)
        self.who_card.add(self.who); self.who_card.setVisible(False); v.addWidget(self.who_card)
        v.addStretch(1)
        self.rows = []

    def open(self, step):
        """One of the standards' own editors, with the Global Standards in view."""
        __import__("effortset").view_global(True)
        self.host.go(step)

    def people(self):
        """The names on the People list (the team's author list), for who has not been seen yet."""
        try:
            return [n for n in self.host.authors.names() if n]
        except Exception:  # noqa: BLE001  the list is a courtesy
            return []

    def toggle_who(self):
        """ST23: the count opens the list, and closes it."""
        self.who_card.setVisible(self.who_card.isHidden())

    def refresh(self):
        import os
        GV.share_now(self.host)                                    # coming back from an editor: what was saved is shared
        GV.show(self)
        folder = GF.folder()
        linked = bool(folder) and os.path.isdir(folder)
        self.who_count.setVisible(linked)
        if not linked:
            self.who_card.setVisible(False)
            return
        try:
            rows = GF.receipts(folder, self.people())
        except Exception:  # noqa: BLE001
            diag.swallowed(); rows = []
        cur = (GF.current(folder) or {}).get("version", 0)
        behind = lambda r: 0 if r["version"] is None else (1 if r["version"] < cur else 2)
        self.rows = sorted(rows, key=lambda r: (behind(r), r["name"].lower()))       # who needs a nudge comes first
        self.who.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            ver = "not seen yet" if r["version"] is None else (f"{r['version']}" + ("" if r["version"] >= cur else f" (latest is {cur})"))
            for j, t in enumerate((r["name"], r["pc"], ver, r["when"])):
                self.who.setItem(i, j, QTableWidgetItem(str(t)))
        self.who.resizeColumnsToContents()
        on = sum(1 for r in self.rows if r["version"] == cur)
        n = len(self.rows)
        self.who_count.setText(f"{on} of {n} {'person is' if n == 1 else 'people are'} on version {cur}" if n and cur
                               else "No one has opened Stationkeeper with this folder yet")

    def forget(self):
        rows = sorted({i.row() for i in self.who.selectionModel().selectedRows()})
        n = sum(1 for i in rows if GF.forget_receipt(GF.folder(), self.rows[i]["file"]))
        self.host.status(f"Removed {n} line{'s' if n != 1 else ''}." if n else "Select a person's line first.")
        self.refresh()
        return n
