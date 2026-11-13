"""Drafts > Status (3.43.0 Draft Status; 4.4.0 by volume, claude/stationkeeper-drafts-plan-4.4.md). Each volume's folder
(a SharePoint library synced to this PC, More > Volume folders...) holds its draft: the newest Word file there. Read the
drafts reads every volume's by the response structure's headings and the setup's styles: the volumes table shows each
one's file, when it was saved, its sections not started, under way and over budget, and requirements removed; a volume
clicked shows its sections, the requirements removed or moved, and the styles pasted text brought in. Nothing in a
draft is changed; each read is kept in the effort record, and the report exports to Excel.
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QScrollArea,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import setupread as SR
from . import design as D

STATUS_TONE = {"Not started": "muted", "Under way": "ctx", "Near budget": "ok", "Over budget": "crit", "Heading not found": "warn"}


def status_color(status):
    """4.27.3: a status in its meaning color, from the colors in use (light or dark)."""
    return D.tokens()[STATUS_TONE.get(status, "text")]


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
        self.vols = []
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
        v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        from .commandbar import CommandBar
        bar = self.bar = CommandBar()
        self.b_read = bar.primary("Read the drafts", lambda: self.read_all(), "Every volume's newest draft, read by the "
                                  "response structure's headings and the setup's styles. Nothing in a draft is changed.")
        bar.add("Volume folders...", lambda: self.edit_folders(), "Each volume's folder: a SharePoint library synced to this PC")
        bar.more("Read another file...", lambda: self.read_other(),
                 "A Word file that is not in a volume's folder")
        bar.more("Drift report...", lambda: self.drift(), "Every draft against the dated copies made of it (Apply in Word, "      # 3.82.0
                 "Fix a Copy): each change taken up, still to take, or in a passage that changed")
        bar.export("The volume's status to Excel...", lambda: self.export())
        v.addWidget(bar)
        self.draft = QComboBox(); self.draft.setVisible(False)          # the files read one at a time (Other file, drift)
        self.card = D.Card("The volumes", "Each volume's newest draft in its folder. Click a volume for its sections.")
        self.v_table = _table(["Volume", "Draft", "Saved", "Not started", "Under way", "Over budget", "Requirements removed"], 1, 150)
        for i, wd in enumerate((160, 0, 120, 80, 80, 90, 150)):
            if wd:
                self.v_table.setColumnWidth(i, wd)
        self.v_table.currentCellChanged.connect(lambda r, _c, _pr, _pc: self.show_volume(r))
        self.card.add(self.v_table)
        f = QFormLayout(); self.card.body.addLayout(f)
        self.wpp = QSpinBox(); self.wpp.setRange(100, 1500); self.wpp.setSingleStep(25); self.wpp.setValue(SR.WORDS_PER_PAGE)
        self.wpp.setSuffix(" words a page")
        self.wpp.valueChanged.connect(lambda val: self._keep_wpp(val))
        f.addRow("Pages from words", self.wpp)
        self.sum = self.card.add(D.label("Not read yet.", "muted"))
        self.card.body.addWidget(self.draft)
        v.addWidget(self.card)
        self.vols = []
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
        self.fill_volumes()
        if self.rep is None:
            last = SR.latest(self.rec()) if self.rec() is not None else []
            if last:
                self.sum.setText(f"Last read {last[0]['when'].replace('T', ' ')}: {os.path.basename(last[0]['file'])}.")

    def drafts(self):
        out = [self.draft.itemData(i) for i in range(self.draft.count()) if self.draft.itemData(i)]
        if self.host.ws is not None:
            import draftvols as DV
            out += [d["file"] for d in DV.drafts(self.host.ws, self.M()) if d["file"] and d["file"] not in out]
        return out

    def drift(self, run=True):
        """3.82.0: the drift report over every draft in the list (the deliverables' linked files, the Volumes folder's)."""
        from . import driftview as DVW
        ds = self.drafts()
        if not ds:
            self.host.status("No draft yet: link a deliverable's working file, or pick one with Other file....")
            return None
        return DVW.show(self, run=run, drafts=ds)

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

    def read_other(self, path=None):
        path = self.pick(path)
        return self.read(path) if path else None

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

    # ------------------------------------------------------------ the volumes
    def edit_folders(self, answers=None):
        """One row per volume, each with its folder. answers ({volume: folder}, tests) skips the dialog."""
        import draftvols as DV
        ws, M = self.host.ws, self.M()
        if ws is None or M is None or not M.outline:
            self.host.status("Build the response structure first (Matrix & Outline > Outline): the folders are by volume.")
            return None
        if answers is None:
            from . import draftfolders as DF
            answers = DF.ask(self, DV.volumes(M), DV.folders(ws))
            if answers is None:
                return None
        for vol, folder in answers.items():
            DV.set_folder(ws, vol, folder)
        self.fill_volumes()
        return DV.folders(ws)

    def read_all(self):
        import draftvols as DV
        M = self.M()
        if M is None or not M.outline:
            self.sum.setText("Build the response structure first: the drafts are read by its headings.")
            return None
        self.vols = DV.read_all(M, self.host.ws, self.rec(), std=self.std(), wpp=self.wpp.value())
        self.fill_volumes(read=True)
        got = [r for r in self.vols if r["rep"] is not None and r["rep"]["matched"]]
        self.sum.setText(f"{len(got)} of {len(self.vols)} volume(s) read." + ("" if got else " Set each volume's folder: Volume folders..."))
        if got:
            i = self.vols.index(got[0])
            self.v_table.setCurrentCell(i, 0)
            self.show_volume(i)
        diag.activity("drafts_read", n=len(self.vols), files=len(got))
        return self.vols

    def fill_volumes(self, read=False):
        import draftvols as DV
        if self.host.ws is None:
            return
        if not read:
            had = {r["volume"]: r for r in self.vols}
            self.vols = [dict(d, rep=(had.get(d["volume"]) or {}).get("rep") if (had.get(d["volume"]) or {}).get("file") == d["file"] else None,
                              said="") for d in DV.drafts(self.host.ws, self.M())]
        t = self.v_table
        t.blockSignals(True); t.setRowCount(0)
        for r in self.vols:
            i = t.rowCount(); t.insertRow(i)
            n = DV.counts(r)
            got = r.get("rep") is not None
            vals = (r["volume"], os.path.basename(r["file"]) if r["file"] else (r.get("said") or DV._why_not(r)), r["saved"],
                    *(str(n[k]) if got else "" for k in ("not_started", "under_way", "over", "removed")))
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c >= 3:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 5 and got and n["over"]:
                    it.setForeground(QColor(status_color("Over budget")))
                t.setItem(i, c, it)
        t.blockSignals(False)

    def show_volume(self, i):
        if not (0 <= i < len(self.vols)):
            return None
        r = self.vols[i]
        if r.get("rep") is None:
            self.sum.setText(f"{r['volume']}: {r.get('said') or 'not read yet: Read the drafts.'}")
            return None
        self.rep = r["rep"]
        self.fill()
        self.sum.setText(f"{r['volume']}: {self.sum.text()}")
        return self.rep

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
                    it.setForeground(QColor(status_color(val)))
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
