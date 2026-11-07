"""The post-submission checklist in Qt (2.91.0): tick items done, assign an owner from the effort's people, set when
each is due (days after submission, or a date), add, reword, remove and reorder items, Mark submitted, Save as default
for new efforts, and Export to Excel (the effort's Exports folder to start). The rules are postsub's. Nothing leaves
the PC."""
import datetime, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QInputDialog, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)
import diag
import effortfolders as EF
import effortrec as R
import postsub as PS
from . import design as D
from .adaptive import FlowLayout

COLS = ("Done", "Task", "Owner", "Days after", "Due", "Status", "Notes")


class PostSubPage(QWidget):
    """3.75.0 (house rule 8): one bar (Mark submitted..., + Item; More: Save as default...; Export: Export to Excel...);
    the checklist shows its values as text with Done as a tick; the selected item's owner, days after and status are
    edited under the table, with Earlier, Later and Remove."""

    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self._filling = False
        self.items = []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        from .commandbar import CommandBar
        self.bar = CommandBar()
        self.bar.add("+ Item", lambda: self.add_item())
        self.sub_btn = self.bar.primary("Mark submitted...", lambda: self.mark_submitted(),
                                        "Due dates count from the moment it went in")
        self.bar.more("Save as default...", lambda: self.save_default(), "This list becomes the default for new efforts on this PC")
        self.bar.export("Export to Excel...", lambda: self.export(), "A formatted workbook for the effort's folder")
        v.addWidget(self.bar)
        self.card = D.Card("Post-submission checklist", "What the team does after the proposal goes in. Due dates count from "
                           "Mark submitted (from the proposal's due date until then). Tick an item when it is done.")
        self.state = self.card.add(D.label("", None))
        self.table = QTableWidget(0, len(COLS)); self.table.setHorizontalHeaderLabels(list(COLS))
        self.table.verticalHeader().setVisible(False); self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection)
        hh = self.table.horizontalHeader()
        for c, wdt in enumerate((50, 420, 170, 90, 110, 130)):
            self.table.setColumnWidth(c, wdt)
        hh.setStretchLastSection(True)
        self.table.itemChanged.connect(self.cell_changed)
        self.table.currentCellChanged.connect(lambda r, _c, _r2, _c2: self.show_row(r))
        self.table.setMinimumHeight(380)
        self.card.add(self.table)
        # the selected item, one editor at a time
        self.row = QWidget(); rl = FlowLayout(self.row, D.SPACE["s"])
        self.row_label = D.label("", "label", wrap=False); rl.addWidget(self.row_label)
        self.r_owner = QComboBox(); self.r_owner.setEditable(True); self.r_owner.setMinimumWidth(170)
        self.r_owner.currentTextChanged.connect(lambda t: self._row_set(owner=t))
        self.r_days = QSpinBox(); self.r_days.setRange(-30, 365); self.r_days.setSuffix(" d after")
        self.r_days.valueChanged.connect(lambda n: self._row_set(days=n))
        self.r_status = QComboBox(); self.r_status.addItems(list(PS.STATUS))
        self.r_status.currentTextChanged.connect(lambda t: self._row_set(status=t))
        for wdg in (D.label("Owner", None, wrap=False), self.r_owner, self.r_days, D.label("Status", None, wrap=False), self.r_status,
                    D.button("Earlier", "ghost", lambda: self.move(-1)), D.button("Later", "ghost", lambda: self.move(1)),
                    D.button("Remove", "ghost", lambda: self.remove_item())):
            rl.addWidget(wdg)
        self.row.setVisible(False)
        self.card.add(self.row)
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
        self.people = [""] + (h.people() if hasattr(h, "people") else [])
        keep = self.selected()
        self._filling = True
        t = self.table
        for i, it in enumerate(self.items):
            t.insertRow(i)
            done = QTableWidgetItem(""); done.setFlags((done.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
            done.setCheckState(Qt.Checked if it["status"] == "Done" else Qt.Unchecked)
            t.setItem(i, 0, done)
            ti = QTableWidgetItem(it["text"]); ti.setData(Qt.UserRole, it["id"]); t.setItem(i, 1, ti)
            dd = PS.due_of(r, it)
            for c, val in ((2, it["owner"]), (3, "" if it.get("due") else f"{int(it.get('days', 0) or 0)} d"),
                           (4, R.short_date(dd.isoformat()) if dd else ""), (5, it["status"])):
                x = QTableWidgetItem(val); x.setFlags(x.flags() & ~Qt.ItemIsEditable)
                t.setItem(i, c, x)
            if PS.late(r, it):
                t.item(i, 4).setForeground(D.color("crit"))
            t.setItem(i, 6, QTableWidgetItem(it.get("notes", "")))
            if it["status"] in ("Done", "Not needed"):
                for c in (1, 4, 6):
                    t.item(i, c).setForeground(D.color("muted"))
        t.resizeRowsToContents()
        self._filling = False
        row = next((i for i in range(t.rowCount()) if self._iid(i) == keep), -1)
        if row >= 0:
            t.setCurrentCell(row, 1)
        self.show_row(t.currentRow())

    def show_row(self, row):
        """The selected item's editors under the table."""
        it = next((x for x in self.items if x["id"] == self._iid(row)), None) if row >= 0 else None
        self.row.setVisible(it is not None)
        if it is None:
            return
        self._filling = True
        self.row_label.setText((it["text"][:40] + ("..." if len(it["text"]) > 40 else "")) + ":")
        self.r_owner.clear(); self.r_owner.addItems(self.people + ([it["owner"]] if it["owner"] and it["owner"] not in self.people else []))
        self.r_owner.setCurrentText(it["owner"])
        self.r_days.setValue(int(it.get("days", 0) or 0)); self.r_days.setEnabled(not it.get("due"))
        self.r_status.setCurrentText(it["status"])
        self._filling = False

    def _row_set(self, **fields):
        iid = self.selected()
        if self._filling or not iid:
            return False
        if "status" in fields:
            return self.set_status(iid, fields["status"])
        if "owner" in fields:                              # typed: the cell follows, the table is not drawn again
            ok = self.update(iid, **fields)
            it = self.table.item(self.table.currentRow(), 2)
            if it is not None:
                it.setText(fields["owner"])
            return ok
        return self.update(iid, refresh=True, **fields)

    # ------------------------------------------------------------ changes
    def _iid(self, row):
        it = self.table.item(row, 1)
        return it.data(Qt.UserRole) if it else None

    def cell_changed(self, item):
        if self._filling or self.host.ws is None:
            return
        iid = self._iid(item.row())
        if item.column() == 0:
            return self.set_status(iid, "Done" if item.checkState() == Qt.Checked else "Not started")
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
