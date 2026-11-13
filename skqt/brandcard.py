"""Settings > Appearance > Branding (2.88.0; its own module since 4.24.0, split from brandview): the company logos at
the top of the menu. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
import branding as BR
import diag
from . import design as D


class BrandingCard(D.Card):
    """Settings > Branding: the company logos at the top of the menu (up to three, in order)."""

    def __init__(self, host):
        super().__init__("Branding", "The company logos at the top of the menu. 3.0.3: they are built into Stationkeeper, so "
                         "nobody changes them by accident; a new logo comes with a new version or the team pack.")
        self.host = host
        self.row = QHBoxLayout(); self.row.setSpacing(D.SPACE["m"]); self.body.addLayout(self.row)
        self.note = self.add(D.label("", "muted"))
        self.refresh()

    def refresh(self):
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        paths = BR.logos(self.host.config_dir)
        t = D.tokens()
        for p in paths:
            box = QFrame(); box.setStyleSheet(f"QFrame{{background:#FFFFFF;border:1px solid {t['border']};border-radius:8px;}}")
            bv = QVBoxLayout(box); bv.setContentsMargins(8, 8, 8, 8)
            lab = QLabel(); lab.setPixmap(QPixmap(p).scaled(160, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lab.setAlignment(Qt.AlignCenter); lab.setStyleSheet("border:none;"); bv.addWidget(lab)
            self.row.addWidget(box)
        self.row.addStretch(1)
        import teampack as TP
        lk = TP.locks(self.host.config_dir).get("logos")
        self.locked = bool(lk)
        for b in self.findChildren(QPushButton):
            if b.text() in ("<", ">", "Remove", "Add logo..."):
                b.setEnabled(not lk)
        baked = bool(BR.baked_logos())
        self.note.setText("Built into this version of Stationkeeper." if baked else
                          f"Set by the team pack {lk}." if lk else
                          "Kept on this PC from an earlier version. A version with your company logo built in replaces them."
                          if paths else "No company logo in this version. It is built in by whoever builds Stationkeeper.")

    def changed(self):
        self.refresh()
        self.host.rail_brand.refresh()

    def add_logo(self, path=None):
        import teampack as TP
        if TP.locked(self.host.config_dir, "logos"):
            self.host.status("The team pack set the logos. They change when the team sends a new pack.")
            return False
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Company logo", "", "Pictures (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return False
        try:
            BR.add_logo(self.host.config_dir, path)
        except ValueError as e:
            self.host.status(f"At most {BR.LOGO_MAX} logos: remove one first." if "most" in str(e) else "That file is not a picture.")
            return False
        except Exception:
            diag.swallowed()
            self.host.status("That picture could not be read. Try a PNG or JPG.")
            return False
        diag.activity("qt_logo_added")
        self.changed()
        return True

    def remove(self, p):
        if not getattr(self, "locked", False):
            BR.remove_logo(self.host.config_dir, p)
        self.changed()

    def move(self, p, step):
        if not getattr(self, "locked", False):
            BR.move_logo(self.host.config_dir, p, step)
        self.changed()
