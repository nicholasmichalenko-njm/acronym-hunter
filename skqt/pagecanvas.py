"""Shred's continuous page, drawn as you scroll (4.2.0; claude/stationkeeper-fix-text-decisions-2026-11-10.md, decision 7;
plan step 7). Every page gets its place at once (its size is known without drawing it), so the scroll bar, the boxes
and the page tops are right from the start; only the pages in view and one each side are drawn, and about eight are
kept. Page mode shows one page at a time; the arrows and Page Up/Down move between pages.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QBrush, QColor, QImage, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem

import diag

KEEP = 8


class Canvas:
    def __init__(self, page, pdf, scale, margin, gap):
        self.page, self.pdf, self.scale, self.margin, self.gap = page, pdf, scale, margin, gap
        self.sizes, self.tops, self.pix, self.order = [], [], {}, []
        self.single = False
        self.timer = QTimer(page, singleShot=True, interval=60, timeout=self.ensure)

    def lay_out(self, sc):
        """Placeholders for every page; returns the page tops."""
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(self.pdf)
        y = 0.0
        try:
            for i in range(len(doc)):
                w, h = doc[i].get_size()
                self.sizes.append((w, h))
                r = sc.addRect(QRectF(self.margin, y, w, h), QPen(QColor("#CBD5E1")), QBrush(QColor("#F8FAFC")))
                r.setZValue(-2)
                t = sc.addSimpleText(f"Page {i + 1}"); t.setPos(self.margin - 60, y); t.setBrush(QColor("#64748B"))
                self.tops.append(y)
                y += h + self.gap
        finally:
            doc.close()
        v = self.page.view
        v.verticalScrollBar().valueChanged.connect(lambda _v: self.timer.start())
        return self.tops

    def visible(self):
        v = self.page.view
        r = v.mapToScene(v.viewport().rect()).boundingRect()
        on = [i for i, (y, (_w, h)) in enumerate(zip(self.tops, self.sizes)) if y + h >= r.top() and y <= r.bottom()]
        return on or [0]

    def ensure(self, pages=None):
        """Draw the pages in view (and one each side); keep about eight. Returns the pages drawn now."""
        if not self.sizes or getattr(self.page, "canvas", None) is not self or self.page.pdf != self.pdf:
            return []                                     # a newer document (or none) is open: this one is done
        on = pages if pages is not None else self.visible()
        want = [i for i in range(max(0, min(on) - 1), min(len(self.sizes), max(on) + 2))]
        drawn = []
        need = [i for i in want if i not in self.pix]
        if need:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(self.pdf)
            try:
                for i in need:
                    img = doc[i].render(scale=self.scale).to_pil().convert("RGB")
                    q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
                    it = QGraphicsPixmapItem(QPixmap.fromImage(q))
                    it.setTransformationMode(Qt.SmoothTransformation)
                    it.setScale(1 / self.scale)
                    it.setPos(self.margin, self.tops[i])
                    it.setZValue(-1)
                    self.page.view.scene().addItem(it)
                    self.pix[i] = it
                    drawn.append(i)
            except Exception:  # noqa: BLE001
                diag.swallowed()
            finally:
                doc.close()
        for i in want:
            if i in self.order:
                self.order.remove(i)
            self.order.append(i)
        while len(self.order) > KEEP:
            old = self.order.pop(0)
            it = self.pix.pop(old, None)
            try:
                if it is not None and it.scene() is not None:
                    it.scene().removeItem(it)
            except RuntimeError:                          # the scene was cleared under it
                pass
        return drawn

    def go_page(self, n):
        """Page mode and the page buttons: page n (1-based) at the top of the view."""
        if not self.tops:
            return 0
        n = max(1, min(len(self.tops), n))
        v = self.page.view
        v.verticalScrollBar().setValue(int(v.mapFromScene(0, self.tops[n - 1]).y() + v.verticalScrollBar().value() - 8))
        self.ensure([n - 1])
        return n

    def page_mode(self, on):
        """One page at a time: the page in view fills the view; Page Up and Page Down go a page at a time."""
        self.single = bool(on)
        v = self.page.view
        if on and self.tops:
            n = self.page_now()
            w, h = self.sizes[n - 1]
            v.fitInView(QRectF(self.margin - 8, self.tops[n - 1] - 8, w + 16, h + 16), Qt.KeepAspectRatio)
            self.ensure([n - 1])
        elif hasattr(v, "fit"):
            v.fit()
        return self.single

    def page_now(self):
        v = self.page.view
        mid = v.mapToScene(v.viewport().rect().center()).y()
        n = 1
        for i, y in enumerate(self.tops):
            if y <= mid:
                n = i + 1
        return n

    def step(self, d):
        """Page Up / Page Down: the next or the previous page, whole in Page mode."""
        n = max(1, min(len(self.tops), self.page_now() + d))
        if self.single:
            w, h = self.sizes[n - 1]
            self.page.view.fitInView(QRectF(self.margin - 8, self.tops[n - 1] - 8, w + 16, h + 16), Qt.KeepAspectRatio)
            self.ensure([n - 1])
            return n
        return self.go_page(n)


class EdgeScroll(QObject):
    """A drag that reaches the top or bottom of the view scrolls it (plan step 4): picking words or drawing a box can run
    from a piece on one page to a piece on the next, and J combines them. Installed once on Shred's page view."""
    EDGE = 36
    STEP = 18

    def __init__(self, view):
        super().__init__(view)
        self.view, self.pos, self.dir = view, None, 0
        self.timer = QTimer(self, interval=40, timeout=self.tick)
        view.viewport().installEventFilter(self)

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.MouseMove and ev.buttons() & Qt.LeftButton:
            y, h = ev.position().y(), self.view.viewport().height()
            self.pos = ev.position()
            self.dir = -1 if y < self.EDGE else 1 if y > h - self.EDGE else 0
            if self.dir and not self.timer.isActive():
                self.timer.start()
            elif not self.dir:
                self.timer.stop()
        elif t == QEvent.MouseButtonRelease:
            self.timer.stop(); self.dir = 0
        return False

    def tick(self):
        if not self.dir or self.pos is None:
            self.timer.stop()
            return
        sb = self.view.verticalScrollBar()
        before = sb.value()
        sb.setValue(before + self.dir * self.STEP)
        if sb.value() == before:
            self.timer.stop()
            return
        ev = QMouseEvent(QEvent.MouseMove, QPointF(self.pos), self.view.viewport().mapToGlobal(self.pos.toPoint()).toPointF(),
                         Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        self.view.mouseMoveEvent(ev)              # the drag goes on under the still mouse

