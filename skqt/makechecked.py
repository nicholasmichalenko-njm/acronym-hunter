"""Shred: Make it checked... (4.26.0; answer 27; the naming plan of 2026-11-12: "A typed piece can become a checked
one"). A piece typed Rule is only listed on Rules & Dates. This button opens Add a rule filled from the piece (kind,
what it is about, what it says); the rule made is read by Effort Formatting and Submit like any other and keeps the
piece as its source. A piece typed Date gets the same offer: the Key date card, filled from the piece, which puts it on
the calendar. The app always waits for the button: it never makes a checked rule or a date by itself. Rules only."""
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit

import diag
from . import design as D

TEXT = "Make it checked..."


def kinds_of(it):
    """Which offers the piece gets: "rule", "date", both, or neither."""
    import shredtypes as ST
    return [k for k in ("rule", "date") if ST.has(it, k)]


def guess(text):
    """(kind, about, says) for the dialog: what the reader finds in the words, else Format with the words themselves."""
    import subreq as SR
    got = [g for g in SR.find(text or "") if g[0] not in ("Due", "Questions due")] or SR.find(text or "")
    if got:
        return got[0]
    return ("Format", "", " ".join(str(text or "").split())[:200])


def register(page):
    import docversions as DV
    import subreq as SR
    return SR.Register(DV.Library(page.host.ws.p("documents")).load())


def source_of(page, it):
    return {"doc": it.get("file", "") or (page.file or ""), "loc": " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x),
            "text": it.get("text", ""), "sid": it.get("id", "")}


def make_rule(page, it, answer=None):
    """The dialog, filled from the piece; answer (tests): (kind, about, says). Returns the rule's key, or None."""
    import subreq as SR
    if page.host.ws is None or it is None:
        return None
    kind, about, says = guess(it.get("text", ""))
    if answer is None:
        dlg = QDialog(page); dlg.setWindowTitle("Make it a rule that is checked"); dlg.setMinimumWidth(520)
        f = QFormLayout(dlg)
        kc = QComboBox(); kc.addItems([k for k in SR.KINDS if k not in ("Due", "Questions due")]); kc.setCurrentText(kind)
        sj = QLineEdit(about); sj.setPlaceholderText("Volume II, Font, Attachment J-3...")
        vl = QLineEdit(says); vl.setPlaceholderText("15 pages")
        f.addRow("Kind", kc); f.addRow("About", sj); f.addRow("Says", vl)
        note = D.label("Effort Formatting and Submit check it from now on. It keeps this piece as its source.", "muted")
        f.addRow(note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        bb.button(QDialogButtonBox.Ok).setText("Make it checked")
        f.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return None
        answer = (kc.currentText(), sj.text(), vl.text())
    kind, about, says = answer
    k = register(page).add(kind or "Format", about or "", says, source=source_of(page, it))
    if k:
        diag.activity("shred_rule_made_checked")
        page.host.toast("Checked from now on: it is on Submission Checklist, and Effort Formatting and Submit read it")
    else:
        page.host.status("Nothing was made: say what the rule says.")
    return k


def make_date(page, it):
    """The Key date card, filled from the piece."""
    from . import capturecard as CCD
    card = CCD.open_card(page, "keydate")
    if card is not None:
        diag.activity("shred_date_made_checked")
    return card


def made(page, it):
    """True when a checked rule already has this piece as its source."""
    try:
        return any((m.get("source") or {}).get("sid") == it.get("id") for m in register(page).state.get("manual", []))
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return False


def add_row(page, rows):
    """On the piece pane, under the types: Make it checked... for one piece typed Rule or Date."""
    page.checked_btn = page.checked_date_btn = None
    if len(rows) != 1 or page.cx is not None or page.host.ws is None:
        return None
    it = rows[-1]
    ks = kinds_of(it)
    if not ks:
        return None
    row = QHBoxLayout(); row.setSpacing(D.SPACE["xs"])
    if "rule" in ks:
        done = made(page, it)
        page.checked_btn = D.button("Checked (make another...)" if done else TEXT, "ghost", lambda: make_rule(page, it),
                                    "A rule Effort Formatting and Submit check, filled from this piece. Until then the piece is "
                                    "only listed on Submission Checklist")
        row.addWidget(page.checked_btn)
    if "date" in ks:
        page.checked_date_btn = D.button(TEXT if "rule" not in ks else "Make the date checked...", "ghost", lambda: make_date(page, it),
                                         "A key date on the calendar, filled from this piece")
        row.addWidget(page.checked_date_btn)
    row.addStretch(1)
    page.body_add_layout(row)
    return row
