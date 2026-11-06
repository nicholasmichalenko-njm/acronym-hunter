"""Setup > Use a template file... (3.72.0, claude/stationkeeper-template-setup-decisions-2026-11-06.md): a Word template
the team already made and trusts, for every volume or one volume. It shows what the template holds (its parts in
order with their page numbers and headers, the heading numbering, its Quick Parts, the setup styles it has or gets,
its theme fonts) and what the setup takes from it: blank by default, the body only in the template's look; tick the
template's own cover, title page or front matter, any Quick Part, and which parts keep their header and footer. Make the
setup makes it and shows the check read from the made file. templatefile and templatesetup hold the rules."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QVBoxLayout)
import diag
import templatefile as TF
import templatesetup as TS
from . import design as D

EVERY = "*"


class TemplateFileDialog(QDialog):
    def __init__(self, page, volume=EVERY):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.setWindowTitle("Use a template file")
        self.resize(1180, 760)
        self.info, self.path = None, ""
        v = QVBoxLayout(self)
        v.addWidget(D.label("A Word template your team already made and trusts. The setup starts blank in its look (its styles, "
                            "theme, numbering, headers and footers): tick what else comes in. The template is only read; a copy "
                            "is kept with the effort.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.label("Template for", None, wrap=False))
        self.vol = QComboBox()
        self.vol.addItem("Every volume", EVERY)
        for name in page.volume_names():
            self.vol.addItem(name or "The response", name)
        self.vol.setCurrentIndex(max(0, self.vol.findData(volume)))
        self.vol.activated.connect(lambda _i: self.load())
        top.addWidget(self.vol)
        self.file_lab = D.label("", None, wrap=False); top.addWidget(self.file_lab, 1)
        top.addWidget(D.button("Pick a template file...", None, lambda: self.pick()))
        self.b_clear = D.button("Use the app's own template", "ghost", lambda: self.clear(),
                                "Make this volume's setup on the template the app builds from the formatting standards")
        top.addWidget(self.b_clear)
        mid = QHBoxLayout(); v.addLayout(mid, 1)
        left = QVBoxLayout(); mid.addLayout(left, 3)
        left.addWidget(D.SectionTitle("What it holds, in order"))
        self.parts = QTableWidget(0, 5)
        self.parts.setHorizontalHeaderLabels(["In the setup", "Part", "Starts with", "Page numbers", "Header, footer"])
        self.parts.verticalHeader().setVisible(False)
        self.parts.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for c, wd in ((0, 96), (1, 110), (3, 215), (4, 110)):
            self.parts.setColumnWidth(c, wd)
        left.addWidget(self.parts, 2)
        left.addWidget(D.SectionTitle("Headings"))
        self.heads = D.label("", "muted"); left.addWidget(self.heads)
        right = QVBoxLayout(); mid.addLayout(right, 2)
        right.addWidget(D.SectionTitle("Quick Parts to add"))
        right.addWidget(D.label("A cover page goes first; the rest just before the body.", "muted"))
        self.qps = QListWidget(); right.addWidget(self.qps, 1)
        right.addWidget(D.SectionTitle("Setup styles"))
        self.styles = QTableWidget(0, 2); self.styles.setHorizontalHeaderLabels(["Style", "In this template"])
        self.styles.verticalHeader().setVisible(False); self.styles.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.styles.setColumnWidth(1, 200)
        right.addWidget(self.styles, 1)
        self.theme = D.label("", "muted"); right.addWidget(self.theme)
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(D.button("Setup styles...", None, lambda: self.page.styles()))
        bar.addStretch(1)
        bb = QDialogButtonBox()
        self.b_make = bb.addButton("Save and make the setup", QDialogButtonBox.AcceptRole)
        self.b_save = bb.addButton("Save", QDialogButtonBox.ApplyRole)
        bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(lambda: (self.save(), self.accept(), self.page.make()))
        self.b_save.clicked.connect(lambda: (self.save(), self.accept()))
        bb.rejected.connect(self.reject)
        bar.addWidget(bb)
        self.load()

    # ------------------------------------------------------------ the chosen file
    def load(self):
        M = self.page._M()
        got = TS.for_volume(M, self.vol.currentData(), self.host.effort_path or "") if M is not None else \
            TS.for_volume(None, EVERY, self.host.effort_path or "", chosen=TS.waiting(self.host.ws))   # 3.73.0: before the sections
        if self.vol.currentData() != EVERY and M is not None and self.vol.currentData() not in TS.choice(M):
            got = None if not TS.choice(M).get(EVERY) else got        # shown as following Every volume
        self.open(got[0] if got else "", got[1] if got else None)

    def open(self, path, picks=None):
        self.path = path or ""
        self.info = None
        if self.path:
            try:
                self.info = TF.read(self.path)
            except (ValueError, OSError) as e:
                diag.swallowed()
                self.host.status(str(e) if isinstance(e, ValueError) else "That file could not be read.")
                self.path = ""
        self.picks = dict(picks or TF.default_picks(self.info))
        self.fill()
        return self.info

    def pick(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "The template", "", "Word templates and documents (*.dotx *.dotm *.docx)")
            if not path:
                return None
        return self.open(path)

    def clear(self):
        M = self.page._M()
        if M is not None:
            TS.clear_choice(M, self.vol.currentData())
            self.page.changed()
        else:
            TS.clear_waiting(self.host.ws)
            self.page.refresh()
        self.open("")

    # ------------------------------------------------------------ the view
    def fill(self):
        i = self.info
        self.file_lab.setText(f"<b>{os.path.basename(self.path)}</b>" + (" (macros are left out of the setup)" if i and i["macros"] else "")
                              if i else "No template file: the app builds the template from the formatting standards.")
        self.file_lab.setTextFormat(Qt.RichText)
        self.b_clear.setEnabled(bool(i)); self.b_make.setEnabled(bool(i)); self.b_save.setEnabled(bool(i))
        secs = i["sections"] if i else []
        keep, no_hf = set(self.picks.get("keep") or []), set(self.picks.get("no_hf") or [])
        self.parts.setRowCount(len(secs)); self.boxes = {}
        for r, s in enumerate(secs):
            fixed = s["kind"] in ("body", "appendix")
            cb = QCheckBox(); cb.setChecked(fixed or s["index"] in keep); cb.setEnabled(not fixed)
            cb.setToolTip("Always: the setup goes here" if s["kind"] == "body" else
                          "Used when the structure has appendices" if s["kind"] == "appendix" else "Add this page of the template")
            hf = QCheckBox("Keep"); hf.setChecked(s["index"] not in no_hf); hf.setEnabled(s["header"] or s["footer"])
            hf.setToolTip("Off: this part has a blank header and footer")
            self.parts.setCellWidget(r, 0, cb)
            self.parts.setItem(r, 1, QTableWidgetItem(s["name"]))
            self.parts.setItem(r, 2, QTableWidgetItem(s["first_text"] or "(blank)"))
            self.parts.setItem(r, 3, QTableWidgetItem({"i": "i, ii, iii", "I": "I, II, III", "1": "1, 2, 3", "A-1": "1-1, 1-2 (by chapter)"}
                                                      .get(s["format"], s["format"] or "-") + ("" if s["page_number"] else ", not shown")
                                                      + (", starts again" if s["restart"] else "")))
            self.parts.setCellWidget(r, 4, hf)
            self.boxes[s["index"]] = (cb, hf)
        hs = i["headings"] if i else []
        self.heads.setText("; ".join(f"Heading {h['level']}: " + (f"numbered {h['sample']}" if h["numbered"] else "not numbered") for h in hs[:4])
                           + (". The outline's numbers are kept where Word's own numbering would print others." if hs else "")
                           if hs else "")
        self.qps.clear()
        chosen = set(self.picks.get("quick_parts") or [])
        for q in (i["quick_parts"] if i else []):
            it = QListWidgetItem(f"{q['gallery_name']}: {q['name']}" + (f"   ({q['text'][:50]})" if q.get("text") else ""))
            it.setData(Qt.UserRole, q["name"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if q["name"] in chosen else Qt.Unchecked)
            self.qps.addItem(it)
        if i is not None and not (i["quick_parts"]):
            self.qps.addItem("This template has no Quick Parts.")
        rows = TF.setup_styles_status(i, self.page.setup_opts()) if i else []
        self.styles.setRowCount(len(rows))
        for r, (_k, name, have) in enumerate(rows):
            self.styles.setItem(r, 0, QTableWidgetItem(name))
            self.styles.setItem(r, 1, QTableWidgetItem("Yes: used as it is" if have == "in the template" else "No: added (Setup styles)"))
        th = (i or {}).get("theme") or {}
        self.theme.setText(f"Theme fonts: {th.get('major') or 'none named'} (headings), {th.get('minor') or 'none named'} (body)"
                           if i and (th.get("major") or th.get("minor")) else "")

    def picks_now(self):
        keep = [k for k, (cb, _hf) in self.boxes.items() if cb.isEnabled() and cb.isChecked()]
        no_hf = [k for k, (_cb, hf) in self.boxes.items() if hf.isEnabled() and not hf.isChecked()]
        qps = [self.qps.item(r).data(Qt.UserRole) for r in range(self.qps.count())
               if self.qps.item(r).data(Qt.UserRole) and self.qps.item(r).checkState() == Qt.Checked]
        return {"keep": sorted(keep), "quick_parts": qps, "no_hf": sorted(no_hf)}

    def save(self):
        M = self.page._M()
        if not self.path:
            return None
        if M is None or not M.outline:                     # 3.73.0: before the sections, it waits with the effort
            if self.host.ws is None:
                self.host.status("Pick an effort first, or work in Unfiled.")
                return None
            c = TS.set_waiting(self.host.ws, self.path, self.picks_now(), self.host.effort_path or "")
            diag.activity("setup_template_file_chosen")
            self.page.refresh()
            self.host.toast("The setup will be made on " + os.path.basename(self.path) + " once there are sections.")
            return c
        c = TS.set_choice(M, self.vol.currentData(), self.path, self.picks_now(), self.host.effort_path or "")
        diag.activity("setup_template_file_chosen")
        self.page.changed()
        self.host.toast("The setup will be made on " + os.path.basename(self.path)
                        + ("" if self.vol.currentData() == EVERY else f" for {self.vol.currentText()}"))
        return c


class CheckView(QDialog):
    """What the check read from each made file: every row, the ones to look at first."""

    def __init__(self, parent, results):
        super().__init__(parent)
        self.setWindowTitle("The setup, checked")
        self.resize(900, 520)
        v = QVBoxLayout(self)
        bad = sum(1 for x in results for r in x["check"] if not r["ok"])
        v.addWidget(D.label("Read back from each file before it is handed over. " + (f"{bad} thing(s) to look at." if bad else
                                                                                       "Nothing to look at."), "muted"))
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["Volume", "Check", "Result", "Where"])
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        rows = [(x["volume"] or "The response", r) for x in results for r in sorted(x["check"], key=lambda r: r["ok"])]
        self.table.setRowCount(len(rows))
        for i, (vol, r) in enumerate(rows):
            for c, val in enumerate((vol, r["what"], "OK" if r["ok"] else "Look at this", r["where"])):
                self.table.setItem(i, c, QTableWidgetItem(val))
        v.addWidget(self.table, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); bb.accepted.connect(self.accept)
        v.addWidget(bb)


def choose(page, volume=EVERY, path=None, modal=True):
    dlg = TemplateFileDialog(page, volume)
    if path:
        dlg.pick(path)
    page.template_dialog = dlg
    if modal:
        dlg.exec()
    else:
        dlg.show()
    return dlg
