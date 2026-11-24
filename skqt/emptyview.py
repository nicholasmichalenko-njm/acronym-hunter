"""A page with nothing on it yet (4.62.0; Nicholas 2026-11-23: an empty page "seems spread out ... Sometimes I have
'Add a document' in the middle of the screen, then the paths at the top, and then there's another button. It just needs
to be cleaner"). House rule 8 says an empty screen shows one way in. So with nothing to list, a page shows one sentence
and one button in one place, and the controls that work on a list (the bar, Find, filters, the panel beside it) are not
shown until there is a list. Each function is called by its page when it fills. Text and widgets only."""
from . import design as D


def _state(page, title, body, action, fn, at=1):
    """The page's one-sentence block, made the first time it is needed."""
    w = getattr(page, "none", None)
    if w is None:
        w = page.none = D.EmptyState(title, body, action, fn)
        page.layout().insertWidget(at, w, 1)
    return w


def graphics(page, every):
    """Graphics: with no graphic, no second Add graphics..., no Find and no filter."""
    for w in (page.bar, page.search, page.flt, page.count):
        w.setVisible(bool(every))
    return bool(every)


def deliverables(page, empty):
    """Deliverables: with none (and none named by the customer's documents), the sentence and + Deliverable..."""
    w = _state(page, "No deliverables yet", "What the effort hands back to the customer: its volumes, forms, and files to "
               "fill in or redline.", "+ Deliverable...", lambda: page.edit())
    top = page.layout().itemAt(0).layout()
    for i in range(top.count()):
        x = top.itemAt(i).widget()
        if x is not None:
            x.setVisible(not empty)
    L = page.layout()
    for i in range(1, L.count()):                    # the board or the list (one stack), not the customer's suggestions
        x = L.itemAt(i).widget()
        if x is not None and x is not w and x is not page.sugg:
            x.setVisible(not empty)
    w.setVisible(empty)
    return empty


def matrix(page, empty):
    """Matrix: with nothing shredded, the sentence and Open Shred; no bar of buttons that cannot be used."""
    w = _state(page, "No matrix yet", "The matrix is made from the customer's documents. Shred one first.",
               "Open Shred", lambda: page.host.go("assign"), at=0)
    page.bar.setVisible(not empty)
    page.design_w.parentWidget().setVisible(not empty)
    w.setVisible(empty)
    return empty
