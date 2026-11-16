"""The strip of sample pages on the template builder (4.43.0; ST41, ST42): templatesample's pages drawn small, side by
side, each with its margins, header and footer lines, page number and what the page holds. Drawn by Stationkeeper from
the template's standard, so it changes the moment a pick changes; the label over it says Approximate. Word's own
pictures take its place when asked (4.44.0).

4.45.0 (ST45): every part drawn is also a region that knows which of the builder's picks made it (WHERE). Pointing at a
part outlines it and says so (pointed); a click asks for that pick's menu (picked); a pick lit from outside (light)
outlines every part it made. Word's pictures are one region a page: the app does not know where Word put each part."""
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import design as D

SCALE = 22.0                                   # pixels per inch
GAP, CAP = 18, 22
# part -> (the builder's pick that made it, "" when it comes from the Global Standards; the part's name)
WHERE = {"paper": ("layout", "Paper size"), "margin": ("layout", "Margins"), "header": ("", "Header"), "footer": ("", "Footer"),
         "number": ("numbering", "Page number"), "hnum": ("numbering", "Heading number"), "heading": ("style_sets", "Heading"),
         "text": ("style_sets", "Body text"), "list": ("", "List"), "caption": ("numbering", "Caption number"),
         "table": ("style_sets", "Table"), "figure": ("style_sets", "Figure"), "title": ("style_sets", "Title"),
         "toc": ("", "Table of Contents"), "built": ("starts", "Starting page"), "word": ("", "Word's page")}


class SampleStrip(QWidget):
    pointed = Signal(str, str)                  # the pick ("" for none), the part's key ("" when nothing is under the pointer)
    picked = Signal(str)                        # a click on a part a pick made

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages = []
        self.exact = False
        self.regions = []                       # [(QRectF, part)] as last painted, the page first, then what is on it
        self.at = None                          # the region under the pointer
        self.lit = ""                           # a pick whose parts are outlined
        self.setMouseTracking(True)
        self.setMinimumHeight(int(11 * SCALE) + CAP + 2 * GAP)

    def show_pages(self, pages):
        self.pages = list(pages or [])
        self.exact = False
        self.setMinimumHeight(int(self._place()[1]))
        self.updateGeometry(); self.update()
        return len(self.pages)

    def show_pictures(self, paths):
        """4.44.0: Word's own pages, as pictures. Each keeps its shape; the short side is a Letter page's width."""
        from PySide6.QtGui import QPixmap
        self.pages = []
        for i, p in enumerate(paths or []):
            pm = QPixmap(p)
            if pm.isNull():
                continue
            short = float(min(pm.width(), pm.height())) or 1.0
            self.pages.append({"key": f"page{i + 1}", "label": f"Page {i + 1}", "w": pm.width() / short * 8.5,
                               "h": pm.height() / short * 8.5, "pix": pm})
        self.exact = bool(self.pages)
        self.setMinimumHeight(int(self._place()[1]))
        self.updateGeometry(); self.update()
        return len(self.pages)

    # ------------------------------------------------------------ 4.45.0: which pick made it
    def region_at(self, pos):
        """(rect, part) of the smallest region under a point, or None."""
        hit = [r for r in self.regions if r[0].contains(pos)]
        return min(hit, key=lambda r: r[0].width() * r[0].height()) if hit else None

    def point(self, pos):
        """Moves the pointer to pos (a QPointF, or None for away). Returns (pick, part) or None."""
        new = self.region_at(pos) if pos is not None else None
        if (new and new[1], new and new[0]) != (self.at and self.at[1], self.at and self.at[0]):
            self.at = new
            self.pointed.emit(WHERE[new[1]][0] if new else "", new[1] if new else "")
            self.update()
        return (WHERE[new[1]][0], new[1]) if new else None

    def light(self, pick):
        """Outlines every part the pick made; '' for none. Returns how many parts that is."""
        self.lit = pick or ""
        self.update()
        return sum(1 for _r, part in self.regions if self.lit and WHERE[part][0] == self.lit)

    def mouseMoveEvent(self, e):
        self.point(e.position())

    def leaveEvent(self, _e):
        self.point(None)

    def mouseReleaseEvent(self, e):
        hit = self.region_at(e.position())
        if e.button() == Qt.LeftButton and hit and WHERE[hit[1]][0]:
            self.picked.emit(WHERE[hit[1]][0])

    def _reg(self, rect, part):
        self.regions.append((QRectF(rect), part))

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
        self.regions = []
        for p, x, y in self._place()[0]:
            w, h = p["w"] * SCALE, p["h"] * SCALE
            qp.setPen(QPen(QColor(t["border"]), 1)); qp.setBrush(QColor("#FFFFFF"))
            qp.drawRect(QRectF(x, y, w, h))
            if p.get("pix") is not None:                      # Word's page, as it is
                self._reg(QRectF(x, y, w, h), "word")
                qp.setRenderHint(QPainter.SmoothPixmapTransform, True)
                qp.drawPixmap(QRectF(x + 1, y + 1, w - 2, h - 2), p["pix"], QRectF(p["pix"].rect()))
                qp.setFont(cap); qp.setPen(QColor(t["muted"]))
                qp.drawText(QRectF(x, y + h + 3, w, CAP - 4), Qt.AlignHCenter | Qt.AlignTop, p["label"])
                continue
            mt, mb, ml, mr = (v * SCALE for v in p["m"])
            box = QRectF(x + ml, y + mt, w - ml - mr, h - mt - mb)
            self._reg(QRectF(x, y, w, h), "paper")
            for r in (QRectF(x, y, w, mt), QRectF(x, y + h - mb, w, mb), QRectF(x, y + mt, ml, h - mt - mb), QRectF(x + w - mr, y + mt, mr, h - mt - mb)):
                self._reg(r, "margin")
            if any(p["header"]):
                self._reg(QRectF(box.left(), y + p["hd"] * SCALE - 4, box.width(), 10), "header")
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
                self._reg(QRectF(box.left() + box.width() * 0.2, fy, box.width() * 0.6, 10), "footer")
            if p["number"]:
                qp.drawText(QRectF(box.left(), fy, box.width(), 10), Qt.AlignRight | Qt.AlignVCenter, p["number"])
                self._reg(QRectF(box.right() - 24, fy, 24, 10), "number")
            self._blocks(qp, p["blocks"], box, ink, mute, rule, small)
            qp.setFont(cap); qp.setPen(QColor(t["muted"]))
            qp.drawText(QRectF(x, y + h + 3, w, CAP - 4), Qt.AlignHCenter | Qt.AlignTop, p["label"])
        acc = QColor(t.get("accent") or "#1F5FBF")
        qp.setBrush(Qt.NoBrush)
        if self.lit:
            qp.setPen(QPen(acc, 1.2))
            for r, part in self.regions:
                if WHERE[part][0] == self.lit and part != "paper":
                    qp.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
        if self.at is not None:
            wash = QColor(acc); wash.setAlpha(34)
            qp.setPen(QPen(acc, 2)); qp.setBrush(wash)
            for r, part in self.regions:
                if part == self.at[1] and (part == "margin" and self._same_page(r, self.at[0]) or r == self.at[0]):
                    qp.drawRect(r.adjusted(1, 1, -1, -1))
        qp.end()

    def _same_page(self, a, b):
        """Whether two regions sit on one page: the four margin bands light together."""
        page = lambda r: next((pr for pr, part in self.regions if part in ("paper", "word") and pr.contains(r.center())), None)
        return page(a) is not None and page(a) == page(b)

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
                qp.drawText(QRectF(box.left(), y, box.width(), 9), Qt.AlignHCenter | Qt.AlignVCenter, c["text"] + " Title")
                self._reg(QRectF(box.left(), y, box.width(), 9), "caption"); y += 11

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
                    self._reg(box, "built")
                else:
                    self._reg(QRectF(box.left(), y, box.width(), 12), "title")
                y += 16
            elif kind == "toc":
                qp.setFont(small); qp.setPen(mute)
                self._reg(QRectF(box.left(), y, box.width(), 50), "toc")
                for i, (ind, pg) in enumerate(((0, "1-1"), (8, "1-1"), (8, "1-2"), (0, "2-1"), (8, "2-1"))):
                    qp.drawText(QRectF(box.left() + ind, y, box.width() - ind, 9), Qt.AlignLeft | Qt.AlignVCenter, "Heading " + "." * 60)
                    qp.fillRect(QRectF(box.right() - 18, y, 18, 9), QColor("#FFFFFF"))
                    qp.drawText(QRectF(box.right() - 18, y, 18, 9), Qt.AlignRight | Qt.AlignVCenter, pg); y += 10
            elif kind == "h":
                qp.setFont(bold); qp.setPen(ink)
                qp.drawText(QRectF(box.left(), y, box.width(), 10), Qt.AlignLeft | Qt.AlignVCenter, (b[2] + "  " if b[2] else "") + f"Heading {b[1]}")
                nw = qp.fontMetrics().horizontalAdvance(b[2] + " ") if b[2] else 0
                self._reg(QRectF(box.left(), y, box.width(), 10), "heading")
                if nw:
                    self._reg(QRectF(box.left(), y, nw, 10), "hnum")
                y += 12
            elif kind == "text":
                y0 = y; bars(b[1]); self._reg(QRectF(box.left(), y0 - 2, box.width(), y - y0 - 1), "text")
            elif kind == "list":
                qp.setFont(small); qp.setPen(ink)
                self._reg(QRectF(box.left(), y - 3, box.width(), 6.5 * len(b[1]) + 3), "list")
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
                self._reg(QRectF(box.left(), y, box.width(), th), "table")
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
                qp.drawRect(QRectF(box.left() + box.width() * 0.15, y, box.width() * 0.7, fh))
                self._reg(QRectF(box.left() + box.width() * 0.15, y, box.width() * 0.7, fh), "figure"); y += fh + 3
                if c and not c["above"]:
                    caption(c)
