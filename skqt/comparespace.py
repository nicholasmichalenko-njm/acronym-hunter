"""Compare (3.55.0, decision 4: one Compare space): Customer versions (the effort's Library documents, each change
decided, the impact on requirements; the page from 2.85.0) and Any two files (our drafts, loose files, anything the reader
takes: sentence by sentence, the changes by heading, the redline in Word). Final Checks and Your Tools open it with two
files picked. Rules only (changereview, compareany); nothing leaves the PC."""
import html
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                               QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import compareany as CA
from . import design as D

KIND_TONE = {"changed": "warn", "added": "ok", "removed": "crit", "same": "muted"}


class FilesCompare(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.result = None
        v = QVBoxLayout(self); v.setContentsMargins(0, D.SPACE["s"], 0, 0)
        f = QFormLayout(); v.addLayout(f)
        self.older, self.newer = QComboBox(), QComboBox()
        for label, cb in (("Earlier", self.older), ("Later", self.newer)):
            cb.setMinimumWidth(360)
            row = QHBoxLayout(); row.addWidget(cb, 1)
            row.addWidget(D.button("Choose...", None, lambda _=False, c=cb: self.pick(c)))
            f.addRow(label, row)
        bar = QHBoxLayout(); v.addLayout(bar)
        from .commandbar import CommandBar                       # 3.77.0: one bar (Rule 8)
        self.cbar = CommandBar()
        self.cbar.primary("Compare", lambda: self.run())
        self.cbar.export("Redline (Word)...", lambda: self.export(), "Removed words struck through, added words marked")
        self.cbar.export("Tracked changes (Word)...", lambda: self.export_tracked(),      # 3.60.0
                         "A Word file with every change a tracked change to accept or reject. Two Word files are "
                         "compared by Word itself, formatting kept; other files as their text.")
        bar.addWidget(self.cbar)
        self.only = QCheckBox("Only changes"); self.only.setChecked(True); self.only.toggled.connect(lambda _b: self.fill())
        bar.addWidget(self.only)
        self.sum = D.label("", "muted"); bar.addWidget(self.sum, 1)
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Change", "Under", "Earlier", "Later"])
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers); self.t.setWordWrap(True)
        self.t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch); self.t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.t.setColumnWidth(0, 80); self.t.setColumnWidth(1, 170)
        v.addWidget(self.t, 1)

    def pick(self, cb, path=None):
        import app_gui as A
        if path is None:
            exts = " ".join("*" + e for e in (".docx", ".pdf", ".pptx", ".xlsx"))
            path, _ = QFileDialog.getOpenFileName(self, "A version", "", f"Documents ({exts})")
            if not path:
                return ""
        if os.path.splitext(path)[1].lower() not in A.SUPPORTED_EXTS:
            return ""
        if cb.findData(path) < 0:
            cb.addItem(os.path.basename(path), path)
        cb.setCurrentIndex(cb.findData(path))
        return path

    def set_files(self, older, newer, run=True):
        self.pick(self.older, older); self.pick(self.newer, newer)
        return self.run() if run else None

    def run(self):
        a, b = self.older.currentData(), self.newer.currentData()
        if not a or not b or a == b:
            self.sum.setText("Pick two different files.")
            return None
        try:
            self.result = CA.compare(a, b)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.sum.setText(f"The files could not be read ({type(e).__name__}).")
            return None
        c = self.result["counts"]
        self.sum.setText(f"{c['changed']} changed, {c['added']} added, {c['removed']} removed")
        from . import filewarn
        filewarn.say(self.host, [a, b])                      # 3.57.0
        self.fill()
        diag.activity("files_compared", n=c["changed"] + c["added"] + c["removed"])
        return self.result

    def fill(self):
        self.t.setRowCount(0)
        if not self.result:
            return
        for r in self.result["rows"]:
            if self.only.isChecked() and r["kind"] == "same":
                continue
            n = self.t.rowCount(); self.t.insertRow(n)
            for c, v in enumerate((r["kind"], r.get("section") or "", r.get("old") or "", r.get("new") or "")):
                it = QTableWidgetItem(v)
                if c == 0:
                    it.setForeground(D.color(KIND_TONE.get(r["kind"], "muted")))
                self.t.setItem(n, c, it)
        self.t.resizeRowsToContents()

    def export(self, path=None):
        if not self.result:
            self.host.status("Compare two files first.")
            return None
        if path is None:
            stem = os.path.splitext(self.result["new"]["file"])[0]
            path, _ = QFileDialog.getSaveFileName(self, "Export the redline", os.path.join(os.path.dirname(self.newer.currentData() or ""),
                                                  f"{stem} - redline.docx"), "Word (*.docx)")
            if not path:
                return None
        CA.export(path, self.result, self.only.isChecked())
        self.host.toast("Redline exported")
        return path

    def export_tracked(self, path=None, use_word=None):
        """3.60.0: the tracked-changes copy. Two .docx files go to Word's own Compare (formatting kept) when Word is on
        this PC; otherwise, and for other files, the text of both with every change a tracked change."""
        if not self.result:
            self.host.status("Compare two files first.")
            return None
        a, b = self.result["old"].get("path"), self.result["new"].get("path")
        if path is None:
            import filesafety as FS
            start = FS.new_path(b, "tracked changes").rsplit(".", 1)[0] + ".docx"
            path, _ = QFileDialog.getSaveFileName(self, "Save the tracked-changes copy", start, "Word (*.docx)")
            if not path:
                return None
        import wordcompare as WC
        word = use_word if use_word is not None else (WC.available() and a.lower().endswith(".docx") and b.lower().endswith(".docx"))
        if word:
            self.host.status("Word is comparing the two files...")
            r = WC.compare(a, b, path, "Compare")
            if r.get("ok"):
                self.host.toast(f"Tracked changes saved: {r.get('revisions', 0)} change(s), compared by Word")
                diag.activity("compare_tracked_word", n=r.get("revisions", 0))
                return path
            self.host.status(r.get("why", "Word could not compare the two files.") + " The text comparison was saved instead.")
        n = CA.export_tracked(path, self.result)
        diag.activity("compare_tracked_text", n=n)
        self.host.toast(f"Tracked changes saved: {n} change(s), the text of both files")
        return path


class CompareSpace(QWidget):
    def __init__(self, host, customer_page):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.customer = customer_page
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget(); v.addWidget(self.tabs)
        self.tabs.addTab(customer_page, "Customer versions")
        self.files = FilesCompare(host)
        wrap = QWidget(); wv = QVBoxLayout(wrap); wv.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        wv.addWidget(D.label("Any two versions: our drafts, a file from outside the app, two loose files. Customer documents kept "
                             "in the Library get decisions and impact on Customer versions.", "muted"))
        wv.addWidget(self.files, 1)
        self.tabs.addTab(wrap, "Any two files")
        from . import changecards as CC
        if not CC.classic():                             # 4.6.0: Any two files is under Changes' More
            self.tabs.tabBar().hide()
            wv.insertWidget(0, D.button("Back to the customer's versions", "ghost", lambda: self.tabs.setCurrentIndex(0)), 0, Qt.AlignLeft)
        shown = customer_page.show                       # a pair opened from elsewhere (a new version, a rule) is a customer pair

        def show_pair(*a, **k):
            self.tabs.setCurrentIndex(0)
            return shown(*a, **k)
        customer_page.show = show_pair

    def refresh(self):
        if self.tabs.currentIndex() == 0:
            self.customer.refresh()

    def show_files(self, older, newer):
        """Opens Any two files with both picked and compared (Final Checks, Your Tools)."""
        self.tabs.setCurrentIndex(1)
        return self.files.set_files(older, newer)
