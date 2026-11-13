"""Bring in styles from a document (3.94.0; canvas "Libraries and Sets" board 2): only the styles of a Word file or
template (it is only read). 4.30.2: a set owns its styles. Each style of the file says what happens to it: New; Same
name, other values (the set gets its own, the others' stay); Identical to one you have (one style, used here too). A
choice is asked only where the set picked already has the name with other values: keep the set's, take the file's, or
keep both. Quick Parts, page setups and the rest come in on their own pages. Rules only (No AI)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

import diag
import stylelib as SL
import styleown as SO
from . import design as D
from .stylespage import dot, preview

FILTERS = (("new", "New"), ("variant", "Same name, other values"), ("same", "Identical to one you have"))


class StyleImport(QDialog):
    def __init__(self, page, path, rows):
        super().__init__(page)
        self.page, self.path, self.rows = page, path, rows
        self.setWindowTitle("Bring in styles"); self.resize(1240, 760)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"<b>Bring in styles from {os.path.basename(path)}</b>", None))
        v.addWidget(D.label(f"{len(rows)} styles in the file. Only styles are shown here; Quick Parts and the rest come in on their own "
                            "pages. The file is only read.", "muted"))
        fr = QHBoxLayout(); fr.setSpacing(D.SPACE["s"])
        self.chips = {}
        t = D.tokens()
        style = (f"QPushButton{{border:1px solid {t['border_strong']};border-radius:12px;padding:3px 10px;background:{t['surface']};color:{t['text']}}}"
                 f"QPushButton:checked{{border:2px solid {t['accent']};background:{t['accent_soft']};color:{t['accent']};font-weight:600}}")
        for k, word in FILTERS:
            b = QPushButton(f"{word} {sum(1 for r in rows if r['state'] == k)}"); b.setCheckable(True); b.setChecked(True)   # 4.30.1: all shown
            b.setStyleSheet(style); b.toggled.connect(lambda _on: self.fill()); fr.addWidget(b); self.chips[k] = b
        fr.addStretch(1)
        # 4.30.1 (Nicholas 2026-11-13 14:30): one set for the whole import, so a style you already have is not missed
        fr.addWidget(D.label("Put every ticked style in the set", "muted", wrap=False))
        self.set_all = QComboBox(); self.set_all.addItem("No set", None)
        for k in SL.sets(page.lib):
            self.set_all.addItem(dot(k.get("color") or "#64748B"), k["name"], k["id"])
        self.set_all.addItem("New set...", "__new__")
        self.set_all.setCurrentIndex(max(0, self.set_all.findData(page.sid)) if page.sid else 0)
        for r in rows:
            r["set"] = page.sid or None
        self.set_all.activated.connect(lambda _i: self.pick_set(self.set_all.currentData()))
        fr.addWidget(self.set_all)
        self.b_all = D.button("Untick all shown", "ghost", lambda: self.tick_all())
        fr.addWidget(self.b_all)
        v.addLayout(fr)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Style", "What happens", "Yours", "In this file", "Into the set"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.Stretch); hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 220); self.table.setColumnWidth(1, 230); self.table.setColumnWidth(4, 200)
        self.table.itemChanged.connect(lambda it: self.ticked(it))
        v.addWidget(self.table, 1)
        v.addWidget(D.label("Every style of the file is listed and ticked. A set owns its styles: one with a name another set uses, "
                            "with other values, becomes this set's own and theirs stay. One identical to a style you have is one style, "
                            "used in this set too. You are asked only where this set already has the name with other values. Each keeps "
                            "Word's own definition as it is in the file.", "muted"))
        foot = QHBoxLayout()
        self.n_lab = D.label("", "muted", wrap=False); foot.addWidget(self.n_lab, 1)
        foot.addWidget(D.button("Cancel", None, self.reject))
        self.b_go = D.button("Bring in", "primary", lambda: self.go())
        foot.addWidget(self.b_go)
        v.addLayout(foot)
        self.shown = []
        self.fill()

    def fill(self):
        want = {k for k, b in self.chips.items() if b.isChecked()}
        self.shown = [r for r in self.rows if r["state"] in want]
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.shown))
        sets = SL.sets(self.page.lib)
        for i, r in enumerate(self.shown):
            it = QTableWidgetItem(f"{r['name']}\n{'Character' if r['type'] == 'character' else 'Paragraph'} style")
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if r["keep"] else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(r["words"]))
            if r.get("clash"):                                # 4.30.2: the one question, on the row it is about
                ch = QComboBox(); ch.setObjectName("clashChoice")
                for key, word in SO.CHOICES:
                    ch.addItem(word, key)
                ch.setCurrentIndex(max(0, ch.findData(r.get("choice") or "mine")))
                ch.setToolTip("This set has a style of this name with other values. Keep both: the set holds the two, with a v switch on its row.")
                ch.currentIndexChanged.connect(lambda _i, r=r, ch=ch: (r.__setitem__("choice", ch.currentData()), self.count()))
                self.table.setCellWidget(i, 1, ch)
            else:
                self.table.removeCellWidget(i, 1)
            shown_mine = r.get("clash") or r.get("mine")
            mine = self.page.lib.values(shown_mine) if shown_mine else None
            if mine:
                self.table.setCellWidget(i, 2, preview(mine, name=r["name"]))
            else:
                self.table.setItem(i, 2, QTableWidgetItem("No style by this name"))
            self.table.setCellWidget(i, 3, preview(r["values"], name=r["name"]))
            cb = QComboBox(); cb.addItem("No set", None)
            for k in sets:
                cb.addItem(dot(k.get("color") or "#64748B"), k["name"], k["id"])
            if r.get("set"):
                cb.setCurrentIndex(max(0, cb.findData(r["set"])))
            cb.currentIndexChanged.connect(lambda _i, r=r, cb=cb: self.row_set(r, cb.currentData()))
            self.table.setCellWidget(i, 4, cb)
            self.table.setRowHeight(i, 58)
        self.table.blockSignals(False)
        self.count()

    def pick_set(self, sid, name=None):
        """The set for the whole import: every style's row takes it (a row can still be given another). New set...
        asks its name (name: tests). Returns the set's id, or None for No set."""
        if sid == "__new__":
            if name is None:
                from PySide6.QtWidgets import QInputDialog
                name, ok = QInputDialog.getText(self, "New set", "The set's name (what these styles are for):")
                if not ok:
                    name = ""
            k = SL.new_set(self.page.lib, name) if (name or "").strip() else None
            sid = k["id"] if k else None
            if k:
                self.set_all.insertItem(self.set_all.count() - 1, dot(k.get("color") or "#64748B"), k["name"], k["id"])
            self.set_all.setCurrentIndex(max(0, self.set_all.findData(sid)))
        for r in self.rows:
            r["set"] = sid
        SO.retarget(self.page.lib, self.rows, sid)
        self.fill()
        return sid

    def row_set(self, r, sid):
        """One row given another set: it is judged against that set."""
        r["set"] = sid
        SO.retarget(self.page.lib, [r], sid)
        self.fill()

    def tick_all(self, on=None):
        """Every style shown ticked, or none (the button says which)."""
        on = (not all(r["keep"] for r in self.shown)) if on is None else bool(on)
        for r in self.shown:
            r["keep"] = on
        self.fill()
        return on

    def ticked(self, it):
        if it.column() == 0 and 0 <= it.row() < len(self.shown):
            self.shown[it.row()]["keep"] = it.checkState() == Qt.Checked
            self.count()

    def count(self):
        n = sum(1 for r in self.rows if r["keep"])
        same = sum(1 for r in self.rows if r["keep"] and r["state"] == "same")
        in_set = sum(1 for r in self.rows if r["keep"] and r.get("set"))
        lost = sum(1 for r in self.rows if r["keep"] and r["state"] == "same" and not r.get("set"))
        ask = [r for r in self.rows if r["keep"] and r.get("clash")]
        kept = sum(1 for r in ask if (r.get("choice") or "mine") == "mine")
        self.n_lab.setText(f"{n} ticked: {sum(1 for r in self.rows if r['keep'] and r['state'] != 'same' and not (r.get('clash') and (r.get('choice') or 'mine') == 'mine'))} come in" + (f", {same} you already have" if same else "")
                           + (f", {len(ask)} to choose ({kept} keep the set's)" if ask else "")
                           + (f". {in_set} go into a set" if in_set else ". No set picked")
                           + (f". {lost} you already have and no set is picked for: nothing changes for those" if lost else "") + ".")
        self.b_go.setText(f"Bring in {n} style(s)")
        self.b_go.setEnabled(n > 0)
        self.b_all.setText("Untick all shown" if self.shown and all(r["keep"] for r in self.shown) else "Tick all shown")
        return n

    def go(self):
        lib = self.page.lib
        c = SL.bring_in(lib, self.rows, self.path, set_of={r["name"]: r.get("set") for r in self.rows if r.get("set")})
        diag.activity("styles_brought_in", added=c["new"], items=c["variant"])
        n_set = sum(1 for r in self.rows if r["keep"] and r.get("set"))
        self.page.host.toast(f"{c['new']} new style(s), {c['variant']} with a name you had and other values"
                             + (f", {c['kept']} left as the set had them" if c.get("kept") else "")
                             + (f", {c['same']} you had already" if c["same"] else "") + (f"; {n_set} in their set" if n_set else ""))
        self.result_counts = c
        self.page.fill_sets(); self.page.fill_rows()
        self.accept()
        return c


def bring_in(page, path=None, run=True):
    if path is None:
        path, _f = QFileDialog.getOpenFileName(page, "Bring in styles from a document", "",
                                               "Word files and templates (*.docx *.dotx *.docm *.dotm)")
        if not path:
            return None
    try:
        rows = SO.against(page.lib, SL.read_styles(path), page.sid)
    except Exception as e:  # noqa: BLE001  a file Word cannot open either
        diag.swallowed()
        page.host.status(f"The styles in that file could not be read ({type(e).__name__}).")
        return None
    if not rows:
        page.host.status("That file holds no paragraph or character styles.")
        return None
    dlg = StyleImport(page, path, rows)
    page.import_dialog = dlg
    if run:
        dlg.exec()
    return dlg
