"""The Overview's landing and the doors' row (4.52.0; decisions 7, 80, 8). With nothing open the Overview shows a place to
drop a document, the three doors as cards of one size (Acronyms, Shred to setup, Check a document) and one quiet row (All
tools, and All Efforts once an effort or a program exists); nothing else. With something open the doors stay as one
compact row under the next step (DoorRow): a small place to drop a document, the doors of that kind of home, All tools.
A drop or a door asks which door and where in one step (doorsview). Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

import doors as DR
from . import design as D
from .adaptive import FlowLayout
from .navrail import ClickFrame
from .toolshome import DropZone


def _files(e):
    return [os.path.normpath(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile() and os.path.isfile(u.toLocalFile())]


def _views():
    from . import doorsview
    return doorsview


class DoorCard(ClickFrame):
    """A door: its name and its one line. A click chooses a file for it; a file dropped on it goes through it."""

    def __init__(self, host, door):
        super().__init__("doorCard")
        self.host, self.door = host, door
        self.setAcceptDrops(True); self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedWidth(300); self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        D.themed(self, lambda t: f"QFrame#doorCard{{background:{t['surface']};border:1px solid {t['border']};border-radius:10px;}}"
                                 f"QFrame#doorCard:hover, QFrame#doorCard:focus{{border-color:{t['accent']};}}"
                                 "QFrame#doorCard QLabel{background:transparent;}")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"]); v.setSpacing(6)
        self.name = D.label(DR.NAMES[door], "title", wrap=False); v.addWidget(self.name)
        self.what = D.label(DR.WHAT[door], "muted"); v.addWidget(self.what)
        v.addStretch(1)
        for x in (self.name, self.what):
            x.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setToolTip("Click to choose a file, or drop one here")
        self.clicked.connect(lambda: _views().choose(self.host, self.door))

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.click()
            e.accept()
            return
        super().keyPressEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = _files(e)
        if files:
            _views().ask(self.host, files, self.door)


class Landing(QWidget):
    """What the Overview shows with nothing open."""

    def __init__(self, host):
        super().__init__()
        self.host = host
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["l"])
        self.drop = DropZone(lambda paths: _views().ask(host, paths), "Drop a document here: Word, PDF, PowerPoint, Excel or a picture.")
        self.drop.setMinimumHeight(150)
        v.addWidget(self.drop)
        row = QHBoxLayout(); v.addLayout(row)
        self.choose_btn = D.button("Choose a file...", "primary", lambda: _views().choose(host))
        row.addWidget(self.choose_btn); row.addStretch(1)
        self.cards_w = QWidget(); self.flow = FlowLayout(self.cards_w, D.SPACE["m"])
        self.cards = {}
        for k in DR.for_home("none"):
            c = DoorCard(host, k)
            self.cards[k] = c
            self.flow.addWidget(c)
        v.addWidget(self.cards_w)
        quiet = QHBoxLayout(); quiet.setSpacing(D.SPACE["s"]); v.addLayout(quiet)
        self.tools_btn = D.button("All tools", "ghost", lambda: host.go("tools"), "Every tool, on any file")
        self.efforts_btn = D.button("All Efforts", "ghost", lambda: host.go("efforts"), "Every effort and program on this PC")
        quiet.addWidget(self.tools_btn); quiet.addWidget(self.efforts_btn); quiet.addStretch(1)
        v.addStretch(1)

    def refresh(self):
        import programs as PG
        reg = self.host.efforts
        self.efforts_btn.setVisible(bool(PG.effort_names(reg) or PG.names(reg)))
        return list(self.cards)


class DoorRow(QFrame):
    """The doors as one compact row, under the next step (an effort) or the program's name (a program)."""

    def __init__(self, host, kind="effort"):
        super().__init__()
        self.host, self.kind = host, kind
        self.setAcceptDrops(True); self.setObjectName("doorRow")
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
        self.drop = QLabel("Drop a document"); self.drop.setObjectName("doorDrop"); self.drop.setAlignment(Qt.AlignCenter)
        self.drop.setMinimumWidth(150)
        self.drop.setStyleSheet("QLabel#doorDrop{border:1px dashed palette(mid);border-radius:6px;padding:5px 10px;}")
        self.drop.setToolTip("Drop a file here, or use a door")
        h.addWidget(self.drop)
        self.btn_box = QHBoxLayout(); self.btn_box.setSpacing(D.SPACE["s"]); h.addLayout(self.btn_box)
        self.tools_btn = D.button("All tools", "ghost", lambda: host.go("tools"), "Every tool, on any file")
        h.addWidget(self.tools_btn); h.addStretch(1)
        self.btns = {}
        self.set_kind(kind)

    def set_kind(self, kind):
        self.kind = kind
        for b in self.btns.values():
            b.setParent(None); b.deleteLater()
        self.btns = {}
        for k in DR.for_home(kind):
            b = D.button(DR.NAMES[k], None, lambda _c=False, k_=k: _views().choose(self.host, k_), DR.WHAT[k])
            self.btn_box.addWidget(b); self.btns[k] = b
        return list(self.btns)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = _files(e)
        if files:
            _views().ask(self.host, files)
