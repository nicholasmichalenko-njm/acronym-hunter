"""The acronym page's tools brought back from the classic window (3.51.0), kept apart so the page stays readable.

install(page)        sorting by any column, text size (Ctrl+= and Ctrl+-, Ctrl+wheel), a right-click menu of the
                     actions, the Details window on double-click
top_buttons(page)    Add a term..., Customer acronym lists..., Exclusion List..., Meaning from context
card_extras(page,t)  the "Found: ... Use" line, the context suggestion with Accept, an equation's symbols
more_actions(page)   Add to the database, Add to the Exclusion List, Back to Proposed, Remove from the list,
                     Accept context suggestions, Fix a misread..., Remove (a term added by hand)
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit, QListWidget,
                               QMenu, QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout)

import acrmore as AM
import app_gui as A
import diag
from . import design as D

SORT_KEYS = {0: lambda t, d: t.casefold(), 1: lambda t, d: str(d.get("category", "")), 2: lambda t, d: -int(d.get("count") or 0),
             3: None, 4: lambda t, d: str(d.get("change", "") or "~"), 5: lambda t, d: A.status_text(d.get("status", "")),
             6: lambda t, d: str(d.get("selected_definition", "")).casefold(), 7: None, 8: lambda t, d: str(d.get("effort", "") or "~"),
             9: lambda t, d: source_text(d)}


def source_text(d):
    """'Kestrel_Technical_Volume.docx (+3 places)': the first file a term was found in, and how many more places."""
    locs = [l for l in d.get("locations", []) if l]
    if not locs:
        return ""
    return A._file_of(locs[0]) + (f" (+{len(locs) - 1} places)" if len(locs) > 1 else "")


class _Wheel(QObject):
    def __init__(self, page):
        super().__init__(page)
        self.page = page

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel and ev.modifiers() & Qt.ControlModifier:
            text_size(self.page, 1 if ev.angleDelta().y() > 0 else -1)
            return True
        return False


def install(page):
    t = page.table
    page.sort_col, page.sort_desc = None, False
    hh = t.horizontalHeader()
    hh.setSectionsClickable(True); hh.setSortIndicatorShown(True)
    hh.sectionClicked.connect(lambda c: sort_by(page, c))
    t.setContextMenuPolicy(Qt.CustomContextMenu)
    t.customContextMenuRequested.connect(lambda pos: row_menu(page, t.viewport().mapToGlobal(pos)))
    t.cellDoubleClicked.connect(lambda r, _c: details(page))
    page._size = 0
    for keys, step in (("Ctrl+=", 1), ("Ctrl++", 1), ("Ctrl+-", -1), ("Ctrl+0", 0)):
        sc = QShortcut(QKeySequence(keys), t); sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(lambda st=step: text_size(page, st))
    t.viewport().installEventFilter(_Wheel(page))


def sort_by(page, col):
    """Sort the list by a column; the same column again turns the order around."""
    if SORT_KEYS.get(col) is None and col not in (3, 7):
        return
    page.sort_desc = (not page.sort_desc) if page.sort_col == col else False
    page.sort_col = col
    page.table.horizontalHeader().setSortIndicator(col, Qt.DescendingOrder if page.sort_desc else Qt.AscendingOrder)
    page.fill()


def sorted_terms(page, terms):
    s = page.session
    col = getattr(page, "sort_col", None)
    if col is None or s is None:
        return terms
    key = SORT_KEYS.get(col)
    if col == 3:
        key = lambda t, d: s.found_in(d)              # noqa: E731
    elif col == 7:
        key = lambda t, d: s.known_cell(t, d)         # noqa: E731
    return sorted(terms, key=lambda t: (key(t, s.results[t]), t.casefold()), reverse=page.sort_desc)


def text_size(page, step):
    """Larger (1), smaller (-1) or back to normal (0) text in the list."""
    page._size = 0 if step == 0 else max(-3, min(8, page._size + step))
    f = page.table.font()
    base = page.font().pointSizeF() if page.font().pointSizeF() > 0 else 9.0
    f.setPointSizeF(base + page._size)
    page.table.setFont(f)
    page.table.verticalHeader().setDefaultSectionSize(int(22 + page._size * 2.2))
    return f.pointSizeF()


def row_menu(page, at=None, run=True):
    """The actions for the selected rows, by right-click. Returns the menu."""
    terms = page.selected_terms()
    m = QMenu(page)
    if not terms:
        return m
    s = page.session
    one = terms[0] if len(terms) == 1 else None
    m.addAction("Add to the effort list").triggered.connect(lambda: page.add(terms))
    m.addAction("Approve...").triggered.connect(lambda: page.approve(terms))
    m.addAction("Needs author").triggered.connect(lambda: page.set_status(terms, "Needs author"))
    m.addAction("Back to Proposed").triggered.connect(lambda: page.set_status(terms, "Proposed"))
    m.addAction("Not a term").triggered.connect(lambda: page.set_status(terms, "Rejected"))
    m.addSeparator()
    om = all(s.results[t].get("excluded") for t in terms)
    m.addAction("Bring back" if om else "Omit (this effort)").triggered.connect(lambda: page.exclude(terms, not om))
    m.addAction("Add to the Exclusion List (every effort)").triggered.connect(lambda: exclusion_add(page, terms))
    m.addAction("Add to this PC's database").triggered.connect(lambda: add_to_db(page, terms))
    if s.effort is not None and any(t in s.effort.rows for t in terms):
        m.addAction("Remove from the acronym list").triggered.connect(lambda: remove_from_list(page, terms))
    if any((s.results[t].get("context") or {}).get("definition") for t in terms):
        m.addAction("Accept the context suggestion").triggered.connect(lambda: accept_context(page, terms))
    if one:
        m.addSeparator()
        m.addAction("Details...").triggered.connect(lambda: details(page))
        m.addAction("Fix a misread...").triggered.connect(lambda: fix_misread(page, one))
        if s.results[one].get("manual"):
            m.addAction("Remove (added by hand)").triggered.connect(lambda: remove_manual(page, one))
    if run and at is not None:
        m.exec(at)
    return m


def details(page, run=True):
    """Every value of the selected term in a window (copyable)."""
    t = page.current()
    s = page.session
    if not t or s is None:
        return None
    d = s.results[t]
    lines = [f"Term: {t}", f"Type: {d.get('category', '')}", f"Status: {A.status_text(d.get('status', ''))}",
             f"Meaning: {d.get('selected_definition', '')}", f"Found: {d.get('count', 0)} time(s)", f"Change: {d.get('change', '')}",
             f"Known in: {s.known_cell(t, d)}", f"Acronym list: {d.get('effort', '')}", "", "Possible meanings:"]
    for x in d.get("definitions", []) or []:
        src = AM.sources_of(d, x)
        lines.append(f"  {x}" + (f"   (customer document: {', '.join(src)})" if src else ""))
    lines += ["", "Where it was found:"] + [f"  {x}" for x in d.get("locations", [])]
    dlg = QDialog(page); dlg.setWindowTitle(f"Details: {t}"); dlg.resize(760, 560)
    v = QVBoxLayout(dlg)
    box = QPlainTextEdit("\n".join(lines)); box.setReadOnly(True); v.addWidget(box)
    v.addWidget(D.button("Close", "ghost", dlg.accept))
    if run:
        dlg.exec()
    return "\n".join(lines)


# ------------------------------------------------------------------ the buttons above the list
def top_buttons(page):
    return [D.button("Add a term...", None, lambda: add_term(page), "A term the scan did not find: to the scan's terms, the "
                     "acronym list or this PC's database"),
            D.button("Customer acronym lists...", None, lambda: page.client_lists(), "The customer's own acronym lists: their "
                     "meanings come first"),
            D.button("Exclusion List...", None, lambda: exclusion_window(page), "Terms never shown in any effort on this PC"),
            D.button("Meaning from context", None, lambda: suggest_context(page), "For each term with several meanings, read the "
                     "words around each use and suggest the meaning that fits (you still decide)"),
            D.button("Fixes for misread text...", None, lambda: ocr_fixes_window(page), "What the reader gets wrong in pictures "
                     "and what it should be, for every later scan on this PC")]


def add_term(page, term=None, category="Acronym", definition="", document="", to=None):
    """Add a term by hand. With term given (tests), no dialog. Returns what was done, in words."""
    s = page.session
    if s is None:
        return ""
    if term is None:
        from . import symbols as SYM
        dlg = QDialog(page); dlg.setWindowTitle("Add a term"); dlg.resize(560, 260)
        f = QFormLayout(dlg)
        e_t = QLineEdit(); SYM.attach(e_t); f.addRow("Term", e_t)
        e_c = QComboBox(); e_c.addItems(["Acronym", "Abbreviation", "Unit", "Symbol"]); f.addRow("Type", e_c)
        e_d = QLineEdit(); rw = QHBoxLayout(); rw.addWidget(e_d, 1); rw.addWidget(SYM.button(e_d)); f.addRow("Meaning", rw)
        e_w = QComboBox(); e_w.setEditable(True); e_w.addItems([""] + sorted({A._file_of(x) for x in getattr(s, "scanned_paths", {})}))
        f.addRow("Document (optional)", e_w)
        c_r = QCheckBox("List it with the scan's terms"); c_r.setChecked(True)
        c_l = QCheckBox("Add it to this effort's acronym list"); c_l.setChecked(s.effort is not None); c_l.setEnabled(s.effort is not None)
        c_d = QCheckBox("Add it to this PC's database (needs a meaning)")
        for c in (c_r, c_l, c_d):
            f.addRow("", c)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return ""
        term, category, definition, document = e_t.text(), e_c.currentText(), e_d.text(), e_w.currentText()
        to = [k for k, c in (("results", c_r), ("list", c_l), ("database", c_d)) if c.isChecked()]
    said = AM.add_manual(s, term, category, definition, document, tuple(to or ("results",)))
    page.fill(); page.select(" ".join(str(term).split()))
    page.host.toast(said or "Nothing was added.")
    return said


def remove_manual(page, term):
    ok = AM.remove_manual(page.session, term)
    page.fill()
    return ok


def exclusion_add(page, terms, reason=None):
    if reason is None:
        from PySide6.QtWidgets import QInputDialog
        reason, ok = QInputDialog.getText(page, "Add to the Exclusion List", f"{len(terms)} term(s) will never be shown in any effort "
                                          "on this PC. Why (optional, for example: a place name)?")
        if not ok:
            return 0
    try:
        n = AM.to_exclusion_list(page.session, terms, reason or "")
    except PermissionError:
        page.host.status(A.DB_LOCKED_MSG)
        return 0
    page.host.toast(f"{n} term(s) on the Exclusion List: never shown in any effort on this PC.")
    page.fill()
    return n


def exclusion_window(page, run=True):
    """The Exclusion List: view it, take terms off it. Returns the dialog."""
    import acrdb
    dlg = QDialog(page); dlg.setWindowTitle("Exclusion List"); dlg.resize(640, 520)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Terms never shown in any effort on this PC. Take one off and it comes back on the next scan. To leave a "
                        "term out of one effort only, use Omit.", "muted"))
    t = QTableWidget(0, 3); t.setHorizontalHeaderLabels(["Term", "Type", "Why"]); t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.NoEditTriggers); t.setSelectionBehavior(QTableWidget.SelectRows)
    t.horizontalHeader().setStretchLastSection(True)
    v.addWidget(t, 1)

    def fill():
        rows = acrdb.exclusion_list()
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                t.setItem(r, c, QTableWidgetItem(str(val)))
    dlg.fill = fill

    def take_off():
        terms = [t.item(i.row(), 0).text() for i in t.selectionModel().selectedRows()]
        if terms:
            try:
                acrdb.exclusion_remove(terms)
            except PermissionError:
                page.host.status(A.DB_LOCKED_MSG)
            fill()
    dlg.take_off = take_off
    dlg.table = t
    row = QHBoxLayout(); v.addLayout(row)
    row.addWidget(D.button("Take off the list", None, take_off)); row.addStretch(1)
    row.addWidget(D.button("Close", "ghost", dlg.accept))
    fill()
    if run:
        dlg.exec()
    return dlg


def add_to_db(page, terms):
    try:
        got = AM.add_to_database(page.session, terms)
    except PermissionError:
        page.host.status(A.DB_LOCKED_MSG)
        return None
    page.host.toast(f"This PC's database: {got['added']} added, {got['updated']} updated, {got['same']} already there.")
    return got


def remove_from_list(page, terms):
    n = page.session.list_remove([t for t in terms if page.session.effort is not None and t in page.session.effort.rows])
    page.fill()
    page.host.toast(f"{n} term(s) taken out of the acronym list.")
    return n


def suggest_context(page):
    s = page.session
    if s is None:
        return 0
    n = AM.suggest_context(s, page.path_of)
    page.fill()
    page.host.toast(f"Meaning from context: a suggestion for {n} term(s). Accept each on its card, or right-click several." if n else
                    "No term with several meanings had a clear answer from the words around it.")
    return n


def accept_context(page, terms=None):
    n = AM.accept_context(page.session, terms)
    page.fill()
    page.host.toast(f"Context suggestion accepted for {n} term(s), each saved like a choice.")
    return n


def fix_misread(page, term, right=None):
    """3.51.0 Fix OCR: what the reader read (this term) and what it should be; every later scan on this PC reads it right."""
    if right is None:
        from . import symbols as SYM
        right, ok = SYM.ask_text(page, "Fix a misread", f"The reader read \"{term}\". What does the picture say? (Every later scan "
                                 "on this PC reads it that way.)", term)
        if not ok:
            return False
    right = " ".join(str(right).split())
    if not right or right == term:
        return False
    import ocrfixes as OF
    try:
        OF.add(term, right, note="fixed on the Acronyms page")
    except PermissionError:
        page.host.status(A.DB_LOCKED_MSG)
        return False
    page.host.toast(f"Fixed: {term} is read as {right} from the next scan on.")
    return True


# ------------------------------------------------------------------ on the card
def card_extras(page, t):
    """Widgets for the top of a term's card: the ready line, the context suggestion, an equation's symbols."""
    s = page.session
    d = s.results[t]
    out = []
    fl = AM.found_line(d)
    if fl:
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.label(f"Found: <b>{fl[0]}</b> ({fl[1]})"), 1)
        row.addWidget(D.button("Use", "primary", lambda: page.choose(t, fl[0])))
        out.append(row)
    ctx = d.get("context") or {}
    if ctx.get("definition") or ctx.get("mixed"):
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.label("Context suggests: " + A.ctx_text(d), "muted"), 1)
        if ctx.get("definition"):
            row.addWidget(D.button("Accept", None, lambda: accept_context(page, [t])))
        out.append(row)
    eq = AM.equation_symbols(s, t)
    if eq:
        lw = QListWidget(); lw.setMaximumHeight(110)
        lw.addItems([f"{sym}: {mean or 'never defined'}" for sym, mean in eq])
        out.append(D.SectionTitle(f"In the same equation ({sum(1 for _s, m in eq if not m)} never defined)"))
        out.append(lw)
    return out


def confirm(page, text):
    return QMessageBox.question(page, "Stationkeeper", text) == QMessageBox.Yes


def ocr_fixes_window(page, run=True):
    """3.51.0: the fixes for misread text: view, add, edit, remove, undo the last change. Returns the dialog."""
    import ocrfixes as OF
    dlg = QDialog(page); dlg.setWindowTitle("Fixes for misread text"); dlg.resize(680, 520)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("What the reader gets wrong in pictures and what it should be. Every later scan on this PC reads it right, "
                        "for every effort. This is not training: the Training app's Trainer makes the reader itself better.", "muted"))
    t = QTableWidget(0, 3); t.setHorizontalHeaderLabels(["Read as", "Should be", "Note"]); t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True); t.setSelectionBehavior(QTableWidget.SelectRows)
    v.addWidget(t, 1)
    state = {"loading": False}

    def fill():
        state["loading"] = True
        rs = OF.rows()
        t.setRowCount(len(rs))
        for r, row in enumerate(rs):
            for c, val in enumerate(row):
                t.setItem(r, c, QTableWidgetItem(val))
        state["loading"] = False

    def edited(item):
        if state["loading"]:
            return
        r = item.row()
        vals = [(t.item(r, c).text() if t.item(r, c) else "") for c in range(3)]
        OF.update(r, *vals)

    def add():
        OF.add("misread", "correct", "new fix: type over both")
        fill(); t.setCurrentCell(t.rowCount() - 1, 0)

    def remove():
        OF.remove([i.row() for i in t.selectionModel().selectedRows()]); fill()

    def undo():
        if OF.undo():
            fill()

    t.itemChanged.connect(edited)
    row = QHBoxLayout(); v.addLayout(row)
    for text, fn in (("Add", add), ("Remove", remove), ("Undo the last change", undo)):
        row.addWidget(D.button(text, None, fn))
    row.addStretch(1); row.addWidget(D.button("Close", "ghost", dlg.accept))
    dlg.table, dlg.fill = t, fill
    fill()
    if run:
        dlg.exec()
    return dlg
