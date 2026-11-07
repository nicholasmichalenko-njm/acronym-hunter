"""Setup (3.56.0, claude/stationkeeper-setup-decisions-2026-11-04.md): the starting draft each author writes in, made from
a structure, layers and a template, and made again whenever one of them changes. A structure is the least it needs:
headings typed, from a Word outline or from an RFP's headings, before or without a Review. Each section: its lead and
contributors, due date, pages and PM direction, and what it will print. Layers say what fills the sections. Make the setup
writes it on each volume's template (Production > Templates); Plain setup writes it with no template; Changes for authors
writes one Word file per person with what changed in their sections. Rules only (setupmake, setupdoc); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

import diag
import pagebudget as PB
import setupmake as SM
from . import design as D
from .adaptive import FlowLayout


class SetupsPage(QWidget):
    """3.74.0 (decision 12, and the eight rules of claude/stationkeeper-simplify-decisions-2026-11-06.md): one page. The
    command bar (Make the setup, Bring in a file..., Use a template file..., Add elements..., + Volume; More; Export), a
    line saying the template and what fills each section, then the sections: the Structure Builder's tree, its
    right-click menu and keys, its placing, and the selected section's lead, contributors, due date, pages and PM
    direction. With no sections yet, one card: drop a file, bring one in, or type them."""

    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.cur = None
        self.setAcceptDrops(True)                                    # 3.73.0: drop a file to bring it in
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["s"])
        from .commandbar import CommandBar
        bar = self.bar = CommandBar()
        bar.add("Bring in a file...", lambda: self.bring_in(),
                "Excel: its columns are read (What's in your workbook). Word: its headings, or the template. PDF: the RFP's sections.")
        bar.add("Use a template file...", lambda: self.template_file(),
                "Your team's Word template: pick it before or after the sections")
        self.b_elements = bar.add("Add elements...", lambda: self.builder.add_elements(),
                                  "Table of Contents, the lists, Acronyms and Abbreviations, the Appendices section and the rest")
        self.b_volume = bar.add("+ Volume", lambda: self.builder.add_volume(), "A new volume at the end, numbered the volumes' way")
        self.b_make = bar.primary("Make the setup", lambda: self.make(),
                                  "Each volume's template with the setup written on it: the customer's words and your notes in "
                                  "hidden reference styles")
        bar.more("Edit as text / Start from", lambda: self.builder.show_text(not self.builder.text_panel.isVisible()),
                 "The sections as text, one per line, and Start from the RFP or a Word outline")
        bar.more("Sort in document order", lambda: self.builder.sort_order(),
                 "The items in every section in the order they appear in the customer documents")
        self.a_show = bar.more("Show what is placed", lambda on: self.builder.show_items.setChecked(on),
                               "Each section's requirements, support, captures and library items under it", checkable=True)
        bar.more_sep()
        bar.more("What fills each section...", lambda: self.show_layers(not self.layers.isVisible()))
        bar.more("Setup styles...", lambda: self.styles(), "The setup's own styles: name, font, size, color, bold, italic, hidden")
        bar.more("Outline versions...", lambda: self.versions(),
                 "Every version of the outline brought in: compare any two, write the workbook back out")
        bar.more("Outline layouts...", lambda: self.layouts(), "Set an outline's column names and how mixed text is told apart")
        bar.export("Plain setup...", lambda: self.plain(), "One plain Word document per volume, no template")
        bar.export("Changes for authors...", lambda: self.packets(),
                   "One Word file per person: what changed in their sections since the last setup")
        bar.export("Changes only (one file)...", lambda: self.host.setup_page.export_changes(), "Just what changed since the last export")
        self.a_kickoff = bar.export("Kickoff packets...", lambda: self.builder.kickoff(),
                                    "One Word file per author: their sections, the customer's words, how each is scored, and dates")
        bar.export("Strip setup...", lambda: self.strip_files(),
                   "Before a volume goes out: a clean copy with the setup's reference text, styles and file properties taken out")
        v.addWidget(bar)
        # ---- one line: the counts, the template, what fills each section
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.p_secs = D.Pill("0 sections", "accent")
        self.p_lead = D.Pill("0 without a lead", "ok")
        self.p_due = D.Pill("0 without a due date", "ok")
        for p in (self.p_secs, self.p_lead, self.p_due):
            top.addWidget(p)
        self.tmpl = D.label("", "muted"); top.addWidget(self.tmpl, 1)
        fl = QHBoxLayout(); fl.setSpacing(D.SPACE["s"]); v.addLayout(fl)
        self.fills = D.label("", "muted"); fl.addWidget(self.fills, 1)
        self.note = D.label("", "muted"); fl.addWidget(self.note)
        self.layers = QWidget(); lw = FlowLayout(self.layers, D.SPACE["m"])   # opened from More or the line above
        self.layer_boxes = {}
        for key, title, _kinds, _on in SM.LAYERS:
            cb = QCheckBox(title); cb.toggled.connect(lambda on, k=key: self.set_layer(k, on))
            self.layer_boxes[key] = cb; lw.addWidget(cb)
        self.layers.setVisible(False)
        v.addWidget(self.layers)

        # ---- the sections, when there are none yet (3.73.0, decision 11: bring in any file, or type them)
        self.start_card = D.Card("Sections", "Drop a file here (Excel, Word or PDF) or bring one in, and the app finds the "
                                 "sections in it. Or type them, one per line (numbers first, two spaces deeper per level). No "
                                 "Review needed, and the template can be picked before or after the sections.", key=True)
        self.heads = QPlainTextEdit(); self.heads.setPlaceholderText("1 Technical Approach\n  1.1 Understanding\n2 Management Approach")
        self.heads.setMinimumHeight(110)
        self.start_card.add(self.heads)
        sr = QHBoxLayout(); sr.setSpacing(D.SPACE["s"]); sr.addStretch(1)
        sr.addWidget(D.button("Use these sections", "primary", lambda: self.use_headings()))
        self.start_card.body.addLayout(sr)
        v.addWidget(self.start_card)

        # ---- the selected section: who writes it and when (shown inside the builder's Section panel)
        self.who = QWidget(); self.who.setProperty("sk_keep", True)
        wv = QVBoxLayout(self.who); wv.setContentsMargins(0, 0, 0, D.SPACE["s"])
        f = QFormLayout(); f.setSpacing(D.SPACE["s"])
        self.f_lead, self.f_with, self.f_due, self.f_pages = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.f_lead.setPlaceholderText("A subsection with no lead takes its parent's")
        self.f_with.setPlaceholderText("Names, with commas")
        self.f_due.setPlaceholderText("2026-11-20, or Pink Team")
        self.f_pages.setPlaceholderText("5, or 2.5")
        self.f_dir = QPlainTextEdit(); self.f_dir.setPlaceholderText("What the proposal manager wants in this section")
        self.f_dir.setMaximumHeight(90)
        for lab, w in (("Lead", self.f_lead), ("Contributors", self.f_with), ("Due", self.f_due), ("Pages", self.f_pages),
                       ("PM direction", self.f_dir)):
            f.addRow(lab, w)
        wv.addLayout(f)
        rb = QHBoxLayout(); rb.addStretch(1); rb.addWidget(D.button("Save this section", "primary", lambda: self.save_section()))
        wv.addLayout(rb)
        wv.addWidget(D.label("What it prints", "label"))
        self.prev = D.label("", "muted"); self.prev.setTextFormat(Qt.RichText)
        wv.addWidget(self.prev)

        # ---- the sections: the Structure Builder's tree, menu, keys and placing (3.74.0)
        self.builder = host.structure_page.embed(section_card=self.section_card, on_text=self.on_text, on_change=self.counts)
        self.main = self.builder
        v.addWidget(self.builder, 1)

    def on_text(self, on):
        """The sections as text (Edit as text / Start from) shows even before there are sections."""
        M = self._M()
        has = M is not None and bool(M.outline)
        self.builder.setVisible(bool(on) or has)
        self.start_card.setVisible(not on and not has)

    def section_card(self, label):
        self.pick(label)
        return self.who

    def show_layers(self, on=True):
        self.layers.setVisible(on)
        return on

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

    # ------------------------------------------------------------ 3.73.0: bring in a file, or drop one (decision 11)
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.isLocalFile() for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [os.path.normpath(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()]   # Windows separators
        if paths:
            e.acceptProposedAction()
            self.bring_in(paths[0])

    def bring_in(self, path=None, as_=None, accept=None):
        """Any file: Excel is the outline (What's in your workbook); a Word template is the template; a Word document is
        its headings or the template (asked when there are no sections yet and it has headings); a PDF is the RFP's
        sections. as_ (tests): "sections" or "template". Returns what it did, or None."""
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Bring in a file", "", "Excel, Word or PDF (*.xlsx *.xlsm *.docx *.dotx *.dotm *.pdf)")
            if not path:
                return None
        ext = os.path.splitext(path)[1].lower()
        M = self._M()
        has = M is not None and bool(M.outline)
        diag.activity("setup_file_brought_in")
        if ext in (".xlsx", ".xlsm"):
            self.from_outline(path, accept=accept)
            return "outline"
        if ext in (".dotx", ".dotm"):
            self.template_file(path=path, modal=accept is None)
            return "template"
        if ext == ".docx":
            if as_ is None:
                as_ = "template" if has else self.word_is(path)
            if as_ == "template":
                self.template_file(path=path, modal=accept is None)
                return "template"
            if has:
                self.host.status("There are sections already: change them here (right-click a section), or bring in Excel for a new version.")
                return None
            return "sections" if self.from_docx(path) else None
        if ext == ".pdf":
            if has:
                self.host.status("There are sections already: change them here (right-click a section).")
                return None
            return "sections" if self.from_rfp(path) else None
        self.host.status("Bring in an Excel workbook, a Word document or template, or a PDF.")
        return None

    def word_is(self, path):
        """A Word document with headings could be the sections or the template: asked. With none, it is the template."""
        try:
            heads = SM.structure_from_docx(path)
        except Exception:  # noqa: BLE001  read again, with its message, by from_docx
            diag.swallowed()
            heads = ""
        if not heads:
            return "template"
        if os.environ.get("AH_TEST"):
            return "sections"
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(self); box.setWindowTitle("Bring in a file")
        box.setText(f"{os.path.basename(path)} has headings. Use it as:")
        b_sec = box.addButton("The sections (its headings)", QMessageBox.AcceptRole)
        box.addButton("The template", QMessageBox.ActionRole)
        box.exec()
        return "sections" if box.clickedButton() is b_sec else "template"

    def from_outline(self, path=None, profile=None, accept=None):
        from .outlineimport import import_outline
        return import_outline(self, path, profile, accept)

    def use_outline(self, parsed, file_name, path=None, headers=None, layout="", accept=None):
        """The outline's structure and blocks into the effort (a new compliance matrix when it has none). 3.73.0: the first
        workbook is version 1; a later one is compared first (New version of the outline)."""
        import outlinexl as OX
        import outlineversions as OV
        R = self.host.review
        if R is not None and OV.current(R.M) is not None:
            from .versionsview import new_version
            return new_version(self, parsed, path or file_name, headers, layout, accept=accept)
        if R is not None:
            R.snap()
            M = R.M
        else:
            if self.host.ws is None or not self.host.effort_path:
                self.host.status("Pick an effort first, or work in Unfiled.")
                return None
            mpath = self.host.out_path("compliance_matrix")
            os.makedirs(os.path.dirname(mpath), exist_ok=True)
            stem, ext = os.path.splitext(mpath)
            k = 2
            while os.path.exists(mpath):
                mpath = f"{stem} ({k}){ext}"; k += 1
            M = SM.start(mpath, (self.host.effort_name or "Effort"), "")
            self.host.set_matrix(M, new=True)
            M = self.host.review.M
        n = OX.apply(M, parsed, file_name, who=getattr(self.host, "my_name", None) or None)
        OV.record(M, parsed, path or file_name, self.host.effort_path or "", headers, layout)    # 3.73.0: version 1
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
        if has and self.host.ws is not None:                        # 3.73.0: a template picked before the sections
            import templatesetup as TS
            if TS.adopt(M, self.host.ws):
                M.pending = True
        texting = not self.builder.text_panel.isHidden()
        self.start_card.setVisible(not has and not texting)
        self.builder.setVisible(has or texting)                      # 3.74.0: one Sections area at a time
        for b in (self.b_elements, self.b_volume, self.b_make):
            b.setEnabled(has)
        for cb in self.layer_boxes.values():
            cb.setEnabled(has)
        self.a_kickoff.setVisible(self._kickoff_on())
        self.a_show.blockSignals(True); self.a_show.setChecked(self.builder.show_items.isChecked()); self.a_show.blockSignals(False)
        if not has:
            self.builder.refresh()
            self.p_secs.setText("0 sections"); self.p_lead.setText("0 without a lead"); self.p_due.setText("0 without a due date")
            self.note.setText(""); self.fills.setText("")
            self.prev.setText(""); self.tmpl.setText(self.waiting_text())
            return
        self.counts()
        on = SM.layers(M)
        for k, cb in self.layer_boxes.items():
            cb.blockSignals(True); cb.setChecked(on[k]); cb.blockSignals(False)
        self.tmpl.setText(self.templates_text(M))
        self.note.setText("Make it again whenever the sections, what fills them or a template changes."
                          if M.setup and M.setup.get("exports") else "No setup made yet.")
        self.builder.refresh()

    def counts(self):
        """The counts and the line saying what fills each section (also after a change in the sections)."""
        M = self._M()
        if M is None or not M.outline:
            return
        g = SM.gaps(M)
        self.p_secs.setText(f"{len(SM.sections(M))} sections")
        self.p_lead.setText(f"{len(g['no_lead'])} without a lead"); self.p_lead.set_tone("warn" if g["no_lead"] else "ok")
        self.p_due.setText(f"{len(g['no_due'])} without a due date"); self.p_due.set_tone("warn" if g["no_due"] else "ok")
        on = SM.layers(M)
        self.fills.setText("What fills each section: " + (", ".join(t for k, t, _kk, _o in SM.LAYERS if on.get(k)) or "nothing")
                           + " (More > What fills each section...)")

    def _kickoff_on(self):
        import menufocus as MF
        from .modes import settings
        return "kickoff" not in MF.hidden(settings())

    def waiting_text(self):
        import templatesetup as TS
        w = TS.waiting(self.host.ws)
        return ("Template picked: " + os.path.basename(w["*"]["file"]) + ". The setup is made on it once there are sections."
                if w.get("*") else "")

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
        self.counts()
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
            self.host.status("No sections yet: bring in a file or type them.")
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

    def versions(self, modal=True):
        from .versionsview import history
        M = self._M()
        if M is None:
            self.host.status("No sections yet: bring in a file or type them.")
            return None
        return history(self, modal)

    def layouts(self, name=None, modal=True):
        from .outlinelayoutsview import edit
        return edit(self, name, modal)

    def template_file(self, volume="*", path=None, modal=True):
        from .templatefileview import choose
        return choose(self, volume, path, modal)                    # 3.73.0: before or after the sections

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
            self.host.status("No sections yet: bring in a file or type them.")
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
