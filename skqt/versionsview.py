"""New version of the outline (3.73.0): the comparison the person reviews before anything changes, and the version
history. Each change is one row: what kind, which section, what it was, what it is now. "Changed in both" (the app's
work and the new version disagree) waits for a pick: keep ours or use theirs; nothing is overwritten until then. Any other
change can be kept as ours too. Accept and update the effort brings the version in; Make the setup again and Changes for
authors take it from there. outlineversions holds the rules."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)
import diag
import outlineversions as OV
from . import design as D

class ChangesTable(QTableWidget):
    def __init__(self, changes, picks=True, on_change=None):
        super().__init__(0, 5 if picks else 4)
        self.changes, self.combos, self.on_change = changes, {}, on_change
        self.values = {c["i"]: (None if c["both"] else "theirs") for c in changes}
        self.setHorizontalHeaderLabels(["Change", "Section", "Was", "Now"] + (["Take"] if picks else []))
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().sectionResized.connect(lambda *_a: self.fit_rows())
        for c in (2, 3):
            self.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self.setColumnWidth(0, 190); self.setColumnWidth(1, 220)
        self.setWordWrap(True)
        self.fill(picks)

    def fill(self, picks, only_both=False):
        rows = [c for c in self.changes if c["both"] or not only_both]
        self.combos = {}
        self.setRowCount(len(rows))
        for r, c in enumerate(rows):
            kind = c["kind"] + (f" ({c['what']})" if c["kind"] == "Changed" else "") + ("  - changed in both" if c["both"] else "")
            self.setItem(r, 0, QTableWidgetItem(kind))
            self.setItem(r, 1, QTableWidgetItem(c["section"]))
            was = c["old"] + (f"\nIn the effort now: {c['ours']}" if c["both"] and c.get("ours") else "")
            self.setItem(r, 2, QTableWidgetItem(was))
            self.setItem(r, 3, QTableWidgetItem(c["new"]))
            if picks:
                cb = QComboBox()
                if c["both"]:
                    cb.addItem("Pick...", None)
                    cb.addItem("Keep ours", "ours"); cb.addItem("Use theirs", "theirs")
                elif c["kind"] in ("Column renamed", "Renumbered", "Renamed", "Section added", "Section removed", "Authors changed"):
                    cb.addItem("Take it", "theirs")
                else:
                    cb.addItem("Take it", "theirs"); cb.addItem("Keep ours", "ours")
                cb.setCurrentIndex(max(0, cb.findData(self.values.get(c["i"]))))
                self.combos[c["i"]] = cb
                cb.currentIndexChanged.connect(lambda _i, k=c["i"], w=cb: self.pick(k, w.currentData()))
                self.setCellWidget(r, 4, cb)
        self.fit_rows()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit_rows()

    def showEvent(self, e):
        super().showEvent(e)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.fit_rows)                 # after the app's table tuner has set the columns

    def fit_rows(self):
        """Each row as tall as its longest wrapped cell (Qt's own measure overshoots with stretched columns)."""
        import math
        fm = self.fontMetrics()
        line, avg = fm.lineSpacing(), max(1, fm.averageCharWidth())
        for r in range(self.rowCount()):
            lines = 1
            for c in range(min(4, self.columnCount())):
                it = self.item(r, c)
                if it is None:
                    continue
                per = max(8, (self.columnWidth(c) - 12) // avg)
                lines = max(lines, sum(max(1, math.ceil(len(p) / per)) for p in it.text().split("\n")))
            self.setRowHeight(r, lines * line + 12)

    def pick(self, i, val):
        self.values[i] = val
        if self.on_change is not None:
            self.on_change()

    def picks(self):
        return {i: v for i, v in self.values.items() if v is not None}

    def waiting(self):
        return [c for c in self.changes if c["both"] and self.values.get(c["i"]) is None]


class NewVersion(QDialog):
    def __init__(self, page, parsed, path, headers, layout):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.parsed, self.path, self.headers, self.layout = parsed, path, headers, layout
        M = page._M()
        self.cur = OV.current(M)
        self.changes = OV.compare(M, parsed, headers)
        self.setWindowTitle(f"New version of the outline: {os.path.basename(path)}")
        self.resize(1200, 760)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"Against version {self.cur['v']} ({self.cur['file']}, {self.cur['when']}). Nothing in the effort changes "
                            "until you accept. Rows are matched by RFP reference, then by wording; your work in the app is kept "
                            "unless you choose theirs.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        self.sum = D.label(OV.summary(self.changes), None); top.addWidget(self.sum, 1)
        self.only = QCheckBox("Only changed in both"); self.only.toggled.connect(lambda on: (self.table.fill(True, on), self.ready()))
        top.addWidget(self.only)
        self.table = ChangesTable(self.changes, on_change=lambda: self.ready())
        v.addWidget(self.table, 1)
        self.wait = D.label("", "muted"); v.addWidget(self.wait)
        bb = QDialogButtonBox()
        self.b_ok = bb.addButton("Accept and update the effort", QDialogButtonBox.AcceptRole)
        bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.ready()

    def ready(self):
        w = self.table.waiting()
        self.b_ok.setEnabled(not w)
        self.wait.setText(f"{len(w)} change(s) in both wait for your pick." if w else
                          ("Every change has its pick." if self.changes else "This version holds nothing new."))

    def apply(self):
        M = self.page._M()
        R = self.host.review
        if R is not None:
            R.snap()
        res = OV.accept(M, self.parsed, self.path, self.table.picks(), self.host.effort_path or "", self.headers, self.layout,
                        who=getattr(self.host, "my_name", None) or None)
        diag.activity("outline_version_accepted", n=len(res["changes"]))
        self.host.changed()
        try:
            self.host.assign_page.fill_tree()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.page.refresh()
        self.host.toast(f"Version {res['version']['v']} is in: {OV.summary(res['changes'])}. Make the setup again; Changes for "
                        "authors gives each person what changed in their sections.")
        return res


def new_version(page, parsed, path, headers, layout, accept=None):
    """accept (tests): True to take every change as set (picks from page.version_picks), False to only show it."""
    dlg = NewVersion(page, parsed, path, headers, layout)
    page.version_dialog = dlg
    if accept is None:
        return dlg.apply() if dlg.exec() == QDialog.Accepted else None
    if not accept:
        return None
    for i, val in (getattr(page, "version_picks", None) or {}).items():
        dlg.table.pick(i, val)
    return dlg.apply() if not dlg.table.waiting() else None


class History(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.host = page, page.host
        M = page._M()
        self.vs = OV.versions(M)
        self.setWindowTitle("Outline versions")
        self.resize(1100, 700)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Every version of the outline brought into this effort, kept in its Outline Versions folder.", "muted"))
        self.list = QTableWidget(len(self.vs), 4); self.list.setHorizontalHeaderLabels(["Version", "File", "Brought in", "Rows"])
        self.list.verticalHeader().setVisible(False); self.list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for r, x in enumerate(self.vs):
            for c, val in enumerate((f"v{x['v']}", x["file"], x["when"], str(len(x["rows"])))):
                self.list.setItem(r, c, QTableWidgetItem(val))
        self.list.setMaximumHeight(170)
        v.addWidget(self.list)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.label("Compare", None, wrap=False))
        self.a, self.b = QComboBox(), QComboBox()
        for x in self.vs:
            self.a.addItem(f"v{x['v']}", x["v"]); self.b.addItem(f"v{x['v']}", x["v"])
        self.a.setCurrentIndex(max(0, len(self.vs) - 2)); self.b.setCurrentIndex(max(0, len(self.vs) - 1))
        row.addWidget(self.a); row.addWidget(D.label("with", None, wrap=False)); row.addWidget(self.b)
        row.addWidget(D.button("Compare", None, lambda: self.compare()))
        row.addStretch(1)
        row.addWidget(D.button("Write the workbook back out...", "primary", lambda: self.write_back(),
                               "The next version of your workbook in its own layout, from the effort as it is now, with a Changes sheet"))
        self.sum = D.label("", "muted"); v.addWidget(self.sum)
        self.table = ChangesTable([], picks=False); v.addWidget(self.table, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); v.addWidget(bb)
        if len(self.vs) > 1:
            self.compare()

    def compare(self, a=None, b=None):
        va = next(x for x in self.vs if x["v"] == (a or self.a.currentData()))
        vb = next(x for x in self.vs if x["v"] == (b or self.b.currentData()))
        ch = OV.compare(self.page._M(), None, None, old=va, new_record=vb)
        self.table.changes = ch; self.table.values = {c["i"]: "theirs" for c in ch}; self.table.fill(False)
        self.sum.setText(f"v{va['v']} to v{vb['v']}: {OV.summary(ch)}")
        return ch

    def write_back(self, out=None):
        import outlinewrite as OW
        M = self.page._M()
        if out is None:
            last = self.vs[-1] if self.vs else None
            stem = os.path.splitext(last["file"])[0] if last else "Outline"
            start = os.path.join(os.path.dirname(self.host.out_path("exports")) if self.host.effort_path else "", f"{stem} (next).xlsx")
            out, _ = QFileDialog.getSaveFileName(self, "The next version of the workbook", start, "Excel (*.xlsx)")
            if not out:
                return None
        try:
            res = OW.write_back(M, out, self.host.config_dir, self.host.effort_path or "")
        except PermissionError:
            self.host.status("A file with that name is open in Excel: close it, then write again.")
            return None
        except ValueError as e:
            self.host.status(str(e))
            return None
        diag.activity("outline_written_back", n=res["rows"])
        self.host.toast(f"Written: {os.path.basename(out)}, {res['rows']} row(s), {res['changes']} change(s) on its Changes sheet")
        return res


def history(page, modal=True):
    dlg = History(page)
    page.history_dialog = dlg
    if modal:
        dlg.exec()
    else:
        dlg.show()
    return dlg
