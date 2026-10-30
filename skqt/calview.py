"""The effort calendar as a file, in Qt (2.88.0): Template..., Import... (a preview of what every row does, then Apply),
Undo import, and Export... (Excel in the template's columns, or an .ics file for Outlook). The rules are effortcal's.
Rules only (No AI); nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QMenu, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)
import diag
import effortfolders as EF
import effortcal as EC
import effortrec as R
from . import design as D


class ImportDialog(QDialog):
    def __init__(self, parent, path, pl):
        super().__init__(parent)
        self.setWindowTitle("Import the calendar")
        self.resize(980, 560)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"<b>{os.path.basename(path)}</b>: {EC.summary(pl)}. Nothing changes until you choose Apply; "
                            "Undo import puts the calendar back afterwards.", None))
        t = QTableWidget(len(pl), 7)
        t.setHorizontalHeaderLabels(["Row", "Date", "Time", "Kind", "What", "Does", "Why"])
        t.verticalHeader().setVisible(False); t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, p in enumerate(pl):
            tm = EC.nice_time(p["start"]) + (f" to {EC.nice_time(p['end'])}" if p["end"] else "") + (f" {p['zone']}" if p["zone"] and p["start"] else "")
            vals = (str(p["row"] or ""), R.short_date(p["date"]) if p["date"] else "", tm, p["kind"], p["title"],
                    EC.ACTION_WORDS[p["action"]], p["why"])
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 5:
                    it.setForeground(D.color("crit" if not p["ok"] else "muted" if p["action"] == "same" else "ok"))
                t.setItem(i, c, it)
        for c, w in enumerate((44, 100, 150, 110, 300, 190)):
            t.setColumnWidth(c, w)
        t.horizontalHeader().setStretchLastSection(True)
        self.table = t
        v.addWidget(t, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.apply_btn = bb.addButton("Apply", QDialogButtonBox.AcceptRole)
        self.apply_btn.setEnabled(any(p["ok"] and p["action"] != "same" for p in pl))
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)


class CalendarFiles:
    """The Calendar card's file buttons, for Effort home."""

    def __init__(self, page):
        self.page = page
        self.host = page.host

    def buttons(self):
        """The card's own buttons: + Due date... and + Event... (the file buttons are file_row())."""
        return [D.button("+ Due date...", "primary", lambda: entry_dialog(self.page, "Due"), "Something due at a date and time: drafts, "
                         "reviews' packets, the questions to the customer"),
                D.button("+ Event...", None, lambda: entry_dialog(self.page, "Meeting"), "A review, a meeting, orals: when, where, who")]

    def file_row(self):
        """2.92.0: Import, Export, Template and Undo import, in a row that wraps under the calendar."""
        from .adaptive import FlowLayout
        row = FlowLayout(None, D.SPACE["s"])
        self.undo_btn = D.button("Undo import", "ghost", lambda: self.undo(), "Put the calendar back as it was before the last import")
        for b in (D.button("Import...", None, lambda: self.import_file(), "A calendar file (the template, a CSV or an Outlook .ics): "
                           "its due date, stage dates, tasks, due dates, reviews and meetings"),
                  D.button("Export...", None, lambda: self.export_menu(), "The whole calendar with its details: Excel or Outlook (.ics)"),
                  D.button("Template...", "ghost", lambda: self.template(), "An Excel calendar for people to fill in"), self.undo_btn):
            row.addWidget(b)
        return row

    def refresh(self):
        h = self.host
        self.undo_btn.setVisible(h.ws is not None and EC.can_undo(h.ws.root))

    def _rec(self):
        return R.Record(self.host.ws.root)

    def template(self, path=None):
        h = self.host
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self.page, "Calendar template", h.out_path("calendar_template"),
                                                  "Excel (*.xlsx)")
        if not path:
            return ""
        EC.write_xlsx(path, [], h.effort_name, template=True)
        diag.activity("qt_calendar_template")
        h.toast("Calendar template saved")
        return path

    def import_file(self, path=None, apply=None):
        """apply (tests): True to apply without the preview, False to look only."""
        h = self.host
        if h.ws is None:
            return None
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self.page, "Import a calendar", "", "Calendar files (*.xlsx *.csv *.ics)")
        if not path:
            return None
        try:
            rows = EC.read_rows(path, h.effort_name)
        except ValueError as e:
            h.status(f"That calendar could not be read: {e}.")
            return None
        except Exception:
            diag.swallowed()
            h.status("That calendar could not be read. Close it in Excel, or save it as .xlsx, .csv or .ics.")
            return None
        rec = self._rec()
        pl = EC.plan(rows, rec)
        self.last_plan = pl
        if apply is None:
            dlg = ImportDialog(self.page, path, pl)
            if dlg.exec() != QDialog.Accepted:
                return pl
        elif not apply:
            return pl
        n = EC.apply(pl, rec, source=path)
        diag.activity("qt_calendar_imported", n=sum(n.values()))
        h.apply_marking()
        self.page.refresh()
        h.toast(f"Calendar imported: {sum(n.values())} change(s)")
        return pl

    def undo(self):
        h = self.host
        if h.ws is None or not EC.undo(self._rec()):
            return False
        diag.activity("qt_calendar_import_undone")
        self.page.refresh()
        h.toast("Calendar import undone")
        return True

    def export_menu(self):
        m = QMenu(self.page)
        m.addAction("Excel (the template's columns)...", lambda: self.export("xlsx"))
        m.addAction("Outlook calendar (.ics)...", lambda: self.export("ics"))
        m.exec(self.page.cursor().pos())

    def export(self, kind="xlsx", path=None):
        h = self.host
        if h.ws is None:
            return ""
        ext = ".xlsx" if kind == "xlsx" else ".ics"
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self.page, "Export the calendar", h.out_path("calendar", ext=ext),
                                                  "Excel (*.xlsx)" if kind == "xlsx" else "Calendar (*.ics)")
        if not path:
            return ""
        st = self.page.state
        rows = EC.rows_of(self._rec(), st.cal_extra() if st is not None else ())
        (EC.write_xlsx if kind == "xlsx" else EC.write_ics)(path, rows, h.effort_name)
        diag.activity("qt_calendar_exported", n=len(rows))
        h.toast(f"Calendar exported: {len(rows)} date(s)")
        return path


class EntryDialog(QDialog):
    """2.92.0: a due date or an event typed in the app: what, when (date, time, end), its time zone, who, where, details."""

    def __init__(self, parent, host, kind="Due", entry=None, day=None):
        from PySide6.QtCore import QDate, QTime
        from PySide6.QtWidgets import QCheckBox, QComboBox, QDateEdit, QFormLayout, QLineEdit, QPlainTextEdit, QTimeEdit
        import tzones as TZ
        from .modes import settings
        super().__init__(parent)
        e = dict(entry or {})
        self.setWindowTitle(("Change " if entry else "New ") + ("due date" if (e.get("kind") or kind) in EC.DUE_KINDS else "event"))
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        f = QFormLayout(); v.addLayout(f)
        self.kind = QComboBox(); self.kind.addItems(list(EC.EVENT_KINDS)); self.kind.setCurrentText(e.get("kind") or kind)
        self.title = QLineEdit(e.get("title", "")); self.title.setPlaceholderText("Drafts to Production, Red team review...")
        self.date = QDateEdit(); self.date.setCalendarPopup(True); self.date.setDisplayFormat("MMM d, yyyy")
        dd = EC.parse_date(e.get("date")) if e.get("date") else (day or datetime.date.today())
        self.date.setDate(QDate(dd.year, dd.month, dd.day))
        self.timed = QCheckBox("At a time"); self.timed.setChecked(bool(e.get("start")) or not entry)
        self.start = QTimeEdit(); self.start.setDisplayFormat("h:mm AP")
        self.end = QTimeEdit(); self.end.setDisplayFormat("h:mm AP")
        st = e.get("start") or ("17:00" if kind in EC.DUE_KINDS else "09:00")
        self.start.setTime(QTime(int(st[:2]), int(st[3:5])))
        en = e.get("end") or ""
        self.has_end = QCheckBox("Ends at"); self.has_end.setChecked(bool(en))
        self.end.setTime(QTime(int(en[:2]), int(en[3:5])) if en else QTime(int(st[:2]) + 1 if int(st[:2]) < 23 else 23, int(st[3:5])))
        self.zone = QComboBox()
        for k, text in TZ.choices():
            self.zone.addItem(text, k)
        rec = R.Record(host.ws.root)
        mine = TZ.my_zone(settings())
        zk = e.get("zone") if TZ.valid(e.get("zone", "")) else ((rec.zone_key() or mine) if kind in EC.DUE_KINDS else mine)
        if self.zone.findData(zk) < 0:
            self.zone.addItem(zk, zk)
        self.zone.setCurrentIndex(max(0, self.zone.findData(zk)))
        self.owner = QComboBox(); self.owner.setEditable(True); self.owner.addItems([""] + (host.people() if hasattr(host, "people") else []))
        self.owner.setCurrentText(e.get("owner", ""))
        self.location = QLineEdit(e.get("location", "")); self.location.setPlaceholderText("Room 2B, a Teams meeting, a site")
        self.details = QPlainTextEdit(e.get("details", "")); self.details.setMaximumHeight(90)
        times = QHBoxLayout(); times.addWidget(self.timed); times.addWidget(self.start); times.addWidget(self.has_end); times.addWidget(self.end); times.addStretch(1)
        f.addRow("Kind", self.kind); f.addRow("What", self.title); f.addRow("Date", self.date); f.addRow("Time", times)
        f.addRow("Time zone", self.zone); f.addRow("Owner", self.owner); f.addRow("Where", self.location); f.addRow("Details", self.details)
        self.mine = D.label("", "muted"); v.addWidget(self.mine)
        for w in (self.timed, self.has_end):
            w.toggled.connect(lambda _on: self._enable())
        for sig in (self.start.timeChanged, self.date.dateChanged):
            sig.connect(lambda *_a: self._say())
        self.zone.currentIndexChanged.connect(lambda _i: self._say())
        self.my_zone = mine
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._enable()

    def _enable(self):
        self.start.setEnabled(self.timed.isChecked()); self.has_end.setEnabled(self.timed.isChecked())
        self.end.setEnabled(self.timed.isChecked() and self.has_end.isChecked())
        self._say()

    def _say(self):
        x = self.values()
        self.mine.setText(EC.entry_times(x, self.my_zone) if x["start"] else "All day.")

    def values(self):
        return {"kind": self.kind.currentText(), "title": self.title.text(), "date": self.date.date().toPython().isoformat(),
                "start": self.start.time().toString("HH:mm") if self.timed.isChecked() else "",
                "end": self.end.time().toString("HH:mm") if self.timed.isChecked() and self.has_end.isChecked() else "",
                "zone": self.zone.currentData() if self.timed.isChecked() else "", "owner": self.owner.currentText().strip(),
                "location": self.location.text(), "details": self.details.toPlainText()}


def entry_dialog(page, kind="Due", entry=None, day=None, answer=None):
    """+ Due date..., + Event... and Edit: returns the id saved, or None. answer (tests): the values."""
    h = page.host
    if h.ws is None:
        return None
    if answer is None:
        dlg = EntryDialog(page, h, kind, entry, day)
        if dlg.exec() != QDialog.Accepted:
            return None
        answer = dlg.values()
    rec = R.Record(h.ws.root)
    if entry:
        EC.update_entry(rec, entry["id"], **answer)
        eid = entry["id"]
    else:
        eid = EC.add_entry(rec, **answer)
        if eid is None:
            h.status("Give it a date and say what it is.")
            return None
    diag.activity("qt_calendar_entry_saved")
    page.refresh()
    return eid
