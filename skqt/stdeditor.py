"""A layer of the Global Standards edited outside Production Standards (3.69.0, retiring Production Standards: decision
1). The same values, in the same file (production_standards.json), shown where people look for them now: Rules (the
checks Fix a Copy runs), Formatting Standards (allowed styles and the styles the rules read), Effort Profiles (a
profile's content map, fields and font rules).

LayerEditor(host, store, sections) shows each section (stdsections builds them) with Save and Undo changes. A value set
in this layer shows in bold; the layer below is what it says when nothing is set here.
Stores: GlobalStore(config_dir) the Global Standards (every effort); ProfileStore(config_dir, eid, pid) one profile's
changes in one effort type. Binder, form rows and a simple table editor live here so Production Standards can retire."""
import copy

from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QScrollArea, QTableWidget, QVBoxLayout, QWidget)
import diag
import prodrules as PRL
from . import design as D


def _get(d, path, default=None):
    for k in path:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d


def _set(d, path, v):
    for k in path[:-1]:
        if not isinstance(d.get(k), dict):
            d[k] = {}
        d = d[k]
    d[path[-1]] = v


def num(lo=0.0, hi=72.0, step=0.5, blank="Not set", dec=2):
    w = QDoubleSpinBox(); w.setRange(lo - (step if blank else 0), hi); w.setSingleStep(step); w.setDecimals(dec)
    if blank:
        w.setSpecialValueText(blank)
    w.setMinimumWidth(110)
    return w


def enum(items, editable=False):
    w = QComboBox(); w.setEditable(editable)
    for k, t in items:
        w.addItem(t, k)
    w.setMinimumWidth(170)
    return w


# ---------------------------------------------------------------- where the layer lives
class GlobalStore:
    """The Global Standards: every effort."""
    scope = "team"
    what = "the Global Standards (every effort)"

    def __init__(self, config_dir):
        self.config_dir = config_dir

    def load(self):
        data = PRL.load(self.config_dir)
        return copy.deepcopy(data["company"]), copy.deepcopy(PRL.COMPANY)

    def save(self, work):
        data = PRL.load(self.config_dir)
        data["company"] = copy.deepcopy(work)
        PRL.save(self.config_dir, data)


class ProfileStore:
    """One volume profile's changes in one effort type (where Effort Profiles writes its picks and limits)."""
    scope = "profile"

    def __init__(self, config_dir, eid, pid):
        self.config_dir, self.eid, self.pid = config_dir, eid, pid
        data = PRL.load(config_dir)
        e = PRL.effort_type_of(data, eid) or {}
        self.what = f"{PRL.type_of(data, pid).get('name', '')} in {e.get('name', '')}"

    def _base(self, data):
        t = PRL.type_of(data, self.pid)
        std = PRL.merge(data["company"], PRL.layer_of(t))
        e = PRL.effort_type_of(data, self.eid)
        return PRL.merge(std, PRL.effort_layer_of(e)) if e is not None else std

    def load(self):
        data = PRL.load(self.config_dir)
        base = self._base(data)
        e = PRL.effort_type_of(data, self.eid) or {}
        return PRL.merge(copy.deepcopy(base), (e.get("profile_over") or {}).get(self.pid) or {}), base

    def save(self, work):
        data = PRL.load(self.config_dir)
        e = PRL.effort_type_of(data, self.eid)
        if e is None:
            return
        e.setdefault("profile_over", {})[self.pid] = PRL.diff(work, self._base(data))
        PRL.save(self.config_dir, data)


# ---------------------------------------------------------------- a value tied to a box
class Binder:
    def __init__(self, ed):
        self.ed, self.items, self.loading = ed, [], False

    def bind(self, w, path, kind, label=None):
        it = {"w": w, "path": tuple(path), "kind": kind, "label": label}
        self.items.append(it)
        sig = {"text": lambda: w.textEdited, "list": lambda: w.textEdited, "num": lambda: w.valueChanged,
               "bool": lambda: w.toggled, "enum": lambda: w.currentIndexChanged}[kind]()
        sig.connect(lambda *_a, i=it: self.write(i))
        if kind == "enum" and w.isEditable():
            w.lineEdit().textEdited.connect(lambda _t, i=it: self.write(i))
        return w

    def value(self, it):
        w, k = it["w"], it["kind"]
        if k == "text":
            return w.text().strip() or None
        if k == "list":
            return [x.strip() for x in w.text().split(",") if x.strip()] or None
        if k == "num":
            return None if (w.value() == w.minimum() and w.specialValueText()) else round(w.value(), 3)
        if k == "bool":
            return w.isChecked()
        if w.isEditable():
            return w.currentText().strip() or None
        d = w.currentData()
        return d if d not in ("", None) else None

    def show(self, it, v):
        w, k = it["w"], it["kind"]
        w.blockSignals(True)
        try:
            if k == "text":
                w.setText("" if v is None else str(v))
            elif k == "list":
                w.setText(", ".join(v or []) if isinstance(v, list) else ("" if v is None else str(v)))
            elif k == "num":
                w.setValue(w.minimum() if v in (None, "") else float(v))
            elif k == "bool":
                w.setChecked(bool(v))
            elif w.isEditable():
                w.setEditText("" if v is None else str(v))
            else:
                w.setCurrentIndex(max(0, w.findData(v if v is not None else "")))
        finally:
            w.blockSignals(False)

    def load(self):
        self.loading = True
        for it in self.items:
            self.show(it, _get(self.ed.work, it["path"]))
            self.mark(it)
        self.loading = False

    def write(self, it):
        if self.loading:
            return
        _set(self.ed.work, it["path"], self.value(it))
        self.ed.changed()
        self.mark(it)

    def mark(self, it):
        if it["label"] is not None:
            own = _get(self.ed.work, it["path"]) != _get(self.ed.base, it["path"])
            f = it["label"].font(); f.setBold(own); it["label"].setFont(f)
            it["label"].setToolTip(f"Set in {self.ed.store.what}" if own else "As the layer below says")


class SimpleTable:
    """Rows of a list in the layer (each a dict), one box per column. cols: (field, heading, kind); kind "text", "bool",
    "list" or ("enum", [(value, words)])."""

    def __init__(self, ed, v, path, cols):
        self.ed, self.path, self.cols = ed, tuple(path), cols
        self.t = QTableWidget(0, len(cols)); self.t.setHorizontalHeaderLabels([c[1] for c in cols])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.horizontalHeader().setStretchLastSection(True); self.t.setMinimumHeight(180)
        v.addWidget(self.t)
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(D.button("+ Add", None, lambda: self.add({})))
        bar.addWidget(D.button("Remove", None, lambda: self.remove()))
        bar.addStretch(1)

    def load(self):
        self.t.setRowCount(0)
        for r in _get(self.ed.work, self.path) or []:
            self._row(r)

    def _row(self, r):
        i = self.t.rowCount(); self.t.insertRow(i)
        for c, (field, _h, kind) in enumerate(self.cols):
            val = r.get(field)
            if isinstance(kind, tuple):
                w = enum(kind[1]); w.setCurrentIndex(max(0, w.findData(val if val is not None else "")))
                w.currentIndexChanged.connect(lambda *_a: self.write())
            elif kind == "bool":
                w = QCheckBox(); w.setChecked(bool(val)); w.toggled.connect(lambda *_a: self.write())
            elif kind == "list":
                w = QLineEdit(", ".join(val or [])); w.textEdited.connect(lambda *_a: self.write())
            else:
                w = QLineEdit("" if val is None else str(val)); w.textEdited.connect(lambda *_a: self.write())
            self.t.setCellWidget(i, c, w)

    def rows(self):
        out = []
        for i in range(self.t.rowCount()):
            r = {}
            for c, (field, _h, kind) in enumerate(self.cols):
                w = self.t.cellWidget(i, c)
                if isinstance(kind, tuple):
                    r[field] = w.currentData() if w.currentData() not in ("", None) else None
                elif kind == "bool":
                    r[field] = w.isChecked()
                elif kind == "list":
                    r[field] = [x.strip() for x in w.text().split(",") if x.strip()]
                else:
                    r[field] = w.text().strip()
            if any(v not in (None, "", [], False) for v in r.values()):
                out.append(r)
        return out

    def write(self):
        _set(self.ed.work, self.path, self.rows())
        self.ed.changed()

    def add(self, r):
        self._row(r)
        self.write()

    def remove(self):
        i = self.t.currentRow()
        if i >= 0:
            self.t.removeRow(i)
            self.write()


# ---------------------------------------------------------------- the editor
class LayerEditor(QWidget):
    def __init__(self, host, store, sections):
        super().__init__()
        from . import stdsections as SS
        self.host, self.store, self.sections = host, store, list(sections)
        self.binder, self.tables, self.dirty = Binder(self), [], False
        self.work, self.base = store.load()
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout(); outer.addLayout(top)
        self.where = D.label(f"Changes here apply to {store.what}.", "muted"); top.addWidget(self.where, 1)
        self.b_save = D.button("Save", "primary", lambda: self.save()); top.addWidget(self.b_save)
        self.b_undo = D.button("Undo changes", "ghost", lambda: self.reload()); top.addWidget(self.b_undo)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame)
        body = QWidget(); self.v = QVBoxLayout(body); self.v.setSpacing(D.SPACE["m"])
        for key in self.sections:
            getattr(SS, f"build_{key}")(self, self.v)
        self.v.addStretch(1)
        sc.setWidget(body); outer.addWidget(sc, 1)
        self.fill()

    def form(self, v, title, subtitle=""):
        c = D.Card(title, subtitle); f = QFormLayout(); f.setSpacing(D.SPACE["s"]); c.body.addLayout(f); v.addWidget(c)
        return f, c

    def row(self, form, text, w, path, kind, help_=""):
        lab = QLabel(text)
        if help_:
            lab.setToolTip(help_); w.setToolTip(help_)
        form.addRow(lab, w)
        return self.binder.bind(w, path, kind, lab)

    def table(self, v, path, cols):
        t = SimpleTable(self, v, path, cols)
        self.tables.append(t)
        return t

    def fill(self):
        self.binder.load()
        for t in self.tables:
            t.load()
        for f in getattr(self, "after_fill", []):
            f()
        self.dirty = False
        self._buttons()

    def changed(self):
        if not self.binder.loading:
            self.dirty = True
            self._buttons()

    def _buttons(self):
        self.b_save.setEnabled(self.dirty); self.b_undo.setEnabled(self.dirty)

    def save(self):
        self.store.save(self.work)
        diag.activity("std_layer_saved")
        self.host.toast(f"Saved: {self.store.what}")
        self.reload()
        return True

    def reload(self):
        self.work, self.base = self.store.load()
        self.fill()


def window(host, store, sections, title):
    """The editor in its own window (Formatting Standards and Effort Profiles open it from a button)."""
    from PySide6.QtWidgets import QDialog
    dlg = QDialog(host); dlg.setWindowTitle(title); dlg.resize(980, 720)
    v = QVBoxLayout(dlg)
    dlg.editor = LayerEditor(host, store, sections); v.addWidget(dlg.editor)
    return dlg
