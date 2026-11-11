"""The piece pane's What it is (4.5.0; claude/stationkeeper-shred-place-plan-4.5.md, step 4): the eight types as chips
that toggle (a click puts the type on every selected piece, a second click takes it off; a piece can carry several;
Not applicable clears the rest). The suggestion shows dashed on its chip, and Enter takes it. Below them: Capture (one
menu of the captures the types do not already cover, their keys kept) and Ask a question (a customer question, citing
the piece, in the Q&A drawer). Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QHBoxLayout, QMenu, QPushButton, QWidget

import shredtypes as ST
from . import design as D

# what a suggestion's category says the piece is (suggestrules categories)
SUGGESTED = {"L": "instruction", "M": "evaluation", "SOW": "requirement", "I": "requirement", "ctx": "information",
             "cust": "information", "ignore": "not_applicable"}
COVERED = ("submit", "format", "keydate", "acronym", "question")   # the types (Rule, Date), Acros & Abs and Ask cover them


def suggested(page, it):
    """The type the suggestion gives an unsorted piece, or ""."""
    rec = (getattr(page, "sg", None) or {}).get(it.get("id"))
    if not rec or rec.get("state") != "shown" or ST._keys(it.get(ST.FIELD)) or it.get("decision"):
        return ""
    return SUGGESTED.get(rec.get("cat") or "", "")


def add(page, rows):
    """The chips and the two actions, added to the card. Returns the chips {key: button}."""
    from .adaptive import FlowLayout
    from . import shredbar as SB
    types = ST.load(page.host.config_dir)
    page.head("What it is")
    w = QWidget(); fl = FlowLayout(w, D.SPACE["xs"]); fl.setContentsMargins(0, 0, 0, 0)
    sug = suggested(page, rows[-1]) if len(rows) == 1 else ""
    page.type_chips = {}
    for key in ST.KEYS:
        t = types.get(key) or {}
        if not t.get("shown", True):
            continue
        b = QPushButton(f"{t.get('name', key)}  {t.get('short', '')}".strip()); b.setCheckable(True)
        b.setObjectName("typeChip")
        on = all(ST.has(it, key) for it in rows)
        b.setChecked(on)
        color = t.get("color") or "#64748B"
        border = f"2px dashed {color}" if key == sug else f"2px solid {color}" if on else f"1px solid {D.tokens()['border_strong']}"
        b.setStyleSheet(f"QPushButton#typeChip{{border:{border};border-radius:12px;padding:3px 10px;"
                        f"background:{D.tokens()['accent_soft'] if on else 'transparent'};font-weight:{600 if on or key == sug else 400};}}")
        b.setToolTip(("On: click to take it off" if on else "Click to put it on") + (" (suggested: Enter takes it)" if key == sug else ""))
        b.clicked.connect(lambda _c=False, k=key: SB.toggle_piece(page, k))
        fl.addWidget(b)
        page.type_chips[key] = b
    page.add(w)
    if sug:
        why = ((page.sg.get(rows[-1]["id"]) or {}).get("why") or "")
        page.sug_label = page.add(D.label(f"Suggested: {types.get(sug, {}).get('name', sug)}" + (f", {why}" if why else "")
                                          + ". Enter takes it.", "muted"))
    row = QHBoxLayout(); row.setSpacing(D.SPACE["xs"])
    cap = D.button("Capture", None, None, "Contact, objective, key point, graphic need and the effort's own captures")
    m = QMenu(cap); m.aboutToShow.connect(lambda: fill_capture(page, m)); cap.setMenu(m)
    page.capture_btn, page.capture_menu = cap, m
    row.addWidget(cap)
    page.ask_btn = D.button("Ask a question", None, lambda: ask(page), "A question for the customer about this piece, in the Q&A log")
    row.addWidget(page.ask_btn)
    row.addStretch(1)
    page.body_add_layout(row)
    return page.type_chips


def fill_capture(page, m):
    """The captures the types do not already cover: the bar's own (keys kept) and the rest (More)."""
    m.clear()
    for key, b in (getattr(page, "cap_keys", None) or {}).items():
        if key in ("more",) + COVERED:
            continue
        m.addAction(b.icon(), b.text(), b.click)
    if getattr(page, "more_actions", None) is not None:
        page.fill_more_menu()
        extra = [a for a in page.more_menu.actions()]
        if extra:
            m.addSeparator()
            for a in extra:
                if a.isSeparator():
                    m.addSeparator()
                elif not a.isCheckable():
                    m.addAction(a.icon(), a.text(), a.trigger)
    return [a.text() for a in m.actions() if not a.isSeparator()]


def ask(page):
    """Ask a question: the Question capture, which files a customer question citing the piece and opens the drawer."""
    fn = page._cap_fn("question")
    return fn() if fn else None
