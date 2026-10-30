"""The Trainer in Qt (2.73.0): open a document or picture, pick a page or picture, drag a box around text the reader
missed (or take the whole picture), see every line the reader finds in it, and teach the reader: Save as text (fix the
spelling first; typing picks it), Not text (lines, arrows or specks read as letters; a reading the scanner keeps today
goes on the ignore list), or Skip. Whole box as one line, OCR fixes from corrections, undo the last save. The same engine
as the classic Trainer (pictures, corrections): the local reader only, no generative AI; nothing leaves the PC.
"""
import os
from PySide6.QtCore import QRectF, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QDialog,
                               QRadioButton, QScrollArea, QSplitter, QVBoxLayout, QWidget)
import app_gui as eng
import diag
import corrections as CO
from . import design as D

CHOICES = ("Skip", "Save as text", "Not text")
OPEN_FILTER = ("Documents and images (*.pdf *.pptx *.docx *.xlsx *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif *.svg "
               "*.svgz *.emf *.wmf *.emz *.wmz)")


def to_pixmap(img):
    img = img.convert("RGB")
    q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(q)


class ReadWorker(QThread):
    done = Signal(object, object, str)

    def __init__(self, crop, read_lines, read_one):
        super().__init__()
        self.crop, self.read_lines, self.read_one = crop, read_lines, read_one

    def run(self):
        try:
            self.done.emit(self.read_lines(self.crop), self.read_one(self.crop), "")
        except Exception as e:
            eng.log_error("Trainer region OCR failed")
            self.done.emit([], ("", 0.0), f"{type(e).__name__}: {e}")


class PictureView(QGraphicsView):
    boxed = Signal(QRectF)                     # a dragged box, in picture pixels

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor("#3A3F47"))
        self.setRenderHints(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.viewport().setCursor(Qt.CrossCursor)
        self.pix = None
        self._p0, self._band = None, None

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            f = 1.25 if e.angleDelta().y() > 0 else 0.8
            self.scale(f, f)
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e):
        if self.pix is None or e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        self._p0 = self.mapToScene(e.position().toPoint())
        if self._band is not None:
            self.scene().removeItem(self._band); self._band = None

    def mouseMoveEvent(self, e):
        if self._p0 is None:
            return super().mouseMoveEvent(e)
        r = QRectF(self._p0, self.mapToScene(e.position().toPoint())).normalized()
        if self._band is None:
            pen = QPen(QColor("#22D3EE")); pen.setWidthF(2); pen.setCosmetic(True); pen.setStyle(Qt.DashLine)
            self._band = self.scene().addRect(r, pen)
            self._band.setZValue(3)
        else:
            self._band.setRect(r)

    def mouseReleaseEvent(self, e):
        if self._p0 is None:
            return super().mouseReleaseEvent(e)
        r = QRectF(self._p0, self.mapToScene(e.position().toPoint())).normalized()
        self._p0 = None
        if self._band is not None:
            self.scene().removeItem(self._band); self._band = None
        r = r.intersected(self.pix.boundingRect())
        if r.width() >= 6 and r.height() >= 6:
            self.boxed.emit(r)


class TrainerPage(QWidget):
    def __init__(self, host=None):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.read_lines, self.read_one = None, None        # tests may give their own readers
        self.sources, self.img, self.source_label = [], None, ""
        self.region, self.region_img, self.rows, self.one = None, None, [], ("", 0.0)
        self.focus_target, self.focus_term, self.worker = None, None, None
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["m"]); v.setSpacing(D.SPACE["s"])
        bar = QHBoxLayout(); bar.setSpacing(D.SPACE["s"])
        bar.addWidget(D.button("Open a file...", "primary", lambda: self.open_file()))
        bar.addWidget(D.button("Fit", None, lambda: self.fit()))
        bar.addWidget(D.button("-", None, lambda: self.view.scale(0.8, 0.8)))
        bar.addWidget(D.button("+", None, lambda: self.view.scale(1.25, 1.25)))
        bar.addWidget(D.button("Select the whole picture", None, lambda: self.select_all()))
        self.hint = D.label("Open a file, pick a page or picture, then drag a box around missed text.", "muted")
        bar.addWidget(self.hint, 1)
        v.addLayout(bar)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(D.label("Pages and pictures", "label"))
        self.list = QListWidget(); self.list.currentRowChanged.connect(lambda r: self.pick(r)); lv.addWidget(self.list)
        split.addWidget(left)
        self.view = PictureView(); self.view.boxed.connect(lambda r: self.run_region((r.left(), r.top(), r.right(), r.bottom())))
        split.addWidget(self.view)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0); rv.setSpacing(D.SPACE["s"])
        rv.addWidget(D.label("What the reader read in the box", "title"))
        rv.addWidget(D.label("Green: the scanner keeps this reading. Red: low confidence, the scanner already ignores it. "
                             "Numbers match the boxes on the picture. For each line: Skip, Save as text (fix the spelling "
                             "first; typing picks it) or Not text (lines, arrows or specks read as letters). Then Save "
                             "choices.", "muted"))
        self.lines_area = QScrollArea(); self.lines_area.setWidgetResizable(True); self.lines_area.setFrameShape(QFrame.NoFrame)
        self.lines_box = QWidget(); self.lines_lay = QVBoxLayout(self.lines_box); self.lines_lay.setAlignment(Qt.AlignTop)
        self.lines_area.setWidget(self.lines_box)
        rv.addWidget(self.lines_area, 1)
        one = D.Card("Whole box as one line", "When the reader found nothing or split the text.")
        self.lbl_one = one.add(D.label("Read as one line: -", "muted"))
        self.entry_one = QLineEdit(); self.entry_one.setPlaceholderText("Correct text for the whole box"); one.add(self.entry_one)
        one.add(D.button("Save the whole box as one sample", None, lambda: self.save_whole()))
        rv.addWidget(one)
        acts = QHBoxLayout(); acts.setSpacing(D.SPACE["s"])
        acts.addWidget(D.button("Save choices", "primary", lambda: self.save_choices()))
        acts.addWidget(D.button("Add OCR fixes from corrections", None, lambda: self.add_fixes()))
        rv.addLayout(acts)
        right.setMinimumWidth(420)
        split.addWidget(right)
        split.setSizes([240, 720, 440])
        foot = QHBoxLayout(); foot.setSpacing(D.SPACE["s"])
        self.stats = D.label("", "muted", wrap=False); foot.addWidget(self.stats)
        self.status = D.label("", "muted"); foot.addWidget(self.status, 1)
        for text, kind, fn in (("How training works", None, lambda: self.show_help()),
                               ("Ignore list", None, lambda: self.open_path(eng.OCR_IGNORE_FILE, make=True)),
                               ("Open the training folder", None, lambda: self.open_path(CO.TRAIN_DIR, folder=True)),
                               ("Undo last save", "danger", lambda: self.undo())):
            foot.addWidget(D.button(text, kind, fn))
        v.addLayout(foot)
        self.refresh_stats()

    # ------------------------------------------------------------ files and pictures
    def open_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Open a document or picture", "", OPEN_FILTER)
            if not path:
                return False
            self.focus_target = self.focus_term = None
        return self.load_file(path)

    def load_file(self, path):
        from pictures import list_sources
        from .sensgate import training_gate                 # 2.97.0: nothing above CUI; an unmarked file is declared
        if not training_gate(self, path, getattr(self, "declare_answer", None), self.status.setText):
            return False
        try:
            self.sources = list_sources(path)
        except Exception as e:
            eng.log_error("Trainer could not open a file", ext=os.path.splitext(path)[1].lower())
            self.status.setText(f"That file could not be opened ({type(e).__name__}).")
            return False
        diag.activity("trainer_file_opened", n=len(self.sources))
        self.list.blockSignals(True)
        self.list.clear()
        for label, _loader in self.sources:
            inner = label.split(" (", 1)[-1].rstrip(")")
            self.list.addItem(os.path.basename(path) if inner == "Image" else inner)
        self.list.blockSignals(False)
        if not self.sources:
            self.status.setText("No pages or pictures in that file.")
            return False
        if self.focus_target:
            return self._apply_focus()
        self.list.setCurrentRow(0)
        return True

    def pick(self, row):
        if row < 0 or row >= len(self.sources):
            return
        label, loader = self.sources[row]
        try:
            self.img = loader()
        except Exception as e:
            eng.log_error("Trainer could not load a picture")
            self.status.setText(f"This picture could not be opened (for example EMF or SVG): {type(e).__name__}.")
            return
        self.source_label = label
        sc = self.view.scene(); sc.clear()
        self.view.pix = QGraphicsPixmapItem(to_pixmap(self.img)); self.view.pix.setTransformationMode(Qt.SmoothTransformation)
        sc.addItem(self.view.pix); sc.setSceneRect(self.view.pix.boundingRect())
        self.region = None; self.clear_lines(); self.fit()
        self.status.setText(f"{label}: {self.img.width} x {self.img.height} px")

    def fit(self):
        if self.view.pix is not None:
            self.view.fitInView(self.view.pix, Qt.KeepAspectRatio)

    def select_all(self):
        if self.img is not None:
            return self.run_region((0, 0, self.img.width, self.img.height))
        return None

    def focus_on(self, path, location, term):
        """Check in picture: open the picture a scan result came from, read it, outline the line holding the term."""
        self.focus_target, self.focus_term = (location, term), term
        return self.load_file(path)

    def _apply_focus(self):
        from pictures import match_source
        location, term = self.focus_target
        self.focus_target = None
        i = match_source([lbl for lbl, _ in self.sources], location)
        if i is None:
            self.status.setText(f"'{term}' was read from typed text there, not a picture: nothing to check.")
            return False
        self.list.setCurrentRow(i)
        self.select_all()
        return True

    # ------------------------------------------------------------ reading a box
    def run_region(self, box, wait=False):
        from pictures import read_region_lines, read_region_as_one_line
        if self.img is None or self.worker is not None:
            return None
        self.region = tuple(box)
        self.region_img = self.img.crop(tuple(int(v) for v in box))
        self.clear_lines()
        self.status.setText("Reading the box...")
        self.worker = ReadWorker(self.region_img, self.read_lines or read_region_lines, self.read_one or read_region_as_one_line)
        self.worker.done.connect(self.show_lines)
        self.worker.start()
        if wait:
            self.worker.wait()
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
        return self.region

    def clear_lines(self):
        while self.lines_lay.count():
            w = self.lines_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        self.rows = []
        self.lbl_one.setText("Read as one line: -"); self.entry_one.clear()
        self.draw_boxes()

    def show_lines(self, lines, one, err):
        self.worker = None
        if err:
            self.status.setText(f"The reader could not read the box: {err}")
            return
        from .sensgate import training_lines                # 2.97.0: words marked above CUI are not shown or kept
        if not training_lines([t for _b, t, _c in lines] + [one[0] if one else ""], self.status.setText):
            self.region_img = None
            return
        cutoff = eng.ocr_cutoff()
        ignored = eng.load_ocr_ignore()
        for n, (box, text, conf) in enumerate(lines, start=1):
            kept, on_list = conf >= cutoff, eng.fold(text).strip() in ignored
            card = QFrame(); card.setProperty("card", True)
            cl = QVBoxLayout(card); cl.setContentsMargins(D.SPACE["s"], D.SPACE["xs"], D.SPACE["s"], D.SPACE["xs"]); cl.setSpacing(2)
            note = "already on the ignore list" if on_list else ("the scanner keeps this" if kept else "the scanner ignores this")
            lab = QLabel(f"{n}.  Read: {text}   ({conf:.2f}, {note})"); lab.setWordWrap(True)
            lab.setStyleSheet(f"color:{'#6B7280' if on_list else '#15803D' if kept else '#DC2626'};font-weight:600;")
            cl.addWidget(lab)
            ent = QLineEdit(text); cl.addWidget(ent)
            rowl = QHBoxLayout(); grp = QButtonGroup(card)
            for k, c in enumerate(CHOICES):
                rb = QRadioButton(c); grp.addButton(rb, k); rowl.addWidget(rb)
                if k == 0:
                    rb.setChecked(True)
            rowl.addStretch(1); cl.addLayout(rowl)
            row = {"n": n, "box": box, "text": text, "conf": conf, "group": grp, "entry": ent}
            grp.idClicked.connect(lambda _i: self.draw_boxes())
            ent.textEdited.connect(lambda _t, g=grp: (g.button(1).setChecked(True), self.draw_boxes()))
            self.rows.append(row)
            self.lines_lay.addWidget(card)
        if not lines:
            self.lines_lay.addWidget(D.label("No text lines found in the box. Use Whole box as one line below.", "muted"))
        self.one = one
        text1, conf1 = one
        self.lbl_one.setText(f"Read as one line: {text1 or '(nothing)'}   ({conf1:.2f})")
        self.entry_one.setText(text1)
        self.draw_boxes()
        msg = f"{len(lines)} line(s) found. Pick Skip, Save as text or Not text for each, then Save choices."
        if self.focus_term:
            hits = [str(r["n"]) for r in self.rows if eng.fold(self.focus_term) in eng.fold(r["text"])]
            msg = (f"'{self.focus_term}' is line {', '.join(hits)} (yellow outline). " if hits else
                   f"'{self.focus_term}' was not read in this picture now: drag a box around it. ") + msg
        self.status.setText(msg)
        diag.activity("trainer_region_read", n=len(lines))

    @staticmethod
    def choice(row):
        return CHOICES[max(0, row["group"].checkedId())]

    def set_choice(self, n, choice, text=None):
        """Pick a line's choice (and its text) as the person would."""
        r = self.rows[n - 1]
        if text is not None:
            r["entry"].setText(text)
        r["group"].button(CHOICES.index(choice)).setChecked(True)
        self.draw_boxes()

    def draw_boxes(self):
        sc = self.view.scene()
        for it in [i for i in sc.items() if i.data(0) == "line"]:
            sc.removeItem(it)
        if not self.region or self.view.pix is None:
            return
        rx, ry = self.region[0], self.region[1]
        pen0 = QPen(QColor("#22D3EE")); pen0.setWidthF(2); pen0.setCosmetic(True); pen0.setStyle(Qt.DashLine)
        reg = sc.addRect(QRectF(rx, ry, self.region[2] - rx, self.region[3] - ry), pen0); reg.setData(0, "line")
        cutoff = eng.ocr_cutoff()
        for r in self.rows:
            (x0, y0, x1, y1), conf = r["box"], r["conf"]
            ch = self.choice(r)
            color = QColor("#9CA3AF" if ch == "Not text" else ("#22C55E" if conf >= cutoff else "#EF4444"))
            pen = QPen(color); pen.setWidthF(2); pen.setCosmetic(True)
            if ch == "Not text":
                pen.setStyle(Qt.DotLine)
            box = sc.addRect(QRectF(rx + x0, ry + y0, x1 - x0, y1 - y0), pen); box.setData(0, "line")
            t = sc.addSimpleText(str(r["n"])); t.setBrush(QBrush(color)); t.setFont(QFont("Segoe UI", 9, QFont.Bold))
            t.setPos(rx + x0, ry + y0 - 14); t.setData(0, "line")
            if self.focus_term and eng.fold(self.focus_term) in eng.fold(r["text"]):
                pen2 = QPen(QColor("#FACC15")); pen2.setWidthF(3); pen2.setCosmetic(True)
                hi = sc.addRect(QRectF(rx + x0 - 5, ry + y0 - 5, x1 - x0 + 10, y1 - y0 + 10), pen2); hi.setData(0, "line")

    # ------------------------------------------------------------ saving
    def save_choices(self):
        if self.region_img is None or not self.rows:
            self.status.setText("Draw a box around text first.")
            return None
        text_rows = [r for r in self.rows if self.choice(r) == "Save as text" and r["entry"].text().strip()]
        junk = [r for r in self.rows if self.choice(r) == "Not text"]
        if not text_rows and not junk:
            self.status.setText("Pick Save as text or Not text for at least one line.")
            return None
        rx, ry = self.region[0], self.region[1]
        images = []
        for r in text_rows:                                  # one tight line each
            x0, y0, x1, y1 = r["box"]; m = 3
            crop = self.region_img.crop((int(max(0, x0 - m)), int(max(0, y0 - m)),
                                         int(min(self.region_img.width, x1 + m)), int(min(self.region_img.height, y1 + m))))
            images.append(CO.save_sample(crop, r["entry"].text(), r["text"], r["conf"], self.source_label,
                                         (rx + x0, ry + y0, rx + x1, ry + y1)))
        unsure = [r["box"] for r in self.rows if self.choice(r) == "Skip"]
        images.append(CO.save_region(self.region_img, [(r["box"], r["entry"].text()) for r in text_rows], unsure,
                                     [(r["box"], r["text"], r["conf"]) for r in junk], self.source_label, self.region))
        cutoff = eng.ocr_cutoff()                           # Not text the scanner keeps today: ignore that reading
        rows = eng.read_ocr_ignore_rows(); have = {eng.fold(x[0]).strip() for x in rows}
        added = []
        for r in junk:
            key = eng.fold(r["text"]).strip()
            if r["conf"] >= cutoff and key and key not in have:
                rows.append([r["text"].strip(), f"Not text, Trainer {CO._now()}, {self.source_label}"]); have.add(key)
                added.append(r["text"].strip())
        if added:
            eng.write_ocr_ignore_rows(rows)
        summary = f"{len(text_rows)} text line(s), {len(junk)} not-text line(s)"
        CO._log_save({"time": CO._now(), "images": images, "ignored": added, "summary": summary})
        for r in self.rows:
            r["group"].button(0).setChecked(True)
        self.draw_boxes()
        diag.activity("trainer_saved", n=len(text_rows), items=len(junk))
        self.refresh_stats(f"Saved {summary}." + (" The scanner now ignores: " + ", ".join(added) if added else ""))
        return {"text": len(text_rows), "junk": len(junk), "ignored": added}

    def save_whole(self):
        text = self.entry_one.text().strip()
        if self.region_img is None or not text:
            self.status.setText("Draw a box and type the correct text first.")
            return None
        from pictures import tighten
        rel = CO.save_sample(tighten(self.region_img), text, self.one[0], float(self.one[1] or 0.0), self.source_label, self.region)
        CO._log_save({"time": CO._now(), "images": [rel], "ignored": [], "summary": f"whole box '{text}'"})
        diag.activity("trainer_saved_whole")
        self.refresh_stats("Saved the whole box as one sample.")
        return rel

    def add_fixes(self):
        pairs = []
        for r in self.rows:
            pairs += CO.fixes_from_correction(r["text"], r["entry"].text())
        if self.one[0]:
            pairs += CO.fixes_from_correction(self.one[0], self.entry_one.text())
        pairs = list(dict.fromkeys(pairs))
        if not pairs:
            self.status.setText("No single-word corrections found: change a word in a line, then try again.")
            return []
        rows = eng.read_ocr_fix_rows()
        existing = {r[0] for r in rows}
        added = [(a, b) for a, b in pairs if a not in existing]
        rows += [[a, b, "Added in Trainer"] for a, b in added]
        eng.write_ocr_fix_rows(rows)
        diag.activity("trainer_fixes_added", n=len(added))
        self.refresh_stats("Added OCR fixes: " + ", ".join(f"{a} > {b}" for a, b in added) if added else "Those fixes already exist.")
        return added

    def undo(self):
        what = CO.remove_last_save()
        diag.activity("trainer_undo")
        self.refresh_stats(f"Removed: {what}" if what else "Nothing to undo.")
        return what

    def refresh_stats(self, msg=None):
        n, regions, junk, size = CO.training_stats()
        self.stats.setText(f"Text lines: {n}  |  Regions: {regions}  |  Not-text examples: {junk}  |  {size / 1024 / 1024:.1f} MB")
        if msg:
            self.status.setText(msg)
        if self.host is not None and hasattr(self.host, "refresh") and msg:
            try:
                self.host.refresh()
            except Exception:
                diag.swallowed()

    def open_path(self, path, make=False, folder=False):
        if folder:
            os.makedirs(path, exist_ok=True)
        elif make and not os.path.exists(path):
            eng.write_ocr_ignore_rows([])
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def show_help(self, run=True):
        import trainer_gui as TG
        text = (TG.HELP_TEXT.split("HOW YOUR SAMPLES MAKE THE SCANNER BETTER")[0] + TG.HELP_TEXT_TESSERACT
                if eng.OCR_BACKEND == "tesseract" else TG.HELP_TEXT)
        d = QDialog(self); d.setWindowTitle("How training works"); d.resize(720, 620)
        lay = QVBoxLayout(d); ed = QPlainTextEdit(text); ed.setReadOnly(True); lay.addWidget(ed)
        if run:
            d.exec()
        return d
