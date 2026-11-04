"""Where a term was found, shown (3.50.0; brings back the classic window's preview, retired in 3.14.0).

For each place a term was found:
  a picture (an image or diagram inside a Word, PowerPoint or Excel file, an image file, or a PDF page) is drawn
  whole with every reading boxed: the term in yellow (the selected find thicker, filled), other readings in green,
  low-confidence readings in red, and on a PDF page the typed matches in orange. Zoom with the wheel or + and -,
  drag to move, Fit to see it all, Enlarge for a big window.
  typed text (Word, PowerPoint, Excel) shows the passage with every match highlighted.
Find < and > step through every find of the term, across all its places; Previous place and Next place jump between
files and pages. Pictures are read off the window's thread and kept for the session, so going back is instant.
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

PENS = {"sel": ("#F59E0B", 4), "find": ("#FACC15", 3), "line": ("#22C55E", 1), "low": ("#EF4444", 1), "typed": ("#F97316", 2)}
LEGEND = ("Yellow: the term (the one selected is filled). Green: other readings. Red: readings below the reader's confidence. "
          "Orange: typed text on a PDF page.")
_CACHE = {}               # (path, source label) -> (QImage, lines, typed hits); the session's pictures
_SOURCES = {}             # path -> [(label, loader)]
_ALIVE = []               # reading jobs until they finish (never dropped while running)


def _fold(t):
    import app_gui as A
    return A.fold(str(t or "")).casefold()


class PicView(QGraphicsView):
    """A picture with boxes: wheel to zoom, drag to move, double-click to zoom in."""
    def __init__(self):
        super().__init__()
        self.scene_ = QGraphicsScene(self); self.setScene(self.scene_)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHints(self.renderHints())
        self.setBackgroundBrush(QBrush(QColor("#3A3F47")))
        self.pix = None
        self.boxes = []

    def set_picture(self, qimg, boxes):
        self.scene_.clear()
        self.pix = QGraphicsPixmapItem(QPixmap.fromImage(qimg)); self.pix.setTransformationMode(Qt.SmoothTransformation)
        self.scene_.addItem(self.pix)
        self.scene_.setSceneRect(QRectF(0, 0, qimg.width(), qimg.height()))
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

    def fit(self):
        if self.pix is not None:
            self.fitInView(self.scene_.sceneRect(), Qt.KeepAspectRatio)

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
        self.fitInView(QRectF(cx - w / 2, cy - h / 2, w, h).intersected(r) if r.contains(cx, cy) else r, Qt.KeepAspectRatio)

    def zoom(self, f):
        self.scale(f, f)

    def wheelEvent(self, e):
        self.zoom(1.25 if e.angleDelta().y() > 0 else 0.8)

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
        import pictures as PIC
        try:
            lines = PIC.read_region_lines(img)
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


class FoundView(QWidget):
    def __init__(self, term, locs, path_of, big=False):
        super().__init__()
        self.term, self.locs, self.path_of, self.big = term, list(locs), path_of, big
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
        if not big:
            tools.addWidget(D.button("Enlarge", None, lambda: self.enlarge(), "The same view in a big window"))
        self.stack = QStackedWidget()
        self.view = PicView(); self.text = QTextBrowser()
        self.stack.addWidget(self.view); self.stack.addWidget(self.text)
        self.stack.setMinimumHeight(560 if big else 300)
        v.addWidget(self.stack, 1)
        self.info = D.label("", "muted"); v.addWidget(self.info)
        self.legend = D.label(LEGEND, "muted"); v.addWidget(self.legend)
        self.show_k()

    # ---- places
    def show_place(self, k):
        """Show place k (0-based), its first find."""
        if 0 <= k < len(self.locs):
            self.k, self.find_k = k, 0
            self.show_k()

    def go(self, d, find=0):
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
            self.info.setText(f"{len(lines)} reading(s) on this picture" if lines else "Typed text on this page")
        else:
            self.view.fit()
            self.info.setText("The reader did not find the term on this picture now (the scan may have read it in a part, or "
                              "at another size); every reading is boxed.")
        self._controls()

    def _controls(self):
        n = len(self.finds)
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
            self._controls()
            return True
        self.go(d, find=0 if d > 0 else -1)
        return True

    def enlarge(self, run=True):
        d = QDialog(self); d.setWindowTitle(f"Where {self.term} was found"); d.resize(1200, 820)
        lv = QVBoxLayout(d)
        big = FoundView(self.term, self.locs, self.path_of, big=True)
        big.k, big.find_k = self.k, self.find_k
        big.show_k()
        lv.addWidget(big)
        if run:
            d.exec()
        return big
