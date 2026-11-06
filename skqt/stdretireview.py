"""Production Standards > What retiring this would lose (3.68.0): the nothing-lost report on one screen. The verdict,
each section with where it is edited now and this PC's own values in it, and the places in the app that still open
Production Standards. prodstdreport holds the rules; nothing is changed here."""
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout

import diag
import prodstdreport as PR
from . import design as D

STATUS = {PR.MOVED: "Edited elsewhere", PR.PARTLY: "Partly elsewhere", PR.ONLY: "Only here"}


class RetireReport(QDialog):
    def __init__(self, page, data=None):
        super().__init__(page)
        self.setWindowTitle("What retiring Production Standards would lose")
        self.resize(1100, 720)
        self.rep = PR.report(page.host.config_dir, data)
        v = QVBoxLayout(self)
        self.verdict = D.label(self.rep["verdict"], None); v.addWidget(self.verdict)
        rows = sorted(self.rep["rows"], key=lambda r: ({PR.ONLY: 0, PR.PARTLY: 1, PR.MOVED: 2}[r["status"]], r["title"]))
        self.table = QTableWidget(len(rows), 5)
        self.table.setHorizontalHeaderLabels(["Section", "Where it is edited now", "Stays only here", "Set on this PC", ""])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i, r in enumerate(rows):
            vals = "; ".join(f"{ln}: {w}" for ln, w in r["values"][:4]) + (" ..." if len(r["values"]) > 4 else "")
            for j, val in enumerate((r["title"], r["where"], r["stays"], vals or "nothing", STATUS[r["status"]])):
                c = QTableWidgetItem(val)
                if j == 4 and r["status"] != PR.MOVED:
                    c.setForeground(D.color("crit" if r["at_risk"] else "warn"))
                self.table.setItem(i, j, c)
        v.addWidget(self.table, 3)
        v.addWidget(D.SectionTitle("Places that still open Production Standards"))
        self.links = QTableWidget(len(self.rep["links"]), 3); self.links.setHorizontalHeaderLabels(["Where", "What it did", "Now"])
        self.links.verticalHeader().setVisible(False); self.links.setEditTriggers(QTableWidget.NoEditTriggers)
        self.links.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i, row in enumerate(self.rep["links"]):
            for j, val in enumerate(row):
                self.links.setItem(i, j, QTableWidgetItem(val))
        v.addWidget(self.links, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); bb.accepted.connect(self.accept)
        v.addWidget(bb)
        diag.activity("prodstd_retire_report", n=self.rep["at_risk"])


def show(page, data=None, modal=True):
    dlg = RetireReport(page, data)
    if modal:
        dlg.exec()
    return dlg
