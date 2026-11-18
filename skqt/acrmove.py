"""Decide and move on (4.56.0; UX decisions 19 with Q7, and 107). After Add to effort list (Enter), Not a term (X),
Skip (N), Later (L) or Not a term on this page only, the next find to decide after the one just handled is selected, in
the page's reading order, and its card opens. A find whose term is decided, marked Later or skipped in this pass is
stepped past. None left on the page: the next page with finds to decide, its first find once the page has loaded.
Only Later finds left: the first of them. Nothing left: the page stays and says so.

Skip is for this pass only: the skipped finds are kept in memory until the scan or the document picked changes, or
until nothing else is left ("You have been through every find. N still to decide.").

After every press one line with Undo says what happened (both things after a fix); Undo takes it all back and selects
that find again. Rules only (No AI); nothing leaves the PC."""
import html

import acrlater as LT
import acrpages as AG
import diag

ONLY_LATER = "Only finds marked for later are left."
NOTHING = "Nothing to decide, as of the last scan."


def _say(op, text):
    op.said = text
    try:
        op.page.host.status(text)
    except Exception:  # noqa: BLE001  a host with no status line (tests)
        diag.swallowed()
    return text


def order_of(x):
    """A find's place in the page's reading order: top to bottom, left to right (a picture), or where it starts (text)."""
    if "box" in x:
        return (round(x["box"][1] / 12), x["box"][0], 0)
    return (0, (x.get("span") or (0, 0))[0], 0)


def skipped(op):
    return op.__dict__.setdefault("skip_pass", set())


def unboxed(op):
    """The pages passed in this pass because none of their finds to decide is boxed on the page (the page reader did not
    find the term where the scan did, or the file is not on this PC)."""
    return op.__dict__.setdefault("nobox_pass", set())


def clear_pass(op):
    skipped(op).clear()
    unboxed(op).clear()


def _open_here(op, i, later=False):
    """True when find i on the page shown is one to serve: shown, still to decide, not skipped in this pass; marked
    Later only when later is True (and then only those)."""
    s = op.session
    x = op.items[i]
    if x.get("behind") or not op.visible(i) or not x.get("term"):
        return False
    d = s.results.get(x["term"]) or {}
    if AG.state_of(d) != "decide":
        return False
    if (op.key, x["term"]) in skipped(op):
        return False
    return (x["term"] in LT.marks(s)) == later


def next_here(op, after=None, later=False):
    """The index of the next find to serve on the page shown, after the order key given (round to the page's start
    once), or None."""
    idx = sorted((i for i in range(len(op.items)) if _open_here(op, i, later)), key=lambda i: order_of(op.items[i]))
    if not idx:
        return None
    if after is not None:
        for i in idx:
            if order_of(op.items[i]) > after:
                return i
    return idx[0]


def _pages(op):
    return [p for p in op.shown_pages()]


def _open_page(op, p, later=False):
    """True when the page has a term to serve: still to decide (or marked Later, with later), not skipped there."""
    mk = LT.marks(op.session)
    if p["key"] in unboxed(op):
        return False
    for t, st in p["terms"].items():
        if st != "decide" or (p["key"], t) in skipped(op):
            continue
        if (t in mk) == later:
            return True
    return False


def next_page(op, later=False):
    pgs = _pages(op)
    keys = [p["key"] for p in pgs]
    k = keys.index(op.key) + 1 if op.key in keys else 0
    for p in pgs[k:] + pgs[:k]:
        if p["key"] != op.key and _open_page(op, p, later):
            return p["key"]
    return None


def serve(op, i):
    op.select([i])
    return i


def go_then(op, key, later=False):
    """Show another page and select its first find to serve once it has loaded (a picture is read off the window's
    thread: the selection waits for it)."""
    op.after_load = lambda: _first(op, later)
    op.go(key)
    if op.state != "reading":
        return _loaded(op)
    return key


NOT_BOXED = "{n} to decide on {page} could not be boxed on the page. They are in Everything found."


def _first(op, later):
    """The first find to serve on the page just shown. A page whose finds to decide are not boxed (nothing to select
    there) is passed, with a line saying so, and the move goes on to the next page: it never ends on a page with no card."""
    i = next_here(op, None, later)
    if i is not None:
        serve(op, i)
        if later:
            _say(op, ONLY_LATER)
        return i
    if op.state == "reading":
        return None
    here = next((p for p in _pages(op) if p["key"] == op.key), None)
    n = here["to_decide"] if here else 0
    unboxed(op).add(op.key)
    if n:
        _say(op, NOT_BOXED.format(n=n, page=op.key))
    nxt = next_page(op, later)
    if nxt:
        go_then(op, nxt, later)
    return None


def loaded(op):
    """Called when a page has been drawn (a picture painted, a passage shown)."""
    return _loaded(op)


def _loaded(op):
    fn, op.after_load = getattr(op, "after_load", None), None
    if fn is not None:
        try:
            fn()
        except RuntimeError:                       # the page closed meanwhile
            pass
    return op.key


def move_on(op, after):
    """From the find just handled (its order key): the next to serve here, then the next page, then the Later ones."""
    if op.session is None or not op.key:
        return None
    i = next_here(op, after)
    if i is not None:
        return serve(op, i)
    nxt = next_page(op)
    if nxt:
        return go_then(op, nxt)
    if skipped(op) or unboxed(op):                    # only skipped finds, or finds no page boxes, are left: the pass ends
        left = sum(p["to_decide"] for p in _pages(op))
        nobox = bool(unboxed(op)) and not skipped(op)
        clear_pass(op)
        if left:
            return _say(op, f"{left} still to decide could not be boxed on a page. They are in Everything found." if nobox
                        else f"You have been through every find. {left} still to decide.")
    i = next_here(op, None, later=True)
    if i is not None:
        serve(op, i)
        return _say(op, ONLY_LATER)
    nxt = next_page(op, later=True)
    if nxt:
        return go_then(op, nxt, later=True)
    return _say(op, NOTHING)


def handled(op):
    """The order key of the last selected find (where the move starts), or None."""
    xs = op.selected()
    return max(order_of(x) for x in xs) if xs else None


def decided(op, msg="", undo=None, move=True, line=None):
    """Every decision ends here. line: the sentence for the line with Undo; undo: a function that takes the press back.
    Then the page and the list are drawn again and (move) the next find to decide is selected."""
    after = handled(op)
    if line is not None:
        op.undo = {"line": line, "fn": undo, "find": (op.key, after)} if undo is not None else None
        op.undo_lab.setText(html.escape(line) + (" <a href='u'>Undo</a>" if undo is not None else ""))
    if msg:
        op.page.host.toast(msg)
    op.sel, op.new_text, op.new_area = [], "", None
    op.close_bar()
    op.page.from_page = True                         # 4.30.3: the list behind this tab is built when it is opened
    try:
        op.page.fill()                               # the counts and this page (acrtabs.after_fill)
    finally:
        op.page.from_page = False
    if move and after is not None:
        move_on(op, after)
    return msg or line or ""


def skip(op):
    """Skip (N): nothing changes; the find is passed for this pass and the next one is served."""
    after = handled(op)
    for x in op.selected():
        skipped(op).add((op.key, x["term"]))
    diag.activity("acronym_page_skipped")
    op.close_bar()
    op.sel = []
    if op.state == "picture":
        op.draw_boxes()
    if after is not None:
        move_on(op, after)
    return after


def undo_last(op):
    u = op.undo
    if not u:
        return 0
    op.undo = None
    op.undo_lab.setText("")
    n = u["fn"]() if u.get("fn") else 0
    op.page.fill()
    key, at = u.get("find") or (None, None)
    if key and at is not None:
        def back():
            idx = [i for i, x in enumerate(op.items) if order_of(x) == at and op.visible(i)]
            if idx:
                op.select(idx[:1])
        if op.key != key:
            op.after_load = back
            op.go(key)
            if op.state != "reading":
                _loaded(op)
        else:
            back()
    _say(op, "Taken back.")
    return n or 1
