"""Production > Audit (3.17.0): Word, Excel and PowerPoint files checked against every standard that applies to them
(their volume in Production Standards: styles, fonts, tables, captions, the TOC, cross-references, pages, headers and
footers, lists, terms, sheets, slides and graphics), with every finding listed and exported. Read only: each file is
read once into memory; nothing is changed, no copy is made, and a file open on SharePoint is never touched. Fix a Copy
makes the dated copy with fixes. Rules only (No AI; the optional text-size estimate inside pictures uses the OCR reader
on this PC). Nothing leaves the PC."""
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QListWidget, QListWidgetItem,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import bgwork
import diag
import effortfolders as EF
import prodfix as PF
from . import design as D

EXTS = (".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pptm")


class AuditPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.results = {}                 # path -> (profile name, Check)
        self._work, self._result, self._progress = None, None, ""
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = D.Card("Files to audit", "Each file is checked against its volume in Production Standards: every rule that "
                     "applies to it. Read only: nothing is changed and no copy is made. Fix a Copy makes a dated copy with "
                     "fixes.", key=True,
                     actions=[D.button("Add the Volumes folder", None, lambda: self.add_volumes(), "Every Word, Excel and PowerPoint file in the effort's Volumes folder"),
                              D.button("Add files...", None, lambda: self.add_files()),
                              D.button("Take out", "ghost", lambda: self.remove())])
        self.files = QListWidget(); self.files.setSelectionMode(QAbstractItemView.ExtendedSelection); self.files.setMaximumHeight(110)
        top.add(self.files)
        row = QHBoxLayout()
        self.status = D.label("Add files, then Audit.", "muted"); row.addWidget(self.status, 1)
        self.export_btn = D.button("Export findings...", None, lambda: self.export(), "Every finding of every file, in one workbook")
        self.run_btn = D.button("Audit", "primary", lambda: self.run(), "Check every listed file against its standards")
        row.addWidget(self.export_btn); row.addWidget(self.run_btn)
        top.body.addLayout(row)
        v.addWidget(top)
        split = QSplitter(Qt.Vertical)
        res = D.Card("Results", "One row per file: what each area found. Click a file to see its findings.")
        self.areas = list(PF.AREAS.keys())
        self.table = QTableWidget(0, 3 + len(self.areas))
        self.table.setHorizontalHeaderLabels(["File", "Volume", "Total"] + [PF.AREAS[a] for a in self.areas])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 3 + len(self.areas)):
            self.table.setColumnWidth(c, 64 if c == 2 else 110)
            self.table.horizontalHeaderItem(c).setToolTip(self.table.horizontalHeaderItem(c).text())
        self.table.itemSelectionChanged.connect(self.show_findings)
        res.add(self.table)
        split.addWidget(res)
        det = D.Card("Findings")
        frow = QHBoxLayout(); frow.addWidget(D.label("Area", "label", wrap=False))
        self.area_f = QComboBox(); self.area_f.addItem("Every area", "")
        for a in self.areas:
            self.area_f.addItem(PF.AREAS[a], a)
        self.area_f.currentIndexChanged.connect(lambda _i: self.show_findings()); frow.addWidget(self.area_f); frow.addStretch(1)
        det.body.addLayout(frow)
        self.found = QTableWidget(0, 5); self.found.setHorizontalHeaderLabels(["Area", "Rule", "What", "Where", "Fix a Copy"])
        self.found.verticalHeader().setVisible(False); self.found.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.found.setWordWrap(True)
        self.found.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for c, w in ((0, 150), (1, 220), (3, 220), (4, 150)):
            self.found.setColumnWidth(c, w)
        det.add(self.found)
        split.addWidget(det); split.setSizes([300, 420])
        v.addWidget(split, 1)
        self.timer = QTimer(self, interval=250, timeout=self.tick)
        self.empty_state()

    # ------------------------------------------------------------------ the files
    def refresh(self):
        if not self.files.count() and self.host.ws is not None:
            self.add_volumes(quiet=True)
        self.empty_state()

    def empty_state(self):
        self.run_btn.setEnabled(bool(self.files.count()) and not self.running())
        self.export_btn.setEnabled(bool(self.results))

    def paths(self):
        return [self.files.item(i).data(Qt.UserRole) for i in range(self.files.count())]

    def add_paths(self, paths):
        have = {os.path.normcase(p) for p in self.paths()}
        n = 0
        for p in paths:
            if p.lower().endswith(EXTS) and not os.path.basename(p).startswith("~$") and os.path.normcase(p) not in have:
                it = QListWidgetItem(os.path.basename(p)); it.setData(Qt.UserRole, p); it.setToolTip(p)
                self.files.addItem(it); have.add(os.path.normcase(p)); n += 1
        self.empty_state()
        return n

    def add_volumes(self, quiet=False):
        if not self.host.effort_path:
            if not quiet:
                self.status.setText("Open an effort first, or Add files...")
            return 0
        d = EF.folder(self.host.effort_path, "volumes")
        paths = [os.path.join(d, f) for f in sorted(os.listdir(d))] if os.path.isdir(d) else []
        n = self.add_paths(paths)
        if not quiet:
            self.status.setText(f"{n} file(s) added from the Volumes folder." if n else "No new Word, Excel or PowerPoint files in the Volumes folder.")
        return n

    def add_files(self, paths=None):
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Files to audit", "", "Word, Excel and PowerPoint (*.docx *.docm *.xlsx *.xlsm *.pptx *.pptm)")
        return self.add_paths(paths or [])

    def remove(self):
        for it in self.files.selectedItems():
            self.results.pop(it.data(Qt.UserRole), None)
            self.files.takeItem(self.files.row(it))
        self.fill()
        self.empty_state()

    # ------------------------------------------------------------------ the audit
    def running(self):
        return self._work is not None and self._work.is_alive()

    def std_for(self, path):
        """The file's standard: the same volume Fix a Copy would use (its deliverable's, the effort type's match, the effort's)."""
        return self.host.fixcopy_page.std_for(path)

    def run(self, wait=False):
        paths = self.paths()
        if not paths or self.running():
            return None
        stds = {}
        for p in paths:
            try:
                stds[p] = self.std_for(p)
            except Exception:  # noqa: BLE001
                diag.swallowed()
        self._result, self._progress = None, ""
        self.status.setText(f"Auditing {len(paths)} file(s)...")
        self.run_btn.setEnabled(False)

        def job():
            out = {}
            for k, p in enumerate(paths, 1):
                self._progress = f"Auditing {k} of {len(paths)}: {os.path.basename(p)}"
                if p not in stds:
                    continue
                try:
                    out[p] = (stds[p].get("name", ""), PF.check(p, stds[p]))
                except Exception:  # noqa: BLE001
                    diag.swallowed()
            self._result = out
        self._work = bgwork.start(job, "stationkeeper-audit")
        diag.activity("audit_started", n=len(paths))
        if wait:
            bgwork.wait(self._work)
            return self.tick()
        self.timer.start()
        return None

    def tick(self):
        if self.running():
            self.status.setText(self._progress or "Auditing...")
            return None
        self.timer.stop()
        out = self._result or {}
        self._work = None
        self.results.update(out)
        self.fill()
        total = sum(c.count() for _n, c in out.values())
        self.status.setText(f"{len(out)} file(s) audited: {total} finding(s). Nothing was changed.")
        diag.activity("audit_done", n=len(out), rows=total)
        self.empty_state()
        return out

    def fill(self):
        t = self.table
        t.setRowCount(0)
        self._rows = []
        for p in self.paths():
            if p not in self.results:
                continue
            prof, chk = self.results[p]
            k = t.rowCount(); t.insertRow(k); self._rows.append(p)
            by = chk.by_area()
            unread = bool(chk.error) and not chk.findings
            vals = [os.path.basename(p), prof, "not read" if unread else str(chk.count())] + \
                   ["-" if unread else str(sum(by.get(a, {}).values()) or "") for a in self.areas]
            for c, text in enumerate(vals):
                it = QTableWidgetItem(text); it.setToolTip(chk.error.strip() if chk.error else p)
                if c >= 2 and text not in ("", "0", "-"):
                    it.setForeground(D.color("warn"))
                t.setItem(k, c, it)
        if t.rowCount():
            t.selectRow(0)
        self.show_findings()

    def show_findings(self):
        r = self.table.currentRow()
        rows = getattr(self, "_rows", [])
        self.found.setRowCount(0)
        if not (0 <= r < len(rows)):
            return 0
        _prof, chk = self.results[rows[r]]
        area = self.area_f.currentData()
        n = 0
        for f in chk.findings:
            if area and f["area"] != area:
                continue
            k = self.found.rowCount(); self.found.insertRow(k)
            fix = PF.FIX[f["fix"]]["label"] if f["fix"] in PF.FIX else ("Update fields in Word" if f["fix"] == "word_update" else "Review by hand")
            for c, text in enumerate((PF.AREAS.get(f["area"], f["area"]), f"{f['rule']} {PF.RULE_TEXT.get(f['rule'], '')}",
                                      f["what"], f["near"], fix)):
                self.found.setItem(k, c, QTableWidgetItem(str(text)))
            n += 1
        self.found.resizeRowsToContents()
        return n

    def export(self, path=None):
        if not self.results:
            self.status.setText("Audit first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the audit", self.host.out_path("audit"), "Excel (*.xlsx)")
            if not path:
                return ""
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        wb = Workbook()
        ws = wb.active; ws.title = "By file"
        ws.append(["File", "Volume", "Total"] + [PF.AREAS[a] for a in self.areas])
        for p, (prof, chk) in self.results.items():
            by = chk.by_area()
            ws.append([os.path.basename(p), prof, chk.count()] + [sum(by.get(a, {}).values()) for a in self.areas])
        ws2 = wb.create_sheet("Findings")
        ws2.append(["File", "Volume", "Area", "Rule", "What", "Where", "Fix a Copy"])
        for p, (prof, chk) in self.results.items():
            for f in chk.findings:
                ws2.append([os.path.basename(p), prof, PF.AREAS.get(f["area"], f["area"]), f"{f['rule']} {PF.RULE_TEXT.get(f['rule'], '')}",
                            f["what"], f["near"], PF.FIX[f["fix"]]["label"] if f["fix"] in PF.FIX else
                            ("Update fields in Word" if f["fix"] == "word_update" else "Review by hand")])
        for w_ in (ws, ws2):
            for c in w_[1]:
                c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
            for row in w_.iter_rows(min_row=2):
                for c in row:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
        for col, wd in zip("ABCDEFG", (36, 22, 22, 36, 80, 40, 40)):
            ws2.column_dimensions[col].width = wd
        ws.column_dimensions["A"].width = 36
        wb.save(path)
        diag.activity("audit_exported", n=sum(c.count() for _n, c in self.results.values()))
        self.host.toast("Audit exported")
        return path
