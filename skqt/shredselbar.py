"""Shred: the bar at the selection (4.26.0; Nicholas's recording 2026-11-12 01:15: "having the buttons at the top").
Select one piece or several and a small bar shows just above them, as Word's mini toolbar does: the types as chips (a
click puts one on, a second click takes it off), Combine for several pieces, Split once a split point is set, and Take
the suggestion when one waits. The top bar keeps what is about the whole document. The piece pane on the right is
unchanged; this is the same work, where the eyes are. The bar moves with the page and goes when nothing is selected.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QRectF, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QPushButton

import diag
import shredtypes as ST
from . import design as D


def install(page):
    page.sel_bar = None
    page._sel_bar_timer = QTimer(page); page._sel_bar_timer.setSingleShot(True); page._sel_bar_timer.setInterval(80)
    page._sel_bar_timer.timeout.connect(lambda: refresh(page))
    v = page.view
    v.scene().selectionChanged.connect(lambda: later(page))
    for sb in (v.verticalScrollBar(), v.horizontalScrollBar()):
        sb.valueChanged.connect(lambda _v: place(page))


def later(page):
    """Draw the bar again shortly (a drag changes the selection many times a second)."""
    t = getattr(page, "_sel_bar_timer", None)
    if t is not None:
        t.start()


def close(page):
    b, page.sel_bar = getattr(page, "sel_bar", None), None
    if b is not None:
        b.hide(); b.setParent(None); b.deleteLater()
    __import__("skqt.typechips", fromlist=["x"]).pane(page, True)


def wanted(page):
    """The pieces the bar is for: the selection, on Shred, in a document being shredded."""
    if getattr(page, "focus", None) != "shred" or page.R is None or page.cx is not None or not page.file:
        return []
    if getattr(page.view, "capturing", False) or page.view.panning():
        return []
    return page.selected()


def refresh(page):
    """Build the bar for what is selected now (or take it away). Returns the bar or None."""
    from . import typechips as TC
    try:
        close(page)
        rows = wanted(page)
        if not rows:
            return None
        page.sel_bar = build(page, rows)
        page.sel_bar.show()
        if place(page) is not None:
            TC.pane(page, False)                 # 4.29.1: the types show here, not on the pane as well
        return page.sel_bar
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def build(page, rows):
    from . import shredbar as SB
    from . import typechips as TC
    t = D.tokens()
    f = QFrame(page.view.viewport()); f.setObjectName("shredSelBar")
    f.setStyleSheet(f"QFrame#shredSelBar{{background:{t['surface']};border:1px solid {t['border_strong']};border-radius:8px}}")
    sh = QGraphicsDropShadowEffect(f); sh.setBlurRadius(18); sh.setOffset(0, 4); sh.setColor(QColor(0, 0, 0, 80))
    f.setGraphicsEffect(sh)
    h = QHBoxLayout(f); h.setContentsMargins(8, 6, 8, 6); h.setSpacing(4)
    types = ST.load(page.host.config_dir)
    sug = TC.suggested(page, rows[-1]) if len(rows) == 1 else ""
    f.chips = {}
    for key in ST.KEYS:
        ty = types.get(key) or {}
        if not ty.get("shown", True):
            continue
        b = QPushButton(ty.get("name", key).replace("&", "&&")); b.setCheckable(True)
        on = all(ST.has(it, key) for it in rows)
        b.setChecked(on)
        color = ty.get("color") or "#64748B"
        border = f"2px dashed {color}" if key == sug else f"2px solid {color}" if on else f"1px solid {t['border_strong']}"
        b.setStyleSheet(f"QPushButton{{border:{border};border-radius:11px;padding:2px 8px;color:{t['text']};"
                        f"background:{t['accent_soft'] if on else t['surface']};font-weight:{600 if on or key == sug else 400};}}")
        b.setToolTip(f"{ty.get('name', key)} ({ty.get('short', '')}): " + ("on, click to take it off" if on else "click to put it on")
                     + (". Suggested: Enter takes it" if key == sug else ""))
        b.clicked.connect(lambda _c=False, k=key: SB.toggle_piece(page, k))
        h.addWidget(b); f.chips[key] = b
    f.combine = f.split = f.take = None
    if len(rows) > 1:
        f.combine = D.button("Combine", "ghost", page.do_combine, "One piece from the selected ones (J)")
        h.addWidget(f.combine)
    if len(rows) == 1 and page.split_at is not None:
        f.split = D.button("Split here", "ghost", page.do_split, "Split the piece at the red line (S)")
        h.addWidget(f.split)
    if any(TC.suggested(page, it) for it in rows):
        f.take = D.button("Take the suggestion" if len(rows) == 1 else "Take the selected suggestions", "ghost",
                          lambda: page.accept_suggestions(rows=page.selected()), "Each selected piece takes its suggested type (Enter)")
        h.addWidget(f.take)
    return f


def sel_rect(page):
    """The selected pieces' rectangle in the view's viewport, or None."""
    v = page.view
    boxes = [v.boxes[it["id"]] for it in page.selected() if it["id"] in v.boxes]
    if not boxes:
        return None
    r = QRectF()
    for b in boxes:
        r = r.united(b.sceneBoundingRect())
    return v.mapFromScene(r).boundingRect()


def place(page):
    """Just above the selection; under it when there is no room above; kept inside the page's view."""
    b = getattr(page, "sel_bar", None)
    if b is None:
        return None
    try:
        r = sel_rect(page)
        if r is None:
            return close(page)
        host = b.parentWidget()
        b.adjustSize()
        W, H, w, h, gap = host.width(), host.height(), b.width(), b.height(), 6
        x = max(0, min(max(0, W - w), r.left()))
        top = max(r.top(), 0)
        y = top - gap - h if top - gap - h >= 0 else min(max(0, H - h), max(r.bottom(), 0) + gap)
        b.move(int(x), int(y))
        b.raise_()
        return b.geometry()
    except RuntimeError:                 # the page closed under it
        page.sel_bar = None
        return None
