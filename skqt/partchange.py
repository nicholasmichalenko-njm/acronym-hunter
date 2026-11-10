"""Change a part (3.98.0; canvas "Libraries and Sets", board 5): three ways, each saved as a new version (the version it
came from stays). 1. The style first: the styles the part names (change them on Styles and every part follows) and the
formatting typed into it, which the styles cannot change (Let the styles decide). 2. Make a variant: cell padding, the
table's width, its column widths, its rows' height, its table style, a paragraph style swapped for another; with a
name and the set it goes into. 3. Anything else in Word: Open in Word, then Bring back as a new version. Rules:
partvariant. Nothing leaves the PC."""
import os

from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLineEdit,
                               QVBoxLayout)

import diag
import partvariant as PV
import stylelib as SL
from . import design as D


def _col(title):
    box = QFrame(); box.setObjectName("changeCol")
    t = D.tokens()
    box.setStyleSheet(f"QFrame#changeCol{{background:{t['surface']};border:1px solid {t['border']};border-radius:8px;}}"
                      "QFrame#changeCol QLabel{background:transparent;}")
    v = QVBoxLayout(box); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(8)
    lab = D.label(title, "label"); v.addWidget(lab)
    return box, v


class ChangePart(QDialog):
    def __init__(self, page, iid):
        super().__init__(page)
        self.page, self.lib, self.iid = page, page.lib, iid
        self.item = self.lib.get(iid)
        self.path, self.name = PV.source_of(self.lib, self.item)
        self.setWindowTitle(f"Change {self.name}")
        self.resize(1240, 700)
        self.result_item = None
        h = QHBoxLayout(self); h.setSpacing(D.SPACE["l"])
        # 1 the style first
        c1, v1 = _col("1  THE STYLE FIRST")
        self.used = PV.styles_used(self.path, self.name)
        v1.addWidget(D.label("This part follows the styles it names. Change them on Styles and every part that uses them "
                             "follows; no new version is needed.", "muted"))
        for nm, typ in self.used or [("(no styles named)", "")]:
            v1.addWidget(D.label(f"<b>{nm}</b>  <span style='color:{D.tokens()['muted']}'>{typ}</span>", None))
        self.b_styles = D.button("Open Styles", "ghost", lambda: self.open_styles()); v1.addWidget(self.b_styles)
        self.n_typed = PV.typed(self.path, self.name)
        self.typed_box = QFrame(); tv = QVBoxLayout(self.typed_box); tv.setContentsMargins(0, 8, 0, 0)
        tv.addWidget(D.label(f"<b>Typed formatting found</b><br>{self.n_typed} run(s) have a size, font or color typed in, so "
                             "the styles cannot change them.", None))
        self.b_decide = D.button("Let the styles decide (new version)", None, lambda: self.decide()); tv.addWidget(self.b_decide)
        self.typed_box.setVisible(self.n_typed > 0)
        v1.addWidget(self.typed_box); v1.addStretch(1)
        h.addWidget(c1, 2)
        # 2 make a variant
        c2, v2 = _col(f"2  MAKE A VARIANT: {self.name.upper()} v{self.item.get('version') or 1}")
        self.table = PV.table_of(self.path, self.name)
        f = QFormLayout(); f.setHorizontalSpacing(12); v2.addLayout(f)
        self.pad = {}
        if self.table:
            prow = QHBoxLayout()
            for side in ("top", "bottom", "left", "right"):
                sb = QDoubleSpinBox(); sb.setRange(0, 2); sb.setDecimals(3); sb.setSingleStep(0.01)
                sb.setValue(float(self.table["padding"].get(side) or 0)); sb.setSpecialValueText("as it is")
                prow.addWidget(D.label(side.title(), "muted", wrap=False)); prow.addWidget(sb); self.pad[side] = sb
            f.addRow("Cell padding (in)", prow)
            self.width = QDoubleSpinBox(); self.width.setRange(0, 20); self.width.setDecimals(2); self.width.setSpecialValueText("as it is")
            self.width.setValue(float(self.table["width"] or 0)); f.addRow("Table width (in)", self.width)
            self.cols = QLineEdit(", ".join(f"{c:g}" for c in self.table["columns"] if c is not None))
            f.addRow("Column widths (in)", self.cols)
            self.row_h = QDoubleSpinBox(); self.row_h.setRange(0, 5); self.row_h.setDecimals(2); self.row_h.setSpecialValueText("as it is")
            self.row_h.setValue(float(self.table["row_height"] or 0)); f.addRow("Row height, at least (in)", self.row_h)
            self.tstyle = QComboBox(); self.tstyle.addItem(f"{self.table['style'] or 'none'} (as it is)", "")
            for nm, typ in self.used:
                if typ == "table" and nm != self.table["style"]:
                    self.tstyle.addItem(nm, nm)
            f.addRow("Table style", self.tstyle)
        else:
            f.addRow(D.label("This part has no table: its paragraph styles can be swapped.", "muted"))
        self.swap_from = QComboBox(); self.swap_to = QComboBox()
        for nm, typ in self.used:
            if typ == "paragraph":
                self.swap_from.addItem(nm, nm)
        self.swap_to.addItem("(keep it)", "")
        self.lib_styles = {self.lib.base_of(i): (self.lib.values(i) or {}) for i in self.lib.items
                           if i["kind"] == "style" and (self.lib.values(i) or {}).get("type", "paragraph") == "paragraph"}
        for nm in sorted(set(self.lib_styles) | {n for n, t in self.used if t == "paragraph"}):
            self.swap_to.addItem(nm, nm)
        sw = QHBoxLayout(); sw.addWidget(self.swap_from, 1); sw.addWidget(D.label("→", None, wrap=False)); sw.addWidget(self.swap_to, 1)
        if self.swap_from.count():                           # a part with no paragraph style has nothing to swap
            f.addRow("Paragraph styles", sw)
        else:
            for x in (self.swap_from, self.swap_to):
                x.setVisible(False)
        self.label = QLineEdit(); self.label.setPlaceholderText("What it is for (compact, page-limited...)")
        f.addRow("Name this version", self.label)
        self.into = QComboBox(); self.into.addItem("No set", "")
        for k in SL.sets(self.lib, "part"):
            self.into.addItem(k["name"], k["id"])
        if page.sid:
            self.into.setCurrentIndex(max(0, self.into.findData(page.sid)))
        f.addRow("Into the set", self.into)
        v2.addStretch(1)
        bh = QHBoxLayout(); bh.addStretch(1)
        bh.addWidget(D.button("Cancel", None, self.reject))
        self.b_save = D.button("Save as a new version", "primary", lambda: self.save_variant()); bh.addWidget(self.b_save)
        v2.addLayout(bh)
        h.addWidget(c2, 4)
        # 3 anything else: in Word
        c3, v3 = _col("3  ANYTHING ELSE: IN WORD")
        v3.addWidget(D.label("<b>Open in Word</b> opens this version on its own in a small Word file. Change anything Word can, "
                             "then save. The library copy stays as it was until you bring it back.", None))
        self.b_open = D.button("Open in Word", None, lambda: self.open_word()); v3.addWidget(self.b_open)
        self.back_label = QLineEdit(); self.back_label.setPlaceholderText("Name the version you bring back")
        v3.addWidget(self.back_label)
        self.b_back = D.button("Bring back as a new version...", None, lambda: self.bring_back()); v3.addWidget(self.b_back)
        v3.addStretch(1)
        h.addWidget(c3, 2)
        self.opened = ""

    # ------------------------------------------------------------ actions
    def open_styles(self):
        self.page.host.go("styles")
        self.reject()

    def done_with(self, it, st, what):
        if it is None:
            self.page.host.status("The part's kept file could not be read.")
            return None
        sid = self.into.currentData() if hasattr(self, "into") else ""
        if sid:
            import partlib as PT
            PT.add_to_set(self.page.cfg(), self.lib, sid, ["q:" + it["id"]])
        self.result_item = it
        self.page.after_change(it, st, what)
        diag.activity("part_changed", how=what)
        self.accept()
        return it

    def decide(self):
        it, st = PV.let_styles_decide(self.lib, self.item)
        return self.done_with(it, st, "styles decide")

    def options(self):
        o = {}
        if self.table:
            pad = {k: sb.value() for k, sb in self.pad.items() if sb.value() > 0 and sb.value() != (self.table["padding"].get(k) or 0)}
            if pad:
                o["padding"] = pad
            if self.width.value() > 0 and self.width.value() != (self.table["width"] or 0):
                o["width"] = self.width.value()
            try:
                cols = [float(x) for x in self.cols.text().replace(";", ",").split(",") if x.strip()]
            except ValueError:
                cols = []
            if cols and cols != [c for c in self.table["columns"]]:
                o["columns"] = cols
            if self.row_h.value() > 0 and self.row_h.value() != (self.table["row_height"] or 0):
                o["row_height"] = self.row_h.value()
            if self.tstyle.currentData():
                o["table_style"] = self.tstyle.currentData()
        if self.swap_from.currentData() and self.swap_to.currentData() and self.swap_from.currentData() != self.swap_to.currentData():
            o["swap"] = {self.swap_from.currentData(): self.swap_to.currentData()}
        return o

    def save_variant(self, opts=None, label=None):
        opts = self.options() if opts is None else opts
        if not opts:
            self.page.host.status("Nothing is different from the version you started from.")
            return None
        have = {n for n, _t in self.used}
        xml = {to: self.lib_styles[to].get("_xml") for to in (opts.get("swap") or {}).values()
               if to not in have and self.lib_styles.get(to, {}).get("_xml")}
        it, st = PV.make_variant(self.lib, self.item, opts, label if label is not None else self.label.text().strip(), styles_xml=xml)
        return self.done_with(it, st, "variant")

    def open_word(self):
        import tempfile
        out = PV.export(self.lib, self.item, tempfile.mkdtemp(prefix="sk_part_"))
        self.opened = out or ""
        if out and not os.environ.get("AH_TEST"):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(out))
        self.page.host.status("Opened in Word. Save it, then Bring back as a new version." if out else "The part could not be opened.")
        return out

    def bring_back(self, path=None):
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "The part saved in Word", os.path.dirname(self.opened) if self.opened else "",
                                                   "Word (*.docx *.dotx)")
            if not path:
                return None
        it, st = PV.bring_back(self.lib, self.item, path, self.back_label.text().strip())
        return self.done_with(it, st, "from Word")


def change(page, iid, run=True):
    dlg = ChangePart(page, iid)
    page.change_dialog = dlg
    if run:
        dlg.exec()
    return dlg
