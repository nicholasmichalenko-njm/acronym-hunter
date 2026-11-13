"""Review's section dialogs (3.83.0, split from assign.py): People for each section, the page budget, and Volumes.
Each takes the Review page (self); the page's methods call these. Nothing leaves the PC."""
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QRadioButton, QScrollArea, QVBoxLayout, QWidget)

import compliance as C
import diag
import setupdoc as SD
from . import design as D


def people_dialog(self):
    if self.M is None or not self.M.outline:
        self.host.status("Build the response structure first (Shred): people lead and write its sections.")
        return None
    d = QDialog(self); d.setWindowTitle("People for each section"); d.resize(720, 520)
    lay = QVBoxLayout(d)
    lay.addWidget(QLabel("A lead and contributors, from the author list. Requirements in a section and its subsections "
                         "take its lead as author unless they have their own."))
    from .people import NamesField, combo_name, empty_text, name_combo
    if not self.host.people():                     # 2.77.0: the author list is the only source of names
        warn = D.label(empty_text(self.host), "crit"); warn.setWordWrap(True); lay.addWidget(warn)
    area = QScrollArea(); area.setWidgetResizable(True); inner = QWidget(); form = QFormLayout(inner); area.setWidget(inner)
    lay.addWidget(area, 1)
    rows = []
    for o in self.M.outline:
        lab = C.outline_label(o)
        pp = SD.setup_of(self.M)["owners"].get(lab) or {}
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
        le = name_combo(self.host, pp.get("lead", ""))
        we = NamesField(self.host, SD.split_names(pp.get("with", "")), empty="(no contributors)", title=f"Contributors: {lab}")
        h.addWidget(le, 1); h.addWidget(we, 2)
        form.addRow(("    " * max(0, o.get("level", 1) - 1)) + lab, w)
        rows.append((lab, le, we))
    bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); lay.addWidget(bb)
    bb.rejected.connect(d.reject)

    def save():
        self.R.snap()
        for lab, le, we in rows:
            SD.set_people(self.M, lab, combo_name(le), we.text())
        self.M.pending = True
        diag.activity("compliance_people_set", n=len(rows))
        d.accept()
        self.after()
    bb.accepted.connect(save)
    d._api = {"rows": rows, "save": save}
    d.show()
    return d


def budget_dialog(self, run=True):
    """3.1.0: each volume's page limit split across its sections. run=False (tests): the dialog."""
    if self.M is None or not self.M.outline:
        self.host.status("Build the response structure first: the budget is split across its sections.")
        return None
    from .budgetview import BudgetDialog
    d = BudgetDialog(self.host)
    if not run:
        return d
    d.exec()
    if d.saved:
        self.after("Page Allocation saved.")
    return d.saved


def volumes_dialog(self):
    """One volume (a name, or blank) or several (the headings of the structure that start a volume)."""
    if self.M is None:
        self.host.status("Add the customer's documents in Documents first: the volumes are part of the compliance matrix.")
        return None
    mode, name, heads = SD.volumes_of(self.M)
    d = QDialog(self); d.setWindowTitle("Volumes"); d.resize(560, 520)
    lay = QVBoxLayout(d)
    one, sev = QRadioButton("One volume"), QRadioButton("Several volumes: tick the headings that start one")
    g = QButtonGroup(d); g.addButton(one); g.addButton(sev)
    (sev if mode == "several" else one).setChecked(True)
    lay.addWidget(one)
    nm = QLineEdit(name); nm.setPlaceholderText("its name (or leave blank)"); lay.addWidget(nm)
    lay.addWidget(sev)
    area = QScrollArea(); area.setWidgetResizable(True); inner = QWidget(); iv = QVBoxLayout(inner); area.setWidget(inner)
    boxes = []
    for o in self.M.outline:
        lab = C.outline_label(o)
        cb = QCheckBox(("    " * max(0, o.get("level", 1) - 1)) + lab); cb.setChecked(lab in heads); iv.addWidget(cb)
        boxes.append((lab, cb))
    lay.addWidget(area, 1)
    bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); lay.addWidget(bb)
    bb.rejected.connect(d.reject)

    def save():
        if sev.isChecked():
            hs = [lab for lab, cb in boxes if cb.isChecked()]
            if not hs:
                self.host.status("Tick at least one heading that starts a volume.")
                return
            SD.set_volumes(self.M, "several", "", hs)
        else:
            SD.set_volumes(self.M, "one", nm.text().strip(), [])
        self.M.pending = True
        diag.activity("compliance_volumes_set")
        d.accept()
        self.host.changed()
    bb.accepted.connect(save)
    d._api = {"one": one, "several": sev, "name": nm, "boxes": boxes, "save": save}
    d.show()
    return d
