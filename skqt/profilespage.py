"""Production > Effort Profiles (3.52.0): each effort type's profiles, built by picking. Left: the effort types with their
profiles (New profile..., Copy..., Rename..., Take out). Right: the profile's volumes, its parts filled from the libraries
(Change... offers the items tagged for this effort type; Show all lifts the filter; a newer version waits until Use it),
and the RFP's size limits, checked against what the profile gives each kind of text. Saved at once to the global
standards file; Templates lists what each profile makes. Rules only (effortprofiles.py); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout, QHBoxLayout,
                               QHeaderView, QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QTableWidget,
                               QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import diag
import effortprofiles as EP
import prodrules as PRL
import templatelib as TL
import templateprofile as TP
from . import design as D


class ChangeDialog(QDialog):
    """A part's choices from the library, filtered to the effort type (Show all lifts it), newest version first."""

    def __init__(self, parent, lib, slot, eid, current=None):
        super().__init__(parent)
        self.lib, self.slot, self.eid, self.current = lib, slot, eid, current
        self.setWindowTitle("Change this row"); self.resize(600, 460)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Items tagged for this effort type, for every effort type, or not tagged yet; retired items are left "
                            "out. The profile keeps the version you pick: a newer one waits until you choose it.", "muted"))
        self.all = QCheckBox("Show all"); self.all.toggled.connect(lambda _b: self.fill()); v.addWidget(self.all)
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(lambda _i: self.accept()); v.addWidget(self.list, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.fill()

    def fill(self):
        self.list.clear()
        for i in EP.choices(self.lib, self.slot, self.eid, self.all.isChecked()):
            w = QListWidgetItem(self.lib.shown_name(i) + ("   in use" if self.current == i["id"] else ""))
            w.setData(Qt.UserRole, i["id"]); w.setToolTip(i.get("note") or i.get("summary") or "")
            self.list.addItem(w)
        if not self.list.count():
            self.list.addItem(QListWidgetItem("Nothing fits yet: Show all, or import items on Formatting Standards, Quick Parts or Layout."))

    def picked(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it is not None else None


class EffortProfilesPage(QWidget):
    COLS = ["Section", "What", "In use", "Newer", ""]

    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.data, self.cur = None, None                  # cur: (eid, pid)
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        outer.setSpacing(D.SPACE["m"])
        outer.addWidget(D.label("Each effort type's profiles, built by picking from the libraries. A profile makes the templates for "
                                "its volumes (Templates lists them).", "muted"))
        split = QSplitter(Qt.Horizontal); outer.addWidget(split, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget(); self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(lambda cur, _prev: self.select(cur.data(0, Qt.UserRole) if cur else None))
        lv.addWidget(self.tree, 1)
        self.b_new = D.button("New profile...", None, lambda: self.new_profile())
        self.b_copy = D.button("Copy...", None, lambda: self.new_profile(copy=True), "A new profile starting from this one")
        self.b_rename = D.button("Rename...", "ghost", lambda: self.rename())
        self.b_out = D.button("Take out", "ghost", lambda: self.take_out(), "Take this profile out of this effort type")
        bw = QWidget(); bl = QGridLayout(bw); bl.setContentsMargins(0, 0, 0, 0)
        for k, b in enumerate((self.b_new, self.b_copy, self.b_rename, self.b_out)):
            bl.addWidget(b, k // 2, k % 2)
        lv.addWidget(bw)
        split.addWidget(left)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.title = D.label("", "title"); rv.addWidget(self.title)
        self.used = D.label("", "muted"); rv.addWidget(self.used)
        vr = QHBoxLayout(); rv.addLayout(vr)
        vr.addWidget(D.label("Volumes", "label", wrap=False))
        self.vols = QLineEdit(); self.vols.setPlaceholderText("The volumes this profile makes, separated by ;  (Volume I Technical; Volume IV Past Performance)")
        self.vols.editingFinished.connect(lambda: self.save_volumes())
        vr.addWidget(self.vols, 1)
        self.b_more = D.button("Content map, fields and font rules...", None, lambda: self.more(),     # 3.69.0
                               "This profile's content map, the fields its template asks for, and every font rule (allowed "
                               "fonts, smallest and largest sizes)")
        vr.addWidget(self.b_more)
        card = D.Card("Sections", "One row per decision for each section of the volume, filled from the libraries. Change... offers the items tagged for this effort type.")
        rv.addWidget(card, 3)
        self.t = QTableWidget(0, len(self.COLS)); self.t.setHorizontalHeaderLabels(self.COLS)
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setWordWrap(True)
        self.t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        for i, w in enumerate((120, 180, 240, 80)):
            self.t.setColumnWidth(i, w)
        card.add(self.t)
        lim = D.Card("RFP limits for this profile", "The smallest size the RFP allows for each kind of text, checked against the "
                     "size the profile gives it. An effort's own limits stay in Effort Formatting.")
        rv.addWidget(lim, 2)
        self.lt = QTableWidget(0, 4); self.lt.setHorizontalHeaderLabels(["Text", "Smallest allowed (pt)", "This profile", "Check"])
        self.lt.verticalHeader().setVisible(False); self.lt.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.lt.setColumnWidth(0, 170); self.lt.setColumnWidth(1, 150); self.lt.setColumnWidth(2, 110)
        lim.add(self.lt)
        split.addWidget(right)
        split.setSizes([300, 900])
        self.empty = D.label("Pick a profile on the left.", "muted"); rv.addWidget(self.empty)

    def more(self, modal=True):
        """3.69.0: the profile's content map, fields and font rules (they lived in Production Standards)."""
        if self.cur is None:
            return None
        from .stdeditor import ProfileStore, window
        dlg = window(self.host, ProfileStore(self.host.config_dir, *self.cur), ["fonts", "content_map", "fillins"],
                     f"{self.title.text()}: content map, fields and font rules")
        if modal:
            dlg.exec()
            self.refresh()
        return dlg

    # ---- loading and saving
    def refresh(self):
        self.data = PRL.load(self.host.config_dir)
        self.fill_tree()

    def save(self):
        PRL.save(self.host.config_dir, self.data)
        diag.activity("effort_profiles_saved")

    def fill_tree(self):
        keep = self.cur
        self.tree.blockSignals(True); self.tree.clear()
        heads = {}
        first = None
        for p in EP.profiles(self.data):
            h = heads.get(p["eid"])
            if h is None:
                h = QTreeWidgetItem([p["ename"]]); h.setFlags(h.flags() & ~Qt.ItemIsSelectable)
                f = h.font(0); f.setBold(True); h.setFont(0, f)
                self.tree.addTopLevelItem(h); heads[p["eid"]] = h
            it = QTreeWidgetItem([p["pname"]]); it.setData(0, Qt.UserRole, (p["eid"], p["pid"]))
            h.addChild(it)
            first = first or it
            if keep == (p["eid"], p["pid"]):
                self.tree.setCurrentItem(it)
        self.tree.expandAll(); self.tree.blockSignals(False)
        if keep is None or self.tree.currentItem() is None or self.tree.currentItem().data(0, Qt.UserRole) != keep:
            if first is not None:
                self.tree.setCurrentItem(first)
            self.select(first.data(0, Qt.UserRole) if first is not None else None)
        else:
            self.select(keep)

    def select(self, key):
        self.cur = tuple(key) if key else None
        on = self.cur is not None
        for w in (self.t, self.lt, self.vols, self.b_copy, self.b_rename, self.b_out, self.b_more):
            w.setEnabled(on)
        self.empty.setVisible(not on)
        if not on:
            self.title.setText(""); self.used.setText("")
            return
        eid, pid = self.cur
        e = PRL.effort_type_of(self.data, eid)
        self.title.setText(f"{PRL.type_of(self.data, pid)['name']}  ({e['name'] if e else ''})")
        others = [n for n in EP.used_by(self.data, pid) if not e or n != e["name"]]
        self.used.setText(("Also in: " + ", ".join(others) + ". Its sections and limits here are this effort type's own.") if others else "")
        self.vols.setText("; ".join(EP.volumes(self.data, eid, pid)))
        self.fill_parts(); self.fill_limits()

    def fill_parts(self):
        eid, pid = self.cur
        lib = TL.Library(self.host.config_dir)
        std = EP.resolved(self.data, eid, pid)
        self.slots = TP.slots(std)
        self.t.setRowCount(0)
        for slot, part, what, _k in self.slots:
            stt = TP.state(std, lib, slot)
            r = self.t.rowCount(); self.t.insertRow(r)
            use = lib.shown_name(stt["item"]) if stt["item"] is not None else (
                "a version no longer in the library" if stt["pin"] else "the Global Standards's values")
            for c, text in enumerate((part, what, use, (f"v{stt['newer']['version']} saved" if stt["newer"] else ""))):
                it = QTableWidgetItem(text); it.setData(Qt.UserRole, slot)
                if c == 3 and stt["newer"]:
                    it.setForeground(D.color("warn"))
                self.t.setItem(r, c, it)
            cell = QWidget(); h = QHBoxLayout(cell); h.setContentsMargins(2, 0, 2, 0); h.setSpacing(4)
            h.addWidget(D.button("Change...", None, lambda _=False, s_=slot: self.change(s_)))
            if stt["newer"]:
                h.addWidget(D.button(f"Use v{stt['newer']['version']}", "primary", lambda _=False, s_=slot: self.use_newer(s_)))
            h.addStretch(1)
            self.t.setCellWidget(r, 4, cell)
        self.t.resizeRowsToContents()

    def fill_limits(self):
        eid, pid = self.cur
        self.lt.blockSignals(True); self.lt.setRowCount(0)
        for r_ in EP.limits(EP.resolved(self.data, eid, pid)):
            r = self.lt.rowCount(); self.lt.insertRow(r)
            self.lt.setItem(r, 0, QTableWidgetItem(r_["what"]))
            sp = QDoubleSpinBox(); sp.setRange(0, 72); sp.setDecimals(1); sp.setSingleStep(0.5); sp.setSpecialValueText("not set")
            sp.setValue(r_["min"] or 0)
            sp.editingFinished.connect(lambda s_=r_["scope"], w_=sp: self.set_limit(s_, w_.value()))
            self.lt.setCellWidget(r, 1, sp)
            self.lt.setItem(r, 2, QTableWidgetItem(f"{r_['value']:g} pt" if r_["value"] is not None else "not set"))
            chk = QTableWidgetItem("met" if r_["ok"] else ("under the limit" if r_["ok"] is False else ""))
            if r_["ok"] is False:
                chk.setForeground(D.color("crit"))
            elif r_["ok"]:
                chk.setForeground(D.color("ok"))
            self.lt.setItem(r, 3, chk)
        self.lt.blockSignals(False)

    # ---- actions
    def change(self, slot, iid=None):
        eid, pid = self.cur
        lib = TL.Library(self.host.config_dir)
        if iid is None:
            cur = (TP.pins(EP.resolved(self.data, eid, pid)).get(slot) or {}).get("id")
            d = ChangeDialog(self, lib, slot, eid, cur)
            if d.exec() != QDialog.Accepted:
                return ""
            iid = d.picked()
        if not iid:
            return ""
        said = EP.pick(self.data, eid, pid, lib, slot, iid, self.host.config_dir)
        self.save(); self.fill_parts(); self.fill_limits()
        broken = EP.broken_limits(EP.resolved(self.data, eid, pid))
        self.host.status(("Picked " + said + ". ") + (("Check: " + broken[0]) if broken else "Every limit is met."))
        return said

    def use_newer(self, slot):
        eid, pid = self.cur
        stt = EP.slot_state(self.data, eid, pid, TL.Library(self.host.config_dir), slot)
        return self.change(slot, stt["newer"]["id"]) if stt["newer"] else ""

    def set_limit(self, scope, value):
        eid, pid = self.cur
        EP.set_limit(self.data, eid, pid, scope, value or None)
        self.save(); self.fill_limits()
        return EP.limits(EP.resolved(self.data, eid, pid))

    def save_volumes(self, text=None):
        if self.cur is None:
            return []
        eid, pid = self.cur
        got = EP.set_volumes(self.data, eid, pid, (self.vols.text() if text is None else text).split(";"))
        self.save()
        self.vols.setText("; ".join(got))
        return got

    def new_profile(self, name=None, copy=False):
        eid = self.cur[0] if self.cur else ((self.data.get("effort_types") or [{}])[0].get("id"))
        if not eid:
            return ""
        if name is None:
            name, ok = QInputDialog.getText(self, "New profile", "Name of the profile (Past Performance Volume, Orals):")
            if not ok:
                return ""
        pid = EP.add(self.data, eid, name, copy_from=self.cur[1] if (copy and self.cur) else None)
        if not pid:
            self.host.status("That name is empty or already in this effort type.")
            return ""
        self.save(); self.cur = (eid, pid); self.fill_tree()
        return pid

    def rename(self, name=None):
        if self.cur is None:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename the profile", "New name:", text=PRL.type_of(self.data, self.cur[1])["name"])
            if not ok:
                return False
        if not EP.rename(self.data, self.cur[1], name):
            self.host.status("That name is empty or already used.")
            return False
        self.save(); self.fill_tree()
        return True

    def take_out(self):
        if self.cur is None:
            return False
        if not EP.remove(self.data, *self.cur):
            self.host.status("An effort type keeps at least one profile.")
            return False
        self.save(); self.cur = None; self.fill_tree()
        return True
