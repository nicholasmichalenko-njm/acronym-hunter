"""Assign in Qt (2.59.0): the customer document as it looks, every page in one scroll, each review sentence a box you
click; Ctrl+click adds or takes out a sentence; drag a rubber band around several (Ctrl+drag adds); Ctrl+wheel zooms.
Headers and footers have no box. Labels in the left margin say what each sentence is. Beside the page: the sentence
card (source, decision, author(s), relationships, notes) and the response structure (click a section: the target for
R). Keys: R requirement, L and E (M) the Shipley designation, C support, G customer's, X ignore, J combine (2.68.0;
M before), S split (where you clicked in the selected
sentence), Ctrl+Z undo. 2.68.0: the structure is built beside the page as you assign, volume by volume. Every decision goes through assign_ops, the same rules as the tkinter edition.
"""
import os, re
from PySide6.QtCore import Qt, QEvent, QPoint, QRectF, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGraphicsItem, QGridLayout,
                               QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsSimpleTextItem,
                               QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QScrollArea, QSplitter, QStyle, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
                               QCheckBox)
import diag
import effortrec as R_
import pagemarks as PM
import pagebudget as PB
import structparts as SP
import compliance as C
import setupdoc as SD
import pagesent as PS
import matrixdesign as MD
import outline_ops as O
import structstart as SS
import capture as CAP
from rfpoutline import mapped as HS_mapped
import office_pdf as OP
from . import design as D

SCALE = 2.0          # pixels per PDF point in the page pictures (sharp when zoomed in)
GAP = 24             # between pages, in points
MARGIN = 160         # the label margin left of the pages, in points
SHEET_X = 8          # 2.96.0: Sheet view starts near the left edge (its row numbers are its labels)
WORD = re.compile(r"[A-Za-z0-9]+")



BULK_DECISIONS = (("Decide all...", ""), ("Instruction", "L"), ("Evaluation", "M"), ("Requirement", "SOW"),
                  ("Support", "ctx"), ("Information", "cust"), ("Not applicable", "ignore"))      # 4.1.0: the piece types' names

EX_BUILTIN_CAPTURES = ("contact", "submit", "format", "acronym", "question", "keydate", "factor", "pagelimit", "deliverable",
                       "detail", "hot", "graphic")          # 3.29.0: captures filed by _do_capture


def _first_piece(it):
    """4.5.0: a piece can have several types ("requirement;date"); the page colors it by the first."""
    return (str(it.get("piece") or "").split(";") or [""])[0]


def RI_decisions(cfg, et, show_all=False):
    import reviewitems as RI
    return RI.decisions_for(cfg, et, show_all)


SG_DEC = {"L": "Keep", "M": "Keep", "SOW": "Keep", "ctx": "Context", "cust": "Customer", "ignore": "Drop", "I": "Keep"}   # 3.18.0
SG_LM = {"L": "L", "M": "M", "SOW": "C", "I": "I"}
SG_KEYS = {"L": "L", "M": "E", "SOW": "R", "ctx": "C", "cust": "G", "ignore": "X", "I": "I"}


def parse_area(text):
    """3.19.0: '2:72.0,140.0,540.0,168.0' -> (2, 72.0, 140.0, 540.0, 168.0), or None."""
    try:
        pg, rest = str(text or "").split(":", 1)
        l, t, r, b = (float(x) for x in rest.split(","))
        return int(pg), min(l, r), min(t, b), max(l, r), max(t, b)
    except (ValueError, TypeError):
        return None


class StructTree(QTreeWidget):
    """3.29.0: the response structure; only a left double-click renames (or sets Pages), a right-click opens the menu."""
    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.LeftButton:
            e.accept()
            return
        super().mouseDoubleClickEvent(e)


class SentenceBox(QGraphicsPathItem):
    def __init__(self, iid, rects):
        path = QPainterPath()
        for l, t, r, b in rects:
            path.addRoundedRect(QRectF(l - 1.5, t - 1, r - l + 3, b - t + 2), 2, 2)
        super().__init__(path.simplified())
        self.iid = iid
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.dec = ""
        self.hover = False
        self.current = False
        self.sg = ""                                # 3.18.0: the suggestion shown (a category), "" for none
        self.lm = ""                                # 3.18.1: a requirement's designation (L, M, C): its own color
        self.mark = False                           # 3.18.1: something was captured from it: the capture color outline

    def color(self):
        return QColor(D.page_color(self.dec, self.lm))

    def style(self, dec=None, current=None):
        self.dec = self.dec if dec is None else dec
        self.current = self.current if current is None else current
        col = self.color()
        sel = self.isSelected()
        fill = QColor("#FDE68A") if (sel and not self.dec) else QColor(col)
        fill.setAlpha((140 if sel else 0) if not self.dec else (115 if sel else (34 if self.dec == "Heading" else 70)))
        if self.mark and not self.dec and not sel:                 # 3.18.1: captured from, not decided yet: a light fill
            fill = QColor(D.CAPTURE_COLOR); fill.setAlpha(36)
        self.setBrush(QBrush(fill))
        pen = QPen(QColor("#F59E0B") if self.current else QColor(D.CAPTURE_COLOR) if self.mark
                   else (col if self.dec else QColor("#CBD5E1")))
        pen.setWidthF(2.6 if self.current else 1.8 if self.mark else (1.4 if (self.dec or sel or self.hover) else 0.7))
        if self.sg and not self.dec and not self.current:          # 3.18.0: a suggestion: dashed, in its category's color
            sc = QColor(D.page_color(SG_DEC.get(self.sg, ""), SG_LM.get(self.sg, "")))
            pen = QPen(sc); pen.setWidthF(1.8); pen.setStyle(Qt.DashLine)
            if not sel:
                f2 = QColor(sc); f2.setAlpha(28); self.setBrush(QBrush(f2))
        pen.setCosmetic(True)
        self.setPen(pen)

    def paint(self, painter, option, widget=None):
        option.state &= ~QStyle.State_Selected        # the colors say it is selected; no dashed frame
        super().paint(painter, option, widget)

    def hoverEnterEvent(self, e):
        self.hover = True
        self.style()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self.hover = False
        self.style()
        super().hoverLeaveEvent(e)


class PageView(QGraphicsView):
    clicked_word = Signal(str, int)               # (sentence id, word index) for S
    hover_word = Signal(str, int)                 # 2.93.0: the word under the mouse in the selected sentence ("", -1: none)
    word_drag = Signal(str, int, int)             # 2.96.0: words being dragged across inside the selected sentence (first, last)
    grabbed = Signal(str, int, int)               # 2.96.0: the words dragged across, when the mouse is let go
    span_drag = Signal(list)                      # 3.28.1: words dragged across several sentences: [(id, first, last)]
    span_grabbed = Signal(list)                   # 3.28.1: ... when the mouse is let go
    captured = Signal(QRectF)                     # 2.70.0: an area dragged in Add missed text mode (scene coordinates)
    menu_at = Signal(str, QPoint)                 # 3.29.0: a right-click on a sentence (its id, where on the screen)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.setBackgroundBrush(D.color("page"))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)        # 2.96.0: a short sheet sits at the top, not in the middle
        self.boxes = {}
        self.words = {}                            # sentence id -> [scene rects of its words, in order]
        self.zoom = 1.0
        self.capturing = False
        self._cap0, self._cap_item = None, None
        self._hovered = ("", -1)
        self._drag = None                         # 2.96.0: (sentence id, first word, last word) while dragging inside it
        self.viewport().setMouseTracking(True)
        self.pan_tool = False                     # 3.15.1: the Pan tool (H): a left drag moves the page
        self._space = False                       # Space held: a left drag moves the page
        self._pan = None                          # where a pan drag started (view position)

    # ------------------------------------------------------------ 3.15.1: pan
    def set_pan(self, on):
        self.pan_tool = bool(on)
        self.viewport().setCursor(Qt.OpenHandCursor if on else Qt.ArrowCursor)

    def panning(self):
        return self._pan is not None

    def _pan_start(self, pos):
        self._pan = pos
        self.viewport().setCursor(Qt.ClosedHandCursor)

    def _pan_move(self, pos):
        d = pos - self._pan
        self._pan = pos
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())

    def _pan_end(self):
        self._pan = None
        self.viewport().setCursor(Qt.OpenHandCursor if (self.pan_tool or self._space) else Qt.ArrowCursor)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat() and not self.capturing:
            self._space = True
            self.viewport().setCursor(Qt.OpenHandCursor)
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._space = False
            if self._pan is None:
                self.viewport().setCursor(Qt.OpenHandCursor if self.pan_tool else Qt.ArrowCursor)
            return
        super().keyReleaseEvent(e)

    def set_capture(self, on):
        self.capturing = on
        self.setDragMode(QGraphicsView.NoDrag if on else QGraphicsView.RubberBandDrag)
        self.viewport().setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)

    def box_at(self, pos):
        """The sentence box under a view position, looking past marks drawn over it (tints, the cut line)."""
        return next((i for i in self.items(pos) if isinstance(i, SentenceBox)), None)

    def _snap(self, iid, p, reach):
        """3.29.0: (distance, word index) of the word of sentence iid on the line under scene point p, nearest within
        reach points (on a word: 0), or None."""
        best = None
        for k, r in enumerate(self.words.get(iid, [])):
            if r.top() - 3 <= p.y() <= r.bottom() + 3:
                dx = 0.0 if r.left() <= p.x() <= r.right() else min(abs(p.x() - r.left()), abs(p.x() - r.right()))
                if dx <= reach and (best is None or dx < best[0]):
                    best = (dx, k)
        return best

    def word_any(self, pos, reach=0):
        """3.28.1: (sentence id, word index) under a view position in any sentence; ("", -1) off the words. 3.29.0: inside
        a sentence, off its words (an opening bracket, the full stop), the nearest word on that line; with reach, a
        position just past a sentence (dragging beyond its end) takes the nearest word within reach points."""
        it = self.box_at(pos)
        p = self.mapToScene(pos)
        if isinstance(it, SentenceBox):
            for k, r in enumerate(self.words.get(it.iid, [])):
                if r.adjusted(-1, -1, 1, 1).contains(p):
                    return it.iid, k
            got = self._snap(it.iid, p, 1e9)
            return it.iid, (got[1] if got else -1)
        if reach:
            best = None
            for iid in self.boxes:
                got = self._snap(iid, p, reach)
                if got and (best is None or got[0] < best[0]):
                    best = (got[0], iid, got[1])
            if best:
                return best[1], best[2]
        return "", -1

    def span(self, a, b):
        """3.28.1: the words from a to b (each (sentence id, word index)) in reading order: [(id, first, last)]."""
        order = getattr(self, "order", None) or sorted(self.boxes, key=lambda i: self.boxes[i].boundingRect().top())
        pos = {iid: n for n, iid in enumerate(order)}
        if a[0] not in pos or b[0] not in pos:
            return []
        if (pos[a[0]], a[1]) > (pos[b[0]], b[1]):
            a, b = b, a
        out = []
        for iid in order[pos[a[0]]:pos[b[0]] + 1]:
            n = len(self.words.get(iid, []))
            if not n:
                continue
            f = a[1] if iid == a[0] else 0
            l = b[1] if iid == b[0] else n - 1
            if f <= l:
                out.append((iid, f, l))
        return out

    def word_at(self, pos, reach=0):
        """(sentence id, word index) under a view position, inside the one selected sentence; ("", -1) otherwise. 3.29.0:
        off its words, the nearest word on that line (with reach, also just past the sentence)."""
        it = self.box_at(pos)
        sel = [b for b in self.scene().selectedItems() if isinstance(b, SentenceBox)]
        if len(sel) != 1:
            return "", -1
        p = self.mapToScene(pos)
        if it is sel[0]:
            for k, r in enumerate(self.words.get(it.iid, [])):
                if r.adjusted(-1, -1, 1, 1).contains(p):
                    return it.iid, k
            got = self._snap(it.iid, p, 1e9)
            return it.iid, (got[1] if got else -1)
        if reach and (it is None or not isinstance(it, SentenceBox)):
            got = self._snap(sel[0].iid, p, reach)
            if got:
                return sel[0].iid, got[1]
        return "", -1

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            self._pan_move(e.position().toPoint())
            return
        if (self.pan_tool or self._space) and not e.buttons():
            return                                          # the hand stays; no split marks while panning
        if self._drag is not None and e.buttons() & Qt.LeftButton:     # 2.96.0: dragging across words
            iid, k2 = self.word_at(e.position().toPoint(), reach=60)       # 3.29.0: past the end still reaches it
            k = self._drag[1]
            if iid == self._drag[0] and k2 >= 0 and k2 != self._drag[2]:
                self._drag = (iid, k, k2)
                self.word_drag.emit(iid, min(k, k2), max(k, k2))
            elif iid != self._drag[0]:                                  # 3.28.1: on into another sentence: a span
                oi, ok = self.word_any(e.position().toPoint())
                if oi and ok >= 0:
                    self._span = ((self._drag[0], self._drag[1]), (oi, ok))
                    self._drag = None
                    self.span_drag.emit(self.span(*self._span))
            return
        if getattr(self, "_span", None) is not None and e.buttons() & Qt.LeftButton:   # 3.28.1: words across sentences
            oi, ok = self.word_any(e.position().toPoint(), reach=60)
            if oi and ok >= 0 and (oi, ok) != self._span[1]:
                self._span = (self._span[0], (oi, ok))
                self.span_drag.emit(self.span(*self._span))
            return
        if not self.capturing and not e.buttons():          # 2.93.0: show where a click would split
            h = self.word_at(e.position().toPoint())
            if h != self._hovered:
                self._hovered = h
                self.hover_word.emit(*h)
            b = self.boxes.get(h[0]) if h[0] else None
            if b is not None:                                # the sentence's own cursor wins over the page's
                b.setCursor(Qt.SplitHCursor if h[1] > 0 else Qt.PointingHandCursor)
                self.viewport().setCursor(b.cursor())
        if self.capturing and self._cap0 is not None:
            r = QRectF(self._cap0, self.mapToScene(e.position().toPoint())).normalized()
            if self._cap_item is None:
                pen = QPen(QColor("#B45309")); pen.setWidthF(1.2); pen.setCosmetic(True); pen.setStyle(Qt.DashLine)
                self._cap_item = self.scene().addRect(r, pen, QBrush(QColor(245, 158, 11, 40)))
                self._cap_item.setZValue(5)
            else:
                self._cap_item.setRect(r)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._pan is not None:
            self._pan_end()
            return
        if getattr(self, "_span", None) is not None:       # 3.28.1: let go after dragging over words
            a, b = self._span
            self._span = None
            sp = self.span(a, b)
            if a == b or not sp:
                return super().mouseReleaseEvent(e)
            if len(sp) == 1:
                self.grabbed.emit(*sp[0])
            else:
                self.span_grabbed.emit(sp)
            return
        if self._drag is not None:                          # 2.96.0: a click splits; a drag picks words
            iid, a, b = self._drag
            self._drag = None
            if a == b:
                self.clicked_word.emit(iid, a)
            else:
                self.grabbed.emit(iid, min(a, b), max(a, b))
            return
        if self.capturing and self._cap0 is not None:
            r = QRectF(self._cap0, self.mapToScene(e.position().toPoint())).normalized()
            self._cap0 = None
            if self._cap_item is not None:
                self.scene().removeItem(self._cap_item)
                self._cap_item = None
            if r.width() > 3 and r.height() > 3:
                self.captured.emit(r)
            return
        super().mouseReleaseEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier and e.angleDelta().y():     # 3.71.0: Ctrl and the side wheel no longer zoom out
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            if 0.3 < self.zoom * f < 5:
                self.zoom *= f
                self.scale(f, f)
            return
        dy = e.angleDelta().y()
        if not dy or e.pixelDelta().y():                  # a touchpad already scrolls smoothly; sideways goes as it was
            return super().wheelEvent(e)
        self.smooth_scroll(-dy)                            # 3.20.3: a wheel notch glides instead of jumping
        e.accept()

    def smooth_scroll(self, delta):
        """Glide the page by delta (wheel units: 120 a notch): about three lines a notch, eased over 200 ms; notches that
        come quickly add up."""
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        sb = self.verticalScrollBar()
        step = delta / 120.0 * max(40, sb.singleStep() * 3)
        anim = getattr(self, "_glide", None)
        start = sb.value()
        target = (self._glide_to if (anim is not None and anim.state() == QPropertyAnimation.Running) else start) + step
        target = int(max(sb.minimum(), min(sb.maximum(), target)))
        if anim is None:
            anim = self._glide = QPropertyAnimation(sb, b"value", self)
            anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.stop()
        anim.setDuration(200)
        anim.setStartValue(start); anim.setEndValue(target)
        self._glide_to = target
        anim.start()
        return target

    def enterEvent(self, e):
        """3.20.3: the page takes the keyboard when the mouse is over it (so Space and drag pans at once), unless you
        are typing in a box."""
        from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox
        fw = QApplication.focusWidget()
        if not isinstance(fw, (QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox)):
            self.setFocus(Qt.MouseFocusReason)
        super().enterEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and (self.pan_tool or self._space) and not self.capturing):
            self._pan_start(e.position().toPoint())        # 3.15.1: middle drag, Space and drag, or the Pan tool
            return
        if self.capturing and e.button() == Qt.LeftButton:
            self._cap0 = self.mapToScene(e.position().toPoint())
            return
        top = self.itemAt(e.position().toPoint())
        if top is not None and top.isWidget():           # the Split here bar: its buttons take the click
            return super().mousePressEvent(e)
        it = self.box_at(e.position().toPoint())
        sel = [b for b in self.scene().selectedItems() if isinstance(b, SentenceBox)]
        if isinstance(it, SentenceBox) and len(sel) == 1 and sel[0] is it and not (e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
            wi, k = self.word_at(e.position().toPoint())     # 3.29.0: off a word (a bracket, the full stop): the nearest
            if wi == it.iid and k >= 0:
                self._drag = (it.iid, k, k)       # 2.96.0: decided on release: a click (split) or a drag (words)
            return                                  # a click inside the selected sentence keeps it selected
        if isinstance(it, SentenceBox) and e.button() == Qt.LeftButton and not (e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
            oi, ok = self.word_any(e.position().toPoint())          # 3.28.1: a press on a word of any sentence may start
            if oi and ok >= 0:                                       # a drag over words (across sentences, whatever is
                self._span = ((oi, ok), (oi, ok))                    # selected); let go without moving: a plain click
        super().mousePressEvent(e)

    def contextMenuEvent(self, e):
        """3.29.0: right-click a sentence for what can come off it."""
        b = None if self.capturing else self.box_at(e.pos())
        if b is None:
            return super().contextMenuEvent(e)
        self.menu_at.emit(b.iid, e.globalPos())
        e.accept()

    def fit(self):
        r = self.scene().itemsBoundingRect().united(QRectF(0, 0, 1, 1))
        if r.width() > 0:
            self.scene().setSceneRect(QRectF(0, r.top(), r.right() + 12, r.height()))
            self.resetTransform()
            self.zoom = max(0.3, (self.viewport().width() - 24) / (r.right() + 12))
            self.scale(self.zoom, self.zoom)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().minimum())


class CopyWorker(QThread):
    """PDF copies of Word, Excel and PowerPoint files, made by Office on this PC (one session per program)."""
    done = Signal(dict)

    def __init__(self, paths, folder):
        super().__init__()
        self.paths, self.folder = paths, folder
        self.stop_asked = False                    # 3.14.3: Stationkeeper is closing: end now, keep no half-made copy

    def run(self):
        import ocrpdf
        ocr = [p for p in self.paths if ocrpdf.needs_copy(p)]             # 2.96.0: pictures and scanned PDFs
        office = [p for p in self.paths if p not in ocr]
        res = {}
        try:
            res.update(OP.make_many(office, self.folder, stop=lambda: self.stop_asked) if office else {})
        except Exception:
            diag.swallowed()
            res.update({p: RuntimeError("Office could not save a PDF copy") for p in office})
        for p in ocr:
            if self.stop_asked:
                res[p] = RuntimeError("stopped before the PDF copy was made")
                continue
            try:
                ocrpdf.make(p, self.folder)
                res[p] = ""
            except Exception:
                diag.swallowed()
                res[p] = RuntimeError("the words on the page could not be read")
        self.done.emit({p: (str(r) if isinstance(r, Exception) else "") for p, r in res.items()})


Chip = D.Chip


class _FitBody(QWidget):
    """3.20.3: Review's body: it takes the window's height (its parts scroll inside), never the height its wrapped rows
    would like, so the page as a whole never scrolls and the toolbar stays on top."""

    def hasHeightForWidth(self):
        return False


class AssignPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host                           # the main window: review, matrix, workspace, changed(), status()
        self.file = None
        self.pdf = ""
        self.placed = {}
        self.tops = []
        self.canvas = None                         # 4.2.0: the page drawn as it scrolls (pagecanvas)
        self.labels = []
        self.marks = {}                            # 3.18.1: sentence id -> what was captured from it
        self.cx_hist = []                          # 3.18.2: undo for library documents (ctxassign)
        self.target = None
        self.cur = None
        self.split_at, self.split_word, self.split_bar = None, None, None
        self.notes = None
        self._guard = False
        self.conv = set()
        self.conv_err = {}
        self.workers = []
        self.cx = None                             # 2.84.0: the library document open (ctxassign.CtxMode), else None
        self.lib_entries = {}
        self.extract_entries = {}                  # 4.1.0: customer documents not extracted yet: picking one extracts it
        self.fixed_page = True                     # 3.20.3: the page never scrolls as a whole: the toolbar stays on top,
        self.setMinimumSize(320, 320)              # the document, the decide panel, the card and the structure scroll apart
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)       # 3.20.3: the body never asks for the height its
        body = _FitBody(); outer.addWidget(body)                                # wrapped rows would like: the page fits the window
        v = QVBoxLayout(body)
        v.setContentsMargins(6, 6, 6, 6)
        from .adaptive import FlowLayout
        bar = FlowLayout(spacing=6); v.addLayout(bar)         # 3.15.1: the tools wrap onto a second row when narrow
        bar.addWidget(QLabel("Document:"))
        self.files = QComboBox(); self.files.setMinimumWidth(240); self.files.currentTextChanged.connect(self.open_file)
        bar.addWidget(self.files)
        self.queue_lbl = D.label("", "muted", wrap=False); bar.addWidget(self.queue_lbl)       # 2.96.0: the documents as a queue
        self.done_btn = D.button("Mark shredded", None, lambda: self.mark_reviewed(), "Every piece of this document is looked at")
        self.next_btn = D.button("Next document \u203a", None, lambda: self.next_file(), "The next document not shredded yet")
        bar.addWidget(self.done_btn); bar.addWidget(self.next_btn)
        self.sg_btn = D.button("Suggest", "ctx", lambda: self.toggle_suggest(), "Show what each sentence most likely is, "
                               "from rules you can read (not AI). Nothing is decided until you accept it")      # 3.18.0
        self.sg_btn.setCheckable(True)                     # 3.20.3: up front, where it is seen
        bar.addWidget(self.sg_btn)
        self.keys = {}
        # 2.82.0: sentence edits stay by the page; the decisions sit beside the response structure, where they land
        for text, kind, fn, tip in (("Combine  J", None, self.do_combine, "One sentence from the selected ones (they need not be next to each other)"),
                                    ("Split  S", None, self.do_split, "Split the selected sentence before the word you clicked"),
                                    ("Make a sentence  Shift+S", None, lambda: self.do_extract(), "Drag across words inside a sentence, "
                                     "then this: those words become a sentence of their own, ready to assign (3.20.3)")):
            b = D.button(text, kind, fn, tip)
            self.keys[text.split("  ")[0].split()[0]] = b
            bar.addWidget(b)
            b.setVisible(False)          # 3.75.0 (house rule 8): the keys and the sentence's right-click do these; Undo is the frame's
        self.keys["Split"].setEnabled(False)
        self.keys["Make"].setEnabled(False)
        self.keys["Split"].setToolTip("Select a sentence, then click the word the second part starts with: a red line "
                                      "shows the split, and this button (or S) makes it")
        bar.addStretch(1)
        self.cap_btn = D.button("Add missed text", None, lambda: self.toggle_capture(),
                                "Drag a box around text the reader missed: Stationkeeper reads it (the PDF's text, else OCR) "
                                "and adds it as a sentence in its place, ready to assign")
        self.cap_btn.setCheckable(True)
        bar.addWidget(self.cap_btn)
        self.pan_btn = D.button("Pan  H", None, lambda: self.toggle_pan(), "Drag to move the page (or hold Space and drag, "
                                "or drag with the middle button). Ctrl+wheel zooms")
        self.pan_btn.setCheckable(True)
        bar.addWidget(self.pan_btn)
        self.sg_on, self.sg = False, {}
        self.sheet_on, self.sheet = True, None          # 2.96.0: Excel files open in Sheet view
        self.sheet_btn = D.button("Page view", None, lambda: self.toggle_sheet(), "Switch an Excel file between its cells (Sheet "
                                  "view) and its PDF copy (Page view)")
        self.sheet_btn.setVisible(False)
        bar.addWidget(self.sheet_btn)
        self.changes_on = True                      # 2.98.0: what this version changed, outlined on the page
        self.changes_btn = D.button("Hide changes", "ghost", lambda: self.toggle_changes(), "Outline what this version changed "
                                    "against the one before it (amber: changed, green: new)")
        self.changes_btn.setVisible(False)
        bar.addWidget(self.changes_btn)
        fit = QPushButton("Fit width"); fit.clicked.connect(lambda: self.view.fit()); bar.addWidget(fit)
        self.note = D.label("", "muted"); v.addWidget(self.note)
        self.task_slot = QVBoxLayout(); v.addLayout(self.task_slot)     # 4.1.0: the extract's progress (shredpick)
        __import__("skqt.reshredbar", fromlist=["x"]).install(self, bar)    # 4.1.0: N to re-shred (Documents > Changes)
        self.sg_strip = QFrame(); self.sg_strip.setObjectName("sgBar")         # 3.18.0: the suggestions shown, and the score
        self.sg_strip.setStyleSheet("QFrame#sgBar{background:rgba(22,163,74,0.07);border:1px dashed rgba(22,163,74,0.55);border-radius:6px;}")
        sh = QHBoxLayout(self.sg_strip); sh.setContentsMargins(D.SPACE["m"], D.SPACE["xs"], D.SPACE["m"], D.SPACE["xs"])
        sh.setSpacing(D.SPACE["s"])
        self.sg_text = D.label("", "body"); self.sg_text.setTextFormat(Qt.RichText); sh.addWidget(self.sg_text, 1)
        self.sg_clear_btn = D.button("Accept the clear ones", "primary", lambda: self.accept_suggestions(clear_only=True),
                                     "Accept the suggestions the rules are sure of, in this document; the rest stay for you")
        self.sg_all_btn = D.button("Accept all shown", None, lambda: self.accept_suggestions(clear_only=False),
                                   "Accept every suggestion shown in this document")
        self.sg_check_btn = D.button("Select unchecked", "ghost", lambda: self.select_unchecked(),
                                     "The sentences decided from a suggestion that nobody has checked yet")
        self.sg_rules_btn = D.button("Rules...", "ghost", lambda: self.rules_dialog(), "The team's and this effort's suggestion rules")
        for b in (self.sg_clear_btn, self.sg_all_btn, self.sg_check_btn, self.sg_rules_btn):
            sh.addWidget(b)
        self.sg_strip.setVisible(False); v.addWidget(self.sg_strip)
        __import__("skqt.fixtext", fromlist=["x"]).install(self, bar, v)    # 4.2.0: Fix text, a mode inside Shred
        self.bulk = QFrame(); self.bulk.setObjectName("bulkBar")       # 3.0.4: several sentences selected, one action for all
        self.bulk.setStyleSheet("QFrame#bulkBar{background:rgba(37,99,235,0.08);border:1px solid rgba(37,99,235,0.35);border-radius:6px;}")
        bh = QHBoxLayout(self.bulk); bh.setContentsMargins(D.SPACE["m"], D.SPACE["xs"], D.SPACE["m"], D.SPACE["xs"])
        bh.setSpacing(D.SPACE["s"])
        self.bulk_lbl = D.label("", "label", wrap=False); bh.addWidget(self.bulk_lbl)
        self.bulk_info = D.label("", "muted", wrap=False); bh.addWidget(self.bulk_info)
        bh.addStretch(1)
        self.bulk_dec = QComboBox(); self.bulk_dec.setToolTip("One decision for every selected sentence")
        for text, key in BULK_DECISIONS:
            self.bulk_dec.addItem(text, key)
        self.bulk_dec.activated.connect(lambda i: self.bulk_decide(self.bulk_dec.itemData(i)))
        self.bulk_sec = QComboBox(); self.bulk_sec.setToolTip("Every selected sentence in this section: decided ones keep "
                                                              "their decision (requirement, support, the customer's); "
                                                              "undecided ones become requirements; ignored ones stay out")
        self.bulk_sec.activated.connect(lambda i: self.bulk_section(self.bulk_sec.itemData(i)))
        self.bulk_own = QComboBox(); self.bulk_own.setToolTip("One author for every selected requirement and support sentence "
                                                              "(names from the author list)")
        self.bulk_own.activated.connect(lambda i: self.bulk_author(self.bulk_own.itemData(i)))
        for cb in (self.bulk_dec, self.bulk_sec, self.bulk_own):
            cb.setMinimumWidth(170); bh.addWidget(cb)
        self.bulk_clear = D.button("Clear selection", "ghost", lambda: self.view.scene().clearSelection(), "Esc")
        bh.addWidget(self.bulk_clear)
        self.bulk.setVisible(False)
        v.addWidget(self.bulk)
        self.view = PageView()
        self.edge_scroll = __import__("skqt.pagecanvas", fromlist=["x"]).EdgeScroll(self.view)   # 4.2.0: drags run across pages
        self.view.scene().selectionChanged.connect(self.on_select)
        self.view.clicked_word.connect(self.on_word)
        self.view.hover_word.connect(self.on_hover_word)
        self.view.word_drag.connect(lambda i, a, b: self.show_grab(i, a, b, final=False))
        self.view.grabbed.connect(lambda i, a, b: self.show_grab(i, a, b, final=True))
        self.view.span_drag.connect(lambda sp: self.show_span(sp, final=False))       # 3.28.1
        self.view.menu_at.connect(lambda iid, gp: self.sentence_menu(iid).exec(gp))   # 3.29.0
        self.view.span_grabbed.connect(lambda sp: self.show_span(sp, final=True))
        self.grab, self._grab_items, self.grab_multi = None, [], None
        self._split_items, self._hover_item = [], None
        self.view.captured.connect(lambda r: self.capture_area(r))
        right = QSplitter(Qt.Vertical)
        self.card_area = QScrollArea(); self.card_area.setWidgetResizable(True)
        self.card_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.card = QWidget(); self.card_lay = QVBoxLayout(self.card); self.card_lay.setAlignment(Qt.AlignTop)
        self.card_area.viewport().installEventFilter(self)              # wrapped text keeps its height; the card scrolls
        self.card_area.setWidget(self.card)
        sw = QWidget(); sv = QVBoxLayout(sw); sv.setContentsMargins(0, 0, 0, 0)
        dec = QFrame(); dec.setProperty("card", True)                      # 2.82.0: decide; 3.34.1: at the bottom,
        dh = QHBoxLayout(dec); dh.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["s"])   # decide and
        dh.setSpacing(D.SPACE["l"])                                                                          # capture side by side
        dv = QVBoxLayout(); dv.setSpacing(D.SPACE["xs"]); dh.addLayout(dv, 1)
        cv = QVBoxLayout(); cv.setSpacing(D.SPACE["xs"]); dh.addLayout(cv, 1)
        self.target_lbl = D.label("", None); self.target_lbl.setTextFormat(Qt.RichText)
        trow = QHBoxLayout(); trow.setSpacing(D.SPACE["s"]); trow.addWidget(self.target_lbl, 1)
        self.undecided_btn = D.button("Select undecided", "ghost", lambda: self.select_undecided(),   # 3.0.4
                                      "Select every sentence in this document with no decision yet (Ctrl+A selects them all)")
        trow.addWidget(self.undecided_btn, 0, Qt.AlignTop); dv.addLayout(trow)
        self._dv = dv                                       # 3.85.0: the home, the offer and what is left go under it
        # 3.35.0: the target item's own values, the ones the outline matrix shows beside its Section L and M content
        from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox
        self.item_row = QWidget(); ir = QHBoxLayout(self.item_row); ir.setContentsMargins(0, 0, 0, 0); ir.setSpacing(D.SPACE["s"])
        ir.addWidget(D.label("Item", "label", wrap=False))
        ir.addWidget(D.label("Assigned To", "muted", wrap=False))
        self.item_who = QComboBox(); self.item_who.setEditable(True); self.item_who.setMinimumWidth(150)
        self.item_who.setToolTip("Who writes this item (its lead); its contributors stay as they are")
        self.item_who.lineEdit().editingFinished.connect(lambda: self.set_item_value("who"))
        self.item_who.activated.connect(lambda _i: self.set_item_value("who"))
        ir.addWidget(self.item_who, 1)
        ir.addWidget(D.label("Initial Page Allocation", "muted", wrap=False))
        self.item_pages = QDoubleSpinBox(); self.item_pages.setRange(0, 2000); self.item_pages.setSingleStep(PB.STEP)
        self.item_pages.setDecimals(1); self.item_pages.setSpecialValueText("not set")
        self.item_pages.setToolTip("The item's pages, as the team plans them (Pages... sets who set them and whether they count)")
        self.item_pages.editingFinished.connect(lambda: self.set_item_value("pages"))
        ir.addWidget(self.item_pages)
        ir.addWidget(D.label("% Complete", "muted", wrap=False))
        self.item_pct = QSpinBox(); self.item_pct.setRange(-1, 100); self.item_pct.setSuffix("%"); self.item_pct.setSpecialValueText("not set")
        self.item_pct.setSingleStep(5)
        self.item_pct.setToolTip("How far along the item's writing is, as the team judges it")
        self.item_pct.editingFinished.connect(lambda: self.set_item_value("pct"))
        ir.addWidget(self.item_pct)
        dv.addWidget(self.item_row)
        self.legend = D.label("&nbsp;&nbsp;".join(f"<span style='color:{c}'>\u25A0</span> {n}" for n, c in D.LEGEND)
                              + "&nbsp;&nbsp;<span style='color:#94A3B8'>\u25A1</span> Not decided", "muted")   # 3.18.1
        self.legend.setTextFormat(Qt.RichText); self.legend.setWordWrap(True)
        self.legend.setToolTip("The colors on the page. Every decision has its own; a sentence something was captured from "
                               "has the pink outline and what was captured in the margin.")
        dv.addWidget(self.legend)
        self.dec_box = dec
        self.dec_lay = FlowLayout(spacing=D.SPACE["xs"])                   # 3.29.0: the decisions, the team's way (Settings)
        self.dec_grid = QWidget(); self.dec_grid.setLayout(self.dec_lay)
        dv.addWidget(self.dec_grid)
        self.dec_all = QCheckBox("Show every decision")                    # 3.29.0: an effort type can hide some (an RFI)
        self.dec_all.toggled.connect(lambda _on: self.build_decide())
        dv.addWidget(self.dec_all)
        ch = QHBoxLayout(); ch.setSpacing(D.SPACE["s"])
        ch.addWidget(D.label("Capture", "label", wrap=False))
        self.into_target = QCheckBox("Into the target section")                  # 3.29.1: captures go where requirements go
        self.into_target.setToolTip("Each capture goes into the section selected in your structure (the target), as a "
                                    "requirement does. Move it later from the sentence's card, a right-click or the Captured list.")
        self.into_target.setChecked(True)
        self.into_target.toggled.connect(lambda on: self._save_into_target(on))
        ch.addWidget(self.into_target); ch.addStretch(1)
        self.captured_btn = D.button("\u2630  Captured list", "primary", lambda: self.all_excerpts(),     # 3.29.0
                                     "Everything captured in this effort, in one list: by capture, with the words and where "
                                     "they sit; edit, take out, export")
        ch.addWidget(self.captured_btn)
        cv.addLayout(ch)
        self.cap_lay = FlowLayout(spacing=D.SPACE["xs"])                   # 3.29.0: one bar: built-in and your own captures
        capw = QWidget(); capw.setLayout(self.cap_lay); cv.addWidget(capw); cv.addStretch(1)
        from PySide6.QtWidgets import QMenu
        self.more_btn = D.button("More...", "cap", None, "The other captures, your own, + Capture... and Captures of this effort")
        self.more_menu = QMenu(self.more_btn)
        self.more_menu.aboutToShow.connect(lambda: self.fill_more_menu())
        self.more_btn.setMenu(self.more_menu)
        self.cap_keys, self.more_actions, self._dyn_keys = {}, {}, []
        self.bins_btn, self.bins_menu = self.more_btn, self.more_menu       # older names
        cgrid = FlowLayout(spacing=D.SPACE["xs"])                             # 2.84.0: for a library document
        self.ctx_keys = {}
        for k, (text, kind, fn, tip) in enumerate((
                ("Context for section  C", "ctx", lambda: self.do_ctx(), "Context for the target section: shows in the section and in Response Setup"),
                ("For a requirement  F", "ctx", lambda: self.do_for_req(), "Context for a compliance requirement of the target section"),
                ("Make it a requirement  R", "req", lambda: self.do_req(), "Into the matrix as a compliance requirement in the target section"),
                ("Note  N", "cap", lambda: self.do_record("note"), "A note in the effort record, quoting it"),
                ("Question  Q", "cust", lambda: self.do_record("question"), "A question for the customer, quoting it"),
                ("Task  T", "cap", lambda: self.do_record("task"), "A task in the effort record, quoting it"),
                ("Ignore  X", "drop", lambda: self.do_clear(), "Ignore it: its attachments come off; grey on the page. "
                 "Delete takes everything off."))):
            b = D.button(text, kind, fn, tip)
            self.ctx_keys[text.split("  ")[0]] = b
            cgrid.addWidget(b)
        self.ctx_grid = QWidget(); self.ctx_grid.setLayout(cgrid); self.ctx_grid.hide()
        dv.addWidget(self.ctx_grid); dv.addStretch(1)
        self.decide_area = QScrollArea(); self.decide_area.setWidgetResizable(True)    # 3.20.3: decide, at the top, on its own
        self.decide_area.setFrameShape(QFrame.NoFrame); self.decide_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.decide_area.setWidget(dec)
        vrow = QHBoxLayout(); sv.addLayout(vrow)                       # 2.68.0: the volume you are working on
        vrow.addWidget(D.label("Volume", "label", wrap=False))
        self.volume = QComboBox(); self.volume.setMinimumWidth(120)
        self.volume.activated.connect(lambda _i: self.pick_volume(self.volume.currentData()))
        vrow.addWidget(self.volume, 1)
        vrow.addWidget(D.button("+ Volume", None, lambda: self.new_volume(), "A new volume at the end of the structure"))
        vrow.addWidget(D.button("Rename", None, lambda: self.rename_volume(), "Rename the volume you are working in (its "  # 3.28.1
                                "number stays; everything in it follows)"))
        self.vol_style = QComboBox(); self.vol_style.setToolTip("How the volumes are numbered: I, II, III; 1, 2, 3; or A, B, C")
        for k, t in O.VOLUME_STYLES:
            self.vol_style.addItem(t, k)
        self.vol_style.activated.connect(lambda _i: self.set_volume_style(self.vol_style.currentData()))
        vrow.addWidget(self.vol_style)
        self.tree = StructTree(); self.tree.setHeaderLabels(["Your response structure (click a section: the target)", "Req.", "Ctx", "Pages", "Cap."])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)                  # 3.29.0: right-click a section for its menu
        self.tree.customContextMenuRequested.connect(
            lambda pos: (lambda i: self.structure_menu(i.data(0, Qt.UserRole)).exec(self.tree.viewport().mapToGlobal(pos))
                         if i is not None and i.data(0, Qt.UserRole) else None)(self.tree.itemAt(pos)))
        self.tree.setColumnWidth(0, 330); self.tree.setColumnWidth(1, 44); self.tree.setColumnWidth(2, 40)
        self.tree.headerItem().setToolTip(3, "Pages for the section: the RFP's limit or the team's guideline. Double-click to set.")
        self.tree.headerItem().setToolTip(4, "Captures placed in the section (3.29.1)")
        self.tree.setColumnWidth(3, 70)
        self.tree.itemClicked.connect(lambda i, _c: self.set_target(i.data(0, Qt.UserRole)) if i.data(0, Qt.UserRole) else None)
        self.tree.itemDoubleClicked.connect(lambda i, c: self.section_pages(i.data(0, Qt.UserRole)) if c == 3
                                            else self.rename_section(i.data(0, Qt.UserRole)))
        sv.addWidget(self.tree)
        srow = FlowLayout(spacing=4); srw = QWidget(); srw.setLayout(srow); sv.addWidget(srw)   # 3.20.3: wraps
        for text, fn, tip in (("+ Heading", lambda: self.new_section(sub=False), "A section at the level of the target (after it), or a first section"),
                              ("+ Subheading", lambda: self.new_section(sub=True), "A section under the target, one level down"),
                              ("From sentence", lambda: self.section_from_sentence(), "A section under the target, named with the selected sentence"),
                              ("Copy RFP section", lambda: self.copy_rfp_section(),
                               "The RFP section the selected sentence is in (and its subsections, if you want) under the "
                               "target, titled as the RFP titles it; its requirements with no section yet go into it")):
            b = D.button(text, None, fn, tip)
            b.setVisible(text == "+ Heading")      # 3.75.0: the rest are on the section's right-click and in Setup
            srow.addWidget(b)
        from PySide6.QtWidgets import QMenu                           # 3.19.0: cover, title page, front matter, appendices
        self.parts_btn = D.button("Parts", None, None, "Cover, title page, front matter, appendices and back cover: add "
                                  "one, move the target to another part, and each part's rules and page limit")
        pm = QMenu(self.parts_btn)
        self.parts_actions = {}
        for key, text in (("cover", "Add a cover"), ("title", "Add a title page"), ("front", "Add a front matter item..."),
                          ("appendix", "Add an appendix..."), ("back", "Add a back cover")):
            a = pm.addAction(text); a.triggered.connect(lambda _=False, k=key: self.add_part(k))
            self.parts_actions[key] = a
        pm.addSeparator()
        a = pm.addAction("Move the target to a part..."); a.triggered.connect(lambda: self.move_to_part())
        self.parts_actions["move"] = a
        a = pm.addAction("Part rules and page limits..."); a.triggered.connect(lambda: self.parts_dialog())
        self.parts_actions["rules"] = a
        self.parts_btn.setMenu(pm)
        srow.addWidget(self.parts_btn)
        self.parts_btn.setVisible(False)           # 3.75.0: Parts is on the section's right-click
        srow.addStretch(1)
        row = FlowLayout(spacing=4); rww = QWidget(); rww.setLayout(row); sv.addWidget(rww)
        for text, fn, tip in (("Rename", lambda: self.rename_section(self.target), "Rename the target (or double-click it, or right-click it)"),
                              ("Pages...", lambda: self.section_pages(self.target),                       # 3.18.2
                               "The target's page length: the RFP's limit or the team's guideline (or double-click Pages)"),
                              ("\u2191", lambda: self.outline_op(O.move, -1), "Up"), ("\u2193", lambda: self.outline_op(O.move, 1), "Down"),
                              ("\u2192", lambda: self.outline_op(O.indent), "One level down (under the section above)"),
                              ("\u2190", lambda: self.outline_op(O.outdent), "One level up"),
                              ("Delete", lambda: self.delete_section(), "Take the target out; its sentences go to the section above")):
            b = D.button(text, "ghost" if text != "Delete" else "danger", fn, tip)
            if len(text) == 1:
                b.setFixedWidth(34)
            row.addWidget(b)
            b.setVisible(False)                    # 3.75.0: the section's right-click does these (house rule 8)
        row.addStretch(1)
        self.start_btn = D.button("Start from...", None, lambda: self.start_from(),     # 3.16.0
                                  "Start or replace the structure: what the RFP prescribes, its headings, its outline, or a "
                                  "Word outline (the Structure tab). Volumes, people and page budget are on the Effort Dashboard.")
        row.addWidget(self.start_btn)
        self.active_volume = ""
        self.tree.setMinimumHeight(220)
        from .sectionpanel import SectionPanel            # 3.83.0: the shared section panel, for the target section
        self.section_panel = SectionPanel(self.host, lambda: self.M if self.R is not None else None,
                                          lambda: R_.Record(self.host.ws.root) if self.host.ws is not None else None)
        sv.addWidget(self.section_panel)
        self.side_area = QScrollArea(); self.side_area.setWidgetResizable(True)      # 3.18.2: the decide panel and the
        self.side_area.setFrameShape(QFrame.NoFrame); self.side_area.setWidget(sw)    # structure scroll on their own
        self.side_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        from .reviewviews import ReviewViews               # 3.90.0: Our structure, L to M and Coverage beside the page
        self.views = ReviewViews(self, self.side_area)
        right.addWidget(self.card_area); right.addWidget(self.views)   # 3.34.1: the decide tools are at the bottom
        right.setSizes([380, 520]); right.setChildrenCollapsible(False)
        self.right = right
        # 3.28.0: topics: Sort mode (keys 1 to 9), the topics, show one, and how far each has come
        pagew = QWidget(); pv = QVBoxLayout(pagew); pv.setContentsMargins(0, 0, 0, 0); pv.setSpacing(D.SPACE["xs"])
        self.topic_bar = QWidget(); tb = FlowLayout(spacing=4); self.topic_bar.setLayout(tb)
        self.sort_btn = D.button("Sort mode", None, lambda: self.toggle_sort(), "Sort by topic: keys 1 to 9 put the selected "
                                 "sentences in the first nine topics (again takes it off). Decisions stay on their keys.")
        self.sort_btn.setCheckable(True)
        tb.addWidget(self.sort_btn)
        self.topic_chips = QWidget(); self.topic_chips_lay = FlowLayout(spacing=4); self.topic_chips.setLayout(self.topic_chips_lay)
        tb.addWidget(self.topic_chips)
        # 3.75.0: + Topic is the first item of Topics
        self.topics_btn = D.button("Topics", None, None, "Topics from the RFP's headings or the library's tags; rename, color, "
                                   "map to response sections, order and take out")
        from PySide6.QtWidgets import QMenu
        tm = QMenu(self.topics_btn)
        tm.addAction("+ Topic...", lambda: self.new_topic())
        tm.addAction("Topics from the RFP's headings", lambda: self.topics_from_headings())
        tm.addAction("Topics from the library's tags", lambda: self.topics_from_tags())
        tm.addAction("Topics of this effort...", lambda: self.manage_topics())
        tm.addAction("Make a section for each topic", lambda: self.sections_from_topics())
        self.topics_btn.setMenu(tm)
        tb.addWidget(self.topics_btn)
        tb.addWidget(D.label("Show", "label", wrap=False))
        self.topic_show = QComboBox(); self.topic_show.setMinimumWidth(180)
        self.topic_show.currentIndexChanged.connect(lambda _i: (self.restyle(), self.show_coverage()))
        tb.addWidget(self.topic_show)
        self.topic_cov = D.label("", "muted", wrap=False); tb.addWidget(self.topic_cov)
        pv.addWidget(self.topic_bar); pv.addWidget(self.view, 1)
        self.sort_on = False
        self.rfi = False
        self.topic_labels = []
        split = QSplitter(Qt.Horizontal); split.addWidget(pagew); split.addWidget(right); split.setSizes([1100, 470])
        from .reviewplace import Placer                     # 3.85.0: their text and our structure, joined by lines
        self._offer_off = False
        self.placer = Placer(self, split, self._dv)
        # 3.34.1: the decisions and captures, permanently at the bottom across the page, so the sentence's details and
        # the structure on the right have the room; drag the line above them to give them more or less
        self.bottom_split = QSplitter(Qt.Vertical)
        self.bottom_split.addWidget(split); self.bottom_split.addWidget(self.decide_area)
        self.bottom_split.setChildrenCollapsible(False)
        self.bottom_split.setStretchFactor(0, 1); self.bottom_split.setStretchFactor(1, 0)
        self.decide_area.setMinimumHeight(96)
        self.bottom_split.setSizes([760, 170])
        v.addWidget(self.bottom_split, 1)
        self.notes_timer = QTimer(self, singleShot=True, interval=700, timeout=self.save_notes)
        for key, fn in (("Delete", self.do_undecide), ("J", self.do_combine), ("S", self.do_split),
                        ("Shift+S", lambda: self.do_extract()),
                        ("B", lambda: self.more_btn.showMenu() if self.cx is None else None),
                        ("F", lambda: self.do_for_req()), ("N", lambda: self.do_record("note")),
                        ("Q", lambda: self.do_record("question")), ("T", lambda: self.do_record("task")),
                        ("Ctrl+A", lambda: self.select_all()), ("H", lambda: self.toggle_pan()),
                        ("Return", lambda: self.accept_suggestions(rows=self.selected())),
                        ("Escape", lambda: self.toggle_capture(False) if self.view.capturing else
                         (self.clear_split() if self.split_at is not None else self.view.scene().clearSelection()))):
            QShortcut(QKeySequence(key), self.view, activated=fn)
        for i in range(9):                                       # 3.21.0: the effort's own bins, in order
            QShortcut(QKeySequence(f"Alt+{i + 1}"), self.view, activated=lambda n=i: self.do_custom_bin(n))
            QShortcut(QKeySequence(str(i + 1)), self.view, activated=lambda n=i: self.tag_topic(n) if self.sort_on else None)
        QShortcut(QKeySequence("Ctrl+T"), self.view, activated=lambda: self.toggle_sort())
        self.apply_items()                                       # 3.29.0: decisions and captures from Settings
        self.show_card([])

    # ------------------------------------------------------------ the review
    @property
    def R(self):
        return self.host.review

    @property
    def M(self):
        return self.host.review.M if self.host.review else None

    def load(self):
        """The review changed (opened, read): fill the file list and the structure."""
        import suggestrules as SR
        import topics as TP                                                    # 3.28.0
        if self.R is None:                    # 3.34.1: an effort with no matrix yet shows nothing of the last effort's
            self.forget()
        rfi = TP.is_rfi(self.host.ws)
        if rfi and not self.rfi and self.R is not None:                       # an RFI effort opens in Sort mode
            self.sort_on = True; self.sort_btn.setChecked(True)
        self.rfi = rfi
        self.apply_items()                                                     # 3.29.0: this effort type's decisions
        self.fill_topics()
        self.sg = SR.store(self.host.ws) if self.R is not None else {}          # 3.18.0: this effort's suggestions
        self.load_marks()
        if self.sg_on and self.R is not None:
            self.run_suggest()
        elif self.sg_on:
            self.sg_on = False; self.sg_btn.setChecked(False); self.sg_strip.setVisible(False)
        self.fill_file_list()
        self.cx = None
        self.fill_tree()
        if self.R and self.R.files():
            self.open_file(self.R.files()[0])
        else:
            self.view.scene().clear()
            self.canvas = None                          # 4.2.0: no pages drawn on scroll
            self.view.boxes = {}

    def forget(self):
        """3.34.1: nothing of the effort open before: its page, its sentences' boxes, the card, the queue."""
        self.cx = None
        self.labels = []
        self.view.scene().clear()
        self.canvas = None                          # 4.2.0: no pages drawn on scroll
        self.view.boxes = {}
        self.file, self.pdf = None, ""
        self.show_card([])
        self.show_queue()

    # ------------------------------------------------------------ 2.96.0 the customer documents as a queue
    def reviewed(self):
        return dict(self.host.ws.get("assign_reviewed", {}) or {}) if self.host.ws is not None else {}

    def show_queue(self):
        __import__("skqt.reshredbar", fromlist=["x"]).refresh(self)         # 4.1.0
        __import__("skqt.fixtext", fromlist=["x"]).refresh(self)            # 4.2.0
        files = self.R.files() if self.R else []
        if not files or self.cx is not None or self.file not in files:
            self.queue_lbl.setText(""); self.done_btn.setVisible(False); self.next_btn.setVisible(False)
            return
        done = self.reviewed()
        left = [f for f in files if f not in done]
        here = self.file in done
        self.queue_lbl.setText(f"Document {files.index(self.file) + 1} of {len(files)}  ·  "
                               + (f"{len(left)} not shredded yet" if left else "all shredded"))
        self.done_btn.setVisible(True); self.next_btn.setVisible(bool([f for f in left if f != self.file]))
        self.done_btn.setText("Shredded \u2713" if here else "Mark shredded")
        self.done_btn.setToolTip(f"Marked shredded {done[self.file]}. Click to take the mark off." if here else
                                 "Every piece of this document is looked at")

    def mark_reviewed(self, on=None):
        if self.host.ws is None or not self.file:
            return False
        done = self.reviewed()
        on = (self.file not in done) if on is None else on
        if on:
            import datetime as _dt
            done[self.file] = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            done.pop(self.file, None)
        self.host.ws.set("assign_reviewed", done)
        if on:
            diag.activity("assign_file_reviewed")
        else:
            diag.activity("assign_file_unreviewed")
        self.show_queue()
        return on

    def next_file(self):
        files = self.R.files() if self.R else []
        done = self.reviewed()
        if not files:
            return None
        k = files.index(self.file) if self.file in files else -1
        order = files[k + 1:] + files[:k + 1]
        nxt = next((f for f in order if f not in done and f != self.file), None)
        if nxt:
            self.files.setCurrentText(nxt)
        return nxt

    def fill_file_list(self):
        """The matrix's files, then (2.84.0) the library documents to read beside the structure."""
        from . import ctxassign as CXA
        from . import shredpick as SP
        self.files.blockSignals(True)
        self.files.clear()
        self.lib_entries = {}
        if self.R:
            self.files.addItems(self.R.files())
        SP.fill(self)                              # 4.1.0: the customer documents to extract, picked like the rest
        if self.R:
            try:
                ents = CXA.library_entries(self)
            except Exception:
                diag.swallowed()
                ents = []
            if ents:
                self.files.insertSeparator(self.files.count())
                for lab, did in ents:
                    self.files.addItem(lab)
                    self.lib_entries[lab] = did
        self.files.blockSignals(False)

    def load_files_keep(self):
        cur = self.files.currentText()
        self.fill_file_list()
        self.files.blockSignals(True)
        if cur:
            self.files.setCurrentText(cur)
        self.files.blockSignals(False)

    def _ctx_counts(self):
        try:
            import ctxdocs as CX
            return CX.Store(self.host.ws.root).load().section_counts() if self.host.ws is not None else {}
        except Exception:
            diag.swallowed()
            return {}

    def set_mode(self):
        """2.84.0: the decision buttons for the matrix, or for a library document."""
        lib = self.cx is not None
        self.dec_grid.setVisible(not lib); self.ctx_grid.setVisible(lib)
        self.keys["Combine"].setEnabled(not lib)
        self.keys["Split"].setEnabled(not lib and self.split_at is not None)     # 2.93.0: ready once a split point is set
        self.show_target()

    def copies_dir(self):
        ws = self.host.ws
        return ws.p("page copies") if ws is not None else ""

    def pdf_of(self, f):
        """(pdf, why not)."""
        if self.cx is not None:
            return self.cx.pdf()
        path = self.M.path_of(f)
        if not path:
            return "", f"{f} is not on this PC"
        import ocrpdf                               # 2.96.0: pictures and scanned pages, with their words laid over them
        folder = self.copies_dir()
        if ocrpdf.needs_copy(path):
            c = ocrpdf.copy_path(path, folder) if folder else ""
            if c and os.path.isfile(c):
                return c, ""
            if path.lower().endswith(".pdf") and not folder:
                return path, ""
            if path in self.conv_err:
                return (path, "") if path.lower().endswith(".pdf") else ("", self.conv_err[path])
            self.make_copies()
            return "", "Reading the words on the page so they can be selected (once per file)"
        if path.lower().endswith(".pdf"):
            return path, ""
        if not OP.kind(path):
            return "", "Page view shows PDF, Word, Excel, PowerPoint files and pictures"
        c = OP.copy_path(path, folder) if folder else ""
        if c and os.path.isfile(c):
            return c, ""
        if path in self.conv_err:
            return "", self.conv_err[path]
        if not OP.available():
            return "", "the PDF copy needs Microsoft Office on this PC"
        self.make_copies()
        return "", f"Microsoft {OP.kind(path).capitalize()} is making a PDF copy (once per file; about a minute)"

    def make_copies(self):
        import ocrpdf
        paths = [p for p in (self.M.path_of(f) for f in self.R.files()) if p and (OP.kind(p) or ocrpdf.needs_copy(p)) and p not in self.conv]
        if not paths:
            return
        self.conv |= set(paths)
        w = CopyWorker(paths, self.copies_dir())
        w.done.connect(self.copies_done)
        self.workers.append(w)
        diag.activity("page_copies_started", files=len(paths))
        w.start()

    def copies_done(self, res):
        self.conv_err.update({p: e for p, e in res.items() if e})
        diag.activity("page_copies_done", files=sum(1 for e in res.values() if not e), errors=sum(1 for e in res.values() if e))
        if self.file:
            self.open_file(self.file)

    def open_file(self, f):
        if f in self.extract_entries:              # 4.1.0: picked a document not extracted yet: extract it now
            from . import shredpick as SP
            return SP.extract(self, self.extract_entries[f])
        if not f or self.R is None:
            return
        if f in self.lib_entries:                  # 2.84.0: a library document beside the structure
            from . import ctxassign as CXA
            try:
                self.cx = CXA.CtxMode(self, self.lib_entries[f])
            except Exception:
                diag.swallowed()
                self.cx = None
                self.host.status("That library document could not be opened.")
                return
            diag.activity("library_document_opened_in_assign")
        else:
            self.cx = None
        self.set_mode()
        self.file = f
        self.sheet = None
        self.show_queue()
        xl = self.M.path_of(f) if self.cx is None else ""
        if xl and xl.lower().endswith((".xlsx", ".xlsm")) and self.sheet_on and os.path.isfile(xl):   # 2.96.0: Sheet view
            self.sheet_btn.setVisible(True)
            return self.draw_sheet(xl)
        self.sheet_btn.setVisible(bool(xl and xl.lower().endswith((".xlsx", ".xlsm"))))
        self.pdf, why = self.pdf_of(f)
        sc = self.view.scene()
        self.view.boxes, self.view.words, self.labels, self.tops = {}, {}, [], []
        self._guard = True                          # clearing the page deselects: not a new selection
        sc.clear()
        self._guard = False
        if not self.pdf:
            t = sc.addText(f"{f}: {why}.")
            t.setDefaultTextColor(QColor("#334155"))
            self.note.setText("")
            return
        from .pagecanvas import Canvas                # 4.2.0: every page placed at once, drawn as it scrolls into view
        self.canvas = Canvas(self, self.pdf, SCALE, MARGIN, GAP)
        self.tops = self.canvas.lay_out(sc)
        self.canvas.ensure([0])
        self.build_boxes()
        self.note.setText("Click a sentence; Ctrl+click adds one (even far apart); drag a box around several. Space and drag, or a middle-button drag, moves the page. Ctrl+wheel zooms.")
        self.mark_changes()                         # 2.98.0: what this version changed, outlined on the page
        QTimer.singleShot(0, self.view.fit)
        QTimer.singleShot(0, lambda: self.canvas.ensure() if getattr(self, "canvas", None) is not None else None)

    # ------------------------------------------------------------ 2.98.0 what this version changed, on the page
    def mark_changes(self):
        """Outline each sentence the open version changed (amber, dashed) or added (green) against the version before
        it, with a tag in the margin. The card then shows what it was, and Show the old page shows it there."""
        import whatchanged as WC
        self.changes, self.change_of = None, {}
        self.changes_btn.setVisible(False)
        if self.cx is not None or not self.file or self.host.ws is None:
            return 0
        try:
            import docversions as DV
            m = WC.marks(DV.Library(self.host.ws.p("documents")).load(), self.file)
        except Exception:
            diag.swallowed()
            return 0
        self.changes = m
        self.changes_btn.setVisible(bool(m))
        if not m or not self.changes_on:
            return 0
        sc = self.view.scene()
        small = QFont(); small.setPointSizeF(6.5); small.setBold(True)
        for it in self.R.rows_of(self.file):
            box = self.view.boxes.get(it["id"])
            ch = WC.mark_of(m, it.get("text", "")) if box is not None else None
            if not ch:
                continue
            tone = QColor("#D97706" if ch["kind"] == "changed" else "#16A34A")
            frame = QGraphicsPathItem(box.path())
            pen = QPen(tone); pen.setWidthF(1.8); pen.setStyle(Qt.DashLine); pen.setCosmetic(True)
            frame.setPen(pen); frame.setBrush(Qt.NoBrush); frame.setZValue(box.zValue() + 0.5)
            frame.setAcceptedMouseButtons(Qt.NoButton); frame.setAcceptHoverEvents(False)
            sc.addItem(frame)
            tag = sc.addSimpleText("CHANGED" if ch["kind"] == "changed" else "NEW", small)
            tag.setBrush(tone); tag.setPos(MARGIN - 52, box.boundingRect().top()); tag.setAcceptedMouseButtons(Qt.NoButton)
            self.change_of[it["id"]] = ch
        n = len(self.change_of)
        if n:
            self.note.setText(f"{m['to'].get('label', '')} of {m['doc'].get('name', '')}: {n} sentence(s) changed or new since "
                              f"{m['from'].get('label', '')}, outlined on the page (amber: changed, green: new). Click one to see "
                              "what it was.")
            diag.activity("assign_changes_marked", n=n)
        return n

    def toggle_changes(self):
        self.changes_on = not self.changes_on
        self.changes_btn.setText("Hide changes" if self.changes_on else "Show changes")
        diag.activity("assign_changes_toggled")
        if self.file:
            self.open_file(self.file)

    def old_page(self, iid, run=True):
        """The previous version's page with the old sentence highlighted. run=False (tests): the dialog, not shown."""
        import whatchanged as WC
        ch = self.change_of.get(iid)
        m = self.changes
        if not ch or not m or not ch.get("old"):
            return None
        import docversions as DV
        lib = DV.Library(self.host.ws.p("documents")).load()
        va = m["from"]
        path = lib.path_of(va)
        pdf = ""
        if path and path.lower().endswith(".pdf") and os.path.isfile(path):
            pdf = path
        elif path and os.path.isfile(path):
            c = OP.copy_path(path, self.copies_dir()) if self.copies_dir() else ""
            if c and os.path.isfile(c):
                pdf = c
            elif OP.available():
                try:
                    pdf = OP.make(path, self.copies_dir())
                except Exception:
                    diag.swallowed()
        if not pdf:
            self.host.status(f"{va.get('file', 'The old version')} needs its PDF copy (Microsoft Office) or is not on this PC.")
            return None
        try:
            found = WC.find_on_pages(pdf, ch["old"])
        except Exception:
            diag.swallowed()
            found = None
        d = OldPageDialog(self, pdf, found, f"{m['doc'].get('name', '')}: {va.get('label', '')}", ch["old"])
        diag.activity("assign_old_page_shown")
        if run:
            d.exec()
        return d

    # ------------------------------------------------------------ 2.96.0 Sheet view (an Excel workbook as its cells)
    def sheet_font(self):
        f = QFont("Consolas"); f.setStyleHint(QFont.Monospace); f.setPointSizeF(8.5)
        from PySide6.QtGui import QFontMetricsF
        fm = QFontMetricsF(f)
        return f, fm.horizontalAdvance("M"), fm.height() * 1.08

    def draw_sheet(self, path):
        import sheetview as SV
        sc = self.view.scene()
        self.view.boxes, self.view.words, self.labels, self.tops = {}, {}, [], []
        self._guard = True
        sc.clear()
        self.canvas = None                          # 4.2.0: no pages drawn on scroll
        self._guard = False
        self.pdf = ""
        try:
            sheets = SV.read(path)
        except Exception:
            diag.swallowed()
            t = sc.addText(f"{self.file}: the workbook could not be read; Page view shows its PDF copy.")
            t.setDefaultTextColor(QColor("#334155"))
            return
        font, cw, lh = self.sheet_font()
        cells, labels, _h = SV.layout(sheets, cw, lh)
        grid = QPen(QColor("#CBD5E1")); grid.setCosmetic(True); grid.setWidthF(0.6)
        ink, muted = QColor("#0F172A"), QColor("#64748B")
        for c in cells:
            x, y, w, h = c["rect"]
            r = sc.addRect(QRectF(x + SHEET_X, y, w, h), grid, QBrush(QColor("#FFFFFF"))); r.setZValue(-1)
            for i, (_s, line) in enumerate(c["lines"]):
                if line:
                    t = sc.addSimpleText(line, font); t.setBrush(ink); t.setPos(x + SHEET_X + 4, y + 4 + i * lh)
        for text, x, y, kind in labels:
            t = sc.addSimpleText(text, font if kind != "sheet" else QFont(font.family(), 11, QFont.Bold))
            t.setBrush(muted if kind != "sheet" else ink)
            t.setPos(x + SHEET_X - (0 if kind != "row" else 0), y)
        self.sheet = {"path": path, "cells": cells, "cw": cw, "lh": lh}
        self.build_boxes()
        self.note.setText("Sheet view: each cell as it is in the workbook. Click a sentence in a cell; Ctrl+click adds one; "
                          "Page view (beside File) shows the PDF copy instead.")
        QTimer.singleShot(0, self.view.fit)

    def toggle_sheet(self):
        self.sheet_on = not self.sheet_on
        self.sheet_btn.setText("Page view" if self.sheet_on else "Sheet view")
        diag.activity("assign_sheet_view_toggled")
        if self.file:
            self.open_file(self.file)

    def build_sheet_boxes(self):
        import sheetview as SV
        sc = self.view.scene()
        rows = self.R.rows_of(self.file)
        S = self.sheet
        found = SV.match(rows, S["cells"])
        self.placed = {}
        for it in rows:
            if it["id"] not in found:
                continue
            k, start = found[it["id"]]
            words = SV.word_rects(S["cells"][k], it.get("text", ""), start, S["cw"], S["lh"])
            if not words:
                continue
            rects = [(l + SHEET_X, t, r + SHEET_X, b) for l, t, r, b in SV.sentence_rects(words)]
            box = SentenceBox(it["id"], rects)
            sc.addItem(box)
            self.view.boxes[it["id"]] = box
            self.view.words[it["id"]] = [QRectF(x + SHEET_X, y, w, h) for x, y, w, h in words]
        self.restyle()

    def build_boxes(self):
        sc = self.view.scene()
        if getattr(self, "sheet", None):                  # 2.96.0
            old, self.view.boxes, self.view.words = self.view.boxes, {}, {}
            self._guard = True
            for b in old.values():
                sc.removeItem(b)
            self._guard = False
            return self.build_sheet_boxes()
        old, self.view.boxes, self.view.words = self.view.boxes, {}, {}
        self._guard = True
        for b in old.values():
            sc.removeItem(b)
        self._guard = False
        rows = self.cx.rows if self.cx is not None else self.R.rows_of(self.file)
        self._area_ids = set()
        try:
            self.placed = PS.place_all(self.pdf, rows)
        except Exception:
            diag.swallowed()
            self.placed = {}
        heads = [] if self.cx is not None else [x for x in self.M.headings if x.get("file") in ("", None, self.file)]
        items = [dict(it, place=self.placed[it["id"]][0], lead_place=self.placed[it["id"]][1]) for it in rows if it["id"] in self.placed]
        rects = {}
        for n in range(1, len(self.tops) + 1):
            try:
                m = PS.place_map(self.pdf, n, items, heads)
            except Exception:
                diag.swallowed()
                continue
            y0 = self.tops[n - 1]
            for x in m["items"]:
                rects.setdefault(x["id"], []).extend((l + MARGIN, t + y0, r + MARGIN, b + y0) for l, t, r, b in x["rects"])
                self.view.words.setdefault(x["id"], []).extend(QRectF(l + MARGIN, t + y0, r - l, b - t) for l, t, r, b in x["words"])
            for l, t, r, b in m["headings"]:
                pen = QPen(QColor("#475569")); pen.setWidthF(0.6); pen.setCosmetic(True)
                sc.addRect(QRectF(l + MARGIN - 1, t + y0 - 1, r - l + 2, b - t + 2), pen)
        for it in ([] if self.cx is not None else rows):    # 3.19.0: text added from an area its words could not be found
            if not it.get("area"):                           # in (a scanned page, wording fixed, header or footer band):
                continue                                    # its box is the area it was read from, on top
            ar = parse_area(it["area"])
            if it["id"] in rects:                           # 3.29.0: found by its words, but somewhere else: the area wins
                if not ar or not (1 <= ar[0] <= len(self.tops)):
                    continue
                y0 = self.tops[ar[0] - 1]
                zone = QRectF(ar[1] + MARGIN - 2, ar[2] + y0 - 2, ar[3] - ar[1] + 4, ar[4] - ar[2] + 4)
                if any(zone.intersects(QRectF(l, t, r - l, b - t)) for l, t, r, b in rects[it["id"]]):
                    continue
                rects.pop(it["id"], None); self.view.words.pop(it["id"], None)
            if ar and 1 <= ar[0] <= len(self.tops):
                y0 = self.tops[ar[0] - 1]
                l, t, r, b = ar[1:]
                rects[it["id"]] = [(l + MARGIN, t + y0, r + MARGIN, b + y0)]
                self._area_ids.add(it["id"])
        for iid, rs in rects.items():
            box = SentenceBox(iid, rs)
            if iid in self._area_ids:
                box.setZValue(2)                            # above a heading's outline or a wider box, so it always selects
            sc.addItem(box)
            self.view.boxes[iid] = box
        self.view.order = [it["id"] for it in rows if it["id"] in self.view.boxes]     # 3.28.1: reading order for spans
        self.restyle()
        if self.cx is None:
            self.refresh_bulk(self.selected())                     # 3.29.0: the selection bar is there from the start

    # ------------------------------------------------------------ drawing decisions
    def restyle(self):
        if self.cx is not None:
            return self.cx.restyle()
        if self.R is None:                                       # 3.34.1: no matrix (a new effort): nothing to color
            return None
        sc = self.view.scene()
        for lab in self.labels:
            sc.removeItem(lab)
        self.labels = []
        import topics as TP                                          # 3.28.0: topics on the right, Show one topic
        trec = self._trec() if hasattr(self, "topic_show") else None
        tlist = TP.topics(trec) if trec is not None else []
        tnum = {t["id"]: n for n, t in enumerate(tlist)}
        tags = trec.data.get("topic_tags", {}) if trec is not None else {}
        want = self.topic_show.currentData() if hasattr(self, "topic_show") else ""
        for iid, box in self.view.boxes.items():
            ids = tags.get(iid) or []
            box.setOpacity(1.0 if (not want or (want == "-" and not ids) or (want not in ("", "-") and want in ids)) else 0.18)
            if ids and tlist:
                r = box.boundingRect()
                lab = QGraphicsSimpleTextItem(" ".join(f"{tnum[x] + 1}" if tnum.get(x, 99) < 9 else "+" for x in ids if x in tnum))
                lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
                first = next((t for t in tlist if t["id"] in ids), None)
                lab.setBrush(QColor(first["color"] if first else "#4338CA"))
                lab.setPos(r.right() + 4, r.top())
                lab.setToolTip(", ".join(t["name"] for t in tlist if t["id"] in ids))
                sc.addItem(lab)
                self.labels.append(lab)
        last_y = -100.0
        for iid, box in sorted(self.view.boxes.items(), key=lambda kv: kv[1].boundingRect().top()):
            it = self.R.item(iid)
            if it is None:
                continue
            dec = it.get("decision", "")
            if dec == "Drop" and it.get("type") == "Heading":      # an RFP heading: not a sentence to answer
                dec = "Heading"
            rec = self.sg.get(iid) if self.sg_on else None          # 3.18.0: a suggestion still waiting shows on the page
            box.sg = rec["cat"] if rec and rec.get("cat") and rec.get("state") == "shown" and not dec else ""
            box.lm = (it.get("lm") or "" if dec == "Keep" else _first_piece(it) if _first_piece(it) in D.PAGE_PIECE else "")   # 4.1.0
            kinds = self.marks.get(iid) or []
            box.mark = bool(kinds)
            box.style(dec if dec in D.PAGE_DEC else "", iid == self.cur)
            tag = {"rule": "RULE", "date": "DATE"}.get(box.lm) or D.decision(dec)[2]      # 4.1.0: a Rule or a Date says so
            if kinds:                                               # 3.18.1: what was captured from it, in the margin
                y = max(box.boundingRect().top(), last_y + 11)
                last_y = y
                lab = QGraphicsSimpleTextItem(PM.text(kinds, getattr(self, "bin_names", {})))
                lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
                lab.setBrush(QColor(D.CAPTURE_COLOR))
                lab.setPos(MARGIN - 8 - lab.boundingRect().width(), y)
                sc.addItem(lab)
                self.labels.append(lab)
            if not tag and box.sg:
                y = max(box.boundingRect().top(), last_y + 11)
                last_y = y
                lab = QGraphicsSimpleTextItem(f"{box.sg}?")
                f = QFont("Segoe UI", 7); f.setItalic(True); lab.setFont(f)
                lab.setBrush(QColor(D.page_color(SG_DEC.get(box.sg, ""), SG_LM.get(box.sg, ""))))
                lab.setPos(MARGIN - 8 - lab.boundingRect().width(), y)
                sc.addItem(lab)
                self.labels.append(lab)
                continue
            if not tag:
                continue
            y = max(box.boundingRect().top(), last_y + (9 if kinds else 11))
            last_y = y
            hosts = C.cf_ids(it.get("context_for", "")) if dec == "Context" else []
            txt = f"{tag} {', '.join(hosts[:2])}" if hosts else f"{tag} {iid}"
            if dec == "Keep":                                           # 2.68.0: L or M and its volumes in the margin
                lmv = it.get("lm") or ""
                vols = [v.split(" ")[1] if v.lower().startswith("volume ") and len(v.split(" ")) > 1 else v[:6] for v in O.volumes_of_item(self.M, it)]
                txt = " ".join(x for x in (tag, lmv, iid, ("V " + "+".join(vols)) if vols else "") if x)
            lab = QGraphicsSimpleTextItem(txt)
            lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
            lab.setBrush(QColor(D.page_color(dec, box.lm or it.get("lm") or "")))
            lab.setPos(MARGIN - 8 - lab.boundingRect().width(), y)
            sc.addItem(lab)
            self.labels.append(lab)
        from . import amendflags as AF                             # 3.89.0 decision 6: changed by an amendment
        AF.mark_page(self)

    def selected(self):
        if self.R is None:
            return []
        if self.cx is not None:
            return self.cx.selected()
        ids = [b.iid for b in self.view.scene().selectedItems() if isinstance(b, SentenceBox)]
        order = {it["id"]: k for k, it in enumerate(self.M.items)}
        return [x for x in (self.R.item(i) for i in sorted(ids, key=lambda i: order.get(i, 0))) if x]

    def on_select(self):
        if self._guard or self.R is None:
            return
        if self.cx is not None:
            return self.cx.on_select()
        self.save_notes()
        rows = self.selected()
        self.clear_split(card=False)
        self.clear_grab()
        self.cur = rows[-1]["id"] if rows else None
        if len(rows) == 1 and rows[0].get("decision") == "Keep":
            self.R.last_req = rows[0]["id"]
        self.restyle()
        self.show_card(rows)
        self.placer.on_select(rows)

    def show_view(self, key):
        """3.90.0: Our structure, L to M (the crosswalk) or Coverage beside the page."""
        return self.views.show_view(key)

    def show_heading(self, num):
        """3.90.0: an L to M row on the page: the first sentence under that customer heading (or under its subsections)."""
        if self.R is None or not num:
            return None
        its = [it for it in self.M.items if (it.get("section") or "") == num] or \
              [it for it in self.M.items if (it.get("section") or "").startswith(num + ".")]
        if not its:
            self.host.status(f"No sentence of {num} is in the review.")
            return None
        self.select(its[0]["id"])
        return its[0]["id"]

    def select(self, iid):
        if self.cx is not None and iid in self.cx.byid:
            self._guard = True
            self.view.scene().clearSelection()
            b = self.view.boxes.get(iid)
            if b is not None:
                b.setSelected(True)
                self.view.ensureVisible(b, 40, 140)
            self._guard = False
            return self.cx.on_select()
        it = self.R.item(iid)
        if it is not None and it.get("file") != self.file:
            self.files.setCurrentText(it["file"])
        self._guard = True
        self.view.scene().clearSelection()
        b = self.view.boxes.get(iid)
        if b is not None:
            b.setSelected(True)
            self.view.ensureVisible(b, 40, 140)
        self._guard = False
        self.on_select()
        if b is None and it is not None:                  # 2.63.0: no page copy to show it on: the card still opens
            self.cur = iid
            self.show_card([it])

    def on_word(self, iid, k):
        it = self.R.item(iid)
        if it is None:
            return
        ms = list(WORD.finditer(it.get("text", "")))      # the boxes hold the sentence's words in order, page by page
        if 0 < k < len(ms):
            self.split_at = ms[k].start()
            self.split_word = (iid, k)
            self.show_split(iid, k)
            self.host.status(f"Split here (S) splits {iid} before \"{ms[k].group(0)}\". Esc cancels.")
        else:
            self.clear_split()
            self.host.status("Click a word after the first one: the second part starts with the word you click.")
        self.show_card(self.selected())

    # ------------------------------------------------------------ 2.96.0 words dragged across, and captures
    def clear_grab(self):
        for x in self._grab_items:
            self._drop(x)
        self._grab_items, self.grab = [], None
        self.grab_multi = None

    def _piece(self, iid, a, b):
        """The characters of words a..b of a sentence (end punctuation and an opening bracket come along)."""
        row = self.R.item(iid) if self.cx is None else next((x for x in self.cx.rows if x["id"] == iid), None)
        text = (row or {}).get("text", "")
        ms = list(WORD.finditer(text))
        if not (0 <= a <= b < len(ms)):
            return None
        tail = re.match(r"[^\s]*", text[ms[b].end():]).group(0)
        lead = re.search(r"[(\[\"'\u201c\u2018]*$", text[:ms[a].start()]).group(0)
        s0, e0 = ms[a].start() - len(lead), ms[b].end() + len(tail)
        return {"iid": iid, "a": a, "b": b, "s": s0, "e": e0, "text": text[s0:e0].strip()}

    def show_span(self, spans, final=True):
        """3.28.1: words dragged across several sentences, tinted; let go, they are picked (whatever was selected before):
        their sentences are selected, a capture or bin takes just these words, and Make a sentence (Shift+S) combines them into
        one sentence, split from the sentences they came from."""
        for x in self._grab_items:
            self._drop(x)
        self._grab_items = []
        tint = QColor("#86EFAC"); tint.setAlpha(140)
        for iid, a, b in spans:
            for r in self.view.words.get(iid, [])[a:b + 1]:
                it = self.view.scene().addRect(r.adjusted(-1, -1, 1, 1), QPen(Qt.NoPen), QBrush(tint)); it.setZValue(13)
                self._grab_items.append(it)
        if not final:
            return None
        pieces = [p for p in (self._piece(*x) for x in spans) if p and p["text"]]
        if not pieces:
            return None
        self.grab = None
        sc = self.view.scene()
        sc.blockSignals(True)
        sc.clearSelection()
        for p in pieces:
            if p["iid"] in self.view.boxes:
                self.view.boxes[p["iid"]].setSelected(True)
        sc.blockSignals(False)
        self.clear_split(card=False)
        self.cur = pieces[-1]["iid"]
        self.restyle()
        self.grab_multi = pieces
        if "Make" in self.keys:
            self.keys["Make"].setEnabled(self.cx is None)
        self.show_card(self.selected())
        self.host.status(f"Picked words in {len(pieces)} sentences. Make a sentence (Shift+S) makes them one sentence, split from "
                         "where they were; a capture uses just these words; click elsewhere to drop them.")
        return pieces

    def show_grab(self, iid, a, b, final=True):
        """The words a..b of the sentence, tinted; when the mouse is let go they are what a capture uses."""
        for x in self._grab_items:
            self._drop(x)
        self._grab_items = []
        rects = self.view.words.get(iid, [])
        tint = QColor("#86EFAC"); tint.setAlpha(140)
        for r in rects[a:b + 1]:
            it = self.view.scene().addRect(r.adjusted(-1, -1, 1, 1), QPen(Qt.NoPen), QBrush(tint)); it.setZValue(13)
            self._grab_items.append(it)
        if not final:
            return None
        row = self.R.item(iid) if self.cx is None else next((x for x in self.cx.rows if x["id"] == iid), None)
        text = (row or {}).get("text", "")
        ms = list(WORD.finditer(text))
        if not (0 <= a <= b < len(ms)):
            return None
        tail = re.match(r"[^\s]*", text[ms[b].end():]).group(0)          # 3.20.3: up to the next space: an e-mail, a number,
        lead = re.search(r"[(\[\"'\u201c\u2018]*$", text[:ms[a].start()]).group(0)   # the end punctuation, a closing bracket
        s0, e0 = ms[a].start() - len(lead), ms[b].end() + len(tail)            # and an opening bracket before it come along
        self.grab = {"iid": iid, "a": a, "b": b, "s": s0, "e": e0, "text": text[s0:e0].strip()}
        self.clear_split(card=False)
        self.host.status(f"Picked: \"{self.grab['text'][:80]}\". Capture uses these words; Make a sentence (Shift+S) makes them a "
                         "sentence of their own; click elsewhere to drop them.")
        if "Make" in self.keys:
            self.keys["Make"].setEnabled(self.cx is None)
        self.show_card(self.selected())
        return self.grab

    def _graphic_section(self):
        """The section a graphic need starts in: the sentence's own (a requirement), else the target section."""
        rows = self.selected()
        it = rows[0] if rows else None
        return (it.get("map") if it is not None and it.get("decision") == "Keep" and it.get("map") else "") or (self.target or "")

    def capture_source(self):
        """(text, source) for a capture: the words dragged across, else the selected sentences."""
        rows = self.selected()
        gm = getattr(self, "grab_multi", None)
        if self.grab and any(it["id"] == self.grab["iid"] for it in rows):
            it = next(it for it in rows if it["id"] == self.grab["iid"])
            text = self.grab["text"]
        elif gm and rows:                                              # 3.28.1: words across sentences
            it = next((x for x in rows if x["id"] == gm[0]["iid"]), rows[0])
            text = " ".join(p["text"] for p in gm)
        elif rows:
            it = rows[0]
            text = " ".join(x.get("text", "") for x in rows)
        else:
            return "", {}
        place = self.placed.get(it["id"], ("",))[0] or it.get("place", "")
        loc = (PS.where_text(self.pdf, place) if (self.pdf and place) else "") or " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        pg = para = ""
        if self.pdf and place:                                         # 2.98.0: page and paragraph for Customer Q&A
            try:
                p_, q_ = PS.where(self.pdf, place)
                pg, para = (str(p_) if p_ else ""), (str(q_) if q_ else "")
            except Exception:
                diag.swallowed()
        return text, {"doc": it.get("file", "") or (self.file or ""), "loc": loc, "text": it.get("text", ""),
                      "section": it.get("section", ""), "page": pg, "para": para, "sid": it["id"]}

    def captured_rules(self, it):
        """3.20.3: the submission and formatting rules captured from this sentence (by its id, or its words for older
        captures): [(register, row)]."""
        import docversions as DV
        import subreq as SR
        reg = SR.Register(DV.Library(self.host.ws.p("documents")).load())
        words = " ".join((it.get("text") or "").split())[:400]
        return reg, [r for r in reg.rows() if r.get("manual") and r.get("captured")
                     and ((r.get("sid") and r["sid"] == it["id"]) or (not r.get("sid") and words and r.get("sentence") == words))]

    def decision_of(self, it):
        """3.29.0: (the decision's name, its color) as Settings names them: L (Instructions), Support, Ignore..."""
        cfg = getattr(self, "items_cfg", None)
        dd = (cfg or {}).get("decisions") or {}
        d = it.get("decision", "")
        if it.get("type") == "Heading" and d in ("", "Drop"):
            return "RFP heading", ""
        if d == "Keep":                                  # 4.1.0: the piece type's name (Instruction, Evaluation, Deliverable...)
            lm = it.get("lm") or ""
            x = dd.get("deliv") if _first_piece(it) == "deliverable" and dd.get("deliv") else dd.get(lm)
            return (x["name"], x["color"]) if x else ("Requirement, not designated", "#4D7C0F")
        code = {"Context": "ctx", "Customer": "cust", "Drop": "ignore"}.get(d)
        if d == "Customer" and _first_piece(it) in ("rule", "date") and _first_piece(it) in dd:     # 4.1.0: a Rule or a Date
            code = _first_piece(it)
        if code and code in dd:
            return dd[code]["name"], dd[code]["color"]
        return "Not decided yet", ""

    def sentence_menu(self, iid):
        """3.29.0: the right-click menu of a sentence on the page: take its decision off, take off what was captured
        from it, deselect it, or clear the selection. A sentence outside the selection becomes the selection first."""
        from PySide6.QtWidgets import QMenu
        import excerpts as EX
        m = QMenu(self)
        if self.R is None or self.cx is not None:
            m.addAction("Clear selection", lambda: self.view.scene().clearSelection())
            return m
        sel = [it["id"] for it in self.selected()]
        if iid not in sel:
            self.select(iid)
            sel = [iid]
        rows = [x for x in (self.R.item(i) for i in sel) if x]
        for key, text in (("Combine", "Combine the selected sentences  J"), ("Split", "Split at the red line  S"),
                          ("Make", "Make the dragged words a sentence  Shift+S")):     # 3.75.0: were buttons
            b = self.keys.get(key)
            if b is not None:
                m.addAction(text, b.click).setEnabled(b.isEnabled())
        from . import leaveoutview as LOV                  # 4.3.0: Leave out of the matrix, on Place
        LOV.add_actions(self, m, rows)
        m.addSeparator()
        decided = [it for it in rows if it.get("decision")]
        if len(rows) == 1:
            name = self.decision_of(rows[0])[0]
            a = m.addAction(f"Take the decision off: {name}" if decided else "Not decided yet", self.do_undecide)
        else:
            a = m.addAction(f"Take the decision off {len(decided)} of {len(rows)} sentences" if decided
                            else f"None of the {len(rows)} sentences is decided", self.do_undecide)
        a.setEnabled(bool(decided)); a.setShortcut("Delete")
        try:
            rec = R_.Record(self.host.ws.root)
            caps = [x for i in sel for x in EX.of_sentence(rec, i)]
            names = {b["id"]: b["name"] for b in EX.bins(rec, self.host.config_dir)}
            names.update({k: c["name"] for k, c in ((getattr(self, "items_cfg", None) or {}).get("captures") or {}).items()})
            seen = set()
            caps = [x for x in caps if not (x["id"] in seen or seen.add(x["id"]))]
        except Exception:  # noqa: BLE001
            diag.swallowed()
            caps = []
        if caps and self.target:                                       # 3.29.1
            m.addAction(f"Put its captures in the target: {self.target}", lambda: self.place_captures([x["id"] for x in caps]))
        for x in caps[:12]:
            txt = EX.text_of(x)
            m.addAction(f"Take off the capture {names.get(x.get('bin'), x.get('bin', ''))}: "
                        f"{txt[:50] + ('...' if len(txt) > 50 else '')}", lambda _=False, i=x["id"]: self.remove_excerpt(i))
        nums = sorted({it.get("section") for it in rows if it.get("section")})   # 3.85.0: map the customer heading
        if nums:
            m.addSeparator()
            if self.target:
                m.addAction(f"Map {', '.join(nums)} to the target: {self.target}", lambda: self.placer.map_selected())
            if any(self.placer and HS_mapped(self.M, n) for n in nums):
                m.addAction(f"Clear the map of {', '.join(nums)}", lambda: self.placer.map_selected(""))
        m.addSeparator()
        if len(rows) > 1:
            m.addAction("Deselect this sentence", lambda: self.deselect(iid))
        m.addAction("Clear selection", lambda: self.view.scene().clearSelection()).setShortcut("Esc")
        return m

    def deselect(self, iid):
        b = self.view.boxes.get(iid)
        if b is not None:
            b.setSelected(False)

    def decided_box(self, it):
        """3.29.0: what was decided and captured on this sentence, at a glance, then each capture to edit."""
        import excerpts as EX
        import topics as TP
        M = self.M
        d = it.get("decision", "")
        name, color = self.decision_of(it)
        box = QFrame(); box.setObjectName("decidedBox")
        c = color or "#94A3B8"
        box.setStyleSheet(f"QFrame#decidedBox{{border:1px solid {c};border-left:5px solid {c};border-radius:6px;}}")
        bv = QVBoxLayout(box); bv.setContentsMargins(D.SPACE["s"], D.SPACE["xs"], D.SPACE["s"], D.SPACE["xs"]); bv.setSpacing(2)
        lines = []
        if d == "Keep":
            secs = SD.item_sections(M, it)
            lines.append(f"<b>Decision:</b> {name}" + (f", in {', '.join(secs)}" if secs else ", no section yet"))
        elif d == "Context":
            hosts = C.cf_ids(it.get("context_for", ""))
            lines.append(f"<b>Decision:</b> {name}" + (f" for {', '.join(hosts)}" if hosts else ", for no requirement yet"))
        elif d == "Customer":
            lines.append(f"<b>Decision:</b> {name}: counted, never answered")
        elif d == "Drop" and it.get("type") != "Heading":
            lines.append(f"<b>Decision:</b> {name}: not in the response")
        else:
            lines.append(f"<b>Decision:</b> {name}")
        rec = R_.Record(self.host.ws.root) if self.host.ws is not None else None
        if rec is not None:
            tps = [t["name"] for t in TP.of(rec, it["id"])]
            if tps:
                lines.append("<b>Topics:</b> " + ", ".join(tps))
            names = {b["id"]: b["name"] for b in EX.bins(rec, self.host.config_dir)}
            cfg = (getattr(self, "items_cfg", None) or {}).get("captures") or {}
            for k_, c_ in cfg.items():
                names[k_] = c_["name"]
            caps = [names.get(x["bin"], x["bin"]) for x in EX.of_sentence(rec, it["id"])]
            caps += [cfg.get(k_, {}).get("name", PM.text([k_])) for k_ in (self.marks.get(it["id"]) or [])
                     if not str(k_).startswith("bin:") and k_ not in ("task", "tquestion") and cfg.get(k_, {}).get("name", "") not in caps]
            if caps:
                lines.append("<b>Captured:</b> " + ", ".join(dict.fromkeys(x for x in caps if x)))
            sg = (getattr(self, "sg", {}) or {}).get(it["id"]) or {}
            if sg.get("state") == "accepted":
                lines.append("Decided from a suggestion" + (", not checked yet" if sg.get("unchecked") else ", checked"))
        for ln in lines:
            lb = QLabel(ln); lb.setTextFormat(Qt.RichText); lb.setWordWrap(True); bv.addWidget(lb)
        self.decided = box
        self.decided_lines = lines
        self.add(box)
        if self.host.ws is not None:
            self.show_captures(it)
        return lines

    def show_captures(self, it):
        """The rules, questions and other captures that came from this sentence, with their values to fix in place."""
        reg, rules = self.captured_rules(it)
        import custqa as Q
        qs = [q for q in Q.items(R_.Record(self.host.ws.root)) if q.get("sid") == it["id"]]
        import excerpts as EX
        rec = R_.Record(self.host.ws.root)
        xs = EX.of_sentence(rec, it["id"])                                # 3.21.0: the excerpts that hold its words
        inbins = {x["bin"] for x in xs}
        others = [k for k in (self.marks.get(it["id"]) or []) if k not in ("submit", "format", "question", "task", "tquestion")
                  and k not in inbins and not str(k).startswith("bin:")]
        self.capture_edits = {}
        self.excerpt_rows = {}
        if not (rules or qs or others or xs):
            return 0
        self.head("Captured from this sentence")
        from PySide6.QtWidgets import QLineEdit
        for r in rules:
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["xs"])
            h.addWidget(D.label(f"{r['kind']}: {r['subject']}", "muted", wrap=False))
            ed = QLineEdit(r["value"]); ed.setToolTip("Fix the value and press Save (Enter)")
            h.addWidget(ed, 1)
            sv = D.button("Save", None, lambda _=False, k=r["key"], e=ed: self.edit_capture(k, e.text()), "Keep this value")
            ed.returnPressed.connect(lambda k=r["key"], e=ed: self.edit_capture(k, e.text()))
            rm = D.button("Take out", "ghost", lambda _=False, k=r["key"]: self.remove_capture(k), "Take this rule out")
            h.addWidget(sv); h.addWidget(rm)
            self.capture_edits[r["key"]] = ed
            self.add(w)
        for q in qs:
            self.add(D.label(f"Customer question ({q.get('status', '')}): {q.get('question', '')[:160]}", None))
        if qs:
            self.add(D.button("Open in the Q&&A log", "ghost", lambda: self.host.go("custqa"), "Edit the question there"))
        names = getattr(self, "bin_names", {}) or {b["id"]: b["name"] for b in EX.bins(rec, self.host.config_dir)}
        for x in xs:
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["xs"])
            words = EX.text_of(x)
            bits = [x.get("value", "")] if x.get("value") else []
            bits.append(("answers: " if x["bin"] == "objective" else "in: ") + (", ".join(x.get("sections", [])) or "no section yet"))
            if x.get("sub") == "written":
                bits.append("phrase check" if x.get("check") == "phrase" else "Final Checks item")
            if x.get("note"):
                bits.append(x["note"])
            lab = D.label(f"<b>{names.get(x['bin'], x['bin'])}</b>: \u201c{words[:120]}{'...' if len(words) > 120 else ''}\u201d"
                          + (f"  ({'; '.join(bits)})" if bits else ""), None)
            lab.setToolTip(words[:1500] + "\n" + EX.where_of(x))
            h.addWidget(lab, 1)
            h.addWidget(D.button("Edit...", None, lambda _=False, i=x["id"]: self.edit_excerpt(i), "Bin, value, note, sections"))
            if self.target and self.target not in (x.get("sections") or []):        # 3.29.1: one click into a section
                h.addWidget(D.button("Into the target", "ghost", lambda _=False, i=x["id"]: self.place_captures([i]),
                                     f"Put it in {self.target}"))
            sb = D.button("Section...", "ghost", None, "Put it in a section of the structure, or take it out of one")
            sb.setMenu(self.section_menu_for(x["id"])); h.addWidget(sb)
            if x["bin"] in ("objective", "keypoint"):                # 3.29.0: seeds for the Wall of Truth
                h.addWidget(D.button("On the wall" if x.get("truth") else "To the Wall of Truth", "ghost",
                                     lambda _=False, i=x["id"]: self.promote_excerpt(i), "A Fact on the effort's Wall of Truth, "
                                     "its words verbatim with where they sit"))
            h.addWidget(D.button("Take out", "ghost", lambda _=False, i=x["id"]: self.remove_excerpt(i), "Take the excerpt out"))
            self.excerpt_rows[x["id"]] = lab
            self.add(w)
        if others:
            self.add(D.label("Also captured: " + PM.text(others) + ". Edit them where they are filed (Effort Dashboard, "
                             "acronym list, Effort Record).", "muted"))
        return len(rules) + len(qs) + len(others) + len(xs)

    def edit_capture(self, key, value):
        """3.20.3: a captured rule's value fixed from the sentence's card (a mistyped e-mail, say)."""
        import docversions as DV
        import subreq as SR
        reg = SR.Register(DV.Library(self.host.ws.p("documents")).load())
        ok = reg.edit(key, value)
        if ok:
            diag.activity("capture_edited")
            self.host.status("Saved: " + " ".join(value.split())[:80])
            self.host.changed()
        return ok

    def remove_capture(self, key):
        import docversions as DV
        import subreq as SR
        ok = SR.Register(DV.Library(self.host.ws.p("documents")).load()).remove_manual(key)
        if ok:
            diag.activity("capture_removed")
            self.show_card(self.selected())
        return ok

    def load_marks(self):
        """3.18.1: the sentences something was captured from (or a task or team question made on)."""
        try:
            ws = self.host.ws
            rec = R_.Record(ws.root) if ws is not None else None
            self.marks = PM.with_bins(PM.load(ws, rec), rec) if ws is not None else {}
            import excerpts as EX
            self.bin_names = {b["id"]: b["name"] for b in EX.bins(rec, self.host.config_dir)} if rec is not None else {}
        except Exception:
            diag.swallowed()
            self.marks = {}
        return self.marks

    def mark_rows(self, kind, sids=None):
        """3.18.1: mark the sentences a capture came from (the one dragged across, else the selected ones)."""
        if sids is None:
            rows = self.selected()
            sids = [self.grab["iid"]] if (self.grab and any(it["id"] == self.grab["iid"] for it in rows)) else [it["id"] for it in rows]
        n = PM.add(self.host.ws, self.marks, sids, kind)
        if n:
            self.restyle()
        return n

    def do_capture(self, kind, answer=None):
        """3.18.1: a capture that was filed marks its sentence on the page."""
        sids, parts = None, []
        if self.cx is None and self.R is not None:
            rows = self.selected()
            sids = [self.grab["iid"]] if (self.grab and any(it["id"] == self.grab["iid"] for it in rows)) else [it["id"] for it in rows]
            parts = self.excerpt_parts()
        got = self._do_capture(kind, answer)
        if got and sids:
            self.mark_rows(kind, sids)
            __import__("skqt.shredbar", fromlist=["x"]).capture_types(self, kind, sids)     # 4.1.0
        if got and parts:                                    # 3.21.0: every capture keeps the words and where they sit
            self.file_excerpt(kind, got, parts)
        return got

    # ------------------------------------------------------------ 3.21.0 excerpts and bins
    def excerpt_parts(self):
        """The words a capture or a bin uses, part by part: the words dragged across, else each selected sentence (in the
        document's order, next to each other or not), with document, version, page, paragraph, numbering and heading."""
        import excerpts as EX
        rows = self.selected() if self.R is not None else []
        if not rows:
            return []
        g = self.grab if (self.grab and any(it["id"] == self.grab["iid"] for it in rows)) else None
        use = [it for it in rows if it["id"] == g["iid"]] if g else rows
        gm = {p["iid"]: p["text"] for p in (getattr(self, "grab_multi", None) or [])}    # 3.28.1: words across sentences
        if gm and not g:
            use = [it for it in rows if it["id"] in gm]
        order = {it["id"]: i for i, it in enumerate(self.R.M.items)}
        out = []
        for it in sorted(use, key=lambda it: order.get(it["id"], 0)):
            place = self.placed.get(it["id"], ("",))[0] or it.get("place", "")
            pg = para = ""
            if self.pdf and place and it.get("file") == self.file:
                try:
                    p_, q_ = PS.where(self.pdf, place)
                    pg, para = (str(p_) if p_ else ""), (str(q_) if q_ else "")
                except Exception:
                    diag.swallowed()
            out.append(EX.part_of(it, doc=it.get("file", "") or (self.file or ""), page=pg, para=para,
                                  version=it.get("version", ""), words=g["text"] if g else gm.get(it["id"], "")))
        return out

    def cap_sections(self):
        """3.29.1: where a new capture goes: the target section, when Into the target section is on."""
        if self.R is None or not getattr(self, "into_target", None) or not self.into_target.isChecked():
            return []
        return [self.target] if self.target and self.target in set(self.R.labels()) else []

    def _save_into_target(self, on):
        import reviewitems as RI
        try:
            data = RI.load(self.host.config_dir)
            data["into_target"] = bool(on)
            RI.save(self.host.config_dir, data)
        except Exception:  # noqa: BLE001
            diag.swallowed()

    def place_captures(self, xids, label=None, only=False, on=True):
        """3.29.1: captures into a section of the structure (the target unless label), in one Undo step."""
        import excerpts as EX
        label = label or self.target
        if not xids or not label or self.R is None:
            if not label:
                self.host.status("Click a section in your structure first: captures go into the target.")
            return 0
        self.R.snap(f"captures into {label}")
        n = EX.place(R_.Record(self.host.ws.root), set(xids), label, on=on, only=only)
        if not n and self.R.undo:
            self.R.undo.pop()
        if n:
            diag.activity("captures_placed", n=n)
            self.host.status(f"{n} capture(s) {'in' if on else 'out of'} {label}")
            self.after_bins(); self.fill_tree()
        return n

    def section_menu_for(self, xid):
        """3.29.1: a menu of the structure's sections; a tick for each one the capture is in; a click puts it in or takes
        it out."""
        from PySide6.QtWidgets import QMenu
        import excerpts as EX
        x = EX.get(R_.Record(self.host.ws.root), xid) or {}
        have = set(x.get("sections") or [])
        m = QMenu(self)
        for lab in (self.R.labels() if self.R is not None else []):
            a = m.addAction(lab, lambda _=False, l=lab: self.place_captures([xid], l, on=l not in have))
            a.setCheckable(True); a.setChecked(lab in have)
        return m

    def file_excerpt(self, kind, got, parts):
        """A capture's excerpt: the bin is the capture; a submission or formatting rule keeps its value and key."""
        import excerpts as EX
        try:
            rec = R_.Record(self.host.ws.root)
            value, refs = "", []
            if kind in ("submit", "format") and isinstance(got, list):
                import docversions as DV
                import subreq as SR
                rows = {r["key"]: r for r in SR.Register(DV.Library(self.host.ws.p("documents")).load()).rows()}
                refs = [k for k in got if k]
                value = "; ".join(f"{rows[k]['subject']}: {rows[k]['value']}" for k in refs if k in rows)
            xid = EX.add(rec, kind, parts, value=value, ref=refs, sections=self.cap_sections())
            if xid:
                self.load_marks(); self.restyle()
            return xid
        except Exception:
            diag.swallowed()
            return None

    # ------------------------------------------------------------ 3.29.0: decisions and captures, the team's way
    DEC_KEY = {"L": "L", "M": "M", "C": "Requirement", "I": "Interest", "ctx": "Support", "cust": "Customer's", "ignore": "Ignore",
               "rule": "Rule", "date": "Date", "deliv": "Deliverable"}                       # 4.1.0: the piece types
    DEC_KIND = {"L": "req", "M": "lmM", "C": "lmS", "I": "req", "ctx": "ctx", "cust": "cust", "ignore": "drop",
                "rule": "cust", "date": "cust", "deliv": "lmS"}

    def _dec_fn(self, code):
        from . import shredbar as SB                       # 4.1.0: each decision keeps the piece's type (shredtypes)
        if code in SB.KEY_OF_CODE:                         # 4.5.0: a type toggles, and a piece can have several
            old = (lambda: SB.do_piece(self, code)) if code in SB.NEW_CODES else (
                lambda: SB.decide(self, code, {"L": lambda: self.do_lm("L"), "M": lambda: self.do_lm("M"), "C": lambda: self.do_sow(),
                                               "cust": self.do_customer, "ignore": self.do_clear}[code]))
            return lambda: SB.toggle_piece(self, SB.KEY_OF_CODE[code]) if self.cx is None else old()
        act = {"I": lambda: self.do_lm("I"), "ctx": self.do_ctx}[code]
        return lambda: SB.decide(self, code, act)

    def _cap_fn(self, key):
        if key in ("objective", "keypoint", "other"):
            return lambda: self.do_bin(key) if self.cx is None else None
        if key == "written":
            return lambda: self.do_bin("format", written=True) if self.cx is None else None
        if key in EX_BUILTIN_CAPTURES:
            return lambda: self.do_capture(key) if (self.cx is None or key != "graphic") else None
        return lambda: self.do_bin(key) if self.cx is None else None

    def apply_items(self):
        """Names, keys, colors and showing of the decisions and captures (Settings > Review: decisions and captures)."""
        import reviewitems as RI
        self.items_cfg = RI.load(self.host.config_dir)
        self.into_target.blockSignals(True); self.into_target.setChecked(self.items_cfg.get("into_target", True))
        self.into_target.blockSignals(False)
        d = self.items_cfg["decisions"]
        for code, lm in (("L", "L"), ("M", "M"), ("C", "C"), ("I", "I")):     # the page and the legend take the colors
            D.PAGE_LM[lm] = d[code]["color"]
            SD.LM_SHORT[lm] = d[code]["name"]
        D.PAGE_LM["SOW"] = d["C"]["color"]
        D.PAGE_DEC["Context"], D.PAGE_DEC["Customer"], D.PAGE_DEC["Drop"] = d["ctx"]["color"], d["cust"]["color"], d["ignore"]["color"]
        D.PAGE_PIECE["rule"], D.PAGE_PIECE["date"] = d["rule"]["color"], d["date"]["color"]        # 4.1.0: as the team colors them
        legend = [(x["name"], x["color"]) for x in RI.decisions_for(self.items_cfg, self.effort_type()) if x["code"] != "ignore"]
        legend += [("Not designated", "#4D7C0F"), ("Ignored", d["ignore"]["color"]), ("Captured", D.CAPTURE_COLOR)]
        self.legend.setText("&nbsp;&nbsp;".join(f"<span style='color:{c}'>\u25A0</span> {n}" for n, c in legend)
                            + "&nbsp;&nbsp;<span style='color:#94A3B8'>\u25A1</span> Not decided")
        self.build_decide()
        self.build_captures()
        if self.view.boxes:
            self.restyle()

    def effort_type(self):
        try:
            return ((self.host.ws.get("prod_std", {}) or {}).get("effort_type") or "") if self.host.ws is not None else ""
        except Exception:  # noqa: BLE001
            return ""

    def _clear_lay(self, lay, keep=()):
        """Take every widget out of a layout and delete it, except the ones in keep (kept for the next build: 3.30.0, a
        capture made a second time hit More... after it was deleted)."""
        while lay.count():
            w = lay.takeAt(0).widget()
            if w is not None and w not in keep:
                w.setParent(None); w.deleteLater()

    def build_decide(self):
        import reviewitems as RI
        cfg = getattr(self, "items_cfg", None) or RI.load(self.host.config_dir)
        self._clear_lay(self.dec_lay)
        for k in list(self.DEC_KEY.values()):
            self.keys.pop(k, None)
        et = self.effort_type()
        shown = RI.decisions_for(cfg, et, show_all=self.dec_all.isChecked())
        hidden = len(RI.decisions_for(cfg, et, show_all=True)) - len(RI.decisions_for(cfg, et))
        self.dec_all.setVisible(bool(hidden) or self.dec_all.isChecked())
        self.dec_all.setText(f"Show every decision ({hidden} hidden for this effort)" if hidden else "Show every decision")
        for d in shown:
            b = D.button(f"{d['name']}  {d['key']}".strip(), self.DEC_KIND[d["code"]], self._dec_fn(d["code"]),
                         f"{d['name']}. Key: {d['key'] or 'none'}. Change its name, key and color in Settings > Review: "
                         "decisions and captures.")
            b.setIcon(D.dot_icon(d["color"]))
            self.keys[self.DEC_KEY[d["code"]]] = b
            self.dec_lay.addWidget(b)
        self._bind_keys(cfg)

    def custom_captures(self):
        import excerpts as EX
        if self.host.ws is None:
            return []
        try:
            return [b for b in EX.bins(R_.Record(self.host.ws.root), self.host.config_dir) if not b["builtin"]]
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return []

    def build_captures(self):
        import reviewitems as RI
        cfg = getattr(self, "items_cfg", None) or RI.load(self.host.config_dir)
        self._clear_lay(self.cap_lay, keep=(self.more_btn,))
        self.cap_keys, self.more_actions = {}, {}
        et = self.effort_type()
        for key in cfg["order"]:
            c = cfg["captures"][key]
            if not RI.capture_on(cfg, key, et):                 # 3.82.0: the effort type hides and shows captures too
                continue
            if c["place"] == "bar":
                b = D.button(f"{c['name']}  {c['keyseq']}".strip(), "cap", self._cap_fn(key),
                             c["does"] + ". Uses the words you dragged across, else the selected sentences.")
                b.setIcon(D.dot_icon(c["color"]))
                self.cap_keys[key] = b
                self.cap_lay.addWidget(b)
            else:
                self.more_actions[key] = c
        for c in self.custom_captures():                       # your own captures, on the bar
            b = D.button(f"{c['name']}  {c.get('key', '')}".strip(), "cap", self._cap_fn(c["id"]),
                         (c.get("about") or "Your own capture") + (" (the team's)" if c.get("team") else " (this effort's)"))
            b.setIcon(D.dot_icon(c["color"]))
            self.cap_keys[c["id"]] = b
            self.cap_lay.addWidget(b)
        self.cap_keys["more"] = self.more_btn
        self.cap_lay.addWidget(self.more_btn)
        self._bind_keys(cfg)

    def fill_more_menu(self):
        import reviewitems as RI
        cfg = getattr(self, "items_cfg", None) or RI.load(self.host.config_dir)
        m = self.more_menu
        m.clear()
        for key, c in self.more_actions.items():
            a = m.addAction(D.dot_icon(c["color"]), c["name"] + (f"   {c['keyseq']}" if c.get("keyseq") else ""), self._cap_fn(key))
            a.setToolTip(c["does"])
        m.addSeparator()
        m.addAction("+ Capture...", lambda: self.new_bin())
        m.addAction("Captures of this effort...", lambda: self.manage_bins())
        m.addAction("Decisions and captures (Settings)...", lambda: self.host.go("settings"))
        m.addSeparator()                                   # 3.85.0: the customer's headings and our sections
        a = m.addAction("Lines for headings"); a.setCheckable(True); a.setChecked(self.placer.gutter.heads_on)
        a.setToolTip("A faint line from each customer heading on the page to the section that answers it")
        a.toggled.connect(self.placer.toggle_heads)
        m.addAction("Export cross-reference table...", lambda: self.placer.export_crossref())
        return m

    def _bind_keys(self, cfg):
        """Every decision and capture key, as set in Settings."""
        import reviewitems as RI
        for sc in getattr(self, "_dyn_keys", []):
            sc.setEnabled(False); sc.setParent(None); sc.deleteLater()
        self._dyn_keys = []
        et = self.effort_type()
        for d in RI_decisions(cfg, et, self.dec_all.isChecked()):
            if d.get("key"):
                self._dyn_keys.append(QShortcut(QKeySequence(d["key"]), self.view, activated=self._dec_fn(d["code"])))
        if "M" in [d["code"] for d in RI_decisions(cfg, et, self.dec_all.isChecked())]:
            self._dyn_keys.append(QShortcut(QKeySequence("Shift+M"), self.view, activated=lambda: self.do_lm("M")))
        for key, c in cfg["captures"].items():
            if c.get("keyseq") and RI.capture_on(cfg, key, et):
                self._dyn_keys.append(QShortcut(QKeySequence(c["keyseq"]), self.view, activated=self._cap_fn(key)))

    def fill_bins_menu(self):
        import excerpts as EX
        m = self.bins_menu
        m.clear()
        m.addAction("Other submission detail", lambda: self.do_bin("other"))
        m.addAction("Written formatting rule", lambda: self.do_bin("format", written=True))
        rec = R_.Record(self.host.ws.root) if self.host.ws is not None else None
        custom = [b for b in EX.bins(rec, self.host.config_dir) if not b["builtin"]] if rec is not None else []
        if custom:
            m.addSeparator()
            for b in custom:
                a = m.addAction(D.dot_icon(b["color"]), b["name"] + (f"   {b['key']}" if b.get("key") else ""),
                                lambda bid=b["id"]: self.do_bin(bid))
                a.setToolTip(b.get("about", ""))
        m.addSeparator()
        m.addAction("New bin...", lambda: self.new_bin())
        m.addAction("Bins of this effort...", lambda: self.manage_bins())
        m.addAction("Every excerpt...", lambda: self.all_excerpts())
        return m

    def do_custom_bin(self, n):
        import excerpts as EX
        if self.cx is not None or self.host.ws is None:
            return None
        custom = [b for b in EX.bins(R_.Record(self.host.ws.root), self.host.config_dir) if not b["builtin"]]
        if n >= len(custom):
            return self.host.status(f"No capture of your own on Alt+{n + 1} yet: More... > + Capture...")
        return self.do_bin(custom[n]["id"])

    def do_bin(self, bin_id, answer=None, written=False):
        """3.21.0: the words dragged across (else the selected sentences, next to each other or not) into a bin, verbatim
        with where they sit; a value only when one exists. answer (tests): BinDialog.values(). Returns the excerpt's id."""
        import excerpts as EX
        from . import binsview as BV
        if self.cx is not None or self.R is None:
            return self.host.status("Captures of this kind are for the matrix's documents.")
        parts = self.excerpt_parts()
        if not parts:
            return self.host.status("Select a sentence first (drag across words inside it to pick just those; Ctrl+click for more).")
        rec = R_.Record(self.host.ws.root)
        if answer is None:
            d = BV.BinDialog(self, rec, self.host.config_dir, bin_id, parts, sections=self.R.labels(), chosen=self.cap_sections())
            if written:
                d.value.clear()
            if d.exec() != QDialog.Accepted:
                return None
            answer = d.values()
        b = answer.get("bin") or bin_id
        sub = ("measured" if (answer.get("value") or "").strip() else "written") if b == "format" else ""
        groups = EX.lead_groups(parts, self.lead_part) if b == "objective" else [parts]   # 3.29.0: a list's items
        xids = []
        for g in groups:
            xid = EX.add(rec, b, g, value=answer.get("value", ""), note=answer.get("note", ""), sub=sub,
                         sections=answer["sections"] if "sections" in answer else self.cap_sections())
            if xid and sub == "written" and answer.get("check"):
                EX.update(rec, xid, check=answer["check"])
            if xid:
                xids.append(xid)
        if xids:
            diag.activity("excerpt_binned", n=len(xids))
            if len(xids) > 1:
                self.host.status(f"{len(xids)} objectives, one for each item, each with its lead-in")
            else:
                secs = (EX.get(rec, xids[0]) or {}).get("sections") or []
                self.host.status(f"In {EX.bin_name(rec, b, self.host.config_dir)}" + (f", in {secs[0]}" if secs else "")
                                 + f": \"{EX.text_of(EX.get(rec, xids[0]))[:70]}\"")
            self.after_bins()
        return xids[0] if len(xids) == 1 else (xids or None)

    def lead_part(self, sid):
        """3.29.0: the lead-in of a list item (the sentence the reader found before its list), as an excerpt part."""
        import excerpts as EX
        it = self.R.item(sid) if (self.R is not None and sid) else None
        lead = (it or {}).get("lead") or ""
        if not lead:
            return None
        items = self.M.items
        k = next((n for n, x in enumerate(items) if x.get("id") == sid), None)
        src = None
        if k is not None:
            src = next((x for x in reversed(items[:k]) if x.get("file") == it.get("file") and (x.get("text") or "").strip()
                        == lead.strip()), None)
        return EX.part_of(src or dict(it, id=(src or {}).get("id", ""), text=lead), doc=it.get("file", ""),
                          version=it.get("version", ""))

    def edit_excerpt(self, xid, answer=None):
        import excerpts as EX
        from . import binsview as BV
        rec = R_.Record(self.host.ws.root)
        x = EX.get(rec, xid)
        if x is None:
            return False
        if answer is None:
            d = BV.BinDialog(self, rec, self.host.config_dir, x["bin"], x["parts"], sections=self.R.labels() if self.R else [], x=x)
            if d.exec() != QDialog.Accepted:
                return False
            answer = d.values()
        b = answer.get("bin") or x["bin"]
        f = {"bin": b, "value": answer.get("value", x.get("value", "")), "note": answer.get("note", x.get("note", ""))}
        f["sections"] = answer.get("sections", x.get("sections", []))       # 3.29.1: every capture has its sections
        if b == "format":
            f["sub"] = "measured" if (f["value"] or "").strip() else "written"
            if f["sub"] == "written":
                f["check"] = answer.get("check") or x.get("check") or "final"
        ok = EX.update(rec, xid, **f)
        if ok:
            diag.activity("excerpt_edited")
            self.after_bins()
        return ok

    def promote_excerpt(self, xid):
        """3.29.0: an objective or key point on the Wall of Truth."""
        import excerpts as EX
        tid = EX.promote(R_.Record(self.host.ws.root), xid)
        if tid:
            diag.activity("excerpt_promoted")
            self.host.status("On the Wall of Truth (Effort > Wall of Truth): confirm or change its words there.")
            self.after_bins()
        return tid

    def remove_excerpt(self, xid):
        import excerpts as EX
        ok = EX.remove(R_.Record(self.host.ws.root), xid)
        if ok:
            self.after_bins()
        return ok

    def after_bins(self):
        self.build_captures()                                  # 3.29.0: your own captures sit on the bar
        self.load_marks(); self.restyle()
        self.show_card(self.selected())
        self.host.changed()

    def new_bin(self, answer=None):
        from . import binsview as BV
        bid = BV.make_bin(self, R_.Record(self.host.ws.root), self.host.config_dir, answer)
        if bid:
            self.after_bins()
        return bid

    def manage_bins(self, run=True):
        from . import binsview as BV
        d = BV.BinsDialog(self, self, R_.Record(self.host.ws.root))
        if run:
            d.exec()
        return d

    def all_excerpts(self, run=True):
        from . import binsview as BV
        d = BV.ExcerptsDialog(self, self, R_.Record(self.host.ws.root))
        if run:
            d.exec()
        return d

    def show_sentence(self, sid):
        if self.R is not None and self.R.item(sid) is not None:
            self.select(sid)
            return True
        return False

    def _do_capture(self, kind, answer=None):
        """Contact, Submission, Formatting, Acronym, Question or Key date (2.98.0), and the More captures (2.99.0: factor,
        pagelimit, deliverable, detail, hot) from the picked words or the selected sentence. answer (tests): the dialog's
        values."""
        from . import captureview as CV
        import effortrec as RR
        text, src = self.capture_source()
        if not text:
            return self.host.status("Select a sentence first (drag across words inside it to pick just those).")
        if kind == "contact":
            if answer is None:
                d = CV.ContactDialog(self, text, RR.Record(self.host.ws.root).contacts())
                if d.exec() != QDialog.Accepted:
                    return None
                answer = d.values()
            values, cid = answer
            return CV.file_contact(self.host, values, cid, src)
        if kind in ("submit", "format"):
            if answer is None:
                d = CV.RuleDialog(self, text, kind)
                if d.exec() != QDialog.Accepted:
                    return None
                answer = d.values()
            rules, due = answer
            got = CV.file_rules(self.host, rules, due, src)
            self.host.changed()
            return got
        if kind == "acronym":
            if answer is None:
                d = CV.AcronymDialog(self, text)
                if d.exec() != QDialog.Accepted:
                    return None
                answer = d.values()
            return CV.file_acronym(self.host, answer[0], answer[1], src)
        if kind == "question":                                         # 2.98.0
            if answer is None:
                d = CV.QuestionDialog(self, text, src, self.host.people())
                if d.exec() != QDialog.Accepted:
                    return None
                answer = d.values()
            return CV.file_question(self.host, answer, src)
        if kind == "keydate":                                          # 2.98.0
            if answer is None:
                d = CV.KeyDateDialog(self, text)
                if d.exec() != QDialog.Accepted:
                    return None
                answer = d.values()
            got = CV.file_key_date(self.host, answer, src)
            self.host.changed()
            return got
        if kind == "graphic":                                          # 3.0.4
            if answer is None:
                d = CV.graphic_dialog(self, text, self.R.labels(), self.host.people(), self._graphic_section())
                if d.exec() != QDialog.Accepted:
                    return None
                answer = d.values()
            got = CV.file_graphic(self.host, answer, dict(src, text=text))     # it quotes the words picked, else the sentence
            if got:
                self.show_card(self.selected())
                self.host.changed()
            return got
        more = {"factor": (lambda: CV.factor_dialog(self, text, self._factors()), CV.file_factor),          # 2.99.0
                "pagelimit": (lambda: CV.page_limit_dialog(self, text, self._limit_targets()), CV.file_page_limit),
                "deliverable": (lambda: CV.deliverable_dialog(self, text), CV.file_deliverable),
                "detail": (lambda: CV.detail_dialog(self, text), CV.file_detail),
                "hot": (lambda: CV.hot_dialog(self, text), CV.file_hot)}
        if kind in more:
            make, file_it = more[kind]
            if answer is None:
                d = make()
                if d.exec() != QDialog.Accepted:
                    return None
                answer = d.values()
            got = file_it(self.host, answer, src)
            self.host.changed()
            return got
        return None

    def add_work(self, kind, iid, answer=None):
        """2.99.0: a task (kind 'task') or a team question ('question') on a sentence. answer (tests): the dialog's values
        {"text", "owner", "due"}. Returns the id."""
        it = self.R.item(iid) if self.R is not None else None
        if it is None or self.host.ws is None:
            return None
        if answer is None:
            from PySide6.QtWidgets import QLineEdit
            d = QDialog(self); d.setWindowTitle("A task on this sentence" if kind == "task" else "A question for the team")
            d.setMinimumWidth(520); f = QFormLayout(d)
            f.addRow(D.label(f"{iid}: {it.get('text', '')[:200]}", "muted"))
            t = QLineEdit(); f.addRow("Task" if kind == "task" else "Question", t)
            who = QComboBox(); who.setEditable(True); who.addItem(""); who.addItems(self.host.people())
            f.addRow("Owner" if kind == "task" else "For", who)
            due = QLineEdit(); due.setPlaceholderText("YYYY-MM-DD (optional)")
            if kind == "task":
                f.addRow("Due", due)
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            f.addRow(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = {"text": t.text(), "owner": who.currentText(), "due": due.text()}
        rec = R_.Record(self.host.ws.root)
        if kind == "task":
            got = rec.add_task(answer.get("text", ""), owner=answer.get("owner", ""), due=answer.get("due", ""), about=f"sentence:{iid}",
                               notes=f"{iid}: {it.get('text', '')[:400]}")
        else:
            got = rec.add_note(answer.get("text", ""), on="requirement", on_id=iid, label=iid, question=True)
            if got and answer.get("owner"):
                n = next((x for x in rec.data["notes"] if x["id"] == got), None)
                if n is not None:
                    n["assignee"] = " ".join(answer["owner"].split())[:80]
                    rec.save()
        if got:
            if kind == "task":
                diag.activity("sentence_task_added")
            else:
                diag.activity("sentence_question_added")
            self.mark_rows("task" if kind == "task" else "tquestion", [iid])
            self.show_card(self.selected())
        return got

    def body_add_layout(self, lay):
        """A row of buttons in the card (the card's add() takes widgets)."""
        w = QWidget(); w.setLayout(lay); lay.setContentsMargins(0, 0, 0, 0)
        return self.add(w)

    def _factors(self):
        import custfocus as F
        return F.factors(R_.Record(self.host.ws.root))

    def _limit_targets(self):
        """Volumes of the structure and the deliverables, for a page limit."""
        import deliverables as DL
        out = []
        try:
            if self.M is not None:
                mode, name, heads = SD.volumes_of(self.M)
                out += heads if mode != "one" else ([name] if name else [])
        except Exception:
            diag.swallowed()
        out += [d["name"] for d in DL.items(R_.Record(self.host.ws.root)) if d.get("name") not in out]
        return out + (["Proposal"] if "Proposal" not in out else [])

    # ------------------------------------------------------------ 2.93.0 the split, shown on the page
    def _drop(self, item):
        try:
            if item is None:
                return
            if item.scene() is not None:
                item.scene().removeItem(item)
        except RuntimeError:                               # the page was drawn again: the item is gone already
            pass

    def on_hover_word(self, iid, k):
        self._drop(self._hover_item); self._hover_item = None
        rects = self.view.words.get(iid, []) if iid else []
        if k <= 0 or k >= len(rects) or getattr(self, "split_word", None) == (iid, k):
            return
        r = rects[k]
        pen = QPen(QColor("#DC2626")); pen.setWidthF(1.6); pen.setCosmetic(True); pen.setStyle(Qt.DashLine)
        self._hover_item = self.view.scene().addLine(r.left() - 1.5, r.top() - 3, r.left() - 1.5, r.bottom() + 3, pen)
        self._hover_item.setZValue(15)
        self._hover_item.setToolTip("Click: split here")

    def show_split(self, iid, k):
        for x in self._split_items:
            self._drop(x)
        self._split_items = []
        rects = self.view.words.get(iid, [])
        if not (0 < k < len(rects)):
            return
        sc = self.view.scene()
        tint = QColor("#93C5FD"); tint.setAlpha(110)
        for r in rects[k:]:                                  # the second part, tinted
            it = sc.addRect(r.adjusted(-1, -1, 1, 1), QPen(Qt.NoPen), QBrush(tint)); it.setZValue(12)
            self._split_items.append(it)
        r = rects[k]
        pen = QPen(QColor("#DC2626")); pen.setWidthF(3); pen.setCosmetic(True)
        cut = sc.addLine(r.left() - 1.5, r.top() - 5, r.left() - 1.5, r.bottom() + 5, pen); cut.setZValue(16)
        self._split_items.append(cut)
        px = self._split_bar_item(sc)
        last = rects[-1]                                     # under the sentence, so neither part is covered
        px.setPos(r.left() - 2, max(r.bottom(), last.bottom()) + 4)
        px.show()
        self.split_bar = px.widget()
        b = self.keys.get("Split")
        if b is not None:
            b.setEnabled(True)                                # 3.20.3: same text, so the toolbar never reflows (no jump)
        self.view.ensureVisible(px, 4, 4)                     # and the page moves only when the bar would be off screen

    def _split_bar_item(self, sc):
        """The Split here / Cancel bar on the page: made once per drawing of the page, then moved and shown or hidden
        (never deleted while the page shows, which Qt does not like for a widget on a page)."""
        px = getattr(self, "_split_px", None)
        try:
            if px is not None and px.scene() is sc:
                return px
        except RuntimeError:
            pass
        bar = QWidget(); bar.setObjectName("splitBar")
        h = QHBoxLayout(bar); h.setContentsMargins(4, 3, 4, 3); h.setSpacing(4)
        h.addWidget(D.button("Split here  S", "primary", self.do_split, "Split the sentence at the red line"))
        h.addWidget(D.button("Cancel", "ghost", lambda: self.clear_split(), "Keep the sentence whole (Esc)"))
        bar.setStyleSheet(f"QWidget#splitBar{{background:{D.tokens()['surface']};border:1px solid #DC2626;border-radius:6px;}}")
        px = sc.addWidget(bar)
        px.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        px.setZValue(30)
        px.hide()
        self._split_px = px
        return px

    def clear_split(self, card=True):
        for x in self._split_items:
            self._drop(x)
        self._split_items = []
        try:
            if getattr(self, "_split_px", None) is not None:
                self._split_px.hide()
        except RuntimeError:
            self._split_px = None
        self._drop(self._hover_item); self._hover_item = None
        self.split_at, self.split_word, self.split_bar = None, None, None
        b = self.keys.get("Split")
        if b is not None:
            b.setEnabled(False); b.setText("Split  S")
        if card and self.cx is None:
            self.show_card(self.selected())

    # ------------------------------------------------------------ the card
    def eventFilter(self, obj, ev):
        if obj is self.card_area.viewport() and ev.type() == QEvent.Resize:
            QTimer.singleShot(0, self.fit_card)
        return False

    def fit_card(self):
        """A scroll area does not ask wrapped text how tall it is at the width shown: the card's height is set from
        its layout at that width, so long text scrolls instead of being cut off."""
        w = self.card_area.viewport().width()
        if w > 50:
            self.card.setMinimumHeight(self.card_lay.totalHeightForWidth(w) if self.card_lay.hasHeightForWidth()
                                       else self.card_lay.sizeHint().height())

    def clear_card(self):
        while self.card_lay.count():
            w = self.card_lay.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def add(self, w):
        if isinstance(w, QLabel):
            w.setWordWrap(True)
        self.card_lay.addWidget(w)
        return w

    def head(self, text):
        l = self.add(D.SectionTitle(text))
        l.setContentsMargins(0, D.SPACE["m"], 0, 0)
        return l

    # ------------------------------------------------------------ 3.0.4 several sentences at once
    def select_all(self, undecided=False):
        """Every sentence of this document on the page (only those with no decision, if undecided)."""
        if self.R is None or self.cx is not None:
            return 0
        self._guard = True
        sc = self.view.scene(); sc.clearSelection()
        n = 0
        for iid, b in self.view.boxes.items():
            it = self.R.item(iid)
            if it is None or (undecided and it.get("decision")) or (undecided and it.get("type") == "Heading"):
                continue
            b.setSelected(True); n += 1
        self._guard = False
        self.on_select()
        self.host.status(f"{n} sentence(s) selected." if n else ("Every sentence here has a decision." if undecided else "Nothing to select."))
        return n

    def select_undecided(self):
        return self.select_all(undecided=True)

    def refresh_bulk(self, rows):
        """3.29.0: the bar stays in its place whenever a document is open, so the page never jumps: two or more sentences
        fill it in (how many, the tally, one action for all); fewer leave it waiting."""
        on = self.cx is None and self.R is not None and len(rows) > 1
        self.bulk.setVisible(self.R is not None)
        for wdg in (self.bulk_dec, self.bulk_sec, self.bulk_own, self.bulk_clear):
            wdg.setEnabled(on)
        if not on:
            self.bulk_lbl.setText("1 sentence selected" if len(rows) == 1 else "No sentences selected")
            self.bulk_info.setText("Select two or more for one decision, section or author on all")
            return
        tally = {}
        for it in rows:
            k = {"Keep": "requirement", "Context": "support", "Customer": "customer's"}.get(it.get("decision", ""), "undecided")
            tally[k] = tally.get(k, 0) + 1
        self.bulk_lbl.setText(f"{len(rows)} sentences selected")
        self.bulk_info.setText("  \u00b7  ".join(f"{tally[k]} {k}" for k in ("requirement", "support", "customer's", "undecided") if tally.get(k)))
        self.bulk_sec.blockSignals(True); self.bulk_sec.clear()
        self.bulk_sec.addItem("Put all in section...", "")
        for lab in self.R.labels():
            self.bulk_sec.addItem(lab, lab)
        self.bulk_sec.setEnabled(self.bulk_sec.count() > 1); self.bulk_sec.blockSignals(False)
        self.bulk_own.blockSignals(True); self.bulk_own.clear()
        self.bulk_own.addItem("Author for all...", None)
        self.bulk_own.addItem("(the section's lead)", "")
        for n in (self.host.people() or []):
            self.bulk_own.addItem(n, n)
        self.bulk_own.blockSignals(False)
        self.bulk_dec.setCurrentIndex(0)

    def bulk_decide(self, key):
        self.bulk_dec.setCurrentIndex(0)
        fn = {"L": lambda: self.do_lm("L"), "M": lambda: self.do_lm("M"), "SOW": self.do_sow, "ctx": self.do_ctx,
              "cust": self.do_customer, "ignore": self.do_clear}.get(key or "")
        if fn is not None:
            fn()

    def bulk_section(self, lab):
        rows = self.selected()
        if not lab or not rows:
            return 0
        n = self.R.put_in(rows, lab)                     # 3.18.2: decided sentences keep their decision
        out = sum(1 for it in rows if it.get("decision") == "Drop")
        diag.activity("compliance_assigned", n=n)
        self.after(f"{n} sentence(s) in {lab}" + (f"; {out} ignored left out of the response" if out else ""))
        return n

    def bulk_author(self, name):
        if name is None:
            return 0
        rows = self.selected()
        n = self.R.set_authors(rows, name) if rows else 0
        if n:
            diag.activity("assign_card_authors", n=n)
            self.after(f"{n} sentence(s): author {name or 'the section lead'}")
        else:
            self.refresh_bulk(rows)
            self.host.status("Authors go on requirements and support sentences: decide them first.")
        return n

    def show_card(self, rows):
        self.refresh_bulk(rows)
        if self.cx is not None:
            return self.cx.show_card(rows)
        self.clear_card()
        self.notes = None
        if self.R is None or not rows:
            self.add(D.EmptyState("No sentence selected", "Click a sentence on the page to see everything decided about it. "
                                  "Ctrl+click adds more; drag a box around several."))
            return
        M = self.M
        it = rows[-1]
        d = it.get("decision", "")
        kind = "Heading" if it.get("type") == "Heading" and d in ("", "Drop") else d
        tone, label, _tag = D.decision(kind)
        dname, dcolor = self.decision_of(it)                            # 3.29.0: the decision, as the team names and colors it
        top = QWidget(); th = QHBoxLayout(top); th.setContentsMargins(0, 0, 0, 0); th.setSpacing(D.SPACE["s"])
        k = D.Pill(dname, tone if tone != "faint" else "head")
        if dcolor:
            k.setStyleSheet(f"color:#FFFFFF;background:{dcolor};border-radius:8px;padding:2px 8px;font-weight:600;")
        th.addWidget(k)
        if len(rows) > 1:
            th.addWidget(D.label(f"and {len(rows) - 1} more selected", "muted", wrap=False))
        th.addStretch(1)
        idl = D.label(it["id"], "mono", wrap=False); th.addWidget(idl)
        self.add(top)
        self.kind_label = k
        t = self.add(D.label(it.get("text", ""), "reading"))
        t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if len(rows) == 1:                                              # 3.29.0: what was decided and captured, first
            try:
                self.decided_box(it)
            except Exception:
                diag.swallowed()
        self.sg_box = None
        try:
            self.suggestion_card(it, rows)                  # 3.18.0
        except Exception:
            diag.swallowed()
        if len(rows) == 1 and self.R is not None:            # 2.93.0: splitting, said where you are looking
            text = it.get("text", "")
            if self.split_at is not None and getattr(self, "split_word", None) and self.split_word[0] == it["id"]:
                box = QFrame(); box.setObjectName("splitPrev")
                box.setStyleSheet("QFrame#splitPrev{border:1px solid #DC2626;border-radius:6px;}")
                bv = QVBoxLayout(box); bv.setContentsMargins(D.SPACE["s"], D.SPACE["s"], D.SPACE["s"], D.SPACE["s"])
                bv.addWidget(D.label("Split preview", "label"))
                bv.addWidget(D.label("Part 1: " + text[:self.split_at].strip()))
                p2 = D.label("Part 2: " + text[self.split_at:].strip()); p2.setStyleSheet("background:rgba(147,197,253,0.35);")
                bv.addWidget(p2)
                br = QHBoxLayout(); bv.addLayout(br)
                br.addWidget(D.button("Split here  S", "primary", self.do_split)); br.addWidget(D.button("Cancel", "ghost", lambda: self.clear_split()))
                br.addStretch(1)
                self.split_preview = box
                self.add(box)
            else:
                self.split_preview = None
                if getattr(self, "grab", None) and self.grab["iid"] == it["id"]:          # 2.96.0
                    pk = self.add(D.label(f"Picked words: \u201c{self.grab['text']}\u201d. Capture (Contact, Submission, Question, "
                                          "Formatting, Acronym) uses them.", None))
                    pk.setStyleSheet("background:rgba(134,239,172,0.35);padding:4px;border-radius:4px;")
        ch = getattr(self, "change_of", {}).get(it["id"]) if len(rows) == 1 else None
        if ch:                                                         # 2.98.0: what this version changed
            m = self.changes
            box = QFrame(); box.setObjectName("changeBox")
            tone = "#D97706" if ch["kind"] == "changed" else "#16A34A"
            box.setStyleSheet(f"QFrame#changeBox{{border:1px dashed {tone};border-radius:6px;}}")
            bv = QVBoxLayout(box); bv.setContentsMargins(D.SPACE["s"], D.SPACE["s"], D.SPACE["s"], D.SPACE["s"])
            if ch["kind"] == "changed":
                bv.addWidget(D.label(f"Changed in {m['to'].get('label', '')} (was, in {m['from'].get('label', '')}):", "label"))
                was = D.label(change_html(ch)); was.setTextFormat(Qt.RichText); was.setWordWrap(True)
                was.setTextInteractionFlags(Qt.TextSelectableByMouse)
                bv.addWidget(was)
            else:
                bv.addWidget(D.label(f"New in {m['to'].get('label', '')}: not in {m['from'].get('label', '')}.", "label"))
            br = QHBoxLayout(); bv.addLayout(br)
            if ch["kind"] == "changed":
                br.addWidget(D.button("Show the old page", None, lambda: self.old_page(it["id"]),
                                      f"{m['from'].get('label', '')} at the same spot, the old sentence highlighted"))
            br.addWidget(D.button("Decide in Compare", "ghost", lambda: self.host.go("compare")))
            br.addStretch(1)
            self.change_box = box
            self.add(box)
        self.head("Source")
        place = self.placed.get(it["id"], ("",))[0] or it.get("place", "")
        where = PS.where_text(self.pdf, place) if (self.pdf and place) else MD._where(it)
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        ref, _how = SD.ref_of(M, it)
        src = [f"File: {it.get('file', '')}"] + ([f"Where: {where}"] if where else []) + ([f"RFP: {sec}"] if sec else []) \
            + ([f"Referenced as: {ref}"] if ref and ref != it.get("section") else []) + [f"ID: {it['id']}    Type: {it.get('type', '')}"]
        self.source_label = self.add(D.label("\n".join(src)))
        ident = SD.docs_of(M).get(it.get("file", "")) or {}
        idl2 = (f"Document {ident.get('initial')} ({ident.get('type', '')})" if ident.get("initial") else "")
        self.ident_label = self.add(D.label(idl2, "muted"))
        self.ident_label.setVisible(bool(idl2))
        if d == "Keep":                                                 # 2.68.0: L or M, and the reference it makes
            lmw = QWidget(); lh = QHBoxLayout(lmw); lh.setContentsMargins(0, 0, 0, 0); lh.setSpacing(D.SPACE["s"])
            cur_lm = it.get("lm", "")
            sug, why = SD.lm_why(M, it)
            for code in (("L", "M", "C", "I") if self.rfi else ("L", "M", "C")):
                b = D.button(SD.LM_SHORT[code], "req" if cur_lm == code else None,
                             lambda _=False, c=code: self.set_lm(rows, c), SD.LM[code] + (" (click again to take it off)" if cur_lm == code else ""))
                lh.addWidget(b)
            lh.addWidget(D.label(f"{'Set: ' + cur_lm if cur_lm else ('Suggested: ' + sug if sug else 'Not set (optional)')}", "muted", wrap=False))
            lh.addStretch(1)
            self.add(lmw)
            if sug and not cur_lm and why:
                self.lm_why = self.add(D.label(f"Suggested because {why}. L and M are our labels (Shipley); the RFP need not use them.", "muted"))
            fr = SD.full_ref(M, it)
            self.ref_label = self.add(D.label(f"Reference in the matrix: {fr}" if fr else "Reference: set the document initial and L or M", "mono"))
            vols = O.volumes_of_item(M, it)
            if vols:
                vw = QWidget(); vh = QHBoxLayout(vw); vh.setContentsMargins(0, 0, 0, 0); vh.setSpacing(4)
                vh.addWidget(D.label("In", "muted", wrap=False))
                for vname in vols:
                    vh.addWidget(D.Pill(vname, "accent"))
                vh.addStretch(1)
                self.vol_badges = self.add(vw)
        self.head("Decision")
        self.chips = []
        if d in ("Keep", "Context", "Customer"):                       # 3.18.2: every decided sentence can go in the structure
            secs = SD.item_sections(M, it)
            tone = {"Keep": "req", "Context": "ctx", "Customer": "cust"}[d]
            if d != "Keep" and (secs or self.R.labels()):
                self.add(D.label("In the response structure:" if secs else "Not in a section (optional): + Section puts it in one "
                                 "for the writers" + ("; the customer's stays unanswered." if d == "Customer" else "."), "muted"))
            self.sec_chips = []
            for lab in secs:
                ch = self.add(Chip(lab, tone, on_remove=lambda _=False, l=lab: self.act(self.R.remove_section, it, l)))
                (self.chips if d == "Keep" else self.sec_chips).append(ch)
            if not secs and d == "Keep":
                self.add(QLabel("No section yet: click one in your structure (or build one: + Heading), then R."))
            cb = QComboBox(); cb.addItem("+ Section")
            cb.addItems([lab for lab in self.R.labels() if lab not in secs])
            cb.activated.connect(lambda i, cb=cb: self.act(self.R.add_section, it, cb.itemText(i)) if i > 0 else None)
            self.add(cb)
            self.section_box = cb
        if d == "Keep":
            pass
        elif d == "Context":
            for i in C.cf_ids(it.get("context_for", "")):
                x = self.R.item(i)
                self.chips.append(self.add(Chip(f"{i}   {x.get('map', '') if x else ''}", "ctx",
                                                on_remove=lambda _=False, b=i: self.act(self.R.unlink, it, b),
                                                on_jump=lambda _=False, b=i: self.select(b))))
            cb = QComboBox(); cb.addItem("+ Requirement")
            for x in M.items:
                if x.get("decision") == "Keep" and x["id"] not in C.cf_ids(it.get("context_for", "")):
                    cb.addItem(f"{x['id']}  {x.get('map', '')}: {x['text'][:50]}", x["id"])
            cb.activated.connect(lambda i, cb=cb: self.act(self.R.link, it, cb.itemData(i)) if i > 0 else None)
            self.add(cb)
        self.head("Author(s)")
        on = d in ("Keep", "Context")
        can = [r for r in rows if r.get("decision") in ("Keep", "Context")]     # 3.15.1: the selection's own count
        from .people import NamesField                  # 2.77.0: authors come from the author list only
        ed = self.add(NamesField(self.host, SD.split_names((can[0] if can else it).get("owner", "")), empty="(the section's lead)",
                                 title="Authors" if len(rows) == 1 else f"Authors for {len(can)} sentences",
                                 on_change=lambda names, rows=rows: self.set_authors(rows, ", ".join(names))))
        ed.setEnabled(bool(can))
        self.authors = ed
        if not can:                                     # 3.15.1: say why, instead of a grey button
            self.add(D.label("Authors go on requirements and context. Decide the sentence first (L, E or R makes it a "
                             "requirement; C makes it context), then choose one or more authors.", "muted"))
        elif len(can) < len(rows):
            self.add(D.label(f"Authors go on the {len(can)} requirement and context sentence(s) of the {len(rows)} selected.", "muted"))
        lead = SD.section_people(M, it.get("map", "")).get("lead", "") if it.get("map") else ""
        if on and not it.get("owner"):
            self.add(D.label(f"Empty: the section lead writes it ({lead})." if lead else "Empty: the section's lead, once one is named (People...).", "muted"))
        if len(rows) == 1 and self.host.ws is not None:                 # 3.20.0: open meeting topics that point here
            try:
                import meetings as MT
                where = [it["id"]] + SD.item_sections(M, it)
                mt = MT.topics(R_.Record(self.host.ws.root), open_only=True, target=where)
            except Exception:
                diag.swallowed()
                mt = []
            self.topic_labels = []
            if mt:
                self.head("Meeting topics")
                for m_, t_ in mt:
                    self.topic_labels.append(self.add(D.label(f"{t_['text']}  \u00b7  {m_['title']} ({m_['date']})"
                                                              + (f"  \u00b7  {t_['owner']}" if t_.get("owner") else ""), None)))
        if len(rows) == 1 and self.host.ws is not None:                 # 2.99.0: tasks and team questions on the sentence
            tq = sentence_work(R_.Record(self.host.ws.root), it["id"])
            import graphics as GX
            if tq or GX.for_sentence(R_.Record(self.host.ws.root), it["id"]):
                self.head("Tasks, questions and graphics")
            self.work_labels = []
            for kind, x in tq:
                if kind == "task":
                    txt = (f"TASK  {x['title']}" + (f"  \u00b7  {x['owner']}" if x.get("owner") else "") + (f"  \u00b7  due {x['due']}" if x.get("due") else "")
                           + f"  \u00b7  {x.get('status', '')}")
                else:
                    txt = (f"QUESTION  {x['text']}" + (f"  \u00b7  for {x['assignee']}" if x.get("assignee") else "")
                           + (f"  \u00b7  answered: {x.get('answer', '')}" if x.get("resolved") else "  \u00b7  open"))
                self.work_labels.append(self.add(D.label(txt)))
            import graphics as GX                                       # 3.0.4: graphic needs tagged here
            self.gfx_labels = []
            for g in GX.for_sentence(R_.Record(self.host.ws.root), it["id"]):
                self.gfx_labels.append(self.add(D.label(f"GRAPHIC  {g['concept']}  \u00b7  {g.get('status', '')}"
                                                        + (f"  \u00b7  {g['section']}" if g.get("section") else ""))))
            wr = QHBoxLayout(); wr.setSpacing(D.SPACE["xs"])
            wr.addWidget(D.button("+ Task...", None, lambda _=False, i=it["id"]: self.add_work("task", i), "A task about this sentence, with an owner and a due date"))
            wr.addWidget(D.button("+ Ask the team...", None, lambda _=False, i=it["id"]: self.add_work("question", i), "A question for the team about this sentence"))
            wr.addStretch(1)
            self.body_add_layout(wr)
        ids, how = self.R.related(it)
        if ids:
            self.head("Relationships")
        self.rel_labels = []
        for i in ids:
            x = self.R.item(i)
            if x is None:
                continue
            role = "REQ" if how == "hosts" else "SUPPORT"
            b = QLabel(f"<a href='{i}'><b>{role} {i}</b></a> ({MD.ctx_ref(M, x)}) {x['text'][:140]}")
            b.setTextFormat(Qt.RichText)
            t_ = D.tokens()
            b.setStyleSheet(f"background:{t_['surface2']};border:1px solid {t_['border']};border-radius:{D.RADIUS['control']}px;padding:6px")
            b.linkActivated.connect(lambda href: self.select(href))
            self.rel_labels.append(self.add(b))
        from . import ctxassign as CXA                  # 2.84.0: what people attached to it from library documents
        lib_ctx = CXA.library_for_requirement(self, it["id"])
        self.lib_labels = []
        if lib_ctx:
            self.head(f"From the library ({len(lib_ctx)})")
            t_ = D.tokens()
            for text_, docn, where_, _aid in lib_ctx:
                b = D.label(f"{text_[:300]}\n{docn}" + (f", {where_}" if where_ else ""))
                b.setStyleSheet(f"background:{t_['ctx_soft']};border:1px solid {t_['border']};border-radius:{D.RADIUS['control']}px;padding:6px")
                self.lib_labels.append(self.add(b))
        self.hist_labels = []                           # 2.85.0: what customer versions did to it
        try:
            import changereview as CHR
            hrv = CHR.Review(self.host.ws.root).load()
            hist = hrv.history(it["id"])
        except Exception:
            diag.swallowed()
            hist = []
        if hist:
            self.head(f"History ({len(hist)})")
            names = {"updated": "Wording changed", "removed": "Removed", "added": "Added"}
            for e in hist:
                txt = f"{names.get(e['kind'], e['kind'])} by {e.get('doc', '')} {e.get('label', '')} ({e.get('when', '')[:10]})"
                if e["kind"] == "updated":
                    txt += f"\nWas: {e.get('old', '')[:200]}"
                if e["kind"] in ("updated", "removed"):
                    txt += "\n" + (f"Owner confirmed {e['confirmed']}" if e.get("confirmed") else "Awaiting the owner")
                self.hist_labels.append(self.add(D.label(txt, None if e.get("confirmed") or e["kind"] == "added" else "crit")))
            if it["id"] in hrv.awaiting():
                self.confirm_btn = self.add(D.button("Confirm it still fits", "primary", lambda _=False, i=it["id"]: self.confirm_change(i),
                                                     "The answer was checked against the new wording"))
        self.head("Notes")
        self.notes = self.add(QPlainTextEdit(it.get("notes", "")))
        self.notes.setFixedHeight(72)
        self.notes_for = it["id"]
        self.notes.textChanged.connect(self.notes_timer.start)
        self.review_labels = []                               # 2.63.0: color team comments read back from review packets
        rv = self.review_notes(it["id"])
        if rv:
            self.head(f"Review comments ({len(rv)})")
            t_ = D.tokens()
            for n in rv:
                b = D.label(f"{n['text']}\n{R_.short_date(n['at'])}" + (f" | {n['who']}" if n.get("who") else ""))
                b.setStyleSheet(f"background:{t_['warn_soft']};border:1px solid {t_['border']};border-radius:{D.RADIUS['control']}px;padding:6px")
                self.review_labels.append(self.add(b))
        QTimer.singleShot(0, self.fit_card)

    def confirm_change(self, iid):
        """2.85.0: the owner checked the answer against the new wording."""
        import changereview as CHR
        if not CHR.Review(self.host.ws.root).load().confirm(iid):
            return False
        it = self.R.item(iid)
        if it is not None and (it.get("new") or "").endswith("owner to confirm"):
            it["new"] = it["new"].replace("owner to confirm", "owner confirmed")
            self.M.pending = True
        diag.activity("change_confirmed")
        self.after(f"{iid}: the owner confirmed the answer still fits")
        return True

    def review_notes(self, iid):
        """The review notes on this sentence in the effort's record (newest first)."""
        ws = getattr(self.host, "ws", None)
        if ws is None:
            return []
        try:
            import reviewpkt as RP
            return RP.review_notes(R_.Record(ws.root), iid)
        except Exception:
            diag.swallowed()
            return []

    def save_notes(self):
        n = self.notes
        if n is None or self.R is None:
            return
        try:
            it = self.R.item(self.notes_for)
            if it is not None and self.R.set_notes(it, n.toPlainText()):
                self.host.changed()
        except RuntimeError:
            pass                                    # the card was rebuilt

    def set_lm(self, rows, lm):
        if rows and all(it.get("lm", "") == lm for it in rows):          # 2.96.0: clicking the one set takes it off
            lm = ""
        self.R.set_lm(rows, lm)
        diag.activity("compliance_lm_set", n=len(rows))
        self.after(f"{len(rows)} sentence(s): {SD.LM_SHORT.get(lm, lm) if lm else 'a requirement, neither L, M nor SOW'}")

    def set_authors(self, rows, text):
        n = self.R.set_authors(rows, text)
        if n:
            diag.activity("assign_card_authors", n=len(rows))
            self.host.changed()
            self.host.status(f"Author(s) set on {n} sentence(s).")

    def act(self, fn, *a):
        fn(*a)
        self.after(" ".join(getattr(fn, "__name__", "change").split("_")).capitalize()
                   + (f": {a[1]}" if len(a) > 1 and isinstance(a[1], str) else ""))

    # ------------------------------------------------------------ the structure
    def fill_volumes(self):
        self.volume.blockSignals(True)
        self.volume.clear()
        self.volume.addItem("All volumes", "")
        mode, name, heads = SD.volumes_of(self.M) if self.M is not None else ("", "", [])
        for h in (heads if mode == "several" else []):
            self.volume.addItem(h, h)
        if self.active_volume and self.volume.findData(self.active_volume) < 0:
            self.active_volume = ""
        self.volume.setCurrentIndex(max(0, self.volume.findData(self.active_volume)))
        self.volume.blockSignals(False)
        if hasattr(self, "vol_style") and self.M is not None:          # 3.28.1
            self.vol_style.blockSignals(True)
            self.vol_style.setCurrentIndex(max(0, self.vol_style.findData(O.volume_style(self.M))))
            self.vol_style.blockSignals(False)

    def rename_volume(self, title=None, label=None):
        """3.28.1: rename a volume (the one you are working in, else the one you pick); its number stays."""
        if self.M is None:
            return None
        mode, _n, heads = SD.volumes_of(self.M)
        heads = list(heads) if mode == "several" else []
        lab = label or self.active_volume
        if not lab:
            if not heads:
                return self.host.status("No volumes yet: + Volume adds one.")
            if len(heads) == 1:
                lab = heads[0]
            else:
                from PySide6.QtWidgets import QInputDialog
                lab, ok = QInputDialog.getItem(self, "Rename a volume", "The volume to rename:", heads, 0, False)
                if not ok:
                    return None
        new = self.rename_section(lab, title)
        if new and self.active_volume == lab:
            self.active_volume = new
        self.fill_volumes()
        return new

    def set_volume_style(self, style):
        """3.28.1: number every volume one way (Volume I, II, III; 1, 2, 3; A, B, C); everything in them follows."""
        if self.M is None:
            return {}
        self.R.snap()
        mp = O.set_volume_style(self.M, style)
        if self.active_volume in mp:
            self.active_volume = mp[self.active_volume]
        if self.target in mp:
            self.target = mp[self.target]
        diag.activity("volumes_numbered", n=len(mp))
        self.after(f"Volumes numbered {dict(O.VOLUME_STYLES)[style].replace('Volume ', '')}.")
        self.fill_volumes()
        return mp

    def pick_volume(self, vol):
        """Work in one volume: the structure shows its sections, and new sections go into it."""
        self.active_volume = vol or ""
        if self.target and self.active_volume and self.target not in O.in_volume(self.M, self.active_volume):
            self.target = None
        self.fill_tree()
        self.host.status(f"Working in {vol}." if vol else "Showing every volume.")

    def fill_tree(self):
        self.tree.clear()
        self.start_btn.setVisible(self.M is None or not self.M.outline)     # 3.75.0: shown while there are no sections
        if self.R is None:
            self.show_target()
            return
        self.fill_volumes()
        counts = self.R.counts()
        ctxn = self._ctx_counts()
        try:                                                    # 3.29.1: captures placed in each section
            import excerpts as EX
            capn = EX.section_counts(R_.Record(self.host.ws.root)) if self.host.ws is not None else {}
        except Exception:  # noqa: BLE001
            diag.swallowed()
            capn = {}
        show = set(O.in_volume(self.M, self.active_volume))
        stack = []
        parts_on = SP.has_parts(self.M)               # 3.19.0: the volume's parts, each with the rules it follows
        heads = O.volume_heads(self.M)
        cur_vol, last_part, part_node, sums = "", None, None, {}
        self.part_nodes = []
        for o in self.M.outline:
            lab = C.outline_label(o)
            if lab not in show:
                continue
            lvl = o.get("level", 1)
            if parts_on and lab in heads:
                cur_vol, last_part, part_node = lab, None, None
            par = next((x for x in reversed(stack) if x[0] < lvl), None)
            top = parts_on and lab not in heads and (par is None or par[1].data(0, Qt.UserRole) in heads)
            if top:
                part = SP.part_of(o)
                if part != last_part:
                    if cur_vol not in sums:
                        sums[cur_vol] = SP.summaries(self.host.config_dir, self.host.ws, self.M, cur_vol)
                    part_node = QTreeWidgetItem([SP.PART_NAME[part].upper(), "", "", "" if SP.counts(self.M, part) else "not counted"])
                    part_node.setData(0, Qt.UserRole, None); part_node.setData(0, Qt.UserRole + 1, part)
                    f = part_node.font(0); f.setBold(True); f.setPointSizeF(max(7.0, f.pointSizeF() - 1)); part_node.setFont(0, f)
                    part_node.setForeground(0, D.color("muted")); part_node.setForeground(3, D.color("muted"))
                    part_node.setToolTip(0, f"{SP.PART_NAME[part]}: {sums[cur_vol][part]}")
                    (par[1].addChild(part_node) if par else self.tree.addTopLevelItem(part_node))
                    part_node.setExpanded(True)
                    self.part_nodes.append(part_node)
                    last_part = part
            node = QTreeWidgetItem([lab, str(counts.get(lab, "") or ""), str(ctxn.get(lab, "") or ""), PB.tag(self.M, lab)
                                    + ("" if SP.item_count(self.M, lab) is None else
                                       (" counts" if SP.item_count(self.M, lab) else " not counted")), str(capn.get(lab, "") or "")])
            if PB.pages(self.M, lab):                                     # 3.18.2: the RFP's limit in red, a guideline in blue
                node.setForeground(3, QColor("#B91C1C" if PB.source(self.M, lab) == "rfp" else "#1D4ED8"))
                node.setToolTip(3, f"{PB.SOURCE_NAME[PB.source(self.M, lab)]}: {PB.fmt(PB.pages(self.M, lab))} page(s), subsections included")
            if ctxn.get(lab):
                node.setToolTip(2, f"{ctxn[lab]} sentence(s) from library documents attached as context")
            node.setData(0, Qt.UserRole, lab)
            if lab == self.target:
                f = node.font(0); f.setBold(True); node.setFont(0, f)
                node.setBackground(0, D.color("warn_soft")); node.setForeground(0, D.color("text"))
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            if top and part_node is not None:
                part_node.addChild(node)
            else:
                (stack[-1][1].addChild(node) if stack else self.tree.addTopLevelItem(node))
            stack.append((lvl, node))
        self.tree.expandAll()
        self.show_target()

    def show_target(self):
        """2.82.0: where R, L and M put the selected sentences, said above the decision buttons."""
        import html
        if self.R is None or not self.M.outline:
            self.target_lbl.setText("<b>Decide</b> &nbsp;Requirements go into the response structure: add a section below first.")
        elif self.cx is not None:
            self.target_lbl.setText("<b>From the library</b> &nbsp;" + (f"C and R put the selected sentences into <b>{html.escape(self.target)}</b>"
                                    if self.target else "Click a section below: C and R put the selected sentences there."))
        elif self.target:
            self.target_lbl.setText(f"<b>Decide</b> &nbsp;L, M and SOW put the selected sentences into "
                                    f"<b>{html.escape(self.target)}</b>")
        else:
            self.target_lbl.setText("<b>Decide</b> &nbsp;Click a section below: L, M and SOW put the selected sentences there.")
        self.show_item_values()
        lab = self.target if (self.R is not None and self.cx is None and self.target and self.target in set(O.labels(self.M))) else None
        self.section_panel.show_section(lab)
        self.section_panel.setVisible(lab is not None)

    def show_item_values(self):
        """3.35.0: the target item's Assigned To, Initial Page Allocation and % Complete, in the bottom bar."""
        lab = self.target if (self.R is not None and self.cx is None and self.target
                              and self.target in set(O.labels(self.M))) else None
        self.item_row.setVisible(lab is not None)
        if lab is None:
            return
        own = (SD.setup_of(self.M)["owners"].get(lab) or {})
        p = SD.section_people(self.M, lab)
        names = set()
        for v in SD.setup_of(self.M)["owners"].values():
            names.update(n.strip() for n in [v.get("lead", "")] + (v.get("with", "") or "").split(",") if n.strip())
        names.update(n for it in self.M.items for n in SD.split_names(it.get("owner", "")) if n)
        for w in (self.item_who, self.item_pages, self.item_pct):
            w.blockSignals(True)
        self.item_who.clear(); self.item_who.addItems(sorted(names, key=str.casefold))
        self.item_who.setEditText(own.get("lead", ""))
        self.item_who.lineEdit().setPlaceholderText(f"{p['lead']} (from {p['from']})" if p.get("lead") and p.get("from") != lab else "Nobody yet")
        self.item_pages.setValue(PB.pages(self.M, lab) or 0)
        v = SD.progress_of(self.M, lab)
        self.item_pct.setValue(-1 if v is None else v)
        for w in (self.item_who, self.item_pages, self.item_pct):
            w.blockSignals(False)
        self._item_shown = lab

    def set_item_value(self, what, value=None):
        """3.35.0: keep one of the target item's values (value: tests). One Undo step. Returns True when it changed."""
        lab = getattr(self, "_item_shown", None)
        if self.R is None or not lab or lab not in set(O.labels(self.M)):
            return False
        S = SD.setup_of(self.M)
        if what == "who":
            v = " ".join((self.item_who.currentText() if value is None else value).split())
            own = S["owners"].get(lab) or {}
            if v == own.get("lead", ""):
                return False
            self.R.snap(f"assigned to for {lab}")
            SD.set_people(self.M, lab, v, own.get("with", ""))
            msg = f"{lab}: assigned to {v or 'nobody'}"
        elif what == "pages":
            v = float(self.item_pages.value() if value is None else value)
            if (PB.pages(self.M, lab) or 0) == PB._round(v):
                return False
            self.R.snap(f"pages for {lab}")
            PB.set_pages(self.M, lab, v)
            msg = f"{lab}: {PB.fmt(PB.pages(self.M, lab)) or 'no'} page(s)"
        else:
            v = int(self.item_pct.value() if value is None else value)
            v = None if v < 0 else v
            if SD.progress_of(self.M, lab) == v:
                return False
            self.R.snap(f"% complete for {lab}")
            SD.set_progress(self.M, lab, v)
            msg = f"{lab}: " + ("% complete not set" if v is None else f"{v}% complete")
        self.R.changed()
        diag.activity("item_value_set")
        self.after(msg)
        return True

    def set_target(self, lab):
        self.target = lab
        self.host.status(f"Target: {lab}. R puts the selected sentences there.")
        self.fill_tree()

    def open_builder(self):
        """3.30.0: the Structure Builder, on the target section."""
        if not self.host.go("structure"):
            return None
        if self.target:
            self.host.structure_page.select(self.target)
        return "open"

    def start_from(self):
        """3.16.0: the Structure tab; with no sections yet it shows what the RFP prescribes (else its headings)."""
        if not self.host.go("structure"):
            return None
        if self.M is not None and not self.M.outline:
            return self.host.structure_page.offer_start()
        return "open"

    def people_dialog(self):
        from . import assigndialogs as AD                # 3.83.0: split out of this file
        return AD.people_dialog(self)

    def budget_dialog(self, run=True):
        """3.1.0: each volume's page limit split across its sections. run=False (tests): the dialog."""
        from . import assigndialogs as AD
        return AD.budget_dialog(self, run)

    def volumes_dialog(self):
        from . import assigndialogs as AD
        return AD.volumes_dialog(self)

    # ------------------------------------------------------------ actions
    def after(self, msg=""):
        try:
            self.note_decided(self.selected())          # 3.18.0: a person's decision on a suggested sentence
        except Exception:
            diag.swallowed()
        if self.R is not None and not getattr(self, "_undoing", False):
            self.R.label_last(msg or "a structure change")             # 3.18.2: Undo says what it puts back
        self.restyle()
        self.fill_tree()
        self.show_card(self.selected())
        self.host.changed()
        if msg:
            self.host.status(msg)
        if self.sg_on:
            self.show_score()
        self.placer.show_left()
        self.placer.gutter.update()

    def do_req(self):
        if self.cx is not None:
            return self.cx.promote()
        rows = self.selected()
        if not rows:
            return
        n = self.place_reqs(rows)
        diag.activity("compliance_assigned", n=n)
        self.after(f"{rows[0]['id'] if n == 1 else str(n) + ' sentences'}: compliance requirement "
                   + (f"in {self.target}" if self.target else "(no section yet: click one, or build one with + Heading)"))

    def do_sow(self):
        """2.96.0: SOW (Work): a compliance requirement in the target section (as R always did), designated SOW."""
        if self.cx is not None:
            return self.cx.promote()
        rows = self.selected()
        if not rows:
            return
        with self.R.group():
            n = self.place_reqs(rows)
            self.R.set_lm(rows, "C")
        diag.activity("compliance_assigned", n=n)
        self.after(f"{rows[0]['id'] if n == 1 else str(n) + ' sentences'}: SOW (Work) requirement "
                   + (f"in {self.target}" if self.target else "(no section yet: click one, or build one with + Heading)"))

    def do_lm(self, lm):
        """2.68.0: L or M; a sentence that is not a requirement yet becomes one (in the target section, if any)."""
        if self.cx is not None:
            return self.host.status("L and M are for the matrix's documents. R makes this sentence a requirement first.")
        rows = self.selected()
        if not rows:
            return
        new = [it for it in rows if it.get("decision") != "Keep"]
        with self.R.group():
            if new:
                self.place_reqs(new)
            self.R.set_lm(rows, lm)
        diag.activity("compliance_lm_set", n=len(rows))
        self.after(f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' sentences'}: {SD.LM_SHORT.get(lm, lm)} ({SD.LM[lm]})")

    # ------------------------------------------------------------ topics and Sort mode (3.28.0)
    def _trec(self):
        return R_.Record(self.host.ws.root) if self.host.ws is not None else None

    def toggle_sort(self, on=None):
        self.sort_on = (not self.sort_on) if on is None else bool(on)
        self.sort_btn.setChecked(self.sort_on)
        self.fill_topics()
        self.host.status("Sort mode: select sentences and press 1 to 9 for a topic (again takes it off)." if self.sort_on
                         else "Sort mode off: 1 to 9 do nothing.")
        return self.sort_on

    def fill_topics(self):
        """The topic chips (numbered in Sort mode), the Show list and the coverage."""
        import topics as TP
        rec = self._trec()
        lst = TP.topics(rec) if rec is not None else []
        lay = self.topic_chips_lay
        while lay.count():
            w = lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.topic_btns = []
        for n, t in enumerate(lst):
            b = D.button((f"{n + 1}  " if self.sort_on and n < 9 else "") + t["name"], None, lambda _=False, i=n: self.tag_topic(i),
                         f"Put the selected sentences in {t['name']} (again takes it off)" + (f"; key {n + 1} in Sort mode" if n < 9 else ""))
            b.setIcon(D.dot_icon(t["color"]))
            lay.addWidget(b); self.topic_btns.append(b)
        cur = self.topic_show.currentData()
        self.topic_show.blockSignals(True); self.topic_show.clear()
        self.topic_show.addItem("Every sentence", "")
        self.topic_show.addItem("No topic yet", "-")
        for t in lst:
            self.topic_show.addItem(t["name"], t["id"])
        self.topic_show.setCurrentIndex(max(0, self.topic_show.findData(cur)))
        self.topic_show.blockSignals(False)
        self.topic_bar.setVisible(self.R is not None)
        self.show_coverage()

    def show_coverage(self):
        import topics as TP
        rec = self._trec()
        tid = self.topic_show.currentData()
        if rec is None or self.M is None or not TP.topics(rec):
            self.topic_cov.setText("" if rec is None else "No topics yet: + Topic, or Topics > from the RFP's headings.")
            return {}
        cov = TP.coverage(rec, self.M.items)
        if tid and tid != "-":
            c = cov.get(tid) or {}
            self.topic_cov.setText(f"{c.get('sentences', 0)} sentence(s): {c.get('decided', 0)} decided, {c.get('open', 0)} open, "
                                   f"{c.get('in_section', 0)} in a section")
        else:
            tagged = set(rec.data.get("topic_tags", {}))
            n = sum(1 for it in self.M.items if it.get("type") != "Heading" and it["id"] not in tagged)
            self.topic_cov.setText(f"{len(TP.topics(rec))} topic(s); {n} sentence(s) with no topic yet")
        return cov

    def tag_topic(self, n):
        """The selected sentences in topic n (the first nine on keys 1 to 9); again takes it off."""
        import topics as TP
        rec = self._trec()
        lst = TP.topics(rec) if rec is not None else []
        if n >= len(lst):
            return self.host.status(f"No topic {n + 1} yet: + Topic adds one.")
        rows = self.selected()
        if not rows:
            return self.host.status("Select sentences first (Ctrl+click for more).")
        on = TP.tag(rec, [it["id"] for it in rows], lst[n]["id"])
        diag.activity("topic_tagged", n=len(rows))
        self.restyle(); self.show_coverage()
        self.host.status(f"{len(rows)} sentence(s) {'in' if on else 'out of'} {lst[n]['name']}.")
        return on

    def new_topic(self, name=None):
        import topics as TP
        rec = self._trec()
        if rec is None:
            return None
        if name is None:
            name = self._ask("New topic", "Topic name (for example Cybersecurity, Transition, Past performance):")
        if not name:
            return None
        tid = TP.add(rec, name)
        diag.activity("topic_added")
        self.fill_topics()
        return tid

    def topics_from_headings(self):
        import topics as TP
        rec = self._trec()
        if rec is None or self.M is None:
            return []
        made = TP.from_headings(rec, self.M.items)
        diag.activity("topics_from_headings", n=len(made))
        self.fill_topics(); self.restyle()
        self.host.status(f"{len(made)} topic(s) from the RFP's headings; the sentences under each carry it." if made
                         else "No headings found (sentences marked as RFP headings make topics).")
        return made

    def topics_from_tags(self):
        import topics as TP
        import docversions as DV
        rec = self._trec()
        if rec is None:
            return []
        try:
            lib = DV.Library(self.host.ws.p("documents")).load()
            names = lib.all_tags()
        except Exception:  # noqa: BLE001
            diag.swallowed(); names = []
        made = TP.from_tags(rec, names)
        self.fill_topics()
        self.host.status(f"{len(made)} topic(s) from the library's tags." if made else "The library's documents have no tags yet.")
        return made

    def manage_topics(self, run=True):
        from .topicsview import TopicsDialog
        d = TopicsDialog(self, self._trec(), self.R.labels() if self.R is not None else [])
        if run:
            d.exec()
            self.fill_topics(); self.restyle()
        return d

    def sections_from_topics(self, volume=None):
        """A section for each topic (in the volume you are working in), each topic mapped to its section: an RFI
        response is laid out one section per topic."""
        import topics as TP
        rec = self._trec()
        if rec is None or self.M is None:
            return []
        lst = TP.topics(rec)
        if not lst:
            return self.host.status("No topics yet.") or []
        self.R.snap()
        vol = volume if volume is not None else self.active_volume
        made = []
        for t in lst:
            if t.get("sections"):
                continue
            lab = O.add(self.M, t["name"], parent=vol) if vol else O.add(self.M, t["name"])
            TP.update(rec, t["id"], sections=[lab])
            made.append(lab)
        diag.activity("sections_from_topics", n=len(made))
        self.after(f"{len(made)} section(s) made, one per topic; a topic's requirements go to its section.")
        return made

    def place_reqs(self, rows):
        """3.28.0: requirements go to the section their topic maps to; the rest to the target section (or none yet)."""
        import topics as TP
        rec = R_.Record(self.host.ws.root) if self.host.ws is not None else None
        labels = set(self.R.labels())
        by, rest = {}, []
        for it in rows:
            sec = TP.section_for(rec, it["id"]) if rec is not None else ""
            (by.setdefault(sec, []) if sec in labels else rest).append(it)
        if getattr(self, "_accepting", False):             # 3.85.0: Enter takes the suggested home too
            homes, still = {}, []
            for it in rest:
                h = self.placer.home_for(it)
                (homes.setdefault(h, []) if h else still).append(it)
            by.update({h: by.get(h, []) + its for h, its in homes.items()})
            rest = still
        n = 0
        with self.R.group():
            for sec, its in by.items():
                n += self.R.req(its, sec) or 0
            if rest:
                n += self.R.req(rest, self.target or "") or 0
        first = next(iter(by.items()), None) or ((self.target, rest) if rest and self.target else None)
        if first and first[1]:
            self.placer.after_place(first[1], first[0])
        return n

    # ------------------------------------------------------------ building the structure as you go (2.68.0)
    def _ask(self, title, label, text=""):
        from PySide6.QtWidgets import QInputDialog
        t, ok = QInputDialog.getText(self, title, label, QLineEdit.Normal, text)
        return t.strip() if ok and t.strip() else None

    def new_volume(self, title=None):
        if self.M is None:
            return None
        title = title if title is not None else self._ask("New volume", "Volume name (for example Technical):")
        if not title:
            return None
        self.R.snap()
        lab = O.add_volume(self.M, title)
        diag.activity("qt_volume_added")
        self.active_volume = lab
        self.target = lab
        self.after(f"Volume added: {lab}. New sections go into it.")
        return lab

    def new_section(self, sub=False, title=None):
        """+ Heading (after the target, at its level) or + Subheading (under the target). With no target: a first
        section in the volume you are working in."""
        if self.M is None:
            return None
        title = title if title is not None else self._ask("New subheading" if sub else "New heading", "Section title:")
        if not title:
            return None
        self.R.snap()
        tgt = self.target if self.target in set(O.labels(self.M)) else None
        heads = O.volume_heads(self.M)
        if tgt and (sub or tgt in heads):
            lab = O.add(self.M, title, parent=tgt)
        elif tgt:
            lab = O.add(self.M, title, after=tgt)
        elif self.active_volume:
            lab = O.add(self.M, title, parent=self.active_volume)
        else:
            lab = O.add(self.M, title)
        diag.activity("qt_section_added")
        self.target = lab
        self.after(f"Section added: {lab}. It is the target: R, L or M puts the selected sentences there.")
        return lab

    def section_from_sentence(self):
        rows = self.selected()
        if not rows or self.M is None:
            self.host.status("Select the sentence to name the section with.")
            return None
        self.R.snap()
        tgt = self.target if self.target in set(O.labels(self.M)) else (self.active_volume or None)
        lab = O.from_sentence(self.M, rows[-1], parent=tgt)
        diag.activity("qt_section_added")
        self.target = lab
        self.after(f"Section added from the sentence: {lab}")
        return lab

    # ------------------------------------------------------------ text the reader missed (2.70.0)
    # ------------------------------------------------------------ 3.18.0: suggestions you ask for
    def toggle_suggest(self, on=None):
        """Suggest: what each sentence most likely is, from rules, shown dashed on the page. Off hides them; nothing
        decided changes either way."""
        on = (not self.sg_on) if on is None else bool(on)
        if on and (self.R is None or self.cx is not None):
            self.host.status("Suggest works on the documents read into the compliance matrix.")
            on = False
        self.sg_on = on
        self.sg_btn.setChecked(on)
        if on:
            n = self.run_suggest()
            diag.activity("suggest_on", n=n)
        self.sg_strip.setVisible(on)
        self.restyle(); self.show_card(self.selected()); self.show_score()
        return on

    def run_suggest(self):
        """Suggestions for every undecided sentence of the matrix that has none yet (or is still only shown). Decided
        sentences keep theirs, so the score stays true."""
        import suggestrules as SR
        ws = self.host.ws
        self.sg = SR.store(ws)
        rules = SR.all_rules(self.host.config_dir, ws)
        inh = None
        n = 0
        for it in self.M.items:
            rec = self.sg.get(it["id"])
            if it.get("decision") or (rec and rec.get("state") != "shown"):
                continue                                    # decided (by you, or from a suggestion): kept as it is
            got = SR.suggest(self.M, it, rules, inh, rfi=self.rfi)
            self.sg[it["id"]] = dict(got, state="shown")
            n += 1 if got.get("cat") else 0
        SR.save_store(ws, self.sg)
        return n

    def shown_here(self, clear_only=False):
        """The sentences of this document whose suggestion is still waiting (the clear ones only, when asked)."""
        if self.R is None or not self.file or not self.sg_on:
            return []
        out = []
        for it in self.R.rows_of(self.file):
            rec = self.sg.get(it["id"])
            if rec and rec.get("cat") and rec.get("state") == "shown" and not it.get("decision") and (rec.get("clear") or not clear_only):
                out.append(it)
        return out

    def accept_suggestions(self, clear_only=True, rows=None):
        """Accept: each sentence takes its suggestion (as if you pressed its key) and is marked as decided from a
        suggestion until someone checks it. rows: these sentences only (Enter on a selection)."""
        import suggestrules as SR
        if not self.sg_on or self.R is None or self.cx is not None:
            return 0
        rows = [it for it in (rows if rows is not None else self.shown_here(clear_only))
                if (self.sg.get(it["id"]) or {}).get("cat") and (self.sg[it["id"]].get("state") == "shown")]
        if not rows:
            self.host.status("No suggestion waiting here." if rows is not None else "No suggestion to accept.")
            return 0
        by = {}
        for it in rows:
            by.setdefault(self.sg[it["id"]]["cat"], []).append(it)
        self._accepting = True
        try:
            with self.R.group():
                for cat, its in by.items():
                    if cat in ("L", "M", "SOW", "I"):
                        self.place_reqs(its)
                        self.R.set_lm(its, {"L": "L", "M": "M", "SOW": "C", "I": "I"}[cat])
                    elif cat == "ctx":
                        self.R.ctx(its)
                    elif cat == "cust":
                        self.R.customer(its)
                    elif cat == "ignore":                            # 3.18.1: Ignore is a decision of its own
                        self.R.ignore(its)
                    for it in its:
                        self.sg[it["id"]].update(state="accepted", unchecked=True)
                        self.M.log(it["id"], f"accepted the suggestion: {SR.CAT_NAME.get(cat, cat)} ({self.sg[it['id']].get('why', '')})")
            SR.save_store(self.host.ws, self.sg)
            self.after(f"{len(rows)} suggestion(s) accepted. They stay marked until someone checks them (Select unchecked).")
        finally:
            self._accepting = False
        diag.activity("suggest_accepted", n=len(rows))
        self.show_score()
        return len(rows)

    def reject_suggestion(self, rows=None):
        """Not right: the suggestion goes; the sentence stays as it was, for you to decide."""
        import suggestrules as SR
        rows = rows if rows is not None else self.selected()
        n = 0
        for it in rows:
            rec = self.sg.get(it["id"])
            if rec and rec.get("cat") and rec.get("state") in ("shown", "accepted"):
                rec.update(state="rejected", unchecked=False)
                n += 1
        if n:
            SR.save_store(self.host.ws, self.sg)
            diag.activity("suggest_rejected", n=n)
            self.restyle(); self.show_card(self.selected()); self.show_score()
        return n

    def check_suggestion(self, rows=None):
        """Checked: a person looked at a sentence decided from a suggestion and it is right."""
        import suggestrules as SR
        rows = rows if rows is not None else self.selected()
        n = 0
        for it in rows:
            rec = self.sg.get(it["id"])
            if rec and rec.get("unchecked"):
                rec["unchecked"] = False; n += 1
        if n:
            SR.save_store(self.host.ws, self.sg)
            self.show_card(self.selected()); self.show_score()
        return n

    def select_unchecked(self):
        ids = [iid for iid, rec in self.sg.items() if rec.get("unchecked") and iid in self.view.boxes]
        sc = self.view.scene(); sc.clearSelection()
        for iid in ids:
            self.view.boxes[iid].setSelected(True)
        self.show_card(self.selected())
        self.host.status(f"{len(ids)} sentence(s) here were decided from a suggestion and not checked yet." if ids else
                         "Every suggestion accepted here has been checked.")
        return len(ids)

    def note_decided(self, rows):
        """A person decided these sentences: a suggestion they changed is marked changed, and a sentence decided from a
        suggestion counts as checked."""
        import suggestrules as SR
        if getattr(self, "_accepting", False) or not self.sg:
            return
        dirty = False
        for it in rows or []:
            rec = self.sg.get(it["id"])
            if rec is None:
                continue
            cat = SR.category(it, rec)
            if rec.get("cat") and cat and not SR.agrees(rec["cat"], cat) and rec.get("state") in ("shown", "accepted"):
                rec["state"] = "changed"; dirty = True
            if rec.get("unchecked"):
                rec["unchecked"] = False; dirty = True
        if dirty:
            SR.save_store(self.host.ws, self.sg)

    def show_score(self):
        import suggestrules as SR
        if not self.sg_on or self.R is None:
            return None
        c = SR.score(self.M.items, self.sg)
        here, clear = len(self.shown_here()), len(self.shown_here(True))
        pct = f"{c['right_pct']}% right" if c["right_pct"] is not None else "no score yet"
        self.sg_text.setText(f"<b>{here} suggestion(s) waiting here</b> ({clear} clear). Whole matrix: {c['agreed']} kept, "
                             f"{c['changed']} changed, {c['rejected']} not right, {c['missed']} missed: <b>{pct}</b>"
                             + (f". {c['unchecked']} accepted, not checked yet." if c["unchecked"] else "."))
        self.sg_clear_btn.setText(f"Accept the clear ones ({clear})"); self.sg_clear_btn.setEnabled(bool(clear))
        self.sg_all_btn.setText(f"Accept all shown ({here})"); self.sg_all_btn.setEnabled(bool(here))
        self.sg_check_btn.setEnabled(bool(c["unchecked"]))
        return c

    def make_rule(self, it=None, answer=None):
        """Teach it: a rule from this sentence (a phrase in it and what such sentences are). answer (tests):
        (phrase, cat, scope)."""
        import suggestrules as SR
        it = it or (self.selected() or [None])[-1]
        if it is None:
            return None
        rec = self.sg.get(it["id"]) or {}
        cur = SR.category(it, rec)
        if answer is None:
            from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
            d = QDialog(self); d.setWindowTitle("Make a suggestion rule"); d.setMinimumWidth(560)
            f = QFormLayout(d)
            f.addRow(D.label("Every sentence holding this phrase gets this suggestion. Keep the phrase short and true for "
                             "every RFP: a few words around the verb usually work.", "muted"))
            ph = QLineEdit(SR.phrase_from(it.get("text", ""))); f.addRow("Phrase", ph)
            cb = QComboBox()
            for k, t in SR.CATS:
                cb.addItem(t, k)
            cb.setCurrentIndex(max(0, cb.findData(cur if cur in SR.CAT_NAME else "L"))); f.addRow("Such sentences are", cb)
            sc = QComboBox(); sc.addItem("The team (every effort on this PC; a team pack shares it)", "team")
            sc.addItem("This effort only", "effort"); f.addRow("For", sc)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Make the rule")
            bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = (ph.text(), cb.currentData(), sc.currentData())
        r = SR.add_rule(self.host.config_dir, self.host.ws, *answer)
        if r is None:
            self.host.status("A rule needs a phrase of at least three letters.")
            return None
        diag.activity("suggest_rule_made")
        if self.sg_on:                                       # the rule applies at once to what is still waiting
            for x in self.M.items:
                rx = self.sg.get(x["id"])
                if rx and rx.get("state") == "shown":
                    self.sg.pop(x["id"], None)
            self.run_suggest()
            self.restyle(); self.show_score()
        self.show_card(self.selected())
        self.host.toast(f"Rule made: \"{r['phrase']}\" is {SR.CAT_NAME[r['cat']]}")
        return r

    def rules_dialog(self, run=True):
        """The suggestion rules: the team's and this effort's, each with its phrase, what it makes, who and when;
        Take out removes one."""
        import suggestrules as SR
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QAbstractItemView
        d = QDialog(self); d.setWindowTitle("Suggestion rules"); d.resize(820, 460)
        lay = QVBoxLayout(d)
        lay.addWidget(D.label("Rules come first, before the built-in ones (who acts, the verb, the RFP section). This effort's "
                              "rules win over the team's. Make one from a sentence in Review: Make a rule... on its card.", "muted"))
        t = QTableWidget(0, 5); t.setHorizontalHeaderLabels(["Phrase", "Makes", "For", "By", "Added"])
        t.setSelectionBehavior(QAbstractItemView.SelectRows); t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setColumnWidth(0, 330)
        lay.addWidget(t, 1)

        def fill():
            rs = SR.all_rules(self.host.config_dir, self.host.ws)
            t.setRowCount(0)
            for r in rs:
                k = t.rowCount(); t.insertRow(k)
                for c, v in enumerate((r["phrase"], SR.CAT_NAME.get(r["cat"], r["cat"]), "This effort" if r["scope"] == "effort" else "Team",
                                       r.get("who", ""), r.get("added", ""))):
                    t.setItem(k, c, QTableWidgetItem(v))
                t.item(k, 0).setData(Qt.UserRole, (r["phrase"], r["scope"]))
            return len(rs)

        def take_out():
            for i in sorted({x.row() for x in t.selectedIndexes()}, reverse=True):
                ph, scope = t.item(i, 0).data(Qt.UserRole)
                SR.remove_rule(self.host.config_dir, self.host.ws, ph, scope)
            fill()
        row = QHBoxLayout(); lay.addLayout(row)
        row.addWidget(D.button("Take out", "danger", take_out)); row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(d.reject); bb.accepted.connect(d.accept); row.addWidget(bb)
        d._api = {"table": t, "fill": fill, "take_out": take_out}
        fill()
        if run:
            d.exec()
            if self.sg_on:
                self.run_suggest(); self.restyle(); self.show_score()
        return d

    def suggestion_card(self, it, rows):
        """3.18.0: on the card: what was suggested and why; Accept, Not right, Checked, and Make a rule... to teach it."""
        import suggestrules as SR
        rec = self.sg.get(it["id"]) if (self.sg_on or (self.sg.get(it["id"]) or {}).get("unchecked")) else None
        if not rec or not (rec.get("cat") or SR.category(it, rec)):
            return None
        cat, state = rec.get("cat"), rec.get("state")
        now = SR.category(it, rec)
        box = QFrame(); box.setObjectName("sgCard")
        box.setStyleSheet("QFrame#sgCard{border:1px dashed rgba(22,163,74,0.6);border-radius:6px;background:rgba(22,163,74,0.05);}")
        bl = QVBoxLayout(box); bl.setContentsMargins(D.SPACE["s"], D.SPACE["xs"], D.SPACE["s"], D.SPACE["s"]); bl.setSpacing(D.SPACE["xs"])
        name = SR.CAT_NAME.get(cat, "nothing") if cat else "nothing"
        if state == "shown" and cat and not now:
            head = f"Suggested: <b>{name}</b> ({SG_KEYS.get(cat, '')})"
        elif state == "rejected":
            head = f"Suggested {name}: you said not right"
        elif state == "changed" or (cat and now and not SR.agrees(cat, now)):
            head = f"Suggested {name}; decided {SR.CAT_NAME.get(now, now) if now != 'req' else 'a requirement'}"
        elif state == "accepted":
            head = f"Decided from a suggestion: <b>{name}</b>" + (" &middot; not checked yet" if rec.get("unchecked") else " &middot; checked")
        elif not cat and now in ("L", "M", "SOW", "I", "req"):
            head = "No suggestion was made; you decided a requirement (a miss)"
        else:
            head = f"Suggested {name}"
        hl = QLabel(head); hl.setTextFormat(Qt.RichText); hl.setWordWrap(True); bl.addWidget(hl)
        if rec.get("why"):
            bl.addWidget(D.label("Why: " + rec["why"], "muted"))
        row = QHBoxLayout(); row.setSpacing(4); bl.addLayout(row)
        if state == "shown" and cat and not now:
            row.addWidget(D.button("Accept  Enter", "primary", lambda: self.accept_suggestions(rows=self.selected()),
                                   "Take the suggestion (or press its key, or another key to decide otherwise)"))
            row.addWidget(D.button("Not right", None, lambda: self.reject_suggestion(), "Leave it undecided, for you"))
        if rec.get("unchecked"):
            row.addWidget(D.button("Checked", "primary", lambda: self.check_suggestion(), "A person looked and it is right"))
        if state in ("rejected", "changed") or (cat and now and not SR.agrees(cat, now)) or (not cat and now in ("L", "M", "SOW", "I", "req")):
            row.addWidget(D.button("Make a rule...", None, lambda: self.make_rule(it),
                                   "Teach it: sentences holding a phrase from this one get the right suggestion from now on"))
        row.addStretch(1)
        self.add(box)
        self.sg_box = box
        return box

    def toggle_pan(self, on=None):
        """3.15.1: the Pan tool. Off when Add missed text is on (that drag draws a box)."""
        on = (not self.view.pan_tool) if on is None else bool(on)
        if on and self.view.capturing:
            self.toggle_capture(False)
        self.view.set_pan(on)
        self.pan_btn.setChecked(on)
        self.note.setText("Drag to move the page. H or the Pan button turns it off." if on else
                          "Click a sentence; Ctrl+click adds one (even far apart); drag a box around several. Space and drag, "
                          "or a middle-button drag, moves the page. Ctrl+wheel zooms.")
        return on

    def toggle_capture(self, on=None):
        on = (not self.view.capturing) if on is None else on
        if on and not self.pdf:
            self.host.status("Add missed text works on the page view of a document.")
            on = False
        if on and self.view.pan_tool:
            self.view.set_pan(False); self.pan_btn.setChecked(False)
        self.view.set_capture(on)
        self.cap_btn.setChecked(on)
        self.note.setText("Drag a box around the text the reader missed (Esc cancels)." if on else
                          "Click a sentence; Ctrl+click adds one (even far apart); drag a box around several. Space and drag, "
                          "or a middle-button drag, moves the page. Ctrl+wheel zooms.")
        return on

    def _page_of(self, y):
        n = 0
        for k, top in enumerate(self.tops):
            if y >= top:
                n = k
        return n

    def capture_area(self, rect, text=None, how=None, as_req=False):
        """Read the text inside an area of the page and add it as a sentence in its place. text (tests, or when nothing
        could be read): use it instead of asking. Returns the new row."""
        self.toggle_capture(False)
        if self.R is None or not self.pdf or not self.tops:
            return None
        n = self._page_of(rect.center().y())
        area = (rect.left() - MARGIN, rect.top() - self.tops[n], rect.right() - MARGIN, rect.bottom() - self.tops[n])
        got, found = "", ""
        try:
            got, found = CAP.text_in(self.pdf, n, area)
        except Exception:
            diag.swallowed()
        if text is None:
            ans = self.ask_text(got, found)
            if ans is None:
                return None
            text, as_req = ans
            how = found if text == got and found else "typed"
        how = how or found or "typed"
        above = [(b.path().boundingRect().top(), iid) for iid, b in self.view.boxes.items()
                 if b.path().boundingRect().top() <= rect.top() + 2]
        after = max(above)[1] if above else None    # nothing above it: before this file's first sentence
        place = ""
        if how == "pdf":                                # 3.29.0: boxed where it was read, not on the same words elsewhere
            try:
                place = CAP.area_place(self.pdf, n + 1, area, text)
            except Exception:
                diag.swallowed()
        self.R.snap()
        it = CAP.add_sentence(self.M, self.file, text, after_id=after, page=n + 1, how=how, at_start=after is None, area=area,
                              place=place)
        if it is None:
            return None
        diag.activity("compliance_text_added_from_page", n=1)
        self.build_boxes()
        self.select(it["id"])
        if as_req:
            self.do_req()
        self.after(f"{it['id']}: added from the page" + (" (read by OCR: check the wording)" if how == "ocr" else "")
                   + (", a compliance requirement" if as_req else ", ready to assign"))
        return it

    def ask_text(self, got, how):
        """The text found (or nothing), to check or type. Returns (text, as a requirement) or None."""
        d = QDialog(self); d.setWindowTitle("Add missed text"); d.setMinimumWidth(560)
        lay = QVBoxLayout(d)
        lay.addWidget(D.label({"pdf": "Read from the PDF's own text. Check it, then add it.",
                               "ocr": "Read by OCR from the picture of the page. Check every word, then add it."}.get(
            how, "Nothing could be read in that area. Type the text as the document shows it."), "muted"))
        ed = QPlainTextEdit(got); ed.setMinimumHeight(110); lay.addWidget(ed)
        req = QCheckBox("Make it a compliance requirement" + (f" in {self.target}" if self.target else " (no section yet)"))
        lay.addWidget(req)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Add to the review")
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        if d.exec() != QDialog.Accepted or not ed.toPlainText().strip():
            return None
        return " ".join(ed.toPlainText().split()), req.isChecked()

    def copy_rfp_section(self, with_subs=None):
        """2.69.0: hybrid structures: copy an RFP section (with its subsections) under the target, then rename or move it
        to say it our way. Returns the new labels."""
        rows = self.selected()
        if not rows or self.M is None:
            self.host.status("Select a sentence (or the heading) of the RFP section to copy.")
            return None
        it = rows[-1]
        f, num, title = SS.rfp_section_of(self.M, it)
        subs = SS.subsections(self.M, f, num)
        if with_subs is None:
            with_subs = False
            if subs:
                from PySide6.QtWidgets import QMessageBox
                ans = QMessageBox.question(self, "Copy RFP section", f"Also copy the {len(subs)} subsection(s) under "
                                           f"{num} {title}?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                if ans == QMessageBox.Cancel:
                    return None
                with_subs = ans == QMessageBox.Yes
        self.R.snap()
        tgt = self.target if self.target in set(O.labels(self.M)) else (self.active_volume or None)
        made = SS.copy_section(self.M, it, parent=tgt, with_subsections=with_subs)
        if not made:
            self.host.status("That sentence is in no RFP section to copy.")
            return None
        diag.activity("qt_rfp_section_copied", n=len(made))
        self.target = made[0]
        self.after(f"{num or 'RFP section'} copied into the structure as {made[0]}"
                   + (f" with {len(made) - 1} subsection(s)" if len(made) > 1 else "") + ". Rename or move it to say it your way.")
        return made

    # ------------------------------------------------------------ 3.19.0: parts of the structure
    def _part_volume(self):
        """The volume new part items go in: the one you are working in, else the target's, else the first."""
        heads = O.volume_heads(self.M)
        if not heads:
            return ""
        if self.active_volume in heads:
            return self.active_volume
        if self.target:
            labs = O.labels(self.M)
            i = labs.index(self.target) if self.target in labs else -1
            for j in range(i, -1, -1):
                if labs[j] in heads:
                    return labs[j]
        return next(l for l in O.labels(self.M) if l in heads)

    def add_part(self, part, title=None, counts=None):
        """Add a cover, title page, front matter item, appendix or back cover to the volume (title, counts: tests).
        3.20.1: the first appendix asks whether the RFP counts the appendices toward the page limit."""
        if self.M is None:
            return None
        if part == "appendix" and not SP.decided(self.M, "appendix") and counts is None and title is None:
            from PySide6.QtWidgets import QMessageBox
            mb = QMessageBox(self); mb.setWindowTitle("Appendices and the page limit")
            mb.setText("Does the RFP count the appendices toward the page limit?")
            mb.setInformativeText("You can change it later, for all appendices (Parts > Part rules and page limits) or for "
                                  "one (its Pages...).")
            yes = mb.addButton("They count", QMessageBox.YesRole); no = mb.addButton("They do not count", QMessageBox.NoRole)
            mb.addButton("Decide later", QMessageBox.RejectRole)
            mb.exec()
            counts = True if mb.clickedButton() is yes else False if mb.clickedButton() is no else None
        if title is None:
            if part in ("cover", "title", "back"):
                title = SP.ITEM_NAME[part]
            else:
                d = QDialog(self); d.setWindowTitle("Add a front matter item" if part == "front" else "Add an appendix")
                d.setMinimumWidth(460); f = QFormLayout(d)
                cb = QComboBox(); cb.setEditable(True)
                if part == "front":
                    cb.addItems(SP.FRONT_PRESETS)
                cb.setCurrentText("" if part != "front" else SP.FRONT_PRESETS[1])
                f.addRow("Title", cb)
                f.addRow(D.label("Unnumbered; it follows the front matter rules of Production Standards." if part == "front"
                                 else "Lettered by its place: Appendix A, B ...", "muted"))
                bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
                f.addRow(bb)
                if d.exec() != QDialog.Accepted:
                    return None
                title = cb.currentText()
        vol = self._part_volume()
        self.R.snap(f"add {SP.ITEM_NAME[part].lower()}: {title}")
        if counts is not None:
            SP.set_counts(self.M, part, counts)
        lab = O.add_part_item(self.M, part, title, vol)
        if lab is None:
            self.R.undo.pop() if self.R.undo else None
            self.host.status("Add a volume first, or pick the volume you are working in.")
            return None
        diag.activity("structure_part_added")
        self.target = lab
        self.after(f"{SP.ITEM_NAME[part]} added: {lab}" + (f" in {vol}" if vol else ""))
        return lab

    def move_to_part(self, part=None):
        """Move the target (with what is under it) to another part of its volume."""
        if not self.target or self.M is None:
            self.host.status("Click a section in your structure first.")
            return None
        if part is None:
            from PySide6.QtWidgets import QInputDialog
            names = [n for _k, n in SP.PARTS]
            cur = SP.PART_NAME[SP.part_of(self.M.outline[O.index_of(self.M, self.target)])]
            name, ok = QInputDialog.getItem(self, "Move to a part", f"{self.target} goes to:", names, names.index(cur), False)
            if not ok:
                return None
            part = dict((n, k) for k, n in SP.PARTS)[name]
        self.R.snap(f"move {self.target} to {SP.PART_NAME[part]}")
        new = O.set_part(self.M, self.target, part)
        if new is None:
            if self.R.undo:
                self.R.undo.pop()
            self.host.status("Only a volume's top sections move between parts; move this one up a level first.")
            return None
        self.target = new
        diag.activity("structure_part_moved")
        self.after(f"{new}: {SP.PART_NAME[part]}")
        return new

    def parts_dialog(self, run=True):
        """Each part's rules from Production Standards for the volume, and whether it counts toward the page limit."""
        if self.M is None:
            return None
        from PySide6.QtWidgets import QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
        vol = self._part_volume()
        sums = {k: SP.summary(SP.standard_for(self.host.config_dir, self.host.ws, vol), k) for k, _n in SP.PARTS}
        d = QDialog(self); d.setWindowTitle("Parts of the structure"); d.resize(900, 420)
        v = QVBoxLayout(d)
        v.addWidget(D.label(f"The rules each part follows{' in ' + vol if vol else ''}, from the page scheme in Production "
                            "Standards (the volume's profile and the effort type). Tick the parts the RFP counts toward "
                            "the page limit.", "muted"))
        t = QTableWidget(len(SP.PARTS), 3); t.setHorizontalHeaderLabels(["Part", "Rules (Production Standards)", "Counts toward the limit"])
        t.verticalHeader().setVisible(False); t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        t.setColumnWidth(0, 130); t.setColumnWidth(2, 170)
        boxes = {}
        for r, (k, name) in enumerate(SP.PARTS):
            it = QTableWidgetItem(name); it.setFlags(Qt.ItemIsEnabled); t.setItem(r, 0, it)
            x = QTableWidgetItem(sums[k]); x.setFlags(Qt.ItemIsEnabled); x.setToolTip(sums[k]); t.setItem(r, 1, x)
            cb = QCheckBox(); cb.setChecked(SP.counts(self.M, k)); t.setCellWidget(r, 2, cb); boxes[k] = cb
        t.resizeRowsToContents()
        v.addWidget(t, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Edit the rules", "ghost", lambda: (d.reject(), self.host.go("rules"))))   # 3.69.0
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); row.addWidget(bb)

        def save():
            self.R.snap("which parts count toward the page limit")
            for k, cb in boxes.items():
                SP.set_counts(self.M, k, cb.isChecked())
            diag.activity("structure_parts_counted")
            d.accept()
            self.after("Parts saved: " + ", ".join(SP.PART_NAME[k] for k, cb in boxes.items() if cb.isChecked()) + " count toward the page limit")
        bb.accepted.connect(save); bb.rejected.connect(d.reject)
        d._api = {"table": t, "boxes": boxes, "save": save, "sums": sums}
        if run:
            d.exec()
        return d

    def section_pages(self, label, answer=None):
        """3.18.2: a section's page length and who set it (the RFP's limit or the team's guideline). answer (tests):
        (pages, 'rfp' or 'team'[, counts: None to follow its part, True or False]); 0 pages takes it off. 3.20.1: whether
        this section counts toward the page limit (an appendix the RFP counts, say). Returns the tag shown, or None."""
        if not label or self.M is None or label not in set(O.labels(self.M)):
            self.host.status("Click a section in your structure first.")
            return None
        if answer is None:
            from PySide6.QtWidgets import QDoubleSpinBox, QRadioButton
            d = QDialog(self); d.setWindowTitle("Pages for the section"); d.setMinimumWidth(460)
            f = QFormLayout(d)
            f.addRow(D.label(label, "label"))
            sp = QDoubleSpinBox(); sp.setRange(0, 2000); sp.setSingleStep(PB.STEP); sp.setDecimals(1); sp.setSpecialValueText("not set")
            sp.setValue(PB.pages(self.M, label) or 0); sp.setSuffix(" pages")
            f.addRow("Pages", sp)
            cur = PB.source(self.M, label) or "team"
            rb = {}
            for key, name in PB.SOURCES:
                rb[key] = QRadioButton(name + (": the customer sets it" if key == "rfp" else ": what our authors aim for"))
                rb[key].setChecked(key == cur); f.addRow("" if key != "team" else "Set by", rb[key])
            part = SP.label_part(self.M).get(label, "body")
            cnt = QComboBox()
            cnt.addItem(f"As its part ({SP.PART_NAME[part]}: {'counts' if SP.counts(self.M, part) else 'not counted'})", None)
            cnt.addItem("Counts toward the page limit", True); cnt.addItem("Does not count toward the page limit", False)
            cnt.setCurrentIndex({None: 0, True: 1, False: 2}[SP.item_count(self.M, label)])
            f.addRow("Page limit", cnt)
            f.addRow(D.label("Subsections are included. The Page budget splits a volume's limit across its sections.", "muted"))
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            f.addRow(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = (sp.value(), "rfp" if rb["rfp"].isChecked() else "team", cnt.currentData())
        n, src = answer[0], answer[1]
        self.R.snap(f"pages for {label}")
        PB.set_pages(self.M, label, n, src)
        if len(answer) > 2:
            SP.set_item_count(self.M, label, answer[2])
        diag.activity("section_pages_set")
        tag = PB.tag(self.M, label)
        self.after(f"{label}: " + (f"{PB.fmt(PB.pages(self.M, label))} page(s), {PB.SOURCE_NAME[PB.source(self.M, label)].lower()}"
                                   if tag else "no page length"))
        return tag

    def structure_menu(self, label):
        """3.29.0: the right-click menu of a section in the structure; the section becomes the target first."""
        from PySide6.QtWidgets import QMenu
        m = QMenu(self)
        if not label or self.M is None:
            return m
        self.set_target(label)
        m.addAction("Rename...", lambda: self.rename_section(label))
        m.addAction("Pages...", lambda: self.section_pages(label))
        m.addSeparator()
        m.addAction("+ Heading after it", lambda: self.new_section(sub=False))
        m.addAction("+ Subheading under it", lambda: self.new_section(sub=True))
        m.addSeparator()
        m.addAction("Up", lambda: self.outline_op(O.move, -1))
        m.addAction("Down", lambda: self.outline_op(O.move, 1))
        m.addAction("One level down", lambda: self.outline_op(O.indent))
        m.addAction("One level up", lambda: self.outline_op(O.outdent))
        m.addAction("Move to a part...", lambda: self.move_to_part())
        m.addSeparator()                                              # 3.75.0: what the buttons under the tree did
        m.addAction("+ Section from the selected sentence", lambda: self.section_from_sentence())
        m.addAction("Copy the RFP section of the selected sentence", lambda: self.copy_rfp_section())
        pm = m.addMenu("Parts")
        for a in self.parts_btn.menu().actions():
            pm.addAction(a)
        m.addSeparator()
        m.addAction("Delete", lambda: self.delete_section())
        return m

    def rename_section(self, label, title=None):
        if not label or self.M is None:
            return None
        o = next((x for x in self.M.outline if C.outline_label(x) == label), None)
        if o is None:
            return None
        title = title if title is not None else self._ask("Rename", f"New title for {label}:", o.get("title", ""))
        if not title:
            return None
        self.R.snap()
        new = O.rename(self.M, label, title)
        try:                                          # 2.84.0: library context follows the section's new name
            import ctxdocs as CX
            CX.Store(self.host.ws.root).load().rename_section(label, new)
        except Exception:
            diag.swallowed()
        if label in O.volume_heads(self.M) or self.active_volume == label:
            self.active_volume = new if self.active_volume == label else self.active_volume
        self.target = new
        self.after(f"Renamed: {new}")
        return new

    def outline_op(self, fn, *args):
        if not self.target or self.M is None:
            self.host.status("Click a section in your structure first.")
            return None
        self.R.snap()
        new = fn(self.M, self.target, *args)
        if new is None:
            if self.R.undo:                           # nothing changed: no step to undo
                self.R.undo.pop()
            self.host.status("It cannot go there.")
            return None
        self.target = new
        self.after(f"Moved: {new}")
        return new

    def delete_section(self, label=None):
        label = label or self.target
        if not label or self.M is None:
            return None
        self.R.snap()
        to = O.delete(self.M, label)
        if self.active_volume == label:
            self.active_volume = ""
        self.target = to or None
        diag.activity("qt_section_removed")
        self.after(f"Section {label} taken out" + (f"; its sentences are in {to}" if to else "; its sentences have no section now"))
        return to

    def do_for_req(self):
        """2.84.0: F, a library sentence as context for a compliance requirement."""
        if self.cx is None:
            return self.host.status("F is for library documents: open one from the File list (Library: ...).")
        return self.cx.for_requirement()

    def do_record(self, kind):
        """2.84.0: N, Q, T: a note, a question or a task from a library sentence."""
        if self.cx is None:
            return self.host.status("N, Q and T are for library documents: open one from the File list (Library: ...).")
        return self.cx.record(kind)

    def do_ctx(self):
        if self.cx is not None:
            return self.cx.attach("section")
        rows = self.selected()
        if rows:
            self.R.ctx(rows)
            diag.activity("compliance_assigned", n=len(rows))
            self.after(f"{len(rows)} sentence(s): support for {rows[0].get('context_for') or 'nothing yet (+ Requirement on the card)'}")

    def do_customer(self):
        if self.cx is not None:
            return self.host.status("G is for the matrix's documents.")
        rows = self.selected()
        if rows:
            self.R.customer(rows)
            self.after(f"{len(rows)} sentence(s): the customer's")

    def do_clear(self):
        """X: ignored, a decision of its own (3.18.1: grey on the page, counted as decided)."""
        if self.cx is not None:
            return self.cx.clear()
        rows = self.selected()
        if rows:
            self.R.ignore(rows)
            diag.activity("compliance_ignored", n=len(rows))
            self.after(f"{len(rows)} sentence(s): ignored")
            return len(rows)
        return 0

    def do_undecide(self):
        """3.18.1 Delete: the decision comes off; the sentence is undecided again."""
        if self.cx is not None:
            return self.cx.undecide()
        rows = self.selected()
        if rows:
            self.R.clear(rows)
            self.after(f"{len(rows)} sentence(s): not decided")
            return len(rows)
        return 0

    def do_combine(self):
        if self.cx is not None:
            return self.host.status("Combine and Split are for the matrix's documents.")
        rows = self.selected()
        if len(rows) < 2:
            self.host.status("Select two or more sentences (Ctrl+click or drag), then M.")
            return
        first = self.R.combine(rows, self.placed)
        diag.activity("compliance_merged", n=len(rows))
        self.build_boxes()
        self.select(first["id"])
        self.after(f"Combined {len(rows)} sentences into {first['id']}")

    def do_split(self):
        if self.cx is not None:
            return self.host.status("Combine and Split are for the matrix's documents.")
        rows = self.selected()
        if len(rows) != 1:
            self.host.status("Select one sentence, click the word to split before, then S.")
            return
        at = self.split_at
        if at is None:                                     # 3.20.3: no word clicked: split exactly where you click in the text
            at = self.ask_split_at(rows[0])
            if at is None:
                return
        parts = self.R.split(rows[0], at)
        if not parts:
            self.host.status("Click the word to split before (in the selected sentence), then S.")
            return
        diag.activity("compliance_split", n=len(parts))
        self.clear_split(card=False)
        self.build_boxes()
        self.select(parts[0]["id"])
        self.after(f"Split into {', '.join(p['id'] for p in parts)}")

    def ask_split_at(self, it, answer=None):
        """3.20.3: the sentence's text with a cursor: click where the second part starts (inside a word, at its very start
        or end, between glued sentences) and Split there. answer (tests): the character position. Returns it or None."""
        if answer is not None:
            return answer
        from PySide6.QtWidgets import QPlainTextEdit
        d = QDialog(self); d.setWindowTitle("Split exactly here"); d.setMinimumWidth(620)
        lay = QVBoxLayout(d)
        lay.addWidget(D.label("Click where the second part starts, then Split. Any character works: inside a word, at its very "
                              "start or end, or between two sentences the reader joined.", "muted"))
        ed = QPlainTextEdit(it.get("text", "")); ed.setReadOnly(True); ed.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        ed.setMinimumHeight(140); lay.addWidget(ed)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Split")
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); lay.addWidget(bb)
        if d.exec() != QDialog.Accepted:
            return None
        return ed.textCursor().position()

    def do_extract(self, grab=None):
        """3.20.3 Shift+S: the words dragged across become a sentence of their own (the rest stays as the parts before and
        after), selected and ready to assign. Returns the new sentence."""
        if self.cx is not None:
            return self.host.status("Make a sentence is for the documents being shredded.")
        if grab is None and getattr(self, "grab_multi", None):     # 3.28.1: words from several sentences: one sentence
            return self.extract_multi(self.grab_multi)
        g = grab or self.grab
        it = self.R.item(g["iid"]) if g else None
        if it is None or "s" not in g:
            self.host.status("Drag across the words inside a sentence first, then Make a sentence (Shift+S).")
            return None
        mid = self.R.extract(it, g["s"], g["e"])
        if mid is None:
            self.host.status("Those words are the whole sentence already.")
            return None
        diag.activity("compliance_extracted")
        self.clear_grab()
        self.keys["Make"].setEnabled(False)
        self.clear_split(card=False)
        self.build_boxes()
        self.select(mid["id"])
        self.after(f"{mid['id']}: extracted, ready to assign")
        return mid

    def extract_multi(self, pieces):
        """3.28.1: the words picked in several sentences become one sentence: each piece is split from its sentence (the
        words before and after stay where they were), then the pieces are combined, in the document's order. One Undo
        step. Returns the new sentence."""
        mids = []
        with self.R.group():
            for p in pieces:
                it = self.R.item(p["iid"])
                if it is None:
                    continue
                text = it.get("text", "")
                if not text[:p["s"]].strip() and not text[p["e"]:].strip():
                    mids.append(it)                                 # the whole sentence: it comes as it is
                    continue
                mid = self.R.extract(it, p["s"], p["e"])
                if mid is not None:
                    mids.append(mid)
            first = self.R.combine(mids, self.placed) if len(mids) > 1 else (mids[0] if mids else None)
        if first is None:
            self.host.status("Nothing to extract there.")
            return None
        diag.activity("compliance_extracted", n=len(mids))
        self.clear_grab()
        self.keys["Make"].setEnabled(False)
        self.clear_split(card=False)
        self.build_boxes()
        self.select(first["id"])
        self.after(f"{first['id']}: the picked words from {len(mids)} sentences, one sentence now, ready to assign")
        return first

    def undo_text(self):
        """3.18.2: what Undo would put back on this page ('' for nothing): the top bar's Undo says it."""
        if self.cx is not None and self.cx_hist:
            return self.cx_hist[-1]["label"]
        return self.R.undo_label() if self.R is not None else ""

    def undo_here(self):
        return self.do_undo()

    def do_undo(self):
        """Ctrl+Z (the window's) or Undo: the last change on this page, decisions and the structure alike (3.18.2)."""
        if self.cx is not None and self.cx_hist:
            return self.cx.undo()
        label = self.R.undo_label() if self.R else ""
        if self.R and self.R.undo_last():
            diag.activity("compliance_undo")
            keep = [it["id"] for it in self.selected()]          # 3.0.4: the selection stays after Undo
            self.build_boxes()
            self._guard = True
            for iid in keep:
                b = self.view.boxes.get(iid)
                if b is not None:
                    b.setSelected(True)
            self._guard = False
            self.cur = keep[-1] if keep else self.cur
            labs = set(O.labels(self.M))
            if self.target and self.target not in labs:          # the section it targeted was the one undone
                self.target = None
            if self.active_volume and self.active_volume not in labs:
                self.active_volume = ""
            self._undoing = True
            try:
                self.after(f"Undone: {label}")
            finally:
                self._undoing = False
            return label
        self.host.status("Nothing to undo.")
        return None


def change_html(ch):
    """2.98.0: the old wording with what the new version took out struck through in red and what it put in, green."""
    import html
    out = []
    for kind, text in ch.get("diff") or [("-", ch.get("old", ""))]:
        t = html.escape(text)
        if kind == "-":
            out.append(f"<span style='color:#B91C1C;text-decoration:line-through'>{t}</span>")
        elif kind == "+":
            out.append(f"<span style='color:#15803D;font-weight:600'>{t}</span>")
        else:
            out.append(t)
    return " ".join(out)


class OldPageDialog(QDialog):
    """2.98.0: the previous version's page, the old sentence highlighted (Show the old page in Review)."""

    def __init__(self, parent, pdf, found, title, old_text):
        super().__init__(parent)
        from PySide6.QtWidgets import QLabel, QScrollArea
        from PySide6.QtGui import QPainter
        import pypdfium2 as pdfium
        self.setWindowTitle(title)
        self.resize(900, 900)
        v = QVBoxLayout(self)
        self.found = found
        if found is None:
            v.addWidget(D.label("The old sentence was not found on the old version's pages (its words may be laid out "
                                "differently). Its wording: " + old_text, "muted"))
            page_i, rects = 0, []
        else:
            page_i, rects = found
            v.addWidget(D.label(f"Page {page_i + 1}: the old sentence is highlighted.", "muted"))
        scale = 1.6
        doc = pdfium.PdfDocument(pdf)
        try:
            img = doc[page_i].render(scale=scale).to_pil().convert("RGB")
        finally:
            doc.close()
        q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
        pix = QPixmap.fromImage(q)
        p = QPainter(pix)
        col = QColor("#F59E0B"); col.setAlpha(90)
        p.setBrush(col); p.setPen(QPen(QColor("#D97706"), 2))
        for l, t, r, b in rects:
            p.drawRect(QRectF(l * scale - 2, t * scale - 2, (r - l) * scale + 4, (b - t) * scale + 4))
        p.end()
        self.image = QLabel(); self.image.setPixmap(pix)
        area = QScrollArea(); area.setWidget(self.image); area.setWidgetResizable(False)
        v.addWidget(area, 1)
        if rects:
            area.ensureVisible(int(rects[0][0] * scale), int(rects[0][1] * scale), 50, 200)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); v.addWidget(bb)


def sentence_work(rec, iid):
    """2.99.0: [("task", task) or ("question", note)] about one sentence, open ones first."""
    out = [("task", t) for t in rec.data.get("tasks", []) if t.get("about") == f"sentence:{iid}"]
    out += [("question", n) for n in rec.data.get("notes", []) if n.get("on") == "requirement" and n.get("on_id") == iid]
    return sorted(out, key=lambda kx: (kx[1].get("status") == "Done" or bool(kx[1].get("resolved")), kx[1].get("at", kx[1].get("created", ""))))

