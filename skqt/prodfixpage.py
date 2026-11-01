"""Production > Fix a Copy (3.6.0): check a Word draft against the production standard, choose every fix, then
Stationkeeper makes a dated copy in the output folder and fixes the copy. The original is never changed: it is read
once, and a file someone has open is not copied at all.

The page: the output folder and the standard in force; the drafts (Volumes folder, or Add a file...); Check; the
fixes grouped by area, each switched on or off, with what it found; tables with every row's role, the questions
grouped so one answer covers every row like it, and keys to set roles (C H 2 S B U T N K); lists that need a
restart decision; broken cross-references to point at a target; Update fields in Word; Make the fixed copy; then
the result: found before and left after by area, every fix that ran or was refused, and proof the original is
unchanged."""
import copy, os, sys, time
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget, QFrame)
import bgwork, diag
import prodcopy as PCY
import prodfix as PF
import prodrules as PRL
from . import design as D

ROLE_KEYS = {"C": "caption", "H": "header", "2": "header2", "S": "subhead", "B": "body", "U": "subtotal", "T": "total",
             "N": "note", "K": "keep"}
ROLE_TEXT = {"caption": "Caption", "header": "Header", "header2": "Header 2", "subhead": "Subhead", "body": "Body",
             "subtotal": "Subtotal", "total": "Total", "note": "Notes", "keep": "Keep as is"}


class FixPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.chk = None
        self.plan = None
        self.job = None
        self.path = ""
        self.vol_typed = {}       # path -> volume name the person typed for that draft
        self.type_chosen = {}     # 3.7.0: path -> document type chosen for a draft that is not a deliverable
        self._work = None
        self._result = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame); outer.addWidget(sc)
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
        v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.card = D.Card("Fix a Copy", "Stationkeeper never changes your file. It makes a dated copy in the output folder and "
                           "fixes only the copy. A file someone has open is not copied.",
                           actions=[D.button("Check", "primary", lambda: self.check())])
        r1 = QHBoxLayout()
        r1.addWidget(D.label("Output folder", "label", wrap=False))
        self.out_lbl = D.label("", None); r1.addWidget(self.out_lbl, 1)
        r1.addWidget(D.button("Change...", None, lambda: self.choose_folder()))
        r1.addWidget(D.button("Open the folder", "ghost", lambda: self.open_folder()))
        self.card.body.addLayout(r1)
        r2 = QHBoxLayout()
        r2.addWidget(D.label("Standard", "label", wrap=False))
        self.std_lbl = D.label("", None); r2.addWidget(self.std_lbl, 1)
        r2.addWidget(D.button("Production Standards", "ghost", lambda: self.host.go("prodstd")))
        self.card.body.addLayout(r2)
        self.files = QListWidget(); self.files.setFixedHeight(120); self.card.add(self.files)
        self.files.currentRowChanged.connect(lambda _r: self.file_changed())
        fr = QHBoxLayout()
        fr.addWidget(D.button("Add a file...", None, lambda: self.add_file(), "Any Word file: it is only read"))
        fr.addStretch(1)
        self.cloud = D.label("", "muted"); fr.addWidget(self.cloud)
        self.card.body.addLayout(fr)
        r3 = QHBoxLayout()
        r3.addWidget(D.label("Volume name", "label", wrap=False))
        self.vol = QLineEdit(); self.vol.setPlaceholderText("The name this volume's headers show, for example Volume I Technical")
        self.vol.textEdited.connect(lambda t: self.vol_typed.__setitem__(self.path, t) if self.path else None)
        r3.addWidget(self.vol, 1)
        self.vol_src = D.label("", "muted"); r3.addWidget(self.vol_src)
        self.card.body.addLayout(r3)
        r4 = QHBoxLayout()
        r4.addWidget(D.label("Document type", "label", wrap=False))
        self.dtype = QComboBox(); self.dtype.setMinimumWidth(260); r4.addWidget(self.dtype)
        self.dtype.activated.connect(lambda _i: self.dtype_chosen())
        self.dtype_src = D.label("", "muted"); r4.addWidget(self.dtype_src, 1)
        self.card.body.addLayout(r4)
        self.ctx_lbl = self.card.add(D.label("", "muted"))
        self.status = self.card.add(D.label("Pick a draft and press Check.", "muted"))
        v.addWidget(self.card)
        # the fixes
        self.fix_card = D.Card("What to fix", "Each fix runs on the copy as one guarded change; a fix that would touch anything it "
                               "did not declare is refused and the copy stays as it was before it.",
                               actions=[D.button("Make the fixed copy", "primary", lambda: self.make())])
        self.tiles = QHBoxLayout(); self.fix_card.body.addLayout(self.tiles)
        self.tree = QTreeWidget(); self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Fix", "Found", "Where"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.setColumnWidth(1, 120); self.tree.setColumnWidth(2, 260)
        self.tree.setMinimumHeight(320)
        self.tree.itemChanged.connect(lambda it, col: self.tree_changed(it, col))
        self.fix_card.add(self.tree)
        wr = QHBoxLayout()
        self.word_cb = QCheckBox(PF.WORD_STEP["label"]); wr.addWidget(self.word_cb, 1)
        self.fix_card.body.addLayout(wr)
        self.word_note = self.fix_card.add(D.label("", "muted"))
        v.addWidget(self.fix_card)
        # tables
        self.tab_card = D.Card("Tables", "Every table's rows and the role each gets. Rows in bold wait for your answer. Select rows "
                               "(click, Shift, Ctrl, Ctrl+A) and press a key to set their role: C caption, H header, 2 second header, "
                               "S subhead, B body, U subtotal, T total, N notes, K keep as is.")
        split = QSplitter(Qt.Horizontal)
        self.tab_list = QTableWidget(0, 4); self.tab_list.setHorizontalHeaderLabels(["Table", "Type", "Rows", "Questions"])
        self.tab_list.verticalHeader().setVisible(False); self.tab_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tab_list.setSelectionMode(QAbstractItemView.SingleSelection); self.tab_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tab_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tab_list.currentCellChanged.connect(lambda r, _c, _pr, _pc: self.show_table(r))
        split.addWidget(self.tab_list)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        tr = QHBoxLayout(); tr.addWidget(D.label("Table type", "label", wrap=False))
        self.ttype = QComboBox(); self.ttype.currentIndexChanged.connect(lambda _i: self.type_changed()); tr.addWidget(self.ttype)
        tr.addStretch(1); rv.addLayout(tr)
        self.rows = QTableWidget(0, 4); self.rows.setHorizontalHeaderLabels(["Row", "Role", "First cell", "Why"])
        self.rows.verticalHeader().setVisible(False); self.rows.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rows.setSelectionMode(QAbstractItemView.ExtendedSelection); self.rows.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rows.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch); self.rows.setColumnWidth(2, 240)
        self.rows.setMinimumHeight(300)
        rv.addWidget(self.rows)
        self.q_box = QVBoxLayout(); rv.addLayout(self.q_box)
        split.addWidget(right); split.setSizes([320, 680])
        self.tab_card.add(split)
        for key, role in ROLE_KEYS.items():
            sc_ = QShortcut(QKeySequence(key), self.rows); sc_.setContext(Qt.WidgetShortcut)
            sc_.activated.connect(lambda r=role: self.set_roles(r))
        v.addWidget(self.tab_card)
        # lists and references
        self.more_card = D.Card("Decisions", "Lists whose numbering depends on you, and broken cross-references to point at a target. "
                                "Anything left undecided is left as it is.")
        self.decide = QVBoxLayout(); self.more_card.body.addLayout(self.decide)
        v.addWidget(self.more_card)
        # the result
        self.res_card = D.Card("The fixed copy", "", actions=[D.button("Open the copy", None, lambda: self.open_copy()),
                                                              D.button("Open the report", None, lambda: self.open_report()),
                                                              D.button("Show in folder", "ghost", lambda: self.open_folder())])
        self.res_text = self.res_card.add(D.label("", None))
        self.res_table = QTableWidget(0, 3); self.res_table.setHorizontalHeaderLabels(["Area", "Found before", "Left after"])
        self.res_table.verticalHeader().setVisible(False); self.res_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.res_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.res_table.setMinimumHeight(280)
        self.res_card.add(self.res_table)
        self.res_steps = QListWidget(); self.res_steps.setMinimumHeight(200); self.res_card.add(self.res_steps)
        v.addWidget(self.res_card)
        v.addStretch(1)
        self.timer = QTimer(self, interval=250, timeout=self.tick)
        for c in (self.fix_card, self.tab_card, self.more_card, self.res_card):
            c.setVisible(False)

    # ------------------------------------------------------------------ setup
    def settings(self):
        import app_gui
        return app_gui.load_settings() or {}, app_gui.DATA_DIR

    def folder(self):
        st, data_dir = self.settings()
        return PCY.output_folder(st, data_dir)

    def effort_folder(self):
        return PCY.effort_folder(self.folder(), self.host.effort_name or "")

    def record(self):
        if self.host.ws is None:
            return None
        try:
            import effortrec as R
            return R.Record(self.host.ws.root)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return None

    def context(self, path=None):
        """The effort's own values for this draft: solicitation, company, the deliverable it belongs to, the team's lists."""
        h = self.host
        info = (h.efforts.get(h.effort_name) or {}) if h.effort_name else {}
        lst = None
        if h.ws is not None:
            try:
                lst = h.record_page.effort_list()
            except Exception:  # noqa: BLE001
                diag.swallowed()
        return PRL.context(h.config_dir, h.effort_name or "", info, lst, self.record(), self.path if path is None else path)

    def draft_type(self, ctx):
        """The draft's document type: the deliverable's, else the one chosen here for this draft, else the effort's."""
        d = (ctx or {}).get("deliverable") or {}
        return d.get("doc_type") or self.type_chosen.get(self.path) or None

    def dtype_chosen(self):
        tid = self.dtype.currentData() or ""
        ctx = self.context()
        d = ctx.get("deliverable")
        rec = self.record()
        if d and rec is not None:
            import deliverables as DL
            DL.update(rec, d["id"], doc_type=tid)
        elif self.path:
            self.type_chosen[self.path] = tid
        self.show_context(self.context())
        self.refresh_std()

    def refresh_std(self):
        s = self.std()
        v = s["variables"]
        self.std_lbl.setText(f"{s['name']}{' + this effort' if s.get('effort_over') else ''}: body {v.get('body_font')} "
                             f"{float(v.get('body_size') or 0):g} pt, tables {v.get('table_font')} {float(v.get('table_size') or 0):g} pt, "
                             f"{len(s.get('style_defs') or {})} styles in the library, "
                             f"captions {'2-1' if any(c.get('chapter_level') for c in s['captions']) else '1, 2, 3'}, "
                             f"pages {s['pagination']['name']}")

    def std(self, ctx=None):
        """The standard for the picked draft: team, document type, effort, then the effort's and the draft's own values."""
        ctx = ctx if ctx is not None else self.context()
        base = PRL.for_effort(self.host.config_dir, self.host.ws, type_id=self.draft_type(ctx))
        std = PRL.apply_context(base, ctx, volume_name=self.vol.text() if self.vol.text().strip() else None)
        std["name"], std["effort_over"] = base["name"], base.get("effort_over")
        return std

    def show_context(self, ctx):
        v = ctx.get("variables", {})
        d = ctx.get("deliverable")
        if self.path and self.path not in self.vol_typed:
            self.vol.setText(v.get("volume_name", "") if d else "")
        self.vol_src.setText(f"from the Deliverables board ({d['name']})" if d and self.path not in self.vol_typed else
                             ("typed" if self.path in self.vol_typed else "not on the Deliverables board: type it to build headers"))
        try:
            data = PRL.load(self.host.config_dir)
            eff = (self.host.ws.get("prod_std", {}) if self.host.ws is not None else {}) or {}
            eff_t = PRL.type_of(data, eff.get("type") or data["default"])
            self.dtype.blockSignals(True); self.dtype.clear()
            self.dtype.addItem(f"The effort's ({eff_t['name']})", "")
            for t in data["types"]:
                self.dtype.addItem(t["name"], t["id"])
            cur = self.draft_type(ctx) or ""
            self.dtype.setCurrentIndex(max(0, self.dtype.findData(cur)))
            self.dtype.blockSignals(False)
            self.dtype_src.setText("kept on the Deliverables board" if d else "for this draft")
        except Exception:  # noqa: BLE001
            diag.swallowed()
        lists = ctx.get("lists", {})
        self.ctx_lbl.setText(f"Solicitation: {v.get('solicitation') or 'not set (effort basics)'}"
                             + (f"; company: {v['company']}" if v.get("company") else "")
                             + f". Terms from the team: {len(ctx.get('banned', []))} banned phrases, "
                             f"{len(lists.get('team_terms', []))} dictionary words, {len(lists.get('employee_names', []))} names, "
                             f"{len(lists.get('acronyms', []))} approved acronyms.")

    def refresh(self):
        self.out_lbl.setText(self.effort_folder())
        self.refresh_std()
        keep = [self.files.item(i).data(Qt.UserRole) for i in range(self.files.count())]
        cur = self.path
        self.files.blockSignals(True)
        self.files.clear()
        drafts = []
        if self.host.ws is not None:
            try:
                drafts = self.host.home_page.theme_drafts()
            except Exception:
                diag.swallowed()
        seen = set()
        for name, p in drafts + [(os.path.basename(x), x) for x in keep]:
            if p in seen:
                continue
            seen.add(p)
            it = QListWidgetItem(name); it.setData(Qt.UserRole, p); it.setToolTip(p); self.files.addItem(it)
        for i in range(self.files.count()):
            if self.files.item(i).data(Qt.UserRole) == cur:
                self.files.setCurrentRow(i)
        self.files.blockSignals(False)
        self.word_cb.setEnabled(sys.platform.startswith("win"))
        if not sys.platform.startswith("win"):
            self.word_note.setText("Updating fields needs Word on Windows; open the copy in Word and press Ctrl+A, F9.")

    def add_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A Word file to fix (it is only read; the fixes go into a copy)",
                                                  os.path.expanduser("~"), "Word (*.docx *.docm *.dotx *.dotm)")
            if not path:
                return ""
        it = QListWidgetItem(os.path.basename(path)); it.setData(Qt.UserRole, path); it.setToolTip(path)
        self.files.addItem(it)
        self.files.setCurrentItem(it)
        return path

    def file_changed(self):
        it = self.files.currentItem()
        self.path = it.data(Qt.UserRole) if it else ""
        try:
            self.show_context(self.context())
            self.refresh_std()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        kind = PCY.cloud_kind(self.path) if self.path else ""
        self.cloud.setText(f"In a {kind} folder: people editing it online can't be seen from here; the copy is the version "
                           "synced to this PC." if kind else "")

    def choose_folder(self, path=None):
        if path is None:
            path = QFileDialog.getExistingDirectory(self, "Where fixed copies go", self.folder())
            if not path:
                return ""
        import app_gui
        st = app_gui.load_settings() or {}
        st["prod_output_dir"] = path
        app_gui.save_settings(st)
        self.out_lbl.setText(self.effort_folder())
        diag.activity("prod_output_folder_set")
        return path

    def open_folder(self):
        f = self.effort_folder()
        os.makedirs(f, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(f))

    # ------------------------------------------------------------------ check
    def check(self, wait=False):
        if not self.path:
            self.status.setText("Pick a draft first, or Add a file...")
            return None
        if self._work is not None and self._work.is_alive():
            return None
        std, path = self.std(), self.path
        self.status.setText("Reading the draft (large volumes take a minute)...")
        self._result = None

        def run():
            try:
                self._result = ("check", PF.check(path, std))
            except Exception as e:  # noqa: BLE001
                diag.swallowed()
                self._result = ("error", f"The check stopped ({type(e).__name__}).")
        self._work = bgwork.start(run, "stationkeeper-prodcheck")
        if wait:
            bgwork.wait(self._work)
            return self.tick()
        self.timer.start()
        return None

    def tick(self):
        if self._work is not None and self._work.is_alive():
            if getattr(self, "_progress", ""):
                self.status.setText(self._progress)
            return None
        bgwork.settle()
        self.timer.stop()
        res, self._result = self._result, None
        if res is None:
            return None
        kind, val = res
        if kind == "check":
            self.show_check(val)
        elif kind == "job":
            self.show_job(val)
        else:
            self.status.setText(val)
        return val

    def show_check(self, chk):
        self.chk = chk
        if chk.error and not chk.findings and not chk.tables:
            self.status.setText(chk.error.strip())
            for c in (self.fix_card, self.tab_card, self.more_card):
                c.setVisible(False)
            return
        self.plan = PF.default_plan(chk)
        n = chk.count()
        self.status.setText(f"Read in {chk.seconds:.1f} s: {n} finding{'s' if n != 1 else ''}, {len(chk.tables)} table(s), "
                            f"{chk.stats.get('captions', 0)} caption(s), {chk.stats.get('sections', 0)} section(s)."
                            + (f" Note: {chk.error.strip()}" if chk.error else ""))
        while self.tiles.count():
            x = self.tiles.takeAt(0)
            if x.widget():
                x.widget().deleteLater()
        for area, counts in chk.by_area().items():
            c = sum(counts.values())
            self.tiles.addWidget(D.Tile(str(c), PF.AREAS[area].split(",")[0].split(" and ")[0].lower() if area in PF.AREAS else area,
                                        "ok" if not c else "warn"))
        self.fill_tree()
        self.word_cb.setChecked(bool(self.plan.get("word_update")) and sys.platform.startswith("win"))
        self.fill_tables()
        self.fill_decisions()
        for c in (self.fix_card, self.tab_card, self.more_card):
            c.setVisible(True)
        self.tab_card.setVisible(bool(chk.tables))
        self.more_card.setVisible(bool(chk.list_blocks or chk.broken_refs))
        self.res_card.setVisible(False)
        diag.activity("prod_checked", n=n, rows=len(chk.tables))

    def fill_tree(self):
        chk = self.chk
        self.tree.blockSignals(True)
        self.tree.clear()
        by_fix = {}
        for f in chk.findings:
            by_fix.setdefault(f["fix"] or "", []).append(f)
        for area, title in PF.AREAS.items():
            fixes = [fx for fx in PF.FIXES if fx["area"] == area]
            rows = []
            for fx in fixes:
                items = by_fix.get(fx["key"], [])
                would = chk.would.get(fx["key"], 0)
                if not items and not would and fx["key"] not in ("styles_merge",):
                    continue
                if fx["key"] == "styles_merge" and not would:
                    continue
                rows.append((fx, items, would))
            manual = [f for f in chk.findings if f["area"] == area and (not f["fix"] or f["fix"] == "word_update")]
            if not rows and not manual:
                continue
            top = QTreeWidgetItem([title, str(sum(1 for f in chk.findings if f["area"] == area)), ""])
            fnt = top.font(0); fnt.setBold(True); top.setFont(0, fnt)
            self.tree.addTopLevelItem(top)
            for fx, items, would in rows:
                found = f"{len(items)} found" if items else f"{would} to change"
                it = QTreeWidgetItem([fx["label"], found, ""])
                it.setData(0, Qt.UserRole, fx["key"])
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(0, Qt.Checked if fx["key"] in self.plan["on"] else Qt.Unchecked)
                if fx["kind"] == "choose":
                    it.setToolTip(0, "Choose the targets under Decisions first")
                if fx.get("help"):
                    it.setToolTip(0, fx["help"])
                top.addChild(it)
                for f in items[:400]:
                    c = QTreeWidgetItem([f"{f['rule']}  {f['what']}", f["severity"], f["near"]])
                    c.setToolTip(0, PF.RULE_TEXT.get(f["rule"], ""))
                    it.addChild(c)
            if manual:
                it = QTreeWidgetItem(["Updated by Word, or reviewed by hand", f"{len(manual)} found", ""])
                top.addChild(it)
                for f in manual[:400]:
                    c = QTreeWidgetItem([f"{f['rule']}  {f['what']}", "Word updates it" if f["fix"] == "word_update" else "review",
                                         f["near"]])
                    it.addChild(c)
            top.setExpanded(True)
        self.tree.blockSignals(False)

    def tree_changed(self, it, col):
        key = it.data(0, Qt.UserRole)
        if not key or self.plan is None:
            return
        on = set(self.plan["on"])
        if it.checkState(0) == Qt.Checked:
            on.add(key)
        else:
            on.discard(key)
        self.plan["on"] = [f["key"] for f in PF.FIXES if f["key"] in on]

    def set_fix(self, key, on):
        """For tests and keyboard users: switch a fix on or off."""
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                c = top.child(j)
                if c.data(0, Qt.UserRole) == key:
                    c.setCheckState(0, Qt.Checked if on else Qt.Unchecked)
                    return True
        return False

    # ------------------------------------------------------------------ tables
    def fill_tables(self):
        chk = self.chk
        self.tab_list.setRowCount(0)
        types = self.std().get("table_types") or {}
        self.ttype.blockSignals(True); self.ttype.clear()
        for k, t in types.items():
            self.ttype.addItem(t.get("name") or k, k)
        self.ttype.blockSignals(False)
        for t in chk.tables:
            r = self.tab_list.rowCount(); self.tab_list.insertRow(r)
            name = f"{t['index']}. {t['caption'][:60]}" if t["caption"] else f"{t['index']}. (no caption)"
            nq = sum(len(g["rows"]) for g in t["questions"].values())
            for c, text in enumerate((name, types.get(t["type"], {}).get("name", t["type"]), str(len(t["rows"])), str(nq) if nq else "")):
                self.tab_list.setItem(r, c, QTableWidgetItem(text))
        if chk.tables:
            self.tab_list.selectRow(0)
            self.show_table(0)

    def current_table(self):
        r = self.tab_list.currentRow()
        return self.chk.tables[r] if self.chk and 0 <= r < len(self.chk.tables) else None

    def role_of(self, t, row):
        manual = (self.plan["table_roles"].get(t["index"]) or {}).get(row["i"])
        if manual:
            return manual, "manual"
        if row["status"] == "ask" and row["group"] in self.plan["table_answers"]:
            return self.plan["table_answers"][row["group"]], "answered"
        return row["role"], row["status"]

    def show_table(self, r):
        t = self.current_table()
        if t is None:
            return
        tkey = self.plan["table_types"].get(t["index"], t["type"])
        self.ttype.blockSignals(True); self.ttype.setCurrentIndex(max(0, self.ttype.findData(tkey))); self.ttype.blockSignals(False)
        self.rows.setRowCount(0)
        for row in t["rows"]:
            k = self.rows.rowCount(); self.rows.insertRow(k)
            role, status = self.role_of(t, row)
            cells = (str(row["i"] + 1), ROLE_TEXT.get(role, role) + ("" if status in ("sure", "tagged") else f" ({status})"),
                     row["text"], row["why"])
            for c, text in enumerate(cells):
                it = QTableWidgetItem(text)
                if status == "ask":
                    f = it.font(); f.setBold(True); it.setFont(f)
                self.rows.setItem(k, c, it)
        self.fill_questions(t)

    def fill_questions(self, t):
        while self.q_box.count():
            x = self.q_box.takeAt(0)
            if x.layout():
                while x.layout().count():
                    y = x.layout().takeAt(0)
                    if y.widget():
                        y.widget().deleteLater()
            elif x.widget():
                x.widget().deleteLater()
        for g, q in t["questions"].items():
            h = QHBoxLayout()
            h.addWidget(QLabel(f"{q['why']} (rows {', '.join(str(i + 1) for i in q['rows'][:8])}{'...' if len(q['rows']) > 8 else ''}; "
                               f"e.g. “{q['example'][:40]}”)"), 1)
            cb = QComboBox(); cb.addItem("Leave as it is", "")
            for o in q["options"]:
                cb.addItem(ROLE_TEXT.get(o, o), o)
            cb.setCurrentIndex(max(0, cb.findData(self.plan["table_answers"].get(g, ""))))
            cb.currentIndexChanged.connect(lambda _i, g=g, cb=cb: self.answer(g, cb.currentData()))
            h.addWidget(cb)
            self.q_box.addLayout(h)

    def answer(self, group, role):
        if role:
            self.plan["table_answers"][group] = role
        else:
            self.plan["table_answers"].pop(group, None)
        self._ensure_tables_on()
        self.show_table(self.tab_list.currentRow())

    def set_roles(self, role, rows=None):
        t = self.current_table()
        if t is None:
            return 0
        sel = rows if rows is not None else sorted({i.row() for i in self.rows.selectedIndexes()})
        if not sel:
            return 0
        d = self.plan["table_roles"].setdefault(t["index"], {})
        for r in sel:
            d[t["rows"][r]["i"]] = role
        self._ensure_tables_on()
        self.show_table(self.tab_list.currentRow())
        self.rows.clearSelection()
        for r in sel:
            self.rows.selectRow(r)
        diag.activity("prod_row_roles_set", n=len(sel))
        return len(sel)

    def type_changed(self):
        t = self.current_table()
        if t is None:
            return
        self.plan["table_types"][t["index"]] = self.ttype.currentData()
        self._ensure_tables_on()
        self.tab_list.item(self.tab_list.currentRow(), 1).setText(self.ttype.currentText())

    def _ensure_tables_on(self):
        if "tables" not in self.plan["on"]:
            self.plan["on"] = [f["key"] for f in PF.FIXES if f["key"] in set(self.plan["on"]) | {"tables"}]
            self.set_fix("tables", True)

    # ------------------------------------------------------------------ decisions
    def fill_decisions(self):
        while self.decide.count():
            x = self.decide.takeAt(0)
            if x.layout():
                while x.layout().count():
                    y = x.layout().takeAt(0)
                    if y.widget():
                        y.widget().deleteLater()
            elif x.widget():
                x.widget().deleteLater()
        chk = self.chk
        for b in chk.list_blocks:
            h = QHBoxLayout()
            h.addWidget(QLabel(f"List “{b['first']}” ({b['near']}): {b['why']}"), 1)
            cb = QComboBox(); cb.addItem("Leave it as it is", ""); cb.addItem("Restart at 1", "restart"); cb.addItem("Continue the list before", "continue")
            cb.currentIndexChanged.connect(lambda _i, bid=b["id"], cb=cb: self.list_answer(bid, cb.currentData()))
            h.addWidget(cb)
            self.decide.addLayout(h)
        for x in chk.broken_refs:
            h = QHBoxLayout()
            h.addWidget(QLabel(f"{x['kind']} to {x['target']} ({x['near']}): the target is gone. Point it at"), 1)
            cb = QComboBox(); cb.addItem("Leave it broken (fix by hand)", "")
            for bm in chk.bookmarks:
                cb.addItem(bm, bm)
            cb.currentIndexChanged.connect(lambda _i, tg=x["target"], cb=cb: self.relink(tg, cb.currentData()))
            h.addWidget(cb)
            self.decide.addLayout(h)

    def list_answer(self, bid, ans):
        if ans:
            self.plan["list_answers"][bid] = ans
            self.plan["on"] = [f["key"] for f in PF.FIXES if f["key"] in set(self.plan["on"]) | {"lists"}]
            self.set_fix("lists", True)
        else:
            self.plan["list_answers"].pop(bid, None)

    def relink(self, target, new):
        if new:
            self.plan["xref_mapping"][target] = new
            self.plan["on"] = [f["key"] for f in PF.FIXES if f["key"] in set(self.plan["on"]) | {"xref_relink"}]
            self.set_fix("xref_relink", True)
        else:
            self.plan["xref_mapping"].pop(target, None)

    # ------------------------------------------------------------------ make the copy
    def make(self, wait=False, open_list=PCY._ASK, word=None):
        if self.chk is None or self.plan is None:
            self.status.setText("Check the draft first.")
            return None
        if self._work is not None and self._work.is_alive():
            return None
        plan = copy.deepcopy(self.plan)
        plan["word_update"] = self.word_cb.isChecked()
        if "xref_relink" in plan["on"] and not plan["xref_mapping"]:
            plan["on"].remove("xref_relink")
        std, path, folder = self.std(), self.path, self.effort_folder()
        if word is None and plan["word_update"] and sys.platform.startswith("win"):
            import prodword
            word = prodword.update_fields
        effort = self.host.effort_name or ""
        reviewed = self.chk
        deliv = self.context().get("deliverable")
        self.status.setText("Making the copy and fixing it...")
        self._result = None

        self._progress = ""
        t0 = time.monotonic()

        def say(text):
            self._progress = f"{text}... ({int(time.monotonic() - t0)} s)"

        def run():
            try:
                job = PF.run(path, folder, std, plan, word=word, open_list=open_list, before=reviewed, progress=say)
                wr = next((x.get("report") or {} for x in job.steps if x.get("key") == "word_update"), {})
                job.page_note = PRL.limit_note((deliv or {}).get("limit", ""), wr.get("pages"))
                job.report = PF.write_report(job, effort)
                self._result = ("job", job)
            except (PCY.Busy, PCY.NotAllowed) as e:
                self._result = ("error", f"Not copied: {e}")
            except Exception as e:  # noqa: BLE001
                diag.swallowed()
                self._result = ("error", f"Stopped ({type(e).__name__}). The original was not changed.")
        self._work = bgwork.start(run, "stationkeeper-prodfix")
        if wait:
            bgwork.wait(self._work)
            return self.tick()
        self.timer.start()
        return None

    def show_job(self, job):
        self.job = job
        refused = [s for s in job.steps if "refused" in s]
        changed = [s for s in job.steps if s.get("changed")]
        ok = "The original is unchanged (checked byte for byte)." if job.original_ok else \
            "Warning: the original changed while Stationkeeper worked. Stationkeeper never opened it for writing: someone else saved it."
        self.res_text.setText(f"{os.path.basename(job.copy)}\n{len(changed)} fix(es) changed the copy"
                              + (f", {len(refused)} refused (the copy kept as it was before each)" if refused else "")
                              + f". {job.before_check.count()} found before, {job.after_check.count()} left. {ok}"
                              + (f"\n{job.page_note}" if getattr(job, "page_note", "") else ""))
        self.res_table.setRowCount(0)
        for r in PF.summary(job):
            k = self.res_table.rowCount(); self.res_table.insertRow(k)
            for c, text in enumerate((r["area"], str(r["before"]), str(r["after"]))):
                self.res_table.setItem(k, c, QTableWidgetItem(text))
        self.res_steps.clear()
        for s in job.steps:
            self.res_steps.addItem(("Refused: " if "refused" in s else ("Changed: " if s.get("changed") else "Nothing to change: "))
                                   + s["step"] + (f"  ({s['refused'][:160]})" if "refused" in s else ""))
        self.res_card.setVisible(True)
        self.status.setText(f"Done. The copy and its report are in {os.path.dirname(job.copy)}.")
        rec = self.record()
        if rec is not None:
            try:
                rec.log("production", f"Fix a Copy: {os.path.basename(job.copy)} made from {os.path.basename(job.original)}; "
                        f"{len(changed)} fix(es), {job.before_check.count()} found, {job.after_check.count()} left; original "
                        + ("unchanged" if job.original_ok else "changed by someone else while it was copied")
                        + (f". {job.page_note}" if getattr(job, "page_note", "") else ""),
                        ref={"copy": job.copy, "original": job.original}, save=True)
            except Exception:  # noqa: BLE001
                diag.swallowed()
        diag.activity("prod_fixed", n=len(job.steps), rows=len(refused))

    def open_copy(self):
        if self.job:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.job.copy))

    def open_report(self):
        if self.job and getattr(self.job, "report", ""):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.job.report))
