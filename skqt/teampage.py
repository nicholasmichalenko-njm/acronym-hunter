"""Team (3.96.0; canvas "Navigation", board 3): the team's own tools on one page of tiles, shown to the roles that use
them: Rules, Check a Draft, Team References (4.28.0: the standards and templates are the menu's Templates group). Each tile says what it is for
and opens it. Nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from . import design as D
from .navrail import ClickFrame

TILES = (("rules", "Rules", "Every production rule in one list"),
         ("audit", "Check a Draft", "Check files against every standard that applies to them: read only"),
         ("refs", "Team References", "The lists the team keeps: dictionaries, banned phrases, the acronym database"))


class TeamPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.note = D.label("", "muted"); v.addWidget(self.note)
        self.grid = QGridLayout(); self.grid.setSpacing(D.SPACE["m"]); v.addLayout(self.grid)
        v.addStretch(1)
        self.tiles = {}
        t = D.tokens()
        for key, name, what in TILES:
            b = ClickFrame("teamTile"); b.setMinimumHeight(96)
            bl = QVBoxLayout(b); bl.setContentsMargins(D.SPACE["l"], D.SPACE["m"], D.SPACE["l"], D.SPACE["m"]); bl.setSpacing(4)
            nm = QLabel(name); nm.setObjectName("tileName"); wt = QLabel(what); wt.setObjectName("tileWhat"); wt.setWordWrap(True)
            for x in (nm, wt):
                x.setAttribute(Qt.WA_TransparentForMouseEvents); bl.addWidget(x)
            bl.addStretch(1)
            D.themed(b, lambda t: f"QFrame#teamTile{{background:{t['surface']};border:1px solid {t['border']};border-radius:10px;}}"
                            f"QFrame#teamTile:hover{{border:1px solid {t['accent']};}}"
                            f"QLabel#tileName{{font-size:15px;font-weight:600;color:{t['text']};background:transparent;}}"
                            f"QLabel#tileWhat{{color:{t['muted']};background:transparent;}}")
            b.clicked.connect(lambda k=key: self.host.rail_go(k))
            self.tiles[key] = b

    def shown(self):
        import roleaccess as RA
        prof, _src = self.host.profile()
        from .mainwin import members
        return [k for k, _n, _w in TILES if any(RA.allowed(prof, x) for x in members(k))], prof

    def refresh(self):
        keys, prof = self.shown()
        while self.grid.count():
            self.grid.takeAt(0)
        for b in self.tiles.values():
            b.setVisible(False)
        for i, k in enumerate(keys):
            b = self.tiles[k]
            self.grid.addWidget(b, i // 3, i % 3); b.setVisible(True)
        hidden = len(TILES) - len(keys)
        self.note.setText(f"{hidden} more are for other roles than {prof}." if hidden else "")
        self.note.setVisible(bool(hidden))
        return keys
