"""The bar beside a selection on the page (3.93.0; claude/stationkeeper-acronyms-two-tabs-3.93.md). Four kinds:
found, to decide (its definitions, 1 and 2 pick, the type, Add to the list with Enter, Not a term with X); partly found
(DC inside DC-RVM: use the whole term, or keep the part too); read with doubt (what it says, Fix the reading, Read again,
Not text); not found before (what the reader sees there now, the term and its definition, Add as a term). Every
decision goes to the effort's list and both tabs at once. Rules and the trained readers only (No AI); nothing leaves
the PC."""
import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import (QButtonGroup, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLineEdit, QPushButton,
                               QVBoxLayout)

import acrpage as P
import acrpages as AG
import app_gui as A
import diag
from . import design as D


def _frame(host):
    t = D.tokens()
    f = QFrame(host); f.setObjectName("selBar")
    f.setStyleSheet(f"QFrame#selBar{{background:{t['surface']};border:1px solid {t['border_strong']};border-radius:8px}}"
                    f"QFrame#selBar QLabel{{color:{t['text']};background:transparent;border:0}}")
    sh = QGraphicsDropShadowEffect(f); sh.setBlurRadius(22); sh.setOffset(0, 6); sh.setColor(QColor(0, 0, 0, 90))
    f.setGraphicsEffect(sh)
    f.setMinimumWidth(420); f.setMaximumWidth(560)                 # 4.26.1: the choices are on the bar
    v = QVBoxLayout(f); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(8)
    f.keys = {}
    f.kind = None
    return f, v


def _chips(f, v, now):
    """It is: Acronym A, Abbreviation B, Unit U, Symbol S (one at a time)."""
    t = D.tokens()
    style = (f"QPushButton{{border:1px solid {t['border_strong']};border-radius:12px;padding:3px 10px;background:{t['surface']};"
             f"color:{t['text']}}}QPushButton:checked{{border:2px solid {t['accent']};background:{t['accent_soft']};"
             f"color:{t['accent']};font-weight:600}}")
    r = QHBoxLayout(); r.setSpacing(6)
    r.addWidget(D.label("It is", "muted", wrap=False))
    g = QButtonGroup(f); g.setExclusive(True)
    f.type_btns = {}
    for name, k in AG.TYPES:
        b = QPushButton(f"{name}  {k}"); b.setCheckable(True); b.setStyleSheet(style); b.setChecked(name == now)
        g.addButton(b); r.addWidget(b); f.type_btns[name] = b
        f.keys[k] = b.click
    r.addStretch(1)
    v.addLayout(r)


def chosen_type(f):
    for name, b in getattr(f, "type_btns", {}).items():
        if b.isChecked():
            return name
    return None


def _buttons(v, spec):
    r = QHBoxLayout(); r.setSpacing(8)
    out = []
    for text, kind, fn in spec:
        if text is None:
            r.addStretch(1); continue
        b = D.button(text, kind, fn); r.addWidget(b); out.append(b)
    v.addLayout(r)
    return out


def build(op, host):
    """The bar for what is selected on the page op shows."""
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
    """A key pressed while the bar is open; True when the bar took it."""
    b = op.bar
    fn = b.keys.get(name) if b is not None else None
    if fn is None:
        return False
    fn()
    return True


# ------------------------------------------------------------------ found, to decide
def decide_bar(op, host, items):
    import acrsuggest as AS
    s = op.session
    terms = list(dict.fromkeys(x["term"] for x in items))
    f, v = _frame(host); f.kind = "decide"
    f.terms = terms
    v.addWidget(D.label(f"<b>{len(terms)} selected: {html.escape(', '.join(terms[:5]))}" + ("...</b>" if len(terms) > 5 else "</b>")
                        if len(terms) > 1 else f"<b>{html.escape(terms[0])}</b>  <span style='color:gray'>"
                        f"{html.escape(_state_words(s.results.get(terms[0]) or {}))}</span>"))
    f.sugs, f.pick = [], 1
    if len(terms) == 1:
        d = s.results.get(terms[0]) or {}
        f.sugs = AS.suggestions(d)[:2]
        f.sug_btns = []
        for k, x in enumerate(f.sugs, 1):
            b = QPushButton(f"{k}   {x['definition']}    ({x['source']})"); b.setFlat(True); b.setCheckable(True)
            b.setStyleSheet("text-align:left;padding:4px 6px"); b.setChecked(k == 1)
            b.clicked.connect(lambda _c=False, k=k: _pick(f, k))
            v.addWidget(b); f.sug_btns.append(b)
            f.keys[str(k)] = (lambda k=k: _pick(f, k))
        f.typed = QLineEdit(); f.typed.setPlaceholderText("Or type a definition" if f.sugs else "No definition found: type one")
        f.typed.textEdited.connect(lambda _t: _pick(f, 0))
        v.addWidget(f.typed)
    else:
        import acrplace as AP
        f.whole = QLineEdit(AP.combined(items)); f.whole.setPlaceholderText("The one term these spell")
        r = QHBoxLayout(); r.addWidget(D.label("Combine into", "muted", wrap=False)); r.addWidget(f.whole, 1); v.addLayout(r)
        f.typed = QLineEdit(); f.typed.setPlaceholderText("Its definition (type it, or leave it empty for now)")
        v.addWidget(f.typed)
        f.says = D.label("", "muted"); v.addWidget(f.says)
        f.whole.textChanged.connect(lambda _t: _say_combine(f))
    types = {AG.type_of(s.results.get(t) or {}) for t in terms}
    _chips(f, v, types.pop() if len(types) == 1 else None)
    import acrplace as AP
    n_all = sum(AP.places(s, t) for t in terms)
    n_here = sum(len(AP.here(s, t, op.key)) for t in terms)
    if len(terms) > 1:
        f.main, f.b_each, f.b_not = _buttons(v, [("Add to effort list  Enter", "primary", lambda: combine(op, f)),
                                                 ("Add each as its own term", None, lambda: add(op, f)),
                                                 ("Ignore here  X", None, lambda: not_term(op, f.terms))])
        _say_combine(f)
    else:
        f.main, f.b_not = _buttons(v, [("Add to effort list  Enter", "primary", lambda: add(op, f)),
                                       ("Ignore here  X", None, lambda: not_term(op, f.terms))])
    f.b_not.setToolTip("Only on this page. The term stays a find everywhere else in the effort.")
    f.b_everywhere = None
    row2 = []
    if n_all > n_here:
        row2.append((f"Ignore in this effort ({n_all})", "ghost", lambda: not_term(op, f.terms, everywhere=True)))
    if len(terms) == 1:                        # 4.26.1: what More held, on the bar (Show in the list is gone)
        t = terms[0]
        from . import acrpart as APT
        row2 += [("Plural of...", "ghost", lambda: (op.page.plural(t), op.decided())),
                 ("A form of...", "ghost", lambda: (op.page.form(t), op.decided())),
                 ("Part of a longer term...", "ghost", lambda: (APT.part_of(op.page, t), op.decided()))]
    f.choices = _buttons(v, row2) if row2 else []
    if n_all > n_here:
        f.b_everywhere = f.choices[0]
    f.b_more = None
    f.keys["enter"] = f.main.click
    f.keys["X"] = f.b_not.click
    return f


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
    for t in parts:
        APS.set_part(s, t, whole, places=AP.here(s, t, op.key))
    if whole not in s.results:
        AM.add_manual(s, whole, typ, dfn, document=op.key, to=("results",))
    AG.set_type(s, [whole], typ)
    s.add([whole], dfn)
    diag.activity("acronym_page_combined", n=len(parts))
    return op.decided(f"{whole}: in the effort list ({', '.join(parts[:4])} on this page are part of it)")


def _state_words(d):
    st = AG.state_of(d)
    return {"decide": "undecided", "list": "added to effort list", "not": "not a term", "tied": "tied to another term"}[st]


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
    """Add to the list: each term with its definition (the one picked or typed; with many, each one's best)."""
    import acrsuggest as AS
    s = op.session
    typ = chosen_type(f)
    if typ:
        AG.set_type(s, f.terms, typ)
    if len(f.terms) == 1:
        s.add(f.terms, definition_of(f))
    else:
        for t in f.terms:
            sg = AS.suggestions(s.results.get(t) or {})
            s.add([t], sg[0]["definition"] if sg else "")
    diag.activity("acronym_page_added", n=len(f.terms))
    return op.decided(f"{', '.join(f.terms[:4])}{'...' if len(f.terms) > 4 else ''}: in the list")


def not_term(op, terms, why=None, everywhere=False):
    """Not a term. 4.26.1: on this page only (the term stays a find everywhere else); everywhere=True: in the whole
    effort, as before. Undo puts them back as they were."""
    import acrplace as AP
    s = op.session
    words = ", ".join(terms[:4]) + ("..." if len(terms) > 4 else "")
    if not everywhere:
        took = AP.not_here(s, terms, op.key)
        if took:
            diag.activity("acronym_page_not_term_here", n=len(terms))
            return op.decided("", undo=(words + ", on this page", {"__here__": took}))
    was = AG.before(s, terms)
    if s.effort is None:
        s.exclude(terms, True)
    else:
        s.set_status(terms, "Not a term")
    diag.activity("acronym_page_not_term", n=len(terms))
    return op.decided("", undo=(words, was))


# ------------------------------------------------------------------ partly found
def partial_bar(op, host, items):
    s = op.session
    t = items[0]["term"]
    lg = P.longer(s.results, t)
    f, v = _frame(host); f.kind = "partial"; f.terms = [t]; f.whole = lg["whole"]
    v.addWidget(D.label(f"<b>{html.escape(t)} is part of {html.escape(lg['whole'])} here</b>"))
    v.addWidget(D.label(f"{html.escape(lg['whole'])} is in {lg['places']} place(s); {html.escape(t)} sits inside it in "
                        f"{lg['shared']}.", "muted"))
    f.main, f.b_keep, f.b_not = _buttons(v, [(f"Use {lg['whole']}  Enter", "primary", lambda: use_whole(op, t, lg["whole"])),
                                             (f"Keep {t} too", None, lambda: keep_part(op)),
                                             ("Ignore here  X", None, lambda: not_term(op, [t]))])
    v.addWidget(D.label("Letters joined by a hyphen can be one term for the whole effort: The list, More.", "muted"))
    f.keys["enter"] = f.main.click
    f.keys["X"] = f.b_not.click
    return f


def use_whole(op, part, whole):
    import acrparts as APS
    import efftrain as ET
    s = op.session
    ok = APS.set_part(s, part, whole)
    if ok:
        ET.add(s, "part", part, whole, [op.key])
        diag.activity("acronym_longer_used")
    return op.decided(f"{part} is part of {whole} where they sit together: {whole} takes the row." if ok else "")


def keep_part(op):
    op.force_decide = True
    return op.show_bar()


# ------------------------------------------------------------------ read with doubt
def _sure(conf):
    c = float(conf or 0)
    return int(round(c * 100 if c <= 1 else c))


def doubt_bar(op, host, items):
    x = items[0]
    f, v = _frame(host); f.kind = "doubt"; f.terms = [x["term"]]; f.item = x
    v.addWidget(D.label(f"<b>Read as {html.escape(x['term'])}</b>  <span style='color:{D.tokens()['warn']}'>{_sure(x['conf'])}% "
                        "sure</span>"))
    r = QHBoxLayout(); r.addWidget(D.label("It says", "muted", wrap=False))
    f.says = QLineEdit(x["term"]); r.addWidget(f.says, 1); v.addLayout(r)
    f.main, f.b_again, f.b_nottext = _buttons(v, [("Fix the reading  Enter", "primary", lambda: fix_reading(op, f)),
                                                  ("Read again", None, lambda: read_again(op, f, x["box"])),
                                                  ("Not text", None, lambda: not_text(op, x))])
    v.addWidget(_link("It reads right: decide it", lambda: keep_part(op)))
    v.addWidget(D.label("The fix is kept with this PC's reading fixes; the term is then decided like any other.", "muted"))
    f.keys["enter"] = f.main.click
    f.keys["X"] = f.b_nottext.click
    return f


def _link(text, fn):
    b = D.button(text, "ghost", fn)
    return b


def fix_reading(op, f):
    """What the picture says: this PC reads it that way from the next scan; the right term is listed here now and the
    misreading is Not a term (Undo puts it back)."""
    import acrmore as AM
    import efftrain as ET
    from . import acrextras as AX
    s = op.session
    term, right = f.terms[0], " ".join(f.says.text().split())
    if not right or right == term:
        op.page.host.status("Type what the picture says, then Fix the reading.")
        return None
    if not AX.fix_misread(op.page, term, right):
        return None
    AM.add_manual(s, right, AG.type_of(s.results.get(term) or {}) or "Acronym", "", document=op.key, to=("results",))
    ET.add(s, "misread", term, right, [op.key], crop=crop(op, f.item["box"]))
    was = AG.before(s, [term])
    if s.effort is None:
        s.exclude([term], True)
    else:
        s.set_status([term], "Not a term")
    diag.activity("acronym_page_fixed")
    return op.decided(f"Fixed: {term} reads as {right}.", undo=(term, was))


def not_text(op, x):
    import efftrain as ET
    ET.add(op.session, "not text", x["term"], "", [op.key], crop=crop(op, x["box"]))
    return not_term(op, [x["term"]])


# ------------------------------------------------------------------ not found before
def new_bar(op, host):
    import acrsuggest as AS
    s = op.session
    f, v = _frame(host); f.kind = "new"; f.terms = []
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
    return op.decided(said or f"{term} added")


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
