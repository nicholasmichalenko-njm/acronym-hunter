"""Stationkeeper Assign in PySide6: a test program (2.58 prototype), run beside the real app to judge whether Qt makes
assigning smoother. It opens an effort's compliance matrix (the same .xlsx Stationkeeper keeps) and shows:
- Page view: every page of the customer document in one scroll, each review sentence a box you can click; Ctrl+click
  adds or takes out a sentence; drag a rubber band to select several (Ctrl+drag adds); Ctrl+wheel zooms smoothly.
  Headers and footers have no box. Labels in the left margin say what each sentence is.
- The sentence card: source (file, page and paragraph, RFP reference), decision (sections as chips with x, + Section;
  supported requirements as chips), author(s) (several, the team offered), relationships with RFP places, notes.
- Your response structure: click a section to make it the target; R puts the selected sentences there.
Keys: R requirement, C support (for the last requirement you clicked), G customer's, X not used, M combine,
Ctrl+Z undo, Ctrl+S save. Nothing leaves the PC; rules only (No AI). The shipped app is not changed.

Run: venv\\Scripts\\python.exe prototypes\\assign_qt.py [matrix.xlsx]
"""
import copy, glob, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AH_TEST", "")

from PySide6.QtCore import Qt, QRectF, QTimer, QPointF
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QImage, QKeySequence, QPainterPath, QPen, QPixmap, QShortcut, QPainter
from PySide6.QtWidgets import (QApplication, QComboBox, QCompleter, QFileDialog, QFrame, QGraphicsItem, QGraphicsPathItem,
                               QGraphicsPixmapItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QSplitter, QToolBar, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import compliance as C
import setupdoc as SD
import pagesent as PS
import matrixdesign as MD
import office_pdf as OP

SCALE = 2.0                      # pixels per PDF point in the page pictures (sharp when zoomed in)
GAP = 24                         # between pages, in points
MARGIN = 150                     # the label margin left of the pages, in points
DEC = {"Keep": ("#16A34A", "Compliance requirement", "REQ"), "Context": ("#2563EB", "Supporting context", "SUPPORTS"),
       "Customer": ("#7E22CE", "The customer's (identified, not answered)", "CUSTOMER'S"), "": ("#94A3B8", "Not used", "")}


# ------------------------------------------------------------------ the matrix and every change to it
class Store:
    def __init__(self, path):
        self.path = path
        self.M = C.Matrix(path).load()
        self.undo = []
        self.dirty = False
        self.last_req = None
        self.backed_up = False

    def item(self, iid):
        return next((it for it in self.M.items if it.get("id") == iid), None)

    def files(self):
        out = []
        for it in self.M.items:
            if it.get("file") and it["file"] not in out:
                out.append(it["file"])
        return out

    def rows_of(self, f):
        return [it for it in self.M.items if it.get("file") == f]

    def snap(self):
        self.undo.append((copy.deepcopy(self.M.items), copy.deepcopy(SD.setup_of(self.M))))
        del self.undo[:-40]

    def changed(self):
        C.link_contexts(self.M.items)
        self.dirty = True

    def undo_last(self):
        if not self.undo:
            return False
        items, setup = self.undo.pop()
        self.M.items[:] = items
        self.M.setup = setup
        self.dirty = True
        return True

    # decisions
    def req(self, rows, label):
        known = {C.outline_label(o) for o in self.M.outline}
        if not rows or label not in known:
            return 0
        self.snap()
        new = [it for it in rows if it.get("decision") != "Keep" or not it.get("map")]
        for it in new:
            SD.clear_sections(self.M, it)
        if new:
            C.assign_requirement(self.M.items, new, label)
        for it in rows:
            if it not in new:
                SD.add_section(self.M, it, label)
            self.M.log(it["id"], f"compliance requirement in {label}")
        if len(rows) == 1:
            self.last_req = rows[0]["id"]
        self.changed()
        return len(rows)

    def ctx(self, rows):
        if not rows:
            return 0
        self.snap()
        last = self.item(self.last_req) if self.last_req else None
        if last is not None and (last.get("decision") != "Keep" or last in rows):
            last = None
        for it in rows:
            d = last["id"] if last is not None else C.default_context_for(self.M.items, it)
            SD.clear_sections(self.M, it)
            C.assign_context(self.M.items, [it], [d] if d else [])
            self.M.log(it["id"], f"context for {it.get('context_for', '')}")
        self.changed()
        return len(rows)

    def customer(self, rows):
        self.snap()
        C.assign_customer(self.M.items, rows)
        for it in rows:
            SD.clear_sections(self.M, it)
        self.changed()

    def clear(self, rows):
        self.snap()
        C.clear_assignment(self.M.items, rows)
        for it in rows:
            SD.clear_sections(self.M, it)
        self.changed()

    def combine(self, rows, placed):
        if len(rows) < 2:
            return None
        self.snap()
        for r in rows:
            if not r.get("place") and r["id"] in placed:
                r["place"] = placed[r["id"]][0]
        first = C.merge_items(self.M.items, [r["id"] for r in rows])
        self.changed()
        return first

    def add_section(self, it, label):
        self.snap()
        SD.add_section(self.M, it, label)
        self.changed()

    def remove_section(self, it, label):
        self.snap()
        SD.remove_section(self.M, it, label)
        self.changed()

    def unlink(self, sup, req_id):
        self.snap()
        ids = [i for i in C.cf_ids(sup.get("context_for", "")) if i != req_id]
        C.assign_context(self.M.items, [sup], ids, section=None if ids else (sup.get("map") or None))
        self.changed()

    def link(self, sup, req_id):
        self.snap()
        ids = C.cf_ids(sup.get("context_for", "")) + [req_id]
        C.assign_context(self.M.items, [sup], list(dict.fromkeys(ids)))
        self.changed()

    def set_authors(self, it, text):
        value = ", ".join(SD.split_names(text))
        if (it.get("owner") or "") == value:
            return
        self.snap()
        it["owner"] = value
        self.changed()

    def set_notes(self, it, text):
        if (it.get("notes") or "") == text:
            return
        it["notes"] = text
        self.changed()

    def save(self):
        if not self.backed_up and os.path.isfile(self.path):
            shutil.copy2(self.path, os.path.splitext(self.path)[0] + " (before the Qt test).xlsx")
            self.backed_up = True
        self.M.pending = True
        self.M.save()
        self.dirty = False


# ------------------------------------------------------------------ the page
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

    def style(self, dec, current=False):
        self.dec = dec
        col = QColor(DEC.get(dec, DEC[""])[0])
        sel = self.isSelected()
        fill = QColor(col)
        fill.setAlpha(70 if dec else (40 if sel else 0))
        if sel:
            fill = QColor("#FDE68A") if not dec else fill
            fill.setAlpha(140 if not dec else 110)
        self.setBrush(QBrush(fill))
        pen = QPen(QColor("#F59E0B") if current else (col if dec else QColor("#CBD5E1")))
        pen.setWidthF(2.4 if current else (1.4 if (dec or sel or self.hover) else 0.8))
        pen.setCosmetic(True)
        self.setPen(pen)

    def paint(self, painter, option, widget=None):
        from PySide6.QtWidgets import QStyle
        option.state &= ~QStyle.State_Selected          # no dashed frame: the colors say it is selected
        super().paint(painter, option, widget)

    def hoverEnterEvent(self, e):
        self.hover = True
        self.style(self.dec)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self.hover = False
        self.style(self.dec)
        super().hoverLeaveEvent(e)


class PageView(QGraphicsView):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.setBackgroundBrush(QColor("#E2E8F0"))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.boxes = {}
        self.labels = []
        self.zoom = 1.0

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            if 0.3 < self.zoom * f < 5:
                self.zoom *= f
                self.scale(f, f)
            return
        super().wheelEvent(e)

    def fit(self):
        r = self.scene().itemsBoundingRect()
        if r.width() > 0:
            self.resetTransform()
            self.zoom = max(0.3, (self.viewport().width() - 30) / r.width())
            self.scale(self.zoom, self.zoom)


# ------------------------------------------------------------------ the window
class Chip(QFrame):
    def __init__(self, text, color, on_remove=None, on_jump=None):
        super().__init__()
        self.setStyleSheet(f"QFrame{{background:{color};border-radius:11px}} QLabel{{background:transparent}}")
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 2, 4, 2)
        h.addWidget(QLabel(text))
        h.addStretch(1)
        if on_jump:
            b = QToolButton(text="Jump"); b.setAutoRaise(True); b.clicked.connect(on_jump); h.addWidget(b)
        if on_remove:
            b = QToolButton(text="×"); b.setAutoRaise(True); b.setStyleSheet("color:#B91C1C;font-weight:bold")
            b.clicked.connect(on_remove); h.addWidget(b)


class Main(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.store = None
        self.file = None
        self.pdf = ""
        self.placed = {}
        self.target = None
        self.cur = None
        self._guard = False
        self.resize(1600, 1000)
        tb = QToolBar(); self.addToolBar(tb)
        self.files = QComboBox(); self.files.setMinimumWidth(260); self.files.currentTextChanged.connect(self.open_file)
        tb.addAction(QAction("Open matrix...", self, triggered=self.choose))
        tb.addWidget(QLabel("  File: ")); tb.addWidget(self.files)
        tb.addSeparator()
        for text, fn in (("Requirement  R", self.do_req), ("Support  C", self.do_ctx), ("Customer's  G", self.do_customer),
                         ("Not used  X", self.do_clear), ("Combine  M", self.do_combine), ("Undo  Ctrl+Z", self.do_undo),
                         ("Save  Ctrl+S", self.do_save)):
            tb.addAction(QAction(text, self, triggered=fn))
        tb.addSeparator()
        tb.addAction(QAction("Fit width", self, triggered=lambda: self.view.fit()))
        self.view = PageView(self)
        self.view.scene().selectionChanged.connect(self.on_select)
        right = QSplitter(Qt.Vertical)
        self.card_area = QScrollArea(); self.card_area.setWidgetResizable(True)
        self.card_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.card = QWidget(); self.card_lay = QVBoxLayout(self.card); self.card_lay.setAlignment(Qt.AlignTop)
        self.card_area.setWidget(self.card)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Your response structure (click: target for R)", "Req."])
        self.tree.setColumnWidth(0, 300)
        self.tree.itemClicked.connect(lambda i, _c: self.set_target(i.data(0, Qt.UserRole)))
        right.addWidget(self.card_area); right.addWidget(self.tree); right.setSizes([600, 380])
        split = QSplitter(Qt.Horizontal); split.addWidget(self.view); split.addWidget(right); split.setSizes([1120, 480])
        self.setCentralWidget(split)
        self.notes_timer = QTimer(self, singleShot=True, interval=700, timeout=self.save_notes)
        for key, fn in (("R", self.do_req), ("C", self.do_ctx), ("G", self.do_customer), ("X", self.do_clear),
                        ("M", self.do_combine), ("Ctrl+Z", self.do_undo), ("Ctrl+S", self.do_save),
                        ("Escape", lambda: self.view.scene().clearSelection())):
            QShortcut(QKeySequence(key), self.view, activated=fn)
        self.setWindowTitle("Stationkeeper Assign (Qt test)")
        if path:
            self.load(path)

    # ---------------- loading
    def choose(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open the effort's compliance matrix", "", "Compliance matrix (*.xlsx)")
        if p:
            self.load(p)

    def load(self, path):
        QMessageBox.information(self, "Qt test", "Close this matrix in Stationkeeper while you test here: Save (Ctrl+S) "
                                "writes the same file. The first save keeps a copy named '(before the Qt test)'.")
        self.store = Store(path)
        self.files.blockSignals(True)
        self.files.clear(); self.files.addItems(self.store.files())
        self.files.blockSignals(False)
        self.fill_tree()
        if self.store.files():
            self.open_file(self.store.files()[0])
        self.title()

    def pdf_of(self, f):
        path = self.store.M.path_of(f)
        if not path:
            return ""
        if path.lower().endswith(".pdf"):
            return path
        d = os.path.dirname(os.path.abspath(self.store.path))
        for folder in glob.glob(os.path.join(d, "* - app data", "page copies")) + glob.glob(os.path.join(os.path.dirname(d), "* - app data", "page copies")):
            c = OP.copy_path(path, folder)
            if os.path.isfile(c):
                return c
        return ""

    def open_file(self, f):
        if not f or self.store is None:
            return
        self.file = f
        self.pdf = self.pdf_of(f)
        sc = self.view.scene()
        sc.clear()
        self.view.boxes = {}
        if not self.pdf:
            sc.addText(f"No page form for {f}: open it once in Stationkeeper's Page view (it makes the PDF copy).")
            return
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(self.pdf)
        self.tops = []
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
        QTimer.singleShot(0, self.view.fit)

    def build_boxes(self):
        sc = self.view.scene()
        for b in self.view.boxes.values():
            sc.removeItem(b)
        self.view.boxes = {}
        rows = self.store.rows_of(self.file)
        self.placed = PS.place_all(self.pdf, rows)
        heads = [x for x in self.store.M.headings if x.get("file") in ("", None, self.file)]
        items = [dict(it, place=self.placed[it["id"]][0], lead_place=self.placed[it["id"]][1]) for it in rows if it["id"] in self.placed]
        rects = {}
        for n in range(1, len(self.tops) + 1):
            m = PS.place_map(self.pdf, n, items, heads)
            for x in m["items"]:
                rects.setdefault(x["id"], []).extend((l + MARGIN, t + self.tops[n - 1], r + MARGIN, b + self.tops[n - 1])
                                                     for l, t, r, b in x["rects"])
            for l, t, r, b in m["headings"]:
                hb = sc.addRect(QRectF(l + MARGIN - 1, t + self.tops[n - 1] - 1, r - l + 2, b - t + 2), QPen(QColor("#475569"), 0.6))
                hb.setZValue(0)
        for iid, rs in rects.items():
            box = SentenceBox(iid, rs)
            sc.addItem(box)
            self.view.boxes[iid] = box
        self.restyle()

    # ---------------- drawing decisions
    def restyle(self):
        sc = self.view.scene()
        for lab in self.view.labels:
            sc.removeItem(lab)
        self.view.labels = []
        last_y = -100
        for iid, box in sorted(self.view.boxes.items(), key=lambda kv: kv[1].boundingRect().top()):
            it = self.store.item(iid)
            if it is None:
                continue
            box.style(it.get("decision", ""), current=(iid == self.cur))
            tag = DEC.get(it.get("decision", ""), DEC[""])[2]
            if tag:
                y = max(box.boundingRect().top(), last_y + 11)
                last_y = y
                hosts = C.cf_ids(it.get("context_for", "")) if it.get("decision") == "Context" else []
                txt = f"{tag} {iid}" if not hosts else f"{tag} {', '.join(hosts[:2])}"
                lab = QGraphicsSimpleTextItem(txt)
                lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
                lab.setBrush(QColor(DEC[it["decision"]][0]))
                lab.setPos(MARGIN - 8 - lab.boundingRect().width(), y)
                sc.addItem(lab)
                self.view.labels.append(lab)

    def selected(self):
        ids = [b.iid for b in self.view.scene().selectedItems() if isinstance(b, SentenceBox)]
        order = {it["id"]: k for k, it in enumerate(self.store.M.items)} if self.store else {}
        return [self.store.item(i) for i in sorted(ids, key=lambda i: order.get(i, 0)) if self.store.item(i)]

    def on_select(self):
        if self._guard or self.store is None:
            return
        self.save_notes()
        rows = self.selected()
        self.cur = rows[-1]["id"] if rows else None
        if rows and rows[-1].get("decision") == "Keep" and len(rows) == 1:
            self.store.last_req = rows[-1]["id"]
        self.restyle()
        self.show_card(rows)

    def select(self, iid):
        self._guard = True
        self.view.scene().clearSelection()
        b = self.view.boxes.get(iid)
        if b is None:
            it = self.store.item(iid)
            if it and it.get("file") != self.file:
                self.files.setCurrentText(it["file"])
                b = self.view.boxes.get(iid)
        if b is not None:
            b.setSelected(True)
            self.view.ensureVisible(b, 40, 120)
        self._guard = False
        self.on_select()

    # ---------------- the card
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
        l = self.add(QLabel(text)); l.setStyleSheet("font-weight:bold;margin-top:10px;font-size:13px")
        return l

    def show_card(self, rows):
        self.clear_card()
        self.notes = None
        M = self.store.M
        if not rows:
            self.add(QLabel("Click a sentence on the page. Ctrl+click adds more; drag a box around several."))
            return
        it = rows[-1]
        d = it.get("decision", "")
        color, kind, _tag = DEC.get(d, DEC[""])
        k = self.add(QLabel(f"  {kind}" + (f"   (and {len(rows) - 1} more selected)" if len(rows) > 1 else "")))
        k.setStyleSheet(f"background:{color};color:white;font-weight:bold;padding:6px;border-radius:6px")
        t = self.add(QLabel(it.get("text", ""))); t.setWordWrap(True); t.setStyleSheet("font-family:Georgia;font-size:14px;margin:6px 0")
        self.head("Source")
        where = PS.where_text(self.pdf, self.placed.get(it["id"], ("",))[0] or it.get("place", "")) if self.pdf else ""
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        ref, _how = SD.ref_of(M, it)
        src = [f"File: {it.get('file', '')}"] + ([f"Where: {where}"] if where else []) + ([f"RFP: {sec}"] if sec else []) \
            + ([f"Referenced as: {ref}"] if ref and ref != it.get("section") else []) + [f"ID: {it['id']}   Type: {it.get('type', '')}"]
        s = self.add(QLabel("\n".join(src))); s.setStyleSheet("color:#334155")
        self.head("Decision")
        if d == "Keep":
            secs = SD.item_sections(M, it)
            for lab in secs:
                self.add(Chip(lab, "#DCFCE7", on_remove=lambda _=False, l=lab: (self.store.remove_section(it, l), self.after())))
            if not secs:
                self.add(QLabel("No section yet: click one in your structure, then R."))
            cb = QComboBox(); cb.addItem("+ Section"); cb.addItems([C.outline_label(o) for o in M.outline if C.outline_label(o) not in secs])
            cb.activated.connect(lambda i, cb=cb: (self.store.add_section(it, cb.itemText(i)), self.after()) if i > 0 else None)
            self.add(cb)
        elif d == "Context":
            for i in C.cf_ids(it.get("context_for", "")):
                x = self.store.item(i)
                self.add(Chip(f"{i}   {x.get('map', '') if x else ''}", "#DBEAFE", on_remove=lambda _=False, b=i: (self.store.unlink(it, b), self.after()),
                              on_jump=lambda _=False, b=i: self.select(b)))
            cb = QComboBox(); cb.addItem("+ Requirement")
            reqs = [x for x in M.items if x.get("decision") == "Keep" and x["id"] not in C.cf_ids(it.get("context_for", ""))]
            for x in reqs:
                cb.addItem(f"{x['id']}  {x.get('map', '')}: {x['text'][:50]}", x["id"])
            cb.activated.connect(lambda i, cb=cb: (self.store.link(it, cb.itemData(i)), self.after()) if i > 0 else None)
            self.add(cb)
        else:
            self.add(QLabel("R: requirement (in the target section).  C: support for the last requirement you clicked.  G: customer's."))
        self.head("Author(s)")
        ed = self.add(QLineEdit(", ".join(SD.split_names(it.get("owner", "")))))
        ed.setPlaceholderText("names, separated by commas (empty: the section's lead)")
        ed.setEnabled(d in ("Keep", "Context"))
        names = SD.people(M)
        comp = QCompleter(names); comp.setCaseSensitivity(Qt.CaseInsensitive); ed.setCompleter(comp)
        ed.editingFinished.connect(lambda ed=ed: (self.store.set_authors(it, ed.text()), self.title(), self.fill_tree()))
        self.head("Relationships")
        if d == "Keep":
            ids = [x["id"] for x in M.items if x.get("decision") == "Context" and it["id"] in C.cf_ids(x.get("context_for", ""))]
        elif d == "Context":
            ids = C.cf_ids(it.get("context_for", ""))
        else:
            ids = []
        if not ids:
            self.add(QLabel("None yet."))
        for i in ids:
            x = self.store.item(i)
            if x is None:
                continue
            role = "REQ" if x.get("decision") == "Keep" else "SUPPORT"
            b = QLabel(f"<a href='{i}'><b>{role} {i}</b></a> ({MD.ctx_ref(M, x)}) {x['text'][:140]}")
            b.setTextFormat(Qt.RichText)
            b.setStyleSheet("background:#EFF6FF;border-radius:6px;padding:6px")
            b.linkActivated.connect(lambda href: self.select(href))
            self.add(b)
        self.head("Notes")
        self.notes = self.add(QPlainTextEdit(it.get("notes", "")))
        self.notes.setFixedHeight(70)
        self.notes_for = it["id"]
        self.notes.textChanged.connect(self.notes_timer.start)

    def save_notes(self):
        n = getattr(self, "notes", None)
        if n is None or self.store is None:
            return
        try:
            it = self.store.item(self.notes_for)
            if it is not None:
                self.store.set_notes(it, n.toPlainText().strip())
                self.title()
        except RuntimeError:
            pass                                    # the card was rebuilt

    # ---------------- the structure
    def fill_tree(self):
        self.tree.clear()
        if self.store is None:
            return
        M = self.store.M
        counts = {}
        for it in M.items:
            if it.get("decision") == "Keep":
                for lab in SD.item_sections(M, it):
                    counts[lab] = counts.get(lab, 0) + 1
        stack = []
        for o in M.outline:
            lab = C.outline_label(o)
            lvl = o.get("level", 1)
            node = QTreeWidgetItem([lab, str(counts.get(lab, "") or "")])
            node.setData(0, Qt.UserRole, lab)
            if lab == self.target:
                f = node.font(0); f.setBold(True); node.setFont(0, f); node.setBackground(0, QColor("#FEF3C7"))
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            (stack[-1][1].addChild(node) if stack else self.tree.addTopLevelItem(node))
            stack.append((lvl, node))
        self.tree.expandAll()

    def set_target(self, lab):
        self.target = lab
        self.statusBar().showMessage(f"Target: {lab}. R puts the selected sentences there.")
        self.fill_tree()

    # ---------------- actions
    def after(self, msg=""):
        self.restyle()
        self.fill_tree()
        self.show_card(self.selected())
        self.title()
        if msg:
            self.statusBar().showMessage(msg, 6000)

    def title(self):
        if self.store:
            self.setWindowTitle(("* " if self.store.dirty else "") + f"{os.path.basename(self.store.path)}: Stationkeeper Assign (Qt test)")

    def do_req(self):
        rows = self.selected()
        if not rows:
            return
        if not self.target:
            self.statusBar().showMessage("Click a section in your structure first (the target for R).", 6000)
            return
        n = self.store.req(rows, self.target)
        self.after(f"{n} sentence(s): compliance requirement in {self.target}")

    def do_ctx(self):
        rows = self.selected()
        if rows:
            self.store.ctx(rows)
            self.after(f"{len(rows)} sentence(s): support for {rows[0].get('context_for') or 'the section'}")

    def do_customer(self):
        rows = self.selected()
        if rows:
            self.store.customer(rows)
            self.after(f"{len(rows)} sentence(s): the customer's")

    def do_clear(self):
        rows = self.selected()
        if rows:
            self.store.clear(rows)
            self.after(f"{len(rows)} sentence(s): not used")

    def do_combine(self):
        rows = self.selected()
        if len(rows) < 2:
            self.statusBar().showMessage("Select two or more sentences (Ctrl+click or drag), then M.", 6000)
            return
        first = self.store.combine(rows, self.placed)
        self.build_boxes()
        self.select(first["id"])
        self.after(f"Combined {len(rows)} sentences into {first['id']}")

    def do_undo(self):
        if self.store and self.store.undo_last():
            self.build_boxes()
            self.after("Undone.")

    def do_save(self):
        if self.store:
            self.save_notes()
            self.store.save()
            self.title()
            self.statusBar().showMessage(f"Saved {os.path.basename(self.store.path)}.", 6000)

    def closeEvent(self, e):
        self.save_notes()
        if self.store and self.store.dirty:
            r = QMessageBox.question(self, "Qt test", "Save the changes to the matrix?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel:
                e.ignore()
                return
            if r == QMessageBox.Save:
                self.store.save()
        e.accept()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    w = Main(sys.argv[1] if len(sys.argv) > 1 else None)
    w.show()
    if len(sys.argv) <= 1:
        QTimer.singleShot(200, w.choose)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
