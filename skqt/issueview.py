"""Issues and ideas (3.9.0): write down a bug, an improvement or an idea about a feature, from any page (Ctrl+Shift+I,
or Issue or idea in the top bar). Reports stay on this PC; Export... saves a text-only zip. A content guard keeps
document words out: a report that holds a word from the effort, its documents or the team's lists is not saved, and
the words to take out are shown here only."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QPlainTextEdit,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QAbstractItemView)
import diag
import issuelog as IL
from . import design as D

STATUSES = ["Open", "Done"]


def features():
    from .mainwin import RAIL, TABS, TITLES
    out = []
    for _g, items in RAIL:                          # 3.16.0: each menu item, then the tabs it holds
        for k, t in items:
            out.append(t)
            out += [TITLES[m][0] for m, _l in TABS.get(k, [])[1:] if TITLES.get(m, ("",))[0] not in out]
    return out + ["Make a .dotx template", "Import from a file", "Effort types and profiles", "Updates", "Speed", "Other"]


def current_page(host):
    try:
        from .mainwin import TITLES
        cur = host.stack.currentWidget()
        key = next((k for k, pg in host.pages.items() if pg is cur), "")
        if not key and cur is getattr(host, "notice_page", None) and cur.why:     # 3.13.0: the tool asked for
            key = cur.why.get("step", "")
            if key not in TITLES:
                return key, cur.card.title.text()
        return key, TITLES.get(key, ("", ""))[0]
    except Exception:  # noqa: BLE001
        return "", ""


class IssueDialog(QDialog):
    def __init__(self, host, feature=None):
        super().__init__(host)
        self.host = host
        self.setWindowTitle("Issues and ideas")
        self.setMinimumSize(900, 640)
        self.editing = None                      # path of the report being edited
        self.page_key, page_title = current_page(host)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Describe the feature, never document content: no document text, names, terms or file names. "
                            "Reports stay on this PC until you export them.", "muted"))
        f = QFormLayout()
        self.type = QComboBox(); self.type.addItems(IL.TYPES); f.addRow("Kind", self.type)
        self.feature = QComboBox(); self.feature.addItems(features()); self.feature.setEditable(False)
        want = feature or page_title
        i = self.feature.findText(want) if want else -1
        self.feature.setCurrentIndex(i if i >= 0 else self.feature.count() - 1)
        f.addRow("Feature", self.feature)
        self.importance = QComboBox(); self.importance.addItems(IL.IMPORTANCE); self.importance.setCurrentText("Medium")
        f.addRow("Importance", self.importance)
        self.title = QLineEdit(); self.title.setPlaceholderText("Short: what happens, or what you would like"); f.addRow("Title", self.title)
        self.text = QPlainTextEdit(); self.text.setPlaceholderText(
            "What you did, what you expected, what happened (steps, which button, which setting). For an idea: what it "
            "would let you do."); self.text.setMinimumHeight(140)
        f.addRow("Details", self.text)
        self.status = QComboBox(); self.status.addItems(STATUSES); f.addRow("Status", self.status)
        v.addLayout(f)
        self.msg = D.label("", "muted"); v.addWidget(self.msg)
        row = QHBoxLayout()
        row.addWidget(D.button("Save", "primary", lambda: self.save()))
        row.addWidget(D.button("New", None, lambda: self.clear()))
        row.addStretch(1)
        row.addWidget(D.button("Edit selected", None, lambda: self.edit_selected()))
        row.addWidget(D.button("Delete selected", "ghost", lambda: self.delete_selected()))
        row.addWidget(D.button("Export...", None, lambda: self.export()))
        v.addLayout(row)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Written", "Kind", "Feature", "Status", "Title"])
        self.table.verticalHeader().setVisible(False); self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(lambda _i: self.edit_selected())
        v.addWidget(self.table, 1)
        self.paths = []
        self.load()

    def guard(self):
        return IL.guard_for(self.host, getattr(self.host, "config_dir", None))

    def load(self):
        try:
            items = IL.reports()
        except IL.Blocked as e:
            self.msg.setText(str(e))
            for b in self.findChildren(type(D.button("x", None, None))):
                b.setEnabled(False)
            return
        self.paths = [p for p, _r in items]
        self.table.setRowCount(0)
        for p, r in reversed(items):
            k = self.table.rowCount(); self.table.insertRow(k)
            c = r.get("context") or {}
            for col, val in enumerate(((c.get("time") or "")[:16].replace("T", " "), r.get("type", ""), r.get("feature", ""),
                                       r.get("status", "Open"), r.get("title", ""))):
                it = QTableWidgetItem(val); it.setData(Qt.UserRole, p); self.table.setItem(k, col, it)

    def report(self):
        return {"type": self.type.currentText(), "feature": self.feature.currentText(), "importance": self.importance.currentText(),
                "title": self.title.text(), "text": self.text.toPlainText(), "status": self.status.currentText()}

    def save(self):
        r = self.report()
        if self.editing:
            try:
                old = next(x for p, x in IL.reports() if p == self.editing)
                r["context"] = old.get("context")
            except StopIteration:
                pass
        else:
            r["context"] = IL.context(self.page_key)
        try:
            path = IL.save(r, self.guard(), path=self.editing)
        except (ValueError, IL.Blocked) as e:
            self.msg.setText(str(e))
            return None
        self.msg.setText("Saved on this PC.")
        self.clear(keep_msg=True)
        self.load()
        return path

    def clear(self, keep_msg=False):
        self.editing = None
        self.title.clear(); self.text.clear(); self.status.setCurrentText("Open")
        if not keep_msg:
            self.msg.setText("")

    def selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 0).data(Qt.UserRole) for r in rows]

    def edit_selected(self):
        sel = self.selected()
        if not sel:
            return
        r = next((x for p, x in IL.reports() if p == sel[0]), None)
        if r is None:
            return
        self.editing = sel[0]
        self.type.setCurrentText(r.get("type", "Bug")); self.importance.setCurrentText(r.get("importance", "Medium"))
        i = self.feature.findText(r.get("feature", "")); self.feature.setCurrentIndex(i if i >= 0 else self.feature.count() - 1)
        self.title.setText(r.get("title", "")); self.text.setPlainText(r.get("text", "")); self.status.setCurrentText(r.get("status", "Open"))
        self.msg.setText("Editing a saved report. Save keeps the changes.")

    def delete_selected(self):
        for p in self.selected():
            try:
                IL.remove(p)
            except (OSError, ValueError, IL.Blocked):
                diag.swallowed()
        self.clear()
        self.load()

    def export(self, path=None):
        import datetime
        import app_gui
        if path is None:
            name = f"Stationkeeper issues and ideas {datetime.date.today().isoformat()}.zip"
            path, _ = QFileDialog.getSaveFileName(self, "Save the issues and ideas", os.path.join(os.path.expanduser("~"), name), "Zip (*.zip)")
            if not path:
                return 0
        sel = self.selected()
        try:
            n = IL.export(path, self.guard(), app_version=app_gui.APP_VERSION, only=set(sel) if len(sel) > 1 else None)
        except (ValueError, IL.Blocked, OSError) as e:
            self.msg.setText(str(e) if not isinstance(e, OSError) else f"Not saved ({type(e).__name__}).")
            return 0
        self.msg.setText(f"{n} report(s) saved to {os.path.basename(path)} (text only). Send it to whoever maintains Stationkeeper.")
        return n


def open_issues(host, feature=None, run=True):
    d = IssueDialog(host, feature)
    if run:
        d.exec()
    return d
