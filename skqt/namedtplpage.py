"""Templates (4.43.0; ST39 to ST44 of 2026-11-15): the gallery of the templates you name. One card each: its name,
whether it is made, what it is made of, and whether its file holds its picks. New template... opens the builder with
nothing picked; a double-click opens it on that template (skqt/tplbuilder: it picks and never changes a piece). A card
has Export (write the .dotx and check it) and Duplicate; its right-click adds Open in Word, Rename, Archive and Remove.
Archived templates leave the gallery and the lists that offer templates; the Archived view brings one back. An effort
picks a template for each volume in Setup (VolumeTemplatesDialog, below). namedtemplates holds the rules."""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog,
                               QLabel, QMenu, QMessageBox, QScrollArea,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import namedtemplates as NT
import templateproof as TPF
from . import design as D
from .commandbar import CommandBar

TONE = {NT.READY: "ok", NT.REVIEW: "warn", NT.NEW: "muted"}


class TemplateCard(QFrame):
    """One template in the gallery: its name, its state, what it is made of, and whether its file holds its picks."""

    def __init__(self, page, t, rows, state, why, proof):
        super().__init__()
        self.page, self.tid = page, t["id"]
        self.setObjectName("tcard"); self.setFixedWidth(340); self.setCursor(Qt.PointingHandCursor)
        v = QVBoxLayout(self); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(4)
        self.name = QLabel(t["name"]); self.name.setWordWrap(True); self.name.setObjectName("tcardName"); v.addWidget(self.name)
        self.state = QLabel(f"{state}. {why}"); self.state.setWordWrap(True); self.state.setObjectName("tcardState")
        self.state.setProperty("tone", TONE[state]); v.addWidget(self.state)
        self.parts = []
        for r in rows:
            lb = D.label(f"{r['name']}: {r['from'].split(': ', 1)[-1] if ': ' in r['from'] else r['from']}", "muted")
            lb.setWordWrap(True); v.addWidget(lb); self.parts.append(lb)
        self.proof = D.label(TPF.words(proof), None); self.proof.setWordWrap(True); self.proof.setObjectName("tcardProof")
        self.proof.setProperty("tone", "warn" if any(x["state"] == TPF.BAD for x in proof) else "ok")
        self.proof.setVisible(bool(proof)); v.addWidget(self.proof)
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)
        h = QHBoxLayout(); h.setSpacing(D.SPACE["s"])
        self.b_export = D.button("Export", None, lambda: page.make(self.tid), "Write this template's .dotx and check it against its picks")
        self.b_dup = D.button("Duplicate", None, lambda: page.duplicate(self.tid), "Another template with the same picks")
        h.addWidget(self.b_export); h.addWidget(self.b_dup); h.addStretch(1); v.addLayout(h)
        if t.get("archived"):
            self.b_export.setEnabled(False)
            self.setToolTip("Archived. Right-click to restore it.")
        else:
            self.setToolTip("Double-click to open it in the builder")

    def paint(self, selected):
        t = D.tokens()
        self.setStyleSheet(f"QFrame#tcard{{background:{t['surface']};border:{2 if selected else 1}px solid {t['accent'] if selected else t['border']};"
                           f"border-radius:{D.RADIUS['card'] + 2}px;}} QFrame#tcard QLabel{{background:transparent;}} "
                           f"QLabel#tcardName{{font-size:{D.TYPE['body'] + 2}pt;font-weight:700;}} "
                           f"QLabel#tcardState[tone=\"ok\"],QLabel#tcardProof[tone=\"ok\"]{{color:{t['ok']};}} "
                           f"QLabel#tcardState[tone=\"warn\"],QLabel#tcardProof[tone=\"warn\"]{{color:{t['warn']};}} "
                           f"QLabel#tcardState[tone=\"muted\"]{{color:{t['muted']};}}")

    def mousePressEvent(self, e):
        self.page.select(self.tid)
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, _e):
        self.page.open_builder(self.tid)

    def contextMenuEvent(self, e):
        self.page.select(self.tid)
        self.page.row_menu().exec(e.globalPos())


class NamedTemplatesPage(QWidget):
    """Templates (4.43.0): the gallery. One card for each template; New template... and a double-click open the builder."""
    COLUMNS = 3

    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows, self.cards, self.archived, self._cur = [], {}, False, None
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar(self)
        self.b_arch = self.bar.add("Archived", lambda: self.show_archived(not self.archived), "The archived templates: right-click one to restore it")
        self.b_arch.setCheckable(True)
        self.b_new = self.bar.primary("New template...", lambda: self.new(), "Pick what goes into a new template")
        self.bar.more("Page layouts and numbering...", lambda: self.layouts())    # 4.42.0: the named ones a template picks
        self.bar.more("Open the folder", lambda: self.open_folder())
        v.addWidget(self.bar)
        self.sum = D.label("", "muted"); v.addWidget(self.sum)
        self.area = QScrollArea(); self.area.setWidgetResizable(True); self.area.setFrameShape(QFrame.NoFrame)
        self.inner = QWidget(); self.grid = QGridLayout(self.inner); self.grid.setSpacing(D.SPACE["m"])
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft); self.area.setWidget(self.inner)
        v.addWidget(self.area, 1)
        self.empty = D.EmptyState("No templates yet", "A template is a name and a pick: a page setup, numbering, style sets, Quick Parts "
                                  "and the pages a document starts with. Build it once; an effort then picks it for a volume in Setup.",
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
        import templatelib as TL
        import templateparts as TP
        cfg = self.host.config_dir
        keep = self._cur
        every = NT.every(cfg)
        n_arch = sum(1 for t in every if t.get("archived"))
        if self.archived and not n_arch:
            self.archived = False
        self.rows = [t for t in every if bool(t.get("archived")) == self.archived]
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w is not None:
                w.setParent(None); w.deleteLater()
        self.cards = {}
        lib = TL.Library(cfg)
        n = {s: 0 for s in (NT.READY, NT.REVIEW, NT.NEW)}
        for i, t in enumerate(self.rows):
            st, why = NT.state(cfg, t, lib=lib)
            n[st] += 1
            c = TemplateCard(self, t, TP.rows(cfg, t, lib), st, why, TPF.check(cfg, t, lib=lib) if st != NT.NEW else [])
            self.grid.addWidget(c, i // self.COLUMNS, i % self.COLUMNS); self.cards[t["id"]] = c
        self.area.setVisible(bool(self.rows)); self.empty.setVisible(not self.rows and not self.archived)
        self.b_arch.setText(f"Archived ({n_arch})"); self.b_arch.setChecked(self.archived); self.b_arch.setVisible(n_arch > 0)
        self.sum.setText(("The archived templates. Right-click one to restore it." if self.archived else
                          f"{len(self.rows)} template(s): {n[NT.READY]} ready, {n[NT.REVIEW]} need review, {n[NT.NEW]} not made yet. "
                          "Double-click one to see or change what goes in. An effort picks one for each volume in Setup > More > "
                          "Templates for the volumes...") if self.rows else "")
        self._cur = keep if keep in self.cards else (self.rows[0]["id"] if self.rows else None)
        self.sync()

    def sync(self):
        for tid, c in self.cards.items():
            c.paint(tid == self._cur)

    def current(self):
        return self._cur

    def select(self, tid):
        if tid not in self.cards:
            return False
        self._cur = tid
        self.sync()
        return True

    def show_archived(self, on):
        self.archived = bool(on)
        self._cur = None
        self.fill()
        return self.archived

    # ------------------------------------------------------------ what you do
    def new(self, modal=True):
        """New template...: the builder, with nothing picked yet. The template exists once it is saved there."""
        from .tplbuilder import builder
        return builder(self, None, modal)

    def open_builder(self, tid=None, modal=True):
        tid = tid or self.current()
        if tid is None or NT.get(self.host.config_dir, tid) is None:
            return None
        from .tplbuilder import builder
        return builder(self, tid, modal)

    def duplicate(self, tid=None):
        t = NT.duplicate(self.host.config_dir, tid or self.current() or "")
        if t is None:
            return None
        diag.activity("named_template_duplicated")
        self.host.status(f"{t['name']} is added with the same picks. Double-click it to change them.")
        self.fill(); self.select(t["id"])
        return t

    def archive(self, tid=None, on=True, ask=True):
        tid = tid or self.current()
        t = NT.get(self.host.config_dir, tid) if tid else None
        if t is None:
            return False
        if on and ask and QMessageBox.question(self, "Archive the template", f"Archive {t['name']}? It leaves the gallery and the "
                                               "lists that offer templates. Nothing is removed, an effort that picked it keeps its "
                                               "copy, and the Archived view brings it back.") != QMessageBox.Yes:
            return False
        NT.archive(self.host.config_dir, tid, on)
        diag.activity("named_template_archived")
        self.host.status(f"{t['name']} is archived." if on else f"{t['name']} is back in the gallery.")
        self.fill()
        return True

    def _allowed(self):
        import roleaccess as RA
        if RA.preview_on(self.host.config_dir, "template"):
            return True
        self.host.status("Making templates is a Preview tool: turn it on in Settings > Preview tools.")
        return False

    def make(self, tid=None, word=None):
        """Export: writes the template's .dotx and checks the file against the picks. Returns the job, or None."""
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
        self.fill(); self.select(tid)
        self.host.status(f"Exported {os.path.basename(job.copy)}. " + TPF.words(TPF.check(self.host.config_dir, NT.get(self.host.config_dir, tid))))
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

    def layouts(self, modal=True, kind=None):
        from . import pagelayoutsview as PLV
        return PLV.layouts(self, modal, kind)

    def row_menu(self, pos=None, run=True):
        tid = self.current()
        if tid is None:
            return None
        t = NT.get(self.host.config_dir, tid)
        m = QMenu(self)
        if t.get("archived"):
            m.addAction("Restore", lambda: self.archive(tid, on=False))
            m.addSeparator()
            m.addAction("Remove", lambda: self.remove(tid))
            return m
        m.addAction("Open in the builder", lambda: self.open_builder(tid))
        m.addAction("Export", lambda: self.make(tid))
        a = m.addAction("Open in Word", lambda: self.open(tid)); a.setEnabled(os.path.isfile(((t or {}).get("made") or {}).get("path") or ""))
        m.addSeparator()
        m.addAction("Duplicate", lambda: self.duplicate(tid))
        m.addAction("Rename...", lambda: self.rename(tid))
        m.addAction("Archive...", lambda: self.archive(tid))
        m.addAction("Remove", lambda: self.remove(tid))
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
        from . import efforttplview as ETV                       # 4.41.0: the effort type's templates, offered
        self.warn = D.label("", None); self.warn.setObjectName("layoutWarn"); self.warn.setWordWrap(True)
        self.warn.setStyleSheet(f"QLabel#layoutWarn{{color:{D.tokens()['warn']}}}"); v.addWidget(self.warn)
        self.b_type = D.button("Use the effort type's templates", None, lambda: ETV.use_type(self), "Picks the effort type's template for each volume that has none")
        v.addWidget(self.b_type)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept); v.addWidget(bb)
        self.boxes = {}
        self._combo = QComboBox
        self.fill()

    def fill(self):
        import templatesetup as TS
        cfg, ws, M = self.host.config_dir, self.host.ws, self.page._M()
        made = [t for t in NT.every(cfg) if NT.state(cfg, t)[0] != NT.NEW and (not t.get('archived') or t['id'] in {(x or {}).get('id') for x in NT.picks(ws).values()})]
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
        from . import efforttplview as ETV
        said, n = ETV.offer_words(self.host, vols)
        self.note.setText(self.note.text() + said)
        self.b_type.setVisible(n > 0)
        import pagelayouts as PGL                                # 4.42.0: one answer per volume
        self.differs, lines = {}, []
        for vol in vols:
            t = NT.get(cfg, (got.get(vol) or {}).get("id") or "")
            what = PGL.disagree(cfg, ws, vol, t) if t else []
            if what:
                self.differs[vol] = what
                lines.append(PGL.disagree_words(vol, t["name"], what))
        self.warn.setText("\n".join(lines))
        self.warn.setVisible(bool(self.differs))

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
