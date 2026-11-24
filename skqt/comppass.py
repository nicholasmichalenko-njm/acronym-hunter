"""Shred in passes: the Compliance pass on the customer's page (4.72.0; compmark holds what is the pass's own). The
Shred page in a mode of its own, as the Response Structure pass is. Nothing is beside the page but the bar (280): Work
Requirement (SOW), Response Instruction (L), Evaluation Criterion (M) on keys 1 to 3; then "In Matrix under:" with the
section the app suggests (Enter takes it), Pick another section, Decide later; then Not needed (X), Ask a question (A)
and For the setup (S). Enter takes the suggested kind and section and goes to the next piece of the document not dealt
with; N goes on without marking. The document's state in the pass is on the row above the page.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QCheckBox, QLabel, QMenu

import assignlinks as AL
import compmark as CM
import diag
from . import design as D

KEY = "comppass"
MODE = "comp"
WIDE = 256                       # the right margin in this pass: the kinds' names are long


def on(page):
    return getattr(page, "focus", None) == MODE


def M_of(page):
    return page.R.M if page.R is not None else None


def install(page):
    if getattr(page, "comp_state", None) is not None:
        return page.comp_state
    page.comp_state = D.label("", "muted", wrap=False)
    page.comp_none = QCheckBox("Nothing of this kind in this document")
    page.comp_none.setToolTip("You looked: this document holds no requirement, instruction or criterion. It can be unticked.")
    page.comp_none.clicked.connect(lambda c=False: set_none(page, bool(c)))
    for x in (page.comp_state, page.comp_none):
        page.top_bar.addWidget(x); x.setVisible(False)
    return page.comp_state


def apply(w, step):
    """Called at the end of structpass.apply: the pass's mode for its tab, and its row put away for any other."""
    pg = w.assign_page
    want = step == KEY and pg.cx is None
    try:
        install(pg)
        if want:
            pg.focus = MODE
            for name in ("shred_check", "queue_lbl", "reshred_btn"):
                x = getattr(pg, name, None)
                if x is not None:
                    x.setVisible(False)
            if getattr(pg, "progress_row", None) is not None:
                pg.progress_row.setVisible(False)
            pg.page_side.setVisible(False)
            pg.gutter_w = WIDE
            __import__("skqt.shredselbar", fromlist=["x"]).gutter(pg, True)
            __import__("skqt.shredfocus", fromlist=["x"]).suggest_on(pg)
            fill(pg)
            __import__("skqt.shredselbar", fromlist=["x"]).later(pg)
        else:
            pg.comp_state.setVisible(False); pg.comp_none.setVisible(False)
            if getattr(pg, "gutter_w", None) == WIDE:                # the other tabs keep the margin they had
                SSB = __import__("skqt.shredselbar", fromlist=["x"])
                pg.gutter_w = SSB.GUTTER
                if pg.view.viewportMargins().right() > 0:
                    SSB.gutter(pg, True)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return want


def fill(page):
    """The document's state on the row above the page."""
    M = M_of(page)
    cur = next((d for d in CM.docs(M) if d["file"] == page.file), None) if M is not None else None
    page.comp_state.setVisible(on(page))
    page.comp_state.setText(f"This document: {cur['state']}" if cur else "")
    page.comp_none.setVisible(on(page) and cur is not None and not cur["finds"])
    page.comp_none.blockSignals(True); page.comp_none.setChecked(bool(cur and cur["none"])); page.comp_none.blockSignals(False)
    return cur


def done(page, msg=""):
    if msg:
        page.after(msg)
    fill(page)
    try:
        page.host.stepper.show_for(KEY)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    __import__("skqt.shredselbar", fromlist=["x"]).later(page)
    return msg


def set_none(page, on_=True):
    M = M_of(page)
    if M is None or not page.file:
        return None
    with page.R.group():
        page.R.snap("Nothing of this kind here" if on_ else "Nothing of this kind here, taken back")
        CM.set_none(M, page.file, on_)
    done(page, f"{page.file}: nothing of this kind here." if on_ else f"{page.file}: not looked at.")
    return on_


# ------------------------------------------------------------------ the bar beside the piece
def _suggested_kind(page, it):
    from . import typechips as TC
    k = TC.suggested(page, it)
    return k if k in CM.KEYS else ""


def heads_menu(page, parent, fn):
    M = M_of(page)
    m = QMenu(parent or page.view)
    if M is None or not M.outline:
        a = m.addAction("The outline has no heading yet"); a.setEnabled(False)
        return m
    import compliance as C
    for o in M.outline:
        lab = C.outline_label(o)
        m.addAction(("    " * (o.get("level", 1) - 1)) + lab, lambda x=lab: fn(page, x))
    return m


def fill_bar(page, f, rows):
    from . import typechips as TC
    M = M_of(page)
    col = f.col
    it = rows[-1]
    one = len(rows) == 1
    f.kinds, f.lead, f.take, f.pick, f.later, f.where = {}, None, None, None, None, None
    sug = _suggested_kind(page, it) if one and not CM.kinds_of(it) else ""
    for n, (key, name) in enumerate(CM.KINDS, 1):
        b = D.button(f"{n}   {name}", "primary" if key == sug else None, lambda _c=False, k=key: kind(page, k),
                     f"{name} ({n}): a row of the matrix at once" + (". Suggested: Enter takes it and goes on" if key == sug else ""))
        b.setCheckable(True); b.setChecked(all(key in CM.kinds_of(x) for x in rows)); b.setProperty("sk_switch", True)
        b.setStyleSheet("text-align:left;")
        col.addWidget(b); f.kinds[key] = b
        if key == sug:
            f.lead = b
    if one and M.outline and (CM.kinds_of(it) or sug):
        secs = CM.sections_of(M, it)
        want = "" if secs else CM.suggested_section(M, it)
        f.where = QLabel("In Matrix under: " + (", ".join(secs) if secs else "" if want else "not yet in a section")); f.where.setWordWrap(True)
        col.addWidget(f.where)
        if want:
            f.take = D.button(f"{want}  Enter", None, lambda _c=False, x=want: place(page, x), "The section the app suggests. Enter takes it and goes on")
            f.take.setStyleSheet("text-align:left;")
            col.addWidget(f.take)
        f.pick = D.button("Pick another section", "ghost", None, "Any heading of the outline")
        f.pick_menu = heads_menu(page, f.pick, place); f.pick.setMenu(f.pick_menu)
        col.addWidget(f.pick)
        if not secs:
            f.later = D.button("Decide later", "ghost", lambda: go_next(page), "It stays in the matrix, not yet in a section; Matrix > Check lists it")
            col.addWidget(f.later)
    f.x = D.button("Not needed  X", "ghost", lambda: not_needed(page), "Looked at: nothing here for this pass. It leaves the pass's next and can be reopened")
    f.x.setCheckable(True); f.x.setChecked(one and CM.state(M, it) == CM.NOT_NEEDED)
    col.addWidget(f.x)
    f.ask = D.button("Ask a question  A", "ghost", lambda: TC.ask(page), TC.ASK_TIP)
    col.addWidget(f.ask)
    f.setup = D.button("For the setup  S", "ghost", None, "Into a section of the outline as text for the author. Pick the heading")
    f.setup_menu = heads_menu(page, f.setup, send_to_setup); f.setup.setMenu(f.setup_menu)
    f.setup.setCheckable(True); f.setup.setChecked(one and CM.state(M, it) == CM.FOR_SETUP)
    col.addWidget(f.setup)
    return f


def kind(page, key):
    """A kind's button or key: on for the selected pieces, off when they all have it (the type chips' own way)."""
    from . import shredbar as SB
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        page.host.status("Select a piece of the customer's text first.")
        return None
    for it in rows:
        CM.marks(M).pop(it["id"], None)
    out = SB.toggle_piece(page, key, rows)
    done(page)
    return out


def place(page, label):
    """In Matrix under: the selected requirements go into the section."""
    M = M_of(page)
    rows = [it for it in (page.selected() if M is not None else []) if it.get("decision") == "Keep"]
    if not rows:
        page.host.status("Mark the piece a requirement, instruction or criterion first.")
        return 0
    with page.R.group():
        page.R.snap(f"In Matrix under {label}")
        n = AL.assign(M, [it["id"] for it in rows], label)
    done(page, f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: in Matrix under {label}.")
    return n


def not_needed(page):
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        return None
    if any(CM.kinds_of(it) for it in rows):
        page.host.status("This piece is in the matrix. Take its kind off first (press its number again).")
        return None
    to = not all(CM.state(M, it) == CM.NOT_NEEDED for it in rows)
    with page.R.group():
        page.R.snap("Not needed" if to else "Not needed, taken back")
        for it in rows:
            CM.not_needed(M, it, to)
    done(page, f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: " + ("not needed in this pass." if to else "open again in this pass."))
    return to


def for_setup(page):
    if not page.selected():
        page.host.status("Select a piece of the customer's text first.")
        return None
    m = heads_menu(page, None, send_to_setup)
    b = getattr(getattr(page, "sel_bar", None), "setup", None)
    from PySide6.QtGui import QCursor
    m.popup(b.mapToGlobal(b.rect().bottomLeft()) if b is not None else QCursor.pos())
    page._comp_menu = m
    return m


def send_to_setup(page, label):
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        return 0
    with page.R.group():
        page.R.snap("For the setup")
        n = sum(1 for it in rows if CM.for_setup(M, it, label))
    done(page, f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: for the setup, under {label}.")
    return n


def key(page, n):
    """1 to 3 on the page."""
    if not on(page) or not 0 <= n < len(CM.KINDS):
        return None
    return kind(page, CM.KINDS[n][0])


def go_next(page):
    """The next piece of this document the pass has not dealt with, after the one selected."""
    M = M_of(page)
    if M is None or not page.file:
        return None
    rows = CM.open_rows(M, page.file)
    if not rows:
        page.host.status("Nothing left in this document for this pass.")
        return None
    ids = [it["id"] for it in page.R.rows_of(page.file)]
    cur = page.selected()
    at = ids.index(cur[-1]["id"]) if cur and cur[-1]["id"] in ids else -1
    nxt = next((it for it in rows if it["id"] in ids and ids.index(it["id"]) > at), rows[0])
    page.select(nxt["id"])
    return nxt["id"]


def enter(page):
    """Enter: take the suggested kind, then the suggested section, and go on. With nothing to take it stays."""
    M = M_of(page)
    rows = page.selected() if M is not None else []
    if len(rows) != 1:
        return go_next(page)
    it = rows[0]
    took = 0
    if not CM.kinds_of(it):
        k = _suggested_kind(page, it)
        if k:
            kind(page, k); took += 1
            it = next((x for x in M_of(page).items if x["id"] == it["id"]), it)
    M = M_of(page)
    if CM.kinds_of(it) and it.get("decision") == "Keep" and not CM.sections_of(M, it):
        want = CM.suggested_section(M, it)
        if want:
            place(page, want); took += 1
    if not took:
        page.host.status("Nothing suggested for this piece: press 1 to 3, or N for the next piece.")
        return 0
    go_next(page)
    return took
