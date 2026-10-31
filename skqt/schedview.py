"""Effort Home > Schedule from the due date... (3.1.0): every stage of the effort with the working days it takes (the
team's defaults by name), dated backward from the proposal due date, or fitted between a start date and the due date.
Every date shows before anything is set; Set the dates writes the stages' planned starts and ends (names, goals and
gates stay). Save as the team's defaults keeps the days and holidays for the next effort."""
import datetime
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDateEdit, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
                               QLineEdit, QRadioButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)
import diag
import effortrec as R
import effortsched as S
from . import design as D


def _d(x):
    return f"{x.strftime('%a')} {x.strftime('%b')} {x.day}, {x.year}" if x else ""


class ScheduleDialog(QDialog):
    def __init__(self, host, rec):
        super().__init__(host)
        self.host, self.rec = host, rec
        self.setWindowTitle("Schedule from the due date")
        self.resize(820, 600)
        self.defaults = S.load_defaults(host.config_dir)
        self.saved = False
        v = QVBoxLayout(self)
        due = R.parse_when(rec.data.get("due", ""))
        self.due = due.date() if due else None
        head = D.label("", None); head.setTextFormat(Qt.RichText); v.addWidget(head)
        head.setText(f"<b>Proposal due:</b> {_d(self.due)}" if self.due else
                     "<b>No due date yet.</b> Set it on Effort Home (click the due date in the banner), then come back.")
        mode = QHBoxLayout(); v.addLayout(mode)
        self.back = QRadioButton("Back from the due date (each stage takes its days)"); self.back.setChecked(True)
        self.fitr = QRadioButton("Fit between"); self.start = QDateEdit(); self.start.setCalendarPopup(True)
        self.start.setDisplayFormat("MMM d, yyyy"); self.start.setDate(QDate.currentDate())
        mode.addWidget(self.back); mode.addSpacing(D.SPACE["l"]); mode.addWidget(self.fitr); mode.addWidget(self.start)
        mode.addWidget(D.label("and the due date", None, wrap=False)); mode.addStretch(1)
        opts = QHBoxLayout(); v.addLayout(opts)
        self.weekends = QCheckBox("Weekends count as working days"); self.weekends.setChecked(self.defaults["weekends"])
        self.last_on_due = QCheckBox("The last stage ends on the due date"); self.last_on_due.setChecked(True)
        self.last_on_due.setToolTip("Untick to finish the working day before the due date")
        opts.addWidget(self.weekends); opts.addWidget(self.last_on_due); opts.addStretch(1)
        hol = QHBoxLayout(); v.addLayout(hol)
        hol.addWidget(D.label("Holidays (not working days)", "muted", wrap=False))
        self.holidays = QLineEdit(", ".join(self.defaults["holidays"]))
        self.holidays.setPlaceholderText("2026-11-26, 2026-12-25")
        hol.addWidget(self.holidays, 1)
        t = QTableWidget(0, 4); t.setHorizontalHeaderLabels(["Stage", "Working days", "Starts", "Ends"])
        t.verticalHeader().setVisible(False); t.setSelectionMode(QAbstractItemView.NoSelection)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in ((1, 110), (2, 190), (3, 190)):
            t.setColumnWidth(i, w)
        t.verticalHeader().setDefaultSectionSize(34)
        self.table = t; v.addWidget(t, 1)
        self.spins = []
        for s in rec.stages:
            r = t.rowCount(); t.insertRow(r)
            it = QTableWidgetItem(s["name"]); it.setFlags(Qt.ItemIsEnabled); t.setItem(r, 0, it)
            sp = QSpinBox(); sp.setRange(0, 200); sp.setValue(S.days_for(s["name"], self.defaults)); sp.setSuffix(" days")
            sp.valueChanged.connect(lambda _v: self.preview())
            t.setCellWidget(r, 1, sp); self.spins.append((s, sp))
            for c in (2, 3):
                x = QTableWidgetItem(""); x.setFlags(Qt.ItemIsEnabled); t.setItem(r, c, x)
        self.note = D.label("", "muted"); self.note.setWordWrap(True); v.addWidget(self.note)
        bb = QDialogButtonBox()
        self.save_def = bb.addButton("Save as the team's defaults", QDialogButtonBox.ActionRole)
        self.set_btn = bb.addButton("Set the dates", QDialogButtonBox.AcceptRole)
        bb.addButton(QDialogButtonBox.Cancel)
        self.save_def.clicked.connect(lambda: self.save_defaults())
        self.set_btn.clicked.connect(lambda: self.apply())
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        for w in (self.back, self.fitr, self.weekends, self.last_on_due):
            w.toggled.connect(lambda _on: self.preview())
        self.start.dateChanged.connect(lambda _d: self.preview())
        self.holidays.editingFinished.connect(lambda: self.preview())
        self.plan = []
        self.preview()

    def holiday_list(self):
        import re
        return [h for h in re.split(r"[\s,;]+", self.holidays.text()) if S._date(h)]

    def calendar(self):
        return S.Calendar(self.weekends.isChecked(), self.holiday_list())

    def preview(self):
        self.plan = []
        for r in range(self.table.rowCount()):
            for c in (2, 3):
                self.table.item(r, c).setText("")
        if not self.due:
            self.set_btn.setEnabled(False)
            self.note.setText("Stationkeeper needs the proposal due date to work back from.")
            return []
        cal = self.calendar()
        items = [(s["id"], sp.value()) for s, sp in self.spins]
        if self.fitr.isChecked():
            plan, avail = S.fit(items, self.start.date().toPython(), self.due, cal, self.last_on_due.isChecked())
            if not plan:
                self.set_btn.setEnabled(False)
                self.note.setText(f"Only {avail} working day(s) between the start and the due date: not enough for one day a stage.")
                return []
        else:
            plan = S.plan_back(items, self.due, cal, self.last_on_due.isChecked())
        self.plan = plan
        for r, (_sid, a, b) in enumerate(plan):
            self.table.item(r, 2).setText(_d(a)); self.table.item(r, 3).setText(_d(b))
        first = plan[0][1] if plan else None
        today = datetime.date.today()
        warn = first is not None and first < today and self.back.isChecked()
        span = S.Calendar(self.weekends.isChecked(), self.holiday_list()).count(first, plan[-1][2]) if plan else 0
        self.note.setText((f"The first stage would start {_d(first)}, before today. Shorten some stages, or choose Fit between today "
                           "and the due date. " if warn else "")
                          + f"{span} working days from {_d(first)} to {_d(plan[-1][2])}. Nothing changes until Set the dates.")
        self.note.setProperty("tone", "warn" if warn else "")
        self.set_btn.setEnabled(bool(plan))
        return plan

    def apply(self):
        if not self.plan:
            return 0
        n = S.apply(self.rec, self.plan)
        diag.activity("schedule_from_due", n=n)
        self.saved = True
        self.host.toast(f"Dates set for {n} stages, from {_d(self.plan[0][1])} to {_d(self.plan[-1][2])}")
        self.accept()
        return n

    def save_defaults(self):
        S.save_defaults(self.host.config_dir, {s["name"]: sp.value() for s, sp in self.spins}, self.weekends.isChecked(),
                        self.holiday_list())
        diag.activity("schedule_defaults_saved")
        self.host.toast("Saved: new efforts start from these working days and holidays")
        return True
