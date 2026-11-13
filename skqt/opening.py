"""The window shown while Stationkeeper opens (4.30.1; Nicholas 2026-11-13 14:21: opening takes several seconds and looks
like nothing is happening, so people double-click again). It shows as soon as the program starts, before the main
window is built, says the app is opening and that there is no need to click again, and goes when the main window shows.
A small window with no buttons; it reads nothing and writes nothing. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from . import design as D

TITLE = "Stationkeeper is opening"
SAYS = "This takes a few seconds. There is no need to click again."


class Opening(QWidget):
    def __init__(self, version="", icon_path=""):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        t = D.tokens()
        self.setObjectName("opening")
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        box = QFrame(); box.setObjectName("openingBox"); v.addWidget(box)
        box.setStyleSheet(f"QFrame#openingBox{{background:{t['surface']};border:1px solid {t['border_strong']};border-radius:10px;}}")
        bv = QVBoxLayout(box); bv.setContentsMargins(D.SPACE["xl"], D.SPACE["xl"], D.SPACE["xl"], D.SPACE["l"]); bv.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); bv.addLayout(top)
        self.pic = QLabel()
        if icon_path:
            pm = QIcon(icon_path).pixmap(40, 40)
            if not pm.isNull():
                self.pic.setPixmap(pm)
        top.addWidget(self.pic, 0, Qt.AlignTop)
        words = QVBoxLayout(); words.setSpacing(2); top.addLayout(words, 1)
        self.title = QLabel(TITLE); self.title.setStyleSheet(f"font-size:{D.TYPE['display'] - 4}pt;font-weight:600;color:{t['text']};background:transparent;")
        self.says = QLabel(SAYS); self.says.setStyleSheet(f"color:{t['muted']};background:transparent;")
        words.addWidget(self.title); words.addWidget(self.says)
        self.bar = QProgressBar(); self.bar.setRange(0, 0); self.bar.setTextVisible(False); self.bar.setFixedHeight(6)
        bv.addSpacing(D.SPACE["s"]); bv.addWidget(self.bar)
        self.ver = QLabel(f"Version {version}" if version else ""); self.ver.setStyleSheet(f"color:{t['faint']};font-size:{D.TYPE['small']}pt;background:transparent;")
        bv.addWidget(self.ver, 0, Qt.AlignRight)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(460)
        self.adjustSize()

    def center(self, app):
        scr = app.primaryScreen()
        if scr is not None:
            g = scr.availableGeometry()
            self.move(g.center().x() - self.width() // 2, g.center().y() - self.height() // 2)


def show(app, version="", icon_path=""):
    """Show the window now and paint it before the slow part starts. Returns it (None if it could not be shown: the
    app opens all the same)."""
    try:
        w = Opening(version, icon_path)
        w.center(app)
        w.show()
        app.processEvents()
        return w
    except Exception:  # noqa: BLE001
        return None


def done(w):
    """The main window is up: the opening window goes."""
    try:
        if w is not None:
            w.close(); w.deleteLater()
    except RuntimeError:
        pass
    return None
