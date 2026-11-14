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
        said, self.num_section = numbering_words(_std(dlg), dlg.name.text().strip(), v)   # 4.33.1 (ST5): the scheme in use, by name
        self.num = D.label(said, "muted")
        self.num.setObjectName("styleNumbering")
        form.addRow("Numbering", self.num)
        self.num_change = D.button("Change the numbering...", None, lambda: change_numbering(dlg, self.num_section),
                                   "Opens the scheme in the standards, where every level of it is set. This form closes without saving.")
        self.num_change.setVisible(bool(self.num_section))
        form.addRow("", self.num_change)
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


FMT_WORDS = {"decimal": "1, 2, 3", "upperLetter": "A, B, C", "lowerLetter": "a, b, c", "upperRoman": "I, II, III",
             "lowerRoman": "i, ii, iii", "bullet": "a bullet", "none": "no number"}


def _std(dlg):
    """The standards in use (the open effort's set, or the Global Standards), {} when they cannot be read."""
    try:
        import prodrules as PRL
        return PRL.load(dlg.parent().host.config_dir).get("company") or {}
    except Exception:  # noqa: BLE001  the form opens without the line
        return {}


def numbering_words(std, name, v):
    """(what the Numbering row says, the standards section that sets it or ""). The scheme is named from the standards:
    Heading numbering for a heading level's style, the list by its name for a list level's style."""
    hn = std.get("heading_numbering") or {}
    for i, lev in enumerate(hn.get("levels") or []):
        if name and lev.get("style") == name:
            shows = str(lev.get("text") or "").replace("%", "level ")
            off = "" if hn.get("on") else " Heading numbering is off: fixing a document leaves its heading numbers as they are."
            return (f"Heading numbering, level {i + 1}: {FMT_WORDS.get(lev.get('fmt'), lev.get('fmt') or 'a number')}, shown as "
                    f"\"{lev.get('text', '')}\" ({shows}). Every heading level shares this scheme.{off}", "headnum")
    ln = std.get("list_numbering") or {}
    for lst in ln.get("lists") or []:
        for i, lev in enumerate(lst.get("levels") or []):
            if name and lev.get("style") == name:
                off = "" if ln.get("on") else " List numbering is off: fixing a document leaves its lists as they are."
                return (f"The list \"{lst.get('name', '')}\", level {i + 1}: {FMT_WORDS.get(lev.get('fmt'), lev.get('fmt') or 'a number')}, "
                        f"shown as \"{lev.get('text', '')}\". Every level of the list shares this scheme.{off}", "lists")
    numbered, level = SL.numbering_of(v)
    if numbered:
        return (f"Part of a list, level {level}, that the standards do not name. Its numbers or bullets are kept as Word wrote "
                "them. To set them here, add this style to a list in the standards.", "lists")
    return "Not part of a list.", ""


def change_numbering(dlg, section):
    """Close the form and open the scheme's section in the standards (one home for numbering)."""
    host = dlg.parent().host
    dlg.reject()
    try:
        from .prodstdpage import SECTIONS
        host.go("prodstd")
        host.prodstd_page.show_section([k for k, _t in SECTIONS].index(section))
    except Exception:  # noqa: BLE001
        __import__("diag").swallowed()
    return section


def add_rows(dlg, form, v):
    return More(dlg, form, v)
