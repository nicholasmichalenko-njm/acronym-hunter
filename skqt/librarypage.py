"""The document library (2.83.0): every document an effort touches, in one place: the customer's documents, the bidders
library, Q&A and our own, plus categories the person adds. Folders and tags (every folder a file came from is a tag),
a role on every document (Builds the matrix, Context, Reference only, Not needed) suggested from its category and type
and confirmed with who, when and why, and search across the names, tags and text of every document.

Bringing in a ton of files: Add a folder... walks it, reads every file in the background with a progress bar (Stop
writes nothing), suggests each file's category from its folders, its type, its role and whether it is a new version of
a document already here, and shows all of it in one review table before anything is added. Customer documents still
go to the customer documents folder (Read RFP, Requirements, Compare, Impact review see only them); the others are
copied into the effort's library folder, so the effort stays whole wherever it goes. Rules only (No AI); nothing leaves
the PC."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox, QListWidgetItem, QScrollArea,
                               QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import docintake as DI
import docversions as DV
from . import design as D
from .doctypeui import type_box
from .adaptive import FlowLayout
from .progress import JobWorker, TaskPanel

CAT_TONE = {"customer": "crit", "bidders": "warn", "qa": "ok", "ours": "cust"}
ROLE_TONE = {"matrix": "req", "context": "ctx", "reference": "accent", "not_needed": "faint"}


def _item(text, data=None, tip=""):
    it = QTableWidgetItem(text)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    if data is not None:
        it.setData(Qt.UserRole, data)
    if tip:
        it.setToolTip(tip)
    return it


# ====================================================================== the review table
class IntakeDialog(QDialog):
    """One table for every file before anything is added: what it is (new, a version of one here, skip), its category,
    folder, role, and for customer documents its initial and type. Rows can be set many at a time."""

    def __init__(self, parent, plan, lib):
        super().__init__(parent)
        self.setWindowTitle(f"Add {len(plan)} document(s) to the library")
        self.resize(1320, 720)
        self.plan, self.lib = plan, lib
        v = QVBoxLayout(self)
        new = sum(1 for e in plan if not e.get("dup"))
        v.addWidget(D.label(f"{new} new file(s), {len(plan) - new} already here. Each file's category comes from the folders "
                            "it was in; its role from its category and type; a match to a document already here makes it a "
                            "new version. Change anything, for one row or many (select rows, then Set), then Add. Customer "
                            "documents need an initial and a type (the initial starts each requirement's reference).", "muted"))
        bulk = QHBoxLayout(); v.addLayout(bulk)
        bulk.addWidget(D.label("Selected rows:", "label", wrap=False))
        self.b_cat = QComboBox(); self.b_cat.addItem("Category...", "")
        for k, n in lib.categories():
            self.b_cat.addItem(n, k)
        self.b_cat.activated.connect(lambda _i: self.set_rows(category=self.b_cat.currentData()))
        bulk.addWidget(self.b_cat)
        self.b_role = QComboBox(); self.b_role.addItem("Role...", "")
        for k, n in DV.ROLES:
            self.b_role.addItem(n, k)
        self.b_role.activated.connect(lambda _i: self.set_rows(role=self.b_role.currentData()))
        bulk.addWidget(self.b_role)
        bulk.addWidget(D.button("Skip them", None, lambda: self.set_rows(skip=True)))
        bulk.addWidget(D.button("Select all", "ghost", lambda: self.table.selectAll()))
        bulk.addStretch(1)
        self.count = D.label("", "muted", wrap=False); bulk.addWidget(self.count)
        cols = ["File", "From folder", "What it is", "Category", "Role", "Initial", "Type", "Name", "Tags"]
        self.table = QTableWidget(len(plan), len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for c, wdt in enumerate((220, 170, 260, 150, 140, 60, 110, 180, 200)):
            self.table.setColumnWidth(c, wdt)
        self.rows = []
        for i, e in enumerate(plan):
            self.table.setItem(i, 0, _item(os.path.basename(e["path"]), tip=e["path"]))
            self.table.setItem(i, 1, _item(e.get("folder", "") or "(the files picked)"))
            what = QComboBox()
            if e.get("dup"):
                what.addItem(f"Already here: {e['dup'][0]['name']}", ("skip", None))
            else:
                what.addItem("A new document", ("new", None))
                for d, _sc, how in e.get("cands", [])[:6]:
                    what.addItem(f"A new version of {d['name']}  ({how})", ("version", d["id"]))
                what.addItem("Skip it", ("skip", None))
                if e["choice"] == "version" and e.get("doc"):
                    what.setCurrentIndex(max(0, next((k for k in range(what.count()) if what.itemData(k) == ("version", e["doc"])), 0)))
            cat = QComboBox()
            for k, n in lib.categories():
                cat.addItem(n, k)
            cat.setCurrentIndex(max(0, cat.findData(e.get("category", "customer"))))
            role = QComboBox()
            for k, n in DV.ROLES:
                role.addItem(n, k)
            role.setCurrentIndex(max(0, role.findData(e.get("role") or "matrix")))
            ini = QLineEdit(e.get("initial", "")); ini.setMaxLength(6)
            ini.setProperty("sk_typed", False)                 # 2.94.0: the initial follows the type until you type one
            ini.textEdited.connect(lambda t, w=ini: w.setProperty("sk_typed", bool(t.strip())))
            ty = type_box(e.get("type", ""))
            name = QLineEdit(e.get("name", ""))
            tags = QLineEdit(", ".join(e.get("tags", []))); tags.setToolTip("Comma between tags; the folder names are always tags")
            for c, w in ((2, what), (3, cat), (4, role), (5, ini), (6, ty), (7, name), (8, tags)):
                self.table.setCellWidget(i, c, w)
            row = {"what": what, "cat": cat, "role": role, "ini": ini, "ty": ty, "name": name, "tags": tags}
            self.rows.append(row)
            what.currentIndexChanged.connect(lambda _k, r=i: self._changed(r))
            cat.currentIndexChanged.connect(lambda _k, r=i: self._cat_changed(r))
            ty.currentTextChanged.connect(lambda _t, r=i: self._type_changed(r))
            self._changed(i)
        v.addWidget(self.table, 1)
        self.problem = D.label("", "crit"); self.problem.hide(); v.addWidget(self.problem)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Add")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.show_count()

    def _changed(self, r):
        w = self.rows[r]
        kind = (w["what"].currentData() or ("",))[0]
        new = kind == "new"
        cust = w["cat"].currentData() == "customer"
        for k in ("cat", "role", "name", "tags"):
            w[k].setEnabled(new)
        w["ini"].setEnabled(new and cust); w["ty"].setEnabled(new and cust)
        if kind == "version":
            d = self.lib.doc(w["what"].currentData()[1])
            if d is not None:
                w["cat"].setCurrentIndex(max(0, w["cat"].findData(d.get("category", "customer"))))
                w["ini"].setText(d.get("initial", ""))
        self.show_count()

    def _cat_changed(self, r):
        w = self.rows[r]
        cat = w["cat"].currentData()
        cust = cat == "customer"
        w["role"].setCurrentIndex(max(0, w["role"].findData(DV.suggest_role(cat, w["ty"].currentText() if cust else ""))))
        if cust and not w["ini"].text().strip():
            taken = [x["ini"].text().strip().upper() for k, x in enumerate(self.rows) if k != r]
            w["ini"].setText(self.lib.suggest_initial(w["ty"].currentText(), taken))
        self._changed(r)

    def _type_changed(self, r):
        w = self.rows[r]
        if w["cat"].currentData() == "customer":
            w["role"].setCurrentIndex(max(0, w["role"].findData(DV.suggest_role("customer", w["ty"].currentText()))))
            e = self.plan[r]
            if not w["ini"].property("sk_typed"):
                taken = [x["ini"].text().strip().upper() for k, x in enumerate(self.rows) if k != r]
                e["initial"] = self.lib.suggest_initial(w["ty"].currentText(), taken)
                w["ini"].setText(e["initial"])

    def selected_rows(self):
        return sorted({ix.row() for ix in self.table.selectionModel().selectedRows()})

    def set_rows(self, category="", role="", skip=False, rows=None):
        """Set many rows at once (the selected ones)."""
        rows = self.selected_rows() if rows is None else rows
        for r in rows:
            w = self.rows[r]
            if skip:
                w["what"].setCurrentIndex(w["what"].count() - 1)
                continue
            if (w["what"].currentData() or ("",))[0] != "new":
                continue
            if category:
                w["cat"].setCurrentIndex(max(0, w["cat"].findData(category)))
            if role:
                w["role"].setCurrentIndex(max(0, w["role"].findData(role)))
        self.b_cat.setCurrentIndex(0); self.b_role.setCurrentIndex(0)
        self.show_count()
        return len(rows)

    def show_count(self):
        if not hasattr(self, "count"):
            return
        adding = sum(1 for w in self.rows if (w["what"].currentData() or ("skip",))[0] != "skip")
        self.count.setText(f"{adding} to add")

    def accept(self):
        problems = DI.check(self.lib, self.result_plan())
        if problems:
            self.problem.setText("Before adding: " + " ".join(problems[:6]) + (" ..." if len(problems) > 6 else ""))
            self.problem.show()
            return
        super().accept()

    def result_plan(self):
        for e, w in zip(self.plan, self.rows):
            choice, doc = w["what"].currentData()
            e["choice"], e["doc"] = choice, doc
            if w["cat"].currentData() != e.get("category"):       # a new category suggests its own role
                e["suggested_role"] = DV.suggest_role(w["cat"].currentData(), w["ty"].currentText() if w["cat"].currentData() == "customer" else "")
            e["category"] = w["cat"].currentData()
            e["role"] = w["role"].currentData()
            e["initial"] = DV.clean_initial(w["ini"].text()) if e["category"] == "customer" else ""
            e["type"] = w["ty"].currentText() if e["category"] == "customer" else ""
            e["name"] = w["name"].text().strip() or e.get("name", "")
            e["tags"] = DV.clean_tags([t for t in w["tags"].text().split(",")])
        return self.plan


# ====================================================================== the page
class LibraryPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.lib = None
        self.worker = None
        self.cat = "all"
        self.folder = ""
        self.setObjectName("page")
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = FlowLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.p_docs = D.Pill("0 documents", "accent"); self.p_und = D.Pill("every role confirmed", "ok")
        self.p_miss = D.Pill("every original here", "ok")
        for p in (self.p_docs, self.p_und, self.p_miss):
            top.addWidget(p)
        top.addStretch(1)
        self.b_taken = D.button("Taken from documents...", None, lambda: self.show_taken(),
                                "Every sentence taken from a library document in Assign, and what it is attached to (2.84.0)")
        top.addWidget(self.b_taken)
        self.b_cat = D.button("New category...", None, lambda: self.new_category(), "A category of your own (Competitor intel, Pricing...)")
        top.addWidget(self.b_cat)
        self.b_folder = D.button("Add a folder...", None, lambda: self.add_folder(), "Every document in a folder and its subfolders; the folder names become tags")
        top.addWidget(self.b_folder)
        self.b_watch = D.button("Watched folders...", None, lambda: self.host.watch_folders(),     # 2.94.0
                                "The folders checked for new, changed and missing files (Customer Documents always)")
        top.addWidget(self.b_watch)
        self.b_files = D.button("Add files...", "primary", lambda: self.add(), "Pick documents")
        top.addWidget(self.b_files)
        self.panel = TaskPanel(self.stop, host); v.addWidget(self.panel)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        # categories and folders
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Categories and folders", ""]); self.tree.setColumnWidth(0, 196)
        self.tree.setColumnWidth(1, 30)
        self.tree.setRootIsDecorated(True)
        self.tree.itemClicked.connect(lambda it, _c: self.pick_place(*it.data(0, Qt.UserRole)))
        split.addWidget(self.tree)
        # the documents
        mid = QWidget(); mv = QVBoxLayout(mid); mv.setContentsMargins(0, 0, 0, 0); mv.setSpacing(D.SPACE["s"])
        bar = QHBoxLayout(); mv.addLayout(bar)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search names, tags and the text of every document")
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.fill)
        self.search.textChanged.connect(lambda t: self.fill() if not t else None)
        bar.addWidget(self.search, 1)
        self.role_f = QComboBox(); self.role_f.addItem("Every role", "")
        for k, n in DV.ROLES:
            self.role_f.addItem(n, k)
        self.role_f.addItem("Role not confirmed", "undecided")
        self.role_f.currentIndexChanged.connect(lambda _i: self.fill())
        bar.addWidget(self.role_f)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Document", "Category", "Versions", "Tags", "Role", "Found"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        for c, wdt in enumerate((220, 135, 64, 150, 165)):
            self.table.setColumnWidth(c, wdt)
        self.table.itemSelectionChanged.connect(self.show_doc)
        mv.addWidget(self.table, 1)
        self.empty = D.EmptyState("No documents in the library yet", "Add a folder: every document in it and its subfolders "
                                  "comes in, sorted by category, with its folders as tags.", "Add a folder...", lambda: self.add_folder())
        mv.addWidget(self.empty)
        split.addWidget(mid)
        # the selected document
        self.side_area = QScrollArea(); self.side_area.setWidgetResizable(True); self.side_area.setMinimumWidth(330)
        side = QWidget(); self.side = QVBoxLayout(side); self.side.setAlignment(Qt.AlignTop); self.side.setSpacing(D.SPACE["s"])
        self.side_area.setWidget(side)
        self.d_name = D.label("Click a document", "title"); self.side.addWidget(self.d_name)
        self.d_info = D.label("", "muted"); self.side.addWidget(self.d_info)
        self.side.addWidget(D.label("Role", "label", wrap=False))
        rrow = QHBoxLayout(); rrow.setSpacing(4); self.side.addLayout(rrow)
        rrow2 = QHBoxLayout(); rrow2.setSpacing(4); self.side.addLayout(rrow2)
        self.role_btns = {}
        for i, (k, n) in enumerate(DV.ROLES):
            b = D.button(n, None, lambda _=False, k=k: self.set_role(k))
            b.setCheckable(True)
            (rrow if i < 2 else rrow2).addWidget(b)
            self.role_btns[k] = b
        self.why = QLineEdit(); self.why.setPlaceholderText("Why (optional): kept with who and when")
        self.side.addWidget(self.why)
        self.role_by = D.label("", "muted"); self.side.addWidget(self.role_by)
        self.side.addWidget(D.label("Category and folder", "label", wrap=False))
        crow = QHBoxLayout(); self.side.addLayout(crow)
        self.d_cat = QComboBox(); crow.addWidget(self.d_cat, 1)
        self.d_cat.activated.connect(lambda _i: self.set_category())
        self.d_folder = QLineEdit(); self.d_folder.setPlaceholderText("Folder (Standards/Test)")
        self.d_folder.editingFinished.connect(self.set_category)
        crow.addWidget(self.d_folder, 1)
        self.side.addWidget(D.label("Tags", "label", wrap=False))
        self.d_tags = QLineEdit(); self.d_tags.setPlaceholderText("Comma between tags")
        self.d_tags.editingFinished.connect(self.set_tags)
        self.side.addWidget(self.d_tags)
        idrow = QHBoxLayout(); self.side.addLayout(idrow)                  # 2.85.0: what Customer versions did
        self.b_ident = D.button("Initial and type...", None, lambda: self.identity(), "A customer document's initial and type")
        self.b_rename = D.button("Rename...", None, lambda: self.rename())
        idrow.addWidget(self.b_ident); idrow.addWidget(self.b_rename); idrow.addStretch(1)
        self.b_read = D.button("Read it in Assign", "primary", lambda: self.read_in_assign(),
                               "Open it beside your response structure: select text, then choose where it goes (2.84.0)")
        self.side.addWidget(self.b_read)
        self.d_taken = D.label("", "muted"); self.side.addWidget(self.d_taken)
        self.side.addWidget(D.label("Versions", "label", wrap=False))
        self.d_versions = QListWidget(); self.d_versions.setMaximumHeight(130); self.side.addWidget(self.d_versions)
        self.hits_lbl = D.label("Found in the text", "label", wrap=False); self.side.addWidget(self.hits_lbl)
        self.d_hits = QListWidget(); self.d_hits.setWordWrap(True); self.d_hits.setMaximumHeight(200); self.side.addWidget(self.d_hits)
        split.addWidget(self.side_area)
        split.setSizes([250, 820, 340])
        self.found = {}
        self.show_doc()
        self.setAcceptDrops(True)                   # drag folders or files from File Explorer onto the page

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self.lib is not None and not self.running():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        e.acceptProposedAction()
        self.add_dropped(paths)

    def add_dropped(self, paths, **kw):
        """Folders and files dropped together: every document in the folders (folder names as tags) and the files."""
        files, folders = [], {}
        for p in paths:
            if os.path.isdir(p):
                for f, rel in DI.walk(p):
                    files.append(f); folders[f] = rel
            elif os.path.isfile(p) and p.lower().endswith(DI.FILE_TYPES):
                files.append(p)
        if not files:
            self.host.status("No documents (Word, PDF, PowerPoint, Excel, text) in what was dropped.")
            return None
        return self.add(files, folders=folders, **kw)

    # ------------------------------------------------------------ fill
    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            self.lib = None
            self.tree.clear(); self.table.setRowCount(0)
            return
        self.lib = DV.Library(h.ws.p("documents")).load()
        self.fill_tree()
        self.fill()
        if hasattr(h, "watch_start"):
            h.watch_start()                         # 2.94.0: the watched folders, checked in the background

    def fill_tree(self):
        lib = self.lib
        self.tree.clear()
        counts = lib.counts_by_category()
        allit = QTreeWidgetItem(["All documents", str(len(lib.all))]); allit.setData(0, Qt.UserRole, ("all", ""))
        self.tree.addTopLevelItem(allit)
        for k, n in lib.categories():
            top = QTreeWidgetItem([n, str(counts.get(k, 0))]); top.setData(0, Qt.UserRole, (k, ""))
            top.setForeground(0, D.color(CAT_TONE.get(k, "text")))
            f = top.font(0); f.setBold(True); top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            nodes = {}
            for path in lib.folders(k):
                parent = nodes.get(path.rsplit("/", 1)[0]) if "/" in path else top
                it = QTreeWidgetItem([path.split("/")[-1], str(sum(1 for d in lib.in_category(k)
                                                                    if (d.get("folder") or "") == path or (d.get("folder") or "").startswith(path + "/")))])
                it.setData(0, Qt.UserRole, (k, path))
                (parent or top).addChild(it)
                nodes[path] = it
        self.tree.expandToDepth(0)
        und, miss = lib.undecided(), self.missing()
        self.p_docs.setText(f"{len(lib.all)} documents")
        self.p_und.setText(f"{len(und)} role(s) to confirm" if und else "every role confirmed"); self.p_und.set_tone("warn" if und else "ok")
        self.p_miss.setText(f"{len(miss)} original(s) not here" if miss else "every original here"); self.p_miss.set_tone("warn" if miss else "ok")

    def missing(self):
        return [d for d in self.lib.all if d["versions"] and not self.lib.has_original(d["versions"][-1])] if self.lib else []

    def pick_place(self, cat, folder=""):
        self.cat, self.folder = cat, folder
        self.fill()

    def shown(self):
        """The documents the category, folder, role filter and search leave, with what search found in each."""
        lib = self.lib
        docs = lib.all if self.cat == "all" else lib.in_category(self.cat)
        if self.folder:
            docs = [d for d in docs if (d.get("folder") or "") == self.folder or (d.get("folder") or "").startswith(self.folder + "/")]
        rf = self.role_f.currentData()
        if rf == "undecided":
            und = {d["id"] for d in lib.undecided()}
            docs = [d for d in docs if d["id"] in und]
        elif rf:
            docs = [d for d in docs if lib.role_of(d) == rf]
        q = self.search.text().strip()
        self.found = {}
        if q:
            res = lib.search(q, docs)
            self.found = {d["id"]: hits for d, hits in res}
            docs = [d for d, _h in res]
        return docs

    def fill(self):
        if self.lib is None:
            return
        docs = self.shown()
        keep = self.current_id()
        self.table.setRowCount(len(docs))
        for r, d in enumerate(docs):
            vs = d["versions"]
            name = d["name"] + (f" ({d['initial']})" if d.get("initial") else "")
            it = _item(name, d["id"], vs[-1].get("file", "") if vs else "")
            if d.get("withdrawn"):                                   # 2.94.0
                it.setText(name + "  (withdrawn)"); it.setForeground(D.color("muted"))
                it.setToolTip(f"Marked withdrawn {d['withdrawn'].get('when', '').replace('T', ' ')} by {d['withdrawn'].get('who', '')}: its file is gone")
            elif vs and vs[-1].get("missing_kept"):
                it.setText(name + "  (original missing)"); it.setForeground(D.color("warn"))
                it.setToolTip("Its file was removed; the record and its text were kept on purpose")
            elif vs and not self.lib.has_original(vs[-1]):
                it.setForeground(D.color("warn")); it.setToolTip("The original file is not here (left out of a package or moved). Its text and record are.")
            self.table.setItem(r, 0, it)
            ci = _item(self.lib.category_name(d.get("category", "customer"))); ci.setForeground(D.color(CAT_TONE.get(d.get("category"), "text")))
            self.table.setItem(r, 1, ci)
            self.table.setItem(r, 2, _item(str(len(vs))))
            self.table.setItem(r, 3, _item(", ".join(d.get("tags", []))))
            role = self.lib.role_of(d)
            sugg = (d.get("role_by") or {}).get("suggested", True)
            ri = _item(DV.ROLE_NAMES[role] + (" (suggested)" if sugg else ""))
            ri.setForeground(D.color(ROLE_TONE.get(role, "text")))
            self.table.setItem(r, 4, ri)
            hits = self.found.get(d["id"]) or []
            self.table.setItem(r, 5, _item(hits[0][1][:160] if hits else ("name or tags" if self.search.text().strip() else "")))
        self.empty.setVisible(not self.lib.all); self.table.setVisible(bool(self.lib.all))
        if keep:
            self.select(keep)
        self.show_doc()

    def current_id(self):
        r = self.table.currentRow()
        it = self.table.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it else None

    def selected_ids(self):
        rows = sorted({ix.row() for ix in self.table.selectionModel().selectedRows()})
        return [self.table.item(r, 0).data(Qt.UserRole) for r in rows if self.table.item(r, 0)]

    def select(self, doc_id):
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0) and self.table.item(r, 0).data(Qt.UserRole) == doc_id:
                self.table.selectRow(r)
                return True
        return False

    def show_doc(self):
        d = self.lib.doc(self.current_id()) if self.lib and self.current_id() else None
        many = len(self.selected_ids()) > 1 if self.lib else False
        for w in list(self.role_btns.values()) + [self.why, self.d_cat, self.d_folder, self.d_tags]:
            w.setEnabled(d is not None)
        if d is None:
            self.d_name.setText("Click a document"); self.d_info.setText("Its role, category, folder, tags and versions show here.")
            self.role_by.setText(""); self.d_versions.clear(); self.d_hits.clear()
            for b in self.role_btns.values():
                b.setChecked(False)
            self.hits_lbl.hide(); self.d_hits.hide()
            return
        lib = self.lib
        self.d_name.setText(d["name"] + (f"  ({len(self.selected_ids())} selected: the role applies to all)" if many else ""))
        bits = [lib.category_name(d.get("category", "customer"))]
        if d.get("initial"):
            bits.append(f"{d['initial']}, {d.get('type', '')}")
        if d.get("folder"):
            bits.append(d["folder"])
        self.d_info.setText("  ·  ".join(bits))
        role = lib.role_of(d)
        for k, b in self.role_btns.items():
            b.setChecked(k == role)
            b.setProperty("kind", "primary" if k == role else None); b.style().unpolish(b); b.style().polish(b)
        rb = d.get("role_by") or {}
        self.role_by.setText("Suggested from its category and type: confirm it or pick another." if rb.get("suggested", True) else
                             f"Set by {rb.get('who', '')} on {rb.get('when', '')[:10]}" + (f": {rb['why']}" if rb.get("why") else ""))
        self.d_cat.blockSignals(True); self.d_cat.clear()
        for k, n in lib.categories():
            self.d_cat.addItem(n, k)
        self.d_cat.setCurrentIndex(max(0, self.d_cat.findData(d.get("category", "customer")))); self.d_cat.blockSignals(False)
        self.d_folder.setText(d.get("folder", "")); self.d_tags.setText(", ".join(d.get("tags", [])))
        try:
            import ctxdocs as CX
            nt = len(CX.Store(self.host.ws.root).load().of_doc(d["id"]))
        except Exception:
            nt = 0
        self.d_taken.setText(f"{nt} sentence(s) taken from it" if nt else "Nothing taken from it yet.")
        self.b_read.setEnabled(self.lib.role_of(d) != "not_needed")
        self.b_ident.setVisible(d.get("category", "customer") == "customer")
        self.d_versions.clear()
        for i, ver in enumerate(reversed(d["versions"])):
            here = lib.has_original(ver)
            txt = f"{ver['label']}  ·  {ver.get('file', '')}  ·  {ver.get('added', '')[:10]}"
            if i:
                txt += "  (superseded)"
            if not here:
                txt += "  (original not here)"
            self.d_versions.addItem(txt)
        hits = self.found.get(d["id"]) or []
        self.d_hits.clear()
        for _i, x in hits:
            self.d_hits.addItem(QListWidgetItem(x))
        self.hits_lbl.setVisible(bool(hits)); self.d_hits.setVisible(bool(hits))

    # ------------------------------------------------------------ decisions
    def set_role(self, role, why=None, ids=None):
        ids = ids or self.selected_ids()
        if not ids or self.lib is None:
            return 0
        why = self.why.text() if why is None else why
        n = sum(1 for i in ids if self.lib.set_role(i, role, why))
        diag.activity("library_role_set", n=n)
        self.why.clear()
        self.host.toast(f"{n} document(s): {DV.ROLE_NAMES[role]}")
        self.fill_tree(); self.fill()
        return n

    def set_category(self, key=None, folder=None):
        d = self.lib.doc(self.current_id()) if self.lib and self.current_id() else None
        if d is None:
            return False
        key = key or self.d_cat.currentData()
        folder = self.d_folder.text() if folder is None else folder
        if key == d.get("category") and (folder or "").strip("/\\") == d.get("folder", ""):
            return False
        ok = self.lib.set_category(d["id"], key, folder)
        if ok:
            diag.activity("library_category_set")
            self.fill_tree(); self.fill()
        return ok

    def set_tags(self, text=None):
        d = self.lib.doc(self.current_id()) if self.lib and self.current_id() else None
        if d is None:
            return False
        text = self.d_tags.text() if text is None else text
        tags = DV.clean_tags(text.split(","))
        if tags == d.get("tags", []):
            return False
        self.lib.set_tags(d["id"], tags)
        self.fill()
        return True

    def new_category(self, name=None):
        if self.lib is None:
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "New category", "Name of the category (Competitor intel, Pricing...)")
            if not ok:
                return None
        key = self.lib.add_category(name)
        if key:
            diag.activity("library_category_added")
            self.fill_tree()
        return key

    def identity(self, initial=None, dtype=None):
        """A customer document's initial and type (what Customer versions did)."""
        did = self.current_id()
        if not did:
            return None
        dp = self.host.docs_page
        dp.refresh()
        why = dp.identity(initial, dtype, doc_id=did)
        self.refresh(); self.select(did)
        return why

    def rename(self, name=None):
        did = self.current_id()
        if not did or self.lib is None:
            return False
        d = self.lib.doc(did)
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename", "Name of the document:", text=d["name"])
            if not ok:
                return False
        ok = self.lib.rename(doc_id=did, name=name)
        if ok:
            self.refresh(); self.select(did)
        return ok

    def read_in_assign(self, doc_id=None):
        """2.84.0: open the document in Assign, beside the response structure."""
        doc_id = doc_id or self.current_id()
        h = self.host
        if not doc_id or h.ws is None:
            return False
        if h.review is None:
            h.status("Read RFP first: Assign reads library documents beside the response structure of the matrix.")
            return False
        h.go("assign")
        ap = h.assign_page
        ap.load_files_keep()
        lab = next((k for k, did in ap.lib_entries.items() if did == doc_id), None)
        if lab is None:
            d = self.lib.doc(doc_id) if self.lib else None
            if d is not None and d["versions"] and d["versions"][-1].get("file") in h.review.files():
                ap.files.setCurrentText(d["versions"][-1]["file"])
                return True
            h.status("That document builds the matrix: it is read in Read RFP.")
            return False
        ap.files.setCurrentText(lab)
        return True

    def show_taken(self, run=True):
        if self.host.ws is None:
            return None
        dlg = TakenDialog(self)
        if run:
            dlg.exec()
        return dlg

    # ------------------------------------------------------------ bringing documents in
    def running(self):
        return self.worker is not None

    def lock(self, busy):
        """While documents are read or added, nothing else changes the library (the job writes it)."""
        for b in (self.b_folder, self.b_files, self.b_cat, self.side_area):
            b.setEnabled(not busy)

    def stop(self):
        if self.worker is not None:
            self.worker.stop_asked = True

    def add_folder(self, folder=None, watch=None, **kw):
        """Every document in a folder and its subfolders; (2.94.0) and keep watching it for new, changed and missing files
        (asked; watch (tests): True or False)."""
        if self.lib is None:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Add every document in a folder (and its subfolders)")
            if not folder:
                return None
        if watch is None:
            watch = QMessageBox.question(self, "Keep watching?", "Keep watching this folder? New files in it (or in the folders "
                                         "inside it) are offered to add, changed files as new versions, and a document whose "
                                         "file is removed is reported.", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes
        if watch:
            import watch as WA
            if WA.add_folder(self.host.ws.root, folder, kw.get("category") or ""):
                diag.activity("qt_watch_folder_added")
        found = DI.walk(folder)
        if not found:
            self.host.status("No documents (Word, PDF, PowerPoint, Excel, text) in that folder.")
            return None
        return self.add([p for p, _r in found], folders=dict(found), **kw)

    def add(self, paths=None, folders=None, category=None, choices=None, reader=None):
        """Read the files in the background (progress, Stop), then the review table, then add them (also in the
        background). choices (tests): {file name: changes} applied instead of the table; returns the worker."""
        if self.lib is None or self.running():
            if self.running():
                self.host.status("Documents are being read: wait for it, or press Stop.")
            return None
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Add documents to the library", "", "Documents (*.docx *.pdf *.pptx *.xlsx *.txt)")
        if not paths:
            return None
        lib, rd = self.lib, reader or DI.read
        self._choices = choices
        self.worker = JobWorker(lambda prog, stop: DI.plan(lib, list(paths), rd, prog, stop, folders, category))
        self.worker.progress.connect(self.panel.step)
        self.worker.done.connect(self._planned)
        self.panel.start(f"Reading {len(paths)} document(s)", "Getting ready")
        self.lock(True)
        diag.activity("library_intake_started", files=len(paths))
        self.worker.start()
        return self.worker

    def _planned(self, res):
        self.worker = None
        if isinstance(res, DI.Stopped):
            self.lock(False)
            self.panel.stopped("Reading stopped", "You pressed Stop. Nothing was added.", "Add them again when you are ready.")
            return
        if isinstance(res, Exception):
            self.lock(False)
            self.panel.failed("The documents could not be read", f"Reading stopped with an error ({type(res).__name__}). Nothing was added.",
                              "Try fewer files, or Help > Create a support file and send it in.")
            return
        plan = res
        choices = getattr(self, "_choices", None)
        if choices is None:
            self.panel.done("Read", f"{len(plan)} file(s) read. Check them in the table.")
            dlg = IntakeDialog(self, plan, self.lib)
            if dlg.exec() != QDialog.Accepted:
                self.lock(False)
                self.panel.stopped("Nothing added", "You closed the table without adding.", "")
                return
            plan = dlg.result_plan()
        else:
            for e in plan:
                e.update(choices.get(os.path.basename(e["path"]), {}))
            problems = DI.check(self.lib, plan)
            if problems:
                self.lock(False)
                self.panel.failed("Not added", " ".join(problems[:4]), "Fix them in the table and Add again.")
                return
        folder, cd = self.lib.folder, self._customer_dir()
        lines = []

        def job(prog, stop):
            lib = DV.Library(folder).load()               # the job's own copy; the page reloads when it ends
            return DI.apply(lib, plan, cd, lambda k, t, ref=None: lines.append((k, t, ref)), prog)
        self.worker = JobWorker(job)
        self.worker.progress.connect(self.panel.step)
        self.worker.done.connect(lambda made, lines=lines: self._added(made, lines))
        self.panel.start(f"Adding {sum(1 for e in plan if not (e.get('dup') or e['choice'] == 'skip'))} document(s)", "Copying into the effort")
        self.worker.start()

    def _added(self, made, lines):
        self.worker = None
        self.lock(False)
        self._log_lines(lines)
        if isinstance(made, Exception):
            self.panel.failed("Adding stopped", f"An error stopped it ({type(made).__name__}). What was added before it is kept.",
                              "Add the rest again: files already added are recognized and skipped.")
            self.refresh()
            return
        by = {}
        for d, _v in made:
            by[d.get("category", "customer")] = by.get(d.get("category", "customer"), 0) + 1
        text = ", ".join(f"{n} to {self.lib.category_name(c)}" for c, n in by.items()) or "nothing new"
        diag.activity("library_intake_done", n=len(made))
        self.panel.done("Added", f"{len(made)} document version(s) added: {text}.")
        self.host.toast(f"{len(made)} added to the library")
        self.refresh()
        if made:
            self.select(made[-1][0]["id"])

    def _customer_dir(self):
        return (self.host.efforts.get(self.host.effort_name) or {}).get("customer_dir", "") or ""

    def _log_lines(self, lines):
        """The paper trail, written on the window's thread once the job ends."""
        if not lines or self.host.ws is None:
            return
        try:
            import effortrec as R
            rec = R.Record(self.host.ws.root)
            for k, t, ref in lines:
                rec.log(k, t, ref=ref)
            rec.save()
        except Exception:
            diag.swallowed()


# ====================================================================== what was taken from the library (2.84.0)
class TakenDialog(QDialog):
    """Every sentence taken from a library document, and what it is attached to: filter by kind, document, section
    or topic, search the words, export it all for writers, or open one in Assign."""

    def __init__(self, page):
        super().__init__(page)
        import ctxdocs as CX
        self.page, self.CX = page, CX
        self.setWindowTitle("Taken from the library"); self.resize(1180, 640)
        self.lib = DV.Library(page.host.ws.p("documents")).load()
        self.store = CX.Store(page.host.ws.root).load()
        v = QVBoxLayout(self)
        bar = QHBoxLayout(); v.addLayout(bar)
        self.kind = QComboBox(); self.kind.addItem("Everything", "")
        for k, n in CX.KINDS:
            self.kind.addItem(n, k)
        self.doc = QComboBox(); self.doc.addItem("Every document", "")
        for d in sorted({a["doc"] for a in self.store.att}, key=lambda i: (self.lib.doc(i) or {}).get("name", "")):
            self.doc.addItem((self.lib.doc(d) or {}).get("name", d), d)
        self.topic = QComboBox(); self.topic.addItem("Every topic", "")
        for t in sorted({t for a in self.store.att for t in a.get("topics", [])}, key=str.lower):
            self.topic.addItem(t, t)
        self.q = QLineEdit(); self.q.setPlaceholderText("Words in the text or the note")
        for w in (self.kind, self.doc, self.topic):
            w.currentIndexChanged.connect(lambda _i: self.fill()); bar.addWidget(w)
        self.q.textChanged.connect(lambda _t: self.fill()); bar.addWidget(self.q, 1)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Attached as", "To", "Text", "Document", "Where", "Topics"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for c, wdt in ((0, 160), (1, 170), (3, 190), (4, 150), (5, 140)):
            self.table.setColumnWidth(c, wdt)
        self.table.itemDoubleClicked.connect(lambda _i: self.open_selected())
        v.addWidget(self.table, 1)
        row = QHBoxLayout(); v.addLayout(row)
        self.count = D.label("", "muted", wrap=False); row.addWidget(self.count); row.addStretch(1)
        row.addWidget(D.button("Open in Assign", None, lambda: self.open_selected(), "Show the sentence on its page"))
        row.addWidget(D.button("Export to Excel...", "primary", lambda: self.export(), "Every row, for writers"))
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); row.addWidget(bb)
        self.fill()

    def fill(self):
        rows = self.store.rows(self.lib, self.kind.currentData(), self.doc.currentData(), "", self.topic.currentData(), self.q.text())
        self.rows = rows
        self.table.setRowCount(len(rows))
        for r, a in enumerate(rows):
            for c, val in enumerate((a["kind_name"], a.get("target", ""), a["text"], a["doc_name"], a.get("loc", ""), ", ".join(a.get("topics", [])))):
                self.table.setItem(r, c, _item(val, a["id"] if c == 0 else None, a["text"] if c == 2 else ""))
        self.count.setText(f"{len(rows)} of {len(self.store.att)}")
        return len(rows)

    def open_selected(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self.rows):
            return False
        a = self.rows[r]
        h = self.page.host
        ap = h.assign_page
        h.go("assign")
        lab = next((k for k, did in ap.lib_entries.items() if did == a["doc"]), None)
        if lab is None:
            h.status("That document is not offered in Assign (its role is Not needed, or it builds the matrix).")
            return False
        ap.files.setCurrentText(lab)
        ap.select(a["iid"])
        self.accept()
        return True

    def export(self, path=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export what was taken from the library", EF.out(self.host.effort_path, "Taken_from_the_library.xlsx"), "Excel (*.xlsx)")
            if not path:
                return None
        try:
            self.store.export_xlsx(path, self.lib)
        except PermissionError:
            self.page.host.status("That file is open in Excel: close it, then export again.")
            return None
        diag.activity("library_taken_exported", n=len(self.store.att))
        self.page.host.toast("Exported")
        return path
