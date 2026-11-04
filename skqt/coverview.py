"""Edit the cover layout (3.27.0): the kept cover or back cover drawn as a page, each floating piece (picture, text box,
table) where Word puts it; drag a piece or type its place and size in inches; set which field a line of text shows.
Save writes a new kept copy (the one before and every original stay); the rules are coverlayout.py's."""
import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGraphicsItem, QGraphicsRectItem,
                               QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QHeaderView, QListWidget,
                               QListWidgetItem, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import coverlayout as CL
import diag
from . import design as D

DPI = 72.0
KIND = {"picture": "Picture", "textbox": "Text box", "shape": "Shape", "table": "Table", "paragraph": "Text", "older": "Older shape"}


class Piece(QGraphicsRectItem):
    def __init__(self, dlg, d):
        super().__init__(0, 0, (d.get("w") or 1) * DPI, (d.get("h") or 0.3) * DPI)
        self.dlg, self.d = dlg, d
        self.setPos((d.get("x") or 0) * DPI, (d.get("y") or 0) * DPI)
        self.setFlags(QGraphicsItem.ItemIsSelectable | (QGraphicsItem.ItemIsMovable if d.get("movable") else QGraphicsItem.GraphicsItemFlag(0))
                      | QGraphicsItem.ItemSendsGeometryChanges)
        tone = {"picture": "#2563eb", "textbox": "#0f766e", "table": "#7c3aed", "shape": "#b45309"}.get(d["kind"], "#6b7280")
        self.setPen(QPen(QColor(tone), 1.2, Qt.DashLine))
        self.setBrush(QBrush(QColor(0, 0, 0, 0)))
        self.setZValue(0 if d.get("behind") else 2)
        self.pix = None
        if d["kind"] == "picture" and d.get("embed"):
            b = CL.picture_bytes(dlg.data, d["embed"])
            if b:
                pm = QPixmap(); pm.loadFromData(b)
                if not pm.isNull():
                    self.pix = pm
        self.block = d.get("block")                    # 3.34.0: a text block, text box or floating table drawn with its words
        self.label = QGraphicsSimpleTextItem("" if self.block is not None else f"{KIND[d['kind']]}: {d.get('text', '')[:40]}", self)
        f = QFont(); f.setPointSizeF(7); self.label.setFont(f); self.label.setBrush(QBrush(QColor(tone)))
        self.label.setPos(2, 1)
        if d["kind"] == "picture":
            self.setPen(QPen(QColor(tone), 0.6, Qt.DotLine))

    def paint(self, painter, option, widget=None):
        if self.pix is not None:                         # 3.34.0: the picture as it will look
            painter.drawPixmap(self.rect().toRect(), self.pix)
        if self.block is not None:                       # 3.34.0: the block's words in their size, weight, color and font
            from .coverdraw import draw_text
            r = self.rect()
            draw_text(painter, QRectF(r.left(), r.top(), r.width(), max(r.height(), 0.3 * DPI) * 1.5), self.dlg.page.work, self.block, DPI)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and not self.dlg.loading:
            self.dlg.moved(self)
        return super().itemChange(change, value)


class CoverLayoutDialog(QDialog):
    def __init__(self, page, key, path=None, data=None):
        super().__init__(page)
        self.page, self.key = page, key
        self.loading = True
        fname = (page.work.get("page_parts") or {}).get(key)
        self.path = path or (os.path.join(page.parts_dir(), fname) if fname else "")
        self.data = data if data is not None else (open(self.path, "rb").read() if self.path and os.path.isfile(self.path) else b"")
        self.changes = {}
        self.setWindowTitle({"cover": "Edit the cover layout", "title": "Edit the title page layout"}.get(key, "Edit the back cover layout"))
        self.resize(1180, 820)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Drag a floating piece (picture, text box, table) or type its place and size in inches from the "
                            "page's top left corner. Set which field a line of text shows: its style becomes the field's cover "
                            "style, so headers, footers and Quick Parts read it. Save keeps a new copy; the one before stays.", "muted"))
        sp = QSplitter(Qt.Horizontal); v.addWidget(sp, 1)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene); self.view.setRenderHint(QPainter.Antialiasing, True)
        sp.addWidget(self.view)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(D.label("Pieces", "title"))
        self.list = QListWidget(); self.list.currentRowChanged.connect(lambda r: self.pick(r)); rv.addWidget(self.list, 1)
        f = QFormLayout(); rv.addLayout(f)
        self.sp = {}
        for k, lab in (("x", "From the left (in)"), ("y", "From the top (in)"), ("w", "Width (in)"), ("h", "Height (in)")):
            s = QDoubleSpinBox(); s.setRange(0, 40); s.setDecimals(2); s.setSingleStep(0.05)
            s.valueChanged.connect(lambda _v, kk=k: self.typed(kk)); f.addRow(lab, s); self.sp[k] = s
        self.keep_ratio = QCheckBox("Keep the picture's proportions"); self.keep_ratio.setChecked(True); f.addRow("", self.keep_ratio)
        rv.addWidget(D.label("The page", "title"))                 # 3.34.0: a background picture and text blocks
        bg = QHBoxLayout()
        self.bg_mode = QComboBox()
        import coverbuild as CB
        for k, label in CB.MODES:
            self.bg_mode.addItem(label, k)
        bg.addWidget(D.button("Background picture...", None, lambda: self.background(),
                              "A PNG, JPG or EMF behind the text, locked; a page that has one gets this one in its place"))
        bg.addWidget(self.bg_mode)
        bg.addWidget(D.button("Take it off", "ghost", lambda: self.take_background()))
        rv.addLayout(bg)
        bb2 = QHBoxLayout()
        bb2.addWidget(D.button("+ Text block...", None, lambda: self.add_block(),
                               "A line that shows a field (Volume name, Solicitation...) or its own words, at a place you set"))
        bb2.addWidget(D.button("Remove the selected block", "ghost", lambda: self.remove_block()))
        rv.addLayout(bb2)
        bb3 = QHBoxLayout()
        bb3.addWidget(D.button("Save as a cover layout...", None, lambda: self.save_layout(),
                               "The page's structure apart from its look (paper, background place, text blocks) in the template library"))
        bb3.addWidget(D.button("Keep in the library...", None, lambda: self.keep_in_library(),
                               "This page, picture and all, as a version in the template library"))
        rv.addLayout(bb3)
        th = QHBoxLayout()                                 # 3.40.0: Text on the page, each line as it prints
        th.addWidget(D.label("Text on the page", "title")); th.addStretch(1)
        th.addWidget(D.button("Add text", None, lambda: self.quick_add(field=""),
                              "A line of your own words under the last line; place and size it on the left or in the boxes above"))
        self.add_field_box = QComboBox()
        for k, label, _style in CL.fields(self.page.work):
            self.add_field_box.addItem(label, k)
        th.addWidget(self.add_field_box)
        th.addWidget(D.button("Add a field", None, lambda: self.quick_add(field=self.add_field_box.currentData() or ""),
                              "A line that prints the chosen field (the volume's value) under the last line"))
        rv.addLayout(th)
        self.kind_lab = D.label("", "muted"); rv.addWidget(self.kind_lab)
        self.texts = QTableWidget(0, 3); self.texts.setHorizontalHeaderLabels(["Prints", "Where", "What it is"])
        self.texts.verticalHeader().setVisible(False); self.texts.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.texts.setMinimumHeight(220); rv.addWidget(self.texts)
        sp.addWidget(right); sp.setSizes([700, 480])
        bh = QHBoxLayout(); v.addLayout(bh)
        self.status = D.label("", "muted"); bh.addWidget(self.status, 1)
        bh.addWidget(D.button("Open a sample in Word", None, lambda: self.sample()))
        bh.addWidget(D.button("Save", "primary", lambda: self.save()))
        bh.addWidget(D.button("Cancel", "ghost", lambda: self.reject()))
        self.items = {}
        self.cur = None
        self.load()

    # ------------------------------------------------------------------ reading
    def load(self):
        self.loading = True
        self.scene.clear(); self.items = {}; self.list.clear(); self.texts.setRowCount(0)
        if not self.data:
            self.status.setText("No kept page yet: Import from a file... keeps one first.")
            self.loading = False
            return
        lay = CL.read(CL.apply(self.data, self.changes, self.page.work), self.page.work)
        pg = lay["page"]
        self.scene.setSceneRect(-10, -10, pg["w"] * DPI + 20, pg["h"] * DPI + 20)
        self.scene.addRect(QRectF(0, 0, pg["w"] * DPI, pg["h"] * DPI), QPen(QColor("#9aa3b2")), QBrush(QColor("#ffffff"))).setZValue(-2)
        m = pg["margins"]
        self.scene.addRect(QRectF(m["left"] * DPI, m["top"] * DPI, (pg["w"] - m["left"] - m["right"]) * DPI,
                                  (pg["h"] - m["top"] - m["bottom"]) * DPI), QPen(QColor("#d6dae2"), 0.8, Qt.DotLine)).setZValue(-1)
        self.pieces = lay["pieces"]
        try:                                              # 3.34.0: each floating table's and text box's words and look
            import coverbuild as CB
            blocks = CB.design_of(CL.apply(self.data, self.changes, self.page.work), self.page.work)["blocks"]
        except Exception:  # noqa: BLE001
            diag.swallowed()
            blocks = []
        for d in self.pieces:
            if d["kind"] in ("table", "textbox") and d.get("floating"):
                hit = next((b for b in blocks if abs(b["x"] - (d.get("x") or 0)) < 0.02 and abs(b["y"] - (d.get("y") or 0)) < 0.02), None)
                if hit is not None:
                    d["block"] = hit
        y_flow = m["top"]
        for d in self.pieces:
            if d["kind"] == "paragraph":
                continue
            if not d.get("floating"):                     # in the text flow: drawn where it roughly falls
                d = dict(d, x=m["left"], y=y_flow); y_flow += (d.get("h") or 0.3) + 0.1
            it = Piece(self, d); self.scene.addItem(it); self.items[d["id"]] = it
            li = QListWidgetItem(f"{KIND[d['kind']]}{' (floating)' if d.get('floating') else ' (in the text)'}: {d.get('text', '')[:40]}")
            li.setData(Qt.UserRole, d["id"]); self.list.addItem(li)
        fields = [("", "Your words")] + [(k, f"The {label} field ({style})") for k, label, style in CL.fields(self.page.work)]
        try:                                              # 3.40.0: which kind of page this is
            import pagekinds as PK
            self.kind_lab.setText(PK.describe(PK.kind_of(self.data, self.page.work)) + ".")
        except Exception:  # noqa: BLE001
            diag.swallowed()
        for d in self.pieces:
            if d["kind"] != "paragraph":
                continue
            r = self.texts.rowCount(); self.texts.insertRow(r)
            self.texts.setItem(r, 0, QTableWidgetItem(d["text"])); self.texts.setItem(r, 1, QTableWidgetItem(d["where"]))
            for c in (0, 1):
                self.texts.item(r, c).setFlags(Qt.ItemIsEnabled)
            cb = QComboBox()
            for k, label in fields:
                cb.addItem(label, k)
            cb.setCurrentIndex(max(0, cb.findData(d.get("field") or "")))
            cb.currentIndexChanged.connect(lambda _i, pid=d["id"], c=cb: self.bind(pid, c.currentData()))
            self.texts.setCellWidget(r, 2, cb)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.loading = False
        if self.list.count():
            self.list.setCurrentRow(0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "scene"):
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def pick(self, r):
        it = self.list.item(r) if r >= 0 else None
        self.cur = self.items.get(it.data(Qt.UserRole)) if it else None
        self.loading = True
        for k, s in self.sp.items():
            s.setEnabled(bool(self.cur) and (self.cur.d.get("movable") or k in ("w", "h") and self.cur.d["kind"] != "table"))
            if self.cur is not None:
                val = {"x": self.cur.pos().x() / DPI, "y": self.cur.pos().y() / DPI, "w": self.cur.rect().width() / DPI,
                       "h": self.cur.rect().height() / DPI}[k]
                s.setValue(round(val, 2))
        if self.cur is not None:
            self.scene.clearSelection(); self.cur.setSelected(True)
        self.loading = False

    # ------------------------------------------------------------------ changing
    def _change(self, pid):
        return self.changes.setdefault(pid, {})

    def moved(self, item):
        ch = self._change(item.d["id"])
        ch["x"], ch["y"] = round(item.pos().x() / DPI, 3), round(item.pos().y() / DPI, 3)
        if item is self.cur:
            self.loading = True
            self.sp["x"].setValue(round(ch["x"], 2)); self.sp["y"].setValue(round(ch["y"], 2))
            self.loading = False
        self.status.setText("Not saved yet.")

    def typed(self, k):
        if self.loading or self.cur is None:
            return
        it = self.cur
        ch = self._change(it.d["id"])
        if k in ("x", "y"):
            it.setPos(self.sp["x"].value() * DPI, self.sp["y"].value() * DPI)
            ch["x"], ch["y"] = self.sp["x"].value(), self.sp["y"].value()
        else:
            w, h = self.sp["w"].value(), self.sp["h"].value()
            ow, oh = it.rect().width() / DPI or 1, it.rect().height() / DPI or 1
            if self.keep_ratio.isChecked() and it.d["kind"] == "picture":
                if k == "w":
                    h = round(w * oh / ow, 3)
                else:
                    w = round(h * ow / oh, 3)
                self.loading = True; self.sp["w"].setValue(w); self.sp["h"].setValue(h); self.loading = False
            it.setRect(0, 0, w * DPI, h * DPI)
            ch["w"], ch["h"] = w, h
        self.status.setText("Not saved yet.")

    def bind(self, pid, key):
        self._change(pid)["field"] = key or ""
        self.status.setText("Not saved yet.")

    def result_bytes(self):
        return CL.apply(self.data, self.changes, self.page.work)

    # ------------------------------------------------------------------ 3.34.0 background and text blocks
    def _fold(self):
        """The moves and fields so far written into the page, so a picture or block goes on top of them."""
        self.data = self.result_bytes()
        self.changes = {}

    def background(self, path=None, mode=None):
        import coverbuild as CB
        from PySide6.QtWidgets import QFileDialog
        if not self.data:
            return False
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Background picture", os.path.expanduser("~"),
                                                  "Pictures (*.png *.jpg *.jpeg *.emf *.gif *.bmp *.tif *.tiff)")
            if not path:
                return False
        if mode is not None:
            self.bg_mode.setCurrentIndex(max(0, self.bg_mode.findData(mode)))
        self._fold()
        try:
            with open(path, "rb") as f:
                self.data = CB.set_background(self.data, f.read(), os.path.splitext(path)[1], self.bg_mode.currentData())
        except (OSError, ValueError) as e:
            self.status.setText(str(e) if isinstance(e, ValueError) else "That picture could not be read.")
            return False
        self.load()
        self.status.setText("Background picture set. Not saved yet.")
        diag.activity("cover_background_set")
        return True

    def take_background(self):
        import coverbuild as CB
        if not self.data:
            return False
        self._fold()
        self.data = CB.take_background(self.data)
        self.load()
        self.status.setText("Background picture taken off. Not saved yet.")
        return True

    def add_block(self, block=None):
        import coverbuild as CB
        if not self.data:
            return False
        if block is None:
            d = BlockDialog(self, self.page.work, CL.read(self.data, self.page.work)["page"])
            if d.exec() != QDialog.Accepted:
                return False
            block = d.block()
        self._fold()
        self.data = CB.add_block(self.data, block, self.page.work)
        self.load()
        self.status.setText("Text block added. Not saved yet.")
        diag.activity("cover_block_added")
        return True

    def quick_add(self, field="", text=""):
        """3.40.0: a line added under the last text block: the field's line, or your own words (asked for, or given here).
        Place and size it by dragging or in the boxes above."""
        if not self.data:
            return False
        pg = CL.read(self.data, self.page.work)["page"]
        m = pg["margins"]
        ys = [(d.get("y") or 0) + (d.get("h") or 0) for d in CL.read(self.result_bytes(), self.page.work)["pieces"]
              if d.get("floating") and d["kind"] in ("table", "textbox")]
        y = round(min(max(ys + [2.5]) + 0.15, pg["h"] - m["bottom"] - 0.6), 2)
        if not field and not text:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "Add text", "The words this line prints:")
            if not ok or not text.strip():
                return False
            text = text.strip()
        return self.add_block({"field": field, "text": text, "x": m["left"], "y": y, "w": round(pg["w"] - m["left"] - m["right"], 2),
                               "h": 0.45, "size": None, "bold": False, "color": None, "font": None, "align": "left"})

    def _block_index(self, pid):
        """The text block (0 first) a table piece is, or -1 for a table not made here."""
        import coverbuild as CB
        if not pid or not pid.startswith("table"):
            return -1
        root = CB._open(self.result_bytes())[2]
        tables = [t for t in root.find(CB.w("body")).iter(CB.w("tbl"))
                  if t.getparent() is not None and t.getparent().tag == CB.w("body")]
        n = int(pid[5:]) - 1
        bs = CB.blocks(root)
        return bs.index(tables[n]) if 0 <= n < len(tables) and tables[n] in bs else -1

    def remove_block(self, pid=None):
        import coverbuild as CB
        pid = pid or (self.cur.d["id"] if self.cur is not None else None)
        n = self._block_index(pid)
        if n < 0:
            self.status.setText("Pick a text block made here (a table on the page) first.")
            return False
        self._fold()
        self.data = CB.remove_block(self.data, n)
        self.load()
        self.status.setText("Text block taken off. Not saved yet.")
        return True

    def save_layout(self, name=None, label=""):
        """The page's structure (paper, where the background goes, its text blocks) as a cover layout in the template
        library: the next version when the name is kept already. Returns the library item."""
        import coverbuild as CB
        import pagekinds as PK
        import templatelib as TL
        from PySide6.QtWidgets import QInputDialog
        if not self.data:
            return None
        k = PK.kind_of(self.data, self.page.work)
        if k and k != "placed":                           # 3.40.0: a cover layout is a placed page; never convert one
            self.status.setText(f"{PK.describe(k)}: a cover layout would turn it into a placed page. Keep in the library... "
                                "keeps it as it is.")
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "Save as a cover layout", "Layout name (an existing name gets a new version):")
            if not ok or not name.strip():
                return None
            label, _ok = QInputDialog.getText(self, "Save as a cover layout", "Label (optional):")
        design = CB.design_of(self.result_bytes(), self.page.work)
        lib = TL.Library(self.page.host.config_dir)
        have = next((i for i in lib.shelf("cover_design") if lib.base_of(i).casefold() == name.strip().casefold()), None)
        if have is not None:
            item, _st = lib.save_version(have["id"], design, label=label or "")
        else:
            item, _st = lib.add("cover_design", name.strip(), design, summary=f"{len(design['blocks'])} text block(s)"
                                + (f", background {design['background']}" if design["background"] else ""))
            if label:
                lib.set_label(item["id"], label)
        self.status.setText(f"Kept as the cover layout {lib.shown_name(item)}"
                            + (f"; {design['left_out']} line(s) in the page's flow are not in it" if design["left_out"] else "") + ".")
        diag.activity("cover_layout_kept")
        return item

    def keep_in_library(self, name=None, label=""):
        """This page as it is (picture and all) on its shelf in the template library (covers, title pages, back covers),
        as the next version when the name is kept already."""
        import hashlib, tempfile
        import templatelib as TL
        from PySide6.QtWidgets import QInputDialog
        if not self.data:
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "Keep in the library", "Name (an existing name gets a new version):")
            if not ok or not name.strip():
                return None
        data = self.result_bytes()
        lib = TL.Library(self.page.host.config_dir)
        fn = lib.keep_file(data, f"{name.strip()}.docx")
        values = {"file": fn, "sha": hashlib.sha256(data).hexdigest()[:16]}
        have = next((i for i in lib.shelf(self.key) if lib.base_of(i).casefold() == name.strip().casefold()), None)
        if have is not None:
            item, _st = lib.save_version(have["id"], values, label=label or "")
        else:
            item, _st = lib.add(self.key, name.strip(), values, summary="built in the layout editor")
            if label:
                lib.set_label(item["id"], label)
        self.status.setText(f"Kept in the template library as {lib.shown_name(item)}.")
        return item

    # ------------------------------------------------------------------ keeping it
    def save(self):
        """A new kept copy with the changes, made this part's page; the one before stays in the parts folder."""
        if not self.data:
            return None
        import prodparts as PP
        name = PP.save_part(self.page.parts_dir(), self.result_bytes(), f"{ {'title': 'title page'}.get(self.key, self.key) } layout")
        self.page.work.setdefault("page_parts", {})[self.key] = name
        self.page.show_parts(); self.page.changed()
        try:
            from . import docparts as DP
            DP.fill(self.page, "cover" if self.key == "title" else self.key)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        diag.activity("cover_layout_saved")
        what = {"cover": "cover", "title": "title page"}.get(self.key, "back cover")
        self.page.host.status(f"The {what} layout is saved as a new copy. Save keeps it in this standard.")
        self.accept()
        return name

    def sample(self, open_it=True):
        """A sample template with this layout (the changes not yet saved), in the Samples folder."""
        import copy
        import sys
        import tempfile
        import prodparts as PP
        import prodrules as PRL
        import prodtemplate as PT
        tmpdir = tempfile.mkdtemp(prefix="sk_cover_")
        for fn in os.listdir(self.page.parts_dir()) if os.path.isdir(self.page.parts_dir()) else []:
            try:
                import shutil
                shutil.copyfile(os.path.join(self.page.parts_dir(), fn), os.path.join(tmpdir, fn))
            except OSError:
                pass
        name = PP.save_part(tmpdir, self.result_bytes(), f"{self.key} layout")
        std = PRL.engine_ready(copy.deepcopy(self.page.work))
        std.setdefault("page_parts", {})[self.key] = name
        std["name"] = "Sample cover layout"
        try:
            job = PT.make(std, os.path.join(self.page.template_folder(), "Samples"), "", parts_dir=tmpdir)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.status.setText(f"The sample could not be made ({type(e).__name__}).")
            return None
        if open_it and sys.platform.startswith("win"):
            try:
                os.startfile(job.copy)                   # noqa: S606  the sample copy only
            except OSError:
                diag.swallowed()
        self.status.setText(f"Sample: {job.copy}")
        return job.copy


class BlockDialog(QDialog):
    """3.34.0: a text block: what it shows (a field, or its own words), where it sits and how wide, and its look."""

    def __init__(self, parent, std, page):
        super().__init__(parent)
        from PySide6.QtWidgets import QDialogButtonBox, QLineEdit, QSpinBox
        self.setWindowTitle("Text block"); self.setMinimumWidth(460)
        f = QFormLayout(self)
        self.field = QComboBox(); self.field.addItem("Its own words", "")
        for k, label, style in CL.fields(std):
            self.field.addItem(f"{label} ({style})", k)
        f.addRow("Shows", self.field)
        self.text = QLineEdit(); self.text.setPlaceholderText("The words, when it shows its own"); f.addRow("Words", self.text)
        self.sp = {}
        m = page["margins"]
        for k, lab, val in (("x", "From the left (in)", m["left"]), ("y", "From the top (in)", 3.0), ("w", "Width (in)", page["w"] - m["left"] - m["right"]),
                            ("h", "Height (in)", 0.6)):
            s = QDoubleSpinBox(); s.setRange(0, 40); s.setDecimals(2); s.setSingleStep(0.1); s.setValue(round(val, 2)); f.addRow(lab, s); self.sp[k] = s
        self.size = QSpinBox(); self.size.setRange(0, 200); self.size.setSpecialValueText("its style's"); self.size.setValue(0); f.addRow("Size (pt)", self.size)
        self.bold = QCheckBox("Bold"); f.addRow("", self.bold)
        self.color = QLineEdit(); self.color.setPlaceholderText("Hex, such as 1F3864 (blank: its style's)"); f.addRow("Color", self.color)
        self.font = QLineEdit(); self.font.setPlaceholderText("Blank: its style's"); f.addRow("Font", self.font)
        self.align = QComboBox()
        for k, label in (("left", "Left"), ("center", "Centered"), ("right", "Right")):
            self.align.addItem(label, k)
        f.addRow("Alignment", self.align)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def block(self):
        return {"field": self.field.currentData() or "", "text": self.text.text().strip(), "x": self.sp["x"].value(), "y": self.sp["y"].value(),
                "w": self.sp["w"].value(), "h": self.sp["h"].value(), "size": self.size.value() or None, "bold": self.bold.isChecked(),
                "color": self.color.text().strip() or None, "font": self.font.text().strip() or None, "align": self.align.currentData()}
