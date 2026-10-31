"""Production (3.5.0): Format Check and Production Standards. Format Check reads Word drafts against the standards and
reports what breaks them; it opens each file read-only into memory and never writes to it. Production Standards keeps
the team's document types (fonts by scope, margins, page size, caption numbering and placement, TOC switches, page
numbers) and the open effort's own values, filled from the RFP's formatting rules."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout,
                               QHBoxLayout, QHeaderView, QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QScrollArea,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import prodcheck as PC
import prodstd as PS
from . import design as D

AREAS = [a for a, _f in PC.AREAS]


def _scroll(page):
    outer = QVBoxLayout(page); outer.setContentsMargins(0, 0, 0, 0)
    sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
    inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
    v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
    return v


class FormatCheckPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.results = []
        v = _scroll(self)
        self.card = D.Card("Format Check", "Your Word drafts read against the production standards. Each file is read into memory and "
                           "never written: the original stays exactly as it is.",
                           actions=[D.button("Check", "primary", lambda: self.run()), D.button("Export...", None, lambda: self.export())])
        top = QHBoxLayout()
        top.addWidget(D.label("Standard", "label", wrap=False))
        self.std_lbl = D.label("", None); top.addWidget(self.std_lbl, 1)
        top.addWidget(D.button("Production Standards", "ghost", lambda: self.host.go("prodstd")))
        self.card.body.addLayout(top)
        self.files = QListWidget(); self.files.setFixedHeight(130); self.card.add(self.files)
        frow = QHBoxLayout()
        frow.addWidget(D.button("Add a file...", None, lambda: self.add_file(), "A Word file anywhere: it is only read"))
        frow.addStretch(1)
        self.area_checks = {}
        for a in AREAS:
            cb = QCheckBox(a); cb.setChecked(True); frow.addWidget(cb); self.area_checks[a] = cb
        self.card.body.addLayout(frow)
        self.summary = self.card.add(D.label("Not checked yet.", "muted"))
        self.tiles = QGridLayout(); self.tiles.setSpacing(D.SPACE["s"]); self.card.body.addLayout(self.tiles)
        t = QTableWidget(0, 5); t.setHorizontalHeaderLabels(["Draft", "Area", "Where", "Finding", "Detail"])
        t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setWordWrap(True)
        t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setMinimumHeight(320)
        for i, wd in ((0, 170), (1, 120), (2, 150), (3, 300)):
            t.setColumnWidth(i, wd)
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table = t; self.card.add(t)
        v.addWidget(self.card)
        v.addStretch(1)

    def std(self):
        """3.6.0: the Format Check view of the production standard (prodrules: team, document type, effort)."""
        import prodrules as PRL
        full = PRL.for_effort(self.host.config_dir, self.host.ws)
        s = PRL.to_check(full)
        s["name"] = full["name"]
        s["effort_over"] = full.get("effort_over")
        return s

    def refresh(self):
        h = self.host
        s = self.std()
        f = s["fonts"]
        self.std_lbl.setText(f"{s['name']}{' + this effort' if s.get('effort_over') else ''}: "
                             f"body {f['body'].get('font') or 'any font'} {PC_size(f['body'])}, tables {f['table'].get('font') or 'any font'} "
                             f"{PC_size(f['table'])}, margins {s['margins_in']:g} in, {s['page']}")
        keep = {self.files.item(i).data(Qt.UserRole): self.files.item(i).checkState() for i in range(self.files.count())}
        extra = [p for p in keep if p not in {x[1] for x in self._drafts()}]
        self.files.clear()
        for name, p in self._drafts() + [(os.path.basename(x), x) for x in extra]:
            it = QListWidgetItem(name); it.setData(Qt.UserRole, p); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(keep.get(p, Qt.Checked)); it.setToolTip(p); self.files.addItem(it)

    def _drafts(self):
        if self.host.ws is None:
            return []
        try:
            return self.host.home_page.theme_drafts()
        except Exception:
            diag.swallowed()
            return []

    def add_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A Word file to check (it is only read)", os.path.expanduser("~"), "Word (*.docx)")
            if not path:
                return ""
        it = QListWidgetItem(os.path.basename(path)); it.setData(Qt.UserRole, path); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked); it.setToolTip(path); self.files.addItem(it)
        return path

    def run(self):
        std = self.std()
        areas = [a for a, cb in self.area_checks.items() if cb.isChecked()]
        paths = [self.files.item(i).data(Qt.UserRole) for i in range(self.files.count()) if self.files.item(i).checkState() == Qt.Checked]
        if not paths:
            self.summary.setText("No drafts: put the volumes' Word files in the effort's Volumes folder, or Add a file...")
            return []
        self.results = [PC.check(p, std, areas) for p in paths]
        t = self.table
        t.setRowCount(0)
        totals = {a: 0 for a in areas}
        for r in self.results:
            rows = ([{"area": "File", "where": "", "problem": r["error"], "detail": ""}] if r["error"] else []) + r["findings"]
            for f in rows:
                k = t.rowCount(); t.insertRow(k)
                for c, text in enumerate((r["file"], f["area"], f["where"], f["problem"], f["detail"])):
                    t.setItem(k, c, QTableWidgetItem(text))
                if f["area"] in totals:
                    totals[f["area"]] += 1
        t.resizeRowsToContents()
        while self.tiles.count():
            x = self.tiles.takeAt(0)
            if x.widget() is not None:
                x.widget().deleteLater()
        for k, a in enumerate(areas):
            n = totals.get(a, 0)
            self.tiles.addWidget(D.Tile(str(n), a.lower(), "ok" if not n else "warn"), 0, k)
        n = sum(totals.values())
        self.summary.setText(f"{len(paths)} draft{'s' if len(paths) != 1 else ''} read: " + (f"{n} finding{'s' if n != 1 else ''}." if n else
                                                                                           "everything meets the standard."))
        diag.activity("format_checked", n=n)
        return self.results

    def export(self, path=None):
        if not self.results:
            self.host.status("Check first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the format check", self.host.out_path("format_check"), "Excel (*.xlsx)")
            if not path:
                return ""
        PC.export(path, self.results, self.host.effort_name)
        self.host.toast("Format check exported")
        return path


def PC_size(rule):
    lo, hi = float(rule.get("min") or 0), float(rule.get("max") or 0)
    if lo and hi and lo == hi:
        return f"{lo:g} pt"
    if lo and hi:
        return f"{lo:g} to {hi:g} pt"
    if lo:
        return f"{lo:g} pt or larger"
    if hi:
        return f"up to {hi:g} pt"
    return "any size"


class StandardsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.data = None
        v = _scroll(self)
        self.card = D.Card("Production Standards", "Your team's formatting rules for each kind of document. Format Check reads drafts "
                           "against them.", actions=[D.button("+ Document type...", None, lambda: self.add_type()),
                                                     D.button("Save", "primary", lambda: self.save())])
        top = QHBoxLayout()
        top.addWidget(D.label("Document type", "label", wrap=False))
        self.type = QComboBox(); self.type.setMinimumWidth(240); self.type.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.type)
        self.is_default = QCheckBox("New efforts use this type"); top.addWidget(self.is_default); top.addStretch(1)
        self.card.body.addLayout(top)
        g = QGridLayout(); g.setHorizontalSpacing(D.SPACE["m"]); g.setVerticalSpacing(D.SPACE["xs"])
        g.addWidget(D.label("Text", "label"), 0, 0); g.addWidget(D.label("Font", "label"), 0, 1)
        g.addWidget(D.label("Smallest (pt)", "label"), 0, 2); g.addWidget(D.label("Largest (pt)", "label"), 0, 3)
        self.font_rows = {}
        for k, sc in enumerate(PS.SCOPES, 1):
            f = QLineEdit(); f.setPlaceholderText("any font")
            lo = QDoubleSpinBox(); lo.setRange(0, 72); lo.setSingleStep(0.5); lo.setSpecialValueText("any")
            hi = QDoubleSpinBox(); hi.setRange(0, 72); hi.setSingleStep(0.5); hi.setSpecialValueText("any")
            g.addWidget(D.label(PS.SCOPE_NAMES[sc], None, wrap=False), k, 0); g.addWidget(f, k, 1); g.addWidget(lo, k, 2); g.addWidget(hi, k, 3)
            self.font_rows[sc] = (f, lo, hi)
        g.setColumnStretch(1, 1)
        self.card.body.addLayout(g)
        form = QFormLayout(); self.card.body.addLayout(form)
        self.margins = QDoubleSpinBox(); self.margins.setRange(0, 3); self.margins.setSingleStep(0.25); self.margins.setSuffix(" in")
        form.addRow("Smallest margin", self.margins)
        self.page = QComboBox(); self.page.addItems(list(PS.PAGES)); form.addRow("Page size", self.page)
        self.land = QCheckBox("Landscape sections allowed"); form.addRow("", self.land)
        self.capnum = QComboBox(); self.capnum.addItem("By section: 2-1, A-1", "chapter"); self.capnum.addItem("Straight through: 1, 2, 3", "plain")
        form.addRow("Caption numbers", self.capnum)
        self.capsep = QComboBox(); self.capsep.addItem("A tab after “Table 2-1.”", "tab"); self.capsep.addItem("A space", "space")
        form.addRow("After the number", self.capsep)
        self.capfld = QCheckBox("Caption numbers must be fields, never typed"); form.addRow("", self.capfld)
        self.cappos = QComboBox()
        for k in ("first row", "above", "below", "either"):
            self.cappos.addItem({"first row": "In the table's first row", "above": "Above the table", "below": "Below the table",
                                 "either": "Any of these"}[k], k)
        form.addRow("Table captions", self.cappos)
        self.toc = QLineEdit(); self.toc.setPlaceholderText("\\o, \\u"); form.addRow("TOC switches never used", self.toc)
        self.pnum = QCheckBox("Every section's footer has a page number field"); form.addRow("", self.pnum)
        v.addWidget(self.card)
        self.eff = D.Card("This effort", "The RFP's own formatting rules, laid over the document type for this effort only.",
                          actions=[D.button("Fill from the RFP's formatting rules", "primary", lambda: self.fill_from_rfp()),
                                   D.button("Clear", "ghost", lambda: self.clear_effort())])
        er = QHBoxLayout(); er.addWidget(D.label("Document type for this effort", "label", wrap=False))
        self.eff_type = QComboBox(); self.eff_type.setMinimumWidth(240); er.addWidget(self.eff_type); er.addStretch(1)
        self.eff.body.addLayout(er)
        self.eff_text = self.eff.add(D.label("", "muted")); self.eff_text.setWordWrap(True)
        v.addWidget(self.eff)
        v.addStretch(1)

    def refresh(self):
        self.data = PS.load(self.host.config_dir)
        cur = self.type.currentText()
        self.type.blockSignals(True); self.type.clear()
        self.type.addItems([t["name"] for t in self.data["types"]])
        self.type.setCurrentText(cur if cur else self.data["default"])
        self.type.blockSignals(False)
        self.fill()
        self.eff.setVisible(self.host.ws is not None)
        if self.host.ws is not None:
            eff = self.host.ws.get("prod_std", {}) or {}
            self.eff_type.clear(); self.eff_type.addItems([t["name"] for t in self.data["types"]])
            self.eff_type.setCurrentText(eff.get("type") or self.data["default"])
            self.show_effort()

    def current(self):
        return PS.get(self.data, self.type.currentText())

    def fill(self):
        t = self.current()
        for sc, (f, lo, hi) in self.font_rows.items():
            r = t["fonts"].get(sc, {})
            f.setText(r.get("font", "")); lo.setValue(float(r.get("min") or 0)); hi.setValue(float(r.get("max") or 0))
        self.margins.setValue(float(t.get("margins_in") or 0)); self.page.setCurrentText(t.get("page", "Letter"))
        self.land.setChecked(bool(t.get("landscape_ok", True)))
        self.capnum.setCurrentIndex(max(0, self.capnum.findData(t.get("caption_numbers"))))
        self.capsep.setCurrentIndex(max(0, self.capsep.findData(t.get("caption_sep"))))
        self.capfld.setChecked(bool(t.get("caption_fields", True)))
        self.cappos.setCurrentIndex(max(0, self.cappos.findData(t.get("caption_position"))))
        self.toc.setText(", ".join(t.get("toc_forbid", []))); self.pnum.setChecked(bool(t.get("page_numbers", True)))
        self.is_default.setChecked(self.data["default"] == t["name"])

    def values(self):
        return {"fonts": {sc: {"font": f.text().strip(), "min": lo.value(), "max": hi.value()} for sc, (f, lo, hi) in self.font_rows.items()},
                "margins_in": self.margins.value(), "page": self.page.currentText(), "landscape_ok": self.land.isChecked(),
                "caption_numbers": self.capnum.currentData(), "caption_sep": self.capsep.currentData(),
                "caption_fields": self.capfld.isChecked(), "caption_position": self.cappos.currentData(),
                "toc_forbid": [x.strip() for x in self.toc.text().split(",") if x.strip()], "page_numbers": self.pnum.isChecked()}

    def save(self):
        t = self.current()
        t.update(self.values())
        if self.is_default.isChecked():
            self.data["default"] = t["name"]
        PS.save(self.host.config_dir, self.data)
        if self.host.ws is not None:
            eff = dict(self.host.ws.get("prod_std", {}) or {})
            eff["type"] = self.eff_type.currentText() or self.data["default"]
            self.host.ws.set("prod_std", eff)
        diag.activity("prod_standards_saved")
        self.host.toast(f"Saved: {t['name']}")
        self.refresh()
        return True

    def add_type(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New document type", "Its name (for example: Cost volume, Customer deliverable):")
            if not ok:
                return ""
        name = " ".join((name or "").split())
        if not name or name in [t["name"] for t in self.data["types"]]:
            self.host.status("Give it a name not already used.")
            return ""
        new = PS.merge(self.current(), {"name": name})
        new["name"] = name
        self.data["types"].append(new)
        PS.save(self.host.config_dir, self.data)
        self.refresh()
        self.type.setCurrentText(name)
        return name

    # ------------------------------------------------------------ the effort's own values
    def show_effort(self):
        eff = self.host.ws.get("prod_std", {}) or {}
        said = eff.get("said") or []
        self.eff_text.setText(("From the RFP: " + "; ".join(said) + ". These replace the document type's values for this effort.")
                              if said else "Nothing from the RFP yet. Fill from the RFP's formatting rules reads them from Submission Rules.")

    def fill_from_rfp(self):
        if self.host.ws is None:
            return {}
        try:
            from .custdocs import Ctx
            rows = Ctx(self.host).reg.rows()
        except Exception:
            diag.swallowed()
            rows = []
        over, said = PS.from_rfp(rows)
        eff = dict(self.host.ws.get("prod_std", {}) or {})
        eff.update({"type": self.eff_type.currentText() or self.data["default"], "over": over, "said": said})
        self.host.ws.set("prod_std", eff)
        diag.activity("prod_standards_from_rfp", n=len(said))
        self.host.status(f"{len(said)} formatting rule(s) read from the RFP." if said else
                         "The RFP's formatting rules are not in Submission Rules yet (capture them in Review: Formatting).")
        self.show_effort()
        return over

    def clear_effort(self):
        if self.host.ws is not None:
            eff = dict(self.host.ws.get("prod_std", {}) or {})
            eff.pop("over", None); eff.pop("said", None)
            self.host.ws.set("prod_std", eff)
            self.show_effort()
