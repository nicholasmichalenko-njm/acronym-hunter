"""Deliver > Final Checks (3.4.0): the last checks before the proposal goes out. The final PDF package (every PDF in the
package folder against the page limits, page size, embedded fonts, searchable text, file size and naming, and every
required volume and form present); cross-references and numbering in the Word drafts; and Compare two drafts (what
changed between the red team copy and today's, as a Word redline). Nothing is changed; each check exports a file."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import effortrec as R
from . import design as D


def _table(cols, widths, stretch, h=220):
    t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setWordWrap(True)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    for i, w in enumerate(widths):
        if w:
            t.setColumnWidth(i, w)
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    t.setMinimumHeight(h)
    return t


class ChecksPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.pkg = None
        self.xref = []
        self.cmp = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
        v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        # ---- the final PDF package
        self.pkg_card = D.Card("Final PDF package", "Every PDF in the package folder, checked the way the portal and the evaluators "
                               "will see it.", actions=[D.button("Check the package", "primary", lambda: self.check_package()),
                                                        D.button("Export...", None, lambda: self.export_package())])
        f = QFormLayout(); self.pkg_card.body.addLayout(f)
        self.folder = QLineEdit(); self.folder.setPlaceholderText("The folder that holds the PDFs you will upload")
        frow = QHBoxLayout(); frow.addWidget(self.folder, 1)
        frow.addWidget(D.button("Choose...", None, lambda: self.choose_folder()))
        f.addRow("Package folder", frow)
        self.size = QComboBox(); self.size.addItems(["Letter", "A4", "Letter or A4"]); f.addRow("Page size", self.size)
        self.mb = QDoubleSpinBox(); self.mb.setRange(0, 2000); self.mb.setSuffix(" MB"); self.mb.setSpecialValueText("no limit")
        f.addRow("Largest file allowed", self.mb)
        self.contain = QLineEdit(); self.contain.setPlaceholderText("Words every file name must hold, with commas between them")
        f.addRow("File names must contain", self.contain)
        self.naming = D.label("", "muted"); f.addRow("", self.naming)
        self.required = QPlainTextEdit(); self.required.setFixedHeight(80)
        self.required.setPlaceholderText("One a line: each volume and form that must have a file (filled from the deliverables)")
        f.addRow("Must be in the package", self.required)
        self.pkg_sum = self.pkg_card.add(D.label("Not checked yet.", "muted"))
        self.pkg_table = _table(["File", "Pages", "Limit", "MB", "Problems", "Notes"], [230, 60, 60, 60, 0, 220], 4)
        self.pkg_card.add(self.pkg_table)
        v.addWidget(self.pkg_card)
        # ---- cross-references
        self.x_card = D.Card("Cross-references and numbering", "Figure, table and exhibit numbers in order; every one the text "
                             "mentions has a caption, every caption is mentioned; pictures and tables with no caption; Word's "
                             "broken references.", actions=[D.button("Check the drafts", "primary", lambda: self.check_xref()),
                                                            D.button("Export...", None, lambda: self.export_xref())])
        self.drafts = QListWidget(); self.drafts.setFixedHeight(110); self.x_card.add(self.drafts)
        self.x_sum = self.x_card.add(D.label("Not checked yet.", "muted"))
        self.x_table = _table(["Draft", "Problem", "Section", "Detail"], [200, 190, 200, 0], 3)
        self.x_card.add(self.x_table)
        v.addWidget(self.x_card)
        # ---- compare two drafts
        self.c_card = D.Card("Compare two drafts", "What changed between two versions of a volume: the red team copy and today's, "
                             "say. Word redline: removed words struck through in red, added words in green.",
                             actions=[D.button("Compare", "primary", lambda: self.compare()),
                                      D.button("Export the redline...", None, lambda: self.export_redline())])
        cf = QFormLayout(); self.c_card.body.addLayout(cf)
        self.older, self.newer = QComboBox(), QComboBox()
        for label, cb in (("Earlier version", self.older), ("Later version", self.newer)):
            cb.setMinimumWidth(320)
            row = QHBoxLayout(); row.addWidget(cb, 1)
            row.addWidget(D.button("Other file...", None, lambda _=False, c=cb: self.pick_file(c)))
            cf.addRow(label, row)
        self.c_sum = self.c_card.add(D.label("", "muted")); self.c_sum.setTextFormat(Qt.RichText)
        v.addWidget(self.c_card)
        v.addStretch(1)

    # ------------------------------------------------------------ state
    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            return
        self.folder.setText(h.ws.get("final_dir", "") or self.folder.text())
        info = h.efforts.get(h.effort_name) or {}
        if not self.contain.text():
            self.contain.setText(info.get("solicitation", "") or "")
        rows = self._rows()
        size = next((r["value"] for r in rows if r.get("subject") == "Page size"), "")
        if "a4" in size.lower():
            self.size.setCurrentText("A4")
        naming = next((r["value"] for r in rows if r.get("subject") == "File naming"), "")
        self.naming.setText(f"The customer's naming rule: {naming}" if naming else "")
        self.naming.setVisible(bool(naming))
        if not self.required.toPlainText().strip():
            try:
                import deliverables as DL
                self.required.setPlainText("\n".join(d["name"] for d in DL.items(R.Record(h.ws.root))))
            except Exception:
                diag.swallowed()
        drafts = h.home_page.theme_drafts()
        self.drafts.clear()
        for name, p in drafts:
            it = QListWidgetItem(name); it.setData(Qt.UserRole, p); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked); self.drafts.addItem(it)
        for cb in (self.older, self.newer):
            keep = cb.currentData()
            cb.clear()
            for name, p in drafts:
                cb.addItem(name, p)
            if keep:
                if cb.findData(keep) < 0:
                    cb.addItem(os.path.basename(keep), keep)
                cb.setCurrentIndex(cb.findData(keep))
        if self.newer.count() > 1 and self.newer.currentIndex() == self.older.currentIndex():
            self.newer.setCurrentIndex(1)

    def _rows(self):
        try:
            from .custdocs import Ctx
            return Ctx(self.host).reg.rows()
        except Exception:
            diag.swallowed()
            return []

    def choose_folder(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "The folder with the final PDFs", self.folder.text() or os.path.expanduser("~"))
            if not folder:
                return ""
        self.folder.setText(folder)
        if self.host.ws is not None:
            self.host.ws.set("final_dir", folder)
        return folder

    # ------------------------------------------------------------ the package
    def check_package(self):
        import pkgcheck as PK
        d = self.folder.text().strip()
        if not d or not os.path.isdir(d):
            self.pkg_sum.setText("Choose the package folder first.")
            return None
        if self.host.ws is not None:
            self.host.ws.set("final_dir", d)
        paths = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".pdf")]
        allowed = ("Letter", "A4") if self.size.currentText() == "Letter or A4" else (self.size.currentText(),)
        self.pkg = PK.check(paths, [r for r in self._rows() if r.get("kind") == "Page limit"], self.mb.value() or None,
                            [w.strip() for w in self.contain.text().split(",") if w.strip()],
                            [x.strip() for x in self.required.toPlainText().splitlines() if x.strip()], allowed)
        t = self.pkg_table
        t.setRowCount(0)
        for fi in self.pkg["files"]:
            k = t.rowCount(); t.insertRow(k)
            for c, text in enumerate((fi["file"], str(fi["pages"]), str(fi["limit"] or ""), f"{fi['mb']:.1f}",
                                      "; ".join(fi["problems"]) or "OK", "; ".join(fi["notes"]))):
                it = QTableWidgetItem(text)
                if c == 4:
                    it.setForeground(D.color("crit" if fi["problems"] else "ok"))
                t.setItem(k, c, it)
        for m in self.pkg["missing"]:
            k = t.rowCount(); t.insertRow(k)
            t.setItem(k, 0, QTableWidgetItem(f"(missing) {m}"))
            it = QTableWidgetItem("no file for it in the package"); it.setForeground(D.color("crit")); t.setItem(k, 4, it)
        t.resizeRowsToContents()
        n, files = self.pkg["problems"], len(self.pkg["files"])
        self.pkg_sum.setText(f"{files} PDF{'s' if files != 1 else ''} checked: " + (f"{n} problem{'s' if n != 1 else ''} to fix before upload."
                                                                                    if n else "ready to upload."))
        diag.activity("package_checked", n=files)
        return self.pkg

    def export_package(self, path=None):
        import pkgcheck as PK
        if not self.pkg:
            self.host.status("Check the package first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the package check", self.host.out_path("package_check"), "Excel (*.xlsx)")
            if not path:
                return ""
        PK.export(path, self.pkg, self.host.effort_name)
        self.host.toast("Package check exported")
        return path

    # ------------------------------------------------------------ cross-references
    def check_xref(self):
        import xrefcheck as X
        out = []
        for i in range(self.drafts.count()):
            it = self.drafts.item(i)
            if it.checkState() == Qt.Checked:
                try:
                    out.append((it.text(), X.check(it.data(Qt.UserRole))))
                except Exception:
                    diag.swallowed()
        self.xref = out
        t = self.x_table
        t.setRowCount(0)
        for name, r in out:
            for p in r["problems"]:
                k = t.rowCount(); t.insertRow(k)
                for c, text in enumerate((name, p["kind"], p["where"], p["text"])):
                    t.setItem(k, c, QTableWidgetItem(text))
        t.resizeRowsToContents()
        n = t.rowCount()
        self.x_sum.setText("No drafts in the Volumes folder yet." if not out else
                           f"{len(out)} draft{'s' if len(out) != 1 else ''} read: " + (f"{n} problem{'s' if n != 1 else ''}." if n else
                                                                                         "numbering and references are clean."))
        diag.activity("xref_checked", n=n)
        return out

    def export_xref(self, path=None):
        import xrefcheck as X
        if not self.xref:
            self.host.status("Check the drafts first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the cross-reference check", self.host.out_path("xref_check"), "Excel (*.xlsx)")
            if not path:
                return ""
        X.export(path, self.xref, self.host.effort_name)
        self.host.toast("Cross-reference check exported")
        return path

    # ------------------------------------------------------------ compare
    def pick_file(self, cb, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A version of the draft", os.path.expanduser("~"), "Word (*.docx)")
            if not path:
                return ""
        if cb.findData(path) < 0:
            cb.addItem(os.path.basename(path), path)
        cb.setCurrentIndex(cb.findData(path))
        return path

    def compare(self):
        import draftcompare as DC
        import html
        a, b = self.older.currentData(), self.newer.currentData()
        if not a or not b or a == b:
            self.c_sum.setText("Pick two different versions.")
            return None
        self.cmp = DC.compare(a, b)
        c = self.cmp["counts"]
        secs = DC.by_section(self.cmp["rows"])
        lines = "".join(f"<br>&nbsp;&nbsp;{html.escape(s)}: {d['changed']} changed, {d['added']} added, {d['removed']} removed"
                        for s, d in list(secs.items())[:20])
        self.c_sum.setText(f"<b>{c['changed']} changed, {c['added']} added, {c['removed']} removed</b> "
                           f"({html.escape(os.path.basename(a))} to {html.escape(os.path.basename(b))}).{lines}"
                           + ("<br>&nbsp;&nbsp;..." if len(secs) > 20 else ""))
        diag.activity("drafts_compared", n=c["changed"] + c["added"] + c["removed"])
        return self.cmp

    def export_redline(self, path=None):
        import draftcompare as DC
        if not self.cmp:
            self.host.status("Compare two versions first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the redline", self.host.out_path(
                "draft_redline", Doc=os.path.splitext(self.cmp["new"]["file"])[0].replace(" ", "_")), "Word (*.docx)")
            if not path:
                return ""
        DC.export(path, self.cmp, os.path.splitext(self.cmp["new"]["file"])[0])
        self.host.toast("Redline exported")
        return path
