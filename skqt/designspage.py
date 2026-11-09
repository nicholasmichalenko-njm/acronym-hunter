"""Section designs (3.87.0, claude/stationkeeper-section-designs-2026-11-08.md): the library of sections built in Word,
kept whole: CUI cover, Cover, Title page, Table of Contents, Acronyms and Abbreviations, Units and Symbols, Back cover.
A library only: Setup picks a design per section. Bring in from Word... puts a file on a shelf (a file with several
Word sections is offered as one design per section, Keep or Skip each). The selected design shows what fills it (one
row per styled paragraph, set once), the text other pages read, and the check (quiet unless a STYLEREF source is
missing or in a text box). Act on the row: Open in Word, Replace with an updated file..., Remove from the library.
Rules: sectiondesigns. Nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFileDialog, QInputDialog, QMenu, QSplitter, QTableWidget,
                               QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import diag
import sectiondesigns as SDZ
from . import design as D


class DesignsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.cur = None
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["s"])
        from .commandbar import CommandBar
        bar = self.bar = CommandBar()
        bar.primary("Bring in from Word...", lambda: self.bring_in(), "A Word file onto a shelf: read, never changed. "
                    "A file with several Word sections is offered as one design per section.")
        v.addWidget(bar)
        v.addWidget(D.label("Build each section in Word on the team template: text that changes per effort in its own "
                            "paragraph and style, each STYLEREF source in its own style. Setup picks a design for each "
                            "section of a volume.", "muted"))
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Section designs", "From"])
        self.tree.setColumnWidth(0, 320)
        self.tree.currentItemChanged.connect(lambda it, _o: self.show_design(it.data(0, Qt.UserRole) if it else None))
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(lambda p: self.row_menu(self.tree.viewport().mapToGlobal(p)))
        self.tree.itemDoubleClicked.connect(lambda _it, _c: self.row_menu())
        split.addWidget(self.tree)
        side = QWidget(); sv = QVBoxLayout(side); sv.setContentsMargins(D.SPACE["s"], 0, 0, 0)
        self.title = D.label("", "title"); sv.addWidget(self.title)
        from PySide6.QtWidgets import QLabel                     # 3.87.1: the page, drawn by Word or sketched
        self.thumb = QLabel(); self.thumb.setFixedSize(230, 300); self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("QLabel { border: 1px solid %s; background: white; }" % D.tokens()["border"])
        self.thumb_note = D.label("", "muted")
        sv.addWidget(self.thumb); sv.addWidget(self.thumb_note)
        sv.addWidget(D.label("What fills it", "label"))
        self.fills = QTableWidget(0, 3); self.fills.setHorizontalHeaderLabels(["Paragraph", "Style", "Fill-in (blank: as written)"])
        self.fills.horizontalHeader().setStretchLastSection(True)
        self.fills.itemChanged.connect(self.fill_changed)
        sv.addWidget(self.fills, 1)
        sv.addWidget(D.label("Text other pages read", "label"))
        self.others = D.label("", "muted"); sv.addWidget(self.others)
        self.problems = D.label("", None); sv.addWidget(self.problems)
        split.addWidget(side); split.setSizes([420, 640])
        self.empty = D.EmptyState("No section designs yet", "Build a cover, a title page or a front matter section in Word, "
                                  "then bring it in here. Setup picks a design for each section of a volume.",
                                  "Bring in from Word...", lambda: self.bring_in())
        v.addWidget(self.empty)
        self._guard = False

    def cfg(self):
        return self.host.config_dir

    def refresh(self):
        self.tree.clear()
        n = 0
        for shelf in SDZ.SHELVES:
            head = QTreeWidgetItem([SDZ.SHELF_NAME[shelf], ""]); head.setFlags(Qt.ItemIsEnabled)
            self.tree.addTopLevelItem(head)
            for x in SDZ.designs(self.cfg(), shelf):
                it = QTreeWidgetItem([x["name"], x.get("from", "")]); it.setData(0, Qt.UserRole, x["id"])
                head.addChild(it); n += 1
            head.setExpanded(True)
        self.empty.setVisible(n == 0)
        self.tree.parentWidget().setVisible(n > 0)
        if self.cur and SDZ.get(self.cfg(), self.cur):
            self.select(self.cur)
        else:
            self.show_design(None)

    def select(self, did):
        it = self.tree.invisibleRootItem()
        for i in range(it.childCount()):
            h = it.child(i)
            for k in range(h.childCount()):
                if h.child(k).data(0, Qt.UserRole) == did:
                    self.tree.setCurrentItem(h.child(k))
                    return True
        return False

    # ------------------------------------------------------------ bringing files in
    def ask_shelf(self):
        names = [SDZ.SHELF_NAME[s] for s in SDZ.SHELVES]
        got, ok = QInputDialog.getItem(self, "Which section is it?", "Shelf:", names, 1, False)
        return SDZ.SHELVES[names.index(got)] if ok else None

    def bring_in(self, path=None, shelf=None, keep=None):
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "Bring in from Word", "", "Word (*.docx *.dotx)")
            if not path:
                return []
        info = SDZ.read(path)
        files = [path]
        if info["sections"] > 1:                          # several Word sections: one design each, Keep or Skip
            import tempfile
            out = tempfile.mkdtemp(prefix="sk_designs_")
            files = SDZ.split(path, out, keep=keep)
        added = []
        for f in files:
            sh = shelf or self.ask_shelf()
            if not sh:
                continue
            added.append(SDZ.add(self.cfg(), sh, f))
        if added:
            diag.activity("section_design_added", n=len(added))
            self.cur = added[-1]["id"]
            self.refresh()
            self.host.status(f"{len(added)} design(s) brought in. Set what fills each one on the right.")
        return added

    # ------------------------------------------------------------ the selected design
    def show_design(self, did):
        self.cur = did
        x = SDZ.get(self.cfg(), did) if did else None
        self._guard = True
        self.fills.setRowCount(0)
        if x is None:
            self.title.setText(""); self.others.setText(""); self.problems.setText("")
            self._guard = False
            return
        path = SDZ.path_of(self.cfg(), x)
        self.title.setText(f"{x['name']}  ·  {SDZ.SHELF_NAME[x['shelf']]}")
        try:
            info = SDZ.read(path)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            self.problems.setText("This design's file could not be read.")
            self._guard = False
            return
        for p in info["paragraphs"]:
            if not p["text"].strip():
                continue
            r = self.fills.rowCount(); self.fills.insertRow(r)
            a = QTableWidgetItem(p["text"][:80]); a.setFlags(Qt.ItemIsEnabled); a.setData(Qt.UserRole, str(p["i"]))
            b = QTableWidgetItem(p["style"]); b.setFlags(Qt.ItemIsEnabled)
            c = QTableWidgetItem(x["map"].get(str(p["i"]), ""))
            self.fills.setItem(r, 0, a); self.fills.setItem(r, 1, b); self.fills.setItem(r, 2, c)
        self.show_thumb(path, info)
        src = SDZ.other_pages(path)
        self.others.setText("\n".join(f"{s['style']}: {s['where'] or '(no paragraph in this style)'}"
                                      + ("  (in a text box)" if s["in_textbox"] else "") for s in src)
                            or "No header, footer or field here reads text from this design.")
        probs = SDZ.check(path)
        self.problems.setText("\n".join(probs))
        self.problems.setVisible(bool(probs))
        self._guard = False

    def fill_changed(self, item):
        if self._guard or item.column() != 2 or not self.cur:
            return
        x = SDZ.get(self.cfg(), self.cur)
        m = dict(x["map"])
        m[self.fills.item(item.row(), 0).data(Qt.UserRole)] = item.text().strip()
        SDZ.set_map(self.cfg(), self.cur, m)

    # ------------------------------------------------------------ act on the row
    def row_menu(self, at=None, run=True):
        it = self.tree.currentItem()
        did = it.data(0, Qt.UserRole) if it else None
        if not did:
            return None
        m = QMenu(self)
        m.addAction("Open in Word", lambda: self.open_word(did))
        m.addAction("Draw with Word", lambda: self.draw(did))
        m.addAction("Replace with an updated file...", lambda: self.replace(did))
        m.addSeparator()
        m.addAction("Remove from the library", lambda: self.remove(did))
        if run:
            m.exec(at or self.tree.viewport().mapToGlobal(self.tree.visualItemRect(it).bottomLeft()))
        return m

    def show_thumb(self, path, info=None):
        """Word's picture of the page when it drew one; otherwise the app's sketch, marked as one."""
        import wordpreview as WP
        from PySide6.QtGui import QPixmap
        try:
            data = open(path, "rb").read()
        except OSError:
            data = b""
        png = WP.cached(SDZ._root(self.cfg()), data) if data else ""
        if png:
            self.thumb.setPixmap(QPixmap(png).scaled(self.thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.thumb_note.setText("Drawn by Word.")
            return "word"
        info = info or SDZ.read(path)
        lines = [p["text"] for p in info["paragraphs"] if p["text"].strip()][:14]
        self.thumb.setText("\n\n".join(t[:34] for t in lines))
        self.thumb_note.setText("A sketch. Right-click the design: Draw with Word shows the exact page.")
        return "sketch"

    def draw(self, did, runner=None):
        """Word lays out the design's first page (on demand; once until the file changes)."""
        import wordpreview as WP
        x = SDZ.get(self.cfg(), did)
        p = SDZ.path_of(self.cfg(), x)
        with open(p, "rb") as f:
            data = f.read()
        res = WP.draw(SDZ._root(self.cfg()), data, runner=runner)
        if res.get("ok"):
            self.show_design(did)
        else:
            self.host.status(res.get("why", "Word could not draw the page."))
        return res

    def open_word(self, did):
        p = SDZ.path_of(self.cfg(), SDZ.get(self.cfg(), did))
        if os.environ.get("AH_TEST"):
            return p
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(p))
        return p

    def replace(self, did, path=None):
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "The updated Word file", "", "Word (*.docx *.dotx)")
            if not path:
                return None
        x = SDZ.replace(self.cfg(), did, path)
        self.refresh()
        self.host.status("Replaced. Setups already made keep the copy they used.")
        return x

    def remove(self, did):
        ok = SDZ.remove(self.cfg(), did)
        self.cur = None
        self.refresh()
        return ok
