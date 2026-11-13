"""Documents, as designed (4.6.0; claude/stationkeeper-documents-changes-plan-4.6.md, step 1; the six-steps board 1;
claude/stationkeeper-documents-decisions-2026-11-10.md, decision 4).

4.25.0 (claude/stationkeeper-documents-board-2026-11-12.html, step A; Nicholas 16:14): one list. Three chips, All,
Customer and Internal, take the place of the Customer and Ours tabs (4.25.2: the filter beside Find also shows what is
For the shred or Returned to the customer, or one folder). The table: Document (with "N versions"), Type, Source (Customer or Internal, with a light tint on the row),
Version, Used for (4.25.2: the marks, skqt/usedfor.py), and Status, which is empty unless the document
needs the person (pages to look at, changes to review, a file edited). How far the shred and the acros and abs are
shows on their own screens and in the panel, not here. The header has Find, More and one main button, Add documents....

The focus changes what the page shows, never what it can do (as shredfocus did for Shred in 4.5.0). SK_DOCS_CLASSIC=1
keeps the page as it was, for the tests written before 4.6.0 that drive its tree. Rules only (No AI); nothing leaves the PC."""
import os

import diag

CUSTOMER_SIDE = ("customer", "bidders", "qa")
# 4.25.0 (Documents board 2026-11-12, step A): one list. All, Customer and Internal are chips over it, not two tabs;
# "ours" stays the saved word for the side, Internal is what a person reads.
SIDES = (("all", "All"), ("customer", "Customer"), ("ours", "Internal"))
USES = (("use:shred", "For the shred"), ("use:returned", "Returned to the customer"))   # 4.25.2: in the filter beside Find
SIDE_NAMES = {"customer": "Customer", "ours": "Internal"}
COLUMNS = ["Document", "Type", "Source", "Version", "Used for", "Status"]


def classic():
    return bool(os.environ.get("SK_DOCS_CLASSIC"))


def side_of(d):
    return "customer" if d.get("category", "customer") in CUSTOMER_SIDE else "ours"


def in_side(page, d):
    """The document shows under the chip picked (All shows every one)."""
    side = getattr(page, "doc_side", "all")
    return side == "all" or side_of(d) == side


def set_side(page, side):
    """Pick a chip: all, customer or ours (shown as Internal)."""
    page.doc_side = side if side in dict(SIDES) else "all"
    for k, b in getattr(page, "side_btns", {}).items():
        b.blockSignals(True); b.setChecked(k == page.doc_side); b.blockSignals(False)
    if getattr(page, "focus", False) and page.lib is not None:
        fill_types(page)
        page.refresh() if hasattr(page, "refresh") else page.fill()
    return page.doc_side


def install(page, side="all"):
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
    for a in page.bar.more_menu.actions():           # 4.25.2: folders took the place of categories
        if a.text() == "+ Category...":
            a.setVisible(False)
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
    from . import design as D0
    page.side_btns = {}
    for i, (k, n) in enumerate(SIDES):
        b = D0.button(n, None, None, {"all": "Every document", "customer": "What the customer issued",
                                      "ours": "Our own documents: past proposals, resumes, graphics, notes"}[k])
        b.setCheckable(True); b.setChecked(k == page.doc_side)
        b.clicked.connect(lambda _c=False, k=k: set_side(page, k))
        _bar_of(page).insertWidget(i, b)
        page.side_btns[k] = b
    page.type_f = QComboBox()
    page.type_f.currentIndexChanged.connect(lambda _i: page.fill())
    _bar_of(page).addWidget(page.type_f)
    page.search.setPlaceholderText("Find: names, tags and the text of every document")
    # 4.25.1 (Nicholas 16:49): the effort's folder, front and center: where it is, and that a file dropped in is added
    from PySide6.QtWidgets import QHBoxLayout
    frow = QHBoxLayout()
    page.folder_lbl = D0.label("", "muted"); page.folder_lbl.setWordWrap(True); frow.addWidget(page.folder_lbl, 1)
    page.folder_lbl.linkActivated.connect(lambda _h: page.host.open_effort_folder())      # the path opens the folder
    page.search.parentWidget().layout().insertLayout(0, frow)
    # a click on "N role(s) to confirm" shows those documents
    page.p_und.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.PointingHandCursor)
    page.p_und.mousePressEvent = lambda _e: _only_undecided(page)
    # the table's columns
    t = page.table
    t.setColumnCount(len(COLUMNS))
    t.setHorizontalHeaderLabels(COLUMNS)
    from PySide6.QtWidgets import QHeaderView
    hh = t.horizontalHeader()
    hh.setStretchLastSection(False)
    for c in range(len(COLUMNS)):
        hh.setSectionResizeMode(c, QHeaderView.Stretch if c == 0 else QHeaderView.Interactive)
    for c, w in enumerate((260, 120, 90, 180, 220, 190)):
        if c:
            t.setColumnWidth(c, w)
    # the panel: Versions once, one next thing; the rest on the right-click
    page.b_more.setVisible(False)
    page.b_taken2.setVisible(False)
    page.d_taken.setVisible(False)
    from . import design as D
    lay = page.empty.parentWidget().layout()
    i = lay.indexOf(page.empty)
    new = D.EmptyState("No documents yet",
                       "Add the solicitation package and your own documents (past proposals, resumes, graphics): each "
                       "one is extracted as it arrives.", "Add documents...", lambda: page.add())
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


KINDS = ((".docx .doc .docm .rtf", "Word"), (".pdf", "PDF"), (".xlsx .xls .xlsm .csv", "Excel"), (".pptx .ppt .pptm", "PowerPoint"),
         (".png .jpg .jpeg .tif .tiff .bmp .gif .webp .svg .emf .wmf", "Picture"), (".txt .md", "Text"))


def kind_of(name):
    """What kind of file a document is, for one that has no document type (Word, PDF, Picture...)."""
    ext = os.path.splitext(name or "")[1].lower()
    for exts, n in KINDS:
        if ext and ext in exts.split():
            return n
    return ext[1:].upper() if ext else ""


def folder_of(page, d):
    """4.25.2 (answer 6: folders replace Category): the folder the document's file is in, as it sits in the effort's
    folder ("06_cost and pricing/Rates"); for a file kept elsewhere, the folder name it was filed under."""
    lib = page.lib
    vs = d.get("versions") or []
    try:
        p = lib.path_of(vs[-1]) if vs else ""
        er = getattr(lib, "effort_root", "") or ""
        if p and er and os.path.normcase(os.path.abspath(p)).startswith(os.path.normcase(os.path.abspath(er)) + os.sep):
            rel = os.path.relpath(os.path.dirname(os.path.abspath(p)), os.path.abspath(er)).replace(os.sep, "/")
            return "" if rel == "." else rel
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return "/".join(x for x in (lib.category_name(d.get("category", "customer")), d.get("folder", "")) if x)


def top_folder(page, d):
    f = folder_of(page, d)
    return f.split("/")[0] if f else "(the effort's folder)"


def fill_types(page):
    """The folder filter (4.25.2; it listed categories before): Every folder, then the top folders that hold documents."""
    if not page.focus or page.lib is None:
        return
    effort_line(page)
    keep = page.type_f.currentData()
    page.type_f.blockSignals(True)
    page.type_f.clear()
    page.type_f.addItem("Every folder", "")
    for k, n in USES:                                   # by what a document is used for, then by folder
        page.type_f.addItem(n, k)
    page.type_f.insertSeparator(page.type_f.count())
    for f in sorted({top_folder(page, d) for d in page.lib.all if in_side(page, d)}, key=str.lower):
        page.type_f.addItem(f, f)
    page.type_f.setCurrentIndex(max(0, page.type_f.findData(keep or "")))
    page.type_f.blockSignals(False)


def effort_line(page):
    """The line over the list: where the effort's folder is."""
    try:
        import effortfolders as EF
        root = EF.root(page.host.effort_path) if page.host.effort_path else ""
    except Exception:  # noqa: BLE001
        root = ""
    import html
    page.folder_lbl.setText(f"Effort folder: <a href='open'>{html.escape(root)}</a>. A file you put in it is added here by "
                            "itself; what you delete here goes to its Deleted folder." if root else "")
    page.folder_lbl.setVisible(bool(root))
    return root


def shown(page, docs):
    """The documents of this tab (and of the type picked)."""
    docs = [d for d in docs if in_side(page, d)]
    k = page.type_f.currentData() if getattr(page, "type_f", None) is not None else ""
    if k == "use:shred":
        docs = [d for d in docs if page.lib.role_of(d) == "matrix"]
    elif k == "use:returned":
        docs = [d for d in docs if page.lib.returns_of(d)]
    elif k:
        docs = [d for d in docs if top_folder(page, d) == k]
    return docs


# ------------------------------------------------------------------ a status, only when the document needs you
def needs(page, d):
    """(text, tone) when the document needs the person, ("", "") when it does not (4.25.0). How far its shred and its
    acros and abs are is on their own screens, and in the panel."""
    from . import docstatus as DS
    if d.get("withdrawn") or page.lib.role_of(d) == "not_needed":
        return "", ""
    ch = DS._changes(page, d)
    if ch is not None and (not ch[0] or ch[1]):
        return ("Changes to review" + (f" ({ch[1]})" if ch[0] and ch[1] else ""), "warn")
    v = DS._verify(page, d)
    if v is not None and v[2]:
        return (f"{v[2]} page" + ("" if v[2] == 1 else "s") + " to look at", "warn")
    if DS._edited(page, d):
        return ("The file was edited: read it again", "warn")
    return "", ""


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
    typ = d.get("type") if d.get("category", "customer") == "customer" and d.get("type") else kind_of(vs[-1].get("file", "") if vs else "")
    page.table.setItem(r, 1, item(typ or "", None, "In " + (folder_of(page, d) or "the effort's folder")))
    side = side_of(d)
    page.table.setItem(r, 2, item(SIDE_NAMES[side]))
    gv = vs[-1] if vs else {}
    gov = (gv.get("label") or "") + (f"  ·  {gv.get('added', '')[:10]}" if gv.get("added") else "")
    page.table.setItem(r, 3, item(gov, None, gv.get("file", "")))
    page.table.setItem(r, 4, item(", ".join(page.lib.marks_of(d))))
    txt, tone = needs(page, d)
    ci = item(txt)
    if txt:
        ci.setForeground(D.color(tone)); ci.setIcon(D.dot_icon(D.color(tone)))
    page.table.setItem(r, 5, ci)
    tint = D.color("cust_soft" if side == "customer" else "accent_soft")     # a light tint says whose it is
    for c in range(len(COLUMNS)):
        page.table.item(r, c).setBackground(tint)


def fill(page, docs, item):
    """Fills the focused table; returns True when it did (the classic fill runs otherwise). 4.25.4: the rows are built by
    skqt/docgroups (packages as groups, a document's earlier versions under it)."""
    if not getattr(page, "focus", False):
        return False
    from . import docgroups as DG
    DG.fill(page, docs, item)
    return True


# ------------------------------------------------------------------ the right-click menu
def more_items(page, m, d):
    """4.6.0: what left the panel, at the end of the row's menu."""
    if not getattr(page, "focus", False) or d is None:
        return
    m.addSeparator()
    if d.get("category", "customer") == "customer":
        m.addAction("Initial and type...", lambda: page.identity())
        __import__("skqt.docgroups", fromlist=["x"]).menu(page, m, d)
    m.addAction("More about this document...", lambda: page.doc_menu(page.table.viewport().mapToGlobal(
        page.table.visualRect(page.table.currentIndex()).bottomLeft())))
    try:
        import ctxdocs as CX
        nt = len(CX.Store(page.host.ws.root).load().of_doc(d["id"]))
    except Exception:  # noqa: BLE001
        nt = 0
    if nt:
        m.addAction(f"See where its text went ({nt})...", lambda: page.show_taken())
