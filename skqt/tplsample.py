"""The strip of sample pages on the template builder (4.43.0; ST41, ST42): templatesample's pages drawn small, side by
side, each with its margins, header and footer lines, page number and what the page holds. Drawn by Stationkeeper from
the template's standard, so it changes the moment a pick changes; the label over it says Approximate. Word's own
pictures replace it in a later release."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import design as D

SCALE = 22.0                                   # pixels per inch
GAP, CAP = 18, 22


class SampleStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages = []
        self.setMinimumHeight(int(11 * SCALE) + CAP + 2 * GAP)

    def show_pages(self, pages):
        self.pages = list(pages or [])
        self.updateGeometry(); self.update()
        return len(self.pages)

    def _cols(self):
        w = max(1, self.width() - GAP)
        return max(1, int(w // (8.5 * SCALE + GAP)))

    def _place(self):
        """[(page, x, y)] wrapped to the widget's width, and the height used."""
        out, x, y, row_h = [], GAP, GAP, 0
        for p in self.pages:
            pw, ph = p["w"] * SCALE, p["h"] * SCALE
            if x + pw > self.width() - GAP / 2 and x > GAP:
                x, y, row_h = GAP, y + row_h + CAP + GAP, 0
            out.append((p, x, y))
            x += pw + GAP
            row_h = max(row_h, ph)
        return out, y + row_h + CAP + GAP

    def sizeHint(self):
        return QSize(640, int(self._place()[1]))

    def heightForWidth(self, _w):
        return int(self._place()[1])

    def hasHeightForWidth(self):
        return True

    def resizeEvent(self, e):
        self.setMinimumHeight(int(self._place()[1]))
        super().resizeEvent(e)

    def paintEvent(self, _e):
        t = D.tokens()
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing, True)
        ink, mute, rule = QColor("#1B2433"), QColor("#6B778A"), QColor("#B9C3D1")
        small = QFont(self.font()); small.setPointSizeF(6.5)
        cap = QFont(self.font()); cap.setPointSizeF(8.5)
        for p, x, y in self._place()[0]:
            w, h = p["w"] * SCALE, p["h"] * SCALE
            qp.setPen(QPen(QColor(t["border"]), 1)); qp.setBrush(QColor("#FFFFFF"))
            qp.drawRect(QRectF(x, y, w, h))
            mt, mb, ml, mr = (v * SCALE for v in p["m"])
            box = QRectF(x + ml, y + mt, w - ml - mr, h - mt - mb)
            qp.setBrush(Qt.NoBrush); qp.setPen(QPen(QColor("#C9D6E2"), 1, Qt.DashLine)); qp.drawRect(box)
            qp.setFont(small); qp.setPen(mute)
            fm = qp.fontMetrics()
            for text, al, part in zip(p["header"], (Qt.AlignLeft, Qt.AlignHCenter, Qt.AlignRight), (0.48, 0.3, 0.48)):
                if text:
                    qp.drawText(QRectF(box.left(), y + p["hd"] * SCALE - 4, box.width(), 10), al | Qt.AlignVCenter,
                                fm.elidedText(text, Qt.ElideRight, int(box.width() * part)))
            fy = y + h - p["ft"] * SCALE - 6
            if p["footer"]:
                qp.drawText(QRectF(box.left(), fy, box.width(), 10), Qt.AlignHCenter | Qt.AlignVCenter, p["footer"])
            if p["number"]:
                qp.drawText(QRectF(box.left(), fy, box.width(), 10), Qt.AlignRight | Qt.AlignVCenter, p["number"])
            self._blocks(qp, p["blocks"], box, ink, mute, rule, small)
            qp.setFont(cap); qp.setPen(QColor(t["muted"]))
            qp.drawText(QRectF(x, y + h + 3, w, CAP - 4), Qt.AlignHCenter | Qt.AlignTop, p["label"])
        qp.end()

    def _blocks(self, qp, blocks, box, ink, mute, rule, small):
        y = box.top() + 4
        bold = QFont(small); bold.setBold(True)

        def bars(n, left=0.0, width=1.0):
            nonlocal y
            qp.setPen(Qt.NoPen); qp.setBrush(rule)
            for i in range(n):
                wd = box.width() * width * (0.7 if i == n - 1 and n > 1 else 1.0) - left
                qp.drawRect(QRectF(box.left() + left, y, max(8.0, wd), 2.2)); y += 5.5
            y += 3

        def caption(c):
            nonlocal y
            if c:
                qp.setFont(bold); qp.setPen(ink)
                qp.drawText(QRectF(box.left(), y, box.width(), 9), Qt.AlignHCenter | Qt.AlignVCenter, c["text"] + " Title"); y += 11

        for b in blocks:
            if y > box.bottom() - 12:
                break
            kind = b[0]
            if kind in ("title", "built"):
                qp.setFont(bold); qp.setPen(ink if kind == "title" else mute)
                qp.drawText(QRectF(box.left(), y if kind == "title" else box.center().y() - 12, box.width(), 12), Qt.AlignHCenter | Qt.AlignVCenter, b[1])
                if kind == "built":
                    qp.setFont(small)
                    qp.drawText(QRectF(box.left(), box.center().y(), box.width(), 12), Qt.AlignHCenter | Qt.AlignVCenter, "a page built in Word")
                y += 16
            elif kind == "toc":
                qp.setFont(small); qp.setPen(mute)
                for i, (ind, pg) in enumerate(((0, "1-1"), (8, "1-1"), (8, "1-2"), (0, "2-1"), (8, "2-1"))):
                    qp.drawText(QRectF(box.left() + ind, y, box.width() - ind, 9), Qt.AlignLeft | Qt.AlignVCenter, "Heading " + "." * 60)
                    qp.fillRect(QRectF(box.right() - 18, y, 18, 9), QColor("#FFFFFF"))
                    qp.drawText(QRectF(box.right() - 18, y, 18, 9), Qt.AlignRight | Qt.AlignVCenter, pg); y += 10
            elif kind == "h":
                qp.setFont(bold); qp.setPen(ink)
                qp.drawText(QRectF(box.left(), y, box.width(), 10), Qt.AlignLeft | Qt.AlignVCenter, (b[2] + "  " if b[2] else "") + f"Heading {b[1]}"); y += 12
            elif kind == "text":
                bars(b[1])
            elif kind == "list":
                qp.setFont(small); qp.setPen(ink)
                for lvl, mark in b[1]:
                    qp.drawText(QRectF(box.left() + 6 + 9 * lvl, y - 3, 14, 9), Qt.AlignLeft | Qt.AlignVCenter, mark)
                    qp.setPen(Qt.NoPen); qp.setBrush(rule); qp.drawRect(QRectF(box.left() + 20 + 9 * lvl, y, box.width() * 0.6, 2.2)); qp.setPen(ink); y += 6.5
                y += 3
            elif kind == "table":
                c = b[1]
                if c and c["above"]:
                    caption(c)
                qp.setBrush(Qt.NoBrush); qp.setPen(QPen(rule, 1))
                th = 26
                qp.drawRect(QRectF(box.left(), y, box.width(), th))
                qp.fillRect(QRectF(box.left() + 1, y + 1, box.width() - 2, 7), QColor("#E7EDF5"))
                for k in (1, 2):
                    qp.drawLine(int(box.left() + box.width() * k / 3), int(y), int(box.left() + box.width() * k / 3), int(y + th))
                y += th + 3
                if c and not c["above"]:
                    caption(c)
            elif kind == "figure":
                c = b[1]
                if c and c["above"]:
                    caption(c)
                qp.setBrush(QColor("#F3F5F8")); qp.setPen(QPen(rule, 1))
                fh = min(40.0, max(14.0, box.bottom() - y - 16))
                qp.drawRect(QRectF(box.left() + box.width() * 0.15, y, box.width() * 0.7, fh)); y += fh + 3
                if c and not c["above"]:
                    caption(c)
