"""Build a header or footer as a table (3.42.0): its columns at inch widths, each with lines of words and fields (each
line its own alignment, size and bold) and a logo; a rule above or below, or a grid. Use Rule 7's footer puts the A
number on the left, the marking and the team's standard line in the middle, and the page number on the right. Save as
a Quick Part keeps what is built as a Quick Part in the standard (Make templates puts it in every template).
The layout is kept in std["hf_layouts"][part][kind]["table"]["cells"] (hfbuild.py)."""
import copy

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QListWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

import hfbuild as HB
from . import design as D

ALIGNS = [("left", "Left"), ("center", "Center"), ("right", "Right")]
BORDERS = [("none", "None"), ("below", "A line under"), ("above", "A line over"), ("grid", "Grid")]
TOKENS = "{volume_name} {solicitation} {company} {page} {pages} {chapter} {a_number} {marking}"


class CellsPreview(QWidget):
    """The row of cells as it will sit across the text width: each cell's lines in place, the logo as a box."""
    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.setMinimumHeight(90)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#ffffff"))
        draw_cells(p, QRectF(8, 8, self.width() - 16, self.height() - 16), self.dlg.spec, self.dlg.work, self.dlg.selected())
        p.end()


def draw_cells(p, band, spec, work=None, selected=-1, text_width_in=6.5):
    """Draw a cells table into band (used by the builder and by the Document parts preview)."""
    t = (spec or {}).get("table") or {}
    cells = t.get("cells") or []
    if not cells:
        return
    widths = [float(c.get("width_in") or 0) for c in cells]
    free = max(0.0, text_width_in - sum(widths))
    blanks = sum(1 for w in widths if not w) or 1
    widths = [w or free / blanks for w in widths]
    total = sum(widths) or 1.0
    scale = band.width() / max(total, text_width_in)
    small = QFont(); small.setPointSizeF(7)
    var = (work or {}).get("variables") or {}
    x = band.left()
    for k, (c, w) in enumerate(zip(cells, widths)):
        cell = QRectF(x, band.top(), w * scale, band.height())
        p.setPen(QPen(QColor("#0f766e") if k == selected else QColor("#9aa3b2"), 1.4 if k == selected else 0.8, Qt.DotLine))
        p.drawRect(cell)
        y = cell.top() + 2
        logo = c.get("logo") or {}
        if logo.get("b64"):
            lw, lh = min(cell.width() - 4, float(logo.get("w_in") or 1) * scale), float(logo.get("h_in") or 0.5) * scale
            al = logo.get("align") or "left"
            lx = cell.left() + 2 if al == "left" else (cell.right() - 2 - lw if al == "right" else cell.center().x() - lw / 2)
            p.setPen(QPen(QColor("#64748b"), 0.8)); p.drawRect(QRectF(lx, y, lw, min(lh, cell.height() / 2)))
            p.drawText(QRectF(lx, y, lw, min(lh, cell.height() / 2)), Qt.AlignCenter, "logo")
            y += min(lh, cell.height() / 2) + 2
        for ln in c.get("lines") or []:
            f = QFont(small); f.setBold(bool(ln.get("bold")))
            if ln.get("size"):
                f.setPointSizeF(max(5.0, float(ln["size"]) * 0.7))
            p.setFont(f); p.setPen(QColor("#1f2937"))
            al = {"left": Qt.AlignLeft, "center": Qt.AlignHCenter, "right": Qt.AlignRight}.get(ln.get("align"), Qt.AlignLeft)
            txt = shown(ln.get("text") or "", var)
            r = QRectF(cell.left() + 3, y, cell.width() - 6, 14)
            p.drawText(r, al | Qt.AlignTop, p.fontMetrics().elidedText(txt, Qt.ElideRight, int(r.width())))
            y += 13
        x += w * scale
    p.setPen(QPen(QColor("#1f2937"), 1))
    b = t.get("borders") or "none"
    if b in ("below", "grid"):
        p.drawLine(band.bottomLeft(), band.bottomRight())
    if b in ("above", "grid"):
        p.drawLine(band.topLeft(), band.topRight())


def shown(text, var):
    """A line's words with its tokens as they read on the page."""
    out = text
    for k, v in (("{page}", "1"), ("{pages}", "12"), ("{a_number}", "A-number"), ("{chapter}", "Chapter title")):
        out = out.replace(k, v)
    tl = str((var or {}).get("team_line") or "")
    out = out.replace("{team_line}", tl or "[the team's line]")
    mk = str((var or {}).get("marking") or "")
    out = out.replace("{marking}", (mk[:40] + "...") if len(mk) > 40 else (mk or "[the marking]"))
    for k in ("volume_name", "solicitation", "company", "classification", "project"):
        out = out.replace("{" + k + "}", str((var or {}).get(k) or k.replace("_", " ").title()))
    return out


class HFBuilder(QDialog):
    def __init__(self, parent, work, part, kind, parts_dir=""):
        super().__init__(parent)
        self.work, self.part, self.kind, self.parts_dir = work, part, kind, parts_dir
        self.setWindowTitle(f"Build the {kind} as a table: {part}")
        self.resize(820, 600)
        cur = ((work.get("hf_layouts") or {}).get(part) or {}).get(kind) or {}
        self.spec = copy.deepcopy(cur) if HB.cells_of(cur) else {"table": {"borders": "none", "cells": [
            HB.new_cell(2.17, "", "left"), HB.new_cell(2.16, "", "center"), HB.new_cell(2.17, "", "right")]}}
        self.spec.setdefault("table", {}).setdefault("borders", "none")
        self.saved_qp = None
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"Columns at inch widths (0 shares the rest of the text width). Each line holds words and fields: {TOKENS}. "
                            "A logo sits above the cell's lines.", "muted"))
        self.preview = CellsPreview(self); v.addWidget(self.preview)
        top = QHBoxLayout(); v.addLayout(top, 1)
        left = QVBoxLayout(); top.addLayout(left, 1)
        left.addWidget(QLabel("Columns"))
        self.cols = QListWidget(); left.addWidget(self.cols, 1)
        self.cols.currentRowChanged.connect(lambda _r: self.show_cell())
        cb = QHBoxLayout()
        self.add_col_btn = D.button("Add a column", None, self.add_col); cb.addWidget(self.add_col_btn)
        self.del_col_btn = D.button("Remove", "ghost", self.del_col); cb.addWidget(self.del_col_btn)
        left.addLayout(cb)
        bl = QHBoxLayout(); bl.addWidget(QLabel("Borders"))
        self.borders = QComboBox()
        for k, t in BORDERS:
            self.borders.addItem(t, k)
        self.borders.setCurrentIndex(max(0, self.borders.findData(self.spec["table"]["borders"])))
        self.borders.currentIndexChanged.connect(self.set_borders)
        bl.addWidget(self.borders, 1); left.addLayout(bl)
        right = QVBoxLayout(); top.addLayout(right, 2)
        wl = QHBoxLayout(); wl.addWidget(QLabel("Width (in)"))
        self.width = QDoubleSpinBox(); self.width.setRange(0, 20); self.width.setDecimals(2); self.width.setSingleStep(0.25)
        self.width.valueChanged.connect(self.set_width); wl.addWidget(self.width); wl.addStretch(1)
        right.addLayout(wl)
        self.lines = QTableWidget(0, 4)
        self.lines.setHorizontalHeaderLabels(["Words and fields", "Align", "Size (pt)", "Bold"])
        self.lines.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.lines.itemChanged.connect(lambda _i: self.read_lines())
        right.addWidget(self.lines, 1)
        lb = QHBoxLayout()
        self.add_line_btn = D.button("Add a line", None, self.add_line); lb.addWidget(self.add_line_btn)
        self.del_line_btn = D.button("Remove the line", "ghost", self.del_line); lb.addWidget(self.del_line_btn)
        from .fieldpicker import FieldButton                 # 3.48.0: fields by name, not typed tokens
        self.field_btn = FieldButton(lambda: self.work, on_pick=self.insert_field)
        lb.addWidget(self.field_btn)
        lb.addStretch(1); right.addLayout(lb)
        gl = QHBoxLayout()
        self.logo_lab = D.label("No logo", "muted"); gl.addWidget(self.logo_lab, 1)
        self.logo_btn = D.button("Logo...", None, lambda: self.pick_logo()); gl.addWidget(self.logo_btn)
        self.logo_w = QDoubleSpinBox(); self.logo_w.setRange(0.2, 8); self.logo_w.setDecimals(2); self.logo_w.setSuffix(" in wide")
        self.logo_w.valueChanged.connect(self.set_logo_w); gl.addWidget(self.logo_w)
        self.logo_al = QComboBox()
        for k, t in ALIGNS:
            self.logo_al.addItem(t, k)
        self.logo_al.currentIndexChanged.connect(self.set_logo_al); gl.addWidget(self.logo_al)
        self.logo_clear = D.button("No logo", "ghost", self.clear_logo); gl.addWidget(self.logo_clear)
        right.addLayout(gl)
        bb = QHBoxLayout()
        if kind == "footer":
            self.r7_btn = D.button("Use Rule 7's footer", None, self.use_r7,
                                   "The A number on the left, the marking and the team's standard line in the middle, the page number on the right")
            bb.addWidget(self.r7_btn)
        self.qp_btn = D.button("Save as a Quick Part...", None, lambda: self.save_qp(),
                               "Kept in this standard's Quick Parts; Make templates puts it in every template")
        bb.addWidget(self.qp_btn)
        self.plain_btn = D.button("Back to plain text", "ghost", self.plain, "Remove the table: the left, center and right text again")
        bb.addWidget(self.plain_btn)
        bb.addStretch(1); v.addLayout(bb)
        self.msg = D.label("", "muted"); v.addWidget(self.msg)
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept); box.rejected.connect(self.reject)
        v.addWidget(box)
        self.fill_cols(0)

    # ---- columns
    def cells(self):
        return self.spec["table"]["cells"]

    def selected(self):
        return self.cols.currentRow()

    def fill_cols(self, row=None):
        row = self.selected() if row is None else row
        self.cols.blockSignals(True)
        self.cols.clear()
        for k, c in enumerate(self.cells()):
            words = " / ".join(ln.get("text") or "" for ln in c.get("lines") or []) or ("logo" if (c.get("logo") or {}).get("b64") else "empty")
            self.cols.addItem(f"{k + 1}. {c.get('width_in') or 'shares'} in: {words}")
        self.cols.blockSignals(False)
        if self.cells():
            self.cols.setCurrentRow(max(0, min(row, len(self.cells()) - 1)))
        self.show_cell()

    def add_col(self):
        self.cells().append(HB.new_cell(0.0))
        self.fill_cols(len(self.cells()) - 1)

    def del_col(self):
        k = self.selected()
        if 0 <= k < len(self.cells()) and len(self.cells()) > 1:
            self.cells().pop(k)
            self.fill_cols(k)

    def set_borders(self):
        self.spec["table"]["borders"] = self.borders.currentData() or "none"
        self.preview.update()

    def cell(self):
        k = self.selected()
        return self.cells()[k] if 0 <= k < len(self.cells()) else None

    def show_cell(self):
        c = self.cell()
        on = c is not None
        for wd in (self.width, self.lines, self.add_line_btn, self.del_line_btn, self.logo_btn, self.logo_w, self.logo_al, self.logo_clear,
                   self.field_btn):
            wd.setEnabled(on)
        if not on:
            self.preview.update()
            return
        self.width.blockSignals(True); self.width.setValue(float(c.get("width_in") or 0)); self.width.blockSignals(False)
        self.lines.blockSignals(True)
        self.lines.setRowCount(0)
        for ln in c.get("lines") or []:
            self._line_row(ln)
        self.lines.blockSignals(False)
        logo = c.get("logo") or {}
        self.logo_lab.setText(f"Logo: {logo.get('name')}" if logo.get("b64") else "No logo")
        for wd, val in ((self.logo_w, float(logo.get("w_in") or 1.2)),):
            wd.blockSignals(True); wd.setValue(val); wd.blockSignals(False)
        self.logo_al.blockSignals(True); self.logo_al.setCurrentIndex(max(0, self.logo_al.findData(logo.get("align") or "left")))
        self.logo_al.blockSignals(False)
        self.preview.update()

    def set_width(self, val):
        c = self.cell()
        if c is not None:
            c["width_in"] = round(float(val), 2)
            self._relabel()

    def _relabel(self):
        k = self.selected()
        self.fill_cols(k)

    # ---- lines
    def _line_row(self, ln):
        r = self.lines.rowCount(); self.lines.insertRow(r)
        self.lines.setItem(r, 0, QTableWidgetItem(ln.get("text") or ""))
        al = QComboBox()
        for k, t in ALIGNS:
            al.addItem(t, k)
        al.setCurrentIndex(max(0, al.findData(ln.get("align") or "left")))
        al.currentIndexChanged.connect(lambda _i: self.read_lines())
        self.lines.setCellWidget(r, 1, al)
        sz = QDoubleSpinBox(); sz.setRange(0, 72); sz.setDecimals(1); sz.setSpecialValueText("style's"); sz.setValue(float(ln.get("size") or 0))
        sz.valueChanged.connect(lambda _v: self.read_lines())
        self.lines.setCellWidget(r, 2, sz)
        b = QCheckBox(); b.setChecked(bool(ln.get("bold"))); b.toggled.connect(lambda _v: self.read_lines())
        self.lines.setCellWidget(r, 3, b)

    def read_lines(self):
        c = self.cell()
        if c is None:
            return
        out = []
        for r in range(self.lines.rowCount()):
            it = self.lines.item(r, 0)
            al, sz, b = self.lines.cellWidget(r, 1), self.lines.cellWidget(r, 2), self.lines.cellWidget(r, 3)
            out.append({"text": it.text() if it else "", "align": al.currentData() if al else "left",
                        "size": (sz.value() or None) if sz else None, "bold": bool(b.isChecked()) if b else False})
        c["lines"] = out
        k = self.selected()
        self.cols.blockSignals(True)
        words = " / ".join(ln["text"] for ln in out) or "empty"
        self.cols.item(k).setText(f"{k + 1}. {c.get('width_in') or 'shares'} in: {words}")
        self.cols.blockSignals(False)
        self.preview.update()

    def add_line(self, text="", align=None):
        c = self.cell()
        if c is None:
            return
        al = align or ("center" if self.selected() == 1 and len(self.cells()) == 3 else "left")
        c.setdefault("lines", []).append({"text": text, "align": al, "size": None, "bold": False})
        self.show_cell(); self._relabel()

    def insert_field(self, token):
        """3.48.0: a field into the line chosen (at its end), or as a new line when none is chosen."""
        c = self.cell()
        if c is None:
            return None
        text = "{" + token + "}"
        r = self.lines.currentRow()
        lines = c.setdefault("lines", [])
        if 0 <= r < len(lines):
            lines[r]["text"] = (str(lines[r].get("text") or "").rstrip() + " " + text).strip()
        else:
            self.add_line(text)
            return text
        self.show_cell(); self._relabel()
        self.lines.setCurrentCell(r, 0)
        return text

    def del_line(self):
        c = self.cell()
        r = self.lines.currentRow()
        if c is not None and 0 <= r < len(c.get("lines") or []):
            c["lines"].pop(r)
            self.show_cell(); self._relabel()

    # ---- logo
    def pick_logo(self, path=None):
        c = self.cell()
        if c is None:
            return None
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "A logo", "", "Pictures (*.png *.jpg *.jpeg *.gif *.bmp *.emf)")
        if not path:
            return None
        try:
            c["logo"] = HB.logo(path, w_in=self.logo_w.value() or 1.2, align=self.logo_al.currentData() or "left")
        except OSError as e:
            self.msg.setText(f"That picture could not be read ({type(e).__name__}).")
            return None
        self.show_cell(); self._relabel()
        return c["logo"]

    def set_logo_w(self, val):
        c = self.cell()
        logo = (c or {}).get("logo") or {}
        if logo.get("b64"):
            ratio = float(logo.get("h_in") or 0.5) / max(0.01, float(logo.get("w_in") or 1))
            logo["w_in"], logo["h_in"] = round(val, 2), round(val * ratio, 2)
            self.preview.update()

    def set_logo_al(self):
        c = self.cell()
        logo = (c or {}).get("logo") or {}
        if logo.get("b64"):
            logo["align"] = self.logo_al.currentData() or "left"
            self.preview.update()

    def clear_logo(self):
        c = self.cell()
        if c is not None:
            c["logo"] = None
            self.show_cell(); self._relabel()

    # ---- whole layouts
    def use_r7(self):
        self.spec = HB.r7_footer(self.work)
        self.borders.blockSignals(True); self.borders.setCurrentIndex(self.borders.findData("none")); self.borders.blockSignals(False)
        self.fill_cols(0)
        self.msg.setText("Rule 7's footer. The second middle line is the team's line"
                         + (f": {HB.team_line(self.work)}." if HB.team_line(self.work)
                            else ": blank until it is typed (Base fonts and sizes, or Effort Formatting's footer box)."))

    def plain(self):
        self.spec = None
        self.accept()

    def result_spec(self):
        """What the dialog leaves: the cells layout, or None for back to plain text."""
        if self.spec is None:
            return None
        s = copy.deepcopy(self.spec)
        s["table"]["cells"] = [c for c in s["table"]["cells"] if isinstance(c, dict)]
        return s

    def save_qp(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "Save as a Quick Part", "Its name in Word's gallery:",
                                            text=f"{self.part.title()} {self.kind}")
            if not ok:
                return None
        work = copy.deepcopy(self.work)
        work.setdefault("hf_layouts", {}).setdefault(self.part, {})[self.kind] = self.result_spec() or {}
        (work.get("hf_designs") or {}).pop(self.part, None)
        try:
            e = HB.make_quick_part(work, self.part, self.kind, name, parts_dir=self.parts_dir)
        except Exception as ex:  # noqa: BLE001  said in the dialog; the layout stays
            import diag
            diag.swallowed()
            self.msg.setText(f"The Quick Part could not be made ({type(ex).__name__}).")
            return None
        if not e:
            self.msg.setText("Nothing to save: give the table some words, fields or a logo first.")
            return None
        self.work["quick_parts"] = work["quick_parts"]
        self.saved_qp = e
        self.msg.setText(f"Saved as the Quick Part {e['name']} ({'Footers' if e['gallery'] == 'ftrs' else 'Headers'} gallery, "
                         f"category {e['category']}). Every template made from this standard carries it.")
        return e


def apply(work, part, kind, spec):
    """The builder's result into the layout: a cells table, or back to plain text (None)."""
    lay = work.setdefault("hf_layouts", {}).setdefault(part, {})
    if spec is None:
        cur = lay.get(kind) or {}
        cur.pop("table", None)
        lay[kind] = cur
    else:
        lay[kind] = spec
    return lay[kind]
