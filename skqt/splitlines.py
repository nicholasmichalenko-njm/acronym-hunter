"""The split view and the bar beside the selection (3.83.0, claude/stationkeeper-design-direction-2026-11-08.md): left
is where it comes from, right is where it goes.

SplitView(left, right, links)   two panes with a painted gutter between them. links() gives the selection's pairs,
                                [(rect in left, rect in right)], each in its own pane's coordinates (a scroll area's:
                                its viewport's, as visualItemRect gives them); the gutter draws a
                                line for each pair, for the selection only. A rect scrolled out of its pane is drawn as an
                                arrow at that pane's edge, pointing the way to scroll. Call refresh() when the selection or
                                a pane's scroll changes (watch(scrollbar) connects one).
ends(y, top, bottom)            where a line meets a pane's edge: (y clamped, -1 above / 0 in view / 1 below)
place_bar(bar, target, area)    where a bar goes so it never covers what was clicked: above it, else below it, else
                                beside it; kept inside the area. Sizes and rects as (x, y, w, h).
BarHost                         a bar over a viewport: show_for(rect) places it with place_bar; a click on blank space
                                (outside the bar and the rect) closes it.
Rules only; nothing leaves the PC."""
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QWidget

from . import design as D

GUTTER = 24            # 4.30.7: half as wide (the gap between the page and the card read as empty space)
GAP = 6


def ends(y, top, bottom):
    """(y kept between top and bottom, -1 when it is above, 1 below, 0 in view)."""
    if y < top:
        return top, -1
    if y > bottom:
        return bottom, 1
    return y, 0


def place_bar(bar, target, area, gap=GAP):
    """Top-left (x, y) for a bar of size (w, h) beside target (x, y, w, h), inside area (x, y, w, h); never over target."""
    bw, bh = bar
    tx, ty, tw, th = target
    ax, ay, aw, ah = area
    x = min(max(tx, ax), max(ax, ax + aw - bw))
    if ty - gap - bh >= ay:                              # above
        return x, ty - gap - bh
    if ty + th + gap + bh <= ay + ah:                    # below
        return x, ty + th + gap
    right = tx + tw + gap                                # beside, when the selection fills the height
    if right + bw <= ax + aw:
        return right, min(max(ty, ay), max(ay, ay + ah - bh))
    left = tx - gap - bw
    if left >= ax:
        return left, min(max(ty, ay), max(ay, ay + ah - bh))
    return x, max(ay, ay + ah - bh)                      # no room anywhere: the area's bottom edge


def overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


class Gutter(QWidget):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setFixedWidth(GUTTER)
        self.drawn = []                                  # [(ly, l_edge, ry, r_edge)]: for tests and for the paint

    def _pane(self, w):
        """The widget a pane's rects are in (a scroll area's viewport) and where its top and bottom are in the gutter."""
        from PySide6.QtWidgets import QAbstractScrollArea
        vp = w.viewport() if isinstance(w, QAbstractScrollArea) else w
        top = self.mapFrom(self.view, vp.mapTo(self.view, QPoint(0, 0))).y()
        return vp, top, top + vp.height()

    def compute(self):
        v = self.view
        out = []
        (lvp, ltop, lbot), (rvp, rtop, rbot) = self._pane(v.left), self._pane(v.right)
        for lr, rr in (v.links() if v.links else []):
            if lr is None or rr is None:
                continue
            ly = self.mapFrom(v, lvp.mapTo(v, QPoint(0, lr.center().y()))).y()
            ry = self.mapFrom(v, rvp.mapTo(v, QPoint(0, rr.center().y()))).y()
            ly, le = ends(ly, ltop + 6, lbot - 6)
            ry, re_ = ends(ry, rtop + 6, rbot - 6)
            out.append((ly, le, ry, re_))
        self.drawn = out
        return out

    def paintEvent(self, _e):
        out = self.compute()
        if not out:
            return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        col = QColor(D.tokens().get("accent", "#2F6FDE"))
        w = self.width()
        for ly, le, ry, re_ in out:
            pen = QPen(col, 1.6); pen.setStyle(Qt.DashLine if (le or re_) else Qt.SolidLine)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            path = QPainterPath(QPointF(0, ly))
            path.cubicTo(QPointF(w * 0.5, ly), QPointF(w * 0.5, ry), QPointF(w, ry))
            p.drawPath(path)
            p.setPen(Qt.NoPen); p.setBrush(col)
            for x, y, edge in ((0, ly, le), (w, ry, re_)):
                if edge:
                    d = -1 if edge < 0 else 1
                    cx = 6 if x == 0 else w - 6
                    p.drawPolygon(QPolygonF([QPointF(cx - 5, y), QPointF(cx + 5, y), QPointF(cx, y + 7 * d)]))
                else:
                    p.drawEllipse(QPointF(x, y), 3, 3)
        p.end()


class SplitView(QWidget):
    def __init__(self, left, right, links=None, parent=None):
        super().__init__(parent)
        self.left, self.right, self.links = left, right, links
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        self.gutter = Gutter(self)
        h.addWidget(left, 1); h.addWidget(self.gutter); h.addWidget(right, 1)

    def set_links(self, fn):
        self.links = fn
        self.refresh()

    def refresh(self):
        self.gutter.update()

    def watch(self, scrollbar):
        scrollbar.valueChanged.connect(lambda _v: self.refresh())


class BarHost(QObject):
    """A bar (any widget) over a viewport, opened beside what was clicked and closed by a click on blank space."""

    def __init__(self, bar, viewport):
        super().__init__(viewport)
        self.bar, self.viewport, self.target = bar, viewport, None
        bar.setParent(viewport); bar.hide()
        viewport.installEventFilter(self)

    def show_for(self, rect, width=None, height=None):
        """Opens the bar beside rect. width: the bar's width (a bar that wraps its buttons takes its height from it);
        height: the bar's own measure, when it holds wrapped rich text the layout measures short (3.89.0)."""
        self.target = QRect(rect)
        if width:
            width = max(120, min(int(width), self.viewport.width() - 8))
            self.bar.setFixedWidth(width)
            lay = self.bar.layout()
            h = lay.heightForWidth(width) if lay is not None and lay.hasHeightForWidth() else -1
            self.bar.setFixedHeight(max(h if h > 0 else self.bar.sizeHint().height(), height or 0))
        else:
            self.bar.adjustSize()
        s = self.bar.size() if width else self.bar.sizeHint()
        x, y = place_bar((s.width(), s.height()), (rect.x(), rect.y(), rect.width(), rect.height()),
                         (0, 0, self.viewport.width(), self.viewport.height()))
        self.bar.move(x, y); self.bar.show(); self.bar.raise_()
        return x, y

    def close(self):
        self.target = None
        self.bar.hide()

    def eventFilter(self, obj, e):
        if obj is self.viewport and e.type() == QEvent.MouseButtonPress and self.bar.isVisible():
            pos = e.position().toPoint() if hasattr(e, "position") else e.pos()
            if not self.bar.geometry().contains(pos) and not (self.target is not None and self.target.contains(pos)):
                self.close()
        return False
