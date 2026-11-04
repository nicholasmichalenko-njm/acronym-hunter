"""Writing > Draft Status (3.43.0): read the setup back. An author's filled setup document (a volume draft) read by the
response structure's headings and the setup's styles: each section's status, its words and pages against the page
budget, the requirements whose text was removed or moved, and the styles pasted text brought in. Nothing in the draft
is changed; the report exports to Excel, and a line of it is kept in the effort record."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QScrollArea,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import setupread as SR
from . import design as D

STATUS_COLOR = {"Not started": "#64748b", "Under way": "#2563eb", "Near budget": "#0f766e", "Over budget": "#b91c1c",
                "Heading not found": "#b45309"}


def _table(cols, stretch, h=200):
    t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setWordWrap(True)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    t.setMinimumHeight(h)
    return t


class DraftStatusPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rep = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
        v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.card = D.Card("Read the setup back", "A volume's draft, read by the response structure's headings and the setup's "
                           "styles. Nothing in the draft is changed.",
                           actions=[D.button("Read the draft", "primary", lambda: self.read()),
                                    D.button("Export...", None, lambda: self.export())])
        f = QFormLayout(); self.card.body.addLayout(f)
        self.draft = QComboBox(); self.draft.setMinimumWidth(360)
        row = QHBoxLayout(); row.addWidget(self.draft, 1)
        row.addWidget(D.button("Other file...", None, lambda: self.pick()))
        f.addRow("Draft", row)
        self.wpp = QSpinBox(); self.wpp.setRange(100, 1500); self.wpp.setSingleStep(25); self.wpp.setValue(SR.WORDS_PER_PAGE)
        self.wpp.setSuffix(" words a page")
        self.wpp.valueChanged.connect(lambda val: self._keep_wpp(val))
        f.addRow("Pages from words", self.wpp)
        self.sum = self.card.add(D.label("Not read yet.", "muted"))
        v.addWidget(self.card)
        self.s_card = D.Card("Sections", "Not started: none of the author's own words yet. Near budget: half the page budget or "
                             "more. Over budget: past it. Pages are counted from words; Word's own count is in the line above.")
        self.s_table = _table(["Section", "Status", "Words", "Pages", "Budget", "Requirements removed", "Moved"], 0, 260)
        for i, wd in enumerate((0, 110, 70, 60, 60, 150, 70)):
            if wd:
                self.s_table.setColumnWidth(i, wd)
        self.s_card.add(self.s_table)
        v.addWidget(self.s_card)
        self.r_card = D.Card("Requirements removed or moved", "Requirements placed in a section whose text is no longer in "
                             "the draft (an author deleted the hidden RFP text), or now sits under another heading.")
        self.r_table = _table(["Section", "What happened", "Requirement", "Text"], 3, 160)
        self.r_card.add(self.r_table)
        v.addWidget(self.r_card)
        self.y_card = D.Card("Styles brought in", "Styles the draft uses that the setup did not have: pasted text usually brings "
                             "them. Fix a Copy maps them onto the standard's styles.")
        self.y_table = _table(["Style", "Times used", "First under"], 0, 140)
        self.y_card.add(self.y_table)
        v.addWidget(self.y_card)
        v.addStretch(1)

    # ------------------------------------------------------------ state
    def M(self):
        return getattr(self.host.review, "M", None) if getattr(self.host, "review", None) is not None else None

    def rec(self):
        import effortrec as R
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            return
        try:
            self.wpp.blockSignals(True); self.wpp.setValue(int(h.ws.get("readback_wpp", SR.WORDS_PER_PAGE) or SR.WORDS_PER_PAGE))
        finally:
            self.wpp.blockSignals(False)
        keep = self.draft.currentData()
        self.draft.clear()
        try:
            drafts = h.home_page.theme_drafts()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            drafts = []
        for name, p in drafts:
            self.draft.addItem(name, p)
        if keep:
            if self.draft.findData(keep) < 0:
                self.draft.addItem(os.path.basename(keep), keep)
            self.draft.setCurrentIndex(self.draft.findData(keep))
        if self.rep is None:
            last = SR.latest(self.rec()) if self.rec() is not None else []
            if last:
                self.sum.setText(f"Last read {last[0]['when'].replace('T', ' ')}: {os.path.basename(last[0]['file'])}.")

    def _keep_wpp(self, val):
        if self.host.ws is not None:
            self.host.ws.set("readback_wpp", int(val))

    def pick(self, path=None):
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "A filled setup document", "", "Word documents (*.docx)")
        if not path:
            return None
        if self.draft.findData(path) < 0:
            self.draft.addItem(os.path.basename(path), path)
        self.draft.setCurrentIndex(self.draft.findData(path))
        return path

    def std(self):
        try:
            import prodrules as PRL
            return PRL.for_effort(self.host.config_dir, self.host.ws)
        except Exception:  # noqa: BLE001  the setup's styles and Word's own still count
            diag.swallowed()
            return None

    # ------------------------------------------------------------ read
    def read(self, path=None):
        M = self.M()
        path = path or self.draft.currentData()
        if M is None or not M.outline:
            self.sum.setText("Build the response structure first: the draft is read by its headings.")
            return None
        if not path or not os.path.isfile(path):
            self.sum.setText("Choose a draft: a volume's Word file from the Volumes folder, or Other file...")
            return None
        try:
            rep = SR.read(M, path, std=self.std(), template=SR.file_template(path), wpp=self.wpp.value())
        except Exception as e:  # noqa: BLE001  a file Word cannot have written is said, never a crash
            diag.swallowed()
            self.sum.setText(f"That file could not be read as a Word document ({type(e).__name__}).")
            return None
        self.rep = rep
        if rep["matched"] and self.rec() is not None:
            SR.keep(self.rec(), rep)
        self.fill()
        return rep

    def fill(self):
        rep = self.rep
        self.sum.setText(SR.summary_line(rep))
        t = self.s_table; t.setRowCount(0)
        for r in rep["sections"]:
            i = t.rowCount(); t.insertRow(i)
            vals = (r["section"], r["status"], str(r["words"]), f"{r['pages']:g}", "" if r["budget"] is None else f"{r['budget']:g}",
                    str(len(r["removed"])) if r["removed"] else "", str(len(r["moved"])) if r["moved"] else "")
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 1:
                    it.setForeground(QColor(STATUS_COLOR.get(val, "#1f2937")))
                if c in (2, 3, 4, 5, 6):
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                t.setItem(i, c, it)
        t.resizeRowsToContents()
        t = self.r_table; t.setRowCount(0)
        for r in rep["sections"]:
            for kind, rows in (("Removed", r["removed"]), ("Moved", r["moved"])):
                for x in rows:
                    i = t.rowCount(); t.insertRow(i)
                    for c, val in enumerate((r["section"], "Removed" if kind == "Removed" else "Now under " + x["to"], x["id"], x["text"])):
                        t.setItem(i, c, QTableWidgetItem(val))
        t.resizeRowsToContents()
        t = self.y_table; t.setRowCount(0)
        for s in rep["styles"]:
            i = t.rowCount(); t.insertRow(i)
            for c, val in enumerate((s["style"], str(s["count"]), s["first"])):
                t.setItem(i, c, QTableWidgetItem(val))

    def export(self, path=None):
        if self.rep is None:
            self.sum.setText("Read a draft first.")
            return None
        if path is None:
            stem = os.path.splitext(os.path.basename(self.rep["file"]))[0]
            path, _f = QFileDialog.getSaveFileName(self, "Export the read-back", f"{stem} - draft status.xlsx", "Excel (*.xlsx)")
        if not path:
            return None
        SR.export_xlsx(self.rep, path)
        self.host.status(f"Exported {os.path.basename(path)}.")
        return path
