"""Shred: add missed text from a box you dragged (4.26.0; answer 17: "Add missed text only on right-click after a drag
selection"). A drag on the page draws a box and selects the pieces it touches, as before. The box now stays on the page
until the next drag; a right-click inside it offers Add missed text, which reads what is in the box (the PDF's text, else
the reader) and adds it as a piece in its place. No mode to turn on and off. Rules only; nothing leaves the PC."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QMenu

import diag

ADD = "Add missed text (read what is in this box)"


def install(page):
    v = page.view
    v._band, v._band_live, v._band_item = None, None, None
    v.rubberBandChanged.connect(lambda r, a, b: changed(v, r, a, b))
    v.band_menu = lambda e: menu(page, e)


def clear(v):
    it, v._band_item = v._band_item, None
    try:
        if it is not None and it.scene() is not None:
            it.scene().removeItem(it)
    except RuntimeError:                  # the page was drawn again: the scene took it away
        pass


def changed(v, rect, a, b):
    """The view's rubber band moved (a, b: scene points) or ended (an empty rect)."""
    if not rect.isNull():
        if v._band_live is None:
            clear(v); v._band = None
        v._band_live = QRectF(a, b).normalized()
        return None
    r, v._band_live = v._band_live, None
    if r is None or r.width() < 6 or r.height() < 6:
        v._band = None
        return None
    v._band = r
    try:
        pen = QPen(QColor("#B45309")); pen.setWidthF(1.2); pen.setCosmetic(True); pen.setStyle(Qt.DashLine)
        v._band_item = v.scene().addRect(r, pen, QBrush(QColor(245, 158, 11, 28)))
        v._band_item.setZValue(5)
        v._band_item.setAcceptedMouseButtons(Qt.NoButton)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return r


def inside(v, view_pos):
    return v._band is not None and not v.capturing and v._band.contains(v.mapToScene(view_pos))


def menu(page, e, show=True):
    """The right-click inside the box. Returns the menu (None: the click was not in a box)."""
    v = page.view
    if not inside(v, e.pos()):
        return None
    m = QMenu(v)
    m.addAction(ADD, lambda: add(page))
    if show:
        m.exec(e.globalPos())
    return m


def add(page, text=None):
    v = page.view
    r = v._band
    if r is None:
        return None
    if not page.pdf:
        page.host.status("Add missed text works on the page view of a document.")
        return None
    clear(v); v._band = None
    diag.activity("shred_missed_text_from_box")
    return page.capture_area(r, text=text) if text is not None else page.capture_area(r)
