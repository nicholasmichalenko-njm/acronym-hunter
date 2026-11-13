"""Make templates (3.25.0): one dialog for every way a .dotx is made, opening on everything each template will carry.

What to make: what you are editing in Production Standards, every volume of an effort type, or this effort's volumes
with the setup written on each. The list shows each template to be made; the view beside it shows that template in
full (styles, pages and margins, pagination by part, headers and footers, numbering, tables, captions, the table of
contents, covers, Quick Parts, fields, theme and fonts) before any file is written. Make writes the files.
"""
import copy
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QRadioButton, QSplitter, QTextBrowser, QVBoxLayout, QWidget)

import diag
import prodrules as PRL
import templatedetails as TD
from . import design as D

WHAT = (("this", "What you are editing in Production Standards"), ("etype", "Every volume of an effort type"),
        ("effort", "This effort's volumes, with the setup written on each"))


class MakeTemplatesDialog(QDialog):
    def __init__(self, page, start=None):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.data = PRL.load(self.host.config_dir)
        self.setWindowTitle("Make templates")
        self.resize(1200, 760)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Choose what to make, then read each template in full on the right. Nothing is written until "
                            "you press Make. Templates go to the Templates folder in the output folder.", "muted"))
        sp = QSplitter(Qt.Horizontal); v.addWidget(sp, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(D.label("What to make", "title"))
        self.what = QButtonGroup(self); self.radios = {}
        for k, label in WHAT:
            r = QRadioButton(label); self.what.addButton(r); self.radios[k] = r; lv.addWidget(r)
            r.toggled.connect(lambda on, _k=k: self.refresh() if on else None)
            if k == "this":
                self.this_lbl = D.label("", "muted"); lv.addWidget(self.this_lbl)
            if k == "etype":
                self.etype = QComboBox()
                for e in self.data.get("effort_types", []):
                    self.etype.addItem(e["name"], e["id"])
                self.etype.currentIndexChanged.connect(lambda _i: self.refresh()); lv.addWidget(self.etype)
            if k == "effort":
                self.effort_lbl = D.label("", "muted"); lv.addWidget(self.effort_lbl)
        self.start_box = QWidget(); sb = QVBoxLayout(self.start_box); sb.setContentsMargins(0, 0, 0, 0)
        sb.addWidget(D.label("Start from", "title"))
        self.base_r = QRadioButton("The Stationkeeper base (cover, front matter, a chapter with a sample table, an appendix)")
        self.mine_r = QRadioButton("A template of mine (only read; its pages, logos and text are kept)")
        self.base_r.setChecked(True)
        sb.addWidget(self.base_r); sb.addWidget(self.mine_r)
        mh = QHBoxLayout(); self.mine = QLineEdit(); self.mine.setPlaceholderText("A .dotx or .docx"); mh.addWidget(self.mine, 1)
        mh.addWidget(D.button("Choose...", None, lambda: self.pick_mine())); sb.addLayout(mh)
        lv.addWidget(self.start_box)
        self.name_box = QWidget(); nb = QVBoxLayout(self.name_box); nb.setContentsMargins(0, 0, 0, 0)
        nb.addWidget(D.label("Name", "title"))
        nb.addWidget(D.label("Where or how it is used. Making it again under the same name makes the next version.", "muted"))
        self.name = QComboBox(); self.name.setEditable(True); nb.addWidget(self.name)
        lv.addWidget(self.name_box)
        self.setup_box = QWidget(); stb = QVBoxLayout(self.setup_box); stb.setContentsMargins(0, 0, 0, 0)
        self.ready_lbl = D.label("", None); stb.addWidget(D.label("Ready to make", "title")); stb.addWidget(self.ready_lbl)
        stb.addWidget(D.label("Reference text in the setup", "title"))
        stb.addWidget(D.label("Each kind goes in its own style; hidden text shows only with Show/Hide on.", "muted"))
        self.ref_grid = QGridLayout(); stb.addLayout(self.ref_grid)
        # 3.27.0: Volume II continues Volume I
        self.cont = QCheckBox("Each volume continues the page and chapter numbers of the volume before")
        self.cont.toggled.connect(lambda on: self.fill_starts(suggest=on)); stb.addWidget(self.cont)
        from PySide6.QtWidgets import QTableWidget
        self.starts_t = QTableWidget(0, 4); self.starts_t.setHorizontalHeaderLabels(["Volume", "Pages start at", "Chapters start at", "From"])
        self.starts_t.verticalHeader().setVisible(False); self.starts_t.setMaximumHeight(150); self.starts_t.setEnabled(False)
        self.starts_t.horizontalHeader().setStretchLastSection(True)
        stb.addWidget(self.starts_t)
        # 3.32.0: a prepaginated setup
        self.prepag = QCheckBox("Keep each section's planned pages (a prepaginated setup)")
        self.prepag.setToolTip("A section with pages set in the page allocation (a first-level section, or one that starts a Word "
                               "section) gets its pages in the setup: empty pages after its content, and the next section "
                               "starts on a new page. Placed Quick Parts count with their measured pages.")
        stb.addWidget(self.prepag)
        self.ref_rows = {}
        lv.addWidget(self.setup_box)
        lv.addWidget(D.label("Templates to make", "title"))
        self.list = QListWidget(); self.list.currentRowChanged.connect(lambda _r: (self.show_details(), self.show_sets() if self.choice() != "this" else None)); lv.addWidget(self.list, 1)
        sp.addWidget(left)
        from PySide6.QtWidgets import QScrollArea, QTabWidget
        self.right_tabs = QTabWidget()                       # 3.97.0: what goes in, picked from the libraries
        from .setspick import WhatGoesIn
        self.goes_in = WhatGoesIn(self)
        gsc = QScrollArea(); gsc.setWidgetResizable(True); gsc.setWidget(self.goes_in)
        self.right_tabs.addTab(gsc, "What goes in")
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        jh = QHBoxLayout(); jh.addWidget(D.label("Go to", "label", wrap=False))
        self.jump = QComboBox(); self.jump.addItems(TD.SECTIONS); self.jump.activated.connect(lambda _i: self.view.scrollToAnchor(self.jump.currentText()))
        jh.addWidget(self.jump); jh.addStretch(1); rv.addLayout(jh)
        self.view = QTextBrowser(); self.view.setOpenLinks(False); rv.addWidget(self.view, 1)
        self.right_tabs.addTab(right, "The template in full")
        sp.addWidget(self.right_tabs); sp.setSizes([420, 780])
        bh = QHBoxLayout(); bh.addStretch(1)
        self.make_btn = D.button("Make", "primary", lambda: self.accept()); bh.addWidget(self.make_btn)
        bh.addWidget(D.button("Cancel", "ghost", lambda: self.reject())); v.addLayout(bh)
        self.plans = []
        self._setup_plan = None
        effort_ok = self._effort_ready()
        self.radios["effort"].setEnabled(effort_ok)
        self.radios["etype"].setEnabled(self.etype.count() > 0)
        want = start or ("effort" if (effort_ok and page.scope == "effort") else "this")
        if not self.radios[want].isEnabled():
            want = "this"
        self.radios[want].setChecked(True)
        self.refresh()

    # ------------------------------------------------------------------ choices
    def _effort_ready(self):
        R = getattr(self.host, "review", None)
        return bool(R is not None and getattr(R.M, "outline", None) and self.host.ws is not None)

    def choice(self):
        return next((k for k, r in self.radios.items() if r.isChecked()), "this")

    def pick_mine(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Start from (only read)", os.path.expanduser("~"), "Word (*.dotx *.docx)")
        if path:
            self.mine.setText(path); self.mine_r.setChecked(True)

    def start_from(self):
        return self.mine.text().strip() if self.mine_r.isChecked() and self.mine.text().strip() else ""

    def _fonts(self):
        try:
            from .collectview import installed_fonts
            return installed_fonts()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return None

    def refresh(self, keep_sets=False):
        k = self.choice()
        self.this_lbl.setText("  " + self.page.scope_box.currentText())
        self.effort_lbl.setText("  " + (self.host.effort_name or "No effort open") if self._effort_ready() else
                                "  Open an effort with a response structure (Matrix) first.")
        self.etype.setEnabled(k == "etype")
        self.start_box.setVisible(k in ("this", "etype"))
        self.name_box.setVisible(k == "this")
        self.setup_box.setVisible(k == "effort")
        fonts = self._fonts()
        self.plans = []
        if k == "this":
            std = PRL.engine_ready(copy.deepcopy(self.page.work))
            title = self.page.scope_box.currentText().split(": ", 1)[-1]
            if not self.name.count():
                import templatereg as TR
                self.name.addItems([title] + [n for n in TR.names(self.host.config_dir) if n != title])
            self.plans.append({"title": title, "std": std, "problems": self.page.show_problems()})
        elif k == "etype":
            e = PRL.effort_type_of(self.data, self.etype.currentData())
            for pid in (e or {}).get("profiles", []):
                std = PRL.engine_ready(PRL.resolved_type(self.data, pid, e["id"]))
                self.plans.append({"title": f"{e['name']} - {PRL.type_of(self.data, pid)['name']}", "std": std,
                                   "problems": PRL.validate(std) if std.get("row_types") else []})
        else:
            import setuptemplate as ST
            import effortrec as RR
            R = self.host.review
            rd = ST.ready(R.M, RR.Record(self.host.ws.root))
            self.ready_lbl.setText("\n".join(("✓ " if ok else "• ") + what + ("" if ok else f" ({n} still open)") for ok, what, n in rd))
            self._ready_ok = all(ok for ok, _w, _n in rd)
            if not self.ref_rows:
                self.prepag.setChecked(ST.prepaginate(R.M))
                info0 = self.host.efforts.get(self.host.effort_name) or {}
                pl0 = ST.plan(R.M, self.host.config_dir, self.host.ws, self.host.effort_name or "", info0)
                opts = ST.options(R.M, pl0[0]["std"] if pl0 else None)      # 3.33.0: the profile's content map, this effort's changes
                for r, (kk, label, _s, _c, _i) in enumerate(ST.KINDS):
                    self.ref_grid.addWidget(D.label(label, None), r, 0)
                    e = QLineEdit(opts[kk]["style"]); self.ref_grid.addWidget(e, r, 1)
                    cb = QCheckBox("Hidden"); cb.setChecked(opts[kk]["hidden"]); self.ref_grid.addWidget(cb, r, 2)
                    inc = QCheckBox("In the file"); inc.setChecked(opts[kk].get("include", True)); self.ref_grid.addWidget(inc, r, 3)
                    self.ref_rows[kk] = (e, cb, inc)
            info = self.host.efforts.get(self.host.effort_name) or {}
            self._effort_plans = ST.plan(R.M, self.host.config_dir, self.host.ws, self.host.effort_name or "", info)
            st = self.starts()
            for p in self._effort_plans:
                std = ST.with_starts(p["std"], *((st.get(p["volume"]) or {}).get(k) for k in ("page", "chapter")))
                self.plans.append({"title": f"{p['template_name']} v{p['version']}", "std": std,
                                   "problems": PRL.validate(std) if std.get("row_types") else []})
            if self.starts_t.rowCount() != len(self._effort_plans):
                self.fill_starts(suggest=self.cont.isChecked())
        self.make_btn.setText("Make anyway" if k == "effort" and not getattr(self, "_ready_ok", True) else "Make")
        self.make_btn.setEnabled(bool(self.plans) and not (k in ("this", "etype") and any(p["problems"] for p in self.plans)))
        self.list.blockSignals(True); self.list.clear()
        for p in self.plans:
            it = QListWidgetItem(p["title"] + (f"  ({len(p['problems'])} to fix first)" if p["problems"] else ""))
            self.list.addItem(it)
        self.list.blockSignals(False)
        self._fonts_cache = fonts
        if self.plans:
            self.list.setCurrentRow(0)
        self.show_details()
        if not keep_sets:
            self.show_sets()

    def recipe_changed(self):
        """3.97.0: a set or a starting page picked for the profile being edited: kept with it (Save on the page)."""
        if hasattr(self.page, "changed"):
            self.page.changed()
        self.refresh(keep_sets=True)

    def show_sets(self):
        if self.choice() == "this":
            return self.goes_in.show_std(self.page.work, True)
        p = self.plans[max(0, self.list.currentRow())] if self.plans else None
        return self.goes_in.show_std(p["std"] if p else {}, False)

    def show_details(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.plans):
            self.view.setHtml("<p>Nothing to make.</p>")
            return ""
        p = self.plans[r]
        h = TD.html_of(p["std"], p["title"], p["problems"], getattr(self, "_fonts_cache", None))
        self.view.setHtml(h)
        return h

    def fill_starts(self, suggest=False):
        """3.27.0: where each volume's pages and chapters start; suggested from the drafts when it continues."""
        from PySide6.QtWidgets import QSpinBox, QTableWidgetItem
        import setuptemplate as ST
        plans = getattr(self, "_effort_plans", [])
        vdir = ""
        if suggest and self.host.effort_path:
            try:
                import effortfolders as EF
                vdir = EF.folder(self.host.effort_path, "volumes")
            except Exception:  # noqa: BLE001
                diag.swallowed()
        sug = ST.suggest_starts(plans, vdir) if suggest else [{"volume": p["volume"], "page": 1, "chapter": 1, "why": "starts at 1"} for p in plans]
        t = self.starts_t
        t.setRowCount(0)
        for r, s_ in enumerate(sug):
            t.insertRow(r)
            it = QTableWidgetItem(s_["volume"] or "(one volume)"); it.setFlags(Qt.ItemIsEnabled); t.setItem(r, 0, it)
            for c, k in ((1, "page"), (2, "chapter")):
                sb = QSpinBox(); sb.setRange(1, 9999); sb.setValue(int(s_[k])); t.setCellWidget(r, c, sb)
                sb.valueChanged.connect(lambda _v: self.refresh())
            it = QTableWidgetItem(s_["why"]); it.setFlags(Qt.ItemIsEnabled); t.setItem(r, 3, it)
        t.setEnabled(bool(suggest))
        return sug

    def starts(self):
        """{volume: {"page", "chapter"}} when volumes continue; {} otherwise."""
        if not getattr(self, "cont", None) or not self.cont.isChecked():
            return {}
        plans = getattr(self, "_effort_plans", [])
        out = {}
        for r in range(self.starts_t.rowCount()):
            if r < len(plans):
                out[plans[r]["volume"]] = {"page": self.starts_t.cellWidget(r, 1).value(), "chapter": self.starts_t.cellWidget(r, 2).value()}
        return out

    def ref_options(self):
        return {k: {"style": e.text().strip() or k, "hidden": cb.isChecked(), "include": inc.isChecked()}
                for k, (e, cb, inc) in self.ref_rows.items()}

    def make(self, word=None):
        """Makes what was chosen. Returns what the page or Response Setup returned."""
        k = self.choice()
        if k == "this":
            return self.page.make_template(start_from=self.start_from(), word=word, name=self.name.currentText().strip() or None)
        if k == "etype":
            return self.page.make_templates_all(word=word, eid=self.etype.currentData(), start_from=self.start_from())
        import setuptemplate as ST
        if self.host.review is not None:
            ST.set_prepaginate(self.host.review.M, self.prepag.isChecked())
        return self.host.setup_page.make_on_templates(opts=self.ref_options(), go=True, starts=self.starts() or None)


def run(page, start=None):
    """Opens Make templates; makes on Make. Returns the result, or None when cancelled. (Making from Production Standards
    is a Preview tool; the page's own make steps say so when it is off.)"""
    d = MakeTemplatesDialog(page, start)
    if d.exec() != QDialog.Accepted:
        return None
    return d.make()
