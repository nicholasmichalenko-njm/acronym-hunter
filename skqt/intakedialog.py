"""Documents > Add (2.83.0 as the library's review table; moved out of librarypage in 4.83.0). One table for every file
before anything is added, rows set one at a time or many at once.

4.83.0 (steps I1 and D3; claude/stationkeeper-document-intake-direction-2026-11-24.md and
claude/stationkeeper-deliverables-that-act-and-the-documents-door-direction-2026-11-25.md; UX decisions 183, 187, 215,
216, 251): the window is "Add documents", with no paragraph and Purpose first. A new version follows its document,
so its deliverable follows it too and is not asked. Version (was "What it is") says New
document or New version of a document here; the same file already added is said by the app and cannot be changed; Skip
is gone and a row is taken out with its x. Purpose is decision 216's list (was "Used for"). Initial and Type show only
for a Customer document; a new version shows its initial as words. A file given Form to fill in, File to submit or
Redline to return shows Deliverable: the app's suggestion, another from the list, or New. Rules only (No AI); nothing
leaves the PC.

4.84.0 (step I2): Part of and Arrived as, a strip above the table for every file from the customer, and an Arrived as
cell on each row that follows it (skqt/releasestrip.py). Shown only in an effort.

4.85.0 (step I3): a New version of a customer document says Compare with, ticked, and the version it is compared with
("Final RFP"); after the add, the summary (skqt/intakesummary.py) offers the ticked ones in What changed. Shown only in an
effort, like the strip."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)
import docintake as DI
import docversions as DV
import delivdoor as DD
import docpackages as DP
from . import design as D
from . import releasestrip as RS
from .doctypeui import type_box

COLS = ["File", "Purpose", "Deliverable", "Version", "Arrived as", "Compare with", "Source", "Initial", "Type", "Name", "Tags", ""]
C_FILE, C_PURPOSE, C_DELIV, C_VERSION, C_ARRIVED, C_COMPARE, C_SOURCE, C_INI, C_TYPE, C_NAME, C_TAGS, C_OUT = range(len(COLS))   # noqa: E501


def _item(text, tip=""):
    it = QTableWidgetItem(text)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    if tip:
        it.setToolTip(tip)
    return it


class _Either(QWidget):
    """A cell that shows its control, or a few words in its place when the control is not needed (decision 187)."""

    def __init__(self, control):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        self.control, self.words = control, QLabel("")
        self.words.setProperty("role", "muted")
        h.addWidget(control); h.addWidget(self.words)
        self.words.hide()

    def show_control(self, on, words=""):
        self.control.setVisible(on)
        self.words.setVisible(not on)
        self.words.setText("" if on else words)


class IntakeDialog(QDialog):
    """Add documents: Purpose, Deliverable, Version, Source, and for a Customer document its initial and type."""

    def __init__(self, parent, plan, lib, rec=None):
        super().__init__(parent)
        self.setWindowTitle("Add documents")
        self.resize(1420, 720)
        self.plan, self.lib, self.rec = plan, lib, rec
        v = QVBoxLayout(self)
        names = [os.path.basename(e["path"]) for e in plan if e.get("category", "customer") in DP.CUSTOMER_SIDE]
        self.strip = RS.ReleaseStrip(lib, names)               # 4.84.0: Part of and Arrived as
        self.strip.changed.connect(self.follow_strip)
        v.addWidget(self.strip)
        bulk = QHBoxLayout(); v.addLayout(bulk)
        bulk.addWidget(D.label("Selected rows:", "label", wrap=False))
        self.b_role = QComboBox(); self.b_role.addItem("Purpose...", "")
        for k, n in DV.ADD_USES:
            self.b_role.addItem(n, k)
        self.b_role.activated.connect(lambda _i: self.set_rows(role=self.b_role.currentData()))
        bulk.addWidget(self.b_role)
        self.b_cat = QComboBox(); self.b_cat.addItem("Source...", "")
        for k, _n in lib.categories():
            self.b_cat.addItem(DV.source_name(lib, k), k)
        self.b_cat.activated.connect(lambda _i: self.set_rows(category=self.b_cat.currentData()))
        bulk.addWidget(self.b_cat)
        bulk.addWidget(D.button("Take them out", None, lambda: self.set_rows(skip=True)))
        bulk.addWidget(D.button("Select all", "ghost", lambda: self.table.selectAll()))
        bulk.addStretch(1)
        self.count = D.label("", "muted", wrap=False); bulk.addWidget(self.count)
        self.table = QTableWidget(len(plan), len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for c, wdt in enumerate((190, 170, 220, 220, 200, 150, 110, 80, 100, 150, 100, 28)):
            self.table.setColumnWidth(c, wdt)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False); hh.setSectionResizeMode(C_TAGS, QHeaderView.Stretch)
        self.rows = []
        for i, e in enumerate(plan):
            self._row(i, e)
        v.addWidget(self.table, 1)
        self.problem = D.label("", "crit"); self.problem.hide(); v.addWidget(self.problem)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Add")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.ok = bb.button(QDialogButtonBox.Ok)
        self.show_deliv_column()
        self.show_strip()
        self.show_count()

    # ------------------------------------------------------------ Part of and Arrived as (4.84.0)
    def strip_wanted(self):
        """In an effort, while any row still to add is the customer's (a program's documents have Version only)."""
        if self.rec is None or not hasattr(self, "rows"):
            return False
        return any(not w["out"] and w["cat"].currentData() in DP.CUSTOMER_SIDE and self.kind(r) in ("new", "version")
                   for r, w in enumerate(self.rows))

    def show_strip(self):
        if not hasattr(self, "rows"):
            return
        on = self.strip_wanted()
        self.strip.setVisible(on)
        self.table.setColumnHidden(C_ARRIVED, not on)
        for r, w in enumerate(self.rows):
            mine = w["cat"].currentData() in DP.CUSTOMER_SIDE and self.kind(r) in ("new", "version")
            w["cells"][C_ARRIVED].show_control(on and mine, "")

    def follow_strip(self):
        for w in getattr(self, "rows", []):
            RS.follow(w["arrived"], self.strip)

    def arrived(self, r):
        """(part, release, date) for a row, or None when not said or not the customer's."""
        w = self.rows[r]
        if not self.strip_wanted() or w["cat"].currentData() not in DP.CUSTOMER_SIDE or self.kind(r) not in ("new", "version"):
            return None
        got = w["arrived"].currentData()
        if got == RS.STRIP:
            return self.strip.part_name(), self.strip.release(), self.strip.day()
        return tuple(got) if got else None

    # ------------------------------------------------------------ one row
    def _row(self, i, e):
        lib = self.lib
        folder = e.get("folder", "")
        self.table.setItem(i, C_FILE, _item(os.path.basename(e["path"]), e["path"] + (f"\nFrom the folder {folder}" if folder else "")))
        what = QComboBox()
        if e.get("dup") and not e.get("dup_how"):        # the same file (its fingerprint): said, not asked
            what.addItem(f"Same file, already added: {e['dup'][0]['name']}", ("skip", None))
            what.setEnabled(False)
            what.setToolTip("This very file is already in Documents. It is not added again.")
        elif e.get("dup"):                               # 3.15.1: the same words, other bytes: add only if asked
            what.addItem(f"Same text as {e['dup'][0]['name']}, already added", ("skip", None))
            if e["dup"][0].get("id"):
                what.addItem(f"New version of {e['dup'][0]['name']}", ("version", e["dup"][0]["id"]))
        else:
            what.addItem("New document", ("new", None))
            if e.get("replace_of"):                      # 4.17.0: read before from this very file
                rd = lib.doc(e["replace_of"])
                if rd is not None:
                    what.addItem(f"Replaces the file of {rd['name']} (edited)", ("replace", rd["id"]))
            for d, _sc, how in e.get("cands", [])[:6]:
                what.addItem(f"New version of {d['name']}  ({how})", ("version", d["id"]))
            if e["choice"] in ("version", "replace") and e.get("doc"):
                what.setCurrentIndex(max(0, next((k for k in range(what.count()) if what.itemData(k) == (e["choice"], e["doc"])), 0)))
        cat = QComboBox()
        for k, _n in lib.categories():
            cat.addItem(DV.source_name(lib, k), k)
        cat.setCurrentIndex(max(0, cat.findData(e.get("category", "customer"))))
        role = QComboBox()
        for k, n in DV.ADD_USES:
            role.addItem(n, k)
        role.setCurrentIndex(max(0, role.findData(DV.use_key(e.get("role") or "matrix"))))
        deliv = QComboBox()
        ini = QLineEdit(e.get("initial", "")); ini.setMaxLength(6)
        ini.setProperty("sk_typed", False)                 # 2.94.0: the initial follows the type until you type one
        ini.textEdited.connect(lambda t, w=ini: w.setProperty("sk_typed", bool(t.strip())))
        ty = type_box(e.get("type", ""))
        name = QLineEdit(e.get("name", ""))
        tags = QLineEdit(", ".join(e.get("tags", []))); tags.setToolTip("Comma between tags; the folder names are always tags")
        arrived = RS.row_box(lib); RS.follow(arrived, self.strip) if hasattr(self, "strip") else None
        cmp = QCheckBox(""); cmp.setChecked(True)               # 4.85.0: compare this new version after the add
        out = QToolButton(); out.setText("x"); out.setAutoRaise(True); out.setToolTip("Take this file out: it is not added")
        out.clicked.connect(lambda _c=False, r=i: self.take_out([r]))
        cells = {C_PURPOSE: _Either(role), C_DELIV: _Either(deliv), C_VERSION: what, C_ARRIVED: _Either(arrived), C_COMPARE: _Either(cmp), C_SOURCE: cat, C_INI: _Either(ini),
                 C_TYPE: _Either(ty), C_NAME: name, C_TAGS: tags, C_OUT: out}
        for c, w in cells.items():
            self.table.setCellWidget(i, c, w)
        row = {"what": what, "cat": cat, "role": role, "deliv": deliv, "arrived": arrived, "cmp": cmp, "ini": ini, "ty": ty, "name": name, "tags": tags,
               "cells": cells, "out": False, "deliv_for": None}
        self.rows.append(row)
        self._fill_deliv(i, keep=e.get("deliverable"))
        what.currentIndexChanged.connect(lambda _k, r=i: self._changed(r))
        cat.currentIndexChanged.connect(lambda _k, r=i: self._cat_changed(r))
        role.currentIndexChanged.connect(lambda _k, r=i: self._role_changed(r))
        ty.currentTextChanged.connect(lambda _t, r=i: self._type_changed(r))
        self._changed(i)

    def kind(self, r):
        return (self.rows[r]["what"].currentData() or ("",))[0]

    def purpose(self, r):
        return self.rows[r]["role"].currentData()

    def _fill_deliv(self, r, keep=None):
        """The Deliverable field for this row's purpose: the app's suggestion first, the others of that kind, New."""
        w = self.rows[r]
        mark = self.purpose(r)
        if self.rec is None or mark not in DD.DOOR_MARKS or w["deliv_for"] == mark and keep is None:
            return
        e = self.plan[r]
        cur = keep or (w["deliv"].currentData() if w["deliv_for"] == mark else None)
        sugg = DD.suggest(self.rec, w["name"].text() or e.get("name", ""), mark, (os.path.basename(e["path"]),))
        cb = w["deliv"]
        cb.blockSignals(True)
        cb.clear()
        opts = DD.options(self.rec, mark)
        if sugg:
            cb.addItem(dict(opts).get(sugg, "") + "  (suggested)", sugg)
        for did, words in opts:
            if did != sugg:
                cb.addItem(words, did)
        cb.addItem("New deliverable", DD.NEW)
        want = cur or sugg or DD.NEW
        cb.setCurrentIndex(max(0, cb.findData(want)))
        cb.blockSignals(False)
        w["deliv_for"] = mark

    def _changed(self, r):
        w = self.rows[r]
        kind = self.kind(r)
        new = kind == "new"
        for k in ("cat", "role", "name", "tags"):
            w[k].setEnabled(new)
        if kind == "version":
            d = self.lib.doc(w["what"].currentData()[1])
            if d is not None:
                w["cat"].setCurrentIndex(max(0, w["cat"].findData(d.get("category", "customer"))))
                w["role"].setCurrentIndex(max(0, w["role"].findData(DV.use_key(self.lib.role_of(d)))))
                w["ini"].setText(d.get("initial", ""))
        self._show(r)
        self.show_count()

    def _show(self, r):
        """Initial and Type for a Customer document only (187); a new version's initial in words; Deliverable for the
        three purposes that hand something back."""
        w, e = self.rows[r], self.plan[r]
        kind = self.kind(r)
        cust = w["cat"].currentData() == "customer" and self.purpose(r) == "matrix"
        c = w["cells"]
        if kind == "version":
            d = self.lib.doc(w["what"].currentData()[1])
            ini = (d or {}).get("initial", "")
            c[C_INI].show_control(False, f"{ini}, kept" if d is not None and ini else "")
            c[C_INI].words.setToolTip(f"{ini}, kept from {d['name']}" if d is not None and ini else "")
            c[C_TYPE].show_control(False, (d or {}).get("type", ""))
        elif kind in ("skip", "replace"):
            c[C_INI].show_control(False); c[C_TYPE].show_control(False)
        else:
            c[C_INI].show_control(cust); c[C_TYPE].show_control(cust)
        c[C_PURPOSE].show_control(kind != "skip", "")
        door = self.rec is not None and kind == "new" and self.purpose(r) in DD.DOOR_MARKS and not w["out"]
        if door:
            self._fill_deliv(r)
        c[C_DELIV].show_control(door, "")
        self.show_deliv_column()
        self.show_strip()
        self.show_compare(r)

    def compare_with(self, r):
        """The version a row's new version is compared with (the document's newest), or None when it is not compared:
        not a new version, not a customer document, or not in an effort."""
        w = self.rows[r]
        if self.rec is None or w["out"] or self.kind(r) != "version":
            return None
        d = self.lib.doc(w["what"].currentData()[1])
        if d is None or d.get("category", "customer") != "customer" or not d.get("versions"):
            return None
        return d["versions"][-1]

    def show_compare(self, r=None):
        """4.85.0: the Compare with cell of each new version of a customer document ("Final RFP"); the column only when
        one row has it."""
        if not hasattr(self, "rows"):
            return
        for k in range(len(self.rows)) if r is None else (r,):
            v = self.compare_with(k)
            box = self.rows[k]["cmp"]
            if v is not None:
                box.setText(v.get("label") or v.get("file", "the version before"))
                box.setToolTip(f"After the add, see in What changed what it changed against {v.get('label', '')} ({v.get('file', '')})")
            self.rows[k]["cells"][C_COMPARE].show_control(v is not None, "")
        need = any(self.compare_with(k) is not None for k in range(len(self.rows)))
        self.table.setColumnHidden(C_COMPARE, not need)

    def show_deliv_column(self):
        if not hasattr(self, "rows"):
            return
        need = any(not w["out"] and w["cells"][C_DELIV].control.isVisibleTo(w["cells"][C_DELIV]) for w in self.rows)
        self.table.setColumnHidden(C_DELIV, not need)

    def _role_changed(self, r):
        self._show(r)

    def _cat_changed(self, r):
        w = self.rows[r]
        cat = w["cat"].currentData()
        cust = cat == "customer"
        w["role"].setCurrentIndex(max(0, w["role"].findData(DV.use_key(DV.suggest_role(cat, w["ty"].currentText() if cust else "")))))
        if cust and not w["ini"].text().strip():
            taken = [x["ini"].text().strip() for k, x in enumerate(self.rows) if k != r]
            w["ini"].setText(self.lib.suggest_initial(w["ty"].currentText(), taken))
        self._changed(r)

    def _type_changed(self, r):
        w = self.rows[r]
        if w["cat"].currentData() == "customer":
            if self.purpose(r) in ("matrix", "reference", "context"):
                w["role"].setCurrentIndex(max(0, w["role"].findData(DV.use_key(DV.suggest_role("customer", w["ty"].currentText())))))
            e = self.plan[r]
            if not w["ini"].property("sk_typed"):
                taken = [x["ini"].text().strip() for k, x in enumerate(self.rows) if k != r]
                e["initial"] = self.lib.suggest_initial(w["ty"].currentText(), taken)
                w["ini"].setText(e["initial"])

    # ------------------------------------------------------------ many rows
    def selected_rows(self):
        return sorted({ix.row() for ix in self.table.selectionModel().selectedRows()})

    def take_out(self, rows):
        """The row's x: the file is not added. The row leaves the table."""
        for r in rows:
            self.rows[r]["out"] = True
            self.table.setRowHidden(r, True)
        self.show_compare()
        self.show_deliv_column()
        self.show_strip()
        self.show_count()
        return len(rows)

    def set_rows(self, category="", role="", skip=False, rows=None):
        """Set many rows at once (the selected ones)."""
        rows = self.selected_rows() if rows is None else rows
        if skip:
            self.take_out(rows)
            return len(rows)
        for r in rows:
            w = self.rows[r]
            if self.kind(r) != "new":
                continue
            if category:
                w["cat"].setCurrentIndex(max(0, w["cat"].findData(category)))
            if role:
                w["role"].setCurrentIndex(max(0, w["role"].findData(DV.use_key(role))))
        self.b_cat.setCurrentIndex(0); self.b_role.setCurrentIndex(0)
        self.show_count()
        return len(rows)

    def show_count(self):
        if not hasattr(self, "count"):
            return
        adding = sum(1 for r, w in enumerate(self.rows) if not w["out"] and self.kind(r) != "skip")
        self.count.setText(f"{adding} to add")
        if hasattr(self, "ok"):
            self.ok.setEnabled(adding > 0)

    def accept(self):
        problems = DI.check(self.lib, self.result_plan())
        if problems:
            self.problem.setText("Before adding: " + " ".join(problems[:6]) + (" ..." if len(problems) > 6 else ""))
            self.problem.show()
            return
        if self.strip.pending and self.strip_wanted():        # 4.84.0: a package named here is kept with Documents
            self.strip.keep_packages()
            self.lib.save()
        super().accept()

    def result_plan(self):
        for r, (e, w) in enumerate(zip(self.plan, self.rows)):
            choice, doc = w["what"].currentData()
            if w["out"]:
                choice = "skip"
            e["choice"], e["doc"] = choice, doc
            if e.get("dup_how") and choice == "version":                 # 3.15.1: the person chose to add it anyway
                e["dup"] = None
            if w["cat"].currentData() != e.get("category"):       # a new category suggests its own role
                e["suggested_role"] = DV.suggest_role(w["cat"].currentData(), w["ty"].currentText() if w["cat"].currentData() == "customer" else "")
            e["category"] = w["cat"].currentData()
            e["role"] = w["role"].currentData()
            e["initial"] = DV.clean_initial(w["ini"].text()) if e["category"] == "customer" else ""
            e["type"] = w["ty"].currentText() if e["category"] == "customer" else ""
            e["name"] = w["name"].text().strip() or e.get("name", "")
            e["tags"] = DV.clean_tags([t for t in w["tags"].text().split(",")])
            e["compare"] = self.compare_with(r) is not None and w["cmp"].isChecked() and choice == "version"   # 4.85.0
            got = None if choice not in ("new", "version") else self.arrived(r)
            if got:                                                      # 4.84.0: kept on the version; its label
                e["part_of"], e["arrived_as"], e["arrived_on"] = got
            else:
                for k in ("part_of", "arrived_as", "arrived_on"):
                    e.pop(k, None)
            if e["role"] in DD.DOOR_MARKS and self.rec is not None and choice == "new":
                e["deliverable"] = w["deliv"].currentData() or DD.NEW
            elif e.get("deliverable") and (e["role"] in DD.DOOR_MARKS or choice != "new"):
                e.pop("deliverable", None)
        return self.plan
