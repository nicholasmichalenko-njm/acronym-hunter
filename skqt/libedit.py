"""The full editors of a library item (3.49.0): a style's every property with where it comes from (Set here, or from
the style it is based on) and Reset; any other item as a tree of its values, the plain ones edited in place. Each holds
the values being edited; edited() is called with the new values after every change. Rules live in libstyle.py."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import libstyle as LS
from . import design as D


class StyleEditor(QWidget):
    def __init__(self, edited=None):
        super().__init__()
        self.edited = edited or (lambda _v: None)
        self.lib = self.item = None
        self.values = {}
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.chain_lab = D.label("", "muted"); v.addWidget(self.chain_lab)
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Property", "Value", "Comes from", ""])
        self.t.verticalHeader().setVisible(False); self.t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.t.horizontalHeader().setMinimumSectionSize(40)
        self.t.setColumnWidth(0, 140); self.t.setColumnWidth(2, 130); self.t.setColumnWidth(3, 60)
        self.t.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(self.t, 1)
        self.widgets = {}

    def set_item(self, lib, item, values):
        self.lib, self.item, self.values = lib, item, dict(values or {})
        ch = LS.chain(lib, item, self.values)
        self.chain_lab.setText(("Based on: " + " > ".join(n + ("" if b is not None else " (not in the library)") for n, b, _v in ch))
                               if ch else "Based on no other style: every value is its own.")
        self.t.setRowCount(0)
        self.widgets = {}
        names = sorted({lib.base_of(i) for i in lib.items if i["kind"] == "style"}, key=str.casefold)
        for key, label, kind in LS.PROPS:
            r = self.t.rowCount(); self.t.insertRow(r)
            self.t.setItem(r, 0, QTableWidgetItem(label))
            w = self._widget(key, kind, names)
            self.t.setCellWidget(r, 1, w)
            b = QPushButton("Reset"); b.setToolTip("Put back the value of the style it is based on")
            b.clicked.connect(lambda _c=False, k=key: self.reset(k))
            self.t.setCellWidget(r, 3, b)
            self.widgets[key] = (w, kind, r, b)
        self.show_origins()

    def _widget(self, key, kind, names):
        val = self.values.get(key)
        if kind == "bool":
            cb = QComboBox()
            for t in ("Not set", "On", "Off"):
                cb.addItem(t)
            cb.setCurrentIndex({True: 1, False: 2}.get(val, 0) if isinstance(val, bool) else 0)
            cb.currentIndexChanged.connect(lambda i, k=key: self.set(k, [None, True, False][i]))
            return cb
        if kind in ("type", "align", "line_rule", "stylename"):
            cb = QComboBox()
            opts = [("", "Not set")] + [(n, n) for n in names] if kind == "stylename" else LS.CHOICES[kind]
            for data, text in opts:
                cb.addItem(text, data)
            if val and cb.findData(val) < 0:
                cb.addItem(str(val), val)
            cb.setCurrentIndex(max(0, cb.findData(val if val is not None else "")))
            cb.currentIndexChanged.connect(lambda _i, k=key, c=cb: self.set(k, c.currentData() or None))
            return cb
        e = QLineEdit("" if val is None else (LS.json.dumps(val) if isinstance(val, (list, dict)) else str(val)))
        e.editingFinished.connect(lambda k=key, w=e, kd=kind: self.typed(k, w, kd))
        return e

    def typed(self, key, w, kind):
        try:
            val = LS.parse(kind, w.text())
        except ValueError:
            w.setText("" if self.values.get(key) is None else str(self.values.get(key)))
            return
        if key in ("tabs",) and val:
            try:
                val = LS.json.loads(val)
            except ValueError:
                pass
        self.set(key, val)

    def set(self, key, val):
        if self.values.get(key) == val:
            return
        self.values = LS.set_value(self.values, key, val)
        self.show_origins()
        self.edited(self.values)

    def reset(self, key):
        self.values = LS.reset(self.lib, self.item, self.values, key)
        self.set_item(self.lib, self.item, self.values)
        self.edited(self.values)

    def show_origins(self):
        orig = LS.origins(self.lib, self.item, self.values)
        for key, (w, _kind, r, b) in self.widgets.items():
            where, base = orig.get(key, ("", None))
            txt = "Set here" if where == "here" else (where[:1].upper() + where[1:] if where else
                                                     ("Not set" if base is None else f"Not set (base: {base})"))
            it = QTableWidgetItem(txt); it.setForeground(D.color("accent" if where == "here" else "muted"))
            self.t.setItem(r, 2, it)
            b.setEnabled(where == "here" and key not in LS.OWN and bool(LS.chain(self.lib, self.item, self.values)))

    def where(self, key):
        """'Set here', 'From Body Text' or 'Not set' (tests)."""
        return self.t.item(self.widgets[key][2], 2).text()


class TreeEditor(QTreeWidget):
    """Any item's values as a tree; double-click a plain value to change it."""
    def __init__(self, edited=None, said=None):
        super().__init__()
        self.edited = edited or (lambda _v: None)
        self.said = said or (lambda _t: None)
        self.values = {}
        self.setColumnCount(2); self.setHeaderLabels(["What", "Value"])
        self.header().setSectionResizeMode(1, QHeaderView.Stretch); self.setColumnWidth(0, 230)
        self.itemChanged.connect(self._changed)
        self._loading = False

    def set_values(self, values):
        self._loading = True
        self.values = values if isinstance(values, (dict, list)) else {}
        self.clear()
        nodes = {(): self.invisibleRootItem()}
        for path, what, shown, editable in LS.rows(self.values):
            it = QTreeWidgetItem([what, shown])
            it.setData(0, Qt.UserRole, path)
            if editable:
                it.setFlags(it.flags() | Qt.ItemIsEditable)
            else:
                it.setForeground(1, D.color("muted"))
            nodes.get(path[:-1], self.invisibleRootItem()).addChild(it)
            nodes[path] = it
        self.expandToDepth(1)
        self._loading = False

    def _changed(self, it, col):
        if self._loading or col != 1:
            return
        path = it.data(0, Qt.UserRole)
        try:
            self.values = LS.set_path(self.values, tuple(path), it.text(1))
        except (ValueError, KeyError, IndexError, TypeError) as e:
            self.said(f"That value does not fit ({e}).")
            self._loading = True
            v = LS.get_path(self.values, tuple(path))
            it.setText(1, "" if v is None else ("yes" if v is True else "no" if v is False else str(v)))
            self._loading = False
            return
        self.edited(self.values)

    def edit_path(self, path, text):
        """Tests: set the value at path as if typed."""
        def walk(node):
            for i in range(node.childCount()):
                c = node.child(i)
                if tuple(c.data(0, Qt.UserRole)) == tuple(path):
                    return c
                f = walk(c)
                if f is not None:
                    return f
            return None
        it = walk(self.invisibleRootItem())
        if it is not None:
            it.setText(1, text)
        return it is not None


class Editor(QWidget):
    """The editor for any item: the style editor for a style, the tree for the rest."""
    def __init__(self, edited=None, said=None):
        super().__init__()
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.style_ed = StyleEditor(edited); self.tree_ed = TreeEditor(edited, said)
        v.addWidget(self.style_ed, 1); v.addWidget(self.tree_ed, 1)
        self.style_ed.hide(); self.tree_ed.hide()

    def set_item(self, lib, item, values):
        is_style = item is not None and item["kind"] == "style"
        self.style_ed.setVisible(is_style); self.tree_ed.setVisible(item is not None and not is_style)
        if item is None:
            return
        if is_style:
            self.style_ed.set_item(lib, item, values)
        else:
            self.tree_ed.set_values(values)

    def values(self):
        return self.style_ed.values if self.style_ed.isVisibleTo(self) else self.tree_ed.values


def row_buttons(*buttons):
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
    for b in buttons:
        h.addWidget(b)
    h.addStretch(1)
    return w
