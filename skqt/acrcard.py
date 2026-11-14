"""A term's card on Acronym Findings (3.61.0: lighter at the top).

At the top: the status, the proposed meaning (other possibilities folded away), the find as text you can copy, the
definition box and the actions. Then the preview. Pills, counts, the equation list and every place sit under Details.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QListWidget, QVBoxLayout, QWidget

import app_gui as A
import acrmore as AM
from . import design as D
from . import acrextras as AX


def _fold(page, title, inner, open_=False):
    """A button that shows or hides a block. Returns (button, block)."""
    block = QWidget(); block.setLayout(inner); block.setVisible(open_)
    btn = D.button(("Hide " if open_ else "Show ") + title, "ghost")

    def flip():                                          # isHidden: right while the card's tab is not showing too
        block.setVisible(block.isHidden())
        btn.setText(("Show " if block.isHidden() else "Hide ") + title)
    btn.clicked.connect(flip)
    return btn, block


def build(page, t, kind_tone):
    s = page.session
    d = s.results[t]
    body = page.body
    kind = "excluded" if d.get("excluded") else A.status_kind(d.get("status", ""))
    top = QHBoxLayout(); top.setSpacing(D.SPACE["s"])
    top.addWidget(D.Pill(A.status_text(d.get("status", "")), kind_tone.get(kind, "accent")))
    top.addWidget(D.label(f"found {d.get('count', 0)} time(s)", "muted", wrap=False))
    top.addStretch(1)
    body.addLayout(top)

    # ---- the meaning
    chosen = d.get("selected_definition", "")
    body.addWidget(D.label(f"Meaning: <b>{chosen}</b>" if chosen else "Meaning: none chosen yet"))
    # 3.88.0: what it could mean, in the stated order, each with its source and why; two customer meanings need a choice
    import acrsuggest as AS
    hint = AS.not_a_term_hint(t)
    if hint and not d.get("excluded") and d.get("effort") != "Not a term":
        hr = QHBoxLayout(); hr.setSpacing(D.SPACE["s"])
        hr.addWidget(D.label(f"Suggested: ignore in this effort. {hint}.", "muted"), 1)
        hr.addWidget(D.button("Ignore in this effort", "ghost", lambda: page.set_status([t], "Not a term")))
        body.addLayout(hr)
    means = AS.meanings(d)
    if means:
        body.addWidget(D.label("Needs a choice: the customer spells it out more than one way. Pick the one this effort uses; "
                               "the other stays in Other definitions.", "muted"))
    sug = AS.suggestions(d)
    page.suggest_rows = []
    for k, x in enumerate(sug[:4], 1):
        r = QHBoxLayout(); r.setSpacing(D.SPACE["s"])
        r.addWidget(D.Pill(x["source"], {"List": "ok", "Customer": "cust", "Client list": "accent", "This PC": "head"}[x["source"]]))
        r.addWidget(D.label(f"<b>{x['definition']}</b>  <span style='color:gray'>{x['why']}</span>"), 1)
        r.addWidget(D.button(f"Use this  {k}" if k <= 2 else "Use this", "ghost", lambda _=False, x=x: page.choose(t, x["definition"])))
        body.addLayout(r)
        page.suggest_rows.append(x)
    extras = AX.card_extras(page, t)
    details_extra = []
    for w_ in extras:                                    # the found line and the context suggestion stay up top
        if isinstance(w_, QHBoxLayout):
            body.addLayout(w_)
        else:
            details_extra.append(w_)
    defs = [x for x in d.get("definitions", []) if x]
    page.other_btn = None
    if defs:
        inner = QVBoxLayout(); inner.setContentsMargins(0, 0, 0, 0); inner.setSpacing(D.SPACE["xs"])
        cust = set(d.get("customer_definitions", []))
        for x in defs:
            r = QHBoxLayout(); r.setSpacing(D.SPACE["s"])
            src = AM.sources_of(d, x) if x in cust else []
            r.addWidget(D.label(x + (f"   (customer document: {', '.join(src[:2])})" if src else "   (customer document)" if x in cust else "")), 1)
            r.addWidget(D.button("Use this", "ghost", lambda _=False, x=x: page.choose(t, x)))
            inner.addLayout(r)
        if len(defs) > 1:
            inner.addWidget(D.button("Keep all possibilities", "ghost", lambda: page.choose(t, "Keep All Possibilities")), 0, Qt.AlignLeft)
        page.other_btn, block = _fold(page, f"other possibilities ({len(defs)})", inner, open_=not chosen and len(defs) > 1)
        body.addWidget(page.other_btn, 0, Qt.AlignLeft); body.addWidget(block)

    # ---- the find as text, then the definition box
    # 4.23.1 (Nicholas 2026-11-12 13:51): two lines. Reads as: the term, typable, to fix a wrong reading. Means: the
    # definition, picked above or typed, or left empty. The line it was read in is the page beside the card, not a box.
    from PySide6.QtWidgets import QFormLayout
    from . import symbols as SYM
    form = QFormLayout(); form.setHorizontalSpacing(D.SPACE["s"]); form.setVerticalSpacing(D.SPACE["s"])
    page.reads = QLineEdit(t)
    page.reads.setToolTip("How the term is written. Fix it here if it was read wrong: what you type goes in the list")
    form.addRow(D.label("Reads as", "muted", wrap=False), page.reads)
    page.typed = QLineEdit(); page.typed.setPlaceholderText("Pick a meaning above or type one; it may stay empty")
    page.typed.setToolTip("Right-click for subscript, superscript and symbols")
    tr = QHBoxLayout(); tr.setSpacing(D.SPACE["s"])
    tr.addWidget(page.typed, 1); tr.addWidget(SYM.button(page.typed))
    form.addRow(D.label("Means", "muted", wrap=False), tr)
    body.addLayout(form)
    page.find_text = QLineEdit(); page.find_text.setReadOnly(True); page.find_text.setVisible(False)   # kept for the preview
    page.use_sel = D.button("Use as the definition", "ghost", lambda: page.use_selected()); page.use_sel.setVisible(False)
    page._actions([t])

    # ---- the preview
    locs = d.get("locations", [])
    page.where_view = None
    if getattr(page, "list_only", False):                              # 3.93.0: the page is the On the page tab
        locs_view = []
    else:
        locs_view = locs
    if locs_view:
        from .foundview import FoundView
        from . import acrpart as APT
        page.where_view = FoundView(t, locs, page.path_of, on_meaning=lambda x: _meaning(page, x),
                                    on_find_text=lambda x: page.find_text.setText(x),
                                    on_add_term=lambda text, loc, read, crop: APT.missed(page, text, loc, read, crop))
        wv = __import__("skqt.acrpick", fromlist=["x"]).hook(page, page.where_view, t)       # 4.30.4: a term clicked on the page
        # 4.23.1: what is selected on the page goes to a line
        wv.read_lab.setText("Selected on the page")
        wv.reading.setPlaceholderText("Click a box in the picture, or select words in the passage")
        for b, text, tip, to in ((wv.b_fixread, "Put in Reads as", "These words are how the term is written", page.reads),
                                 (wv.b_usemean, "Put in Means", "These words are what the term means", page.typed)):
            b.setText(text); b.setToolTip(tip)
            b.clicked.disconnect()
            b.clicked.connect(lambda _c=False, to=to: (to.setText(" ".join(wv.reading.text().split())), to.setFocus())
                              if wv.reading.text().strip() else page.host.status("Select words on the page first."))
        if getattr(page, "mid_box", None) is not None:                  # 3.92.0: the customer's page, in the middle
            page.mid_hint.setVisible(False)
            page.mid_box.addWidget(page.where_view, 1)
        else:
            body.addWidget(page.where_view)

    # ---- details, folded
    inner = QVBoxLayout(); inner.setContentsMargins(0, 0, 0, 0); inner.setSpacing(D.SPACE["s"])
    pills = QHBoxLayout(); pills.setSpacing(D.SPACE["s"])
    if d.get("effort"):
        pills.addWidget(D.Pill(f"Acronym list: {__import__('skqt.acrwords', fromlist=['x']).shown(d['effort'])}" + ("" if ((d.get("list_definition") or "").strip() or d["effort"] == "Not a term") else ", no definition yet"),
                            "ok" if (d.get("list_definition") or "").strip() and d["effort"] == "In the list" else "head" if d["effort"] == "Not a term" else "warn"))
    if d.get("from_drafts"):                                  # 4.4.0: Drafts > Acronyms sent it here
        pills.addWidget(D.Pill("From our drafts: " + ", ".join(d["from_drafts"]), "warn" if not d.get("effort") else "ctx"))
    if d.get("plural_of"):
        pills.addWidget(D.Pill(f"Plural of {d['plural_of']}", "ctx"))
    if d.get("form_of"):
        pills.addWidget(D.Pill(f"Written as {d['form_of']} plus a number", "ctx"))
    if d.get("from_forms"):
        pills.addWidget(D.Pill("Found inside its forms", "ctx"))
    pills.addStretch(1)
    inner.addLayout(pills)
    known = s.known_cell(t, d)
    inner.addWidget(D.label(f"{d.get('category', '')}" + (f"  |  known in: {known}" if known else ""), "muted"))
    for w_ in details_extra:
        inner.addWidget(w_)
    if locs:
        inner.addWidget(D.SectionTitle(f"Where it was found ({len(locs)})"))
        box = QListWidget(); box.setMinimumHeight(100)
        box.addItems(locs[:500] + ([f"... and {len(locs) - 500} more"] if len(locs) > 500 else []))
        box.setToolTip("Click a place to show it in the preview")
        if page.where_view is not None:
            box.currentRowChanged.connect(lambda r, fv=page.where_view: fv.show_place(r))
        elif getattr(page, "show_on_page", None) is not None:          # 3.93.0: that page, in On the page
            from . import acrtabs as TB
            box.currentRowChanged.connect(lambda r: TB.show_place(page, locs[r]) if 0 <= r < len(locs) else None)
        inner.addWidget(box)
        page.places = box
    page.details_btn, block = _fold(page, "details", inner)
    body.addWidget(page.details_btn, 0, Qt.AlignLeft); body.addWidget(block)
    body.addStretch(1)


def _meaning(page, text):
    page.typed.setText(text)
    page.typed.setFocus()


def _copy(text):
    from PySide6.QtWidgets import QApplication
    if text:
        QApplication.clipboard().setText(text)
    return text
