"""Shred: the bar at the selection (4.26.0; Nicholas's recording 2026-11-12 01:15: "having the buttons at the top").
Select one piece or several and a small bar shows just above them, as Word's mini toolbar does: the types as chips (a
click puts one on, a second click takes it off), Combine for several pieces, Split once a split point is set, and Take
the suggestion when one waits. The top bar keeps what is about the whole document. The piece pane on the right is
unchanged; this is the same work, where the eyes are. The bar moves with the page and goes when nothing is selected.
4.29.3: the bar wraps to as many rows as it needs and never runs off the page; drag it by its grip and it stays put.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QPushButton, QWidget

import diag
import shredtypes as ST
from . import design as D


def install(page):
    page.sel_bar = None
    page.sel_bar_pos = None                              # 4.29.3: where the person dragged the bar to, or None
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
    from .adaptive import FlowLayout                     # 4.29.3: the bar wraps inside the page; it never runs off it
    f.inner = QWidget(f); f.inner.move(8, 6)
    h = f.flow = FlowLayout(f.inner, 4)
    f.grip = Grip(page, f); h.addWidget(f.grip)
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
    # 4.29.3 (Nicholas 2026-11-13 11:06): Capture and Ask a question sit here with the types; each says where it is kept
    from PySide6.QtWidgets import QMenu
    f.capture = D.button("Capture", "ghost", None, "A contact, an objective, a key point, a graphic need and the effort's own captures. "
                         "Each line says where it is kept.")
    f.capture_menu = QMenu(f.capture); f.capture_menu.setToolTipsVisible(True)
    f.capture_menu.aboutToShow.connect(lambda: TC.fill_capture(page, f.capture_menu)); f.capture.setMenu(f.capture_menu)
    h.addWidget(f.capture)
    f.ask = D.button("Ask a question", "ghost", lambda: TC.ask(page), TC.ASK_TIP)
    h.addWidget(f.ask)
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


class Grip(QLabel):
    """4.29.3 (Nicholas 2026-11-13 11:06): drag the bar by its grip to put it where it is out of the way; it stays there
    for every selection until it is double-clicked, which sends it back to the selection."""
    def __init__(self, page, bar):
        super().__init__("::")
        self.page, self.bar, self._from = page, bar, None
        t = D.tokens()
        self.setStyleSheet(f"QLabel{{color:{t['faint']};font-weight:700;padding:2px 4px;}}")
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Drag to move the bar; it stays where you put it. Double-click: back to the selection.")

    def mousePressEvent(self, e):
        self._from = e.globalPosition().toPoint() - self.bar.pos()

    def mouseMoveEvent(self, e):
        if self._from is not None:
            move_to(self.page, e.globalPosition().toPoint() - self._from)

    def mouseReleaseEvent(self, _e):
        self._from = None

    def mouseDoubleClickEvent(self, _e):
        self.page.sel_bar_pos = None
        place(self.page)


def move_to(page, pos):
    """Put the bar at a point of the page's view (kept inside it) and keep it there."""
    b = getattr(page, "sel_bar", None)
    if b is None:
        return None
    host = b.parentWidget()
    x = max(0, min(max(0, host.width() - b.width()), int(pos.x())))
    y = max(0, min(max(0, host.height() - b.height()), int(pos.y())))
    page.sel_bar_pos = (x, y)
    b.move(x, y); b.raise_()
    return page.sel_bar_pos


def fit(b):
    """The bar's size: one row when the page is wide enough, else as many rows as it takes, never wider than the page."""
    host, lay = b.parentWidget(), b.flow
    one = lay.sizeHint().width()
    w = max(120, min(one, host.width() - 12 - 16))
    hgt = lay.heightForWidth(w)
    b.inner.setGeometry(8, 6, w, hgt)
    b.resize(w + 16, hgt + 12)
    return b.size()


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
        fit(b)
        if getattr(page, "sel_bar_pos", None):          # 4.29.3: moved by its grip: it stays there
            x, y = page.sel_bar_pos
            b.move(max(0, min(max(0, host.width() - b.width()), x)), max(0, min(max(0, host.height() - b.height()), y)))
            b.raise_()
            return b.geometry()
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
