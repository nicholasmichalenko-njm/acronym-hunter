"""Setup > Setup styles... (3.71.0): the setup's own styles, in the effort. For each kind of setup text (the compliance
requirement, customer requirement text, supporting RFP text, management guidance, and the rest the setup writes): the
style's name, font, size, color, bold, italic, and whether it is hidden. A sample line shows the look. Save for this
effort; Use for every effort; Put them in this effort's template. setuptemplate holds the rules."""
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFontComboBox, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QVBoxLayout)
import diag
import setuptemplate as ST
from . import design as D

FIRST = ("rfp", "customer", "support", "pm")              # the outline's four, first
NAMES = {"rfp": "Compliance requirement", "customer": "Customer requirement text", "support": "Supporting RFP text",
         "pm": "Management guidance"}


class SetupStyles(QDialog):
    def __init__(self, page, kinds=None):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.setWindowTitle("Setup styles")
        self.resize(1240, 500)
        self.opts = page.setup_opts()
        self.kinds = list(kinds or FIRST) + [k for k, *_r in ST.KINDS if k not in (kinds or FIRST)]
        v = QVBoxLayout(self)
        v.addWidget(D.label("The setup's own styles. Each kind of setup text goes in its style; hidden text shows only with "
                            "Show/Hide on, and Strip setup takes it out before the volume goes. A template that already has a "
                            "style of the same name keeps its own look.", "muted"))
        g = QGridLayout(); v.addLayout(g)
        for c, h in enumerate(("What it holds", "Style name", "Font", "Size", "Color (hex)", "Bold", "Italic", "Hidden", "Sample")):
            g.addWidget(D.label(h, "label"), 0, c)
        self.rows = {}
        for r, k in enumerate(self.kinds, 1):
            o = self.opts.get(k) or {}
            lk = ST.look(self.opts, k)
            name = QLineEdit(o.get("style", "")); name.setMinimumWidth(210)
            font = QFontComboBox(); font.setEditable(True); font.setEditText(lk["font"] or ""); font.setMaximumWidth(190)
            size = QDoubleSpinBox(); size.setRange(0, 72); size.setSingleStep(0.5); size.setSpecialValueText("as Normal"); size.setValue(lk["size"] or 0)
            color = QLineEdit(lk["color"]); color.setFixedWidth(84)
            bold, ital, hid = QCheckBox(), QCheckBox(), QCheckBox()
            bold.setChecked(lk["bold"]); ital.setChecked(lk["italic"]); hid.setChecked(lk["hidden"])
            sample = QLabel()
            g.addWidget(QLabel(NAMES.get(k, ST.KIND_OF[k][0])), r, 0)
            for c, w in enumerate((name, font, size, color, bold, ital, hid, sample), 1):
                g.addWidget(w, r, c)
            self.rows[k] = {"style": name, "font": font, "size": size, "color": color, "bold": bold, "italic": ital, "hidden": hid, "sample": sample}
            for w in (name, color):
                w.textChanged.connect(lambda _t, kk=k: self.redraw(kk))
            font.editTextChanged.connect(lambda _t, kk=k: self.redraw(kk))
            size.valueChanged.connect(lambda _v, kk=k: self.redraw(kk))
            for w in (bold, ital, hid):
                w.toggled.connect(lambda _v, kk=k: self.redraw(kk))
            self.redraw(k)
        g.setColumnStretch(9, 1)
        bar = QHBoxLayout(); v.addLayout(bar)
        self.b_team = D.button("Use for every effort", None, lambda: self.save(team=True), "The team's starting point for new efforts")
        self.b_tmpl = D.button("Put them in this effort's template", None, lambda: self.to_template(),
                               "The effort's formatting carries them, so the template made for it has them")
        bar.addWidget(self.b_team); bar.addWidget(self.b_tmpl); bar.addStretch(1)
        bb = QDialogButtonBox(); bb.addButton("Save for this effort", QDialogButtonBox.AcceptRole); bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(lambda: (self.save(), self.accept())); bb.rejected.connect(self.reject); bar.addWidget(bb)
        self.b_tmpl.setEnabled(self.host.ws is not None)

    def values(self):
        out = {k: dict(o) for k, o in self.opts.items()}
        for k, w in self.rows.items():
            o = out.setdefault(k, {"include": True})
            o.update(style=w["style"].text().strip() or (o.get("style") or ST.KIND_OF[k][1]), font=w["font"].currentText().strip(),
                     size=w["size"].value() or None, color=w["color"].text().strip().lstrip("#")[:6], bold=w["bold"].isChecked(),
                     italic=w["italic"].isChecked(), hidden=w["hidden"].isChecked())
        return out

    def redraw(self, k):
        w = self.rows[k]
        from .outlineimport import look_css
        lk = {"color": w["color"].text().strip().lstrip("#") or "000000", "bold": w["bold"].isChecked(), "italic": w["italic"].isChecked(),
              "font": w["font"].currentText().strip(), "size": w["size"].value()}
        w["sample"].setText(f'<span style="{look_css(lk)}">The offeror shall describe...</span>'
                            + (' <span style="color:gray">(hidden)</span>' if w["hidden"].isChecked() else ""))

    def save(self, team=False):
        vals = self.values()
        self.page.set_setup_opts(vals)
        if team:
            ST.set_team_options(self.host.config_dir, vals)
            self.host.toast("Setup styles saved for every effort")
        diag.activity("setup_styles_saved")
        self.opts = self.page.setup_opts()
        return vals

    def to_template(self):
        if self.host.ws is None:
            return []
        vals = self.save()
        names = ST.to_effort_template(self.host.ws, vals)
        diag.activity("setup_styles_to_template", n=len(names))
        self.host.toast(f"{len(names)} setup style(s) are in this effort's formatting: its template will carry them")
        return names
