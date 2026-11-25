"""Customer information (4.75.0; custinfo holds the rules): a tab of the Overview. Two lists and nothing else: the
people at the customer, each with a role, and the facts about the customer and the buy. A fact is typed here (double-
click its Value) or captured in Shred (More > Customer info); the From column says which, and where a captured one came
from. An empty fact shows where it usually is. One main button: + Contact."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHeaderView, QLineEdit, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

import custinfo as CI
import diag
import effortrec as R
from . import design as D
from .commandbar import CommandBar

CONTACT_COLS = ("Role", "Name", "Title", "Organization", "E-mail", "Phone", "From")
FACT_COLS = ("Fact", "Value", "From")


class ContactDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("A contact at the customer")
        f = QFormLayout(self)
        self.role = QComboBox(); self.role.setEditable(True); self.role.addItems(["", *CI.ROLES])
        self.name, self.title, self.org, self.email, self.phone = (QLineEdit() for _ in range(5))
        for lab, w in (("Role", self.role), ("Name", self.name), ("Title", self.title), ("Organization", self.org),
                       ("E-mail", self.email), ("Phone", self.phone)):
            f.addRow(lab, w)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def values(self):
        return {"role": self.role.currentText(), "name": self.name.text(), "title": self.title.text(), "org": self.org.text(),
                "email": self.email.text(), "phone": self.phone.text()}


class CustInfoPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self._loading = False
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.b_add = self.bar.primary("+ Contact", lambda: self.add_contact(), "A person at the customer, typed here. In Shred, More > Customer info takes one from the customer's words")
        v.addWidget(self.bar)
        self.none = D.EmptyState("No effort is open", "Customer information belongs to an effort.", "Open or create an effort",
                                 lambda: self.host.go("efforts"))
        v.addWidget(self.none, 1)
        self.body = QWidget(); b = QVBoxLayout(self.body); b.setContentsMargins(0, 0, 0, 0); b.setSpacing(D.SPACE["s"])
        b.addWidget(D.label("People", "h3"))
        self.people = QTableWidget(0, len(CONTACT_COLS)); self.people.setHorizontalHeaderLabels(list(CONTACT_COLS))
        self.people.verticalHeader().setVisible(False); self.people.setEditTriggers(QTableWidget.NoEditTriggers)
        self.people.setSelectionBehavior(QTableWidget.SelectRows)
        self.people.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        b.addWidget(self.people)
        self.people_none = D.label("No one yet. Add a contact here, or take one from the customer's words in Shred (More > Customer info).", "muted")
        b.addWidget(self.people_none)
        b.addWidget(D.label("Facts", "h3"))
        self.said = D.label("", "muted")
        b.addWidget(self.said)
        self.facts = QTableWidget(0, len(FACT_COLS)); self.facts.setHorizontalHeaderLabels(list(FACT_COLS))
        self.facts.verticalHeader().setVisible(False)
        hh = self.facts.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed); self.facts.setColumnWidth(0, 250)      # every fact's name readable in full
        hh.setSectionResizeMode(1, QHeaderView.Stretch); hh.setSectionResizeMode(2, QHeaderView.Interactive); self.facts.setColumnWidth(2, 430)
        hh.setStretchLastSection(False)
        self.facts.itemChanged.connect(self._typed)
        b.addWidget(self.facts, 1)
        v.addWidget(self.body, 1)

    @property
    def rec(self):
        h = self.host
        return R.Record(h.ws.root) if getattr(h, "ws", None) is not None else None

    def who(self):
        try:
            import effort as E
            return E.user_name()
        except Exception:  # noqa: BLE001
            return ""

    def refresh(self):
        rec = self.rec
        self.none.setVisible(rec is None); self.body.setVisible(rec is not None); self.bar.setVisible(rec is not None)
        if rec is None:
            return 0
        self._loading = True
        try:
            people = CI.contacts(rec)
            self.people.setRowCount(len(people))
            for r, c in enumerate(people):
                for k, key in enumerate(("role", "name", "title", "org", "email", "phone", "from")):
                    it = QTableWidgetItem(c[key]); it.setData(Qt.UserRole, c["id"]); it.setToolTip(c[key])
                    self.people.setItem(r, k, it)
            self.people.setVisible(bool(people)); self.people_none.setVisible(not people)
            self.people.setFixedHeight(min(260, self.people.horizontalHeader().height() + sum(self.people.rowHeight(r) for r in range(len(people))) + 6))
            rows = CI.rows(rec)
            muted = QBrush(QColor(D.tokens()["muted"]))
            self.facts.setRowCount(0)
            group = None
            for x in rows:
                if x["group"] != group:
                    group = x["group"]
                    r = self.facts.rowCount(); self.facts.insertRow(r)
                    g = QTableWidgetItem(group); f = QFont(); f.setBold(True); g.setFont(f); g.setFlags(Qt.ItemIsEnabled)
                    self.facts.setItem(r, 0, g); self.facts.setSpan(r, 0, 1, len(FACT_COLS))
                r = self.facts.rowCount(); self.facts.insertRow(r)
                a = QTableWidgetItem(x["label"]); a.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                val = QTableWidgetItem(x["value"]); val.setData(Qt.UserRole, x["label"])
                val.setToolTip("Double-click to type it. In Shred, More > Customer info takes it from the customer's words.")
                frm = QTableWidgetItem(x["from"] or (("Usually: " + x["hint"]) if x["hint"] else "")); frm.setFlags(Qt.ItemIsEnabled)
                if not x["from"]:
                    frm.setForeground(muted)
                for k, it in enumerate((a, val, frm)):
                    self.facts.setItem(r, k, it)
            n = CI.filled(rec)
            self.said.setText(f"{n} of {len(rows)} filled. Double-click a Value to type it; in Shred, More > Customer info takes it from the customer's words.")
        finally:
            self._loading = False
        return len(rows)

    def _typed(self, item):
        """A Value typed on the page: the person's own change, kept at once with their name and the date."""
        if self._loading or item.column() != 1:
            return
        label = item.data(Qt.UserRole)
        rec = self.rec
        if not label or rec is None:
            return
        out = CI.set_fact(rec, label, item.text(), "typed", self.who(), replace=True)
        if out in ("set", "cleared"):
            diag.activity("customer_fact_typed")
            self.host.status(f"{label}: {'kept' if out == 'set' else 'cleared'}.")
        self.refresh()

    def set_value(self, label, text):
        """Type a fact's value (what a double-click and Enter do)."""
        for r in range(self.facts.rowCount()):
            it = self.facts.item(r, 1)
            if it is not None and it.data(Qt.UserRole) == label:
                it.setText(text)
                return True
        return False

    def add_contact(self, answer=None):
        rec = self.rec
        if rec is None:
            return None
        if answer is None:
            d = ContactDialog(self)
            if d.exec() != QDialog.Accepted:
                return None
            answer = d.values()
        cid = CI.add_contact(rec, who=self.who(), **answer)
        if cid is None:
            self.host.status("A contact needs a name.")
            return None
        self.refresh()
        self.host.status(f"{answer.get('name', '')} added to Customer information.")
        return cid
