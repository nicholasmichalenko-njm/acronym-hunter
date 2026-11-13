"""What a section prints (3.86.0, claude/stationkeeper-setup-from-review-2026-11-08.md): Setup's list of the blocks the
setup will print in the selected section, in print order, each with its kind and where it came from. Act on the row:
Earlier, Later, Move to another section..., Print the reference only (or the words again), Show it in Review. One set
of records: a move here moves it in Review and the matrix too. Rules: setupdoc. Nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu

import diag
import setupdoc as SD
from . import design as D

KIND = {"Requirement": "Requirement", "Evaluation": "Evaluation", "Context": "Support", "Customer": "Customer's"}


class BlockList(QListWidget):
    def __init__(self, page):
        super().__init__()
        self.pg = page
        self.label = None
        self.setWordWrap(True)
        self.setMaximumHeight(170)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda p: self.menu(self.viewport().mapToGlobal(p)))
        self.itemDoubleClicked.connect(lambda _it: self.menu())

    def M(self):
        return self.pg._M()

    def fill(self, label):
        self.label = label
        self.clear()
        M = self.M()
        if M is None or not label:
            self.setVisible(False)
            return 0
        ids = SD.placed_in(M).get(label, [])
        B, inh = SD.by_id(M), SD.inherited_sections(M)
        from . import amendflags as AF                             # 3.89.0 decision 6: changed by an amendment
        self.amend = AF.flags(self.pg.host)
        for n, iid in enumerate(ids, 1):
            it = B.get(iid)
            if it is None:
                continue
            kind = KIND.get(SD.kind_of(it), SD.kind_of(it))
            src = SD.where_of(it) or it.get("file", "")
            text = SD.block_text(M, it, inh)
            row = QListWidgetItem(f"{n}. {kind}" + ("  (reference only)" if SD.refonly(M, iid) else "")
                                  + (f"  ·  {src}" if src else "") + f"\n{text[:180]}")
            row.setData(Qt.UserRole, iid)
            row.setToolTip(f"From {it.get('file', '')}" + (f", {src}" if src else ""))
            fl = self.amend.get(iid)
            if fl:
                row.setText(row.text().replace("\n", f"  ·  {fl[0]['text']}\n", 1))
                row.setForeground(D.color("warn"))
                row.setToolTip(row.toolTip() + "\n" + "\n".join(x["text"] for x in fl) + "\nIt keeps its place. Decide the change in Amendments.")
            self.addItem(row)
        self.setVisible(self.count() > 0)
        return self.count()

    def current(self):
        it = self.currentItem()
        return it.data(Qt.UserRole) if it is not None else None

    def menu(self, at=None, run=True):
        iid = self.current()
        if iid is None:
            return None
        M = self.M()
        m = QMenu(self)
        m.addAction("Earlier", lambda: self.move(iid, -1))
        m.addAction("Later", lambda: self.move(iid, 1))
        m.addAction("Move to another section...", lambda: self.move_to(iid))
        m.addSeparator()
        m.addAction("Print the words again" if SD.refonly(M, iid) else "Print the reference only", lambda: self.toggle_ref(iid))
        m.addAction("Show it in Shred", lambda: self.show_source(iid))
        fl = (getattr(self, "amend", None) or {}).get(iid)
        if fl:                                                    # 3.89.0 decision 6
            from . import amendflags as AF
            m.addAction(f"Open the change in Amendments ({fl[0]['text']})", lambda: AF.open_change(self.pg.host, fl[0]))
        if run:
            m.exec(at or self.viewport().mapToGlobal(self.visualItemRect(self.currentItem()).bottomLeft()))
        return m

    def _changed(self, msg):
        try:
            self.pg.host.review.snap()
        except Exception:  # noqa: BLE001
            diag.swallowed()

    def _after(self, iid, msg):
        self.pg.host.changed()
        self.fill(self.label)
        for i in range(self.count()):
            if self.item(i).data(Qt.UserRole) == iid:
                self.setCurrentRow(i)
        try:
            import html
            import setupmake as SM
            self.pg.prev.setText("<br>".join(f"<b>{html.escape(t)}</b>: {html.escape(x)}" for t, x in SM.preview(self.M(), self.label)))
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.pg.host.status(msg)

    def move(self, iid, delta):
        M = self.M()
        self._changed("move")
        SD.move(M, iid, self.label, delta)
        M.pending = True
        self._after(iid, "Moved " + ("earlier." if delta < 0 else "later."))
        return True

    def move_to(self, iid, to=None):
        M = self.M()
        if to is None:
            from PySide6.QtWidgets import QInputDialog
            labs = [x for x in SD.labels(M) if x != self.label]
            to, ok = QInputDialog.getItem(self, "Move to another section", "Section:", labs, 0, False)
            if not ok:
                return False
        self._changed("move to")
        ok = SD.move_to_section(M, iid, to, frm=self.label)
        M.pending = True
        self._after(iid, f"Moved to {to}." if ok else "It could not be moved there.")
        return ok

    def toggle_ref(self, iid):
        M = self.M()
        self._changed("reference only")
        on = SD.set_refonly(M, iid, not SD.refonly(M, iid))
        self._after(iid, "Prints its reference only." if on else "Prints its words again.")
        return on

    def show_source(self, iid):
        host = self.pg.host
        if not host.go("assign"):
            return False
        try:
            ap = host.assign_page
            it = ap.R.item(iid)
            if it and it.get("file") and ap.file != it["file"]:
                ap.files.setCurrentText(it["file"])
            ap.select(iid)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return True
