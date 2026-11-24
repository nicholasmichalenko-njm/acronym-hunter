"""Matrix in Qt (2.61.0): the compliance matrix as the customer will see it. Pick, order and rename its columns
(and add columns of the team's own), choose the rows (requirements, context, in the RFP's order or your structure's,
context in the requirement's cell or on its own rows), see it as it will be, and export it to Excel. Export the
compliance package writes the matrix, the Response Setup, the coverage report and the L/M crosswalk into one dated
folder. The design is kept with the matrix; Save as the team default makes it the starting design for new matrices.
4.55.0 (UX decision 18; Nicholas 2026-11-17 21:19): the matrix leads the page and has the room; Design... opens the
design beside it, with Save as a view... at its foot. Whether it was open is kept for the session only."""
import datetime, os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
                               QListWidget, QListWidgetItem, QSplitter, QTableView, QVBoxLayout, QWidget, QAbstractItemView)
import diag
import effortfolders as EF
import matrixdesign as MD
from . import design as D

PREVIEW_ROWS = 400


class MatrixPage(QWidget):
    design_open = False                     # 4.55.0: this session only; the page opens with the design closed

    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.d = MD.default()
        self._loading = False
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        split = QSplitter(Qt.Horizontal)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(D.SPACE["m"])
        # 3.35.0: named matrix views, kept in the template library with versions; each effort picks one
        vc = D.Card("View", "A saved set of columns, headings and rows. Pick one for this effort; change it here and "
                            "save it as a view, or as a new version of the one in use.")
        self.view_box = QComboBox()
        self.view_box.activated.connect(lambda _i: self.use_view(self.view_box.currentData()))
        vc.add(self.view_box)
        self.view_note = D.label("", "muted"); vc.add(self.view_note)
        lv.addWidget(vc)
        cols = D.Card("Columns", "Tick the columns, drag them in order; click one to rename it.")
        self.cols = QListWidget()
        self.cols.setDragDropMode(QAbstractItemView.InternalMove)
        self.cols.itemChanged.connect(lambda _i: self.changed())
        self.cols.model().rowsMoved.connect(lambda *_a: self.changed())
        self.cols.currentItemChanged.connect(self.pick_col)
        cols.add(self.cols)
        row = QHBoxLayout()
        self.heading = QLineEdit(); self.heading.setPlaceholderText("Heading in Excel")
        self.heading.editingFinished.connect(self.rename)
        row.addWidget(self.heading, 1)
        row.addWidget(D.button("Add a column...", None, self.add_column, "A column of the team's own, blank in Excel for them to fill"))
        cols.body.addLayout(row)
        lv.addWidget(cols, 1)
        rows = D.Card("Rows")
        self.layout_box = QComboBox()                                     # 3.35.0: the outline matrix or sentence rows
        for k, lab in MD.LAYOUTS:
            self.layout_box.addItem(lab, k)
        self.layout_box.currentIndexChanged.connect(lambda _i: self.changed())
        rows.add(self.layout_box)
        self.role_keep = QCheckBox("Compliance requirements"); self.role_ctx = QCheckBox("Context")
        self.order = QComboBox(); self.order.addItems(["In the RFP's order", "In your structure's order"])
        self.context = QComboBox(); self.context.addItems(["Supporting context in its requirement's cell", "Supporting context on its own rows"])
        self.empty = QCheckBox("Sections with nothing assigned yet")
        self.cust = QCheckBox("A sheet listing the customer's pieces")
        for w in (self.role_keep, self.role_ctx, self.order, self.context, self.empty, self.cust):
            (w.toggled if isinstance(w, QCheckBox) else w.currentIndexChanged).connect(lambda *_a: self.changed())
            rows.add(w)
        rows.add(D.label("In the cell, each piece of context starts with where it is in the RFP, e.g. (L.4.2, p.3).", "muted"))
        lv.addWidget(rows)
        self.b_saveview = D.button("Save as a view...", None, lambda: self.save_view(),
                                   "Keep this design in the template library under a name")      # 4.55.0: with the design
        lv.addWidget(self.b_saveview)
        from PySide6.QtWidgets import QFrame, QScrollArea                  # 3.35.0: the design scrolls; nothing is squeezed
        self.cols.setMinimumHeight(170)
        lsc = QScrollArea(); lsc.setWidgetResizable(True); lsc.setFrameShape(QFrame.NoFrame)
        lsc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); lsc.setWidget(left); lsc.setMinimumWidth(left.minimumSizeHint().width() + 18)
        split.addWidget(lsc)
        self.design_w = lsc
        prev = D.Card("As it will be", actions=())
        sw = QHBoxLayout(); sw.setSpacing(D.SPACE["xs"])                  # 4.69.0: the two layouts, on the page itself
        self.layout_btns = {}
        for (key, _lab), (text, tip) in zip(MD.LAYOUTS, (("By section", "One row per item of your outline, Section L and M side by side"),
                                                         ("By requirement", "One row per piece of the RFP"))):
            b = D.button(text, None, None, tip); b.setCheckable(True); b.setProperty("sk_switch", True)
            b.clicked.connect(lambda _c=False, k=key: self.show_layout(k))
            sw.addWidget(b); self.layout_btns[key] = b
        sw.addStretch(1)
        prev.body.addLayout(sw)
        self.info = D.label("", "muted")
        prev.add(self.info)
        self.model = QStandardItemModel(self)
        self.table = QTableView(); self.table.setModel(self.model)
        self.table.setWordWrap(True); self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        prev.add(self.table)
        split.addWidget(prev)
        split.setSizes([450, 910])
        v.addWidget(split, 1)
        from .commandbar import CommandBar                       # 3.77.0: one bar (Rule 8)
        self.bar = CommandBar()
        self.bar.add("Bring the edited matrix back...", lambda: self.bring_back(),        # 3.73.0
                     "The exported matrix as the team filled it in: their values come back, after you look")
        self.b_design = self.bar.add("Design...", None, "The view, the columns and the rows, beside the matrix")   # 4.55.0
        self.b_design.setCheckable(True)
        self.b_design.toggled.connect(lambda on: self.show_design_panel(on))
        self.bar.primary("Export the matrix...", self.export, "The matrix as an Excel workbook")
        self.ver_btn = self.bar.more("Save as a new version", lambda: self.save_version(),
                                    "A new version of the view in use, with this design; the old version stays")
        self.type_btn = self.bar.more("Start this effort type with it", lambda: self.type_start(),
                                     "New efforts of this effort type start with the view in use")
        self.bar.more("The L/M crosswalk...", lambda: self.host.go("crosswalk"),             # 4.69.0: off the tabs
                      "Each Section L instruction beside the Section M factor that scores it and the work it describes; the gaps; your own links")
        self.bar.more_sep()
        self.bar.more("Merge another copy's matrix...", lambda: self.bring_back(merge=True),
                      "Another copy of this effort's matrix: its values listed beside ours, ours kept unless you take theirs")
        self.bar.more("Save as the team default", self.team_save, "New matrices start with this design")
        self.bar.more("Use the team default", self.team_use)
        self.bar.export("The compliance package...", self.export_package,
                        "Matrix, Response Setup, coverage report and L/M crosswalk in one dated folder")
        v.insertWidget(0, self.bar)
        self.timer = QTimer(self, singleShot=True, interval=250, timeout=self.preview)
        self.b_design.setChecked(MatrixPage.design_open)
        self.design_w.setVisible(MatrixPage.design_open)

    def show_design_panel(self, on=True):
        """Design...: the design opens beside the matrix, or closes; kept for the session."""
        MatrixPage.design_open = bool(on)
        self.design_w.setVisible(bool(on))
        if self.b_design.isChecked() != bool(on):
            self.b_design.blockSignals(True); self.b_design.setChecked(bool(on)); self.b_design.blockSignals(False)
        return bool(on)

    def show_layout(self, key):
        """By section or By requirement (4.69.0): the same choice as Design > Rows. The other layout starts from its
        own columns, as it always has."""
        i = self.layout_box.findData(key)
        if i >= 0 and i != self.layout_box.currentIndex():
            self.layout_box.setCurrentIndex(i)
        self.mark_layout()
        return self.d.get("layout")

    def mark_layout(self):
        for k, b in self.layout_btns.items():
            b.setChecked(k == self.d.get("layout", "outline"))

    # ------------------------------------------------------------ the design
    def refresh(self):
        R = self.host.review
        self.setEnabled(True); __import__("skqt.emptyview", fromlist=["x"]).matrix(self, R is None)   # 4.62.0
        if R is None:                                # 3.34.1: nothing of the effort open before
            self.model.clear()
            self.info.setText("No matrix yet: read the customer's documents first.")
            return
        self.d = MD.design_for(R.M, self.host.config_dir, self.effort_type())
        self.show_design()
        self.preview()

    def show_design(self):
        self._loading = True
        self.cols.clear()
        chosen = [c["key"] for c in self.d["columns"]]
        heads = {c["key"]: c["heading"] for c in self.d["columns"]}
        for k in chosen + [k for k in MD.COLUMNS if k not in chosen]:
            it = QListWidgetItem(heads.get(k, MD.heading_of(k)) + ("   (your own)" if k.startswith(MD.CUSTOM) else ""))
            it.setData(Qt.UserRole, k)
            it.setData(Qt.UserRole + 1, heads.get(k, MD.heading_of(k)))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            it.setCheckState(Qt.Checked if k in chosen else Qt.Unchecked)
            self.cols.addItem(it)
        self.role_keep.setChecked("Keep" in self.d["roles"]); self.role_ctx.setChecked("Context" in self.d["roles"])
        self.order.setCurrentIndex(0 if self.d.get("order", "rfp") == "rfp" else 1)
        self.context.setCurrentIndex(0 if self.d.get("context", "cell") == "cell" else 1)
        self.empty.setChecked(bool(self.d.get("empty_sections", True)))
        self.cust.setChecked(bool(self.d.get("customer_sheet", True)))
        self.layout_box.setCurrentIndex(max(0, self.layout_box.findData(self.d.get("layout", "outline"))))
        outline = self.d.get("layout") == "outline"
        self.order.setEnabled(not outline); self.context.setEnabled(not outline)   # the outline sets both
        self.empty.setText("Outline items with nothing in them yet" if outline else "Sections with nothing assigned yet")
        self.fill_views()
        self.mark_layout()
        self._loading = False

    def read_design(self):
        cols = []
        for i in range(self.cols.count()):
            it = self.cols.item(i)
            if it.checkState() == Qt.Checked:
                cols.append({"key": it.data(Qt.UserRole), "heading": it.data(Qt.UserRole + 1)})
        roles = [r for r, box in (("Keep", self.role_keep), ("Context", self.role_ctx)) if box.isChecked()] or ["Keep"]
        return MD.clean(dict(self.d, columns=cols or MD.default()["columns"], roles=roles,
                             order="rfp" if self.order.currentIndex() == 0 else "structure",
                             context="cell" if self.context.currentIndex() == 0 else "rows",
                             empty_sections=self.empty.isChecked(), customer_sheet=self.cust.isChecked(),
                             layout=self.layout_box.currentData() or "outline"))

    def changed(self):
        if self._loading or self.host.review is None:
            return
        was = self.d.get("layout")
        self.d = self.read_design()
        MD.set_matrix(self.host.review.M, self.d)
        self.host.changed()
        if self.d.get("layout") != was:                    # 3.35.0: the other layout starts from its own columns
            self.d = MD.clean(dict(MD.default(self.d["layout"]), view=self.d.get("view")))
            MD.set_matrix(self.host.review.M, self.d)
            self.show_design()
        else:
            self.show_view_note()
        self.timer.start()

    def pick_col(self, cur, _prev=None):
        self.heading.setText(cur.data(Qt.UserRole + 1) if cur else "")

    def rename(self):
        it = self.cols.currentItem()
        if it is None or not self.heading.text().strip():
            return
        it.setData(Qt.UserRole + 1, " ".join(self.heading.text().split())[:60])
        k = it.data(Qt.UserRole)
        it.setText(it.data(Qt.UserRole + 1) + ("   (your own)" if k.startswith(MD.CUSTOM) else ""))
        self.changed()

    def add_column(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "Add a column", "Its heading (blank in Excel for the team to fill):")
            if not ok:
                return None
        name = " ".join((name or "").split())[:40]
        if not name:
            return None
        k = MD.CUSTOM + name
        it = QListWidgetItem(name + "   (your own)")
        it.setData(Qt.UserRole, k); it.setData(Qt.UserRole + 1, name)
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
        it.setCheckState(Qt.Checked)
        self._loading = True
        self.cols.addItem(it)
        self._loading = False
        self.changed()
        return k

    # ------------------------------------------------------------ the preview
    def preview(self):
        R = self.host.review
        if R is None:
            return
        try:
            heads, rows, n = MD.preview(R.M, self.d, ctx=MD.effort_ctx(self.host.ws))
            items, _data = MD.rows(R.M, self.d, ctx=None)
        except Exception:
            diag.swallowed()
            self.info.setText("The matrix could not be built.")
            return
        self.model.clear()
        self.model.setHorizontalHeaderLabels(heads)
        t = D.tokens()
        keys = [c["key"] for c in self.d["columns"]]
        for it, r in list(zip(items, rows))[:PREVIEW_ROWS]:
            cells = [QStandardItem(str(v)) for v in r]
            if it.get("_kind") == "item":                     # 3.35.0: the outline matrix: indented by level
                lvl = max(1, it.get("_level", 1))
                for k, c in enumerate(cells):
                    if keys[k] == "item":
                        c.setText("    " * (lvl - 1) + c.text())
                    if lvl == 1 or it.get("_parent"):
                        f = c.font(); f.setBold(True); c.setFont(f)
            if it.get("_kind") == "ctx":
                for c in cells:
                    c.setForeground(QColor(t["muted"]))
            elif it.get("_kind") == "empty":
                for c in cells:
                    c.setForeground(QColor(t["faint"]))
            self.model.appendRow(cells)
        hh = self.table.horizontalHeader()
        fm = hh.fontMetrics()
        for i, h in enumerate(heads):
            hh.setSectionResizeMode(i, QHeaderView.Interactive)
            want = int(MD.width_of(self.d["columns"][i]["key"]) * 6.5)
            self.table.setColumnWidth(i, min(420, max(90, want, fm.horizontalAdvance(h) + 28)))
        self.table.resizeRowsToContents()
        if self.d.get("layout") == "outline":
            how = "One row per outline item; a piece in several items is in each of their rows."
        else:
            how = "Context in its requirement's cell." if self.d.get("context") == "cell" else "Context on its own rows."
        self.info.setText(f"{n} rows" + (f" (the first {PREVIEW_ROWS} shown)" if n > PREVIEW_ROWS else "")
                          + f", {len(heads)} columns. " + how)

    # ------------------------------------------------------------ 3.35.0 matrix views
    def effort_type(self):
        try:
            return ((self.host.ws.get("prod_std", {}) or {}).get("effort_type") or "") if self.host.ws is not None else ""
        except Exception:  # noqa: BLE001
            return ""

    def fill_views(self):
        self.view_box.blockSignals(True)
        self.view_box.clear()
        for name, lay in MD.BUILTIN_VIEWS:
            self.view_box.addItem(f"{name} (built in)", "builtin:" + lay)
        try:
            for iid, name in MD.views(self.host.config_dir):
                self.view_box.addItem(name, iid)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        v = (self.d.get("view") or {}).get("id")
        i = self.view_box.findData(v) if v else -1
        self.view_box.setCurrentIndex(i if i >= 0 else -1)
        self.view_box.blockSignals(False)
        self.show_view_note()

    def show_view_note(self):
        v = self.d.get("view") or {}
        if not v.get("id"):
            self.view_note.setText("This effort's own design (not saved as a view).")
            self.ver_btn.setEnabled(False); self.type_btn.setEnabled(False)
            return
        base = MD.view_design(self.host.config_dir, v["id"])
        same = base is not None and MD._plain(base) == MD._plain(self.d)
        self.view_note.setText(f"From {v.get('name') or 'a saved view'}" + ("." if same else ", changed for this effort."))
        self.ver_btn.setEnabled(not same and base is not None)
        et = self.effort_type()
        self.type_btn.setEnabled(bool(et))
        on = bool(et) and MD.type_view(self.host.config_dir, et) == v["id"]
        self.type_btn.setText("This effort type starts with it" if on else "Start this effort type with it")

    def use_view(self, key):
        R = self.host.review
        if R is None or not key:
            return None
        if str(key).startswith("builtin:"):
            d = MD.default(str(key).split(":", 1)[1])
        else:
            d = MD.view_design(self.host.config_dir, key)
            if d is None:
                self.host.status("That view is no longer in the template library.")
                return None
        self.d = d
        MD.set_matrix(R.M, d)
        self.host.changed()
        self.show_design()
        self.preview()
        diag.activity("matrix_view_used")
        return d

    def save_view(self, name=None):
        if self.host.review is None:
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "Save as a view", "The view's name:", text=(self.d.get("view") or {}).get("name", ""))
            if not ok:
                return None
        iid, shown, state = MD.save_view(self.host.config_dir, name, self.d)
        if not iid:
            self.host.status("Give the view a name.")
            return None
        self.d = MD.clean(dict(self.d, view={"id": iid, "name": shown}))
        MD.set_matrix(self.host.review.M, self.d)
        self.host.changed()
        self.fill_views()
        diag.activity("matrix_view_saved")
        self.host.toast(f"Saved as the view {shown}" if state != "same" else f"The library already holds this design: {shown}")
        return iid

    def save_version(self, label=None):
        v = self.d.get("view") or {}
        if self.host.review is None or not v.get("id"):
            return None
        if label is None:
            label, ok = QInputDialog.getText(self, "Save as a new version", "A few words on what changed (optional):")
            if not ok:
                return None
        iid, shown, state = MD.save_view_version(self.host.config_dir, v["id"], self.d, label)
        if not iid:
            return None
        self.d = MD.clean(dict(self.d, view={"id": iid, "name": shown}))
        MD.set_matrix(self.host.review.M, self.d)
        self.host.changed()
        self.fill_views()
        diag.activity("matrix_view_version_saved")
        self.host.toast(f"Saved as {shown}")
        return iid

    def type_start(self):
        v = (self.d.get("view") or {}).get("id")
        et = self.effort_type()
        if not v or not et:
            return None
        on = MD.type_view(self.host.config_dir, et) == v
        MD.set_type_view(self.host.config_dir, et, "" if on else v)
        self.show_view_note()
        self.host.toast("New efforts of this type start with the team default" if on else "New efforts of this type start with this view")
        return not on

    # ------------------------------------------------------------ team default and export
    def team_save(self):
        import teampack as TP
        if TP.locked(self.host.config_dir, "design"):              # 2.89.0: the team pack set it
            self.host.status("The team pack set the team matrix design. It changes when the team sends a new pack.")
            return None
        p = MD.save_team(self.host.config_dir, self.d)
        diag.activity("matrix_design_team_saved")
        self.host.toast("Saved as the team default design")
        return p

    def team_use(self):
        t = MD.load_team(self.host.config_dir)
        if t is None:
            self.host.toast("No team default saved yet")
            return None
        self.d = t
        MD.set_matrix(self.host.review.M, t)
        self.host.changed()
        self.show_design()
        self.preview()
        self.host.toast("The team default design is in use")
        return t

    def _effort_name(self):
        return self.host.effort_name or self.host.review.M.name

    def export(self, path=None):
        R = self.host.review
        if R is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the compliance matrix", self.host.out_path("matrix_export", Effort=self._effort_name())
                                                  if self.host.effort_path else os.path.join(os.path.dirname(R.M.path), f"{self._effort_name().replace(' ', '_')}_Compliance_Matrix_{datetime.date.today():%Y-%m-%d}.xlsx"), "Excel (*.xlsx)")
            if not path:
                return None
        try:
            res = MD.export(R.M, path, self.d, self._effort_name(), ctx=MD.effort_ctx(self.host.ws))
        except PermissionError:
            self.host.status("A workbook with that name is open in Excel: close it, then export again.")
            return None
        diag.activity("matrix_exported", n=res["rows"])
        try:                                                     # 3.73.0: each export is a version, kept with the effort
            import matrixversions as MV
            MV.record(R.M, path, self.d, self.host.effort_path or "")
            R.M.pending = True
            self.host.changed()
        except OSError:
            diag.swallowed()
        self.host.toast(f"Matrix exported: {res['rows']} rows")
        return res

    def bring_back(self, path=None, merge=False, accept=None, picks=None):
        """3.73.0: an edited export (or another copy's matrix) brought back after the person looks at every change."""
        from .matrixbackview import bring_back
        return bring_back(self, path, merge, accept, picks)

    def export_package(self, folder=None):
        """Matrix, Response Setup, coverage report and L/M crosswalk in one dated folder."""
        import compliance as C, crosswalk as X
        R = self.host.review
        if R is None:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the compliance package", (self.host.out_path("compliance_package") if self.host.effort_path else "") or os.path.dirname(R.M.path))
            if not folder:
                return None
        try:
            res = MD.export_together(R.M, folder, self.d, self._effort_name(), ctx=MD.effort_ctx(self.host.ws))
            stem = MD.safe_name(self._effort_name().replace(" ", "_"))
            p = os.path.join(res["folder"], f"{stem}_RFP_Coverage.docx")
            C.write_coverage_docx(R.M, p)
            res["files"].append(p)
            p = os.path.join(res["folder"], f"{stem}_LM_Crosswalk.xlsx")
            X.export(R.M, p, self._effort_name())
            res["files"].append(p)
        except PermissionError:
            self.host.status("A file with the same name is open: close it, then export again.")
            return None
        R.M.pending = True                       # the setup export is recorded with the matrix
        self.host.changed()
        diag.activity("compliance_package_exported", files=len(res["files"]))
        self.host.toast(f"Compliance package exported: {len(res['files'])} files")
        return res
