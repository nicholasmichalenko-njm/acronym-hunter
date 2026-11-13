"""On Shred's piece pane (4.12.0; claude/stationkeeper-capture-cards-plan-4.12.md, A5 and B2): which deliverable a
Deliverable piece belongs to, and what was captured from the piece, each with Open (to edit it in place) and Take out.

A piece typed Deliverable shows Which deliverable: the deliverables already on the effort's board, by name and kind.
Picking one attaches the piece (the deliverable's page lists it under From the solicitation). A new deliverable is made on
Dashboard > Deliverables only; with none there, the drop-down says so and a button opens it. Rules only (No AI)."""
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget

import deliverables as DL
import diag
import shredtypes as ST
from . import design as D

NONE = "No deliverables yet"
GO = "Go to Overview > Deliverables to add a deliverable"


def _rec(page):
    import effortrec as R
    return R.Record(page.host.ws.root)


def add(page, rows):
    """The two blocks, under the type chips. Returns the number of lines added."""
    page.deliv_pick = page.deliv_go = None
    page.capture_lines = []
    if len(rows) != 1 or page.cx is not None or page.host.ws is None:
        return 0
    it = rows[0]
    n = 0
    try:
        if ST.has(it, "deliverable"):
            n += deliverable_row(page, it)
        n += captured(page, it)
    except Exception:
        diag.swallowed()
    return n


def deliverable_row(page, it):
    rec = _rec(page)
    lst = DL.items(rec)
    now = DL.of_piece(rec, it["id"])
    page.head("Which deliverable")
    c = QComboBox()
    if not lst:
        c.addItem(NONE, None)
        c.setEnabled(False)
        page.deliv_pick = c
        page.add(c)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["xs"])
        row.addWidget(D.label(GO + ".", "muted"))
        page.deliv_go = D.button("Open Deliverables", None, lambda: go_deliverables(page), "Overview > Deliverables, to add one")
        row.addWidget(page.deliv_go); row.addStretch(1)
        page.body_add_layout(row)
        return 1
    c.addItem("Not attached yet" if now is None else "Take it off", None)
    for d in lst:
        c.addItem(f"{d['name']}  ({d.get('kind') or 'Deliverable'})", d["id"])
    if now is not None:
        c.setCurrentIndex(max(0, c.findData(now["id"])))
    c.setToolTip("The deliverable this piece describes. Its page lists the piece under From the solicitation.")
    c.activated.connect(lambda i, cb=c: attach(page, cb.itemData(i)))
    page.deliv_pick = c
    page.add(c)
    if now is not None:
        page.add(D.label(f"Attached to {now['name']}. Pick another to move it.", "muted"))
    return 1


def attach(page, did, it=None):
    """Attach the selected piece to a deliverable (None takes it off). Returns True when it changed."""
    rows = page.selected()
    it = it or (rows[0] if len(rows) == 1 else None)
    if it is None:
        return False
    rec = _rec(page)
    if did is None:
        ok = DL.detach(rec, it["id"])
        msg = "Taken off its deliverable"
    else:
        _text, src = page.capture_source()
        piece = {"sid": it["id"], "doc": src.get("doc", ""), "page": src.get("page", ""), "loc": src.get("loc", ""),
                 "text": it.get("text", "")}
        ok = DL.attach_piece(rec, did, piece)
        msg = f"Attached to {DL.get(rec, did)['name']}"
        if ok and not ST.has(it, "deliverable"):
            __import__("skqt.shredbar", fromlist=["x"]).capture_types(page, "deliverable", [it["id"]])
    if ok:
        if did:
            diag.activity("shred_deliverable_attached")
        else:
            diag.activity("shred_deliverable_taken_off")
        page.host.status(f"{it['id']}: {msg}")
        page.show_card(page.selected())
        page.host.changed()
    return ok


def go_deliverables(page):
    page.host.go("deliverables")
    return True


def pick_deliverable(page):
    """Capture > Deliverable on Shred: the piece is typed Deliverable (if it is not) and the pane shows Which deliverable."""
    rows = page.selected()
    if len(rows) != 1:
        return page.host.status("Select one piece to attach to a deliverable.")
    if not ST.has(rows[0], "deliverable"):
        __import__("skqt.shredbar", fromlist=["x"]).toggle_piece(page, "deliverable", rows)
    page.show_card(page.selected())
    if getattr(page, "deliv_pick", None) is not None:
        page.deliv_pick.setFocus()
    return page.deliv_pick


# ------------------------------------------------------------------ A5: captured from this piece
def lines_of(page, it):
    """[(excerpt, text)] for the captures holding this piece's words."""
    import excerpts as EX
    import contactcard as CC
    rec = _rec(page)
    names = {b["id"]: b["name"] for b in EX.bins(rec, page.host.config_dir)}
    out = []
    for x in EX.of_sentence(rec, it["id"]):
        name = names.get(x["bin"], x["bin"])
        what = x.get("value") or ""
        if x["bin"] == "contact":
            c = rec.contact(x["refs"][0]) if x.get("refs") else None
            what = CC.summary(c) if c else what
        words = EX.text_of(x)
        out.append((x, f"<b>{name}</b>: " + (what or f"“{words[:90]}{'...' if len(words) > 90 else ''}”")))
    return out


def captured(page, it):
    got = lines_of(page, it)
    if not got:
        return 0
    page.head("Captured from this piece")
    for x, text in got:
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["xs"])
        lab = D.label(text, None); h.addWidget(lab, 1)
        h.addWidget(D.button("Open", None, lambda _=False, xx=x: open_capture(page, xx), "Edit it in place"))
        h.addWidget(D.button("Take out", "ghost", lambda _=False, xx=x, i=it["id"]: take_out(page, xx, i),
                             "Take this capture off the piece"))
        page.add(w)
        page.capture_lines.append((x["id"], lab))
    return len(got)


def open_capture(page, x):
    """A contact opens on the card, filed values and all; the other captures open their editor."""
    if x["bin"] == "contact":
        from . import capturecard as CCARD
        return CCARD.open_card(page, "contact", cid=(x.get("refs") or [None])[0])
    return page.edit_excerpt(x["id"])


def take_out(page, x, sid):
    """Take the capture off the piece: a contact loses what this piece gave it (and goes if nothing is left)."""
    if x["bin"] == "contact" and x.get("refs"):
        import contactcard as CC
        CC.take_out_piece(_rec(page), x["refs"][0], sid)
    return page.remove_excerpt(x["id"])
