"""The Section L/M crosswalk in Qt (2.61.0): each instruction beside the factor that evaluates it and the work it
describes, with the gaps flagged and how each link was found. Select a row to add or take out links; your links are
kept with the matrix. Export writes the crosswalk to Excel."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import crosswalk as X
from . import design as D

COLS = ["Section L", "Instruction", "Evaluated by (Section M)", "Work (Section C, SOW, PWS)", "Gaps"]


class CrosswalkPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.p_inst = D.Pill("0 instructions", "accent")
        self.p_noeval = D.Pill("0 not evaluated", "ok")
        self.p_noinst = D.Pill("0 factors with no instruction", "ok")
        for p in (self.p_inst, self.p_noeval, self.p_noinst):
            top.addWidget(p)
        top.addStretch(1)
        top.addWidget(D.button("Export the crosswalk...", "primary", self.export, "The crosswalk as an Excel workbook"))
        split = QSplitter(Qt.Horizontal)
        card = D.Card("Instructions, evaluation and work", "Found by rules: cross-references in the RFP, the same words in "
                                                          "section titles, a parent section's links, and your own.")
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setWordWrap(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        for i, wd in enumerate((90, 220, 240, 240)):
            self.table.setColumnWidth(i, wd)
        self.table.itemSelectionChanged.connect(self.show_detail)
        card.add(self.table)
        split.addWidget(card)
        self.detail = D.Card("Links")
        self.detail_body = QWidget(); self.dv = QVBoxLayout(self.detail_body); self.dv.setContentsMargins(0, 0, 0, 0)
        self.detail.add(self.detail_body)
        split.addWidget(self.detail)
        split.setSizes([960, 380])
        v.addWidget(split, 1)

    def refresh(self):
        R = self.host.review
        self.setEnabled(R is not None)
        if R is None:
            return
        keep = self.current()
        self.rows = X.build(R.M)
        self.table.setRowCount(len(self.rows))
        t = D.tokens()
        for i, r in enumerate(self.rows):
            vals = [r["num"] if r["kind"] == "L" else "", r["title"] if r["kind"] == "L" else "",
                    "\n".join(f"{n} {tt}".strip() for n, tt, _h in r["m"]) or (f"{r['num']} {r['title']}" if r["kind"] == "M" else ""),
                    "\n".join(f"{n} {tt}".strip() for n, tt, _h in r["c"]), "; ".join(r["gaps"])]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 4 and r["gaps"]:
                    it.setForeground(D.color("warn"))
                self.table.setItem(i, c, it)
        self.table.resizeRowsToContents()
        n = X.counts(self.rows)
        self.p_inst.setText(f"{n['instructions']} instructions")
        self.p_noeval.setText(f"{n['not_evaluated']} not evaluated"); self.p_noeval.set_tone("warn" if n["not_evaluated"] else "ok")
        self.p_noinst.setText(f"{n['no_instruction']} factors with no instruction"); self.p_noinst.set_tone("warn" if n["no_instruction"] else "ok")
        if keep:
            self.select(keep)
        else:
            self.show_detail()

    def current(self):
        i = self.table.currentRow()
        return self.rows[i]["num"] if 0 <= i < len(self.rows) else None

    def select(self, num):
        for i, r in enumerate(self.rows):
            if r["num"] == num:
                self.table.selectRow(i)
                return True
        return False

    def show_detail(self):
        while self.dv.count():
            w = self.dv.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        i = self.table.currentRow()
        if not (0 <= i < len(self.rows)):
            self.dv.addWidget(D.EmptyState("No instruction selected", "Select a row to see how it is linked and to add or take out links."))
            return
        r = self.rows[i]
        if r["kind"] == "M":
            self.dv.addWidget(D.label(f"{r['num']} {r['title']}", "title"))
            self.dv.addWidget(D.label("This factor is evaluated, but no instruction was found that asks for it. Select an "
                                      "instruction and add this factor to it, or note it for the proposal manager.", "muted"))
            return
        self.dv.addWidget(D.label(f"{r['num']} {r['title']}", "title"))
        self.dv.addWidget(D.label(f"{r['items']} sentence(s) in this section of the RFP.", "muted"))
        secs = X.sections(self.host.review.M)
        for kind, title, links in (("M", "Evaluated by", r["m"]), ("C", "Work", r["c"])):
            self.dv.addWidget(D.SectionTitle(title))
            for n, tt, how in links:
                self.dv.addWidget(D.Chip(f"{n} {tt}  ·  {how}", "ctx" if kind == "M" else "req",
                                         on_remove=lambda _=False, n=n: self.link(r["num"], n, False)))
            if not links:
                self.dv.addWidget(D.label("None found." if kind == "C" else "None found: a gap.", "muted"))
            cb = QComboBox()
            cb.addItem("+ Section M factor" if kind == "M" else "+ Work section")
            for k in sorted((k for k, s in secs.items() if s["kind"] == kind and len(k) > 1), key=X._sec_key):
                if k not in [n for n, _t, _h in links]:
                    cb.addItem(f"{k} {secs[k]['title']}", k)
            cb.activated.connect(lambda idx, cb=cb: self.link(r["num"], cb.itemData(idx), True) if idx > 0 else None)
            self.dv.addWidget(cb)
        self.dv.addStretch(1)

    def link(self, l_num, other, on):
        R = self.host.review
        R.snap()
        X.link(R.M, l_num, other, on)
        diag.activity("crosswalk_link_set")
        self.host.changed()
        self.refresh()
        self.select(l_num)
        return True

    def export(self, path=None):
        R = self.host.review
        if R is None:
            return None
        if path is None:
            name = (self.host.effort_name or R.M.name).replace(" ", "_")
            path, _ = QFileDialog.getSaveFileName(self, "Export the L/M crosswalk", os.path.join(EF.out(self.host.effort_path) or os.path.dirname(R.M.path),
                                                                                                f"{name}_LM_Crosswalk.xlsx"), "Excel (*.xlsx)")
            if not path:
                return None
        try:
            res = X.export(R.M, path, self.host.effort_name)
        except PermissionError:
            self.host.status("A workbook with that name is open in Excel: close it, then export again.")
            return None
        diag.activity("crosswalk_exported", n=res["rows"])
        self.host.toast(f"Crosswalk exported: {res['rows']} rows")
        return res
