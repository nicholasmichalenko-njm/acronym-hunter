"""Color team reviews in Qt (2.63.0): build a review packet for a stage (Red team, Gold team: a Word file with every
compliance requirement under its section, for reviewers to give a verdict and comments), read it back (verdicts and
Word comments land on each requirement's sentence card), and see the score by section. Rules only (No AI); nothing
leaves the PC."""
import datetime, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLineEdit, QScrollArea,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import effortrec as R
import reviewpkt as RP
from . import design as D

TONE = {"Compliant": "ok", "Partly": "warn", "Not compliant": "crit", "Not addressed": "cust", "not_reviewed": "border_strong"}


class ReviewPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        inner = QWidget(); inner.setObjectName("page"); scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.empty = D.EmptyState("No compliance matrix yet", "Read the RFP and assign its requirements; then build a review packet here.")
        v.addWidget(self.empty)
        self.top = D.Card("Review packet", "A Word file with every compliance requirement under the section it is answered in. "
                                           "Reviewers give a verdict and comments in the table or as Word comments.")
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.label("Stage", "label", wrap=False))
        self.stage = QComboBox(); self.stage.setMinimumWidth(200); self.stage.setEditable(True)
        self.stage.activated.connect(lambda _i: self.fill())
        row.addWidget(self.stage)
        row.addWidget(D.label("Reviewers", "label", wrap=False))
        self.reviewers = QLineEdit(); self.reviewers.setPlaceholderText("Names, separated by commas"); row.addWidget(self.reviewers, 1)
        row.addWidget(D.button("Build the packet...", "primary", lambda: self.build()))
        row.addWidget(D.button("Read back a packet...", None, lambda: self.read_back()))
        self.top.body.addLayout(row)
        v.addWidget(self.top)
        self.tiles = {k: D.Tile("-", lab, TONE[k]) for k, lab in (("Compliant", "compliant"), ("Partly", "partly compliant"),
                                                                    ("Not compliant", "not compliant"), ("Not addressed", "not addressed"),
                                                                    ("not_reviewed", "not reviewed yet"))}
        self.tile_row = QWidget(); tg = QGridLayout(self.tile_row); tg.setContentsMargins(0, 0, 0, 0); tg.setSpacing(D.SPACE["m"])
        for i, t in enumerate(self.tiles.values()):
            tg.addWidget(t, 0, i); tg.setColumnStretch(i, 1)
        v.addWidget(self.tile_row)
        self.score = D.Card("Score by section")
        self.bar = D.StackBar(14); self.score.add(self.bar)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Section", "Compliant", "Partly", "Not compliant", "Not addressed", "Not reviewed"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.table.setMinimumHeight(220)
        self.score.add(self.table)
        v.addWidget(self.score)
        self.found = D.Card("Comments read back", "Each one is also on the requirement's piece card. Double-click to open it in Shred.")
        self.notes = QTableWidget(0, 3)
        self.notes.setHorizontalHeaderLabels(["Requirement", "Comment", "When"])
        self.notes.verticalHeader().setVisible(False); self.notes.setEditTriggers(QTableWidget.NoEditTriggers)
        self.notes.setWordWrap(True); self.notes.setColumnWidth(0, 160); self.notes.setColumnWidth(2, 90)
        self.notes.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.notes.setMinimumHeight(260)
        self.notes.cellDoubleClicked.connect(lambda r, _c: self.open_row(r))
        self.found.add(self.notes)
        v.addWidget(self.found)
        # 3.39.0: every reviewer comment gets a disposition, an owner and a due date
        self.disp = D.Card("Comment dispositions", "Accept, Reject (say why) or Done, with an owner and a due date, for every comment: "
                           "from the packet read back, and from Word comments in the drafts (placed under their heading). "
                           "The recovery stages' gate holds until every comment has one.")
        dr = QHBoxLayout(); dr.setSpacing(D.SPACE["s"])
        self.disp_sum = D.label("", "muted"); dr.addWidget(self.disp_sum, 1)
        self.open_only = QCheckBox("Open only"); self.open_only.toggled.connect(lambda _on: self.fill_disp()); dr.addWidget(self.open_only)
        dr.addWidget(D.button("Read Word comments from the drafts", None, lambda: self.read_drafts(),
                              "Every Word comment in the drafts in the Volumes folder, placed under the heading it sits beneath"))
        dr.addWidget(D.button("Export the disposition log...", None, lambda: self.export_disp(), "One row per comment, for the record"))
        self.disp.body.addLayout(dr)
        self.dt = QTableWidget(0, 7)
        self.dt.setHorizontalHeaderLabels(["Where", "Reviewer", "Comment", "Disposition", "Reason", "Owner", "Due"])
        self.dt.verticalHeader().setVisible(False); self.dt.setEditTriggers(QTableWidget.NoEditTriggers); self.dt.setWordWrap(True)
        for c, w in ((0, 180), (1, 110), (3, 120), (4, 200), (5, 140), (6, 100)):
            self.dt.setColumnWidth(c, w)
        self.dt.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch); self.dt.setMinimumHeight(300)
        self.disp.add(self.dt)
        v.addWidget(self.disp)
        v.addStretch(1)

    def refresh(self):
        h = self.host
        on = h.ws is not None and h.review is not None and bool(h.review.M.items)
        self.empty.setVisible(not on)
        for w in (self.top, self.tile_row, self.score, self.found, self.disp):
            w.setVisible(on)
        if not on:
            return
        r = R.Record(h.ws.root)
        keep = self.stage.currentText()
        names = [s["name"] for s in r.stages]
        done = RP.stages_reviewed(h.review.M)
        self.stage.clear(); self.stage.addItems(names + [n for n in done if n not in names])
        cur = r.stage()["name"]
        pick = keep if keep in names + done else (cur if "team" in cur.lower() else next((n for n in names if "team" in n.lower()), cur))
        self.stage.setCurrentText(pick)
        if not self.reviewers.text():
            self.reviewers.setText(", ".join(m["name"] for m in r.team() if "review" in (m.get("role") or "").lower()))
        self.fill()

    def fill(self):
        h = self.host
        if h.review is None:
            return None
        M = h.review.M
        stage = self.stage.currentText() or "Review"
        sc = RP.score(M, stage)
        for k, t in self.tiles.items():
            t.set(sc[k])
        self.bar.set([(sc[k], TONE[k], k) for k in TONE])
        self.table.setRowCount(len(sc["sections"]))
        for i, (lab, c) in enumerate(sc["sections"]):
            self.table.setItem(i, 0, QTableWidgetItem(lab))
            for j, k in enumerate(("Compliant", "Partly", "Not compliant", "Not addressed", "not_reviewed"), 1):
                it = QTableWidgetItem(str(c[k]))
                if c[k] and k in ("Not compliant", "Not addressed"):
                    it.setForeground(D.color("crit"))
                self.table.setItem(i, j, it)
        r = R.Record(h.ws.root)
        ns = [n for n in r.notes(on="requirement") if n["text"].startswith(f"{stage} review: ")]
        self.notes.setRowCount(len(ns))
        for i, n in enumerate(ns):
            a = QTableWidgetItem(n["label"] or n["on_id"]); a.setData(Qt.UserRole, n["on_id"])
            self.notes.setItem(i, 0, a)
            self.notes.setItem(i, 1, QTableWidgetItem(n["text"][len(stage) + 9:]))
            self.notes.setItem(i, 2, QTableWidgetItem(R.short_date(n["at"])))
        self.notes.resizeRowsToContents()
        self.fill_disp()
        return sc

    # ------------------------------------------------------------ 3.39.0 comment dispositions
    def fill_disp(self):
        h = self.host
        if h.ws is None:
            return []
        import dispositions as DP
        r = R.Record(h.ws.root)
        stage = self.stage.currentText() or "Review"
        self.disp_sum.setText(f"{stage}: " + DP.summary(r, stage))
        rows = DP.items(r, stage, open_only=self.open_only.isChecked())
        people = [""] + list(h.people())
        self.dt.setRowCount(len(rows))
        for i, c in enumerate(rows):
            w = QTableWidgetItem(c.get("where", "") + (f"\n{c['file']}" if c.get("file") and c.get("source") == "draft" else ""))
            w.setData(Qt.UserRole, c["id"])
            self.dt.setItem(i, 0, w)
            self.dt.setItem(i, 1, QTableWidgetItem(c.get("author", "")))
            self.dt.setItem(i, 2, QTableWidgetItem(c.get("text", "")))
            cb = QComboBox(); cb.addItem("Open", "")
            for d_ in DP.DISPOSITIONS:
                cb.addItem(d_, d_)
            cb.setCurrentIndex(max(0, cb.findData(c.get("disposition", ""))))
            cb.activated.connect(lambda _i, cid=c["id"], box=cb: self.set_disp(cid, box.currentData()))
            self.dt.setCellWidget(i, 3, cb)
            rs = QLineEdit(c.get("reason", "")); rs.setPlaceholderText("Why (needed to reject)")
            rs.editingFinished.connect(lambda cid=c["id"], e=rs: self.set_disp(cid, None, reason=e.text()))
            self.dt.setCellWidget(i, 4, rs)
            ow = QComboBox(); ow.setEditable(True); ow.addItems(people); ow.setCurrentText(c.get("owner", ""))
            ow.activated.connect(lambda _i, cid=c["id"], box=ow: self.set_disp(cid, None, owner=box.currentText()))
            ow.lineEdit().editingFinished.connect(lambda cid=c["id"], box=ow: self.set_disp(cid, None, owner=box.currentText()))
            self.dt.setCellWidget(i, 5, ow)
            du = QLineEdit(c.get("due", "")); du.setPlaceholderText("YYYY-MM-DD")
            du.editingFinished.connect(lambda cid=c["id"], e=du: self.set_disp(cid, None, due=e.text()))
            self.dt.setCellWidget(i, 6, du)
        self.dt.resizeRowsToContents()
        return rows

    def set_disp(self, cid, disposition=None, reason=None, owner=None, due=None):
        """Change one comment (disposition None keeps it). Returns '' when saved, else why not."""
        import dispositions as DP
        r = R.Record(self.host.ws.root)
        c = DP.get(r, cid)
        if c is None:
            return "No such comment."
        why = DP.set_disposition(r, cid, c.get("disposition", "") if disposition is None else disposition, reason=reason, owner=owner, due=due)
        if why:
            self.host.status(why)
            self.fill_disp()
            return why
        if disposition is not None:
            self.fill_disp()
        else:
            self.disp_sum.setText(f"{self.stage.currentText() or 'Review'}: " + DP.summary(r, self.stage.currentText() or "Review"))
        return ""

    def read_drafts(self, paths=None):
        h = self.host
        if h.ws is None:
            return None
        import dispositions as DP
        if paths is None:
            folder = EF.folder(h.effort_path, "volumes") if h.effort_path else ""
            paths = [os.path.join(folder, f) for f in sorted(os.listdir(folder))] if folder and os.path.isdir(folder) else []
            if not paths:
                h.status("No drafts in the Volumes folder yet.")
                return None
        stage = self.stage.currentText() or "Review"
        res = DP.from_drafts(R.Record(h.ws.root), paths, stage)
        diag.activity("draft_comments_read", n=res["added"])
        n_files = sum(1 for _f, k in res["files"] if k > 0)
        h.status(f"{res['added']} new comment(s) from {n_files} draft(s), each under its heading.")
        self.fill_disp()
        return res

    def export_disp(self, path=None):
        h = self.host
        if h.ws is None:
            return ""
        import dispositions as DP
        stage = self.stage.currentText() or "Review"
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save the disposition log", h.out_path("comment_log", Stage=stage),
                                                  "Excel (*.xlsx)")
            if not path:
                return ""
        DP.export_xlsx(path, R.Record(h.ws.root), stage, h.effort_name or "")
        diag.activity("comment_log_exported")
        return path

    def build(self, path=None):
        h = self.host
        if h.review is None:
            return None
        stage = self.stage.currentText() or "Review"
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save the review packet", h.out_path("review_packet", Stage=stage),
                                                  "Word (*.docx)")
            if not path:
                return None
        try:
            res = RP.build(h.review.M, path, h.effort_name, stage, self.reviewers.text().strip())
        except PermissionError:
            h.status("That file is open in Word. Close it, then build again.")
            return None
        R.Record(h.ws.root).log("review", f"{stage} review packet built: {res['rows']} requirements in {res['sections']} sections", save=True)
        diag.activity("qt_review_packet_built", n=res["rows"])
        h.toast(f"Review packet: {res['rows']} requirements")
        return res

    def read_back(self, path=None):
        h = self.host
        if h.review is None:
            return None
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Read back a review packet", os.path.dirname(h.review.M.path), "Word (*.docx)")
            if not path:
                return None
        try:
            res = RP.read_back(path, h.review.M)
        except Exception:
            diag.swallowed()
            h.status("That file could not be read as a review packet.")
            return None
        stage = res["stage"] or self.stage.currentText() or "Review"
        h.review.snap()
        out = RP.apply(h.review.M, R.Record(h.ws.root), res, stage)
        h.changed()
        diag.activity("qt_review_packet_read", n=out["verdicts"])
        h.toast(f"{stage} review read back: {out['verdicts']} verdicts, {out['notes']} comments, {out.get('comments', 0)} to disposition"
                + (f"; {len(res['unknown'])} rows with an ID not in the matrix" if res["unknown"] else ""))
        self.stage.setCurrentText(stage)
        self.fill()
        return {**out, "unknown": res["unknown"], "stage": stage}

    def open_row(self, row):
        it = self.notes.item(row, 0)
        if it is None:
            return None
        iid = it.data(Qt.UserRole)
        self.host.go("assign")
        self.host.assign_page.select(iid)
        return iid
