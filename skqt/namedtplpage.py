"""Templates > Template (4.28.2; answer 23): the templates you name. One row each: its name, what goes in, whether it is
made. New template... names one; What goes in... picks its style sets, Quick Part set and starting pages (the same
picker Make templates uses); Make it writes the .dotx. A row's right-click holds Open in Word, Rename and Remove. An
effort picks one for each volume in Setup. namedtemplates holds the rules; nothing leaves the PC."""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QHeaderView, QInputDialog, QMenu, QMessageBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import namedtemplates as NT
from . import design as D
from .commandbar import CommandBar

TONE = {NT.READY: "ok", NT.REVIEW: "warn", NT.NEW: "muted"}
COLS = ["Template", "What goes in", "State", "Why"]


class GoesInDialog(QDialog):
    """What goes in one template: the picker, saved as you pick."""

    def __init__(self, page, tid):
        super().__init__(page)
        self.host, self.page, self.tid = page.host, page, tid
        t = NT.get(self.host.config_dir, tid)
        self.setWindowTitle(f"What goes in: {t['name']}")
        self.resize(760, 640)
        v = QVBoxLayout(self)
        from .setspick import WhatGoesIn
        self.std = NT.std_of(self.host.config_dir, t)
        self.goes_in = WhatGoesIn(self); v.addWidget(self.goes_in, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept); v.addWidget(bb)
        self.goes_in.show_std(self.std, True)

    def recipe_changed(self):
        import templatesets as TS
        NT.set_recipe(self.host.config_dir, self.tid, TS.recipe(self.std))
        self.page.fill()


class NamedTemplatesPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows = []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar(self)
        self.b_goes = self.bar.add("What goes in...", lambda: self.goes_in(), "The selected template's style sets, Quick Part set and starting pages")
        self.b_make = self.bar.add("Make it", lambda: self.make(), "Write the selected template's .dotx")
        self.b_new = self.bar.primary("New template...", lambda: self.new(), "A template with a name of its own")
        self.bar.more("Open the folder", lambda: self.open_folder())
        v.addWidget(self.bar)
        self.sum = D.label("", "muted"); v.addWidget(self.sum)
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels(COLS)
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t.setWordWrap(True)
        self.t.setColumnWidth(0, 260); self.t.setColumnWidth(2, 120); self.t.setColumnWidth(3, 300)
        self.t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.t.doubleClicked.connect(lambda _i: self.goes_in())
        self.t.setContextMenuPolicy(Qt.CustomContextMenu); self.t.customContextMenuRequested.connect(self.row_menu)
        self.t.itemSelectionChanged.connect(self.sync)
        v.addWidget(self.t, 1)
        self.empty = D.EmptyState("No templates yet", "A template is a name and a pick: which style sets, which Quick Parts and which "
                                  "pages a document starts with. Make it once; an effort then picks it for a volume in Setup.",
                                  "New template...", lambda: self.new())
        v.addWidget(self.empty)

    def folder(self):
        import app_gui
        import prodcopy as PCY
        return os.path.join(PCY.output_folder(app_gui.load_settings() or {}, app_gui.DATA_DIR), "Templates")

    # ------------------------------------------------------------ filling
    def refresh(self):
        self.fill()

    def fill(self):
        cfg = self.host.config_dir
        keep = self.current()
        self.rows = NT.every(cfg)
        self.t.setRowCount(0)
        n = {s: 0 for s in (NT.READY, NT.REVIEW, NT.NEW)}
        for t in self.rows:
            st, why = NT.state(cfg, t)
            n[st] += 1
            r = self.t.rowCount(); self.t.insertRow(r)
            for c, text in enumerate((t["name"], NT.words(cfg, t), st, why)):
                it = QTableWidgetItem(text); it.setData(Qt.UserRole, t["id"])
                if c == 2:
                    it.setForeground(D.color(TONE[st]))
                self.t.setItem(r, c, it)
        self.t.resizeRowsToContents()
        self.t.setVisible(bool(self.rows)); self.empty.setVisible(not self.rows)
        self.sum.setText(f"{len(self.rows)} template(s): {n[NT.READY]} ready, {n[NT.REVIEW]} need review, {n[NT.NEW]} not made yet. "
                         "An effort picks one for each volume in Setup > More > Templates for the volumes..." if self.rows else "")
        if keep:
            self.select(keep)
        elif self.rows:
            self.t.selectRow(0)
        self.sync()

    def sync(self):
        on = self.current() is not None
        self.b_goes.setEnabled(on); self.b_make.setEnabled(on)

    def current(self):
        r = self.t.currentRow()
        it = self.t.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it is not None else None

    def select(self, tid):
        for r in range(self.t.rowCount()):
            if self.t.item(r, 0).data(Qt.UserRole) == tid:
                self.t.selectRow(r)
                return True
        return False

    # ------------------------------------------------------------ what you do
    def new(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New template", "Its name (where or how it is used: Page-limited RFP, Volume I):")
            if not ok:
                return None
        t = NT.new(self.host.config_dir, name)
        if t is None:
            self.host.status("A template needs a name that no other template has.")
            return None
        diag.activity("named_template_new")
        self.fill(); self.select(t["id"])
        return t

    def goes_in(self, tid=None, modal=True):
        tid = tid or self.current()
        if tid is None:
            return None
        dlg = GoesInDialog(self, tid)
        self.goes_dialog = dlg
        if modal and not os.environ.get("AH_TEST"):
            dlg.exec()
        return dlg

    def _allowed(self):
        import roleaccess as RA
        if RA.preview_on(self.host.config_dir, "template"):
            return True
        self.host.status("Making templates is a Preview tool: turn it on in Settings > Preview tools.")
        return False

    def make(self, tid=None, word=None):
        tid = tid or self.current()
        if tid is None or not self._allowed():
            return None
        if word is None and sys.platform.startswith("win"):
            import prodword
            word = prodword.update_fields
        try:
            job = NT.make(self.host.config_dir, self.folder(), tid, word=word)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"The template was not made ({type(e).__name__}).")
            return None
        diag.activity("named_template_made")
        self.host.status(f"Made {os.path.basename(job.copy)}")
        self.fill(); self.select(tid)
        return job

    def rename(self, tid=None, name=None):
        tid = tid or self.current()
        t = NT.get(self.host.config_dir, tid) if tid else None
        if t is None:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename the template", "New name:", text=t["name"])
            if not ok:
                return False
        ok = NT.rename(self.host.config_dir, tid, name)
        if not ok:
            self.host.status("Another template has that name.")
        self.fill()
        return ok

    def remove(self, tid=None, ask=True):
        tid = tid or self.current()
        t = NT.get(self.host.config_dir, tid) if tid else None
        if t is None:
            return False
        if ask and QMessageBox.question(self, "Remove the template", f"Take {t['name']} off the list? A file already made stays in "
                                        "its folder, and an effort that picked it keeps its copy.") != QMessageBox.Yes:
            return False
        NT.remove(self.host.config_dir, tid)
        diag.activity("named_template_removed")
        self.fill()
        return True

    def open(self, tid=None):
        t = NT.get(self.host.config_dir, tid or self.current() or "")
        p = ((t or {}).get("made") or {}).get("path") or ""
        if p and os.path.isfile(p) and sys.platform.startswith("win"):
            os.startfile(p)                                 # noqa: S606  a template this PC made
        return p

    def open_folder(self):
        f = NT.folder(self.folder())
        os.makedirs(f, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(f)                                 # noqa: S606  the output folder
        return f

    def row_menu(self, pos=None, run=True):
        tid = self.current()
        if tid is None:
            return None
        t = NT.get(self.host.config_dir, tid)
        m = QMenu(self)
        m.addAction("What goes in...", lambda: self.goes_in(tid))
        m.addAction("Make it", lambda: self.make(tid))
        a = m.addAction("Open in Word", lambda: self.open(tid)); a.setEnabled(os.path.isfile(((t or {}).get("made") or {}).get("path") or ""))
        m.addSeparator()
        m.addAction("Rename...", lambda: self.rename(tid))
        m.addAction("Remove", lambda: self.remove(tid))
        if run and pos is not None:
            m.exec(self.t.viewport().mapToGlobal(pos))
        return m


class VolumeTemplatesDialog(QDialog):
    """Setup > More > Templates for the volumes...: each volume of the effort takes a template you named, or the
    effort's own formatting. A pick is kept as that volume's template file."""
    OWN = "The effort's own formatting"

    def __init__(self, page):
        super().__init__(page)
        from PySide6.QtWidgets import QComboBox
        self.page, self.host = page, page.host
        self.setWindowTitle("Templates for the volumes")
        self.resize(640, 420)
        v = QVBoxLayout(self)
        self.note = D.label("", "muted"); v.addWidget(self.note)
        self.t = QTableWidget(0, 2); self.t.setHorizontalHeaderLabels(["Volume", "Template"])
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setColumnWidth(0, 260); self.t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.t.verticalHeader().setDefaultSectionSize(34); self.t.setProperty("sk_rows_fixed", True)
        v.addWidget(self.t, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept); v.addWidget(bb)
        self.boxes = {}
        self._combo = QComboBox
        self.fill()

    def fill(self):
        import templatesetup as TS
        cfg, ws, M = self.host.config_dir, self.host.ws, self.page._M()
        made = [t for t in NT.every(cfg) if NT.state(cfg, t)[0] != NT.NEW]
        got = NT.picks(ws)
        vols = self.page.volume_names()
        self.t.setRowCount(0); self.boxes = {}
        for vol in vols:
            r = self.t.rowCount(); self.t.insertRow(r)
            self.t.setItem(r, 0, QTableWidgetItem(vol))
            cb = self._combo(); cb.addItem(self.OWN, "")
            for t in made:
                cb.addItem(f"{t['name']}  (version {t['made']['version']})", t["id"])
            cur = (got.get(vol) or {}).get("id") or ""
            fv = TS.for_volume(M, vol, self.host.effort_path or "") if M is not None else None
            if not cur and fv:
                cb.addItem(f"A template file: {os.path.basename(fv[0])}", "file")
                cur = "file"
            cb.setCurrentIndex(max(0, cb.findData(cur)))
            cb.activated.connect(lambda _i, v=vol, c=cb: self.pick(v, c.currentData()))
            self.t.setCellWidget(r, 1, cb); self.boxes[vol] = cb
        newer = NT.newer(cfg, ws)
        self.note.setText(("No volumes yet: add the volumes in Setup first." if not vols else
                           "No template is made yet: name one and make it in Templates > Template." if not made else
                           "Pick a template for a volume. The setup is then written on it.")
                          + ("".join(f" {vol}: {nm} has a newer version ({b}); pick it again to take it." for vol, nm, _a, b in newer)))

    def pick(self, volume, tid):
        M = self.page._M()
        if M is None or tid == "file":
            return None
        if not tid:
            NT.unpick(M, self.host.ws, volume)
            got = None
        else:
            got = NT.pick(M, self.host.ws, self.host.config_dir, volume, tid, self.host.effort_path or "")
            if got is None:
                self.host.status("Make that template first (Templates > Template).")
        diag.activity("volume_template_picked", n=int(bool(tid)))
        self.page.changed()
        self.fill()
        return got


def volume_templates(page, modal=True):
    dlg = VolumeTemplatesDialog(page)
    page.volume_templates_dialog = dlg
    if modal and not os.environ.get("AH_TEST"):
        dlg.exec()
    return dlg
