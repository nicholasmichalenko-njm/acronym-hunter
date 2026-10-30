"""The post-submission checklist in Qt (2.91.0): tick items done, assign an owner from the effort's people, set when
each is due (days after submission, or a date), add, reword, remove and reorder items, Mark submitted, Save as default
for new efforts, and Export to Excel (the effort's Exports folder to start). The rules are postsub's. Nothing leaves
the PC."""
import datetime, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHeaderView, QInputDialog, QSpinBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import effortrec as R
import postsub as PS
from . import design as D
from .adaptive import FlowLayout

COLS = ("Done", "Task", "Owner", "Days after", "Due", "Status", "Notes")


class PostSubPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self._filling = False
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.card = D.Card("Post-submission checklist", "What the team does after the proposal goes in. Due dates count from "
                           "Mark submitted (from the proposal's due date until then).")
        row = FlowLayout(None, D.SPACE["s"]); self.card.body.addLayout(row)
        self.sub_btn = D.button("Mark submitted...", "primary", lambda: self.mark_submitted())
        row.addWidget(self.sub_btn)
        row.addWidget(D.button("+ Item", None, lambda: self.add_item()))
        row.addWidget(D.button("Remove", "ghost", lambda: self.remove_item()))
        row.addWidget(D.button("Up", "ghost", lambda: self.move(-1))); row.addWidget(D.button("Down", "ghost", lambda: self.move(1)))
        row.addStretch()
        row.addWidget(D.button("Save as default...", None, lambda: self.save_default(), "This list becomes the default for new efforts on this PC"))
        row.addWidget(D.button("Export to Excel...", None, lambda: self.export(), "A formatted workbook for the effort's folder"))
        self.state = self.card.add(D.label("", None))
        self.table = QTableWidget(0, len(COLS)); self.table.setHorizontalHeaderLabels(list(COLS))
        self.table.verticalHeader().setVisible(False); self.table.setWordWrap(True)
        hh = self.table.horizontalHeader()
        for c, wdt in enumerate((50, 420, 170, 90, 110, 130)):
            self.table.setColumnWidth(c, wdt)
        hh.setStretchLastSection(True)
        self.table.itemChanged.connect(self.cell_changed)
        self.table.setMinimumHeight(420)
        self.card.add(self.table)
        v.addWidget(self.card)

    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        self.table.setRowCount(0)
        if h.ws is None:
            self.state.setText("Open an effort first.")
            return
        r = self.rec()
        d = PS.data(r, h.config_dir)
        self.items = d["items"]
        done, total, nlate = PS.progress(r)
        b = PS.base_date(r)
        self.state.setText((f"Submitted {d['submitted'].replace('T', ' ')}. " if d.get("submitted") else
                            (f"Not marked submitted; due dates count from the due date, {R.short_date(b.isoformat())}. " if b else
                             "Not marked submitted and no due date: set either for due dates. "))
                           + f"{done} of {total} done" + (f", {nlate} late." if nlate else "."))
        people = [""] + (h.people() if hasattr(h, "people") else [])
        self._filling = True
        t = self.table
        for i, it in enumerate(self.items):
            t.insertRow(i)
            cb = QCheckBox(); cb.setChecked(it["status"] == "Done")
            cb.toggled.connect(lambda on, iid=it["id"]: self.set_status(iid, "Done" if on else "Not started"))
            w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(14, 0, 0, 0); lay.addWidget(cb)
            t.setCellWidget(i, 0, w)
            ti = QTableWidgetItem(it["text"]); ti.setData(Qt.UserRole, it["id"]); t.setItem(i, 1, ti)
            own = QComboBox(); own.setEditable(True); own.addItems(people + ([it["owner"]] if it["owner"] and it["owner"] not in people else []))
            own.setCurrentText(it["owner"])
            own.currentTextChanged.connect(lambda txt, iid=it["id"]: self.update(iid, owner=txt))
            t.setCellWidget(i, 2, own)
            sp = QSpinBox(); sp.setRange(-30, 365); sp.setValue(int(it.get("days", 0) or 0)); sp.setSuffix(" d")
            sp.setEnabled(not it.get("due"))
            sp.valueChanged.connect(lambda n, iid=it["id"]: self.update(iid, days=n))
            t.setCellWidget(i, 3, sp)
            dd = PS.due_of(r, it)
            di = QTableWidgetItem(R.short_date(dd.isoformat()) if dd else ""); di.setFlags(di.flags() & ~Qt.ItemIsEditable)
            di.setToolTip("A date set by hand: double-click Days after's row, Set due date... (or type in the Excel copy)")
            if PS.late(r, it):
                di.setForeground(D.color("crit"))
            t.setItem(i, 4, di)
            st = QComboBox(); st.addItems(list(PS.STATUS)); st.setCurrentText(it["status"])
            st.currentTextChanged.connect(lambda s, iid=it["id"]: self.set_status(iid, s))
            t.setCellWidget(i, 5, st)
            t.setItem(i, 6, QTableWidgetItem(it.get("notes", "")))
            if it["status"] in ("Done", "Not needed"):
                for c in (1, 4, 6):
                    t.item(i, c).setForeground(D.color("muted"))
        t.resizeRowsToContents()
        self._filling = False

    # ------------------------------------------------------------ changes
    def _iid(self, row):
        it = self.table.item(row, 1)
        return it.data(Qt.UserRole) if it else None

    def cell_changed(self, item):
        if self._filling or self.host.ws is None:
            return
        iid = self._iid(item.row())
        if item.column() == 1:
            self.update(iid, text=item.text(), refresh=False)
        elif item.column() == 6:
            self.update(iid, notes=item.text(), refresh=False)

    def update(self, iid, refresh=False, **fields):
        if self._filling or self.host.ws is None or not iid:
            return False
        ok = PS.update(self.rec(), iid, **fields)
        if refresh or "days" in fields:
            self.refresh()
        return ok

    def set_status(self, iid, status):
        if self._filling:
            return False
        ok = PS.update(self.rec(), iid, status=status)
        diag.activity("qt_postsub_status")
        self.refresh()
        return ok

    def add_item(self, text=None, owner="", days=0):
        if self.host.ws is None:
            return None
        if text is None:
            text, ok = QInputDialog.getText(self, "Post-submission item", "What needs doing:")
            if not ok:
                return None
        iid = PS.add(self.rec(), text, owner, days)
        self.refresh()
        return iid

    def selected(self):
        r = self.table.currentRow()
        return self._iid(r) if r >= 0 else None

    def remove_item(self, iid=None):
        iid = iid or self.selected()
        if not iid:
            return False
        ok = PS.remove(self.rec(), iid)
        self.refresh()
        return ok

    def move(self, step, iid=None):
        iid = iid or self.selected()
        if not iid or not PS.move(self.rec(), iid, step):
            return False
        self.refresh()
        row = next((i for i in range(self.table.rowCount()) if self._iid(i) == iid), -1)
        self.table.setCurrentCell(row, 1)
        return True

    def mark_submitted(self, when=None):
        if self.host.ws is None:
            return None
        if when is None:
            now = datetime.datetime.now()
            text, ok = QInputDialog.getText(self, "Mark submitted", "When was it submitted? (YYYY-MM-DD HH:MM)", text=f"{now:%Y-%m-%d %H:%M}")
            if not ok:
                return None
            try:
                when = datetime.datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").isoformat(timespec="minutes")
            except ValueError:
                self.host.status("Write the time as 2026-12-15 14:05.")
                return None
        got = PS.mark_submitted(self.rec(), when)
        diag.activity("qt_postsub_submitted")
        self.refresh()
        self.host.toast("Marked submitted")
        return got

    def save_default(self, confirm=True):
        if self.host.ws is None:
            return 0
        import teampack as TP
        if TP.locked(self.host.config_dir, "postsub"):
            self.host.status("The team pack set the default post-submission checklist.")
            return 0
        n = PS.save_default(self.host.config_dir, PS.data(self.rec())["items"])
        diag.activity("qt_postsub_default_saved", n=n)
        self.host.toast(f"Default post-submission checklist saved ({n} items)")
        return n

    def export(self, path=None):
        h = self.host
        if h.ws is None:
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the post-submission checklist",
                                                  h.out_path("postsub"),
                                                  "Excel (*.xlsx)")
        if not path:
            return ""
        PS.export_xlsx(self.rec(), path, h.effort_name)
        diag.activity("qt_postsub_exported")
        h.toast("Post-submission checklist exported")
        return path
