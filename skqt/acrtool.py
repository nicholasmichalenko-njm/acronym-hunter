"""Acronym Finder (3.50.0): the acronym scan as a tool in its own window, for the quick jobs that need no effort.

Scan files or a folder (customer documents, your own drafts or submittals, pictures, PDFs); every acronym, abbreviation,
unit and symbol is listed with its meaning and where it was found: the picture or page it is on, every find boxed, or
the passage it is in (foundview). Choose a meaning, type one, mark not a term. Export the list (Word, Excel or CSV):
each term and its meaning, ready to paste into a volume. Check first use in your own Word files: where each acronym
first appears, and whether it is spelled out there.

The window keeps its own list on this PC (<config>\\acronym_tool), apart from every effort; it reopens with the last
scan. Open it from its button at the foot of the main window's menu (the arrow lists every tool), from Acronyms > Open in its own window, or start the
program with --acronyms for this window alone. Rules and the trained readers only (No AI); nothing leaves the PC."""
import csv
import os

from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMainWindow, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)

import diag
from . import design as D

FOLDER = "acronym_tool"
LIST_NAME = "Acronym_Finder_List.xlsx"
_OPEN = []                      # the open tool windows (kept while open)


class ToolHost:
    """What the acronym page needs from a main window, for the tool's own list."""
    def __init__(self, win, config_dir):
        import workspace as W
        self.win, self.config_dir = win, config_dir
        root = os.path.join(config_dir, FOLDER)
        self.ws = W.Workspace(root, "Acronym Finder")
        self.effort_path = os.path.join(root, LIST_NAME)
        self.efforts = {}

    def status(self, text):
        self.win.statusBar().showMessage(str(text), 12000)

    def toast(self, text):
        self.status(text)

    def out_path(self, name):
        base = os.path.join(os.path.expanduser("~"), "Documents")
        return os.path.join(base if os.path.isdir(base) else os.path.expanduser("~"), f"{name}.csv")


def list_rows(session, terms=None):
    """[(term, meaning)] for the list to export: every term found that is not excluded, not rejected, not a plural or
    form (tied to its term) and not on the omit list; sorted as the list shows them."""
    out = []
    for t, d in session.results.items():
        if terms is not None and t not in terms:
            continue
        if d.get("excluded") or d.get("known") or d.get("plural_of") or d.get("form_of") or d.get("gone") or d.get("file_error"):
            continue
        if (d.get("effort") or "") == "Rejected" or t.startswith("["):
            continue
        meaning = d.get("selected_definition") or ""
        if meaning == "Keep All Possibilities":
            meaning = "; ".join(x for x in d.get("definitions", []) if x)
        out.append((t, meaning))
    return sorted(out, key=lambda r: r[0].casefold())


def export_list(rows, path):
    """Writes the list: .docx (a two-column table), .xlsx or .csv. Returns the number of rows."""
    low = path.lower()
    if low.endswith(".docx"):
        import volcheck as V
        V.write_docx(rows, path)
    elif low.endswith(".xlsx"):
        import openpyxl
        from openpyxl.styles import Font
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Acronyms"
        ws.append(["Acronym", "Meaning"])
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append(list(r))
        ws.column_dimensions["A"].width = 18; ws.column_dimensions["B"].width = 70
        wb.save(path)
    else:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["Acronym", "Meaning"]); w.writerows(rows)
    return len(rows)


class AcronymToolWindow(QMainWindow):
    def __init__(self, config_dir):
        super().__init__()
        self.setWindowTitle("Acronym Finder - Stationkeeper")
        self.resize(1440, 900)
        self.host = ToolHost(self, config_dir)
        from .acronympage import AcronymPage
        root = QWidget(); v = QVBoxLayout(root); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"])
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(D.label("Acronym Finder", "title"))
        bar.addWidget(D.label("Its own list on this PC, apart from every effort. Scan, check the meanings and where each was "
                              "found, then export the list.", "muted"), 1)
        self.b_export = D.button("Export the list...", "primary", lambda: self.export(), "Each term and its meaning: Word "
                                 "(a two-column table), Excel or CSV")
        self.b_first = D.button("Check first use...", None, lambda: self.first_use(), "Your own Word files, in order: where each "
                                "acronym first appears and whether it is spelled out there")
        self.b_new = D.button("Start a new list", "ghost", lambda: self.new_list(), "Clear the results and the list (the files are untouched)")
        for b in (self.b_export, self.b_first, self.b_new):
            bar.addWidget(b)
        self.page = AcronymPage(self.host)
        self.page.tool_mode()
        v.addWidget(self.page, 1)
        self.setCentralWidget(root)
        self.page.load()
        diag.activity("acronym_tool_opened")

    def closeEvent(self, e):
        if self in _OPEN:
            _OPEN.remove(self)
        super().closeEvent(e)

    # ---- the list
    def export(self, path=None):
        s = self.page.session
        rows = list_rows(s) if s is not None else []
        if not rows:
            self.host.status("Nothing to export yet: scan files first.")
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the acronym list", self.host.out_path("Acronym_List")[:-4] + ".docx",
                                                  "Word table (*.docx);;Excel (*.xlsx);;CSV (*.csv)")
            if not path:
                return None
        try:
            n = export_list(rows, path)
        except PermissionError:
            self.host.status("That file is open. Close it, then export again.")
            return None
        diag.activity("acronym_tool_exported", n=n)
        self.host.status(f"{n} terms exported to {path}")
        return path

    def new_list(self):
        s = self.page.session
        if s is None:
            return False
        s.results, s.manual_items, s.scanned_paths, s.last_scan = {}, {}, {}, None
        s.save()
        if s.effort is not None:
            for t in list(s.effort.rows):
                s.effort.remove(t)
            s._save_effort_list(backup=False)
        self.page.fill()
        self.host.status("A new list: scan files to start.")
        return True

    # ---- first use in your own Word files
    def first_use(self, paths=None, run=True):
        """Scans your Word files in order and shows first use for each acronym. Returns the report (or None)."""
        s = self.page.session
        if s is None:
            return None
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Check first use: your Word files (in submission order)", "", "Word (*.docx)")
            if not paths:
                return None
        self.host.status("Reading your files for first use...")
        try:
            report = s.qa_check(paths, lambda m: None)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"First use could not be checked ({type(e).__name__}).")
            return None
        if report is None:
            self.host.status("First use needs Word files (.docx) with different names.")
            return None
        self.page.fill()
        if run:
            FirstUseDialog(self, report).exec()
        return report


class FirstUseDialog(QDialog):
    COLS = (("check", "Check"), ("volume", "File"), ("term", "Acronym"), ("state", "Result"), ("loc", "First use in text"),
            ("written", "Written as"), ("in_figures", "In figures or tables"), ("also_defined", "Also defined at"))

    def __init__(self, parent, report):
        super().__init__(parent)
        import volcheck as V
        self.report = report
        self.setWindowTitle("First use"); self.resize(1200, 700)
        v = QVBoxLayout(self)
        s = report.get("summary", {})
        c = s.get("checks", {})
        v.addWidget(D.label(f"{c.get(V.BAD, 0)} to fix, {c.get(V.WARN, 0)} to check, {c.get(V.OK, 0)} OK. First use "
                            f"{V.RULE_SHORT.get(s.get('rule'), s.get('rule', ''))}. Order: " + "  >  ".join(report.get("volumes", [])), "muted"))
        tabs = QTabWidget(); v.addWidget(tabs, 1)
        rows = report.get("first_use", [])
        t = QTableWidget(len(rows), len(self.COLS)); t.setHorizontalHeaderLabels([h for _k, h in self.COLS])
        t.verticalHeader().setVisible(False); t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        for r, row in enumerate(rows):
            for c_, (k, _h) in enumerate(self.COLS):
                val = V.CHECK_MARKS.get(row.get("level"), "") if k == "check" else str(row.get(k) or "")
                it = QTableWidgetItem(val); it.setToolTip(val)
                if k == "check":
                    it.setForeground(D.color({V.BAD: "crit", V.WARN: "warn", V.OK: "ok"}.get(row.get("level"), "muted")))
                t.setItem(r, c_, it)
        tabs.addTab(t, f"First use ({len(rows)})")
        miss = report.get("missing", [])
        mt = QTableWidget(len(miss), 3); mt.setHorizontalHeaderLabels(["Term", "Files", "First found at"])
        mt.verticalHeader().setVisible(False); mt.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for r, row in enumerate(miss):
            for c_, k in enumerate(("term", "volumes", "loc")):
                mt.setItem(r, c_, QTableWidgetItem(str(row.get(k) or "")))
        tabs.addTab(mt, f"Not in the list ({len(miss)})")
        self.table = t
        br = QHBoxLayout(); v.addLayout(br)
        br.addWidget(QLabel("")); br.addStretch(1)
        br.addWidget(D.button("Export the report...", None, lambda: self.export()))
        br.addWidget(D.button("Close", "ghost", self.accept))

    def export(self, path=None):
        import volcheck as V
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "First use report", os.path.join(os.path.expanduser("~"), "First_Use.xlsx"), "Excel (*.xlsx)")
            if not path:
                return None
        V.write_excel(self.report, path, "Acronym Finder")
        return path


def open_tool(config_dir):
    """Opens the Acronym Finder window (or brings the open one forward). Returns it."""
    for w in _OPEN:
        w.show(); w.raise_(); w.activateWindow()
        return w
    w = AcronymToolWindow(config_dir)
    _OPEN.append(w)
    w.show()
    return w
