"""A term picked on the page, in The list (4.30.4; Nicholas 2026-11-13 20:20: "If I'm looking at the page and I click on
a highlighted selection, I want to be able to make a decision for the item that I clicked on, not the item in the list
at that time ... and then if I click back into the list, go back to making a decision on that").

The page beside the list shows the selected term's place, with the scan's other readings boxed in green. A click on one
of those boxes that holds another of the scan's terms makes that term the one on the card: its definition, its buttons,
its keys, on the same page. The list is left as it is and nothing in it is selected; a click on any row of the list
goes back to the list's own term. A click on a box that holds no term does what it did: it shows what was read there.
Rules only (No AI); nothing leaves the PC."""
import re

import diag


def clear_layout(lay):
    """Take everything out of a layout, at every depth. 4.30.7 (Nicholas 2026-11-13 20:30: "the buttons move up over top
    of each other as I'm making decisions"): the card was cleared one level down only, so a row inside a row (the
    Definition box with its symbols button) stayed on the card with no place of its own, and each new card drew over it."""
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.hide(); w.setParent(None); w.deleteLater()
        elif it.layout() is not None:
            clear_layout(it.layout())
            it.layout().deleteLater()


def term_in(session, reading, loc, but="", at=None):
    """The scan's term a clicked reading holds: one found at this place, written in the reading as a whole word. When
    the reading holds several, the one nearest the click (at: how far along the reading the click was, 0 to 1), or the
    longest when that is not known. None when it holds none (or only the term already on the card)."""
    text = str(reading or "")
    if not text.strip() or session is None:
        return None
    hits = []
    for t, d in session.results.items():
        if t == but or d.get("file_error") or loc not in (d.get("locations") or []):
            continue
        for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", text):
            hits.append((t, (m.start() + m.end()) / 2.0))
    if not hits:
        return None
    if at is None:
        return max(hits, key=lambda h: len(h[0]))[0]
    spot = min(max(float(at), 0.0), 1.0) * len(text)
    return min(hits, key=lambda h: (abs(h[1] - spot), -len(h[0])))[0]


def picked(page, current, reading, loc, at=None):
    """A box clicked on the page beside the list. Returns the term now on the card, or None when nothing changed."""
    t = term_in(page.session, reading, loc, but=current, at=at)
    if t is None:
        return None
    page.open_at = (t, loc)
    diag.activity("acronym_picked_on_page")
    if page.select(t):                                    # 4.30.7: it is in the list as filtered: the list focuses it too,
        return t                                          # so the page and the list always show the same term
    page.pinned = t
    was = page.table.blockSignals(True)
    try:
        page.table.clearSelection()                       # not in the list as filtered: the card alone shows it
    finally:
        page.table.blockSignals(was)
    page.show_detail()
    page.host.status(f"{t} is not in the list as it is filtered. It is on the card; click a row of the list to go back.")
    return t


def terms(page):
    """The term or terms the card is for: the list's selection, or the term picked on the page while the list has none."""
    sel = page.selected_terms()
    if sel:
        page.pinned = None                                # a click in the list goes back to the list
        return sel
    t = getattr(page, "pinned", None)
    return [t] if t and page.session is not None and t in page.session.results else []


def hook(page, view, term):
    """The card's page view: clicks pick; a term picked on the page opens on the place it was picked at."""
    view.on_pick = lambda reading, loc, at=None: picked(page, term, reading, loc, at)
    at = getattr(page, "open_at", None)
    if at and at[0] == term and at[1] in view.locs:
        page.open_at = None
        view.show_place(view.locs.index(at[1]))
    return view
