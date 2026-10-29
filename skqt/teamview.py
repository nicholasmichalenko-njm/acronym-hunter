"""Team defaults in Qt (2.89.0): Settings > Team defaults. Make a team pack (tick what it carries and what the team
locks), install one (a preview of what changes, then Install), undo the last install, and the team's topics and
sensitivity markings. The rules are teampack's. Rules only (No AI); nothing leaves the PC."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QVBoxLayout)
import diag
import teampack as TP
from . import design as D


class MakeDialog(QDialog):
    def __init__(self, parent, config_dir):
        super().__init__(parent)
        self.setWindowTitle("Make a team pack")
        self.setMinimumWidth(620)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Tick what the pack carries. A locked part replaces each PC's own and stays as the team set it until "
                            "the pack is undone; everything else only adds what a PC does not have.", "muted"))
        f = QFormLayout(); v.addLayout(f)
        self.name = QLineEdit("Team defaults"); f.addRow("Pack name", self.name)
        self.notes = QPlainTextEdit(); self.notes.setMaximumHeight(70); self.notes.setPlaceholderText("What changed in this version")
        f.addRow("Notes", self.notes)
        g = QGridLayout(); v.addLayout(g)
        g.addWidget(D.label("<b>Carry</b>", None), 0, 0); g.addWidget(D.label("<b>On this PC</b>", None), 0, 1)
        g.addWidget(D.label("<b>Lock</b>", None), 0, 2)
        have = TP.available(config_dir)
        self.carry, self.lock = {}, {}
        for i, p in enumerate(TP.PARTS, start=1):
            cb = QCheckBox(TP.PART_NAMES[p]); cb.setChecked(p in have); cb.setEnabled(p in have)
            self.carry[p] = cb; g.addWidget(cb, i, 0)
            g.addWidget(D.label(have.get(p, "nothing yet"), "muted"), i, 1)
            if p in TP.LOCKABLE:
                lk = QCheckBox(); lk.setEnabled(p in have); lk.setToolTip("Each PC takes the team's and cannot change it")
                self.lock[p] = lk; g.addWidget(lk, i, 2, Qt.AlignCenter)
        v.addWidget(D.label("The pack holds names. Keep it on the approved SharePoint folder; never on GitHub.", "warn"))
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        parts = [p for p, cb in self.carry.items() if cb.isChecked()]
        return {"parts": parts, "lock": [p for p, cb in self.lock.items() if cb.isChecked() and p in parts],
                "name": self.name.text(), "notes": self.notes.toPlainText()}


class InstallDialog(QDialog):
    def __init__(self, parent, info, said):
        super().__init__(parent)
        self.setWindowTitle("Install the team pack")
        self.setMinimumWidth(600)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"<b>{info.get('name')}</b>  version {info.get('version')}, made by {info.get('created_by')} on "
                            f"{info.get('created')}", None))
        if info.get("notes"):
            v.addWidget(D.label(info["notes"], "muted"))
        for part, text in said:
            row = QHBoxLayout(); v.addLayout(row)
            row.addWidget(D.Pill("Locked" if part in info["locks"] else "Adds", "warn" if part in info["locks"] else "ok"))
            row.addWidget(D.label(f"<b>{TP.PART_NAMES[part]}</b>: {text}", None), 1)
        v.addWidget(D.label("Settings > Team defaults > Undo puts back everything this changes.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        bb.addButton("Install", QDialogButtonBox.AcceptRole)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)


class ListDialog(QDialog):
    def __init__(self, parent, title, say, items):
        super().__init__(parent)
        self.setWindowTitle(title); self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.addWidget(D.label(say, "muted"))
        self.box = QPlainTextEdit("\n".join(items)); v.addWidget(self.box)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        return [x for x in self.box.toPlainText().splitlines() if x.strip()]


class TeamCard(D.Card):
    def __init__(self, host):
        self.make_btn = D.button("Make a team pack...", None, lambda: self.make())
        self.inst_btn = D.button("Install a team pack...", "primary", lambda: self.install())
        self.undo_btn = D.button("Undo", "ghost", lambda: self.undo(), "Put back everything the last team pack changed")
        super().__init__("Team defaults", "One file sets up every PC the same way: the author list, matrix design, banned words, "
                         "default gate goals, company logos, Effort Home layouts by role, sensitivity markings and team topics.",
                         actions=[self.make_btn, self.inst_btn, self.undo_btn])
        self.host = host
        self.state = self.add(D.label("", None))
        row = QHBoxLayout(); self.body.addLayout(row)
        self.topics_btn = D.button("Team topics...", None, lambda: self.edit_topics(), "Offered as one-click tags when context is taken")
        self.marks_btn = D.button("Sensitivity markings...", None, lambda: self.edit_markings(), "Offered in Effort Home > Edit details")
        row.addWidget(self.topics_btn); row.addWidget(self.marks_btn); row.addStretch(1)
        self.refresh()

    @property
    def cfg(self):
        return self.host.config_dir

    def refresh(self):
        i = TP.installed(self.cfg)
        lk = TP.locks(self.cfg)
        if i:
            self.state.setText(f"Installed: <b>{i.get('name')}</b> version {i.get('version')} (from {i.get('created_by')}), on "
                               f"{i.get('installed')}." + (f" Locked by the team: {', '.join(TP.PART_NAMES[p] for p in lk)}." if lk else ""))
        else:
            self.state.setText("No team pack installed on this PC.")
        self.undo_btn.setVisible(TP.can_undo(self.cfg))
        self.marks_btn.setEnabled("markings" not in lk)
        self.marks_btn.setToolTip("The team pack set the markings" if "markings" in lk else "Offered in Effort Home > Edit details")

    def make(self, path=None, answer=None):
        if answer is None:
            dlg = MakeDialog(self, self.cfg)
            if dlg.exec() != QDialog.Accepted:
                return None
            answer = dlg.values()
        if not answer["parts"]:
            self.host.status("Tick at least one part for the pack.")
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save the team pack", f"{answer['name'] or 'Team defaults'}{TP.EXT}",
                                                  f"Team pack (*{TP.EXT})")
        if not path:
            return None
        info = TP.make(self.cfg, path, answer["parts"], answer["lock"], answer["name"], answer["notes"])
        diag.activity("qt_team_pack_made", n=len(info["parts"]))
        self.host.toast("Team pack saved. Put it on the approved SharePoint folder for the team.")
        return info

    def install(self, path=None, confirm=None):
        """confirm (tests): True installs without the preview, False only looks."""
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Install a team pack", "", f"Team pack (*{TP.EXT})")
        if not path:
            return None
        try:
            info, data = TP.read(path)
        except Exception as e:
            diag.swallowed()
            self.host.status(f"That is not a sound team pack: {e}." if isinstance(e, ValueError) else "That file could not be read as a team pack.")
            return None
        said = TP.preview(self.cfg, info, data)
        self.last_preview = said
        if confirm is None:
            if InstallDialog(self, info, said).exec() != QDialog.Accepted:
                return said
        elif not confirm:
            return said
        TP.install(self.cfg, info, data)
        diag.activity("qt_team_pack_installed", n=len(info["parts"]))
        self.after()
        self.host.toast(f"Team pack installed: {info.get('name')}")
        return said

    def undo(self):
        if not TP.undo(self.cfg):
            return False
        diag.activity("qt_team_pack_undone")
        self.after()
        self.host.toast("Team pack undone")
        return True

    def after(self):
        h = self.host
        try:
            h.authors = h._load_authors(self.cfg)
            h.authors_changed()
        except Exception:
            diag.swallowed()
        for f in (lambda: h.rail_brand.refresh(), lambda: h.settings_page.branding_card.refresh(),
                  lambda: h.home_page.apply_layout(), lambda: h.settings_page.authors.fill()):
            try:
                f()
            except Exception:
                diag.swallowed()
        self.refresh()

    def edit_topics(self, answer=None):
        if answer is None:
            dlg = ListDialog(self, "Team topics", "One topic per line. They are offered as one-click tags when context is taken "
                             "from a library document, and a team pack carries them.", TP.topics(self.cfg))
            if dlg.exec() != QDialog.Accepted:
                return None
            answer = dlg.values()
        return TP.save_topics(self.cfg, answer)

    def edit_markings(self, answer=None):
        if TP.locked(self.cfg, "markings"):
            return None
        if answer is None:
            dlg = ListDialog(self, "Sensitivity markings", "One marking per line, as the team writes it (CUI//SP-PROPIN, Proprietary). "
                             "A marking that starts with CUI shows in the CUI color.", TP.markings(self.cfg))
            if dlg.exec() != QDialog.Accepted:
                return None
            answer = dlg.values()
        return TP.save_markings(self.cfg, answer)
