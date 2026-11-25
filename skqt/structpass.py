"""Shred in passes: the Response Structure pass on the customer's page (4.70.0; structmark holds the rules). The Shred
page in a mode of its own, as Place is: the bar beside the selected piece has the pass's buttons and nothing else:
Volume, Heading 1, Heading 2, Heading 3 (keys 1 to 4), Not needed (X), Ask a question, and Take the mark off. A piece
that lists several sections shows each item as a ticked line. A near match asks once on the bar: Same as [the
heading]? Attach (Enter) or Add as new. Enter takes the suggestion and goes to the next one, across the documents; N
goes on without marking. The outline sits beside the page as a tree and fills as he marks; a heading's row selects the
piece that required it. Above the tree, this document's state in the pass, and Nothing of this kind here.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QCheckBox, QFrame, QLabel, QMenu, QTreeWidget, QTreeWidgetItem, QVBoxLayout

import diag
import structmark as SM
from . import design as D

KEY = "structpass"
MODE = "struct"


def on(page):
    return getattr(page, "focus", None) == MODE


def M_of(page):
    return page.R.M if page.R is not None else None


class OutlineTree(QTreeWidget):
    """The outline beside the page. 4.71.0 (209): a heading can be dragged to fix its level or place; the drop is
    carried out on the outline itself (with everything under the heading) and the tree is drawn again from it."""
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def dropEvent(self, e):
        src = self.currentItem()
        tgt = self.itemAt(e.position().toPoint() if hasattr(e, "position") else e.pos())
        where = {QAbstractItemView.OnItem: "into", QAbstractItemView.AboveItem: "before",
                 QAbstractItemView.BelowItem: "after"}.get(self.dropIndicatorPosition())
        e.setDropAction(Qt.IgnoreAction); e.accept()
        if src is not None and tgt is not None and where:
            moved(self.page, src.text(0), tgt.text(0), where)


# ------------------------------------------------------------------ the mode
def install(page):
    """Once: the outline tree and the document's state, as a third pane of the page's splitter."""
    if getattr(page, "struct_panel", None) is not None:
        return page.struct_panel
    f = QFrame(); f.setObjectName("card")
    v = QVBoxLayout(f); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"]); v.setSpacing(D.SPACE["s"])
    v.addWidget(D.label("The outline", "h3"))
    page.struct_state = D.label("", "muted")
    v.addWidget(page.struct_state)
    page.struct_none = QCheckBox("Nothing of this kind in this document")
    page.struct_none.setToolTip("You looked: this document says nothing about how the response is organized. It can be unticked.")
    page.struct_none.clicked.connect(lambda c=False: set_none(page, bool(c)))
    v.addWidget(page.struct_none)
    page.struct_sent = D.button("", "ghost", lambda: go_next(page), "Pieces sent here from Shred with Send to Outline: the next one, on the page")
    v.addWidget(page.struct_sent)
    t = page.struct_tree = OutlineTree(page)
    t.setHeaderLabels(["Heading", "Required by"])
    t.setRootIsDecorated(False); t.setIndentation(14)
    t.setColumnWidth(0, 250)
    t.itemClicked.connect(lambda it, _c=0: show_piece(page, it.data(0, Qt.UserRole)))
    v.addWidget(t, 1)
    page.struct_hint = D.label("", "muted")
    v.addWidget(page.struct_hint)
    page.struct_panel = f
    f.setVisible(False)
    page.page_split.addWidget(f)
    page._struct_ask = None
    page._struct_lines = {}
    return f


def apply(w, step):
    """After go(step) opened the Shred page (after placemode): the pass's mode for its tab, and out of it for any other."""
    pg = w.assign_page
    want = step == KEY and pg.cx is None
    try:
        install(pg)
        side, sp = pg.page_side, pg.page_split
        sizes = lambda a, b: sp.setSizes([1000 if i == 0 else a if sp.widget(i) is side else b if sp.widget(i) is pg.struct_panel else 0
                                          for i in range(sp.count())])
        if want:
            pg.focus = MODE
            pg._struct_ask = None
            for name in ("shred_check", "queue_lbl", "reshred_btn"):
                x = getattr(pg, name, None)
                if x is not None:
                    x.setVisible(False)
            if getattr(pg, "progress_row", None) is not None:
                pg.progress_row.setVisible(False)
            side.setVisible(False)
            pg.struct_panel.setVisible(True)
            sizes(0, 430)
            __import__("skqt.shredselbar", fromlist=["x"]).gutter(pg, True)
            fill(pg)
            __import__("skqt.shredselbar", fromlist=["x"]).later(pg)
            from PySide6.QtCore import QTimer             # 4.74.0: the page at the width of its pane, once the panes have their sizes
            QTimer.singleShot(0, lambda: pg.view.fit() if on(pg) and pg.file else None)
        elif pg.struct_panel.isVisibleTo(pg) or not side.isVisibleTo(pg):
            pg.struct_panel.setVisible(False)
            side.setVisible(True)
            sizes(430, 0)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    __import__("skqt.comppass", fromlist=["x"]).apply(w, step)       # 4.72.0: the Compliance pass, after this one
    return want


def fill(page):
    """The tree, the document's state and the hint, from the matrix as it is now."""
    M = M_of(page)
    t = page.struct_tree
    t.clear()
    if M is None:
        page.struct_state.setText(""); page.struct_none.setVisible(False); page.struct_hint.setText(""); page.struct_sent.setVisible(False)
        return 0
    stack = []
    for r in SM.tree(M):
        it = QTreeWidgetItem([r["label"], r["ref"]])
        it.setData(0, Qt.UserRole, r["req"])
        it.setToolTip(0, r["label"]); it.setToolTip(1, r["ref"] or "Not from a piece of the customer's text")
        while stack and stack[-1][0] >= r["level"]:
            stack.pop()
        (stack[-1][1].addChild(it) if stack else t.addTopLevelItem(it))
        stack.append((r["level"], it))
    t.expandAll()
    cur = next((d for d in SM.docs(M) if d["file"] == page.file), None)
    page.struct_state.setText(f"This document: {cur['state']}" if cur else "No document is open.")
    page.struct_none.setVisible(cur is not None and not cur["finds"])
    page.struct_none.blockSignals(True); page.struct_none.setChecked(bool(cur and cur["none"])); page.struct_none.blockSignals(False)
    shut = False
    import custstruct as CS                          # 4.74.0: what Shred sent here waits to be marked
    nsent = len([x for x in CS.sent(M) if x.get("id") not in SM.marks(M)])
    page.struct_sent.setVisible(bool(nsent))
    page.struct_sent.setText(f"{nsent} piece{'s' if nsent != 1 else ''} sent from Shred to mark: show the next")
    if SM.closed(M):                                 # 4.73.0: 4.71.0's "Not required by the customer" is Outline's "We build it"
        import setupdoc as SD
        SD.setup_of(M).setdefault("outline_from", "ours"); SD.setup_of(M).setdefault("outline_reason", "No structure given")
        SM.set_closed(M, False)
    left = len(SM.suggestions(M))
    page.struct_hint.setText("Closed: the customer does not require a structure. Drag a heading to fix its level or place." if shut else
                             (f"{left} piece{'s' if left != 1 else ''} the app reads as setting the structure. Enter takes one and goes to the next. "
                              "Drag a heading to fix its level or place.") if left else "Nothing more is suggested. Select any piece to mark it. Drag a heading to fix its level or place.")
    return t.topLevelItemCount()


def set_none(page, on_=True):
    M = M_of(page)
    if M is None or not page.file:
        return None
    with page.R.group():
        page.R.snap("Nothing of this kind here" if on_ else "Nothing of this kind here, taken back")
        SM.set_none(M, page.file, on_)
    done(page, f"{page.file}: nothing of this kind here." if on_ else f"{page.file}: not looked at.")
    return on_


def set_closed(page, on_=True):
    """Not required by the customer: the pass is closed in one click, and opened again the same way."""
    M = M_of(page)
    if M is None:
        return None
    with page.R.group():
        page.R.snap("Not required by the customer" if on_ else "Response Structure, open again")
        SM.set_closed(M, on_)
    done(page, "Response Structure: not required by the customer. The pass is closed." if on_ else "Response Structure is open again.")
    return on_


def moved(page, label, target, where):
    """A heading dragged on the tree: before, after or into another. One Undo step."""
    M = M_of(page)
    if M is None or label == target:
        return None
    with page.R.group():
        page.R.snap(f"Move {label}")
        new = SM.move(M, label, target, where)
    if new is None:
        page.host.status(f"{label} cannot go there.")
        fill(page)
        return None
    done(page, f"{label} moved: now {new}.")
    return new


def setup_menu(page, parent=None):
    """For the setup: the outline's headings to pick from (indented by level)."""
    M = M_of(page)
    m = QMenu(parent or page.view)
    rows = SM.tree(M) if M is not None else []
    if not rows:
        a = m.addAction("The outline has no heading yet: mark one first"); a.setEnabled(False)
    for r in rows:
        m.addAction(("    " * (r["level"] - 1)) + r["label"], lambda lab=r["label"]: send_to_setup(page, lab))
    return m


def for_setup(page):
    """S: the list of headings opens beside the piece; a pick sends the piece there as text for the author."""
    if getattr(page, "focus", None) in ("comp", "deliv"):
        return __import__("skqt.comppass", fromlist=["x"]).for_setup(page)
    if not on(page) or not page.selected():
        if on(page):
            page.host.status("Select a piece of the customer's text first.")
        return None
    m = setup_menu(page)
    b = getattr(getattr(page, "sel_bar", None), "setup", None)
    from PySide6.QtGui import QCursor
    m.popup(b.mapToGlobal(b.rect().bottomLeft()) if b is not None else QCursor.pos())
    page._struct_menu = m
    return m


def send_to_setup(page, label):
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        return 0
    with page.R.group():
        page.R.snap("For the setup")
        n = sum(1 for it in rows if SM.for_setup(M, it, label))
    done(page, f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: for the setup, under {label}.")
    return n


def ask(page):
    """A: Ask a question, in the pass (the button does the same)."""
    if getattr(page, "focus", None) not in (MODE, "comp", "deliv") or not page.selected():
        return None
    from . import typechips as TC
    return TC.ask(page)


def show_piece(page, iid):
    """A heading's row: the piece that required it, on the page (its document opened when it is another one)."""
    M = M_of(page)
    it = next((x for x in M.items if x.get("id") == iid), None) if M is not None and iid else None
    if it is None:
        return None
    if it.get("file") and it["file"] != page.file:
        page.open_file(it["file"])
    page.select(iid)
    return iid


# ------------------------------------------------------------------ the bar beside the piece
def fill_bar(page, f, rows):
    """The pass's buttons, into the bar's frame (shredselbar.build made the frame and its column)."""
    from . import typechips as TC
    M = M_of(page)
    col = f.col
    it = rows[-1]
    one = len(rows) == 1
    f.levels, f.lines, f.attach, f.new, f.off, f.lead = {}, [], None, None, None, None
    ask = page._struct_ask if page._struct_ask and page._struct_ask[0] == it["id"] and one else None
    if ask:
        lab = QLabel(f"Same as “{ask[2][0]['label']}”?"); lab.setWordWrap(True)
        col.addWidget(lab)
        f.attach = D.button("Attach  Enter", "primary", lambda: press(page, ask[1], attach=True), "The heading is already in the outline: this piece is another place the customer asks for it")
        f.new = D.button("Add as new", None, lambda: press(page, ask[1], attach=False), "A heading of its own")
        col.addWidget(f.attach); col.addWidget(f.new)
        return f
    cur = SM.level_of(M, it) if one else ""
    sug = SM.suggest(M, it) if one else ""
    lines = SM.lines(M, it) if one else []
    if len(lines) > 1:
        kept = page._struct_lines.setdefault(it["id"], set(SM.norm(x) for x in lines))
        for t in lines:
            c = QCheckBox(t); c.setChecked(SM.norm(t) in kept)
            c.toggled.connect(lambda o, k=SM.norm(t), s=kept: (s.add(k) if o else s.discard(k)))
            col.addWidget(c); f.lines.append(c)
    for n, (key, name) in enumerate(SM.LEVELS, 1):
        b = D.button(f"{n}   {name}", "primary" if key == sug else None, lambda _c=False, k=key: press(page, k),
                     f"{name} of our response ({n})" + (". Suggested: Enter takes it and goes to the next" if key == sug else ""))
        b.setCheckable(True); b.setChecked(key == cur); b.setProperty("sk_switch", True)
        b.setStyleSheet("text-align:left;")
        col.addWidget(b); f.levels[key] = b
        if key == sug:
            f.lead = b
    f.x = D.button("Not needed  X", "ghost", lambda: not_needed(page), "Looked at: nothing here for this pass. It leaves the pass's next and can be reopened")
    f.x.setCheckable(True); f.x.setChecked(one and cur == SM.NOT_NEEDED)
    col.addWidget(f.x)
    f.ask = D.button("Ask a question  A", "ghost", lambda: TC.ask(page), TC.ASK_TIP)
    col.addWidget(f.ask)
    f.setup = D.button("For the setup  S", "ghost", None, "Into a section of the outline as text for the author. Pick the heading")
    f.setup_menu = setup_menu(page, f.setup); f.setup.setMenu(f.setup_menu)
    f.setup.setCheckable(True); f.setup.setChecked(one and cur == SM.FOR_SETUP)
    col.addWidget(f.setup)
    if cur in SM.DEPTH and one and it["id"] in SM.marks(M):
        f.off = D.button("Take the mark off", "ghost", lambda: unmark(page), "The piece is no heading; a heading the mark made, with nothing in it, goes too")
        col.addWidget(f.off)
    return f


def _titles(page, M, it):
    lines = SM.lines(M, it)
    kept = page._struct_lines.get(it["id"])
    return [t for t in lines if kept is None or SM.norm(t) in kept] if len(lines) > 1 else lines


def done(page, msg):
    page._struct_ask = None
    page.after(msg)
    fill(page)
    __import__("skqt.shredselbar", fromlist=["x"]).later(page)
    return msg


def press(page, level, attach=None):
    """A level's button or key on the selected pieces. A near match asks on the bar first and changes nothing."""
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        page.host.status("Select a piece of the customer's text first.")
        return None
    made = attached = 0
    for it in rows:
        titles = _titles(page, M, it)
        if not titles:
            page.host.status("No line is ticked.")
            continue
        if attach is None and len(rows) == 1:
            ask = SM.asks(M, it, level, titles)
            if ask:
                page._struct_ask = (it["id"], level, ask)
                __import__("skqt.shredselbar", fromlist=["x"]).later(page)
                page.host.status(f"Same as “{ask[0]['label']}”? Enter attaches; Add as new makes a heading of its own.")
                return {"ask": ask}
        with page.R.group():
            page.R.snap(SM.NAME[level])
            res = SM.mark(M, it, level, titles, attach=bool(attach) if attach is not None else False)
        made += len(res["made"]); attached += len(res["attached"])
    diag.activity("struct_marked", n=len(rows), added=made)
    who = rows[0]["id"] if len(rows) == 1 else f"{len(rows)} pieces"
    what = ", ".join(x for x in (f"{made} added to the outline" if made else "", f"{attached} attached" if attached else "") if x) or "nothing changed"
    done(page, f"{who}: {SM.NAME[level]} ({what})")
    return {"made": made, "attached": attached}


def unmark(page):
    M = M_of(page)
    rows = [it for it in (page.selected() if M is not None else []) if it["id"] in SM.marks(M)]
    if not rows:
        return 0
    with page.R.group():
        page.R.snap("Take the mark off")
        for it in rows:
            SM.unmark(M, it)
    done(page, f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: the mark is off.")
    return len(rows)


def not_needed(page):
    """Not needed, on or off, for the selected pieces."""
    M = M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        return None
    to = not all(SM.level_of(M, it) == SM.NOT_NEEDED and it["id"] in SM.marks(M) for it in rows)
    with page.R.group():
        page.R.snap("Not needed" if to else "Not needed, taken back")
        for it in rows:
            SM.not_needed(M, it, to)
    done(page, f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: " + ("not needed in this pass." if to else "open again in this pass."))
    return to


def key(page, n):
    """1 to 4 on the page."""
    if getattr(page, "focus", None) in ("comp", "deliv"):                       # 4.72.0: 1 to 3 in the Compliance pass
        return __import__("skqt.comppass", fromlist=["x"]).key(page, n)
    if not on(page) or not 0 <= n < len(SM.LEVELS):
        return None
    return press(page, SM.LEVELS[n][0])


def typed(page, type_key):
    """A type's own key pressed in this pass: Not applicable's key (X) is Not needed; the others say where they are."""
    if type_key == "not_applicable":
        return not_needed(page)
    page.host.status("Here you mark Volume and Heading 1 to 3 (keys 1 to 4). The other types are in Shred.")
    return None


def go_next(page, after_id=None):
    M = M_of(page)
    if M is not None and SM.closed(M):
        page.host.status("This pass is closed: not required by the customer. Untick it to go on.")
        return None
    nxt = SM.next_suggestion(M, after_id) if M is not None else None
    if nxt is None:
        page.host.status("Nothing more is suggested in this pass.")
        return None
    return show_piece(page, nxt["id"])


def enter(page):
    """Enter: Attach when the bar asks; else take the selected piece's suggestion and go to the next suggestion."""
    M = M_of(page)
    rows = page.selected() if M is not None else []
    if page._struct_ask and rows and rows[-1]["id"] == page._struct_ask[0]:
        return press(page, page._struct_ask[1], attach=True)
    if len(rows) != 1:
        return go_next(page, rows[-1]["id"] if rows else None)
    lvl = SM.suggest(M, rows[0])
    if not lvl:
        page.host.status("No suggestion for this piece: press 1 to 4, or N for the next suggestion.")
        return None
    res = press(page, lvl)
    if res and "ask" not in res:
        go_next(page, rows[0]["id"])
    return res


def next_open(page):
    """N: the next suggestion after the selected piece, without marking."""
    rows = page.selected()
    return go_next(page, rows[-1]["id"] if rows else None)
