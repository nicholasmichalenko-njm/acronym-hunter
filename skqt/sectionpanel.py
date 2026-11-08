"""The section panel (3.83.0, claude/stationkeeper-redesign-decisions-2026-11-08.md): the one panel Review and Setup show
for the selected section, in this order.

    Management guidance                  saved as it is typed; the line under it says when
    References and notes for authors     files from the Effort Library, files added, or a note; each one goes into the
                                         setup as a Word comment on the section's heading. Act on the row.
    Notes and context for this section   notes pointed at the section, meeting topics aimed at it, captures placed in
                                         it: Copy into guidance, Send to authors, or Keep as context. Act on the row.
    Notes waiting for a section          quick notes not pointed anywhere yet: Point at this section.

SectionPanel(host, get_M, get_rec) / show_section(label) / flush(). The records are sectionnotes'. Nothing leaves the PC."""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFileDialog, QListWidget, QListWidgetItem, QMenu, QPlainTextEdit, QVBoxLayout, QWidget

import diag
import sectionnotes as SN
from . import design as D

PLACEHOLDER = "Add Management Guidance Text"
SAVE_AFTER_MS = 700
USED_NAME = {"guidance": "copied into the guidance", "authors": "sent to the authors", "context": "kept as context"}


class SectionPanel(QWidget):
    def __init__(self, host, get_M, get_rec, on_saved=None):
        super().__init__()
        self.host, self.get_M, self.get_rec, self.on_saved = host, get_M, get_rec, on_saved
        self.label = None
        self._loading = False
        self._snapped = False
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["s"])
        # ---- management guidance
        v.addWidget(D.label("Management guidance", "label"))
        self.guide = QPlainTextEdit(); self.guide.setPlaceholderText(PLACEHOLDER)
        self.guide.setMinimumHeight(70); self.guide.setMaximumHeight(130)
        self.guide.textChanged.connect(self._typed)
        v.addWidget(self.guide)
        self.saved = D.label("", "muted"); v.addWidget(self.saved)
        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(SAVE_AFTER_MS)
        self.timer.timeout.connect(self.flush)
        # ---- references and notes for authors
        self.refs_head = D.label("References and notes for authors", "label")
        v.addWidget(self.refs_head)
        self.refs = QListWidget(); self.refs.setMaximumHeight(110); self.refs.setWordWrap(True)
        self.refs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.refs.customContextMenuRequested.connect(lambda p: self.ref_menu(self.refs.viewport().mapToGlobal(p)))
        self.refs.itemDoubleClicked.connect(lambda _it: self.ref_menu())
        v.addWidget(self.refs)
        self.b_add = D.button("+ Add a reference", None, None,
                              "A file from the Effort Library, a file of your own, or a note. Each one goes into the setup "
                              "as a Word comment on this section's heading; Strip setup takes them out.")
        m = QMenu(self.b_add)
        m.addAction("From the Effort Library...", lambda: self.add_files(library=True))
        m.addAction("Add files...", lambda: self.add_files(library=False))
        m.addAction("A note for the authors...", lambda: self.add_note())
        self.b_add.setMenu(m)
        v.addWidget(self.b_add, 0, Qt.AlignLeft)
        # ---- notes and context
        self.ctx_head = D.label("Notes and context for this section", "label"); v.addWidget(self.ctx_head)
        self.ctx = QListWidget(); self.ctx.setMaximumHeight(150); self.ctx.setWordWrap(True)
        self.ctx.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ctx.customContextMenuRequested.connect(lambda p: self.ctx_menu(self.ctx.viewport().mapToGlobal(p)))
        self.ctx.itemDoubleClicked.connect(lambda _it: self.ctx_menu())
        v.addWidget(self.ctx)
        self.ctx_empty = D.label("Nothing yet. A note pointed at this section, a meeting topic aimed at it, or a capture "
                                 "placed in it shows here.", "muted")
        v.addWidget(self.ctx_empty)
        # ---- the tray
        self.tray_head = D.label("", "label"); v.addWidget(self.tray_head)
        self.tray = QListWidget(); self.tray.setMaximumHeight(90); self.tray.setWordWrap(True)
        self.tray.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tray.customContextMenuRequested.connect(lambda p: self.tray_menu(self.tray.viewport().mapToGlobal(p)))
        self.tray.itemDoubleClicked.connect(lambda it: self.point_here(it.data(Qt.UserRole)))
        v.addWidget(self.tray)

    # ------------------------------------------------------------ the section
    def show_section(self, label):
        """Fill the panel for a section (None: empty). Typing in progress for the same section is kept."""
        if label != self.label:
            self.flush()
        same = label == self.label
        self.label = label
        M = self.get_M()
        self._loading = True
        try:
            want = SN.guidance(M, label) if (M is not None and label) else ""
            if not (same and self.guide.hasFocus()) and self.guide.toPlainText() != want:
                self.guide.setPlainText(want)
            self.guide.setEnabled(bool(label) and M is not None)
        finally:
            self._loading = False
        if not same:
            self.saved.setText("Saved as you type." if label else "")
            self._snapped = False
        self.fill()

    def fill(self):
        M, rec, label = self.get_M(), self._rec(), self.label
        self.refs.clear()
        for r in (SN.refs(M, label) if (M is not None and label) else []):
            it = QListWidgetItem(SN.describe(r)); it.setData(Qt.UserRole, r["id"])
            it.setToolTip(SN.ORIGIN_NAME.get(r.get("origin"), "") + (f"\n{r['path']}" if r.get("path") else ""))
            self.refs.addItem(it)
        self.refs.setVisible(self.refs.count() > 0)
        self.b_add.setEnabled(bool(label) and M is not None)
        ctx = SN.context(rec, label) if (rec is not None and label) else []
        self.ctx.clear()
        for c in ctx:
            tag = SN.KIND_NAME.get(c["kind"], "") + (f" · {c['source']}" if c["source"] else "")
            used = USED_NAME.get(c["used"], "")
            it = QListWidgetItem(f"{tag}{'  (' + used + ')' if used else ''}\n{c['text']}")
            it.setData(Qt.UserRole, c["key"])
            if c["used"]:
                it.setForeground(QColor(D.tokens().get("muted", "#777777")))
            self.ctx.addItem(it)
        self.ctx_head.setText("Notes and context for this section" + (f" ({len(ctx)})" if ctx else ""))
        self.ctx.setVisible(bool(ctx))
        self.ctx_empty.setVisible(not ctx and bool(label))
        tray = SN.unassigned(rec) if rec is not None else []
        self.tray.clear()
        for n in tray:
            it = QListWidgetItem(n["text"]); it.setData(Qt.UserRole, n["id"])
            it.setToolTip("Double-click to point it at this section")
            self.tray.addItem(it)
        self.tray_head.setText(f"Notes waiting for a section ({len(tray)})")
        self.tray_head.setVisible(bool(tray) and bool(label))
        self.tray.setVisible(bool(tray) and bool(label))

    def _rec(self):
        try:
            return self.get_rec()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return None

    def _changed(self):
        try:
            self.host.changed()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        if self.on_saved:
            self.on_saved(self.label)

    def _snap(self):
        try:
            self.host.review.snap()
        except Exception:  # noqa: BLE001
            diag.swallowed()

    def hideEvent(self, e):                       # leaving the page saves what is typed
        if self.timer.isActive():
            self.flush()
        super().hideEvent(e)

    # ------------------------------------------------------------ guidance, saved as typed
    def _typed(self):
        if self._loading or not self.label:
            return
        if not self._snapped:                    # one undo step for each run of typing
            self._snap(); self._snapped = True
        self.saved.setText("Saving...")
        self.timer.start()

    def flush(self):
        """Save what is typed now (the timer, leaving the section, or the page)."""
        self.timer.stop()
        M = self.get_M()
        if M is None or not self.label:
            return False
        if SN.set_guidance(M, self.label, self.guide.toPlainText()):
            diag.activity("section_guidance_saved", n=1)
            self._changed()
        self.saved.setText("Saved.")
        self._snapped = False
        return True

    # ------------------------------------------------------------ references
    def start_folder(self, library):
        import effortlib as EL
        path = getattr(self.host, "effort_path", "") or ""
        try:
            return (EL.root(path) if library else "") or os.path.dirname(path)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return ""

    def pick_files(self, library):
        got, _f = QFileDialog.getOpenFileNames(self, "Files for the authors" if not library else "From the Effort Library",
                                               self.start_folder(library))
        return got

    def add_files(self, library=False, files=None):
        M = self.get_M()
        if M is None or not self.label:
            return 0
        files = files if files is not None else self.pick_files(library)
        if not files:
            return 0
        self._snap()
        n = sum(1 for f in files if SN.add_ref(M, self.label, path=f, origin="library" if library else "file"))
        self._changed(); self.fill()
        return n

    def ask(self, title, text="", label=""):
        from .symbols import ask_text
        return ask_text(self, title, label or title, text)

    def add_note(self, text=None):
        M = self.get_M()
        if M is None or not self.label:
            return None
        if text is None:
            text, ok = self.ask("A note for the authors", "", "What the authors should know (it becomes a Word comment):")
            if not ok:
                return None
        self._snap()
        rid = SN.add_ref(M, self.label, note=text, origin="note")
        if rid:
            self._changed(); self.fill()
        return rid

    def ref_menu(self, at=None, run=True):
        it = self.refs.currentItem()
        if it is None:
            return None
        rid = it.data(Qt.UserRole)
        r = next((x for x in SN.refs(self.get_M(), self.label) if x["id"] == rid), None)
        if r is None:
            return None
        m = QMenu(self)
        if r.get("path"):
            m.addAction("Where to look...", lambda: self.edit_ref(rid, "where"))
        m.addAction("Edit the note...", lambda: self.edit_ref(rid, "note"))
        m.addSeparator()
        m.addAction("Take it out", lambda: self.remove_ref(rid))
        if run:
            m.exec(at or self.refs.viewport().mapToGlobal(self.refs.visualItemRect(it).bottomLeft()))
        return m

    def edit_ref(self, rid, field, text=None):
        M = self.get_M()
        r = next((x for x in SN.refs(M, self.label) if x["id"] == rid), None)
        if r is None:
            return False
        if text is None:
            text, ok = self.ask("Where to look" if field == "where" else "The note",
                                r.get(field, ""), "Pages, a section or a figure to look at:" if field == "where" else "The note:")
            if not ok:
                return False
        self._snap()
        if SN.update_ref(M, self.label, rid, **{field: text}):
            self._changed(); self.fill()
            return True
        return False

    def remove_ref(self, rid):
        self._snap()
        if SN.remove_ref(self.get_M(), self.label, rid):
            self._changed(); self.fill()
            return True
        return False

    # ------------------------------------------------------------ notes and context
    def ctx_menu(self, at=None, run=True):
        it = self.ctx.currentItem()
        if it is None:
            return None
        key = it.data(Qt.UserRole)
        m = QMenu(self)
        m.addAction("Copy into guidance", lambda: self.use(key, "guidance"))
        m.addAction("Send to authors", lambda: self.use(key, "authors"))
        m.addAction("Keep as context", lambda: self.use(key, "context"))
        if run:
            m.exec(at or self.ctx.viewport().mapToGlobal(self.ctx.visualItemRect(it).bottomLeft()))
        return m

    def use(self, key, how):
        M, rec = self.get_M(), self._rec()
        if M is None or rec is None or not self.label:
            return False
        if how == "guidance":
            self.flush(); self._snap()
            new = SN.copy_into_guidance(M, rec, self.label, key)
            if new is None:
                return False
            self._loading = True
            self.guide.setPlainText(new)
            self._loading = False
            self.saved.setText("Saved.")
            self._changed()
        elif how == "authors":
            self._snap()
            if not SN.send_to_authors(M, rec, self.label, key):
                return False
            self._changed()
        else:
            SN.mark_used(rec, key, "context")
        self.fill()
        return True

    # ------------------------------------------------------------ the tray
    def tray_menu(self, at=None, run=True):
        it = self.tray.currentItem()
        if it is None:
            return None
        nid = it.data(Qt.UserRole)
        m = QMenu(self)
        m.addAction(f"Point at {self.label}", lambda: self.point_here(nid))
        if run:
            m.exec(at or self.tray.viewport().mapToGlobal(self.tray.visualItemRect(it).bottomLeft()))
        return m

    def point_here(self, nid):
        rec = self._rec()
        if rec is None or not self.label:
            return False
        if SN.point_at(rec, nid, self.label):
            self.fill()
            return True
        return False
