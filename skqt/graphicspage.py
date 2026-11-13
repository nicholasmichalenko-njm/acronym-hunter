"""Graphics (4.25.5; Nicholas's recording 2026-11-12: "its own menu item here for graphics"; the Documents board, step
E). One row per graphic: a picture in Documents, every picture the reader saw inside a document (4.29.2), and each graphic
need tagged in Shred. Per row, on its current version: are its words read, are its acros and abs swept. The row opens
the picture in Acros & Abs with the words the reader found. Nothing is kept twice: the rows are read from Documents,
the scan and the effort record (graphiclog). Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLineEdit, QMenu, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import graphiclog as GL
from . import design as D
from .commandbar import CommandBar

SIDE = {"customer": "Customer", "ours": "Internal"}
TONE = {"swept": "ok", "decide": "warn", "decided": "warn", "none": "warn", "not": "muted", "": "muted"}


class GraphicsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        self.rows = []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.bar.primary("Add graphics...", lambda: self.add(), "Pictures of ours: each is added to Documents as an Internal "
                         "graphic, read, and listed here")
        v.addWidget(self.bar)
        row = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Find a graphic"); self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self.fill())
        self.flt = QComboBox()
        for k, n in GL.FILTERS:
            self.flt.addItem(n, k)
        self.flt.currentIndexChanged.connect(lambda _i: self.fill())
        row.addWidget(self.search, 1); row.addWidget(self.flt)
        v.addLayout(row)
        self.count = D.label("", "muted"); v.addWidget(self.count)
        self.table = QTableWidget(0, len(GL.COLUMNS))
        self.table.setHorizontalHeaderLabels(GL.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        for c in range(len(GL.COLUMNS)):
            hh.setSectionResizeMode(c, QHeaderView.Stretch if c == 0 else QHeaderView.Interactive)
        for c, wd in enumerate((0, 220, 90, 110, 120, 90, 160, 190)):
            if c:
                self.table.setColumnWidth(c, wd)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.menu)
        self.table.doubleClicked.connect(lambda _ix: self.open_row())
        v.addWidget(self.table, 1)
        self.empty = D.EmptyState("No graphics yet",
                                  "A picture you add, a picture inside a customer document that the scan reads, and a graphic "
                                  "need you tag in Shred each get a row here.", "Add graphics...", lambda: self.add())
        v.addWidget(self.empty, 1)

    # ------------------------------------------------------------------ the rows
    def lib(self):
        import docversions as DV
        return DV.Library(self.host.ws.p("documents")).load() if self.host.ws is not None else None

    def all_rows(self):
        h = self.host
        if h.ws is None:
            return []
        import acrpages as AG
        import graphics as GX
        ap = getattr(h, "acronym_page", None)
        s = ap.session if ap is not None else None
        try:
            pages = AG.pages(s.results, AG.done_set(s.ws)) if s is not None and s.results else []
            scanned = ((s.last_scan or {}).get("paths") or []) if s is not None else []
        except Exception:  # noqa: BLE001
            diag.swallowed()
            pages, scanned = [], []
        needs = GX.items(self.rec())
        return GL.rows(self.lib(), pages, scanned, AG.done_set(h.ws), GL.words_ok(h.ws), needs,
                       pictures=getattr(s, "pictures", None) if s is not None else None)

    def rec(self):
        import effortrec as RR
        return RR.Record(self.host.ws.root)

    def refresh(self):
        return self.fill()

    def fill(self):
        keep = self.current()["id"] if self.current() else None
        every = self.all_rows()
        self.rows = GL.shown(every, self.flt.currentData() or "", self.search.text())
        t = self.table
        t.setRowCount(len(self.rows))
        for r, g in enumerate(self.rows):
            lk = GL.linked_text(g)                           # 4.29.2: a need and its picture name each other
            vals = (g["name"] + (f"   ({g['type']})" if g.get("type") else ""), "   ·   ".join(x for x in (g["where"], lk) if x),
                    "" if g["kind"] == "need" else SIDE[g["side"]],
                    g["version"] + (f"   {g['versions']} versions" if g["versions"] > 1 else ""), g["owner"], g["status"],
                    g["words"], g["acros"])
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 0:
                    it.setData(Qt.UserRole, g["id"])
                if c == 6 and val:
                    it.setForeground(D.color("ok" if g["words_ok"] else "warn"))
                if c == 7 and val:
                    it.setForeground(D.color(TONE.get(g["acros_state"], "muted")))
                if c == 5 and val:
                    it.setForeground(D.color("ok" if val == "Done" else "warn"))
                t.setItem(r, c, it)
            if keep and g["id"] == keep:
                t.selectRow(r)
        n, words, sweep, needs = GL.counts(every)
        self.count.setText(f"{n} graphic" + ("" if n == 1 else "s") + f": {words} with words to confirm, {sweep} to sweep for acronyms "
                           f"and abs. {needs} graphic need" + ("" if needs == 1 else "s") + " open." if every else "")
        self.empty.setVisible(not every); self.table.setVisible(bool(every))
        self.every = every
        return len(self.rows)

    def link(self, need_id, picture_id):
        """4.29.2: the picture that answers a need ("" takes the link off), set from either row. Returns True when changed."""
        import graphics as GX
        pic = next((r for r in getattr(self, "every", []) if r["id"] == picture_id), None) if picture_id else None
        ok = GX.link(self.rec(), need_id, picture_id if pic is not None else "", pic["name"] if pic is not None else "")
        if ok:
            diag.activity("qt_graphic_need_linked")
            self.fill()
        return ok

    def _link_menu(self, m, g):
        every = getattr(self, "every", [])
        if g["kind"] == "need":
            sm = m.addMenu("Answered by")
            a = sm.addAction("(no picture)", lambda: self.link(g["need"], "")); a.setCheckable(True); a.setChecked(not g.get("picture"))
            sm.addSeparator()
            for r in [x for x in every if x["kind"] != "need"][:40]:
                a = sm.addAction(f"{r['name']}   ({r['where']})", lambda r=r: self.link(g["need"], r["id"]))
                a.setCheckable(True); a.setChecked(g.get("picture") == r["id"])
        else:
            needs = [x for x in every if x["kind"] == "need"]
            if not needs:
                return None
            sm = m.addMenu("Answers the need")
            for r in needs[:40]:
                on = r.get("picture") == g["id"]
                a = sm.addAction(r["name"], lambda r=r, on=on: self.link(r["need"], "" if on else g["id"]))
                a.setCheckable(True); a.setChecked(on)
        return sm

    def current(self):
        r = self.table.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def select(self, rid):
        for r, g in enumerate(self.rows):
            if g["id"] == rid:
                self.table.selectRow(r)
                return True
        return False

    # ------------------------------------------------------------------ what a row does
    def add(self, paths=None):
        """Pictures of ours, added to Documents as Internal graphics (Documents reads them; the row appears here)."""
        h = self.host
        if h.ws is None:
            return None
        if paths is None:
            paths, _f = QFileDialog.getOpenFileNames(self, "Add graphics", "", "Pictures (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif "
                                                     "*.webp *.svg *.emf *.wmf *.pdf *.pptx);;Every file (*)")
        if not paths:
            return None
        from .watchauto import _Same
        diag.activity("graphics_added", n=len(paths))
        w = h.library_page.add(list(paths), category="graphics", choices=_Same(role="reference"))
        if w is not None:
            w.finished.connect(lambda: self.fill())
        return w

    def open_row(self, g=None):
        """The picture in Acros & Abs, with the words the reader found; a need opens where it was tagged."""
        g = g or self.current()
        h = self.host
        if g is None:
            return False
        if g["kind"] == "need":
            h.go("home")
            return True
        if not g["page"]:
            h.status("The scan found no terms in it, so there is no page to show. Open the file to look at it.")
            return False
        h.go("acronyms")
        ap = h.acronym_page
        if getattr(ap, "tabs", None) is not None:
            ap.tabs.setCurrentIndex(0)
        ap.onpage.fill()
        ap.onpage.go(g["page"])
        return True

    def open_file(self, g=None):
        g = g or self.current()
        if g is None or not g["doc"]:
            return False
        h = self.host
        h.go("library")
        return h.library_page.select(g["doc"])

    def set_words(self, on, g=None):
        g = g or self.current()
        if g is None or not g["keys"]:
            return False
        GL.set_words_ok(self.host.ws, g["keys"], on)
        diag.activity("graphic_words_confirmed", n=int(bool(on)))
        self.fill()
        return True

    def set_swept(self, on, g=None):
        import acrpages as AG
        g = g or self.current()
        if g is None or not g["keys"]:
            return False
        for k in g["keys"]:
            AG.set_done(self.host.ws, k, on)
        diag.activity("graphic_swept", n=int(bool(on)))
        self.fill()
        return True

    def set_status(self, status, g=None):
        import graphics as GX
        g = g or self.current()
        if g is None or g["kind"] != "need":
            return False
        ok = GX.update(self.rec(), g["need"], status=status)
        self.fill()
        return ok

    def scan(self, g=None):
        """Find acros and abs in this graphic now: the last scan's files again, with this one."""
        g = g or self.current()
        h = self.host
        if g is None or not g["file"]:
            return None
        p = h.acronym_page.path_of(g["file"])
        if not p:
            h.status("Its file is not on this PC.")
            return None
        import os
        s = h.acronym_page.session
        last = [q for q in (((s.last_scan or {}).get("paths") or []) if s is not None else []) if os.path.isfile(q)]
        # a scan replaces what the last one found, so this one reads the last scan's files again with the graphic added
        return h.acronym_page.scan(list(dict.fromkeys(last + [p])))

    def menu(self, pos):
        g = self.current()
        if g is None:
            return None
        m = QMenu(self)
        if g["kind"] == "need":
            for s in ("Needed", "In work", "Done"):
                a = m.addAction(s, lambda s=s: self.set_status(s)); a.setCheckable(True); a.setChecked(g["status"] == s)
        else:
            m.addAction("Open it in Acronyms", lambda: self.open_row())
            m.addAction("Show its document", lambda: self.open_file())
            m.addSeparator()
            a = m.addAction("Words read: confirmed", lambda: self.set_words(not g["words_ok"])); a.setCheckable(True); a.setChecked(g["words_ok"])
            a = m.addAction("Acronyms: swept", lambda: self.set_swept(g["acros_state"] != "swept")); a.setCheckable(True)
            a.setChecked(g["acros_state"] == "swept")
            if g["kind"] == "file":
                m.addSeparator()
                m.addAction("Find acronyms in it now", lambda: self.scan())
        m.addSeparator()
        self._link_menu(m, g)
        if pos is not None:
            m.exec(self.table.viewport().mapToGlobal(pos))
        return m
