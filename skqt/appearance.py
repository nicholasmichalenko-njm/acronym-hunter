"""Settings > Appearance (3.91.0): Follow Windows, Light or Dark, kept on this PC (settings "appearance") and used at
once. The customer's pages and Word previews stay white in both."""
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
    page.look_note.setText(("Dark" if dark else "Light") + " now. A page you have open takes every color when you open it "
                           "again; restart Stationkeeper to see it everywhere at once.")
    return dark
