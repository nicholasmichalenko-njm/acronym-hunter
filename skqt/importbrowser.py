"""Import from a file as one browser (3.44.0): what the template or Word document holds, by layer (Building blocks,
Components, Sections) on the left; the selected group's items in the middle, each New, Same as the library or Differs
(with what differs), each with a tick box; a picture of the selected item on the right. Take the ticked puts every
ticked item into what is being edited (Use here) and the library (Keep in the library), as ticked at the top. The file
is read once and never written; macros never run."""
import copy
import os
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QSplitter,
                               QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import diag
import importbrowse as IB
import templatelib as TL
from . import design as D

TONE = {"new": "accent", "same": "ok", "variant": "warn"}
FILTERS = [("all", "Everything"), ("new", "New"), ("variant", "Differs"), ("same", "Same as the library")]


class ItemPicture(QWidget):
    """A picture of one item: a style as a sample paragraph in it; a page setup or section as a page with its margins,
    header and footer; a table look as a sample table; anything else its summary."""
    def __init__(self):
        super().__init__()
        self.it = None
        self.setMinimumSize(260, 300)

    def show_item(self, it):
        self.it = it
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(D.tokens()["surface2"]))
        it = self.it
        r = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        p.setPen(QColor(D.tokens()["text"]))
        if not it:
            p.drawText(r, Qt.AlignCenter | Qt.TextWordWrap, "Select an item to see it.")
            p.end(); return
        k, v = it["kind"], it.get("values") or {}
        if k == "style":
            draw_style(p, r, it["name"], v)
        elif k in ("page_setup", "section"):
            draw_page(p, r, v.get("page") if k == "section" else v, it)
        elif k == "table_look":
            draw_table(p, r, v)
        else:
            p.drawText(r, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, f"{it['name']}\n\n{it.get('summary') or ''}")
        p.end()


def draw_style(p, r, name, v):
    f = QFont(str(v.get("font") or "Calibri"))
    f.setPointSizeF(max(6.0, min(28.0, float(v.get("size") or 11))))
    f.setBold(bool(v.get("bold"))); f.setItalic(bool(v.get("italic")))
    f.setCapitalization(QFont.AllUppercase if v.get("caps") else QFont.MixedCase)
    p.setFont(f)
    col = v.get("color")
    p.setPen(QColor("#" + col) if isinstance(col, str) and len(col) == 6 else QColor(D.tokens()["text"]))
    sample = "Section heading" if name.lower().startswith(("heading", "title")) else \
        "Body text in this style: how a paragraph of the volume reads, line after line, at this size and spacing."
    al = {"center": Qt.AlignHCenter, "right": Qt.AlignRight, "both": Qt.AlignJustify}.get(v.get("jc"), Qt.AlignLeft)
    p.drawText(r.adjusted(0, 0, 0, -40), al | Qt.AlignTop | Qt.TextWordWrap, sample)
    small = QFont(); small.setPointSizeF(8); p.setFont(small); p.setPen(QColor(D.tokens()["muted"]))
    bits = [str(v.get("font") or ""), f"{v.get('size')} pt" if v.get("size") else "", "bold" if v.get("bold") else "",
            "hidden text" if v.get("hidden") else "", f"based on {v['based_on']}" if v.get("based_on") else ""]
    p.drawText(QRectF(r.left(), r.bottom() - 34, r.width(), 34), Qt.AlignLeft | Qt.TextWordWrap, f"{name}: " + ", ".join(b for b in bits if b))


def _num(x, d):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def draw_page(p, r, pg, it):
    pg = pg or {}
    w, h = _num(pg.get("w"), 8.5), _num(pg.get("h"), 11)
    s = min(r.width() / w, (r.height() - 40) / h)
    page = QRectF(r.left() + (r.width() - w * s) / 2, r.top(), w * s, h * s)
    p.setPen(QPen(QColor("#9aa3b2"), 1)); p.setBrush(QColor("#ffffff")); p.drawRect(page); p.setBrush(Qt.NoBrush)
    m = [_num(pg.get(k), 1) for k in ("top", "bottom", "left", "right")]
    body = QRectF(page.left() + m[2] * s, page.top() + m[0] * s, page.width() - (m[2] + m[3]) * s, page.height() - (m[0] + m[1]) * s)
    p.setPen(QPen(QColor("#c7cdd8"), 1, Qt.DashLine)); p.drawRect(body)
    small = QFont(); small.setPointSizeF(7); p.setFont(small); p.setPen(QColor("#1f2937"))
    v = it.get("values") or {}
    for kind, y in (("header", page.top() + 4), ("footer", page.bottom() - 16)):
        txt = IB.hf_text(v.get(kind)) if it["kind"] == "section" else ""
        if txt:
            p.drawText(QRectF(body.left(), y, body.width(), 12), Qt.AlignHCenter, p.fontMetrics().elidedText(txt, Qt.ElideRight, int(body.width())))
    p.setPen(QColor(D.tokens()["muted"]))
    p.drawText(QRectF(r.left(), page.bottom() + 6, r.width(), 30), Qt.AlignHCenter | Qt.TextWordWrap, it.get("summary") or "")


def draw_table(p, r, v):
    rows = (v.get("row_types") or {}) if isinstance(v, dict) else {}
    order = [x for x in ("caption", "header", "body", "subtotal", "total", "note") if x in rows] or list(rows)[:5]
    y = r.top()
    small = QFont(); small.setPointSizeF(8); p.setFont(small)
    for role in order:
        look = rows.get(role) or {}
        fill = look.get("fill")
        rr = QRectF(r.left(), y, r.width(), 22)
        if isinstance(fill, str) and len(fill) == 6:
            p.fillRect(rr, QColor("#" + fill))
        p.setPen(QPen(QColor("#64748b"), 0.8)); p.drawRect(rr)
        p.setPen(QColor("#" + look["color"]) if isinstance(look.get("color"), str) and len(look["color"]) == 6 else QColor("#1f2937"))
        p.drawText(rr.adjusted(6, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft, role.title())
        y += 24


class ImportBrowser(QDialog):
    def __init__(self, page, path, only=None, section=""):
        super().__init__(page)
        self.page, self.path = page, path
        self.only = set(only) if only else None
        self.lib = TL.Library(page.host.config_dir)
        self.setWindowTitle(f"Import from {os.path.basename(path)}" + (f": {section}" if section else ""))
        self.resize(1180, 720)
        v = QVBoxLayout(self)
        v.addWidget(D.label("The file is read once and never written; macros never run. Tick what you want, from any group, "
                            "and press Take the ticked.", "muted"))
        wh = QHBoxLayout(); v.addLayout(wh)
        self.use_here = QCheckBox("Use here (in what you are editing: " + page.scope_box.currentText() + ")"); self.use_here.setChecked(True)
        self.keep_lib = QCheckBox("Keep in the library (to use in any standard later)"); self.keep_lib.setChecked(True)
        wh.addWidget(self.use_here); wh.addWidget(self.keep_lib); wh.addStretch(1)
        tf = QFormLayout(); v.addLayout(tf)
        uw = QWidget(); uh = QHBoxLayout(uw); uh.setContentsMargins(0, 0, 0, 0)
        self.uses = {}
        for u in TL.USES:
            cb = QCheckBox(u); uh.addWidget(cb); self.uses[u] = cb
        uh.addStretch(1)
        tf.addRow("Use case", uw)
        self.ptype = QLineEdit(); self.ptype.setPlaceholderText("Proposal type (optional)"); tf.addRow("Proposal type", self.ptype)
        self.cust = QLineEdit(); self.cust.setPlaceholderText("Customer (optional)"); tf.addRow("Customer", self.cust)
        import prodrules as PRL
        from .collectview import installed_fonts
        self.cards, err = IB.collect(path, PRL.engine_ready(copy.deepcopy(page.work)), self.lib, installed_fonts())
        if self.only is not None:
            for c in self.cards:
                c.items = [it for it in c.items if it["kind"] in self.only]
            self.cards = [c for c in self.cards if c.items]
            if not self.cards and not err:
                err = f"That file carries nothing for {section or 'this section'}."
        for c in self.cards:
            for it in c.items:
                it["keep"] = it["state"] != "same"
                it["differs"] = IB.differs(self.lib, it)[1]
        self.error = err
        self.used, self.qp_ids = [], []
        self.saved = {"new": 0, "same": 0, "variant": 0}
        self.note = D.label(err or "", "muted"); v.addWidget(self.note)
        sp = QSplitter(Qt.Horizontal); v.addWidget(sp, 1)
        self.tree = QTreeWidget(); self.tree.setHeaderHidden(True); self.tree.setMinimumWidth(240)
        self.tree.currentItemChanged.connect(lambda *_a: self.show_group())
        sp.addWidget(self.tree)
        mid = QWidget(); mv = QVBoxLayout(mid); mv.setContentsMargins(0, 0, 0, 0)
        fr = QHBoxLayout(); mv.addLayout(fr)
        self.head = D.label("", "title"); fr.addWidget(self.head, 1)
        self.filter = QComboBox()
        for k, t in FILTERS:
            self.filter.addItem(t, k)
        self.filter.currentIndexChanged.connect(lambda _i: self.show_group())
        fr.addWidget(self.filter)
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Take", "Name", "In the library", "What it is"])
        self.t.verticalHeader().setVisible(False); self.t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.t.setColumnWidth(0, 46); self.t.setColumnWidth(1, 220); self.t.setColumnWidth(2, 230)
        self.t.itemChanged.connect(self.read_row)
        self.t.currentCellChanged.connect(lambda *_a: self.show_picture())
        mv.addWidget(self.t, 1)
        br = QHBoxLayout(); mv.addLayout(br)
        br.addWidget(D.button("Tick all shown", "ghost", lambda: self.tick_shown(True)))
        br.addWidget(D.button("Untick all shown", "ghost", lambda: self.tick_shown(False)))
        br.addWidget(D.button("Open a sample in Word", None, lambda: self.sample(), "A small template made with the ticked items "
                              "of the groups shown, so you see them in use before keeping them"))
        br.addStretch(1)
        sp.addWidget(mid)
        self.picture = ItemPicture(); sp.addWidget(self.picture)
        sp.setSizes([250, 640, 290])
        row = QHBoxLayout(); v.addLayout(row)
        self.count_lab = D.label("", "muted"); row.addWidget(self.count_lab, 1)
        self.take_btn = D.button("Take the ticked", "primary", lambda: self.take()); row.addWidget(self.take_btn)
        row.addWidget(D.button("Close", "ghost", lambda: self.reject()))
        self.shown = []
        self.fill_tree()

    def done(self, r):
        TL.cleanup(self.lib)
        super().done(r)

    def tags(self):
        return {"use": [u for u, cb in self.uses.items() if cb.isChecked()], "proposal_type": self.ptype.text().strip(),
                "customer": self.cust.text().strip()}

    # ---- the tree of groups by layer
    def fill_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        first = None
        for lk, lt in IB.LAYERS:
            cards = [c for c in self.cards if IB.layer_of(c) == lk]
            if not cards:
                continue
            top = QTreeWidgetItem([f"{lt} ({sum(len(c.items) for c in cards)})"]); top.setData(0, Qt.UserRole, "layer:" + lk)
            self.tree.addTopLevelItem(top)
            for c in cards:
                n_new = sum(1 for it in c.items if it["state"] == "new"); n_var = sum(1 for it in c.items if it["state"] == "variant")
                badge = ", ".join(x for x in (f"{n_new} new" if n_new else "", f"{n_var} differ" if n_var else "") if x)
                ch = QTreeWidgetItem([c.title + (f"  [{badge}]" if badge else "")]); ch.setData(0, Qt.UserRole, c.key)
                top.addChild(ch)
                first = first or ch
            top.setExpanded(True)
        self.tree.blockSignals(False)
        if first is not None:
            self.tree.setCurrentItem(first)
        else:
            self.show_group()
        self.count()

    def group(self):
        it = self.tree.currentItem()
        key = it.data(0, Qt.UserRole) if it else None
        if not key:
            return []
        if key.startswith("layer:"):
            return [c for c in self.cards if IB.layer_of(c) == key[6:]]
        return [c for c in self.cards if c.key == key]

    def select(self, key):
        """Select a group (a card key) or a layer ("layer:blocks")."""
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for it in [top] + [top.child(j) for j in range(top.childCount())]:
                if it.data(0, Qt.UserRole) == key:
                    self.tree.setCurrentItem(it)
                    return True
        return False

    def show_group(self):
        cards = self.group()
        want = self.filter.currentData() or "all"
        self.shown = [it for c in cards for it in c.items if want == "all" or it["state"] == want]
        self.head.setText(", ".join(c.title for c in cards) if len(cards) == 1 else (f"{len(cards)} groups" if cards else ""))
        self.t.blockSignals(True)
        self.t.setRowCount(0)
        for it in self.shown:
            r = self.t.rowCount(); self.t.insertRow(r)
            k = QTableWidgetItem(); k.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            k.setCheckState(Qt.Checked if it["keep"] else Qt.Unchecked); self.t.setItem(r, 0, k)
            self.t.setItem(r, 1, QTableWidgetItem(it["name"]))
            txt = IB.BADGE[it["state"]] + (f": {it['differs']}" if it.get("differs") else (f" ({it['match']})" if it["state"] == "same" and it["match"] else ""))
            si = QTableWidgetItem(txt); si.setFlags(Qt.ItemIsEnabled); si.setToolTip(txt); si.setForeground(D.color(TONE[it["state"]]))
            self.t.setItem(r, 2, si)
            w = QTableWidgetItem(it["summary"]); w.setFlags(Qt.ItemIsEnabled); w.setToolTip(it["summary"]); self.t.setItem(r, 3, w)
        self.t.blockSignals(False)
        if self.shown:
            self.t.setCurrentCell(0, 1)
        self.show_picture()

    def read_row(self, cell):
        r = cell.row()
        if 0 <= r < len(self.shown):
            it = self.shown[r]
            if cell.column() == 0:
                it["keep"] = cell.checkState() == Qt.Checked
            elif cell.column() == 1:
                it["name"] = " ".join(cell.text().split()) or it["name"]
        self.count()

    def tick_shown(self, on):
        for r in range(self.t.rowCount()):
            self.t.item(r, 0).setCheckState(Qt.Checked if on else Qt.Unchecked)

    def show_picture(self):
        r = self.t.currentRow()
        self.picture.show_item(self.shown[r] if 0 <= r < len(self.shown) else None)

    def ticked(self):
        return [it for c in self.cards for it in c.items if it.get("keep")]

    def count(self):
        n = len(self.ticked())
        self.count_lab.setText(f"{n} item(s) ticked across every group." if n else "Nothing ticked.")
        self.take_btn.setEnabled(bool(n) and (self.use_here.isChecked() or self.keep_lib.isChecked()))

    # ---- take
    def take(self):
        """Every ticked item into what is being edited and the library, as ticked at the top. Returns the counts kept."""
        picked = self.ticked()
        if not picked:
            return self.saved
        if self.use_here.isChecked():
            for it in picked:
                if it["kind"] == "font":
                    continue
                try:
                    said = TL.use_values(self.lib.config_dir, it["kind"], it["name"], it["values"], self.page.work, src=self.path)
                    if said:
                        self.used.append(said)
                except Exception:  # noqa: BLE001
                    diag.swallowed()
        if self.keep_lib.isChecked():
            got = TL.save_collected(self.lib, self.path, self.cards, tags=self.tags(), quickparts=self.qp_ids)
            for k in got:
                self.saved[k] += got[k]
        for it in picked:
            it["keep"] = False
            it["state"] = "same" if self.keep_lib.isChecked() else it["state"]
        diag.activity("template_library_collected", n=self.saved["new"] + self.saved["variant"])
        if self.used:
            self.page.after_library(f"{len(self.used)} item(s) from {os.path.basename(self.path)}")
        self.measure_kept()
        self.note.setText(f"Taken: {len(picked)} item(s)" + (f"; {self.saved['new']} new and {self.saved['variant']} new version(s) in the library"
                                                               if self.keep_lib.isChecked() else "") + ".")
        self.fill_tree()
        return self.saved

    def measure_kept(self):
        """3.32.0: the Quick Parts just kept measure their pages once, by Word on this PC, off the window's thread."""
        import qpmeasure as QM
        if not self.qp_ids or not QM.available() or (os.environ.get("AH_TEST") and not os.environ.get("SK_MEASURE_TEST")):
            return False                                # tests never start a real Word
        from .progress import JobWorker
        ids, cfg, host = list(self.qp_ids), self.lib.config_dir, self.page.host
        w = JobWorker(lambda _p, _s: QM.measure(TL.Library(cfg), ids))
        w.done.connect(lambda r: host.toast(f"{sum(1 for v in (r or {}).values() if isinstance(v, int))} Quick Part(s) measured by Word."
                                            if isinstance(r, dict) else "Word could not measure the Quick Parts' pages."))
        self.page._qp_measure = w                       # the page keeps it running after this browser closes
        w.start()
        self.qp_ids = []
        return True

    def sample(self, open_it=True):
        """A small template with the ticked items of the groups shown, in the Samples folder; opened in Word when it is there."""
        import prodrules as PRL
        import prodtemplate as PT
        import prodparts as PP
        cards = self.group()
        work = copy.deepcopy(self.page.work)
        tmp = TL.Library(os.path.join(self.lib.root, "_collecting", "sample_cfg"))
        for c in cards:
            for it in c.items:
                if it["keep"] and it["kind"] not in ("font",):
                    vals = dict(it["values"])
                    if it["kind"] in ("cover", "backer"):
                        vals["file"] = tmp.keep_file(vals.pop("_tmp"), vals["file"])
                    if it["kind"] == "quickpart":
                        vals["source"] = tmp.keep_file(self.path, os.path.basename(self.path))
                    item, _st = tmp.add(it["kind"], it["name"], vals)
                    TL.use_in_standard(tmp, item["id"], work)
        std = PRL.engine_ready(work); std["_parts_dir"] = PP.parts_dir(tmp.config_dir)
        std["name"] = "Sample " + (cards[0].title.split(" (")[0] if len(cards) == 1 else "import")
        folder = os.path.join(self.page.template_folder(), "Samples")
        try:
            job = PT.make(std, folder)
        except Exception as e:                           # noqa: BLE001
            diag.swallowed()
            self.page.host.status(f"The sample could not be made ({type(e).__name__}).")
            return None
        if open_it and sys.platform.startswith("win"):
            try:
                os.startfile(job.copy)                   # noqa: S606  the sample copy, never the source
            except OSError:
                diag.swallowed()
        self.page.host.status(f"Sample: {job.copy}")
        return job.copy
