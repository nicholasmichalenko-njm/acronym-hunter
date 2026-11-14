"""Effort Standards on screen (4.32.0, Standards step 3; decisions ST3 and ST4 of 2026-11-14): the card on Effort
Formatting that says where the effort's own set came from, what the Global Standards would change in it and what the
effort changed itself, with one Review... dialog for both; and the line under a standards page's title that says which
set a change there goes to. Rules only (No AI); nothing leaves the PC."""
import diag
import effortset as ES
from . import design as D

# the pages that read and change the parts an effort owns
STANDARDS = {"prodstd", "styles", "qpstd", "designs", "layoutstd", "formatstd", "rules", "templates", "profiles",
             "tplprofiles", "studio"}


def sub(host, step, line):
    """The line under the page title: on a standards page, which set a change goes to."""
    name = getattr(host, "effort_name", "")
    if step in STANDARDS:
        if name and ES.active():
            return f"Effort Standards: {name}. A change here is this effort's own.  ·  {line}"
        return f"Global Standards. A change here waits on this PC until Update Global Standards.  ·  {line}"
    return line + (f"  ·  {name}" if name else "")


def add_card(page, v):
    page.es_card = D.Card("Effort Standards", "This effort's own set of standards: Production Standards with their covers and "
                          "Quick Parts, the template library, rules, templates, section designs, outline layouts and field "
                          "recipes. Taken from the Global Standards once; a change on a standards page while this effort is "
                          "open changes this set only.",
                          actions=[D.button("Review...", None, lambda: review(page),
                                            "What the Global Standards would change in this effort's set, and what this effort changed itself")])
    page.es_line = page.es_card.add(D.label("", None)); page.es_line.setWordWrap(True)
    page.es_offer = page.es_card.add(D.label("", None)); page.es_offer.setWordWrap(True)
    v.addWidget(page.es_card)
    return page.es_card


def offer_words(cfg, root):
    of = ES.offer(cfg, root)
    if not of["rows"]:
        return ""
    n = len(of["rows"])
    was = ES.info(root).get("from_version") or 0
    head = (f"Global Standards version {of['version']} is ready for this effort" if of["version"] and of["version"] != was
            else "The Global Standards on this PC have changed since this effort took its set")
    return f"{head}: {n} change{'s' if n != 1 else ''}. Review... shows each one; nothing is taken until you say so."


def show(page):
    """The card's two lines, read again. Returns (line, offer)."""
    try:
        ws = page.host.ws
        if ws is None or not ES.has(ws.root):
            page.es_card.setVisible(False)
            return "", ""
        page.es_card.setVisible(True)
        page.es_line.setText(ES.line(page.host.config_dir, ws.root))
        said = offer_words(page.host.config_dir, ws.root)
        page.es_offer.setText(said); page.es_offer.setVisible(bool(said))
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return page.es_line.text(), page.es_offer.text()


def _reload(host):
    try:
        fn = getattr(host.stack.currentWidget(), "refresh", None)
        if callable(fn):
            fn()
    except Exception:  # noqa: BLE001
        diag.swallowed()


def take(page, files=None):
    """Take the Global Standards' changes (the files named, or every one) into this effort's set. Returns how many."""
    n = ES.take(page.host.config_dir, page.host.ws.root, files)
    if n:
        diag.activity("effort_standards_taken", n=n)
        page.host.status(f"This effort's standards took {n} file{'s' if n != 1 else ''} from the Global Standards.")
        _reload(page.host); show(page)
    return n


def give(page, files=None):
    """This effort's own changes become changes waiting in the Global Standards on this PC. Returns how many."""
    n = ES.give(page.host.config_dir, page.host.ws.root, files)
    if n:
        diag.activity("effort_standards_given", n=n)
        page.host.status(f"{n} file{'s' if n != 1 else ''} of this effort's changes now wait in the Global Standards on this PC. "
                         "Settings > Global Standards > Update Global Standards makes them a version.")
        show(page)
    return n


def review(page, run=True):
    """Two lists: what the Global Standards would change here (Take for this effort) and what this effort changed
    (Send to the Global Standards). Each acts on the selected rows, or on every row when none is selected."""
    from PySide6.QtWidgets import QAbstractItemView, QDialog, QHBoxLayout, QTableWidget, QTableWidgetItem, QVBoxLayout
    host = page.host
    cfg, root = host.config_dir, host.ws.root
    dlg = QDialog(page); dlg.setWindowTitle("Effort Standards"); dlg.resize(900, 620)
    v = QVBoxLayout(dlg)

    def table(heads):
        t = QTableWidget(0, len(heads)); t.setHorizontalHeaderLabels(heads)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    h1 = D.label("", None); h1.setWordWrap(True); v.addWidget(h1)
    t1 = table(["Part", "What", "This effort has", "The Global Standards have"]); v.addWidget(t1, 1)
    r1 = QHBoxLayout(); b_take = D.button("Take for this effort", "primary"); r1.addStretch(1); r1.addWidget(b_take); v.addLayout(r1)
    h2 = D.label("", None); h2.setWordWrap(True); v.addWidget(h2)
    t2 = table(["Part", "File"]); v.addWidget(t2, 1)
    r2 = QHBoxLayout()
    b_give = D.button("Send to the Global Standards", None, None,
                      "The selected changes wait in the Global Standards on this PC; Update Global Standards makes them a version for everyone.")
    r2.addStretch(1); r2.addWidget(b_give); r2.addWidget(D.button("Close", None, dlg.reject)); v.addLayout(r2)
    dlg.rows, dlg.mine = [], []

    def fill():
        of = ES.offer(cfg, root)
        dlg.rows = of["rows"]
        t1.setRowCount(len(dlg.rows))
        for i, r in enumerate(dlg.rows):
            for j, k in enumerate(("part", "what", "old", "new")):
                t1.setItem(i, j, QTableWidgetItem(str(r[k])))
        t1.resizeColumnsToContents()
        also = of["also_here"]
        h1.setText((offer_words(cfg, root).split(". Review")[0] + "." if dlg.rows else "The Global Standards would change nothing in this effort's set.")
                   + (f" This effort changed {len(also)} of these files itself; taking one replaces the effort's change." if also else ""))
        b_take.setEnabled(bool(dlg.rows))
        dlg.mine = ES.changed(cfg, root)
        t2.setRowCount(len(dlg.mine))
        for i, m in enumerate(dlg.mine):
            t2.setItem(i, 0, QTableWidgetItem(ES._part_of(m))); t2.setItem(i, 1, QTableWidgetItem(m))
        t2.resizeColumnsToContents()
        k = len(dlg.mine)
        h2.setText(f"This effort changed {k} file{'s' if k != 1 else ''} of its set. They stay this effort's own unless you send them."
                   if k else "This effort has changed nothing in its set.")
        b_give.setEnabled(bool(k))

    def picked(t, names):
        rows = sorted({i.row() for i in t.selectionModel().selectedRows()})
        return sorted({names[i] for i in rows}) if rows else None

    def do_take():
        take(page, picked(t1, [r["file"] for r in dlg.rows])); fill()

    def do_give():
        give(page, picked(t2, dlg.mine)); fill()

    b_take.clicked.connect(do_take); b_give.clicked.connect(do_give)
    dlg.fill, dlg.t_offer, dlg.t_mine, dlg.b_take, dlg.b_give = fill, t1, t2, b_take, b_give
    fill()
    page.es_dialog = dlg
    if run:
        dlg.exec()
    return dlg
