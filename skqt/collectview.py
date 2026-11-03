"""Collect and the template library (3.22.0): read a template or Word document, confirm what it carries card by card,
and keep it on the library's shelves; then browse, rename, tag, take out, or use an item in the standard being edited.
The rules are templatelib.py's; nothing leaves the PC."""
import os, sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import templatelib as TL
from . import design as D

STATE = {"new": ("New", "accent"), "same": ("Already in the library", "ok"), "variant": ("Variant (same name, other values)", "warn")}


def installed_fonts():
    try:
        return list(QFontDatabase.families())
    except Exception:                                    # noqa: BLE001
        diag.swallowed()
        return None


class CollectDialog(QDialog):
    """The file and its tags, then one card per group: keep, rename or skip each item. Next saves the card's items at
    once, so stopping keeps what was confirmed."""

    def __init__(self, page, path):
        super().__init__(page)
        self.page, self.path = page, path
        self.lib = TL.Library(page.host.config_dir)
        self.setWindowTitle(f"Collect from {os.path.basename(path)}")
        self.resize(1000, 640)
        v = QVBoxLayout(self)
        v.addWidget(D.label("The file is read once and never written; macros never run. Tick what to keep, rename anything, "
                            "and press Next: each card is saved as you go.", "muted"))
        tf = QFormLayout(); v.addLayout(tf)
        uw = QWidget(); uh = QHBoxLayout(uw); uh.setContentsMargins(0, 0, 0, 0)
        self.uses = {}
        for u in TL.USES:
            cb = QCheckBox(u); uh.addWidget(cb); self.uses[u] = cb
        uh.addStretch(1)
        tf.addRow("Use case", uw)
        self.ptype = QLineEdit(); self.ptype.setPlaceholderText("Proposal type (optional)"); tf.addRow("Proposal type", self.ptype)
        self.prog = QLineEdit(); self.prog.setPlaceholderText("Program type (optional)"); tf.addRow("Program type", self.prog)
        self.cust = QLineEdit(); self.cust.setPlaceholderText("Customer (optional)"); tf.addRow("Customer", self.cust)
        import prodrules as PRL
        import copy
        self.cards, err = TL.collect(path, PRL.engine_ready(copy.deepcopy(page.work)), self.lib, installed_fonts())
        self.error = err
        self.step = 0
        self.saved = {"new": 0, "same": 0, "variant": 0}
        self.head = D.label("", "title"); v.addWidget(self.head)
        self.note = D.label("", "muted"); v.addWidget(self.note)
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Keep", "Name", "In the library", "What it is"])
        self.t.verticalHeader().setVisible(False); self.t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.t.setColumnWidth(0, 50); self.t.setColumnWidth(1, 220); self.t.setColumnWidth(2, 200)
        v.addWidget(self.t, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Keep all", "ghost", lambda: self.tick_all(True)))
        row.addWidget(D.button("Skip all", "ghost", lambda: self.tick_all(False)))
        self.sample_btn = D.button("Open a sample in Word", None, lambda: self.sample(), "A small template made with this card's items, "
                                   "so you see them in use before keeping them")
        row.addWidget(self.sample_btn)
        row.addStretch(1)
        self.back_btn = D.button("Back", None, lambda: self.go(-1)); row.addWidget(self.back_btn)
        self.next_btn = D.button("Next", "primary", lambda: self.go(1)); row.addWidget(self.next_btn)
        row.addWidget(D.button("Close", "ghost", lambda: self.reject()))
        self.show_card()

    def done(self, r):
        TL.cleanup(self.lib)
        super().done(r)

    def tags(self):
        return {"use": [u for u, cb in self.uses.items() if cb.isChecked()], "proposal_type": self.ptype.text().strip(),
                "program_type": self.prog.text().strip(), "customer": self.cust.text().strip()}

    def show_card(self):
        if self.error or not self.cards:
            self.head.setText("Nothing to collect"); self.note.setText(self.error or "That file carries nothing the library keeps.")
            self.t.setRowCount(0); self.next_btn.setEnabled(False); self.back_btn.setEnabled(False)
            return
        c = self.cards[self.step]
        self.head.setText(f"{self.step + 1} of {len(self.cards)}: {c.title}")
        self.note.setText(c.note)
        self.t.setRowCount(0)
        for it in c.items:
            r = self.t.rowCount(); self.t.insertRow(r)
            k = QTableWidgetItem(); k.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled); k.setCheckState(Qt.Checked if it["keep"] else Qt.Unchecked)
            self.t.setItem(r, 0, k)
            self.t.setItem(r, 1, QTableWidgetItem(it["name"]))
            st, tone = STATE[it["state"]]
            si = QTableWidgetItem(st + (f": {it['match']}" if it["match"] and it["state"] != "new" else "")); si.setFlags(Qt.ItemIsEnabled)
            si.setForeground(D.color(tone)); self.t.setItem(r, 2, si)
            w = QTableWidgetItem(it["summary"]); w.setFlags(Qt.ItemIsEnabled); w.setToolTip(it["summary"]); self.t.setItem(r, 3, w)
        self.back_btn.setEnabled(self.step > 0)
        self.next_btn.setText("Keep and finish" if self.step == len(self.cards) - 1 else "Keep and next")

    def read_card(self):
        c = self.cards[self.step]
        for r, it in enumerate(c.items):
            it["keep"] = self.t.item(r, 0).checkState() == Qt.Checked
            it["name"] = " ".join(self.t.item(r, 1).text().split()) or it["name"]
        return c

    def tick_all(self, on):
        for r in range(self.t.rowCount()):
            self.t.item(r, 0).setCheckState(Qt.Checked if on else Qt.Unchecked)

    def go(self, step):
        if not self.cards:
            return None
        if step > 0:
            c = self.read_card()
            got = TL.save_collected(self.lib, self.path, [c], tags=self.tags())
            for k in got:
                self.saved[k] += got[k]
            for it in c.items:                           # saved: met again, they are the library's now
                it["keep"] = False
            if self.step == len(self.cards) - 1:
                diag.activity("template_library_collected", n=self.saved["new"] + self.saved["variant"])
                self.accept()
                return self.saved
        self.step = max(0, min(len(self.cards) - 1, self.step + step))
        self.show_card()
        return self.saved

    def sample(self, open_it=True):
        """A small template with this card's items in use, in the Samples folder; opened in Word when it is there."""
        import copy
        import prodrules as PRL
        import prodtemplate as PT
        c = self.read_card()
        work = copy.deepcopy(self.page.work)
        tmp = TL.Library(os.path.join(self.lib.root, "_collecting", "sample_cfg"))
        for it in c.items:
            if it["keep"] and it["kind"] not in ("font",):
                vals = dict(it["values"])
                if it["kind"] in ("cover", "backer"):
                    vals["file"] = tmp.keep_file(vals.pop("_tmp"), vals["file"])
                if it["kind"] == "quickpart":
                    vals["source"] = tmp.keep_file(self.path, os.path.basename(self.path))
                item, _st = tmp.add(it["kind"], it["name"], vals)
                TL.use_in_standard(tmp, item["id"], work)
        import prodparts as PP
        std = PRL.engine_ready(work); std["_parts_dir"] = PP.parts_dir(tmp.config_dir)
        std["name"] = f"Sample {c.title.split(' (')[0]}"
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


class StyleDialog(QDialog):
    """A style's definition, every property of the style library (blank: not set)."""

    def __init__(self, parent, name, values, fixed_name=False):
        super().__init__(parent)
        from .prodstdpage import STYLE_COLS, TRI_KEYS
        self.cols, self.tri = [c for c in STYLE_COLS if c[0] != "key"], TRI_KEYS
        self.setWindowTitle("Style"); self.resize(560, 680)
        v = QVBoxLayout(self)
        f = QFormLayout()
        from PySide6.QtWidgets import QScrollArea
        sc = QScrollArea(); sc.setWidgetResizable(True); inner = QWidget(); inner.setLayout(f); sc.setWidget(inner); v.addWidget(sc, 1)
        self.name = QLineEdit(name); self.name.setReadOnly(fixed_name); f.addRow("Name", self.name)
        self.ed = {}
        for key, label, kind in self.cols:
            if isinstance(kind, tuple):
                cb = QComboBox()
                for val, txt in kind[1]:
                    cb.addItem(txt, val)
                cur = values.get(key)
                cur = ("on" if cur else "off") if key in self.tri and cur is not None else (cur or "")
                cb.setCurrentIndex(max(0, cb.findData(cur)))
                self.ed[key] = cb
            else:
                le = QLineEdit("" if values.get(key) is None else str(values.get(key)))
                self.ed[key] = le
            f.addRow(label, self.ed[key])
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        from .prodstdpage import tabs_parse
        out = {}
        for key, _label, kind in self.cols:
            w = self.ed[key]
            if isinstance(w, QComboBox):
                val = w.currentData()
                if val in ("", None):
                    continue
                out[key] = (val == "on") if key in self.tri else val
            else:
                t = w.text().strip()
                if not t:
                    continue
                if kind == "num0":
                    try:
                        out[key] = float(t)
                    except ValueError:
                        continue
                elif key == "tabs":
                    out[key] = tabs_parse(t)
                else:
                    out[key] = t
        return " ".join(self.name.text().split()), out


class ValuesDialog(QDialog):
    """An item's values, one by one (lists and groups shown as they are, to edit with care)."""

    def __init__(self, parent, name, values):
        super().__init__(parent)
        import json
        self.json = json
        self.setWindowTitle(f"Edit: {name}"); self.resize(620, 520)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each value as it is kept. Numbers in points or inches as shown; a group stays in brackets.", "muted"))
        self.t = QTableWidget(0, 2); self.t.setHorizontalHeaderLabels(["Value", "Setting"])
        self.t.verticalHeader().setVisible(False); self.t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.keys = []
        for k, val in values.items():
            if str(k).startswith("_") or k in ("xml",):
                continue
            r = self.t.rowCount(); self.t.insertRow(r)
            a = QTableWidgetItem(str(k)); a.setFlags(Qt.ItemIsEnabled); self.t.setItem(r, 0, a)
            self.t.setItem(r, 1, QTableWidgetItem(val if isinstance(val, str) else json.dumps(val)))
            self.keys.append(k)
        self.base = dict(values)
        v.addWidget(self.t, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        out = dict(self.base)
        for r, k in enumerate(self.keys):
            t = self.t.item(r, 1).text()
            if isinstance(self.base[k], str):
                out[k] = t
            else:
                try:
                    out[k] = self.json.loads(t)
                except ValueError:
                    pass
        return out


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def preview_html(lib, iid):
    if not iid or str(iid).startswith("kit:"):
        k = lib.kit(str(iid)[4:]) if iid else None
        return f"<b>{_esc(k['name'])}</b>: {len(k['items'])} item(s)" if k else ""
    it = lib.get(iid)
    v = lib.values(it) if it else None
    if it is None or v is None:
        return ""
    if it["kind"] == "style":
        css = []
        if v.get("font") and not str(v["font"]).startswith("+"):
            css.append(f"font-family:'{_esc(v['font'])}'")
        if isinstance(v.get("size"), (int, float)):
            css.append(f"font-size:{v['size']}pt")
        if v.get("bold"):
            css.append("font-weight:bold")
        if v.get("italic"):
            css.append("font-style:italic")
        if v.get("color") and str(v["color"]).upper() != "AUTO":
            css.append(f"color:#{_esc(v['color'])}")
        if v.get("caps"):
            css.append("text-transform:uppercase")
        if v.get("hidden"):
            css.append("text-decoration:underline dotted")
        sample = _esc(it["name"]) + ": The Offeror shall describe its technical approach."
        return (f"<div style=\"{';'.join(css)}\">{sample}</div>"
                + (f"<div style='color:{D.tokens()['muted']}'>Hidden text: shows only with Show/Hide on.</div>" if v.get("hidden") else ""))
    if it["kind"] == "font":
        return f"<div style=\"font-family:'{_esc(v.get('font', ''))}';font-size:14pt\">{_esc(v.get('font', ''))}: Aa Bb Cc 0123456789</div>"
    if it["kind"] == "theme":
        sw = "".join(f"<span style='background:#{c};color:#{c}'>&nbsp;&nbsp;&nbsp;&nbsp;</span>&nbsp;" for c in v.get("colors", {}).values())
        return f"<div>{sw}</div><div>Headings: {_esc(v.get('major') or '-')}; body: {_esc(v.get('minor') or '-')}</div>"
    return f"<b>{_esc(it['name'])}</b>: {_esc(it.get('summary', ''))}"


class LibraryDialog(QDialog):
    """The shelves: browse by kind and use case; rename, tag, take out, or use an item in the standard being edited."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.lib = TL.Library(page.host.config_dir)
        self.setWindowTitle("Template library")
        self.resize(1080, 620)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Everything collected from templates and Word documents, kept on this PC as the team's data (the Our "
                            "data file carries it). Use in this standard puts an item into what you are editing.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.label("Use case", "label"))
        self.use = QComboBox(); self.use.addItem("Every use case", None)
        for u in TL.USES:
            self.use.addItem(u, u)
        self.use.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.use); top.addStretch(1)
        top.addWidget(D.button("Collect from a file...", "primary", lambda: self.collect()))
        body = QHBoxLayout(); v.addLayout(body, 1)
        self.shelves = QListWidget(); self.shelves.setFixedWidth(210)
        self.shelves.currentRowChanged.connect(lambda _r: self.fill())
        body.addWidget(self.shelves)
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Name", "Tags", "From", "What it is"])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QTableWidget.SelectRows)
        self.t.setEditTriggers(QTableWidget.NoEditTriggers); self.t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.t.setColumnWidth(0, 220); self.t.setColumnWidth(1, 200); self.t.setColumnWidth(2, 180)
        body.addWidget(self.t, 1)
        self.preview = QLabel(); self.preview.setWordWrap(True); self.preview.setMinimumHeight(70)    # 3.23.0
        self.preview.setTextFormat(Qt.RichText)
        self.preview.setStyleSheet(f"background:{D.tokens()['surface2']};border:1px solid {D.tokens()['border']};padding:8px;")
        v.addWidget(self.preview)
        self.t.currentCellChanged.connect(lambda *_a: self.show_preview())
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Use in this standard", "primary", lambda: self.use_it()))
        row.addWidget(D.button("New style...", None, lambda: self.new_style(), "A style of your own (hidden text ones too), "
                               "kept here to pull into any standard"))
        row.addWidget(D.button("Edit...", None, lambda: self.edit()))
        row.addWidget(D.button("Rename...", None, lambda: self.rename()))
        row.addWidget(D.button("Use cases...", None, lambda: self.retag()))
        row.addWidget(D.button("Take out", "ghost", lambda: self.remove()))
        row.addWidget(D.button("Save as a kit...", None, lambda: self.save_kit(), "The selected items (Ctrl+click for several, on "
                               "any shelf) as a named kit: start a standard from it and change only what the effort needs"))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); row.addWidget(bb)
        self.t.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.kit_pick = []                         # items picked for a kit, across shelves
        self.fill_shelves()

    def fill_shelves(self):
        cur = self.shelves.currentRow()
        self.shelves.blockSignals(True)
        self.shelves.clear()
        for k, t in TL.SHELVES:
            it = QListWidgetItem(f"{t} ({len(self.lib.shelf(k))})"); it.setData(Qt.UserRole, k); self.shelves.addItem(it)
        it = QListWidgetItem(f"Kits ({len(self.lib.kits)})"); it.setData(Qt.UserRole, "kit"); self.shelves.addItem(it)
        self.shelves.blockSignals(False)
        self.shelves.setCurrentRow(max(0, cur))
        self.fill()

    def kind(self):
        it = self.shelves.currentItem()
        return it.data(Qt.UserRole) if it else TL.SHELVES[0][0]

    def fill(self):
        if self.kind() == "kit":
            self.t.setRowCount(0)
            for k in self.lib.kits:
                r = self.t.rowCount(); self.t.insertRow(r)
                names = [self.lib.get(i)["name"] for i in k["items"] if self.lib.get(i)]
                for c, s in enumerate((k["name"], ", ".join(k.get("tags", {}).get("use", [])), f"{len(names)} item(s)", ", ".join(names))):
                    cell = QTableWidgetItem(s); cell.setToolTip(s)
                    if c == 0:
                        cell.setData(Qt.UserRole, "kit:" + k["id"])
                    self.t.setItem(r, c, cell)
            return len(self.lib.kits)
        items = self.lib.shelf(self.kind(), self.use.currentData())
        self.t.setRowCount(0)
        for i in items:
            r = self.t.rowCount(); self.t.insertRow(r)
            tg = i.get("tags") or {}
            tags = ", ".join(tg.get("use", []) + [x for x in (tg.get("proposal_type"), tg.get("program_type"), tg.get("customer")) if x])
            for c, s in enumerate((i["name"] + (" (variant)" if i.get("variant_of") else ""), tags, i.get("source", ""), i.get("summary", ""))):
                cell = QTableWidgetItem(s); cell.setToolTip(s)
                if c == 0:
                    cell.setData(Qt.UserRole, i["id"])
                self.t.setItem(r, c, cell)
        return len(items)

    def show_preview(self):
        """3.23.0: what the item looks like: a style as text in its font, size, weight, color and caps (hidden text
        marked); a font in itself; a theme's colors; anything else its summary."""
        html = preview_html(self.lib, self.selected())
        self.preview.setText(html)
        return html

    def selected(self):
        r = self.t.currentRow()
        it = self.t.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it else None

    def collect(self, path=None):
        r = self.page.collect(path)
        self.lib.load(); self.fill_shelves()
        return r

    def save_kit(self, name=None):
        """The selected rows (on this shelf, plus those picked on other shelves) as a kit."""
        ids = [self.t.item(i.row(), 0).data(Qt.UserRole) for i in self.t.selectionModel().selectedRows()] if self.t.selectionModel() else []
        ids = [i for i in ids if i and not str(i).startswith("kit:")]
        if not ids:
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "Save as a kit", "Kit name (for example: Space Force page-limited RFP). "
                                            "An existing name adds these items to it:")
            if not ok:
                return None
        use = [self.use.currentData()] if self.use.currentData() else []
        k = self.lib.add_kit(name, ids, tags={"use": use} if use else None)
        self.fill_shelves()
        return k

    def use_it(self, category=None):
        iid = self.selected()
        if not iid:
            return ""
        if str(iid).startswith("kit:"):            # a kit: every item in it
            said = TL.use_kit(self.lib, iid[4:], self.page.work)
            if said:
                self.page.after_library(f"kit with {len(said)} item(s)")
            return "; ".join(said)
        it = self.lib.get(iid)
        if it["kind"] == "hf_design" and category is None:          # 3.24.0: which part it heads
            v = self.lib.values(it) or {}
            parts = [p.get("key") for p in (self.page.work.get("pagination") or {}).get("parts", []) if p.get("key")] or ["cover", "front", "body", "appendix"]
            cur = parts.index(v.get("part")) if v.get("part") in parts else 0
            category, ok = QInputDialog.getItem(self, "Header and footer design", "The part of the page scheme it heads:", parts, cur, False)
            if not ok:
                return ""
        if it["kind"] == "quickpart" and category is None:
            v = self.lib.values(it) or {}
            category, ok = QInputDialog.getText(self, "Quick Parts category", "Category in the Quick Parts menu (01 Covers, 02 Title pages...):",
                                                text=v.get("category", ""))
            if not ok:
                return ""
        said = TL.use_in_standard(self.lib, iid, self.page.work, category or "")
        if said:
            self.page.after_library(said)
        return said

    def new_style(self, name=None, values=None, uses=()):
        """A style made here (values, tests: its definition). Returns the item."""
        if values is None:
            d = StyleDialog(self, name or "", {})
            if d.exec() != QDialog.Accepted:
                return None
            name, values = d.values()
        if not name:
            return None
        values = dict({"type": "paragraph"}, **values)
        item, _st = self.lib.add("style", name, values, tags={"use": list(uses)}, source="made in Stationkeeper",
                                 summary=TL._summary_style(values))
        k = [k for k, _t in TL.SHELVES].index("style")
        self.fill_shelves(); self.shelves.setCurrentRow(k); self.fill()
        diag.activity("template_library_style_made")
        return item

    def edit(self, values=None):
        """Change an item's values: a style in the style form, anything else value by value."""
        iid = self.selected()
        it = self.lib.get(iid) if iid else None
        if it is None:
            return False
        cur = self.lib.values(it) or {}
        if values is None:
            d = StyleDialog(self, it["name"], cur, fixed_name=True) if it["kind"] == "style" else ValuesDialog(self, it["name"], cur)
            if d.exec() != QDialog.Accepted:
                return False
            values = d.values()[1] if it["kind"] == "style" else d.values()
        ok = self.lib.update(iid, values)
        self.fill()
        return ok

    def rename(self, name=None):
        iid = self.selected()
        if not iid:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename", "Name:", text=self.lib.get(iid)["name"])
            if not ok:
                return False
        ok = self.lib.rename(iid, name)
        self.fill()
        return ok

    def retag(self, uses=None):
        iid = self.selected()
        if not iid:
            return False
        if uses is None:
            have = (self.lib.get(iid).get("tags") or {}).get("use", [])
            d = QDialog(self); d.setWindowTitle("Use cases"); dv = QVBoxLayout(d); boxes = {}
            for u in TL.USES:
                cb = QCheckBox(u); cb.setChecked(u in have); dv.addWidget(cb); boxes[u] = cb
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            dv.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return False
            uses = [u for u, cb in boxes.items() if cb.isChecked()]
        ok = self.lib.tag(iid, use=list(uses))
        self.fill()
        return ok

    def remove(self):
        iid = self.selected()
        if iid and str(iid).startswith("kit:"):
            ok = self.lib.remove_kit(iid[4:])
            self.fill_shelves()
            return ok
        ok = bool(iid) and self.lib.remove(iid)
        self.fill_shelves()
        return ok
