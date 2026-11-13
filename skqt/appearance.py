"""Settings > Appearance (3.91.0): Follow Windows, Light or Dark, kept on this PC (settings "appearance") and used at
once. The customer's pages and Word previews stay white in both. 4.27.3: used at once everywhere: design.apply writes
every widget's own style again (design.themed, design.retheme); the menu is one navy in light and dark."""
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout

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
    v.addWidget(page.look_card)
    return page.look_card


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
