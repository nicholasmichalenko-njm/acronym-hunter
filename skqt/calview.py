"""The effort calendar as a file, in Qt (2.88.0): Template..., Import... (a preview of what every row does, then Apply),
Undo import, and Export... (Excel in the template's columns, or an .ics file for Outlook). The rules are effortcal's.
Rules only (No AI); nothing leaves the PC."""
import os
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
        self.undo_btn = D.button("Undo import", "ghost", lambda: self.undo(), "Put the calendar back as it was before the last import")
        return [D.button("Import...", None, lambda: self.import_file(), "A calendar file (the template, a CSV or an Outlook .ics): "
                         "its due date, stage dates, tasks, reviews and meetings"),
                D.button("Export...", None, lambda: self.export_menu(), "The whole calendar with its details: Excel or Outlook (.ics)"),
                D.button("Template...", "ghost", lambda: self.template(), "An Excel calendar for people to fill in"),
                self.undo_btn]

    def refresh(self):
        h = self.host
        self.undo_btn.setVisible(h.ws is not None and EC.can_undo(h.ws.root))

    def _rec(self):
        return R.Record(self.host.ws.root)

    def template(self, path=None):
        h = self.host
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self.page, "Calendar template", EF.out(h.effort_path, f"{h.effort_name or 'Effort'}_Calendar_Template.xlsx"),
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
            path, _ = QFileDialog.getSaveFileName(self.page, "Export the calendar", EF.out(h.effort_path, f"{h.effort_name}_Calendar{ext}"),
                                                  "Excel (*.xlsx)" if kind == "xlsx" else "Calendar (*.ics)")
        if not path:
            return ""
        st = self.page.state
        rows = EC.rows_of(self._rec(), st.cal_extra() if st is not None else ())
        (EC.write_xlsx if kind == "xlsx" else EC.write_ics)(path, rows, h.effort_name)
        diag.activity("qt_calendar_exported", n=len(rows))
        h.toast(f"Calendar exported: {len(rows)} date(s)")
        return path
