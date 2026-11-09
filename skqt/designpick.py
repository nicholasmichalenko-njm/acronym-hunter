"""Setup's Design rows (3.87.0): for each section around the response (CUI cover, Cover, Title page, Table of Contents,
Acronyms and Abbreviations, Units and Symbols, Back cover) the design to use, from the Section designs library, or None
where the section is optional (None leaves it out). Make the setup fills each picked design with the volume's fill-ins
and writes it beside the setup. Rules: sectiondesigns. Nothing leaves the PC."""
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout

import sectiondesigns as SDZ
from . import design as D


class DesignPick(QDialog):
    def __init__(self, page, M, config_dir):
        super().__init__(page)
        self.setWindowTitle("Section designs for this effort"); self.resize(560, 360)
        self.M, self.cfg = M, config_dir
        v = QVBoxLayout(self)
        v.addWidget(D.label("The design each section uses, from Production > Section designs. None leaves an optional "
                            "section out. Make the setup fills each one and writes it beside the setup.", "muted"))
        f = QFormLayout(); v.addLayout(f)
        self.boxes = {}
        for shelf in SDZ.SHELVES:
            cb = QComboBox()
            cb.addItem("(not set)", "")
            if shelf in SDZ.OPTIONAL:
                cb.addItem("None: leave this section out", "none")
            for x in SDZ.designs(config_dir, shelf):
                cb.addItem(x["name"], x["id"])
            cur = SDZ.picked(M, shelf)
            cb.setCurrentIndex(max(0, cb.findData(cur)))
            f.addRow(SDZ.SHELF_NAME[shelf], cb)
            self.boxes[shelf] = cb
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def save(self):
        for shelf, cb in self.boxes.items():
            SDZ.pick(self.M, shelf, cb.currentData() or "")
        self.accept()
