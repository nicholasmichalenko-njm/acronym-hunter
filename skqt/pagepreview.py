"""The Structure Builder's live preview (3.31.0): the volume's pages drawn from pageplan, as they will run: each part's
page numbers, header, footer and marking; elements with their entries, divider and placeholder pages, the response's
headings with how many requirements each holds, landscape pages turned. A click on a page selects its section; the
selected section's pages are outlined. Drawn by Stationkeeper, close to Word's layout; Make templates gives Word's own."""
from PySide6.QtCore import QRectF, Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

PART_FILL = {"cover": "#ECEDEF", "title": "#ECEDEF", "front": "#F3EEFA", "body": "#FFFFFF", "appendix": "#FBF3EC", "back": "#ECEDEF"}
PART_EDGE = {"cover": "#64748B", "title": "#64748B", "front": "#6B4E9B", "body": "#2E7D5B", "appendix": "#A35A1E", "back": "#64748B"}


class PagesPreview(QWidget):
    page_clicked = Signal(str)

    PW, GAP = 170.0, 14.0                          # a portrait page's width on screen, and the gap between pages

    def __init__(self):
        super().__init__()
        self.pages, self.sel = [], ""
        self.rects = []
        self.setMinimumWidth(int(self.PW + 2 * self.GAP))
        self.setMouseTracking(True)

    def set_pages(self, pages, sel=""):
        self.pages, self.sel = list(pages or []), sel or ""
        self.updateGeometry()
        self._layout()
        self.update()

    def _size(self, p):
        img = p.get("image")
        if img is not None and not img.isNull() and img.height():          # 3.32.0: Word's page, at its own shape
            r = img.width() / img.height()
            return (self.PW, self.PW / r) if r <= 1 else (self.PW * r, self.PW)
        h = self.PW * 11 / 8.5
        return (h, self.PW) if p.get("orient") == "landscape" else (self.PW, h)

    def _layout(self):
        """Pages left to right, wrapping at the widget's width."""
        width = max(self.width(), int(self.PW + 2 * self.GAP))
        x, y, row_h = self.GAP, self.GAP, 0.0
        self.rects = []
        for p in self.pages:
            w, h = self._size(p)
            if x + w + self.GAP > width and x > self.GAP:
                x, y, row_h = self.GAP, y + row_h + self.GAP + 14, 0.0
            self.rects.append(QRectF(x, y, w, h))
            x += w + self.GAP
            row_h = max(row_h, h)
        self._height = int(y + row_h + self.GAP + 14)
        self.setMinimumHeight(self._height)

    def resizeEvent(self, e):
        self._layout()
        super().resizeEvent(e)

    def sizeHint(self):
        return QSize(int(3 * (self.PW + self.GAP) + self.GAP), getattr(self, "_height", 400))

    def page_at(self, pos):
        for r, p in zip(self.rects, self.pages):
            if r.contains(pos):
                return p
        return None

    def mousePressEvent(self, e):
        p = self.page_at(e.position())
        if p is not None and p.get("label"):
            self.page_clicked.emit(p["label"])

    def paintEvent(self, _e):
        if not self.rects or len(self.rects) != len(self.pages):
            self._layout()
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing, True); qp.setRenderHint(QPainter.TextAntialiasing, True)
        tiny = QFont(self.font()); tiny.setPointSizeF(5.5)
        small = QFont(self.font()); small.setPointSizeF(6.5)
        bold = QFont(small); bold.setBold(True)
        h1 = QFont(self.font()); h1.setPointSizeF(8); h1.setBold(True)
        for r, p in zip(self.rects, self.pages):
            if p.get("image") is not None:                # 3.32.0: the exact preview: Word's page as it is
                qp.fillRect(r.translated(1.5, 2), QColor(0, 0, 0, 40))
                qp.drawImage(r, p["image"])
                qp.setPen(QPen(QColor("#B8B3A7"), 1)); qp.drawRect(r)
                if p.get("label") and p["label"] == self.sel:
                    qp.setPen(QPen(QColor("#2F5D8A"), 2.5)); qp.drawRect(r.adjusted(-2, -2, 2, 2))
                qp.setFont(small); qp.setPen(QColor("#5D6672"))
                qp.drawText(QRectF(r.left(), r.bottom() + 1, r.width(), 13), Qt.AlignHCenter | Qt.AlignVCenter, p.get("num") or "")
                continue
            qp.setPen(QPen(QColor("#B8B3A7"), 1))
            qp.fillRect(r.translated(1.5, 2), QColor(0, 0, 0, 40))
            qp.fillRect(r, QColor(PART_FILL.get(p["part"], "#FFFFFF")))
            if p.get("label") and p["label"] == self.sel:
                qp.setPen(QPen(QColor("#2F5D8A"), 2.5)); qp.drawRect(r.adjusted(-2, -2, 2, 2))
            qp.setPen(QPen(QColor(PART_EDGE.get(p["part"], "#2E7D5B")), 1)); qp.drawRect(r)
            m = r.width() * 0.09
            body = r.adjusted(m, m * 1.2, -m, -m * 1.2)
            qp.setFont(tiny); qp.setPen(QColor("#5D6672"))
            hd = p.get("header") or {}
            band = QRectF(body.left(), r.top() + m * 0.35, body.width(), m * 0.6)
            for s, al in (("left", Qt.AlignLeft), ("center", Qt.AlignHCenter), ("right", Qt.AlignRight)):
                if hd.get(s):
                    qp.drawText(band, al | Qt.AlignVCenter, hd[s][:40])
            ft = p.get("footer") or {}
            fband = QRectF(body.left(), r.bottom() - m * 0.95, body.width(), m * 0.6)
            for s, al in (("left", Qt.AlignLeft), ("center", Qt.AlignHCenter), ("right", Qt.AlignRight)):
                if ft.get(s):
                    qp.drawText(fband, al | Qt.AlignVCenter, ft[s][:40])
            if p.get("marking"):
                qp.setPen(QColor("#9A3B2E")); qp.setFont(bold)
                qp.drawText(QRectF(body.left(), fband.top() - m * 0.55, body.width(), m * 0.5), Qt.AlignCenter, p["marking"][:30])
            y = body.top()
            kind = p.get("kind")
            if kind in ("cover", "divider"):
                qp.setFont(h1); qp.setPen(QColor("#1F3A5A"))
                qp.drawText(QRectF(body.left(), body.top() + body.height() * 0.35, body.width(), 40), Qt.AlignHCenter | Qt.TextWordWrap,
                            p.get("title") or "")
            else:
                if kind in ("element",) and p.get("title"):
                    qp.setFont(h1); qp.setPen(QColor("#1F3A5A"))
                    qp.drawText(QRectF(body.left(), y, body.width(), 14), Qt.AlignLeft | Qt.AlignVCenter, p["title"][:34]); y += 16
                for text, how in p.get("lines") or []:
                    if y > body.bottom() - 8:
                        break
                    if how.startswith("h"):
                        lv = int(how[1:] or 1)
                        f = QFont(self.font()); f.setPointSizeF(max(5.5, 8 - 0.5 * (lv - 1))); f.setBold(True)
                        qp.setFont(f); qp.setPen(QColor("#1F3A5A"))
                        qp.drawText(QRectF(body.left() + 4 * (lv - 1), y, body.width(), 12), Qt.AlignLeft | Qt.AlignVCenter, text[:40])
                        y += 13
                        qp.setPen(Qt.NoPen); qp.setBrush(QColor("#E4E1D8"))
                        for k in range(2):
                            qp.drawRoundedRect(QRectF(body.left(), y + k * 5, body.width() * (0.95 - 0.25 * k), 2.5), 1, 1)
                        qp.setBrush(Qt.NoBrush)
                        y += 11
                    elif how == "toc":
                        qp.setFont(tiny); qp.setPen(QColor("#334155"))
                        qp.drawText(QRectF(body.left(), y, body.width() - 8, 9), Qt.AlignLeft | Qt.AlignVCenter, text[:36])
                        qp.drawText(QRectF(body.left(), y, body.width(), 9), Qt.AlignRight | Qt.AlignVCenter, "#")
                        y += 9
                    elif how == "row":
                        qp.setFont(tiny); qp.setPen(QColor("#334155"))
                        qp.drawText(QRectF(body.left(), y, body.width(), 9), Qt.AlignLeft | Qt.AlignVCenter, text[:40])
                        qp.setPen(QPen(QColor("#D8D4C8"), 0.5)); qp.drawLine(body.left(), y + 9, body.right(), y + 9)
                        y += 10
                    elif how == "lib":
                        qp.setPen(QPen(QColor("#2F5D8A"), 0.8, Qt.DashLine)); qp.setBrush(QColor("#EEF3F9"))
                        qp.drawRect(QRectF(body.left(), y, body.width(), 14)); qp.setBrush(Qt.NoBrush)
                        qp.setFont(tiny); qp.setPen(QColor("#2F5D8A"))
                        qp.drawText(QRectF(body.left() + 3, y, body.width() - 6, 14), Qt.AlignLeft | Qt.AlignVCenter, text[:40])
                        y += 17
                    else:
                        qp.setFont(tiny); qp.setPen(QColor("#6B4E9B" if how == "text" else "#5D6672"))
                        qp.drawText(QRectF(body.left(), y, body.width(), 9), Qt.AlignLeft | Qt.AlignVCenter, text[:44])
                        y += 10
                if kind == "more":
                    qp.setPen(Qt.NoPen); qp.setBrush(QColor("#E4E1D8"))
                    yy = max(y, body.top())
                    while yy < body.bottom() - 6:
                        qp.drawRoundedRect(QRectF(body.left(), yy, body.width() * 0.92, 2.5), 1, 1)
                        yy += 6
                    qp.setBrush(Qt.NoBrush)
            qp.setFont(small); qp.setPen(QColor("#5D6672"))
            qp.drawText(QRectF(r.left(), r.bottom() + 1, r.width(), 13), Qt.AlignHCenter | Qt.AlignVCenter,
                        (p.get("num") or "-") + ("  landscape" if p.get("orient") == "landscape" else ""))
        qp.end()


def exact_pages(pdf, sections, width=340):
    """3.32.0: Word's pages from the exact preview's PDF, as images at width pixels, each with the section it is in
    (sections: [label] per page) and its page in the file."""
    import pypdfium2 as pdfium
    from PySide6.QtGui import QImage
    out = []
    doc = pdfium.PdfDocument(pdf)
    try:
        for k in range(len(doc)):
            page = doc[k]
            w, h = page.get_size()
            z = (width if w <= h else width * 11 / 8.5) / max(1.0, w)
            img = page.render(scale=z).to_pil().convert("RGB")
            q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
            out.append({"part": "body", "key": "body", "label": sections[k] if k < len(sections) else "", "kind": "word",
                        "orient": "landscape" if w > h else "portrait", "num": f"page {k + 1}",
                        "header": {}, "footer": {}, "marking": "", "title": "", "lines": [], "image": q})
    finally:
        doc.close()
    return out
