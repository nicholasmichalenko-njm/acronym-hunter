"""The template library's forms (3.22.0): a style made or edited, an item's values, an item's versions, and a style's
preview. 3.44.0: Import is one browser of the file (importbrowser.py) and the library a page (templatelibview.py).
The rules are templatelib.py's; nothing leaves the PC."""
import os, sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import templatelib as TL
from . import design as D

STATE = {"new": ("New", "accent"), "same": ("Already in the library", "ok"), "variant": ("Variant (same name, other values)", "warn")}


def installed_fonts():
    try:
        return list(QFontDatabase.families())
    except Exception:                                    # noqa: BLE001
        diag.swallowed()
        return None


class StyleDialog(QDialog):
    """A style's definition, every property of the style library (blank: not set)."""

    def __init__(self, parent, name, values, fixed_name=False):
        super().__init__(parent)
        from .prodstdpage import STYLE_COLS, TRI_KEYS
        self.cols, self.tri = [c for c in STYLE_COLS if c[0] != "key"], TRI_KEYS
        self.setWindowTitle("Style"); self.resize(560, 680)
        v = QVBoxLayout(self)
        f = QFormLayout()
        from PySide6.QtWidgets import QScrollArea
        sc = QScrollArea(); sc.setWidgetResizable(True); inner = QWidget(); inner.setLayout(f); sc.setWidget(inner); v.addWidget(sc, 1)
        self.name = QLineEdit(name); self.name.setReadOnly(fixed_name); f.addRow("Name", self.name)
        self.ed = {}
        for key, label, kind in self.cols:
            if isinstance(kind, tuple):
                cb = QComboBox()
                for val, txt in kind[1]:
                    cb.addItem(txt, val)
                cur = values.get(key)
                cur = ("on" if cur else "off") if key in self.tri and cur is not None else (cur or "")
                cb.setCurrentIndex(max(0, cb.findData(cur)))
                self.ed[key] = cb
            else:
                le = QLineEdit("" if values.get(key) is None else str(values.get(key)))
                self.ed[key] = le
            f.addRow(label, self.ed[key])
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        from .prodstdpage import tabs_parse
        out = {}
        for key, _label, kind in self.cols:
            w = self.ed[key]
            if isinstance(w, QComboBox):
                val = w.currentData()
                if val in ("", None):
                    continue
                out[key] = (val == "on") if key in self.tri else val
            else:
                t = w.text().strip()
                if not t:
                    continue
                if kind == "num0":
                    try:
                        out[key] = float(t)
                    except ValueError:
                        continue
                elif key == "tabs":
                    out[key] = tabs_parse(t)
                else:
                    out[key] = t
        return " ".join(self.name.text().split()), out


class ValuesDialog(QDialog):
    """An item's values, one by one (lists and groups shown as they are, to edit with care)."""

    def __init__(self, parent, name, values):
        super().__init__(parent)
        import json
        self.json = json
        self.setWindowTitle(f"Edit: {name}"); self.resize(620, 520)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each value as it is kept. Numbers in points or inches as shown; a group stays in brackets.", "muted"))
        self.t = QTableWidget(0, 2); self.t.setHorizontalHeaderLabels(["Value", "Setting"])
        self.t.verticalHeader().setVisible(False); self.t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.keys = []
        for k, val in values.items():
            if str(k).startswith("_") or k in ("xml",):
                continue
            r = self.t.rowCount(); self.t.insertRow(r)
            a = QTableWidgetItem(str(k)); a.setFlags(Qt.ItemIsEnabled); self.t.setItem(r, 0, a)
            self.t.setItem(r, 1, QTableWidgetItem(val if isinstance(val, str) else json.dumps(val)))
            self.keys.append(k)
        self.base = dict(values)
        v.addWidget(self.t, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        out = dict(self.base)
        for r, k in enumerate(self.keys):
            t = self.t.item(r, 1).text()
            if isinstance(self.base[k], str):
                out[k] = t
            else:
                try:
                    out[k] = self.json.loads(t)
                except ValueError:
                    pass
        return out


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def preview_html(lib, iid):
    if not iid or str(iid).startswith("kit:"):
        k = lib.kit(str(iid)[4:]) if iid else None
        return f"<b>{_esc(k['name'])}</b>: {len(k['items'])} item(s)" if k else ""
    it = lib.get(iid)
    v = lib.values(it) if it else None
    if it is None or v is None:
        return ""
    if it["kind"] == "style":
        css = []
        if v.get("font") and not str(v["font"]).startswith("+"):
            css.append(f"font-family:'{_esc(v['font'])}'")
        if isinstance(v.get("size"), (int, float)):
            css.append(f"font-size:{v['size']}pt")
        if v.get("bold"):
            css.append("font-weight:bold")
        if v.get("italic"):
            css.append("font-style:italic")
        if v.get("color") and str(v["color"]).upper() != "AUTO":
            css.append(f"color:#{_esc(v['color'])}")
        if v.get("caps"):
            css.append("text-transform:uppercase")
        if v.get("hidden"):
            css.append("text-decoration:underline dotted")
        sample = _esc(it["name"]) + ": The Offeror shall describe its technical approach."
        return (f"<div style=\"{';'.join(css)}\">{sample}</div>"
                + (f"<div style='color:{D.tokens()['muted']}'>Hidden text: shows only with Show/Hide on.</div>" if v.get("hidden") else ""))
    if it["kind"] == "font":
        return f"<div style=\"font-family:'{_esc(v.get('font', ''))}';font-size:14pt\">{_esc(v.get('font', ''))}: Aa Bb Cc 0123456789</div>"
    if it["kind"] == "theme":
        sw = "".join(f"<span style='background:#{c};color:#{c}'>&nbsp;&nbsp;&nbsp;&nbsp;</span>&nbsp;" for c in v.get("colors", {}).values())
        return f"<div>{sw}</div><div>Headings: {_esc(v.get('major') or '-')}; body: {_esc(v.get('minor') or '-')}</div>"
    return f"<b>{_esc(it['name'])}</b>: {_esc(it.get('summary', ''))}"


class VersionsDialog(QDialog):
    """3.33.0: a library item's versions, newest first: who kept each and when, its label and note; Label... names the
    selected one; Compare lists every value that differs between the two selected."""

    def __init__(self, parent, lib, iid):
        super().__init__(parent)
        self.lib = lib
        it = lib.get(iid)
        self.setWindowTitle(f"Versions of {lib.base_of(it)}"); self.resize(820, 560)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Every version is kept whole; nothing is overwritten. A template profile uses the version it is "
                            "pinned to until you choose a newer one.", "muted"))
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Version", "Label", "Kept", "Note"])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QTableWidget.SelectRows)
        self.t.setSelectionMode(QAbstractItemView.ExtendedSelection); self.t.setEditTriggers(QTableWidget.NoEditTriggers)
        self.t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        v.addWidget(self.t, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Label...", None, lambda: self.label()))
        row.addWidget(D.button("Compare the two selected", "primary", lambda: self.compare()))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); row.addWidget(bb)
        self.diff = QTableWidget(0, 3); self.diff.setHorizontalHeaderLabels(["Value", "", ""])
        self.diff.verticalHeader().setVisible(False); self.diff.setEditTriggers(QTableWidget.NoEditTriggers)
        self.diff.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        v.addWidget(self.diff, 1)
        self.iid = iid
        self.fill()

    def fill(self):
        self.fam = self.lib.family(self.iid)
        self.t.setRowCount(0)
        for i in self.fam:
            r = self.t.rowCount(); self.t.insertRow(r)
            for c, s in enumerate((f"v{i.get('version', 1)}", i.get("label", ""), f"{str(i.get('at', ''))[:16]} {i.get('by', '')}".strip(),
                                   i.get("note", ""))):
                cell = QTableWidgetItem(s)
                if c == 0:
                    cell.setData(Qt.UserRole, i["id"])
                self.t.setItem(r, c, cell)
        return len(self.fam)

    def picked(self):
        return [self.t.item(x.row(), 0).data(Qt.UserRole) for x in self.t.selectionModel().selectedRows()]

    def label(self, text=None, note=None):
        ids = self.picked()
        if not ids:
            return False
        it = self.lib.get(ids[0])
        if text is None:
            text, ok = QInputDialog.getText(self, "Label", "Label for this version:", text=it.get("label", ""))
            if not ok:
                return False
        ok = self.lib.set_label(ids[0], text, note)
        self.fill()
        return ok

    def compare(self, a=None, b=None):
        if a is None or b is None:
            ids = self.picked()
            if len(ids) != 2:
                return []
            a, b = ids
        A, B = self.lib.get(a), self.lib.get(b)
        rows = self.lib.compare(a, b)
        self.diff.setHorizontalHeaderLabels(["Value", f"v{A.get('version')}", f"v{B.get('version')}"])
        self.diff.setRowCount(0)
        for k, x, y in rows:
            r = self.diff.rowCount(); self.diff.insertRow(r)
            for c, s in enumerate((k, "" if x is None else str(x), "" if y is None else str(y))):
                self.diff.setItem(r, c, QTableWidgetItem(s[:200]))
        if not rows:
            self.diff.insertRow(0); self.diff.setItem(0, 0, QTableWidgetItem("The two versions hold the same values."))
        return rows
