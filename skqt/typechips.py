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


def pane(page, chips):
    """4.29.1 (Nicholas 2026-11-13 answer 8): the types show once. While the bar sits at the selection the pane says
    which types the piece has; the pane's own chips show only when there is no bar (the piece is off the page shown).
    4.29.3: Capture and Ask a question follow the chips. 4.29.4: a widget of a card that was drawn again has no parent
    any more; showing it would open it as a window of its own, so only widgets still in the card are touched."""
    def live(x):
        try:
            return x is not None and x.parentWidget() is not None
        except RuntimeError:             # deleted with its card
            return False
    w, say, cr = getattr(page, "type_w", None), getattr(page, "type_say", None), getattr(page, "cap_row", None)
    if live(w):
        w.setVisible(bool(chips))
    if live(say):
        say.setVisible(not chips)
    if live(cr):
        cr.setVisible(bool(chips))


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
        b = QPushButton(f"{t.get('name', key)}  {t.get('short', '')}".strip().replace("&", "&&")); b.setCheckable(True)   # 4.29.0: Format & Submission
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
    page.type_w = w
    names = [(types.get(k) or {}).get("name", k) for k in ST.KEYS if all(ST.has(it, k) for it in rows)]
    page.type_say = page.add(D.label((", ".join(names) if names else "No type yet") + ". Set on the bar at the selection.", "muted"))
    pane(page, getattr(page, "sel_bar", None) is None)        # 4.29.1: the bar at the selection holds the types
    import captureuse as CU                                  # 4.21.0: where what was said here goes
    have = [k for k in ST.KEYS if all(ST.has(it, k) for it in rows)]
    say = CU.line(have, {k: (types.get(k) or {}).get("name", k) for k in have})
    page.goes_label = page.add(D.label(say, "muted")) if say else None
    if sug:
        why = ((page.sg.get(rows[-1]["id"]) or {}).get("why") or "")
        page.sug_label = page.add(D.label(f"Suggested: {types.get(sug, {}).get('name', sug)}" + (f", {why}" if why else "")
                                          + ". Enter takes it.", "muted"))
    rule_row(page, rows, sug)
    __import__("skqt.makechecked", fromlist=["x"]).add_row(page, rows)       # 4.26.0: a typed Rule or Date, made checked
    roww = QWidget(); row = QHBoxLayout(roww); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(D.SPACE["xs"])
    cap = D.button("Capture", None, None, "Contact, objective, key point, graphic need and the effort's own captures")
    m = QMenu(cap); m.setToolTipsVisible(True); m.aboutToShow.connect(lambda: fill_capture(page, m)); cap.setMenu(m)
    page.capture_btn, page.capture_menu = cap, m
    row.addWidget(cap)
    page.ask_btn = D.button("Ask a question", None, lambda: ask(page), ASK_TIP)
    row.addWidget(page.ask_btn)
    row.addStretch(1)
    page.cap_row = page.add(roww)                        # 4.29.3: on the bar at the selection while that shows
    pane(page, getattr(page, "sel_bar", None) is None)
    __import__("skqt.piececaptures", fromlist=["x"]).add(page, rows)        # 4.12.0: its deliverable, what it gave
    __import__("skqt.shredselbar", fromlist=["x"]).later(page)              # 4.26.0: the bar at the selection follows
    __import__("skqt.shredprogress", fromlist=["x"]).refresh(page)
    return page.type_chips


def rule_row(page, rows, sug):
    """4.10.0 (morning answer 15): Not right beside a suggestion (this one piece only; the rule stays), and Make it a team
    rule... on a sorted piece, so the team's list of phrases grows from the shred."""
    import suggestrules as SR
    page.not_right_btn = page.team_rule_btn = None
    if len(rows) != 1 or page.cx is not None:
        return None
    it = rows[-1]
    rec = (getattr(page, "sg", None) or {}).get(it.get("id")) or {}
    cat = SR.category(it, rec)
    if not sug and cat not in ("L", "M", "SOW", "I", "req", "ctx", "cust", "ignore"):
        return None
    row = QHBoxLayout(); row.setSpacing(D.SPACE["xs"])
    if sug:
        page.not_right_btn = D.button("Not right", "ghost", lambda: page.reject_suggestion([it]),
                                      "This suggestion is wrong for this piece only; the rule stays for the rest")
        row.addWidget(page.not_right_btn)
    if cat:
        page.team_rule_btn = D.button("Make it a team rule...", "ghost", lambda: page.make_rule(it),
                                      "Every piece holding a phrase like this one gets this suggestion, in every effort")
        row.addWidget(page.team_rule_btn)
    row.addStretch(1)
    page.body_add_layout(row)
    return row


ASK_TIP = "Files a question for the customer that cites this piece. It is kept in Customer Q&A (Documents), where it is answered and tracked."


def goes(key):
    """Where a capture is kept, from the audited list (captureuse.CAPTURES): 'Shred > Evaluation Criteria'."""
    import captureuse as CU
    return CU.capture_line(key)


def fill_capture(page, m):
    """The captures the types do not already cover: the bar's own (keys kept) and the rest (More). 4.29.3: each line
    says where what it captures is kept, so a capture is never a label with no home."""
    m.clear()
    for key, b in (getattr(page, "cap_keys", None) or {}).items():
        if key in ("more",) + COVERED:
            continue
        g = goes(key)
        a = m.addAction(b.icon(), b.text() + (f"   ·   {g}" if g else ""), b.click)
        a.setToolTip(next((c[5] for c in __import__("reviewitems").CAPTURES if c[0] == key), ""))
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
