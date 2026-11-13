"""Shred's progress bar (4.26.0; Nicholas's recording 2026-11-12 08:45: "this bar for compliance review ... should be
connected to the shred process"). The bar that sat on the Dashboard as the Compliance review card: one line under
Shred's document row with the pieces as parts of a whole (requirements placed and not placed, supporting context, the
customer's, ignored, not shredded) and the count in words. Hover it for each part's number. The Dashboard keeps the
card's code and no longer shows it. Rules only; nothing leaves the PC."""
from PySide6.QtWidgets import QHBoxLayout, QWidget

import diag
import shredwords as SW
from . import design as D


def numbers(M):
    """{"total", "shredded", "segments"} from the matrix, or None with nothing extracted."""
    if M is None or not M.items:
        return None
    import compliance as C
    pg = C.progress(M.items)
    keeps = [it for it in M.items if it["decision"] == "Keep"]
    placed = sum(1 for it in keeps if it.get("map"))
    left = pg["total"] - pg["decided"]
    segs = [(placed, "req", "Requirements placed"), (len(keeps) - placed, "warn", "Requirements not placed"),
            (pg["Context"], "ctx", "Supporting context"), (pg.get("Customer", 0), "cust", "The customer's"),
            (pg["Drop"], "border_strong", "Ignored"), (left, "faint", "Not shredded")]
    return {"total": pg["total"], "shredded": pg["decided"], "left": left, "segments": segs}


def install(page):
    """Once: the row under the document row."""
    w = QWidget()
    h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["m"])
    page.progress_bar = D.StackBar(8)
    page.progress_lbl = D.label("", "muted", wrap=False)
    h.addWidget(page.progress_bar, 1); h.addWidget(page.progress_lbl)
    page.progress_row = w
    v = page.top_bar.parent()
    try:
        v.insertWidget(v.indexOf(page.top_bar) + 1, w)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    w.setVisible(False)
    return w


def refresh(page):
    """The numbers now. Shown on Shred with something extracted; hidden otherwise."""
    w = getattr(page, "progress_row", None)
    if w is None:
        return None
    try:
        n = numbers(page.R.M) if page.R is not None else None
        on = n is not None and getattr(page, "focus", None) == "shred" and page.cx is None
        w.setVisible(bool(on))
        if not on:
            return None
        page.progress_bar.set(n["segments"])
        page.progress_lbl.setText(SW.progress(n["shredded"], n["total"]) + ", " + SW.left(n["left"]))
        return n
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None
