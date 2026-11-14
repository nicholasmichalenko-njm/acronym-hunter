"""Line spacing, indents and tabs on a style's own form (4.30.6; Nicholas 2026-11-13 18:52: "all four", numbering only
where the style carries a list). For every paragraph style:

- Line spacing: single, 1.15, 1.5, double, another multiple, exactly so many points, or at least so many;
- Indents, in inches: left, right, and a first line that is indented or hangs;
- Tabs: each one written as its position in inches, its kind and its leader ("6.5 right dots; 0.5").

Only what is changed on the form is saved, so a value a style takes from the style it is based on stays taken from it.
A style that is part of a list (a numbered heading, a bullet) says which level it is; its numbers and bullets are set
with the list, which every level shares, so they are not set here yet. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QLineEdit

import stylelib as SL
from . import design as D

SPACING = (("1.0", "Single"), ("1.15", "1.15"), ("1.5", "1.5"), ("2.0", "Double"), ("multiple", "Multiple"), ("exact", "Exactly"),
           ("atLeast", "At least"))
SPECIAL = (("", "None"), ("first", "First line"), ("hanging", "Hanging"))
TAB_HINT = "Each tab: inches, then left, center, right or decimal, then dots, dashes or line. 6.5 right dots; 0.5"


class More:
    """The extra rows of the form and what they were when it opened."""

    def __init__(self, dlg, form, v):
        self.dlg = dlg
        rule, line = v.get("line_rule") or "auto", float(v.get("line") or 1.0)
        self.sp = QComboBox()
        for k, t in SPACING:
            self.sp.addItem(t, k)
        key = rule if rule in ("exact", "atLeast") else (f"{line:g}" if f"{line:g}" in ("1", "1.15", "1.5", "2") else "multiple")
        key = {"1": "1.0", "2": "2.0"}.get(key, key)
        self.sp.setCurrentIndex(max(0, self.sp.findData(key)))
        self.sp_by = QDoubleSpinBox(); self.sp_by.setRange(0.5, 200); self.sp_by.setSingleStep(0.05); self.sp_by.setValue(line)
        r = QHBoxLayout(); r.addWidget(self.sp); r.addWidget(self.sp_by); r.addStretch(1)
        form.addRow("Line spacing", r)
        self.ind = {}
        r = QHBoxLayout()
        for k, t in (("left", "Left"), ("right", "Right")):
            b = QDoubleSpinBox(); b.setRange(-2, 12); b.setSingleStep(0.05); b.setDecimals(2); b.setSuffix(" in")
            b.setValue(float(v.get(k) or 0) / 72)
            r.addWidget(D.label(t, "muted", wrap=False)); r.addWidget(b); self.ind[k] = b
        self.special = QComboBox()
        for k, t in SPECIAL:
            self.special.addItem(t, k)
        sp_now = "hanging" if v.get("hanging") else "first" if v.get("first") else ""
        self.special.setCurrentIndex(self.special.findData(sp_now))
        self.by = QDoubleSpinBox(); self.by.setRange(0, 12); self.by.setSingleStep(0.05); self.by.setDecimals(2); self.by.setSuffix(" in")
        self.by.setValue(float(v.get("hanging") or v.get("first") or 0) / 72)
        r.addWidget(self.special); r.addWidget(self.by); r.addStretch(1)
        form.addRow("Indents", r)
        self.tabs = QLineEdit(SL.tabs_text(v.get("tabs"))); self.tabs.setPlaceholderText("No tabs of its own")
        self.tabs.setToolTip(TAB_HINT)
        form.addRow("Tabs", self.tabs)
        self.tabs_say = D.label(TAB_HINT, "faint"); form.addRow("", self.tabs_say)
        numbered, level = SL.numbering_of(v)
        self.num = D.label(f"Part of a list, level {level}. Its numbers or bullets are set with the list, which every level shares; "
                           "they are kept as Word wrote them." if numbered else "Not part of a list.", "muted")
        self.num.setObjectName("styleNumbering")
        form.addRow("Numbering", self.num)
        for w in (self.sp, self.special):
            w.currentIndexChanged.connect(lambda _i: self.sync())
        for w in [self.sp_by, self.by] + list(self.ind.values()):
            w.valueChanged.connect(lambda _x: dlg.redraw())
        self.tabs.textEdited.connect(lambda _t: self.sync())
        self.sync(redraw=False)
        self.first = self.read()

    def sync(self, redraw=True):
        k = self.sp.currentData()
        self.sp_by.setVisible(k in ("multiple", "exact", "atLeast"))
        self.sp_by.setSuffix(" pt" if k in ("exact", "atLeast") else " lines")
        self.by.setEnabled(bool(self.special.currentData()))
        _tabs, bad = SL.parse_tabs(self.tabs.text())
        self.tabs_say.setText(("Not understood: " + "; ".join(bad) + ". " if bad else "") + TAB_HINT)
        if redraw:
            self.dlg.redraw()

    def read(self):
        """What the rows say now, as the style's values (points)."""
        k = self.sp.currentData()
        rule = k if k in ("exact", "atLeast") else "auto"
        line = self.sp_by.value() if k in ("multiple", "exact", "atLeast") else float(k)
        sp = self.special.currentData()
        by = round(self.by.value() * 72, 2) if sp else 0.0
        tabs, _bad = SL.parse_tabs(self.tabs.text())
        return {"line": round(line, 2), "line_rule": rule, "left": round(self.ind["left"].value() * 72, 2),
                "right": round(self.ind["right"].value() * 72, 2), "first": by if sp == "first" else 0.0,
                "hanging": by if sp == "hanging" else 0.0, "tabs": tabs}

    def values(self):
        """Only what was changed since the form opened (line spacing and its rule go together; so do first and hanging)."""
        now, out = self.read(), {}
        groups = (("line", "line_rule"), ("left",), ("right",), ("first", "hanging"), ("tabs",))
        for g in groups:
            if any(now[k] != self.first[k] for k in g):
                out.update({k: now[k] for k in g})
        return out


def add_rows(dlg, form, v):
    return More(dlg, form, v)
