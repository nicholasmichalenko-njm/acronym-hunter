"""Settings > Appearance (3.91.0): Follow Windows, Light or Dark, kept on this PC (settings "appearance") and used at
once. The customer's pages and Word previews stay white in both. 4.27.3: used at once everywhere: design.apply writes
every widget's own style again (design.themed, design.retheme); the menu is one navy in light and dark. 4.29.1: Colors:
Station navy, Slate and teal, or My colors (an accent, a menu color and a page color as hex values, kept on this PC),
with a line saying where text would be hard to read, and Reset (skqt/palette.py)."""
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QWidget

import diag
from . import design as D


def add_card(page, v):
    from .modes import settings
    page.look_card = D.Card("Appearance", "Light or dark. The customer's pages and Word previews stay white in both. "
                            "Yours alone, on this PC.")
    row = QHBoxLayout(); page.look_card.body.addLayout(row)
    page.look = QComboBox()
    for k, text in D.APPEARANCE:
        page.look.addItem(text, k)
    page.look.setCurrentIndex(max(0, page.look.findData((settings() or {}).get("appearance") or "windows")))
    page.look.currentIndexChanged.connect(lambda _i: page.set_look(page.look.currentData()))
    row.addWidget(page.look); row.addStretch(1)
    page.look_note = page.look_card.add(D.label("", "muted"))
    add_colors(page)
    v.addWidget(page.look_card)
    return page.look_card


def add_colors(page):
    """4.29.1: the palette, and the person's own three colors."""
    from . import palette as P
    from .modes import settings
    st = settings() or {}
    row = QHBoxLayout(); page.look_card.body.addLayout(row)
    row.addWidget(D.label("Colors", "label", wrap=False))
    page.colors = QComboBox()
    for k, text in P.CHOICES:
        page.colors.addItem(text, k)
    page.colors.setCurrentIndex(max(0, page.colors.findData(st.get("palette") or P.NAVY)))
    page.colors.currentIndexChanged.connect(lambda _i: set_colors(page, page.colors.currentData()))
    row.addWidget(page.colors)
    page.colors_reset = D.button("Reset", "ghost", lambda: reset_colors(page), "Back to Station navy; your three colors are forgotten")
    row.addWidget(page.colors_reset); row.addStretch(1)
    page.color_boxes, page.color_dots = {}, {}
    page.mine_w = QWidget()
    mr = QHBoxLayout(page.mine_w); mr.setContentsMargins(0, 0, 0, 0); mr.setSpacing(D.SPACE["s"])
    mine = st.get("brand_colors") or {}
    for key, name, what in P.FIELDS:
        dot = QLabel(); dot.setFixedSize(16, 16); page.color_dots[key] = dot
        box = QLineEdit(P.clean(mine.get(key))); box.setPlaceholderText("#RRGGBB"); box.setMaximumWidth(96); box.setToolTip(what)
        box.editingFinished.connect(lambda k=key: set_color(page, k, page.color_boxes[k].text()))
        page.color_boxes[key] = box
        mr.addWidget(D.label(name, "muted", wrap=False)); mr.addWidget(dot); mr.addWidget(box)
    mr.addStretch(1)
    page.look_card.body.addWidget(page.mine_w)
    page.colors_warn = page.look_card.add(D.label("", "muted"))
    show_colors(page)


def show_colors(page):
    """The three boxes show for My colors; each dot shows its color; the line says what is hard to read."""
    from . import palette as P
    from .modes import settings
    st = settings() or {}
    key = st.get("palette") or P.NAVY
    page.mine_w.setVisible(key == P.MINE)
    page.colors_reset.setVisible(key != P.NAVY or bool(st.get("brand_colors")))
    t = D.tokens()
    for k, box in page.color_boxes.items():
        c = P.clean(box.text())
        page.color_dots[k].setStyleSheet(f"background:{c or 'transparent'};border:1px solid {t['border_strong']};border-radius:8px")
    bad = [n for k, n, _w in P.FIELDS if page.color_boxes[k].text().strip() and not P.clean(page.color_boxes[k].text())]
    said = [f"{', '.join(bad)}: not a hex color (six digits, such as #0F6F6A); left as it was."] if bad else []
    said += P.warn(t) if key != P.NAVY else []
    page.colors_warn.setText(" ".join(said)); page.colors_warn.setVisible(bool(said))
    return said


def _use(page):
    from .modes import settings
    D.apply(QApplication.instance(), None if ((settings() or {}).get("appearance") or "windows") == "windows" else (settings() or {}).get("appearance"))
    host = getattr(page, "host", None)
    try:
        if host is not None:
            host.refresh_access()
            for w in QApplication.topLevelWidgets():
                w.update()
    except Exception:                                # noqa: BLE001
        diag.swallowed()
    return show_colors(page)


def set_colors(page, key):
    """Station navy, Slate and teal or My colors, kept and used now. Returns what is hard to read ([] when nothing)."""
    from . import palette as P
    from .modes import save
    save(palette=key if key in dict(P.CHOICES) else P.NAVY)
    diag.activity("qt_palette_set")
    return _use(page)


def set_color(page, key, value):
    """One of My colors typed: kept when it is a hex color, and used now. Returns what is hard to read."""
    from . import palette as P
    from .modes import save, settings
    mine = dict((settings() or {}).get("brand_colors") or {})
    c = P.clean(value)
    if c:
        mine[key] = c
        page.color_boxes[key].setText(c)
    elif not str(value or "").strip():
        mine.pop(key, None)
    save(brand_colors=mine)
    return _use(page)


def reset_colors(page):
    """Back to Station navy; the three colors are forgotten."""
    from . import palette as P
    from .modes import save
    save(palette=P.NAVY, brand_colors={})
    page.colors.blockSignals(True); page.colors.setCurrentIndex(page.colors.findData(P.NAVY)); page.colors.blockSignals(False)
    for box in page.color_boxes.values():
        box.setText("")
    return _use(page)


def set_look(page, key):
    """Follow Windows, Light or Dark, kept and used now. Returns True for dark."""
    from .modes import save
    key = key if key in dict(D.APPEARANCE) else "windows"
    save(appearance=key)
    dark = D.apply(QApplication.instance(), None if key == "windows" else key)
    diag.activity("qt_appearance_set")
    page.look_note.setText(("Dark" if dark else "Light") + " now, on every page. The menu keeps its navy in both.")
    host = getattr(page, "host", None)               # 4.27.3: every style written again; the page in view drawn again
    try:
        if host is not None:
            host.refresh_access()
            for w in QApplication.topLevelWidgets():
                w.update()
    except Exception:                                # noqa: BLE001  the colors are set; a redraw must not stop that
        diag.swallowed()
    return dark
