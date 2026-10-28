"""Assign in Qt (2.59.0): the customer document as it looks, every page in one scroll, each review sentence a box you
click; Ctrl+click adds or takes out a sentence; drag a rubber band around several (Ctrl+drag adds); Ctrl+wheel zooms.
Headers and footers have no box. Labels in the left margin say what each sentence is. Beside the page: the sentence
card (source, decision, author(s), relationships, notes) and the response structure (click a section: the target for
R). Keys: R requirement, C support, G customer's, X not used, M combine, S split (where you clicked in the selected
sentence), Ctrl+Z undo. Every decision goes through assign_ops, the same rules as the tkinter edition.
"""
import os, re
from PySide6.QtCore import Qt, QRectF, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QComboBox, QCompleter, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGraphicsItem,
                               QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsSimpleTextItem,
                               QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QRadioButton,
                               QScrollArea, QSplitter, QStyle, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
                               QCheckBox, QButtonGroup)
import diag
import compliance as C
import setupdoc as SD
import pagesent as PS
import matrixdesign as MD
import office_pdf as OP
from . import theme as T

SCALE = 2.0          # pixels per PDF point in the page pictures (sharp when zoomed in)
GAP = 24             # between pages, in points
MARGIN = 160         # the label margin left of the pages, in points
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
        col = QColor(T.DEC.get(self.dec, T.DEC[""])[0])
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

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.setBackgroundBrush(QColor("#E2E8F0"))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.boxes = {}
        self.words = {}                            # sentence id -> [scene rects of its words, in order]
        self.zoom = 1.0

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            if 0.3 < self.zoom * f < 5:
                self.zoom *= f
                self.scale(f, f)
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e):
        it = self.itemAt(e.position().toPoint())
        sel = [b for b in self.scene().selectedItems() if isinstance(b, SentenceBox)]
        if isinstance(it, SentenceBox) and len(sel) == 1 and sel[0] is it and not (e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
            p = self.mapToScene(e.position().toPoint())
            for k, r in enumerate(self.words.get(it.iid, [])):
                if r.adjusted(-1, -1, 1, 1).contains(p):
                    self.clicked_word.emit(it.iid, k)
                    break
            return                                  # a click inside the selected sentence keeps it selected
        super().mousePressEvent(e)

    def fit(self):
        r = self.scene().itemsBoundingRect()
        if r.width() > 0:
            self.resetTransform()
            self.zoom = max(0.3, (self.viewport().width() - 30) / r.width())
            self.scale(self.zoom, self.zoom)


class CopyWorker(QThread):
    """PDF copies of Word, Excel and PowerPoint files, made by Office on this PC (one session per program)."""
    done = Signal(dict)

    def __init__(self, paths, folder):
        super().__init__()
        self.paths, self.folder = paths, folder

    def run(self):
        try:
            res = OP.make_many(self.paths, self.folder)
        except Exception:
            diag.swallowed()
            res = {p: RuntimeError("Office could not save a PDF copy") for p in self.paths}
        self.done.emit({p: (str(r) if isinstance(r, Exception) else "") for p, r in res.items()})


class Chip(QFrame):
    def __init__(self, text, color, on_remove=None, on_jump=None):
        super().__init__()
        self.setObjectName("chip")
        self.setStyleSheet(f"QFrame#chip{{background:{color};border-radius:11px}} QLabel{{background:transparent}}")
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 2, 4, 2)
        self.label = QLabel(text)
        h.addWidget(self.label, 1)
        if on_jump:
            b = QToolButton(text="Jump"); b.setAutoRaise(True); b.clicked.connect(on_jump); h.addWidget(b)
        if on_remove:
            b = QToolButton(text="×"); b.setAutoRaise(True); b.setStyleSheet("color:#DC2626;font-weight:bold")
            b.setToolTip("Take it out"); b.clicked.connect(on_remove); h.addWidget(b)
            self.remove = b


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
        self.split_at = None
        self.notes = None
        self._guard = False
        self.conv = set()
        self.conv_err = {}
        self.workers = []
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(QLabel("File:"))
        self.files = QComboBox(); self.files.setMinimumWidth(280); self.files.currentTextChanged.connect(self.open_file)
        bar.addWidget(self.files)
        for text, color, fn in (("Requirement  R", "#15803D", self.do_req), ("Support  C", "#1D4ED8", self.do_ctx),
                                ("Customer's  G", "#7E22CE", self.do_customer), ("Not used  X", "#475569", self.do_clear),
                                ("Combine  M", "#475569", self.do_combine), ("Split  S", "#475569", self.do_split),
                                ("Undo  Ctrl+Z", "#475569", self.do_undo)):
            b = QPushButton(text); b.setObjectName("key"); b.setStyleSheet(f"background:{color}"); b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addStretch(1)
        fit = QPushButton("Fit width"); fit.clicked.connect(lambda: self.view.fit()); bar.addWidget(fit)
        self.note = QLabel(""); self.note.setObjectName("muted"); v.addWidget(self.note)
        self.view = PageView()
        self.view.scene().selectionChanged.connect(self.on_select)
        self.view.clicked_word.connect(self.on_word)
        right = QSplitter(Qt.Vertical)
        self.card_area = QScrollArea(); self.card_area.setWidgetResizable(True)
        self.card_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.card = QWidget(); self.card_lay = QVBoxLayout(self.card); self.card_lay.setAlignment(Qt.AlignTop)
        self.card_area.setWidget(self.card)
        sw = QWidget(); sv = QVBoxLayout(sw); sv.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Your response structure (click: the target for R)", "Req."])
        self.tree.setColumnWidth(0, 310)
        self.tree.itemClicked.connect(lambda i, _c: self.set_target(i.data(0, Qt.UserRole)))
        sv.addWidget(self.tree)
        row = QHBoxLayout(); sv.addLayout(row)
        for text, fn in (("People...", self.people_dialog), ("Volumes...", self.volumes_dialog)):
            b = QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        row.addStretch(1)
        right.addWidget(self.card_area); right.addWidget(sw); right.setSizes([620, 360])
        split = QSplitter(Qt.Horizontal); split.addWidget(self.view); split.addWidget(right); split.setSizes([1100, 470])
        v.addWidget(split, 1)
        self.notes_timer = QTimer(self, singleShot=True, interval=700, timeout=self.save_notes)
        for key, fn in (("R", self.do_req), ("C", self.do_ctx), ("G", self.do_customer), ("X", self.do_clear),
                        ("Delete", self.do_clear), ("M", self.do_combine), ("S", self.do_split), ("Ctrl+Z", self.do_undo),
                        ("Escape", lambda: self.view.scene().clearSelection())):
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
        self.files.blockSignals(True)
        self.files.clear()
        if self.R:
            self.files.addItems(self.R.files())
        self.files.blockSignals(False)
        self.fill_tree()
        if self.R and self.R.files():
            self.open_file(self.R.files()[0])
        else:
            self.view.scene().clear()
            self.view.boxes = {}

    def copies_dir(self):
        ws = self.host.ws
        return ws.p("page copies") if ws is not None else ""

    def pdf_of(self, f):
        """(pdf, why not)."""
        path = self.M.path_of(f)
        if not path:
            return "", f"{f} is not on this PC"
        if path.lower().endswith(".pdf"):
            return path, ""
        if not OP.kind(path):
            return "", "Page view shows PDF, Word, Excel and PowerPoint files"
        folder = self.copies_dir()
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
        paths = [p for p in (self.M.path_of(f) for f in self.R.files()) if p and OP.kind(p) and p not in self.conv]
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
        self.file = f
        self.pdf, why = self.pdf_of(f)
        sc = self.view.scene()
        sc.clear()
        self.view.boxes, self.view.words, self.labels, self.tops = {}, {}, [], []
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

    def build_boxes(self):
        sc = self.view.scene()
        for b in self.view.boxes.values():
            sc.removeItem(b)
        self.view.boxes, self.view.words = {}, {}
        rows = self.R.rows_of(self.file)
        try:
            self.placed = PS.place_all(self.pdf, rows)
        except Exception:
            diag.swallowed()
            self.placed = {}
        heads = [x for x in self.M.headings if x.get("file") in ("", None, self.file)]
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
            box.style(dec if dec in T.DEC else "", iid == self.cur)
            tag = T.DEC.get(dec, T.DEC[""])[2]
            if not tag:
                continue
            y = max(box.boundingRect().top(), last_y + 11)
            last_y = y
            hosts = C.cf_ids(it.get("context_for", "")) if dec == "Context" else []
            txt = f"{tag} {', '.join(hosts[:2])}" if hosts else f"{tag} {iid}"
            lab = QGraphicsSimpleTextItem(txt)
            lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
            lab.setBrush(QColor(T.DEC[dec][0]))
            lab.setPos(MARGIN - 8 - lab.boundingRect().width(), y)
            sc.addItem(lab)
            self.labels.append(lab)

    def selected(self):
        if self.R is None:
            return []
        ids = [b.iid for b in self.view.scene().selectedItems() if isinstance(b, SentenceBox)]
        order = {it["id"]: k for k, it in enumerate(self.M.items)}
        return [x for x in (self.R.item(i) for i in sorted(ids, key=lambda i: order.get(i, 0))) if x]

    def on_select(self):
        if self._guard or self.R is None:
            return
        self.save_notes()
        rows = self.selected()
        self.split_at = None
        self.cur = rows[-1]["id"] if rows else None
        if len(rows) == 1 and rows[0].get("decision") == "Keep":
            self.R.last_req = rows[0]["id"]
        self.restyle()
        self.show_card(rows)

    def select(self, iid):
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

    def on_word(self, iid, k):
        it = self.R.item(iid)
        if it is None:
            return
        ms = list(WORD.finditer(it.get("text", "")))      # the boxes hold the sentence's words in order, page by page
        if 0 < k < len(ms):
            self.split_at = ms[k].start()
            self.host.status(f"S splits {iid} before \"{ms[k].group(0)}\".")
        else:
            self.split_at = None
            self.host.status("Click a word after the first one: S splits the sentence before it.")

    # ------------------------------------------------------------ the card
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
        l = self.add(QLabel(text)); l.setObjectName("h")
        return l

    def show_card(self, rows):
        self.clear_card()
        self.notes = None
        if self.R is None or not rows:
            self.add(QLabel("Click a sentence on the page. Ctrl+click adds more; drag a box around several."))
            return
        M = self.M
        dark = T.is_dark(self.host.app)
        it = rows[-1]
        d = it.get("decision", "")
        kind = "Heading" if it.get("type") == "Heading" and not d else d
        color, label, _tag = T.DEC.get(kind, T.DEC[""])
        k = self.add(QLabel(f"{label}" + (f"   (and {len(rows) - 1} more selected)" if len(rows) > 1 else "")))
        k.setObjectName("kind"); k.setStyleSheet(f"background:{color}")
        self.kind_label = k
        t = self.add(QLabel(it.get("text", ""))); t.setStyleSheet("font-family:Georgia;font-size:14px;margin:6px 0")
        self.head("Source")
        place = self.placed.get(it["id"], ("",))[0] or it.get("place", "")
        where = PS.where_text(self.pdf, place) if (self.pdf and place) else MD._where(it)
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        ref, _how = SD.ref_of(M, it)
        src = [f"File: {it.get('file', '')}"] + ([f"Where: {where}"] if where else []) + ([f"RFP: {sec}"] if sec else []) \
            + ([f"Referenced as: {ref}"] if ref and ref != it.get("section") else []) + [f"ID: {it['id']}    Type: {it.get('type', '')}"]
        self.source_label = self.add(QLabel("\n".join(src)))
        self.head("Decision")
        self.chips = []
        if d == "Keep":
            secs = SD.item_sections(M, it)
            for lab in secs:
                self.chips.append(self.add(Chip(lab, T.chip(dark, "req"), on_remove=lambda _=False, l=lab: self.act(self.R.remove_section, it, l))))
            if not secs:
                self.add(QLabel("No section yet: click one in your structure, then R."))
            cb = QComboBox(); cb.addItem("+ Section")
            cb.addItems([lab for lab in self.R.labels() if lab not in secs])
            cb.activated.connect(lambda i, cb=cb: self.act(self.R.add_section, it, cb.itemText(i)) if i > 0 else None)
            self.add(cb)
        elif d == "Context":
            for i in C.cf_ids(it.get("context_for", "")):
                x = self.R.item(i)
                self.chips.append(self.add(Chip(f"{i}   {x.get('map', '') if x else ''}", T.chip(dark, "ctx"),
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
            self.add(QLabel("R: requirement (in the target section).  C: support for the last requirement you clicked.  G: the customer's."))
        self.head("Author(s)")
        ed = self.add(QLineEdit(", ".join(SD.split_names(it.get("owner", "")))))
        ed.setPlaceholderText("names, separated by commas (empty: the section's lead)")
        on = d in ("Keep", "Context")
        ed.setEnabled(on)
        comp = QCompleter(self.host.people()); comp.setCaseSensitivity(Qt.CaseInsensitive); ed.setCompleter(comp)
        ed.editingFinished.connect(lambda ed=ed: self.set_authors(rows, ed.text()))
        self.authors = ed
        lead = SD.section_people(M, it.get("map", "")).get("lead", "") if it.get("map") else ""
        if on and not it.get("owner"):
            n = self.add(QLabel(f"Empty: the section lead writes it ({lead})." if lead else "Empty: the section's lead, once one is named (People...)."))
            n.setObjectName("muted")
        self.head("Relationships")
        ids, how = self.R.related(it)
        if not ids:
            self.add(QLabel("None yet."))
        self.rel_labels = []
        for i in ids:
            x = self.R.item(i)
            if x is None:
                continue
            role = "REQ" if how == "hosts" else "SUPPORT"
            b = QLabel(f"<a href='{i}'><b>{role} {i}</b></a> ({MD.ctx_ref(M, x)}) {x['text'][:140]}")
            b.setTextFormat(Qt.RichText)
            b.setStyleSheet("border:1px solid palette(mid);border-radius:6px;padding:6px")
            b.linkActivated.connect(lambda href: self.select(href))
            self.rel_labels.append(self.add(b))
        self.head("Notes")
        self.notes = self.add(QPlainTextEdit(it.get("notes", "")))
        self.notes.setFixedHeight(72)
        self.notes_for = it["id"]
        self.notes.textChanged.connect(self.notes_timer.start)

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

    def set_authors(self, rows, text):
        if self.R.set_authors(rows, text):
            diag.activity("assign_card_authors", n=len(rows))
            self.host.changed()

    def act(self, fn, *a):
        fn(*a)
        self.after()

    # ------------------------------------------------------------ the structure
    def fill_tree(self):
        self.tree.clear()
        if self.R is None:
            return
        counts = self.R.counts()
        stack = []
        for o in self.M.outline:
            lab = C.outline_label(o)
            lvl = o.get("level", 1)
            node = QTreeWidgetItem([lab, str(counts.get(lab, "") or "")])
            node.setData(0, Qt.UserRole, lab)
            if lab == self.target:
                f = node.font(0); f.setBold(True); node.setFont(0, f)
                node.setBackground(0, QColor("#FEF3C7")); node.setForeground(0, QColor("#0F172A"))
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            (stack[-1][1].addChild(node) if stack else self.tree.addTopLevelItem(node))
            stack.append((lvl, node))
        self.tree.expandAll()

    def set_target(self, lab):
        self.target = lab
        self.host.status(f"Target: {lab}. R puts the selected sentences there.")
        self.fill_tree()

    def people_dialog(self):
        if self.M is None or not self.M.outline:
            return None
        d = QDialog(self); d.setWindowTitle("People for each section"); d.resize(720, 520)
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel("A lead and contributors (names separated by commas). Requirements in a section and its subsections "
                             "take its lead as author unless they have their own."))
        area = QScrollArea(); area.setWidgetResizable(True); inner = QWidget(); form = QFormLayout(inner); area.setWidget(inner)
        lay.addWidget(area, 1)
        rows = []
        team = self.host.people()
        for o in self.M.outline:
            lab = C.outline_label(o)
            pp = SD.setup_of(self.M)["owners"].get(lab) or {}
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
            le = QComboBox(); le.setEditable(True); le.addItems([""] + team); le.setCurrentText(pp.get("lead", ""))
            we = QLineEdit(pp.get("with", "")); we.setPlaceholderText("contributors")
            h.addWidget(le, 1); h.addWidget(we, 2)
            form.addRow(("    " * max(0, o.get("level", 1) - 1)) + lab, w)
            rows.append((lab, le, we))
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); lay.addWidget(bb)
        bb.rejected.connect(d.reject)

        def save():
            self.R.snap()
            for lab, le, we in rows:
                SD.set_people(self.M, lab, le.currentText(), we.text())
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
        rows = self.selected()
        if not rows:
            return
        if not self.target:
            self.host.status("Click a section in your structure first (the target for R).")
            return
        n = self.R.req(rows, self.target)
        diag.activity("compliance_assigned", n=n)
        self.after(f"{rows[0]['id'] if n == 1 else str(n) + ' sentences'}: compliance requirement in {self.target}")

    def do_ctx(self):
        rows = self.selected()
        if rows:
            self.R.ctx(rows)
            diag.activity("compliance_assigned", n=len(rows))
            self.after(f"{len(rows)} sentence(s): support for {rows[0].get('context_for') or 'nothing yet (+ Requirement on the card)'}")

    def do_customer(self):
        rows = self.selected()
        if rows:
            self.R.customer(rows)
            self.after(f"{len(rows)} sentence(s): the customer's")

    def do_clear(self):
        rows = self.selected()
        if rows:
            self.R.clear(rows)
            self.after(f"{len(rows)} sentence(s): not used")

    def do_combine(self):
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
        rows = self.selected()
        if len(rows) != 1:
            self.host.status("Select one sentence, click the word to split before, then S.")
            return
        parts = self.R.split(rows[0], self.split_at)
        if not parts:
            self.host.status("Click the word to split before (in the selected sentence), then S.")
            return
        diag.activity("compliance_split", n=len(parts))
        self.split_at = None
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
