"""Compare on the page (3.89.0, claude/stationkeeper-compare-on-the-page-plan-3.89.md; was the 2.85.0 Changes table).

    Left, their page: the new version's page as Verify draws it, each change marked on it (new and changed words green,
    a changed sentence outlined amber, a removed sentence as a red mark where it stood; a decided change pale with a
    tick in the margin). Without a page copy yet, the new version's text in reading order stands in, marked the same way.
    Right, our response: the setup's sections with the placed sentences this version touches; a flagged sentence says
    so ("Changed in Amendment 1"; decision 6: it keeps its place until the change is decided).
    Lines for the selected change only: solid to each placed sentence it touches, dotted to the section suggested for it.
    The decide bar opens beside the change (comparebar). The summary line counts the changes and filters them by a click;
    the Verify line says how many of the new version's pages a person verified, with the next step to verify them.
    Prev change (K), Next change (J), Next to decide (F8, the main button); Enter takes the suggestion. More: Only what
    touches our response, Editorial changes: No action for all, Requirement history... Export: Redline (Word), Change
    list (Excel), Author briefs.
Rules: comparemap, changereview, docversions, docintake. Nothing leaves the PC."""
import html
import os

from PySide6.QtCore import QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QImage, QKeySequence, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QFileDialog, QGraphicsPixmapItem, QGraphicsTextItem, QHBoxLayout, QMenu, QSpinBox, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import diag
import changereview as CR
import comparemap as CM
import docintake as DI
import docversions as DV
from . import design as D
from . import changecards as CC
from .comparebar import DecideBar
from .compareview import CmpView, Gutter, _rgba
from .splitlines import BarHost
from .verifypage import PageStrip

SCALE = 2.0
MARGIN = 54
KIND_TONE = {"changed": "warn", "added": "ok", "removed": "crit"}
TEXT_W = 560


class ComparePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.ctx = None
        self.rows, self.links, self.tags, self.suggest, self.shown = [], [], [], [], []
        self.placed, self.touch, self.pdf, self.n, self.i = {}, {}, "", 1, None
        self.sel = (None, None, None)
        self.cur = (None, None, None)
        self.review, self.pk, self.impact = None, "", None
        self.tag_filter = "all"
        self._tries = 0
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["s"])
        from .commandbar import CommandBar
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.b_ver = D.button("Versions", None, None, "Each customer document and the two versions compared")
        self.ver_menu = QMenu(self.b_ver); self.b_ver.setMenu(self.ver_menu)
        self.ver_menu.aboutToShow.connect(self.fill_versions)
        top.addWidget(self.b_ver)
        self.page_box = QSpinBox(); self.page_box.setMinimum(1); self.page_box.setPrefix("Page "); self.page_box.setKeyboardTracking(False)
        self.page_box.valueChanged.connect(lambda n: self.go(n) if n != self.n else None)
        top.addWidget(self.page_box)
        self.p_dec = D.Pill("", "ok"); self.p_dec.hide(); top.addWidget(self.p_dec)
        bar = self.bar = CommandBar(); top.addWidget(bar, 1)
        bar.add("Prev change", lambda: self.step(-1), "The change before this one (K)")
        bar.add("Next change", lambda: self.step(1), "The next change (J)")
        self.b_next = bar.primary("Next to decide", lambda: self.next_open(), "The next change still to decide (F8)")
        self.in_matrix = bar.more("Only what touches our response", lambda _on: self.fill(), "Only the changes that touch a piece "
                                  "in the compliance matrix", checkable=True)
        bar.more("Editorial changes: No action for all", lambda: self.editorial_all(),
                 "Punctuation, spacing, capitals and numbering only: No action (editorial) for each one still to decide")
        bar.more("Requirement history...", lambda: self.history_dialog(),
                 "Every requirement a version changed or removed, its history, and whether its owner confirmed it")
        bar.export("Redline (Word)...", lambda: self.export_redline(), "Removed words struck through, added words marked")
        bar.export("Change list (Excel)...", lambda: self.export_list(), "Every change with its decision")
        bar.export("Author briefs...", lambda: self.author_briefs(), "One brief per person this version touches")
        self.sum = D.label("", "muted"); self.sum.setTextFormat(Qt.RichText); self.sum.linkActivated.connect(self.set_tag_filter)
        v.addWidget(self.sum)
        self.vline = D.label("", "muted"); self.vline.setTextFormat(Qt.RichText); self.vline.linkActivated.connect(lambda _h: self.verify_pages())
        v.addWidget(self.vline)
        self.strip = PageStrip(); self.strip.picked.connect(self.go); v.addWidget(self.strip)
        split = self.split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        self.view = CmpView(self); split.addWidget(self.view)
        self.gutter = Gutter(self); split.addWidget(self.gutter)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0); rv.setSpacing(4)
        rv.addWidget(D.label("Our response", "label"))
        self.tree = QTreeWidget(); self.tree.setHeaderHidden(True); self.tree.setWordWrap(True)
        self.tree.itemClicked.connect(self.tree_clicked)
        rv.addWidget(self.tree, 1)
        self.right_note = D.label("", "muted"); rv.addWidget(self.right_note)
        split.addWidget(right)
        split.setCollapsible(1, False)
        split.setSizes([900, 44, 420]); split.setStretchFactor(0, 1); split.setStretchFactor(1, 0); split.setStretchFactor(2, 0)
        for sb in (self.view.verticalScrollBar(), self.tree.verticalScrollBar()):
            sb.valueChanged.connect(lambda _v: self.gutter.update())
        self.empty = D.EmptyState("No new versions to compare yet", "Add the amendment or the new version in Documents. "
                                  "Changes shows what changed on its pages, beside our response.", "Go to Documents",
                                  lambda: self.host.go("library"))
        v.addWidget(self.empty); self.empty.hide()
        self.decide_panel = DecideBar(self)
        self.bar_host = BarHost(self.decide_panel, self.view.viewport())
        for k, fn in (("J", lambda: self.step(1)), ("K", lambda: self.step(-1)), ("F8", lambda: self.next_open()),
                      ("Return", lambda: self.decide_panel.take()), ("Enter", lambda: self.decide_panel.take()),
                      ("Esc", lambda: self.bar_host.close())):
            s = QShortcut(QKeySequence(k), self); s.setContext(Qt.WidgetWithChildrenShortcut); s.activated.connect(fn)
        self.copy_timer = QTimer(self); self.copy_timer.setInterval(3000); self.copy_timer.timeout.connect(self.retry_copy)
        CC.install(self)                             # 4.6.0: a card per change, Next change (changecards)

    # ------------------------------------------------------------ the effort
    def M(self):
        return self.host.review.M if self.host.review is not None else None

    def item(self, iid):
        return self.host.review.item(iid) if self.host.review is not None and iid else None

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            self.ctx = None
            return
        from .custdocs import Ctx
        self.ctx = Ctx(h)
        docs = [d for d in self.ctx.lib.docs if len(d["versions"]) > 1]
        self.empty.setVisible(not docs)
        for w in (self.split, self.strip, self.sum, self.vline, self.bar, self.b_ver, self.page_box):
            w.setVisible(bool(docs))
        if not docs:
            self.rows = []
            CC.refreshed(self, docs)
            return
        want = self.sel if self.sel[0] in [d["id"] for d in docs] else (docs[0]["id"], None, None)
        self.open_pair(*want)
        CC.refreshed(self, docs)

    def fill_versions(self):
        self.ver_menu.clear()
        if self.ctx is None:
            return
        for d in [x for x in self.ctx.lib.docs if len(x["versions"]) > 1]:
            vs = d["versions"]
            sub = self.ver_menu.addMenu(d["name"])
            for k in range(len(vs) - 1, 0, -1):
                a, b = vs[k - 1], vs[k]
                act = sub.addAction(f"{b['label']} against {a['label']}")
                act.setCheckable(True); act.setChecked(self.sel == (d["id"], a["id"], b["id"]))
                act.triggered.connect(lambda _=False, di=d["id"], ai=a["id"], bi=b["id"]: self.open_pair(di, ai, bi))

    def show(self, doc_id, a=None, b=None):
        """Open Compare on two versions (b and the one before it by default). Returns the rows."""
        self.sel = (doc_id, a, b)
        if self.ctx is None:
            self.refresh()
        else:
            self.open_pair(doc_id, a, b)
        return self.rows

    def open_pair(self, doc_id, a=None, b=None):
        lib = self.ctx.lib
        d = lib.doc(doc_id)
        if d is None or not d["versions"]:
            return []
        ids = [v["id"] for v in d["versions"]]
        b = b if b in ids else ids[-1]
        a = a if a in ids and a != b else ids[max(0, ids.index(b) - 1)]
        va, vb = d["versions"][ids.index(a)], d["versions"][ids.index(b)]
        self.sel, self.cur = (d["id"], va["id"], vb["id"]), (d, va, vb)
        self.b_ver.setText(f"{d['name']}: {vb['label']} against {va['label']}")
        if va is vb:
            self.rows = []
            self.sum.setText("Pick two different versions.")
            return []
        return self.run()

    # ------------------------------------------------------------ compare
    def run(self):
        d, va, vb = self.cur
        lib = self.ctx.lib
        self.snaps = (lib.text(va), lib.text(vb))
        self.rows = CR.keyed(DV.compare(*self.snaps))
        self.review = CR.Review(self.host.ws.root).load()
        self.pk = CR.pair_key(va, vb)
        self.review.opened(d, va, vb, self.rows, save=False)
        M = self.M()
        owner_of = None
        if M is not None:
            import setupdoc as SD
            owner_of = lambda it: SD.owner_of(M, it)                  # noqa: E731
        self.impact = None
        try:                                                   # what this version touches across the effort (was Impact)
            i_a, i_b = d["versions"].index(va), d["versions"].index(vb)
            if i_b == i_a + 1:
                import impact as IM
                self.impact = IM.build(lib, vb["id"], self.ctx.reg.rows(), self.ctx.rec, M, owner_of, volumes=self.ctx.volumes())
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.links = DI.link(M, self.rows, owner_of, files=(va.get("file", ""), vb.get("file", "")))
        from .changeview import tag_rows
        self.tags = tag_rows(self.rows, self.links, self.impact)
        self.suggest = [CM.suggest(r, self.links[k], M, self.tags[k], self.snaps[1]) for k, r in enumerate(self.rows)]
        self.touch = CM.touches(self.rows, self.links, M, self.snaps[1])
        self.review.set_touch(self.pk, self.touch, save=False)
        self.review.save()
        self.load_pages()
        c = DV.summary(self.rows)
        diag.activity("qt_compared", n=c["changed"] + c["added"] + c["removed"])
        self.i = None
        self.fill()
        first = next((k for k in self.shown if not self.decided(k)), self.shown[0] if self.shown else None)
        if first is not None:
            self.select(first)
        return self.rows

    def load_pages(self):
        d, va, vb = self.cur
        self.pdf, self.placed = "", {}
        path = self.ctx.lib.path_of(vb) if hasattr(self.ctx.lib, "path_of") else vb.get("path", "")
        self.vpath = path or ""
        try:
            self.pdf = self.host.verify_page.pdf_of(path) if path and os.path.isfile(path) else ""
        except Exception:  # noqa: BLE001
            diag.swallowed()
        if self.pdf:
            try:
                self.placed = CM.place(self.pdf, self.rows)
            except Exception:  # noqa: BLE001  a page copy that cannot be read: the text stands in
                diag.swallowed()
                self.pdf, self.placed = "", {}
        self._tries = 0
        if not self.pdf and path and os.path.isfile(path):
            self.copy_timer.start()
        else:
            self.copy_timer.stop()

    def retry_copy(self):
        self._tries += 1
        if self._tries > 40 or not self.isVisible():
            self.copy_timer.stop()
            return
        d, va, vb = self.cur
        if vb is None:
            return
        pdf = self.host.verify_page.pdf_of(self.vpath, make=False) if self.vpath else ""
        if pdf:
            self.copy_timer.stop()
            keep = self.i
            self.load_pages()
            self.fill()
            if keep is not None:
                self.select(keep)

    def npages(self):
        if not self.pdf:
            return 1
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(self.pdf)
            n = len(doc); doc.close()
            return n
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return 1

    def page_of(self, i):
        if not self.pdf:
            return 1
        p = self.placed.get(self.rows[i]["key"])
        return p["page"] if p else None

    # ------------------------------------------------------------ what shows
    def decided(self, i):
        return bool(self.review.decisions(self.pk, self.rows[i]["key"])) if self.review is not None else False

    def decided_text(self, key):
        decs = self.review.decisions(self.pk, key) if self.review is not None else []
        return "; ".join(CR.KIND_NAMES[x["kind"]] + (f" {x['target']}" if x.get("target") else "") for x in decs)

    def _keep(self, i, r):
        if r["kind"] == "same":
            return False
        if self.in_matrix.isChecked() and not self.links[i]:
            return False
        f = self.tag_filter
        return (f == "all" or (f == "open" and not self.decided(i)) or (f == "placed" and r["key"] in self.touch)
                or (f == "editorial" and CM.editorial(r)) or f in (self.tags[i] if i < len(self.tags) else ()))

    def fill(self):
        self.shown = [i for i, r in enumerate(self.rows) if self._keep(i, r)]
        self.say_summary()
        self.say_verify()
        self.fill_tree()
        n = self.npages()
        self.page_box.blockSignals(True); self.page_box.setMaximum(n); self.page_box.blockSignals(False)
        self.show_strip()
        self.draw()
        CC.fill(self)

    def say_summary(self):
        d, va, vb = self.cur
        ch = [i for i, r in enumerate(self.rows) if r["kind"] != "same"]
        if vb is None:
            self.sum.setText("")
            return
        if not ch:
            self.sum.setText(f"{vb['label']} against {va['label']}: no changes.")
            self.p_dec.hide()
            return
        a = lambda key, text: f"<a href='{key}'>{text}</a>"                       # noqa: E731
        n_pl = sum(1 for i in ch if self.rows[i]["key"] in self.touch)
        n_ru = sum(1 for i in ch if "rule" in self.tags[i])
        n_ed = sum(1 for i in ch if CM.editorial(self.rows[i]))
        n_op = sum(1 for i in ch if not self.decided(i))
        parts = [a("all", f"{len(ch)} changes"), a("placed", f"{n_pl} touch placed pieces"), a("rule", f"{n_ru} submission rules"),
                 a("editorial", f"{n_ed} editorial"), a("open", f"{n_op} to decide")]
        txt = f"{html.escape(vb['label'])} against {html.escape(va['label'])}: " + " · ".join(parts)
        if self.tag_filter != "all" or self.in_matrix.isChecked():
            txt += f"  ·  Showing {len(self.shown)}. {a('all', 'Show all')}"
        if self.M() is None:
            txt += "  ·  Pick the documents in Shred (it extracts them) to see which changes touch our response."
        self.sum.setText(txt)
        dn, n = self.review.progress(self.pk, self.rows)
        self.p_dec.setText(f"{dn} of {n} decided"); self.p_dec.set_tone("ok" if dn == n else "warn"); self.p_dec.show()

    def say_verify(self):
        d, va, vb = self.cur
        if vb is None:
            return
        if not self.pdf:
            self.vline.setText(f"{html.escape(vb['label'])}: no page copy yet, so its text stands in for the page."
                               + (" The page copy is being made." if self.copy_timer.isActive() else ""))
            return
        try:
            import verifystate as VS
            vp = self.host.verify_page
            c = VS.counts(self.pdf, vp.store(), os.path.basename(self.vpath))
        except Exception:  # noqa: BLE001
            diag.swallowed()
            c = None
        if c and c["verified"] >= c["pages"]:
            self.vline.setText(f"{html.escape(vb['label'])}: every page verified.")
        elif c:
            self.vline.setText(f"{html.escape(vb['label'])}: {c['verified']} of {c['pages']} pages verified. A misread word shows "
                               f"here as a change. <a href='verify'>Verify its pages</a>")
        else:
            self.vline.setText("")

    def show_strip(self):
        st = CM.page_status(self.placed, [self.rows[i] for i in self.shown], lambda k: bool(self.review.decisions(self.pk, k))) \
            if self.pdf else {}
        n = self.npages()
        tone = {"todo": "look", "done": "verified"}
        if not self.pdf:
            any_open = any(not self.decided(i) for i in self.shown)
            self.strip.set(["look" if any_open else ("verified" if self.shown else "notyet")], 1)
        else:
            self.strip.set([tone.get(st.get(k), "notyet") for k in range(1, n + 1)], self.n)

    # ------------------------------------------------------------ our response
    def fill_tree(self):
        import compliance as C
        self.tree.clear()
        self.nodes, self.sec_nodes = {}, {}
        M = self.M()
        if M is None:
            self.right_note.setText("Pick the documents in Shred (it extracts them) to see our response here.")
            return
        flags = CM.flags(M, self.review)
        mine = {}
        for key, t in self.touch.items():
            for iid in t["items"]:
                mine.setdefault(iid, []).append(key)
        by_sec = {}
        for iid in mine:
            it = self.item(iid)
            if it and it.get("map"):
                by_sec.setdefault(it["map"], []).append(it)
        stack = []
        t = D.tokens()
        for o in M.outline:
            lab = C.outline_label(o)
            num = o.get("num", "")
            node = QTreeWidgetItem([lab + (f"   ({len(by_sec[lab])})" if lab in by_sec else "")])
            node.setData(0, Qt.UserRole, ("sec", lab))
            while stack and not (num.startswith(stack[-1][0] + ".") and stack[-1][0]):
                stack.pop()
            (stack[-1][1].addChild(node) if stack else self.tree.addTopLevelItem(node))
            stack.append((num, node))
            self.sec_nodes[lab] = node
            for it in by_sec.get(lab, []):
                fl = flags.get(it["id"], [])
                note = "  ·  " + fl[0]["text"] if fl else "  ·  decided"
                ch = QTreeWidgetItem([f"{it['id']}  {it['text'][:110]}{note}"])
                ch.setData(0, Qt.UserRole, ("item", it["id"]))
                ch.setForeground(0, QColor(t["warn"] if fl else t["muted"]))
                ch.setToolTip(0, it["text"])
                node.addChild(ch)
                self.nodes[it["id"]] = ch
        self.tree.expandAll()
        n = len(mine)
        self.right_note.setText(f"{n} placed piece{'s' if n != 1 else ''} touched by {self.cur[2]['label']}; each keeps its place "
                                "until its change is decided." if n else "No placed piece is touched by this version.")

    def targets_of(self, i):
        """[(tree node, style, tone)] the selected change's lines go to."""
        out = []
        for h in (self.links[i] if i is not None and i < len(self.links) else []):
            node = self.nodes.get(h["id"])
            if node is not None:
                out.append((node, "placed", "req"))
        s = self.suggest[i] if i is not None and i < len(self.suggest) else None
        if s and s["kind"] == "new" and s.get("target") in self.sec_nodes:
            out.append((self.sec_nodes[s["target"]], "suggested", "faint"))
        return out

    def tree_clicked(self, node, _col):
        what = node.data(0, Qt.UserRole)
        if not what:
            return
        if what[0] == "sec":
            self.decide_panel.set_sec(what[1])
        else:
            self.decide_panel.set_req(what[1])

    # ------------------------------------------------------------ their page
    def go(self, n):
        n = max(1, min(self.npages(), int(n)))
        if n == self.n and self.view.boxes:
            return False
        self.n = n
        self.draw()
        on = [i for i in self.shown if self.page_of(i) == n]
        if on:
            self.select(on[0])
        return True

    def draw(self):
        if CC.on(self):                              # 4.7.1: the page view is hidden behind the cards; drawn when shown
            self._draw_owed = True
            return
        self._draw_owed = False
        sc = self.view.scene(); sc.clear(); self.view.boxes = {}
        self._tag_y = -100.0
        self.page_box.blockSignals(True); self.page_box.setValue(self.n); self.page_box.blockSignals(False)
        if not self.rows:
            return
        if self.pdf:
            self.draw_pdf(sc)
        else:
            self.draw_text(sc)
        self.fit()
        self.gutter.update()

    def _mark(self, sc, i, rects, words, removed=False):
        t = D.tokens()
        r = self.rows[i]
        sel = i == self.i
        done = self.decided(i)
        col = QColor(t[KIND_TONE[r["kind"]]])
        if r["kind"] == "changed" and CM.editorial(r):
            col = QColor(t["faint"])
        a = 60 if done else 255
        for l, tp, rr, b in words:
            sc.addRect(QRectF(MARGIN + l, tp, rr - l, b - tp), QPen(Qt.NoPen), QBrush(_rgba(t["ok"], 40 if done else 90)))
        box = None
        for l, tp, rr, b in rects:
            q = QRectF(MARGIN + l - 2, tp - 2, rr - l + 4, b - tp + 4)
            box = q if box is None else box.united(q)
        if box is None:
            return
        pen = QPen(QColor(t["focus"]) if sel else _rgba(col, a), 2.2 if sel else (1.4 if not done else 0.8))
        if removed:
            pen.setStyle(Qt.SolidLine)
            sc.addRect(box, pen, QBrush(_rgba(t["crit"], 120 if not done else 40)))
        else:
            for l, tp, rr, b in rects:
                sc.addRect(QRectF(MARGIN + l - 2, tp - 2, rr - l + 4, b - tp + 4), pen, QBrush(Qt.NoBrush))
        tag = sc.addSimpleText(("✓ " if done else "") + {"changed": "Changed", "added": "Added", "removed": "Removed"}[r["kind"]])
        f = tag.font(); f.setPointSizeF(6.5); tag.setFont(f)
        y = max(box.top() - 2, self._tag_y + 9)                 # the margin's words never sit on each other
        self._tag_y = y
        tag.setBrush(_rgba(col, 255 if not done else 140)); tag.setPos(2, y)
        self.view.boxes[i] = box.adjusted(0, -2, 0, 2) if removed else box

    def draw_pdf(self, sc):
        t = D.tokens()
        w, h = 612, 792
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(self.pdf)
            pg = doc[self.n - 1]
            w, h = pg.get_size()
            img = pg.render(scale=SCALE).to_pil().convert("RGB")
            doc.close()
            q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
            pix = QGraphicsPixmapItem(QPixmap.fromImage(q)); pix.setScale(1 / SCALE); pix.setPos(MARGIN, 0); pix.setZValue(-1)
            pix.setTransformationMode(Qt.SmoothTransformation); sc.addItem(pix)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            sc.addRect(QRectF(MARGIN, 0, w, h), QPen(QColor(t["border"])), QBrush(QColor(t["surface"])))
        on = [(p["rects"][0][1], i, p) for i in self.shown for p in [self.placed.get(self.rows[i]["key"])] if p and p["page"] == self.n and p["rects"]]
        for _y, i, p in sorted(on, key=lambda x: (x[0], x[1])):
            self._mark(sc, i, p["rects"], p.get("changed", []), removed=bool(p.get("removed")))
        sc.setSceneRect(QRectF(0, -10, MARGIN + w + 20, h + 20))

    def draw_text(self, sc):
        """No page copy yet: the new version's text in reading order, marked the same way."""
        t = D.tokens()
        old, new = self.snaps
        at = {r["nj"]: i for i, r in enumerate(self.rows) if r.get("nj") is not None}
        removed_before = {}
        nxt = None
        for i in range(len(self.rows) - 1, -1, -1):
            r = self.rows[i]
            if r.get("nj") is not None:
                nxt = r["nj"]
            elif r["kind"] == "removed":
                removed_before.setdefault(nxt if nxt is not None else len(new), []).insert(0, i)
        shown = set(self.shown)
        y, last_head = 0.0, None
        for j in list(range(len(new))) + [len(new)]:
            for i in removed_before.get(j, []):
                if i not in shown:
                    continue
                ti = QGraphicsTextItem()
                ti.setTextWidth(TEXT_W)
                ti.setHtml(f"<span style='color:{t['crit']};text-decoration:line-through'>{html.escape(self.rows[i]['old'])}</span>")
                ti.setPos(MARGIN, y); sc.addItem(ti)
                br = ti.boundingRect()
                self._mark(sc, i, [(0, y + 2, TEXT_W, y + br.height() - 2)], [], removed=False)
                y += br.height() + 2
            if j >= len(new):
                break
            s = new[j]
            head = " ".join(x for x in (s.get("s", ""), s.get("t", "")) if x)
            if head and head != last_head:
                hi = QGraphicsTextItem(); hi.setTextWidth(TEXT_W); hi.setHtml(f"<b>{html.escape(head)}</b>")
                hi.setPos(MARGIN, y + 4); sc.addItem(hi)
                y += hi.boundingRect().height() + 6
                last_head = head
            i = at.get(j)
            ti = QGraphicsTextItem(); ti.setTextWidth(TEXT_W)
            r = self.rows[i] if i is not None else None
            if r is not None and r["kind"] in ("changed", "added") and i in shown:
                if r["kind"] == "added":
                    body = f"<span style='background:{t['ok_soft']}'>{html.escape(s['x'])}</span>"
                else:
                    out = []
                    for k, part in DV.word_diff(r["old"], r["new"]):
                        if k == "=":
                            out.append(html.escape(part))
                        elif k == "+":
                            out.append(f"<span style='background:{t['ok_soft']}'>{html.escape(part)}</span>")
                    body = " ".join(out)
            else:
                body = f"<span style='color:{t['muted']}'>{html.escape(s['x'])}</span>"
            ti.setHtml(body)
            ti.setPos(MARGIN, y); sc.addItem(ti)
            br = ti.boundingRect()
            if r is not None and r["kind"] in ("changed", "added") and i in shown:
                self._mark(sc, i, [(0, y + 2, TEXT_W, y + br.height() - 2)], [])
            y += br.height()
        sc.setSceneRect(QRectF(0, -10, MARGIN + TEXT_W + 20, y + 20))

    def fit(self):
        r = self.view.scene().sceneRect()
        if r.width() <= 0:
            return
        k = max(0.5, min(3.0, (self.view.viewport().width() - 8) / r.width()))
        self.view.resetTransform(); self.view.scale(k, k)

    # ------------------------------------------------------------ the selection
    def current_index(self):
        return self.i

    def select_index(self, i):
        if i in self.shown:
            self.select(i)
            return True
        return False

    def select(self, i):
        if i is None or not (0 <= i < len(self.rows)):
            self.i = None
            self.bar_host.close()
            self.decide_panel.show_change(None)
            self.gutter.update()
            return
        self.i = i
        n = self.page_of(i)
        if n and n != self.n:
            self.n = n
        self.draw()
        box = self.view.boxes.get(i)
        if box is not None:
            self.view.centerOn(box.center())
        self.decide_panel.show_change(i)
        for h in self.links[i] if i < len(self.links) else []:
            node = self.nodes.get(h["id"])
            if node is not None:
                self.tree.scrollToItem(node)
                break
        else:
            s = self.suggest[i] if i < len(self.suggest) else None
            if s and s.get("target") in self.sec_nodes:
                self.tree.scrollToItem(self.sec_nodes[s["target"]])
        self.place_bar()
        self.show_strip()
        self.gutter.update()
        CC.select(self, i)

    def place_bar(self):
        if CC.on(self):                              # 4.6.0: the card carries the choices
            return self.bar_host.close()
        r = self.view.view_rect(self.i) if self.i is not None else None
        if r is None:
            r = QRect(8, 8, 10, 10)
        w = min(460, max(300, self.view.viewport().width() // 2))
        self.bar_host.show_for(r, width=w, height=self.decide_panel.measure(w))

    def redraw(self, i=None):
        """After a decision: the counts, the marks and the bar again, the same change selected."""
        keep = self.i if i is None else i
        self.fill()
        if keep is not None and keep in self.shown:
            self.select(keep)
        elif self.shown:
            self.select(self.shown[0])
        else:
            self.select(None)

    def step(self, d):
        if not self.shown:
            return None
        if self.i not in self.shown:
            k = 0 if d > 0 else len(self.shown) - 1
        else:
            k = max(0, min(len(self.shown) - 1, self.shown.index(self.i) + d))
        self.select(self.shown[k])
        return self.i

    def next_open(self):
        if not self.shown:
            return None
        start = self.shown.index(self.i) + 1 if self.i in self.shown else 0
        order = self.shown[start:] + self.shown[:start]
        nx = next((k for k in order if not self.decided(k)), None)
        if nx is None:
            self.host.status("Every change shown is decided.")
            return None
        self.select(nx)
        return nx

    def set_tag_filter(self, tag):
        self.tag_filter = tag or "all"
        if tag == "all":
            self.in_matrix.setChecked(False)
        keep = self.i
        self.fill()
        if keep in self.shown:
            self.select(keep)
        elif self.shown:
            self.select(self.shown[0])

    def editorial_all(self):
        keys = {r["key"] for r in self.rows if CM.editorial(r)}
        n = self.decide_panel.no_action_all(keys)
        self.host.status(f"No action (editorial) for {n} change{'s' if n != 1 else ''}.")
        self.redraw()
        return n

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, lambda: (self.fit(), self.place_bar() if self.i is not None else None, self.gutter.update()))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()
        if self.i is not None and self.bar_host.bar.isVisible():
            self.place_bar()

    # ------------------------------------------------------------ the next step, and the rest
    def verify_pages(self):
        if not self.vpath:
            return False
        self.host.go("verify")
        self.host.verify_page.open_doc(self.vpath)
        diag.activity("compare_to_verify")
        return True

    def author_briefs(self, run=True):
        d, va, vb = self.cur
        if vb is None:
            return None
        ip = self.host.impact_page
        ip.refresh()
        ip.show(vb["id"])
        return ip.briefs_dialog(run=run)

    def history_dialog(self, run=True):
        from .changeview import history_dialog
        return history_dialog(self, run)

    def open_item(self, iid):
        if self.item(iid) is None:
            return None
        self.host.go("assign")
        self.host.assign_page.select(iid)
        diag.activity("qt_compare_opened_in_assign")
        return iid

    def open_key(self, key):
        """Select the change with this key (from a flag in Review or Setup)."""
        i = next((k for k, r in enumerate(self.rows) if r.get("key") == key), None)
        if i is None:
            return False
        if i not in self.shown:
            self.set_tag_filter("all")
        self.select(i)
        return True

    def export_redline(self, path=None):
        d, va, vb = self.cur
        if d is None or va is None or va is vb:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Redline", self.host.out_path("redline", Doc=d["name"], From=va["label"], To=vb["label"]), "Word (*.docx)")
            if not path:
                return None
        DV.export_redline(path, d["name"], va, vb, self.rows, only_changes=True)
        self.host.toast("Redline written")
        return path

    def export_list(self, path=None):
        d, va, vb = self.cur
        if d is None or va is None or va is vb:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Change list", self.host.out_path("change_list", Doc=d["name"], From=va["label"], To=vb["label"]), "Excel (*.xlsx)")
            if not path:
                return None
        DV.export_list(path, self.ctx.lib, doc=d, compares=[(d, va, vb, self.rows)])
        self.host.toast("Change list written")
        return path
