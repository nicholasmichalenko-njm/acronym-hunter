"""The template library as a page (3.44.0; a dialog from 3.22.0): the shelves by layer (building blocks, components,
sections), each as a list or as pictures, a search, versions, kits, and where each item is used. The rules are
templatelib.py's; nothing leaves the PC."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
                               QInputDialog, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import templatelib as TL
from . import design as D
from .collectview import StyleDialog, ValuesDialog, VersionsDialog, preview_html

LAYERS = (("blocks", "Building blocks"), ("components", "Components"), ("sections", "Sections"))
SHELF_LAYER = {"style": "blocks", "page_setup": "blocks", "heading_numbering": "blocks", "list_numbering": "blocks",
               "table_style": "blocks", "font": "blocks", "theme": "blocks", "variables": "blocks", "pagination": "blocks",
               "section": "sections", "part": "sections"}


def shelf_layer(kind):
    return SHELF_LAYER.get(kind, "components") if kind != "kit" else "components"


def item_icon(lib, i):
    """A small picture of a library item, drawn the way the import browser draws it."""
    from .itempicture import draw_page, draw_style, draw_table
    pm = QPixmap(150, 110); pm.fill(QColor("#ffffff"))
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    v = lib.values(i) or {}
    r = QRectF(6, 6, 138, 98)
    try:
        if i["kind"] == "style":
            draw_style(p, r, i["name"], v)
        elif i["kind"] in ("page_setup", "section"):
            draw_page(p, r, v.get("page") if i["kind"] == "section" else v, {"kind": i["kind"], "values": v, "summary": ""})
        elif i["kind"] == "table_look":
            draw_table(p, r, v)
        else:
            p.setPen(QColor("#1f2937"))
            p.drawText(r, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, f"{TL.SHELF.get(i['kind'], i['kind'])}\n{i.get('summary', '')[:90]}")
    except Exception:  # noqa: BLE001  a picture that cannot be drawn leaves the card blank
        diag.swallowed()
    p.setPen(QColor("#c7cdd8")); p.drawRect(QRectF(0.5, 0.5, 149, 109))
    p.end()
    return QIcon(pm)


def where_used(page, lib, iid):
    """The standards that carry an item by name: the one being edited and the saved Global Standards and volume
    profiles (styles, page setups, Quick Parts, table styles, header and footer designs)."""
    it = lib.get(iid) if iid and not str(iid).startswith("kit:") else None
    if it is None:
        return []
    name, k = lib.base_of(it) if hasattr(lib, "base_of") else it["name"], it["kind"]
    names = {it["name"], name}

    def has(std):
        std = std or {}
        if k == "style":
            return bool(names & set((std.get("style_defs") or {}).keys()))
        if k == "page_setup":
            return bool(names & set((std.get("page_setups") or {}).keys()))
        if k == "table_style":
            return bool(names & set((std.get("table_styles") or {}).keys()))
        if k == "quickpart":
            v = lib.values(it) or {}
            return any(e.get("name") == v.get("entry") for e in (std.get("quick_parts") or {}).get("entries") or [])
        return False
    out = []
    if has(page.work):
        out.append("the standard you are editing")
    try:
        import prodrules as PRL
        data = PRL.load(page.host.config_dir)
        if has(data.get("company") if isinstance(data, dict) else None):
            out.append("the Global Standards")
        for t in (data.get("types") or []) if isinstance(data, dict) else []:
            if has(t):
                out.append(t.get("name") or t.get("id") or "a volume profile")
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return out


class LibraryView(QWidget):
    """The shelves (3.44.0: a page of Production Standards): browse by layer, kind, use case and words, as a list or as
    pictures; rename, tag, take out, or use an item in the standard being edited; see where an item is used."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.lib = TL.Library(page.host.config_dir)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(D.label("Everything collected from templates and Word documents, kept on this PC as the team's data (the Our "
                            "data file carries it). Use in this standard puts an item into what you are editing.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.label("Use case", "label"))
        self.use = QComboBox(); self.use.addItem("Every use case", None)
        for u in TL.USES:
            self.use.addItem(u, u)
        self.use.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.use)
        top.addWidget(D.label("Layer", "label"))                  # 3.44.0: building blocks, components, sections
        self.layer = QComboBox(); self.layer.addItem("Every layer", None)
        for k, t in LAYERS:
            self.layer.addItem(t, k)
        self.layer.currentIndexChanged.connect(lambda _i: self.show_layer())
        top.addWidget(self.layer)
        self.search = QLineEdit(); self.search.setPlaceholderText("Find by name, tag or what it is")
        self.search.textChanged.connect(lambda _t: self.fill())
        top.addWidget(self.search, 1)
        self.pictures = QCheckBox("Pictures"); self.pictures.toggled.connect(lambda _on: self.fill())
        top.addWidget(self.pictures)
        top.addWidget(D.button("Import from a file...", "primary", lambda: self.collect()))
        body = QHBoxLayout(); v.addLayout(body, 1)
        self.shelves = QListWidget(); self.shelves.setFixedWidth(210)
        self.shelves.currentRowChanged.connect(lambda _r: self.fill())
        body.addWidget(self.shelves)
        self.t = QTableWidget(0, 5); self.t.setHorizontalHeaderLabels(["Name", "Tags", "From", "What it is", "Pages"])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QTableWidget.SelectRows)
        self.t.setEditTriggers(QTableWidget.NoEditTriggers); self.t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.t.setColumnWidth(0, 220); self.t.setColumnWidth(1, 200); self.t.setColumnWidth(2, 180); self.t.setColumnWidth(4, 120)
        self.grid = QListWidget(); self.grid.setViewMode(QListView.IconMode); self.grid.setIconSize(QSize(150, 110))
        self.grid.setGridSize(QSize(176, 160)); self.grid.setResizeMode(QListView.Adjust); self.grid.setMovement(QListView.Static)
        self.grid.setWordWrap(True); self.grid.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.grid.currentRowChanged.connect(lambda _r: self.show_preview())
        self.views = QStackedWidget(); self.views.addWidget(self.t); self.views.addWidget(self.grid)
        body.addWidget(self.views, 1)
        self.preview = QLabel(); self.preview.setWordWrap(True); self.preview.setMinimumHeight(70)    # 3.23.0
        self.preview.setTextFormat(Qt.RichText)
        D.themed(self.preview, lambda t: f"background:{t['surface2']};border:1px solid {t['border']};padding:8px;")
        v.addWidget(self.preview)
        self.where = D.label("", "muted"); v.addWidget(self.where)          # 3.44.0: the standards that carry it
        self.t.currentCellChanged.connect(lambda *_a: self.show_preview())
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Use in this standard", "primary", lambda: self.use_it()))
        row.addWidget(D.button("New style...", None, lambda: self.new_style(), "A style of your own (hidden text ones too), "
                               "kept here to pull into any standard"))
        row.addWidget(D.button("Edit...", None, lambda: self.edit()))
        row.addWidget(D.button("Rename...", None, lambda: self.rename()))
        row.addWidget(D.button("Use cases...", None, lambda: self.retag()))
        row.addWidget(D.button("Take out", "ghost", lambda: self.remove()))
        import qpmeasure as QM                    # 3.32.0: a Quick Part's pages, measured by Word or typed
        self.measure_btn = D.button("Measure pages", None, lambda: self.measure(), "Word on this PC counts the pages each "
                                    "selected Quick Part fills (all on the shelf when none is selected). The page plan, "
                                    "the page allocation and a prepaginated setup use them.")
        self.measure_btn.setEnabled(QM.available())
        row.addWidget(self.measure_btn)
        row.addWidget(D.button("Pages...", None, lambda: self.type_pages(), "Type the pages a Quick Part fills"))
        row.addWidget(D.button("Versions...", None, lambda: self.versions(), "The selected item's versions: label them, "
                               "compare two side by side"))                                   # 3.33.0
        row.addWidget(D.button("Save as a kit...", None, lambda: self.save_kit(), "The selected items (Ctrl+click for several, on "
                               "any shelf) as a named kit: start a standard from it and change only what the effort needs"))
        row.addStretch(1)
        self.t.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.kit_pick = []                         # items picked for a kit, across shelves
        self.fill_shelves()

    def fill_shelves(self):
        self.lib.fresh()                                # 3.49.0: what another window or an import kept since
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
        words = self.search.text().strip().casefold()
        if words:
            items = [i for i in items if words in " ".join([i.get("name", ""), i.get("summary", ""), i.get("source", ""),
                                                             " ".join(str(x) for x in (i.get("tags") or {}).values())]).casefold()]
        self.fill_grid(items)
        self.t.setRowCount(0)
        for i in items:
            r = self.t.rowCount(); self.t.insertRow(r)
            tg = i.get("tags") or {}
            tags = ", ".join(tg.get("use", []) + [x for x in (tg.get("proposal_type"), tg.get("program_type"), tg.get("customer")) if x])
            pg = (f"{i['pages']} ({i.get('pages_how', 'typed')})" if i.get("pages") else
                  ("not measured" if i["kind"] == "quickpart" else ""))
            for c, s in enumerate((self.lib.shown_name(i), tags, i.get("source", ""), i.get("summary", ""), pg)):   # 3.33.0: its version
                cell = QTableWidgetItem(s); cell.setToolTip(s)
                if c == 0:
                    cell.setData(Qt.UserRole, i["id"])
                self.t.setItem(r, c, cell)
        return len(items)

    def fill_grid(self, items):
        """3.44.0: the shelf as pictures: each item drawn (a style as sample text, a page or section as a page, a table
        look as a sample table), with its name and version under it."""
        self.views.setCurrentIndex(1 if self.pictures.isChecked() else 0)
        self.grid.clear()
        if not self.pictures.isChecked():
            return
        for i in items:
            gi = QListWidgetItem(item_icon(self.lib, i), self.lib.shown_name(i))
            gi.setData(Qt.UserRole, i["id"]); gi.setToolTip(i.get("summary", ""))
            self.grid.addItem(gi)

    def show_layer(self):
        want = self.layer.currentData()
        for r in range(self.shelves.count()):
            k = self.shelves.item(r).data(Qt.UserRole)
            self.shelves.item(r).setHidden(bool(want) and shelf_layer(k) != want)
        cur = self.shelves.currentItem()
        if cur is None or cur.isHidden():
            first = next((r for r in range(self.shelves.count()) if not self.shelves.item(r).isHidden()), 0)
            self.shelves.setCurrentRow(first)

    def show_preview(self):
        """3.23.0: what the item looks like: a style as text in its font, size, weight, color and caps (hidden text
        marked); a font in itself; a theme's colors; anything else its summary. 3.44.0: and where it is used."""
        iid = self.selected()
        html = preview_html(self.lib, iid)
        self.preview.setText(html)
        used = where_used(self.page, self.lib, iid)
        self.where.setText(("Used in: " + ", ".join(used) + ".") if used else ("Not used in any standard yet." if iid else ""))
        return html

    def selected(self):
        if self.pictures.isChecked():
            gi = self.grid.currentItem()
            return gi.data(Qt.UserRole) if gi else None
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
        if it["kind"] == "section" and category is None:          # 3.44.0: the part its header and footer head
            parts = ["(the page setup only)"] + ([p.get("key") for p in (self.page.work.get("pagination") or {}).get("parts", []) if p.get("key")]
                                                 or ["cover", "front", "body", "appendix"])
            category, ok = QInputDialog.getItem(self, "A section", "Its header and footer go on the part:", parts, 0, False)
            if not ok:
                return ""
            category = "" if category.startswith("(") else category
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

    def versions(self, run=True):
        """3.33.0: the selected item's family, newest first: label a version, compare two."""
        iid = self.selected()
        if not iid or str(iid).startswith("kit:"):
            return None
        d = VersionsDialog(self, self.lib, iid)
        if run:
            d.exec()
            self.lib.load(); self.fill()
        return d

    def _picked_quickparts(self):
        ids = [self.t.item(i.row(), 0).data(Qt.UserRole) for i in self.t.selectionModel().selectedRows()] if self.t.selectionModel() else []
        ids = [i for i in ids if i and (self.lib.get(i) or {}).get("kind") == "quickpart"]
        return ids or ([i["id"] for i in self.lib.shelf("quickpart")] if self.kind() == "quickpart" else [])

    def measure(self, ids=None, runner=None):
        """3.32.0: Word measures the selected Quick Parts' pages (every one on the shelf when none is selected). 3.49.0: in
        the background (qpjobs), one measuring at a time, the pages kept by this window when Word is done."""
        ids = ids if ids is not None else self._picked_quickparts()
        if not ids:
            self.page.host.status("Pick a Quick Part on the Quick Parts shelf first.")
            return {}
        from . import qpjobs
        if runner is not None:                          # tests: Word's answers given, measured here and now
            return qpjobs.measure_now(self.lib.config_dir, ids, runner, after=self._measured)
        ok = qpjobs.start(self.lib.config_dir, ids, after=self._measured)
        self.page.host.status("Word is measuring the Quick Parts' pages in the background." if ok else qpjobs.why_not())
        return {}

    def _measured(self, res):
        self.lib.load(); self.fill()
        n = sum(1 for v in res.values() if isinstance(v, int))
        bad = [v for v in res.values() if not isinstance(v, int)]
        self.page.host.toast(f"{n} Quick Part(s) measured." + (f" {len(bad)} not: {bad[0]}" if bad else ""))
        diag.activity("quickparts_measured", n=n)

    def type_pages(self, pages=None):
        """The pages a Quick Part fills, typed (0 takes them off)."""
        iid = self.selected()
        it = self.lib.get(iid) if iid else None
        if it is None or it["kind"] != "quickpart":
            self.page.host.status("Pick a Quick Part on the Quick Parts shelf first.")
            return False
        if pages is None:
            pages, ok = QInputDialog.getInt(self, "Pages", f"Pages {it['name']} fills (0 takes them off):", int(it.get("pages") or 1), 0, 500)
            if not ok:
                return False
        ok = self.lib.set_pages(iid, pages or None, "typed")
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


class LibraryDialog(QDialog):
    """The library in a window, for places outside Production Standards."""

    def __init__(self, page):
        super().__init__(page)
        self.setWindowTitle("Template library")
        self.resize(1080, 620)
        v = QVBoxLayout(self)
        self.view = LibraryView(page); v.addWidget(self.view)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); v.addWidget(bb)

    def __getattr__(self, name):
        return getattr(self.__dict__.get("view") or super().__getattribute__("view"), name)
