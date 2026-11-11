"""Changes, as designed (4.6.0; claude/stationkeeper-documents-changes-plan-4.6.md, step 2; the six-steps board 2).

Left, the new versions, each with how many of its changes are left to decide. Right, one card per change: where it is,
the old and new wording inline (old words struck, new ones marked), what it touches in our response, and three ways to
decide it on the card: No impact, Re-shred (into Shred's queue), Ask a question; the rest of the choices under the card's
More. A decided card turns pale and says what was decided, with Undo. The main button is Next change (the next one to
decide); "Open in Word as tracked changes" sits beside it. The footer says how many passages wait in Shred, with a link
to the re-shred queue. Any two files and the page view (each change marked on the new version's page, beside our
response) are under More.

The cards drive ComparePage's own machinery (rows, the decide bar's decide, next_open): the focus changes what the page
shows, never what it can do. SK_CHANGES_CLASSIC=1 keeps the page as it was, for the tests written before 4.6.0 that drive
the page view. Rules only (No AI); nothing leaves the PC."""
import html
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QScrollArea, QSplitter, QVBoxLayout, QWidget

import diag
from . import design as D

CAP = 150                     # cards built at once; the rest wait behind a filter or the next ones decided


def classic():
    return bool(os.environ.get("SK_CHANGES_CLASSIC"))


def on(page):
    return getattr(page, "cards", None) is not None and not getattr(page, "page_view", False)


def install(page):
    """Called at the end of ComparePage.__init__."""
    page.cards = None
    page.page_view = False
    if classic():
        return
    v = page.layout()
    page.cards = Cards(page)
    v.insertWidget(v.indexOf(page.split), page.cards, 1)
    b = page.bar
    for c in list(b.commands):
        if c is not b.main and c.text() in ("Prev change", "Next change"):
            c.setVisible(False)
    b.commands = [c for c in b.commands if c.isVisibleTo(b) or c is b.main]
    b.main.setText("Next change")
    b.main.setToolTip("The next change still to decide (F8). Enter takes the suggestion on the selected card.")
    page.b_word = b.add("Open in Word as tracked changes", lambda: open_in_word(page),
                        "The two versions in Word, every change a tracked change (Word compares them when it is on this PC)")
    b.more_sep()
    page.a_page_view = b.more("See the changes on the page", lambda on_: set_page_view(page, on_),
                              "Each change marked on the new version's page, beside our response", checkable=True)
    b.more("Any two files...", lambda: any_two(page), "Two versions of anything: our drafts, a file from outside the app")
    page.b_ver.setVisible(False)
    page.page_box.setVisible(False)


def any_two(page):
    sp = getattr(page.host, "compare_space", None)
    if sp is not None:
        sp.tabs.setCurrentIndex(1)
    return sp


def set_page_view(page, on_):
    page.page_view = bool(on_)
    show(page)
    if not on_:
        fill(page)
    elif page.i is not None:
        page.select(page.i)
    elif getattr(page, "_draw_owed", False):
        page.draw()


def show(page):
    """Which of the two views shows (after refresh decided whether there is anything to compare)."""
    if page.cards is None:
        return
    has = bool(getattr(page, "rows", None)) or page.cards.versions.count() > 0
    cards = has and not page.page_view
    page.cards.setVisible(cards)
    for w in (page.split, page.strip, page.page_box):
        w.setVisible(has and page.page_view)
    page.b_ver.setVisible(False)
    if cards:
        page.bar_host.close()


def open_in_word(page):
    """The two versions' original files, every change a tracked change: Word's Compare for two Word files, the text of
    both otherwise (the same as Any two files' export). Returns the path written, or None."""
    d, va, vb = page.cur
    if vb is None or va is vb:
        page.host.status("Pick a new version first.")
        return None
    lib = page.ctx.lib
    a, b = lib.path_of(va), lib.path_of(vb)
    if not (a and b and os.path.isfile(a) and os.path.isfile(b)):
        page.host.status("The original files of both versions are needed: one is not here.")
        return None
    import filesafety as FS
    path = FS.new_path(b, "tracked changes").rsplit(".", 1)[0] + ".docx"
    import compareany as CA
    import wordcompare as WC
    if WC.available() and a.lower().endswith(".docx") and b.lower().endswith(".docx"):
        r = WC.compare(a, b, path, "Compare")
        if r.get("ok"):
            page.host.toast(f"Tracked changes saved: {r.get('revisions', 0)} change(s), compared by Word")
            _open(path)
            return path
    n = CA.export_tracked(path, CA.compare(a, b))
    diag.activity("changes_tracked_word", n=n)
    page.host.toast(f"Tracked changes saved: {n} change(s)")
    _open(path)
    return path


def _open(path):
    if os.environ.get("AH_TEST"):
        return
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


# ------------------------------------------------------------------ hooks from ComparePage
def refreshed(page, docs):
    if page.cards is None:
        return
    page.cards.fill_versions(docs)
    show(page)


def fill(page):
    if on(page):
        page.cards.fill_cards()


def select(page, i):
    if on(page):
        page.cards.mark(i)


class Cards(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.boxes = {}
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["s"])
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(4)
        lv.addWidget(D.label("New versions", "label", wrap=False))
        self.versions = QListWidget(); self.versions.itemClicked.connect(self.pick); lv.addWidget(self.versions, 1)
        split.addWidget(left)
        self.area = QScrollArea(); self.area.setWidgetResizable(True); self.area.setFrameShape(QFrame.NoFrame)
        self.inner = QWidget(); self.col = QVBoxLayout(self.inner); self.col.setAlignment(Qt.AlignTop)
        self.col.setSpacing(D.SPACE["s"]); self.col.setContentsMargins(0, 0, D.SPACE["s"], 0)
        self.area.setWidget(self.inner)
        split.addWidget(self.area)
        split.setSizes([280, 900]); split.setStretchFactor(1, 1)
        self.foot = D.label("", "muted"); self.foot.setTextFormat(Qt.RichText); self.foot.linkActivated.connect(self.to_queue)
        v.addWidget(self.foot)

    # -------------------------------------------------------------- the versions
    def fill_versions(self, docs):
        pg = self.page
        self.versions.clear()
        try:
            import changereview as CR
            rv = CR.Review(pg.host.ws.root).load()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            rv = None
        for d in docs:
            vs = d["versions"]
            for k in range(len(vs) - 1, 0, -1):
                a, b = vs[k - 1], vs[k]
                left = ""
                if rv is not None:
                    import changereview as CR
                    p = rv.pairs.get(CR.pair_key(a, b))
                    if p is None:
                        left = "not opened"
                    else:
                        dn, n = rv.progress_of(p)
                        left = f"{n - dn} to decide" if n - dn else "all decided"
                it = QListWidgetItem(f"{d['name']}\n{b['label']} against {a['label']}" + (f"  ·  {left}" if left else ""))
                it.setData(Qt.UserRole, (d["id"], a["id"], b["id"]))
                self.versions.addItem(it)
                if pg.sel[0] == d["id"] and pg.sel[2] in (b["id"], None) and pg.sel[1] in (a["id"], None):
                    self.versions.setCurrentItem(it)
        if self.versions.currentItem() is None and self.versions.count():
            self.versions.setCurrentRow(0)

    def pick(self, it):
        di, ai, bi = it.data(Qt.UserRole)
        self.page.open_pair(di, ai, bi)
        self.fill_versions([d for d in self.page.ctx.lib.docs if len(d["versions"]) > 1])

    # -------------------------------------------------------------- the cards
    def fill_cards(self):
        pg = self.page
        while self.col.count():
            w = self.col.takeAt(0).widget()
            if w is not None:
                w.hide(); w.setParent(None)
        self.boxes = {}
        idx = list(pg.shown)
        if not idx:
            self.col.addWidget(D.label("No changes to show." if pg.rows else "Pick a new version on the left.", "muted"))
        for i in idx[:CAP]:
            box = Card(self, i)
            self.col.addWidget(box)
            self.boxes[i] = box
        if len(idx) > CAP:
            self.col.addWidget(D.label(f"Showing {CAP} of {len(idx)}. Decide these, or use the counts above to show fewer.", "muted"))
        self.say_foot()
        self.mark(pg.i)

    def mark(self, i):
        for k, b in self.boxes.items():
            b.setProperty("sel", k == i)
            b.style().unpolish(b); b.style().polish(b)
        b = self.boxes.get(i)
        if b is not None:
            QTimer.singleShot(0, lambda: self.area.ensureWidgetVisible(b, 0, 40))

    def say_foot(self):
        try:
            import reshred as RS
            n = len(RS.Queue(self.page.host.ws.root).load().open_items())
        except Exception:  # noqa: BLE001
            n = 0
        self.foot.setText(f"{n} passage(s) wait in Shred to be shredded again. <a href='q'>Go to the re-shred queue</a>" if n else "")
        self.foot.setVisible(bool(n))

    def to_queue(self, _href=""):
        h = self.page.host
        h.go("assign")
        try:
            return __import__("skqt.reshredbar", fromlist=["x"]).open_next(h.assign_page)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return None

    def decide(self, i, kind):
        """A card's button: select the change (its targets come with it), decide it, then the next one to decide."""
        pg = self.page
        pg.select(i)
        why = "editorial" if kind == "none" and pg.suggest and pg.suggest[i] and pg.suggest[i].get("kind") == "none" else None
        dec = pg.decide_panel.decide(kind, why=why if why else ("no impact" if kind == "none" else None))
        if dec:
            pg.next_open()
            self.fill_versions([d for d in pg.ctx.lib.docs if len(d["versions"]) > 1])
        return dec

    def undo(self, dec_id):
        pg = self.page
        r = pg.decide_panel.undo(dec_id)
        pg.redraw()
        return r


class Card(QFrame):
    def __init__(self, cards, i):
        super().__init__()
        from .comparebar import MAIN, MORE, WORDS, diff_html
        import changereview as CR
        self.setObjectName("changecard"); self.setProperty("card", True)
        pg = cards.page
        r = pg.rows[i]
        decs = pg.review.decisions(pg.pk, r["key"])
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["s"]); v.setSpacing(4)
        where = r.get("section", "")
        head = D.label(f"<b>{WORDS.get(r['kind'], 'Changed')}</b>" + (f" under {html.escape(where)}" if where else ""), None)
        head.setTextFormat(Qt.RichText); v.addWidget(head)
        words = D.label(diff_html(r), None); words.setTextFormat(Qt.RichText); words.setWordWrap(True)
        words.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(words)
        touch = [h for h in (pg.links[i] if i < len(pg.links) else []) if h.get("map")]
        bits = []
        if touch:
            bits.append("Touches " + ", ".join(f"{h['id']} in {h['map']}" for h in touch[:3]) + (" and more" if len(touch) > 3 else ""))
        s = pg.suggest[i] if i < len(pg.suggest) else None
        if s and not decs:
            name = dict((k, t) for k, t, _x in MAIN).get(s["kind"]) or dict(MORE).get(s["kind"], "")
            bits.append(f"Suggested: {name}. {s.get('why', '')}")
        if bits:
            v.addWidget(D.label("  ·  ".join(bits), "muted"))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); v.addLayout(row)
        if decs:
            self.setProperty("done", True)
            for x in decs:
                row.addWidget(D.label(CR.KIND_NAMES[x["kind"]] + (f": {x['target']}" if x.get("target") else "")
                                      + f"  ·  {x.get('who', '')} {x.get('when', '')[:10]}", "muted"))
                row.addWidget(D.button("Undo", "ghost", lambda _=False, did=x["id"]: cards.undo(did)))
        else:
            if s and s.get("kind") in dict(MORE):                 # the suggestion is one of More's: it leads the row
                row.addWidget(D.button(dict(MORE)[s["kind"]], "primary", lambda _=False, k=s["kind"]: cards.decide(i, k),
                                       "The suggestion (Enter takes it on the selected card)"))
            for kind, text, tip in MAIN:
                b = D.button(text, "primary" if s and s.get("kind") == kind else None,
                             lambda _=False, k=kind: cards.decide(i, k), tip)
                row.addWidget(b)
            mb = D.button("More", "ghost", None, "Update our wording, add to a section, remove, context, a submission rule, a task, a note")
            m = QMenu(mb)
            for kind, text in MORE:
                a = m.addAction(text, lambda k=kind: cards.decide(i, k))
                if kind == "rule":
                    a.setVisible("rule" in (pg.tags[i] if i < len(pg.tags) else ()))
                elif kind in ("updates", "new"):
                    a.setEnabled(r["kind"] != "removed")
            mb.setMenu(m)
            row.addWidget(mb)
        row.addStretch(1)
        self.i = i
        self.cards = cards

    def mousePressEvent(self, e):
        self.cards.page.select(self.i)
        super().mousePressEvent(e)
