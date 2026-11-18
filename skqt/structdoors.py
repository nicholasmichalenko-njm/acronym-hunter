"""Start our structure: two doors to one outline (4.19.0; claude/stationkeeper-response-structure-plan-4.19.html).
The Setup builder shows a card on Matrix & Outline > Outline (4.26.0: on Setup it is one line that opens Outline) while our outline is empty, or still the start
the app made from the customer's headings when it first read them (either door replaces that start):
- The customer prescribes it (4.55.0, UX decision 13): a list of the pieces typed Structure, then those only suggested
  (structfrom.suggested), each in the customer's words with where it is, Use it and Show on its page; Use all of them...
  with two or more typed. Use it reads that piece (structfrom.read), shows the preview, then puts the headings in: at
  once while our outline is untouched, else after Add or Replace, asked with the effect in counts (structfrom.effect).
  With none: "No piece sets the structure yet." and Go to Shred (the how-to is in the Guide).
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
    """The start card, added above the builder's tree; refresh() shows it while the outline is untouched. 4.55.0 (UX
    decisions 13 and 15): the customer's side is a list of the pieces typed or suggested as Structure, in their words,
    each with Use it and Show on its page; with none, one line and Go to Shred. We build it stays beside it."""
    from PySide6.QtWidgets import QWidget
    f = QFrame(); f.setObjectName("card")
    v = QVBoxLayout(f); v.setContentsMargins(D.SPACE["l"], D.SPACE["m"], D.SPACE["l"], D.SPACE["m"]); v.setSpacing(D.SPACE["s"])
    v.addWidget(D.label("Start our structure", "title"))
    page.doors_w = QWidget(); v.addWidget(page.doors_w)                # 4.26.0 (answer 28): the two doors show on Outline only
    row = QHBoxLayout(page.doors_w); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(D.SPACE["l"])
    page.start_line = D.label("Our structure starts on Matrix & Outline > Outline. <a href='outline'>Open Outline</a>", "muted")
    page.start_line.linkActivated.connect(lambda _h: page.host.go("outline"))
    page.start_line.setVisible(False)
    v.addWidget(page.start_line)
    one = QVBoxLayout(); row.addLayout(one, 2)
    one.addWidget(D.label("The customer prescribes it", "label"))
    page.door1_say = D.label("No piece sets the structure yet.", "muted"); one.addWidget(page.door1_say)
    page.go_shred = D.button("Go to Shred", "primary", lambda: page.host.go("assign"),
                             "Shred, where a piece is typed Response Structure")
    one.addWidget(page.go_shred)
    page.door1 = D.button("Use all of them...", None, lambda: preview(page),
                          "Headings from every piece typed Structure in Shred, to check before they go in")
    one.addWidget(page.door1)
    page.pieces_w = QWidget(); page.pieces_l = QVBoxLayout(page.pieces_w)
    page.pieces_l.setContentsMargins(0, 0, 0, 0); page.pieces_l.setSpacing(D.SPACE["xs"])
    one.addWidget(page.pieces_w)
    page.piece_rows = []
    two = QVBoxLayout(); row.addLayout(two, 1)
    two.addWidget(D.label("We build it", "label"))
    two.addWidget(D.label("Draft headings of our own.", "muted"))
    page.door2 = D.button("Draft headings from...", None, None, "The customer's headings, the SOW or PWS, the evaluation "
                          "factors, or blank")
    m = QMenu(page.door2)
    import structfrom as SF
    for key, name in SF.STARTS:
        m.addAction(name, lambda k=key: drafts(page, k))
    page.door2.setMenu(m)
    two.addWidget(page.door2)
    two.addStretch(1)
    page.start_card = f
    return f


class PieceRow(QFrame):
    """One piece that sets (or may set) the structure: its words, where it is, Use it and Show on its page. A click on
    the row shows it on its page too."""
    MOST = 220

    def __init__(self, page, it, suggested):
        super().__init__()
        import structfrom as SF
        self.page, self.it, self.suggested = page, it, suggested
        self.setObjectName("card")
        h = QHBoxLayout(self); h.setContentsMargins(D.SPACE["s"], D.SPACE["xs"], D.SPACE["s"], D.SPACE["xs"]); h.setSpacing(D.SPACE["s"])
        col = QVBoxLayout(); col.setSpacing(0); h.addLayout(col, 1)
        full = " ".join(" ".join((x.get("text") or "") for x in SF.group(page.M, it)).split())
        short = full if len(full) <= self.MOST else full[:self.MOST].rsplit(" ", 1)[0] + " ..."
        self.words = D.label(short, "muted" if suggested else None); self.words.setToolTip(full)
        col.addWidget(self.words)
        self.where = D.label(("Suggested. " if suggested else "") + SF.where(it), "muted"); col.addWidget(self.where)
        self.use = D.button("Use it", None if suggested else "primary", lambda: use_piece(page, it),
                            "Read this piece into headings, to check before they go in"
                            + (" (it is typed Response Structure when they go in)" if suggested else ""))
        self.show_btn = D.button("Show on its page", "ghost", lambda: show_piece(page, it), "Shred, with this piece selected")
        h.addWidget(self.use); h.addWidget(self.show_btn)

    def mousePressEvent(self, e):
        show_piece(self.page, self.it)
        super().mousePressEvent(e)


def rows(page):
    """The pieces the list shows: [(piece, suggested)], the typed ones first."""
    import structfrom as SF
    M = page.M
    if M is None:
        return []
    return [(it, False) for it in SF.pieces(M)] + [(it, True) for it in SF.suggested(M)]


def fill(page):
    while page.pieces_l.count():
        x = page.pieces_l.takeAt(0).widget()
        if x is not None:
            x.setParent(None); x.deleteLater()
    page.piece_rows = []
    got = rows(page)
    for it, sug in got[:12]:
        r = PieceRow(page, it, sug); page.pieces_l.addWidget(r); page.piece_rows.append(r)
    if len(got) > 12:
        page.pieces_l.addWidget(D.label(f"and {len(got) - 12} more in Shred", "muted"))
    return got


def on_outline(page):
    """The builder sits on Matrix & Outline > Outline (True) or on Setup (False): starting has one place."""
    p = page.parentWidget()
    while p is not None:
        n = type(p).__name__
        if n == "OutlinePage":
            return True
        if n in ("SetupsPage", "SetupPage"):
            return False
        p = p.parentWidget()
    return True


def refresh(page):
    """Show the card while our outline is untouched (decision 15: it leaves once a start is chosen); list the pieces."""
    c = getattr(page, "start_card", None)
    if c is None:
        return
    import structfrom as SF
    M = page.M
    empty = M is not None and SF.untouched(M)
    c.setVisible(bool(empty))
    if not empty:
        return
    here = on_outline(page)
    page.doors_w.setVisible(here); page.start_line.setVisible(not here)
    got = fill(page)
    typed = sum(1 for _it, sug in got if not sug)
    page.door1_say.setVisible(not got); page.go_shred.setVisible(not got)
    page.door1.setVisible(typed >= 2)
    page.pieces_w.setVisible(bool(got))


def show_piece(page, it):
    """Shred, with the piece selected on its page."""
    h = page.host
    if h.go("assign") is False:
        return False
    pg = h.assign_page
    try:
        f = it.get("file", "")
        if pg.file != f:
            pg.files.setCurrentText(f)
            if pg.file != f:
                pg.open_file(f)
        pg.select(it["id"])
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return False
    return True


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
        v.addWidget(D.label("Read from the customer's words. Fix a level or a title the reading got wrong, add what it "
                            "missed, then put them in. Each keeps where the customer required it.", "muted"))
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Level", "Heading", "Page limit", "Source"])
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


def preview(page, run=True, its=None):
    """Use all of them (or Use it on one piece, its): read the pieces, show the preview, then finish(). Returns the
    entries put in, or the dialog (run=False; the test then calls finish with dlg.heads() and dlg.pieces)."""
    import structfrom as SF
    M = page.M
    if M is None:
        return None
    heads = SF.read(M, its)
    if not heads and not (its or SF.pieces(M)):
        page.host.status("No piece sets the structure yet.")
    dlg = Preview(page, heads)
    dlg.pieces = [it for it in (its or []) if not __import__("shredtypes").has(it, "structure")]
    page._preview = dlg
    if not run:
        return dlg
    if dlg.exec() != QDialog.Accepted:
        return None
    return finish(page, dlg.heads(), dlg.pieces)


def use_piece(page, it, run=True):
    """Use it: one piece's headings (with the list it leads in), through the same preview."""
    import structfrom as SF
    return preview(page, run, SF.group(page.M, it) if page.M is not None else [it])


class AddOrReplace(QDialog):
    """4.55.0 (UX decision 13): asked only when our outline already holds a structure, before anything changes. The
    effect first, in counts and names; Add, Replace or Cancel."""

    def __init__(self, page, eff):
        super().__init__(page)
        self.setWindowTitle("Our outline already has a structure")
        self.choice = "cancel"
        v = QVBoxLayout(self)
        self.add_say = D.label(f"Add: {eff['add']} heading(s) go in after the {eff['have']} in our outline. Nothing else "
                               "changes.", None)
        lose = eff["lose"]
        names = ", ".join(lose[:10]) + (f" and {len(lose) - 10} more" if len(lose) > 10 else "")
        rep = (f"Replace: {eff['add']} heading(s) take the place of the {eff['have']} in our outline. "
               + (f"{len(lose)} requirement(s) placed in them lose their place and stay in the matrix as not placed: {names}."
                  if lose else "No requirement loses its place.")
               + (f" {eff['lose_other']} other placed piece(s) lose their place too." if eff.get("lose_other") else ""))
        self.rep_say = D.label(rep, None)
        for x in (self.add_say, self.rep_say):
            x.setWordWrap(True); v.addWidget(x)
        row = QHBoxLayout(); row.addStretch(1); v.addLayout(row)
        self.b_add = D.button("Add to our outline", "primary", lambda: self.pick("add"))
        self.b_rep = D.button("Replace our outline", "danger", lambda: self.pick("replace"))
        self.b_cancel = D.button("Cancel", None, lambda: self.pick("cancel"))
        for b in (self.b_add, self.b_rep, self.b_cancel):
            row.addWidget(b)

    def pick(self, choice):
        self.choice = choice
        (self.accept if choice != "cancel" else self.reject)()


def finish(page, heads, typed=(), answer=None):
    """Put the headings in. Our outline untouched: they simply go in. A structure there: Add or Replace is asked first
    (answer: "add", "replace" or "cancel" given by a test). A suggested piece used is typed Response Structure with them.
    Returns the entries put in, or None."""
    import structfrom as SF
    M = page.M
    page._ask = None
    if M is None or not heads:
        return None
    if SF.untouched(M):
        replace = True
    else:
        dlg = AddOrReplace(page, SF.effect(M, heads))
        page._ask = dlg
        if answer is None:
            dlg.exec()
            answer = dlg.choice
        if answer not in ("add", "replace"):
            return None
        replace = answer == "replace"
    return put(page, heads, replace, typed)


def put(page, heads, replace=None, typed=()):
    import setupdoc as SD
    import shredtypes as ST
    import structfrom as SF
    M = page.M
    if M is None or not heads:
        return []
    page.host.review.snap("the required structure")
    for it in typed:                                  # 4.55.0: a suggested piece used is typed Structure, so Shred agrees
        ST.set_types([it], ST.combine(ST.types_of(it), "structure", True), lambda i, t: M.log(i, t))
    ents = SF.put(M, heads, replace)
    SD.setup_of(M).setdefault("outline_from", "prescribed")      # 4.55.0: a start is chosen; Outline's question leaves too
    page.host.changed()
    diag.activity("structure_required_put", n=len(ents))
    page.refresh()
    page.host.status(f"{len(ents)} required heading(s) in our outline.")
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
    __import__("setupdoc").setup_of(M).setdefault("outline_from", "ours")    # 4.55.0: a start is chosen
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
