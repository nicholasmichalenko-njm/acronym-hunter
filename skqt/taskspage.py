"""Tasks (4.27.1; Nicholas 2026-11-12, answer 2: "Tasks and Calendar are menu entries"; the recording 07:05 to 07:55).
One page, two views. This effort: its tasks by gate, late ones first, with Add a task... and the status on the row.
Mine, across efforts: one person's items in every effort on this PC, in Late, Today, This week, Later (the work My Work
did, set aside in 3.57.0; its code and data are the same). Tasks are kept in the effort record, as before.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
                               QLineEdit, QMenu, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import worklists as WL
from . import design as D
from .commandbar import CommandBar

VIEWS = (("effort", "This effort"), ("mine", "Mine, across efforts"))
COLS = {"effort": ["Task", "Owner", "Due", "About", "Status"], "mine": ["Due", "Effort", "What", "Item", "Where"]}


class TasksPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        self.view = "effort"
        self.rows = []                      # one per table row: a task, a mine row, or None for a group line
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.bar.primary("Add a task...", lambda: self.add(), "A task in this effort: what, who, by when")
        v.addWidget(self.bar)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        self.view_btns = {}
        for k, n in VIEWS:
            b = D.button(n, None, None, {"effort": "This effort's tasks, by gate", "mine": "One person's items in every effort on this PC"}[k])
            b.setCheckable(True); b.setChecked(k == self.view)
            b.clicked.connect(lambda _c=False, k=k: self.set_view(k))
            row.addWidget(b); self.view_btns[k] = b
        self.who = QComboBox(); self.who.setMinimumWidth(180); self.who.setEditable(False)
        self.who.setToolTip("Whose items to show across efforts")
        self.who.activated.connect(lambda _i: self.fill())
        row.addWidget(self.who)
        row.addStretch(1)
        self.count = D.label("", "muted", wrap=False); row.addWidget(self.count)
        v.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.menu)
        self.table.doubleClicked.connect(lambda _ix: self.open_row())
        v.addWidget(self.table, 1)
        self.empty = D.EmptyState("No tasks yet", "A task is something one person does by a date: a data call to chase, a section "
                                  "to send back, a form to sign.", "Add a task...", lambda: self.add())
        v.addWidget(self.empty, 1)

    # ------------------------------------------------------------------ the data
    def rec(self):
        import effortrec as RR
        return RR.Record(self.host.ws.root) if self.host.ws is not None else None

    def person(self):
        return self.who.currentText().strip() if self.who.count() else ""

    def _people(self):
        """The team's names (the author list), with yours first when it is set (Customize Home > I am)."""
        from .modes import settings
        h = self.host
        names = list(h.authors.names()) if getattr(h, "authors", None) is not None else []
        me = (settings() or {}).get("my_name", "")
        if me and me not in names:
            names.insert(0, me)
        return names, me

    def set_view(self, k):
        self.view = k if k in dict(VIEWS) else "effort"
        for key, b in self.view_btns.items():
            b.blockSignals(True); b.setChecked(key == self.view); b.blockSignals(False)
        diag.activity("tasks_view")
        return self.fill()

    def refresh(self):
        keep = self.person()
        names, me = self._people()
        self.who.blockSignals(True)
        self.who.clear(); self.who.addItems(names)
        self.who.setCurrentIndex(max(0, self.who.findText(keep or me)))
        self.who.blockSignals(False)
        return self.fill()

    def fill(self):
        h = self.host
        t = self.table
        self.who.setVisible(self.view == "mine")
        cols = COLS[self.view]
        t.setColumnCount(len(cols)); t.setHorizontalHeaderLabels(cols)
        hh = t.horizontalHeader()
        for c in range(len(cols)):
            hh.setSectionResizeMode(c, QHeaderView.Stretch if c == (0 if self.view == "effort" else 3) else QHeaderView.Interactive)
        t.clearSpans()
        self.rows = []
        groups = []
        if self.view == "effort":
            rec = self.rec()
            tasks = rec.tasks() if rec is not None else []
            groups = WL.task_groups(tasks, rec.stages if rec is not None else [], overdue=(rec.task_overdue if rec is not None else None))
            op, late, done = WL.task_counts(tasks, overdue=(rec.task_overdue if rec is not None else None))
            self.count.setText(f"{op} open" + (f", {late} late" if late else "") + (f", {done} done" if done else "") if tasks else "")
            on = h.ws is not None
        else:
            import mywork as MW
            p = self.person()
            work = []
            if p:
                names = [n for n in h.efforts.names() if not (h.efforts.get(n) or {}).get("archived")]
                try:
                    work = MW.collect(h.efforts, p, names=names)
                except Exception:  # noqa: BLE001
                    diag.swallowed()
            rows = MW.soonest(work)
            groups = WL.mine_groups(rows)
            late = sum(1 for r in rows if r.get("late"))
            self.count.setText((f"{p}: {len(rows)} item" + ("" if len(rows) == 1 else "s") + f" in {len(work)} effort" + ("" if len(work) == 1 else "s")
                                + (f", {late} late" if late else "")) if p else "Pick a name.")
            on = True
        n = sum(1 + len(g[1]) for g in groups)
        t.setRowCount(n)
        r = 0
        for name, items in groups:
            it = QTableWidgetItem(f"{name}   ·   {len(items)}")
            f = it.font(); f.setWeight(QFont.DemiBold); it.setFont(f); it.setFlags(Qt.ItemIsEnabled)
            it.setBackground(D.color("surface2"))
            if name == "Late":
                it.setForeground(D.color("crit"))
            t.setItem(r, 0, it)
            for c in range(1, len(cols)):
                x = QTableWidgetItem(""); x.setFlags(Qt.ItemIsEnabled); t.setItem(r, c, x)
            t.setSpan(r, 0, 1, len(cols))
            self.rows.append(None); r += 1
            for x in items:
                vals = self._effort_row(x) if self.view == "effort" else self._mine_row(x)
                for c, val in enumerate(vals):
                    ci = QTableWidgetItem(val)
                    if x.get("late"):
                        ci.setForeground(D.color("crit"))
                    elif self.view == "effort" and x.get("status") == "Done":
                        ci.setForeground(D.color("faint"))
                    t.setItem(r, c, ci)
                self.rows.append(x); r += 1
        has = bool(groups)
        self.empty.setVisible(self.view == "effort" and not has and on)
        t.setVisible(has or self.view == "mine")
        return n

    @staticmethod
    def _effort_row(t):
        return (t.get("title", ""), t.get("owner", "") or "No owner", (t.get("due", "") or "").replace("T", " ") + ("  LATE" if t.get("late") else ""),
                t.get("about", ""), t.get("status", ""))

    @staticmethod
    def _mine_row(r):
        import mywork as MW
        due = r.get("due_date")
        when = f"{due.strftime('%b')} {due.day}" if due else ""
        return (when + ("  LATE" if r.get("late") else ""), r.get("effort", ""), MW.KIND_WORDS.get(r.get("kind"), str(r.get("kind", ""))),
                r.get("text", ""), r.get("where", ""))

    def current(self):
        r = self.table.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def select(self, tid):
        for r, x in enumerate(self.rows):
            if x is not None and x.get("id") == tid:
                self.table.selectRow(r)
                return True
        return False

    # ------------------------------------------------------------------ what it does
    def add(self, answer=None):
        """A task in this effort. answer (tests): {"title", "owner", "due", "about"}. Returns its id, or None."""
        rec = self.rec()
        if rec is None:
            self.host.status("Open an effort first.")
            return None
        if answer is None:
            dlg = QDialog(self); dlg.setWindowTitle("Add a task"); dlg.setMinimumWidth(480)
            f = QFormLayout(dlg)
            title = QLineEdit(); owner = QLineEdit(); due = QLineEdit(); about = QLineEdit()
            due.setPlaceholderText("YYYY-MM-DD"); about.setPlaceholderText("A deliverable, a section, a gate")
            f.addRow("What", title); f.addRow("Who", owner); f.addRow("By when", due); f.addRow("About", about)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
            bb.button(QDialogButtonBox.Ok).setText("Add the task")
            f.addRow(bb)
            if dlg.exec() != QDialog.Accepted:
                return None
            answer = {"title": title.text(), "owner": owner.text(), "due": due.text(), "about": about.text()}
        tid = rec.add_task(answer.get("title", ""), owner=answer.get("owner", ""), due=answer.get("due", ""), about=answer.get("about", ""))
        if tid:
            diag.activity("task_added_on_tasks")
            self.set_view("effort")
            self.select(tid)
            self.host.changed() if hasattr(self.host, "changed") else None
        else:
            self.host.status("Say what the task is.")
        return tid

    def set_status(self, status, t=None):
        t = t or self.current()
        rec = self.rec()
        if t is None or rec is None or self.view != "effort":
            return False
        ok = rec.update_task(t["id"], status=status)
        self.fill(); self.select(t["id"])
        return ok

    def remove(self, t=None):
        t = t or self.current()
        rec = self.rec()
        if t is None or rec is None or self.view != "effort":
            return False
        ok = rec.remove_task(t["id"])
        self.fill()
        return ok

    def open_row(self, x=None):
        """Mine: open the item's effort. This effort: nothing to open (the task is the row)."""
        x = x or self.current()
        if x is None or self.view != "mine":
            return False
        return self.host.mywork_page.open_effort(x["effort"], "overview")

    def menu(self, pos):
        x = self.current()
        if x is None:
            return None
        m = QMenu(self)
        if self.view == "effort":
            import effortrec as RR
            for s in RR.TASK_STATUS:
                a = m.addAction(s, lambda s=s: self.set_status(s)); a.setCheckable(True); a.setChecked(x.get("status") == s)
            m.addSeparator()
            m.addAction("Remove the task", lambda: self.remove())
        else:
            m.addAction(f"Open {x.get('effort', 'the effort')}", lambda: self.open_row())
        if pos is not None:
            m.exec(self.table.viewport().mapToGlobal(pos))
        return m
