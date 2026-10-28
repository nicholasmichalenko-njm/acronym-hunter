"""Prove in Qt (2.60.0): that every line of every RFP file was read and decided. Coverage per file (requirements,
context, the customer's, not used, assigned without a section) and the text check (every word of each file is in the
review), with any missing line added to the review in its place."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import compliance_read as CR
from . import design as D

COLS = [("file", "File"), ("total", "Sentences"), ("Keep", "Requirements"), ("Context", "Context"), ("Customer", "Customer's"),
        ("unused", "Not used"), ("needs_home", "No section yet")]


class ProvePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.results = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.pills = {}
        for key, text, tone in (("Keep", "requirements", "req"), ("Context", "context", "ctx"), ("unused", "not used", "head"),
                                ("needs_home", "without a section", "warn"), ("missing", "words not in the review", "crit")):
            p = D.Pill(f"0 {text}", tone); p.base = text
            self.pills[key] = p
            top.addWidget(p)
        top.addStretch(1)
        cov = D.Card("Coverage", "Every sentence of every file, by decision.")
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels([h for _k, h in COLS])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        cov.add(self.table)
        v.addWidget(cov, 1)
        self.check_btn = D.button("Run the text check", "primary", self.run_check, "Compare each file word for word with the review")
        self.add_btn = D.button("Add the missing lines", None, self.add_missing, "Each goes into the review where it is in the document")
        self.add_btn.setEnabled(False)
        tc = D.Card("Text check", "Every word of each RFP file, read straight from the file, compared with the review.",
                    actions=(self.add_btn, self.check_btn))
        self.check_line = D.label("Not run yet.", "muted")
        tc.add(self.check_line)
        self.missing = QTableWidget(0, 3)
        self.missing.setHorizontalHeaderLabels(["File", "Where", "Text not in the review"])
        self.missing.verticalHeader().setVisible(False)
        self.missing.setEditTriggers(QTableWidget.NoEditTriggers)
        self.missing.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.missing.setMaximumHeight(220)
        tc.add(self.missing)
        v.addWidget(tc)

    def refresh(self):
        R = self.host.review
        self.setEnabled(R is not None)
        if R is None:
            self.table.setRowCount(0)
            return
        rows = R.M.coverage()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            row = dict(row, unused=row.get("", 0) + row.get("Drop", 0))
            for c, (k, _h) in enumerate(COLS):
                val = row.get(k, "")
                item = QTableWidgetItem(str(val) if (val or k == "file") else "")
                if c:
                    item.setTextAlignment(Qt.AlignCenter)
                if row["file"] == "Total":
                    f = item.font(); f.setBold(True); item.setFont(f)
                self.table.setItem(r, c, item)
        tot = dict(rows[-1]) if rows else {}
        tot["unused"] = tot.get("", 0) + tot.get("Drop", 0)
        for key, p in self.pills.items():
            n = sum(r["missing"] for r in self.results) if key == "missing" else tot.get(key, 0)
            base = p.base[:-1] if (n == 1 and p.base.endswith("requirements")) else p.base
            p.setText(f"{n} {base}")
            if key == "needs_home":
                p.set_tone("warn" if n else "ok")
            if key == "missing":
                p.set_tone("crit" if n else "ok")

    def run_check(self):
        R = self.host.review
        if R is None:
            return []
        self.results = CR.text_check(R.M)
        diag.activity("compliance_text_check", files=len(self.results), n=sum(r["missing"] for r in self.results))
        self.check_line.setText(CR.text_check_line(self.results) + ("" if not any(r.get("gone") for r in self.results)
                                                                    else " Some files are no longer on this PC."))
        lines = [(r["file"], w, t) for r in self.results for w, t, kind in r.get("lines", []) if kind == "missing"]
        self.missing.setRowCount(len(lines))
        for i, (f, w, t) in enumerate(lines):
            for c, val in enumerate((f, w, " ".join(t.split()))):
                self.missing.setItem(i, c, QTableWidgetItem(val))
        self.add_btn.setEnabled(bool(lines))
        self.refresh()
        return self.results

    def add_missing(self):
        R = self.host.review
        if R is None or not self.results:
            return []
        R.snap()
        added = CR.add_missing(R.M, self.results)
        diag.activity("compliance_text_added", n=len(added))
        self.host.changed()
        self.host.assign_page.load()
        self.host.toast(f"{len(added)} line(s) added to the review in their place")
        self.run_check()
        return added
