"""Matrix in Qt (2.61.0): the compliance matrix as the customer will see it. Pick, order and rename its columns
(and add columns of the team's own), choose the rows (requirements, context, in the RFP's order or your structure's,
context in the requirement's cell or on its own rows), see it as it will be, and export it to Excel. Export the
compliance package writes the matrix, the Response Setup, the coverage report and the L/M crosswalk into one dated
folder. The design is kept with the matrix; Save as the team default makes it the starting design for new matrices."""
import datetime, os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
                               QListWidget, QListWidgetItem, QSplitter, QTableView, QVBoxLayout, QWidget, QAbstractItemView)
import diag
import matrixdesign as MD
from . import design as D

PREVIEW_ROWS = 400


class MatrixPage(QWidget):
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
        self.role_keep = QCheckBox("Compliance requirements"); self.role_ctx = QCheckBox("Context")
        self.order = QComboBox(); self.order.addItems(["In the RFP's order", "In your structure's order"])
        self.context = QComboBox(); self.context.addItems(["Supporting context in its requirement's cell", "Supporting context on its own rows"])
        self.empty = QCheckBox("Sections with nothing assigned yet")
        self.cust = QCheckBox("A sheet listing the customer's sentences")
        for w in (self.role_keep, self.role_ctx, self.order, self.context, self.empty, self.cust):
            (w.toggled if isinstance(w, QCheckBox) else w.currentIndexChanged).connect(lambda *_a: self.changed())
            rows.add(w)
        rows.add(D.label("In the cell, each piece of context starts with where it is in the RFP, e.g. (L.4.2, p.3).", "muted"))
        lv.addWidget(rows)
        split.addWidget(left)
        prev = D.Card("As it will be", actions=())
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
        split.setSizes([380, 980])
        v.addWidget(split, 1)
        bar = QHBoxLayout(); bar.setSpacing(D.SPACE["s"]); v.addLayout(bar)
        bar.addWidget(D.button("Save as the team default", "ghost", self.team_save, "New matrices start with this design"))
        bar.addWidget(D.button("Use the team default", "ghost", self.team_use))
        bar.addStretch(1)
        bar.addWidget(D.button("Export the compliance package...", None, self.export_package,
                               "Matrix, Response Setup, coverage report and L/M crosswalk in one dated folder"))
        bar.addWidget(D.button("Export the matrix...", "primary", self.export, "The matrix as an Excel workbook"))
        self.timer = QTimer(self, singleShot=True, interval=250, timeout=self.preview)

    # ------------------------------------------------------------ the design
    def refresh(self):
        R = self.host.review
        self.setEnabled(R is not None)
        if R is None:
            return
        self.d = MD.design_for(R.M, self.host.config_dir)
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
                             empty_sections=self.empty.isChecked(), customer_sheet=self.cust.isChecked()))

    def changed(self):
        if self._loading or self.host.review is None:
            return
        self.d = self.read_design()
        MD.set_matrix(self.host.review.M, self.d)
        self.host.changed()
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
        for it, r in list(zip(items, rows))[:PREVIEW_ROWS]:
            cells = [QStandardItem(str(v)) for v in r]
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
        self.info.setText(f"{n} rows" + (f" (the first {PREVIEW_ROWS} shown)" if n > PREVIEW_ROWS else "")
                          + f", {len(heads)} columns. " + ("Context in its requirement's cell." if self.d.get("context") == "cell"
                                                           else "Context on its own rows."))

    # ------------------------------------------------------------ team default and export
    def team_save(self):
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
            stem = self._effort_name().replace(" ", "_")
            path, _ = QFileDialog.getSaveFileName(self, "Export the compliance matrix", os.path.join(
                os.path.dirname(R.M.path), f"{stem}_Compliance_Matrix_{datetime.date.today():%Y-%m-%d}.xlsx"), "Excel (*.xlsx)")
            if not path:
                return None
        try:
            res = MD.export(R.M, path, self.d, self._effort_name(), ctx=MD.effort_ctx(self.host.ws))
        except PermissionError:
            self.host.status("A workbook with that name is open in Excel: close it, then export again.")
            return None
        diag.activity("matrix_exported", n=res["rows"])
        self.host.toast(f"Matrix exported: {res['rows']} rows")
        return res

    def export_package(self, folder=None):
        """Matrix, Response Setup, coverage report and L/M crosswalk in one dated folder."""
        import compliance as C, crosswalk as X
        R = self.host.review
        if R is None:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the compliance package", os.path.dirname(R.M.path))
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
