"""Insert a field (3.48.0): a menu of the fields a header, footer or cover line can hold, in plain words, so nobody types
{a_number} or {solicitation} from memory. Picking one puts its token where the cursor is in the last box used, or
hands it to a function (the header and footer builder adds it to the line chosen). The standard's own fill-ins are
listed too. The tokens are what the template maker turns into fields (prodengine/pe/hf.py)."""
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QLineEdit, QMenu, QToolButton

# the page fields first, then Rule 7's, then the volume values and the standard's fill-ins
PAGE_FIELDS = (("page", "Page number"), ("pages", "Pages in this section"), ("chapter", "Chapter title (Heading 1)"))
RULE7_FIELDS = (("a_number", "A number (Rule 7)"), ("marking", "Restriction marking"), ("team_line", "The team's line (Rule 7)"))


def choices(std=None):
    """[(token, words)] every field a line may hold, the standard's fill-ins included."""
    out = list(PAGE_FIELDS) + list(RULE7_FIELDS)
    try:
        import fillins as FI
        out += [(k, v) for k, v in FI.tokens(std or {}).items() if k not in dict(out)]
    except Exception:  # noqa: BLE001  the page and Rule 7 fields still list
        import diag
        diag.swallowed()
    return out


class _Focus(QObject):
    def __init__(self, button):
        super().__init__(button)
        self.button = button

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.FocusIn:
            self.button.last = obj
        return False


class FieldButton(QToolButton):
    """Insert a field: std_of() gives the standard (for its fill-ins); edits are the boxes it may type into (the last one
    used gets the field); on_pick(token), when given, takes the field instead."""
    def __init__(self, std_of=None, edits=(), on_pick=None, text="Insert a field"):
        super().__init__()
        self.std_of, self.on_pick, self.last = std_of, on_pick, None
        self.setText(text)
        self.setToolTip("Put a field where the cursor is: page number, A number, marking, volume values, your fill-ins")
        self.setPopupMode(QToolButton.InstantPopup)
        self.menu_ = QMenu(self)
        self.setMenu(self.menu_)
        self.menu_.aboutToShow.connect(self.fill)
        self._focus = _Focus(self)
        self.edits = []
        for e in edits:
            self.track(e)

    def track(self, edit):
        self.edits.append(edit)
        edit.installEventFilter(self._focus)
        if self.last is None:
            self.last = edit

    def fill(self):
        self.menu_.clear()
        std = self.std_of() if self.std_of else {}
        groups = [PAGE_FIELDS, RULE7_FIELDS]
        listed = {k for g in groups for k, _t in g}
        rest = [(k, t) for k, t in choices(std) if k not in listed]
        for g in groups + ([rest] if rest else []):
            for k, t in g:
                a = self.menu_.addAction(t)
                a.setToolTip("{" + k + "}")
                a.triggered.connect(lambda _=False, tok=k: self.pick(tok))
            self.menu_.addSeparator()

    def pick(self, token):
        text = "{" + token + "}"
        if self.on_pick is not None:
            self.on_pick(token)
            return text
        e = self.last
        if isinstance(e, QLineEdit):
            e.insert(text)
            e.editingFinished.emit()
        return text
