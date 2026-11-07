"""Production Standards > Template profile (3.33.0): the profile being edited as the parts a template is built from,
each filled from a version kept in the template library and pinned to it (Parts and versions), and the content map that
says which style each kind of placed item takes, whether it is hidden, and whether it goes in the file (Content map).
The rules are templateprofile.py's and setuptemplate.options; nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
                               QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

import diag
import templatelib as TL
import templateprofile as TP
from . import design as D


def _lib(page):
    return TL.Library(page.host.config_dir)


def _reload(page):
    """The other menus show what a slot just changed."""
    page.changed()
    for f in (lambda: page.binder.load(), page.load_tables, page.show_parts, page.fill_row_scope):
        try:
            f()
        except Exception:  # noqa: BLE001
            diag.swallowed()


class PickDialog(QDialog):
    """A slot's choices: each family with its versions, newest first, and the version in use marked."""

    def __init__(self, parent, lib, slot, current=None):
        super().__init__(parent)
        self.setWindowTitle("Pick from the library"); self.resize(560, 420)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each family with its versions, newest first. The profile is pinned to the version you pick: a newer "
                            "one waits until you choose it.", "muted"))
        self.list = QListWidget(); v.addWidget(self.list, 1)
        for i in TP.choices(lib, slot):
            w = QListWidgetItem(lib.shown_name(i) + (f"   ({i.get('by', '')}, {str(i.get('at', ''))[:10]})" if i.get("at") else "")
                                + ("   in use" if current and current == i["id"] else ""))
            w.setData(Qt.UserRole, i["id"]); w.setToolTip(i.get("note") or i.get("summary") or "")
            self.list.addItem(w)
        if not self.list.count():
            self.list.addItem(QListWidgetItem("Nothing on this shelf yet: Import from a file, or Save as a new version."))
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def picked(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it is not None else None


class VersionDialog(QDialog):
    """Save as a new version: the family's name (when it has none yet), a label and a note."""

    def __init__(self, parent, need_name, name=""):
        super().__init__(parent)
        self.setWindowTitle("Save as a new version"); self.setMinimumWidth(460)
        f = QFormLayout(self)
        self.name = QLineEdit(name); self.name.setPlaceholderText("The family's name, such as Volume cover")
        if need_name:
            f.addRow("Name", self.name)
        self.label = QLineEdit(); self.label.setPlaceholderText("Space Force 2026, 11 pt body...")
        f.addRow("Label", self.label)
        self.note = QLineEdit(); self.note.setPlaceholderText("What changed (optional)")
        f.addRow("Note", self.note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)


class ProfileParts(QWidget):
    COLS = ["Part", "What", "In use", "Newer", ""]

    def __init__(self, page):
        super().__init__()
        self.page = page
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        c = D.Card("Parts and versions", "The parts a template made from this profile is built from, in the order a response runs. "
                   "Each part holds the profile's own values or a version from the template library, pinned: a newer version "
                   "waits until you choose Use it. Save as a new version keeps what the part holds now in the library.")
        v.addWidget(c)
        self.sum = D.label("", "muted"); c.add(self.sum)
        self.t = QTableWidget(0, len(self.COLS)); self.t.setHorizontalHeaderLabels(self.COLS)
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        for i, w in enumerate((110, 170, 210, 80)):
            self.t.setColumnWidth(i, w)
        self.t.setWordWrap(True)
        self.t.setMinimumHeight(420)
        c.add(self.t)
        self.slots = []

    def refresh(self):
        import prodparts as PP
        work = self.page.work or {}
        lib = _lib(self.page)
        pdir = PP.parts_dir(self.page.host.config_dir)
        self.slots = TP.slots(work)
        self.t.setRowCount(0)
        pinned = 0
        for slot, part, what, _kind in self.slots:
            stt = TP.state(work, lib, slot)
            r = self.t.rowCount(); self.t.insertRow(r)
            use = lib.shown_name(stt["item"]) if stt["item"] is not None else (
                "a version no longer in the library" if stt["pin"] else ("the profile's own values" if TP.current_values(work, slot, pdir) else "not set"))
            pinned += stt["item"] is not None
            for c, text in enumerate((part, what, use, (f"v{stt['newer']['version']} saved" if stt["newer"] else ""))):
                it = QTableWidgetItem(text); it.setData(Qt.UserRole, slot)
                if c == 3 and stt["newer"]:
                    it.setForeground(D.color("warn"))
                self.t.setItem(r, c, it)
            cell = QWidget(); h = QHBoxLayout(cell); h.setContentsMargins(2, 0, 2, 0); h.setSpacing(4)
            h.addWidget(D.button("Pick...", None, lambda _=False, s_=slot: self.pick(s_), "A version from the template library"))
            if stt["newer"]:
                h.addWidget(D.button(f"Use v{stt['newer']['version']}", "primary", lambda _=False, s_=slot: self.use_newer(s_)))
            h.addWidget(D.button("Save as a new version...", None, lambda _=False, s_=slot: self.save_version(s_)))
            if stt["pin"]:
                h.addWidget(D.button("Own values", "ghost", lambda _=False, s_=slot: self.unpin(s_),
                                     "Keep the values the part has as this profile's own; the pin comes off"))
            h.addStretch(1)
            self.t.setCellWidget(r, 4, cell)
        self.t.resizeRowsToContents()
        self.sum.setText(f"{pinned} of {len(self.slots)} parts pinned to a library version.")

    def _row(self, slot):
        return next((n for n, s in enumerate(self.slots) if s[0] == slot), -1)

    def pick(self, slot, iid=None):
        lib = _lib(self.page)
        if iid is None:
            d = PickDialog(self, lib, slot, (TP.pins(self.page.work).get(slot) or {}).get("id"))
            if d.exec() != QDialog.Accepted:
                return ""
            iid = d.picked()
        if not iid:
            return ""
        said = TP.pick(self.page.work, lib, slot, iid, self.page.host.config_dir)
        _reload(self.page)
        self.refresh()
        diag.activity("profile_slot_picked")
        return said

    def use_newer(self, slot):
        lib = _lib(self.page)
        stt = TP.state(self.page.work, lib, slot)
        return self.pick(slot, stt["newer"]["id"]) if stt["newer"] else ""

    def save_version(self, slot, name=None, label=None, note=""):
        import prodparts as PP
        lib = _lib(self.page)
        need = TP.state(self.page.work, lib, slot)["item"] is None
        if label is None:
            d = VersionDialog(self, need, next((w for s, _p, w, _k in self.slots if s == slot), slot))
            if d.exec() != QDialog.Accepted:
                return None
            name, label, note = d.name.text().strip(), d.label.text().strip(), d.note.text().strip()
        item, st = TP.save_version(self.page.work, lib, slot, name or "", label or "", note or "", PP.parts_dir(self.page.host.config_dir))
        if item is None:
            self.page.host.status("That part holds nothing yet to keep.")
            return None
        self.page.changed()
        self.refresh()
        self.page.host.toast(("Kept as " if st != "same" else "Already kept as ") + lib.shown_name(item) + " in the template library.")
        diag.activity("profile_version_saved")
        return item

    def unpin(self, slot):
        ok = TP.unpin(self.page.work, slot)
        self.page.changed()
        self.refresh()
        return ok


class ContentMap(QWidget):
    COLS = ["What is placed", "Style", "Hidden", "In the file"]

    def __init__(self, page):
        super().__init__()
        self.page = page
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        c = D.Card("Content map", "What each kind of item Review and Setup place becomes in a setup made on the "
                   "template: its style, whether it is hidden (it shows only with Show/Hide on), and whether it goes in the "
                   "file at all. Section headings take Heading 1 to 9 (Word's table of contents and numbering use them) and "
                   "appendices Appendix Heading 1 to 9. A style that is not in the template is added. On This effort, a change "
                   "is this effort's only.")
        v.addWidget(c)
        self.t = QTableWidget(0, len(self.COLS)); self.t.setHorizontalHeaderLabels(self.COLS)
        self.t.verticalHeader().setVisible(False)
        self.t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.t.setColumnWidth(1, 220); self.t.setColumnWidth(2, 80); self.t.setColumnWidth(3, 90)
        self.t.setMinimumHeight(460)
        c.add(self.t)
        self.keys = []
        self._loading = False

    def rows(self):
        """(key, what): the kinds, then a row of its own for each capture (it follows Captures unless set)."""
        import setuptemplate as ST
        import excerpts as EX
        out = [(k, label) for k, label, _s, _c, _i in ST.KINDS]
        bins = []
        try:
            bins = EX.bins(None, self.page.host.config_dir)
        except Exception:  # noqa: BLE001
            bins = [{"id": k, "name": n} for k, n, _f in EX.BUILTIN]
        for b in bins:
            if b["id"] != "objective":
                out.append((f"cap:{b['id']}", f"   Capture: {b['name']}"))
        return out

    def refresh(self):
        import setuptemplate as ST
        opts = ST.options(None, self.page.work)
        cmap = (self.page.work or {}).get("content_map") or {}
        self._loading = True
        self.t.setRowCount(0)
        self.keys = []
        for k, what in self.rows():
            o = opts.get(k) or opts["capture"]
            r = self.t.rowCount(); self.t.insertRow(r)
            it = QTableWidgetItem(what); it.setFlags(Qt.ItemIsEnabled)
            if k.startswith("cap:") and k not in cmap:
                it.setForeground(D.color("muted")); it.setToolTip("Follows the Captures row until you change it")
            self.t.setItem(r, 0, it)
            e = QLineEdit(o["style"]); e.editingFinished.connect(lambda k_=k: self.write(k_)); self.t.setCellWidget(r, 1, e)
            for col, key in ((2, "hidden"), (3, "include")):
                cb = QCheckBox(); cb.setChecked(bool(o.get(key, True))); cb.toggled.connect(lambda _v, k_=k: self.write(k_))
                self.t.setCellWidget(r, col, cb)
            self.keys.append(k)
        self._loading = False

    def write(self, k):
        if self._loading or k not in self.keys:
            return None
        r = self.keys.index(k)
        o = {"style": " ".join(self.t.cellWidget(r, 1).text().split())[:60], "hidden": self.t.cellWidget(r, 2).isChecked(),
             "include": self.t.cellWidget(r, 3).isChecked()}
        if not o["style"]:
            return None
        self.page.work.setdefault("content_map", {})[k] = o
        self.page.changed()
        if hasattr(self.page, "std_preview"):
            self.page.std_preview.refresh()
        return o

    def set_row(self, k, style=None, hidden=None, include=None):
        """Tests and keys: set a row as a person would."""
        r = self.keys.index(k)
        if style is not None:
            self.t.cellWidget(r, 1).setText(style); self.write(k)
        if hidden is not None:
            self.t.cellWidget(r, 2).setChecked(hidden)
        if include is not None:
            self.t.cellWidget(r, 3).setChecked(include)
        return self.page.work.get("content_map", {}).get(k)
