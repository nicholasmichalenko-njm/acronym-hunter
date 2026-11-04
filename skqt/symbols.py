"""Symbols (3.50.0; brings back the classic window's symbol picker, retired in 3.14.0): Greek letters, subscripts,
superscripts, math operators, accents, units and arrows, inserted straight into the box you are typing in, so a term is
defined exactly as written (H₂O, m², ṁ, Δv, µm, Ω).

    from skqt import symbols
    symbols.attach(edit)          # right-click: Symbols..., make the selection subscript, superscript or normal; Ctrl+Shift+Space
    symbols.button(edit)          # a small button that opens the picker for that box

One floating window serves every attached box: it inserts into the box that had the cursor last, so it can stay open
while you define several terms. Accents attach to the letter before the cursor (m + dot above makes ṁ). The Recent row
is kept on this PC (<config>\\symbol_recent.json). Rules only; nothing leaves the PC."""
import json
import os
import unicodedata

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea,
                               QTabBar, QTextEdit, QToolButton, QVBoxLayout, QWidget)

import diag

SUB_FROM, SUB_TO = "0123456789+-=()aehijklmnoprstuvxβγρφχ", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓᵦᵧᵨᵩᵪ"
SUP_FROM = "0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVW"
SUP_TO = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ"
SUB = str.maketrans(SUB_FROM, SUB_TO)
SUP = str.maketrans(SUP_FROM, SUP_TO)
UNSUB = dict(zip(SUB_TO, SUB_FROM))
UNSUP = dict(zip(SUP_TO, SUP_FROM))
ACCENTS = [("̇", "dot above (ṁ, ẋ: rate)"), ("̈", "two dots (ẍ: second derivative)"), ("̄", "bar (x̄: mean)"),
           ("̂", "hat (x̂: unit vector, estimate)"), ("̃", "tilde (x̃)"), ("⃗", "vector arrow (v⃗)"),
           ("̅", "overline (long bar)"), ("̲", "underline"), ("̸", "slash through (negation)"),
           ("′", "prime (not combining)"), ("″", "double prime"), ("‴", "triple prime")]
TABS = {
    "Greek": "αβγδεζηθϑικλμνξοπϖρϱσςτυφϕχψω" "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ",
    "Sub x₂": SUB_TO,
    "Sup x²": SUP_TO,
    "Math": "±∓×÷·∙∘√∛∜∞∝∂∇∆∫∬∮∑∏∐′″≈≃≅≡≠≤≥≪≫≲≳∼∠∡⊥∥∦⌀°%‰‱⁄",
    "Accents": "".join(c for c, _ in ACCENTS),
    "Units": "µΩ℧Å℃℉㎛㎜㎝㎞㎏㎎㎐㎑㎒㎓㎾㎿ℓ℔№½⅓⅔¼¾⅛⅜⅝⅞⅕",
    "Arrows": "→←↑↓↔↕⇒⇐⇔↦⟶⟹∈∉∋⊂⊃⊆⊇∪∩∅∀∃∄∧∨¬⊕⊗⊙ℝℕℤℚℂℏℓ∴∵",
}
ALIASES = {"ṁ": "m dot mass flow", "Δ": "delta change", "Ω": "ohm omega", "µ": "micro mu", "°": "degree", "√": "root sqrt",
           "∞": "infinity", "∂": "partial derivative", "∇": "nabla gradient del", "∑": "sum sigma", "∫": "integral",
           "±": "plus minus", "×": "times multiply cross", "·": "dot multiply middle", "≈": "approx about", "≠": "not equal",
           "≤": "less equal", "≥": "greater equal", "∝": "proportional", "→": "arrow right yields", "ℓ": "liter script l",
           "Å": "angstrom", "℃": "celsius", "℉": "fahrenheit", "‰": "per mille", "′": "prime minute foot", "″": "double prime second inch"}
_recent = []
_targets = []           # attached boxes, the one with the cursor last first
_win = [None]
_loaded = [False]


def _recent_file():
    try:
        import app_gui as A
        return os.path.join(A.CONFIG_DIR, "symbol_recent.json")
    except Exception:  # noqa: BLE001
        return ""


def _load_recent():
    if _loaded[0]:
        return
    _loaded[0] = True
    try:
        with open(_recent_file(), encoding="utf-8") as f:
            _recent[:] = [c for c in json.load(f) if isinstance(c, str) and len(c) == 1][:24]
    except (OSError, ValueError):
        pass


def _remember(ch):
    if len(ch) != 1:
        return
    _load_recent()
    if ch in _recent:
        _recent.remove(ch)
    _recent.insert(0, ch)
    del _recent[24:]
    try:
        with open(_recent_file(), "w", encoding="utf-8") as f:
            json.dump(_recent, f, ensure_ascii=False)
    except OSError:
        diag.swallowed()


def is_combining(c):
    return len(c) == 1 and unicodedata.combining(c) > 0


def converted(seg, kind):
    """seg as subscript ('sub'), superscript ('sup') or normal text ('normal'); characters with no such form stay."""
    if kind == "sub":
        return seg.translate(SUB)
    if kind == "sup":
        return seg.translate(SUP)
    return "".join(UNSUB.get(c, UNSUP.get(c, c)) for c in seg)


def names_of(ch):
    try:
        n = unicodedata.name(ch).lower()
    except ValueError:
        n = ""
    return n + " " + ALIASES.get(ch, "")


def search(words):
    """Every symbol whose Unicode name or alias holds all the words ('sub 2', 'sigma', 'degree')."""
    pool = "".join(dict.fromkeys("".join(TABS.values())))
    num = dict(zip("0123456789", ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")))
    ws = [num.get(w, w) for w in (words or "").lower().replace("sub ", "subscript ").replace("sup ", "superscript ").split()]
    return [c for c in pool if ws and all(w in names_of(c) for w in ws)]


# ------------------------------------------------------------------ the boxes
def _target():
    for e in list(_targets):
        try:
            e.objectName()                               # raises when the box is gone
            return e
        except RuntimeError:
            _targets.remove(e)
    return None


def insert(ch, edit=None):
    """Inserts ch at the cursor (over a selection). An accent attaches to the letter before it (m + dot above: ṁ)."""
    e = edit or _target()
    if e is None:
        return False
    if isinstance(e, QLineEdit):
        if e.isReadOnly():
            return False
        e.insert(ch)
        pos, text = e.cursorPosition(), e.text()
        comp = unicodedata.normalize("NFC", text)
        if comp != text:
            e.setText(comp); e.setCursorPosition(len(unicodedata.normalize("NFC", text[:pos])))
    elif isinstance(e, (QPlainTextEdit, QTextEdit)):
        if e.isReadOnly():
            return False
        c = e.textCursor(); c.insertText(ch); e.setTextCursor(c)
    else:
        return False
    e.setFocus()
    _remember(ch)
    return True


def convert(kind, edit=None):
    """The selection (or the character before the cursor) as subscript, superscript or normal text."""
    e = edit or _target()
    if e is None:
        return False
    if isinstance(e, QLineEdit):
        if e.hasSelectedText():
            a, seg = e.selectionStart(), e.selectedText()
        else:
            b = e.cursorPosition(); a = max(0, b - 1); seg = e.text()[a:b]
        if not seg:
            return False
        new = converted(seg, kind)
        e.setText(e.text()[:a] + new + e.text()[a + len(seg):]); e.setCursorPosition(a + len(new))
    elif isinstance(e, (QPlainTextEdit, QTextEdit)):
        c = e.textCursor()
        if not c.hasSelection():
            c.movePosition(c.MoveOperation.Left, c.MoveMode.KeepAnchor)
        seg = c.selectedText()
        if not seg:
            return False
        c.insertText(converted(seg, kind)); e.setTextCursor(c)
    e.setFocus()
    return True


class _Watch(QObject):
    """Focus tracking and the right-click menu for an attached box."""
    def __init__(self, edit):
        super().__init__(edit)
        self.edit = edit

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.FocusIn:
            _focused(self.edit)
        elif ev.type() == QEvent.ContextMenu:
            _focused(self.edit)
            m = self.edit.createStandardContextMenu()
            first = m.actions()[0] if m.actions() else None
            for text, fn in (("Symbols... (Ctrl+Shift+Space)", lambda: open_picker(self.edit)),
                             ("Make the selection subscript", lambda: convert("sub", self.edit)),
                             ("Make the selection superscript", lambda: convert("sup", self.edit)),
                             ("Make the selection normal text", lambda: convert("normal", self.edit))):
                a = m.addAction(text); a.triggered.connect(fn)
                if first is not None:
                    m.removeAction(a); m.insertAction(first, a)
            if first is not None:
                m.insertSeparator(first)
            m.exec(ev.globalPos())
            return True
        return False


def _focused(edit):
    if edit in _targets:
        _targets.remove(edit)
    _targets.insert(0, edit)


def attach(edit):
    """Makes a box a target of the picker: right-click menu, Ctrl+Shift+Space. Returns the box."""
    if getattr(edit, "_sk_symbols", False):
        return edit
    edit._sk_symbols = True
    edit.installEventFilter(_Watch(edit))
    sc = QShortcut(QKeySequence("Ctrl+Shift+Space"), edit)
    sc.setContext(Qt.WidgetShortcut)
    sc.activated.connect(lambda: (_focused(edit), open_picker(edit)))
    return edit


def button(edit, text="Ω Symbols"):
    """A small button that opens the picker for this box."""
    attach(edit)
    b = QToolButton(); b.setText(text)
    b.setToolTip("Greek letters, subscripts, superscripts, math, accents and units for this box (Ctrl+Shift+Space)")
    b.clicked.connect(lambda: (_focused(edit), open_picker(edit)))
    return b


# ------------------------------------------------------------------ the picker
class SymbolPicker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Symbols")
        self.setWindowFlag(Qt.Tool, True); self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setModal(False)
        self.resize(560, 480)
        v = QVBoxLayout(self)
        top = QHBoxLayout(); v.addLayout(top)
        self.q = QLineEdit(); self.q.setPlaceholderText("Search: sigma, dot, sub 2, degree..."); self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(lambda _t: self.draw())
        top.addWidget(self.q, 1)
        for text, kind in (("Sub x₂", "sub"), ("Sup x²", "sup"), ("Normal", "normal")):
            b = QPushButton(text); b.setToolTip(f"Make the selection in the box {'normal text' if kind == 'normal' else kind + 'script'}")
            b.clicked.connect(lambda _c=False, k=kind: convert(k))
            top.addWidget(b)
        self.tabs = QTabBar(); self.tabs.setExpanding(False)
        for t in ["Recent"] + list(TABS):
            self.tabs.addTab(t)
        self.tabs.currentChanged.connect(lambda _i: self.draw())
        v.addWidget(self.tabs)
        from . import design as D
        v.addWidget(D.label("Click to insert into the box you were typing in. Accents attach to the letter before the cursor.", "muted"))
        self.area = QScrollArea(); self.area.setWidgetResizable(True); v.addWidget(self.area, 1)
        self.status = D.label("", "muted"); v.addWidget(self.status)
        _load_recent()
        self.tabs.setCurrentIndex(0 if _recent else 1)
        self.buttons = []
        self.draw()

    def chars(self):
        if self.q.text().strip():
            return search(self.q.text())
        t = self.tabs.tabText(self.tabs.currentIndex())
        return list(_recent) if t == "Recent" else list(TABS.get(t, ""))

    def draw(self):
        w = QWidget(); g = QGridLayout(w); g.setSpacing(3)
        self.buttons = []
        acc = dict(ACCENTS)
        f = QFont("Cambria"); f.setPointSize(15)
        for i, c in enumerate(self.chars()[:240]):
            b = QPushButton(("◌" + c) if is_combining(c) else c); b.setFont(f); b.setFixedSize(42, 38)
            tip = acc.get(c) or unicodedata.name(c, "").title()
            b.setToolTip(tip)
            b.clicked.connect(lambda _c=False, ch=c, t=tip: (insert(ch), self.status.setText(f"{ch}  {t}")))
            g.addWidget(b, i // 11, i % 11)
            self.buttons.append((c, b))
        if not self.buttons:
            from . import design as D
            g.addWidget(D.label("Nothing here yet." if not self.q.text() else "No match.", "muted"), 0, 0)
        g.setRowStretch(g.rowCount(), 1); g.setColumnStretch(11, 1)
        self.area.setWidget(w)


def open_picker(anchor=None):
    """Opens the picker (or brings it forward). Returns it."""
    if _win[0] is not None:
        try:
            _win[0].show(); _win[0].raise_(); _win[0].activateWindow()
            return _win[0]
        except RuntimeError:
            _win[0] = None
    p = SymbolPicker(anchor.window() if anchor is not None else None)
    if anchor is not None:
        try:
            pt = anchor.mapToGlobal(anchor.rect().bottomLeft())
            p.move(pt.x(), pt.y() + 8)
        except RuntimeError:
            pass
    _win[0] = p
    p.show()
    diag.activity("symbols_opened")
    return p


def ask_text(parent, title, label, text=""):
    """A box to type into with the Symbols button beside it (in place of a plain text question). Returns (text, ok)."""
    from PySide6.QtWidgets import QDialogButtonBox
    from . import design as D
    d = QDialog(parent); d.setWindowTitle(title); d.resize(560, 140)
    v = QVBoxLayout(d)
    v.addWidget(D.label(label))
    row = QHBoxLayout(); v.addLayout(row)
    e = QLineEdit(text); row.addWidget(e, 1); row.addWidget(button(e))
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
    v.addWidget(bb)
    e.setFocus()
    ok = d.exec() == QDialog.Accepted
    return e.text(), ok
