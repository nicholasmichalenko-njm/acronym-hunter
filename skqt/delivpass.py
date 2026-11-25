"""Shred in passes, the Deliverables pass on the screen (4.76.0). The Shred page in the pass's own mode (the Compliance
pass's page and bar, skqt/comppass.py, with these buttons in place of the three kinds): Document We Write, Form We Fill
In, File We Submit, Redline We Return on 1 to 4, each a row of the Deliverables list at once with the customer's words
attached; the same button again takes it off. Key date sends the piece to the effort's calendar through the capture
the Shred already has. Rules only; nothing leaves the PC."""
from PySide6.QtWidgets import QLabel

import delivmark as DM
import diag
from . import design as D

KEY = "delivpass"


def _who():
    try:
        import effort as E
        return E.user_name()
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def buttons(page, f, rows, M, it, one, col):
    """The pass's own buttons on the bar beside the piece."""
    from . import comppass as CP
    rec = CP.rec_of(page)
    cur = DM.kind_of(rec, it) if one else ""
    d = DM.of_piece(rec, it) if one else None
    f.kinds, f.on_list, f.open_list, f.keydate = {}, None, None, None
    for n, (key, name) in enumerate(DM.KINDS, 1):
        b = D.button(f"{n}   {name}", None, lambda _c=False, k=key: mark(page, k), f"{name} ({n}): a row of the Deliverables list at once")
        b.setCheckable(True); b.setChecked(key == cur); b.setProperty("sk_switch", True)
        b.setStyleSheet("text-align:left;")
        col.addWidget(b); f.kinds[key] = b
    if d is not None:
        f.on_list = QLabel("On the Deliverables list: " + d["name"]); f.on_list.setWordWrap(True)
        col.addWidget(f.on_list)
        f.open_list = D.button("Open the Deliverables list", "ghost", lambda: page.host.go("deliverables"), "The list with this deliverable on it: name, owner, due")
        col.addWidget(f.open_list)
    f.keydate = D.button("Key date  D", "ghost", lambda: key_date(page), "A date the customer sets: it goes on the effort's calendar at once")
    col.addWidget(f.keydate)
    return f


def mark(page, key):
    """A kind's button or key. One piece: on, changed to this kind, or off when it already has it. Several pieces:
    each becomes a deliverable of the kind."""
    from . import comppass as CP
    M = CP.M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        page.host.status("Select a piece of the customer's text first.")
        return None
    rec = CP.rec_of(page)
    who = _who()
    if all(DM.kind_of(rec, it) == key for it in rows):
        for it in rows:
            DM.unmark(rec, it, who)
        msg = "Taken off the Deliverables list."
        out = "off"
    else:
        names = []
        for it in rows:
            DM.marks(M).pop(it["id"], None)
            did, _how = DM.mark(rec, it, key, who=who)
            if did:
                names.append(DM.DL.get(rec, did)["name"])
        msg = f"{DM.NAME[key]}: {names[0]} is on the Deliverables list." if len(names) == 1 else f"{DM.NAME[key]}: {len(names)} on the Deliverables list."
        out = "on"
    diag.activity("deliverable_marked", n=len(rows))
    try:
        page.host.changed()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    CP.done(page, msg)
    return out


def key_date(page, answer=None):
    """Key date (D): the capture the Shred has, from the selected piece; the calendar has it at once."""
    if not page.selected():
        page.host.status("Select the piece that holds the date first.")
        return None
    got = page._do_capture("keydate", answer)
    if got:
        __import__("skqt.comppass", fromlist=["x"]).done(page)
    return got
