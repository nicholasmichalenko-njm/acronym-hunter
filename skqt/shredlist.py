"""Shred > As a table (4.54.0; UX decisions 5 and 62; Nicholas 2026-11-17 13:52: flat rows that sort). Shred is one
page with two views, On the page and As a table. The table has one row per piece of the shred (every piece the page
boxes: no header row, no Heading): ID, Type (a suggestion waiting shows its type with "?"), Section, Page, Words (the
trigger word) and the piece on one line. A column heading sorts by it (Page by number, Section in natural order); the
document's own order is the start. Filters: the document, the type, Not shredded only.

A change here is the same act as on the page: the selected rows are selected on the page and its own code sets the type
(skqt/shredbar.toggle_piece) or takes the suggestion (accept_suggestions), in its Undo steps; Ctrl+Z is the page's Undo.
The page's keys work here (each type's letter, as set in Settings; Enter takes the suggestion and goes to the next row not
shredded; N goes to the next). Export > Draft compliance matrix... writes the rows shown, in the order shown
(shredquick.export_rows). tree() (4.19.0, the shred under the customer's headings) is kept for its callers; the tree is no
longer shown. Rules only (No AI); nothing leaves the PC."""
import datetime
import os
import re

import shredwords as SW

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

import diag
from . import design as D

ALL = "Every document"


def _decided(it):
    return bool(it.get("decision") or it.get("piece"))


def _parts(num):
    """L.3.2 -> ["L.3", "L.3.2"]; 3.1.2 -> ["3", "3.1", "3.1.2"]; "" -> []."""
    if not num:
        return []
    bits = num.split(".")
    start = 2 if bits[0].isalpha() and len(bits) > 1 else 1
    return [".".join(bits[:k]) for k in range(start, len(bits) + 1)]


def tree(M, file=None, undecided=False, kind=""):
    """[(file, [node])]: node {"num", "title", "level", "pieces": [item], "kids": [node], "n", "done"} for each heading
    with pieces under it (and the headings above it)."""
    import shredtypes as ST
    titles = {}
    for h in getattr(M, "headings", []):
        if h.get("num"):
            titles.setdefault((h.get("file", ""), h["num"]), h.get("title", ""))
    out, files = [], []
    for it in M.items:
        f = it.get("file", "")
        if f and f not in files and (file in (None, "", ALL) or f == file):
            files.append(f)
    for f in files:
        nodes, roots = {}, []

        def node(key, num, title, level, parent):
            if key in nodes:
                return nodes[key]
            n = {"num": num, "title": title, "level": level, "pieces": [], "kids": [], "n": 0, "done": 0}
            nodes[key] = n
            (parent["kids"] if parent is not None else roots).append(n)
            return n
        for it in M.items:
            if it.get("file", "") != f or it.get("header") == "Yes" or it.get("type") == "Heading":
                continue
            if undecided and _decided(it):
                continue
            if kind and not ST.has(it, kind):
                continue
            num, title = it.get("section", "") or "", it.get("section_title", "") or ""
            parent = None
            parts = _parts(num)
            for k, p in enumerate(parts):
                last = k == len(parts) - 1
                t = title.split(" > ")[0] if last else titles.get((f, p), "")
                parent = node((p, None), p, t, k + 1, parent)
            segs = title.split(" > ")[1:] if parts else [s for s in title.split(" > ") if s]
            for k, s in enumerate(segs):
                parent = node((num, " > ".join(segs[:k + 1])), "", s, len(parts) + k + 1, parent)
            if parent is None:
                parent = node(("", ""), "", "Before the first heading", 1, None)
            parent["pieces"].append(it)

        def count(n):
            n["n"] = len(n["pieces"]) + sum(count(k)[0] for k in n["kids"])
            n["done"] = sum(1 for it in n["pieces"] if _decided(it)) + sum(k["done"] for k in n["kids"])
            return n["n"], n["done"]
        for r in roots:
            count(r)
        out.append((f, roots))
    return out


def pieces(M):
    """The pieces the page boxes, in the document's order: no header row and no Heading."""
    return [it for it in M.items if it.get("header") != "Yes" and it.get("type") != "Heading"]


def _nat(s):
    """Natural order: 3.2 before 3.10."""
    return tuple((0, int(x), "") if x.isdigit() else (1, 0, x.casefold()) for x in re.split(r"(\d+)", str(s or "")) if x)


def _page(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 10 ** 9


COLS = ["ID", "Type", "Section", "Page", "Words", "Piece"]


class ListPage(QWidget):
    COLS = COLS

    def __init__(self, host):
        super().__init__()
        from .commandbar import CommandBar
        self.setObjectName("page")
        self.host = host
        self.rows, self.sort_col, self.desc, self._keys = [], None, False, []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.top = QWidget(); top = QHBoxLayout(self.top); top.setContentsMargins(0, 0, 0, 0); v.addWidget(self.top)
        self.bar = CommandBar(); top.addWidget(self.bar, 1)
        self.type_menu = self.bar.add_menu("Set type", "Put a type on the selected pieces, or take it off (the page's keys work here too)")
        self.type_menu.aboutToShow.connect(self.fill_type_menu)
        self.type_acts = {}
        self.b_take = self.bar.add("Take the suggestion", lambda: self.take(),
                                   "Enter: each selected piece takes its suggested type, then the next row not shredded is selected")
        self.b_open = self.bar.add("Open on the page", lambda: self.open_current(), "The selected piece on its page (or double-click a row)")
        self.bar.export("Draft compliance matrix...", lambda: self.export(), "The rows shown, in the order shown, as an Excel workbook")
        self.doc = QComboBox(); self.doc.setMinimumWidth(220); self.doc.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.doc)
        self.kind = QComboBox(); self.kind.currentIndexChanged.connect(lambda _i: self.fill()); top.addWidget(self.kind)
        self.only = QCheckBox("Not shredded only"); self.only.toggled.connect(lambda _on: self.fill()); top.addWidget(self.only)
        self.say = D.label("", "muted"); v.addWidget(self.say)
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels(COLS)
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.t.setWordWrap(False)
        hh = self.t.horizontalHeader(); hh.setSectionResizeMode(5, QHeaderView.Stretch); hh.setSectionsClickable(True)
        hh.sectionClicked.connect(self.sort_by)
        for c, w in enumerate((90, 170, 240, 50, 90)):
            self.t.setColumnWidth(c, w)
        self.t.cellDoubleClicked.connect(lambda r, _c: self.open_current(r))
        v.addWidget(self.t, 1)
        self.empty = D.EmptyState("Nothing shredded yet", "Add a customer document in Documents; its pieces show here, one row "
                                  "each, once it is extracted.", "Go to Shred", lambda: self.host.go("assign"))
        v.addWidget(self.empty); self.empty.hide()

    # ------------------------------------------------------------ what shows
    def types(self):
        import shredtypes as ST
        try:
            return ST.load(self.host.config_dir)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return {}

    def refresh(self):
        """Called as the table opens. From the page, the table follows the page's place (its piece selected)."""
        h = self.host
        pg = getattr(h, "assign_page", None)
        came = pg is not None and h.stack.currentWidget() is pg
        keep_doc, keep_kind = self.doc.currentText(), self.kind.currentData()
        for cb in (self.doc, self.kind):
            cb.blockSignals(True); cb.clear()
        self.doc.addItem(ALL)
        if h.review is not None:
            for f in h.review.files():
                self.doc.addItem(f)
        if keep_doc and self.doc.findText(keep_doc) >= 0:
            self.doc.setCurrentText(keep_doc)
        self.kind.addItem("Every type", "")
        import shredtypes as ST
        types = self.types()
        for k in ST.KEYS:
            self.kind.addItem((types.get(k) or {}).get("name", k), k)
        if keep_kind:
            self.kind.setCurrentIndex(max(0, self.kind.findData(keep_kind)))
        for cb in (self.doc, self.kind):
            cb.blockSignals(False)
        self.bind_keys()
        if pg is not None and h.review is not None and not pg.sg_on and pg.cx is None:
            __import__("skqt.shredfocus", fromlist=["x"]).suggest_on(pg)      # the suggestions, as the page works them out
        at = None
        if came:
            sel = pg.selected()
            at = sel[-1]["id"] if sel else getattr(pg, "cur", None)
        return self.show_piece(at) if at else self.fill()

    def suggested(self, it):
        pg = getattr(self.host, "assign_page", None)
        return __import__("skqt.typechips", fromlist=["x"]).suggested(pg, it) if pg is not None else ""

    def key_of(self, col, it, n):
        import shredtypes as ST
        if col == 0:
            return (_nat(it.get("id")), n)
        if col == 1:
            ks = ST.types_of(it)
            names = ", ".join((self._types.get(k) or {}).get("name", k) for k in ks)
            sug = "" if ks else self.suggested(it)
            return (0 if ks else 1 if sug else 2, (names or sug).casefold(), n)
        if col == 2:
            num = it.get("section") or ""
            return (0 if num else 1, _nat(num), (it.get("section_title") or "").casefold(), n)
        if col == 3:
            return (_page(it.get("page")), n)
        if col == 4:
            return (0 if it.get("modal") else 1, (it.get("modal") or "").casefold(), n)
        return (re.sub(r"\s+", " ", it.get("text") or "").casefold(), n)

    def fill(self, keep=None):
        """The rows the filters let through, in the order asked for. keep: the ids to select again (else the selection
        stays). Returns how many rows show."""
        import shredtypes as ST
        R = self.host.review
        keep = self.ids() if keep is None else keep
        self.t.setRowCount(0); self.rows = []
        has = R is not None and bool(pieces(R.M))
        for x in (self.t, self.top, self.say):
            x.setVisible(has)
        self.empty.setVisible(not has)
        if not has:
            self.say.setText("")
            return 0
        self._types = types = self.types()
        f, k = self.doc.currentText(), self.kind.currentData() or ""
        order = {id(it): n for n, it in enumerate(R.M.items)}
        base = [it for it in pieces(R.M) if (f in ("", ALL) or it.get("file", "") == f) and (not k or ST.has(it, k))]
        done = sum(1 for it in base if _decided(it))
        rows = [it for it in base if not (self.only.isChecked() and _decided(it))]
        if self.sort_col is not None:
            rows.sort(key=lambda it: self.key_of(self.sort_col, it, order[id(it)]), reverse=self.desc)
        self.rows = rows
        muted = D.color("muted")
        self.t.setRowCount(len(rows))
        for r, it in enumerate(rows):
            ks = ST.types_of(it)
            names = ", ".join((types.get(x) or {}).get("name", x) for x in ks)
            sug = "" if ks else self.suggested(it)
            txt = re.sub(r"\s+", " ", it.get("text") or "").strip()
            sec = " ".join(x for x in (it.get("section") or "", it.get("section_title") or "") if x)
            vals = (it.get("id", ""), names or ((types.get(sug) or {}).get("name", sug) + "?" if sug else ""), sec,
                    str(it.get("page") or ""), it.get("modal") or "", txt)
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                if c == 0:
                    cell.setData(Qt.UserRole, (it.get("file", ""), it.get("id", "")))
                if c == 1 and sug:
                    fo = cell.font(); fo.setItalic(True); cell.setFont(fo); cell.setForeground(muted)
                    cell.setToolTip("Suggested. Not set yet.")
                elif c in (2, 5):
                    cell.setToolTip(val)
                self.t.setItem(r, c, cell)
        self.say.setText(SW.progress(done, len(base)) if rows else "No piece matches.")
        self.select_ids(keep)
        return len(rows)

    def sort_by(self, col):
        """A column heading: sort by it; again, the other way."""
        self.desc = (not self.desc) if self.sort_col == col else False
        self.sort_col = col
        hh = self.t.horizontalHeader()
        hh.setSortIndicatorShown(True); hh.setSortIndicator(col, Qt.DescendingOrder if self.desc else Qt.AscendingOrder)
        return self.fill()

    # ------------------------------------------------------------ the selection
    def ids(self):
        return [self.rows[r]["id"] for r in sorted({i.row() for i in self.t.selectionModel().selectedRows()}) if r < len(self.rows)]

    def selected(self):
        R = self.host.review
        return [x for x in (R.item(i) for i in self.ids()) if x] if R is not None else []

    def select_ids(self, ids):
        at = {it["id"]: r for r, it in enumerate(self.rows)}
        rows = [at[i] for i in ids or [] if i in at]
        self.t.clearSelection()
        if not rows:
            return []
        sm, model = self.t.selectionModel(), self.t.model()
        from PySide6.QtCore import QItemSelectionModel
        self.t.setCurrentCell(rows[-1], 0, QItemSelectionModel.NoUpdate)
        for r in rows:
            sm.select(model.index(r, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.t.scrollToItem(self.t.item(rows[0], 0))
        return rows

    def show_piece(self, iid):
        """Select a piece's row (the page's place); its document shows when the document filter would hide it."""
        R = self.host.review
        it = R.item(iid) if R is not None and iid else None
        if it is not None and self.doc.currentText() not in ("", ALL, it.get("file", "")):
            self.doc.blockSignals(True); self.doc.setCurrentText(it.get("file", "")); self.doc.blockSignals(False)
        return self.fill(keep=[iid] if it is not None else None)

    # ------------------------------------------------------------ the same acts as on the page
    def onto_page(self, rows):
        """The rows selected on the page, so its own code acts on them. None (and the status line says why) when they
        are of two documents or the page cannot take them."""
        h = self.host
        pg = h.assign_page
        files = {it.get("file", "") for it in rows}
        if len(files) != 1:
            h.status("Select pieces of one document.")
            return None
        f = files.pop()
        try:
            if pg.cx is not None or pg.file != f:
                if pg.files.findText(f) >= 0:
                    pg.files.setCurrentText(f)
                if pg.cx is not None or pg.file != f:
                    pg.open_file(f)
            pg._guard = True
            pg.view.scene().clearSelection()
            for it in rows:
                b = pg.view.boxes.get(it["id"])
                if b is not None:
                    b.setSelected(True)
            pg._guard = False
            pg.on_select()
            if not pg.sg_on:
                __import__("skqt.shredfocus", fromlist=["x"]).suggest_on(pg)
        except Exception:  # noqa: BLE001
            pg._guard = False
            diag.swallowed()
        return pg if pg.R is not None and pg.cx is None and pg.file == f else None

    def set_type(self, key, rows=None):
        """Set type (or the type's letter): on for every selected piece, off when all of them have it; stays."""
        rows = rows if rows is not None else self.selected()
        if not rows:
            self.host.status("Select a piece first.")
            return None
        pg = self.onto_page(rows)
        if pg is None:
            return None
        on = __import__("skqt.shredbar", fromlist=["x"]).toggle_piece(pg, key, rows)
        self.fill(keep=[it["id"] for it in rows])
        return on

    def fill_type_menu(self):
        import shredtypes as ST
        m, rows, types = self.type_menu, self.selected(), self.types()
        letter = {v: k for k, v in self.type_keys().items()}
        m.clear(); self.type_acts = {}
        for k in ST.KEYS:
            t = types.get(k) or {}
            if not t.get("shown", True):
                continue
            a = m.addAction((t.get("name", k) + (f"   {letter[k]}" if k in letter else "")).replace("&", "&&"))
            a.setCheckable(True); a.setChecked(bool(rows) and all(ST.has(it, k) for it in rows))
            a.triggered.connect(lambda _c=False, key=k: self.set_type(key))
            self.type_acts[k] = a
        return self.type_acts

    def take(self):
        """Enter or Take the suggestion: each selected row takes its suggestion, then the next row not shredded after the
        last one (in the table's order) is selected. With no suggestion waiting nothing changes and the selection stays."""
        rows = self.selected()
        if not rows:
            self.host.status("Select a piece first.")
            return 0
        pg = self.onto_page(rows)
        if pg is None:
            return 0
        before = [it["id"] for it in self.rows]
        n = pg.accept_suggestions(rows=rows)
        if not n:
            self.fill(keep=[it["id"] for it in rows])
            return 0
        last = max(before.index(it["id"]) for it in rows if it["id"] in before) if before else -1
        R = self.host.review
        open_ = [i for i in before if (R.item(i) is not None and not _decided(R.item(i)))]
        nxt = next((i for i in open_ if before.index(i) > last), open_[0] if open_ else None)
        self.fill(keep=[nxt] if nxt else [it["id"] for it in rows])
        if not nxt:
            self.host.status("Every piece shown has a type.")
        return n

    def next_open(self):
        """N: the next row not shredded after the one selected, in the table's order."""
        cur = self.ids()
        at = max(r for r, it in enumerate(self.rows) if it["id"] in cur) if cur else -1
        left = [r for r, it in enumerate(self.rows) if not _decided(it)]
        if not left:
            self.host.status("Nothing left here.")
            return None
        r = next((x for x in left if x > at), left[0])
        self.select_ids([self.rows[r]["id"]])
        return self.rows[r]["id"]

    def type_keys(self):
        return __import__("skqt.shredbar", fromlist=["x"]).type_keys(self.host.assign_page)

    def bind_keys(self):
        """The page's keys on the table: each type's letter as set in Settings, Enter, N."""
        for sc in self._keys:
            sc.setEnabled(False); sc.setParent(None); sc.deleteLater()
        self._keys = []
        try:
            keys = self.type_keys()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            keys = {}
        for seq, k in list(keys.items()) + [("Return", None), ("N", None)]:
            fn = (lambda key=k: self.set_type(key)) if k else (self.take if seq == "Return" else self.next_open)
            self._keys.append(QShortcut(QKeySequence(seq), self.t, activated=fn))
        return keys

    def undo_text(self):
        pg = self.host.assign_page
        return pg.undo_text() if pg.R is not None else ""

    def undo_here(self):
        """Ctrl+Z: the page's Undo (the same steps); the table shows what it put back."""
        got = self.host.assign_page.do_undo()
        self.fill()
        return got

    # ------------------------------------------------------------ to the page, and out
    def open_current(self, row=None):
        """Open on the page (or a double-click): the document, with the current row's piece selected."""
        r = self.t.currentRow() if row is None else row
        if r is None or r < 0 or r >= len(self.rows):
            sel = self.ids()
            if not sel:
                self.host.status("Select a piece first.")
                return False
            r = [it["id"] for it in self.rows].index(sel[-1])
        f, iid = self.rows[r].get("file", ""), self.rows[r]["id"]
        h = self.host
        if h.go("assign") is False:
            return False
        pg = h.assign_page
        try:
            if pg.file != f:
                pg.files.setCurrentText(f)
                if pg.file != f:
                    pg.open_file(f)
            pg.select(iid)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return False
        return True

    def export(self, path=None):
        """Export > Draft compliance matrix...: the rows shown, in the order shown, with an About sheet naming the scan."""
        import datum as DT
        import filesafety as FS
        import shredquick as SQ
        import shredtypes as ST
        h, R = self.host, self.host.review
        rows = [x for x in (R.item(it["id"]) for it in self.rows) if x] if R is not None else []
        if not rows:
            h.status("No piece shows in the table.")
            return None
        files = list(dict.fromkeys(it.get("file", "") for it in rows))
        sources = [R.M.path_of(f) for f in files] + [getattr(R.M, "path", "")]
        if path is None:
            near = next((os.path.dirname(p) for p in sources if p), "")
            start = os.path.join(near, f"{h.effort_name or 'Shred'} - draft compliance matrix.xlsx")
            path, _ = QFileDialog.getSaveFileName(self, "Export the draft compliance matrix", start, "Excel (*.xlsx)")
            if not path:
                return None
        types = self.types()
        out = []
        for it in rows:
            ks = ST.types_of(it)
            sug = "" if ks else self.suggested(it)
            out.append({"id": it.get("id", ""), "type": ", ".join((types.get(k) or {}).get("name", k) for k in ks),
                        "section": it.get("section", ""), "title": it.get("section_title", ""), "page": it.get("page") or "",
                        "words": it.get("modal", ""), "text": " ".join((it.get("text") or "").split()), "loc": it.get("loc", ""),
                        "suggest": (types.get(sug) or {}).get("name", sug) if sug else ""})
        try:
            mark = DT.mark(DT.state(h.config_dir))
        except Exception:  # noqa: BLE001
            diag.swallowed()
            mark = "No Production Datum installed"
        about = [["Documents", ", ".join(files)], ["Made", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
                 ["Rows", len(out)], ["Working from", mark],
                 ["Note", "A draft from Shred's table: the rows shown, in the order shown."]]
        try:
            n = SQ.export_rows(out, path, about, sources)
        except FS.WouldOverwrite:
            h.status("That is a file the shred reads. Pick another name.")
            return None
        except PermissionError:
            h.status("That file is open in Excel. Close it, then export again.")
            return None
        h.toast(f"{n} row(s) exported to {os.path.basename(path)}.")
        return path
