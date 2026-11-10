"""What goes in (3.97.0; canvas "Libraries and Sets", boards 6 and 9): Make templates picks from the libraries and edits
nothing. Style sets in order (where two hold a style, the lower one wins), the Setup style set (hidden in the document),
a part set for the Quick Parts gallery, and what the document starts with: pages in order, each from Parts, each also
in the Quick Parts gallery unless its switch is off. The checks before it is made sit beside them. templatesets holds
the rules; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QListWidget, QListWidgetItem, QMenu,
                               QTableWidget, QVBoxLayout, QWidget)

import stylelib as SL
import templatelib as TL
import templatesets as TS
from . import design as D
from .stylespage import dot


class WhatGoesIn(QWidget):
    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.cfg = dlg.host.config_dir
        self.lib = TL.Library(self.cfg)
        self.std = None
        self.editable = False
        self._guard = False
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["m"])
        self.note = D.label("", "muted"); v.addWidget(self.note)
        g = QGridLayout(); g.setHorizontalSpacing(D.SPACE["m"]); g.setVerticalSpacing(D.SPACE["s"]); v.addLayout(g)
        g.addWidget(D.label("Style sets", "label"), 0, 0, Qt.AlignTop)
        sv = QVBoxLayout()
        self.sets = QListWidget(); self.sets.setMaximumHeight(90); sv.addWidget(self.sets)
        sh = QHBoxLayout()
        self.b_add = D.button("Add a set", "ghost", lambda: self.add_menu()); sh.addWidget(self.b_add)
        self.b_up = D.button("Up", "ghost", lambda: self.move(-1)); sh.addWidget(self.b_up)
        self.b_down = D.button("Down", "ghost", lambda: self.move(1)); sh.addWidget(self.b_down)
        self.b_out = D.button("Take out", "ghost", lambda: self.take_out()); sh.addWidget(self.b_out)
        sh.addStretch(1); sv.addLayout(sh)
        sv.addWidget(D.label("Where two sets hold a style, the lower one wins.", "muted"))
        g.addLayout(sv, 0, 1)
        g.addWidget(D.label("Setup styles", "label"), 1, 0)
        self.setup = QComboBox(); self.setup.currentIndexChanged.connect(lambda _i: self.picked()); g.addWidget(self.setup, 1, 1)
        g.addWidget(D.label("Quick Part set", "label"), 2, 0)
        self.parts = QComboBox(); self.parts.currentIndexChanged.connect(lambda _i: self.picked()); g.addWidget(self.parts, 2, 1)
        v.addWidget(D.label("The document starts with", "title"))
        v.addWidget(D.label("A new document made from this template opens with these pages, in this order, each in its own "
                            "Word section, then the body.", "muted"))
        self.starts = QTableWidget(0, 3); self.starts.setHorizontalHeaderLabels(["Page", "From Parts", "Also in Quick Parts"])
        self.starts.verticalHeader().setVisible(True); self.starts.horizontalHeader().setStretchLastSection(False)
        self.starts.setColumnWidth(0, 150); self.starts.setMaximumHeight(170)
        from PySide6.QtWidgets import QHeaderView
        self.starts.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.starts)
        th = QHBoxLayout()
        self.b_page = D.button("Add a page", "ghost", lambda: self.add_page()); th.addWidget(self.b_page)
        self.b_pup = D.button("Up", "ghost", lambda: self.move_page(-1)); th.addWidget(self.b_pup)
        self.b_pdown = D.button("Down", "ghost", lambda: self.move_page(1)); th.addWidget(self.b_pdown)
        self.b_pout = D.button("Remove", "ghost", lambda: self.remove_page()); th.addWidget(self.b_pout)
        th.addStretch(1); v.addLayout(th)
        v.addWidget(D.label("Before it is made", "title"))
        self.checks_box = QVBoxLayout(); self.checks_box.setSpacing(4); v.addLayout(self.checks_box)
        v.addStretch(1)

    # ------------------------------------------------------------ show a standard's choice
    def show_std(self, std, editable):
        self.std, self.editable = std, editable
        self.lib.fresh()
        self.note.setText("Nothing is changed here: to change a style or a part, open its library. This template takes the "
                          "change the next time it is made." if editable else
                          "Each profile's own choice, as set in Production Standards. Open the profile there to change it.")
        for w in (self.b_add, self.b_up, self.b_down, self.b_out, self.setup, self.parts, self.b_page, self.b_pup, self.b_pdown,
                  self.b_pout, self.starts):
            w.setEnabled(editable)
        self.fill()

    def rec(self):
        return TS.recipe(self.std or {})

    def fill(self):
        self._guard = True
        r = self.rec()
        self.sets.clear()
        for sid in r["style_sets"]:
            k = SL.get_set(self.lib, sid)
            if k is None:
                continue
            it = QListWidgetItem(dot(k.get("color") or "#64748B"), f"{k['name']}    {len(k['items'])} style{'' if len(k['items']) == 1 else 's'}")
            it.setData(Qt.UserRole, sid); self.sets.addItem(it)
        for cb, kind, cur in ((self.setup, "style", r["setup_set"]), (self.parts, "part", r["part_set"])):
            cb.clear(); cb.addItem("None", "")
            for k in SL.sets(self.lib, kind):
                cb.addItem(dot(k.get("color") or "#64748B"), f"{k['name']}  ({len(k['items'])})", k["id"])
            cb.setCurrentIndex(max(0, cb.findData(cur)))
        self.fill_starts(r)
        self._guard = False
        self.fill_checks()

    def page_choices(self, kind):
        import sectiondesigns as SDZ
        import partlib as PT
        shelf = {"cui": "cui", "cover": "cover", "title": "title", "toc": "toc", "acronyms": "acronyms", "units": "units"}.get(kind, kind)
        return [(x["id"], PT.shown_name(self.cfg, x)) for x in SDZ.designs(self.cfg, shelf)]

    def fill_starts(self, r=None):
        r = r or self.rec()
        t = self.starts
        t.setRowCount(0)
        for i, s in enumerate(r["starts"]):
            t.insertRow(i)
            kc = QComboBox()
            for k, label in TS.SLOT_KINDS:
                kc.addItem(label, k)
            kc.setCurrentIndex(max(0, kc.findData(s["kind"])))
            kc.currentIndexChanged.connect(lambda _x, row=i: self.kind_changed(row))
            pc = QComboBox()
            for did, name in self.page_choices(s["kind"]):
                pc.addItem(name, did)
            pc.setCurrentIndex(max(0, pc.findData(s["part"])))
            pc.currentIndexChanged.connect(lambda _x: self.starts_changed())
            gc = QCheckBox(); gc.setChecked(s["gallery"]); gc.toggled.connect(lambda _on: self.starts_changed())
            t.setCellWidget(i, 0, kc); t.setCellWidget(i, 1, pc); t.setCellWidget(i, 2, gc)
        return t.rowCount()

    def fill_checks(self):
        while self.checks_box.count():
            w = self.checks_box.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        if self.std is None or not TS.used(self.std):
            self.checks_box.addWidget(D.label("No sets picked: the template is made from the profile's own values, as before.", "muted"))
            self.checks_now = []
            return []
        t = D.tokens()
        fonts = getattr(self.dlg, "_fonts_cache", None)
        self.checks_now = TS.checks(self.std, self.lib, self.cfg, fonts)
        for st, what, more in self.checks_now:
            col = t["ok"] if st == "ok" else t["warn"]
            self.checks_box.addWidget(D.label(f"<span style='color:{col}'>●</span> <b>{what}</b><br>"
                                              f"<span style='color:{t['muted']}'>{more}</span>", None))
        return self.checks_now

    # ------------------------------------------------------------ changes
    def save(self, **kw):
        if self.std is None or not self.editable:
            return None
        r = TS.set_recipe(self.std, **kw)
        self.dlg.recipe_changed()
        return r

    def picked(self):
        if self._guard:
            return
        self.save(setup_set=self.setup.currentData() or "", part_set=self.parts.currentData() or "")
        self.fill_checks()

    def set_ids(self):
        return [self.sets.item(i).data(Qt.UserRole) for i in range(self.sets.count())]

    def add_menu(self, run=True):
        m = QMenu(self)
        have = set(self.set_ids())
        for k in SL.sets(self.lib, "style"):
            if k["id"] not in have:
                m.addAction(dot(k.get("color") or "#64748B"), k["name"]).triggered.connect(lambda _c=False, sid=k["id"]: self.add_set(sid))
        if not m.actions():
            m.addAction("No other style sets: make one on Styles").setEnabled(False)
        if run:
            m.exec(self.b_add.mapToGlobal(self.b_add.rect().bottomLeft()))
        return m

    def add_set(self, sid):
        self.save(style_sets=self.set_ids() + [sid])
        self.fill()
        return self.set_ids()

    def move(self, d):
        i = self.sets.currentRow()
        ids = self.set_ids()
        if not 0 <= i < len(ids) or not 0 <= i + d < len(ids):
            return ids
        ids[i], ids[i + d] = ids[i + d], ids[i]
        self.save(style_sets=ids); self.fill(); self.sets.setCurrentRow(i + d)
        return ids

    def take_out(self):
        i = self.sets.currentRow()
        ids = self.set_ids()
        if 0 <= i < len(ids):
            ids.pop(i)
            self.save(style_sets=ids); self.fill()
        return ids

    def rows(self):
        out = []
        for i in range(self.starts.rowCount()):
            kc, pc, gc = (self.starts.cellWidget(i, c) for c in range(3))
            out.append({"kind": kc.currentData(), "part": pc.currentData() or "", "gallery": gc.isChecked()})
        return out

    def starts_changed(self):
        if self._guard:
            return
        self.save(starts=[r for r in self.rows() if r["part"]] if False else self.rows())
        self.fill_checks()

    def kind_changed(self, row):
        rows = self.rows()
        ch = self.page_choices(rows[row]["kind"])
        rows[row]["part"] = ch[0][0] if ch else ""
        self.save(starts=rows); self._guard = True; self.fill_starts(); self._guard = False; self.fill_checks()

    def add_page(self, kind=None, part=None):
        rows = self.rows()
        used = {r["kind"] for r in rows}
        kind = kind or next((k for k, _l in TS.SLOT_KINDS if k not in used), "cover")
        ch = self.page_choices(kind)
        rows.append({"kind": kind, "part": part or (ch[0][0] if ch else ""), "gallery": True})
        self.save(starts=rows); self._guard = True; self.fill_starts(); self._guard = False; self.fill_checks()
        return rows

    def move_page(self, d):
        i = self.starts.currentRow()
        rows = self.rows()
        if not 0 <= i < len(rows) or not 0 <= i + d < len(rows):
            return rows
        rows[i], rows[i + d] = rows[i + d], rows[i]
        self.save(starts=rows); self._guard = True; self.fill_starts(); self._guard = False; self.starts.selectRow(i + d)
        return rows

    def remove_page(self, i=None):
        i = self.starts.currentRow() if i is None else i
        rows = self.rows()
        if 0 <= i < len(rows):
            rows.pop(i)
            self.save(starts=rows); self._guard = True; self.fill_starts(); self._guard = False; self.fill_checks()
        return rows
