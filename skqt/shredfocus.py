"""Shred and Place, as designed (4.5.0; claude/stationkeeper-shred-place-plan-4.5.md, steps 3 and 5). The Shred page
shows one job per mode. Shred says what each piece is; Place puts it in our outline. Every tool that leaves the screen
keeps its key, its right-click entry or a place in More.

apply(page, mode): mode "shred" or "place" (placemode.apply calls it on every visit).
- Both: the selection bar, the topic bar, the bottom decide and capture panel and the help line leave; Fit width and
  Fix text are in More. Suggestions are always worked out: the piece pane
  shows the suggested type dashed, and Enter takes it and goes to the next piece not shredded (4.53.0).
- Shred: This document is shredded is a checkbox (4.26.0; it was the main button and opened the next document). N goes
  to the next piece not sorted.
- Place: the piece pane is the place pane (placepane); N goes to the next piece not placed. 4.55.0 (decision 17): none of
  Shred's whole-document row shows (place_row); the document picker stays and Fit width is a button beside it.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QMenu

import diag
from . import design as D

LEAVE = ("next_btn", "sg_btn", "cap_btn", "pan_btn", "fit_btn", "fix_btn", "done_btn")


def install(page):
    """Once, in AssignPage.__init__: the checkbox and More on the document row.
    4.26.0 (answer 17): This document is shredded is a plain checkbox (it marks, and opens nothing); Take the selected
    suggestions and Split are on the bar at the selection (skqt/shredselbar); Next document, Pan, Add missed text,
    Take every suggestion and the Captured list left More. The page pans and zooms at any time (Space and drag, a middle-button drag, Ctrl+wheel);
    missed text is added from a dragged box (skqt/shredband)."""
    from PySide6.QtWidgets import QCheckBox
    bar = page.top_bar
    page.focus = "shred"
    page.shred_check = QCheckBox("This document is shredded")
    page.shred_check.toggled.connect(lambda on: shredded(page, on))
    page.shred_main = page.shred_check                    # the name the older code and tests know
    page.focus_more = D.button("More", None, None, "Fix text, the page's size")
    m = QMenu(page.focus_more)
    page.more_acts = {}
    for name, fn in (("Fix text  F2", lambda: __import__("skqt.fixtext", fromlist=["x"]).toggle(page)),
                     ("Fit width  Ctrl+0", lambda: page.view.fit())):
        page.more_acts[name.split("  ")[0]] = m.addAction(name, fn)
    page.focus_more.setMenu(m)
    bar.addWidget(page.focus_more)
    bar.addWidget(page.shred_check)
    __import__("skqt.shredband", fromlist=["x"]).install(page)
    __import__("skqt.shredselbar", fromlist=["x"]).install(page)       # 4.26.0: the bar at the selection
    __import__("skqt.shredprogress", fromlist=["x"]).install(page)     # 4.26.0: the compliance bar, moved from the Dashboard
    import os
    if os.environ.get("SK_SHRED_CLASSIC"):
        page.focus = None
        for x in (page.shred_check, page.focus_more):
            x.setVisible(False)
    from PySide6.QtGui import QKeySequence, QShortcut
    QShortcut(QKeySequence("Ctrl+0"), page.view, activated=lambda: page.view.fit())


def apply(page, mode):
    """Show what the mode needs (and only that). Returns the mode. SK_SHRED_CLASSIC (the older tests of the machinery
    under the screen) keeps the page as it was before 4.5.0."""
    import os
    if os.environ.get("SK_SHRED_CLASSIC"):
        return off(page)
    page.focus = mode
    try:
        for name in LEAVE:
            b = getattr(page, name, None)
            if b is not None:
                b.setVisible(False)
        for name in ("bulk", "topic_bar", "decide_area", "sg_strip", "vol_add_btn", "vol_ren_btn", "vol_style"):
            x = getattr(page, name, None)
            if x is not None:
                x.setVisible(False)
        for x in getattr(page, "outline_rows", []):                  # + Heading, Start from: Outline builds the outline
            x.setVisible(False)
        page.note.setVisible(not page.file)                         # only the empty page's one way in
        on = mode == "shred" and bool(page.file) and page.cx is None
        page.shred_check.setVisible(on)
        if page.view.pan_tool:                                       # the Pan tool is gone: Space, the middle button
            page.toggle_pan(False)
        if getattr(page, "sort_on", False):                          # 4.26.0 (answer 30): Sort mode is Quick tools > Sort's;
            page.sort_on = False; page.sort_btn.setChecked(False)    # here the keys 1 to 9 file nothing
        page.show_queue()
        if mode != "shred":
            __import__("skqt.capturecard", fromlist=["x"]).closing(page)       # 4.12.0: the card is Shred's
        if mode == "shred":
            suggest_on(page)
        elif page.sg_on:                                             # Place places: the type suggestions stay in Shred
            page.sg_on = False
            page.restyle()
        page.show_card(page.selected())
        __import__("skqt.shredselbar", fromlist=["x"]).gutter(page, mode == "shred")   # 4.53.0: the bar's margin
        __import__("skqt.shredselbar", fromlist=["x"]).later(page)
        __import__("skqt.shredprogress", fromlist=["x"]).refresh(page)
        place_row(page)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return mode


PLACE_HIDES = ("queue_lbl", "done_btn", "next_btn", "focus_more", "shred_check", "reshred_btn")


def place_row(page):
    """4.55.0 (UX decision 17): on Place (and L to M and Coverage) none of Shred's whole-document row shows: the count of
    documents not shredded, Mark shredded, This document is shredded, re-shred, and More (Fix text, Fit width). The
    document picker stays, and Fit width is a button of its own beside it (Ctrl+0 too). Shred's own row is unchanged.
    show_queue calls it after it sets the row, so a document picked on Place keeps the row hidden."""
    if getattr(page, "focus", None) in ("struct", "comp", "deliv"):            # 4.74.0: a pass keeps Shred's whole-document row away
        for name in ("queue_lbl", "done_btn", "next_btn", "shred_check", "reshred_btn"):   # (a document picked in the pass drew it again)
            x = getattr(page, name, None)
            if x is not None:
                x.setVisible(False)
        if page.focus in ("comp", "deliv") and getattr(page, "comp_state", None) is not None:
            __import__("skqt.comppass", fromlist=["x"]).fill(page)
        return False
    if getattr(page, "focus", None) != "place":
        if getattr(page, "fit_btn", None) is not None:
            page.fit_btn.setVisible(False)
        if getattr(page, "focus_more", None) is not None and page.focus == "shred":
            page.focus_more.setVisible(True)
            page.queue_lbl.setVisible(True)
        return False
    for name in PLACE_HIDES:
        x = getattr(page, name, None)
        if x is not None:
            x.setVisible(False)
    if getattr(page, "fit_btn", None) is not None:
        page.fit_btn.setVisible(bool(page.file))
    return True


def suggest_on(page):
    """Suggestions always worked out, quietly (no strip): the pane shows the suggested type, Enter takes it."""
    if page.R is None or page.cx is not None or page.sg_on:
        return False
    try:
        page.sg_on = True
        page.run_suggest()
        page.restyle()
    except Exception:  # noqa: BLE001
        diag.swallowed()
        page.sg_on = False
    return page.sg_on


def shredded(page, on=True):
    """Tick or untick This document is shredded. It marks the document; nothing else opens."""
    got = page.mark_reviewed(bool(on))
    if page.file:
        page.host.status(f"{page.file} is marked shredded." if got else f"{page.file}: the mark is off.")
    return got


def enter(page):
    """Enter: Place it on Place. On Shred (4.53.0, UX decision 11): take the suggestion of each selected piece that has
    one waiting, then go to the next piece not shredded after the last one selected (its bar opens beside it). With no
    suggestion waiting Enter changes nothing and stays. A chip or a type letter sets a type and stays; only Enter moves."""
    if getattr(page, "focus", "") == "place":
        from . import placepane as PP
        return PP.place_it(page)
    if getattr(page, "focus", "") == "struct":                       # 4.70.0: the pass's own Enter
        return __import__("skqt.structpass", fromlist=["x"]).enter(page)
    if getattr(page, "focus", "") in ("comp", "deliv"):                         # 4.72.0
        return __import__("skqt.comppass", fromlist=["x"]).enter(page)
    rows = page.selected()
    before = (getattr(page.R, "undo", None) or [None])[-1] if page.R is not None else None
    n = page.accept_suggestions(rows=rows)
    if not n or getattr(page, "focus", "") != "shred" or page.cx is not None or page.R is None:
        return n
    try:
        undo = getattr(page.R, "undo", None) or []
        step = undo[-1][0] if undo and (before is None or undo[-1][0] is not before[0]) else None
        page._enter_took = (step, [it["id"] for it in rows])          # Undo selects these again
        go_on(page, rows[-1]["id"] if rows else None)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return n


def open_rows(page):
    """The pieces of this document not shredded yet: no type and no decision (headings left out), in order."""
    import shredtypes as ST
    if page.R is None or not page.file:
        return []
    return [it for it in page.R.rows_of(page.file) if it.get("type") != "Heading"
            and not ST._keys(it.get(ST.FIELD)) and not it.get("decision")]


def go_on(page, after_id):
    """After Enter: select the next piece not shredded after after_id, else the first one left in the document; with
    none left the selection stays and the status line says so. Nothing is marked shredded here."""
    rows = open_rows(page)
    if not rows:
        page.host.status("Every piece in this document has a type.")
        return None
    ids = [it["id"] for it in page.R.rows_of(page.file)]
    at = ids.index(after_id) if after_id in ids else -1
    nxt = next((it for it in rows if ids.index(it["id"]) > at), rows[0])
    page.select(nxt["id"])
    return nxt["id"]


def taken_back(page):
    """Called by do_undo before it undoes: when the step it undoes is the one Enter took, the ids Enter took (Undo
    selects them again), else None."""
    took = getattr(page, "_enter_took", None)
    undo = getattr(page.R, "undo", None) if page.R is not None else None
    if not took or not undo or took[0] is None or undo[-1][0] is not took[0]:
        return None
    page._enter_took = None
    return list(took[1])


def show_back(page, ids):
    """After Undo put Enter's step back: the piece it took is in view again."""
    b = page.view.boxes.get(ids[-1]) if ids else None
    if b is not None:
        page.view.ensureVisible(b, 40, 140)


def next_open(page):
    """N: the next piece not sorted (Shred) or not placed (Place) in this document, after the one selected."""
    if page.R is None or not page.file:
        return None
    if getattr(page, "focus", "") == "struct":                       # 4.70.0: the pass's next suggestion, across documents
        return __import__("skqt.structpass", fromlist=["x"]).next_open(page)
    if getattr(page, "focus", "") in ("comp", "deliv"):                         # 4.72.0
        return __import__("skqt.comppass", fromlist=["x"]).go_next(page)
    rows = [it for it in page.R.rows_of(page.file) if it.get("type") != "Heading"]
    if getattr(page, "focus", "") == "place":
        import homesuggest as HS
        left = set(HS.left(page.M)["unplaced"])
        rows = [it for it in rows if it["id"] in left]
    else:
        rows = open_rows(page)
    if not rows:
        page.host.status("Nothing left here." if getattr(page, "focus", "") != "place" else "Everything here is placed.")
        return None
    cur = page.selected()
    ids = [it["id"] for it in page.R.rows_of(page.file)]
    at = ids.index(cur[-1]["id"]) if cur and cur[-1]["id"] in ids else -1
    nxt = next((it for it in rows if ids.index(it["id"]) > at), rows[0])
    page.select(nxt["id"])
    return nxt["id"]


def flag(page, it):
    """4.5.0 (loose end): on the piece pane, "Changed by <version>" while a new version's change to it waits to be
    shredded again (reshred.flagged), and "New in <version>" for a piece a new version added (newversion)."""
    said = []
    try:
        import reshred as RS
        if page.host.ws is not None:
            f = RS.flagged(page.host.ws.root).get(it.get("id"))
            if f:
                said.append(f)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    if str(it.get("new") or "").startswith("New in"):                # (pagejoin's joins use the same field)
        said.append(str(it["new"]))
    if said:
        lab = page.add(D.label("  \u00b7  ".join(said), "crit"))
        page.flag_label = lab
        return lab
    page.flag_label = None
    return None


def off(page):
    """The page as it was before 4.5.0: every control on the screen and the keys deciding as they did (R places in the
    target, C is Support). Kept for the older tests of the machinery under the screen; mainwin's next visit to Shred or
    Place applies the focus again."""
    page.focus = None
    for name in LEAVE + ("bulk", "topic_bar", "decide_area", "vol_add_btn", "vol_ren_btn", "vol_style"):
        x = getattr(page, name, None)
        if x is not None:
            x.setVisible(True)
    for x in getattr(page, "outline_rows", []):
        x.setVisible(True)
    page.sg_strip.setVisible(page.sg_on)
    page.note.setVisible(True)
    if getattr(page, "progress_row", None) is not None:
        page.progress_row.setVisible(False)
    for x in (page.shred_check, page.focus_more):
        x.setVisible(False)
    __import__("skqt.shredselbar", fromlist=["x"]).gutter(page, False)
    page.show_card(page.selected())
    return None
