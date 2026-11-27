"""Add documents: Part of and Arrived as (4.84.0, step I2 of claude/stationkeeper-document-intake-direction-2026-11-24.md).

A strip above the table says, once for every file from the customer in this add, which package the files are Part of
(Solicitation, Pre-RFP (RFI / Sources Sought), Discussions & FPR, or one the team names with New package...) and which
dated release they Arrived as (Final RFP, Draft RFP 2, Amendment 0002, Q&A set 1 ...). A numbered release numbers
itself: one past the highest in that package, or the number in a file's name. Each row's Arrived as cell follows the
strip unless a row is set to another release or to Not said. The release is kept on each version and is its label.
Shown only in an effort (a program's documents have Version and Label only) and only while a row is the customer's.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QInputDialog, QSpinBox, QWidget

import docpackages as DP
from . import design as D

NEW_PACKAGE = "New package..."
STRIP = "strip"


class _Number(QSpinBox):
    """A release's number; an amendment's shows its four digits (0002)."""

    four = False

    def __init__(self):
        super().__init__()
        self.setRange(1, 9999)

    def textFromValue(self, v):
        return f"{v:04d}" if self.four else str(v)


class ReleaseStrip(QWidget):
    changed = Signal()

    def __init__(self, lib, names=()):
        super().__init__()
        self.lib, self.pending = lib, []
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 4)
        h.addWidget(D.label("Part of", "label", wrap=False))
        self.part = QComboBox()
        self.part.setToolTip("The package these files belong to. Pick New package... to name another.")
        for n in DP.package_names(lib):
            self.part.addItem(n)
        self.part.addItem(NEW_PACKAGE)
        h.addWidget(self.part)
        h.addSpacing(12)
        h.addWidget(D.label("Arrived as", "label", wrap=False))
        self.kind = QComboBox()
        self.kind.setToolTip("The release these files came in. A numbered one numbers itself; change the number if it is wrong.")
        for k in DP.KINDS:
            self.kind.addItem(k)
        h.addWidget(self.kind)
        self.num = _Number(); h.addWidget(self.num)
        h.addWidget(D.label("on", "label", wrap=False))
        self.date = QDateEdit(QDate.currentDate()); self.date.setCalendarPopup(True); self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setToolTip("The date the customer issued it")
        h.addWidget(self.date)
        h.addSpacing(12)
        self.note = D.label("For every file from the customer below. A row can say otherwise.", "muted", wrap=False)
        h.addWidget(self.note)
        h.addStretch(1)
        self._last_part = ""
        part, kind, n = DP.guess(lib, list(names))
        self.set(part, kind, n)
        self.part.activated.connect(lambda _i: self._part_changed())
        self.kind.activated.connect(lambda _i: self._kind_changed())
        self.num.valueChanged.connect(lambda _v: self.changed.emit())
        self.date.dateChanged.connect(lambda _d: self.changed.emit())

    # ------------------------------------------------------------ what it says
    def part_name(self):
        return self.part.currentText()

    def release(self):
        """The release's name: 'Amendment 0002', 'Final RFP'."""
        k = self.kind.currentText()
        return DP.release_name(k, self.num.value() if k in DP.NUMBERED else None)

    def day(self):
        return self.date.date().toString("yyyy-MM-dd")

    def title(self):
        return DP.release_title(self.part_name(), self.release())

    def set(self, part, kind, n=None):
        if self.part.findText(part) < 0:
            self.part.insertItem(self.part.count() - 1, part)
        self.part.setCurrentIndex(self.part.findText(part))
        self._last_part = part
        self.kind.setCurrentIndex(max(0, self.kind.findText(kind)))
        self._show_num(n)
        self.changed.emit()

    def _show_num(self, n=None):
        k = self.kind.currentText()
        on = k in DP.NUMBERED
        self.num.setVisible(on)
        self.num.four = k == "Amendment"
        if on:
            self.num.blockSignals(True)
            self.num.setValue(int(n or DP.next_number(self.lib, self.part_name(), k)))
            self.num.blockSignals(False)
            self.num.lineEdit().setText(self.num.textFromValue(self.num.value()))

    # ------------------------------------------------------------ changes
    def _part_changed(self, name=None, number=None):
        if self.part.currentText() == NEW_PACKAGE:
            if name is None:
                name, ok = QInputDialog.getText(self, "New package", "Name the package (for example: Task Order 12):")
                if not ok or not name.strip():
                    self.part.setCurrentIndex(max(0, self.part.findText(self._last_part)))
                    return
                if number is None:
                    number, ok = QInputDialog.getText(self, "New package", "Its solicitation number, if it has its own (leave empty if not):")
                    number = number if ok else ""
            name = " ".join(name.split())[:80]
            known = next((self.part.itemText(i) for i in range(self.part.count() - 1) if self.part.itemText(i).casefold() == name.casefold()), None)
            if known is None:
                self.part.insertItem(self.part.count() - 1, name)
                self.pending.append((name, number or ""))
                known = name
            self.part.setCurrentIndex(self.part.findText(known))
        part = self.part_name()
        self._last_part = part
        rs = [r for r in DP.releases(self.lib) if r["part"] == part]
        if part == DP.PACKAGES[1]:
            kind = "RFI"
        elif part == DP.PACKAGES[2]:
            kind = "Evaluation Notices"
        elif rs or (part == DP.PACKAGES[0] and DP.amendments(self.lib)):
            kind = "Amendment"
        else:
            kind = "Final RFP"
        self.kind.setCurrentIndex(self.kind.findText(kind))
        self._show_num()
        self.changed.emit()

    def _kind_changed(self):
        self._show_num()
        self.changed.emit()

    def keep_packages(self):
        """The packages named here, kept in Documents' own record (on Add). Returns how many."""
        n = 0
        for name, number in self.pending:
            if DP.add_package(self.lib, name, number):
                n += 1
        self.pending = []
        return n


def row_box(lib):
    """A row's Arrived as: the strip's release (first), the effort's earlier releases, or Not said."""
    cb = QComboBox()
    cb.addItem("", STRIP)
    for r in DP.releases(lib):
        cb.addItem(DP.release_title(r["part"], r["name"]), (r["part"], r["name"], r["date"]))
    cb.addItem("Not said", None)
    cb.setToolTip("Follows Part of and Arrived as above. Pick another release for this file only, or Not said.")
    return cb


def follow(cb, strip):
    """The first item reads as the strip does."""
    cb.setItemText(0, strip.title())
