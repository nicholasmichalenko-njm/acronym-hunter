"""The Structure Builder (3.30.0): one page to build the response.

Left, the structure: volume tabs, parts, every section with its tag (H1 to H9 and deeper, UN unnumbered, DIV divider
page, PH placeholder, EL element, SEC when it starts a Word section), its requirements, captures and pages. A toolbar like
Word's style buttons makes the selected item Heading 1, 2, 3 or deeper, unnumbered, a divider or a placeholder, starts a
Word section, adds a section below or under it, moves it and takes it out; Enter, Tab, Shift+Tab, F2 and Delete do the
same from the keyboard, and a drag moves a section before, after or into another.

Middle, the selected section: what it is, its pages, and everything in it in order (its requirements and support, its
captures, the library items placed in it), to reorder or take out. Response Setup lives here now.

Right, the production library (Quick Parts, covers, table looks...) to place in the section, and what is not placed yet.

Add elements puts the Table of Contents, the lists, Acronyms and Abbreviations, the Appendices section and the rest
into a volume in one tick list (Settings > Response elements). Edit as text keeps the structure's text and Start from.
Make templates, Export the setup and Export changes only are on the toolbar. Rules only; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QMenu, QPushButton, QScrollArea, QSplitter, QTabBar,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QLineEdit, QInputDialog)
import os

import diag
import compliance as C
import outline_ops as O
import responseelements as RE
import setupdoc as SD
import structparts as SP
from . import design as D
from .structure import StructurePage

PART_COLOR = {"cover": "#64748B", "title": "#64748B", "front": "#6B4E9B", "body": "#2E7D5B", "appendix": "#A35A1E",
              "back": "#64748B"}


class BuilderTree(QTreeWidget):
    """The structure: a left double-click renames, a drag moves a section before, after or into another, and Enter,
    Tab, Shift+Tab, F2 and Delete work like an outline."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setHeaderLabels(["Section", "Kind", "Req.", "Cap.", "Pages"])
        self.setColumnWidth(0, 330); self.setColumnWidth(1, 64); self.setColumnWidth(2, 44); self.setColumnWidth(3, 44)
        self.setDragDropMode(QAbstractItemView.DragDrop)       # from itself, Not placed yet and the library
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragEnabled(True); self.setAcceptDrops(True); self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.LeftButton:
            e.accept()
            return
        it = self.itemAt(e.position().toPoint())
        if it is not None and it.data(0, Qt.UserRole):
            self.page.rename(it.data(0, Qt.UserRole))
            return
        super().mouseDoubleClickEvent(e)

    def _ok_source(self, e):
        return e.source() in (self, self.page.unp_list, self.page.lib_list)

    def dragEnterEvent(self, e):
        if self._ok_source(e):
            e.setDropAction(Qt.MoveAction); e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._ok_source(e):
            super().dragMoveEvent(e)
            e.setDropAction(Qt.MoveAction); e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        """A section onto a section moves it; a placed item, a Not placed yet item or a library item onto a section (or
        onto an item in it) goes into that section (before that item)."""
        tgt = self.itemAt(e.position().toPoint())
        pos = self.dropIndicatorPosition()
        src_w = e.source()
        e.setDropAction(Qt.IgnoreAction); e.accept()  # the structure changes, then the tree is drawn again
        if tgt is None:
            return
        tlab, tcon = tgt.data(0, Qt.UserRole), tgt.data(0, Qt.UserRole + 1)
        where = {QAbstractItemView.AboveItem: "before", QAbstractItemView.BelowItem: "after"}.get(pos, "into")
        if src_w is self.page.unp_list:
            return self.page.drop_unplaced([i.data(Qt.UserRole) for i in src_w.selectedItems() if i.data(Qt.UserRole)], tlab, tcon)
        if src_w is self.page.lib_list:
            it = src_w.currentItem()
            return self.page.drop_library(it.data(Qt.UserRole) if it is not None else None, tlab, tcon)
        src = self.currentItem()
        if src is None:
            return
        slab, scon = src.data(0, Qt.UserRole), src.data(0, Qt.UserRole + 1)
        if scon:
            return self.page.drop_content(scon, tlab, tcon, where)
        if slab and tlab:
            self.page.drop(slab, tlab, where)

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Return, Qt.Key_Enter) and not e.modifiers():
            return self.page.add_below()
        if k == Qt.Key_Tab:
            return self.page.level_down()
        if k == Qt.Key_Backtab:
            return self.page.level_up()
        if k == Qt.Key_F2:
            return self.page.rename()
        if k == Qt.Key_Delete:
            return self.page.delete()
        super().keyPressEvent(e)

    def focusNextPrevChild(self, nxt):
        return False                                 # Tab and Shift+Tab move levels here, not the focus


class BuilderPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.sel = None
        self.volume = ""
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["s"])
        from .adaptive import FlowLayout
        top = FlowLayout(spacing=D.SPACE["s"]); v.addLayout(top)        # wraps when the window is narrow
        self.vol_tabs = QTabBar(); self.vol_tabs.setObjectName("groupbar"); self.vol_tabs.setExpanding(False)
        self.vol_tabs.setDrawBase(False)
        self.vol_tabs.currentChanged.connect(lambda i: self.pick_volume(i))
        top.addWidget(self.vol_tabs)
        top.addWidget(D.button("+ Volume", "ghost", lambda: self.add_volume(), "A new volume at the end, numbered the volumes' way"))
        self.text_btn = D.button("Edit as text / Start from", None, lambda: self.show_text(not self.text_panel.isVisible()),
                                 "The structure as text, one section per line, and Start from the RFP or a Word outline")
        top.addWidget(self.text_btn)
        self.show_items = QCheckBox("Show what is placed")
        self.show_items.setToolTip("Each section's requirements, support, captures and library items under it, in order. "
                                   "Drag them to another section, or to another place in the section.")
        self.show_items.setChecked(True); self.show_items.toggled.connect(lambda _on: self.fill_tree())
        top.addWidget(self.show_items)
        top.addWidget(D.button("Sort in document order", None, lambda: self.sort_order(),
                               "The items in every section in the order they appear in the customer documents. Each "
                               "section is sorted on its own: nothing moves to another section."))
        top.addWidget(D.button("Add elements...", None, lambda: self.add_elements(),
                               "Table of Contents, the lists, Acronyms and Abbreviations, the Appendices section and the rest, "
                               "in one tick list (Settings > Response elements)"))
        top.addWidget(D.button("Export the setup...", None, lambda: self.host.setup_page.export(), "One plain Word document per volume"))
        top.addWidget(D.button("Export changes only...", "ghost", lambda: self.host.setup_page.export_changes(),
                               "Just what changed since the last export"))
        top.addWidget(D.button("Kickoff packets...", None, lambda: self.kickoff(),                    # 3.37.0
                               "One Word file per author: their sections, the customer's words, how each is scored, "
                               "objectives, themes, topics, answers, pages and dates"))
        top.addWidget(D.button("Make templates", "primary", lambda: self.host.prodstd_page.make_templates("effort"),
                               "For each volume: its template from Production Standards, and the setup written on it"))
        # the toolbar: what the selected item is, like Word's style buttons
        bar = QFrame(); bar.setObjectName("navband"); bl = FlowLayout(spacing=D.SPACE["xs"]); bar.setLayout(bl)
        bl.setContentsMargins(D.SPACE["s"], D.SPACE["xs"], D.SPACE["s"], D.SPACE["xs"])
        bl.addWidget(D.label("Make the selected item", "label", wrap=False))
        self.tools = {}

        def tb(key, text, tip, fn, shortcut=None):
            b = D.button(text, None, fn, tip + (f" ({shortcut})" if shortcut else ""))
            b.setCheckable(key.startswith(("H", "kind:", "brk")))
            self.tools[key] = b
            bl.addWidget(b)
            return b
        for n in (1, 2, 3):
            tb(f"H{n}", f"Heading {n}", f"Make it Heading {n}: numbered, level {n}", lambda _=False, n=n: self.make_level(n), f"Ctrl+{n}")
        deep = tb("H4+", "Heading 4-9...", "Make it Heading 4 to 9, or deeper", None)
        deep.setCheckable(True)
        dm = QMenu(deep)
        for n in range(4, 13):
            dm.addAction(f"Heading {n}" + ("  (Stationkeeper numbers it; not in Word's TOC)" if n > 9 else ""),
                         lambda n=n: self.make_level(n))
        deep.setMenu(dm)
        bl.addWidget(self._sep())
        tb("kind:unnumbered", "Unnumbered", "A heading with no number (in the TOC)", lambda: self.make_kind("unnumbered"))
        tb("kind:divider", "Divider page", "A page with its title only (a tab, the Appendices divider)", lambda: self.make_kind("divider"))
        tb("kind:placeholder", "Placeholder", "Pages for authors to fill (a resume, a past performance card)", lambda: self.make_kind("placeholder"))
        ws = tb("brk", "Word section", "Starts a new page with its own page setup: portrait or landscape", None)
        wm = QMenu(ws)
        wm.addAction("Starts a Word section, portrait", lambda: self.make_break("portrait"))
        wm.addAction("Starts a Word section, landscape", lambda: self.make_break("landscape"))
        wm.addAction("No Word section of its own", lambda: self.make_break(None))
        ws.setMenu(wm)
        bl.addWidget(self._sep())
        tb("add", "+ Below", "A new section after it, at its level", lambda: self.add_below(), "Enter")
        tb("sub", "+ Under", "A new section under it, one level down", lambda: self.add_under())
        tb("in", "Level down", "One level down, under the section above", lambda: self.level_down(), "Tab")
        tb("out", "Level up", "One level up", lambda: self.level_up(), "Shift+Tab")
        tb("up", "Up", "Earlier, past the section before it", lambda: self.move(-1))
        tb("down", "Down", "Later, past the section after it", lambda: self.move(1))
        bl.addWidget(self._sep())
        tb("rename", "Rename", "Rename it", lambda: self.rename(), "F2")
        tb("delete", "Delete", "Take it out; its sentences go to the section above", lambda: self.delete(), "Delete")
        v.addWidget(bar)
        for n in (1, 2, 3):
            sc = QShortcut(QKeySequence(f"Ctrl+{n}"), self); sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(lambda n=n: self.make_level(n))
        # the text and Start from (the Structure tab before 3.30.0), hidden until asked for
        self.text_panel = StructurePage(host)
        self.text_panel.setVisible(False)
        v.addWidget(self.text_panel, 1)
        split = QSplitter(Qt.Horizontal)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        self.btree = BuilderTree(self)
        self.btree.itemSelectionChanged.connect(self.on_pick)
        self.btree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btree.customContextMenuRequested.connect(
            lambda pos: (lambda i: self.menu(i.data(0, Qt.UserRole)).exec(self.btree.viewport().mapToGlobal(pos))
                         if i is not None and i.data(0, Qt.UserRole) else None)(self.btree.itemAt(pos)))
        lv.addWidget(self.btree, 1)
        self.sum = D.label("", "muted"); lv.addWidget(self.sum)
        split.addWidget(left)
        mid = QScrollArea(); mid.setWidgetResizable(True); mid.setFrameShape(QFrame.NoFrame)
        self.mid = QWidget(); self.mv = QVBoxLayout(self.mid); self.mv.setAlignment(Qt.AlignTop)
        mid.setWidget(self.mid)
        from PySide6.QtWidgets import QTabWidget
        from .pagepreview import PagesPreview              # 3.31.0: the volume's pages as they will run
        self.mid_tabs = QTabWidget()
        self.mid_tabs.addTab(mid, "Section")
        pv = QWidget(); pvl = QVBoxLayout(pv); pvl.setContentsMargins(0, 0, 0, 0)
        self.preview_sum = D.label("", "muted"); pvl.addWidget(self.preview_sum)
        eh = QHBoxLayout(); eh.setContentsMargins(0, 0, 0, 0)            # 3.32.0: Word's own pages, on request
        import exactpreview as EP
        self.exact_btn = D.button("Exact preview in Word", "primary", lambda: self.exact_preview(),
                                  "Word lays out the volume's template and setup (a dated copy) and shows its own pages "
                                  "and the true page count. Nothing is recorded and the effort's files are not touched.")
        self.exact_btn.setEnabled(EP.available())
        if not EP.available():
            self.exact_btn.setToolTip("Word on this PC is needed for the exact preview.")
        eh.addWidget(self.exact_btn)
        self.plan_btn = D.button("Back to the plan", None, lambda: self.drop_exact())
        self.plan_btn.setVisible(False); eh.addWidget(self.plan_btn)
        eh.addStretch(1); pvl.addLayout(eh)
        self.exact = None
        self.preview = PagesPreview()
        self.preview.page_clicked.connect(lambda lab: self.select(lab))
        psc = QScrollArea(); psc.setWidgetResizable(True); psc.setFrameShape(QFrame.NoFrame); psc.setWidget(self.preview)
        psc.setStyleSheet("QScrollArea{background:#D9D6CD;}")
        pvl.addWidget(psc, 1)
        self.preview_note = D.label("", "muted"); pvl.addWidget(self.preview_note)
        self.mid_tabs.addTab(pv, "Preview")
        self.mid_tabs.currentChanged.connect(lambda _i: self.fill_preview())
        mid = self.mid_tabs
        split.addWidget(mid)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(D.label("Production library", "title"))
        self.lib_find = QLineEdit(); self.lib_find.setPlaceholderText("Find a library item")
        self.lib_find.textChanged.connect(lambda _t: self.fill_library())
        rv.addWidget(self.lib_find)
        self.lib_list = QListWidget(); rv.addWidget(self.lib_list, 2)
        self.lib_list.setDragEnabled(True); self.lib_list.setDragDropMode(QAbstractItemView.DragOnly)
        self.lib_list.itemDoubleClicked.connect(lambda _i: self.place_selected())
        self.place_btn = D.button("Place in the section", "primary", lambda: self.place_selected(),
                                  "Put the library item in the selected section, before its requirements")
        rv.addWidget(self.place_btn)
        rv.addWidget(D.label("Not placed yet", "title"))
        self.unp_list = QListWidget(); self.unp_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.unp_list.setDragEnabled(True); self.unp_list.setDragDropMode(QAbstractItemView.DragOnly)   # drag onto a section
        rv.addWidget(self.unp_list, 1)
        self.unp_btn = D.button("Into the selected section", None, lambda: self.place_unplaced(),
                                "Requirements and captures with no section yet go into the selected section")
        rv.addWidget(self.unp_btn)
        split.addWidget(right)
        for wdg, mn in ((left, 300), (mid, 260), (right, 220)):
            wdg.setMinimumWidth(mn)
        split.setSizes([480, 380, 280])
        self.split = split
        v.addWidget(split, 1)

    @staticmethod
    def _sep():
        f = QFrame(); f.setFrameShape(QFrame.VLine); f.setFixedHeight(22)
        return f

    # ------------------------------------------------------------ the text panel (tests and Start from use these)
    def __getattr__(self, name):
        if name in ("text", "apply", "apply_btn", "state", "letter", "doc", "from_rfp_outline", "from_word",
                    "set_text", "why", "tree") and "text_panel" in self.__dict__:
            return getattr(self.__dict__["text_panel"], name)
        raise AttributeError(name)

    def show_text(self, on=True):
        self.text_panel.setVisible(on)
        self.split.setVisible(not on)
        self.text_btn.setText("Back to the builder" if on else "Edit as text / Start from")
        if on:
            self.text_panel.refresh()
        else:
            self.refresh()

    def offer_start(self):
        self.show_text(True)
        return self.text_panel.offer_start()

    def from_prescribed(self):
        self.show_text(True)
        return self.text_panel.from_prescribed()

    def from_headings(self):
        self.show_text(True)
        return self.text_panel.from_headings()

    def blank(self):
        self.show_text(True)
        return self.text_panel.blank()

    # ------------------------------------------------------------ the structure
    @property
    def M(self):
        R = self.host.review
        return R.M if R is not None else None

    def refresh(self):
        R = self.host.review
        self.setEnabled(R is not None)
        self.text_panel.refresh()                    # the text stays the structure's, shown or not
        if R is None:
            self.btree.clear()
            self.sel = None                          # 3.34.1: nothing of the effort open before
            self.vol_tabs.blockSignals(True)
            while self.vol_tabs.count():
                self.vol_tabs.removeTab(0)
            self.vol_tabs.blockSignals(False)
            self.fill_unplaced()
            self.show_section()
            return
        self.fill_volumes()
        self.fill_tree()
        self.fill_library()
        self.fill_unplaced()
        self.show_section()

    def fill_volumes(self):
        hs = O.volume_heads(self.M)
        heads = [l for l in O.labels(self.M) if l in hs]          # in the structure's order
        self.vol_tabs.blockSignals(True)
        while self.vol_tabs.count():
            self.vol_tabs.removeTab(0)
        self._vols = ([""] if len(heads) != 1 else []) + list(heads)
        for h in self._vols:
            self.vol_tabs.addTab(h or ("Every volume" if heads else "The response"))
        if self.volume not in self._vols:
            self.volume = self._vols[0] if self._vols else ""
        self.vol_tabs.setCurrentIndex(self._vols.index(self.volume) if self.volume in self._vols else 0)
        self.vol_tabs.blockSignals(False)

    def pick_volume(self, i):
        if 0 <= i < len(getattr(self, "_vols", [])):
            self.volume = self._vols[i]
            self.fill_tree()

    def _counts(self):
        R = self.host.review
        caps = {}
        try:
            import effortrec as RR
            import excerpts as EX
            caps = EX.section_counts(RR.Record(self.host.ws.root)) if self.host.ws is not None else {}
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return R.counts(), caps

    def fill_tree(self):
        M = self.M
        self.btree.blockSignals(True)                # clearing must not pick the old item again
        self.btree.clear()
        self.btree.blockSignals(False)
        if M is None:
            return
        import pagebudget as PB
        reqs, caps = self._counts()
        show = set(O.in_volume(M, self.volume))
        heads = O.volume_heads(M)
        stack, last_part, part_node, keep = [], {}, None, None
        vos = SD.volume_of_sections(M)
        parted = {vos.get(C.outline_label(o), "") for o in M.outline if SP.part_of(o) != "body"}   # volumes with parts
        for o in M.outline:
            lab = C.outline_label(o)
            if lab not in show:
                continue
            lvl = o.get("level", 1)
            par = next((x for x in reversed(stack) if x[0] < lvl), None)
            top = lab not in heads and (par is None or par[1].data(0, Qt.UserRole) in heads)
            hl = O.heading_level(M, lab)
            node = QTreeWidgetItem([lab, "VOL" if lab in heads else RE.tag(o, hl), str(reqs.get(lab, "") or ""),
                                    str(caps.get(lab, "") or ""), PB.tag(M, lab)])
            node.setData(0, Qt.UserRole, lab)
            part = SP.part_of(o)
            node.setForeground(1, QColor(PART_COLOR.get(part, "#2E7D5B")))
            f = node.font(1); f.setBold(True); node.setFont(1, f)
            node.setToolTip(1, self._tag_tip(o, hl, lab in heads))
            if o.get("lib"):
                node.setToolTip(0, "Library items: " + ", ".join(x["name"] for x in o["lib"]))
            if lab in heads:
                f0 = node.font(0); f0.setBold(True); node.setFont(0, f0)
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            if top and (par[1].data(0, Qt.UserRole) if par else "") in parted:
                vol_node = par[1] if par else None
                key = (id(vol_node), part)
                if last_part.get(id(vol_node)) != part:
                    part_node = QTreeWidgetItem([SP.PART_NAME[part].upper(), "", "", "", ""])
                    part_node.setData(0, Qt.UserRole, None)
                    part_node.setForeground(0, QColor(PART_COLOR.get(part, "#2E7D5B")))
                    fp = part_node.font(0); fp.setBold(True); part_node.setFont(0, fp)
                    part_node.setFlags(part_node.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)
                    (vol_node.addChild(part_node) if vol_node else self.btree.addTopLevelItem(part_node))
                    part_node.setExpanded(True)
                    last_part[id(vol_node)] = part
                part_node.addChild(node)
            else:
                (stack[-1][1].addChild(node) if stack else self.btree.addTopLevelItem(node))
            stack.append((lvl, node))
            if lab == self.sel:
                keep = node
            if self.show_items.isChecked():
                self._add_contents(node, lab)
        self.btree.expandAll()
        if keep is not None:
            self.btree.blockSignals(True); self.btree.setCurrentItem(keep); self.btree.blockSignals(False)
        n = len([o for o in M.outline if C.outline_label(o) in show])
        self.sum.setText(f"{n} item(s) in {self.volume or 'the structure'}. Drag a section onto another to move it; "
                         "Enter adds one below, Tab and Shift+Tab change its level.")
        self.sync_tools()
        self.fill_preview()

    CON_TAG = {"lib": "LIB", "cap": "CAP"}

    def _add_contents(self, node, lab):
        """The section's items as rows under it, before its subsections: drag them to move them."""
        for kind, key, text in self.contents(lab):
            sub = ""
            if kind == "item":
                it = SD.by_id(self.M).get(key) or {}
                sub = {"Context": "SUP", "Customer": "CUST"}.get(it.get("decision"), it.get("lm") or "REQ")
            shown = text.split("  ", 1)[-1] if kind == "item" else text      # the Kind column says what it is
            row = QTreeWidgetItem([shown, sub or self.CON_TAG.get(kind, ""), "", "", ""])
            row.setData(0, Qt.UserRole, None)
            row.setData(0, Qt.UserRole + 1, (kind, key, lab))
            f = row.font(0); f.setItalic(True); row.setFont(0, f)
            row.setForeground(0, QColor({"lib": "#2F5D8A", "cap": "#0E7490"}.get(kind, "#5D6672")))
            row.setForeground(1, QColor({"lib": "#2F5D8A", "cap": "#0E7490"}.get(kind, "#7030A0")))
            row.setToolTip(0, text)
            node.insertChild(node.childCount(), row)

    def _preview_volume(self):
        heads = [l for l in O.labels(self.M) if l in O.volume_heads(self.M)]
        if self.volume in heads:
            return self.volume
        if self.sel:
            v = self.sel if self.sel in heads else SD.volume_of_sections(self.M).get(self.sel, "")
            if v:
                return v
        return heads[0] if heads else ""

    def preview_pages(self, volume=None):
        """3.31.0: the pages of a volume as pageplan works them out, with the volume's standard and the effort's values."""
        import pageplan as PP
        import setuptemplate as ST
        M = self.M
        vol = self._preview_volume() if volume is None else volume
        std, extras = {}, {}
        try:
            info = self.host.efforts.get(self.host.effort_name) or {}
            extras = ST.element_extras(self.host.config_dir, info, self.host.ws.root if self.host.ws is not None else None)
            for p in ST.plan(M, self.host.config_dir, self.host.ws, self.host.effort_name or "", info):
                if p["volume"] == vol or not vol:
                    std = p["std"]
                    break
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return PP.plan(M, vol, std, extras)

    def fill_preview(self):
        """The Preview tab, drawn again when it is showing (the structure changed, or the tab was opened)."""
        if not hasattr(self, "mid_tabs") or self.mid_tabs.currentIndex() != 1 or self.M is None:
            return
        import pageplan as PP
        pages = self.preview_pages()
        by, n = PP.summary(pages)
        stale = ""
        ex = getattr(self, "exact", None)
        if ex is not None and (ex["sig"] != self._sig() or ex["volume"] != (self._preview_volume() or "")):
            self.exact = ex = None                       # the structure changed since: Word's pages are out of date
            stale = "  ·  The exact preview was from before a change: run it again."
        self.plan_btn.setVisible(ex is not None)
        self.preview_note.setText("Word's own pages, laid out from a dated copy of the volume's template and setup. A change to "
                                  "the structure goes back to the plan." if ex is not None else
                                  "Drawn by Stationkeeper from the structure, the page budget and Production Standards: close to "
                                  "Word's layout. Exact preview in Word gives Word's own pages.")
        if ex is not None:
            self.preview.set_pages(ex["pages"], self.sel or "")
            self.preview_sum.setText(f"{self._preview_volume() or 'The response'}: {ex['count']} page(s) in Word (the plan: {n})  ·  "
                                     f"laid out by Word {ex['when']}")
            return
        self.preview.set_pages(pages, self.sel or "")
        self.preview_sum.setText(f"{self._preview_volume() or 'The response'}: {n} page(s) planned  ·  "
                                 + "  ·  ".join(f"{SP.PART_NAME.get(k, k)} {v}" for k, v in by.items()) + stale)

    def _sig(self):
        """What the exact preview depends on: the structure and the page budget."""
        import hashlib, json
        try:
            return hashlib.sha1(json.dumps([self.M.outline, SD.setup_of(self.M).get("budget"), SD.setup_of(self.M).get("prepaginate")],
                                           sort_keys=True, default=str).encode("utf-8")).hexdigest()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return ""

    def drop_exact(self):
        self.exact = None
        self.fill_preview()

    def exact_preview(self, runner=None, wait=False):
        """3.32.0: Word lays out the volume (a dated copy of its template and setup); its pages show here with the true
        page count. Runs off the window's thread; runner and wait (tests) run it at once."""
        import exactpreview as EP
        M = self.M
        if M is None or self.host.ws is None or not M.outline:
            self.host.status("Open an effort with a response structure first.")
            return None
        if runner is None and not EP.available():
            self.host.status("Word on this PC is needed for the exact preview.")
            return None
        vol = self._preview_volume() or ""
        base = self.host.out_path("setup_documents") if self.host.effort_path else os.path.dirname(M.path)
        base = base if os.path.isdir(base) else os.path.dirname(base)
        folder = os.path.join(base, "Exact preview")
        info = self.host.efforts.get(self.host.effort_name) or {}
        try:
            import ctxdocs as CX
            ctx = CX.section_context(self.host.ws.root)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            ctx = None
        sig = self._sig()
        cfg, ws, name = self.host.config_dir, self.host.ws, self.host.effort_name or ""

        def job(progress=lambda *a: None, stop=lambda: False):
            return EP.run(M, vol, folder, cfg, ws, name, info, context=ctx, runner=runner, progress=progress)

        def done(res):
            self.exact_btn.setEnabled(EP.available() or runner is not None)
            if isinstance(res, Exception) or not (res or {}).get("ok"):
                why = str(res) if isinstance(res, Exception) else (res or {}).get("why", "")
                self.host.status("No exact preview: " + (why or "Word could not lay it out."))
                return None
            labels = O.labels(M)
            try:
                from .pagepreview import exact_pages
                pages = exact_pages(res["pdf"], EP.section_of_pages(res["heads"], labels, max(res["pages"], 1)))
            except Exception:  # noqa: BLE001
                diag.swallowed()
                self.host.status("No exact preview: the PDF Word saved could not be read.")
                return None
            self.exact = {"pages": pages, "count": res["pages"] or len(pages), "when": res["when"], "sig": sig,
                          "volume": vol, "pdf": res["pdf"], "docx": res["docx"]}
            diag.activity("exact_preview", pages=len(pages))
            if self.mid_tabs.currentIndex() != 1:
                self.mid_tabs.setCurrentIndex(1)
            self.fill_preview()
            self.host.toast(f"Exact preview: {self.exact['count']} page(s) in Word. The copy is in {folder}.")
            return self.exact

        self.exact_btn.setEnabled(False)
        self.host.status("Word is laying out the volume for the exact preview...")
        if wait:
            try:
                res = job()
            except Exception as ex:  # noqa: BLE001
                diag.swallowed()
                res = ex
            return done(res)
        from .progress import JobWorker
        self._exact_worker = JobWorker(job)
        self._exact_worker.done.connect(done)
        self._exact_worker.start()
        return True

    def _tag_tip(self, o, hl, is_vol):
        if is_vol:
            return "A volume"
        k = o.get("kind") or ""
        what = {"unnumbered": "An unnumbered heading", "divider": "A divider page", "placeholder": "A placeholder",
                "element": "An element: " + (o.get("element") or "")}.get(k, f"Heading {hl}" + (" (Word numbers and lists "
                                                                                                   "Heading 1 to 9; deeper levels are numbered by Stationkeeper)" if hl > 9 else ""))
        brk = o.get("brk")
        return what + (f"; starts a Word section, {brk.get('orient', 'portrait')}" if brk else "")

    def on_pick(self):
        it = self.btree.currentItem()
        lab = it.data(0, Qt.UserRole) if it is not None else None
        con = it.data(0, Qt.UserRole + 1) if it is not None else None
        if con and not lab:
            lab = con[2]                                # an item row: its section
        if lab:
            self.sel = lab
        self.sync_tools()
        self.show_section()
        if hasattr(self, "preview") and self.preview.pages:
            self.preview.set_pages(self.preview.pages, self.sel or "")

    def select(self, lab):
        self.sel = lab
        self.fill_tree()
        self.show_section()
        if hasattr(self, "preview"):
            self.preview.set_pages(self.preview.pages, lab)

    def sync_tools(self):
        M, lab = self.M, self.sel
        o = M.outline[O.index_of(M, lab)] if (M is not None and lab and O.index_of(M, lab) >= 0) else None
        hl = O.heading_level(M, lab) if o is not None else 0
        k = (o or {}).get("kind") or ""
        for key, b in self.tools.items():
            b.setEnabled(o is not None or key in ("add",))
            if b.isCheckable():
                on = (key == f"H{hl}" and not k) or (key == "H4+" and hl >= 4 and not k) or key == f"kind:{k}" \
                    or (key == "brk" and bool((o or {}).get("brk")))
                b.blockSignals(True); b.setChecked(bool(on)); b.blockSignals(False)

    # ------------------------------------------------------------ changes
    def _change(self, what, fn):
        """One Undo step for a change to the structure; Review's structure follows."""
        R = self.host.review
        if R is None:
            return None
        R.snap(what)
        new = fn()
        if new is None:
            if R.undo:
                R.undo.pop()
            return None
        if isinstance(new, str):
            self.sel = new
        self.host.changed()
        try:
            self.host.assign_page.fill_tree()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.fill_tree()
        self.fill_unplaced()
        self.show_section()
        return new

    def _need(self):
        if not self.sel or self.M is None or O.index_of(self.M, self.sel) < 0:
            self.host.status("Click a section in the structure first.")
            return False
        return True

    def make_level(self, n):
        if not self._need():
            return None
        lab = self.sel
        o = self.M.outline[O.index_of(self.M, lab)]

        def go():
            new = lab
            if o.get("kind"):
                new = O.set_kind(self.M, new, "")
            return O.set_level(self.M, new, n)
        return self._change(f"Heading {n}: {lab}", go)

    def make_kind(self, kind):
        if not self._need():
            return None
        o = self.M.outline[O.index_of(self.M, self.sel)]
        kind = "" if (o.get("kind") or "") == kind else kind          # a second click takes it off, like Bold
        return self._change(f"{dict(O.KINDS)[kind].lower()}: {self.sel}", lambda: O.set_kind(self.M, self.sel, kind))

    def make_break(self, orient):
        if not self._need():
            return None
        return self._change(f"Word section: {self.sel}", lambda: O.set_break(self.M, self.sel, orient))

    def _ask(self, title, label, text=""):
        if hasattr(self, "answer"):                    # tests
            a = self.answer
            return a.pop(0) if isinstance(a, list) else a
        t, ok = QInputDialog.getText(self, title, label, text=text)
        return t.strip() if ok and t.strip() else None

    def add_below(self, title=None):
        M = self.M
        if M is None:
            return None
        title = title if title is not None else self._ask("New section", "Title:")
        if not title:
            return None
        if self.sel and O.index_of(M, self.sel) >= 0 and self.sel not in O.volume_heads(M):
            return self._change(f"add section {title}", lambda: O.add(M, title, after=self.sel))
        parent = self.sel if self.sel in O.volume_heads(M) else (self.volume or None)
        return self._change(f"add section {title}", lambda: O.add(M, title, parent=parent))

    def add_under(self, title=None):
        if not self._need():
            return None
        title = title if title is not None else self._ask("New subsection", f"Title (under {self.sel}):")
        if not title:
            return None
        return self._change(f"add section {title}", lambda: O.add(self.M, title, parent=self.sel))

    def level_down(self):
        if not self._need():
            return None
        return self._change(f"level down: {self.sel}", lambda: O.indent(self.M, self.sel))

    def level_up(self):
        if not self._need():
            return None
        return self._change(f"level up: {self.sel}", lambda: O.outdent(self.M, self.sel))

    def move(self, delta):
        if not self._need():
            return None
        return self._change(f"move: {self.sel}", lambda: O.move(self.M, self.sel, delta))

    def drop(self, label, target, where):
        return self._change(f"move {label}", lambda: O.move_to(self.M, label, target, where))

    def rename(self, label=None, title=None):
        label = label or self.sel
        if not label or self.M is None:
            return None
        self.sel = label
        o = self.M.outline[O.index_of(self.M, label)]
        title = title if title is not None else self._ask("Rename", f"New title for {label}:", o.get("title", ""))
        if not title:
            return None
        return self.host.assign_page.rename_section(label, title) and self._after_assign(label)

    def _after_assign(self, label):
        self.sel = self.host.assign_page.target or label
        self.refresh()
        return self.sel

    def delete(self, label=None):
        label = label or self.sel
        if not label or self.M is None:
            return None
        to = self.host.assign_page.delete_section(label)
        self.sel = to or None
        self.refresh()
        return to

    def add_volume(self, title=None):
        title = title if title is not None else self._ask("New volume", "Volume title (the number is added):")
        if not title:
            return None
        lab = self._change(f"add volume {title}", lambda: O.add_volume(self.M, title))
        if lab:
            self.volume = lab
            self.refresh()
        return lab

    def menu(self, label):
        m = QMenu(self)
        if not label or self.M is None:
            return m
        self.select(label)
        m.addAction("Rename... (F2)", lambda: self.rename(label))
        lv = m.addMenu("Make it")
        for n in range(1, 10):
            lv.addAction(f"Heading {n}", lambda n=n: self.make_level(n))
        lv.addSeparator()
        for k, t in O.KINDS[1:4]:
            lv.addAction(t, lambda k=k: self.make_kind(k))
        m.addAction("Pages...", lambda: self.host.assign_page.section_pages(label) and self.refresh())
        m.addAction("Sort this section in document order", lambda: self.sort_order([label]))
        m.addSeparator()
        m.addAction("+ Below (Enter)", lambda: self.add_below())
        m.addAction("+ Under", lambda: self.add_under())
        m.addAction("Level down (Tab)", lambda: self.level_down())
        m.addAction("Level up (Shift+Tab)", lambda: self.level_up())
        m.addAction("Up", lambda: self.move(-1))
        m.addAction("Down", lambda: self.move(1))
        pm = m.addMenu("Move to a part")
        for k, t in SP.PARTS:
            pm.addAction(t, lambda k=k: self._change(f"to {k}: {label}", lambda: O.set_part(self.M, label, k)))
        m.addSeparator()
        m.addAction("Delete (Del)", lambda: self.delete(label))
        return m

    # ------------------------------------------------------------ the section: what it is and what is in it
    def _clear_mid(self):
        while self.mv.count():
            w = self.mv.takeAt(0).widget()
            if w is not None:
                w.setParent(None); w.deleteLater()

    def contents(self, label=None):
        """[(kind, id, text)] in the order the setup prints them: library items before, the requirements and support,
        library items after, then the captures placed here."""
        label = label or self.sel
        M = self.M
        if M is None or not label:
            return []
        out = []
        lib = O.lib_items(M, label)
        out += [("lib", n, f"{x['name']} ({x.get('kind', '')})") for n, x in enumerate(lib) if x.get("where") != "after"]
        P = SD.placed_in(M)
        B = SD.by_id(M)
        inh = SD.inherited_sections(M)
        for i in P.get(label, []):
            it = B.get(i)
            if it is not None:
                ref = SD.ref_of(M, it, inh)[0] or i
                out.append(("item", i, f"{SD.kind_of(it)}  {ref}: {it.get('text', '')[:140]}"))
        out += [("lib", n, f"{x['name']} ({x.get('kind', '')})") for n, x in enumerate(lib) if x.get("where") == "after"]
        try:
            import effortrec as RR
            import excerpts as EX
            rec = RR.Record(self.host.ws.root)
            names = {b["id"]: b["name"] for b in EX.bins(rec, self.host.config_dir)}
            di = SD.doc_index(M)
            xs = sorted(EX.in_section(rec, label), key=lambda x: min([di.get(p.get("sid"), (99, 10 ** 9)) for p in x.get("parts", [])]
                                                                        or [(99, 10 ** 9)]))
            out += [("cap", x["id"], f"{names.get(x['bin'], x['bin'])}: {EX.text_of(x)[:140]}") for x in xs]
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return out

    def show_section(self):
        self._clear_mid()
        M, lab = self.M, self.sel
        if M is None or not lab or O.index_of(M, lab) < 0:
            self.mv.addWidget(D.EmptyState("Pick a section", "Click a section in the structure to see what it is and "
                                           "everything in it. Add elements puts the TOC, the lists and the rest in."))
            return
        import pagebudget as PB
        o = M.outline[O.index_of(M, lab)]
        hl = O.heading_level(M, lab)
        self.mv.addWidget(D.label(lab, "title"))
        self.mv.addWidget(D.label(self._tag_tip(o, hl, lab in O.volume_heads(M)) + f"  ·  {SP.PART_NAME[SP.part_of(o)]}", "muted"))
        pages = PB.tag(M, lab)
        row = QHBoxLayout()
        row.addWidget(D.label(f"Pages: {pages or 'not set'}", None))
        row.addWidget(D.button("Pages...", "ghost", lambda: self.host.assign_page.section_pages(lab) and self.refresh()))
        cnt = SP.counted(M, lab)
        cb = QCheckBox("Counts toward the page limit"); cb.setChecked(cnt)
        cb.toggled.connect(lambda on: self._change(f"counts: {lab}", lambda: (SP.set_item_count(M, lab, on), lab)[1]))
        row.addWidget(cb); row.addStretch(1)
        w = QWidget(); w.setLayout(row); self.mv.addWidget(w)
        self.mv.addWidget(D.label("In this section, in order", "label"))
        self.cont = QListWidget(); self.cont.setMinimumHeight(160)
        for kind, key, text in self.contents(lab):
            it = QListWidgetItem({"lib": "Library   ", "item": "", "cap": "Capture   "}[kind] + text)
            it.setData(Qt.UserRole, (kind, key))
            if kind == "lib":
                it.setForeground(QColor("#2F5D8A"))
            elif kind == "cap":
                it.setForeground(QColor("#0E7490"))
            self.cont.addItem(it)
        self.mv.addWidget(self.cont)
        r2 = QHBoxLayout()
        r2.addWidget(D.button("Up", None, lambda: self.move_content(-1), "Earlier in the section"))
        r2.addWidget(D.button("Down", None, lambda: self.move_content(1), "Later in the section"))
        r2.addWidget(D.button("Take out of this section", "danger", lambda: self.take_out()))
        r2.addStretch(1)
        w2 = QWidget(); w2.setLayout(r2); self.mv.addWidget(w2)
        if not self.cont.count():
            self.mv.addWidget(D.label("Nothing in it yet: decide sentences into it in Review, or place library items and "
                                      "what is not placed yet from the right.", "muted"))
        self.show_everything(lab)                     # 3.37.0

    def kickoff(self, run=True, folder=None):
        """3.37.0: the author kickoff packets."""
        from .kickoffview import open_dialog
        return open_dialog(self.host, run, folder)

    def show_everything(self, lab):
        """3.37.0 Everything for this section: who, pages, the customer's words, how it is scored, objectives, hot
        buttons, key points, themes, topics, answers and the storyboard, with a filter. The same facts as the packet."""
        import html
        import kickoff as KO
        from .kickoffview import record_of
        card = D.Card("Everything for this section", "What an author of this section needs, from every page of the effort.")
        self.ev_filter = QLineEdit(); self.ev_filter.setPlaceholderText("Filter (words in any line)"); self.ev_filter.setClearButtonEnabled(True)
        card.add(self.ev_filter)
        self.ev_text = QLabel(""); self.ev_text.setTextFormat(Qt.RichText); self.ev_text.setWordWrap(True)
        self.ev_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card.add(self.ev_text)
        try:
            self.ev_groups = KO.panel_groups(KO.section_pack(record_of(self.host), self.M, lab))
        except Exception:  # noqa: BLE001
            diag.swallowed()
            self.ev_groups = []
        t = D.tokens()

        def draw():
            q = self.ev_filter.text().strip().casefold()
            parts = []
            for g, lines in self.ev_groups:
                keep = [x for x in lines if not q or q in x.casefold() or q in g.casefold()]
                if keep:
                    parts.append(f"<div style='margin-top:6px'><b>{html.escape(g)}</b></div>"
                                 + "".join(f"<div style='margin-left:10px;color:{t['text']}'>{html.escape(x)}</div>" for x in keep))
            self.ev_text.setText("".join(parts) or f"<span style='color:{t['muted']}'>Nothing matches.</span>")
        self.ev_filter.textChanged.connect(lambda _t: draw())
        draw()
        self.mv.addWidget(card)

    def _content_sel(self):
        it = self.cont.currentItem() if hasattr(self, "cont") else None
        return it.data(Qt.UserRole) if it is not None else None

    def move_content(self, delta, sel=None):
        s = sel or self._content_sel()
        if not s or not self.sel:
            return False
        kind, key = s
        lab = self.sel
        if kind == "item":
            r = self._change("move in the setup", lambda: (SD.move(self.M, key, lab, delta), lab)[1])
        elif kind == "lib":
            r = self._change("move a library item", lambda: lab if O.move_lib(self.M, lab, key, delta) else None)
        else:
            return False
        rows = [self.cont.item(i).data(Qt.UserRole) for i in range(self.cont.count())]
        want = (kind, key + delta) if kind == "lib" else s
        if want in rows:
            self.cont.setCurrentRow(rows.index(want))
        return bool(r)

    def take_out(self, sel=None):
        s = sel or self._content_sel()
        if not s or not self.sel:
            return False
        kind, key = s
        lab = self.sel
        if kind == "item":
            r = self._change("take out of the section", lambda: (SD.unplace(self.M, key, lab), lab)[1])
        elif kind == "lib":
            r = self._change("take a library item out", lambda: lab if O.unplace_lib(self.M, lab, key) else None)
        else:
            r = self.host.assign_page.place_captures([key], lab, on=False)
            self.refresh()
        return bool(r)

    # ------------------------------------------------------------ the library and what is not placed
    SHELVES = ("quickpart", "table_look", "table_style", "cover", "backer", "hf_design", "part")

    def fill_library(self):
        import templatelib as TL
        self.lib_list.clear()
        try:
            lib = TL.Library(self.host.config_dir)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return
        q = self.lib_find.text().strip().casefold()
        for kind in self.SHELVES:
            items = [i for i in lib.items if i["kind"] == kind and (not q or q in i["name"].casefold())]
            if not items:
                continue
            h = QListWidgetItem(TL.SHELF.get(kind, kind).upper()); h.setFlags(Qt.NoItemFlags)
            h.setForeground(D.color("muted")); self.lib_list.addItem(h)
            for i in sorted(items, key=lambda x: x["name"].casefold()):
                it = QListWidgetItem("  " + i["name"]); it.setData(Qt.UserRole, {"id": i["id"], "kind": kind, "name": i["name"]})
                it.setToolTip(i.get("summary", "") or i["name"])
                self.lib_list.addItem(it)
        if not self.lib_list.count():
            self.lib_list.addItem(QListWidgetItem("The library is empty: collect Quick Parts, covers and table looks in "
                                                  "Production Standards > Import from a file."))

    def place_selected(self, item=None, where="before"):
        it = self.lib_list.currentItem()
        item = item or (it.data(Qt.UserRole) if it is not None else None)
        if not item or not self._need():
            return None
        lab = self.sel
        return self._change(f"place {item['name']}", lambda: lab if O.place_lib(self.M, lab, item, where) is not None else None)

    def fill_unplaced(self):
        self.unp_list.clear()
        M = self.M
        if M is None:
            return
        B = SD.by_id(M)
        for i in SD.export_check(M)["unplaced"]:
            it = B.get(i)
            if it is not None and it.get("decision") == "Keep":
                w = QListWidgetItem(f"Requirement  {i}: {it.get('text', '')[:90]}"); w.setData(Qt.UserRole, ("item", i))
                self.unp_list.addItem(w)
        try:
            import effortrec as RR
            import excerpts as EX
            rec = RR.Record(self.host.ws.root)
            names = {b["id"]: b["name"] for b in EX.bins(rec, self.host.config_dir)}
            for x in EX.excerpts(rec):
                if not x.get("sections"):
                    w = QListWidgetItem(f"{names.get(x['bin'], x['bin'])}: {EX.text_of(x)[:90]}"); w.setData(Qt.UserRole, ("cap", x["id"]))
                    self.unp_list.addItem(w)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        if not self.unp_list.count():
            self.unp_list.addItem(QListWidgetItem("Everything is placed."))

    def place_unplaced(self, picks=None):
        if not self._need():
            return 0
        picks = picks if picks is not None else [i.data(Qt.UserRole) for i in self.unp_list.selectedItems() if i.data(Qt.UserRole)]
        lab = self.sel
        reqs = [k for t, k in picks if t == "item"]
        caps = [k for t, k in picks if t == "cap"]
        n = 0
        R = self.host.review
        if reqs:
            rows = [R.item(i) for i in reqs if R.item(i) is not None]
            n += R.req(rows, lab) or 0
            self.host.changed()
            self.host.assign_page.fill_tree()
        if caps:
            n += self.host.assign_page.place_captures(caps, lab) or 0
        self.refresh()
        return n

    # ------------------------------------------------------------ drag and drop of items, and sorting
    def drop_content(self, con, tlab, tcon, where="into"):
        """A placed item dragged onto a section (to its end) or onto an item (before it, or after it when dropped below)."""
        kind, key, frm = con
        to = tlab or (tcon[2] if tcon else None)
        if not to:
            return None
        before = None
        if tcon and tcon[0] == "item" and kind == "item":
            ids = SD.placed_in(self.M).get(to, [])
            if where == "after" and tcon[1] in ids:
                k = ids.index(tcon[1]) + 1
                before = ids[k] if k < len(ids) else None
            else:
                before = tcon[1]
            if before == key:
                return None
        if kind == "item":
            return self._change(f"move {key} to {to}", lambda: to if SD.move_to_section(self.M, key, to, frm, before) else None)
        if kind == "cap":
            if to == frm:
                return None
            n = self.host.assign_page.place_captures([key], to)
            if n and frm:
                self.host.assign_page.place_captures([key], frm, on=False)
            self.refresh()
            return n
        if kind == "lib" and to != frm:
            x = O.lib_items(self.M, frm)[key] if 0 <= key < len(O.lib_items(self.M, frm)) else None
            if x is None:
                return None
            return self._change(f"move {x['name']} to {to}", lambda: to if (O.unplace_lib(self.M, frm, key)
                                                                         and O.place_lib(self.M, to, x, x.get("where", "before")) is not None) else None)
        return None

    def drop_unplaced(self, picks, tlab, tcon):
        to = tlab or (tcon[2] if tcon else None)
        if not to or not picks:
            return 0
        before = tcon[1] if (tcon and tcon[0] == "item") else None
        reqs = [k for t, k in picks if t == "item"]
        caps = [k for t, k in picks if t == "cap"]
        n = 0
        if reqs:
            def go():
                for i in reqs:
                    SD.move_to_section(self.M, i, to, None, before)
                return to
            n += len(reqs) if self._change(f"{len(reqs)} item(s) into {to}", go) else 0
        if caps:
            n += self.host.assign_page.place_captures(caps, to) or 0
            self.refresh()
        diag.activity("builder_dropped", n=n)
        return n

    def drop_library(self, item, tlab, tcon):
        to = tlab or (tcon[2] if tcon else None)
        if not item or not to:
            return None
        return self._change(f"place {item['name']}", lambda: to if O.place_lib(self.M, to, item) is not None else None)

    def sort_order(self, labels=None):
        """Sort in document order: every section (or the ones given) on its own."""
        M = self.M
        if M is None:
            return 0
        res = self._change("sort in document order", lambda: True if SD.sort_doc_order(M, labels) else None)
        self.host.status("Each section's items are in the order they appear in the customer documents." if res
                         else "Every section is in document order already.")
        return bool(res)

    # ------------------------------------------------------------ elements
    def add_elements(self, ids=None):
        """The tick list: the volume's elements ticked (its kit when it has none yet); OK puts in the ticked ones and
        takes out the unticked."""
        M = self.M
        if M is None:
            return None
        data = RE.load(self.host.config_dir)
        try:                                               # 3.32.0: a Quick Part element takes its measured pages
            import templatelib as TL
            data["lib_pages_by_name"] = {i["name"].casefold(): int(i["pages"]) for i in TL.Library(self.host.config_dir).items
                                         if i.get("pages") and i["kind"] == "quickpart"}
        except Exception:  # noqa: BLE001
            diag.swallowed()
        heads = O.volume_heads(M)
        vol = self.volume if self.volume in heads else ""
        if heads and not vol and self.sel:                 # every volume shown: the selected section's volume
            vol = self.sel if self.sel in heads else SD.volume_of_sections(M).get(self.sel, "")
        if heads and not vol:
            vol = next(iter(heads)) if len(heads) == 1 else ""
        if heads and not vol:
            self.host.status("Pick a volume tab (or a section in the volume) first: elements go into one volume.")
            return None
        have = RE.in_volume(M, vol)
        if ids is None:
            d = ElementsPick(self, data, list(have) or RE.kit(data, self.host.assign_page.effort_type()), vol)
            if d.exec() != QDialog.Accepted:
                return None
            ids = d.ticked()
        res = self._change(f"elements in {vol or 'the response'}", lambda: (RE.apply_kit(M, data, ids, vol), True)[1])
        diag.activity("builder_elements", n=len(ids))
        self.refresh()
        return res


class ElementsPick(QDialog):
    """Add elements: every element by part, ticked for the volume."""

    def __init__(self, parent, data, ticked, volume):
        super().__init__(parent)
        self.setWindowTitle(f"Add elements: {volume or 'the response'}")
        self.setMinimumSize(520, 560)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Tick what this volume needs; untick to take an element out. Each goes in its part, in the "
                            "team's order (Settings > Response elements).", "muted"))
        self.list = QListWidget(); v.addWidget(self.list, 1)
        last = None
        for e in data["elements"]:
            if not e.get("shown", True):
                continue
            if e["part"] != last:
                h = QListWidgetItem(RE.PART_NAME[e["part"]].upper()); h.setFlags(Qt.NoItemFlags)
                h.setForeground(QColor(PART_COLOR.get(e["part"], "#2E7D5B"))); self.list.addItem(h)
                last = e["part"]
            it = QListWidgetItem(f"  {e['name']}   ({RE.SOURCE_NAME[e['source']].split(' (')[0]}, {e['pages']} page"
                                 f"{'s' if e['pages'] != 1 else ''}{', counts' if e['counts'] else ''})")
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if e["id"] in ticked else Qt.Unchecked)
            it.setData(Qt.UserRole, e["id"])
            self.list.addItem(it)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Put them in")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def ticked(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())
                if self.list.item(i).data(Qt.UserRole) and self.list.item(i).checkState() == Qt.Checked]
