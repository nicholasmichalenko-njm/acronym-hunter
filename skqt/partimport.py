"""Bring in parts from a document (3.95.0; canvas "Libraries and Sets" board 5): a Word file read once (it is only
read). Its pages, one per Word section, each with what it most likely is (a cover, a CUI page, a title page, contents,
acronyms...: change it if the guess is wrong), its name and its first lines; and its Quick Parts gallery, each one New
or Already have it. A tick each, and the part set they go into. Rules: partlib. Nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

import diag
import partlib as PT
import stylelib as SL
from . import design as D
from .stylespage import dot

STATE = {"new": "New", "variant": "Different from yours (a new version)", "same": "Already have it"}


class PartImport(QDialog):
    def __init__(self, page, plan):
        super().__init__(page)
        self.page, self.plan = page, plan
        self.setWindowTitle("Bring in parts"); self.resize(1100, 720)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"<b>Bring in parts from {os.path.basename(plan['path'])}</b>", None))
        v.addWidget(D.label(f"{len(plan['pages'])} page(s), one per Word section, and {len(plan['gallery'])} Quick Part(s). Each page is "
                            "kept whole, exactly as built in Word. Check what each page is; the file is only read.", "muted"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Part", "What it is", "Its first lines", "Against yours"])
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 260); self.table.setColumnWidth(1, 220); self.table.setColumnWidth(3, 200)
        self.table.itemChanged.connect(lambda it: self.edited(it))
        v.addWidget(self.table, 1)
        foot = QHBoxLayout()
        foot.addWidget(D.label("Into the part set", "muted", wrap=False))
        self.set_box = QComboBox(); self.set_box.addItem("No set", None)
        for k in SL.sets(page.lib, "part"):
            self.set_box.addItem(dot(k.get("color") or "#64748B"), k["name"], k["id"])
        if page.sid:
            self.set_box.setCurrentIndex(max(0, self.set_box.findData(page.sid)))
        foot.addWidget(self.set_box)
        self.n_lab = D.label("", "muted", wrap=False); foot.addWidget(self.n_lab, 1)
        foot.addWidget(D.button("Cancel", None, self.reject))
        self.b_go = D.button("Bring in", "primary", lambda: self.go())
        foot.addWidget(self.b_go)
        v.addLayout(foot)
        self.fill()

    def entries(self):
        return [("page", p) for p in self.plan["pages"]] + [("quick", e) for e in self.plan["gallery"]]

    def fill(self):
        self.table.blockSignals(True)
        rows = self.entries()
        self.table.setRowCount(len(rows))
        for i, (what, e) in enumerate(rows):
            it = QTableWidgetItem(e["name"])
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | (Qt.ItemIsEditable if what == "page" else Qt.NoItemFlags))
            it.setCheckState(Qt.Checked if e.get("keep") else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            if what == "page":
                cb = QComboBox()
                for k in PT.PAGE_SHELVES:
                    cb.addItem(PT.PAGE_WORDS[k], k)
                cb.setCurrentIndex(max(0, cb.findData(e["kind"])))
                cb.currentIndexChanged.connect(lambda _i, e=e, cb=cb: e.__setitem__("kind", cb.currentData()))
                self.table.setCellWidget(i, 1, cb)
                lines = QTableWidgetItem("  /  ".join(t[:60] for t in e["lines"][:4])); lines.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(i, 2, lines)
                self.table.setItem(i, 3, self.ro(f"Page {e['n']} of the file"))
            else:
                self.table.setItem(i, 1, self.ro(f"Quick Part · {e.get('category') or 'no category'}"))
                self.table.setItem(i, 2, self.ro((e.get("text") or "")[:160]))
                self.table.setItem(i, 3, self.ro(STATE.get(e["state"], e["state"])))
        self.table.blockSignals(False)
        self.count()

    @staticmethod
    def ro(text):
        it = QTableWidgetItem(text); it.setFlags(Qt.ItemIsEnabled)
        return it

    def edited(self, it):
        rows = self.entries()
        if it.column() != 0 or not 0 <= it.row() < len(rows):
            return
        what, e = rows[it.row()]
        e["keep"] = it.checkState() == Qt.Checked
        if what == "page" and it.text().strip():
            e["name"] = " ".join(it.text().split())[:80]
        self.count()

    def count(self):
        n = sum(1 for _w, e in self.entries() if e.get("keep"))
        self.n_lab.setText(f"{n} ticked")
        self.b_go.setText(f"Bring in {n} part(s)")
        self.b_go.setEnabled(n > 0)
        return n

    def go(self):
        page = self.page
        designs, items = PT.keep(page.cfg(), page.lib, self.plan)
        ids = ["d:" + d["id"] for d in designs] + ["q:" + i["id"] for i in items]
        sid = self.set_box.currentData()
        if sid and ids:
            PT.add_to_set(page.cfg(), page.lib, sid, ids)
        diag.activity("parts_brought_in", pages=len(designs), quick=len(items))
        said = [f"{len(designs)} page(s)" if designs else "", f"{len(items)} Quick Part(s)" if items else ""]
        page.host.toast(" and ".join(x for x in said if x) + " brought in." + (" Set what fills each page on the right." if designs else ""))
        self.kept = (designs, items)
        if designs:
            k = next((k for k, _t, s in PT.KINDS if designs[-1]["shelf"] in s), page.kind)
            page.cur = "d:" + designs[-1]["id"]
        elif items:
            k, page.cur = "quick", "q:" + items[-1]["id"]
        else:
            k = page.kind
        page.lib.fresh()
        page.fill_tabs(); page.fill_sets()
        page.tabs.setCurrentIndex(next(i for i in range(page.tabs.count()) if page.tabs.tabData(i) == k))
        page.kind = k
        page.fill_rows()
        self.accept()
        return designs, items


def bring_in(page, path=None, run=True):
    if path is None:
        path, _f = QFileDialog.getOpenFileName(page, "Bring in parts from a document", "",
                                               "Word files and templates (*.docx *.dotx *.docm *.dotm)")
        if not path:
            return None
    try:
        plan = PT.look(path, page.lib)
    except Exception as e:  # noqa: BLE001  a file Word cannot open either
        diag.swallowed()
        page.host.status(f"That file could not be read ({type(e).__name__}).")
        return None
    if not plan["pages"] and not plan["gallery"]:
        page.host.status("That file holds no pages or Quick Parts to bring in.")
        return None
    dlg = PartImport(page, plan)
    page.import_dialog = dlg
    if run:
        dlg.exec()
    return dlg
