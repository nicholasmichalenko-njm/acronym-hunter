"""Where a term was found, shown (3.50.0; brings back the classic window's preview, retired in 3.14.0).

For each place a term was found:
  a picture (an image or diagram inside a Word, PowerPoint or Excel file, an image file, or a PDF page) is drawn
  whole with every reading boxed: the term in yellow (the selected find thicker, filled), other readings in green,
  low-confidence readings in red, and on a PDF page the typed matches in orange. Zoom with the wheel or + and -,
  drag to move, Fit to see it all, Enlarge for a big window.
  typed text (Word, PowerPoint, Excel) shows the passage with every match highlighted.
Find < and > step through every find of the term, across all its places; Previous place and Next place jump between
files and pages. Pictures are read off the window's thread and kept for the session, so going back is instant; 3.80.0:
the scan's readings of each picture are kept with the effort (picreadings), so the preview draws them without reading
again, after a restart too, and the next term's first picture is drawn in the background (prefetch).
Files are only read. Rules and the trained readers only (No AI); nothing leaves the PC."""
import html
import os
import re

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPen, QPixmap
from PySide6.QtWidgets import (QDialog, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout,
                               QStackedWidget, QTextBrowser, QVBoxLayout, QWidget)

import diag
from . import design as D
from .whereview import docx_snippet, parse_loc

PENS = {"sel": ("#F59E0B", 4), "find": ("#FACC15", 3), "line": ("#22C55E", 1), "low": ("#EF4444", 1), "typed": ("#F97316", 2),
        "pick": ("#3B82F6", 3), "area": ("#3B82F6", 2), "inarea": ("#60A5FA", 2)}
LEGEND = ("Yellow: the term (the one selected is filled). Green: the scan's other readings. Orange: typed text on a PDF page. "
          "Click a box to see what the scan read there. Drag to draw a box around text (Read this area again reads only "
          "that part); right-drag, or hold Space and drag, to move the picture.")
_CACHE = {}               # (path, source label) -> (QImage, lines, typed hits); the session's pictures
_SOURCES = {}             # path -> [(label, loader)]
_ALIVE = []               # reading jobs until they finish (never dropped while running)


def _fold(t):
    import app_gui as A
    return A.fold(str(t or "")).casefold()


class PicView(QGraphicsView):
    """A picture with boxes: wheel to zoom; 3.80.0: a plain drag draws a box (on_area), a right-button drag or Space
    held while dragging moves the picture."""
    def __init__(self):
        super().__init__()
        self.scene_ = QGraphicsScene(self); self.setScene(self.scene_)
        self.setDragMode(QGraphicsView.NoDrag)
        self._pan = None; self._space = False; self._area0 = None; self._area_item = None
        self.area = None
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHints(self.renderHints())
        self.setBackgroundBrush(QBrush(QColor("#3A3F47")))
        self.pix = None
        self.boxes = []

    def set_picture(self, qimg, boxes):
        self.scene_.clear(); self._mark = None; self._area_item = None; self.area = None; self._marks = []
        self.pix = QGraphicsPixmapItem(QPixmap.fromImage(qimg)); self.pix.setTransformationMode(Qt.SmoothTransformation)
        self.scene_.addItem(self.pix)
        self.scene_.setSceneRect(QRectF(0, 0, qimg.width(), qimg.height()))
        self._room()
        self.boxes = []
        for (x0, y0, x1, y1), kind in boxes:
            col, wd = PENS[kind]
            it = QGraphicsRectItem(QRectF(x0 - 2, y0 - 2, (x1 - x0) + 4, (y1 - y0) + 4))
            pen = QPen(QColor(col)); pen.setWidthF(wd); pen.setCosmetic(True); it.setPen(pen)
            if kind == "sel":
                c = QColor(col); c.setAlpha(60); it.setBrush(QBrush(c))
            it.setZValue(3 if kind in ("sel", "find", "typed") else 2)
            self.scene_.addItem(it)
            self.boxes.append(((x0, y0, x1, y1), kind))

    on_click = None                      # 3.61.0: called with a scene point when the picture is clicked (not dragged)
    on_area = None                       # 3.80.0: called with (x0, y0, x1, y1) in the picture's pixels when a box is drawn

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._space = True; self.viewport().setCursor(Qt.OpenHandCursor); return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._space = False; self.viewport().unsetCursor(); return
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e):
        self._press = e.position().toPoint()
        if e.button() == Qt.RightButton or e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self._space):
            self._pan = e.position().toPoint(); self.viewport().setCursor(Qt.ClosedHandCursor)
            e.accept(); return
        if e.button() == Qt.LeftButton and self.pix is not None:
            self._area0 = self.mapToScene(self._press)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            p = e.position().toPoint(); d = p - self._pan; self._pan = p
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            e.accept(); return
        if self._area0 is not None and (e.position().toPoint() - self._press).manhattanLength() >= 5:
            self.draw_area(self._area0, self.mapToScene(e.position().toPoint()))
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._pan is not None:
            self._pan = None; self.viewport().unsetCursor() if not self._space else self.viewport().setCursor(Qt.OpenHandCursor)
            e.accept(); return
        super().mouseReleaseEvent(e)
        p0 = getattr(self, "_press", None)
        a0, self._area0 = self._area0, None
        if p0 is None:
            return
        if (e.position().toPoint() - p0).manhattanLength() < 5:
            if self.on_click is not None:
                self.on_click(self.mapToScene(p0))
        elif a0 is not None:
            box = self.draw_area(a0, self.mapToScene(e.position().toPoint()))
            self.drop_area()                     # 3.93.0: the drag box is gone when you let go; what it held is selected
            if box and self.on_area is not None:
                self.on_area(box)

    def drop_area(self):
        """The dashed drag box off the picture (its area stays, for reading that part again)."""
        if self._area_item is not None and self._area_item.scene() is self.scene_:
            self.scene_.removeItem(self._area_item)
        self._area_item = None

    def draw_area(self, a, b):
        """The box between two scene points, kept inside the picture; drawn dashed. Returns (x0, y0, x1, y1) or None."""
        if self.pix is None:
            return None
        r = QRectF(0, 0, self.pix.pixmap().width(), self.pix.pixmap().height())
        x0, x1 = sorted((max(r.left(), min(r.right(), a.x())), max(r.left(), min(r.right(), b.x()))))
        y0, y1 = sorted((max(r.top(), min(r.bottom(), a.y())), max(r.top(), min(r.bottom(), b.y()))))
        if x1 - x0 < 3 or y1 - y0 < 3:
            return None
        if self._area_item is not None and self._area_item.scene() is self.scene_:
            self.scene_.removeItem(self._area_item)
        col, wd = PENS["area"]
        it = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
        pen = QPen(QColor(col)); pen.setWidthF(wd); pen.setCosmetic(True); pen.setStyle(Qt.DashLine); it.setPen(pen); it.setZValue(5)
        c = QColor(col); c.setAlpha(30); it.setBrush(QBrush(c))
        self.scene_.addItem(it)
        self._area_item = it
        self.area = (x0, y0, x1, y1)
        return self.area

    def mark_many(self, boxes, kind="inarea"):
        """3.80.0: every reading inside the drawn box, highlighted at once."""
        for it in getattr(self, "_marks", []):
            if it.scene() is self.scene_:
                self.scene_.removeItem(it)
        self._marks = []
        col, wd = PENS[kind]
        for x0, y0, x1, y1 in boxes:
            it = QGraphicsRectItem(QRectF(x0 - 2, y0 - 2, (x1 - x0) + 4, (y1 - y0) + 4))
            pen = QPen(QColor(col)); pen.setWidthF(wd); pen.setCosmetic(True); it.setPen(pen); it.setZValue(4)
            self.scene_.addItem(it); self._marks.append(it)
        return len(self._marks)

    def mark(self, box, kind="pick"):
        """One extra box (a clicked reading) without moving the view."""
        old = getattr(self, "_mark", None)
        if old is not None and old.scene() is self.scene_:
            self.scene_.removeItem(old)
        col, wd = PENS[kind]
        x0, y0, x1, y1 = box
        it = QGraphicsRectItem(QRectF(x0 - 3, y0 - 3, (x1 - x0) + 6, (y1 - y0) + 6))
        pen = QPen(QColor(col)); pen.setWidthF(wd); pen.setCosmetic(True); it.setPen(pen); it.setZValue(4)
        self.scene_.addItem(it)
        self._mark = it
        return it

    def box_at(self, pt):
        """The smallest box under a scene point, or None."""
        hit = [b for b, _k in self.boxes if b[0] - 2 <= pt.x() <= b[2] + 2 and b[1] - 2 <= pt.y() <= b[3] + 2]
        return min(hit, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if hit else None

    def fit(self):
        if self.pix is not None:
            self.fitInView(self.scene_.sceneRect(), Qt.KeepAspectRatio)
            self._room()

    ROOM, MOST = 0.5, 16.0               # 3.71.0: half a view past each edge; zoom from half the fitted size to 16 times

    def _room(self):
        """Room past the picture's edges at every zoom, so it can be dragged anywhere, zoomed in or out."""
        if self.pix is None:
            return
        s = max(1e-6, self.transform().m11())
        w = self.viewport().width() / s * self.ROOM
        h = self.viewport().height() / s * self.ROOM
        self.setSceneRect(self.scene_.sceneRect().adjusted(-w, -h, w, h))

    def _fit_scale(self):
        r = self.scene_.sceneRect()
        return min(self.viewport().width() / max(1.0, r.width()), self.viewport().height() / max(1.0, r.height()))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._room()

    def focus(self, box, context=6.0):
        """Center on a box with the lines around it."""
        if self.pix is None or not box:
            return self.fit()
        x0, y0, x1, y1 = box
        r = self.scene_.sceneRect()
        w = min(r.width(), max(900.0, (x1 - x0) * context))
        h = w * max(1, self.viewport().height()) / max(1, self.viewport().width())
        h = max(h, (y1 - y0) * 4)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if not r.contains(cx, cy):
            return self.fit()
        # 3.61.0: room past the picture's edges, so a find near an edge sits in the middle of the view too
        self.fitInView(QRectF(cx - w / 2, cy - h / 2, w, h), Qt.KeepAspectRatio)
        self._room()
        self.centerOn(cx, cy)
        self.focused = (cx, cy)

    def zoom(self, f):
        s = self.transform().m11()
        if self.pix is not None:
            f = max(self._fit_scale() * 0.5 / s, min(self.MOST / s, f))
        if abs(f - 1.0) > 1e-3:
            self.scale(f, f)
        self._room()

    def wheelEvent(self, e):
        d = e.angleDelta()
        if abs(d.x()) > abs(d.y()):                  # 3.71.0: a mouse's side wheel moves the picture left and right
            sb = self.horizontalScrollBar(); sb.setValue(sb.value() - d.x())
        elif d.y():                                  # up and down zoom; no movement, no zoom
            self.zoom(1.25 if d.y() > 0 else 0.8)
        e.accept()                                   # 3.71.0: the panel around the preview never scrolls from here


class PreviewText(QTextBrowser):
    """3.71.0: a passage that scrolls itself and never hands the wheel to the panel around it."""
    def wheelEvent(self, e):
        super().wheelEvent(e)
        e.accept()

    def mouseDoubleClickEvent(self, e):
        self.zoom(1.6)


def _qimage(pil):
    pil = pil.convert("RGB")
    return QImage(pil.tobytes("raw", "RGB"), pil.width, pil.height, pil.width * 3, QImage.Format_RGB888).copy()


def pdf_hits(path, loc, img_h, term):
    """Typed matches of the term on a PDF page, in picture pixels (PDFium's text search)."""
    if not path.lower().endswith(".pdf") or "(p." not in loc or not term:
        return []
    import pypdfium2 as pdfium
    n = int(loc.rsplit("(p.", 1)[1].split(")")[0].split(",")[0])
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[n - 1]
        h_pt = page.get_height()
        s = img_h / h_pt
        tp = page.get_textpage()
        out = []
        for case, whole in ((True, True), (False, False)):
            srch = tp.search(term, match_case=case, match_whole_word=whole)
            occ = srch.get_next()
            while occ:
                idx, cnt = occ
                for r in range(tp.count_rects(idx, cnt)):
                    l, b, rr, t = tp.get_rect(r)
                    out.append((l * s, (h_pt - t) * s, rr * s, (h_pt - b) * s))
                occ = srch.get_next()
            if out:
                break
        return out
    finally:
        doc.close()


def read_place(path, label, loader, loc, term):
    """(QImage, OCR lines, typed hits, note) for one picture: a PDF page with typed matches skips the reader. When the
    reader cannot run, the picture still shows, with a note."""
    img = loader()
    hits = pdf_hits(path, loc, img.height, term)
    lines, note = [], ""
    if not hits:
        try:                                    # 3.61.0: the scan's own readings and boxes (the same reader and passes)
            import app_gui as A
            import picreadings as PR
            key = PR.key_of(img)
            kept = PR.get(key)                  # 3.80.0: kept with the effort's scan: drawn, not read again
            if kept is None:
                kept = A.scan_readings(A._pil_png(img))
                PR.put(key, kept)
                PR.flush()
            lines = [(b, t, c) for b, t, c, _how in kept]
        except Exception as e:  # noqa: BLE001  the picture is still worth seeing
            diag.swallowed()
            note = f"The picture is shown, but the reader could not run here ({type(e).__name__}), so nothing is boxed."
    return _qimage(img), lines, hits, note


def sources(path):
    if path not in _SOURCES:
        import pictures as PIC
        _SOURCES[path] = PIC.list_sources(path)
    return _SOURCES[path]


def typed_html(path, loc, term, para=None):
    """The passage a typed find is in, every match highlighted; None when the term is not in the file's typed text."""
    if path.lower().endswith(".docx"):
        sn = docx_snippet(path, para, term)
        if sn:
            return sn
    import app_gui as A
    chunks = A.typed_chunks(path)
    where = loc.split(" (", 1)[1].rstrip(")") if " (" in loc else ""
    ft = _fold(term)
    pick = [c for c in chunks if where and where.split(",")[0] in str(c[0])] or list(chunks)
    for _lbl, text in pick:
        k = _fold(text).find(ft)
        if k >= 0:
            a, b = max(0, k - 400), min(len(text), k + len(term) + 400)
            t = D.tokens()
            seg = html.escape(text[a:b])
            seg = re.sub(re.escape(html.escape(text[k:k + len(term)])),
                         lambda m: f"<span style='background:{t['warn_soft']};outline:2px solid {t['warn']};font-weight:700'>{m.group(0)}</span>",
                         seg, flags=re.I)
            return f"<p style='color:{t['muted']}'>{html.escape(str(_lbl))}</p><p>{'...' if a else ''}{seg}{'...' if b < len(text) else ''}</p>"
    return None


def prefetch(term, locs, path_of):
    """3.80.0: read the first picture place of a term in the background, so its preview opens at once. Returns the
    worker, or None when there is nothing to read (typed text, already kept, or a file not on this PC)."""
    for loc in list(locs)[:3]:
        try:
            name, _page, _para = parse_loc(loc)
            path = path_of(name)
            if not path or not os.path.isfile(path):
                continue
            import pictures as PIC
            srcs = sources(path)
            idx = PIC.match_source([lbl for lbl, _ld in srcs], loc)
            if idx is None:
                continue
            label, loader = srcs[idx]
            key = (path, label)
            if key in _CACHE or any(getattr(w, "_key", None) == key for w in _ALIVE):
                return None
            from .progress import JobWorker
            w = JobWorker(lambda _p, _s, k=key, ld=loader, lc=loc: read_place(k[0], k[1], ld, lc, term))
            w._key = key

            def done(res, _key=key):
                if isinstance(res, tuple):
                    _CACHE[_key] = res
                    if len(_CACHE) > 40:
                        _CACHE.pop(next(iter(_CACHE)))

            def gone(w=w):
                w.wait(2000)
                if w in _ALIVE:
                    _ALIVE.remove(w)
            w.done.connect(done); w.finished.connect(gone)
            _ALIVE.append(w)
            w.start()
            return w
        except Exception:  # noqa: BLE001  a prefetch never stops the card
            diag.swallowed()
    return None


class FoundView(QWidget):
    def __init__(self, term, locs, path_of, big=False, on_meaning=None, on_find_text=None, on_add_term=None):
        super().__init__()
        self.term, self.locs, self.path_of, self.big = term, list(locs), path_of, big
        self.on_meaning, self.on_find_text = on_meaning, on_find_text       # 3.61.0
        self.on_add_term = on_add_term                                      # 3.80.0: a term the scan missed
        self.page_k = None                       # 3.61.0: a page of the file shown by Page < and > (None: the place's own)
        self.lines = []
        self.k, self.find_k, self.finds, self.state = 0, 0, [], "none"
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(4)
        nav = QHBoxLayout(); v.addLayout(nav)
        self.where = D.label("", "muted"); nav.addWidget(self.where, 1)
        self.b_prev = D.button("Previous place", "ghost", lambda: self.go(-1)); nav.addWidget(self.b_prev)
        self.b_next = D.button("Next place", "ghost", lambda: self.go(1)); nav.addWidget(self.b_next)
        tools = QHBoxLayout(); v.addLayout(tools)
        self.b_fprev = D.button("Find <", None, lambda: self.step(-1), "The previous find of the term (across every place)")
        self.b_fnext = D.button("Find >", None, lambda: self.step(1), "The next find of the term (across every place)")
        self.find_lab = D.label("", "muted", wrap=False)
        tools.addWidget(self.b_fprev); tools.addWidget(self.b_fnext); tools.addWidget(self.find_lab, 1)
        self.b_out = D.button("-", "ghost", lambda: self.view.zoom(0.8)); self.b_in = D.button("+", "ghost", lambda: self.view.zoom(1.25))
        self.b_fit = D.button("Fit", "ghost", lambda: self.view.fit())
        for b in (self.b_out, self.b_in, self.b_fit):
            tools.addWidget(b)
        self.b_pprev = D.button("Page <", "ghost", lambda: self.page_step(-1), "The previous page or picture of this file")
        self.b_pnext = D.button("Page >", "ghost", lambda: self.page_step(1), "The next page or picture of this file")
        tools.addWidget(self.b_pprev); tools.addWidget(self.b_pnext)
        if not big:
            tools.addWidget(D.button("Enlarge", None, lambda: self.enlarge(), "The same view in a big window"))
        self.stack = QStackedWidget()
        self.view = PicView(); self.text = PreviewText()
        self.stack.addWidget(self.view); self.stack.addWidget(self.text)
        self.stack.setMinimumHeight(560 if big else 300)
        v.addWidget(self.stack, 1)
        self.info = D.label("", "muted"); v.addWidget(self.info)
        from PySide6.QtWidgets import QLineEdit                                 # 3.61.0: what the scan read, fixed here
        rr = QHBoxLayout(); rr.setSpacing(D.SPACE["s"]); v.addLayout(rr)
        self.read_lab = D.label("It read", "muted", wrap=False)
        rr.addWidget(self.read_lab)
        self.reading = QLineEdit(); self.reading.setPlaceholderText("Click a box in the picture, or select words in the passage")
        self.read_orig = ""
        rr.addWidget(self.reading, 1)
        self.b_fixread = D.button("Fix the reading", "ghost", lambda: self.fix_reading(),
                                  "Correct what the scan read here; the fix applies every time a picture is read on this PC")
        self.b_usemean = D.button("Use as the meaning", None, lambda: self.use_meaning(),
                                  "Put these words in the term's definition box")
        rr.addWidget(self.b_fixread); rr.addWidget(self.b_usemean)
        ar = QHBoxLayout(); ar.setSpacing(D.SPACE["s"]); v.addLayout(ar)                 # 3.80.0: the drawn box
        self.area_lab = D.label("", "muted"); ar.addWidget(self.area_lab, 1)
        self.b_readarea = D.button("Read this area again", "ghost", lambda: self.read_area(),
                                   "Read only what is inside the box: a stray mark or a missing letter often comes out right")
        self.b_addterm = D.button("Add as a term...", "ghost", lambda: self.add_term(),
                                  "A term the scan missed: the text in the box joins the scan's terms and this effort's list, "
                                  "with this place")
        ar.addWidget(self.b_readarea); ar.addWidget(self.b_addterm)
        for b in (self.b_readarea, self.b_addterm):
            b.setVisible(False)
        self.area_read = ""
        self.view.on_click = self.clicked
        self.view.on_area = self.area_drawn
        self.text.selectionChanged.connect(lambda: self._selected_text())
        self.legend = D.label(LEGEND, "muted"); v.addWidget(self.legend)
        self.show_k()

    # ---- places
    def show_place(self, k):
        """Show place k (0-based), its first find."""
        if 0 <= k < len(self.locs):
            self.k, self.find_k, self.page_k = k, 0, None
            self.show_k()

    def page_step(self, d):
        """3.61.0: every page or picture of the file, not only the ones with a find; a find's place shows again with
        Find < and > or Previous and Next place."""
        srcs = getattr(self, "cur_srcs", None) or []
        if not srcs:
            return None
        base = self.page_k if self.page_k is not None else getattr(self, "page_k_base", -1 if d > 0 else 0)
        self.page_k = max(0, min(len(srcs) - 1, base + d))
        self.find_k = 0
        self.show_k()
        return self.page_k

    def clicked(self, pt):
        """3.61.0: a click on a box shows what the scan read there."""
        b = self.view.box_at(pt)
        if b is None:
            return None
        line = next((t for bb, t, _c in self.lines if bb == b), None)
        if line is None:                                  # a find inside a line: the line it sits in
            line = next((t for bb, t, _c in self.lines if bb[0] <= b[0] + 1 and bb[2] >= b[2] - 1 and bb[1] <= b[1] + 1 and bb[3] >= b[3] - 1), "")
        self.set_reading(line)
        self.view.mark(b)
        return line

    # ---- 3.80.0: a box drawn on the picture
    def area_drawn(self, box):
        """Every reading inside the box is highlighted at once, with the text read there (the scan's own readings)."""
        x0, y0, x1, y1 = box
        inside = [(b, t) for b, t, _c in self.lines
                  if x0 <= (b[0] + b[2]) / 2 <= x1 and y0 <= (b[1] + b[3]) / 2 <= y1]
        inside.sort(key=lambda bt: (round(bt[0][1] / 12), bt[0][0]))
        self.view.mark_many([b for b, _t in inside])
        text = " ".join(t for _b, t in inside)
        self.area_read = text
        self.set_reading(text)
        self.area_lab.setText(f"Box: {len(inside)} reading(s) inside" if inside else "Box: nothing read inside yet; Read this area again")
        for b in (self.b_readarea, self.b_addterm):
            b.setVisible(True)
        diag.activity("preview_area_drawn")
        return text

    def area_crop(self):
        """The drawn box of the picture as a PIL image, or None."""
        box = self.view.area
        if box is None or self.view.pix is None:
            return None
        from PIL import Image
        q = self.view.pix.pixmap().toImage().convertToFormat(QImage.Format_RGB888)
        w, h, bpl = q.width(), q.height(), q.bytesPerLine()
        im = Image.frombuffer("RGB", (w, h), bytes(q.constBits()), "raw", "RGB", bpl, 1)
        x0, y0, x1, y1 = [int(round(v)) for v in box]
        return im.crop((max(0, x0), max(0, y0), min(w, x1), min(h, y1))).copy()

    def read_area(self, wait=False):
        """Read only the drawn box (off the window's thread); the text comes into It read, to correct."""
        crop = self.area_crop()
        if crop is None:
            self.info.setText("Drag a box around the text first.")
            return None
        from .progress import JobWorker

        def job(_p, _s, c=crop):
            import pictures as PIC
            lines = PIC.read_region_lines(c)
            text = " ".join(t for _b, t, _c in lines).strip()
            if not text:
                text, _conf = PIC.read_region_as_one_line(c)
            return text

        w = JobWorker(job)

        def done(res):
            try:
                if isinstance(res, str):
                    self.reading.setText(res)
                    self.area_lab.setText(f"Read again: {res}" if res else "Nothing read inside the box; type what it says")
                else:
                    self.area_lab.setText(f"The box could not be read ({type(res).__name__}); type what it says")
            except RuntimeError:
                pass
        self.area_lab.setText("Reading the box...")
        w.done.connect(done)
        _ALIVE.append(w); w.finished.connect(lambda w=w: _ALIVE.remove(w) if w in _ALIVE else None)
        w.start()
        if wait:
            import time
            from PySide6.QtWidgets import QApplication
            t0 = time.time()
            while w.isRunning() and time.time() - t0 < 60:
                QApplication.processEvents(); time.sleep(0.02)
            QApplication.processEvents()
        diag.activity("preview_area_read")
        return w

    def add_term(self, text=None):
        """A term the scan missed: the box's text (as corrected) with this place."""
        t = " ".join((text if text is not None else self.reading.text()).split())
        if not t:
            self.info.setText("Draw a box around the term, correct the text, then Add as a term.")
            return None
        loc = self.locs[self.k] if self.locs else ""
        if self.on_add_term is not None:
            self.on_add_term(t, loc, self.area_read, self.area_crop())
        return t

    def set_reading(self, text):
        self.read_orig = text or ""
        self.reading.setText(self.read_orig)
        if self.on_find_text is not None and text:
            self.on_find_text(text)

    def _selected_text(self):
        t = " ".join(self.text.textCursor().selectedText().replace("\u2029", " ").split())
        if t:
            self.read_orig = ""
            self.reading.setText(t)

    def fix_reading(self):
        new = " ".join(self.reading.text().split())
        if not self.read_orig or not new or new == self.read_orig:
            self.info.setText("Click a box, change what it read, then Fix the reading.")
            return None
        import ocrfixes as OF
        OF.add(self.read_orig, new, f"fixed in the preview of {self.term}")
        self.info.setText(f"Fixed: {self.read_orig} reads as {new} from the next scan on this PC.")
        diag.activity("preview_fix_reading", n=1)
        self.read_orig = new
        return new

    def use_meaning(self):
        t = " ".join(self.reading.text().split())
        if t and self.on_meaning is not None:
            self.on_meaning(t)
        return t

    def go(self, d, find=0):
        self.page_k = None
        if self.locs:
            self.k = (self.k + d) % len(self.locs)
            self.find_k = find
            self.show_k()

    def show_k(self):
        n = len(self.locs)
        self.b_prev.setEnabled(n > 1); self.b_next.setEnabled(n > 1)
        self.finds = []
        if not n:
            self.where.setText("No place recorded."); self._text("")
            return
        loc = self.locs[self.k]
        self.where.setText(f"Place {self.k + 1} of {n}: {loc}")
        try:
            name, page, para = parse_loc(loc)
            path = self.path_of(name)
            if not path or not os.path.isfile(path):
                self.state = "missing"
                return self._text(f"{html.escape(name)} is not on this PC where it was scanned, so the place cannot be shown.")
            import pictures as PIC
            srcs = sources(path)
            idx = PIC.match_source([lbl for lbl, _ld in srcs], loc)
            self.cur_path, self.cur_srcs = path, srcs
            if self.page_k is not None and 0 <= self.page_k < len(srcs):
                idx = self.page_k
                self.where.setText(f"Place {self.k + 1} of {n}: {loc}   |   showing {srcs[idx][0]} ({idx + 1} of {len(srcs)} in the file)")
            elif idx is not None:
                self.page_k_base = idx
            if idx is None:
                sn = typed_html(path, loc, self.term, para)
                self.state = "text" if sn else "none"
                return self._text(sn or "The term is in a part of the file that cannot be shown; the place is listed below.")
            label, loader = srcs[idx]
            key = (path, label)
            if key in _CACHE:
                return self._paint(*_CACHE[key])
            self.state = "reading"
            self.info.setText("Reading the picture...")
            self._start(key, loader, loc)
        except Exception:  # noqa: BLE001  the place is still listed
            diag.swallowed()
            self.state = "none"
            self._text("The place could not be shown; it is listed below.")

    def _start(self, key, loader, loc):
        from .progress import JobWorker
        want = (self.k, key)
        term = self.term
        w = JobWorker(lambda _p, _s: read_place(key[0], key[1], loader, loc, term))

        def done(res, _want=want, _key=key):
            if isinstance(res, tuple):
                _CACHE[_key] = res
                if len(_CACHE) > 40:
                    _CACHE.pop(next(iter(_CACHE)))
            try:
                if (self.k, _key) == _want:
                    if isinstance(res, tuple):
                        self._paint(*res)
                    else:
                        self.state = "none"
                        self._text(f"The picture could not be read ({type(res).__name__}).")
            except RuntimeError:                         # the view was closed meanwhile
                pass

        def gone():
            w.wait(2000)
            if w in _ALIVE:
                _ALIVE.remove(w)

        w.done.connect(done); w.finished.connect(gone)
        _ALIVE.append(w)
        diag.activity("preview_picture")
        w.start()

    def wait(self, seconds=60):
        """Tests: until the picture being read is shown."""
        import time
        from PySide6.QtWidgets import QApplication
        t0 = time.time()
        while self.state == "reading" and time.time() - t0 < seconds:
            QApplication.processEvents(); time.sleep(0.02)
        return self.state

    def _text(self, html_text):
        self.stack.setCurrentWidget(self.text)
        self.text.setHtml(html_text or "")
        self.info.setText("")
        self.legend.setVisible(False)
        self._controls()

    # ---- a picture and its finds
    def _paint(self, qimg, lines, hits, note=""):
        import app_gui as A
        for b in (self.b_readarea, self.b_addterm):          # 3.80.0: a new picture, no box yet
            b.setVisible(False)
        self.area_lab.setText(""); self.area_read = ""
        ft = _fold(self.term)
        cutoff = A.ocr_cutoff()
        finds = [b for b in hits]
        others = []
        for (x0, y0, x1, y1), text, conf in lines:
            k = _fold(text).find(ft) if ft else -1
            if k >= 0:
                per = (x1 - x0) / max(1, len(text))
                finds.append((x0 + k * per, y0, x0 + (k + len(self.term)) * per, y1))
            others.append(((x0, y0, x1, y1), "low" if conf < cutoff else "line"))
        finds.sort(key=lambda b: (round(b[1] / 12), b[0]))
        self.finds = finds
        self.lines = list(lines)
        if self.find_k < 0:
            self.find_k = len(finds) - 1
        self.find_k = max(0, min(self.find_k, len(finds) - 1)) if finds else 0
        boxes = others + [(b, "typed" if b in hits else "find") for b in finds]
        if finds:
            boxes.append((finds[self.find_k], "sel"))
        self.stack.setCurrentWidget(self.view)
        self.view.set_picture(qimg, boxes)
        self.legend.setVisible(True)
        self.state = "picture"
        if note:
            self.view.fit()
            self.info.setText(note)
        elif finds:
            self.view.focus(finds[self.find_k])
            from PySide6.QtCore import QTimer                          # 3.61.0: again once the view has its size
            QTimer.singleShot(0, lambda b=finds[self.find_k]: self._refocus(b))
            self.info.setText(f"{len(lines)} reading(s) on this picture" if lines else "Typed text on this page")
            self._find_line(finds[self.find_k])
        else:
            self.view.fit()
            self.info.setText("The reader did not find the term on this picture now (the scan may have read it in a part, or "
                              "at another size); every reading is boxed.")
        self._controls()

    def _refocus(self, box):
        try:
            self.view.focus(box)
        except RuntimeError:                                       # closed meanwhile
            pass

    def _find_line(self, box):
        """The reading a find sits in becomes It read (and the find as text above)."""
        line = next((t for bb, t, _c in self.lines if bb[0] <= box[0] + 1 and bb[2] >= box[2] - 1 and bb[1] <= box[1] + 1
                     and bb[3] >= box[3] - 1), "")
        if line:
            self.set_reading(line)

    def _controls(self):
        n = len(self.finds)
        many = len(getattr(self, "cur_srcs", None) or []) > 1
        self.b_pprev.setEnabled(many); self.b_pnext.setEnabled(many)
        self.find_lab.setText(f"Find {self.find_k + 1} of {n} here" if n else "")
        pic = self.stack.currentWidget() is self.view
        for b in (self.b_out, self.b_in, self.b_fit):
            b.setEnabled(pic)
        self.b_fprev.setEnabled(n > 1 or len(self.locs) > 1); self.b_fnext.setEnabled(n > 1 or len(self.locs) > 1)

    def step(self, d):
        """The next (or previous) find; past the last on this picture, the next place."""
        if self.finds and 0 <= self.find_k + d < len(self.finds):
            self.find_k += d
            boxes = [b for b in self.view.boxes if b[1] != "sel"] + [(self.finds[self.find_k], "sel")]
            self.view.set_picture(self.view.pix.pixmap().toImage(), boxes)
            self.view.focus(self.finds[self.find_k])
            self._find_line(self.finds[self.find_k])
            self._controls()
            return True
        self.page_k = None
        self.go(d, find=0 if d > 0 else -1)
        return True

    def enlarge(self, run=True):
        d = QDialog(self); d.setWindowTitle(f"Where {self.term} was found"); d.resize(1200, 820)
        lv = QVBoxLayout(d)
        big = FoundView(self.term, self.locs, self.path_of, big=True, on_meaning=self.on_meaning, on_find_text=self.on_find_text,
                        on_add_term=self.on_add_term)
        big.k, big.find_k = self.k, self.find_k
        big.show_k()
        lv.addWidget(big)
        if run:
            d.exec()
        return big
