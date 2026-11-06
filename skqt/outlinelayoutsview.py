"""Setup > Outline layouts... (3.73.0): an outline's layout set ahead of time, with no workbook needed. For each kind
of column, the heading names it may carry (one per line); the columns to leave out; and the formatting rules for a column
whose cells mix kinds of text, by color, italic and bold, each with a sample in its look. outlinelayouts holds the rules."""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                               QLineEdit, QPlainTextEdit, QTableWidget, QVBoxLayout)
import diag
import outlinelayouts as OL
import outlinexl as OX
from . import design as D

TRI = (("any", None), ("yes", True), ("no", False))


class OutlineLayouts(QDialog):
    def __init__(self, page, name=None):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.cfg = self.host.config_dir
        self.setWindowTitle("Outline layouts")
        self.resize(1000, 720)
        self.layouts = OL.load(self.cfg)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Set an outline's layout before you have the workbook: the heading names each column may carry and "
                            "how mixed text is told apart. An import uses the layout that knows the most of its headings.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.label("Layout", None, wrap=False))
        self.pick = QComboBox(); self.pick.setMinimumWidth(260); top.addWidget(self.pick)
        self.pick.activated.connect(lambda _i: self.show_layout(self.pick.currentText()))
        top.addWidget(D.button("New layout...", None, lambda: self.new()))
        top.addStretch(1)
        form = QFormLayout(); v.addLayout(form)
        self.names = {}
        for role, title in OX.ROLES:
            if role == "ignore":
                continue
            e = QPlainTextEdit(); e.setFixedHeight(46); e.setPlaceholderText("One heading name per line")
            form.addRow(title, e); self.names[role] = e
        self.skip = QLineEdit(); self.skip.setPlaceholderText("Headings to leave out, separated by ;")
        form.addRow("Leave out", self.skip)
        v.addWidget(D.SectionTitle("Formatting rules for mixed columns"))
        self.rules = QTableWidget(0, 7)
        self.rules.setHorizontalHeaderLabels(["Column", "Color", "Italic", "Bold", "Setup style", "Sample", ""])
        self.rules.verticalHeader().setVisible(False); self.rules.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        for c, wd in ((0, 180), (1, 110), (2, 70), (3, 70), (4, 230), (6, 80)):
            self.rules.setColumnWidth(c, wd)
        self.rules.horizontalHeaderItem(1).setToolTip("A hex color such as 6B21A8, or auto for black")
        v.addWidget(self.rules, 1)
        v.addWidget(D.button("Add a rule", None, lambda: self.add_rule()), 0, Qt.AlignLeft)
        bb = QDialogButtonBox(); bb.addButton("Save", QDialogButtonBox.AcceptRole); bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(lambda: (self.save(), self.accept())); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.fill_pick(name)

    def fill_pick(self, name=None):
        self.pick.clear(); self.pick.addItems(list(self.layouts))
        name = name if name in self.layouts else (list(self.layouts)[0] if self.layouts else OL.STARTING)
        self.pick.setCurrentText(name)
        self.show_layout(name)

    def new(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New layout", "A name for this outline layout:")
            if not ok or not name.strip():
                return None
        name = " ".join(name.split())
        self.layouts.setdefault(name, {"names": {}, "skip": [], "rules": {}})
        self.fill_pick(name)
        return name

    # ------------------------------------------------------------ one layout
    def show_layout(self, name):
        self.cur = name
        lay = self.layouts.get(name) or {"names": {}, "skip": [], "rules": {}}
        for role, e in self.names.items():
            e.setPlainText("\n".join((lay.get("names") or {}).get(role) or []))
        self.skip.setText("; ".join(lay.get("skip") or []))
        self.rules.setRowCount(0)
        for role, rs in (lay.get("rules") or {}).items():
            for r in rs:
                self.add_rule(role, r)

    def add_rule(self, role="support", r=None):
        r = r or {"color": "auto", "italic": None, "bold": None, "kind": OX.DEFAULT_KIND.get(role, "support")}
        i = self.rules.rowCount(); self.rules.insertRow(i)
        col = QComboBox()
        for k in OL.MIXED:
            col.addItem(dict(OX.ROLES)[k], k)
        col.setCurrentIndex(max(0, col.findData(role)))
        color = QLineEdit(r.get("color") or "auto")
        ital, bold = QComboBox(), QComboBox()
        for cb, key in ((ital, "italic"), (bold, "bold")):
            for t, val in TRI:
                cb.addItem(t, val)
            cb.setCurrentIndex(next(j for j, (_t, val) in enumerate(TRI) if val == r.get(key)))
        kind = QComboBox()
        for k, t in OX.KINDS:
            kind.addItem(t, k)
        kind.setCurrentIndex(max(0, kind.findData(r.get("kind"))))
        sample = QLabel(); sample.setTextFormat(Qt.RichText)
        rm = D.button("Remove", "ghost", lambda _=False, w=color: self.remove_rule(w))
        for c, w in enumerate((col, color, ital, bold, kind, sample, rm)):
            self.rules.setCellWidget(i, c, w)
        for w in (ital, bold, col, kind):
            w.currentIndexChanged.connect(lambda _i, row=color: self.redraw(row))
        color.textChanged.connect(lambda _t, row=color: self.redraw(row))
        self.redraw(color)
        return i

    def _row_of(self, color_widget):
        return next((i for i in range(self.rules.rowCount()) if self.rules.cellWidget(i, 1) is color_widget), -1)

    def remove_rule(self, color_widget):
        i = self._row_of(color_widget)
        if i >= 0:
            self.rules.removeRow(i)

    def redraw(self, color_widget):
        i = self._row_of(color_widget)
        if i < 0:
            return
        r = self.rule(i)
        from .outlineimport import run_css
        lk = OL.look_key(r["color"], r["italic"], r["bold"])
        self.rules.cellWidget(i, 5).setText(f'<span style="{run_css(lk)}">{html.escape("The Government requires...")}</span>')

    def rule(self, i):
        g = self.rules.cellWidget
        return {"color": (g(i, 1).text().strip().lstrip("#") or "auto"), "italic": g(i, 2).currentData(), "bold": g(i, 3).currentData(),
                "kind": g(i, 4).currentData(), "_role": g(i, 0).currentData()}

    def values(self):
        names = {role: [x.strip() for x in e.toPlainText().splitlines() if x.strip()] for role, e in self.names.items()}
        rules = {}
        for i in range(self.rules.rowCount()):
            r = self.rule(i)
            rules.setdefault(r.pop("_role"), []).append(r)
        return {"names": {k: v for k, v in names.items() if v}, "skip": [x.strip() for x in self.skip.text().split(";") if x.strip()],
                "rules": rules}

    def save(self):
        lay = self.values()
        OL.put(self.cfg, self.cur, lay)
        self.layouts = OL.load(self.cfg)
        diag.activity("outline_layout_saved")
        self.host.toast(f"Outline layout saved: {self.cur}")
        return lay


def edit(page, name=None, modal=True):
    dlg = OutlineLayouts(page, name)
    page.layouts_dialog = dlg
    if modal:
        dlg.exec()
    else:
        dlg.show()
    return dlg
