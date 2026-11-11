"""Shred and Place, as designed (4.5.0; claude/stationkeeper-shred-place-plan-4.5.md, steps 3 and 5). The Shred page
shows one job per mode. Shred says what each piece is; Place puts it in our outline. Every tool that leaves the screen
keeps its key, its right-click entry or a place in More.

apply(page, mode): mode "shred" or "place" (placemode.apply calls it on every visit).
- Both: the selection bar, the topic bar, the bottom decide and capture panel and the help line leave; Next document,
  Suggest, Add missed text, Pan, Fit width and Fix text go to More. Suggestions are always worked out: the piece pane
  shows the suggested type dashed, and Enter takes it.
- Shred: the main button is Mark this document shredded (it marks the document and opens the next one). N goes to the
  next piece not sorted.
- Place: the piece pane is the place pane (placepane); N goes to the next piece not placed.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QMenu

import diag
from . import design as D

LEAVE = ("next_btn", "sg_btn", "cap_btn", "pan_btn", "fit_btn", "fix_btn", "done_btn")


def install(page):
    """Once, in AssignPage.__init__: the main button and More on the document row."""
    bar = page.top_bar
    page.focus = "shred"
    page.shred_main = D.button("Mark this document shredded", "primary", lambda: shredded(page),
                               "Every piece of this document is looked at: it is marked shredded and the next one opens")
    page.focus_more = D.button("More", None, None, "Fix text, suggestions, missed text, the page's size")
    m = QMenu(page.focus_more)
    page.more_acts = {}
    for name, fn in (("Fix text  F2", lambda: __import__("skqt.fixtext", fromlist=["x"]).toggle(page)),
                     ("Take every suggestion", lambda: page.accept_suggestions(clear_only=False)),
                     ("Add missed text", lambda: page.toggle_capture()),
                     ("Next document", lambda: page.next_file()),
                     ("Fit width  Ctrl+0", lambda: page.view.fit()),
                     ("Pan  H", lambda: page.toggle_pan()),
                     ("Captured list", lambda: page.all_excerpts())):
        page.more_acts[name.split("  ")[0]] = m.addAction(name, fn)
    page.focus_more.setMenu(m)
    bar.addWidget(page.focus_more)
    bar.addWidget(page.shred_main)
    import os
    if os.environ.get("SK_SHRED_CLASSIC"):
        page.focus = None
        page.shred_main.setVisible(False); page.focus_more.setVisible(False)
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
        page.shred_main.setVisible(mode == "shred" and bool(page.file) and page.cx is None)
        page.more_acts["Take every suggestion"].setVisible(mode == "shred")
        page.more_acts["Captured list"].setVisible(mode == "shred")
        if mode == "shred":
            suggest_on(page)
        elif page.sg_on:                                             # Place places: the type suggestions stay in Shred
            page.sg_on = False
            page.restyle()
        page.show_card(page.selected())
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return mode


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


def shredded(page):
    """Mark this document shredded, then the next one not shredded opens."""
    if not page.mark_reviewed(True):
        return None
    nxt = page.next_file()
    page.host.status(f"{page.file} shredded." if not nxt else f"Shredded. Next: {nxt}.")
    return nxt or True


def enter(page):
    """Enter: Place it on Place; take the suggestion on Shred."""
    if getattr(page, "focus", "") == "place":
        from . import placepane as PP
        return PP.place_it(page)
    return page.accept_suggestions(rows=page.selected())


def next_open(page):
    """N: the next piece not sorted (Shred) or not placed (Place) in this document, after the one selected."""
    if page.R is None or not page.file:
        return None
    import shredtypes as ST
    rows = [it for it in page.R.rows_of(page.file) if it.get("type") != "Heading"]
    if getattr(page, "focus", "") == "place":
        import homesuggest as HS
        left = set(HS.left(page.M)["unplaced"])
        rows = [it for it in rows if it["id"] in left]
    else:
        rows = [it for it in rows if not ST._keys(it.get(ST.FIELD)) and not it.get("decision")]
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
    page.shred_main.setVisible(False)
    page.focus_more.setVisible(False)
    page.show_card(page.selected())
    return None
