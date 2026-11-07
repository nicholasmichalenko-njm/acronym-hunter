"""The command bar (3.74.0, claude/stationkeeper-simplify-decisions-2026-11-06.md decision 1): one screen's commands in
one row. One main button (the screen's job, on the right), at most four more commands, then one More menu for the rest
(one level, labeled) and one Export menu for every output. tests/qt_screenrules.py holds every bar to MAX."""
from PySide6.QtWidgets import QHBoxLayout, QMenu, QPushButton, QWidget

from . import design as D

MAX = 5                                   # visible commands in a bar, the main one included (More and Export are menus)


class CommandBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("commandbar")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(D.SPACE["s"])
        self.row = h
        self.commands = []                # the visible buttons that count toward MAX
        self._n = 0
        self.main = None
        self.more_menu = QMenu(self)
        self.export_menu = QMenu(self)
        self.b_more = D.button("More", None, None, "Everything else this screen does")
        self.b_more.setMenu(self.more_menu)
        self.b_export = D.button("Export", None, None, "Every file this screen makes")
        self.b_export.setMenu(self.export_menu)
        self.b_more.setVisible(False); self.b_export.setVisible(False)
        h.addWidget(self.b_more); h.addWidget(self.b_export)
        h.addStretch(1)

    def add(self, text, fn, tip=""):
        """A command in the bar (before More and Export)."""
        b = D.button(text, None, fn, tip)
        self.row.insertWidget(self._n, b)
        self._n += 1
        self.commands.append(b)
        return b

    def add_menu(self, text, tip=""):
        """A command that opens a menu of its own (+ Add): one command in the bar. Returns the menu."""
        b = D.button(text, None, None, tip)
        m = QMenu(b); m.setToolTipsVisible(True); b.setMenu(m)
        self.row.insertWidget(self._n, b)
        self._n += 1
        self.commands.append(b)
        return m

    def primary(self, text, fn, tip=""):
        """The screen's one main button, on the right."""
        b = D.button(text, "primary", fn, tip)
        self.row.addWidget(b)
        self.main = b
        self.commands.append(b)
        return b

    def more(self, text, fn=None, tip="", checkable=False):
        a = self.more_menu.addAction(text)
        if tip:
            a.setToolTip(tip)
        a.setCheckable(checkable)
        if fn is not None and checkable:
            a.toggled.connect(fn)
        elif fn is not None:
            a.triggered.connect(lambda *_x: fn())
        self.more_menu.setToolTipsVisible(True)
        self.b_more.setVisible(True)
        return a

    def more_sep(self):
        self.more_menu.addSeparator()

    def export(self, text, fn, tip=""):
        a = self.export_menu.addAction(text)
        if tip:
            a.setToolTip(tip)
        a.triggered.connect(lambda *_x: fn())
        self.export_menu.setToolTipsVisible(True)
        self.b_export.setVisible(True)
        return a

    def action(self, text):
        """A More or Export item by its words (tests, and the Guide)."""
        for m in (self.more_menu, self.export_menu):
            for a in m.actions():
                if a.text() == text:
                    return a
        return None

    def visible_commands(self):
        return [b for b in self.commands if b.isVisibleTo(self)]

    def labels(self):
        return [b.text() for b in self.commands] + [a.text() for a in self.more_menu.actions() if a.text()] + \
               [a.text() for a in self.export_menu.actions() if a.text()]
