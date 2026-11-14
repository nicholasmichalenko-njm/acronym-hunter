"""A style's own form on Styles (4.30.1; Nicholas 2026-11-13 14:28: "double-clicking the style doesn't even allow me to
open up and review or modify the style ... I need to be able to do that within the styles pane", "not able to right-click
and duplicate", "differentiate between the character and paragraph styles").

Double-click a row (or right-click > See or change...): the style's font, size, color and character marks, and for a
paragraph style its alignment, space before and after, and keep with next, with how it looks as you set it. Save keeps it
as a new version; the version it came from stays. Duplicate... makes a new style under its own name with the same
values. A style brought in from Word keeps everything else Word wrote (numbering, tabs, borders). The list shows each
style's kind and can show only paragraph or only character styles. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFontComboBox, QFormLayout, QHBoxLayout,
                               QLineEdit, QVBoxLayout)

import diag
import stylelib as SL
import styleown as SO
from . import design as D

KINDS = (("", "Every style"), ("paragraph", "Paragraph styles"), ("character", "Character styles"))
KIND_WORD = {"paragraph": "Paragraph", "character": "Character"}


class StyleEdit(QDialog):
    """Review or change one style. name_edit: a new name is asked for (Duplicate)."""
    def __init__(self, page, it, v, name_edit=False):
        super().__init__(page)
        from .stylespage import NAMED, dot, preview
        self._preview = preview
        self.v, self.kind = dict(v), SL.kind_of(v)
        base = page.lib.base_of(it)
        self.setWindowTitle(("Duplicate " if name_edit else "") + f"{base}: {KIND_WORD[self.kind].lower()} style")
        self.setMinimumWidth(520)
        f = QFormLayout(self)
        self.name = QLineEdit(f"{base} copy" if name_edit else base); self.name.setEnabled(name_edit)
        f.addRow("Name", self.name)
        f.addRow("Kind", D.label(KIND_WORD[self.kind] + " style" + ("" if name_edit else f", version {it.get('version', 1)}"), None))
        self.font = QFontComboBox(); self.font.setCurrentFont(QFont(str(v.get("font") or "Calibri")))
        self.font_own = QCheckBox("Its own font"); self.font_own.setChecked(bool(v.get("font")))
        fr = QHBoxLayout(); fr.addWidget(self.font_own); fr.addWidget(self.font, 1); f.addRow("Font", fr)
        self.size = QDoubleSpinBox(); self.size.setRange(0, 96); self.size.setSingleStep(0.5); self.size.setSpecialValueText("As its base")
        self.size.setSuffix(" pt"); self.size.setValue(float(v.get("size") or 0)); f.addRow("Size", self.size)
        self.color = QComboBox()
        for t, hx in NAMED:
            self.color.addItem(dot("#" + hx if hx else "#111111"), t, hx)
        cur = str(v.get("color") or "").lstrip("#").upper()
        i = self.color.findData("" if cur in ("AUTO", "") else cur)
        if i < 0 and cur:
            self.color.addItem(dot("#" + cur), f"#{cur}", cur); i = self.color.count() - 1
        self.color.setCurrentIndex(max(0, i)); f.addRow("Color", self.color)
        row = QHBoxLayout(); self.marks = {}
        for k, t in (("bold", "Bold"), ("italic", "Italic"), ("underline", "Underline"), ("caps", "All caps"), ("hidden", "Hidden")):
            cb = QCheckBox(t); cb.setChecked(bool(v.get(k))); row.addWidget(cb); self.marks[k] = cb
        row.addStretch(1); f.addRow("Characters", row)
        self.jc = self.before = self.after = self.keep = self.more = None
        if self.kind == "paragraph":
            self.jc = QComboBox()
            for k, t in SL.JC:
                self.jc.addItem(t, k)
            now = {"start": "left", "end": "right"}.get(str(v.get("jc") or ""), str(v.get("jc") or ""))
            self.jc.setCurrentIndex(max(0, self.jc.findData(now))); f.addRow("Alignment", self.jc)
            self.before, self.after = QDoubleSpinBox(), QDoubleSpinBox()
            sp = QHBoxLayout()
            for box, k, t in ((self.before, "before", "Before"), (self.after, "after", "After")):
                box.setRange(0, 144); box.setSingleStep(1); box.setSuffix(" pt"); box.setValue(float(v.get(k) or 0))
                sp.addWidget(D.label(t, "muted", wrap=False)); sp.addWidget(box)
            sp.addStretch(1); f.addRow("Space", sp)
            self.keep = QCheckBox("Keep with the next paragraph"); self.keep.setChecked(bool(v.get("keep_next"))); f.addRow("", self.keep)
            from . import stylemore as SM                     # 4.30.6: line spacing, indents, tabs, and what list it is in
            self.more = SM.add_rows(self, f, v)
        d = SL.describe(v)
        more = " · ".join(x for x in (d.get("other") or "",) if x)
        self.note = D.label(("Also carries: " + more + ". " if more else "") + ("Everything else Word wrote for it (numbering, borders) is kept."
                            if v.get("_xml") and v.get("_made") != "app" else ""), "muted")
        self.note.setVisible(bool(self.note.text().strip())); f.addRow(self.note)
        self.sample_box = QVBoxLayout(); f.addRow("How it looks", self.sample_box)
        self.sample = None
        for w in [self.font, self.size, self.color, self.font_own] + list(self.marks.values()):
            sig = getattr(w, "currentIndexChanged", None) or getattr(w, "valueChanged", None) or getattr(w, "toggled", None)
            sig.connect(lambda *_a: self.redraw())
        self.scope = None                                     # 4.30.2: whose style the change is
        if not name_edit:
            sets_ = SL.sets_of(page.lib, it["id"])
            here = SL.get_set(page.lib, page.sid) if getattr(page, "sid", None) else None
            others = [k["name"] for k in sets_ if not here or k["id"] != here["id"]]
            if here is not None and any(k["id"] == here["id"] for k in sets_) and others:
                self.scope = QComboBox()
                self.scope.addItem(f"{here['name']} only", False)
                self.scope.addItem(f"Every set that uses it ({here['name']}, {', '.join(others)})", True)
                f.addRow("Change it for", self.scope)
                tail = f"{', '.join(others)} keep{'s' if len(others) == 1 else ''} the style as it is unless you pick every set."
            elif here is not None and any(k["id"] == here["id"] for k in sets_):
                tail = f"The change is {here['name']}'s; no other set uses this style."
            elif sets_:
                self.scope = QComboBox()
                self.scope.addItem("No set yet: each set is asked when it is shown", False)
                self.scope.addItem(f"Every set that uses it ({', '.join(k['name'] for k in sets_)})", True)
                f.addRow("Change it for", self.scope)
                tail = "The style as it was stays for any set that keeps it."
            else:
                tail = "No set uses this style yet."
        f.addRow(D.label("Saved as a new style." if name_edit else tail, "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Make the copy" if name_edit else "Save the changes")
        bb.button(QDialogButtonBox.Cancel).setText("Cancel" if name_edit else "Close")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); f.addRow(bb)
        self.redraw()

    def values(self):
        out = {"font": self.font.currentFont().family() if self.font_own.isChecked() else "", "size": self.size.value() or "",
               "color": self.color.currentData() or ""}
        out.update({k: cb.isChecked() for k, cb in self.marks.items()})
        if self.kind == "paragraph":
            out.update({"jc": self.jc.currentData() or "", "before": self.before.value(), "after": self.after.value(),
                        "keep_next": self.keep.isChecked()})
            out.update(self.more.values())                    # only what was changed on the form
        return out

    def redraw(self):
        self.font.setEnabled(self.font_own.isChecked())
        if self.sample is not None:
            self.sample.hide(); self.sample.setParent(None)
        v = SL._edited(self.v, self.values())                 # as it will be saved (4.30.6: the indents and line spacing too)
        self.sample = self._preview(v, name=self.name.text())
        self.sample_box.addWidget(self.sample)


def review(page, iid, values=None, every=None):
    """Open the style's form (values, every: tests, no dialog). Saved from inside a set, the change is that set's alone
    unless every set is picked (4.30.2). Returns the changed style, or None when nothing was saved."""
    it = page.lib.get(iid)
    if it is None:
        return None
    v = page.lib.values(it) or {}
    if values is None:
        dlg = StyleEdit(page, it, v)
        if dlg.exec() != QDialog.Accepted:
            return None
        values = dlg.values()
        every = bool(dlg.scope.currentData()) if dlg.scope is not None else False
    new, st, moved = SO.save(page.lib, iid, values, sid=getattr(page, "sid", None), every=bool(every))
    if new is None:
        return None
    page.shown_ver[new.get("family")] = new["id"]
    page.host.toast(f"{page.lib.base_of(it)}: " + ("nothing changed" if st != "version" else
                    (f"changed for {', '.join(moved)}" if moved else "changed; no set uses the change yet")))
    diag.activity("style_edited")
    page.fill_sets(); page.fill_rows(); page.select(new["id"])
    return new


def duplicate(page, iid, name=None, values=None):
    """Duplicate...: a new style under its own name with this one's values (name: tests, no dialog). Returns it."""
    it = page.lib.get(iid)
    if it is None:
        return None
    if name is None:
        dlg = StyleEdit(page, it, page.lib.values(it) or {}, name_edit=True)
        if dlg.exec() != QDialog.Accepted:
            return None
        name, values = dlg.name.text(), dlg.values()
    new, st = SL.duplicate(page.lib, iid, name, values)
    if new is None:
        page.host.status("The library has a style of that name: give the copy another." if st == "taken" else "A style needs a name.")
        return None
    if page.sid:
        SL.add_to_set(page.lib, page.sid, [new["id"]])
    page.host.toast(f"{page.lib.base_of(new)}: made from {page.lib.base_of(it)}")
    diag.activity("style_duplicated")
    page.fill_sets(); page.fill_rows(); page.select(new["id"])
    return new


def add_kind_filter(page, row):
    """Every style, Paragraph styles or Character styles, beside Find."""
    page.kind_f = QComboBox()
    for k, t in KINDS:
        page.kind_f.addItem(t, k)
    page.kind_f.currentIndexChanged.connect(lambda _i: page.fill_rows())
    row.addWidget(page.kind_f)
    return page.kind_f


def keep_kind(page, rows):
    """The rows of the kind picked."""
    want = page.kind_f.currentData() if getattr(page, "kind_f", None) is not None else ""
    if not want:
        return rows
    return [r for r in rows if SL.kind_of(page.lib.values(page.lib.get(r["shown"])) or {}) == want]
