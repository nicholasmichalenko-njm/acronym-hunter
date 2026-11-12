"""Shred > Sort (3.64.0): name the big areas of what is being bought and file every requirement under one. Topics on the
left with Unsorted pinned on top, the sentences of the one picked in the middle, the customer's words on the right.
The same topics as Review's Sort mode (topics.py, the effort record): a sentence's first topic is its home, the others
are cross-references. Overview counts each topic's shall, should and may and its L, M and SOW sentences.
claude/stationkeeper-sort-decisions-2026-11-05.md"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QSplitter,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import diag
import effortrec as R
import topics as TP
from . import design as D

STRENGTH = {"Mandatory": "shall", "Desired": "should", "Optional": "may", "Evaluation": "evaluated", "Check": "check", "Information": "info"}
UNSORTED, ALL = "__unsorted__", "__all__"


class SortPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.showing = UNSORTED
        self.rows = []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.sumlab = D.label("", "title"); top.addWidget(self.sumlab, 1)
        self.view = QComboBox(); self.view.addItems(["Sort", "Overview", "Structure"]); self.view.currentIndexChanged.connect(lambda i: self.stack.setCurrentIndex(i))
        top.addWidget(self.view)
        self.start = QComboBox(); self.start.addItem("Start from...", "")
        for k, lab in (("headings", "The RFP's headings (its own numbering)"), ("factors", "The evaluation factors"),
                       ("starter", "The starter list")):
            self.start.addItem(lab, k)
        self.start.activated.connect(lambda _i: self.seed(self.start.currentData()))
        top.addWidget(self.start)
        top.addWidget(D.button("Read back from Excel...", None, lambda: self.read_back(), "A matrix workbook with ID and Topic columns, "
                               "edited in Excel: each piece goes under the topics typed there"))
        v.addWidget(D.label("Name the big areas of what is being bought, then file each requirement under one: select rows and "
                            "press 1 to 9 for the first nine topics, or pick a topic and File. A piece's first topic is its home; "
                            "the others are cross-references. Rename a seeded topic in your own words; its pieces stay.", "muted"))
        self.stack = QStackedWidget(); v.addWidget(self.stack, 1)
        # ---- Sort
        sw = QWidget(); sl = QVBoxLayout(sw); sl.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Horizontal); sl.addWidget(split, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Topic", ""]); self.tree.setColumnCount(2)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.itemSelectionChanged.connect(self._tree_picked)
        lv.addWidget(self.tree, 1)
        tb = QHBoxLayout(); lv.addLayout(tb)
        tb.addWidget(D.button("+ Topic", None, lambda: self.add_topic()))
        tb.addWidget(D.button("+ Subtopic", "ghost", lambda: self.add_topic(sub=True)))
        tb.addWidget(D.button("Rename", "ghost", lambda: self.rename()))
        tb2 = QHBoxLayout(); lv.addLayout(tb2)
        tb2.addWidget(D.button("Merge into...", "ghost", lambda: self.merge()))
        tb2.addWidget(D.button("Keywords...", "ghost", lambda: self.keywords(), "Words that point at this topic, for the suggestions"))
        tb2.addWidget(D.button("Remove", "danger", lambda: self.remove_topic()))
        split.addWidget(left)
        mid = QWidget(); mv = QVBoxLayout(mid); mv.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 6); self.table.setHorizontalHeaderLabels(["ID", "", "Kind", "The customer's words", "Home", "Suggested"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.show_card)
        mv.addWidget(self.table, 1)
        fr = QHBoxLayout(); mv.addLayout(fr)
        fr.addWidget(D.label("File the selected under", None, wrap=False))
        self.target = QComboBox(); fr.addWidget(self.target, 1)
        fr.addWidget(D.button("File", "primary", lambda: self.file(self.target.currentData())))
        fr.addWidget(D.button("Also under", "ghost", lambda: self.file(self.target.currentData(), also=True), "A cross-reference: the home stays"))
        fr.addWidget(D.button("Back to Unsorted", "ghost", lambda: self.unfile()))
        fr.addWidget(D.button("Take the suggestions", "ghost", lambda: self.take_suggestions(),
                              "File the selected rows (or every row shown) under their suggested topic; each shows why"))
        split.addWidget(mid)
        right = QWidget(); self.card = QVBoxLayout(right); self.card.setAlignment(Qt.AlignTop)
        split.addWidget(right)
        split.setSizes([260, 700, 320])
        self.stack.addWidget(sw)
        # ---- Overview
        ow = QWidget(); ol = QVBoxLayout(ow); ol.setContentsMargins(0, 0, 0, 0)
        self.over = QTableWidget(0, 9)
        self.over.setHorizontalHeaderLabels(["Topic", "Requirements", "shall / must", "should", "may", "Instructions (L)", "Evaluation (M)", "Work (SOW)", "Our fit"])
        self.over.verticalHeader().setVisible(False); self.over.setEditTriggers(QTableWidget.NoEditTriggers)
        self.over.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        ol.addWidget(D.label("The request at a glance: what each area asks for and how firmly.", "muted"))
        ol.addWidget(self.over, 1)
        self.stack.addWidget(ow)
        from .sortstructure import StructureView                       # 3.65.0
        self.struct = StructureView(self); self.stack.addWidget(self.struct)
        self.keys = []
        for n in range(9):
            sc = QShortcut(QKeySequence(str(n + 1)), self.table); sc.setContext(Qt.WidgetShortcut)
            sc.activated.connect(lambda n=n: self.file_n(n))
            self.keys.append(sc)

    # ------------------------------------------------------------ data
    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    @property
    def M(self):
        return self.host.review.M if self.host.review is not None else None

    def refresh(self):
        r, M = self.rec(), self.M
        self.setEnabled(r is not None)
        if r is None:
            return
        items = M.items if M is not None else []
        srt = TP.sortable(items)
        uns = TP.unsorted(r, items)
        self.sumlab.setText(f"{len(srt) - len(uns)} of {len(srt)} sorted, {len(uns)} in Unsorted" if srt else
                            "Nothing to sort yet: add the customer's documents in Documents first")
        self.fill_tree(r, items)
        self.fill_table(r, items)
        self.fill_targets(r)
        self.fill_overview(r, items)
        self.struct.refresh()
        self.show_card()

    def fill_tree(self, r, items):
        tags = r.data.get("topic_tags", {})
        srt = {it["id"] for it in TP.sortable(items)}
        home = {}
        for s, xs in tags.items():
            if xs and s in srt:
                home[xs[0]] = home.get(xs[0], 0) + 1
        self.tree.blockSignals(True); self.tree.clear()
        u = QTreeWidgetItem([f"Unsorted", str(len(TP.unsorted(r, items)))]); u.setData(0, Qt.UserRole, UNSORTED)
        f = u.font(0); f.setBold(True); u.setFont(0, f); self.tree.addTopLevelItem(u)
        a = QTreeWidgetItem(["All requirements", str(len(srt))]); a.setData(0, Qt.UserRole, ALL); self.tree.addTopLevelItem(a)
        self.tree_items = {UNSORTED: u, ALL: a}
        for n, t in enumerate(TP.roots(r)):
            kids = TP.children(r, t["id"])
            total = home.get(t["id"], 0) + sum(home.get(c["id"], 0) for c in kids)
            it = QTreeWidgetItem([(f"{n + 1}  " if n < 9 else "") + t["name"], str(total)]); it.setData(0, Qt.UserRole, t["id"])
            it.setIcon(0, D.dot_icon(t.get("color") or "#888888"))
            if t.get("aliases"):
                it.setToolTip(0, "Also called: " + ", ".join(t["aliases"]))
            self.tree.addTopLevelItem(it); self.tree_items[t["id"]] = it
            for c in kids:
                ci = QTreeWidgetItem([c["name"], str(home.get(c["id"], 0))]); ci.setData(0, Qt.UserRole, c["id"]); it.addChild(ci)
                self.tree_items[c["id"]] = ci
            it.setExpanded(True)
        cur = self.tree_items.get(self.showing) or u
        cur.setSelected(True); self.tree.setCurrentItem(cur)
        self.tree.blockSignals(False)

    def _tree_picked(self):
        it = self.tree.currentItem()
        self.showing = it.data(0, Qt.UserRole) if it is not None else UNSORTED
        r = self.rec()
        if r is not None:
            self.fill_table(r, self.M.items if self.M is not None else [])
            if self.showing not in (UNSORTED, ALL):
                self.target.setCurrentIndex(max(0, self.target.findData(self.showing)))

    def fill_table(self, r, items):
        tags = r.data.get("topic_tags", {})
        names = {t["id"]: t["name"] for t in TP.topics(r)}
        srt = TP.sortable(items)
        if self.showing == UNSORTED:
            rows = TP.unsorted(r, items)
        elif self.showing == ALL:
            rows = srt
        else:
            ids = {self.showing} | {c["id"] for c in TP.children(r, self.showing)}
            rows = [it for it in srt if (tags.get(it["id"]) or [None])[0] in ids or (set(tags.get(it["id"]) or []) & ids)]
        self.rows = rows
        self.sugg = TP.suggest(r, items) if self.showing in (UNSORTED, ALL) else {}
        self.table.setRowCount(len(rows))
        for i, it in enumerate(rows):
            xs = tags.get(it["id"]) or []
            homen = names.get(xs[0], "") if xs else ""
            if len(xs) > 1:
                homen += f" (+{len(xs) - 1})"
            sg = self.sugg.get(it["id"])
            vals = [it["id"], STRENGTH.get(it.get("strength", ""), ""), it.get("type", ""), it.get("text", ""), homen,
                    f"{names.get(sg[0], '')} ({sg[1]})" if sg else ""]
            for j, val in enumerate(vals):
                c = QTableWidgetItem(val)
                if j == 3:
                    c.setToolTip(it.get("text", ""))
                self.table.setItem(i, j, c)

    def fill_targets(self, r):
        cur = self.target.currentData()
        self.target.clear()
        for t in TP.roots(r):
            self.target.addItem(t["name"], t["id"])
            for c in TP.children(r, t["id"]):
                self.target.addItem("    " + c["name"], c["id"])
        self.target.setCurrentIndex(max(0, self.target.findData(cur)))

    def fill_overview(self, r, items):
        ov = TP.overview(r, items)
        self.over.setRowCount(len(ov))
        for i, o in enumerate(ov):
            st, ty = o["by_strength"], o["by_type"]
            fit = (TP.get(r, o["id"]) or {}).get("fit", "") if o["id"] else ""
            for j, val in enumerate((o["name"], o["total"], st["Mandatory"], st["Desired"], st["Optional"], ty["Instruction"],
                                     ty["Evaluation"], ty["SOW"], fit)):
                self.over.setItem(i, j, QTableWidgetItem(str(val)))
        self.overview_now = ov

    def selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.rows[i] for i in rows if 0 <= i < len(self.rows)]

    def show_card(self):
        while self.card.count():
            w = self.card.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        sel = self.selected()
        if len(sel) != 1:
            self.card.addWidget(D.label(f"{len(sel)} selected." if sel else "Select a requirement to see the customer's words, "
                                        "where it came from and its topics.", "muted"))
            return
        it = sel[0]
        r = self.rec()
        self.card.addWidget(D.label(f"{it['id']}  ·  {it.get('type', '')}  ·  {STRENGTH.get(it.get('strength', ''), '')}", "muted"))
        q = D.label(it.get("text", "")); q.setTextInteractionFlags(Qt.TextSelectableByMouse); self.card.addWidget(q)
        where = " ".join(x for x in (it.get("doc", ""), it.get("loc", ""), it.get("section", "")) if x)
        if where:
            self.card.addWidget(D.label(where, "muted"))
        ts = TP.of(r, it["id"])
        self.card.addWidget(D.label(("Home: <b>" + ts[0]["name"] + "</b>" + ("; also under " + ", ".join(t["name"] for t in ts[1:]) if len(ts) > 1 else ""))
                                    if ts else "In Unsorted.", None))
        self.card.addWidget(D.button("Split...", "ghost", lambda: self.split(it), "Cut a compound sentence into parts with the same words "
                                     "(IDs .a, .b); each part keeps its topics"))
        self.card.addWidget(D.button("Open in Shred", "ghost", lambda: (self.host.go("assign"), self.host.assign_page.select(it["id"]))))

    # ------------------------------------------------------------ actions
    def _after(self, msg=""):
        self.refresh()
        try:
            self.host.home_page.path.refresh()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        if msg:
            self.host.status(msg)

    def seed(self, how):
        r = self.rec()
        if r is None or not how:
            return []
        if how == "headings":
            got = TP.from_headings(r, self.M.items if self.M is not None else [])
        elif how == "factors":
            got = TP.from_factors(r)
        else:
            got = TP.add_starter(r)
        self.start.setCurrentIndex(0)
        diag.activity("sort_seeded", n=len(got))
        self._after(f"{len(got)} topic(s) ready. Rename any in your own words; the pieces under them stay.")
        return got

    def add_topic(self, name=None, sub=False):
        r = self.rec()
        if r is None:
            return None
        parent = self.showing if sub and self.showing not in (UNSORTED, ALL) else ""
        if sub and not parent:
            self.host.status("Pick the topic the subtopic goes under first.")
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "New subtopic" if sub else "New topic", "Name (for example Network Operations):")
            if not ok:
                return None
        tid = TP.add(r, name)
        if tid and parent:
            TP.set_parent(R.Record(self.host.ws.root), tid, parent)
        self._after()
        return tid

    def _current_topic(self):
        return self.showing if self.showing not in (UNSORTED, ALL) else None

    def rename(self, name=None):
        tid = self._current_topic()
        r = self.rec()
        t = TP.get(r, tid) if tid else None
        if t is None:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename", "New name:", text=t["name"])
            if not ok:
                return False
        old = t["name"]
        ok = TP.update(r, tid, name=name)
        r2 = R.Record(self.host.ws.root)
        t2 = TP.get(r2, tid)
        if ok and t2 is not None and old != t2["name"]:
            t2.setdefault("aliases", [])
            if old not in t2["aliases"]:
                t2["aliases"].append(old)
            r2.save()
        self._after()
        return ok

    def merge(self, into=None):
        tid = self._current_topic()
        r = self.rec()
        if tid is None:
            self.host.status("Pick the topic to merge first.")
            return False
        if into is None:
            others = [t for t in TP.topics(r) if t["id"] != tid]
            names = [t["name"] for t in others]
            pick, ok = QInputDialog.getItem(self, "Merge into", "Its requirements go to:", names, 0, False)
            if not ok:
                return False
            into = others[names.index(pick)]["id"]
        ok = TP.merge(r, into, tid)
        self.showing = into
        self._after()
        return ok

    def remove_topic(self):
        tid = self._current_topic()
        if tid is None:
            return False
        r = self.rec()
        for c in TP.children(r, tid):
            TP.set_parent(r, c["id"], "")
        ok = TP.remove(R.Record(self.host.ws.root), tid)
        self.showing = UNSORTED
        self._after()
        return ok

    def file(self, tid, also=False, rows=None):
        r = self.rec()
        rows = rows if rows is not None else self.selected()
        if r is None or not tid or not rows:
            self.host.status("Select requirements and a topic first.")
            return 0
        sids = [it["id"] for it in rows]
        if also:
            n = 0
            tags = r.data.setdefault("topic_tags", {})
            for s in sids:
                if tid not in (tags.get(s) or []):
                    tags.setdefault(s, []).append(tid); n += 1
            r.save()
        else:
            n = TP.file_under(r, sids, tid)
        diag.activity("sort_filed", n=len(sids))
        self._after(f"{len(sids)} requirement(s) {'also under' if also else 'filed under'} {TP.get(r, tid)['name']}.")
        return n

    def file_n(self, n):
        r = self.rec()
        roots = TP.roots(r) if r is not None else []
        if n < len(roots):
            return self.file(roots[n]["id"])
        self.host.status(f"No topic {n + 1} yet.")
        return 0

    def unfile(self, rows=None):
        r = self.rec()
        rows = rows if rows is not None else self.selected()
        if r is None or not rows:
            return 0
        TP.untag(r, [it["id"] for it in rows])
        self._after()
        return len(rows)

    def split(self, it, at=None):
        R_ = self.host.review
        if R_ is None:
            return []
        old = it["id"]
        parts = R_.split(it, at)
        if parts:
            TP.carry_split(self.rec(), old, [p["id"] for p in parts])
            self.host.changed()
            diag.activity("sort_split", n=len(parts))
        else:
            self.host.status("The rules see one requirement here. Split it in Shred at the point you click.")
        self._after()
        return parts

    def read_back(self, path=None):
        r = self.rec()
        if r is None:
            return None
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A matrix workbook with ID and Topic columns", "", "Excel (*.xlsx)")
            if not path:
                return None
        try:
            got = TP.read_back(r, self.M.items if self.M is not None else [], path)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"That workbook could not be read ({type(e).__name__}). Close it in Excel and try again.")
            return None
        diag.activity("sort_read_back", n=got["filed"])
        self._after(f"{got['filed']} requirement(s) filed from the workbook; {got['new_topics']} new topic(s)"
                    + (f"; {got['unknown_ids']} ID(s) not in this effort" if got["unknown_ids"] else "") + ".")
        return got

    # ------------------------------------------------------------ 3.65.0 suggestions
    def keywords(self, words=None):
        tid = self._current_topic()
        r = self.rec()
        t = TP.get(r, tid) if tid else None
        if t is None:
            self.host.status("Pick a topic first.")
            return None
        if words is None:
            words, ok = QInputDialog.getText(self, f"Words for {t['name']}", "Words that point at it, commas between them "
                                             "(for example SIEM, log retention, NIST 800-53):", text=", ".join(t.get("keywords") or []))
            if not ok:
                return None
        TP.set_keywords(r, tid, words)
        self._after("Suggestions use these words now.")
        return TP.get(self.rec(), tid).get("keywords")

    def take_suggestions(self, rows=None):
        r = self.rec()
        rows = rows if rows is not None else (self.selected() or self.rows)
        sg = getattr(self, "sugg", {}) or {}
        by = {}
        for it in rows:
            if it["id"] in sg:
                by.setdefault(sg[it["id"]][0], []).append(it["id"])
        n = 0
        for tid, sids in by.items():
            n += TP.file_under(r, sids, tid)
        diag.activity("sort_suggestions_taken", n=n)
        self._after(f"{n} requirement(s) filed under their suggested topic.")
        return n

