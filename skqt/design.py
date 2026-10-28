"""Stationkeeper's design system for the Qt edition (2.60.0): one set of colors, type, spacing and controls for every
screen, in light and dark (following Windows), so each area that moves to Qt looks finished and alike.

Tokens
- Color: a navy-and-slate neutral with a signal-blue accent (the look of a flight-operations console, not a web app),
  and fixed meaning colors used the same way everywhere: requirement green, context blue, customer's violet, heading
  slate; ok green, warning amber, critical red. Text on every surface meets WCAG 2.1 AA contrast (checked in tests).
- Type: Segoe UI for the interface, Segoe UI Semibold for titles, Cascadia Mono (else Consolas) for IDs and references.
- Spacing: 4, 8, 12, 16, 24, 32. Radius: 6 for controls, 10 for cards, 12 for chips and pills.
Components: Card, Pill, Chip, SectionTitle, EmptyState, Toast, Tile, StackBar (2.62.0), and button kinds (primary, secondary, ghost, danger,
plus decision buttons) set with the "kind" property. Rules only (No AI); nothing leaves the PC.
"""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QToolButton,
                               QVBoxLayout, QWidget)

SPACE = {"xs": 4, "s": 8, "m": 12, "l": 16, "xl": 24, "xxl": 32}
RADIUS = {"control": 6, "card": 10, "chip": 12}
UI_FONT, MONO_FONT = "Segoe UI", "Cascadia Mono"
TYPE = {"display": 18, "title": 13, "body": 10, "small": 9, "label": 8}   # points

LIGHT = {
    "bg": "#EEF2F7", "surface": "#FFFFFF", "surface2": "#F6F8FB", "border": "#D3DBE6", "border_strong": "#AEB9C9",
    "text": "#0E1A2B", "muted": "#4E5D71", "faint": "#66748A",
    "accent": "#1F5FAD", "accent_hover": "#184E90", "accent_fg": "#FFFFFF", "accent_soft": "#E2ECF8",
    "rail": "#0F1E33", "rail_text": "#C7D3E3", "rail_active": "#1F5FAD", "rail_active_text": "#FFFFFF",
    "ok": "#146C36", "ok_soft": "#DCF3E4", "warn": "#9A4508", "warn_soft": "#FCEFD9", "crit": "#B91C1C", "crit_soft": "#FBE2E2",
    "req": "#146C36", "req_soft": "#DCF3E4", "ctx": "#1D4ED8", "ctx_soft": "#DFE8FB", "cust": "#7E22CE", "cust_soft": "#EFE1FA",
    "head": "#334155", "head_soft": "#E5E9EF", "focus": "#2E7BE0", "page": "#DCE3EC",
}
DARK = {
    "bg": "#0B1220", "surface": "#121B2C", "surface2": "#172235", "border": "#26344B", "border_strong": "#3A4B66",
    "text": "#E6ECF5", "muted": "#A3B1C4", "faint": "#8796AB",
    "accent": "#5B9BEB", "accent_hover": "#76ADF0", "accent_fg": "#06101F", "accent_soft": "#1A2C47",
    "rail": "#070D18", "rail_text": "#AFC0D6", "rail_active": "#2A5FA3", "rail_active_text": "#FFFFFF",
    "ok": "#4ADE80", "ok_soft": "#123323", "warn": "#FBBF24", "warn_soft": "#3A2A0B", "crit": "#F87171", "crit_soft": "#3B1414",
    "req": "#4ADE80", "req_soft": "#133524", "ctx": "#7FA8F5", "ctx_soft": "#172A4D", "cust": "#C59AF5", "cust_soft": "#2C1A44",
    "head": "#B3C0D2", "head_soft": "#1E293B", "focus": "#76ADF0", "page": "#1A2436",
}
# what each decision is called and how it is tagged in the page margin (colors come from the tokens)
DECISIONS = {"Keep": ("req", "Compliance requirement", "REQ"), "Context": ("ctx", "Supporting context", "SUPPORTS"),
             "Customer": ("cust", "The customer's (identified, not answered)", "CUSTOMER'S"),
             "Heading": ("head", "RFP heading", ""), "": ("faint", "Not used (not assigned)", "")}
# box colors on the white page: the same meaning colors, chosen to read on paper in both themes
PAGE_DEC = {"Keep": "#16A34A", "Context": "#2563EB", "Customer": "#7E22CE", "Heading": "#334155", "": "#94A3B8"}

_current = {"t": LIGHT, "dark": False}


def tokens():
    return _current["t"]


def is_dark():
    return _current["dark"]


def color(name):
    return QColor(tokens()[name])


def decision(dec):
    """(token name, label, margin tag) of a decision."""
    return DECISIONS.get(dec, DECISIONS[""])


# ------------------------------------------------------------------ contrast (WCAG 2.1)
def _lum(hexcolor):
    h = hexcolor.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ------------------------------------------------------------------ the style
def qss(t):
    r = RADIUS
    return f"""
* {{ font-family: "{UI_FONT}"; font-size: {TYPE['body']}pt; }}
QWidget {{ color: {t['text']}; }}
QMainWindow, QDialog, QWidget#page {{ background: {t['bg']}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']}; padding: 4px 6px; }}
QLabel[role="display"] {{ font-size: {TYPE['display']}pt; font-weight: 600; }}
QLabel[role="title"] {{ font-size: {TYPE['title']}pt; font-weight: 600; }}
QLabel[role="label"] {{ font-size: {TYPE['label']}pt; font-weight: 600; color: {t['muted']}; letter-spacing: 0.6px; }}
QLabel[role="muted"] {{ color: {t['muted']}; }}
QLabel[role="mono"] {{ font-family: "{MONO_FONT}", Consolas, monospace; font-size: {TYPE['small']}pt; color: {t['muted']}; }}
QLabel[role="reading"] {{ font-family: Georgia, "Times New Roman", serif; font-size: 12pt; }}
QFrame[card="true"] {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: {r['card']}px; }}
QFrame[card="true"] QLabel {{ background: transparent; }}
QFrame[bar="true"] {{ background: {t['surface']}; border-bottom: 1px solid {t['border']}; }}
QPushButton {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border_strong']}; border-radius: {r['control']}px;
              padding: 5px 12px; min-height: 18px; }}
QPushButton:hover {{ border-color: {t['accent']}; }}
QPushButton:focus {{ border: 2px solid {t['focus']}; }}
QPushButton:disabled {{ color: {t['faint']}; border-color: {t['border']}; }}
QPushButton[kind="primary"] {{ background: {t['accent']}; color: {t['accent_fg']}; border: 1px solid {t['accent']}; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: {t['accent_hover']}; }}
QPushButton[kind="ghost"] {{ background: transparent; border: 1px solid transparent; color: {t['accent']}; }}
QPushButton[kind="ghost"]:hover {{ background: {t['accent_soft']}; }}
QPushButton[kind="danger"] {{ color: {t['crit']}; border-color: {t['crit']}; }}
QPushButton[kind="req"] {{ background: {t['req_soft']}; color: {t['req']}; border: 1px solid {t['req']}; font-weight: 600; }}
QPushButton[kind="ctx"] {{ background: {t['ctx_soft']}; color: {t['ctx']}; border: 1px solid {t['ctx']}; font-weight: 600; }}
QPushButton[kind="cust"] {{ background: {t['cust_soft']}; color: {t['cust']}; border: 1px solid {t['cust']}; font-weight: 600; }}
QPushButton#rail {{ background: transparent; color: {t['rail_text']}; border: none; border-radius: {r['control']}px; text-align: left;
                    padding: 8px 12px; font-weight: 600; }}
QPushButton#rail:hover {{ background: rgba(255,255,255,0.07); }}
QPushButton#rail:checked {{ background: {t['rail_active']}; color: {t['rail_active_text']}; }}
QPushButton#rail:disabled {{ color: #5E6E84; }}
QWidget#railbox {{ background: {t['rail']}; }}
QLabel#railhead {{ color: #7F91AA; font-size: {TYPE['label']}pt; font-weight: 600; letter-spacing: 0.8px; padding: 10px 12px 2px 12px; }}
QLabel#brand {{ color: #FFFFFF; font-size: {TYPE['title']}pt; font-weight: 600; padding: 14px 12px 8px 12px; }}
QLineEdit, QPlainTextEdit, QComboBox {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border_strong']};
                                       border-radius: {r['control']}px; padding: 4px 8px; selection-background-color: {t['accent']}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 2px solid {t['focus']}; }}
QComboBox QAbstractItemView {{ background: {t['surface']}; color: {t['text']}; selection-background-color: {t['accent_soft']};
                              selection-color: {t['text']}; border: 1px solid {t['border']}; }}
QTreeWidget, QTreeView, QTableView, QListWidget {{ background: {t['surface']}; alternate-background-color: {t['surface2']};
       border: 1px solid {t['border']}; border-radius: {r['card']}px; selection-background-color: {t['accent_soft']};
       selection-color: {t['text']}; }}
QHeaderView::section {{ background: {t['surface2']}; color: {t['muted']}; border: none; border-bottom: 1px solid {t['border']};
                        padding: 6px 8px; font-weight: 600; font-size: {TYPE['small']}pt; }}
QSplitter::handle {{ background: {t['border']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QStatusBar {{ background: {t['surface']}; color: {t['muted']}; border-top: 1px solid {t['border']}; }}
QCheckBox, QRadioButton {{ spacing: 8px; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['border_strong']}; border-radius: 4px; min-height: 30px; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {t['border_strong']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QLabel#toast {{ background: {t['text']}; color: {t['surface']}; border-radius: 8px; padding: 9px 14px; font-weight: 600; }}
"""


def apply(app):
    """Light or dark from Windows; the palette and the style for the whole app. Returns True for dark."""
    app.setStyle("Fusion")
    import os
    want = os.environ.get("SK_THEME", "").lower()          # light or dark by choice; else Windows decides
    dark = False
    try:
        dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        dark = False
    if want in ("light", "dark"):
        dark = want == "dark"
    t = DARK if dark else LIGHT
    _current.update(t=t, dark=dark)
    pal = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.WindowText, "text"), (QPalette.Base, "surface"),
                      (QPalette.AlternateBase, "surface2"), (QPalette.Text, "text"), (QPalette.Button, "surface"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "accent"), (QPalette.HighlightedText, "accent_fg"),
                      (QPalette.ToolTipBase, "surface"), (QPalette.ToolTipText, "text"), (QPalette.Link, "accent"),
                      (QPalette.PlaceholderText, "faint"), (QPalette.Mid, "border")):
        pal.setColor(role, QColor(t[key]))
    app.setPalette(pal)
    f = QFont(UI_FONT, TYPE["body"])
    app.setFont(f)
    app.setStyleSheet(qss(t))
    return dark


# ------------------------------------------------------------------ components
def label(text, role=None, wrap=True):
    l = QLabel(text)
    if role:
        l.setProperty("role", role)
    l.setWordWrap(wrap)
    return l


def button(text, kind=None, on_click=None, tip=""):
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if on_click:
        b.clicked.connect(on_click)
    if tip:
        b.setToolTip(tip)
    return b


class Card(QFrame):
    """A surface with a title (and an optional subtitle and actions on the right); add content to .body."""

    def __init__(self, title="", subtitle="", actions=()):
        super().__init__()
        self.setProperty("card", True)
        v = QVBoxLayout(self)
        v.setContentsMargins(SPACE["l"], SPACE["m"], SPACE["l"], SPACE["l"])
        v.setSpacing(SPACE["s"])
        if title or actions:
            h = QHBoxLayout(); h.setSpacing(SPACE["s"])
            col = QVBoxLayout(); col.setSpacing(0)
            if title:
                self.title = label(title, "title", wrap=False); col.addWidget(self.title)
            if subtitle:
                self.subtitle = label(subtitle, "muted"); col.addWidget(self.subtitle)
            h.addLayout(col, 1)
            for a in actions:
                h.addWidget(a)
            v.addLayout(h)
        self.body = QVBoxLayout()
        self.body.setSpacing(SPACE["s"])
        v.addLayout(self.body)

    def add(self, w):
        self.body.addWidget(w)
        return w


class Pill(QLabel):
    """A short state in its meaning color: tone is a token pair (req, ctx, cust, head, ok, warn, crit, accent)."""

    def __init__(self, text, tone="accent"):
        super().__init__(text)
        self.set_tone(tone)

    def set_tone(self, tone):
        t = tokens()
        fg = t.get(tone, t["accent"])
        bg = t.get(tone + "_soft", t["accent_soft"])
        self.setStyleSheet(f"background:{bg};color:{fg};border-radius:{RADIUS['chip']}px;padding:2px 10px;"
                           f"font-weight:600;font-size:{TYPE['small']}pt;")


class Chip(QFrame):
    """A removable item (a section a requirement is in, a requirement a support sentence backs up)."""

    def __init__(self, text, tone="req", on_remove=None, on_jump=None, remove_tip="Take it out"):
        super().__init__()
        t = tokens()
        self.setObjectName("chip")
        self.setStyleSheet(f"QFrame#chip{{background:{t.get(tone + '_soft', t['accent_soft'])};border-radius:{RADIUS['chip']}px;"
                           f"border:1px solid {t.get(tone, t['accent'])};}} QLabel{{background:transparent;color:{t['text']};}}"
                           f"QToolButton{{border:none;background:transparent;color:{t['muted']};font-weight:600;padding:0 4px;}}"
                           f"QToolButton:hover{{color:{t['crit']};}}")
        h = QHBoxLayout(self)
        h.setContentsMargins(SPACE["m"], 2, SPACE["xs"], 2)
        self.label = QLabel(text)
        h.addWidget(self.label, 1)
        self.jump = self.remove = None
        if on_jump:
            self.jump = QToolButton(text="Jump"); self.jump.clicked.connect(on_jump); h.addWidget(self.jump)
        if on_remove:
            self.remove = QToolButton(text="×"); self.remove.setToolTip(remove_tip)
            self.remove.clicked.connect(on_remove); h.addWidget(self.remove)


class SectionTitle(QLabel):
    def __init__(self, text):
        super().__init__(text.upper())
        self.setProperty("role", "label")


class EmptyState(QFrame):
    """What goes here, and the one action that fills it."""

    def __init__(self, title, body, action_text="", on_action=None):
        super().__init__()
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(SPACE["s"])
        t = label(title, "title", wrap=False); t.setAlignment(Qt.AlignCenter); v.addWidget(t)
        b = label(body, "muted"); b.setAlignment(Qt.AlignCenter); b.setFixedWidth(440)
        b.setMinimumHeight(b.heightForWidth(440) + 4)               # a wrapped line is never cut off
        v.addWidget(b, 0, Qt.AlignCenter)
        if action_text and on_action:
            v.addWidget(button(action_text, "primary", on_action), 0, Qt.AlignCenter)


class Toast(QLabel):
    """A short confirmation over the bottom of a window that fades away ("Saved", "3 sentences: not used")."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.hide()
        self.eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.eff)
        self.anim = QPropertyAnimation(self.eff, b"opacity", self)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.timer = QTimer(self, singleShot=True, timeout=self._fade)

    def show_text(self, text, ms=2600):
        self.setText(text)
        self.adjustSize()
        p = self.parentWidget()
        self.move(max(12, (p.width() - self.width()) // 2), p.height() - self.height() - 46)
        self.anim.stop()
        self.eff.setOpacity(1.0)
        self.show()
        self.raise_()
        self.timer.start(ms)

    def _fade(self):
        self.anim.setDuration(350)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self.anim.start()


class Tile(QFrame):
    """2.62.0: one number that matters, with what it counts, in its meaning color; clickable when it leads somewhere."""

    def __init__(self, value="", caption="", tone="accent", on_click=None, tip=""):
        super().__init__()
        self.setObjectName("tile")
        self.on_click = on_click
        v = QVBoxLayout(self)
        v.setContentsMargins(SPACE["l"], SPACE["m"], SPACE["l"], SPACE["m"])
        v.setSpacing(2)
        self.value = QLabel(str(value)); self.caption = QLabel(caption); self.caption.setWordWrap(True)
        v.addWidget(self.value); v.addWidget(self.caption)
        if on_click:
            self.setCursor(Qt.PointingHandCursor)
        if tip:
            self.setToolTip(tip)
        self.set(value, caption, tone)

    def set(self, value, caption=None, tone=None):
        t = tokens()
        self.tone = tone or getattr(self, "tone", "accent")
        fg = t.get(self.tone, t["accent"])
        self.value.setText(str(value))
        if caption is not None:
            self.caption.setText(caption)
        self.setStyleSheet(f"QFrame#tile{{background:{t['surface']};border:1px solid {t['border']};border-left:4px solid {fg};"
                           f"border-radius:{RADIUS['card']}px;}} QLabel{{background:transparent;}}")
        self.value.setStyleSheet(f"color:{fg};font-size:{TYPE['display'] + 4}pt;font-weight:600;")
        self.caption.setStyleSheet(f"color:{t['muted']};font-size:{TYPE['small']}pt;font-weight:600;")

    def mouseReleaseEvent(self, e):
        if self.on_click and e.button() == Qt.LeftButton:
            self.on_click()
        super().mouseReleaseEvent(e)


class StackBar(QWidget):
    """2.62.0: parts of a whole as one rounded bar: segments [(count, token, label)], with a legend under it."""

    def __init__(self, height=14):
        super().__init__()
        self.segments = []
        self.bar_h = height
        self.setMinimumHeight(height + 2)
        self.setMinimumWidth(120)

    def set(self, segments):
        self.segments = [(max(0, int(n or 0)), tok, lab) for n, tok, lab in segments]
        total = sum(n for n, _t, _l in self.segments)
        self.setToolTip("\n".join(f"{lab}: {n}" for n, _t, lab in self.segments if n) if total else "")
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = tokens()
        w, h = self.width(), self.bar_h
        y = (self.height() - h) / 2
        clip = QPainterPath(); clip.addRoundedRect(0, y, w, h, h / 2, h / 2)
        p.setClipPath(clip)
        p.fillRect(0, int(y), w, h, QColor(t["surface2"]))
        total = sum(n for n, _t, _l in self.segments)
        x = 0.0
        for n, tok, _lab in self.segments:
            if not n or not total:
                continue
            seg = w * n / total
            p.fillRect(int(x), int(y), int(round(x + seg)) - int(x), h, QColor(t.get(tok, t["accent"])))
            x += seg
        p.end()


def legend(segments):
    """A row of colored marks and labels for a StackBar ("Placed 41", "Not placed 3")."""
    w = QWidget()
    h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(SPACE["l"])
    t = tokens()
    for n, tok, lab in segments:
        l = QLabel(f"<span style='color:{t.get(tok, t['accent'])}'>\u25a0</span> {lab} {n}")
        l.setStyleSheet(f"color:{t['muted']};font-size:{TYPE['small']}pt;background:transparent;")
        h.addWidget(l)
    h.addStretch(1)
    return w
