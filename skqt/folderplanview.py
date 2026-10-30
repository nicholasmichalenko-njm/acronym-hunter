"""Settings > Folders and file names (2.95.0): the team's effort folder tree, where each thing the app makes goes and
how it is named, with a preview of the exact path. A team pack can carry and lock it. On this PC only."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QTableWidget,
                               QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import diag
import folderplan as FP
from . import design as D
from .stagesedit import clear_table


class FolderPlanCard(D.Card):
    def __init__(self, host):
        super().__init__("Folders and file names",
                         "Your effort folder tree as you keep it on SharePoint, where each thing Stationkeeper makes goes, and "
                         "how it is named. New efforts get the whole tree; an effort that exists keeps its folders (a folder "
                         "appears the first time something is saved into it, and nothing is ever renamed or moved). Customer "
                         "files keep the names the customer gave them.",
                         actions=[D.button("Put back the built-in ones", "ghost", lambda: self.reset()),
                                  D.button("Make the folders in this effort", None, lambda: self.make_here(),
                                           "Every folder of the tree that the open effort does not have yet"),
                                  D.button("Save", "primary", lambda: self.save())])
        self.host = host
        self.lock_note = self.add(D.label("", "muted"))
        self.tabs = QTabWidget(); self.add(self.tabs)
        # the tree
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(D.label("Folders in order; a subfolder sits under its folder. Names can use {Effort}, {Client}, {Solicitation}, "
                            "{Internal}, {Company}. Double-click a name to change it. Give four folders their job: customer "
                            "documents, volumes, Response Setup documents, exports.", "muted"))
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Folder", "Its job"]); self.tree.setColumnWidth(0, 380)
        self.tree.setMinimumHeight(260)
        self.tree.itemChanged.connect(lambda *_a: self.refresh_places())
        v.addWidget(self.tree, 1)
        row = QHBoxLayout(); v.addLayout(row)
        for text, fn in (("+ Folder", lambda: self.add_folder()), ("+ Subfolder", lambda: self.add_folder(sub=True)),
                         ("Up", lambda: self.move(-1)), ("Down", lambda: self.move(1)), ("Remove", lambda: self.remove())):
            row.addWidget(D.button(text, "ghost" if text == "Remove" else None, fn))
        row.addStretch(1)
        self.tabs.addTab(w, "Folder tree")
        # where things go
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(D.label("Each thing the app makes: the folder it goes to and its name. Names use fields in braces: {Effort} "
                            "{Client} {Solicitation} {Internal} {Company} {Date} {Time} {Version} {Person} {Stage} {Doc} "
                            "{DocVersion} {From} {To} {Matrix}. The last column shows a sample.", "muted"))
        self.places = QTableWidget(0, 4); self.places.setHorizontalHeaderLabels(["What", "Folder", "File name", "Sample"])
        self.places.verticalHeader().setVisible(False); self.places.setSelectionBehavior(QAbstractItemView.SelectRows)
        for i, wd in enumerate((260, 220, 340, 0)):
            if wd:
                self.places.setColumnWidth(i, wd)
        self.places.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.places.verticalHeader().setDefaultSectionSize(32); self.places.setProperty("sk_rows_fixed", True)
        self.places.setMinimumHeight(360)
        v.addWidget(self.places, 1)
        self.tabs.addTab(w, "Where things go")
        # options
        w = QWidget(); f = QFormLayout(w)
        self.datef = QComboBox()
        for k, sample in FP.DATE_FORMATS:
            self.datef.addItem(sample, k)
        self.space = QComboBox()
        for k, t in FP.SPACES:
            self.space.addItem(t, k)
        self.company = QLineEdit(); self.company.setPlaceholderText("Your company's short name, for {Company}")
        self.home = QComboBox()
        for x in (self.datef, self.space, self.home):
            x.currentIndexChanged.connect(lambda *_a: self.refresh_samples())
        self.company.textChanged.connect(lambda *_a: self.refresh_samples())
        f.addRow("Dates in names", self.datef)
        f.addRow("A space in a name becomes", self.space)
        f.addRow("Company", self.company)
        f.addRow("The effort list and its app data sit in", self.home)
        f.addRow("", D.label("New efforts only. The app data folder must stay beside the effort list: effort packages and "
                             "backups depend on it.", "muted"))
        self.tabs.addTab(w, "Options")
        self.fill()

    # ------------------------------------------------------------ filling
    def fill(self, plan=None):
        plan = plan or FP.load(self.host.config_dir)
        self.tree.blockSignals(True)
        self.tree.clear()
        items = {}
        for t in plan["tree"]:
            parent, _sep, leaf = t["path"].rpartition("/")
            it = QTreeWidgetItem([leaf, ""]); it.setFlags(it.flags() | Qt.ItemIsEditable)
            (items.get(parent) or self.tree.invisibleRootItem()).addChild(it)
            items[t["path"]] = it
            self._job_box(it, t["role"])
        self.tree.expandAll()
        self.tree.blockSignals(False)
        self.datef.setCurrentIndex(max(0, self.datef.findData(plan["date_format"])))
        self.space.setCurrentIndex(max(0, self.space.findData(plan["space"])))
        self.company.setText(plan["company"])
        self._plan_places = dict(plan["places"]); self._plan_names = dict(plan["names"]); self._home = plan["home"]
        clear_table(self.places)
        self.home.blockSignals(True); self.home.clear(); self.home.blockSignals(False)
        self.refresh_places()
        import teampack as TP
        lk = TP.locked(self.host.config_dir, "folders")
        self.lock_note.setText(f"Set by the team pack ({lk}). They change when the team sends a new pack." if lk else "")
        self.lock_note.setVisible(bool(lk))
        self.tabs.setEnabled(not lk)

    def _job_box(self, it, role=""):
        cb = QComboBox(); cb.addItem("", "")
        for k, n in FP.ROLES:
            cb.addItem(n, k)
        cb.setCurrentIndex(max(0, cb.findData(role)))
        cb.currentIndexChanged.connect(lambda _i, c=cb: self._one_job(c))
        self.tree.setItemWidget(it, 1, cb)
        return cb

    def _one_job(self, cb):
        """A job belongs to one folder: picking it for one takes it off another."""
        r = cb.currentData()
        if not r:
            return self.refresh_places()
        for it in self._items():
            other = self.tree.itemWidget(it, 1)
            if other is not None and other is not cb and other.currentData() == r:
                other.blockSignals(True); other.setCurrentIndex(0); other.blockSignals(False)
        self.refresh_places()

    def _items(self):
        out = []

        def walk(p):
            for i in range(p.childCount()):
                out.append(p.child(i)); walk(p.child(i))
        walk(self.tree.invisibleRootItem())
        return out

    def _path(self, it):
        parts = []
        while it is not None:
            parts.insert(0, " ".join(it.text(0).split()))
            it = it.parent()
        return "/".join(p for p in parts if p)

    def tree_rows(self):
        return [{"path": self._path(it), "role": (self.tree.itemWidget(it, 1).currentData() if self.tree.itemWidget(it, 1) else "") or ""}
                for it in self._items() if self._path(it)]

    def refresh_places(self):
        """The folder choices follow the tree; a row keeps its folder when it still exists."""
        paths = [t["path"] for t in self.tree_rows()]
        cur = {}
        for i in range(self.places.rowCount()):
            k = self.places.item(i, 0).data(Qt.UserRole)
            cur[k] = (self.places.cellWidget(i, 1).currentData(), self.places.item(i, 2).text() if self.places.item(i, 2) else "")
        if cur:
            self._plan_places = {k: v[0] for k, v in cur.items() if v[0] != "*"}
            self._plan_names = {k: v[1] for k, v in cur.items() if v[1].strip() and v[1].strip() != FP.OUT[k][2]}
        self.places.blockSignals(True)
        clear_table(self.places)
        for k, lab, role, pat, ext in FP.OUTPUTS:
            i = self.places.rowCount(); self.places.insertRow(i)
            it = QTableWidgetItem(lab); it.setData(Qt.UserRole, k); it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.places.setItem(i, 0, it)
            cb = QComboBox()
            if role:
                cb.addItem("(the folder for " + FP.ROLE_NAMES[role].split(" (")[0].lower() + ")", "*")
            else:
                cb.addItem("(where the effort list is)", "*")
            for p in paths:
                cb.addItem(p, p)
            want = self._plan_places.get(k)
            cb.setCurrentIndex(max(0, cb.findData(want)) if want else 0)
            cb.currentIndexChanged.connect(lambda *_a: self.refresh_samples())
            self.places.setCellWidget(i, 1, cb)
            nm = QTableWidgetItem(self._plan_names.get(k, pat) if ext else "(a folder: no name)")
            if not ext:
                nm.setFlags(nm.flags() & ~Qt.ItemIsEditable)
            self.places.setItem(i, 2, nm)
            self.places.setItem(i, 3, QTableWidgetItem(""))
        self.places.blockSignals(False)
        self.places.itemChanged.connect(self._name_edited) if not getattr(self, "_conn", False) else None
        self._conn = True
        home_was = self.home.currentData() if self.home.count() else self._home
        self.home.blockSignals(True); self.home.clear(); self.home.addItem("(the effort's folder)", "")
        for p in paths:
            self.home.addItem(p, p)
        self.home.setCurrentIndex(max(0, self.home.findData(home_was)))
        self.home.blockSignals(False)
        self.refresh_samples()

    def _name_edited(self, it):
        if it.column() == 2:
            self.refresh_samples()

    def values(self):
        places, names = {}, {}
        for i in range(self.places.rowCount()):
            k = self.places.item(i, 0).data(Qt.UserRole)
            f = self.places.cellWidget(i, 1).currentData()
            if f and f != "*":
                places[k] = f
            n = self.places.item(i, 2).text().strip() if self.places.item(i, 2) else ""
            if FP.OUT[k][3] and n and n != FP.OUT[k][2]:
                names[k] = n
        return {"tree": self.tree_rows(), "places": places, "names": names, "date_format": self.datef.currentData(),
                "space": self.space.currentData(), "company": self.company.text().strip(), "home": self.home.currentData() or ""}

    def refresh_samples(self):
        plan = dict(FP.default(), **self.values())
        self.places.blockSignals(True)
        for i in range(self.places.rowCount()):
            if self.places.item(i, 3) is None or self.places.item(i, 0) is None:
                continue
            k = self.places.item(i, 0).data(Qt.UserRole)
            try:
                s = FP.preview(plan, k)
            except Exception:
                s = ""
            self.places.item(i, 3).setText(s)
            self.places.item(i, 3).setToolTip(s)
        self.places.blockSignals(False)

    # ------------------------------------------------------------ editing the tree
    def add_folder(self, name="New folder", sub=False):
        cur = self.tree.currentItem()
        it = QTreeWidgetItem([name, ""]); it.setFlags(it.flags() | Qt.ItemIsEditable)
        self.tree.blockSignals(True)
        if sub and cur is not None:
            cur.addChild(it); cur.setExpanded(True)
        elif cur is not None:
            parent = cur.parent() or self.tree.invisibleRootItem()
            parent.insertChild(parent.indexOfChild(cur) + 1, it)
        else:
            self.tree.addTopLevelItem(it)
        self.tree.blockSignals(False)
        self._job_box(it, "")
        self.tree.setCurrentItem(it)
        self.refresh_places()
        return it

    def move(self, d):
        it = self.tree.currentItem()
        if it is None:
            return False
        parent = it.parent() or self.tree.invisibleRootItem()
        i = parent.indexOfChild(it); j = i + d
        if not (0 <= j < parent.childCount()):
            return False
        role = self.tree.itemWidget(it, 1).currentData() if self.tree.itemWidget(it, 1) else ""
        roles = {id(x): (self.tree.itemWidget(x, 1).currentData() if self.tree.itemWidget(x, 1) else "") for x in self._sub(it)}
        parent.takeChild(i); parent.insertChild(j, it)
        self._job_box(it, role)
        for x in self._sub(it):                       # moving an item drops its widgets: put them back
            self._job_box(x, roles.get(id(x), ""))
        it.setExpanded(True)
        self.tree.setCurrentItem(it)
        self.refresh_places()
        return True

    def _sub(self, it):
        out = []
        for i in range(it.childCount()):
            out.append(it.child(i)); out += self._sub(it.child(i))
        return out

    def remove(self):
        it = self.tree.currentItem()
        if it is None:
            return False
        if any((self.tree.itemWidget(x, 1).currentData() if self.tree.itemWidget(x, 1) else "") for x in [it] + self._sub(it)):
            self.host.status("That folder (or one inside it) has a job. Give the job to another folder first.")
            return False
        (it.parent() or self.tree.invisibleRootItem()).removeChild(it)
        self.refresh_places()
        return True

    # ------------------------------------------------------------ saving
    def save(self):
        import teampack as TP
        if TP.locked(self.host.config_dir, "folders"):
            self.host.status("The team pack set the folders and file names. They change when the team sends a new pack.")
            return False
        v = self.values()
        missing = [FP.ROLE_NAMES[r] for r, _n in FP.ROLES if not any(t["role"] == r for t in v["tree"])]
        if missing:
            self.host.status("Give these jobs a folder first: " + ", ".join(missing) + ".")
            return False
        why = FP.problems(v)
        if why:
            self.host.status("Not saved: " + "; ".join(why) + ".")
            return False
        P = FP.save(self.host.config_dir, v)
        diag.activity("qt_folder_plan_saved", n=len(P["tree"]))
        self.host.toast("Folders and file names saved")
        self.fill(P)
        return True

    def make_here(self):
        import effortfolders as EF
        h = self.host
        if not h.effort_path:
            h.status("Open an effort first.")
            return []
        made = [p for p in EF.create_all(h.effort_path, h.effort_fields())]
        diag.activity("qt_folder_plan_made", n=len(made))
        h.toast(f"{len(made)} folder(s) in {h.effort_name}")
        return made

    def reset(self, answer=None):
        if answer is None:
            from PySide6.QtWidgets import QMessageBox
            answer = QMessageBox.question(self, "Folders and file names", "Put back the built-in folders and names? Nothing changes "
                                          "until you save, and no folder on disk is touched.") == QMessageBox.Yes
        if not answer:
            return False
        self.fill(FP.default())
        return True
