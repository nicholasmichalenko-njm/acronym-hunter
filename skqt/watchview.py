"""Watched folders in the window (2.94.0): a strip under the header says what the last check found (new files, changed
files, documents whose file is missing) with what to do about each; the Watched folders dialog lists the folders and
adds or removes one; Review missing lets the person find a file, keep the record without it, or mark the document
withdrawn. The check itself runs in the background (watch.py). Nothing leaves the PC."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView,
                               QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import watch as WA
from . import design as D


class WatchStrip(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("watchStrip")
        h = QHBoxLayout(self); h.setContentsMargins(D.SPACE["xl"], 6, D.SPACE["xl"], 6); h.setSpacing(D.SPACE["s"])
        self.text = QLabel(""); self.text.setWordWrap(True); self.text.setTextFormat(Qt.RichText); h.addWidget(self.text, 1)
        self.add_btn = D.button("Add them...", "primary", lambda: host.watch_add(), "Read the new and changed files and add them "
                                "(a changed file is offered as a new version of its document)")
        self.skip_btn = D.button("Not these", None, lambda: host.watch_set_aside(), "Do not offer these files again unless they change")
        self.miss_btn = D.button("Review missing...", None, lambda: host.watch_missing(), "Find the file, keep the record without "
                                 "it, or mark the document withdrawn")
        for b in (self.add_btn, self.skip_btn, self.miss_btn):
            h.addWidget(b)
        self.setVisible(False)

    def show_found(self, found):
        found = found or {"new": [], "changed": [], "missing": []}
        n_new, n_ch, n_miss = len(found["new"]), len(found["changed"]), len(found["missing"])
        t = D.tokens()
        tone = "crit" if n_miss else "warn"
        self.setStyleSheet(f"QWidget#watchStrip{{background:{t[tone + '_soft']};}} QWidget#watchStrip QLabel{{color:{t['text']};}}")
        bits = []
        if n_new or n_ch:
            names = [os.path.basename(p) for p, _c in found["new"][:3]] + [os.path.basename(p) for p, _d, _v in found["changed"][:2]]
            bits.append(f"<b>{WA.summary({'new': found['new'], 'changed': found['changed'], 'missing': []})}</b> in the watched "
                        f"folders: {', '.join(names)}{'...' if n_new + n_ch > len(names) else ''}.")
        if n_miss:
            bits.append(f"<b>{n_miss} document file(s) missing</b>: " + ", ".join(d["name"] for d, _v, _p in found["missing"][:3])
                        + ("..." if n_miss > 3 else "") + ". The documents stay; decide what happened.")
        self.text.setText(" ".join(bits))
        self.add_btn.setVisible(bool(n_new or n_ch)); self.skip_btn.setVisible(bool(n_new or n_ch)); self.miss_btn.setVisible(bool(n_miss))
        self.setVisible(bool(n_new or n_ch or n_miss))
        return self.isVisible()


class MissingDialog(QDialog):
    """Each document whose file is gone: Find it..., Keep without the original, Mark withdrawn."""

    def __init__(self, host, found):
        super().__init__(host)
        self.host = host
        self.setWindowTitle("Document files missing")
        self.resize(900, 420)
        v = QVBoxLayout(self)
        v.addWidget(D.label("These documents were read from files that are no longer in the watched folders. The documents and "
                            "their text stay in the effort. Say what happened to each.", "muted"))
        self.t = QTableWidget(0, 3); self.t.setHorizontalHeaderLabels(["Document", "Its file was", "What happened"])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.setColumnWidth(0, 220); self.t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.t.setColumnWidth(2, 380)
        self.t.verticalHeader().setDefaultSectionSize(38); self.t.setProperty("sk_rows_fixed", True)
        v.addWidget(self.t, 1)
        self.rows = []
        for d, ver, p in found["missing"]:
            i = self.t.rowCount(); self.t.insertRow(i)
            self.t.setItem(i, 0, QTableWidgetItem(d["name"])); self.t.setItem(i, 1, QTableWidgetItem(p))
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(2, 1, 2, 1); h.setSpacing(4)
            h.addWidget(D.button("Find it...", None, lambda _=False, di=d["id"]: self.find(di), "Point at where the file went"))
            h.addWidget(D.button("Keep without it", None, lambda _=False, di=d["id"]: self.keep(di), "The document stays; its file is gone"))
            h.addWidget(D.button("Withdrawn", "ghost", lambda _=False, di=d["id"]: self.withdrawn(di), "The customer withdrew it"))
            self.t.setCellWidget(i, 2, w)
            self.rows.append(d["id"])
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept)
        v.addWidget(bb)
        self.done_ids = set()

    def _row_done(self, doc_id, text):
        i = self.rows.index(doc_id)
        lab = QLabel(text); lab.setContentsMargins(6, 0, 0, 0)
        self.t.cellWidget(i, 2).hide()
        self.t.setCellWidget(i, 2, lab)
        self.done_ids.add(doc_id)

    def find(self, doc_id, path=None):
        lib, rec = self.host.watch_lib_rec()
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Where is the file now?", self.host.watch_customer_dir())
            if not path:
                return None
        if WA.found_at(lib, rec, doc_id, path):
            self._row_done(doc_id, "Found: the same file at a new place")
            return True
        self.host.status("That file holds other contents. Add it as a new version from the Library (Add files...).")
        return False

    def keep(self, doc_id):
        lib, rec = self.host.watch_lib_rec()
        ok = WA.keep_without_original(lib, rec, doc_id)
        if ok:
            self._row_done(doc_id, "Kept without its original file")
        return ok

    def withdrawn(self, doc_id):
        lib, rec = self.host.watch_lib_rec()
        ok = WA.mark_withdrawn(lib, rec, doc_id)
        if ok:
            self._row_done(doc_id, "Marked withdrawn")
        return ok


class FoldersDialog(QDialog):
    """Library > Watched folders...: the folders checked for new, changed and missing files."""

    CATS = None

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.setWindowTitle("Watched folders")
        self.resize(860, 380)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Stationkeeper checks these folders, and every folder inside them, when the effort opens, when the "
                            "Library refreshes, and every few minutes. New files are offered to add, changed files as new "
                            "versions, and a document whose file is gone is reported until you decide what happened.", "muted"))
        self.t = QTableWidget(0, 2); self.t.setHorizontalHeaderLabels(["Folder", "New files go to"])
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.t.setColumnWidth(1, 220)
        v.addWidget(self.t, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("+ Folder...", None, lambda: self.add()))
        row.addWidget(D.button("Stop watching", "ghost", lambda: self.remove()))
        row.addStretch(1)
        row.addWidget(D.button("Check now", "primary", lambda: self.check()))
        self.last = D.label("", "muted"); v.addWidget(self.last)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept)
        v.addWidget(bb)
        self.fill()

    def fill(self):
        from .stagesedit import clear_table
        import docversions as DV
        clear_table(self.t)
        data, cust = self.host.ws.root, self.host.watch_customer_dir()
        names = {"": "Guessed from the folders"}
        try:
            names.update(dict(DV.Library(self.host.ws.p("documents")).load().categories()))
        except Exception:
            diag.swallowed()
        for p, cat, built in WA.folders(data, cust):
            i = self.t.rowCount(); self.t.insertRow(i)
            it = QTableWidgetItem(p + ("   (the effort's Customer Documents, always watched)" if built else "")); it.setData(Qt.UserRole, (p, built))
            self.t.setItem(i, 0, it); self.t.setItem(i, 1, QTableWidgetItem(names.get(cat, cat)))
        st = WA.load(data)
        self.last.setText(f"Last checked {st['last'].replace('T', ' ')}." if st.get("last") else "Not checked yet.")

    def add(self, path=None, category=""):
        if path is None:
            path = QFileDialog.getExistingDirectory(self, "Watch a folder (and every folder in it)")
            if not path:
                return False
        ok = WA.add_folder(self.host.ws.root, path, category)
        self.fill()
        if ok:
            diag.activity("qt_watch_folder_added")
            self.host.watch_now()
        return ok

    def remove(self):
        i = self.t.currentRow()
        if i < 0:
            return False
        p, built = self.t.item(i, 0).data(Qt.UserRole)
        if built:
            self.host.status("The effort's Customer Documents folder is always watched.")
            return False
        ok = WA.remove_folder(self.host.ws.root, p)
        self.fill()
        return ok

    def check(self):
        found = self.host.watch_now()
        self.fill()
        self.host.toast(WA.summary(found) or "Nothing new, changed or missing")
        return found
