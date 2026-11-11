"""Documents, as designed (4.6.0; claude/stationkeeper-documents-changes-plan-4.6.md, step 1; the six-steps board 1;
claude/stationkeeper-documents-decisions-2026-11-10.md, decision 4).

Two tabs, Customer and Ours, take the place of the category and folder tree: Customer holds what the customer issued
(their documents, the bidders library, Q&A); Ours holds the rest (our documents, graphics, categories of our own). The
header has Find, More (folders, watched folders, the Library folder...) and one main button, Add documents.... The
table: Document (with "N versions" when there are more than one), Type, Governing version, and three progress chips:
Text (pages checked), Shred (where its shred stands) and Terms (acros and abs found and to decide). The panel says what
has been done, lists the versions once and offers one next thing; More about this document, Initial and type, and See
where its text went are on the row's right-click.

The focus changes what the page shows, never what it can do (as shredfocus did for Shred in 4.5.0). SK_DOCS_CLASSIC=1
keeps the page as it was, for the tests written before 4.6.0 that drive its tree. Rules only (No AI); nothing leaves the PC."""
import os

import diag

CUSTOMER_SIDE = ("customer", "bidders", "qa")
SIDES = (("customer", "Customer"), ("ours", "Ours"))
COLUMNS = ["Document", "Type", "Governing version", "Text", "Shred", "Terms"]


def classic():
    return bool(os.environ.get("SK_DOCS_CLASSIC"))


def side_of(d):
    return "customer" if d.get("category", "customer") in CUSTOMER_SIDE else "ours"


def install(page, side="customer"):
    """Called at the end of LibraryPage.__init__. Leaves the page as it was under SK_DOCS_CLASSIC."""
    page.doc_side = side
    page.focus = not classic()
    if not page.focus:
        return
    from PySide6.QtWidgets import QComboBox
    # the header: Find, More, Add documents...
    for b in (page.b_folder, page.b_watch):
        b.setVisible(False)
    for b in list(page.bar.commands):
        if b is not page.bar.main and b.text() == "New folder...":
            b.setVisible(False)
    page.bar.commands = [b for b in page.bar.commands if b.isVisibleTo(page.bar) or b is page.bar.main]
    page.bar.main.setText("Add documents...")
    page.bar.main.setToolTip("Pick documents or drop them on the page: each one is extracted as it arrives")
    page.bar.more_sep()
    page.bar.more("Add a folder...", lambda: page.add_folder(), "Bring in every document in a folder and its subfolders "
                  "(the folder names become tags)")
    page.bar.more("Watched folders...", lambda: page.host.watch_folders(),
                  "The folders checked for new, changed and missing files (Customer Documents always)")
    page.bar.more("New folder...", lambda: page.new_folder(), "A folder in the Library's folders on disk")
    # the tree becomes the two tabs; a type filter beside Find instead of the role filter
    page.tree.parentWidget().setVisible(False)
    page.role_f.setVisible(False)
    page.type_f = QComboBox()
    page.type_f.currentIndexChanged.connect(lambda _i: page.fill())
    _bar_of(page).addWidget(page.type_f)
    page.search.setPlaceholderText("Find: names, tags and the text of every document")
    # a click on "N role(s) to confirm" shows those documents
    page.p_und.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.PointingHandCursor)
    page.p_und.mousePressEvent = lambda _e: _only_undecided(page)
    # the table's columns
    t = page.table
    t.setColumnCount(len(COLUMNS))
    t.setHorizontalHeaderLabels(COLUMNS)
    from PySide6.QtWidgets import QHeaderView
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for c, w in enumerate((260, 120, 170, 110, 150, 120)):
        if c:
            t.setColumnWidth(c, w)
    # the panel: Versions once, one next thing; the rest on the right-click
    page.b_more.setVisible(False)
    page.b_taken2.setVisible(False)
    page.d_taken.setVisible(False)
    from . import design as D
    lay = page.empty.parentWidget().layout()
    i = lay.indexOf(page.empty)
    new = D.EmptyState("No customer documents yet" if side == "customer" else "None of our documents yet",
                       "Add the solicitation package: each document is extracted as it arrives, ready to shred."
                       if side == "customer" else "Our own documents (past proposals, resumes, graphics), kept for context "
                       "and reference.", "Add documents...", lambda: page.add())
    lay.insertWidget(i, new)
    page.empty.hide(); page.empty.setParent(None)
    page.empty = new


def _bar_of(page):
    """The row that holds Find (the search box) and the role filter."""
    from PySide6.QtWidgets import QHBoxLayout
    par = page.search.parentWidget()
    lay = par.layout()
    for i in range(lay.count()):
        it = lay.itemAt(i)
        if isinstance(it.layout(), QHBoxLayout) and it.layout().indexOf(page.search) >= 0:
            return it.layout()
    return lay


def _only_undecided(page):
    i = page.role_f.findData("undecided")
    page.role_f.setCurrentIndex(0 if page.role_f.currentIndex() == i else i)


def fill_types(page):
    """The type filter: Every type, then the side's categories."""
    if not page.focus or page.lib is None:
        return
    keep = page.type_f.currentData()
    page.type_f.blockSignals(True)
    page.type_f.clear()
    page.type_f.addItem("Every type", "")
    for k, n in page.lib.categories():
        if side_of({"category": k}) == page.doc_side:
            page.type_f.addItem(n, k)
    page.type_f.setCurrentIndex(max(0, page.type_f.findData(keep or "")))
    page.type_f.blockSignals(False)


def shown(page, docs):
    """The documents of this tab (and of the type picked)."""
    docs = [d for d in docs if side_of(d) == page.doc_side]
    k = page.type_f.currentData() if getattr(page, "type_f", None) is not None else ""
    if k:
        docs = [d for d in docs if d.get("category", "customer") == k]
    return docs


# ------------------------------------------------------------------ the progress chips
def chips(page, d, st=None, terms=None):
    """{column: (text, tone)} for Text, Shred and Terms. tone: ok, warn, accent, faint."""
    from . import docstatus as DS
    out = {}
    if d.get("category", "customer") == "customer":
        v = DS._verify(page, d)
        if v is None:
            out["Text"] = ("Not checked", "faint")
        else:
            ver, pages, look = v
            out["Text"] = (f"{look} to look at" if look else f"{ver}/{pages} pages" if ver < pages else "Checked",
                           "warn" if look else "ok" if ver >= pages else "accent")
    else:
        out["Text"] = ("", "faint")
    text, _tone, key = page.review_state(d, st)
    out["Shred"] = {"unread": ("Not extracted", "accent"), "not_needed": ("Left out", "faint"), "reviewed": ("Done", "ok"),
                    "needs": (text.replace("Needs reviewing: ", "").replace("Needs reviewing", "In progress"), "warn")}[key]
    t = (terms or {}).get((d.get("versions") or [{}])[-1].get("file", ""))
    if t:
        found, decide = t
        out["Terms"] = (f"{decide} to decide" if decide else f"{found} found", "warn" if decide else "ok")
    else:
        out["Terms"] = ("", "faint")
    return out


def term_counts(page):
    """{file: (terms found, to decide)} from the acronym scan, worked out once per fill."""
    try:
        s = page.host.acronym_page.session
        if s is None or not s.results:
            return {}
        import acrpages as AG
        got = {}
        for p in AG.pages(s.results):
            got.setdefault(p["name"], {}).update(p["terms"])
        return {f: (len(t), sum(1 for v in t.values() if v == "decide")) for f, t in got.items()}
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return {}


def fill_row(page, r, d, st, terms, item):
    """One row of the focused table. item(text, data, tip) makes a cell."""
    from . import design as D
    vs = d.get("versions") or []
    name = d["name"] + (f" ({d['initial']})" if d.get("initial") else "")
    if d.get("under") and page.lib.doc(d["under"]):
        name = "↳ " + name
    it = item(name + (f"   {len(vs)} versions" if len(vs) > 1 else ""), d["id"], vs[-1].get("file", "") if vs else "")
    if d.get("withdrawn"):
        it.setText(name + "  (withdrawn)"); it.setForeground(D.color("muted"))
    elif vs and vs[-1].get("missing_kept"):
        it.setText(name + "  (original missing)"); it.setForeground(D.color("warn"))
        it.setToolTip("Its file was removed; the record and its text were kept on purpose")
    elif vs and not page.lib.has_original(vs[-1]):
        it.setForeground(D.color("warn")); it.setToolTip("The original file is not here. Its text and record are.")
    page.table.setItem(r, 0, it)
    typ = d.get("type") if d.get("category", "customer") == "customer" and d.get("type") else page.lib.category_name(d.get("category", "customer"))
    page.table.setItem(r, 1, item(typ or ""))
    gv = vs[-1] if vs else {}
    gov = (gv.get("label") or "") + (f"  ·  {gv.get('added', '')[:10]}" if gv.get("added") else "")
    page.table.setItem(r, 2, item(gov, None, gv.get("file", "")))
    for c, (k, (txt, tone)) in enumerate(chips(page, d, st, terms).items(), start=3):
        ci = item(txt)
        if txt:
            ci.setForeground(D.color(tone)); ci.setIcon(D.dot_icon(D.color(tone)))
        page.table.setItem(r, c, ci)


def fill(page, docs, item):
    """Fills the focused table; returns True when it did (the classic fill runs otherwise)."""
    if not getattr(page, "focus", False):
        return False
    st = page.review_states()
    terms = term_counts(page)
    page.table.setRowCount(len(docs))
    for r, d in enumerate(docs):
        fill_row(page, r, d, st, terms, item)
    return True


# ------------------------------------------------------------------ the right-click menu
def more_items(page, m, d):
    """4.6.0: what left the panel, at the end of the row's menu."""
    if not getattr(page, "focus", False) or d is None:
        return
    m.addSeparator()
    if d.get("category", "customer") == "customer":
        m.addAction("Initial and type...", lambda: page.identity())
    m.addAction("More about this document...", lambda: page.doc_menu(page.table.viewport().mapToGlobal(
        page.table.visualRect(page.table.currentIndex()).bottomLeft())))
    try:
        import ctxdocs as CX
        nt = len(CX.Store(page.host.ws.root).load().of_doc(d["id"]))
    except Exception:  # noqa: BLE001
        nt = 0
    if nt:
        m.addAction(f"See where its text went ({nt})...", lambda: page.show_taken())
