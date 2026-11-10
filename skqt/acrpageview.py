"""Acronyms, On the page (3.93.0; claude/stationkeeper-acronyms-two-tabs-3.93.md). The customer's pages one at a time,
like Verify: the pages with finds to decide on the left, the page in the middle with every find boxed (yellow to
decide, green in the list, orange read with doubt, blue selected). Click a box to select it, Ctrl or Shift adds; drag on
the page to select every find inside (the drag box is gone when you let go; words the scan never found are selected as
the reader sees them). The bar beside the selection decides (acrselbar). Page done marks the page and goes on.
acrpages holds the rules. Files are only read. Rules and the trained readers only (No AI); nothing leaves the PC."""
import html
import os

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPen, QTextCursor
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsRectItem, QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget,
                               QTextBrowser, QVBoxLayout, QWidget)

import acrpages as AG
import app_gui as A
import diag
from . import design as D
from . import foundview as FV
from .whereview import parse_loc

_PICS = {}                                   # page key -> (QImage, lines, typed finds, note); the session's pages
FILL = {"decide": (252, 231, 161), "list": None, "doubt": None, "sel": (46, 123, 224), "not": None}
TEXT_BG = {"decide": "#FCE7A1", "list": "#D9F2E1", "doubt": "#F9D3BF", "sel": "#BFD7F7", "not": "#E5E7EB"}


def _mods():
    return bool(QApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier))


class PageText(QTextBrowser):
    """Typed text with every find as a link (a passage of a Word, PowerPoint or Excel file)."""
    def wheelEvent(self, e):
        super().wheelEvent(e)
        e.accept()


class OnPage(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page = page                       # the AcronymPage: its session, host and files
        self.key = None
        self.items, self.sel = [], []           # the finds on the page shown; the ones selected (their indexes)
        self.new_text, self.new_area = "", None  # words in a dragged box the scan never found
        self.new_boxes = []
        self.lines = []
        self.show_not = False
        self.undo = None                         # (words, what each term was) after Not a term
        self.state = "none"
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["m"])
        left = QVBoxLayout(); left.setSpacing(D.SPACE["s"])
        left.addWidget(D.label("PAGES WITH FINDS TO DECIDE", "faint", wrap=False))
        self.list = QListWidget(); self.list.setMinimumWidth(240); self.list.setMaximumWidth(320)
        self.list.setTextElideMode(Qt.ElideMiddle); self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(lambda cur, _prev: self._picked(cur))
        left.addWidget(self.list, 1)
        self.foot = D.label("", "muted"); left.addWidget(self.foot)
        h.addLayout(left)
        mid = QVBoxLayout(); mid.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"])
        for name, col, fill in (("to decide", AG.COLORS["decide"], "rgba(252,231,161,160)"), ("in the list", AG.COLORS["list"], "transparent"),
                                ("read with doubt", AG.COLORS["doubt"], "transparent"), ("selected", AG.COLORS["sel"], "rgba(46,123,224,60)")):
            sw = QFrame(); sw.setFixedSize(12, 12); sw.setStyleSheet(f"QFrame{{border:2px solid {col};background:{fill}}}")
            top.addWidget(sw); top.addWidget(D.label(name, "muted", wrap=False))
            top.addSpacing(6)
        top.addStretch(1)
        self.where = D.label("", "muted", wrap=False); top.addWidget(self.where)
        mid.addLayout(top)
        self.stack = QStackedWidget()
        self.view = FV.PicView(); self.view.on_click = self.clicked; self.view.on_area = self.dragged
        self.text = PageText(); self.text.setOpenLinks(False); self.text.anchorClicked.connect(lambda u: self.link(u.toString()))
        self.text.setStyleSheet("QTextBrowser{background:#FFFFFF;color:#111111}")
        self.text.selectionChanged.connect(lambda: self._sel_timer.start())
        self._sel_timer = QTimer(self, singleShot=True, interval=300, timeout=self.text_selected)
        self.empty = D.label("", "muted"); self.empty.setAlignment(Qt.AlignCenter)
        for w in (self.view, self.text, self.empty):
            self.stack.addWidget(w)
        mid.addWidget(self.stack, 1)
        hint = QHBoxLayout()
        self.hint = D.label("Click a box to select it; Ctrl or Shift adds; drag on the page to select every find inside. Drag "
                            "around words that were not found to add them.", "muted")
        self.undo_lab = D.label("", None, wrap=False); self.undo_lab.setTextFormat(Qt.RichText)
        self.undo_lab.linkActivated.connect(lambda _h: self.undo_last())
        self.left_lab = D.label("", "muted", wrap=False)
        hint.addWidget(self.hint, 1); hint.addWidget(self.undo_lab); hint.addWidget(self.left_lab)
        mid.addLayout(hint)
        h.addLayout(mid, 1)
        self.bar = None
        self.install_keys()
        for sb in (self.view.horizontalScrollBar(), self.view.verticalScrollBar(), self.text.verticalScrollBar()):
            sb.valueChanged.connect(lambda _v: self.place_bar())

    # ------------------------------------------------------------ the pages
    @property
    def session(self):
        return self.page.session

    def pages(self):
        s = self.session
        if s is None:
            return []
        return AG.pages(s.results, AG.done_set(s.ws))

    def fill(self, keep=True):
        """The page list again (after any decision); the page shown stays."""
        pgs = self.pages()
        cur = self.key if keep else None
        self.list.blockSignals(True)
        self.list.clear()
        last = None
        t = D.tokens()
        for p in pgs:
            if p["name"] != last:
                hd = QListWidgetItem(p["name"]); hd.setFlags(Qt.NoItemFlags)
                f = hd.font(); f.setBold(True); hd.setFont(f); hd.setForeground(QColor(t["text"]))
                self.list.addItem(hd); last = p["name"]
            n = p["to_decide"]
            it = QListWidgetItem(f"    {p['label']}    " + ("done" if p["done"] else f"{n} to decide" if n else "decided"))
            it.setData(Qt.UserRole, p["key"])
            it.setForeground(QColor(t["faint"] if (p["done"] or not n) else t["warn"]))
            self.list.addItem(it)
            if p["key"] == cur:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        tot = AG.totals(pgs)
        self.foot.setText(f"{tot['to_decide']} to decide in {tot['pages_left']} page(s). {tot['pages_done']} page(s) done."
                          if pgs else "")
        if not pgs:
            self.key = None
            self.show_empty("Scan the customer documents (in The list, More): every page with a find shows here.")
        elif cur is None or cur not in [p["key"] for p in pgs]:
            self.go(AG.next_page(pgs) or pgs[0]["key"])
        else:
            self.redraw()
        self.left_lab.setText(f"{self.left_here()} to decide on this page" if self.key else "")
        return pgs

    def left_here(self):
        s = self.session
        if s is None or not self.key:
            return 0
        return sum(1 for t in {x["term"] for x in self.items if x.get("term")}
                   if AG.state_of(s.results.get(t) or {}) == "decide")

    def _picked(self, item):
        key = item.data(Qt.UserRole) if item is not None else None
        if key and key != self.key:
            self.go(key)

    def go(self, key):
        """Show a page: its picture (read off the window's thread) or its typed text."""
        self.key, self.items, self.sel, self.lines = key, [], [], []
        self.new_text, self.new_area = "", None
        self.close_bar()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == key:
                self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False)
        name = parse_loc(key)[0]
        self.where.setText(key)
        path = self.page.path_of(name)
        if not path or not os.path.isfile(path):
            self.state = "missing"
            return self.show_empty(f"{name} is not on this PC where it was scanned, so its page cannot be shown.")
        try:
            import pictures as PIC
            srcs = FV.sources(path)
            idx = PIC.match_source([lbl for lbl, _ld in srcs], key)
        except Exception:  # noqa: BLE001  the typed text can still show
            diag.swallowed()
            srcs, idx = [], None
        if idx is None:
            return self.show_text(path)
        if key in _PICS:
            return self.paint(*_PICS[key])
        self.state = "reading"
        self.show_empty("Reading the page...")
        label, loader = srcs[idx]
        terms = self.terms_here()
        from .progress import JobWorker
        w = JobWorker(lambda _p, _s: read_page(path, loader, key, terms))

        def done(res, want=key):
            if isinstance(res, tuple):
                _PICS[want] = res
                if len(_PICS) > 30:
                    _PICS.pop(next(iter(_PICS)))
            try:
                if self.key == want:
                    self.paint(*res) if isinstance(res, tuple) else self.show_empty(f"The page could not be read ({type(res).__name__}).")
            except RuntimeError:                 # closed meanwhile
                pass
        w.done.connect(done)
        FV._ALIVE.append(w); w.finished.connect(lambda w=w: FV._ALIVE.remove(w) if w in FV._ALIVE else None)
        diag.activity("acronym_page_read")
        w.start()
        return w

    def terms_here(self):
        s = self.session
        return sorted(t for t, d in s.results.items() if AG._real(t, d)
                      and any(AG.place_of(x) == self.key for x in d.get("locations") or []))

    def wait(self, seconds=60):
        """Tests: until the page being read is shown."""
        import time
        t0 = time.time()
        while self.state == "reading" and time.time() - t0 < seconds:
            QApplication.processEvents(); time.sleep(0.02)
        return self.state

    def show_empty(self, text):
        self.empty.setText(text)
        self.stack.setCurrentWidget(self.empty)
        return None

    # ------------------------------------------------------------ a picture
    def paint(self, qimg, lines, typed, note=""):
        self.lines = list(lines)
        finds = list(typed) + AG.line_finds(lines, self.terms_here())
        self.items = AG.resolve(finds, self.session.results)
        self.items.sort(key=lambda x: (round(x["box"][1] / 12), x["box"][0]))
        self.view.set_picture(qimg, [])          # a new scene: the boxes drawn before are gone with it
        self._drawn = []
        self.stack.setCurrentWidget(self.view)
        self.state = "picture"
        self.frame()
        QTimer.singleShot(0, self._reframe)                # again once the view has its size
        self.draw_boxes()
        self.where.setText(self.key + (f"   {note}" if note else ""))
        self.left_lab.setText(f"{self.left_here()} to decide on this page")
        return self.items

    def frame(self):
        """A page fills the width (its text readable), at the first find left to decide; a picture is shown whole."""
        v = self.view
        if v.pix is None:
            return None
        iw, ih = v.pix.pixmap().width(), v.pix.pixmap().height()
        if ih > iw * 1.1:
            sc = min(v.viewport().width() * 0.98 / max(1, iw), 1.5)
            v.resetTransform(); v.scale(sc, sc); v._room()
            first = next((x for x in self.items if not x.get("behind") and self.kind(x) in ("decide", "doubt")), None)
            cy = (first["box"][1] + first["box"][3]) / 2 if first is not None else 0
            v.centerOn(iw / 2, cy)
        else:
            v.fit()
        return v.transform().m11()

    def _reframe(self):
        try:
            if self.state == "picture":
                self.frame(); self.place_bar()
        except RuntimeError:                     # closed meanwhile
            pass

    def kind(self, x):
        d = self.session.results.get(x["term"]) or {}
        st = AG.state_of(d)
        if st == "tied":
            st = "list"
        if st == "decide" and x.get("conf") is not None and x["conf"] < A.ocr_cutoff():
            st = "doubt"
        return st

    def draw_boxes(self):
        sc = self.view.scene_
        for it in getattr(self, "_drawn", []):
            if it.scene() is sc:
                sc.removeItem(it)
        self._drawn = []
        for i, x in enumerate(self.items):
            st = self.kind(x)
            if st == "not" and not self.show_not:
                continue
            col = AG.COLORS["sel"] if i in self.sel else AG.COLORS.get(st, "#9CA3AF")
            x0, y0, x1, y1 = x["box"]
            it = QGraphicsRectItem(QRectF(x0 - 3, y0 - 3, (x1 - x0) + 6, (y1 - y0) + 6))
            pen = QPen(QColor(col)); pen.setWidthF(3 if i in self.sel else 2); pen.setCosmetic(True)
            if x.get("behind"):                  # the whole term behind a part still to decide: dashed
                pen = QPen(QColor(AG.COLORS["sel"] if any(self.items[j].get("whole") is not None and AG._within(self.items[j], x)
                                                          for j in self.sel) else AG.COLORS["decide"]))
                pen.setWidthF(2); pen.setCosmetic(True); pen.setStyle(Qt.DashLine)
                it.setPen(pen); it.setZValue(3); sc.addItem(it); self._drawn.append(it)
                continue
            if st == "not":
                pen.setStyle(Qt.DashLine)
            it.setPen(pen)
            fill = FILL["sel"] if i in self.sel else FILL.get(st)
            if fill:
                it.setBrush(QBrush(QColor(*fill, 50 if i in self.sel else 110)))
            it.setZValue(4)
            sc.addItem(it); self._drawn.append(it)
        for b in (self.new_boxes if self.new_area is not None else []):     # the words never found, selected
            it = QGraphicsRectItem(QRectF(b[0] - 3, b[1] - 3, b[2] - b[0] + 6, b[3] - b[1] + 6))
            pen = QPen(QColor(AG.COLORS["new"])); pen.setWidthF(2); pen.setCosmetic(True); it.setPen(pen)
            it.setBrush(QBrush(QColor(46, 123, 224, 40))); it.setZValue(4)
            sc.addItem(it); self._drawn.append(it)

    def visible(self, i):
        x = self.items[i]
        return not x.get("behind") and (self.kind(x) != "not" or self.show_not)

    def clicked(self, pt):
        hit = [i for i, x in enumerate(self.items) if self.visible(i)
               and x["box"][0] - 3 <= pt.x() <= x["box"][2] + 3 and x["box"][1] - 3 <= pt.y() <= x["box"][3] + 3]
        if not hit:
            return self.select([])
        i = min(hit, key=lambda k: (self.items[k]["box"][2] - self.items[k]["box"][0]))
        return self.select(sorted(set(self.sel) ^ {i}) if _mods() else [i])

    def dragged(self, box):
        """A box dragged on the picture: it is gone at once; what it held is selected."""
        got, rest = AG.area_pick([x for i, x in enumerate(self.items) if self.visible(i)], self.lines, box)
        idx = [self.items.index(g) for g in got]
        if idx:
            return self.select(sorted(set(self.sel) | set(idx)) if _mods() else idx)
        self.sel = []
        self.new_text, self.new_area = rest, box
        seen = {g["line"] for g in got}
        self.new_boxes = [b for b, t, _c in self.lines if AG.inside(b, box) and t not in seen]
        diag.activity("acronym_page_new_area")
        return self.show_bar()

    # ------------------------------------------------------------ typed text
    def show_text(self, path):
        chunks = dict(A.typed_chunks(path))
        text = chunks.get(self.key)
        if text is None:
            self.state = "none"
            return self.show_empty("This place cannot be shown here; the term is listed in The list.")
        self.src_text = text
        self.items = AG.resolve(AG.all_spans(text, self.terms_here()), self.session.results)
        self.state = "text"
        self.stack.setCurrentWidget(self.text)
        self.draw_text()
        self.left_lab.setText(f"{self.left_here()} to decide on this page")
        return self.items

    def draw_text(self):
        text, k, out = self.src_text, 0, []
        for i, x in enumerate(self.items):
            if x.get("behind"):
                continue
            a, b = x["span"]
            if a < k:
                continue
            out.append(html.escape(text[k:a]))
            st = "sel" if i in self.sel else self.kind(x)
            word = html.escape(text[a:b])
            if st == "not" and not self.show_not:
                out.append(word)
            else:
                out.append(f"<a href='f:{i}' style='color:#111111;text-decoration:none;background-color:{TEXT_BG[st]};"
                           f"font-weight:600'>{word}</a>")
            if x.get("whole") is not None and st != "not":    # the rest of the longer term, dashed
                end = x["whole"]["span"][1]
                out.append(f"<span style='text-decoration:underline;color:#1F5FAD'>{html.escape(text[b:end])}</span>")
                b = end
            k = b
        out.append(html.escape(text[k:]))
        body = "".join(out).replace("\n", "<br>")
        y = self.text.verticalScrollBar().value()
        self.text.setHtml(f"<div style='font-family:Calibri,Carlito,Arial;font-size:14px;line-height:150%'>{body}</div>")
        self.text.verticalScrollBar().setValue(y)

    def link(self, href):
        if not href.startswith("f:"):
            return None
        i = int(href[2:])
        return self.select(sorted(set(self.sel) ^ {i}) if _mods() else [i])

    def text_selected(self):
        """Words selected in typed text: the finds inside are selected; words with no find can be added."""
        cur = self.text.textCursor()
        if self.state != "text" or not cur.hasSelection():
            return None
        a, b = cur.selectionStart(), cur.selectionEnd()
        plain = self.text.toPlainText()
        idx = [i for i, x in enumerate(self.items) if self.visible(i) and self._pos(i) is not None and a <= self._pos(i) < b]
        if idx:
            return self.select(idx)
        self.sel = []
        self.new_text, self.new_area = " ".join(plain[a:b].split()), None
        return self.show_bar()

    def _pos(self, i):
        """Where find i starts in the text as shown (the passage is shown character for character)."""
        x = self.items[i]
        return x["span"][0] if "span" in x else None

    # ------------------------------------------------------------ the selection and its bar
    def select(self, idx):
        self.sel = [i for i in idx if 0 <= i < len(self.items)]
        self.new_text, self.new_area = "", None
        if self.state == "picture":
            self.draw_boxes()
        elif self.state == "text":
            self.draw_text()
        return self.show_bar() if self.sel else self.close_bar()

    def selected(self):
        return [self.items[i] for i in self.sel]

    def show_bar(self):
        from . import acrselbar as SB
        self.close_bar()
        if self.state == "picture" and self.new_area is not None:
            self.draw_boxes()
        if not self.sel and not self.new_text and self.new_area is None:
            return None
        host = self.view.viewport() if self.state == "picture" else self.text.viewport()
        self.bar = SB.build(self, host)
        self.bar.show()
        self.place_bar()
        return self.bar

    def close_bar(self):
        if self.bar is not None:
            self.bar.hide(); self.bar.setParent(None); self.bar.deleteLater()
        self.bar = None
        return None

    def sel_rect(self):
        """The selection's rectangle in the view's viewport."""
        from PySide6.QtCore import QRect
        if self.state == "picture":
            boxes = [self.items[i]["box"] for i in self.sel] or ([self.new_area] if self.new_area else [])
            if not boxes:
                return None
            r = QRectF(min(b[0] for b in boxes), min(b[1] for b in boxes), 0, 0)
            r.setRight(max(b[2] for b in boxes)); r.setBottom(max(b[3] for b in boxes))
            return self.view.mapFromScene(r).boundingRect()
        rects = []
        for i in self.sel:
            p = self._pos(i)
            if p is not None:
                c = QTextCursor(self.text.document()); c.setPosition(p)
                rects.append(self.text.cursorRect(c))
        if not rects:
            c = self.text.textCursor()
            rects = [self.text.cursorRect(c)]
        out = QRect(rects[0])
        for r in rects[1:]:
            out = out.united(r)
        return out.adjusted(-2, -2, 60, 2)

    def place_bar(self):
        """Beside the selection, never over it: under its line (the words before and after it stay in view), else above,
        else to its right, else to its left."""
        b, r = self.bar, self.sel_rect()
        if b is None or r is None:
            return None
        host = b.parentWidget()
        b.adjustSize()
        W, H, w, h, gap = host.width(), host.height(), b.width(), b.height(), 12
        x = max(0, min(W - w, r.left()))
        if r.bottom() + gap + h <= H:
            pos = (x, r.bottom() + gap)
        elif r.top() - gap - h >= 0:
            pos = (x, r.top() - gap - h)
        elif r.right() + gap + w <= W:
            pos = (r.right() + gap, max(0, min(H - h, r.top())))
        else:
            pos = (max(0, r.left() - gap - w), max(0, min(H - h, r.top())))
        b.move(int(pos[0]), int(pos[1]))
        return b.geometry()

    # ------------------------------------------------------------ after a decision
    def decided(self, msg="", undo=None):
        """Every decision ends here: the page and the list are drawn again; the page shown stays."""
        if undo is not None:
            self.undo = undo
            self.undo_lab.setText(f"{html.escape(undo[0])}: Not a term. <a href='u'>Undo</a>")
        if msg:
            self.page.host.toast(msg)
        self.sel, self.new_text, self.new_area = [], "", None
        self.close_bar()
        self.page.fill()                         # the list, its counts and this page (acrtabs.after_fill)
        return msg

    def undo_last(self):
        if self.undo is None:
            return 0
        words, was = self.undo
        n = AG.undo_not_term(self.session, was)
        self.undo = None
        self.undo_lab.setText("")
        self.decided(f"{words}: back as before")
        return n

    def redraw(self):
        if self.state == "picture":
            self.items = AG.resolve(list(_PICS.get(self.key, (None, [], []))[2]) + AG.line_finds(self.lines, self.terms_here()),
                                    self.session.results)
            self.items.sort(key=lambda x: (round(x["box"][1] / 12), x["box"][0]))
            self.draw_boxes()
        elif self.state == "text":
            self.items = AG.resolve(AG.all_spans(self.src_text, self.terms_here()), self.session.results)
            self.draw_text()

    def page_done(self):
        """The page is done: marked with the effort; the next page with finds to decide shows."""
        s = self.session
        if s is None or not self.key:
            return None
        AG.set_done(s.ws, self.key, True)
        diag.activity("acronym_page_done")
        nxt = AG.next_page(self.pages(), self.key)
        self.fill()
        if nxt:
            self.go(nxt)
        else:
            self.page.host.toast("Every page with finds is done.")
        return nxt

    def next_page(self):
        nxt = AG.next_page(self.pages(), self.key)
        if nxt:
            self.go(nxt)
        else:
            self.page.host.toast("No other page has finds to decide.")
        return nxt

    def show_term(self, term):
        """From The list: the first page the term is on, with its finds selected."""
        s = self.session
        locs = [AG.place_of(x) for x in (s.results.get(term) or {}).get("locations") or []]
        if not locs:
            return None
        self.go(locs[0])
        if self.state == "reading":
            self.wait()
        idx = [i for i, x in enumerate(self.items) if x.get("term") == term]
        if idx:
            self.select(idx)
        return locs[0]

    def set_show_not(self, on):
        self.show_not = bool(on)
        self.redraw()
        return self.show_not

    def install_keys(self):
        """Keys while a bar is open: Enter its main step (typing too), X Not a term, 1 and 2 a definition, A B U S the type."""
        from PySide6.QtGui import QKeySequence, QShortcut
        from . import acrselbar as SB
        from .acrlayout import _typing
        self.keys = []
        for seq in (Qt.Key_Return, Qt.Key_Enter, "X", "1", "2", "A", "B", "U", "S"):
            sc = QShortcut(QKeySequence(seq), self); sc.setContext(Qt.WidgetWithChildrenShortcut)
            name = "enter" if seq in (Qt.Key_Return, Qt.Key_Enter) else seq
            sc.activated.connect(lambda n=name: None if (self.bar is None or (n != "enter" and _typing())) else SB.key(self, n))
            self.keys.append(sc)


def read_page(path, loader, key, terms):
    """(QImage, readings, typed finds, note) for one page: a PDF page's typed text is found where it is written; a picture
    or a scanned page is read (the scan's readings, kept with the effort, are drawn without reading again)."""
    img = loader()
    typed, lines, note = [], [], ""
    if path.lower().endswith(".pdf"):
        for t in terms:
            for b in FV.pdf_hits(path, key, img.height, t):
                typed.append({"term": t, "box": b, "conf": None, "line": t})
    if not typed:
        try:
            import picreadings as PR
            k = PR.key_of(img)
            kept = PR.get(k)
            if kept is None:
                kept = A.scan_readings(A._pil_png(img))
                PR.put(k, kept); PR.flush()
            lines = [(b, t, c) for b, t, c, _how in kept]
        except Exception as e:  # noqa: BLE001  the page is still worth seeing
            diag.swallowed()
            note = f"The reader could not run here ({type(e).__name__}), so nothing is boxed."
    return FV._qimage(img), lines, typed, note
