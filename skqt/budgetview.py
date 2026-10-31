"""Page budget... (3.1.0, in Review and Structure): each volume's page limit split across its sections. The limit comes
from the customer's page limit for the volume (Submission Rules) or the volume's deliverable, or is typed here; Split
evenly or Split by requirements fills the pages, and any section can be changed by half pages. The total shows against
the limit and against the draft's page count. Saved with the response structure; printed under each section in the
Response Setup documents and listed in My Work."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QHeaderView,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)
import diag
import pagebudget as PB
import setupdoc as SD
from . import design as D


class BudgetDialog(QDialog):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.M = host.review.M
        self.setWindowTitle("Page budget")
        self.resize(860, 640)
        self.rows, self.delivs = self._sources()
        self.vols = PB.volumes(self.M)
        self.edit = {l: PB.pages(self.M, l) or 0 for l in SD.labels(self.M)}
        self.limits = {}
        self.saved = False
        v = QVBoxLayout(self)
        v.addWidget(D.label("Give each section its share of the volume's page limit. A section's pages include its subsections.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        self.vol = QComboBox()
        for name, _labs in self.vols:
            self.vol.addItem(name or "The response", name)
        self.vol.setVisible(len(self.vols) > 1)
        if len(self.vols) > 1:
            top.addWidget(D.label("Volume", "label", wrap=False))
        top.addWidget(self.vol)
        top.addWidget(D.label("Page limit", "label", wrap=False))
        self.limit = QSpinBox(); self.limit.setRange(0, 2000); self.limit.setSuffix(" pages"); self.limit.setSpecialValueText("not set")
        top.addWidget(self.limit)
        self.limit_from = D.label("", "muted", wrap=False); top.addWidget(self.limit_from)
        top.addStretch(1)
        t = QTableWidget(0, 4); t.setHorizontalHeaderLabels(["Section", "Pages", "Requirements", "Lead"])
        t.verticalHeader().setVisible(False); t.setSelectionMode(QAbstractItemView.NoSelection)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in ((1, 120), (2, 110), (3, 160)):
            t.setColumnWidth(i, w)
        t.verticalHeader().setDefaultSectionSize(32)
        self.table = t; v.addWidget(t, 1)
        self.totals = D.label("", None); self.totals.setTextFormat(Qt.RichText); v.addWidget(self.totals)
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(D.button("Split evenly", None, lambda: self.split("even"), "The limit spread evenly across the volume's main sections"))
        bar.addWidget(D.button("Split by requirements", None, lambda: self.split("reqs"),
                               "The limit spread by how many compliance requirements each main section holds"))
        bar.addWidget(D.button("Clear this volume", "ghost", lambda: self.clear()))
        bar.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(lambda: self.save()); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.vol.currentIndexChanged.connect(lambda _i: self.fill())
        self.limit.valueChanged.connect(lambda n: (self.limits.__setitem__(self.cur_vol(), n), self.show_totals()))
        self.spins = {}
        self.fill()

    def _sources(self):
        try:
            from .custdocs import Ctx
            import deliverables as DL
            c = Ctx(self.host)
            return c.reg.rows(), list(DL.items(c.rec))
        except Exception:
            diag.swallowed()
            return [], []

    def cur_vol(self):
        return self.vol.currentData() if self.vol.count() else ""

    def labels(self):
        return dict(self.vols).get(self.cur_vol(), SD.labels(self.M))

    def fill(self):
        import compliance as C
        vol = self.cur_vol()
        n, src = (self.limits[vol], "set here") if vol in self.limits else PB.limit_for(self.M, vol, self.rows, self.delivs)
        self.limit.blockSignals(True); self.limit.setValue(n or 0); self.limit.blockSignals(False)
        self.limit_from.setText(f"from {src}" if src and src != "set here" else ("set here" if n else "type the volume's limit"))
        labs = self.labels()
        lv = {C.outline_label(o): o.get("level", 1) for o in self.M.outline}
        base = min((lv.get(l, 1) for l in labs), default=1)
        counts = PB.req_counts(self.M, labs)
        t = self.table
        t.setRowCount(0); self.spins = {}
        for l in labs:
            r = t.rowCount(); t.insertRow(r)
            it = QTableWidgetItem(("    " * (lv.get(l, 1) - base)) + l); it.setFlags(Qt.ItemIsEnabled); t.setItem(r, 0, it)
            sp = QDoubleSpinBox(); sp.setRange(0, 2000); sp.setSingleStep(PB.STEP); sp.setDecimals(1); sp.setSpecialValueText("-")
            sp.setValue(self.edit.get(l) or 0)
            sp.valueChanged.connect(lambda val, l=l: (self.edit.__setitem__(l, val), self.show_totals()))
            t.setCellWidget(r, 1, sp); self.spins[l] = sp
            for c, text in ((2, str(counts.get(l, 0))), (3, SD.section_people(self.M, l).get("lead", ""))):
                x = QTableWidgetItem(text); x.setFlags(Qt.ItemIsEnabled); t.setItem(r, c, x)
        self.show_totals()

    def _total(self):
        labs = self.labels()
        have = {l for l in labs if self.edit.get(l)}
        return sum(self.edit[l] for l in have if not any(p in have for p in SD._parents(self.M, l)[1:]))

    def show_totals(self):
        tot, lim = self._total(), self.limit.value()
        draft = PB.draft_pages(self.cur_vol(), self.delivs)
        t = D.tokens()
        msg = f"<b>Budgeted {PB.fmt(tot)}</b>"
        if lim:
            left = lim - tot
            color = t["crit"] if left < 0 else t["ok"] if left == 0 else t["text"]
            msg += (f" of {lim} pages: <span style='color:{color}'><b>" + (f"{PB.fmt(-left)} over the limit" if left < 0 else
                    "every page given" if left == 0 else f"{PB.fmt(left)} left to give") + "</b></span>")
        else:
            msg += " pages (no limit set)"
        if draft is not None:
            msg += f"  ·  The draft is {draft} page{'s' if draft != 1 else ''} (Word's count)"
            if lim and draft > lim:
                msg += f": <span style='color:{t['crit']}'>over the limit</span>"
        self.totals.setText(msg)
        return tot

    def split(self, by):
        lim = self.limit.value()
        if not lim:
            self.host.status("Set the volume's page limit first.")
            return {}
        parts = PB.parts(self.M, self.labels())
        import copy
        tmp = copy.copy(self.M)
        tmp.setup = copy.deepcopy(SD.setup_of(self.M))
        got = PB.split(tmp, parts, lim, by)
        for l, n in got.items():
            self.edit[l] = n
            if l in self.spins:
                self.spins[l].blockSignals(True); self.spins[l].setValue(n); self.spins[l].blockSignals(False)
        self.show_totals()
        return got

    def clear(self):
        for l in self.labels():
            self.edit[l] = 0
            if l in self.spins:
                self.spins[l].blockSignals(True); self.spins[l].setValue(0); self.spins[l].blockSignals(False)
        self.show_totals()

    def save(self):
        R = self.host.review
        R.snap()
        for l, n in self.edit.items():
            if (PB.pages(self.M, l) or 0) != (n or 0):
                PB.set_pages(self.M, l, n)
        for vol, n in self.limits.items():                     # typed only when it differs from the documents' limit
            PB.set_limit(self.M, vol, 0)
            found, _src = PB.limit_for(self.M, vol, self.rows, self.delivs)
            if n != (found or 0):
                PB.set_limit(self.M, vol, n)
        self.M.pending = True
        self.saved = True
        diag.activity("page_budget_saved", n=sum(1 for n in self.edit.values() if n))
        self.host.changed()
        self.accept()
        return True
