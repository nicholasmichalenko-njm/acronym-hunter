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

from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QInputDialog, QHBoxLayout, QHeaderView, QLabel, QMainWindow, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)

import diag
from . import design as D

FOLDER = "acronym_tool"
LIST_NAME = "Acronym_Finder_List.xlsx"
_OPEN = []                      # the open tool windows (kept while open)


class ToolHost:
    """What the acronym page needs from a main window, for the tool's own list."""
    def __init__(self, win, config_dir, name=None):
        import acrlists as AL
        self.win, self.config_dir = win, config_dir
        self.root = os.path.join(config_dir, FOLDER)
        self.efforts = {}
        self.use(name or AL.last(self.root))

    def use(self, name):
        """3.51.0: open one of the named lists (its own folder: files, results, choices and list)."""
        import acrlists as AL
        import workspace as W
        self.name = name if name in AL.names(self.root) else AL.FIRST
        where = AL.folder(self.root, self.name)
        self.ws = W.Workspace(where, "Acros & Abs Finder" if self.name == AL.FIRST else f"Acros & Abs Finder: {self.name}")
        self.effort_path = os.path.join(where, LIST_NAME)
        AL.remember(self.root, self.name)

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
        if (d.get("effort") or "") == "Not a term" or t.startswith("["):
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
        self.setWindowTitle("Acros & Abs Finder - Stationkeeper")
        self.resize(1440, 900)
        self.host = ToolHost(self, config_dir)
        from .acronympage import AcronymPage
        root = QWidget(); v = QVBoxLayout(root); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"])
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(D.label("Acros & Abs Finder", "title"))
        bar.addWidget(D.label("Its own list on this PC, apart from every effort. Scan, check the meanings and where each was "
                              "found, then export the list.", "muted"), 1)
        self.b_export = D.button("Export the list...", "primary", lambda: self.export(), "Each term and its meaning: Word "
                                 "(a two-column table), Excel or CSV")
        self.b_first = D.button("Check first use...", None, lambda: self.first_use(), "Your own Word files, in order: where each "
                                "acronym first appears and whether it is spelled out there")
        self.b_new = D.button("Start a new list", "ghost", lambda: self.new_list(), "Clear the results and the list (the files are untouched)")
        for b in (self.b_export, self.b_first, self.b_new):
            bar.addWidget(b)
        lists = QHBoxLayout(); v.addLayout(lists)                         # 3.51.0: named lists
        lists.addWidget(D.label("List", "label"))
        self.pick = QComboBox(); self.pick.setMinimumWidth(220)
        self.pick.activated.connect(lambda _i: self.open_list(self.pick.currentText()))
        lists.addWidget(self.pick)
        self.b_newlist = D.button("New list...", "ghost", lambda: self.make_list(), "Another list beside this one: its own files, "
                                  "results and choices")
        self.b_rename = D.button("Rename...", "ghost", lambda: self.rename_list())
        self.b_add = D.button("Add files...", None, lambda: self.add_files(), "Scan this list's files again with more added")
        self.b_gone = D.button("Clear no longer found", "ghost", lambda: self.clear_gone(), "Take the terms the last scan no "
                               "longer found off this list")
        for b in (self.b_newlist, self.b_rename, self.b_add, self.b_gone):
            lists.addWidget(b)
        lists.addStretch(1)
        self.page = AcronymPage(self.host)
        self.page.tool_mode()
        v.addWidget(self.page, 1)
        self.setCentralWidget(root)
        self.page.load()
        self.fill_lists()
        diag.activity("acronym_tool_opened")

    # ---- named lists (3.51.0)
    def fill_lists(self):
        import acrlists as AL
        self.pick.blockSignals(True)
        self.pick.clear(); self.pick.addItems(AL.names(self.host.root))
        self.pick.setCurrentText(self.host.name)
        self.pick.blockSignals(False)
        self.b_rename.setEnabled(self.host.name != AL.FIRST)
        self.setWindowTitle(("Acros & Abs Finder" if self.host.name == AL.FIRST else f"Acros & Abs Finder: {self.host.name}") + " - Stationkeeper")

    def open_list(self, name):
        if self.page.worker is not None:
            self.host.status("Wait for the scan to finish, or stop it, then open another list.")
            self.fill_lists()
            return False
        if self.page.session is not None:
            self.page.session.save()
        self.host.use(name)
        self.page.load()
        self.fill_lists()
        self.host.status(f"Opened {self.host.name}.")
        return True

    def make_list(self, name=None):
        import acrlists as AL
        if name is None:
            name, ok = QInputDialog.getText(self, "New list", "Name of the new list:")
            if not ok:
                return ""
        n = AL.create(self.host.root, name)
        if not n:
            self.host.status("That name is empty or already used.")
            return ""
        self.open_list(n)
        return n

    def rename_list(self, new=None):
        import acrlists as AL
        if new is None:
            new, ok = QInputDialog.getText(self, "Rename the list", "New name:", text=self.host.name)
            if not ok:
                return ""
        old = self.host.name
        n = AL.rename(self.host.root, old, new)
        if not n:
            self.host.status("That name is empty or already used, or this is the first list.")
            return ""
        self.host.use(n); self.page.load(); self.fill_lists()
        return n

    def add_files(self, more=None):
        import acrlists as AL
        import app_gui as A
        if more is None:
            exts = " ".join("*" + e for e in sorted(A.SUPPORTED_EXTS))
            more, _ = QFileDialog.getOpenFileNames(self, "Add files to this list", "", f"Documents and pictures ({exts})")
            if not more:
                return None
        s = self.page.session
        last = ((s.last_scan or {}).get("paths") if s is not None else None) or []
        return self.page.scan(AL.add_files(last, more))

    def clear_gone(self):
        import acrlists as AL
        s = self.page.session
        if s is None:
            return []
        terms = AL.clear_gone(s)
        self.page.fill()
        self.host.status(f"{len(terms)} term(s) no longer found taken off this list." if terms else "Every term on this list was found in the last scan.")
        return terms

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
        report["tables"] = table_checks(s, paths)          # 3.88.0: each volume's own Acronyms table against the list
        self.page.fill()
        if run:
            FirstUseDialog(self, report).exec()
        return report


def table_checks(session, paths):
    """3.88.0 (decision 7): each volume's own Acronyms table against what its text uses: listed but not used, used but
    not listed (from the effort's list)."""
    import acrdrafts as AD
    listed = [t for t, d in session.results.items() if d.get("effort") == "In the list"]
    out = []
    for p in paths:
        try:
            r = AD.table_check(p, listed)
        except Exception:  # noqa: BLE001  a file that cannot be read is left out of this tab
            diag.swallowed()
            continue
        for t in r["listed_not_used"]:
            out.append({"volume": os.path.basename(p), "term": t, "state": "In its Acronyms table, not used in its text"})
        for t in r["used_not_listed"]:
            out.append({"volume": os.path.basename(p), "term": t, "state": "Used in its text, not in its Acronyms table"})
        if not r["table"]:
            out.append({"volume": os.path.basename(p), "term": "", "state": "No Acronyms table found in this file"})
    return out


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
        tb = report.get("tables", [])                          # 3.88.0
        tt = QTableWidget(len(tb), 3); tt.setHorizontalHeaderLabels(["File", "Acronym", "Its Acronyms table"])
        tt.verticalHeader().setVisible(False); tt.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for r, row in enumerate(tb):
            for c_, k in enumerate(("volume", "term", "state")):
                tt.setItem(r, c_, QTableWidgetItem(str(row.get(k) or "")))
        tabs.addTab(tt, f"Each volume's Acronyms table ({len(tb)})")
        self.tables_tab = tt
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
        V.write_excel(self.report, path, "Acros & Abs Finder")
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
