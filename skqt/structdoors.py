"""Start our structure: two doors to one outline (4.19.0; claude/stationkeeper-response-structure-plan-4.19.html).
The Setup builder (Matrix & Outline's outline, and Setup's) shows a card while our outline is empty, or still the start
the app made from the customer's headings when it first read them (either door replaces that start):
- The customer prescribes it: the pieces typed Structure in Shred are read into headings (structfrom.read), shown in a
  preview to fix levels and titles, then Put in our outline. Each heading keeps Required by. Recommended when Structure
  pieces exist; with none, the card says how to mark them (Shred: select the piece, Structure, key O).
- We build it: Draft headings from... the customer's headings, the SOW or PWS headings, the evaluation factors, or blank.
The builder's More keeps both for later (the required frame first, our drafts under it), Use it as our structure (takes
Draft off) and Check against the required structure (structfrom.drift). Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QFrame, QHBoxLayout, QLineEdit, QMenu, QMessageBox,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

import diag
from . import design as D


def card(page):
    """The start card, added above the builder's tree; refresh() shows it while the outline is empty."""
    f = QFrame(); f.setObjectName("card")
    v = QVBoxLayout(f); v.setContentsMargins(D.SPACE["l"], D.SPACE["m"], D.SPACE["l"], D.SPACE["m"]); v.setSpacing(D.SPACE["s"])
    v.addWidget(D.label("Start our structure", "title"))
    row = QHBoxLayout(); row.setSpacing(D.SPACE["l"]); v.addLayout(row)
    one = QVBoxLayout(); row.addLayout(one, 1)
    one.addWidget(D.label("The customer prescribes it", "label"))
    page.door1_say = D.label("", "muted"); one.addWidget(page.door1_say)
    page.door1 = D.button("Read the Structure pieces...", "primary", lambda: preview(page),
                          "Headings from the pieces typed Structure in Shred, to check before they go in")
    one.addWidget(page.door1)
    two = QVBoxLayout(); row.addLayout(two, 1)
    two.addWidget(D.label("We build it", "label"))
    two.addWidget(D.label("Draft headings from a start of your choice; send pieces to them in Shred as you read, then "
                          "arrange them here and Use it as our structure.", "muted"))
    page.door2 = D.button("Draft headings from...", None, None, "The customer's headings, the SOW or PWS, the evaluation "
                          "factors, or blank")
    m = QMenu(page.door2)
    import structfrom as SF
    for key, name in SF.STARTS:
        m.addAction(name, lambda k=key: drafts(page, k))
    page.door2.setMenu(m)
    two.addWidget(page.door2)
    page.start_card = f
    return f


def refresh(page):
    """Show the card while our outline is empty; say what Door 1 has to read."""
    c = getattr(page, "start_card", None)
    if c is None:
        return
    import structfrom as SF
    M = page.M
    empty = M is not None and SF.untouched(M)
    c.setVisible(bool(empty))
    if not empty:
        return
    n = len(SF.pieces(M))
    page.door1.setProperty("kind", "primary" if n else None)
    page.door1.setEnabled(bool(n))
    page.door1_say.setText(f"{n} piece(s) typed Structure in Shred. Recommended: read them into our outline." if n else
                           "In Shred, select the piece that sets the structure (\"shall be organized as follows\", the "
                           "volumes) and type it Structure (O). Then read it here.")
    page.door2.setProperty("kind", None if n else "primary")
    for b in (page.door1, page.door2):
        b.style().unpolish(b); b.style().polish(b)


def more_items(page, m):
    """The builder's More: both doors for later, Use it as our structure, Check against the required structure."""
    import structfrom as SF
    m.addSeparator()
    m.addAction("Add the required headings (Structure pieces)...", lambda: preview(page))
    dm = m.addMenu("Draft headings from")
    for key, name in SF.STARTS[:-1]:
        dm.addAction(name, lambda k=key: drafts(page, k))
    if page.M is not None and SF.draft_count(page.M):
        m.addAction(f"Use it as our structure ({SF.draft_count(page.M)} draft heading(s))", lambda: use_as_ours(page))
    m.addAction("Check against the required structure", lambda: check(page))


class Preview(QDialog):
    """The headings read from the Structure pieces: H level, title, page limit and where each came from, to fix before
    they go in. + Add a heading, Remove, Put in our outline."""
    def __init__(self, page, heads):
        super().__init__(page)
        self.setWindowTitle("The required structure")
        self.resize(900, 460)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Read from the pieces typed Structure. Fix a level or a title the reading got wrong, add what it "
                            "missed, then put them in. Each keeps where the customer required it.", "muted"))
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Level", "Heading", "Page limit", "Required by"])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.setColumnWidth(0, 70); self.t.setColumnWidth(1, 360); self.t.setColumnWidth(2, 90)
        self.t.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.t, 1)
        for h in heads:
            self.add_row(h)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("+ Add a heading", None, lambda: self.add_row({"title": "", "level": 2})))
        row.addWidget(D.button("Remove", None, lambda: self.remove()))
        row.addStretch(1)
        row.addWidget(D.button("Cancel", None, self.reject))
        row.addWidget(D.button("Put in our outline", "primary", self.accept))

    def add_row(self, h):
        r = self.t.rowCount(); self.t.insertRow(r)
        lv = QComboBox(); lv.addItems([f"H{n}" for n in range(1, 10)]); lv.setCurrentIndex(max(0, min(8, int(h.get("level") or 1) - 1)))
        self.t.setCellWidget(r, 0, lv)
        self.t.setCellWidget(r, 1, QLineEdit(h.get("title", "")))
        sp = QSpinBox(); sp.setRange(0, 999); sp.setSpecialValueText("none"); sp.setValue(int(h.get("limit") or 0))
        self.t.setCellWidget(r, 2, sp)
        it = QTableWidgetItem(h.get("ref", "") or "added here"); it.setData(Qt.UserRole, h.get("req", ""))
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.t.setItem(r, 3, it)
        return r

    def remove(self):
        for r in sorted({i.row() for i in self.t.selectedIndexes()}, reverse=True):
            self.t.removeRow(r)

    def heads(self):
        out = []
        for r in range(self.t.rowCount()):
            title = self.t.cellWidget(r, 1).text().strip()
            if not title:
                continue
            it = self.t.item(r, 3)
            out.append({"title": title, "level": self.t.cellWidget(r, 0).currentIndex() + 1, "limit": self.t.cellWidget(r, 2).value(),
                        "req": it.data(Qt.UserRole) or "", "ref": it.text() if it.data(Qt.UserRole) else ""})
        return out


def preview(page, run=True):
    """Door 1: read the Structure pieces, show the preview, put them in. Returns the entries put in, or the dialog
    (run=False)."""
    import structfrom as SF
    M = page.M
    if M is None:
        return None
    heads = SF.read(M)
    if not heads and not SF.pieces(M):
        page.host.status("No piece is typed Structure yet: in Shred, select the piece that sets the structure and type it "
                         "Structure (O).")
    dlg = Preview(page, heads)
    page._preview = dlg
    if not run:
        return dlg
    if dlg.exec() != QDialog.Accepted:
        return None
    return put(page, dlg.heads())


def put(page, heads, replace=None):
    import structfrom as SF
    M = page.M
    if M is None or not heads:
        return []
    page.host.review.snap("the required structure")
    ents = SF.put(M, heads, replace)
    page.host.changed()
    diag.activity("structure_required_put", n=len(ents))
    page.refresh()
    page.host.status(f"{len(ents)} required heading(s) in our outline. Add your own under them; each says where it was required.")
    return ents


def drafts(page, start):
    """Door 2: draft headings from a start into the outline."""
    import effortrec as R
    import structfrom as SF
    M = page.M
    if M is None:
        return []
    lib = None
    try:
        import docversions as DV
        lib = DV.Library(page.host.ws.p("documents")).load()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    try:
        rec = R.Record(page.host.ws.root)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        rec = None
    ents = SF.drafts(M, start, rec, lib)
    if start != "blank" and not ents:
        page.host.status({"headings": "No customer headings yet: mark them in Shred (Fix text > Heading) or extract the documents.",
                          "sow": "No SOW or PWS headings found among the customer documents.",
                          "factors": "No evaluation factors yet: capture them in Shred (Evaluation)."}.get(start, ""))
        return []
    page.host.review.snap("draft headings")
    if start == "blank":
        ents = [{"num": "1", "title": "First section", "level": 1, "draft": True}]
    got = SF.put_drafts(M, ents)
    page.host.changed()
    diag.activity("structure_drafts_put", n=len(got))
    page.refresh()
    page.host.status(f"{len(got)} draft heading(s). In Shred, send pieces to them (R on a target); arrange them here, then "
                     "More > Use it as our structure.")
    return got


def use_as_ours(page):
    import structfrom as SF
    page.host.review.snap("use it as our structure")
    n = SF.use_as_ours(page.M)
    page.host.changed()
    page.refresh()
    page.host.status(f"{n} heading(s) are our structure now.")
    return n


def check(page, show=True):
    """Check against the required structure. Returns the issues."""
    import structfrom as SF
    got = SF.drift(page.M) if page.M is not None else []
    if page.M is not None and SF.deliver_limits(page.M):          # 4.21.0: limits read before 4.21.0 reach the page budget
        page.host.changed()
    text = "\n".join(t for _k, t in got) if got else "Our outline holds every required heading, by its name and in its order."
    if show and not os.environ.get("AH_TEST"):
        QMessageBox.information(page, "Check against the required structure", text)
    page.host.status(f"{len(got)} difference(s) from the required structure." if got else text)
    return got
