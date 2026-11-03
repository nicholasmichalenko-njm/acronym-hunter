"""Bins in Review (3.21.0): put the picked words in a bin (an excerpt keeps them verbatim with where they sit), make the
effort's own bins, and see every excerpt. The rules are excerpts.py's; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QHeaderView, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QRadioButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QButtonGroup)
import diag
import excerpts as EX
from . import design as D

HINT = {"submit": "The value, if it sets one: a date and time, an address, a portal (optional)",
        "other": "A value, if any (optional): this detail needs no rule",
        "format": "The value, if it is measured: 12 pt, 1 inch margins, 25 pages (leave empty for a written rule)",
        "objective": "Optional: how the customer will measure it",
        "keypoint": "Optional: a short label (a theme, a discriminator, a risk)"}


class BinDialog(QDialog):
    """The words picked, verbatim, with where they sit; the bin; a value only when one exists; a note; for an objective,
    the sections that answer it; for a written formatting rule, how it is checked."""

    def __init__(self, parent, rec, config_dir, bin_id, parts, sections=(), x=None):
        super().__init__(parent)
        self.rec, self.x = rec, x
        self.setWindowTitle("Edit the excerpt" if x else f"Put in a bin: {EX.bin_name(rec, bin_id, config_dir)}")
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        f = QFormLayout(); v.addLayout(f)
        self.bin = QComboBox()
        for b in EX.bins(rec, config_dir):
            self.bin.addItem(b["name"], b["id"])
        self.bin.setCurrentIndex(max(0, self.bin.findData(bin_id)))
        f.addRow("Bin", self.bin)
        probe = {"parts": parts}
        self.words = QPlainTextEdit(EX.text_of(probe)); self.words.setReadOnly(True); self.words.setMaximumHeight(110)
        self.words.setToolTip("The customer's words, verbatim (fix a part from the sentence's card if the reader got it wrong)")
        f.addRow("The customer's words", self.words)
        f.addRow("Where", D.label(EX.where_of(probe) or "(not known)", "muted"))
        self.value = QLineEdit((x or {}).get("value", ""))
        f.addRow("Value", self.value)
        self.note = QLineEdit((x or {}).get("note", "")); self.note.setPlaceholderText("Your note (optional)")
        f.addRow("Note", self.note)
        self.sec_label = D.label("Sections that answer it", "label")
        self.sections = QListWidget(); self.sections.setSelectionMode(QAbstractItemView.MultiSelection); self.sections.setMaximumHeight(140)
        have = set((x or {}).get("sections", []))
        for s in sections:
            it = QListWidgetItem(s); self.sections.addItem(it); it.setSelected(s in have)
        v.addWidget(self.sec_label); v.addWidget(self.sections)
        self.fmt = QWidget(); fh = QHBoxLayout(self.fmt); fh.setContentsMargins(0, 0, 0, 0)
        self.fmt_group = QButtonGroup(self)
        self.fmt_btn = {}
        for k, t in EX.WRITTEN_CHECKS:
            r = QRadioButton(t); self.fmt_group.addButton(r); fh.addWidget(r); self.fmt_btn[k] = r
        guess = (x or {}).get("check") or EX.written_check(EX.text_of(probe))
        self.fmt_btn[guess].setChecked(True)
        v.addWidget(self.fmt)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.bin.currentIndexChanged.connect(lambda _i: self._kind())
        self.value.textChanged.connect(lambda _t: self._kind())
        self._kind()

    def _kind(self):
        b = self.bin.currentData()
        self.value.setPlaceholderText(HINT.get(b, "A value, if one exists (optional)"))
        self.sec_label.setVisible(b == "objective"); self.sections.setVisible(b == "objective")
        self.fmt.setVisible(b == "format" and not self.value.text().strip())

    def values(self):
        return {"bin": self.bin.currentData(), "value": self.value.text(), "note": self.note.text(),
                "sections": [i.text() for i in self.sections.selectedItems()],
                "check": next((k for k, r in self.fmt_btn.items() if r.isChecked()), "final")}


class NewBinDialog(QDialog):
    """A bin of the effort's own: its name, color and where it feeds; Share with team puts it in the team pack."""

    def __init__(self, parent, rec, b=None):
        super().__init__(parent)
        self.setWindowTitle("Bin" if b else "New bin")
        self.setMinimumWidth(480)
        f = QFormLayout(self)
        self.name = QLineEdit((b or {}).get("name", "")); self.name.setPlaceholderText("For example: Transition risk, Small business")
        f.addRow("Name", self.name)
        self.color = QComboBox()
        used = {x.get("color") for x in EX.custom_bins(rec)}
        for c in EX.COLORS:
            self.color.addItem(D.dot_icon(c), c, c)
        start = (b or {}).get("color") or next((c for c in EX.COLORS if c not in used), EX.COLORS[0])
        self.color.setCurrentIndex(max(0, self.color.findData(start)))
        f.addRow("Color", self.color)
        self.feeds = {}
        fw = QWidget(); fl = QVBoxLayout(fw); fl.setContentsMargins(0, 0, 0, 0)
        for k, t in EX.FEEDS:
            cb = QCheckBox(t); cb.setChecked(k in ((b or {}).get("feeds") or ["setup"])); fl.addWidget(cb); self.feeds[k] = cb
        f.addRow("Feeds", fw)
        self.about = QLineEdit((b or {}).get("about", "")); self.about.setPlaceholderText("What goes in it (optional)")
        f.addRow("About", self.about)
        self.share = QCheckBox("Share with team (it travels in the next team pack)"); self.share.setChecked(bool((b or {}).get("shared")))
        f.addRow(self.share)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def values(self):
        return {"name": self.name.text(), "color": self.color.currentData(), "feeds": [k for k, cb in self.feeds.items() if cb.isChecked()],
                "about": self.about.text(), "share": self.share.isChecked()}


def make_bin(parent, rec, config_dir, answer=None):
    """A new bin of the effort's own (answer, tests: NewBinDialog.values()). Returns its id."""
    if answer is None:
        d = NewBinDialog(parent, rec)
        if d.exec() != QDialog.Accepted:
            return None
        answer = d.values()
    bid = EX.add_bin(rec, answer.get("name", ""), answer.get("color", ""), answer.get("feeds", ()), answer.get("about", ""))
    if bid and answer.get("share") and config_dir:
        EX.share_bin(rec, bid, config_dir)
    if bid:
        diag.activity("bin_added")
    return bid


class ExcerptsDialog(QDialog):
    """Every excerpt of the effort, by bin: the words, value, where they sit and the note; Edit, Take out, and Show in
    Review."""

    def __init__(self, parent, page, rec):
        super().__init__(parent)
        self.page, self.rec = page, rec
        self.setWindowTitle("Every excerpt")
        self.resize(1100, 620)
        v = QVBoxLayout(self)
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.label("Bin", "label"))
        self.filter = QComboBox(); self.filter.addItem("Every bin", None)
        for b in EX.bins(rec, page.host.config_dir):
            n = EX.counts(rec).get(b["id"], 0)
            if n or not b["builtin"]:
                self.filter.addItem(f"{b['name']} ({n})", b["id"])
        self.filter.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.filter); top.addStretch(1)
        self.t = QTableWidget(0, 5); self.t.setHorizontalHeaderLabels(["Bin", "The customer's words", "Value", "Where", "Note"])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QTableWidget.SelectRows)
        self.t.setEditTriggers(QTableWidget.NoEditTriggers); self.t.setWordWrap(True)
        hh = self.t.horizontalHeader(); hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for i, w in ((0, 150), (2, 170), (3, 230), (4, 170)):
            self.t.setColumnWidth(i, w)
        self.t.itemDoubleClicked.connect(lambda _i: self.edit())
        v.addWidget(self.t, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Edit...", None, lambda: self.edit()))
        row.addWidget(D.button("Show in Review", "ghost", lambda: self.show_it()))
        row.addWidget(D.button("Take out", "ghost", lambda: self.take_out()))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); bb.accepted.connect(self.accept)
        row.addWidget(bb)
        self.fill()

    def fill(self):
        import effortrec as RR
        self.rec = RR.Record(self.rec.folder)
        b = self.filter.currentData()
        xs = EX.excerpts(self.rec, b)
        self.t.setRowCount(0)
        names = {x["id"]: x["name"] for x in EX.bins(self.rec, self.page.host.config_dir)}
        for x in xs:
            r = self.t.rowCount(); self.t.insertRow(r)
            sub = {"measured": " (measured)", "written": " (written: " + ("phrase check" if x.get("check") == "phrase" else "Final Checks") + ")"}.get(x.get("sub"), "")
            val = x.get("value", "") or (", ".join(x.get("sections", [])) if x["bin"] == "objective" else "")
            for c, s in enumerate((names.get(x["bin"], x["bin"]) + sub, EX.text_of(x), val, EX.where_of(x), x.get("note", ""))):
                it = QTableWidgetItem(s); it.setToolTip(s[:1000])
                if c == 0:
                    it.setData(Qt.UserRole, x["id"])
                self.t.setItem(r, c, it)
        self.t.resizeRowsToContents()
        return len(xs)

    def selected(self):
        r = self.t.currentRow()
        it = self.t.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it is not None else None

    def edit(self, answer=None):
        xid = self.selected()
        if xid and self.page.edit_excerpt(xid, answer):
            self.fill()
            return True
        return False

    def take_out(self):
        xid = self.selected()
        if xid and EX.remove(self.rec, xid):
            self.page.after_bins()
            self.fill()
            return True
        return False

    def show_it(self):
        x = EX.get(self.rec, self.selected() or "")
        if x and x.get("parts"):
            self.accept()
            self.page.show_sentence(x["parts"][0]["sid"])
            return True
        return False


class BinsDialog(QDialog):
    """The effort's own bins and the team's: add, change, share or take one out."""

    def __init__(self, parent, page, rec):
        super().__init__(parent)
        self.page, self.rec = page, rec
        self.setWindowTitle("Bins")
        self.resize(640, 420)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Built-in bins are always there. Bins of this effort get the keys Alt+1 to Alt+9; a bin shared with the "
                            "team shows in every effort on this PC and travels in the next team pack.", "muted"))
        self.list = QListWidget(); v.addWidget(self.list, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("+ Bin...", None, lambda: self.add()))
        row.addWidget(D.button("Change...", "ghost", lambda: self.change()))
        row.addWidget(D.button("Share with team", "ghost", lambda: self.share()))
        row.addWidget(D.button("Take out", "ghost", lambda: self.remove()))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); row.addWidget(bb)
        self.fill()

    def fill(self):
        self.list.clear()
        for b in EX.bins(self.rec, self.page.host.config_dir):
            if b["builtin"]:
                continue
            feeds = ", ".join(dict(EX.FEEDS)[f] for f in b.get("feeds", []))
            it = QListWidgetItem(f"{b['name']}   {b.get('key', '')}   feeds: {feeds or 'nothing yet'}"
                                 + ("   (the team's)" if b.get("team") else "   (shared)" if b.get("shared") else ""))
            it.setForeground(QColor(b["color"]))
            it.setData(Qt.UserRole, b["id"]); it.setData(Qt.UserRole + 1, bool(b.get("team")))
            self.list.addItem(it)
        return self.list.count()

    def _cur(self):
        it = self.list.currentItem()
        return (it.data(Qt.UserRole), it.data(Qt.UserRole + 1)) if it else (None, None)

    def add(self, answer=None):
        bid = make_bin(self, self.rec, self.page.host.config_dir, answer)
        self.fill(); self.page.after_bins()
        return bid

    def change(self, answer=None):
        bid, team = self._cur()
        b = next((x for x in EX.custom_bins(self.rec) if x["id"] == bid), None)
        if b is None:
            return False
        if answer is None:
            d = NewBinDialog(self, self.rec, b)
            if d.exec() != QDialog.Accepted:
                return False
            answer = d.values()
        EX.update_bin(self.rec, bid, name=answer["name"], color=answer["color"], feeds=answer["feeds"], about=answer["about"])
        if answer.get("share"):
            EX.share_bin(self.rec, bid, self.page.host.config_dir)
        self.fill(); self.page.after_bins()
        return True

    def share(self):
        bid, team = self._cur()
        ok = bool(bid) and not team and EX.share_bin(self.rec, bid, self.page.host.config_dir)
        self.fill()
        return ok

    def remove(self):
        bid, team = self._cur()
        if not bid or team:
            return None
        n = EX.remove_bin(self.rec, bid)
        self.fill(); self.page.after_bins()
        return n
