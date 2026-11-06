"""Setup (3.56.0, claude/stationkeeper-setup-decisions-2026-11-04.md): the starting draft each author writes in, made from
a structure, layers and a template, and made again whenever one of them changes. A structure is the least it needs:
headings typed, from a Word outline or from an RFP's headings, before or without a Review. Each section: its lead and
contributors, due date, pages and PM direction, and what it will print. Layers say what fills the sections. Make the setup
writes it on each volume's template (Production > Templates); Plain setup writes it with no template; Changes for authors
writes one Word file per person with what changed in their sections. Rules only (setupmake, setupdoc); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

import diag
import pagebudget as PB
import setupmake as SM
from . import design as D
from .adaptive import FlowLayout


class SetupsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.cur = None
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.p_secs = D.Pill("0 sections", "accent")
        self.p_lead = D.Pill("0 without a lead", "ok")
        self.p_due = D.Pill("0 without a due date", "ok")
        for p in (self.p_secs, self.p_lead, self.p_due):
            top.addWidget(p)
        top.addStretch(1)
        top.addWidget(D.button("Open the Structure Builder", "ghost", lambda: self.host.go("structure"),
                               "Move, number and rename sections, and place requirements in them"))

        # ---- the structure, when there is none yet
        self.start_card = D.Card("Start with a structure", "Type the headings, one per line (numbers first, two spaces "
                                 "deeper per level), or take them from a Word outline or an RFP. No Review needed: read "
                                 "the customer's documents later and the requirements fill the same sections.", key=True)
        self.heads = QPlainTextEdit(); self.heads.setPlaceholderText("1 Technical Approach\n  1.1 Understanding\n2 Management Approach")
        self.heads.setMinimumHeight(110)
        self.start_card.add(self.heads)
        sr = QHBoxLayout(); sr.setSpacing(D.SPACE["s"])
        sr.addWidget(D.button("From an outline workbook...", None, lambda: self.from_outline(),       # 3.71.0
                              "Your outline Excel: sections, requirements, supporting text, guidance and authors, each in its setup style"))
        sr.addWidget(D.button("From a Word outline...", None, lambda: self.from_docx(), "The headings of a Word document"))
        sr.addWidget(D.button("From an RFP's headings...", None, lambda: self.from_rfp(),
                              "The volumes and sections the RFP prescribes, else its numbered headings"))
        sr.addStretch(1)
        sr.addWidget(D.button("Use these headings", "primary", lambda: self.use_headings()))
        self.start_card.body.addLayout(sr)
        v.addWidget(self.start_card)

        # ---- sections and the selected one
        self.main = QWidget(); mh = QHBoxLayout(self.main); mh.setContentsMargins(0, 0, 0, 0); mh.setSpacing(D.SPACE["m"])
        left = D.Card("Sections", "Who writes each one, when it is due and how long it is. A subsection with no lead "
                      "takes its parent's.")
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Section", "Lead", "Due", "Pages"])
        self.tree.setColumnWidth(0, 300); self.tree.setColumnWidth(1, 140); self.tree.setColumnWidth(2, 100)
        self.tree.setAlternatingRowColors(True)
        self.tree.currentItemChanged.connect(lambda cur, _old: self.pick(cur.data(0, Qt.UserRole) if cur else None))
        left.add(self.tree)
        mh.addWidget(left, 3)
        right = D.Card("This section")
        f = QFormLayout(); f.setSpacing(D.SPACE["s"])
        self.f_lead, self.f_with, self.f_due, self.f_pages = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.f_with.setPlaceholderText("Names, with commas")
        self.f_due.setPlaceholderText("2026-11-20, or Pink Team")
        self.f_pages.setPlaceholderText("5, or 2.5")
        self.f_dir = QPlainTextEdit(); self.f_dir.setPlaceholderText("What the proposal manager wants in this section")
        self.f_dir.setMaximumHeight(110)
        for lab, w in (("Lead", self.f_lead), ("Contributors", self.f_with), ("Due", self.f_due), ("Pages", self.f_pages),
                       ("PM direction", self.f_dir)):
            f.addRow(lab, w)
        right.body.addLayout(f)
        rb = QHBoxLayout(); rb.addStretch(1); rb.addWidget(D.button("Save this section", "primary", lambda: self.save_section()))
        right.body.addLayout(rb)
        right.add(D.label("What it prints", "label"))
        self.prev = D.label("", "muted"); self.prev.setTextFormat(Qt.RichText)
        right.add(self.prev)
        mh.addWidget(right, 2)
        v.addWidget(self.main, 1)

        # ---- layers and templates
        lay = D.Card("What fills each section", "Turn a layer off and the next setup leaves it out.")
        lw = QWidget(); fl = FlowLayout(lw, D.SPACE["m"])
        self.layer_boxes = {}
        for key, title, _kinds, _on in SM.LAYERS:
            cb = QCheckBox(title); cb.toggled.connect(lambda on, k=key: self.set_layer(k, on))
            self.layer_boxes[key] = cb; fl.addWidget(cb)
        lay.add(lw)
        self.tmpl = D.label("", "muted"); lay.add(self.tmpl)
        v.addWidget(lay)

        bar = QHBoxLayout(); bar.setSpacing(D.SPACE["s"]); v.addLayout(bar)
        self.note = D.label("", "muted"); bar.addWidget(self.note, 1)
        bar.addWidget(D.button("From an outline workbook...", "ghost", lambda: self.from_outline(),     # 3.71.0
                               "Read your outline Excel again (it replaces what an earlier import of it made)"))
        bar.addWidget(D.button("Setup styles...", None, lambda: self.styles(), "The setup's own styles: name, font, size, color, "
                               "bold, italic, hidden"))
        bar.addWidget(D.button("Strip setup...", "ghost", lambda: self.strip_files(),                 # 3.60.0
                               "Before a volume goes out: a clean copy with the setup's reference text, styles and file "
                               "properties taken out"))
        bar.addWidget(D.button("Changes for authors...", None, lambda: self.packets(),
                               "One Word file per person: what changed in their sections since the last setup"))
        bar.addWidget(D.button("Plain setup...", None, lambda: self.plain(), "One plain Word document per volume, no template"))
        bar.addWidget(D.button("Use a template file...", None, lambda: self.template_file(),          # 3.72.0
                               "Make the setup on a Word template your team already made: you pick what comes in"))
        bar.addWidget(D.button("Make the setup", "primary", lambda: self.make(),
                               "Each volume's template with the setup written on it: the customer's words and your notes in "
                               "hidden reference styles"))

    # ------------------------------------------------------------ state
    def _M(self):
        R = self.host.review
        return R.M if R is not None else None

    # ------------------------------------------------------------ 3.71.0: the outline workbook and the setup styles
    def setup_opts(self):
        import prodrules as PRL
        import setuptemplate as ST
        try:
            std = PRL.for_effort(self.host.config_dir, self.host.ws)
        except Exception:  # noqa: BLE001  no standard yet: the kinds' defaults
            diag.swallowed(); std = None
        return ST.options(self._M(), std)

    def set_setup_opts(self, opts):
        import setuptemplate as ST
        M = self._M()
        if self.host.ws is not None:
            ST.set_options(M, opts, self.host.ws)
        elif M is not None:
            ST.set_options(M, opts)
            M.pending = True

    def styles(self, modal=True):
        from .setupstyles import SetupStyles
        dlg = SetupStyles(self)
        if modal:
            dlg.exec()
        return dlg

    def from_outline(self, path=None, profile=None, accept=None):
        from .outlineimport import import_outline
        return import_outline(self, path, profile, accept)

    def use_outline(self, parsed, file_name):
        """The outline's structure and blocks into the effort (a new compliance matrix when it has none)."""
        import outlinexl as OX
        R = self.host.review
        if R is not None:
            R.snap()
            M = R.M
        else:
            if self.host.ws is None or not self.host.effort_path:
                self.host.status("Pick an effort first, or work in Unfiled.")
                return None
            path = self.host.out_path("compliance_matrix")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            stem, ext = os.path.splitext(path)
            k = 2
            while os.path.exists(path):
                path = f"{stem} ({k}){ext}"; k += 1
            M = SM.start(path, (self.host.effort_name or "Effort"), "")
            self.host.set_matrix(M, new=True)
            M = self.host.review.M
        n = OX.apply(M, parsed, file_name, who=getattr(self.host, "my_name", None) or None)
        M.pending = True
        diag.activity("setup_outline_used", n=n["requirements"])
        self.host.changed()
        try:
            self.host.assign_page.fill_tree()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.refresh()
        self.host.toast(f"From {file_name}: {n['sections']} section(s), {n['requirements']} requirement(s), {n['support'] + n['customer']} "
                        f"supporting and customer block(s), {n['guidance']} guidance note(s)")
        return n

    def refresh(self):
        M = self._M()
        has = M is not None and bool(M.outline)
        self.start_card.setVisible(not has)
        self.main.setEnabled(has)
        for cb in self.layer_boxes.values():
            cb.setEnabled(has)
        keep = self.cur
        self.tree.blockSignals(True); self.tree.clear()
        if not has:
            self.tree.blockSignals(False)
            self.p_secs.setText("0 sections"); self.note.setText("Start with a structure.")
            self.prev.setText(""); self.tmpl.setText("")
            return
        sel = None
        for lab, lv in SM.sections(M):
            lead = SM.people(M, lab)[0]
            pg = PB.pages(M, lab)
            it = QTreeWidgetItem([("    " * max(0, lv - 1)) + lab, lead, SM.due(M, lab), f"{pg:g}" if pg else ""])
            it.setData(0, Qt.UserRole, lab)
            if lv == 1:
                ft = it.font(0); ft.setBold(True); it.setFont(0, ft)
            self.tree.addTopLevelItem(it)
            if lab == keep:
                sel = it
        self.tree.blockSignals(False)
        g = SM.gaps(M)
        n = self.tree.topLevelItemCount()
        self.p_secs.setText(f"{n} sections")
        self.p_lead.setText(f"{len(g['no_lead'])} without a lead"); self.p_lead.set_tone("warn" if g["no_lead"] else "ok")
        self.p_due.setText(f"{len(g['no_due'])} without a due date"); self.p_due.set_tone("warn" if g["no_due"] else "ok")
        on = SM.layers(M)
        for k, cb in self.layer_boxes.items():
            cb.blockSignals(True); cb.setChecked(on[k]); cb.blockSignals(False)
        self.tmpl.setText(self.templates_text(M))
        self.note.setText("Make it again whenever the structure, a layer or a template changes."
                          if M.setup and M.setup.get("exports") else "No setup made yet.")
        self.tree.setCurrentItem(sel or self.tree.topLevelItem(0))
        self.pick(self.tree.currentItem().data(0, Qt.UserRole) if self.tree.currentItem() else None)

    def templates_text(self, M):
        import templatesetup as TS
        tf = TS.choice(M)                                         # 3.72.0: a template file the team brought
        if tf:
            own = {k: os.path.basename(v["file"]) for k, v in tf.items()}
            return "Made on your template: " + "; ".join(("every volume" if k == "*" else k) + f": {n}" for k, n in own.items()) \
                + ". Use a template file... to change it or go back to the app's own."
        try:
            import setuptemplate as ST
            info = self.host.efforts.get(self.host.effort_name) or {}
            pl = ST.plan(M, self.host.config_dir, self.host.ws, self.host.effort_name or "", info)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return "Templates: set in Production > Templates."
        return "Templates (Production > Templates): " + "; ".join(
            f"{p['volume'] or 'the response'}: {p['template_name']} version {p['version']}" for p in pl)

    def pick(self, label):
        self.cur = label
        M = self._M()
        if M is None or not label:
            for w in (self.f_lead, self.f_with, self.f_due, self.f_pages):
                w.clear()
            self.f_dir.clear(); self.prev.setText("")
            return
        lead, with_ = SM.people(M, label)
        pg = PB.pages(M, label)
        self.f_lead.setText(lead); self.f_with.setText(with_); self.f_due.setText(SM.due(M, label))
        self.f_pages.setText(f"{pg:g}" if pg else ""); self.f_dir.setPlainText(SM.direction(M, label))
        self.show_preview(M, label)

    def show_preview(self, M, label):
        import html
        self.prev.setText("<br>".join(f"<b>{html.escape(t)}</b>: {html.escape(x)}" for t, x in SM.preview(M, label))
                          or "Every layer is off.")

    # ------------------------------------------------------------ edits
    def save_section(self):
        M = self._M()
        if M is None or not self.cur:
            return False
        pages = self.f_pages.text().strip()
        if pages:
            try:
                float(pages)
            except ValueError:
                self.host.status("Pages is a number, like 5 or 2.5.")
                return False
        self.host.review.snap()
        lab = self.cur
        SM.set_people(M, lab, self.f_lead.text(), self.f_with.text())
        SM.set_due(M, lab, self.f_due.text())
        SM.set_direction(M, lab, self.f_dir.toPlainText())
        old = PB.pages(M, lab)
        if (float(pages) if pages else None) != old:
            PB.set_pages(M, lab, float(pages) if pages else 0, "team")
        diag.activity("setup_section_saved", n=1)
        self.host.changed()
        self.refresh()
        return True

    def set_layer(self, key, on):
        M = self._M()
        if M is None:
            return
        self.host.review.snap()
        SM.set_layer(M, key, on)
        diag.activity("setup_layer_set", n=int(bool(on)))
        self.host.changed()
        if self.cur:
            self.show_preview(M, self.cur)

    # ------------------------------------------------------------ the structure
    def from_docx(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A Word outline", "", "Word (*.docx)")
            if not path:
                return ""
        try:
            text = SM.structure_from_docx(path)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"That file could not be read ({type(e).__name__}).")
            return ""
        if not text:
            self.host.status("No headings found: the outline needs Word's Heading styles.")
        self.heads.setPlainText(text)
        return text

    def from_rfp(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "An RFP", "", "Documents (*.docx *.pdf)")
            if not path:
                return ""
        try:
            text = SM.structure_from_rfp(path)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"That file could not be read ({type(e).__name__}).")
            return ""
        if not text:
            self.host.status("No structure found in that file. Type the headings instead.")
        self.heads.setPlainText(text)
        return text

    def use_headings(self, text=None):
        text = self.heads.toPlainText() if text is None else text
        if not SM.structure_from_text(text):
            self.host.status("Type at least one heading, like 1 Technical Approach.")
            return None
        R = self.host.review
        if R is not None:
            R.snap()
            R.M.outline = SM.structure_from_text(text)
            R.M.pending = True
            M = R.M
        else:
            if self.host.ws is None or not self.host.effort_path:
                self.host.status("Pick an effort first, or work in Unfiled.")
                return None
            path = self.host.out_path("compliance_matrix")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            stem, ext = os.path.splitext(path)
            k = 2
            while os.path.exists(path):
                path = f"{stem} ({k}){ext}"; k += 1
            M = SM.start(path, (self.host.effort_name or "Effort"), text)
            self.host.set_matrix(M, new=True)
        diag.activity("setup_structure_started", n=len(M.outline))
        self.host.changed()
        self.refresh()
        self.host.toast(f"Structure set: {len(M.outline)} section(s)")
        return M

    # ------------------------------------------------------------ outputs
    def make(self, opts=None, go=None, folder=None):
        M = self._M()
        if M is None or not M.outline:
            self.host.status("Start with a structure.")
            return None
        SM.ensure_skip(M)
        import templatesetup as TS
        if not TS.choice(M):
            return self.host.setup_page.make_on_templates(opts=opts, go=go)
        return self.make_on_file(folder)

    # ------------------------------------------------------------ 3.72.0: a template file the team brought
    def volume_names(self):
        import setupdoc as SD
        M = self._M()
        return [v for v, _e in SD.volume_groups(M)] if M is not None and M.outline else []

    def changed(self):
        M = self._M()
        if M is not None:
            M.pending = True
            self.host.changed()
        self.refresh()

    def template_file(self, volume="*", path=None, modal=True):
        from .templatefileview import choose
        if self._M() is None or not self._M().outline:
            self.host.status("Start with a structure.")
            return None
        return choose(self, volume, path, modal)

    def make_on_file(self, folder=None):
        """Every volume with a template file made on it and checked; the others on the app's own template."""
        import templatesetup as TS
        M = self._M()
        if folder is None:
            folder = self.host.out_path("setup_documents") if self.host.effort_path else os.path.dirname(M.path)
            folder = folder if os.path.isdir(folder) else os.path.dirname(folder)
        info = self.host.efforts.get(self.host.effort_name) or {}
        try:
            import ctxdocs as CX
            ctx = CX.section_context(self.host.ws.root) if self.host.ws is not None else None
            res = TS.make(M, folder, self.host.config_dir, self.host.ws, self.host.effort_name or "", info, context=ctx,
                          effort_path=self.host.effort_path or "")
        except PermissionError:
            self.host.status("A file with that name is open in Word: close it, then make again.")
            return None
        except (ValueError, OSError):
            diag.swallowed()
            self.host.status("The template file could not be read: pick it again in Use a template file...")
            return None
        others = [v for v in self.volume_names() if not TS.for_volume(M, v, self.host.effort_path or "")]
        if others:
            self.host.setup_page.make_on_templates(folder=folder, volumes=others)
        self.last_check = res
        diag.activity("setup_on_template_file", files=len(res))
        M.pending = True
        self.host.changed()
        bad = sum(1 for x in res for r in x["check"] if not r["ok"])
        self.host.toast(f"{len(res)} setup(s) made on your template in {folder}. " + (f"{bad} thing(s) to look at in the check." if bad else
                                                                                       "The check found nothing to look at."))
        if not os.environ.get("AH_TEST"):
            from .templatefileview import CheckView
            CheckView(self, res).exec()
        return res

    def plain(self, folder=None):
        M = self._M()
        if M is None or not M.outline:
            self.host.status("Start with a structure.")
            return None
        SM.ensure_skip(M)
        return self.host.setup_page.export(folder)

    def strip_files(self, paths=None):
        """3.60.0: a stripped copy of each volume, beside it; the volume itself is never changed."""
        import setupstrip as SS
        from . import filewarn
        if paths is None:
            start = self.host.out_path("setup_documents") if self.host.effort_path else ""
            paths, _ = QFileDialog.getOpenFileNames(self, "Volumes to strip", os.path.dirname(start) if start else "", "Word (*.docx)")
        out = []
        for p in paths or []:
            filewarn.say(self.host, [p])
            try:
                out.append(SS.strip(p))
            except Exception as e:  # noqa: BLE001
                diag.swallowed()
                self.host.status(f"{os.path.basename(p)} could not be stripped ({type(e).__name__}).")
        if out:
            n = sum(r["paragraphs"] for r in out)
            self.host.toast(f"{len(out)} stripped cop{'y' if len(out) == 1 else 'ies'} made: {n} setup paragraph(s) taken out")
            diag.activity("setup_stripped", n=n)
        return out

    def packets(self, folder=None):
        M = self._M()
        if M is None:
            return None
        got = SM.changes_by_person(M)
        if got is None:
            self.host.toast("Make the setup once first; changes are counted from it")
            return None
        if not got:
            self.host.toast("Nothing changed since the last setup")
            return []
        if folder is None:
            start = self.host.out_path("setup_documents") if self.host.effort_path else os.path.dirname(M.path)
            folder = QFileDialog.getExistingDirectory(self, "Folder for the authors' changes",
                                                      start if os.path.isdir(start) else os.path.dirname(start))
            if not folder:
                return None
        try:
            paths = SM.author_packets(M, folder)
        except PermissionError:
            self.host.status("A file with that name is open in Word: close it, then try again.")
            return None
        diag.activity("setup_author_changes", n=len(paths))
        self.host.toast(f"{len(paths)} author file(s) written")
        return paths
