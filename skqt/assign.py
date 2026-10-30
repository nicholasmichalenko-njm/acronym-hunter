"""Assign in Qt (2.59.0): the customer document as it looks, every page in one scroll, each review sentence a box you
click; Ctrl+click adds or takes out a sentence; drag a rubber band around several (Ctrl+drag adds); Ctrl+wheel zooms.
Headers and footers have no box. Labels in the left margin say what each sentence is. Beside the page: the sentence
card (source, decision, author(s), relationships, notes) and the response structure (click a section: the target for
R). Keys: R requirement, L and E (M) the Shipley designation, C support, G customer's, X ignore, J combine (2.68.0;
M before), S split (where you clicked in the selected
sentence), Ctrl+Z undo. 2.68.0: the structure is built beside the page as you assign, volume by volume. Every decision goes through assign_ops, the same rules as the tkinter edition.
"""
import os, re
from PySide6.QtCore import Qt, QEvent, QRectF, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGraphicsItem, QGridLayout,
                               QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsSimpleTextItem,
                               QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QRadioButton,
                               QScrollArea, QSplitter, QStyle, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
                               QCheckBox, QButtonGroup)
import diag
import effortrec as R_
import compliance as C
import setupdoc as SD
import pagesent as PS
import matrixdesign as MD
import outline_ops as O
import structstart as SS
import capture as CAP
import office_pdf as OP
from . import design as D

SCALE = 2.0          # pixels per PDF point in the page pictures (sharp when zoomed in)
GAP = 24             # between pages, in points
MARGIN = 160         # the label margin left of the pages, in points
SHEET_X = 8          # 2.96.0: Sheet view starts near the left edge (its row numbers are its labels)
WORD = re.compile(r"[A-Za-z0-9]+")


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

    def style(self, dec=None, current=None):
        self.dec = self.dec if dec is None else dec
        self.current = self.current if current is None else current
        col = QColor(D.PAGE_DEC.get(self.dec, D.PAGE_DEC[""]))
        sel = self.isSelected()
        fill = QColor("#FDE68A") if (sel and not self.dec) else QColor(col)
        fill.setAlpha((140 if sel else 0) if not self.dec else (115 if sel else 70))
        self.setBrush(QBrush(fill))
        pen = QPen(QColor("#F59E0B") if self.current else (col if self.dec else QColor("#CBD5E1")))
        pen.setWidthF(2.6 if self.current else (1.4 if (self.dec or sel or self.hover) else 0.7))
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
    captured = Signal(QRectF)                     # 2.70.0: an area dragged in Add missed text mode (scene coordinates)

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

    def set_capture(self, on):
        self.capturing = on
        self.setDragMode(QGraphicsView.NoDrag if on else QGraphicsView.RubberBandDrag)
        self.viewport().setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)

    def box_at(self, pos):
        """The sentence box under a view position, looking past marks drawn over it (tints, the cut line)."""
        return next((i for i in self.items(pos) if isinstance(i, SentenceBox)), None)

    def word_at(self, pos):
        """(sentence id, word index) under a view position, inside the one selected sentence; ("", -1) otherwise."""
        it = self.box_at(pos)
        sel = [b for b in self.scene().selectedItems() if isinstance(b, SentenceBox)]
        if not (isinstance(it, SentenceBox) and len(sel) == 1 and sel[0] is it):
            return "", -1
        p = self.mapToScene(pos)
        for k, r in enumerate(self.words.get(it.iid, [])):
            if r.adjusted(-1, -1, 1, 1).contains(p):
                return it.iid, k
        return it.iid, -1

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:     # 2.96.0: dragging across words
            iid, k, k2 = self.word_at(e.position().toPoint())[0], self._drag[1], self.word_at(e.position().toPoint())[1]
            if iid == self._drag[0] and k2 >= 0 and k2 != self._drag[2]:
                self._drag = (iid, k, k2)
                self.word_drag.emit(iid, min(k, k2), max(k, k2))
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
        if e.modifiers() & Qt.ControlModifier:
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            if 0.3 < self.zoom * f < 5:
                self.zoom *= f
                self.scale(f, f)
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e):
        if self.capturing and e.button() == Qt.LeftButton:
            self._cap0 = self.mapToScene(e.position().toPoint())
            return
        top = self.itemAt(e.position().toPoint())
        if top is not None and top.isWidget():           # the Split here bar: its buttons take the click
            return super().mousePressEvent(e)
        it = self.box_at(e.position().toPoint())
        sel = [b for b in self.scene().selectedItems() if isinstance(b, SentenceBox)]
        if isinstance(it, SentenceBox) and len(sel) == 1 and sel[0] is it and not (e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
            p = self.mapToScene(e.position().toPoint())
            for k, r in enumerate(self.words.get(it.iid, [])):
                if r.adjusted(-1, -1, 1, 1).contains(p):
                    self._drag = (it.iid, k, k)       # 2.96.0: decided on release: a click (split) or a drag (words)
                    break
            return                                  # a click inside the selected sentence keeps it selected
        super().mousePressEvent(e)

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

    def run(self):
        import ocrpdf
        ocr = [p for p in self.paths if ocrpdf.needs_copy(p)]             # 2.96.0: pictures and scanned PDFs
        office = [p for p in self.paths if p not in ocr]
        res = {}
        try:
            res.update(OP.make_many(office, self.folder) if office else {})
        except Exception:
            diag.swallowed()
            res.update({p: RuntimeError("Office could not save a PDF copy") for p in office})
        for p in ocr:
            try:
                ocrpdf.make(p, self.folder)
                res[p] = ""
            except Exception:
                diag.swallowed()
                res[p] = RuntimeError("the words on the page could not be read")
        self.done.emit({p: (str(r) if isinstance(r, Exception) else "") for p, r in res.items()})


Chip = D.Chip


class AssignPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host                           # the main window: review, matrix, workspace, changed(), status()
        self.file = None
        self.pdf = ""
        self.placed = {}
        self.tops = []
        self.labels = []
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
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(QLabel("File:"))
        self.files = QComboBox(); self.files.setMinimumWidth(280); self.files.currentTextChanged.connect(self.open_file)
        bar.addWidget(self.files)
        self.queue_lbl = D.label("", "muted", wrap=False); bar.addWidget(self.queue_lbl)       # 2.96.0: the documents as a queue
        self.done_btn = D.button("Mark reviewed", None, lambda: self.mark_reviewed(), "This document's sentences are all looked at")
        self.next_btn = D.button("Next document \u203a", None, lambda: self.next_file(), "The next document not reviewed yet")
        bar.addWidget(self.done_btn); bar.addWidget(self.next_btn)
        self.keys = {}
        # 2.82.0: sentence edits stay by the page; the decisions sit beside the response structure, where they land
        for text, kind, fn, tip in (("Combine  J", None, self.do_combine, "One sentence from the selected ones (they need not be next to each other)"),
                                    ("Split  S", None, self.do_split, "Split the selected sentence before the word you clicked"),
                                    ("Undo  Ctrl+Z", "ghost", self.do_undo, "Put back the last change")):
            b = D.button(text, kind, fn, tip)
            self.keys[text.split()[0]] = b
            bar.addWidget(b)
        self.keys["Split"].setEnabled(False)
        self.keys["Split"].setToolTip("Select a sentence, then click the word the second part starts with: a red line "
                                      "shows the split, and this button (or S) makes it")
        bar.addStretch(1)
        self.cap_btn = D.button("Add missed text", None, lambda: self.toggle_capture(),
                                "Drag a box around text the reader missed: Stationkeeper reads it (the PDF's text, else OCR) "
                                "and adds it as a sentence in its place, ready to assign")
        self.cap_btn.setCheckable(True)
        bar.addWidget(self.cap_btn)
        self.sheet_on, self.sheet = True, None          # 2.96.0: Excel files open in Sheet view
        self.sheet_btn = D.button("Page view", None, lambda: self.toggle_sheet(), "Switch an Excel file between its cells (Sheet "
                                  "view) and its PDF copy (Page view)")
        self.sheet_btn.setVisible(False)
        bar.addWidget(self.sheet_btn)
        fit = QPushButton("Fit width"); fit.clicked.connect(lambda: self.view.fit()); bar.addWidget(fit)
        self.note = D.label("", "muted"); v.addWidget(self.note)
        self.view = PageView()
        self.view.scene().selectionChanged.connect(self.on_select)
        self.view.clicked_word.connect(self.on_word)
        self.view.hover_word.connect(self.on_hover_word)
        self.view.word_drag.connect(lambda i, a, b: self.show_grab(i, a, b, final=False))
        self.view.grabbed.connect(lambda i, a, b: self.show_grab(i, a, b, final=True))
        self.grab, self._grab_items = None, []
        self._split_items, self._hover_item = [], None
        self.view.captured.connect(lambda r: self.capture_area(r))
        right = QSplitter(Qt.Vertical)
        self.card_area = QScrollArea(); self.card_area.setWidgetResizable(True)
        self.card_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.card = QWidget(); self.card_lay = QVBoxLayout(self.card); self.card_lay.setAlignment(Qt.AlignTop)
        self.card_area.viewport().installEventFilter(self)              # wrapped text keeps its height; the card scrolls
        self.card_area.setWidget(self.card)
        sw = QWidget(); sv = QVBoxLayout(sw); sv.setContentsMargins(0, 0, 0, 0)
        dec = QFrame(); dec.setProperty("card", True); dv = QVBoxLayout(dec)       # 2.82.0: decide, next to the structure
        dv.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["s"]); dv.setSpacing(D.SPACE["xs"])
        self.target_lbl = D.label("", None); self.target_lbl.setTextFormat(Qt.RichText); dv.addWidget(self.target_lbl)
        grid = QGridLayout(); grid.setSpacing(D.SPACE["xs"]); grid.setContentsMargins(0, 0, 0, 0)
        self.dec_box = dec
        for k, (text, kind, fn, tip) in enumerate((
                ("L (Instructions)  L", "req", lambda: self.do_lm("L"), "L: Instructions, Conditions and Notices to Offerors. A compliance "
                 "requirement in the target section. Key: L"),
                ("M (Evaluation)  E", "req", lambda: self.do_lm("M"), "M: Evaluation Factors for Award. A compliance requirement in the "
                 "target section. Key: E"),
                ("SOW (Work)  R", "req", lambda: self.do_sow(), "What the contractor shall do (Section C, SOW, PWS). A compliance "
                 "requirement in the target section. Key: R"),
                ("Support  C", "ctx", self.do_ctx, "Supporting context for the last requirement you clicked"),
                ("Customer's  G", "cust", self.do_customer, "The customer's to act on: identified, never answered"),
                ("Ignore  X", None, self.do_clear, "Ignore it: no decision, not in the response"))):
            b = D.button(text, kind, fn, tip)
            self.keys[{"L": "L", "M": "M", "SOW": "Requirement"}.get(text.split()[0], text.split()[0])] = b
            grid.addWidget(b, k // 3, k % 3)
        self.dec_grid = QWidget(); self.dec_grid.setLayout(grid)
        dv.addWidget(self.dec_grid)
        caprow = QHBoxLayout(); caprow.setSpacing(D.SPACE["xs"])           # 2.96.0: capture what the sentence holds
        caprow.addWidget(D.label("Capture", "label", wrap=False))
        self.cap_keys = {}
        for key, text, tip in (("contact", "Contact", "A point of contact: name, title, e-mail, phone, address (Customer information)"),
                               ("submit", "Submission", "A submission instruction: due date and time, delivery, copies, file format"),
                               ("format", "Formatting", "A formatting rule: page limit, font, margins, page size, spacing"),
                               ("acronym", "Acronym", "The acronym and what it stands for, into the effort list")):
            b = D.button(text, "ghost", lambda _=False, k=key: self.do_capture(k), tip + ". Uses the words you dragged across, "
                         "else the selected sentence.")
            self.cap_keys[key] = b
            caprow.addWidget(b)
        caprow.addStretch(1)
        dv.addLayout(caprow)
        cgrid = QGridLayout(); cgrid.setSpacing(D.SPACE["xs"])                # 2.84.0: for a library document
        self.ctx_keys = {}
        for k, (text, kind, fn, tip) in enumerate((
                ("Context for section  C", "ctx", lambda: self.do_ctx(), "Context for the target section: shows in the section and in Response Setup"),
                ("For a requirement  F", "ctx", lambda: self.do_for_req(), "Context for a compliance requirement of the target section"),
                ("Make it a requirement  R", "req", lambda: self.do_req(), "Into the matrix as a compliance requirement in the target section"),
                ("Note  N", None, lambda: self.do_record("note"), "A note in the effort record, quoting it"),
                ("Question  Q", "cust", lambda: self.do_record("question"), "A question for the customer, quoting it"),
                ("Task  T", None, lambda: self.do_record("task"), "A task in the effort record, quoting it"),
                ("Ignore  X", None, lambda: self.do_clear(), "Ignore it: take its attachments off"))):
            b = D.button(text, kind, fn, tip)
            self.ctx_keys[text.split("  ")[0]] = b
            cgrid.addWidget(b, k // 3, k % 3)
        self.ctx_grid = QWidget(); self.ctx_grid.setLayout(cgrid); self.ctx_grid.hide()
        dv.addWidget(self.ctx_grid)
        sv.addWidget(dec)
        vrow = QHBoxLayout(); sv.addLayout(vrow)                       # 2.68.0: the volume you are working on
        vrow.addWidget(D.label("Volume", "label", wrap=False))
        self.volume = QComboBox(); self.volume.setMinimumWidth(200)
        self.volume.activated.connect(lambda _i: self.pick_volume(self.volume.currentData()))
        vrow.addWidget(self.volume, 1)
        vrow.addWidget(D.button("+ Volume", None, lambda: self.new_volume(), "A new volume at the end of the structure"))
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Your response structure (click a section: the target)", "Req.", "Ctx"])
        self.tree.setColumnWidth(0, 380)
        self.tree.itemClicked.connect(lambda i, _c: self.set_target(i.data(0, Qt.UserRole)))
        self.tree.itemDoubleClicked.connect(lambda i, _c: self.rename_section(i.data(0, Qt.UserRole)))
        sv.addWidget(self.tree)
        srow = QHBoxLayout(); srow.setSpacing(4); sv.addLayout(srow)
        for text, fn, tip in (("+ Heading", lambda: self.new_section(sub=False), "A section at the level of the target (after it), or a first section"),
                              ("+ Subheading", lambda: self.new_section(sub=True), "A section under the target, one level down"),
                              ("From sentence", lambda: self.section_from_sentence(), "A section under the target, named with the selected sentence"),
                              ("Copy RFP section", lambda: self.copy_rfp_section(),
                               "The RFP section the selected sentence is in (and its subsections, if you want) under the "
                               "target, titled as the RFP titles it; its requirements with no section yet go into it")):
            srow.addWidget(D.button(text, None, fn, tip))
        srow.addStretch(1)
        row = QHBoxLayout(); row.setSpacing(4); sv.addLayout(row)
        for text, fn, tip in (("Rename", lambda: self.rename_section(self.target), "Rename the target (or double-click it)"),
                              ("\u2191", lambda: self.outline_op(O.move, -1), "Up"), ("\u2193", lambda: self.outline_op(O.move, 1), "Down"),
                              ("\u2192", lambda: self.outline_op(O.indent), "One level down (under the section above)"),
                              ("\u2190", lambda: self.outline_op(O.outdent), "One level up"),
                              ("Delete", lambda: self.delete_section(), "Take the target out; its sentences go to the section above")):
            b = D.button(text, "ghost" if text != "Delete" else "danger", fn, tip)
            if len(text) == 1:
                b.setFixedWidth(34)
            row.addWidget(b)
        row.addStretch(1)
        for text, fn in (("People...", self.people_dialog), ("Volumes...", self.volumes_dialog)):
            b = QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        self.active_volume = ""
        right.addWidget(self.card_area); right.addWidget(sw); right.setSizes([440, 540])
        split = QSplitter(Qt.Horizontal); split.addWidget(self.view); split.addWidget(right); split.setSizes([1100, 470])
        v.addWidget(split, 1)
        self.notes_timer = QTimer(self, singleShot=True, interval=700, timeout=self.save_notes)
        for key, fn in (("R", lambda: self.do_sow()), ("C", self.do_ctx), ("G", self.do_customer), ("X", self.do_clear),
                        ("L", lambda: self.do_lm("L")), ("E", lambda: self.do_lm("M")), ("Shift+M", lambda: self.do_lm("M")),
                        ("Delete", self.do_clear), ("J", self.do_combine), ("S", self.do_split), ("Ctrl+Z", self.do_undo),
                        ("F", lambda: self.do_for_req()), ("N", lambda: self.do_record("note")),
                        ("Q", lambda: self.do_record("question")), ("T", lambda: self.do_record("task")),
                        ("Escape", lambda: self.toggle_capture(False) if self.view.capturing else
                         (self.clear_split() if self.split_at is not None else self.view.scene().clearSelection()))):
            QShortcut(QKeySequence(key), self.view, activated=fn)
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
        self.fill_file_list()
        self.cx = None
        self.fill_tree()
        if self.R and self.R.files():
            self.open_file(self.R.files()[0])
        else:
            self.view.scene().clear()
            self.view.boxes = {}

    # ------------------------------------------------------------ 2.96.0 the customer documents as a queue
    def reviewed(self):
        return dict(self.host.ws.get("assign_reviewed", {}) or {}) if self.host.ws is not None else {}

    def show_queue(self):
        files = self.R.files() if self.R else []
        if not files or self.cx is not None or self.file not in files:
            self.queue_lbl.setText(""); self.done_btn.setVisible(False); self.next_btn.setVisible(False)
            return
        done = self.reviewed()
        left = [f for f in files if f not in done]
        here = self.file in done
        self.queue_lbl.setText(f"Document {files.index(self.file) + 1} of {len(files)}  ·  "
                               + (f"{len(left)} not reviewed yet" if left else "all reviewed"))
        self.done_btn.setVisible(True); self.next_btn.setVisible(bool([f for f in left if f != self.file]))
        self.done_btn.setText("Reviewed \u2713" if here else "Mark reviewed")
        self.done_btn.setToolTip(f"Marked reviewed {done[self.file]}. Click to take the mark off." if here else
                                 "This document's sentences are all looked at")

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
        self.files.blockSignals(True)
        self.files.clear()
        self.lib_entries = {}
        if self.R:
            self.files.addItems(self.R.files())
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
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(self.pdf)
        y = 0.0
        try:
            for i in range(len(doc)):
                page = doc[i]
                w, h = page.get_size()
                img = page.render(scale=SCALE).to_pil().convert("RGB")
                q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
                pix = QGraphicsPixmapItem(QPixmap.fromImage(q))
                pix.setTransformationMode(Qt.SmoothTransformation)
                pix.setScale(1 / SCALE)
                pix.setPos(MARGIN, y)
                pix.setZValue(-1)
                sc.addItem(pix)
                t = sc.addSimpleText(f"Page {i + 1}"); t.setPos(MARGIN - 60, y); t.setBrush(QColor("#64748B"))
                self.tops.append(y)
                y += h + GAP
        finally:
            doc.close()
        self.build_boxes()
        self.note.setText("Click a sentence; Ctrl+click adds one (even far apart); drag a box around several. Ctrl+wheel zooms.")
        QTimer.singleShot(0, self.view.fit)

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
        for iid, rs in rects.items():
            box = SentenceBox(iid, rs)
            sc.addItem(box)
            self.view.boxes[iid] = box
        self.restyle()

    # ------------------------------------------------------------ drawing decisions
    def restyle(self):
        if self.cx is not None:
            return self.cx.restyle()
        sc = self.view.scene()
        for lab in self.labels:
            sc.removeItem(lab)
        self.labels = []
        last_y = -100.0
        for iid, box in sorted(self.view.boxes.items(), key=lambda kv: kv[1].boundingRect().top()):
            it = self.R.item(iid)
            if it is None:
                continue
            dec = it.get("decision", "")
            box.style(dec if dec in D.PAGE_DEC else "", iid == self.cur)
            tag = D.decision(dec)[2]
            if not tag:
                continue
            y = max(box.boundingRect().top(), last_y + 11)
            last_y = y
            hosts = C.cf_ids(it.get("context_for", "")) if dec == "Context" else []
            txt = f"{tag} {', '.join(hosts[:2])}" if hosts else f"{tag} {iid}"
            if dec == "Keep":                                           # 2.68.0: L or M and its volumes in the margin
                lmv = it.get("lm") or ""
                vols = [v.split(" ")[1] if v.lower().startswith("volume ") and len(v.split(" ")) > 1 else v[:6] for v in O.volumes_of_item(self.M, it)]
                txt = " ".join(x for x in (tag, lmv, iid, ("V " + "+".join(vols)) if vols else "") if x)
            lab = QGraphicsSimpleTextItem(txt)
            lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
            lab.setBrush(QColor(D.PAGE_DEC[dec]))
            lab.setPos(MARGIN - 8 - lab.boundingRect().width(), y)
            sc.addItem(lab)
            self.labels.append(lab)

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
        tail = re.match(r"[\w@.\-]*", text[ms[b].end():]).group(0)        # an e-mail or a number runs on past the word
        self.grab = {"iid": iid, "a": a, "b": b, "text": text[ms[a].start():ms[b].end() + len(tail)].strip(" ,;:").rstrip(".")}
        self.clear_split(card=False)
        self.host.status(f"Picked: \"{self.grab['text'][:80]}\". Capture uses these words; click elsewhere to drop them.")
        self.show_card(self.selected())
        return self.grab

    def capture_source(self):
        """(text, source) for a capture: the words dragged across, else the selected sentences."""
        rows = self.selected()
        if self.grab and any(it["id"] == self.grab["iid"] for it in rows):
            it = next(it for it in rows if it["id"] == self.grab["iid"])
            text = self.grab["text"]
        elif rows:
            it = rows[0]
            text = " ".join(x.get("text", "") for x in rows)
        else:
            return "", {}
        place = self.placed.get(it["id"], ("",))[0] or it.get("place", "")
        loc = (PS.where_text(self.pdf, place) if (self.pdf and place) else "") or " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        return text, {"doc": it.get("file", "") or (self.file or ""), "loc": loc, "text": it.get("text", "")}

    def do_capture(self, kind, answer=None):
        """Contact, Submission, Formatting or Acronym from the picked words or the selected sentence. answer (tests): the
        dialog's values."""
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
        return None

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
            b.setEnabled(True); b.setText("Split here  S")
        self.view.ensureVisible(px, 40, 60)

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

    def show_card(self, rows):
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
        kind = "Heading" if it.get("type") == "Heading" and not d else d
        tone, label, _tag = D.decision(kind)
        top = QWidget(); th = QHBoxLayout(top); th.setContentsMargins(0, 0, 0, 0); th.setSpacing(D.SPACE["s"])
        k = D.Pill(label, tone if tone != "faint" else "head")
        th.addWidget(k)
        if len(rows) > 1:
            th.addWidget(D.label(f"and {len(rows) - 1} more selected", "muted", wrap=False))
        th.addStretch(1)
        idl = D.label(it["id"], "mono", wrap=False); th.addWidget(idl)
        self.add(top)
        self.kind_label = k
        t = self.add(D.label(it.get("text", ""), "reading"))
        t.setTextInteractionFlags(Qt.TextSelectableByMouse)
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
                    pk = self.add(D.label(f"Picked words: \u201c{self.grab['text']}\u201d. Capture (Contact, Submission, "
                                          "Formatting, Acronym) uses them.", None))
                    pk.setStyleSheet("background:rgba(134,239,172,0.35);padding:4px;border-radius:4px;")
                else:
                    self.add(D.label("To split it, click the word the second part starts with. To capture part of it, drag "
                                     "across those words.", "muted"))
        self.head("Source")
        place = self.placed.get(it["id"], ("",))[0] or it.get("place", "")
        where = PS.where_text(self.pdf, place) if (self.pdf and place) else MD._where(it)
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        ref, _how = SD.ref_of(M, it)
        src = [f"File: {it.get('file', '')}"] + ([f"Where: {where}"] if where else []) + ([f"RFP: {sec}"] if sec else []) \
            + ([f"Referenced as: {ref}"] if ref and ref != it.get("section") else []) + [f"ID: {it['id']}    Type: {it.get('type', '')}"]
        self.source_label = self.add(D.label("\n".join(src)))
        ident = SD.docs_of(M).get(it.get("file", "")) or {}
        idl2 = (f"Document {ident.get('initial')} ({ident.get('type', '')})" if ident.get("initial") else
                "This document has no initial and type yet: set them in Customer Documents.")
        self.ident_label = self.add(D.label(idl2, "muted" if ident.get("initial") else None))
        if d == "Keep":                                                 # 2.68.0: L or M, and the reference it makes
            lmw = QWidget(); lh = QHBoxLayout(lmw); lh.setContentsMargins(0, 0, 0, 0); lh.setSpacing(D.SPACE["s"])
            cur_lm = it.get("lm", "")
            sug, why = SD.lm_why(M, it)
            for code in ("L", "M", "C"):
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
        if d == "Keep":
            secs = SD.item_sections(M, it)
            for lab in secs:
                self.chips.append(self.add(Chip(lab, "req", on_remove=lambda _=False, l=lab: self.act(self.R.remove_section, it, l))))
            if not secs:
                self.add(QLabel("No section yet: click one in your structure (or build one: + Heading), then R."))
            cb = QComboBox(); cb.addItem("+ Section")
            cb.addItems([lab for lab in self.R.labels() if lab not in secs])
            cb.activated.connect(lambda i, cb=cb: self.act(self.R.add_section, it, cb.itemText(i)) if i > 0 else None)
            self.add(cb)
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
        elif d == "Customer":
            self.add(QLabel("Counted, never answered and never put in the response."))
        else:
            self.add(QLabel("L, M or SOW (keys L, E, R): a requirement in the target section.  C: support for the last requirement you clicked.  G: the customer's."))
        self.head("Author(s)")
        on = d in ("Keep", "Context")
        from .people import NamesField                  # 2.77.0: authors come from the author list only
        ed = self.add(NamesField(self.host, SD.split_names(it.get("owner", "")), empty="(the section's lead)", title="Authors",
                                 on_change=lambda names, rows=rows: self.set_authors(rows, ", ".join(names))))
        ed.setEnabled(on)
        self.authors = ed
        lead = SD.section_people(M, it.get("map", "")).get("lead", "") if it.get("map") else ""
        if on and not it.get("owner"):
            self.add(D.label(f"Empty: the section lead writes it ({lead})." if lead else "Empty: the section's lead, once one is named (People...).", "muted"))
        self.head("Relationships")
        ids, how = self.R.related(it)
        if not ids:
            self.add(D.label("None yet.", "muted"))
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
        if self.R.set_authors(rows, text):
            diag.activity("assign_card_authors", n=len(rows))
            self.host.changed()

    def act(self, fn, *a):
        fn(*a)
        self.after()

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

    def pick_volume(self, vol):
        """Work in one volume: the structure shows its sections, and new sections go into it."""
        self.active_volume = vol or ""
        if self.target and self.active_volume and self.target not in O.in_volume(self.M, self.active_volume):
            self.target = None
        self.fill_tree()
        self.host.status(f"Working in {vol}." if vol else "Showing every volume.")

    def fill_tree(self):
        self.tree.clear()
        if self.R is None:
            self.show_target()
            return
        self.fill_volumes()
        counts = self.R.counts()
        ctxn = self._ctx_counts()
        show = set(O.in_volume(self.M, self.active_volume))
        stack = []
        for o in self.M.outline:
            lab = C.outline_label(o)
            if lab not in show:
                continue
            lvl = o.get("level", 1)
            node = QTreeWidgetItem([lab, str(counts.get(lab, "") or ""), str(ctxn.get(lab, "") or "")])
            if ctxn.get(lab):
                node.setToolTip(2, f"{ctxn[lab]} sentence(s) from library documents attached as context")
            node.setData(0, Qt.UserRole, lab)
            if lab == self.target:
                f = node.font(0); f.setBold(True); node.setFont(0, f)
                node.setBackground(0, D.color("warn_soft")); node.setForeground(0, D.color("text"))
            while stack and stack[-1][0] >= lvl:
                stack.pop()
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

    def set_target(self, lab):
        self.target = lab
        self.host.status(f"Target: {lab}. R puts the selected sentences there.")
        self.fill_tree()

    def people_dialog(self):
        if self.M is None or not self.M.outline:
            return None
        d = QDialog(self); d.setWindowTitle("People for each section"); d.resize(720, 520)
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel("A lead and contributors, from the author list. Requirements in a section and its subsections "
                             "take its lead as author unless they have their own."))
        from .people import NamesField, combo_name, empty_text, name_combo
        if not self.host.people():                     # 2.77.0: the author list is the only source of names
            warn = D.label(empty_text(self.host), "crit"); warn.setWordWrap(True); lay.addWidget(warn)
        area = QScrollArea(); area.setWidgetResizable(True); inner = QWidget(); form = QFormLayout(inner); area.setWidget(inner)
        lay.addWidget(area, 1)
        rows = []
        for o in self.M.outline:
            lab = C.outline_label(o)
            pp = SD.setup_of(self.M)["owners"].get(lab) or {}
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
            le = name_combo(self.host, pp.get("lead", ""))
            we = NamesField(self.host, SD.split_names(pp.get("with", "")), empty="(no contributors)", title=f"Contributors: {lab}")
            h.addWidget(le, 1); h.addWidget(we, 2)
            form.addRow(("    " * max(0, o.get("level", 1) - 1)) + lab, w)
            rows.append((lab, le, we))
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); lay.addWidget(bb)
        bb.rejected.connect(d.reject)

        def save():
            self.R.snap()
            for lab, le, we in rows:
                SD.set_people(self.M, lab, combo_name(le), we.text())
            self.M.pending = True
            diag.activity("compliance_people_set", n=len(rows))
            d.accept()
            self.after()
        bb.accepted.connect(save)
        d._api = {"rows": rows, "save": save}
        d.show()
        return d

    def volumes_dialog(self):
        """One volume (a name, or blank) or several (the headings of the structure that start a volume)."""
        if self.M is None:
            return None
        mode, name, heads = SD.volumes_of(self.M)
        d = QDialog(self); d.setWindowTitle("Volumes"); d.resize(560, 520)
        lay = QVBoxLayout(d)
        one, sev = QRadioButton("One volume"), QRadioButton("Several volumes: tick the headings that start one")
        g = QButtonGroup(d); g.addButton(one); g.addButton(sev)
        (sev if mode == "several" else one).setChecked(True)
        lay.addWidget(one)
        nm = QLineEdit(name); nm.setPlaceholderText("its name (or leave blank)"); lay.addWidget(nm)
        lay.addWidget(sev)
        area = QScrollArea(); area.setWidgetResizable(True); inner = QWidget(); iv = QVBoxLayout(inner); area.setWidget(inner)
        boxes = []
        for o in self.M.outline:
            lab = C.outline_label(o)
            cb = QCheckBox(("    " * max(0, o.get("level", 1) - 1)) + lab); cb.setChecked(lab in heads); iv.addWidget(cb)
            boxes.append((lab, cb))
        lay.addWidget(area, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); lay.addWidget(bb)
        bb.rejected.connect(d.reject)

        def save():
            if sev.isChecked():
                hs = [lab for lab, cb in boxes if cb.isChecked()]
                if not hs:
                    self.host.status("Tick at least one heading that starts a volume.")
                    return
                SD.set_volumes(self.M, "several", "", hs)
            else:
                SD.set_volumes(self.M, "one", nm.text().strip(), [])
            self.M.pending = True
            diag.activity("compliance_volumes_set")
            d.accept()
            self.host.changed()
        bb.accepted.connect(save)
        d._api = {"one": one, "several": sev, "name": nm, "boxes": boxes, "save": save}
        d.show()
        return d

    # ------------------------------------------------------------ actions
    def after(self, msg=""):
        self.restyle()
        self.fill_tree()
        self.show_card(self.selected())
        self.host.changed()
        if msg:
            self.host.status(msg)

    def do_req(self):
        if self.cx is not None:
            return self.cx.promote()
        rows = self.selected()
        if not rows:
            return
        n = self.R.req(rows, self.target or "")
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
        n = self.R.req(rows, self.target or "")
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
        if new:
            self.R.req(new, self.target or "")
        self.R.set_lm(rows, lm)
        diag.activity("compliance_lm_set", n=len(rows))
        self.after(f"{len(rows)} sentence(s): {SD.LM_SHORT.get(lm, lm)} ({SD.LM[lm]})")

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
    def toggle_capture(self, on=None):
        on = (not self.view.capturing) if on is None else on
        if on and not self.pdf:
            self.host.status("Add missed text works on the page view of a document.")
            on = False
        self.view.set_capture(on)
        self.cap_btn.setChecked(on)
        self.note.setText("Drag a box around the text the reader missed (Esc cancels)." if on else
                          "Click a sentence; Ctrl+click adds one (even far apart); drag a box around several. Ctrl+wheel zooms.")
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
        self.R.snap()
        it = CAP.add_sentence(self.M, self.file, text, after_id=after, page=n + 1, how=how, at_start=after is None)
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
            self.host.status("It cannot go there.")
            return None
        self.target = new
        self.after()
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
        if self.cx is not None:
            return self.cx.clear()
        rows = self.selected()
        if rows:
            self.R.clear(rows)
            self.after(f"{len(rows)} sentence(s): ignored")

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
        parts = self.R.split(rows[0], self.split_at)
        if not parts:
            self.host.status("Click the word to split before (in the selected sentence), then S.")
            return
        diag.activity("compliance_split", n=len(parts))
        self.clear_split(card=False)
        self.build_boxes()
        self.select(parts[0]["id"])
        self.after(f"Split into {', '.join(p['id'] for p in parts)}")

    def do_undo(self):
        if self.R and self.R.undo_last():
            diag.activity("compliance_undo")
            self.build_boxes()
            self.after("Undone.")
        else:
            self.host.status("Nothing to undo.")
