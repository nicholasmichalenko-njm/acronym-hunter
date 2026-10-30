"""QA/QC in Qt (2.66.0): check our Word volumes against the effort list: first use in the running text, terms not in
the effort list, not approved, definitions that differ, list entries not used, each volume's own acronym list, banned
words and phrases, and page limits from the customer documents. Word (.docx) only. The rules and the report are the
classic window's own (volcheck, volcheck_ui); the report is kept in the effort's session. Rules only (No AI); nothing
leaves the PC."""
import os
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QHeaderView, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import app_gui as A
import volcheck as V
import volcheck_ui as VU
from . import design as D
from .adaptive import FlowLayout

LEVEL_TONE = {V.BAD: "crit", V.WARN: "warn", V.INFO: "accent", V.OK: "ok"}
RANK = {V.BAD: 0, V.WARN: 1, V.INFO: 2, V.OK: 3}


class QAWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, session, paths, reg_rows, volumes):
        super().__init__()
        self.session, self.paths, self.reg_rows, self.volumes = session, paths, reg_rows, volumes

    def run(self):
        try:
            r = self.session.qa_check(self.paths, lambda m: (A.check_cancel(), self.progress.emit(str(m))), self.reg_rows, self.volumes)
            self.finished_ok.emit(r)
        except A.ScanCancelled:
            self.failed.emit("cancelled")
        except Exception as e:
            diag.swallowed()
            self.failed.emit(type(e).__name__)


class QAPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.worker = None
        self.tables = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.where = D.label("<b>END</b> &nbsp;Only the documents you will submit, checked against the effort list, banned words "
                             "and page limits. The acronym lists to submit are built from this check (Lists to submit).", "muted")
        self.where.setTextFormat(Qt.RichText); v.addWidget(self.where)                  # 2.86.0
        vc = D.Card("Submission volumes", "Marked once: the Word files you will submit, in submission order. Volumes in "
                    "Deliverables with a Word file are included.")
        self.vol_list = QListWidget(); self.vol_list.setMaximumHeight(110); vc.add(self.vol_list)
        vrow = QHBoxLayout(); vc.body.addLayout(vrow)
        self.b_run = D.button("Check the submission volumes", "primary", lambda: self.check_volumes(), "Checks every volume listed here")
        vrow.addWidget(self.b_run)
        vrow.addWidget(D.button("Add volumes...", None, lambda: self.add_volumes()))
        vrow.addWidget(D.button("Take out", "ghost", lambda: self.remove_volume()))
        vrow.addStretch(1)
        v.addWidget(vc)
        top = FlowLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.b_check = D.button("Check other Word files...", None, lambda: self.pick(), "Any Word files, once (not saved as submission volumes)")
        self.b_cancel = D.button("Cancel", "danger", lambda: A.CANCEL.set()); self.b_cancel.hide()
        top.addWidget(self.b_check); top.addWidget(self.b_cancel)
        self.progress = D.label("", "muted", wrap=False); top.addWidget(self.progress, 1)
        self.b_export = D.button("Export report (Excel)...", None, lambda: self.export())
        self.b_lists = D.button("Lists to submit", None, lambda: self.host.go("lists"), "The acronym lists for your volumes, from this check")
        self.b_missing = D.button("Add missing to the effort list", None, lambda: self.add_missing())
        self.b_record = D.button("Record in the effort list", None, lambda: self.record(), "Used in volumes and First use, for terms in the list")
        for b in (self.b_export, self.b_lists, self.b_missing, self.b_record):
            top.addWidget(b)
        self.tiles = {k: D.Tile("-", cap, tone) for k, cap, tone in (("fix", "first-use fixes", "crit"), ("check", "to check", "warn"),
                                                                       ("ok", "defined at first use", "ok"), ("banned", "banned words", "crit"),
                                                                       ("pages", "over a page limit", "crit"), ("missing", "not in the effort list", "warn"),
                                                                       ("notappr", "not approved", "warn"))}
        self.tile_row = QWidget(); g = QGridLayout(self.tile_row); g.setContentsMargins(0, 0, 0, 0); g.setSpacing(D.SPACE["m"])
        for i, t in enumerate(self.tiles.values()):
            g.addWidget(t, 0, i); g.setColumnStretch(i, 1)
        v.addWidget(self.tile_row)
        self.order = D.label("", "muted"); v.addWidget(self.order)
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        self.empty = D.EmptyState("No submission check yet", "Add the Word volumes you will submit above, then check them against "
                                                             "the effort list: first use, missing and unapproved terms, banned words, "
                                                             "page limits.", "Add volumes...", lambda: self.add_volumes())
        v.addWidget(self.empty)

    @property
    def session(self):
        return self.host.acronym_page.session

    # ------------------------------------------------------------ 2.86.0 submission volumes, marked once
    def volumes(self):
        """[(path, where from)]: the effort's submission volumes (saved here, then Deliverables' Word files)."""
        h = self.host
        if h.ws is None:
            return []
        out, seen = [], set()
        for p in h.ws.get("submission_volumes", []) or []:
            k = os.path.normcase(os.path.abspath(p))
            if k not in seen:
                seen.add(k); out.append((p, "added here"))
        try:
            import effortrec as R
            for dl in R.Record(h.ws.root).data.get("deliverables", []):
                f = dl.get("file") or ""
                if f.lower().endswith(".docx") and (dl.get("kind") or "").lower().startswith("volume"):
                    k = os.path.normcase(os.path.abspath(f))
                    if k not in seen:
                        seen.add(k); out.append((f, "from Deliverables"))
        except Exception:
            diag.swallowed()
        return sorted(out, key=lambda x: V.natural_key(os.path.basename(x[0])))

    def fill_volumes(self):
        self.vol_list.clear()
        for p, src in self.volumes():
            here = os.path.isfile(p)
            it = QListWidgetItem(f"{os.path.basename(p)}   ({src}" + ("" if here else ", not on this PC") + ")")
            it.setData(0x0100, p)
            if not here:
                it.setForeground(D.color("warn"))
            self.vol_list.addItem(it)
        self.b_run.setEnabled(any(os.path.isfile(p) for p, _s in self.volumes()) and self.worker is None)

    def add_volumes(self, paths=None):
        if self.host.ws is None:
            return 0
        if paths is None:
            start = (self.host.efforts.get(self.host.effort_name) or {}).get("volumes_dir", "") or ""
            paths, _ = QFileDialog.getOpenFileNames(self, "The Word volumes you will submit", start, "Word documents (*.docx)")
        paths = [p for p in (paths or []) if p.lower().endswith(".docx")]
        if not paths:
            return 0
        have = list(self.host.ws.get("submission_volumes", []) or [])
        keys = {os.path.normcase(os.path.abspath(p)) for p in have}
        add = [p for p in paths if os.path.normcase(os.path.abspath(p)) not in keys]
        self.host.ws.set("submission_volumes", have + add)
        diag.activity("submission_volumes_added", files=len(add))
        self.fill_volumes()
        return len(add)

    def remove_volume(self, path=None):
        it = self.vol_list.currentItem()
        path = path or (it.data(0x0100) if it else None)
        have = list(self.host.ws.get("submission_volumes", []) or []) if self.host.ws is not None else []
        keep = [p for p in have if os.path.normcase(os.path.abspath(p)) != os.path.normcase(os.path.abspath(path or ""))]
        if path is None or len(keep) == len(have):
            self.host.status("Only volumes added here can be taken out; Deliverables' volumes are changed in Deliverables.")
            return False
        self.host.ws.set("submission_volumes", keep)
        self.fill_volumes()
        return True

    def check_volumes(self):
        paths = [p for p, _s in self.volumes() if os.path.isfile(p)]
        if not paths:
            self.host.status("Add the Word volumes you will submit first.")
            return None
        return self.check(paths)

    def refresh(self):
        h = self.host
        if h.ws is not None and self.session is None:
            h.acronym_page.load()
        self.setEnabled(h.ws is not None)
        self.fill_volumes()
        self.show_report(self.session.volume_report if self.session is not None else None)

    def pick(self):
        start = ""
        try:
            start = (self.host.efforts.get(self.host.effort_name) or {}).get("volumes_dir", "") or ""
        except Exception:
            diag.swallowed()
        paths, _ = QFileDialog.getOpenFileNames(self, "Word deliverables to check (submission order follows the file names)", start,
                                                "Word documents (*.docx)")
        if paths:
            self.check(paths)

    def check(self, paths):
        s = self.session
        if s is None or self.worker is not None:
            return None
        docx = [p for p in paths if p.lower().endswith(".docx")]
        if not docx:
            self.host.status(VU.WORD_ONLY)
            return None
        names = [os.path.basename(p) for p in docx]
        if len(set(names)) != len(names):
            self.host.status("Two volumes have the same file name. Rename one so the report can tell them apart.")
            return None
        from .custdocs import Ctx
        try:
            c = Ctx(self.host)
            reg_rows, vols = c.reg.rows(), c.volumes()
        except Exception:
            diag.swallowed(); reg_rows, vols = [], []
        self.worker = QAWorker(s, docx, reg_rows, vols)
        self.worker.progress.connect(self.progress.setText)
        self.worker.finished_ok.connect(self.done)
        self.worker.failed.connect(self.failed)
        self.b_check.setEnabled(False); self.b_run.setEnabled(False); self.b_cancel.show()
        self.worker.start()
        return self.worker

    def _end(self):
        if self.worker is not None:
            self.worker.wait(2000)
        self.worker = None
        self.b_check.setEnabled(True); self.b_cancel.hide(); self.progress.setText("")
        self.fill_volumes()

    def done(self, report):
        self._end()
        if report:
            try:
                import effortrec as R
                R.Record(self.host.ws.root).log("qa", VU.qa_log_text(report), save=True)
            except Exception:
                diag.swallowed()
        self.show_report(report)
        self.host.toast("QA/QC check done" if report else "Nothing to check")
        return report

    def failed(self, why):
        self._end()
        self.host.status("QA/QC stopped." if why == "cancelled" else f"The check failed ({why}). Details are in the logs (no file names or content).")

    # ------------------------------------------------------------ the report
    def _table(self, title, cols, rows, keys, level=False):
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.verticalHeader().setVisible(False); t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows); t.setAlternatingRowColors(not level); t.setWordWrap(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        t.horizontalHeader().setStretchLastSection(True)
        if level:
            rows = sorted(rows, key=lambda r: RANK.get(r.get("level", ""), 4))
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for c, k in enumerate(keys):
                it = QTableWidgetItem(str(r.get(k, "") if r.get(k, "") is not None else ""))
                if level and r.get("level") in LEVEL_TONE:
                    it.setBackground(D.color(LEVEL_TONE[r["level"]] + "_soft") if LEVEL_TONE[r["level"]] + "_soft" in D.tokens() else D.color("surface2"))
                t.setItem(i, c, it)
        t.resizeColumnsToContents()
        for c in range(len(cols)):
            t.setColumnWidth(c, min(max(t.columnWidth(c), 70), 380))
        t.resizeRowsToContents()
        t.cellDoubleClicked.connect(lambda row, _c, rows=rows: self.jump(rows[row]))
        self.tabs.addTab(t, f"{title} ({len(rows)})")
        self.tables[title] = (t, rows)
        return t

    def show_report(self, r):
        self.tabs.clear(); self.tables = {}
        on = bool(r)
        self.empty.setVisible(not on)
        for w in (self.tile_row, self.order, self.tabs, self.b_export, self.b_lists, self.b_missing, self.b_record):
            w.setVisible(on)
        if not on:
            return None
        s = r["summary"]
        c = s.get("checks", {})
        bc = s.get("banned", {})
        pg = r.get("pages") or []
        vals = {"fix": c.get(V.BAD, 0), "check": c.get(V.WARN, 0), "ok": c.get(V.OK, 0),
                "banned": bc.get(V.BAD, 0) if s.get("banned_checked") else "-", "pages": sum(1 for x in pg if x["level"] == V.BAD) if pg else "-",
                "missing": s["missing"], "notappr": s["not_approved"]}
        for k, t in self.tiles.items():
            n = vals[k]
            t.set(n, None, ("ok" if n == 0 or n == "-" else t.tone) if k != "ok" else "ok")
        rule = V.RULE_SHORT.get(s["rule"], s["rule"])
        self.order.setText(f"First use {rule}.  Order: " + "  >  ".join(r["volumes"]) + ".  Double-click a row to open the term in Scan and review.")
        self.b_missing.setText(f"Add {s['missing']} missing to the effort list"); self.b_missing.setEnabled(bool(s["missing"]))
        if s["rule"] == "section":
            self._table("First use", ["Check", "Volume", "Section", "Acronym", "Result", "First use in text", "In figures or tables", "Written as",
                                      "Effort list says", "Also defined at"], r["first_use"],
                        ["check", "volume", "section", "term", "state", "loc", "in_figures", "written", "list_definition", "also_defined"], level=True)
        else:
            self._table("First use", ["Check", "Volume", "Acronym", "Result", "First use in text", "In figures or tables", "Written as",
                                      "Effort list says", "Also defined at"], r["first_use"],
                        ["check", "volume", "term", "state", "loc", "in_figures", "written", "list_definition", "also_defined"], level=True)
        if pg:
            self._table("Page limits", ["Check", "Volume", "Limit for", "Limit", "Pages (Word's count)", "Result", "From"], pg,
                        ["check", "volume", "limit_for", "limit", "pages", "result", "source"], level=True)
        if s.get("banned_checked"):
            self._table("Banned words", ["Check", "Volume", "Found", "Banned phrase", "Use instead", "Where", "Sentence", "Why"],
                        r.get("banned", []), ["check", "volume", "found", "phrase", "use", "where", "sentence", "why"], level=True)
        if r.get("acronym_list"):
            self._table("Acronym list", ["Check", "Volume", "Acronym", "Result", "In the list as", "Effort list says", "Uses outside the list"],
                        r["acronym_list"], ["check", "volume", "term", "state", "listed_as", "list_definition", "uses"], level=True)
        self._table("Not in effort list", ["Term", "Type", "Count", "Volumes", "Suggested definition", "First found at"], r["missing"],
                    ["term", "type", "count", "volumes", "suggestion", "loc"])
        self._table("Not approved", ["Term", "Status", "Definition", "Volumes", "First found at"], r["not_approved"],
                    ["term", "status", "definition", "volumes", "loc"])
        self._table("Definition differs", ["Term", "Volume", "Volume says", "Effort list says", "Where"], r["differs"],
                    ["term", "volume", "written", "list_definition", "loc"])
        self._table("Unused", ["Term", "Type", "Status", "Definition"], r["unused"], ["term", "type", "status", "definition"])
        for i, vol in enumerate(r["volumes"], 1):
            self._table(f"List {i}: {vol[:24]}", ["Term", "Definition", "Status"], r["lists"].get(vol, []), ["term", "definition", "status"])
        return r

    def jump(self, row):
        term = (row or {}).get("term")
        ap = self.host.acronym_page
        if not term or ap.session is None or term not in ap.session.results:
            return None
        self.host.go("acronyms")
        ap.f_search.setText(""); ap.f_status.setCurrentIndex(0); ap.f_excl.setChecked(True)
        ap.select(term)
        return term

    # ------------------------------------------------------------ outputs
    def export(self, path=None):
        r = self.session.volume_report if self.session else None
        if not r:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save the QA/QC report", self.host.out_path("qaqc_report"), "Excel (*.xlsx)")
            if not path:
                return None
        try:
            V.write_excel(r, path, self.host.effort_name)
        except PermissionError:
            self.host.status("That file is open in Excel. Close it, then save again.")
            return None
        diag.activity("volume_check_exported", rows=len(r["first_use"]))
        self.host.toast("QA/QC report written. It holds customer content: keep it on this PC or SharePoint.")
        return path

    def lists(self, folder=None):
        r = self.session.volume_report if self.session else None
        if not r:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the acronym lists (one Word file per volume)",
                                                      self.host.out_path("acronym_lists"))
            if not folder:
                return None
        try:
            os.makedirs(folder, exist_ok=True)
            written, open_items = VU.qa_volume_lists(r, folder)
        except PermissionError:
            self.host.status("A list with that name is open in Word. Close it, then try again.")
            return None
        diag.activity("volume_lists_exported", files=len(written))
        self.host.toast(f"{len(written)} acronym list(s) written" + (f"; {open_items} entries not approved or without a definition" if open_items else ""))
        return written

    def add_missing(self):
        n = self.session.qa_add_missing()
        self.host.toast(f"{n} terms added to the effort list as Proposed")
        return n

    def record(self):
        n = self.session.qa_record_use()
        self.host.toast(f"Used in volumes and First use updated for {n} terms")
        return n
