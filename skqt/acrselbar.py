"""The card beside a selection on the page (3.93.0; claude/stationkeeper-acronyms-two-tabs-3.93.md). Four kinds:
found, to decide (its definitions, 1 and 2 pick, the type, the Candidate and Definition boxes, the four decisions);
partly found (DC inside DC-RVM: use the whole term, or keep the part too); read with doubt (what it says, Fix the
reading, Read again, Not text); not found before (what the reader sees there now, the term and its definition, Add as a
term). Every decision goes to the effort's list and both tabs at once.
4.56.0 (UX decisions 20, 61, 107 to 110; his answers 8 and 9): the card opens in the page's right margin, one column
(acrmargin); the four decisions are Add to effort list (Enter), Not a term for the whole effort (X), Skip (N) and Later
(L), with Fix and... once the Candidate box differs (acrdecide); Not a term on this page only is the smaller second
choice; each moves on to the next find to decide (acrmove). Rules and the trained readers only (No AI); nothing leaves
the PC."""
import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLineEdit, QPushButton, QWidget

import acrlater as LT
import acrpage as P
import acrpages as AG
import app_gui as A
import diag
from . import design as D


def _frame(op):
    """4.56.0: the card in the right margin, CARD_W wide, one column (acrmargin)."""
    from . import acrmargin as MG
    return MG.frame(op)


def _chips(f, v, now):
    """It is: Acronym A, Abbreviation B, Unit U, Symbol S (one at a time); 4.56.0: they wrap in the one column."""
    from .adaptive import FlowLayout
    t = D.tokens()
    style = (f"QPushButton{{border:1px solid {t['border_strong']};border-radius:12px;padding:3px 10px;background:{t['surface']};"
             f"color:{t['text']}}}QPushButton:checked{{border:2px solid {t['accent']};background:{t['accent_soft']};"
             f"color:{t['accent']};font-weight:600}}")
    r = FlowLayout(); r.setSpacing(6)
    r.addWidget(D.label("It is", "muted", wrap=False))
    g = QButtonGroup(f); g.setExclusive(True)
    f.type_btns = {}
    for name, k in AG.TYPES:
        b = QPushButton(f"{name}  {k}"); b.setCheckable(True); b.setStyleSheet(style); b.setChecked(name == now)
        g.addButton(b); r.addWidget(b); f.type_btns[name] = b
        f.keys[k] = b.click
    v.addLayout(r)


def chosen_type(f):
    for name, b in getattr(f, "type_btns", {}).items():
        if b.isChecked():
            return name
    return None


def _buttons(v, spec):
    """4.56.0: one button per row (the card is one column)."""
    out = []
    for text, kind, fn in spec:
        if text is None:
            continue
        b = D.button(text, kind, fn); v.addWidget(b); out.append(b)
    return out


def build(op, host=None):
    """The card for what is selected on the page op shows."""
    items = op.selected()
    if not items:
        return new_bar(op, host)
    s = op.session
    kind = "decide" if getattr(op, "force_decide", False) else AG.bar_kind(items, s.results, A.ocr_cutoff())
    op.force_decide = False
    f = {"partial": partial_bar, "doubt": doubt_bar}.get(kind, decide_bar)(op, host, items)
    diag.activity("acronym_page_bar")
    return f


def key(op, name):
    """A key pressed while the card is open; True when the card took it."""
    b = op.bar
    fn = b.keys.get(name) if b is not None else None
    if fn is None:
        return False
    fn()
    return True


# ------------------------------------------------------------------ found, to decide
def decide_bar(op, host, items):
    import acrsuggest as AS
    from . import acrdecide as DC
    from . import acrmargin as MG
    s = op.session
    terms = list(dict.fromkeys(x["term"] for x in items))
    f, v = _frame(op); f.kind = "decide"
    f.terms = terms
    mk = LT.marks(s)
    if len(terms) > 1:
        head = f"<b>{len(terms)} selected: {html.escape(', '.join(terms[:5]))}" + ("...</b>" if len(terms) > 5 else "</b>")
    else:
        m = mk.get(terms[0])
        state = (f"for later: {LT.label(m.get('reason'))[0].lower()}" + (f" ({m['note']})" if m.get("note") else "")
                 if m else _state_words(s.results.get(terms[0]) or {}))
        head = f"<b>{html.escape(terms[0])}</b>  <span style='color:gray'>{html.escape(state)}</span>"
    v.addWidget(D.label(head))
    f.sugs, f.pick, f.cand = [], 1, None
    if len(terms) == 1:
        d = s.results.get(terms[0]) or {}
        f.sugs = AS.suggestions(d)[:2]
        f.sug_btns = []
        for k, x in enumerate(f.sugs, 1):
            b = QPushButton(); b.setFlat(True); b.setCheckable(True)
            b.setText(MG.wrap(f"{k}   {x['definition']}    ({x['source']})", b))       # 4.56.0: definitions wrap
            b.setToolTip(f"{x['definition']} ({x['source']})")
            b.setStyleSheet("text-align:left;padding:4px 6px"); b.setChecked(k == 1)
            b.clicked.connect(lambda _c=False, k=k: _pick(f, k))
            v.addWidget(b); f.sug_btns.append(b)
            f.keys[str(k)] = (lambda k=k: _pick(f, k))
    else:
        import acrplace as AP
        f.whole = QLineEdit(AP.combined(items)); f.whole.setPlaceholderText("The one term these spell")
        v.addWidget(D.label("Combine into", "muted", wrap=False)); v.addWidget(f.whole)
        f.typed = QLineEdit(); f.typed.setPlaceholderText("Its definition (type it, or leave it empty for now)")
        v.addWidget(f.typed)
        f.says = D.label("", "muted"); v.addWidget(f.says)
        f.whole.textChanged.connect(lambda _t: _say_combine(f))
    types = {AG.type_of(s.results.get(t) or {}) for t in terms}
    _chips(f, v, types.pop() if len(types) == 1 else None)
    if len(terms) == 1:                        # 4.56.0: Candidate and Definition, the same two boxes as the list's card
        from . import acrcard as AC
        form, f.cand, f.typed = AC.boxes(terms[0], "Or type a definition" if f.sugs else "No definition found: type one")
        v.addLayout(form)
        f.typed.textEdited.connect(lambda _t: _pick(f, 0))
        f.cand.textChanged.connect(lambda _t: DC.relabel(f))
    f.four = {}
    for k in DC.ORDER:
        fn = {"add": (lambda: combine(op, f)) if len(terms) > 1 else (lambda: DC.press(op, f, "add")),
              "not": lambda: DC.press(op, f, "not"), "skip": lambda: DC.press(op, f, "skip"),
              "later": lambda: open_later(op, f)}[k]
        f.four[k] = _buttons(v, [(DC.label(k), "primary" if k == "add" else None, fn)])[0]
    f.main, f.b_not, f.b_skip, f.b_later = (f.four[k] for k in DC.ORDER)
    _later_row(op, f, v)
    if len(terms) > 1:
        f.b_each = _buttons(v, [("Add each as its own term", "ghost", lambda: DC.press(op, f, "add"))])[0]
        _say_combine(f)
    f.b_here = _buttons(v, [(DC.HERE, "ghost", lambda: DC.here(op, f.terms))])[0]
    f.b_here.setStyleSheet(f"font-size:{D.TYPE['small']}pt")                    # the smaller second choice
    f.b_everywhere = None                      # 4.56.0: X is the whole effort; the second button of 4.26.1 is gone
    row2 = []
    if any(t in mk for t in terms):
        row2.append((DC.TAKE_OFF, "ghost", lambda: DC.take_off(op, [t for t in f.terms if t in LT.marks(s)])))
    if len(terms) == 1:                        # 4.26.1: what More held, on the card
        t = terms[0]
        from . import acrpart as APT
        row2 += [("Plural of...", "ghost", lambda: (op.page.plural(t), op.decided())),
                 ("A form of...", "ghost", lambda: (op.page.form(t), op.decided())),
                 ("Part of a longer term...", "ghost", lambda: (APT.part_of(op.page, t), op.decided()))]
    f.choices = _buttons(v, row2) if row2 else []
    f.b_take_off = f.choices[0] if row2 and row2[0][0] == DC.TAKE_OFF else None
    f.b_more = None
    DC.relabel(f)
    f.keys["enter"] = f.main.click
    f.keys["X"] = f.b_not.click
    f.keys["N"] = f.b_skip.click
    f.keys["L"] = f.b_later.click
    return f


def _later_row(op, f, v):
    """Later's two reasons and an optional note, shown by the first L (L or Enter: Come back to it; R: For author review;
    Esc closes it without marking)."""
    from . import acrdecide as DC
    f.later_w = QWidget(); col = __import__("PySide6.QtWidgets", fromlist=["x"]).QVBoxLayout(f.later_w)
    col.setContentsMargins(12, 0, 0, 0); col.setSpacing(4)
    f.later_btns = {}
    for (k, words, _c), key_ in zip(LT.REASONS, ("L", "R")):
        b = D.button(f"{words}  {key_}", None, lambda _c=False, k=k: DC.press(op, f, "later", k, f.note.text()))
        col.addWidget(b); f.later_btns[k] = b
    f.note = QLineEdit(); f.note.setPlaceholderText("A note (optional)")
    col.addWidget(f.note)
    f.later_back = D.button("Back  Esc", "ghost", lambda: close_later(op, f), "Close the reasons without marking")
    col.addWidget(f.later_back)
    f.later_w.setVisible(False)
    v.addWidget(f.later_w)


def open_later(op, f):
    """The first L: the reasons open on the card; the keys take a reason, Esc closes them."""
    from . import acrmargin as MG
    first, second = (r[0] for r in LT.REASONS)
    f.later_w.setVisible(True)
    f.saved_keys = dict(f.keys)
    f.keys = {"enter": f.later_btns[first].click, "L": f.later_btns[first].click, "R": f.later_btns[second].click,
              "Escape": lambda: close_later(op, f)}
    MG.place(op)
    return True


def close_later(op, f):
    from . import acrmargin as MG
    f.later_w.setVisible(False)
    f.keys = getattr(f, "saved_keys", f.keys)
    MG.place(op)
    return False


def _say_combine(f):
    """What goes in the list, said before the button is pressed."""
    w = " ".join(f.whole.text().split())
    f.says.setText(f"Add to effort list adds one term, {w}. {', '.join(f.terms[:5])} on this page become part of it."
                   if w else "Type the one term these spell, or add each as its own term.")
    return w


def combine(op, f):
    """Several finds side by side are one term: it goes in the effort's list, and the finds on this page become part of it
    (acrparts: where they sit together), so they are not left to decide here."""
    import acrmore as AM
    import acrparts as APS
    import acrplace as AP
    s = op.session
    whole = " ".join(f.whole.text().split())
    if not whole:
        op.page.host.status("Type the one term these spell first.")
        return None
    typ = chosen_type(f) or "Acronym"
    dfn = f.typed.text().strip()
    parts = [t for t in f.terms if t != whole]
    also = AP.together(s, parts) if len(parts) > 1 else {}       # 4.29.3: the same finds side by side elsewhere, decided once
    n_else = len({APS.place(l) for ls in also.values() for l in ls} - {APS.place(l) for t in parts for l in AP.here(s, t, op.key)})
    was = AG.before(s, [whole]) if whole in s.results else None
    for t in parts:
        APS.set_part(s, t, whole, places=list(AP.here(s, t, op.key)) + list(also.get(t, [])))
    made = whole not in s.results
    if made:
        AM.add_manual(s, whole, typ, dfn, document=op.key, to=("results",))
    AG.set_type(s, [whole], typ)
    s.add([whole], dfn)
    diag.activity("acronym_page_combined", n=len(parts))

    def back():
        for t in parts:
            APS.clear_part(s, t)
        if was is not None:
            AG.undo_not_term(s, was)
        else:
            s.list_remove([whole])
            if made:
                AM.remove_manual(s, whole)
        s.save()
    return op.decided("", undo=back, line=f"{whole} added to the effort list ({', '.join(parts[:4])} on this page are part of it"
                      + (f", and in {n_else} other place{'' if n_else == 1 else 's'} where they sit together" if n_else else "") + ").")


def _state_words(d):
    st = AG.state_of(d)
    return {"decide": "to decide", "list": "added to effort list", "not": "Not a term", "tied": "tied to another term"}[st]


def _pick(f, k):
    f.pick = k
    for i, b in enumerate(getattr(f, "sug_btns", []), 1):
        b.setChecked(i == k)
    if k and getattr(f, "typed", None) is not None:
        f.typed.clear()
    return k


def definition_of(f):
    typed = f.typed.text().strip() if getattr(f, "typed", None) is not None else ""
    if typed:
        return typed
    if f.pick and 0 < f.pick <= len(f.sugs):
        return f.sugs[f.pick - 1]["definition"]
    return ""


def add(op, f):
    """Add to effort list (Enter): each term with its definition (the one picked or typed; with many, each one's best).
    A term with no definition goes in without one; the move goes on (UX decision 19, Q7)."""
    from . import acrdecide as DC
    return DC.press(op, f, "add")


def not_term(op, terms, why=None, everywhere=True):
    """Not a term. 4.56.0 (his answer 8): for the whole effort; everywhere=False: on this page only (what X did from
    4.26.1). Undo puts them back as they were."""
    from . import acrdecide as DC
    if not everywhere:
        return DC.here(op, list(terms))
    f = type("Card", (), {"terms": list(terms)})()
    return DC.press(op, f, "not")


def skip_card(op):
    from . import acrmove as MV
    return MV.skip(op)


# ------------------------------------------------------------------ partly found
def partial_bar(op, host, items):
    s = op.session
    t = items[0]["term"]
    lg = P.longer(s.results, t)
    f, v = _frame(op); f.kind = "partial"; f.terms = [t]; f.whole = lg["whole"]
    v.addWidget(D.label(f"<b>{html.escape(t)} is part of {html.escape(lg['whole'])} here</b>"))
    v.addWidget(D.label(f"{html.escape(lg['whole'])} is in {lg['places']} place(s); {html.escape(t)} sits inside it in "
                        f"{lg['shared']}.", "muted"))
    f.main, f.b_keep, f.b_not, f.b_skip = _buttons(v, [(f"Use {lg['whole']}  Enter", "primary", lambda: use_whole(op, t, lg["whole"])),
                                             (f"Keep {t} too", None, lambda: keep_part(op)),
                                             ("Not a term  X", None, lambda: not_term(op, [t])),
                                             ("Skip  N", None, lambda: skip_card(op))])
    v.addWidget(D.label("Letters joined by a hyphen can be one term for the whole effort: Everything found, More.", "muted"))
    f.keys["enter"] = f.main.click
    f.keys["X"] = f.b_not.click
    f.keys["N"] = f.b_skip.click
    return f


def use_whole(op, part, whole):
    import acrparts as APS
    import efftrain as ET
    s = op.session
    ok = APS.set_part(s, part, whole)
    if not ok:
        return op.decided("", move=False)
    ET.add(s, "part", part, whole, [op.key])
    diag.activity("acronym_longer_used")
    return op.decided("", undo=lambda: (APS.clear_part(s, part), s.save()),
                      line=f"{part} is part of {whole} where they sit together: {whole} takes the row.")


def keep_part(op):
    op.force_decide = True
    return op.show_bar()


# ------------------------------------------------------------------ read with doubt
def _sure(conf):
    c = float(conf or 0)
    return int(round(c * 100 if c <= 1 else c))


def doubt_bar(op, host, items):
    x = items[0]
    f, v = _frame(op); f.kind = "doubt"; f.terms = [x["term"]]; f.item = x
    v.addWidget(D.label(f"<b>Read as {html.escape(x['term'])}</b>  <span style='color:{D.tokens()['warn']}'>{_sure(x['conf'])}% "
                        "sure</span>"))
    r = QHBoxLayout(); r.addWidget(D.label("It says", "muted", wrap=False))
    f.says = QLineEdit(x["term"]); r.addWidget(f.says, 1); v.addLayout(r)
    f.main, f.b_again, f.b_nottext = _buttons(v, [("Fix the reading  Enter", "primary", lambda: fix_reading(op, f)),
                                                  ("Read again", None, lambda: read_again(op, f, x["box"])),
                                                  ("Not text", None, lambda: not_text(op, x))])
    f.b_skip = _buttons(v, [("Skip  N", None, lambda: skip_card(op))])[0]
    v.addWidget(_link("It reads right: decide it", lambda: keep_part(op)))
    f.keys["enter"] = f.main.click
    f.keys["X"] = f.b_nottext.click
    f.keys["N"] = f.b_skip.click
    return f


def _link(text, fn):
    b = D.button(text, "ghost", fn)
    return b


def fix_reading(op, f):
    """What the picture says: this PC reads it that way from the next scan; the right term is listed here now and the
    misreading is Not a term (Undo puts it back)."""
    term, right = f.terms[0], " ".join(f.says.text().split())
    if not right or right == term:
        op.page.host.status("Type what the picture says, then Fix the reading.")
        return None
    from . import acrdecide as DC
    said, back = DC.fix(op, term, right, f.item["box"])
    return op.decided("", undo=back, line=f"{term} reads as {right}; {right} is a find to decide." + said, move=False)


def not_text(op, x):
    import efftrain as ET
    ET.add(op.session, "not text", x["term"], "", [op.key], crop=crop(op, x["box"]))
    return not_term(op, [x["term"]], everywhere=False)


# ------------------------------------------------------------------ not found before
def new_bar(op, host):
    import acrsuggest as AS
    s = op.session
    f, v = _frame(op); f.kind = "new"; f.terms = []
    v.addWidget(D.label("<b>Not found before</b>"))
    f.seen = D.label("", None); f.seen.setTextFormat(Qt.RichText); v.addWidget(f.seen)
    _seen(f, op.new_text)
    f.term = QLineEdit(AG.guess_term(op.new_text)); f.term.setPlaceholderText("The term, as written")
    f.dfn = QLineEdit(); f.dfn.setPlaceholderText("Its definition (type it)")
    known = s.results.get(f.term.text()) or {}
    sg = AS.suggestions(known) if known else []
    if sg:
        f.dfn.setPlaceholderText(f"Type it, or leave it for {sg[0]['definition']}")
    for lab, w in (("Term", f.term), ("Definition", f.dfn)):
        r = QHBoxLayout(); r.addWidget(D.label(lab, "muted", wrap=False)); r.addWidget(w, 1); v.addLayout(r)
    _chips(f, v, "Acronym")
    spec = [("Add as a term  Enter", "primary", lambda: add_new(op, f))]
    if op.state == "picture" and op.new_area is not None:
        spec.append(("Read this area again", None, lambda: read_again(op, f, op.new_area)))
    got = _buttons(v, spec)
    f.main = got[0]
    f.keys["enter"] = f.main.click
    return f


def _seen(f, text):
    f.seen.setText(f"<span style='color:gray'>The reader sees here now</span>&nbsp;&nbsp;<span style='font-family:Consolas,"
                   f"monospace'>{html.escape(text) if text else '(nothing read)'}</span>")


def add_new(op, f):
    """A term the scan never found: listed with the scan's terms at this page, and in this effort's list."""
    import acrmore as AM
    import efftrain as ET
    s = op.session
    term = " ".join(f.term.text().split())
    if not term:
        op.page.host.status("Type the term first.")
        return None
    to = ("results", "list") if s.effort is not None else ("results",)
    said = AM.add_manual(s, term, chosen_type(f) or "Acronym", f.dfn.text().strip(), document=op.key, to=to)
    ET.add(s, "missed", op.new_text, term, [op.key], crop=crop(op, op.new_area) if op.new_area else None)
    diag.activity("acronym_page_new_added")
    return op.decided("", line=f"{term} added to the effort list." if "list" in to else f"{term} added: {said}.", move=False)


# ------------------------------------------------------------------ the picture's parts
def crop(op, box):
    """Part of the page shown, as a PIL image (for Read again and the effort's training samples), or None."""
    pix = getattr(op.view, "pix", None)
    if box is None or pix is None or op.state != "picture":
        return None
    from PIL import Image
    q = pix.pixmap().toImage().convertToFormat(QImage.Format_RGB888)
    w, h, bpl = q.width(), q.height(), q.bytesPerLine()
    im = Image.frombuffer("RGB", (w, h), bytes(q.constBits()), "raw", "RGB", bpl, 1)
    x0, y0, x1, y1 = [int(round(c)) for c in box]
    return im.crop((max(0, x0 - 4), max(0, y0 - 4), min(w, x1 + 4), min(h, y1 + 4))).copy()


def read_again(op, f, box, wait=False):
    """Reads only that part of the page again (off the window's thread); what it reads now goes in the bar."""
    c = crop(op, box)
    if c is None:
        return None
    from .progress import JobWorker
    from . import foundview as FV

    def job(_p, _s, c=c):
        import pictures as PIC
        lines = PIC.read_region_lines(c)
        text = " ".join(t for _b, t, _c in lines).strip()
        if not text:
            text, _conf = PIC.read_region_as_one_line(c)
        return text

    w = JobWorker(job)

    def done(res):
        try:
            if not isinstance(res, str):
                return
            if f.kind == "doubt":
                f.says.setText(AG.guess_term(res) or res)
            else:
                op.new_text = res
                _seen(f, res)
                f.term.setText(AG.guess_term(res))
        except RuntimeError:                     # the bar was closed meanwhile
            pass
    w.done.connect(done)
    FV._ALIVE.append(w); w.finished.connect(lambda w=w: FV._ALIVE.remove(w) if w in FV._ALIVE else None)
    w.start()
    diag.activity("acronym_page_read_again")
    if wait:
        import time
        from PySide6.QtWidgets import QApplication
        t0 = time.time()
        while w.isRunning() and time.time() - t0 < 60:
            QApplication.processEvents(); time.sleep(0.02)
        QApplication.processEvents()
    return w
