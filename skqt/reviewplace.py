"""Review and place (3.85.0, claude/stationkeeper-review-and-structure-2026-11-08.md): their text on the left, our
structure on the right, joined by lines for the selection only.

    LinkGutter      painted between the page and the structure: a line from each selected sentence to its home (solid
                    and in its kind's color when placed, dotted grey while only suggested), an arrow at the edge for a
                    home scrolled away. Lines for headings (More) adds a faint line from each customer heading on the
                    page to the section that answers it.
    Placer          the home suggested with the reason under the decide line ("Goes to 2.1 Staffing Plan: L.3.5 is
                    answered by 2.1"), Enter accepts what it is and where it goes; after a placement the offer to send
                    the rest of the heading too (Map and place N, Map only, Just this one); Map this heading to the
                    target on the sentence's menu; what is left (not decided, not placed, headings not answered), each
                    a link that selects them; Export cross-reference table...
Rules: homesuggest. Nothing leaves the PC."""
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QWidget

import diag
import homesuggest as HS
from . import design as D
from .splitlines import ends

KIND_TONE = {"Keep": "req", "Context": "ctx", "Customer": "cust"}


class LinkGutter(QWidget):
    def __init__(self, page):
        super().__init__()
        self.pg = page
        self.setFixedWidth(44)
        self.heads_on = False
        self.drawn = []                                  # [(ly, le, ry, re, style)]: for tests and the paint

    def _y(self, w, local_y):
        return self.mapFromGlobal(w.mapToGlobal(QPoint(0, int(local_y)))).y()

    def _row_rect(self, label):
        """The section's row in the structure (its viewport's coordinates), scrolled into view first."""
        tree = self.pg.tree
        hit = None
        it = tree.invisibleRootItem()
        stack = [it.child(i) for i in range(it.childCount())]
        while stack:
            x = stack.pop(0)
            if x.data(0, Qt.UserRole) == label:
                hit = x
                break
            stack += [x.child(i) for i in range(x.childCount())]
        return (tree.visualItemRect(hit), hit) if hit is not None else (None, None)

    def compute(self):
        pg = self.pg
        out = []
        if pg.R is None or pg.cx is not None or getattr(getattr(pg, "views", None), "key", "structure") != "structure":
            self.drawn = out                              # 3.90.0: the lines go to Our structure only
            return out
        view, tree = pg.view, pg.tree
        lvp, rvp = view.viewport(), tree.viewport()
        ltop, lbot = self._y(lvp, 0), self._y(lvp, lvp.height())
        rtop, rbot = self._y(rvp, 0), self._y(rvp, rvp.height())
        side = getattr(pg, "side_area", None)
        if side is not None and side.isVisible():          # the structure scrolls inside the side area too
            rtop = max(rtop, self._y(side.viewport(), 0))
            rbot = min(rbot, self._y(side.viewport(), side.viewport().height()))
        pairs = []
        for it in pg.selected():
            box = view.boxes.get(it["id"])
            if box is None:
                continue
            if it.get("map"):
                pairs.append((box, it["map"], KIND_TONE.get(it.get("decision"), "head"), "placed"))
            else:
                h = HS.home(pg.M, it)
                if h:
                    pairs.append((box, h["label"], "faint", "suggested"))
        if self.heads_on:
            for it in pg.R.rows_of(pg.file) if pg.file else []:
                num = HS.heading_of(it)[0]
                to = HS._S(pg.M)["rfp_map"].get(num)
                box = view.boxes.get(it["id"])
                if to and box is not None and it.get("type") == "Heading":
                    pairs.append((box, to, "accent", "heading"))
        for box, label, tone, style in pairs:
            r = view.mapFromScene(box.sceneBoundingRect()).boundingRect()
            rr, _x = self._row_rect(label)
            if rr is None:
                continue
            ly, le = ends(self._y(lvp, r.center().y()), ltop + 4, lbot - 4)
            ry, re_ = ends(self._y(rvp, rr.center().y()), rtop + 4, rbot - 4)
            out.append((ly, le, ry, re_, style, tone))
        self.drawn = out
        return out

    def paintEvent(self, _e):
        out = self.compute()
        if not out:
            return
        t = D.tokens()
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        for ly, le, ry, re_, style, tone in out:
            col = QColor(t.get(tone, t["faint"]))
            if style == "heading":
                col.setAlpha(110)
            pen = QPen(col, 1.8 if style == "placed" else 1.2)
            pen.setStyle(Qt.SolidLine if style == "placed" else (Qt.DotLine if style == "suggested" else Qt.DashLine))
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            path = QPainterPath(QPointF(0, ly))
            path.cubicTo(QPointF(w * 0.5, ly), QPointF(w * 0.5, ry), QPointF(w, ry))
            p.drawPath(path)
            p.setPen(Qt.NoPen); p.setBrush(col)
            for x, y, edge in ((5, ly, le), (w - 5, ry, re_)):
                if edge:
                    d = -1 if edge < 0 else 1
                    p.drawPolygon(QPolygonF([QPointF(x - 4, y), QPointF(x + 4, y), QPointF(x, y + 6 * d)]))
        p.end()


class Placer:
    """Attached to Review (page.placer)."""

    def __init__(self, page, split, decide_layout):
        self.pg = page
        self.gutter = LinkGutter(page)
        split.insertWidget(1, self.gutter)
        split.setCollapsible(1, False)
        split.setSizes([1040, 44, 520])                  # the structure keeps its width beside the gutter
        split.setStretchFactor(0, 1); split.setStretchFactor(1, 0); split.setStretchFactor(2, 0)
        for sb in (page.view.verticalScrollBar(), page.tree.verticalScrollBar(), page.side_area.verticalScrollBar()):
            sb.valueChanged.connect(lambda _v: self.gutter.update())
        self.home_lbl = D.label("", "muted")
        self.home_lbl.setTextFormat(Qt.RichText)
        self.home_lbl.linkActivated.connect(self.open_flag)
        decide_layout.addWidget(self.home_lbl)
        self.offer_row = QWidget(); orow = QHBoxLayout(self.offer_row); orow.setContentsMargins(0, 0, 0, 0)
        self.offer_lbl = D.label("", None)
        orow.addWidget(self.offer_lbl, 1)
        self.b_place = D.button("Map and place", "primary", lambda: self.take("place"))
        orow.addWidget(self.b_place)
        orow.addWidget(D.button("Map only", None, lambda: self.take("map"), "The heading's other sentences are suggested for it"))
        orow.addWidget(D.button("Just this one", None, lambda: self.take("once"), "No map; the app does not ask again for it"))
        self.offer_row.setVisible(False)
        decide_layout.addWidget(self.offer_row)
        self.left_lbl = D.label("", "muted")
        self.left_lbl.setTextFormat(Qt.RichText)
        self.left_lbl.linkActivated.connect(self.select_left)
        decide_layout.addWidget(self.left_lbl)
        self.off = None

    # ------------------------------------------------------------ the selection
    def on_select(self, rows):
        pg = self.pg
        self.gutter.update()
        if pg.R is None or pg.cx is not None or not rows:
            self.home_lbl.setText("")
            return
        it = rows[-1]
        if it.get("map"):
            fl = (getattr(pg, "amend_flags", None) or {}).get(it["id"])      # 3.89.0 decision 6
            from . import amendflags as AF
            self.home_lbl.setText(f"Placed in <b>{it['map']}</b>" + (f"<br>{AF.line(fl[0])}" if fl else ""))
            self.scroll_to(it["map"])
            return
        h = HS.home(pg.M, it)
        self.home_lbl.setText(f"Goes to <b>{h['label']}</b>: {h['why']}. Enter accepts it." if h else
                              "No home suggested yet: pick a target section on the right, or Map the heading.")
        if h:
            self.scroll_to(h["label"])

    def scroll_to(self, label):
        _r, x = self.gutter._row_rect(label)
        if x is not None:
            self.pg.tree.scrollToItem(x)
            try:
                self.pg.side_area.ensureWidgetVisible(self.pg.tree, 0, 0)
            except Exception:  # noqa: BLE001
                diag.swallowed()
            self.gutter.update()

    def home_for(self, it):
        h = HS.home(self.pg.M, it)
        return h["label"] if h else ""

    # ------------------------------------------------------------ the offer after a placement
    def after_place(self, rows, label):
        """Called once requirements were placed in label: the offer for the first one's customer heading."""
        if not rows or not label or self.pg._offer_off:
            return None
        self.off = HS.offer(self.pg.M, rows[0], label)
        if self.off and self.off["rest"]:
            n = len(self.off["rest"])
            self.offer_lbl.setText(f"Send the rest of {self.off['num']} {self.off['title']} to {label} too? "
                                   f"({n} more sentence{'s' if n != 1 else ''})")
            self.b_place.setText(f"Map and place {n}")
            self.offer_row.setVisible(True)
        else:
            self.off = None
            self.offer_row.setVisible(False)
        return self.off

    def take(self, how):
        pg, off = self.pg, self.off
        if not off:
            return 0

        def place(ids, label):
            rows = [x for x in (pg.R.item(i) for i in ids) if x]
            pg._offer_off = True
            try:
                with pg.R.group():
                    return pg.R.req(rows, label) or 0
            finally:
                pg._offer_off = False
        pg.R.snap()
        n = HS.take_offer(pg.M, off, how, place)
        self.off = None
        self.offer_row.setVisible(False)
        diag.activity("review_map_offer", how=how, n=n)
        pg.after({"place": f"{off['num']} goes to {off['label']}: {n} more placed.",
                  "map": f"{off['num']} goes to {off['label']}: its other sentences are suggested there.",
                  "once": f"Just this one: {off['num']} stays unmapped."}[how])
        return n

    # ------------------------------------------------------------ map a heading, what is left, the table
    def map_selected(self, label=None):
        pg = self.pg
        label = label if label is not None else (pg.target or "")
        nums = sorted({HS.heading_of(it)[0] for it in pg.selected() if HS.heading_of(it)[0]})
        if not nums:
            pg.host.status("The selected sentences sit under no customer heading.")
            return 0
        pg.R.snap()
        for n in nums:
            HS.map_heading(pg.M, n, label)
        pg.after((f"{', '.join(nums)} goes to {label}." if label else f"{', '.join(nums)}: map cleared.")
                 + " Placed sentences stay where they are.")
        return len(nums)

    def show_left(self):
        pg = self.pg
        if pg.R is None or pg.cx is not None:
            self.left_lbl.setText("")
            return
        lf = HS.left(pg.M)
        cov = HS.coverage(pg.M)
        ans = sum(1 for c in cov if c["answered"])
        from . import amendflags as AF                           # 3.89.0 decision 6
        nf = len(AF.flags(pg.host))
        self.left_lbl.setText(f"Left: <a href='undecided'>{len(lf['undecided'])} not decided</a> · "
                              f"<a href='unplaced'>{len(lf['unplaced'])} not placed</a> · "
                              f"{ans} of {len(cov)} customer headings answered"
                              + (f" · <a href='flagged'>{nf} changed by an amendment</a>" if nf else "")
                              + self.verify_changed())

    def verify_changed(self):
        """3.90.0: " · Verify changed this file after it was read (10:12): read it again", or ""."""
        pg = self.pg
        f = getattr(pg, "file", "") or ""
        if not f or pg.host.ws is None:
            return ""
        read_at = next((row[2] for row in reversed(pg.M.sources) if row and row[0] == f and len(row) > 2), "")
        try:
            import verifystate as VS
            ch = VS.changed_after(pg.host.verify_page.store(), f, read_at)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return ""
        self.reread = f if ch else ""
        return (f" · <span style='color:{D.tokens()['warn']}'>Verify changed this file after it was read ({ch[11:16]})</span>: "
                f"<a href='reread'>read it again</a>") if ch else ""

    def read_again(self):
        """The Read tab with this file ticked, to read it again with Verify's corrections."""
        f = getattr(self, "reread", "")
        if not f:
            return 0
        self.pg.host.go("read")
        n = self.pg.host.read_page.tick_only([f])
        self.pg.host.status("Read it again: the file is ticked; your decisions are kept." if n else
                            f"{f} is not in the list to read: add it from the Library.")
        return n

    def open_flag(self, href):
        """3.89.0: the link on a flagged sentence opens its change in Compare."""
        from . import amendflags as AF
        f = AF.from_link(href)
        return AF.open_change(self.pg.host, f) if f else False

    def select_left(self, which):
        pg = self.pg
        if which == "reread":                               # 3.90.0
            return self.read_again()
        if which == "flagged":                              # 3.89.0: the placed sentences an amendment changed
            from . import amendflags as AF
            ids = set(AF.flags(pg.host))
        else:
            ids = set(HS.left(pg.M)[which])
        sc = pg.view.scene()
        sc.clearSelection()
        n = 0
        for iid, box in pg.view.boxes.items():
            if iid in ids:
                box.setSelected(True); n += 1
        rest = len(ids) - n
        pg.host.status(f"{n} selected in this document" + (f"; {rest} more in other documents." if rest else "."))
        return n

    def toggle_heads(self, on):
        self.gutter.heads_on = bool(on)
        self.gutter.update()

    def export_crossref(self, path=None):
        pg = self.pg
        if pg.M is None:
            return ""
        if path is None:
            path, _f = QFileDialog.getSaveFileName(pg, "Cross-reference table", "Cross-reference table.xlsx", "Excel (*.xlsx)")
            if not path:
                return ""
        from openpyxl import Workbook
        from openpyxl.styles import Font
        wb = Workbook(); ws = wb.active; ws.title = "Cross-reference"
        ws.append(["Customer heading", "Title", "Where we answer it"])
        for c in ws[1]:
            c.font = Font(bold=True)
        for row in HS.crossref_rows(pg.M):
            ws.append(list(row))
        for col, wdt in zip("ABC", (18, 48, 48)):
            ws.column_dimensions[col].width = wdt
        wb.save(path)
        diag.activity("crossref_exported")
        pg.host.status("Cross-reference table written.")
        return path
