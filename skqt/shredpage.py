"""Shred > Requirements (3.55.0): one file in, every requirement out, no matrix to set up. Choose a file (or drop one on
Your Tools and pick Find the requirements); each requirement with its kind, section, page and the words that make it one;
filter by kind; Export the matrix... writes a draft compliance matrix (Excel); File to an effort... reads the file into
that effort's Review. Rules only (shredquick.py); nothing leaves the PC."""
import html
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QSplitter,
                               QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

import diag
import shredquick as SQ
from . import design as D

COLS = ["ID", "Kind", "Section", "Page", "Words", "Requirement"]
TONE = {"Requirement": "accent", "Instruction (L)": "ok", "Evaluation (M)": "warn", "SOW task": "muted"}


class ShredPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.result = None
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        v.addWidget(D.label("Every requirement in one file, with no matrix to set up: an RFP, a draft RFP or a statement of work. "
                            "Export a draft matrix, or file it to an effort to decide each one in Review.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.button("Choose a file...", "primary", lambda: self.choose()))
        self.file = D.label("No file yet.", "label"); top.addWidget(self.file, 1)
        self.f_kind = QComboBox(); self.f_kind.addItem("Every kind"); self.f_kind.addItems(list(SQ.KINDS))
        self.f_kind.currentIndexChanged.connect(lambda _i: self.fill()); top.addWidget(self.f_kind)
        self.b_export = D.button("Export the matrix...", None, lambda: self.export(), "A draft compliance matrix in Excel")
        self.b_file = D.button("File to an effort...", None, lambda: self.to_effort(), "Read this file into an effort's Review")
        top.addWidget(self.b_export); top.addWidget(self.b_file)
        self.counts = D.label("", "muted"); v.addWidget(self.counts)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels(COLS)
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setWordWrap(True)
        self.t.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        for i, w in enumerate((80, 120, 70, 50, 90)):
            self.t.setColumnWidth(i, w)
        self.t.itemSelectionChanged.connect(self.show_one)
        split.addWidget(self.t)
        self.detail = QTextBrowser(); split.addWidget(self.detail)
        split.setSizes([820, 380])
        for b in (self.b_export, self.b_file):
            b.setEnabled(False)

    def refresh(self):
        pass

    def choose(self):
        import app_gui as A
        exts = " ".join("*" + e for e in sorted(A.SUPPORTED_EXTS) if e in (".pdf", ".docx", ".pptx", ".xlsx"))
        path, _ = QFileDialog.getOpenFileName(self, "A solicitation, draft RFP or statement of work", "", f"Documents ({exts})")
        return self.open(path) if path else None

    def open(self, path):
        try:
            self.result = SQ.shred(path)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"The file could not be read ({type(e).__name__}).")
            return None
        self.file.setText(os.path.basename(path))
        from . import filewarn
        filewarn.say(self.host, [path])                      # 3.57.0
        c = self.result["counts"]
        self.counts.setText(f"{len(self.result['rows'])} requirement(s): " + ", ".join(f"{n} {k}" for k, n in c.items()))
        for b in (self.b_export, self.b_file):
            b.setEnabled(True)
        self.fill()
        diag.activity("quick_shred", n=len(self.result["rows"]))
        return self.result

    def shown(self):
        if not self.result:
            return []
        k = self.f_kind.currentText()
        return [r for r in self.result["rows"] if k == "Every kind" or r["kind"] == k]

    def fill(self):
        rows = self.shown()
        self.t.setRowCount(0)
        for r in rows:
            n = self.t.rowCount(); self.t.insertRow(n)
            for c, v in enumerate((r["id"], r["kind"], r["section"], str(r["page"]), r["words"], r["text"])):
                it = QTableWidgetItem(v); it.setData(Qt.UserRole, n)
                if c == 1:
                    it.setForeground(D.color(TONE.get(r["kind"], "muted")))
                self.t.setItem(n, c, it)
        self.t.resizeRowsToContents()

    def show_one(self):
        rows = self.shown()
        sel = sorted({i.row() for i in self.t.selectedIndexes()})
        if not sel or sel[0] >= len(rows):
            self.detail.setHtml("")
            return
        r = rows[sel[0]]
        text = html.escape(r["text"])
        if r["words"]:
            text = text.replace(html.escape(r["words"]), f"<b>{html.escape(r['words'])}</b>", 1)
        self.detail.setHtml(f"<p><b>{html.escape(r['kind'])}</b> · {html.escape(r['section'])} {html.escape(r['title'])}</p>"
                            f"<p>{text}</p><p style='color:gray'>{html.escape(r['loc'])}</p>")

    def export(self, path=None):
        if not self.result:
            return None
        if path is None:
            stem = os.path.splitext(os.path.basename(self.result["file"]))[0]
            start = os.path.join(os.path.dirname(self.result["file"]), f"{stem} - draft compliance matrix.xlsx")
            path, _ = QFileDialog.getSaveFileName(self, "Export the draft matrix", start, "Excel (*.xlsx)")
            if not path:
                return None
        try:
            n = SQ.export(self.result, path)
        except PermissionError:
            self.host.status("That file is open in Excel. Close it, then export again.")
            return None
        self.host.toast(f"{n} requirement(s) exported to {os.path.basename(path)}.")
        return path

    def to_effort(self, name=None):
        """Reads the file into an effort's Review (the effort's own read: identities, the matrix, every decision)."""
        import unfiled as UF
        if not self.result:
            return None
        h = self.host
        names = [n for n in h.efforts.names() if not (h.efforts.get(n) or {}).get("archived")]
        if name is None:
            if not names:
                h.status("No effort yet: start one on All Efforts, or Working on: Unfiled.")
                return None
            name, ok = QInputDialog.getItem(self, "File to an effort", "Read this file into the Review of:", names + [UF.NAME], 0, False)
            if not ok:
                return None
        if h.effort_name != name and not h.work_on(name):
            return None
        h.go("read")
        return h.read_page.read([self.result["file"]])
