"""Template Studio > Read back (3.67.0): a template or volume made from the Studio read back from its XML and set against
the volume's sections and numbering and the field recipes, one row per thing checked; Word draws the first page of each part
when Word is on this PC. readback holds the rules."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QHeaderView, QLabel, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import fieldrecipes as FR
import readback as RB
from . import design as D


class ReadBackView(QWidget):
    def __init__(self, studio):
        super().__init__()
        self.studio = studio
        self.path, self.result, self.pngs = "", None, {}
        v = QVBoxLayout(self); v.setContentsMargins(0, D.SPACE["s"], 0, 0); v.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.button("Read a file...", "primary", lambda: self.choose(), "A template or volume made from this volume's template"))
        self.b_again = D.button("Read it again", None, lambda: self.read(self.path)); top.addWidget(self.b_again)
        self.b_draw = D.button("Word draws each section", None, lambda: self.draw(),
                               "A hidden Word lays out a copy and the first page of each section is shown below")
        top.addWidget(self.b_draw)
        top.addStretch(1)
        self.what = D.label("Read a template or volume to see each section against its plan: page numbers, restarts, the "
                            "chapter style, orientation and paper, then the fields against the field recipes.", "muted")
        v.addWidget(self.what)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Part", "Checked", "The plan says", "The file has", ""])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        v.addWidget(self.table, 2)
        self.strip = QWidget(); self.sl = QHBoxLayout(self.strip); self.sl.setContentsMargins(0, 0, 0, 0); self.sl.addStretch(1)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(self.strip); sc.setMinimumHeight(180)
        v.addWidget(sc, 1)
        self._buttons()

    def _buttons(self):
        self.b_again.setEnabled(bool(self.path)); self.b_draw.setEnabled(bool(self.path))

    def parts(self):
        return self.studio.plan()

    def choose(self):
        path, _ = QFileDialog.getOpenFileName(self, "A template or volume made from this volume's template", "",
                                              "Word (*.dotx *.docx *.dotm *.docm)")
        if path:
            self.read(path)

    def read(self, path):
        if not path or not os.path.isfile(path):
            return None
        host = self.studio.host
        try:
            self.result = RB.check(path, self.parts(), FR.effective(host.config_dir, host.ws))
        except Exception:  # noqa: BLE001  a file that does not read as Word
            diag.swallowed()
            host.status("That file does not read as a Word file.")
            return None
        self.path = path
        diag.activity("readback_read")
        rows = self.result["rows"]
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, val in enumerate((r["part"], r["what"], r["plan"], r["file"], {"matches": "Matches", "differs": "Differs",
                                                                                   "missing": "Missing"}[r["status"]])):
                c = QTableWidgetItem(str(val))
                if j == 4 and r["status"] != "matches":
                    c.setForeground(D.color("warn" if r["status"] == "differs" else "crit"))
                self.table.setItem(i, j, c)
        self.what.setText(f"{os.path.basename(path)}: {self.result['summary']}.")
        self._buttons()
        return self.result

    def draw(self, runner=None):
        if not self.path:
            return None
        out = os.path.join(self.studio.host.config_dir, "readback pages")
        res = RB.draw_parts(self.path, out, self.parts(), runner=runner)
        if not res.get("ok"):
            self.studio.host.status(res.get("why", "Word could not draw the pages."))
            return res
        self.pngs = res["pngs"]
        while self.sl.count() > 1:
            w = self.sl.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for p in self.parts():
            png = self.pngs.get(p["id"])
            box = QWidget(); bl = QVBoxLayout(box); bl.setContentsMargins(0, 0, 0, 0)
            pic = QLabel(); pic.setAlignment(Qt.AlignCenter)
            if png:
                pic.setPixmap(QPixmap(png).scaledToHeight(150, Qt.SmoothTransformation))
            else:
                pic.setText("No page")
            bl.addWidget(pic); bl.addWidget(D.label(p["name"], "muted", wrap=False))
            self.sl.insertWidget(self.sl.count() - 1, box)
        self.studio.host.toast(f"Word drew {len(self.pngs)} section(s) of {res.get('pages')} page(s)")
        return res
