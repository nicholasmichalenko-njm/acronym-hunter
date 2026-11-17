"""Shred: the bar at the selection (4.26.0; Nicholas's recording 2026-11-12 01:15: "having the buttons at the top").
Select one piece or several and a small bar shows beside them: the types as chips (a click puts one on, a second click
takes it off), Combine for several pieces, Split once a split point is set, and Take the suggestion when one waits. The
top bar keeps what is about the whole document. The bar moves with the page and goes when nothing is selected.
4.53.0 (UX decisions 12 and 61): the bar opens in the right margin, level with the first selected piece, in one column:
the suggested type first, then the other types as one compact group, Capture, Ask a question, Combine or Split when they
apply, and Take the suggestion. On Shred the page keeps that margin (GUTTER) to its right, so nothing covers the text;
decided marks stay in the left margin. The drag grip of 4.29.3 is gone: the bar always opens in the margin.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QRectF, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QPushButton, QVBoxLayout

import diag
import shredtypes as ST
from . import design as D

GUTTER = 200                     # the right margin the page keeps on Shred, for the bar
GAP = 6                          # between the page and the bar


def install(page):
    page.sel_bar = None
    page._sel_bar_timer = QTimer(page); page._sel_bar_timer.setSingleShot(True); page._sel_bar_timer.setInterval(80)
    page._sel_bar_timer.timeout.connect(lambda: refresh(page))
    v = page.view
    v.scene().selectionChanged.connect(lambda: later(page))
    for sb in (v.verticalScrollBar(), v.horizontalScrollBar()):
        sb.valueChanged.connect(lambda _v: place(page))
        sb.rangeChanged.connect(lambda _a, _b: place(page))        # a resize or a zoom moves the piece too


def fitted(v):
    """True when the page is at Fit width for the viewport it has now."""
    r = v.scene().itemsBoundingRect().united(QRectF(0, 0, 1, 1))
    w, sb = v.viewport().width(), v.verticalScrollBar().sizeHint().width()
    widths = (w, w + sb, w - sb)                         # fitted before its scroll bar showed, or went
    return r.width() > 1 and any(abs(v.zoom - max(0.3, (x - 24) / (r.right() + 12))) < 0.005 for x in widths)


def gutter(page, on):
    """Keep (on) or give back the right margin the bar opens in. A page that was at Fit width is fitted again to the
    narrower (or wider) viewport. Returns the margin."""
    v = page.view
    want = GUTTER if on else 0
    try:
        if v.viewportMargins().right() == want:
            return want
        was = fitted(v)
        v.setViewportMargins(0, 0, want, 0)
        if was:
            v.fit()
        if not on:
            close(page)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return want


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


def chip(page, t, ty, key, on):
    from . import shredbar as SB
    b = QPushButton(ty.get("name", key).replace("&", "&&")); b.setCheckable(True)
    b.setChecked(on)
    color = ty.get("color") or "#64748B"
    border = f"2px solid {color}" if on else f"1px solid {t['border_strong']}"
    b.setStyleSheet(f"QPushButton{{border:{border};border-left:4px solid {color};border-radius:6px;padding:1px 6px;"
                    f"text-align:left;color:{t['text']};background:{t['accent_soft'] if on else t['surface']};"
                    f"font-weight:{600 if on else 400};}}")
    b.setToolTip(f"{ty.get('name', key)} ({ty.get('short', '')}): " + ("on, click to take it off" if on else "click to put it on"))
    b.clicked.connect(lambda _c=False, k=key: SB.toggle_piece(page, k))
    return b


def build(page, rows):
    from . import shredbar as SB
    from . import typechips as TC
    t = D.tokens()
    f = QFrame(page.view); f.setObjectName("shredSelBar")
    f.setStyleSheet(f"QFrame#shredSelBar{{background:{t['surface']};border:1px solid {t['border_strong']};border-radius:8px}}")
    sh = QGraphicsDropShadowEffect(f); sh.setBlurRadius(18); sh.setOffset(0, 4); sh.setColor(QColor(0, 0, 0, 80))
    f.setGraphicsEffect(sh)
    col = f.col = QVBoxLayout(f); col.setContentsMargins(6, 6, 6, 6); col.setSpacing(4)
    types = ST.load(page.host.config_dir)
    sug = TC.suggested(page, rows[-1]) if len(rows) == 1 else ""
    f.chips, f.lead = {}, None
    if sug and (types.get(sug) or {}).get("shown", True):            # the suggested type first, as the lead button
        ty = types.get(sug) or {}
        f.lead = D.button(ty.get("name", sug).replace("&", "&&"), "primary", lambda _c=False: SB.toggle_piece(page, sug),
                          "Suggested. Enter takes it and goes to the next piece not shredded")
        col.addWidget(f.lead); f.chips[sug] = f.lead
    group = QVBoxLayout(); group.setSpacing(1)                         # the other types, one compact group
    for key in ST.KEYS:
        ty = types.get(key) or {}
        if not ty.get("shown", True) or key in f.chips:
            continue
        b = chip(page, t, ty, key, all(ST.has(it, key) for it in rows))
        group.addWidget(b); f.chips[key] = b
    col.addLayout(group)
    # 4.29.3 (Nicholas 2026-11-13 11:06): Capture and Ask a question sit here with the types; each says where it is kept
    from PySide6.QtWidgets import QMenu
    f.capture = D.button("Capture", "ghost", None, "A contact, an objective, a key point, a graphic need and the effort's own captures. "
                         "Each line says where it is kept.")
    f.capture_menu = QMenu(f.capture); f.capture_menu.setToolTipsVisible(True)
    f.capture_menu.aboutToShow.connect(lambda: TC.fill_capture(page, f.capture_menu)); f.capture.setMenu(f.capture_menu)
    col.addWidget(f.capture)
    f.ask = D.button("Ask a question", "ghost", lambda: TC.ask(page), TC.ASK_TIP)
    col.addWidget(f.ask)
    f.combine = f.split = f.take = None
    if len(rows) > 1:
        f.combine = D.button("Combine", "ghost", page.do_combine, "One piece from the selected ones (J)")
        col.addWidget(f.combine)
    if len(rows) == 1 and page.split_at is not None:
        f.split = D.button("Split here", "ghost", page.do_split, "Split the piece at the red line (S)")
        col.addWidget(f.split)
    if any(TC.suggested(page, it) for it in rows):
        f.take = D.button("Take the suggestion" if len(rows) == 1 else "Take the selected suggestions", "ghost",
                          lambda: page.accept_suggestions(rows=page.selected()), "Each selected piece takes its suggested type and stays (Enter takes it and goes on)")
        col.addWidget(f.take)
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


def first_top(page):
    """The top of the first selected piece, in the viewport, or None."""
    v = page.view
    its = [it for it in page.selected() if it["id"] in v.boxes]
    if not its:
        return None
    return v.mapFromScene(v.boxes[its[0]["id"]].sceneBoundingRect()).boundingRect().top()


def place(page):
    """In the right margin, level with the first selected piece; kept inside the view's height (at the top or bottom
    edge of the margin when the piece is scrolled out of view). Never over the page's text."""
    b = getattr(page, "sel_bar", None)
    if b is None:
        return None
    try:
        top = first_top(page)
        if top is None:
            return close(page)
        v = page.view
        vp = v.viewport().geometry()
        w = max(GUTTER - 2 * GAP, b.sizeHint().width())
        h = b.sizeHint().height()
        b.resize(w, h)
        x = vp.right() + 1 + GAP
        y = max(vp.top(), min(vp.top() + top, vp.bottom() + 1 - h))
        b.move(int(x), int(max(0, y)))
        b.raise_()
        return b.geometry()
    except RuntimeError:                 # the page closed under it
        page.sel_bar = None
        return None
