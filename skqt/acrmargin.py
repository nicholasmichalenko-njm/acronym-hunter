"""The acronym card in the right margin (4.56.0; UX decisions 20 and 61, his answer 9). On the On the page tab the page
keeps a right margin of CARD_W (and a small gap each side), the card opens there level with the first selected find,
kept inside the view's height, following scroll and zoom; it never covers the page. Decided marks stay on the left.
The pattern is Shred's margin (shredselbar: gutter, place). A card taller than the view scrolls inside itself.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QScrollArea, QVBoxLayout, QWidget

import diag
from . import design as D

CARD_W = 320                     # the card's width: one number, so a look can change it (answer 9)
GAP = 8                          # between the page and the card, and the card and the view's edge


def margin():
    return CARD_W + 2 * GAP


def views(op):
    return (op.view, op.text)


def gutter(op, on):
    """Keep (on) or give back the right margin on both of the page's views (the picture and the typed text). A picture
    that was framed to the view is framed again for the narrower (or wider) view. Returns the margin."""
    want = margin() if on else 0
    changed = False
    for v in views(op):
        try:
            if v.viewportMargins().right() != want:
                v.setViewportMargins(0, 0, want, 0)
                changed = True
        except Exception:  # noqa: BLE001
            diag.swallowed()
    op.margin_on = bool(on)
    if changed and getattr(op, "state", "") == "picture":
        try:
            op.frame()
        except Exception:  # noqa: BLE001
            diag.swallowed()
    if changed:
        place(op)
    return want


def host(op):
    """The view the card is a child of: the picture's or the typed text's (not their viewport)."""
    return op.view if op.state == "picture" else op.text


def frame(op):
    """An empty card: (the outer frame, the column its contents go in). The column sits in a scroll area, so a card
    taller than the view scrolls inside itself."""
    t = D.tokens()
    f = QFrame(host(op)); f.setObjectName("selBar")
    f.setStyleSheet(f"QFrame#selBar{{background:{t['surface']};border:1px solid {t['border_strong']};border-radius:8px}}"
                    f"QFrame#selBar QLabel{{color:{t['text']};background:transparent;border:0}}")
    sh = QGraphicsDropShadowEffect(f); sh.setBlurRadius(18); sh.setOffset(0, 4); sh.setColor(QColor(0, 0, 0, 80))
    f.setGraphicsEffect(sh)
    f.setFixedWidth(CARD_W)
    outer = QVBoxLayout(f); outer.setContentsMargins(1, 1, 1, 1); outer.setSpacing(0)
    sa = QScrollArea(f); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.NoFrame)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    sa.setStyleSheet("QScrollArea{background:transparent}")
    inner = QWidget(); inner.setObjectName("cardInner"); inner.setStyleSheet("QWidget#cardInner{background:transparent}")
    v = QVBoxLayout(inner); v.setContentsMargins(12, 10, 12, 10); v.setSpacing(6)
    sa.setWidget(inner)
    outer.addWidget(sa)
    f.scroll, f.inner = sa, inner
    f.keys = {}
    f.kind = None
    return f, v


def room():
    """The width the card's contents have, inside its margins."""
    return CARD_W - 2 - 24 - 4


def wrap(text, widget, width=None):
    """The text broken into lines that fit the card (a push button does not wrap by itself)."""
    fm = QFontMetrics(widget.font())
    width = width or room() - 16
    out, line = [], ""
    for word in str(text).split():
        nxt = (line + " " + word) if line else word
        if line and fm.horizontalAdvance(nxt) > width:
            out.append(line); line = word
        else:
            line = nxt
    if line:
        out.append(line)
    return "\n".join(out)


def first_top(op):
    """The top of the first selected find (or the dragged area, or the selected words) in the view's own coordinates."""
    r = op.sel_rect()
    if r is None:
        return None
    vp = (op.view if op.state == "picture" else op.text).viewport()
    return vp.geometry().top() + r.top()


def place(op):
    """In the right margin, level with the first selected find; kept inside the view's height. Returns the geometry."""
    b = getattr(op, "bar", None)
    if b is None:
        return None
    try:
        h_ = b.parentWidget()
        vp = h_.viewport().geometry()
        top = first_top(op)
        if top is None:
            top = vp.top()
        inner_h = b.inner.sizeHint().height() + 4
        h = max(60, min(inner_h, h_.height() - 2 * GAP))
        b.setFixedHeight(h)
        x = vp.right() + 1 + GAP
        y = max(vp.top(), min(top, h_.height() - GAP - h))
        b.move(int(x), int(max(0, y)))
        b.raise_()
        return b.geometry()
    except RuntimeError:                 # the view closed under it
        op.bar = None
        return None
