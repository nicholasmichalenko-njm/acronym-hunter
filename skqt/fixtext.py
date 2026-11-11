"""Fix text, a mode inside Shred (4.2.0; claude/stationkeeper-fix-text-decisions-2026-11-10.md, decisions 1 and 8).
F2 (or the Fix text button) turns it on: a strip over the page holds the tools for text that came out wrong, on the
same continuous page and the same Undo as the shred: Combine (J), Split (S), Make a sentence (Shift+S), Heading, Set
aside (a page header, footer or banner; More: every line like it), Add missed text, and Page checked (Ctrl+Enter, the
main button). The strip says how far the document is checked ("37 of 120 pages checked") and never holds the shred up.
Text check is no longer a tab of Documents: go("verify") opens Shred in Fix text; the page-by-page check stays under
More for its own tools (a misread corrected, a block's role).

Pages checked are kept where Text check kept them (verifystate), so Documents' panel still counts them.
Rules only (No AI); nothing leaves the PC."""
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu

import diag
from . import design as D

KEY = "F2"
ASIDE_NOTE = "Set aside: a page header, footer or banner"


def install(page, bar, v):
    page.fix_on = False
    page.fix_btn = D.button("Fix text", None, lambda: toggle(page), "Fix text that came out wrong: combine, split, a heading, "
                            "a header or footer set aside, missed text, pages checked (F2)")
    page.fix_btn.setCheckable(True)
    bar.addWidget(page.fix_btn)
    s = page.fix_strip = QFrame(); s.setObjectName("fixBar")
    s.setStyleSheet("QFrame#fixBar{background:rgba(180,83,9,0.07);border:1px dashed rgba(180,83,9,0.6);border-radius:6px;}")
    h = QHBoxLayout(s); h.setContentsMargins(D.SPACE["m"], D.SPACE["xs"], D.SPACE["m"], D.SPACE["xs"]); h.setSpacing(D.SPACE["s"])
    page.fix_lbl = D.label("", "body"); h.addWidget(page.fix_lbl, 1)
    page.fix_tools = {}
    for name, fn, tip in (("Combine  J", lambda: page.do_combine(), "One piece from the selected ones, across pages too"),
                          ("Split  S", lambda: page.do_split(), "Split the selected piece at the word you clicked"),
                          ("Heading", lambda: heading(page), "The selected piece is a heading of the customer's, not text to answer"),
                          ("Set aside", lambda: set_aside(page), "A page header, footer, page number or banner: out of the shred, "
                           "still shown on the page"),
                          ("Add missed text", lambda: page.toggle_capture(), "Draw a box around text the reader missed")):
        b = D.button(name, None, fn, tip); h.addWidget(b); page.fix_tools[name.split("  ")[0]] = b
    page.fix_sus = D.button("Suspects", None, lambda: next_suspect(page), "The next piece worth a look: a join across "
                            "pages, a page that ends mid-sentence, a fragment, a broken word (F3)")
    h.addWidget(page.fix_sus)
    page.fix_keep = D.button("Keep the join", None, lambda: keep_join(page), "The page break split this sentence; joined is right")
    page.fix_unjoin = D.button("Undo the join", None, lambda: undo_join(page), "Two pieces again, at the page break")
    for b in (page.fix_keep, page.fix_unjoin):
        b.setVisible(False); h.addWidget(b)
    page.fix_cur = None
    more = D.button("More", None, None, "More ways to fix text")
    m = QMenu(more); more.setMenu(m)
    m.addAction("Set aside every line like this", lambda: set_aside(page, every=True))
    m.addAction("Page by page check...", lambda: page_by_page(page))
    page.page_mode_act = m.addAction("One page at a time")                # 4.2.0: Page mode (decision 7)
    page.page_mode_act.setCheckable(True)
    page.page_mode_act.toggled.connect(lambda on: page.canvas.page_mode(on) if getattr(page, "canvas", None) else None)
    h.addWidget(more)
    page.fix_checked = D.button("Page checked", "primary", lambda: page_checked(page),
                                "This page reads right (Ctrl+Enter): counted, never a gate")
    h.addWidget(page.fix_checked)
    s.setVisible(False)
    v.addWidget(s)
    for seq, fn in ((KEY, lambda: toggle(page)), ("Ctrl+Return", lambda: page_checked(page) if page.fix_on else None),
                    ("F3", lambda: next_suspect(page) if page.fix_on else None),
                    ("PgDown", lambda: page.canvas.step(1) if getattr(page, "canvas", None) else None),
                    ("PgUp", lambda: page.canvas.step(-1) if getattr(page, "canvas", None) else None)):
        sc = QShortcut(QKeySequence(seq), page, activated=fn)
        sc.setContext(Qt.WidgetWithChildrenShortcut)          # only while Shred has the focus


def toggle(page, on=None):
    on = (not page.fix_on) if on is None else bool(on)
    page.fix_on = on
    page.fix_btn.setChecked(on)
    page.fix_strip.setVisible(on)
    if on:
        refresh(page)
        diag.activity("fix_text_on")
    return on


# ------------------------------------------------------------------ pages checked
def _store(page):
    import verifystate as VS
    ws = page.host.ws
    return VS.Store(ws.root) if ws is not None else None


def page_now(page):
    """The page in the middle of the view (1-based), or 0 with no page open."""
    tops = getattr(page, "tops", None) or []
    if not tops:
        return 0
    mid = page.view.mapToScene(page.view.viewport().rect().center()).y()
    n = 1
    for i, y in enumerate(tops):
        if y <= mid:
            n = i + 1
    return n


def checked(page):
    """(pages checked, pages) of the open document."""
    st = _store(page)
    n = len(getattr(page, "tops", None) or [])
    if st is None or not page.file or not n:
        return 0, n
    d = st.doc(page.file)
    return sum(1 for k in d.get("verified", {}) if k not in d.get("reopened", {}) and k.isdigit() and int(k) <= n), n


def page_checked(page, n=None):
    """Mark the page in view checked; the view moves to the next page. Returns the page number."""
    st = _store(page)
    n = n or page_now(page)
    if st is None or not page.file or not n:
        return 0
    st.verify(page.file, n)
    diag.activity("fix_text_page_checked")
    tops = getattr(page, "tops", [])
    if n < len(tops):
        page.view.centerOn(page.view.mapToScene(page.view.viewport().rect().center()).x(), tops[n] + page.view.viewport().height() / 2 - 40)
    refresh(page)
    return n


def refresh(page):
    if not getattr(page, "fix_on", False):
        return ""
    c, n = checked(page)
    text = (f"<b>Fix text</b> &nbsp;{c} of {n} pages checked" if n else "<b>Fix text</b> &nbsp;Pick a document") + \
        " &nbsp;·&nbsp; select pieces (across pages too), then a tool. Nothing here holds the shred up."
    page.fix_lbl.setTextFormat(Qt.RichText)
    page.fix_lbl.setText(text)
    n_s = len(suspects(page))
    page.fix_sus.setText(f"Suspects ({n_s})" if n_s else "No suspects")
    page.fix_sus.setEnabled(bool(n_s))
    return text


# ------------------------------------------------------------------ suspects (pagejoin)
def suspects(page):
    import pagejoin as PJ
    if page.R is None or page.cx is not None or not page.file:
        return []
    return PJ.suspects(page.M.items, page.file) + headers_set_aside(page)


def headers_set_aside(page):
    """4.5.0 (loose end): the lines set aside as running headers or footers, one per wording, page numbers left out:
    the rule can set aside real text that repeats with only its numbers changed. [("header", {"id": "", "page", "text"},
    why)]."""
    import pagesent as PS
    if not page.pdf or not str(page.pdf).lower().endswith(".pdf"):
        return []
    try:
        doc = PS.doc_of(page.pdf)
        skip = PS.running(doc)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return []
    seen, out = {}, []
    for pi, li in sorted(skip):
        txt = doc["pages"][pi]["lines"][li]["text"].strip()
        if not txt or PS._PAGE_NO.match(txt):
            continue
        k = PS._norm(txt)
        seen.setdefault(k, []).append(pi + 1)
    for k, pages in seen.items():
        pi, li = next((pi, li) for pi, li in sorted(skip) if PS._norm(doc["pages"][pi]["lines"][li]["text"].strip()) == k)
        txt = doc["pages"][pi]["lines"][li]["text"].strip()
        n = len(set(pages))
        out.append(("header", {"id": "", "page": pages[0], "text": txt},
                    f"Set aside as a running header or footer on {n} page{'s' if n != 1 else ''}: \u201c{txt[:80]}\u201d. "
                    "If it is the customer's text, More > Add missed text and drag around it."))
    return out


def next_suspect(page):
    """Select the next suspect after the one shown (round to the start); say why. Returns (kind, item, why) or None."""
    sus = suspects(page)
    if not sus:
        refresh(page)
        return None
    ids = [it["id"] or f"p{it.get('page')}:{it.get('text', '')}" for _k, it, _w in sus]
    cur = page.fix_cur
    i = (ids.index(cur) + 1) % len(ids) if cur in ids else 0
    kind, it, why = sus[i]
    page.fix_cur = ids[i]
    if it["id"]:
        page.select(it["id"])
    elif getattr(page, "canvas", None) is not None:              # 4.5.0: a line set aside has no piece: its page
        page.canvas.go_page(it.get("page") or 1)
    page.fix_keep.setVisible(kind == "join"); page.fix_unjoin.setVisible(kind == "join")
    page.host.status(f"{it['id']}: {why}")
    return kind, it, why


def keep_join(page):
    import pagejoin as PJ
    it = page.R.item(page.fix_cur) if page.fix_cur and page.R is not None else None
    if it is None or not PJ.keep(it):
        return False
    page.M.pending = True
    page.host.changed()
    page.fix_keep.setVisible(False); page.fix_unjoin.setVisible(False)
    refresh(page)
    return True


def undo_join(page):
    """Split the joined piece back at the page break (one Undo step). Returns the parts."""
    import pagejoin as PJ
    it = page.R.item(page.fix_cur) if page.fix_cur and page.R is not None else None
    at = PJ.unjoin_at(it) if it is not None else None
    if at is None:
        return []
    parts = page.R.split(it, at)
    for p in parts or []:
        if PJ.joined(p):
            p["new"] = ""
    page.M.pending = True
    page.host.changed()
    page.fix_keep.setVisible(False); page.fix_unjoin.setVisible(False)
    page.fix_cur = None
    page.after("the join undone")
    refresh(page)
    return parts


# ------------------------------------------------------------------ heading, set aside
def heading(page):
    rows = page.selected() if page.R is not None and page.cx is None else []
    if not rows:
        return page.host.status("Select the piece that is a heading first.")
    page.R.snap("a heading")
    for it in rows:
        it.update(type="Heading", header="Yes", decision="Drop")
        page.M.log(it["id"], "fix text: a heading")
    page.M.pending = True
    page.host.changed()
    page.after(f"{len(rows)} heading(s)")
    return len(rows)


def _shape(t):
    return re.sub(r"\d+", "#", " ".join((t or "").lower().split()))


def set_aside(page, every=False):
    """The selected pieces (every=True: and every piece of the document that reads like them, page numbers aside) are a
    page header, footer or banner: out of the shred, still shown greyed on the page. Undo puts them back."""
    rows = page.selected() if page.R is not None and page.cx is None else []
    if not rows:
        return page.host.status("Select the header, footer or banner first.")
    if every:
        shapes = {_shape(it.get("text")) for it in rows}
        rows = [it for it in page.M.items if it.get("file") == page.file and _shape(it.get("text")) in shapes]
    import shredtypes as ST
    page.R.snap("set aside")
    for it in rows:
        it["decision"] = "Drop"
        it[ST.FIELD] = "not_applicable"
        if ASIDE_NOTE not in (it.get("notes") or ""):
            it["notes"] = ((it.get("notes") or "") + ("; " if it.get("notes") else "") + ASIDE_NOTE)
        page.M.log(it["id"], "fix text: set aside")
    page.M.pending = True
    page.host.changed()
    page.after(f"{len(rows)} set aside")
    return len(rows)


def page_check(h):
    """Open the page-by-page check itself (go("verify") opens Shred in Fix text)."""
    h._page_check = True
    try:
        return h.go("verify")
    finally:
        h._page_check = False


def page_by_page(page):
    """The page-by-page check (Text check's own page) for its own tools, opened on this document."""
    h = page.host
    page_check(h)
    path = page.M.path_of(page.file) if page.M is not None and page.file else ""
    if path:
        try:
            h.verify_page.open_doc(path)
        except Exception:  # noqa: BLE001
            diag.swallowed()
    return True
