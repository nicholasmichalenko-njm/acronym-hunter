"""Verify (3.84.0, claude/stationkeeper-verify-hands-on-2026-11-08.md): every block on every customer page gets a role,
on the page itself, before Review. The page is drawn as the PDF page; each block carries its role in the margin, a tick
when a person decided it and a mark when there is something to look at.

    Click a block, Shift+click or drag across blocks; the bar opens beside them (above, else below; never over them)
    with every role in the menu and Select all text in this section. A key sets the role (1 to 6, T, B, F, Shift+F,
    M, Shift+M, N, R, X, and your own). A click on blank page, or Esc, clears the selection.
    A caption is linked to its figure or table: the bracket in the margin is dashed while suggested, solid once
    confirmed; Confirm, or Pick another and click the object.
    A scanned page shows the reader's lines under the page: an unsure one is a flag; confirm it or correct it here (the
    correction also goes to the training file).
    The strip shows every page (verified, to look at, not yet); Prev and Next (Page Up, Page Down), the page box
    (Ctrl+G), Next to look at (F8), Page verified, next (Enter). The document button (Ctrl+O) switches document, each
    opening where it was left. Moving on never blocks; only a page's own Verified mark waits on its flags.
Rules: verifyblocks, verifystate, verifyroles. Nothing leaves the PC."""
import os

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QThread, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QSpinBox, QSplitter, QVBoxLayout, QWidget)

import diag
import verifyroles as VR
import verifystate as VS
from . import design as D
from .adaptive import FlowLayout
from .splitlines import BarHost

SCALE = 2.0
MARGIN = 70
ACT_TONE = {"heading": "accent", "text": "head", "bullet": "ctx", "object": "cust", "caption": "cust", "running": "faint", "skip": "faint"}
STATUS_TONE = {"verified": "ok", "look": "warn", "notyet": "border_strong"}


class CopyThread(QThread):
    done = Signal(str, str)

    def __init__(self, path, folder):
        super().__init__()
        self.path, self.folder = path, folder

    def run(self):
        import ocrpdf
        try:
            self.done.emit(self.path, ocrpdf.page_copy(self.path, self.folder) or "")
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.done.emit(self.path, "!" + str(e)[:200])


class PageStrip(QWidget):
    """One cell per page: green verified, amber to look at, grey not yet; the page you are on outlined."""
    picked = Signal(int)

    def __init__(self):
        super().__init__()
        self.status, self.cur = [], 0
        self.setFixedHeight(18); self.setMouseTracking(True)

    def set(self, status, cur):
        self.status, self.cur = list(status), cur
        self.setToolTip(f"{len(status)} pages: click one to go there")
        self.update()

    def _cell(self):
        n = max(1, len(self.status))
        return max(3.0, min(22.0, (self.width() - 2) / n))

    def paintEvent(self, _e):
        if not self.status:
            return
        p = QPainter(self); t = D.tokens(); w = self._cell()
        for i, s in enumerate(self.status):
            r = QRectF(1 + i * w, 3, max(2.0, w - 2), 12)
            p.fillRect(r, QColor(t.get(STATUS_TONE[s], "#999999")))
            if i + 1 == self.cur:
                p.setPen(QPen(QColor(t["focus"]), 2)); p.setBrush(Qt.NoBrush); p.drawRect(r.adjusted(-1, -2, 1, 2))
        p.end()

    def mousePressEvent(self, e):
        i = int((e.position().x() - 1) // self._cell())
        if 0 <= i < len(self.status):
            self.picked.emit(i + 1)


class PageView(QGraphicsView):
    """The page and its blocks. Clicks select; a drag selects what it crosses; blank page clears."""

    def __init__(self, page):
        super().__init__()
        self.pg = page
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing); self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.items = {}                                 # key -> rect item
        self._press = None

    def block_at(self, pos):
        sp = self.mapToScene(pos)
        hits = [k for k, it in self.items.items() if it.rect().contains(sp)]
        return min(hits, key=lambda k: self.items[k].rect().width() * self.items[k].rect().height()) if hits else None

    def mousePressEvent(self, e):
        self._press = e.position().toPoint()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        start, end = self._press, e.position().toPoint()
        self._press = None
        if start is None:
            return super().mouseReleaseEvent(e)
        if (start - end).manhattanLength() > 6:            # a drag: every block it crosses
            r = QRectF(self.mapToScene(start), self.mapToScene(end)).normalized()
            self.pg.select([k for k, it in self.items.items() if it.rect().intersects(r)], add=bool(e.modifiers() & Qt.ShiftModifier))
            return
        k = self.block_at(end)
        if self.pg.picking:                                 # Pick another: the next click names the caption's object
            self.pg.pick_object(k)
        elif k is None:
            self.pg.select([])
        elif e.modifiers() & Qt.ShiftModifier:
            self.pg.select_run(k)
        elif e.modifiers() & Qt.ControlModifier:
            self.pg.toggle(k)
        else:
            self.pg.select([k])


class VerifyPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.doc, self.pdf, self.n, self.sel, self.picking = None, "", 1, [], False
        self.v, self.threads, self.failed, self.bad = [], [], {}, set()
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["s"])
        from .commandbar import CommandBar
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.b_doc = D.button("Document", None, None, "Every document in the effort (Ctrl+O); each opens where you left off")
        self.doc_menu = QMenu(self.b_doc); self.b_doc.setMenu(self.doc_menu)
        self.doc_menu.aboutToShow.connect(self.fill_docs)
        top.addWidget(self.b_doc)
        self.page_box = QSpinBox(); self.page_box.setMinimum(1); self.page_box.setPrefix("Page "); self.page_box.setKeyboardTracking(False)
        self.page_box.valueChanged.connect(lambda n: self.go(n) if n != self.n else None)
        self.page_box.setToolTip("Go to page (Ctrl+G)")
        top.addWidget(self.page_box)
        self.of = D.label("", "muted", wrap=False); top.addWidget(self.of)
        bar = self.bar = CommandBar(); top.addWidget(bar, 1)
        bar.add("Prev", lambda: self.go(self.n - 1), "The previous page (Page Up)")
        bar.add("Next", lambda: self.go(self.n + 1), "The next page (Page Down)")
        self.b_look = bar.add("Next to look at", lambda: self.next_look(), "The next page with something to look at (F8)")
        self.b_ok = bar.primary("Page verified, next", lambda: self.verified_next(),
                                "Marks this page verified by you and moves on (Enter). It waits on the page's flags; moving on never does.")
        bar.more("Select all text in this section", lambda: self.select_section(), "Every Text and Bullet block under the nearest heading")
        bar.more("Reopen this page...", lambda: self.reopen(), "A spot check: the page goes back to amber, with your name and why")
        bar.more_sep()
        bar.more("Menu roles...", lambda: self.edit_menu(), "Show, hide, rename, key and order the roles; add your own")
        self.strip = PageStrip(); self.strip.picked.connect(self.go); v.addWidget(self.strip)
        self.line = D.label("", "muted"); v.addWidget(self.line)
        self.line.setTextFormat(Qt.RichText); self.line.linkActivated.connect(lambda h: self.read_next() if h == "read" else self.compare_next())
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        self.view = PageView(self); split.addWidget(self.view)
        side = QWidget(); sv = QVBoxLayout(side); sv.setContentsMargins(D.SPACE["s"], 0, 0, 0); sv.setSpacing(D.SPACE["s"])
        sv.addWidget(D.label("This page, in reading order", "label"))
        self.order = QListWidget(); self.order.setWordWrap(True)
        self.order.itemClicked.connect(lambda it: self.select([it.data(Qt.UserRole)]))
        sv.addWidget(self.order, 1)
        self.scan_box = QWidget(); sb = QVBoxLayout(self.scan_box); sb.setContentsMargins(0, 0, 0, 0)
        sb.addWidget(D.label("Check the reading", "label"))
        self.scan = QListWidget(); self.scan.setMaximumHeight(160); self.scan.setWordWrap(True)
        self.scan.currentItemChanged.connect(lambda it, _o: self.fix.setText(it.data(Qt.UserRole + 1) if it else ""))
        sb.addWidget(self.scan)
        self.fix = QLineEdit(); self.fix.setPlaceholderText("Correct it here, then Enter")
        self.fix.returnPressed.connect(lambda: self.correct())
        sb.addWidget(self.fix)
        sb.addWidget(D.label("A correction also goes to the training file, so the reader learns this font.", "muted"))
        sv.addWidget(self.scan_box)
        split.addWidget(side); split.setSizes([900, 320])
        self.empty = D.EmptyState("No customer documents yet", "Add the RFP files in Library (Customer documents). Verify shows "
                                  "each page so every block gets a role before Review.", "Go to Library", lambda: self.host.go("library"))
        v.addWidget(self.empty)
        # ---- the bar beside the selection
        self.rolebar = QFrame(); self.rolebar.setObjectName("cardhead")
        self.rolebar.setAutoFillBackground(True)
        self.rolebar.setStyleSheet("QFrame#cardhead { background: %s; border: 1px solid %s; border-radius: 6px; }"
                                   % (D.tokens()["surface"], D.tokens()["border_strong"]))
        rb = QVBoxLayout(self.rolebar); rb.setContentsMargins(6, 4, 6, 4); rb.setSpacing(4)
        self.bar_msg = D.label("", "muted", wrap=False); rb.addWidget(self.bar_msg)
        self.roles_row = QWidget(); self.roles_lay = FlowLayout(self.roles_row, 4); rb.addWidget(self.roles_row)
        self.link_row = QWidget(); lr = QHBoxLayout(self.link_row); lr.setContentsMargins(0, 0, 0, 0)
        self.link_lbl = D.label("", None, wrap=False); lr.addWidget(self.link_lbl, 1)
        self.b_confirm = D.button("Confirm", "primary", lambda: self.confirm_link()); lr.addWidget(self.b_confirm)
        lr.addWidget(D.button("Pick another", None, lambda: self.start_pick()))
        rb.addWidget(self.link_row)
        from . import verifysplitbar as VSB                          # 3.92.1: a heading on the same line as its text
        self.split_row = VSB.row(self); rb.addWidget(self.split_row)
        self.barhost = BarHost(self.rolebar, self.view.viewport())
        self.role_btns = []
        # ---- keys
        for k, fn in (("PgDown", lambda: self.go(self.n + 1)), ("PgUp", lambda: self.go(self.n - 1)), ("F8", self.next_look),
                      ("Ctrl+G", lambda: (self.page_box.setFocus(), self.page_box.selectAll())),
                      ("Ctrl+O", lambda: self.b_doc.showMenu()), ("Esc", lambda: self.select([])),
                      ("J", lambda: self.step(1)), ("K", lambda: self.step(-1))):
            s = QShortcut(QKeySequence(k), self); s.setContext(Qt.WidgetWithChildrenShortcut); s.activated.connect(fn)
        self.key_shortcuts = []

    # ------------------------------------------------------------ the effort's documents
    def store(self):
        return VS.Store(self.host.ws.root) if self.host.ws is not None else VS.Store("")

    def menu_now(self):
        return self.store().menu(self.host.config_dir)

    def docs(self):
        import compliance_read as CR
        return [(os.path.basename(p), label, p) for _n, label, p in CR.effort_docs(self.host.ws)] if self.host.ws is not None else []

    def fill_docs(self):
        self.doc_menu.clear()
        st = self.store()
        for name, label, path in self.docs():
            pdf = self.pdf_of(path, make=False)
            try:
                c = VS.counts(pdf, st, name) if pdf and pdf not in self.bad else None
            except Exception:  # noqa: BLE001
                diag.swallowed()
                c = None
            txt = f"{name}  ({c['verified']} of {c['pages']} verified)" if c else f"{name}  (not ready yet)"
            a = self.doc_menu.addAction(txt); a.triggered.connect(lambda _=False, p=path: self.open_doc(p))
            a.setCheckable(True); a.setChecked(name == self.doc)
        self.doc_menu.addSeparator()
        self.doc_menu.addAction("All documents and work units", lambda: self.host.go("library"))

    def pdf_of(self, path, make=True):
        """The page form of a document: the PDF, or its page copy (made in the background when missing)."""
        import ocrpdf
        import office_pdf as OP
        folder = self.host.ws.p("page copies") if self.host.ws is not None else ""
        if ocrpdf.needs_copy(path):
            c = ocrpdf.copy_path(path, folder) if folder else ""
        elif path.lower().endswith(".pdf"):
            return path
        else:
            c = OP.copy_path(path, folder) if folder and OP.kind(path) else ""
        if c and os.path.isfile(c):
            return c
        if make and folder and path not in self.failed and not any(t.path == path for t in self.threads):
            t = CopyThread(path, folder); t.done.connect(self.copy_done); self.threads.append(t); t.start()
        return ""

    def copy_done(self, path, got):
        self.threads = [t for t in self.threads if t.path != path]
        if got.startswith("!") or not got:
            self.failed[path] = got[1:] or "no page copy could be made"
        if self.doc == os.path.basename(path):
            self.open_doc(path)

    def refresh(self):
        docs = self.docs()
        self.empty.setVisible(not docs)
        for w in (self.view, self.strip, self.order, self.bar, self.b_doc, self.page_box, self.of, self.line):
            w.setVisible(bool(docs))
        self.scan_box.setVisible(False)
        if not docs:
            return
        names = [n for n, _l, _p in docs]
        if self.doc not in names:
            self.open_doc(docs[0][2])
        else:
            self.show_page()

    def open_doc(self, path):
        self.doc, self.path = os.path.basename(path), path
        self.b_doc.setText(self.doc)
        self.pdf = self.pdf_of(path)
        self.select([], draw=False)
        if not self.pdf:
            self.view.scene().clear(); self.view.items = {}
            why = self.failed.get(path)
            self.line.setText(f"{self.doc}: {why}." if why else f"{self.doc}: making the page copy (once per file).")
            self.strip.set([], 0)
            return
        self.n = max(1, self.store().doc(self.doc)["last"])
        if not self.pages():
            self.view.scene().clear(); self.view.items = {}; self.v = []
            self.strip.set([], 0)
            return
        self.show_page()

    # ------------------------------------------------------------ one page
    def pages(self):
        import verifyblocks as VB
        if not self.pdf or self.pdf in self.bad:
            return []
        try:
            return VB.blocks(self.pdf)["pages"]
        except Exception:  # noqa: BLE001  a damaged file: say so, never stop the page
            diag.swallowed()
            self.bad.add(self.pdf)
            self.line.setText(f"{self.doc}: this file could not be read as pages. Open it in its own program to check it.")
            return []

    def go(self, n):
        ps = self.pages()
        if not ps:
            return False
        n = max(1, min(len(ps), int(n)))
        if n == self.n and self.v:
            return False
        self.n = n
        self.store().set_last(self.doc, n)
        self.show_page(first_flag=True)
        return True

    def show_page(self, first_flag=False):
        ps = self.pages()
        if not ps:
            return
        self.n = max(1, min(self.n, len(ps)))
        st, m = self.store(), self.menu_now()
        self.v = VS.view(self.pdf, st, self.doc, self.n, m)
        self.page_box.blockSignals(True); self.page_box.setMaximum(len(ps)); self.page_box.setValue(self.n); self.page_box.blockSignals(False)
        status = VS.status(self.pdf, st, self.doc, m)
        self.strip.set(status, self.n)
        c = {"verified": status.count("verified"), "pages": len(status)}
        self.of.setText(f"of {len(ps)}  ·  Pages verified {c['verified']} of {c['pages']}")
        nl = VS.next_to_look(self.pdf, st, self.doc, self.n, m)
        self.b_look.setText(f"Next to look at: p. {nl}" if nl else "Nothing to look at")
        self.b_look.setEnabled(nl is not None)
        self.draw()
        self.fill_side()
        self.say_page()
        self.build_role_buttons(m)
        if first_flag:
            fl = VS.page_flags(self.v)
            self.select([fl[0][0]] if fl else [])

    def say_page(self):
        d = self.store().doc(self.doc)
        fl = VS.page_flags(self.v)
        ver = d["verified"].get(str(self.n))
        rep = d["reopened"].get(str(self.n))
        import verifyblocks as VB
        lg = VB.ledger(self.pdf, self.n)
        words = f"Every word on the page is in a block ({lg['placed']} of {lg['total']})." if lg["placed"] == lg["total"] \
            else f"{lg['total'] - lg['placed']} of {lg['total']} words on the page are in no block: {' '.join(lg['missing'][:8])}"
        if rep:
            head = f"Reopened {rep['at'].replace('T', ' ')} by {rep['by']}" + (f": {rep['why']}" if rep.get("why") else "") + "."
        elif ver:
            head = f"Verified {ver['at'].replace('T', ' ')} by {ver['by']}. You can still change any block."
        else:
            head = f"{len(fl)} to look at on this page." if fl else "Nothing to look at on this page."
        nxt = ""
        pair = self.newer_version() if self.verified() and self.n == len(self.pages()) else None
        if pair:                                         # 3.89.0: the next step for an amendment is Compare
            nxt = f"  <a href='compare'>Next: compare {pair[2]['label']} with {pair[1]['label']}</a>"
        elif self.verified() and self.n == len(self.pages()) and self.needs_read():
            nxt = "  <a href='read'>Next: extract it for the shred</a>"     # 3.90.0; 4.0.0: Extract, in Shred
        import html
        self.line.setText(html.escape(f"{head}  {words}  A verified page is a record that a person checked it, not a guarantee.") + nxt)
        self.b_ok.setEnabled(not fl)
        self.b_ok.setText("Page verified, next" if not fl else f"{len(fl)} to look at")

    def draw(self):
        sc = self.view.scene(); sc.clear(); self.view.items = {}
        p = self.pages()[self.n - 1]
        t = D.tokens(); m = VR.by_id(self.menu_now())
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(self.pdf)
            img = doc[self.n - 1].render(scale=SCALE).to_pil().convert("RGB")
            doc.close()
            q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
            pix = QGraphicsPixmapItem(QPixmap.fromImage(q)); pix.setScale(1 / SCALE); pix.setPos(MARGIN, 0); pix.setZValue(-1)
            pix.setTransformationMode(Qt.SmoothTransformation); sc.addItem(pix)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            sc.addRect(QRectF(MARGIN, 0, p["w"], p["h"]), QPen(QColor(t["border"])), QBrush(QColor(t["surface"])))
        by = {b["key"]: b for b in self.v}
        for b in self.v:
            l, tp, r, bt = b["box"]
            rect = QRectF(MARGIN + l - 2, tp - 2, r - l + 4, bt - tp + 4)
            acts = m.get(b["role"], {}).get("acts", "text")
            col = QColor(t.get(ACT_TONE.get(acts, "head"), "#334155"))
            sel = b["key"] in self.sel
            pen = QPen(QColor(t["focus"]) if sel else col, 2.2 if sel else 0.8)
            if acts in ("running", "skip"):
                pen.setStyle(Qt.DotLine)
            fill = QColor(t["focus"] if sel else col); fill.setAlpha(46 if sel else (10 if acts != "skip" else 26))
            it = sc.addRect(rect, pen, QBrush(fill)); it.setData(0, b["key"])
            self.view.items[b["key"]] = it
            mark = "!" if b["flags"] else ("✓" if b["decided"] or self.verified() else "")
            tag = sc.addSimpleText(f"{m.get(b['role'], {}).get('name', b['role'])} {mark}".strip())
            tag.setBrush(QColor(t["warn"] if b["flags"] else col)); tag.setPos(2, tp - 1)
            f = tag.font(); f.setPointSizeF(6.5); tag.setFont(f)
            if b.get("link") and b["link"].get("to") in by:            # the bracket: dashed while suggested, solid confirmed
                o = by[b["link"]["to"]]
                ya, yb = (tp + bt) / 2, (o["box"][1] + o["box"][3]) / 2
                path = QPainterPath(QPointF(MARGIN - 6, ya)); path.lineTo(MARGIN - 14, ya); path.lineTo(MARGIN - 14, yb)
                path.lineTo(MARGIN - 6, yb)
                bp = QPen(QColor(t["cust"]), 1.4); bp.setStyle(Qt.SolidLine if b["link"]["ok"] else Qt.DashLine)
                sc.addPath(path, bp)
        sc.setSceneRect(QRectF(0, -10, MARGIN + p["w"] + 20, p["h"] + 20))
        self.fit()

    def fit(self):
        """The page fills the view's width."""
        r = self.view.scene().sceneRect()
        if r.width() <= 0:
            return
        k = max(0.5, min(3.0, (self.view.viewport().width() - 8) / r.width()))
        self.view.resetTransform(); self.view.scale(k, k)

    def verified(self):
        d = self.store().doc(self.doc)
        return str(self.n) in d["verified"] and str(self.n) not in d["reopened"]

    def fill_side(self):
        m = VR.by_id(self.menu_now())
        self.order.clear()
        by = {b["key"]: b for b in self.v}
        for i, b in enumerate(self.v, 1):
            link = ""
            if b.get("link") and b["link"].get("to") in by:
                link = "  → " + (by[b["link"]["to"]]["text"][:24] or m.get(by[b["link"]["to"]]["role"], {}).get("name", "object"))
            mark = "  !" if b["flags"] else ("  ✓" if b["decided"] else "")
            it = QListWidgetItem(f"{i}. {m.get(b['role'], {}).get('name', b['role'])}{mark}{link}\n{(b['text'] or '(picture)')[:140]}")
            it.setData(Qt.UserRole, b["key"])
            if b["flags"]:
                it.setToolTip("\n".join(b["flags"]))
            self.order.addItem(it)
        lines = VS.scan_lines(self.pdf, self.n)
        d = self.store().doc(self.doc)
        self.scan.clear()
        for r in lines:
            fixed = d["readings"].get(f"{self.n}:{r['line']}")
            unsure = float(r.get("conf", 1)) < self.store().unsure() and fixed is None
            it = QListWidgetItem(("Unsure  " if unsure else ("Checked  " if fixed is not None else "")) + (fixed or r["text"]))
            it.setData(Qt.UserRole, r["line"]); it.setData(Qt.UserRole + 1, fixed or r["text"])
            if unsure:
                it.setForeground(QColor(D.tokens()["warn"]))
            self.scan.addItem(it)
        self.scan_box.setVisible(bool(lines))

    # ------------------------------------------------------------ the selection and the bar
    def keys(self):
        return [b["key"] for b in self.v]

    def select(self, keys, add=False, draw=True):
        keys = [k for k in keys if k in self.keys()] if self.v else []
        self.sel = list(dict.fromkeys((self.sel if add else []) + keys))
        self.picking = False
        if draw and self.v:
            self.draw()
        self.place_bar()

    def toggle(self, k):
        self.select([x for x in self.sel if x != k] if k in self.sel else self.sel + [k])

    def select_run(self, k):
        ks = self.keys()
        if not self.sel or k not in ks:
            return self.select([k])
        a, b = sorted((ks.index(self.sel[0]), ks.index(k)))
        self.select(ks[a:b + 1])

    def step(self, d):
        ks = self.keys()
        if not ks:
            return
        i = ks.index(self.sel[-1]) + d if self.sel and self.sel[-1] in ks else 0
        self.select([ks[max(0, min(len(ks) - 1, i))]])

    def select_section(self):
        if self.sel:
            self.select(VS.section_of(self.v, self.sel[0], self.menu_now()))

    def sel_rect(self):
        rs = [self.view.items[k].rect() for k in self.sel if k in self.view.items]
        by = {b["key"]: b for b in self.v}
        for k in list(self.sel):                                 # the linked figure or table is part of what is selected
            to = (by.get(k) or {}).get("link") or {}
            if to.get("to") in self.view.items:
                rs.append(self.view.items[to["to"]].rect())
        if not rs:
            return None
        u = rs[0]
        for r in rs[1:]:
            u = u.united(r)
        return self.view.mapFromScene(u).boundingRect()

    def place_bar(self):
        r = self.sel_rect() if self.sel else None
        if r is None:
            self.barhost.close()
            return
        b = next((x for x in self.v if x["key"] == self.sel[0]), None)
        m = VR.by_id(self.menu_now())
        one_cap = len(self.sel) == 1 and b is not None and m.get(b["role"], {}).get("acts") == "caption"
        self.link_row.setVisible(one_cap)
        if one_cap:
            by = {x["key"]: x for x in self.v}
            to = (b.get("link") or {}).get("to")
            self.link_lbl.setText(("Names: " + ((by.get(to) or {}).get("text") or "the figure")[:40] +
                                   ("  (confirmed)" if b["link"]["ok"] else "  (suggested)")) if to else "Names nothing yet: Pick another")
            self.b_confirm.setVisible(bool(to) and not b["link"]["ok"])
        from . import verifysplitbar as VSB
        VSB.show(self, b if len(self.sel) == 1 else None)
        flags = [f for x in self.v if x["key"] in self.sel for f in x["flags"]]
        self.bar_msg.setText(flags[0] if flags else (f"{len(self.sel)} blocks: this is a" if len(self.sel) > 1 else "This is a"))
        self.barhost.show_for(r, width=min(640, self.view.viewport().width() - 16))

    def build_role_buttons(self, m):
        for b in self.role_btns:
            b.setParent(None)
        for s in self.key_shortcuts:
            s.setParent(None)
        self.role_btns, self.key_shortcuts = [], []
        for r in m:
            if not r["on"]:
                continue
            b = D.button(r["name"] + (f"  {r['key']}" if r["key"] else ""), None, lambda _=False, rid=r["id"]: self.set_role(rid),
                         VR.ACTS_NAME.get(r["acts"], ""))
            self.roles_lay.addWidget(b); self.role_btns.append(b)
            if r["key"]:
                s = QShortcut(QKeySequence(r["key"]), self); s.setContext(Qt.WidgetWithChildrenShortcut)
                s.activated.connect(lambda rid=r["id"]: self.set_role(rid)); self.key_shortcuts.append(s)
        enter = QShortcut(QKeySequence(Qt.Key_Return), self); enter.setContext(Qt.WidgetWithChildrenShortcut)
        enter.activated.connect(lambda: self.verified_next() if not self.fix.hasFocus() else None)
        self.key_shortcuts.append(enter)

    def set_role(self, rid):
        if not self.sel:
            return 0
        n = self.store().set_role(self.doc, list(self.sel), rid)
        diag.activity("verify_role_set", n=n)
        keep = list(self.sel)
        self.show_page()
        self.select(keep)
        return n

    def confirm_link(self):
        b = next((x for x in self.v if x["key"] in self.sel), None)
        if b and b.get("link") and b["link"].get("to"):
            self.store().set_link(self.doc, b["key"], b["link"]["to"], True)
            keep = list(self.sel); self.show_page(); self.select(keep)
            return True
        return False

    def start_pick(self):
        self.picking = True
        self.bar_msg.setText("Click the figure or table this caption names")

    def pick_object(self, k):
        cap = self.sel[0] if self.sel else None
        self.picking = False
        if cap and k and k != cap:
            self.store().set_link(self.doc, cap, k, True)
            self.show_page(); self.select([cap])
            return True
        return False

    # ------------------------------------------------------------ the page's decisions
    def verified_next(self):
        if not self.v:
            return False
        if not VS.can_verify(self.v):
            fl = VS.page_flags(self.v)
            self.host.status(f"{len(fl)} to look at on this page first. Next moves on without verifying it.")
            self.select([fl[0][0]])
            return False
        self.store().verify(self.doc, self.n)
        diag.activity("verify_page", n=1)
        if self.n < len(self.pages()):
            self.go(self.n + 1)
        else:
            self.show_page()
        return True

    def newer_version(self):
        """(doc, the version before, this version) when the open file is a later version of a Library document."""
        try:
            import docversions as DV
            lib = DV.Library(self.host.ws.p("documents")).load()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return None
        for d in lib.docs:
            for k, v in enumerate(d["versions"]):
                if k and v.get("file") == self.doc:
                    return d, d["versions"][k - 1], v
        return None

    def needs_read(self):
        """3.90.0: this file was never read into Review, or Verify changed it after it was read."""
        R = self.host.review
        if R is None:
            return True
        rows = [r for r in R.M.sources if r and r[0] == self.doc]
        if not rows:
            return True
        return bool(VS.changed_after(self.store(), self.doc, rows[-1][2] if len(rows[-1]) > 2 else ""))

    def read_next(self):
        from . import shredpick as SP                    # 4.1.0: extracted at once and opened in Shred
        return 1 if SP.extract_file(self.host, self.doc) is not None else 0

    def compare_next(self):
        pair = self.newer_version()
        if not pair:
            return False
        self.host.go("compare")
        self.host.compare_page.show(pair[0]["id"], pair[1]["id"], pair[2]["id"])
        return True

    def next_look(self):
        nl = VS.next_to_look(self.pdf, self.store(), self.doc, self.n, self.menu_now()) if self.pdf else None
        if nl:
            if nl == self.n:
                self.show_page(first_flag=True)
            else:
                self.go(nl)
        return nl

    def reopen(self, why=None):
        if not self.v:
            return False
        if why is None:
            from .symbols import ask_text
            why, ok = ask_text(self, "Reopen this page", "What needs another look (it shows on the page):")
            if not ok:
                return False
        self.store().reopen(self.doc, self.n, why=why)
        self.show_page()
        return True

    def correct(self, text=None):
        it = self.scan.currentItem()
        if it is None:
            return False
        line = it.data(Qt.UserRole)
        text = self.fix.text() if text is None else text
        read = next((r for r in VS.scan_lines(self.pdf, self.n) if r["line"] == line), None)
        self.store().set_reading(self.doc, self.n, line, text)
        if read and " ".join(text.split()) != read["text"]:
            self.train(read, text)
        self.show_page()
        return True

    def train(self, read, text):
        """The page's crop of the line, with the reading and the correction, goes to the training file."""
        try:
            import corrections as CO
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(self.pdf)
            img = doc[self.n - 1].render(scale=200 / 72).to_pil().convert("RGB")
            doc.close()
            k = 200 / 72
            box = tuple(int(v * k) for v in read["box"])
            CO.save_sample(img.crop(box), text, read["text"], read.get("conf", 0), f"verify:{self.doc}:p{self.n}", box)
        except Exception:  # noqa: BLE001
            diag.swallowed()

    def edit_menu(self, run=True):
        from .verifymenu import MenuDialog
        d = MenuDialog(self, self.menu_now(), self.host.config_dir)
        if not run:
            return d
        if d.exec():
            self.store().set_menu(d.result_menu())
            self.show_page()
        return d

    def showEvent(self, e):
        super().showEvent(e)
        self.setFocus()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.v:
            self.fit(); self.place_bar()

    def sel_text(self):
        return [b["text"] for b in self.v if b["key"] in self.sel]

    def bar_rect(self):
        return self.rolebar.geometry() if self.rolebar.isVisible() else QRect()
