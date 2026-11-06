"""Setup > Outline layouts... (3.73.0): an outline's layout set ahead of time, with no workbook needed, in the import's
words: Column headings (each heading the workbook may use and what that column is, a column to leave out among them) and
Text by its look (text in a color word or hex color, italic or bold, is that kind; in any column of text or one kind),
each with a sample in its look. outlinelayouts holds the rules."""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                               QLineEdit, QTableWidget, QVBoxLayout)
import diag
import outlinelayouts as OL
import outlinexl as OX
from . import design as D

TRI = (("any", None), ("yes", True), ("no", False))
WORD_HEX = {"black": "auto", "gray": "808080", "red": "C00000", "orange": "E36C09", "yellow": "BF9000", "green": "00B050",
            "blue": "0070C0", "purple": "7030A0"}            # a sample's color for a color word


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
        # 3.73.0 (decision 10): in the import's words. Each heading and what its column is; text by its look and what it is.
        v.addWidget(D.SectionTitle("Column headings"))
        v.addWidget(D.label("A heading the workbook may use, and what that column is. Add another name for the same kind of "
                            "column on a row of its own.", "muted"))
        self.heads = QTableWidget(0, 3); self.heads.setHorizontalHeaderLabels(["Heading", "The column is", ""])
        self.heads.verticalHeader().setVisible(False); self.heads.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.heads.setColumnWidth(1, 230); self.heads.setColumnWidth(2, 80)
        v.addWidget(self.heads, 1)
        v.addWidget(D.button("Add a heading", None, lambda: self.add_heading()), 0, Qt.AlignLeft)
        v.addWidget(D.SectionTitle("Text by its look"))
        v.addWidget(D.label("In a column whose cells mix kinds of text: text that looks like this is that kind. Leave italic or "
                            "bold at any to match either.", "muted"))
        self.rules = QTableWidget(0, 7)
        self.rules.setHorizontalHeaderLabels(["In", "Color", "Italic", "Bold", "Sample", "It is", ""])
        self.rules.verticalHeader().setVisible(False); self.rules.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        for c, wd in ((0, 240), (1, 110), (2, 64), (3, 64), (5, 210), (6, 76)):
            self.rules.setColumnWidth(c, wd)
        self.rules.horizontalHeaderItem(1).setToolTip("A color word (red, purple), black, or a hex color such as 6B21A8")
        v.addWidget(self.rules, 1)
        v.addWidget(D.button("Add a look", None, lambda: self.add_rule()), 0, Qt.AlignLeft)
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
        self.layouts.setdefault(name, OL.new_layout())
        self.fill_pick(name)
        return name

    # ------------------------------------------------------------ one layout
    def show_layout(self, name):
        self.cur = name
        lay = self.layouts.get(name) or {"names": {}, "skip": [], "rules": {}}
        self.heads.setRowCount(0)
        for role, _t in OX.ROLES:
            for h in ((lay.get("names") or {}).get(role) or []) if role != "ignore" else (lay.get("skip") or []):
                self.add_heading(h, role)
        self.rules.setRowCount(0)
        for role, rs in (lay.get("rules") or {}).items():
            for r in rs:
                self.add_rule(role, r)

    def add_heading(self, heading="", role="requirement"):
        i = self.heads.rowCount(); self.heads.insertRow(i)
        e = QLineEdit(heading); e.setPlaceholderText("Compliance Requirement")
        cb = QComboBox()
        for k, t in OX.ROLES:
            cb.addItem(t, k)
        cb.setCurrentIndex(max(0, cb.findData(role)))
        rm = D.button("Remove", "ghost", lambda _=False, w=e: self.heads.removeRow(next(
            (j for j in range(self.heads.rowCount()) if self.heads.cellWidget(j, 0) is w), -1)))
        for c, w in enumerate((e, cb, rm)):
            self.heads.setCellWidget(i, c, w)
        return i

    def add_rule(self, role=OL.ANY, r=None):
        r = r or {"color": "red", "italic": None, "bold": None, "kind": "rfp"}
        i = self.rules.rowCount(); self.rules.insertRow(i)
        col = QComboBox()
        col.addItem("Any column of text", OL.ANY)
        for k in OL.MIXED:
            col.addItem(dict(OX.ROLES)[k] + " columns", k)
        col.setCurrentIndex(max(0, col.findData(role)))
        color = QComboBox(); color.setEditable(True)
        color.addItems(["black"] + [w for w in OX.COLOR_WORDS if w != "black"])
        c0 = str(r.get("color") or "auto")
        color.setCurrentText("black" if c0.lower() in ("auto", "000000") else c0)
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
        for c, w in enumerate((col, color, ital, bold, sample, kind, rm)):
            self.rules.setCellWidget(i, c, w)
        for w in (ital, bold, col, kind):
            w.currentIndexChanged.connect(lambda _i, row=color: self.redraw(row))
        color.currentTextChanged.connect(lambda _t, row=color: self.redraw(row))
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
        c = r["color"]
        c = WORD_HEX.get(c.lower(), c) if c.lower() != "auto" else c
        lk = OL.look_key(c, r["italic"], r["bold"])
        self.rules.cellWidget(i, 4).setText(f'<span style="{run_css(lk)}">{html.escape("The Government requires...")}</span>')

    def rule(self, i):
        g = self.rules.cellWidget
        c = g(i, 1).currentText().strip().lstrip("#") or "auto"
        return {"color": "auto" if c.lower() in ("black", "auto", "000000") else c.lower() if c.lower() in OX.COLOR_WORDS else c.upper(),
                "italic": g(i, 2).currentData(), "bold": g(i, 3).currentData(), "kind": g(i, 5).currentData(), "_role": g(i, 0).currentData()}

    def values(self):
        names, skip = {}, []
        for i in range(self.heads.rowCount()):
            h, role = self.heads.cellWidget(i, 0).text().strip(), self.heads.cellWidget(i, 1).currentData()
            if h:
                (skip if role == "ignore" else names.setdefault(role, [])).append(h)
        rules = {}
        for i in range(self.rules.rowCount()):
            r = self.rule(i)
            rules.setdefault(r.pop("_role"), []).append(r)
        return {"names": names, "skip": skip, "rules": rules}

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
