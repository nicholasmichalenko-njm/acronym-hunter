"""Effort Standards on screen (4.32.0; 4.36.0, ST8 and ST20 of 2026-11-14): the card on Effort Formatting that shows
where the effort's standards differ from the Global Standards, each difference in color on its own row with the value
in use chosen there (This effort or Global); and the line under a standards page's title that says which set a change
there goes to. The 4.32.0 dialog (See the changes, Take for this effort, Send to the Global Standards) is gone.
Rules only (No AI); nothing leaves the PC."""
import diag
import effortset as ES
from . import design as D

# the pages that read and change the parts an effort owns
STANDARDS = {"prodstd", "styles", "qpstd", "designs", "layoutstd", "formatstd", "rules", "templates", "profiles",
             "tplprofiles", "studio"}


def sub(host, step, line):
    """The line under the page title: on a standards page, which set a change goes to. 4.34.0: the Global Standards
    page puts the Global Standards in view; they stay in view on the standards' editors it opens and leave view on any
    other page, when what was saved is shared."""
    name = getattr(host, "effort_name", "")
    if step == "globalstd":
        ES.view_global(True)
        return line
    if step in STANDARDS:
        if ES.viewing_global() or not (name and ES.active()):
            return f"Global Standards. A change here is saved for everyone.  \u00b7  {line}"
        return f"Effort Standards: {name}. A change here is this effort's own.  \u00b7  {line}"
    if ES.view_global(False):
        __import__("skqt.globalview", fromlist=["x"]).share_now(host)
    return line + (f"  \u00b7  {name}" if name else "")


STATE_SAYS = {"differs": "Differs", "only_here": "Only in this effort", "only_theirs": "Only in the Global Standards"}
STATE_COLOR = {"differs": "warn_soft", "only_here": "ok_soft", "only_theirs": "crit_soft"}


def add_card(page, v):
    """4.36.0 (ST8, ST20): the Effort Standards as they differ from the Global Standards, each difference on its own row
    in color, with the value in use chosen on the row: This effort (the start) or Global. No list to open, no sweep."""
    from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget
    page.es_card = D.Card("Effort Standards", "This effort's own standards. Each row is something that differs from the Global "
                          "Standards. The effort's own value is the one in use; choose Global Standards on a row to use their "
                          "value there, and This effort to go back. Neither value is lost.")
    page.es_line = page.es_card.add(D.label("", None)); page.es_line.setWordWrap(True)
    page.es_count = page.es_card.add(D.label("", "muted")); page.es_count.setWordWrap(True)
    t = QTableWidget(0, 6); t.setHorizontalHeaderLabels(["Part", "What", "", "This effort", "Global Standards", "In use"])
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionMode(QAbstractItemView.NoSelection)
    t.verticalHeader().setVisible(False); t.setMinimumHeight(220)
    hh = t.horizontalHeader(); hh.setSectionResizeMode(3, QHeaderView.Stretch); hh.setSectionResizeMode(4, QHeaderView.Stretch)
    page.es_table = page.es_card.add(t)
    page.es_rows = []
    v.addWidget(page.es_card)
    return page.es_card


def _switch(page, r):
    """The two choices on a row; the one in use is pressed."""
    from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(4, 2, 4, 2); h.setSpacing(4)
    mine = QPushButton("This effort"); glob = QPushButton("Global Standards")
    for b, on in ((mine, r["using"] == "effort"), (glob, r["using"] == "theirs")):
        b.setCheckable(True); b.setChecked(on); b.setEnabled(r["can"]); h.addWidget(b)
    mine.setObjectName("useMine"); glob.setObjectName("useGlobal")
    tip = "" if r["can"] else ("Made in this effort: the Global Standards have no value to use." if r["state"] == "only_here"
                               else "Only the Global Standards have it. Bring it in on its own page.")
    mine.setToolTip(tip); glob.setToolTip(tip)
    mine.clicked.connect(lambda _c=False: choose(page, r["key"], "effort"))
    glob.clicked.connect(lambda _c=False: choose(page, r["key"], "theirs"))
    return w


def choose(page, key, which):
    """The value in use on a row: "effort" or "theirs". Returns True when it changed."""
    import effortdiff as ED
    cfg, root = page.host.config_dir, page.host.ws.root
    ok = ED.use_global(cfg, root, key) if which == "theirs" else ED.use_mine(cfg, root, key)
    if ok:
        if which == "theirs":
            diag.activity("effort_standards_global_chosen")
        else:
            diag.activity("effort_standards_own_chosen")
        page.host.status("This effort uses the Global Standards' value there. Its own value is kept: This effort brings it back."
                         if which == "theirs" else "This effort uses its own value there again.")
    fn = getattr(page, "refresh", None)
    fn() if callable(fn) else show(page)                          # the page's own values follow the choice
    return ok


def show(page):
    """The line and the rows, read again. Returns (line, how many rows)."""
    import effortdiff as ED
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QTableWidgetItem
    try:
        ws = page.host.ws
        if ws is None or not ES.has(ws.root):
            page.es_card.setVisible(False)
            return "", 0
        page.es_card.setVisible(True)
        cfg = page.host.config_dir
        page.es_line.setText(ES.line(cfg, ws.root))
        rows = page.es_rows = ED.rows(cfg, ws.root)
        c = ED.counts(rows)
        page.es_count.setText("Nothing differs from the Global Standards." if not rows else
                              f"{len(rows)} thing{'s' if len(rows) != 1 else ''} differ{'s' if len(rows) == 1 else ''} from the Global Standards"
                              + (f"; {c['theirs']} use{'s' if c['theirs'] == 1 else ''} the Global Standards' value by your choice" if c["theirs"] else "")
                              + (f". Showing the first {ED.MOST}." if len(rows) >= ED.MOST else "."))
        t = page.es_table
        t.setVisible(bool(rows))
        t.setRowCount(len(rows))
        tok = D.tokens()
        for i, r in enumerate(rows):
            for j, text in enumerate((r["part"], r["what"], STATE_SAYS[r["state"]], r["mine"], r["theirs"])):
                it = QTableWidgetItem(str(text))
                it.setBackground(QColor(tok[STATE_COLOR[r["state"]]]))
                it.setForeground(QColor(tok["text"]))
                t.setItem(i, j, it)
            t.setCellWidget(i, 5, _switch(page, r))
        t.resizeColumnsToContents()
        t.horizontalHeader().setStretchLastSection(False)
        return page.es_line.text(), len(rows)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return page.es_line.text(), 0


def _reload(host):
    try:
        fn = getattr(host.stack.currentWidget(), "refresh", None)
        if callable(fn):
            fn()
    except Exception:  # noqa: BLE001
        diag.swallowed()
