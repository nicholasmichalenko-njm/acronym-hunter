"""Compare on the page (3.89.0): the page view and the lines between the page and our response (comparepage uses them).
    CmpView   the new version's page; a click on a change selects it, a click on blank page closes the bar
    Gutter    the lines for the selected change only: solid to each placed sentence it touches, dotted to the section
              suggested for it; an arrow at the edge for one scrolled away
Nothing leaves the PC."""
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget

from . import design as D
from .splitlines import ends


def _rgba(c, a):
    q = QColor(c); q.setAlpha(a)
    return q


class CmpView(QGraphicsView):
    def __init__(self, page):
        super().__init__()
        self.pg = page
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing); self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.boxes = {}                                  # row index -> scene rect

    def mouseReleaseEvent(self, e):
        sp = self.mapToScene(e.position().toPoint())
        hits = [i for i, r in self.boxes.items() if r.adjusted(-3, -3, 3, 3).contains(sp)]
        if hits:
            self.pg.select(min(hits, key=lambda i: self.boxes[i].width() * self.boxes[i].height()))
        else:
            self.pg.bar_host.close()
        super().mouseReleaseEvent(e)

    def view_rect(self, i):
        r = self.boxes.get(i)
        return self.mapFromScene(r).boundingRect() if r is not None else None


class Gutter(QWidget):
    """The lines for the selected change only: solid to each placed sentence it touches, dotted to the suggested section."""

    def __init__(self, page):
        super().__init__()
        self.pg = page
        self.setFixedWidth(44)
        self.drawn = []

    def _y(self, w, local_y):
        return self.mapFromGlobal(w.mapToGlobal(QPoint(0, int(local_y)))).y()

    def compute(self):
        pg = self.pg
        out = []
        i = pg.i
        r = pg.view.view_rect(i) if i is not None else None
        if r is None:
            self.drawn = out
            return out
        lvp, tvp = pg.view.viewport(), pg.tree.viewport()
        ltop, lbot = self._y(lvp, 0), self._y(lvp, lvp.height())
        rtop, rbot = self._y(tvp, 0), self._y(tvp, tvp.height())
        for node, style, tone in pg.targets_of(i):
            rr = pg.tree.visualItemRect(node)
            if not rr.isValid() or rr.height() <= 0:
                continue
            ly, le = ends(self._y(lvp, r.center().y()), ltop + 4, lbot - 4)
            ry, re_ = ends(self._y(tvp, rr.center().y()), rtop + 4, rbot - 4)
            out.append((ly, le, ry, re_, style, tone))
        self.drawn = out
        return out

    def paintEvent(self, _e):
        out = self.compute()
        if not out:
            return
        t = D.tokens()
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        for ly, le, ry, re_, style, tone in out:
            col = QColor(t.get(tone, t["faint"]))
            pen = QPen(col, 1.8 if style == "placed" else 1.2)
            pen.setStyle(Qt.SolidLine if style == "placed" else Qt.DotLine)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            path = QPainterPath(QPointF(0, ly)); path.cubicTo(QPointF(w * 0.5, ly), QPointF(w * 0.5, ry), QPointF(w, ry))
            p.drawPath(path)
            p.setPen(Qt.NoPen); p.setBrush(col)
            for x, y, edge in ((5, ly, le), (w - 5, ry, re_)):
                if edge:
                    d = -1 if edge < 0 else 1
                    p.drawPolygon(QPolygonF([QPointF(x - 4, y), QPointF(x + 4, y), QPointF(x, y + 6 * d)]))
        p.end()
