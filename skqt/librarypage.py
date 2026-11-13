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
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox, QListWidgetItem, QScrollArea,
                               QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import docintake as DI
import docversions as DV
from . import design as D
from . import progress as PR
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
        v.addWidget(D.label(f"{new} new file(s), {len(plan) - new} already here. Each file's source comes from the folders "
                            "it was in; what it is used for from its source and type; a match to a document already here makes it a "
                            "new version. Change anything, for one row or many (select rows, then Source or Used for), then Add. Customer "
                            "documents need an initial and a type (the initial starts each requirement's reference).", "muted"))
        bulk = QHBoxLayout(); v.addLayout(bulk)
        bulk.addWidget(D.label("Selected rows:", "label", wrap=False))
        self.b_cat = QComboBox(); self.b_cat.addItem("Source...", "")       # 4.25.2: Source and Used for, for many rows at once
        for k, _n in lib.categories():
            self.b_cat.addItem(DV.source_name(lib, k), k)
        self.b_cat.activated.connect(lambda _i: self.set_rows(category=self.b_cat.currentData()))
        bulk.addWidget(self.b_cat)
        self.b_role = QComboBox(); self.b_role.addItem("Used for...", "")
        for k, n in DV.USES:
            self.b_role.addItem(n, k)
        self.b_role.activated.connect(lambda _i: self.set_rows(role=self.b_role.currentData()))
        bulk.addWidget(self.b_role)
        bulk.addWidget(D.button("Skip them", None, lambda: self.set_rows(skip=True)))
        bulk.addWidget(D.button("Select all", "ghost", lambda: self.table.selectAll()))
        bulk.addStretch(1)
        self.count = D.label("", "muted", wrap=False); bulk.addWidget(self.count)
        cols = ["File", "From folder", "What it is", "Source", "Used for", "Initial", "Type", "Name", "Tags"]
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
                how = "  (the same text)" if e.get("dup_how") else ""
                what.addItem(f"Already here: {e['dup'][0]['name']}{how}", ("skip", None))
                if e.get("dup_how") and e["dup"][0].get("id"):            # 3.15.1: same words, other bytes: add only if asked
                    what.addItem(f"Add it anyway as a new version of {e['dup'][0]['name']}", ("version", e["dup"][0]["id"]))
            else:
                what.addItem("A new document", ("new", None))
                if e.get("replace_of"):                    # 4.17.0: read before from this very file
                    rd = lib.doc(e["replace_of"])
                    if rd is not None:
                        what.addItem(f"The same document, edited: replace the file of {rd['name']}", ("replace", rd["id"]))
                for d, _sc, how in e.get("cands", [])[:6]:
                    what.addItem(f"A new version of {d['name']}  ({how})", ("version", d["id"]))
                what.addItem("Skip it", ("skip", None))
                if e["choice"] in ("version", "replace") and e.get("doc"):
                    what.setCurrentIndex(max(0, next((k for k in range(what.count()) if what.itemData(k) == (e["choice"], e["doc"])), 0)))
            cat = QComboBox()
            for k, _n in lib.categories():
                cat.addItem(DV.source_name(lib, k), k)
            cat.setCurrentIndex(max(0, cat.findData(e.get("category", "customer"))))
            role = QComboBox()
            for k, n in DV.USES:
                role.addItem(n, k)
            role.setCurrentIndex(max(0, role.findData(DV.use_key(e.get("role") or "matrix"))))
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
        w["role"].setCurrentIndex(max(0, w["role"].findData(DV.use_key(DV.suggest_role(cat, w["ty"].currentText() if cust else "")))))
        if cust and not w["ini"].text().strip():
            taken = [x["ini"].text().strip() for k, x in enumerate(self.rows) if k != r]
            w["ini"].setText(self.lib.suggest_initial(w["ty"].currentText(), taken))
        self._changed(r)

    def _type_changed(self, r):
        w = self.rows[r]
        if w["cat"].currentData() == "customer":
            w["role"].setCurrentIndex(max(0, w["role"].findData(DV.use_key(DV.suggest_role("customer", w["ty"].currentText())))))
            e = self.plan[r]
            if not w["ini"].property("sk_typed"):
                taken = [x["ini"].text().strip() for k, x in enumerate(self.rows) if k != r]
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
                w["role"].setCurrentIndex(max(0, w["role"].findData(DV.use_key(role))))
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
            if e.get("dup_how") and choice == "version":                 # 3.15.1: the person chose to add it anyway
                e["dup"] = None
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
    def __init__(self, host, side="all"):
        super().__init__()
        self.doc_side = side                         # 4.25.0: all, customer or ours (the chips; docfocus)
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
        top.addWidget(self.p_docs)
        for p in (self.p_und, self.p_miss):            # 3.20.3: shown only when something needs you (roles to confirm,
            top.addWidget(p); p.setVisible(False)       # originals missing), never as green chatter
        top.addStretch(1)
        self.b_taken = D.button("Library text used in the shred...", None, lambda: self.show_taken(),
                                "Every piece you took from a library document in the shred (as context for a section, a "
                                "requirement's context, a note, a task) and where it went: a list to check and export for writers")
        self.b_taken.setVisible(False)                  # 3.20.3: in the document's panel and its right-click menu instead
        self.b_cat = D.button("+ Category...", "ghost", lambda: self.new_category(), "A category of your own (Competitor intel, Pricing...)")
        self.b_folder = D.button("Add a folder...", None, lambda: self.add_folder(), "Bring in every document in a folder on this "
                                 "PC and its subfolders (the folder names become tags). Watched folders... is for folders checked "
                                 "for new files.")
        from .commandbar import CommandBar                   # 3.78.0: the Effort Library's one bar (Rule 8)
        self.bar = CommandBar()
        self._b_folder_old = self.b_folder
        self.b_folder = self.bar.add("Add a folder...", lambda: self.add_folder(), self._b_folder_old.toolTip())
        self.b_watch = self.bar.add("Watched folders...", lambda: self.host.watch_folders(),     # 2.94.0
                                    "The folders checked for new, changed and missing files (Customer Documents always)")
        self.bar.add("New folder...", lambda: self.new_folder(), "A folder in the selected category's folder on disk")
        self.b_files = self.bar.primary("Add files...", lambda: self.add(), "Pick documents")
        self.bar.more("Open the Library folder", lambda: self.open_folder(), "The effort's Library folder in File Explorer")
        self.bar.more("Move kept files into the Library folders...", lambda: self.move_into_folders(),
                      "Files an older version kept in the app's working folder move into the Library's real folders")
        self.bar.more_sep()
        self.bar.more("Add from another copy...", lambda: __import__("skqt.mergedialog", fromlist=["x"]).add_to_effort(self.host, self.host.effort_name),   # 3.70.0
                      "Merge another copy of this effort: its documents, acronyms, volumes and record")
        self.bar.more("+ Category...", lambda: self.new_category(), "A category of your own (Competitor intel, Pricing...)")
        self.bar.more("Trash...", lambda: __import__("skqt.docmanage", fromlist=["x"]).show_trash(self),   # 4.17.0
                      "What was deleted or replaced here, with Restore")
        top.addWidget(self.bar)
        self._b_folder_old.setVisible(False)
        self.panel = TaskPanel(self.stop, host); v.addWidget(self.panel)
        self.new_box = QFrame(); self.new_box.setObjectName("newfiles"); self.new_box.setProperty("card", True)   # 3.16.0
        nb = QHBoxLayout(self.new_box); nb.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["s"]); nb.setSpacing(D.SPACE["m"])
        self.new_lbl = D.label("", "body"); nb.addWidget(self.new_lbl, 1)
        self.b_new_add = D.button("Add to Documents...", "primary", lambda: self.host.watch_add(),
                                  "Look at the new and changed files in a table, then add them (a changed file is a new version)")
        self.b_new_skip = D.button("Ignore", None, lambda: self.host.watch_set_aside(), "Do not offer these files again unless they change")
        nb.addWidget(self.b_new_add); nb.addWidget(self.b_new_skip)
        self.new_box.setVisible(False); v.addWidget(self.new_box)
        from .libfolders import kept_banner                  # 3.81.0: an older effort's kept files, one line
        kept_banner(self, v)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        # categories and folders
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Categories and folders", ""]); self.tree.setColumnWidth(0, 196)
        self.tree.setColumnWidth(1, 30)
        self.tree.setRootIsDecorated(True)
        self.tree.itemClicked.connect(lambda it, _c: self.pick_place(*it.data(0, Qt.UserRole)))
        lcol = QWidget(); lv = QVBoxLayout(lcol); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(D.SPACE["xs"])   # 3.20.3
        lv.addWidget(self.tree, 1); self.b_cat.setVisible(False)                                       # 3.78.0: in More
        split.addWidget(lcol)
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
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Document", "Shred", "Category", "Versions", "Tags", "Role", "Found"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        for c, wdt in enumerate((220, 200, 125, 64, 130, 150)):
            self.table.setColumnWidth(c, wdt)
        self.table.itemSelectionChanged.connect(self.show_doc)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)          # 3.20.3: a document's menu on right-click
        self.table.customContextMenuRequested.connect(lambda pos: __import__("skqt.docstatus", fromlist=["x"]).row_menu(
            self, self.table.viewport().mapToGlobal(pos)))                 # 4.0.0: five things about the file
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
        # 3.16.0: reviewing it comes first: where its review stands and the one button that moves it on
        self.rv_box = QFrame(); self.rv_box.setObjectName("reviewbox"); self.rv_box.setProperty("card", True)
        rvl = QVBoxLayout(self.rv_box); rvl.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["m"]); rvl.setSpacing(D.SPACE["s"])
        rvl.addWidget(D.label("What has been done", "label", wrap=False))   # 4.0.0: the status panel (docstatus)
        self.rv_state = D.label("", "title"); rvl.addWidget(self.rv_state); self.rv_state.setVisible(False)
        self.st_lines = QVBoxLayout(); self.st_lines.setSpacing(6); rvl.addLayout(self.st_lines)
        self.b_read = D.button("Extract it", "primary", lambda: self.review_selected(), "This document's next thing")
        rvl.addWidget(self.b_read)
        self.b_more = D.button("More about this document...", "ghost", lambda: self.doc_menu(self.b_more.mapToGlobal(
            self.b_more.rect().bottomLeft())), "Role, folder, tags, its name, where it is filed, its instructions, where its text went")
        rvl.addWidget(self.b_more)
        self.d_taken = D.label("", "muted"); rvl.addWidget(self.d_taken)
        self.b_taken2 = D.button("See where its text went...", "ghost", lambda: self.show_taken(),
                                 "The pieces taken from library documents in the shred, and what each is attached to")
        rvl.addWidget(self.b_taken2)
        self.side.addWidget(self.rv_box)
        self._side_labels = []
        lab = D.label("Role", "label", wrap=False); self._side_labels.append(lab); self.side.addWidget(lab)
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
        lab = D.label("Category and folder", "label", wrap=False); self._side_labels.append(lab); self.side.addWidget(lab)
        crow = QHBoxLayout(); self.side.addLayout(crow)
        self.d_cat = QComboBox(); crow.addWidget(self.d_cat, 1)
        self.d_cat.activated.connect(lambda _i: self.set_category())
        self.d_folder = QLineEdit(); self.d_folder.setPlaceholderText("Folder (Standards/Test)")
        self.d_folder.editingFinished.connect(self.set_category)
        crow.addWidget(self.d_folder, 1)
        lab = D.label("Tags", "label", wrap=False); self._side_labels.append(lab); self.side.addWidget(lab)
        self.d_tags = QLineEdit(); self.d_tags.setPlaceholderText("Comma between tags")
        self.d_tags.editingFinished.connect(self.set_tags)
        self.side.addWidget(self.d_tags)
        idrow = QHBoxLayout(); self.side.addLayout(idrow)                  # 2.85.0: what Customer versions did
        self.b_ident = D.button("Initial and type...", None, lambda: self.identity(), "A customer document's initial and type")
        self.b_rename = D.button("Rename...", None, lambda: self.rename())
        idrow.addWidget(self.b_ident); idrow.addWidget(self.b_rename); idrow.addStretch(1)
        urow = QHBoxLayout(); self.side.addLayout(urow)                    # task and delivery orders under their base
        lab = D.label("Filed under", "label", wrap=False); self._side_labels.append(lab); urow.addWidget(lab)
        self.d_under = QComboBox(); self.d_under.activated.connect(lambda _i: self.set_under()); urow.addWidget(self.d_under, 1)
        self.b_conform = D.button("Apply its instructions...", None, lambda: self.conform(),
                                  "An amendment that says what to change (delete and insert, replace a paragraph): apply it to "
                                  "the base document to get the conformed version")
        self.side.addWidget(self.b_conform)
        self.side.addWidget(D.label("Versions", "label", wrap=False))
        __import__("skqt.docmanage", fromlist=["x"]).install(self)          # 4.17.0: Undo of a delete, a version's right-click
        self.d_versions = QListWidget(); self.d_versions.setMaximumHeight(130); self.side.addWidget(self.d_versions)
        self.hits_lbl = D.label("Found in the text", "label", wrap=False); self.side.addWidget(self.hits_lbl)
        self.d_hits = QListWidget(); self.d_hits.setWordWrap(True); self.d_hits.setMaximumHeight(200); self.side.addWidget(self.d_hits)
        self.side.addWidget(D.label("Right-click a document to open it, set its type, add a newer version, leave it out or "
                                    "show it in its folder.", "muted"))
        for wdg in [self.why, self.role_by, self.d_cat, self.d_folder, self.d_tags, self.b_ident, self.b_rename, self.d_under,
                    *self.role_btns.values()] + self._side_labels:     # 3.20.3: the same choices, in the menu instead
            wdg.setVisible(False)
        split.addWidget(self.side_area)
        split.setSizes([250, 820, 340])
        self.found = {}
        from . import docfocus as DF                 # 4.6.0: Customer and Ours, the progress chips, one panel
        DF.install(self, self.doc_side)
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
        __import__("skqt.docfocus", fromlist=["x"]).fill_types(self)
        self.fill()
        from .libfolders import kept_refresh
        kept_refresh(self)
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
            top.setIcon(0, D.dot_icon(D.color(CAT_TONE.get(k, "text"))))      # 3.15.0: a dot marks the category
            f = top.font(0); f.setWeight(QFont.DemiBold); top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            nodes = {}
            import effortlib as EL                  # 3.78.0: the folders on disk too, so an empty one shows
            paths = sorted(set(lib.folders(k)) | set(EL.disk_folders(lib, k) if k != "customer" else []), key=str.lower)
            for path in paths:
                parent = nodes.get(path.rsplit("/", 1)[0]) if "/" in path else top
                it = QTreeWidgetItem([path.split("/")[-1], str(sum(1 for d in lib.in_category(k)
                                                                    if (d.get("folder") or "") == path or (d.get("folder") or "").startswith(path + "/")))])
                it.setData(0, Qt.UserRole, (k, path))
                (parent or top).addChild(it)
                nodes[path] = it
        self.tree.expandToDepth(0)
        und, miss = lib.undecided(), self.missing()
        n_docs = len([d for d in lib.all if __import__("skqt.docfocus", fromlist=["x"]).in_side(self, d)]) \
            if getattr(self, "focus", False) else len(lib.all)                 # 4.6.0: this tab's documents
        self.p_docs.setText(f"{n_docs} document" + ("" if n_docs == 1 else "s"))
        self.p_und.setText(f"{len(und)} role(s) to confirm" if und else "every role confirmed"); self.p_und.set_tone("warn" if und else "ok")
        self.p_miss.setText(f"{len(miss)} original(s) not here" if miss else "every original here"); self.p_miss.set_tone("warn" if miss else "ok")
        # 4.23.3 (Nicholas 2026-11-12 17:25): "N role(s) to confirm" is off the page. It counted the documents whose role
        # (Builds the matrix, Context, Reference only) the program had suggested and nobody had confirmed; the Role column
        # still shows a suggested role, and the Dashboard's tile still counts them.
        self.p_und.setVisible(False); self.p_miss.setVisible(bool(miss))

    def missing(self):
        return [d for d in self.lib.all if d["versions"] and not self.lib.has_original(d["versions"][-1])] if self.lib else []

    def pick_place(self, cat, folder=""):
        self.cat, self.folder = cat, folder
        self.fill()

    def shown(self):
        """The documents the category, folder, role filter and search leave, with what search found in each."""
        lib = self.lib
        docs = lib.all if self.cat == "all" else lib.in_category(self.cat)
        if getattr(self, "focus", False):                                  # 4.6.0: this tab's documents
            docs = __import__("skqt.docfocus", fromlist=["x"]).shown(self, lib.all)
        elif self.folder:
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
        docs = under_parents(self.shown())
        keep = self.current_id()
        st = self.review_states()
        from . import docfocus as DF
        focused = DF.fill(self, docs, _item)
        if not focused:
            self.table.setRowCount(len(docs))
        for r, d in enumerate([] if focused else docs):
            vs = d["versions"]
            name = ("\u21b3 " if d.get("under") and any(x["id"] == d["under"] for x in docs) else "") + d["name"] \
                + (f" ({d['initial']})" if d.get("initial") else "")
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
            rtext, rtone, _rk = self.review_state(d, st)                 # 3.16.0: where its review stands, in color
            rv = _item(rtext); rv.setForeground(D.color(rtone)); rv.setIcon(D.dot_icon(D.color(rtone)))
            if rtone in ("warn", "ok"):
                f0 = rv.font(); f0.setWeight(QFont.DemiBold); rv.setFont(f0)
            self.table.setItem(r, 1, rv)
            ci = _item(self.lib.category_name(d.get("category", "customer"))); ci.setIcon(D.dot_icon(D.color(CAT_TONE.get(d.get("category"), "text"))))
            self.table.setItem(r, 2, ci)
            self.table.setItem(r, 3, _item(str(len(vs))))
            self.table.setItem(r, 4, _item(", ".join(d.get("tags", []))))
            role = self.lib.role_of(d)
            sugg = (d.get("role_by") or {}).get("suggested", True)
            ri = _item(DV.ROLE_NAMES[role] + (" (suggested)" if sugg else ""))
            ri.setIcon(D.dot_icon(D.color(ROLE_TONE.get(role, "text"))))
            self.table.setItem(r, 5, ri)
            hits = self.found.get(d["id"]) or []
            self.table.setItem(r, 6, _item(hits[0][1][:160] if hits else ("name or tags" if self.search.text().strip() else "")))
        here = [d for d in self.lib.all if DF.in_side(self, d)] if focused else self.lib.all
        self.empty.setVisible(not here); self.table.setVisible(bool(here))
        if keep:
            self.select(keep)
        self.show_doc()

    def set_under(self, base_id=None):
        """A task or delivery order filed under its contract or RFP (or taken out)."""
        d = self.lib.doc(self.current_id()) if self.lib and self.current_id() else None
        if d is None:
            return False
        base_id = self.d_under.currentData() if base_id is None else base_id
        ok = self.lib.set_under(d["id"], base_id or "")
        if not ok:
            self.host.status("Not filed there: a document cannot be under itself or one of its own.")
        else:
            diag.activity("library_filed_under")
            self.fill()
            self.select(d["id"])
        return ok

    def conform(self, base_id=None, pick=None, answer=None):
        """Apply an amendment's instructions to its base document. answer (tests): skip the dialog (True to make it)."""
        import amendinst as AI
        d = self.lib.doc(self.current_id()) if self.lib and self.current_id() else None
        if d is None:
            return None
        ins = AI.instructions_of(self.lib, d["versions"][-1])
        if not ins:
            self.host.status(f"{d['name']} holds no change instructions (delete and insert, replace a paragraph...). "
                             "When an amendment reissues the document, add it as a new version instead.")
            return None
        if base_id is None:
            base = self.lib.base_for_orders() or next((x for x in self.lib.docs if x["id"] != d["id"]), None)
            base_id = base["id"] if base else None
        if answer is None:
            dlg = ConformDialog(self, self.lib, d, ins, base_id)
            if dlg.exec() != QDialog.Accepted:
                return None
            base_id, pick = dlg.values()
        base = self.lib.doc(base_id) if base_id else None
        if base is None:
            self.host.status("Pick the document the amendment changes.")
            return None
        dd, v, res = AI.conform(self.lib, d, base, pick)
        self.last_conform = res
        if v is None:
            self.host.status("None of the instructions could be applied: " + "; ".join(r["why"] for r in res if r["why"])[:300])
            return None
        diag.activity("amendment_conformed", n=sum(1 for r in res if r["status"] == "applied"))
        self.host.toast(f"{base['name']}: {v['label']} added. {AI.summary(res)}.")
        self.fill(); self.select(base["id"])
        try:
            from .whatview import after_added
            after_added(self.host, [(dd, v)], self.lib)
        except Exception:
            diag.swallowed()
        return v

    def current_id(self):
        r = self.table.currentRow()
        it = self.table.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it else None

    def selected_ids(self):
        rows = sorted({ix.row() for ix in self.table.selectionModel().selectedRows()})
        ids = [self.table.item(r, 0).data(Qt.UserRole) for r in rows if self.table.item(r, 0)]
        return list(dict.fromkeys(i for i in ids if i))      # 4.25.4: a group line has none; a version line is its document

    def select(self, doc_id):
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0) and self.table.item(r, 0).data(Qt.UserRole) == doc_id:
                self.table.selectRow(r)
                return True
        return False

    def show_doc(self):
        d = self.lib.doc(self.current_id()) if self.lib and self.current_id() else None
        many = len(self.selected_ids()) > 1 if self.lib else False
        for w in list(self.role_btns.values()) + [self.why, self.d_cat, self.d_folder, self.d_tags, self.d_under]:
            w.setEnabled(d is not None)
        self.b_conform.setVisible(bool(d) and d.get("type") == "Amendment")
        self.rv_box.setVisible(d is not None)
        if d is None:
            self.d_name.setText("Click a document"); self.d_info.setText("Where its review stands, its role, category, folder, "
                                                                          "tags and versions show here.")
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
        self.d_under.blockSignals(True); self.d_under.clear(); self.d_under.addItem("(not under another document)", "")
        for o in lib.docs:
            if o["id"] != d["id"] and o.get("category", "customer") == "customer":
                self.d_under.addItem(o["name"] + (f" ({o['initial']})" if o.get("initial") else ""), o["id"])
        self.d_under.setCurrentIndex(max(0, self.d_under.findData(d.get("under", "")))); self.d_under.blockSignals(False)
        kids = lib.children(d["id"])
        if d.get("under") and lib.doc(d["under"]):
            bits.append(f"under {lib.doc(d['under'])['name']}")
        if kids:
            bits.append(f"{len(kids)} order(s) under it")
        self.d_info.setText("  ·  ".join(bits))
        try:
            import ctxdocs as CX
            nt = len(CX.Store(self.host.ws.root).load().of_doc(d["id"]))
        except Exception:
            nt = 0
        self.d_taken.setText(f"{nt} piece(s) taken from it" if nt else "")
        self.d_taken.setVisible(bool(nt))
        self.show_review(d)
        self.b_ident.setVisible(d.get("category", "customer") == "customer" and not getattr(self, "focus", False))   # 4.6.0: right-click
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
        import effortlib as EL                      # 3.78.0: moving in the app moves the file on disk
        try:
            EL.move_doc(self.lib, d["id"], key, (folder or "").strip("/\\"))
            ok = True
        except OSError:
            diag.swallowed()
            self.host.status("The file could not be moved (open in another program?). Close it, then try again.")
            return False
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

    from .libfolders import new_folder, open_folder, move_into_folders   # 3.78.0: the Library's real folders

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

    # ------------------------------------------------------------ 3.16.0: the review, from the Library
    def review_states(self):
        """What the review holds now, worked out once per fill: the matrix's files with their sentence counts, the
        files marked reviewed, and the library entries Review offers."""
        h = self.host
        st = {"matrix": h.review is not None, "files": {}, "done": {}}
        if h.ws is not None:
            st["done"] = dict(h.ws.get("assign_reviewed") or {})
        if h.review is not None:
            read = {x[0] for x in h.review.M.sources if x} or set(h.review.files())   # read into the matrix, not taken from others
            st["files"] = {f: (0, 0) for f in read}
            for it in h.review.M.items:
                f = it.get("file", "")
                if f in read:
                    tot, dec = st["files"][f]
                    st["files"][f] = (tot + 1, dec + (1 if it.get("decision") else 0))
        return st

    def review_state(self, d, st=None):
        """(text, tone, key) for one document: not_needed, unread, needs, reviewed."""
        st = st if st is not None else self.review_states()
        if self.lib.role_of(d) == "not_needed":
            return "Not needed", "faint", "not_needed"
        v = d["versions"][-1] if d.get("versions") else {}
        f = v.get("file", "")
        if f in st["files"]:
            if f in st["done"]:
                return "Shredded", "ok", "reviewed"
            tot, dec = st["files"][f]
            return (f"Shred in progress: {dec}/{tot} decided" if tot else "Shred in progress"), "warn", "needs"
        if not st["matrix"] or self.lib.role_of(d) == "matrix":
            return "Not shredded", "accent", "unread"
        try:
            import ctxdocs as CX
            from .ctxassign import PREFIX
            if f"{PREFIX}{d['name']} ({CX.doc_tag(d, self.lib)})" in st["done"]:
                return "Shredded", "ok", "reviewed"
        except Exception:
            diag.swallowed()
        return "Shred in progress", "warn", "needs"

    def show_review(self, d):
        """4.0.0: the status panel: what has been done to the document and its next thing (docstatus)."""
        from . import docstatus as DS
        ids = self.selected_ids()
        text, tone, key = self.review_state(d)
        self.rv_state.setText(text)
        rows, nxt = DS.status(self, d)
        while self.st_lines.count():
            it = self.st_lines.takeAt(0)
            if it.widget() is not None:
                it.widget().hide(); it.widget().setParent(None)
        t = D.tokens()
        for what, detail, state in rows:
            col = {"ok": t["ok"], "warn": t["warn"]}.get(state, t["muted"])
            lab = D.label(f"<b>{what}</b><br><span style='color:{col}'>{detail}</span>", None)
            self.st_lines.addWidget(lab)
        self.status_now = rows
        self._next = nxt
        unread = [i for i in ids if self.lib.doc(i) and self.review_state(self.lib.doc(i))[2] == "unread"]
        if len(ids) > 1 and len(unread) > 1:
            self.b_read.setText(f"Extract {len(unread)}")
            self.b_read.setToolTip("Extract the selected documents, ready to shred")
            self.b_read.setVisible(True)
        else:
            self.b_read.setText(nxt[0] if nxt else "")
            self.b_read.setVisible(bool(nxt))
        return key

    def review_selected(self, answer=None, out=None):
        """The panel's button: the document's next thing (docstatus); several unread ones are read in together."""
        ids = self.selected_ids()
        unread = [i for i in ids if self.lib.doc(i) and self.review_state(self.lib.doc(i))[2] == "unread"]
        if len(ids) > 1 and len(unread) > 1:
            return self.read_many(unread, answer, out)
        d = self.lib.doc(self.current_id()) if self.lib and self.current_id() else None
        if d is None:
            return False
        from . import docstatus as DS
        _rows, nxt = DS.status(self, d)
        if nxt and nxt[1] == "assign":
            return self.read_in_assign(d["id"], answer, out)
        return DS.go_next(self, d, nxt[1]) if nxt else False

    def read_many(self, ids, answer=None, out=None):
        import compliance_read as CR
        h = self.host
        docs = {(self.lib.doc_of_file(p) or {}).get("id"): p for _n, _l, p in CR.effort_docs(h.ws)}
        paths = [docs[i] for i in ids if i in docs]
        if not paths:
            return self._say("Extract", "Only customer documents are read into the compliance matrix. Open the others "
                             "one at a time: they read beside the structure.", answer)
        from . import shredpick as SP                # 4.1.0: extracted at once, no question; the first opens in Shred
        w = SP.extract_paths(h, paths, then_file=os.path.basename(paths[0]), out=out)
        if w is None:
            return False
        diag.activity("library_read_many", n=len(paths))
        return w

    def show_new(self, found):
        """3.16.0: new and changed files in the watched folders, shown in the Library with Add and Ignore."""
        found = found or {}
        n = len(found.get("new", [])) + len(found.get("changed", []))
        if n:
            names = [os.path.basename(p) for p, _c in found.get("new", [])[:3]] + \
                    [os.path.basename(p) for p, _d, _v in found.get("changed", [])[:2]]
            self.new_lbl.setText(f"<b>{n} new or changed file(s)</b> in the watched folders: {', '.join(names)}"
                                 + ("..." if n > len(names) else "") + ". Add them to read and review them.")
        self.new_box.setVisible(bool(n))
        return n

    def read_in_assign(self, doc_id=None, answer=None, out=None):
        """2.84.0: open the document in Review, beside the response structure. 3.15.1: never a dead button: with no
        compliance matrix yet it offers to read the documents that build it (this one first), then opens this one;
        a document whose role is Not needed says how to read it. answer (tests): True/False for the question."""
        doc_id = doc_id or self.current_id()
        h = self.host
        if not doc_id or h.ws is None or self.lib is None:
            return False
        d = self.lib.doc(doc_id)
        if d is None or not d["versions"]:
            return False
        if self.lib.role_of(d) == "not_needed":
            return self._say("Shred", f"{d['name']} is left out. Right-click it and choose Put it back, then shred it.", answer)
        if h.review is None:
            return self._start_matrix(d, answer, out)
        return self._open_in_review(d)

    def _say(self, title, text, answer=None):
        self.host.status(text)
        if answer is None:
            QMessageBox.information(self, title, text)
        return False

    def _open_in_review(self, d):
        h = self.host
        h.go("assign")
        ap = h.assign_page
        ap.load_files_keep()
        lab = next((k for k, did in ap.lib_entries.items() if did == d["id"]), None)
        if lab is not None:
            ap.files.setCurrentText(lab)
            return True
        f = d["versions"][-1].get("file")
        if h.review is not None and f in h.review.files():
            ap.files.setCurrentText(f)
            return True
        h.status(f"{d['name']} is not offered in Shred.")
        return False

    def _start_matrix(self, d, answer=None, out=None):
        """3.15.1: Review works on the compliance matrix, read from the documents whose role is Builds the matrix."""
        import compliance_read as CR
        h = self.host
        docs = CR.effort_docs(h.ws)
        build = [p for _n, _l, p in docs if self.lib.role_of(self.lib.doc_of_file(p) or {}) == "matrix"]
        mine = next((p for _n, _l, p in docs if (self.lib.doc_of_file(p) or {}).get("id") == d["id"]), "")
        if mine and self.lib.role_of(d) == "matrix" and mine in build:
            build.remove(mine); build.insert(0, mine)
        if not build and mine:                         # 3.20.3: never a dead end: no document builds the matrix yet, so this
            self.lib.set_role(d["id"], "matrix", why="read into Review")     # one does (change its role any time)
            build = [mine]
            h.status(f"{d['name']} now builds the matrix (right-click it to change its role).")
        if not build:
            return self._say("Shred", "This document is not one Stationkeeper can extract (PDF, Word, Excel or "
                             "PowerPoint).", answer)
        if mine and mine in build:                     # 4.1.0: this one now, at once, no question; the others when picked
            build = [mine]
        from . import shredpick as SP
        w = SP.extract_paths(h, build[:1], out=out)
        if w is None:
            return False
        h.read_page._then = lambda: self._open_in_review(self.lib.doc(d["id"]) or d)
        return w

    def doc_menu(self, at=None, run=True):
        """3.20.3: what else can be said about a document: its role, category, folder, tags, initial and type, name, where
        it is filed, its instructions, and where its text went (4.0.0: the panel's More; the right-click menu is
        docstatus.row_menu). Returns the menu (run=False: not shown, for tests)."""
        from PySide6.QtWidgets import QMenu
        ids = self.selected_ids()
        m = QMenu(self)
        if not ids:
            return m
        d = self.lib.doc(ids[0]) if self.lib else None
        if d is not None and getattr(self, "focus", False):     # 4.25.2: Used for and Source are on the row's own menu
            pass
        else:
            rm = m.addMenu("Role")
            cur = self.lib.role_of(d) if d else ""
            for k, n in DV.ROLES:
                a = rm.addAction(n, lambda k=k: self.set_role(k)); a.setCheckable(True); a.setChecked(k == cur)
            cm = m.addMenu("Category")
            for k, n in self.lib.categories() if hasattr(self.lib, "categories") else []:
                a = cm.addAction(n, lambda k=k: self.set_category(k)); a.setCheckable(True); a.setChecked(bool(d) and d.get("category") == k)
            cm.addSeparator(); cm.addAction("New category...", lambda: self.new_category())
            m.addAction("Folder...", lambda: self._ask_and(lambda t: self.set_category(folder=t), "Folder", "Folder (Standards/Test):",
                                                           (d or {}).get("folder", "")))
        m.addAction("Tags...", lambda: self._ask_and(lambda t: self.set_tags(t), "Tags", "Tags, with a comma between:",
                                                     ", ".join((d or {}).get("tags", []))))
        m.addSeparator()
        m.addAction("Initial and type...", lambda: self.identity())
        m.addAction("Rename...", lambda: self.rename())
        if self.d_under.count() > 1:
            um = m.addMenu("Filed under")
            for i in range(self.d_under.count()):
                um.addAction(self.d_under.itemText(i), lambda i=i: (self.d_under.setCurrentIndex(i), self.set_under()))
        if self.b_conform.isVisible():
            m.addAction("Apply its instructions...", lambda: self.conform())
        m.addSeparator()
        m.addAction("Where its text went in the shred...", lambda: self.show_taken())
        from . import docmanage as DM                                   # 4.17.0
        m.addAction("Replace the file...", lambda: DM.replace_file(self, d))
        m.addAction("Delete...", lambda: DM.delete(self, d))
        self._menu = m
        if run and at is not None:
            m.exec(at)
        return m

    def _ask_and(self, fn, title, label, text=""):
        from PySide6.QtWidgets import QInputDialog
        t, ok = QInputDialog.getText(self, title, label, text=text)
        if ok:
            fn(t)
        return ok

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

    def add(self, paths=None, folders=None, category=None, choices=None, reader=None, edited="replace"):
        """Read the files in the background (progress, Stop), then the review table, then add them (also in the
        background). choices (tests): {file name: changes} applied instead of the table; returns the worker."""
        if self.lib is None or self.running():
            if self.running():
                self.host.status("Documents are being read: wait for it, or press Stop.")
            return None
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Add documents to the library", "", "Documents (*.docx *.pdf *.pptx *.xlsx *.txt *.doc *.xls *.ppt *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif *.webp);;Every file (*)")
        if not paths:
            return None
        self.lib = DV.Library(self.lib.folder).load()     # 3.15.1: plan against the library as saved now, never a stale copy
        lib, rd = self.lib, reader or DI.read
        self._choices = choices
        # 4.17.0: edited "replace": Add files and a drop (the person edited the file); the watch passes "version"
        self.worker = JobWorker(lambda prog, stop: DI.plan(lib, list(paths), rd, prog, stop, folders, category, edited))
        self.worker.progress.connect(self.panel.step)
        self.worker.done.connect(self._planned)
        self.panel.start(f"Reading {len(paths)} document(s)", "Getting ready")
        self.lock(True)
        diag.activity("library_intake_started", files=len(paths))
        self.worker.start()
        return self.worker

    def _planned(self, res):
        self.worker = PR.let_go(self.worker)
        if isinstance(res, DI.Spill):                   # 2.97.0: marked above CUI: stop, nothing copied
            self.lock(False)
            from .sensgate import spill_stop
            self.panel.failed("Stopped: a document is marked above CUI", res.text(),
                              "Nothing was copied or added. Leave the file where it is and tell your security officer.")
            spill_stop(self.host, res)
            return
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
        dups = [e["path"] for e in plan if e.get("dup")]
        if dups and self.host.ws is not None:          # 3.15.1: already here: the watched folders stop offering them
            try:
                import watch as WA
                WA.set_aside(self.host.ws.root, dups)
            except Exception:
                diag.swallowed()
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
        self.worker = PR.let_go(self.worker)
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
        self.host.refresh_level()                      # 2.97.0: the effort's level follows its documents
        try:                                           # 2.98.0: what each new version changed, at once
            from .whatview import after_added
            after_added(self.host, made, DV.Library(self.lib.folder).load())
        except Exception:
            diag.swallowed()
        self.panel.done("Added", f"{len(made)} document version(s) added: {text}.")
        self.host.toast(f"{len(made)} added to the library")
        self.refresh()
        if made:
            self.show_added([d["id"] for d, _v in made])

    def show_added(self, ids):
        """3.15.1: what was just added, in view: every filter off, All documents, the new documents selected."""
        for w in (self.search, self.role_f):
            w.blockSignals(True)
        self.search.clear(); self.role_f.setCurrentIndex(0)
        for w in (self.search, self.role_f):
            w.blockSignals(False)
        self.cat, self.folder = "all", ""
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        self.fill()
        self.table.clearSelection()
        mode = self.table.selectionMode()
        self.table.setSelectionMode(QAbstractItemView.MultiSelection)
        first = None
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it is not None and it.data(Qt.UserRole) in set(ids):
                self.table.selectRow(r)
                first = it if first is None else first
        self.table.setSelectionMode(mode)
        if first is not None:
            self.table.scrollToItem(first)
        return sum(1 for r in range(self.table.rowCount()) if self.table.item(r, 0) and self.table.item(r, 0).isSelected())

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
    or topic, search the words, export it all for writers, or open one in Review."""

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
        row.addWidget(D.button("Open in Shred", None, lambda: self.open_selected(), "Show the piece on its page"))
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
            h.status("That document is not offered in Shred (it is left out, or it builds the matrix).")
            return False
        ap.files.setCurrentText(lab)
        ap.select(a["iid"])
        self.accept()
        return True

    def export(self, path=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export what was taken from the library", self.host.out_path("taken_from_library"), "Excel (*.xlsx)")
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


class ConformDialog(QDialog):
    """The amendment's instructions, each ticked, the document they change, and what applying them does (applied, or why
    not), before the conformed version is made."""

    def __init__(self, parent, lib, amend, ins, base_id):
        super().__init__(parent)
        import amendinst as AI
        self.lib, self.ins = lib, ins
        self.setWindowTitle(f"Apply {amend['name']}'s instructions")
        self.setMinimumWidth(760)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"{len(ins)} change instruction(s) found in {amend['name']}. Each is applied to the latest version "
                            "of the document it changes; the result is its next version, Conformed, which Changes and Shred "
                            "show like any reissued version. Nothing in the files changes.", "muted"))
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.label("It changes", "label", wrap=False))
        self.base = QComboBox()
        for o in lib.docs:
            if o["id"] != amend["id"] and o.get("category", "customer") == "customer":
                self.base.addItem(o["name"], o["id"])
        self.base.setCurrentIndex(max(0, self.base.findData(base_id)))
        self.base.currentIndexChanged.connect(lambda _i: self.preview())
        row.addWidget(self.base, 1)
        self.list = QListWidget(); v.addWidget(self.list, 1)
        for i, x in enumerate(ins):
            it = QListWidgetItem(AI.describe(x)); it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked)
            it.setData(Qt.UserRole, i); self.list.addItem(it)
        self.list.itemChanged.connect(lambda _it: self.preview())
        self.result = D.label("", None); self.result.setWordWrap(True); v.addWidget(self.result)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.go = bb.addButton("Make the conformed version", QDialogButtonBox.AcceptRole)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.preview()

    def values(self):
        pick = [self.list.item(k).data(Qt.UserRole) for k in range(self.list.count()) if self.list.item(k).checkState() == Qt.Checked]
        return self.base.currentData(), pick

    def preview(self):
        import amendinst as AI
        base = self.lib.doc(self.base.currentData())
        if base is None:
            self.result.setText(""); self.go.setEnabled(False)
            return
        bid, pick = self.values()
        _out, res = AI.apply(self.lib.text(base["versions"][-1]), [self.ins[i] for i in pick])
        for k in range(self.list.count()):
            it = self.list.item(k); i = it.data(Qt.UserRole)
            r = next((x for j, x in zip(pick, res) if j == i), None)
            it.setForeground(D.color("muted") if r is None else (D.color("ok") if r["status"] == "applied" else D.color("crit")))
            it.setToolTip("" if r is None else (r["why"] or f"applied to {r['n']} piece(s)"))
        self.result.setText(AI.summary(res) + ". Red ones were not found in " + base["name"] + "; hover for why." if res else "Tick an instruction.")
        self.go.setEnabled(any(r["status"] == "applied" for r in res))


def under_parents(docs):
    """Each document followed by the task and delivery orders filed under it (those shown), in their order."""
    ids = {d["id"] for d in docs}
    kids = {}
    for d in docs:
        if d.get("under") in ids:
            kids.setdefault(d["under"], []).append(d)
    out, seen = [], set()

    def put(d):
        if d["id"] in seen:
            return
        seen.add(d["id"]); out.append(d)
        for k in kids.get(d["id"], []):
            put(k)
    for d in docs:
        if d.get("under") not in ids:
            put(d)
    for d in docs:
        put(d)
    return out

