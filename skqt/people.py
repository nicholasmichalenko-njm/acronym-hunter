"""The author list in Qt (2.77.0): the Settings card that keeps it (type names, import a list, export it, choose which
efforts each name shows in), and the pickers every page uses (authors, section leads and contributors, owners). A
picker offers only the names set to show in the open effort; with no effort open it says to select or create one.
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import authorlist as AL
import diag
from . import design as D

NO_EFFORT = "Select or create an effort first. Names come from the author list for the open effort (Settings > Author list)."
OFF_LIST = " (not on the author list)"


def _eff(host):
    """The open effort's name ('' when none is open)."""
    return host.effort_name if getattr(host, "ws", None) is not None else ""


def effort_names(host):
    return [n for n in host.efforts.names() if not (host.efforts.get(n) or {}).get("archived")]


def empty_text(host):
    return (f"No names show in {_eff(host)} yet. Add names in Settings > Author list, or set names there to show "
            "in this effort.")


# ---------------------------------------------------------------- pickers
def pick_names(host, current=(), title="Choose authors", multi=True, answer=None, parent=None):
    """The names to use, or None (cancelled, or nothing to pick from). current: names already set; one that is not on
    the list shows ticked and marked, so it can be kept or taken off. answer (tests): the names to return."""
    if not _eff(host):
        host.status(NO_EFFORT)
        if answer is None:
            QMessageBox.information(parent or host, title, NO_EFFORT)
        return None
    names = host.authors.for_effort(_eff(host))
    cur = [AL.clean(n) for n in current if AL.clean(n)]
    if not names and not cur:
        host.status(empty_text(host))
        if answer is None:
            box = QMessageBox(parent or host); box.setWindowTitle(title); box.setText(empty_text(host))
            go = box.addButton("Open the author list", QMessageBox.AcceptRole); box.addButton(QMessageBox.Close)
            box.exec()
            if box.clickedButton() is go:
                host.go("settings"); host.settings_page.focus_authors()
        return None
    if answer is not None:
        ok = [n for n in answer if host.authors.find(n) and n in names or n in cur]
        return ok if multi else ok[:1]
    d = QDialog(parent or host); d.setWindowTitle(title); d.setMinimumSize(420, 460)
    v = QVBoxLayout(d)
    v.addWidget(D.label(f"Names for {_eff(host)}, from the author list.", "muted"))
    flt = QLineEdit(); flt.setPlaceholderText("Find a name"); v.addWidget(flt)
    lw = QListWidget(); v.addWidget(lw, 1)
    keys = {n.casefold() for n in names}
    for n in names + [c for c in cur if c.casefold() not in keys]:
        it = QListWidgetItem(n + ("" if n.casefold() in keys else OFF_LIST)); it.setData(Qt.UserRole, n)
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked if n.casefold() in {c.casefold() for c in cur} else Qt.Unchecked)
        lw.addItem(it)
    flt.textChanged.connect(lambda t: [lw.item(i).setHidden(t.casefold() not in lw.item(i).text().casefold()) for i in range(lw.count())])
    if not multi:
        def one(changed):
            if changed.checkState() == Qt.Checked:
                for i in range(lw.count()):
                    if lw.item(i) is not changed:
                        lw.item(i).setCheckState(Qt.Unchecked)
        lw.itemChanged.connect(one)
    row = QHBoxLayout()
    edit = QPushButton("Edit the author list..."); edit.setFlat(True)
    edit.clicked.connect(lambda: (d.reject(), host.go("settings"), host.settings_page.focus_authors()))
    row.addWidget(edit); row.addStretch(1)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
    row.addWidget(bb); v.addLayout(row)
    d._list = lw
    if d.exec() != QDialog.Accepted:
        return None
    return [lw.item(i).data(Qt.UserRole) for i in range(lw.count()) if lw.item(i).checkState() == Qt.Checked]


def name_combo(host, current=""):
    """One name from the author list for the open effort (a lead, an owner). Not typed: the list is the only source.
    A current name that is not on the list stays as the choice, marked."""
    cb = QComboBox(); cb.setEditable(False)
    cb.addItem("", "")
    names = host.authors.for_effort(_eff(host)) if _eff(host) else []
    for n in names:
        cb.addItem(n, n)
    cur = AL.clean(current)
    if cur and cur.casefold() not in {n.casefold() for n in names}:
        cb.addItem(cur + OFF_LIST, cur)
    if cur:
        cb.setCurrentIndex(max(0, next((i for i in range(cb.count()) if (cb.itemData(i) or "").casefold() == cur.casefold()), 0)))
    if not names:
        cb.setToolTip(NO_EFFORT if not _eff(host) else empty_text(host))
    return cb


def combo_name(cb):
    return cb.currentData() or ""


class NamesField(QWidget):
    """Names shown as text with a Choose... button (Assign's Author(s), a section's contributors)."""

    def __init__(self, host, names=(), empty="", title="Choose authors", on_change=None):
        super().__init__()
        self.host, self.title, self.on_change, self.empty = host, title, on_change, empty
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
        self.lbl = QLabel(); self.lbl.setWordWrap(True); h.addWidget(self.lbl, 1)
        self.btn = D.button("Choose...", None, lambda: self.choose()); h.addWidget(self.btn)
        self.set_names(names)

    def set_names(self, names):
        self._names = [AL.clean(n) for n in names if AL.clean(n)]
        shown = [n + ("" if self.host.authors.on_list(n) else OFF_LIST) for n in self._names]
        self.lbl.setText(", ".join(shown) if shown else self.empty)

    def names(self):
        return list(self._names)

    def text(self):
        return ", ".join(self._names)

    def choose(self, answer=None):
        got = pick_names(self.host, self._names, self.title, answer=answer, parent=self)
        if got is None:
            return None
        self.set_names(got)
        if self.on_change:
            self.on_change(got)
        return got

    def setEnabled(self, on):                   # noqa: N802 (Qt name)
        super().setEnabled(on)
        self.btn.setEnabled(on)


# ---------------------------------------------------------------- the Settings card
class EffortsDialog(QDialog):
    """Where names show (2.87.0): All efforts, or the efforts ticked. With All efforts ticked every effort shows ticked
    and cannot be changed (they all apply). Unticking it brings back the efforts the names had (none for a name that
    showed in all efforts). Nothing changes until OK."""

    def __init__(self, parent, efforts, current, title):
        super().__init__(parent)
        self.setWindowTitle(title); self.setMinimumWidth(400)
        v = QVBoxLayout(self)
        self.alle = QCheckBox("All efforts (now and new ones)"); v.addWidget(self.alle)
        v.addWidget(D.label("Or only these efforts:", "muted"))
        cur = [] if current == AL.ALL else [x.casefold() for x in current or []]
        self.picked = {e for e in efforts if e.casefold() in cur}      # what the efforts boxes hold when All is off
        self.boxes = []
        for e in efforts:
            b = QCheckBox(e); b.toggled.connect(lambda _on, b=b: self._box(b)); v.addWidget(b); self.boxes.append(b)
        self.summary = D.label("", None); v.addWidget(self.summary)
        v.addWidget(D.label("Nothing changes until you click OK.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._quiet = False
        self.alle.toggled.connect(self._all)
        self.alle.setChecked(current == AL.ALL)
        self._all(current == AL.ALL)

    def _all(self, on):
        self._quiet = True
        for b in self.boxes:
            b.setChecked(True if on else b.text() in self.picked)
            b.setEnabled(not on)
        self._quiet = False
        self._say()

    def _box(self, b):
        if self._quiet or self.alle.isChecked():
            return
        (self.picked.add if b.isChecked() else self.picked.discard)(b.text())
        self._say()

    def _say(self):
        v = self.values()
        self.summary.setText("Shows in every effort, now and new ones." if v == AL.ALL else
                             ("Shows in: " + ", ".join(v)) if v else "Shows in no effort yet.")

    def values(self):
        return AL.ALL if self.alle.isChecked() else [b.text() for b in self.boxes if b.text() in self.picked]


class AuthorListCard(D.Card):
    def __init__(self, host):
        super().__init__("Author list", "The only place names come from. Author, section lead, contributor and owner "
                         "drop-downs show the names set to show in the open effort. To offer more people, add them here "
                         "or import an updated list: names already on the list stay as they are; only new names are added.",
                         actions=[D.button("Export the list...", None, lambda: self.export()),
                                  D.button("Import a list...", None, lambda: self.import_list()),
                                  D.button("Add names...", "primary", lambda: self.add_names())])
        self.host = host
        self.banner = self.add(D.label("", "crit")); self.banner.setWordWrap(True)
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["Name", "Shows in", "Added"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 240); self.table.setColumnWidth(1, 380); self.table.setColumnWidth(2, 110)
        self.table.setMinimumHeight(220)
        self.table.doubleClicked.connect(lambda _i: self.choose_efforts())
        self.add(self.table)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        self.edit_btn = D.button("Edit which efforts...", "primary", lambda: self.choose_efforts(),
                                 "Choose the efforts the selected name(s) show in: all efforts, or only the ones you tick")
        row.addWidget(self.edit_btn)
        for text, fn in (("Show in this effort", lambda: self.this_effort(True)),
                         ("Not in this effort", lambda: self.this_effort(False)), ("Rename...", self.rename), ("Remove", self.remove)):
            row.addWidget(D.button(text, None, lambda _=False, fn=fn: fn()))
        row.addStretch(1)
        self.body.addLayout(row)
        self.info = self.add(D.label("", "muted"))
        self.fill()

    @property
    def L(self):
        return self.host.authors

    def fill(self):
        effs = effort_names(self.host)
        if not effs:
            self.banner.setText("No effort exists yet. Create or select an effort first (Efforts > New effort... above), "
                                "then choose which efforts each name shows in (Edit which efforts...). Names added now show in all efforts.")
        elif not _eff(self.host):
            self.banner.setText("No effort is open. Select or create an effort first to see whose names show in it.")
        else:
            self.banner.setText("")
        self.banner.setVisible(bool(self.banner.text()))
        t = self.table
        t.setRowCount(0)
        for p in sorted(self.L.people, key=lambda p: p["name"].casefold()):
            r = t.rowCount(); t.insertRow(r)
            t.setItem(r, 0, QTableWidgetItem(p["name"]))
            t.setItem(r, 1, QTableWidgetItem(AL.efforts_text(p["efforts"])))
            t.setItem(r, 2, QTableWidgetItem(p.get("added", "")))
        here = _eff(self.host)
        n_here = len(self.L.for_effort(here)) if here else 0
        self.info.setText(f"{len(self.L.people)} name(s) on the list" + (f"; {n_here} show in {here}." if here else "."))

    def selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 0).text() for r in rows]

    def select(self, names):
        ks = {AL.key(n) for n in names}
        self.table.clearSelection()
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).text().casefold() in ks:
                self.table.selectRow(r)

    def _changed(self, msg):
        self.fill()
        self.host.toast(msg)
        try:
            self.host.authors_changed()
        except Exception:
            diag.swallowed()

    def _default_choice(self, title, text, answer=None):
        """Where new names show: this effort, all efforts, or chosen efforts. Returns ALL, a list, or None."""
        effs = effort_names(self.host)
        if answer is not None:
            return answer
        if not effs:
            return AL.ALL
        d = QDialog(self); d.setWindowTitle(title); v = QVBoxLayout(d)
        v.addWidget(QLabel(text))
        here = QRadioButton(f"This effort: {_eff(self.host)}") if _eff(self.host) else None
        alle = QRadioButton("All efforts"); pick = QRadioButton("Choose efforts...")
        for b in (here, alle, pick):
            if b is not None:
                v.addWidget(b)
        (here or alle).setChecked(True)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        v.addWidget(bb)
        if d.exec() != QDialog.Accepted:
            return None
        if here is not None and here.isChecked():
            return [_eff(self.host)]
        if alle.isChecked():
            return AL.ALL
        return self._effort_dialog([], "Show the new names in")

    def add_names(self, text=None, efforts=None):
        """Type one name per line (or names separated by semicolons)."""
        if text is None:
            d = QDialog(self); d.setWindowTitle("Add names"); d.setMinimumWidth(460); v = QVBoxLayout(d)
            v.addWidget(QLabel("One name per line, as people should see it (for example Joe Garcia)."))
            from PySide6.QtWidgets import QPlainTextEdit
            ed = QPlainTextEdit(); ed.setFixedHeight(160); v.addWidget(ed)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return None
            text = ed.toPlainText()
        entries = [(x, None) for ln in text.splitlines() for x in ln.split(";") if x.strip()]
        if not entries:
            return None
        eff = self._default_choice("Add names", "Where should the new names show?", efforts)
        if eff is None:
            return None
        res = self.L.merge(entries, default=eff, source="typed")
        diag.activity("authors_added", added=len(res["added"]))
        self._changed(f"{len(res['added'])} name(s) added" + (f"; {len(res['kept'])} already on the list" if res["kept"] else ""))
        self.select(res["added"])
        return res

    def import_list(self, path=None, efforts=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import a list of names", "", "Lists (*.xlsx *.csv *.txt)")
            if not path:
                return None
        try:
            entries = AL.read_file(path)
        except Exception as e:
            diag.swallowed()
            self.host.status(f"The list could not be read ({type(e).__name__}). Use a .txt, .csv or .xlsx file with a Name column.")
            return None
        new = [(n, e) for n, e in entries if AL.clean(n) and not self.L.find(n)]
        need_default = any(e is None for _n, e in new)
        eff = AL.ALL
        if new and need_default:
            eff = self._default_choice("Import a list", f"{len(new)} new name(s) found; names already on the list stay as "
                                       "they are. Where should the new names show?", efforts)
            if eff is None:
                return None
        res = self.L.merge(entries, default=eff, source="imported: " + os.path.basename(path))
        diag.activity("authors_imported", added=len(res["added"]), n=len(res["kept"]))
        self._changed(f"Imported: {len(res['added'])} new name(s) added; {len(res['kept'])} already on the list, kept as they are"
                      + (f"; {res['skipped']} line(s) were not names" if res["skipped"] else ""))
        self.select(res["added"])
        return res

    def export(self, path=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the author list", "Author list.xlsx", "Excel (*.xlsx);;CSV (*.csv)")
            if not path:
                return None
        n = self.L.export(path)
        diag.activity("authors_exported", n=n)
        self.host.toast(f"Author list exported: {n} name(s)")
        return n

    def _effort_dialog(self, current, title, answer=None):
        """Tick the efforts (or All efforts). Returns ALL, a list, or None."""
        effs = effort_names(self.host)
        if not effs:
            if answer is None:
                QMessageBox.information(self, title, "Create or select an effort first (Efforts > New effort... above). "
                                        "Until then every name shows in all efforts.")
            self.host.status("Create or select an effort first.")
            return None
        if answer is not None:
            return answer
        d = EffortsDialog(self, effs, current, title)
        if d.exec() != QDialog.Accepted:
            return None
        return d.values()

    def choose_efforts(self, names=None, answer=None):
        names = names if names is not None else self.selected()
        if not names:
            self.host.status("Select one or more names first.")
            return None
        p = self.L.find(names[0])
        eff = self._effort_dialog(p["efforts"] if p else [], f"Where {names[0]} shows" if len(names) == 1 else f"Where {len(names)} names show", answer)
        if eff is None:
            return None
        n = self.L.set_efforts(names, eff)
        diag.activity("authors_efforts_set", n=n)
        self._changed(f"{n} name(s) now show in {AL.efforts_text(eff)}")
        self.select(names)
        return eff

    def this_effort(self, on, names=None):
        here = _eff(self.host)
        if not here:
            self.host.status(NO_EFFORT)
            QMessageBox.information(self, "Author list", NO_EFFORT) if names is None else None
            return 0
        names = names if names is not None else self.selected()
        n = sum(self.L.show_in(nm, here, on, effort_names(self.host)) for nm in names)
        diag.activity("authors_effort_toggled", n=n)
        self._changed(f"{n} name(s) " + ("now show" if on else "no longer show") + f" in {here}")
        self.select(names)
        return n

    def rename(self, old=None, new=None):
        old = old or next(iter(self.selected()), None)
        if not old:
            self.host.status("Select a name first.")
            return False
        if new is None:
            new, ok = QInputDialog.getText(self, "Rename", "New spelling:", text=old)
            if not ok:
                return False
        ok = self.L.rename(old, new)
        if ok:
            diag.activity("authors_renamed")
            self._changed("Renamed. Sentences already assigned keep the old spelling until reassigned.")
        else:
            self.host.status("That name is empty or already on the list.")
        return ok

    def remove(self, names=None, answer=None):
        names = names if names is not None else self.selected()
        if not names:
            self.host.status("Select one or more names first.")
            return 0
        if answer is None and QMessageBox.question(self, "Remove", f"Take {len(names)} name(s) off the author list? Sentences "
                                                   "already assigned to them keep their names.") != QMessageBox.Yes:
            return 0
        n = self.L.remove(names)
        diag.activity("authors_removed", n=n)
        self._changed(f"{n} name(s) taken off the list")
        return n
