"""Home > My Work (3.1.0): one person's work in every effort on this PC, soonest first: tasks, questions for them,
customer questions, deliverables and graphic needs they own, the requirements they answer (due when the current stage
ends), and the sections they lead or write with their page budgets. Pick any name on the author list. Double-click a row
to open that effort at the right page. Read only; the efforts are read in the background."""
import datetime
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import mywork as MW
from . import design as D

GO = {"task": "home", "question": "home", "graphic": "home", "custqa": "custqa", "deliverable": "deliverables", "requirements": "assign"}


class Loader(QThread):
    done = Signal(object)

    def __init__(self, registry, person, names):
        super().__init__()
        self.registry, self.person, self.names = registry, person, names

    def run(self):
        try:
            self.done.emit(MW.collect(self.registry, self.person, names=self.names))
        except Exception:
            diag.swallowed()
            self.done.emit([])


class MyWorkPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.work, self.rows, self.loader = [], [], None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
        v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.label("Work for", "label", wrap=False))
        self.who = QComboBox(); self.who.setMinimumWidth(220); self.who.activated.connect(lambda _i: self.load())
        top.addWidget(self.who)
        top.addWidget(D.button("Refresh", None, lambda: self.load(), "Read every effort again"))
        top.addStretch(1)
        top.addWidget(D.button("Export...", None, lambda: self.export(), "A workbook of this person's work, soonest first"))
        self.summary = D.label("", None); self.summary.setTextFormat(Qt.RichText); v.addWidget(self.summary)
        self.list_card = D.Card("Soonest first", "Late items first, then by due date; double-click one to open it in its effort.")
        t = QTableWidget(0, 5); t.setHorizontalHeaderLabels(["Due", "Effort", "What", "Item", "Where"])
        t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for i, w in ((0, 130), (1, 170), (2, 150), (4, 200)):
            t.setColumnWidth(i, w)
        t.setMinimumHeight(320); t.setWordWrap(True)
        t.cellDoubleClicked.connect(lambda r, _c: self.open_row(r))
        self.table = t; self.list_card.add(t)
        v.addWidget(self.list_card)
        self.eff_card = D.Card("By effort", "Where each effort stands, and the sections this person leads or writes with their page budgets.")
        self.eff_box = QVBoxLayout(); self.eff_box.setSpacing(D.SPACE["s"]); self.eff_card.body.addLayout(self.eff_box)
        v.addWidget(self.eff_card)
        v.addStretch(1)

    # ------------------------------------------------------------ state
    def person(self):
        return self.who.currentText().strip()

    def refresh(self):
        from .modes import settings
        names = list(self.host.authors.names()) if getattr(self.host, "authors", None) is not None else []
        cur = self.person() or (settings() or {}).get("my_name", "")
        if cur and cur not in names:
            names.insert(0, cur)
        self.who.blockSignals(True); self.who.clear(); self.who.addItems(names)
        if cur:
            self.who.setCurrentText(cur)
        self.who.blockSignals(False)
        self.load()

    def load(self, wait=False):
        p = self.person()
        if not p:
            self.show([])
            self.summary.setText("Pick a name. Customize Home > I am sets yours, so My work opens on it.")
            return None
        if self.host.ws is not None and self.host.review is not None and self.host.review.M.pending:
            self.host.save_now()                      # the open effort as it stands now
        self.summary.setText(f"Reading every effort for {p}...")
        names = [n for n in self.host.efforts.names() if not (self.host.efforts.get(n) or {}).get("archived")]
        if wait or __import__("os").environ.get("AH_TEST"):
            got = MW.collect(self.host.efforts, p, names=names)
            self.show(got)
            return got
        self.loader = Loader(self.host.efforts, p, names)
        self.loader.done.connect(self.show)
        self.loader.start()
        return None

    def show(self, work):
        self.work = work or []
        self.rows = MW.soonest(self.work)
        t, tok = self.table, D.tokens()
        t.setRowCount(0)
        for r in self.rows:
            k = t.rowCount(); t.insertRow(k)
            due = r["due_date"]
            when = (f"{due.strftime('%b')} {due.day}" + ("" if due.hour == 23 and due.minute == 59 else
                    f", {due.hour % 12 or 12}:{due.minute:02d} {'a.m.' if due.hour < 12 else 'p.m.'}")) if due else ""
            for c, text in enumerate((when + ("  LATE" if r["late"] else ""), r["effort"], MW.KIND_WORDS.get(r["kind"], r["kind"]),
                                      r["text"], r["where"])):
                it = QTableWidgetItem(text)
                if r["late"]:
                    it.setForeground(D.color("crit"))
                t.setItem(k, c, it)
        t.resizeRowsToContents()
        p = self.person()
        late = sum(1 for r in self.rows if r["late"])
        self.summary.setText(f"<b>{p}</b>: {len(self.rows)} item{'s' if len(self.rows) != 1 else ''} in {len(self.work)} "
                             f"effort{'s' if len(self.work) != 1 else ''}" + (f", <span style='color:{tok['crit']}'><b>{late} late</b></span>" if late else "")
                             + "." if p else "")
        while self.eff_box.count():
            x = self.eff_box.takeAt(0)
            if x.widget() is not None:
                x.widget().deleteLater()
        if not self.work:
            self.eff_box.addWidget(D.label(f"Nothing assigned to {p} in any effort on this PC." if p else "", "muted"))
        import effortrec as R
        for w in self.work:
            due = R.parse_when(w.get("due", ""))
            head = f"<b>{w['effort']}</b>  ·  {w['stage'] or 'no stage'}" + (f"  ·  due {due.strftime('%b')} {due.day}, {due.year}" if due else "")
            lab = D.label(head, None); lab.setTextFormat(Qt.RichText); self.eff_box.addWidget(lab)
            parts = []
            if w["sections"]:
                parts.append("Sections: " + "; ".join(f"{x['label']} ({x['role']}" + (f", {_pages(x['pages'])}" if x["pages"] else "") + ")"
                                                      for x in w["sections"]))
            if w["reqs"]:
                parts.append(f"{w['reqs']} requirement(s)" + (f", {w['awaiting']} changed by a customer version" if w["awaiting"] else ""))
            counts = {}
            for it in w["items"]:
                if it["kind"] != "requirements":
                    counts[it["kind"]] = counts.get(it["kind"], 0) + 1
            parts += [f"{n} {MW.KIND_WORDS[k].lower()}{'s' if n != 1 else ''}" for k, n in counts.items()]
            row = QHBoxLayout()
            row.addWidget(D.label("  ·  ".join(parts) or "Nothing open.", "muted"), 1)
            row.addWidget(D.button("Open", "ghost", lambda _=False, n=w["effort"]: self.open_effort(n)), 0, Qt.AlignTop)
            self.eff_box.addLayout(row)
        diag.activity("mywork_shown", n=len(self.rows))
        return self.rows

    # ------------------------------------------------------------ actions
    def open_effort(self, name, page="home"):
        h = self.host
        if h.effort_name != name or h.ws is None:
            if not h.open_effort(name):
                return False
        h.go(page if page in h.pages else "home")
        return True

    def open_row(self, r):
        if not (0 <= r < len(self.rows)):
            return False
        row = self.rows[r]
        return self.open_effort(row["effort"], GO.get(row["kind"], "home"))

    def export(self, path=None):
        p = self.person()
        if not p:
            return ""
        if path is None:
            import re
            name = f"My_Work_{re.sub(r'[^A-Za-z0-9]+', '_', p).strip('_')}_{datetime.date.today().isoformat()}.xlsx"
            path, _ = QFileDialog.getSaveFileName(self, "Export my work", name, "Excel (*.xlsx)")
            if not path:
                return ""
        MW.export_excel(path, p, self.work)
        diag.activity("mywork_exported", n=len(self.rows))
        self.host.toast(f"Work for {p} exported")
        return path


def _pages(n):
    import pagebudget as PB
    return f"{PB.fmt(n)} page{'s' if n != 1 else ''}"
