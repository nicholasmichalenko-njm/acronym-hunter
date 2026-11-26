"""Shred in passes: the Compliance pass on the customer's page (4.72.0; compmark holds what is the pass's own). The
Shred page in a mode of its own, as the Response Structure pass is. Nothing is beside the page but the bar (280): Work
Requirement (SOW), Response Instruction (L), Evaluation Criterion (M) on keys 1 to 3; then "In Matrix under:" with the
section the app suggests (Enter takes it), Pick another section, Decide later; then Not needed (X), Ask a question (A)
and For the setup (S). Enter takes the suggested kind and section and goes to the next piece of the document not dealt
with; N goes on without marking. The document's state in the pass is on the row above the page.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QMenu

import assignlinks as AL
import compmark as CM
import custinfo as CI
import custstruct as CS
import diag
from . import design as D

KEY = "comppass"
MODE = "comp"
WIDE = 256                       # the right margin in this pass: the kinds' names are long


DELIV = "deliv"                  # 4.76.0: the Deliverables pass is this page too, with its own buttons
PASSES = (MODE, DELIV)
STEP_OF = {KEY: MODE, "delivpass": DELIV}


def on(page):
    return getattr(page, "focus", None) in PASSES


def deliv(page):
    return getattr(page, "focus", None) == DELIV


def mk(page):
    """The key the open pass keeps its own marks under."""
    return "deliv_marks" if deliv(page) else "comp_marks"


def rec_of(page):
    import effortrec as RR
    return RR.Record(page.host.ws.root)


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
    want = step in STEP_OF and pg.cx is None
    try:
        install(pg)
        if want:
            pg.focus = STEP_OF[step]
            pg._cust_ask = pg._deliv_ask = pg._deliv_file = None
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
    docs = [] if M is None else (__import__("delivmark").docs(M, rec_of(page)) if deliv(page) else CM.docs(M))
    cur = next((d for d in docs if d["file"] == page.file), None)
    page.comp_state.setVisible(on(page))
    page.comp_state.setText(f"This document: {cur['state']}" if cur else "")
    page.comp_none.setToolTip("You looked: this document asks for nothing to be handed in. It can be unticked." if deliv(page) else
                              "You looked: this document holds no requirement, instruction or criterion. It can be unticked.")
    page.comp_none.setVisible(on(page) and cur is not None and not cur["finds"])
    page.comp_none.blockSignals(True); page.comp_none.setChecked(bool(cur and cur["none"])); page.comp_none.blockSignals(False)
    return cur


def done(page, msg=""):
    if msg:
        page.after(msg)
    fill(page)
    try:
        page.host.stepper.show_for("delivpass" if deliv(page) else KEY)
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
        CM.set_none(M, page.file, on_, "deliv_none" if deliv(page) else "comp_none")
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


def _comp_buttons(page, f, rows, M, it, one, col):
    """The Compliance pass's own buttons: the three kinds, then In Matrix under."""
    if True:
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


def fill_bar(page, f, rows):
    from . import typechips as TC
    M = M_of(page)
    col = f.col
    it = rows[-1]
    one = len(rows) == 1
    f.kinds, f.lead, f.take, f.pick, f.later, f.where = {}, None, None, None, None, None
    f.head, f.head_edit, f.head_level, f.head_ok, f.head_off, f.under, f.send = None, None, None, None, None, None, None
    ask = getattr(page, "_cust_ask", None)
    if ask and one and ask[0] == it["id"]:                             # 4.74.0: Customer heading, proposed; Enter takes it
        col.addWidget(QLabel("Customer heading:"))
        f.head_edit = QLineEdit(f"{ask[1]}: {ask[2]}" if ask[1] else ask[2])
        f.head_edit.setToolTip("The number and title as printed in the customer's document. Change it if the app read it wrong")
        f.head_edit.returnPressed.connect(lambda: head_take(page))
        col.addWidget(f.head_edit)
        f.head_level = QComboBox()
        for lv, nm in CS.LEVELS:
            f.head_level.addItem(nm, lv)
        f.head_level.setCurrentIndex(max(0, f.head_level.findData(ask[3])))
        col.addWidget(f.head_level)
        f.head_ok = D.button("Mark it  Enter", "primary", lambda: head_take(page), "A section or heading of the customer's document. It is not added to our outline")
        col.addWidget(f.head_ok)
        col.addWidget(D.button("Cancel  Esc", "ghost", lambda: head_cancel(page)))
        f.head_edit.setFocus(); f.head_edit.selectAll()
        return f
    if one and CS.is_head(M, it):
        f.under = QLabel("Customer heading: " + CS.label(CS.heads(M)[it["id"]])); f.under.setWordWrap(True)
        col.addWidget(f.under)
        f.head_off = D.button("Take the heading off", "ghost", lambda: head_off(page), "It is no section or heading of the customer's document")
        col.addWidget(f.head_off)
        return f
    if deliv(page):
        if __import__("skqt.delivpass", fromlist=["x"]).buttons(page, f, rows, M, it, one, col) == "ask":
            return f                                                   # 4.77.0: the name, or Attach or Add as new
    else:
        _comp_buttons(page, f, rows, M, it, one, col)
    if one:
        h = CS.above(M, it)
        f.under = QLabel("Under: " + (CS.label(h) if h else (it.get("section") or "no customer heading marked above"))); f.under.setWordWrap(True)
        f.under.setStyleSheet(f"color:{D.tokens()['muted']};")
        col.addWidget(f.under)
    f.head = D.button("Customer heading  H", "ghost", lambda: head_ask(page), "Mark as a section or heading in the Customer Doc Structure")
    col.addWidget(f.head)
    f.send = D.button("Send to Outline", "ghost", lambda: send_outline(page), "It waits on the Outline page to be marked there. The shred is not interrupted")
    f.send.setCheckable(True); f.send.setChecked(one and it["id"] in [x["id"] for x in CS.sent(M)])
    col.addWidget(f.send)
    f.more = D.button("More  M", "ghost", None, "Four captures: Customer info, Objective, Hot button, Graphic need (M, then 1 to 4)")
    f.more_menu = more_menu(page, f.more); f.more.setMenu(f.more_menu)
    col.addWidget(f.more)
    f.x = D.button("Not needed  X", "ghost", lambda: not_needed(page), "Looked at: nothing here for this pass. It leaves the pass's next and can be reopened")
    f.x.setCheckable(True); f.x.setChecked(one and CM.state(M, it, mk(page)) == CM.NOT_NEEDED)
    col.addWidget(f.x)
    f.ask = D.button("Ask a question  A", "ghost", lambda: TC.ask(page), TC.ASK_TIP)
    col.addWidget(f.ask)
    f.setup = D.button("For the setup  S", "ghost", None, "Into a section of the outline as text for the author. Pick the heading")
    f.setup_menu = heads_menu(page, f.setup, send_to_setup); f.setup.setMenu(f.setup_menu)
    f.setup.setCheckable(True); f.setup.setChecked(one and CM.state(M, it, mk(page)) == CM.FOR_SETUP)
    col.addWidget(f.setup)
    return f


def head_ask(page):
    """Customer heading (H): the app proposes the number, title and level from the piece; the bar asks."""
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if len(rows) != 1:
        page.host.status("Select the one piece that is the customer's heading.")
        return None
    num, title, level = CS.propose(rows[0])
    page._cust_ask = (rows[0]["id"], num, title, level)
    __import__("skqt.shredselbar", fromlist=["x"]).later(page)
    return page._cust_ask


def head_take(page):
    """Enter, or Mark it: the heading as shown on the bar (edited or not)."""
    M = M_of(page)
    ask = getattr(page, "_cust_ask", None)
    rows = page.selected() if M is not None else []
    if not ask or len(rows) != 1 or rows[0]["id"] != ask[0]:
        return None
    f = getattr(page, "sel_bar", None)
    num, title, level = ask[1], ask[2], ask[3]
    if f is not None and getattr(f, "head_edit", None) is not None:
        num, title = CS.parse(f.head_edit.text())
        level = f.head_level.currentData() or level
    with page.R.group():
        page.R.snap("Customer heading")
        lab = CS.mark(M, rows[0], num, title, level)
        if lab and (deliv(page) or not CM.kinds_of(rows[0])):
            CM.marks(M, mk(page))[rows[0]["id"]] = "h"                 # a heading is dealt with in this pass
    page._cust_ask = None
    if not lab:
        page.host.status("A heading needs a number or a title.")
        return None
    done(page, f"Customer heading: {lab}. The pieces under it now say so.")
    page.view.setFocus()
    return lab


def head_cancel(page):
    page._cust_ask = None
    __import__("skqt.shredselbar", fromlist=["x"]).later(page)
    page.view.setFocus()


def head_off(page):
    M = M_of(page)
    rows = [it for it in (page.selected() if M is not None else []) if CS.is_head(M, it)]
    if not rows:
        return 0
    with page.R.group():
        page.R.snap("Take the heading off")
        for it in rows:
            CS.unmark(M, it)
            if CM.marks(M, mk(page)).get(it["id"]) == "h":
                CM.marks(M, mk(page)).pop(it["id"])
    done(page, f"{rows[0]['id']}: no longer a customer heading.")
    return len(rows)


def send_outline(page):
    """Send to Outline: the selected pieces wait on the Outline page. A second press takes them back."""
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        page.host.status("Select a piece of the customer's text first.")
        return None
    waiting = {x["id"] for x in CS.sent(M)}
    to = not all(it["id"] in waiting for it in rows)
    with page.R.group():
        page.R.snap("Send to Outline" if to else "Send to Outline, taken back")
        for it in rows:
            CS.send(M, it) if to else CS.unsend(M, it["id"])
    n = len(CS.sent(M))
    done(page, (f"Sent to Outline. {n} piece{'s' if n != 1 else ''} wait there to be marked." if to else "Taken back from Outline."))
    return to


# ------------------------------------------------------------------ More: four captures (4.75.0; his 15:56 to 16:01)
MORE = (("custinfo", "Customer info"), ("objective", "Objective"), ("hot", "Hot button"), ("graphic", "Graphic need"))


def more_menu(page, parent=None):
    """More: 1 Customer info (a contact, or a fact picked from the list), 2 Objective, 3 Hot button, 4 Graphic need.
    The number picks while the menu is open; the menu closes itself after a pick."""
    m = QMenu(parent or page.view)
    sub = m.addMenu("&1  Customer info")
    sub.addAction("A contact...", lambda: capture(page, "contact"))
    for g, items in CI.GROUPS:
        sub.addSection(g)
        for lab, _h in items:
            sub.addAction(lab, lambda x=lab: fact(page, x))
    m.custinfo = sub
    for n, (key, name) in enumerate(MORE[1:], 2):
        m.addAction(f"&{n}  {name}", lambda k=key: capture(page, k))
    return m


def more(page):
    """M: the menu opens beside the piece."""
    if not on(page) or not page.selected():
        if on(page):
            page.host.status("Select a piece of the customer's text first.")
        return None
    m = more_menu(page)
    b = getattr(getattr(page, "sel_bar", None), "more", None)
    from PySide6.QtGui import QCursor
    m.popup(b.mapToGlobal(b.rect().bottomLeft()) if b is not None else QCursor.pos())
    page._more_menu = m
    return m


def capture(page, key, answer=None):
    """Objective, Hot button, Graphic need or a contact: the app's own capture for it, from the selected words."""
    if not page.selected():
        page.host.status("Select a piece of the customer's text first.")
        return None
    out = page._do_capture(key, answer)
    done(page)
    return out


def fact(page, label, replace=None):
    """Customer info: a fact filled from the words dragged across, else the selected piece. One already filled with
    something else asks once before it is replaced."""
    import effortrec as RR
    text, src = page.capture_source()
    if not text:
        page.host.status("Select a piece first (drag across words inside it to take just those).")
        return None
    rec = RR.Record(page.host.ws.root)
    value = CI.guess(label, text)
    try:
        import effort as E
        who = E.user_name()
    except Exception:  # noqa: BLE001
        who = ""
    source = {"doc": (src or {}).get("doc", "") or page.file, "page": (src or {}).get("page", ""), "loc": (src or {}).get("loc", ""),
              "sid": (src or {}).get("sid", "")}
    from . import sharedfacts as SF                                     # 4.78.0: the shared three are one value
    out = SF.set_fact(page.host, label, value, "captured", source, replace)
    if isinstance(out, dict):
        if replace is None:
            from PySide6.QtWidgets import QMessageBox
            cur = out["ask"]
            b = QMessageBox.question(page, label, f"{label} is already filled:\n\n{cur['value']}\n({CI.where(cur)})\n\nReplace it with:\n\n{value}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            return fact(page, label, replace=(b == QMessageBox.Yes))
        return None
    if out in SF.MESSAGES:
        return None
    if out == "set":
        diag.activity("customer_fact_captured")
        page.host.status(f"Customer information: {label} is \u201c{value[:80]}\u201d. Change it on Overview > Customer information.")
    elif out == "same":
        page.host.status(f"{label} is unchanged.")
    return out


def kind(page, key):
    """A kind's button or key: on for the selected pieces, off when they all have it (the type chips' own way)."""
    if deliv(page):
        return __import__("skqt.delivpass", fromlist=["x"]).mark(page, key)
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
    if deliv(page) and any(__import__("delivmark").of_piece(rec_of(page), it) for it in rows):
        page.host.status("This piece is on a deliverable. Take it off the list first.")
        return None
    if not deliv(page) and any(CM.kinds_of(it) for it in rows):
        page.host.status("This piece is in the matrix. Take its kind off first (press its number again).")
        return None
    to = not all(CM.state(M, it, mk(page)) == CM.NOT_NEEDED for it in rows)
    with page.R.group():
        page.R.snap("Not needed" if to else "Not needed, taken back")
        for it in rows:
            CM.not_needed(M, it, to, mk(page))
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
        n = sum(1 for it in rows if CM.for_setup(M, it, label, mk(page)))
    done(page, f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: for the setup, under {label}.")
    return n


def key(page, n):
    """1 to 3 on the page."""
    kinds = __import__("delivmark").KINDS if deliv(page) else CM.KINDS
    if not on(page) or not 0 <= n < len(kinds):
        return None
    return kind(page, kinds[n][0])


def go_next(page):
    """The next piece of this document the pass has not dealt with, after the one selected."""
    M = M_of(page)
    if M is None or not page.file:
        return None
    rows = __import__("delivmark").open_rows(M, rec_of(page), page.file) if deliv(page) else CM.open_rows(M, page.file)
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
    if getattr(page, "_cust_ask", None):
        return head_take(page)
    if deliv(page) and getattr(page, "_deliv_file", None):             # 4.81.0: Its file: the suggestion, else None yet
        DP = __import__("skqt.delivpass", fromlist=["x"])
        fa = DP.file_asking(page, rows)
        if fa:
            return DP.file_take(page, "sugg" if fa.get("sugg") else "none")
        page._deliv_file = None
    if deliv(page) and getattr(page, "_deliv_ask", None):              # 4.77.0: Enter takes the name, or Attach
        DP = __import__("skqt.delivpass", fromlist=["x"])
        return DP.take(page, "attach" if page._deliv_ask.get("near") else "")
    if len(rows) != 1 or deliv(page):                    # the Deliverables pass suggests no kind: Enter goes on
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
