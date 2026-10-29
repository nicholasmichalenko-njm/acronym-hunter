"""Editing an effort's stages (2.92.0; 2.93.0 date pickers and times): the stage table (name, when it starts, when it
ends, gate) with Up, Down, + Stage and Remove, shared by Effort Record and Effort Home's Edit stages... A stage's start
and end are picked from a calendar, with an optional time (a stage without a time starts at the start of its day and
ends at the end of it). The gate choices are the team's (Settings > Stages, gates and roles). The current stage cannot
be removed. The rules are the effort record's. Nothing leaves the PC."""
import datetime
import re

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCalendarWidget, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
                               QMenu, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QWidgetAction)
import diag
import effortrec as R
from . import design as D

ANY = "Any time"


def clear_table(t):
    """Empty a table whose cells hold widgets: the old widgets are hidden at once (Qt deletes them a moment later, and
    until then a hidden one could show again over the new rows)."""
    for i in range(t.rowCount()):
        for c in range(t.columnCount()):
            w = t.cellWidget(i, c)
            if w is not None:
                w.hide()
    t.setRowCount(0)


def set_cell_widget(t, i, c, w):
    old = t.cellWidget(i, c)
    if old is not None:
        old.hide()
    t.setCellWidget(i, c, w)


def times():
    """The times offered: every half hour (any other can be typed, like 8:15 AM)."""
    return [ANY] + [nice_hm(f"{h:02d}:{m:02d}") for h in range(24) for m in (0, 30)]


def nice_hm(hm):
    """'14:30' -> '2:30 PM' ('' -> 'Any time')."""
    if not hm:
        return ANY
    h, m = int(hm[:2]), int(hm[3:5])
    return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def parse_hm(text):
    """'2:30 PM', '2:30pm', '14:30', '2 pm', 'Any time' or '' -> 'HH:MM' or '' (None when not understood)."""
    t = " ".join(str(text or "").lower().replace(".", "").split())
    if not t or t == ANY.lower():
        return ""
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a|p)?", t)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "")[:1]
    if mi > 59 or h > 23 or (ap and not 1 <= h <= 12):
        return None
    if ap == "p" and h != 12:
        h += 12
    elif ap == "a" and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}"


class WhenCell(QWidget):
    """A date picked from a calendar ('Not set' until one is) and an optional time."""
    changed = Signal()

    def __init__(self, date_iso="", hm="", end=False):
        super().__init__()
        self.end = end
        h = QHBoxLayout(self); h.setContentsMargins(2, 1, 2, 1); h.setSpacing(4)
        self.btn = QPushButton(); self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setToolTip("Pick the date from a calendar")
        self.btn.clicked.connect(self.pick)
        h.addWidget(self.btn, 3)
        self.time = QComboBox(); self.time.setEditable(True); self.time.addItems(times())
        self.time.setToolTip("Optional: when on that day the stage " + ("ends" if end else "starts") +
                             ". Without one it " + ("ends at the end of the day." if end else "starts at the start of the day."))
        self.time.currentTextChanged.connect(lambda _t: self.changed.emit())
        h.addWidget(self.time, 2)
        self._date = None
        self.set_value(date_iso, hm)

    def set_value(self, date_iso="", hm=""):
        self._date = R.parse_date(date_iso) if date_iso else None
        self.time.setCurrentText(nice_hm(hm) if hm else ANY)
        self._show()

    def set_date(self, d):
        self._date = d
        self._show()
        self.changed.emit()

    def _show(self):
        d = self._date
        self.btn.setText(f"{d.strftime('%b')} {d.day}, {d.year}" if d else "Not set")
        self.btn.setStyleSheet("" if d else f"color:{D.tokens()['muted']};font-style:italic;")
        self.time.setEnabled(d is not None)

    def pick(self, run=True):
        m = QMenu(self)
        cal = QCalendarWidget(); cal.setGridVisible(False)
        d = self._date or datetime.date.today()
        cal.setSelectedDate(QDate(d.year, d.month, d.day))
        wa = QWidgetAction(m); wa.setDefaultWidget(cal); m.addAction(wa)
        cal.clicked.connect(lambda q: (self.set_date(datetime.date(q.year(), q.month(), q.day())), m.close()))
        m.addSeparator()
        m.addAction("Clear the date", lambda: self.set_date(None))
        self.menu = m
        if run:
            m.exec(self.btn.mapToGlobal(self.btn.rect().bottomLeft()))
        return m

    def value(self):
        """(YYYY-MM-DD or '', HH:MM or ''); the time is None when it was typed and not understood."""
        if self._date is None:
            return "", ""
        return self._date.isoformat(), parse_hm(self.time.currentText())


def gate_box(gate=""):
    cb = QComboBox()
    for k, text in R.GATES.items():
        cb.addItem(text, k)
        about = R.GATE_ABOUT.get(k, "")
        if about:
            cb.setItemData(cb.count() - 1, about, Qt.ToolTipRole)
    cb.setCurrentIndex(max(0, cb.findData(gate)))
    return cb


def stage_table():
    t = QTableWidget(0, 4); t.setHorizontalHeaderLabels(["Stage", "Starts", "Ends", "Gate"])
    t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    hh = t.horizontalHeader()
    for i, w in enumerate((190, 250, 250, 240)):
        t.setColumnWidth(i, w)
        hh.setSectionResizeMode(i, QHeaderView.Interactive)
    hh.setSectionResizeMode(3, QHeaderView.Stretch)            # the gate takes what is left; the name stays readable
    t.verticalHeader().setDefaultSectionSize(36)
    t.setProperty("sk_rows_fixed", True)
    return t


class StageTableMixin:
    """Needs self.stage_table, self.rec (an effort record), self.host and self.refresh()."""

    def fill_stages(self, r):
        t = self.stage_table
        clear_table(t)
        for s in r.stages:
            self._stage_row(s["id"], s["name"], (s.get("planned", ""), s.get("planned_time", "")),
                            (s.get("planned_end", ""), s.get("planned_end_time", "")), r.gate_id(s), s["id"] == r.data["stage"])

    def _stage_row(self, sid, name, start, end, gate, current=False, at=None):
        """start and end: (YYYY-MM-DD or '', HH:MM or '')."""
        t = self.stage_table
        i = t.rowCount() if at is None else at
        t.insertRow(i)
        it = QTableWidgetItem(name); it.setData(Qt.UserRole, sid)
        it.setToolTip("Double-click to rename" + (". The current stage" if current else ""))
        it.setData(Qt.UserRole + 1, bool(current))
        if current:
            it.setForeground(D.color("accent"))
            f = it.font(); f.setBold(True); it.setFont(f)
        t.setItem(i, 0, it)
        for c, (d, hm) in ((1, start), (2, end)):
            t.setCellWidget(i, c, WhenCell(d, hm, end=(c == 2)))
        t.setCellWidget(i, 3, gate_box(gate))
        return i

    def _is_current(self, i):
        it = self.stage_table.item(i, 0)
        return bool(it and it.data(Qt.UserRole + 1))

    def _stage_values(self, i):
        t = self.stage_table
        it = t.item(i, 0)
        return (it.data(Qt.UserRole) if it else None, it.text() if it else "", t.cellWidget(i, 1).value(),
                t.cellWidget(i, 2).value(), t.cellWidget(i, 3).currentData())

    def move_row(self, d):
        t = self.stage_table
        i = t.currentRow()
        j = i + d
        if i < 0 or not (0 <= j < t.rowCount()):
            return False
        vals = self._stage_values(i)
        cur = self._is_current(i)
        for c in (1, 2, 3):
            t.cellWidget(i, c).hide()
        t.removeRow(i)
        self._stage_row(vals[0], vals[1], tuple(x or "" for x in vals[2]), tuple(x or "" for x in vals[3]), vals[4], cur, at=j)
        t.setCurrentCell(j, 0)
        return True

    def add_stage(self, name="New stage"):
        i = self._stage_row(None, name, ("", ""), ("", ""), R.DEFAULT_STAGE_GATES.get(name, ""))
        self.stage_table.setCurrentCell(i, 0)
        return i

    def remove_stage(self):
        t = self.stage_table
        i = t.currentRow()
        if i < 0:
            return False
        if self._is_current(i):
            self.host.status("The current stage cannot be removed.")
            return False
        for c in (1, 2, 3):
            t.cellWidget(i, c).hide()
        t.removeRow(i)
        return True

    def stage_problems(self):
        """Why the table cannot be saved ([] when it can): a time not understood, or a stage that ends before it starts."""
        out = []
        for i in range(self.stage_table.rowCount()):
            _sid, name, (ds, ts), (de, te), _g = self._stage_values(i)
            if ts is None or te is None:
                out.append(f"{name}: the time was not understood (write it like 8:00 AM)")
                continue
            if ds and de:
                a = datetime.datetime.fromisoformat(f"{ds}T{ts or '00:00'}")
                b = datetime.datetime.fromisoformat(f"{de}T{te or '23:59'}")
                if b < a:
                    out.append(f"{name} ends before it starts")
        return out

    def save_stages(self):
        r = self.rec
        bad = self.stage_problems()
        if bad:
            self.host.status("Not saved: " + "; ".join(bad) + ".")
            return False
        rows, gates = [], []
        for i in range(self.stage_table.rowCount()):
            sid, name, (ds, ts), (de, te), gate = self._stage_values(i)
            rows.append((sid, name, ds, de, ts if ds else "", te if de else ""))
            gates.append(gate)
        try:
            new = r.edit_stages(rows)
        except ValueError as e:
            self.host.status(str(e))
            return False
        for s, g in zip(new, gates):
            r.set_gate(s["id"], g)
        outside = R.Record(r.root).deadlines_outside() if hasattr(r, "root") else []
        diag.activity("qt_stages_saved")
        self.host.toast("Stages saved")
        if outside:
            self.host.status(f"{len(outside)} deadline(s) now fall outside their stage's dates: "
                             + "; ".join(f"{x['stage']}: {x['text'][:40]}" for x in outside[:3]) + ".")
        self.refresh()
        return True


class StagesDialog(StageTableMixin, QDialog):
    """Effort Home > Edit stages...: rename, add, remove and reorder the effort's stages, with their dates, times and
    gates. Nothing changes until Save."""

    def __init__(self, page):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.setWindowTitle(f"Stages of {self.host.effort_name}")
        self.resize(1000, 480)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Double-click a stage's name to rename it. Click a date to pick it from a calendar; the time is "
                            "optional. The current stage cannot be removed. The gate choices are set in Settings > Stages, "
                            "gates and roles.", "muted"))
        self.stage_table = stage_table(); v.addWidget(self.stage_table, 1)
        row = QHBoxLayout(); v.addLayout(row)
        for text, fn in (("Up", lambda: self.move_row(-1)), ("Down", lambda: self.move_row(1)), ("+ Stage", lambda: self.add_stage()),
                         ("Remove", lambda: self.remove_stage())):
            row.addWidget(D.button(text, None if text != "Remove" else "ghost", fn))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.saved = False
        self.fill_stages(self.rec)

    @property
    def rec(self):
        return R.Record(self.host.ws.root)

    def refresh(self):
        pass

    def save(self):
        if self.save_stages():
            self.saved = True
            self.accept()
            return True
        return False


class DeadlineRow(QWidget):
    """2.93.0: a deadline for a gate goal or a task: 'Deadline' ticked, a date from a calendar, an optional time. The
    stage's dates show under it, and a deadline outside them is refused by the record with the reason."""
    changed = Signal()

    def __init__(self, due="", label="Deadline"):
        super().__init__()
        from PySide6.QtWidgets import QCheckBox, QDateEdit
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)
        self.has = QCheckBox(label); h.addWidget(self.has)
        self.date = QDateEdit(); self.date.setCalendarPopup(True); self.date.setDisplayFormat("MMM d, yyyy"); h.addWidget(self.date, 2)
        self.time = QComboBox(); self.time.setEditable(True); self.time.addItems(times()); h.addWidget(self.time, 1)
        self.time.setToolTip("Optional. Without a time the deadline is the end of that day.")
        w = R.parse_when(due) if due else None
        self.has.setChecked(w is not None)
        d = w.date() if w else (datetime.date.today() + datetime.timedelta(days=7))
        self.date.setDate(QDate(d.year, d.month, d.day))
        self.time.setCurrentText(nice_hm(due[11:16]) if w and "T" in due else ANY)
        for x in (self.date, self.time):
            x.setEnabled(w is not None)
        self.has.toggled.connect(lambda on: (self.date.setEnabled(on), self.time.setEnabled(on), self.changed.emit()))
        self.date.dateChanged.connect(lambda _d: (self.has.setChecked(True), self.changed.emit()))   # picking a date sets it
        self.time.currentTextChanged.connect(lambda _t: self.changed.emit())

    def set_value(self, due):
        w = R.parse_when(due) if due else None
        self.has.setChecked(w is not None)
        if w:
            self.date.setDate(QDate(w.year, w.month, w.day))
            self.time.setCurrentText(nice_hm(due[11:16]) if "T" in due else ANY)

    def value(self):
        """'' (none), 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM', or None when the time was not understood."""
        if not self.has.isChecked():
            return ""
        hm = parse_hm(self.time.currentText())
        if hm is None:
            return None
        d = self.date.date().toPython().isoformat()
        return f"{d}T{hm}" if hm else d


def window_hint(r, sid):
    """'Red team runs Nov 18, 8:00 a.m. to Nov 21, 5:00 p.m.' or a nudge to set the stage's dates."""
    s = r.stage(sid)
    if s is None:
        return ""
    w = r.window_text(s)
    return (f"{s['name']} runs {w}. A deadline has to fall inside it." if w else
            f"{s['name']} has no dates yet, so any deadline is accepted. Set them in Edit stages... to keep deadlines inside it.")
