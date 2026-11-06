"""Check and Submit > Final Check (3.58.0, claude/stationkeeper-final-check-decisions-2026-11-05.md): one ready-to-send
report per submission volume, on its Word file and its PDF together, eight sections with Pass, Fail or Needs a person on
every line (finalcheck.py). The volumes are Submission Check's; each one's PDF is set once beside its Word file, and the
pages that do not count against the limit are ticked out per volume (every page counts until then). Export writes the
report to Excel and records it in the effort record. Submission Check and Final Checks are this page's tabs. Reads only."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView,
                               QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import diag
import finalcheck as FC
from . import design as D

TONE = {FC.PASS: "ok", FC.FAIL: "crit", FC.HUMAN: "warn"}


class FinalCheckPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.reports = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.p_pass, self.p_fail, self.p_human = D.Pill("0 pass", "ok"), D.Pill("0 fail", "ok"), D.Pill("0 need a person", "ok")
        for p in (self.p_pass, self.p_fail, self.p_human):
            top.addWidget(p)
        top.addStretch(1)
        card = D.Card("Submission volumes", "Each volume's Word file and the PDF you will upload. Every page counts against "
                      "the limit until you tick it out under Pages that do not count.", key=True,
                      actions=[D.button("Check", "primary", lambda: self.check()), D.button("Export...", None, lambda: self.export())])
        self.vols = QTableWidget(0, 3); self.vols.setHorizontalHeaderLabels(["Word file", "PDF", "Pages that do not count"])
        self.vols.verticalHeader().setVisible(False); self.vols.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.vols.setSelectionBehavior(QAbstractItemView.SelectRows); self.vols.setSelectionMode(QAbstractItemView.SingleSelection)
        hh = self.vols.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch); hh.setSectionResizeMode(1, QHeaderView.Stretch); self.vols.setColumnWidth(2, 260)
        self.vols.setMaximumHeight(200)
        card.add(self.vols)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.button("Set the PDF...", None, lambda: self.set_pdf(), "The PDF you will upload for the selected volume"))
        row.addWidget(D.button("Pages that do not count...", None, lambda: self.set_exclude(),
                               "The cover, the TOC, the acronym list, resumes, dividers: tick only what the RFP leaves out"))
        row.addWidget(D.button("Add volumes...", "ghost", lambda: self.add_volumes(), "Word files you will submit (Submission Check's list)"))
        row.addStretch(1)
        card.body.addLayout(row)
        v.addWidget(card)
        rc = D.Card("The report", "Pass, Fail or Needs a person on every line. A fail says where and what to do; nothing is changed.")
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Check", "Result", "Detail"])
        self.tree.setColumnWidth(0, 300); self.tree.setColumnWidth(1, 120); self.tree.setWordWrap(True)
        rc.add(self.tree)
        self.note = rc.add(D.label("Not checked yet.", "muted"))
        v.addWidget(rc, 1)

    # ------------------------------------------------------------ the volumes
    def _ws(self):
        return self.host.ws

    def volumes(self):
        """[{"name", "docx", "pdf", "exclude"}] Submission Check's volumes with their PDFs and tick-outs."""
        ws = self._ws()
        if ws is None:
            return []
        pdfs, ex = ws.get("final_pdfs", {}) or {}, ws.get("final_exclude", {}) or {}
        out = []
        for p, _src in self.host.qa_page.volumes():
            out.append({"name": os.path.splitext(os.path.basename(p))[0], "docx": p, "pdf": pdfs.get(p, ""), "exclude": list(ex.get(p, []))})
        return out

    def refresh(self):
        self.setEnabled(self._ws() is not None)
        keep = self.vols.currentRow()
        self.vols.setRowCount(0)
        names = dict(FC.EXCLUDE)
        for vol in self.volumes():
            k = self.vols.rowCount(); self.vols.insertRow(k)
            a = QTableWidgetItem(os.path.basename(vol["docx"])); a.setData(Qt.UserRole, vol["docx"])
            if not os.path.isfile(vol["docx"]):
                a.setForeground(D.color("warn"))
            b = QTableWidgetItem(os.path.basename(vol["pdf"]) if vol["pdf"] else "not set")
            if not vol["pdf"] or not os.path.isfile(vol["pdf"]):
                b.setForeground(D.color("warn"))
            c = QTableWidgetItem(", ".join(names[x] for x in vol["exclude"] if x in names) or "every page counts")
            for col, it in enumerate((a, b, c)):
                self.vols.setItem(k, col, it)
        if self.vols.rowCount():
            self.vols.selectRow(min(max(keep, 0), self.vols.rowCount() - 1))

    def _sel(self):
        r = self.vols.currentRow()
        it = self.vols.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it else None

    def add_volumes(self, paths=None):
        got = self.host.qa_page.add_volumes(paths)
        self.refresh()
        return got

    def set_pdf(self, path=None, docx=None):
        docx = docx or self._sel()
        if not docx or self._ws() is None:
            self.host.status("Pick a volume first.")
            return ""
        if path is None:
            start = self._ws().get("final_dir", "") or os.path.dirname(docx)
            path, _ = QFileDialog.getOpenFileName(self, "The PDF you will upload", start, "PDF (*.pdf)")
            if not path:
                return ""
        d = dict(self._ws().get("final_pdfs", {}) or {}); d[docx] = path
        self._ws().set("final_pdfs", d)
        self.refresh()
        return path

    def set_exclude(self, kinds=None, docx=None):
        docx = docx or self._sel()
        if not docx or self._ws() is None:
            self.host.status("Pick a volume first.")
            return None
        cur = set((self._ws().get("final_exclude", {}) or {}).get(docx, []))
        if kinds is None:
            dlg = QDialog(self); dlg.setWindowTitle("Pages that do not count"); dv = QVBoxLayout(dlg)
            dv.addWidget(D.label("Tick only what the RFP says does not count against this volume's page limit. "
                                 "Every page counts until you do.", "muted"))
            boxes = {}
            for k, t in FC.EXCLUDE:
                cb = QCheckBox(t); cb.setChecked(k in cur); dv.addWidget(cb); boxes[k] = cb
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
            dv.addWidget(bb)
            if dlg.exec() != QDialog.Accepted:
                return None
            kinds = [k for k, cb in boxes.items() if cb.isChecked()]
        d = dict(self._ws().get("final_exclude", {}) or {}); d[docx] = [k for k, _t in FC.EXCLUDE if k in kinds]
        self._ws().set("final_exclude", d)
        self.refresh()
        return d[docx]

    # ------------------------------------------------------------ the check
    def context(self, vols):
        h = self.host
        ctx = {"effort_name": h.effort_name or ""}
        if h.review is not None:
            ctx["matrix"] = h.review.M
        try:
            ctx["rows"] = h.checks_page._rows()
            ctx["allowed_sizes"] = ("Letter", "A4") if h.checks_page.size.currentText() == "Letter or A4" else (h.checks_page.size.currentText(),)
            ctx["size_mb"] = h.checks_page.mb.value() or None
            ctx["must_contain"] = [w.strip() for w in h.checks_page.contain.text().split(",") if w.strip()]
        except Exception:  # noqa: BLE001
            diag.swallowed()
        try:
            import docversions as DV
            ctx["amendments"] = sum(1 for d in DV.Library(h.ws.p("documents")).load().docs if d.get("type") == "Amendment")
        except Exception:  # noqa: BLE001
            diag.swallowed()
        try:
            import unfiled as UF
            ctx["other_names"] = [n for n in h.efforts.names() if n not in (h.effort_name, UF.NAME)]
        except Exception:  # noqa: BLE001
            diag.swallowed()
        try:                                                         # 3.66.0: the parts and numbering plans, the field recipes
            import effortrec as RR, fieldrecipes as FR
            import partplan as PP                            # 3.68.0: shared plans for its effort type too
            ctx["part_plans"] = PP.for_effort(h.config_dir, h.ws)
            ctx["recipes"] = FR.effective(h.config_dir, h.ws)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        docx = [v["docx"] for v in vols if os.path.isfile(v["docx"])]
        s = getattr(h.acronym_page, "session", None)
        if docx and s is not None and s.effort is not None:
            try:
                ctx["qa_report"] = s.qa_check(docx, None, ctx.get("rows") or (), ())
            except Exception:  # noqa: BLE001
                diag.swallowed()
        return ctx

    def check(self, vols=None):
        vols = vols if vols is not None else self.volumes()
        if not vols:
            self.note.setText("Add the Word volumes you will submit (Add volumes...).")
            return []
        ctx = self.context(vols)
        out = []
        for vol in vols:
            c = dict(ctx)
            try:
                c["std"] = self.host.fixcopy_page.std_for(vol["docx"]) if os.path.isfile(vol["docx"]) else None
            except Exception:  # noqa: BLE001
                diag.swallowed(); c["std"] = None
            try:
                c["marking"] = ((c["std"] or {}).get("variables") or {}).get("marking") or ""
            except Exception:  # noqa: BLE001
                c["marking"] = ""
            out.append(FC.run(vol, c))
        self.reports = out
        self.fill()
        diag.activity("final_check_run", n=sum(r["counts"][FC.FAIL] for r in out))
        return out

    def fill(self):
        self.tree.clear()
        tot = {FC.PASS: 0, FC.FAIL: 0, FC.HUMAN: 0}
        for r in self.reports:
            for k in tot:
                tot[k] += r["counts"][k]
            top = QTreeWidgetItem([r["volume"], f"{r['counts'][FC.FAIL]} fail", f"{r['counts'][FC.PASS]} pass, "
                                   f"{r['counts'][FC.HUMAN]} need a person"])
            f = top.font(0); f.setBold(True); top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            sec = None
            for x in r["lines"]:
                if x["section"] != sec:
                    sec = x["section"]
                    s_it = QTreeWidgetItem([sec, "", ""]); top.addChild(s_it)
                it = QTreeWidgetItem([x["check"], x["status"], x["detail"]])
                it.setForeground(1, D.color(TONE[x["status"]])); it.setToolTip(2, x["detail"])
                s_it.addChild(it)
        self.tree.expandAll()
        self.p_pass.setText(f"{tot[FC.PASS]} pass")
        self.p_fail.setText(f"{tot[FC.FAIL]} fail"); self.p_fail.set_tone("crit" if tot[FC.FAIL] else "ok")
        self.p_human.setText(f"{tot[FC.HUMAN]} need a person"); self.p_human.set_tone("warn" if tot[FC.HUMAN] else "ok")
        self.note.setText("Export... writes the report to Excel and records it in the effort record." if self.reports else "Not checked yet.")

    def export(self, path=None):
        if not self.reports:
            self.host.status("Check first.")
            return ""
        if path is None:
            start = os.path.join(os.path.dirname(self.host.out_path("xref_check")), "Final Check.xlsx") if self.host.effort_path else ""
            path, _ = QFileDialog.getSaveFileName(self, "Export the Final Check", start, "Excel (*.xlsx)")
            if not path:
                return ""
        FC.export(path, self.reports, self.host.effort_name or "")
        try:
            import effortrec as R
            rec = R.Record(self.host.ws.root)
            fails = sum(r["counts"][FC.FAIL] for r in self.reports)
            rec.log("check", f"Final Check: {len(self.reports)} volume(s), {fails} fail, "
                    f"{sum(r['counts'][FC.HUMAN] for r in self.reports)} need a person ({os.path.basename(path)})", save=True)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.host.toast("Final Check exported and recorded")
        return path
