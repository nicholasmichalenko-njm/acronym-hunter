"""Response Setup in Qt (2.61.0): the Word documents your writers start from, one per volume: under each section of
your structure, the RFP text assigned to it (its reference first) and its context. Here: what goes where and in what
order (move a block up or down, take one out of a section), what is not placed yet, and Export. Export changes only
writes just what changed since the last export."""
import datetime, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import compliance as C
import setupdoc as SD
from . import design as D


class SetupPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.p_blocks = D.Pill("0 blocks placed", "accent")
        self.p_unplaced = D.Pill("0 not placed", "ok")
        self.p_noref = D.Pill("0 without a reference", "ok")
        for p in (self.p_blocks, self.p_unplaced, self.p_noref):
            top.addWidget(p)
        top.addStretch(1)
        card = D.Card("What goes where", "Each section of your structure with the RFP text placed under it, in the order "
                                         "the setup document prints it.")
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Section / reference", "RFP text", "Kind"])
        self.tree.setColumnWidth(0, 260); self.tree.setColumnWidth(1, 700); self.tree.setAlternatingRowColors(True)
        self.tree.setWordWrap(True)
        card.add(self.tree)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.button("Up", None, lambda: self.move(-1), "Earlier in its section"))
        row.addWidget(D.button("Down", None, lambda: self.move(1), "Later in its section"))
        row.addWidget(D.button("Take out of this section", "danger", self.remove))
        row.addStretch(1)
        card.body.addLayout(row)
        v.addWidget(card, 1)
        self.unplaced = D.label("", "muted")
        v.addWidget(self.unplaced)
        bar = QHBoxLayout(); bar.setSpacing(D.SPACE["s"]); v.addLayout(bar)
        bar.addStretch(1)
        bar.addWidget(D.button("Export changes only...", None, self.export_changes, "Just what changed since the last export"))
        bar.addWidget(D.button("Export the setup...", None, self.export, "One plain Word document per volume"))
        bar.addWidget(D.button("Make templates and setup...", "primary", lambda: self.make_on_templates(),       # 3.24.0
                               "For each planned volume: its template from Production Standards, and the setup written on it, "
                               "with the RFP's words and your notes in hidden reference styles"))

    def refresh(self):
        R = self.host.review
        self.setEnabled(R is not None and bool(R and R.M.outline))
        self.tree.clear()
        if R is None:
            return
        M = R.M
        P = SD.placed_in(M)
        B = SD.by_id(M)
        inh = SD.inherited_sections(M)
        for o in M.outline:
            lab = C.outline_label(o)
            sec = QTreeWidgetItem([("    " * max(0, o.get("level", 1) - 1)) + lab, "", ""])
            f = sec.font(0); f.setBold(True); sec.setFont(0, f)
            sec.setData(0, Qt.UserRole, ("section", lab, ""))
            self.tree.addTopLevelItem(sec)
            for i in P.get(lab, []):
                it = B.get(i)
                if it is None:
                    continue
                ref = SD.ref_of(M, it, inh)[0] or SD.MISSING
                ch = QTreeWidgetItem([ref, ((it.get("lead") + " ") if it.get("lead") else "") + it.get("text", ""), SD.kind_of(it)])
                ch.setData(0, Qt.UserRole, ("item", lab, i))
                if SD.kind_of(it) == "Context":
                    ch.setForeground(1, D.color("muted"))
                sec.addChild(ch)
        self.tree.expandAll()
        chk = SD.export_check(M)
        self.p_blocks.setText(f"{chk['blocks']} blocks placed")
        self.p_unplaced.setText(f"{len(chk['unplaced'])} not placed"); self.p_unplaced.set_tone("warn" if chk["unplaced"] else "ok")
        self.p_noref.setText(f"{len(chk['no_ref'])} without a reference"); self.p_noref.set_tone("warn" if chk["no_ref"] else "ok")
        self.unplaced.setText(("Not placed (assign them to a section in Review): " + ", ".join(chk["unplaced"][:12])
                               + (" ..." if len(chk["unplaced"]) > 12 else "")) if chk["unplaced"] else "Every requirement and context is placed.")

    def _sel(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def move(self, delta):
        s = self._sel()
        if not s or s[0] != "item":
            return False
        self.host.review.snap()
        SD.move(self.host.review.M, s[2], s[1], delta)
        self.host.changed()
        self.refresh()
        for i in range(self.tree.topLevelItemCount()):
            sec = self.tree.topLevelItem(i)
            for j in range(sec.childCount()):
                if sec.child(j).data(0, Qt.UserRole) == s:
                    self.tree.setCurrentItem(sec.child(j))
        return True

    def remove(self):
        s = self._sel()
        if not s or s[0] != "item":
            return False
        self.host.review.snap()
        SD.unplace(self.host.review.M, s[2], s[1])
        diag.activity("setup_removed", n=1)
        self.host.changed()
        self.host.assign_page.fill_tree()
        self.refresh()
        return True

    def export(self, folder=None):
        R = self.host.review
        if R is None or not R.M.outline:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the setup documents", (self.host.out_path("setup_documents") if self.host.effort_path else "") or os.path.dirname(R.M.path))
            if not folder:
                return None
        try:
            os.makedirs(folder, exist_ok=True)
            import ctxdocs as CX
            import structparts as SP
            paths = SD.export(R.M, folder, context=CX.section_context(self.host.ws.root),
                              part_rules=lambda vol: SP.summaries(self.host.config_dir, self.host.ws, R.M, vol))   # 3.19.0
        except PermissionError:
            self.host.status("A file with that name is open in Word: close it, then export again.")
            return None
        diag.activity("setup_exported", files=len(paths))
        R.M.pending = True
        self.host.changed()
        self.host.toast(f"Setup exported: {len(paths)} document(s). RFP text is purple, direction green.")
        return paths

    def make_on_templates(self, folder=None, opts=None, go=None):
        """3.24.0: Ready to make, the reference styles, then a template per volume and the setup written on each.
        opts and go (tests): the styles to use and whether to make with items still open. Returns the results."""
        import setuptemplate as ST
        import effortrec as RR
        R = self.host.review
        if R is None or not R.M.outline or self.host.ws is None:
            return None
        rec = RR.Record(self.host.ws.root)
        rd = ST.ready(R.M, rec)
        if opts is None or go is None:
            d = MakeDialog(self, rd, ST.options(R.M))
            if d.exec() != d.Accepted:
                return None
            opts = d.values()
            go = True
        if not go and not all(ok for ok, _w, _n in rd):
            return None
        ST.set_options(R.M, opts)
        if folder is None:
            folder = self.host.out_path("setup_documents") if self.host.effort_path else os.path.dirname(R.M.path)
            folder = folder if os.path.isdir(folder) else os.path.dirname(folder)
        info = self.host.efforts.get(self.host.effort_name) or {}
        try:
            import ctxdocs as CX
            word = None
            import prodwordgate as WG
            if WG.available():
                import prodword
                word = prodword.update_fields
            out = ST.make_all(R.M, folder, self.host.config_dir, self.host.ws, self.host.effort_name or "", info,
                              context=CX.section_context(self.host.ws.root), word=word)
        except PermissionError:
            self.host.status("A file with that name is open in Word: close it, then make again.")
            return None
        diag.activity("setup_on_templates", files=len(out))
        R.M.pending = True
        self.host.changed()
        self.host.toast(f"{len(out)} template(s) and setup(s) made in {folder}. Show/Hide shows the RFP's words and your notes.")
        self.last_made = out
        return out

    def export_changes(self, path=None):
        R = self.host.review
        if R is None:
            return None
        ch = SD.changes_since_last(R.M)
        if ch is None:
            self.host.toast("Export the setup once first; changes are counted from that export")
            return None
        if not ch:
            self.host.toast("Nothing changed since the last export")
            return []
        if path is None:
            stem = os.path.splitext(os.path.basename(R.M.path))[0]
            path, _ = QFileDialog.getSaveFileName(self, "Setup changes", self.host.out_path("setup_changes", Matrix=stem) if self.host.effort_path else os.path.join(
                os.path.dirname(R.M.path), f"{stem}_Setup_changes_{datetime.datetime.now():%Y-%m-%d_%H%M}.docx"), "Word (*.docx)")
            if not path:
                return None
        SD.export_changes(R.M, path)
        diag.activity("setup_changes_exported", n=len(ch))
        R.M.pending = True
        self.host.changed()
        self.host.toast(f"{len(ch)} change(s) exported")
        return ch


class MakeDialog(QDialog):
    """3.24.0: Ready to make (what is still open), and the style each kind of reference text takes, hidden or shown."""

    def __init__(self, parent, ready, opts):
        super().__init__(parent)
        import setuptemplate as ST
        self.setWindowTitle("Make templates and setup"); self.setMinimumWidth(680)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Ready to make", "title"))
        for ok, what, n in ready:
            v.addWidget(D.label(("\u2713 " if ok else "\u2022 ") + what + ("" if ok else f" ({n} still open)"), None if ok else "muted"))
        v.addWidget(D.label("Reference text in the setup", "title"))
        v.addWidget(D.label("Each kind goes in its own style. Hidden text shows only with Show/Hide on, so authors see the "
                            "response alone with it off. Type the name of one of your own styles to use it.", "muted"))
        g = QGridLayout(); v.addLayout(g)
        self.rows = {}
        for r, (k, label, _s, _c, _i) in enumerate(ST.KINDS):
            g.addWidget(D.label(label, None), r, 0)
            e = QLineEdit(opts[k]["style"]); g.addWidget(e, r, 1)
            cb = QCheckBox("Hidden"); cb.setChecked(opts[k]["hidden"]); g.addWidget(cb, r, 2)
            self.rows[k] = (e, cb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Make" if all(ok for ok, _w, _n in ready) else "Make anyway")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        return {k: {"style": e.text().strip() or k, "hidden": cb.isChecked()} for k, (e, cb) in self.rows.items()}
