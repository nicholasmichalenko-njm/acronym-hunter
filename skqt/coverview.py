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
        self.label = QGraphicsSimpleTextItem(f"{KIND[d['kind']]}: {d.get('text', '')[:40]}", self)
        f = QFont(); f.setPointSizeF(7); self.label.setFont(f); self.label.setBrush(QBrush(QColor(tone)))
        self.label.setPos(2, 1)

    def paint(self, painter, option, widget=None):
        if self.pix is not None:
            painter.setOpacity(0.55)
            painter.drawPixmap(self.rect().toRect(), self.pix)
            painter.setOpacity(1.0)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and not self.dlg.loading:
            self.dlg.moved(self)
        return super().itemChange(change, value)


class CoverLayoutDialog(QDialog):
    def __init__(self, page, key, path=None):
        super().__init__(page)
        self.page, self.key = page, key
        self.loading = True
        fname = (page.work.get("page_parts") or {}).get(key)
        self.path = path or (os.path.join(page.parts_dir(), fname) if fname else "")
        self.data = open(self.path, "rb").read() if self.path and os.path.isfile(self.path) else b""
        self.changes = {}
        self.setWindowTitle("Edit the cover layout" if key == "cover" else "Edit the back cover layout")
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
        rv.addWidget(D.label("Text and the fields it shows", "title"))
        self.texts = QTableWidget(0, 3); self.texts.setHorizontalHeaderLabels(["Text", "Where", "Shows"])
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
        y_flow = m["top"]
        for d in self.pieces:
            if d["kind"] == "paragraph":
                continue
            if not d.get("floating"):                     # in the text flow: drawn where it roughly falls
                d = dict(d, x=m["left"], y=y_flow); y_flow += (d.get("h") or 0.3) + 0.1
            it = Piece(self, d); self.scene.addItem(it); self.items[d["id"]] = it
            li = QListWidgetItem(f"{KIND[d['kind']]}{' (floating)' if d.get('floating') else ' (in the text)'}: {d.get('text', '')[:40]}")
            li.setData(Qt.UserRole, d["id"]); self.list.addItem(li)
        fields = [("", "Its own text")] + [(k, f"{label} ({style})") for k, label, style in CL.fields(self.page.work)]
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

    # ------------------------------------------------------------------ keeping it
    def save(self):
        """A new kept copy with the changes, made this part's page; the one before stays in the parts folder."""
        if not self.data:
            return None
        import prodparts as PP
        name = PP.save_part(self.page.parts_dir(), self.result_bytes(), f"{self.key} layout")
        self.page.work.setdefault("page_parts", {})[self.key] = name
        self.page.show_parts(); self.page.changed()
        try:
            from . import docparts as DP
            DP.fill(self.page, self.key)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        diag.activity("cover_layout_saved")
        self.page.host.status(f"The {'cover' if self.key == 'cover' else 'back cover'} layout is saved as a new copy. Save keeps it in this standard.")
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
