"""Import from a Word file (3.49.0): what the template or Word document holds, by where it will land (Formatting
Standards, Quick Parts, Layout, each by category) on the left; the selected group's items in the middle, each New, Same
as (Show me) or Differs (what differs), with a tick and what to do with it in the library (Add, Add as a new version,
Keep both, Replace, Do not keep); a picture of the selected item on the right. Take the ticked keeps everything at once
or nothing (libimport); Undo this import takes it back. Use here, on Production Standards, puts the ticked items into
what is being edited only after the library kept them. Quick Parts' pages are measured by a button, never here. The file
is read once and never written; macros never run."""
import copy
import os
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QMenu, QSplitter,
                               QTableWidget, QTableWidgetItem, QTextBrowser, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

import diag
import importbrowse as IB
import libcats as LC
import libimport as LI
import templatelib as TL
from . import design as D

TONE = {"new": "accent", "same": "ok", "variant": "warn"}
FILTERS = [("all", "Everything"), ("new", "New"), ("variant", "Differs"), ("same", "Same as the library")]


def effort_type_names(config_dir):
    """[(id, name)] of the effort types on this PC."""
    try:
        import prodrules as PRL
        return [(e["id"], e["name"]) for e in PRL.load(config_dir).get("effort_types", [])]
    except Exception:  # noqa: BLE001  no effort types: every item is for every effort type
        diag.swallowed()
        return []


class EffortTypesButton(QToolButton):
    """Every effort type, or some: a menu of ticks. chosen() is [ALL] or the ids ticked."""
    def __init__(self, config_dir, chosen=(LC.ALL,)):
        super().__init__()
        self.names = effort_type_names(config_dir)
        self.setPopupMode(QToolButton.InstantPopup)
        self.menu_ = QMenu(self); self.setMenu(self.menu_)
        self.all_act = self.menu_.addAction("Every effort type"); self.all_act.setCheckable(True)
        self.menu_.addSeparator()
        self.acts = {}
        for eid, nm in self.names:
            a = self.menu_.addAction(nm); a.setCheckable(True); self.acts[eid] = a
            a.toggled.connect(lambda on, _e=eid: self._one(on))
        self.all_act.toggled.connect(self._all)
        self.set(chosen)

    def _all(self, on):
        if on:
            for a in self.acts.values():
                a.blockSignals(True); a.setChecked(False); a.blockSignals(False)
        self._words()

    def _one(self, on):
        if on:
            self.all_act.blockSignals(True); self.all_act.setChecked(False); self.all_act.blockSignals(False)
        if not on and not any(a.isChecked() for a in self.acts.values()):
            self.all_act.setChecked(True)
        self._words()

    def set(self, ets):
        ets = list(ets or [LC.ALL])
        self.all_act.blockSignals(True); self.all_act.setChecked(LC.ALL in ets or not ets); self.all_act.blockSignals(False)
        for eid, a in self.acts.items():
            a.blockSignals(True); a.setChecked(LC.ALL not in ets and eid in ets); a.blockSignals(False)
        self._words()

    def chosen(self):
        got = [e for e, a in self.acts.items() if a.isChecked()]
        return got if got and not self.all_act.isChecked() else [LC.ALL]

    def _words(self):
        ch = self.chosen()
        self.setText("Effort types: " + ("every effort type" if LC.ALL in ch else ", ".join(dict(self.names).get(e, e) for e in ch)))


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
    def __init__(self, page, path, only=None, section="", library=None):
        super().__init__(page)
        self.page, self.path = page, path
        self.only = set(only) if only else None
        cfg = page.host.config_dir
        self.lib = TL.Library(cfg)
        self.edits_here = hasattr(page, "work") and hasattr(page, "scope_box")
        self.setWindowTitle(f"Import from {os.path.basename(path)}" + (f": {section}" if section else ""))
        self.resize(1240, 760)
        v = QVBoxLayout(self)
        v.addWidget(D.label("The file is read once and never written; macros never run. Each item lands in its library and "
                            "category. Tick what you want, choose what to do with each, and press Take the ticked: everything "
                            "is kept at once, or nothing is.", "muted"))
        wh = QHBoxLayout(); v.addLayout(wh)
        self.use_here = QCheckBox("Use here (in what you are editing" + (": " + page.scope_box.currentText() if self.edits_here else "") + ")")
        self.use_here.setChecked(self.edits_here); self.use_here.setVisible(self.edits_here)
        self.keep_lib = QCheckBox("Keep in the libraries"); self.keep_lib.setChecked(True); self.keep_lib.setVisible(self.edits_here)
        self.use_here.toggled.connect(lambda _on: self.count()); self.keep_lib.toggled.connect(lambda _on: self.count())
        wh.addWidget(self.use_here); wh.addWidget(self.keep_lib)
        self.ets = EffortTypesButton(cfg); self.ets.setToolTip("The effort types new items are for (change them later on the library screens)")
        wh.addWidget(self.ets); wh.addStretch(1)
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
        std = PRL.engine_ready(copy.deepcopy(page.work)) if self.edits_here else PRL.for_effort(cfg)
        try:
            self.items, err = LI.stage(path, std, self.lib, installed_fonts(), self.only)
        except Exception as e:  # noqa: BLE001  a file that cannot be read says so; nothing changed
            diag.error("library_import", "A file could not be read for import", exc=(type(e), e, e.__traceback__))
            self.items, err = [], f"The file could not be read ({type(e).__name__}). Nothing changed."
        self.items = [it for it in self.items if it.get("library")]
        if self.only is not None and not self.items and not err:
            err = f"That file carries nothing for {section or 'this section'}."
        self.error = err
        self.report = None
        self.used = []
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
        self.t = QTableWidget(0, 5); self.t.setHorizontalHeaderLabels(["Take", "Name", "In the library", "What to do", "What it is"])
        self.t.verticalHeader().setVisible(False); self.t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.t.setColumnWidth(0, 46); self.t.setColumnWidth(1, 210); self.t.setColumnWidth(2, 230); self.t.setColumnWidth(3, 190)
        self.t.itemChanged.connect(self.read_row)
        self.t.currentCellChanged.connect(lambda *_a: self.show_picture())
        mv.addWidget(self.t, 1)
        br = QHBoxLayout(); mv.addLayout(br)
        br.addWidget(D.button("Tick all shown", "ghost", lambda: self.tick_shown(True)))
        br.addWidget(D.button("Untick all shown", "ghost", lambda: self.tick_shown(False)))
        self.all_action = QComboBox(); self.all_action.addItem("For every item shown...", "")
        for k, t in LI.ACTIONS:
            self.all_action.addItem(t, k)
        self.all_action.activated.connect(lambda _i: self.act_shown(self.all_action.currentData()))
        br.addWidget(self.all_action)
        br.addWidget(D.button("Show me", None, lambda: self.show_match(), "The library's item this one is the same as, or "
                              "differs from, value by value"))
        br.addWidget(D.button("Open a sample in Word", None, lambda: self.sample(), "A small template made with the ticked items "
                              "of the groups shown, so you see them in use before keeping them"))
        br.addStretch(1)
        sp.addWidget(mid)
        self.picture = ItemPicture(); sp.addWidget(self.picture)
        sp.setSizes([250, 690, 290])
        row = QHBoxLayout(); v.addLayout(row)
        self.count_lab = D.label("", "muted"); row.addWidget(self.count_lab, 1)
        self.undo_btn = D.button("Undo this import", "ghost", lambda: self.undo()); self.undo_btn.setVisible(False)
        row.addWidget(self.undo_btn)
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

    # ---- the tree: library, then category
    def fill_tree(self):
        cur = self.tree.currentItem().data(0, Qt.UserRole) if self.tree.currentItem() else None
        self.tree.blockSignals(True)
        self.tree.clear()
        first = None
        for lk, lt in LC.LIBRARIES:
            mine = [it for it in self.items if it["library"] == lk]
            if not mine:
                continue
            top = QTreeWidgetItem([f"{lt} ({len(mine)})"]); top.setData(0, Qt.UserRole, "lib:" + lk)
            self.tree.addTopLevelItem(top)
            cats = [c for c, _t in LC.categories(self.lib, lk)] if lk != "quickparts" else []
            cats += [c for c in dict.fromkeys(it["category"] for it in mine) if c not in cats]
            for c in cats:
                its = [it for it in mine if it["category"] == c]
                if not its:
                    continue
                n_new = sum(1 for it in its if it["state"] == "new"); n_var = sum(1 for it in its if it["state"] == "variant")
                badge = ", ".join(x for x in (f"{n_new} new" if n_new else "", f"{n_var} differ" if n_var else "") if x)
                ch = QTreeWidgetItem([f"{LC.category_title(lk, c)} ({len(its)})" + (f"  [{badge}]" if badge else "")])
                ch.setData(0, Qt.UserRole, f"cat:{lk}:{c}")
                top.addChild(ch)
                first = first or ch
            top.setExpanded(True)
        self.tree.blockSignals(False)
        if not (cur and self.select(cur)):
            if first is not None:
                self.tree.setCurrentItem(first)
            else:
                self.show_group()
        self.count()

    def group(self):
        """The staged items of the selected library or category."""
        it = self.tree.currentItem()
        key = it.data(0, Qt.UserRole) if it else None
        if not key:
            return []
        if key.startswith("lib:"):
            return [x for x in self.items if x["library"] == key[4:]]
        _c, lk, cat = key.split(":", 2)
        return [x for x in self.items if x["library"] == lk and x["category"] == cat]

    def select(self, key):
        """Select a library ("lib:formatting") or a category ("cat:formatting:para_styles")."""
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for it in [top] + [top.child(j) for j in range(top.childCount())]:
                if it.data(0, Qt.UserRole) == key:
                    self.tree.setCurrentItem(it)
                    return True
        return False

    def show_group(self):
        want = self.filter.currentData() or "all"
        self.shown = [it for it in self.group() if want == "all" or it["state"] == want]
        cur = self.tree.currentItem()
        self.head.setText(cur.text(0).split("  [")[0] if cur else "")
        self.t.blockSignals(True)
        self.t.setRowCount(0)
        for it in self.shown:
            r = self.t.rowCount(); self.t.insertRow(r)
            k = QTableWidgetItem(); k.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            k.setCheckState(Qt.Checked if it["take"] else Qt.Unchecked); self.t.setItem(r, 0, k)
            self.t.setItem(r, 1, QTableWidgetItem(it["name"]))
            txt = IB.BADGE[it["state"]] + (f": {it['differs']}" if it.get("differs") else (f" ({it['match_name']})" if it["state"] == "same" and it.get("match_name") else ""))
            si = QTableWidgetItem(txt); si.setFlags(Qt.ItemIsEnabled); si.setToolTip(txt); si.setForeground(D.color(TONE[it["state"]]))
            self.t.setItem(r, 2, si)
            cb = QComboBox()
            for a in LI.ALLOWED[it["state"]]:
                cb.addItem(LI.ACTION[a], a)
            cb.setCurrentIndex(max(0, cb.findData(it["action"])))
            cb.currentIndexChanged.connect(lambda _i, _it=it, _cb=cb: self.set_action(_it, _cb.currentData()))
            self.t.setCellWidget(r, 3, cb)
            w = QTableWidgetItem(it["summary"]); w.setFlags(Qt.ItemIsEnabled); w.setToolTip(it["summary"]); self.t.setItem(r, 4, w)
        self.t.blockSignals(False)
        if self.shown:
            self.t.setCurrentCell(0, 1)
        self.show_picture()

    def set_action(self, it, action):
        if action in LI.ALLOWED[it["state"]]:
            it["action"] = action
        self.count()

    def act_shown(self, action):
        """One action for every item shown that allows it."""
        if action:
            for it in self.shown:
                if action in LI.ALLOWED[it["state"]]:
                    it["action"] = action
            self.show_group()
        self.all_action.setCurrentIndex(0)
        self.count()

    def read_row(self, cell):
        r = cell.row()
        if 0 <= r < len(self.shown):
            it = self.shown[r]
            if cell.column() == 0:
                it["take"] = cell.checkState() == Qt.Checked
            elif cell.column() == 1:
                it["name"] = " ".join(cell.text().split()) or it["name"]
        self.count()

    def tick_shown(self, on):
        for r in range(self.t.rowCount()):
            self.t.item(r, 0).setCheckState(Qt.Checked if on else Qt.Unchecked)

    def current(self):
        r = self.t.currentRow()
        return self.shown[r] if 0 <= r < len(self.shown) else None

    def show_picture(self):
        self.picture.show_item(self.current())

    def show_match(self, run=True):
        """The library item the selected one matches, its values next to the file's (what differs first)."""
        it = self.current()
        hit = self.lib.get(it["match"]) if it and it.get("match") else None
        if hit is None:
            self.page.host.status("The selected item is new: the library holds nothing like it.")
            return None
        rows, _line = IB.differs(self.lib, it, most=999)
        from .collectview import preview_html
        html = (f"<h3>{self.lib.shown_name(hit)}</h3>" + ("<p>The library holds these values already.</p>" if it["state"] == "same" else
                "<table cellpadding=4><tr><th align=left>What</th><th align=left>In the file</th><th align=left>In the library</th></tr>"
                + "".join(f"<tr><td>{k}</td><td>{a}</td><td>{b}</td></tr>" for k, a, b in rows[:80]) + "</table>")
                + "<hr>" + preview_html(self.lib, hit["id"]))
        d = QDialog(self); d.setWindowTitle("Show me: " + self.lib.shown_name(hit)); d.resize(640, 520)
        lv = QVBoxLayout(d); tb = QTextBrowser(); tb.setHtml(html); lv.addWidget(tb)
        lv.addWidget(D.button("Close", "ghost", d.accept))
        if run:
            d.exec()
        return html

    def ticked(self):
        return [it for it in self.items if it.get("take")]

    def count(self):
        n = len(self.ticked())
        keep = sum(1 for it in self.ticked() if it["action"] != "skip")
        self.count_lab.setText(f"{n} item(s) ticked across every group; {keep} to keep in the libraries." if n else "Nothing ticked.")
        self.take_btn.setEnabled(bool(n) and (self.use_here.isChecked() or self.keep_lib.isChecked()))

    # ---- take, all at once
    def take(self):
        """Keeps every ticked item at once (or nothing), then puts them into what is being edited (Use here). Returns
        the counts kept: {"new", "variant", "same"}."""
        picked = self.ticked()
        if not picked:
            return self.saved
        LI.restate(self.lib, self.items)                 # what the library holds now (another window may have kept items)
        here = self.edits_here and self.use_here.isChecked()
        try:
            new_work, said = LI.apply_here(self.lib.config_dir, picked, self.page.work, self.path) if here else (None, [])
            rep = LI.commit(self.lib, self.path, picked, self.ets.chosen(), self.tags()) if self.keep_lib.isChecked() else None
        except LI.ImportFailed as e:
            self.note.setText(f"Nothing was kept. It stopped while {e.step} ({type(e.cause).__name__}). The log has the details; "
                              "the libraries and what you are editing are as they were.")
            self.fill_tree()
            return self.saved
        if here:
            self.page.work.clear(); self.page.work.update(new_work)
            self.used += said
            if said and hasattr(self.page, "after_library"):
                self.page.after_library(f"{len(said)} item(s) from {os.path.basename(self.path)}")
        if rep is not None:
            self.report = rep
            self.saved["new"] += len(rep["added"]); self.saved["variant"] += len(rep["versions"]) + len(rep["replaced"])
            self.saved["same"] += rep["same"]
            self.undo_btn.setVisible(bool(rep["added"] or rep["versions"] or rep["replaced"]))
        for it in picked:
            it["take"] = False
        LI.restate(self.lib, self.items)
        self.note.setText((f"Kept: {LI.report_words(rep)}." if rep else "") + (f" Used here: {len(said)} item(s)." if here else ""))
        diag.activity("template_library_collected", n=self.saved["new"] + self.saved["variant"])
        refresh = getattr(self.page, "library_changed", None)
        if callable(refresh):
            refresh()
        self.fill_tree()
        return self.saved

    def undo(self):
        """Takes the last import back. Returns how many items it changed."""
        if not self.report:
            return 0
        n = LI.undo(self.lib, self.report["id"])
        self.report = None
        self.undo_btn.setVisible(False)
        LI.restate(self.lib, self.items)
        self.note.setText(f"Import taken back: {max(n, 0)} item(s).")
        refresh = getattr(self.page, "library_changed", None)
        if callable(refresh):
            refresh()
        self.fill_tree()
        return n

    def sample(self, open_it=True):
        """A small template with the ticked items of the groups shown, in the Samples folder; opened in Word when it is there."""
        import prodrules as PRL
        import prodtemplate as PT
        import prodparts as PP
        cfg = self.lib.config_dir
        work = copy.deepcopy(self.page.work) if self.edits_here else PRL.for_effort(cfg)
        tmp = TL.Library(os.path.join(self.lib.root, "_collecting", "sample_cfg"))
        for it in self.group():
            if it["take"] and it["kind"] not in ("font",):
                vals = dict(it["values"])
                if it["kind"] in ("cover", "backer", "title") and vals.get("_tmp"):
                    vals["file"] = tmp.keep_file(vals.pop("_tmp"), vals["file"])
                if it["kind"] == "quickpart":
                    vals["source"] = tmp.keep_file(self.path, os.path.basename(self.path))
                item, _st = tmp.add(it["kind"], it["name"], vals)
                TL.use_in_standard(tmp, item["id"], work)
        std = PRL.engine_ready(work); std["_parts_dir"] = PP.parts_dir(tmp.config_dir)
        std["name"] = "Sample " + (self.head.text().split(" (")[0] or "import")
        folder = os.path.join(self.page.template_folder() if hasattr(self.page, "template_folder") else os.path.join(cfg, "Templates"), "Samples")
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
