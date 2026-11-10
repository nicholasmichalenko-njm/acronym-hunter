"""Acronyms on the page (3.92.0; claude/stationkeeper-acronyms-on-the-page-3.92.md): the page in three panes. The terms on
the left (filters as counts you click), the customer's page in the middle where the term was found (the found view, made
large), the card on the right; a line from the words that spell the term out to the definition picked, through the
gutter. One command bar: Next to decide, Add a term, In our drafts, More (every scan and tool), Export. Keys on the card:
1 to 4 pick a definition, Enter adds to the list, X says Not a term. The card says when a find sits inside a longer term
(DC in DC-RVM), shows where the term goes (the A to Z rows of the Acronyms table) and its sources over the effort.
acrpage holds the rules. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractButton, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLineEdit, QPushButton,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import acrpage as P
import app_gui as A
import diag
from . import design as D
from .adaptive import FlowLayout
from .commandbar import CommandBar
from .splitlines import SplitView

KEEP_COLS = (0, 5, 6)                       # Term, Status, Definition; the rest stay in Export and Details
LIST_COLS = (0, 1, 5, 6, 9)                 # 3.93.0 The list: Term, Type, Status, Definition, Source (the tool: KEEP_COLS)


def install(page):
    """Rearranges the page built by AcronymPage.__init__ (its widgets and their names stay, for the tools and tests)."""
    v = page.layout()
    page.list_w = QWidget()                                # 3.93.0: The list, one of two tabs
    lv = QVBoxLayout(page.list_w); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(D.SPACE["m"])
    # the bar
    bar = CommandBar(page)
    page.bar = bar
    page.b_next = bar.add("Next to decide", lambda: next_to_decide(page), "The next term to decide, in the list's order")
    bar.add("Add a term", lambda: __import__("skqt.acrextras", fromlist=["x"]).add_term(page),
            "A term the scan did not find: select its words on the page, or type it")
    page.b_drafts = bar.primary("In our drafts", lambda: open_drafts(page), "Each volume's draft against the list: first use, "
                                "spelled out again, the volume's Acronyms table")
    for b in (page.b_cust, page.b_files, page.b_lib, page.b_again, page.b_paste, page.b_window):
        bar.more(b.text(), b.click, b.toolTip())
        b.setVisible(False)
    bar.more_sep()
    for b in __import__("skqt.acrextras", fromlist=["x"]).top_buttons(page):
        bar.more(b.text(), b.click, b.toolTip())
    page.hyphen_act = bar.more("Letters joined by a hyphen are one term", lambda: set_hyphen(page), checkable=True)
    bar.export("Export the report...", lambda: page.export())
    # the old rows of buttons and filters: hidden, still there for the tools
    for i in range(v.count()):
        it = v.itemAt(i)
        lay = it.layout() if it is not None else None
        if lay is not None and lay is not v:
            for k in range(lay.count()):
                w = lay.itemAt(k).widget()
                if w is not None and w not in (page.progress, page.b_cancel, page.f_search, page.showing):
                    w.setVisible(False)
    page.where.setVisible(False)                           # the page's title says what it is
    from . import acrtabs as TB
    TB.install(page, v)                                    # 3.93.0: On the page and The list
    # the filters as counts
    page.counts_row = FlowLayout(); page.counts_row.setSpacing(D.SPACE["s"])
    page.count_btns = {}
    t = D.tokens()
    chip = (f"QPushButton{{border:1px solid {t['border_strong']};border-radius:12px;padding:3px 10px;background:{t['surface']};color:{t['text']}}}"
            f"QPushButton:checked{{border:2px solid {t['accent']};background:{t['accent_soft']};color:{t['accent']};font-weight:600}}")
    for name in P.COUNTS:
        b = QPushButton(name); b.setCheckable(True); b.setObjectName("chip"); b.setStyleSheet(chip)
        b.clicked.connect(lambda _c=False, n=name: pick_count(page, n))
        page.counts_row.addWidget(b); page.count_btns[name] = b
    page.counts_row.addWidget(page.f_search)
    page.f_search.setVisible(True); page.f_search.setMinimumWidth(200)
    page.counts_row.addWidget(page.showing)                # 3.93.0: in The list, with its filters
    lv.addLayout(page.counts_row)
    lv.addWidget(page.bulk)
    # three panes: the terms, the page, the card
    split = page.card_area.parentWidget()
    if isinstance(split, QSplitter):
        page.mid = QWidget(); page.mid_box = QVBoxLayout(page.mid); page.mid_box.setContentsMargins(0, 0, 0, 0)
        page.mid_hint = D.label("Select a term: the customer's page where it was found shows here.", "muted")
        page.mid_box.addWidget(page.mid_hint)
        page.decide = SplitView(page.mid, page.card_area, links=lambda: links(page))
        page.decide.layout().setStretch(0, 3); page.decide.layout().setStretch(2, 2)
        split.addWidget(page.decide)
        split.setSizes([300, 1200])
        lv.addWidget(split, 1)
        page.mid.setVisible(False)                         # 3.93.0: the page is the other tab (the tool keeps it here)
        split.setSizes([760, 740])
        page.split = split
    page.table.setMinimumWidth(240)
    for c in range(page.table.columnCount()):
        page.table.setColumnHidden(c, c not in LIST_COLS)    # 3.93.0: room for the type and where it is from
    page.card_area.verticalScrollBar().valueChanged.connect(lambda _v: refresh_line(page))
    # keys on the card
    page.keys = []
    for k in ("1", "2", "3", "4"):
        page.keys.append(_key(page, k, lambda k=k: pick_suggestion(page, int(k))))
    page.keys.append(_key(page, Qt.Key_Return, lambda: add_current(page)))
    page.keys.append(_key(page, Qt.Key_Enter, lambda: add_current(page)))
    page.keys.append(_key(page, "X", lambda: not_term_current(page)))
    page.pick = None                                       # the suggestion picked with a key or a click (its number)


def _key(page, seq, fn):
    sc = QShortcut(QKeySequence(seq), page.list_w)         # 3.93.0: The list's keys; On the page has its own
    sc.setContext(Qt.WidgetWithChildrenShortcut)
    sc.activated.connect(lambda: None if _typing() else fn())
    return sc


def _typing():
    from PySide6.QtWidgets import QApplication, QTextEdit
    w = QApplication.focusWidget()
    return isinstance(w, (QLineEdit, QTextEdit)) and not getattr(w, "isReadOnly", lambda: False)()


# ------------------------------------------------------------------ the counts
def kind_of(d):
    return "excluded" if d.get("excluded") else A.status_kind(d.get("status", ""))


def fill_counts(page):
    s = page.session
    c = P.count_of(s.results, kind_of) if s else {k: 0 for k in P.COUNTS}
    want = current_count(page)
    for name, b in page.count_btns.items():
        b.setText(f"{name} {c[name]}")
        b.setChecked(name == want)
    from . import acrtabs as TB
    TB.after_fill(page)                                    # 3.93.0: the tabs, and the page drawn again
    return c


def current_count(page):
    if page.f_pics.isChecked():
        return "On pictures"
    st = page.f_status.currentText()
    return st if st in P.COUNTS else None


def pick_count(page, name):
    """A count clicked: its filter (clicked again: every term)."""
    on = current_count(page) != name
    page.f_pics.blockSignals(True); page.f_status.blockSignals(True)
    page.f_pics.setChecked(on and name == "On pictures")
    page.f_status.setCurrentText(name if on and name != "On pictures" else page.f_status.itemText(0))
    page.f_pics.blockSignals(False); page.f_status.blockSignals(False)
    page.fill()
    return current_count(page)


def next_to_decide(page):
    s = page.session
    if s is None:
        return None
    if current_count(page) != "To decide":
        pick_count(page, "To decide")
    cur = page.current()
    order = page.terms
    k = order.index(cur) + 1 if cur in order else 0
    for t in order[k:] + order[:k]:
        if P.passes(s.results[t], "To decide", kind_of(s.results[t])):
            page.select(t)
            return t
    page.host.toast("Nothing left to decide.")
    return None


# ------------------------------------------------------------------ keys
def pick_suggestion(page, k):
    rows = getattr(page, "suggest_rows", []) or []
    t = page.current()
    if t is None or not (1 <= k <= len(rows)):
        return None
    page.pick = k
    page.typed.setText(rows[k - 1]["definition"])
    mark_pick(page)
    refresh_line(page)
    return rows[k - 1]["definition"]


def add_current(page):
    t = page.current()
    if t is None:
        return None
    dfn = page.typed.text().strip() or None
    page.add([t], dfn)
    nxt = next_to_decide(page)
    return nxt or t


def not_term_current(page):
    t = page.current()
    if t is None:
        return None
    page.set_status([t], "Not a term")
    next_to_decide(page)
    return t


def mark_pick(page):
    for k, w in enumerate(getattr(page, "suggest_widgets", []) or [], 1):
        w.setProperty("picked", k == page.pick)
        w.setStyleSheet(f"QFrame#sugg{{border:2px solid {D.tokens()['ok']};border-radius:6px}}" if k == page.pick else
                        f"QFrame#sugg{{border:1px solid {D.tokens()['border']};border-radius:6px}}")


# ------------------------------------------------------------------ the line from the spelled-out words
def spelled_rect(page):
    """Where the picked definition's words are in the passage shown in the middle, in the middle pane's coordinates."""
    wv = getattr(page, "where_view", None)
    rows = getattr(page, "suggest_rows", []) or []
    if wv is None or not rows or wv.stack.currentWidget() is not wv.text:
        return None
    want = rows[(page.pick or 1) - 1]["definition"]
    doc = wv.text.document()
    cur = doc.find(want)
    if cur.isNull():
        return None
    r = wv.text.cursorRect(cur)
    tl = wv.text.viewport().mapTo(page.mid, r.topLeft())
    return QRect(tl, r.size())


def pick_rect(page):
    ws = getattr(page, "suggest_widgets", []) or []
    k = (page.pick or 1) - 1
    if not (0 <= k < len(ws)):
        return None
    w = ws[k]
    tl = w.mapTo(page.card_area.viewport(), w.rect().topLeft())
    return QRect(tl, w.size())


def links(page):
    a, b = spelled_rect(page), pick_rect(page)
    return [(a, b)] if a is not None and b is not None else []


def refresh_line(page):
    if getattr(page, "decide", None) is not None:
        page.decide.refresh()


# ------------------------------------------------------------------ the card's new parts
def card_more(page, t):
    """After the card is built: the suggestions as rows you can key, a longer term, where it goes, the sources."""
    s = page.session
    d = s.results.get(t, {})
    body = page.body
    page.suggest_widgets = []
    page.pick = None
    rows = getattr(page, "suggest_rows", []) or []
    if rows:                                                  # the same suggestions, framed so the line can find them
        box = QVBoxLayout(); box.setSpacing(4)
        for k, x in enumerate(rows[:4], 1):
            f = QFrame(); f.setObjectName("sugg")
            h = QHBoxLayout(f); h.setContentsMargins(8, 4, 8, 4)
            h.addWidget(D.label(f"<b>{k}</b>", None, wrap=False))
            h.addWidget(D.label(f"<b>{x['definition']}</b><br><span style='color:gray'>{x['source']}: {x['why']}</span>"), 1)
            box.addWidget(f)
            page.suggest_widgets.append(f)
        body.insertLayout(1, box)
        body.insertWidget(2, D.label("Keys: 1 to 4 pick · Enter adds to the list · X says Not a term", "muted"))
        page.pick = 1
        mark_pick(page)
    lg = P.longer(s.results, t)
    if lg and not d.get("part_of"):
        r = QHBoxLayout(); r.setSpacing(D.SPACE["s"])
        r.addWidget(D.label(f"Part of a longer term? Here {t} is inside <b>{lg['whole']}</b> in {lg['shared']} of {lg['places']} "
                            "place(s).", None), 1)
        r.addWidget(D.button(f"Use {lg['whole']}, one term", None, lambda: use_whole(page, t, lg["whole"])))
        body.insertLayout(0, r)
        page.longer_line = lg
    else:
        page.longer_line = None
    body.insertWidget(body.count() - 1, where_it_goes(page, t))
    sr = QHBoxLayout()
    if getattr(page, "list_only", False) and d.get("locations"):           # 3.93.0: the page is the other tab
        page.b_onpage = D.button("Show on the page", None, lambda: page.show_on_page(t),
                                 "The first page the term is on, with its finds selected")
        sr.addWidget(page.b_onpage)
    sr.addWidget(D.button("Sources", "ghost", lambda: sources_window(page, t), "Where each meaning comes from, and the "
                          "effort's timeline"))
    sr.addStretch(1)
    body.insertLayout(body.count() - 1, sr)
    if page.where_view is not None and getattr(page, "mid_box", None) is not None:
        page.where_view.text.verticalScrollBar().valueChanged.connect(lambda _v: refresh_line(page))
    refresh_line(page)


def use_whole(page, part, whole):
    import acrparts as AP
    ok = AP.set_part(page.session, part, whole)
    if ok:
        diag.activity("acronym_longer_used")
        page.fill()
        page.select(whole) or page.select(part)
    return ok


def list_entries(s):
    return [(t, _real(d.get("list_definition") or d.get("selected_definition"))) for t, d in s.results.items()
            if d.get("effort") == "In the list"]


def _real(dfn):
    """A definition, or "" for the scan's placeholders ([Not in Database ...])."""
    dfn = " ".join(str(dfn or "").split())
    return "" if dfn.startswith("[") else dfn


def where_it_goes(page, t):
    """The A to Z rows of the Acronyms table around this term, as the setup writes them, and the volumes that use it."""
    s = page.session
    d = s.results.get(t, {})
    dfn = page.typed.text().strip() if getattr(page, "typed", None) else ""
    dfn = _real(dfn or (page.suggest_rows[0]["definition"] if getattr(page, "suggest_rows", None) else d.get("selected_definition", "")))
    card = QFrame(); card.setObjectName("whereGoes")
    v = QVBoxLayout(card); v.setContentsMargins(0, 6, 0, 0); v.setSpacing(4)
    v.addWidget(D.SectionTitle("Where it goes"))
    v.addWidget(D.label("Each volume's Acronyms table, A to Z. The row this term adds is marked.", "muted"))
    tab = QTableWidget(0, 2); tab.setHorizontalHeaderLabels(["Acronym", "Definition"]); tab.verticalHeader().setVisible(False)
    tab.setEditTriggers(QTableWidget.NoEditTriggers); tab.horizontalHeader().setStretchLastSection(True)
    tab.setStyleSheet("QTableWidget{background:#FFFFFF;color:#111111} QHeaderView::section{background:#1F3864;color:#FFFFFF}")
    rows = P.table_rows(list_entries(s), t, dfn)
    for t2, d2, new in rows:
        i = tab.rowCount(); tab.insertRow(i)
        for c, val in enumerate((t2, d2)):
            it = QTableWidgetItem(val)
            if t2 == t:
                from PySide6.QtGui import QColor
                it.setBackground(QColor("#DCF3E4"))
                f = it.font(); f.setBold(True); it.setFont(f)
            tab.setItem(i, c, it)
    tab.setFixedHeight(28 + 26 * max(1, len(rows)))
    v.addWidget(tab)
    page.where_rows = rows
    vols = _volumes(page, t)
    v.addWidget(D.label(vols, "muted"))
    return card


def _volumes(page, t):
    """Which volumes use the term (from the last drafts check), as a line."""
    used = (page.session.ws.get("acronym_volume_use", {}) if page.session and page.session.ws is not None else {}) or {}
    rows = [f"{v}: {n} use(s)" for v, n in sorted((used.get(t) or {}).items())]
    return ("Used in our volumes: " + "; ".join(rows)) if rows else "Not checked in our drafts yet (In our drafts)."


# ------------------------------------------------------------------ sources and the timeline
def sources_window(page, t, run=True):
    s = page.session
    d = s.results.get(t, {})
    dlg = QDialog(page); dlg.setWindowTitle(f"{t}: where its meaning comes from")
    v = QVBoxLayout(dlg)
    rows = P.sources(d)
    tab = QTableWidget(len(rows), 3); tab.setHorizontalHeaderLabels(["Source", "What it says", "Against yours"])
    tab.verticalHeader().setVisible(False); tab.setEditTriggers(QTableWidget.NoEditTriggers)
    tab.horizontalHeader().setStretchLastSection(True)
    for i, r in enumerate(rows):
        for c, k in enumerate(("source", "says", "against")):
            tab.setItem(i, c, QTableWidgetItem(r[k]))
    tab.resizeColumnsToContents()
    v.addWidget(tab)
    v.addWidget(D.label("Which one wins: " + ", then ".join(P.SOURCE_ORDER) + ". A source lower down never changes a decision; "
                        "one that differs puts the term back in To decide.", "muted"))
    v.addWidget(D.SectionTitle("Over the effort"))
    tl = P.timeline(s.ws)
    v.addWidget(D.label("<br>".join(f"{x['when']}  <b>{x['what']}</b>" + (f": {P.counts_text(x['counts'])}" if x["counts"] else "")
                                    for x in tl[-12:]) or "Nothing yet: each scan, customer list and drafts check is noted here.",
                        None))
    bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(dlg.reject); v.addWidget(bb)
    page.sources_dialog = dlg
    if run:
        dlg.exec()
    return rows


def note_scan(page):
    s = page.session
    if s is None:
        return None
    c = P.count_of(s.results, kind_of)
    return P.note(s.ws, "Scan", found=len(s.results), to_decide=c["To decide"], pictures=c["On pictures"])


# ------------------------------------------------------------------ the hyphen rule and In our drafts
def set_hyphen(page, on=None):
    s = page.session
    if s is None:
        return 0
    on = (not P.hyphen_whole(s)) if on is None else bool(on)
    n = P.set_hyphen_whole(s, on)
    page.hyphen_act.blockSignals(True); page.hyphen_act.setChecked(on); page.hyphen_act.blockSignals(False)
    page.host.toast((f"Letters joined by a hyphen are one term: {n} piece(s) joined" if on else
                     "Letters joined by a hyphen are read apart again"))
    page.fill()
    return n


def open_drafts(page):
    from .acrdrafts import open_drafts as go
    return go(page)
