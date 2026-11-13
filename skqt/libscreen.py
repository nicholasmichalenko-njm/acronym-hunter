"""A library as a full screen (3.49.0): Production > Formatting Standards (3.50.0 adds Quick Parts and Layout on the same
screen). Three panes: the library's categories with their counts; the category's items (name, effort types, status,
version, where each came from), filtered by effort type, status and words; the selected item's picture and every
value it holds, to edit one by one.

Each item has a name you choose, effort-type tags, a status (Draft, Approved, Retired) and versions. Import from a
Word file lands each item in its own category, all at once or not at all. The first time the libraries open, the
standards on this PC become library items (libconvert); nothing is deleted. Until Effort Profiles arrive (3.51.0),
Put in a standard... carries an item into the Company Standards (Default), a profile or an effort type."""
import html
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
                               QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QSplitter, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

import diag
import libcats as LC
import libconvert as CV
import libimport as LI
import libpreview as LP
import templatelib as TL
from . import design as D
from .importbrowser import effort_type_names
from .adaptive import FlowLayout
from .itempicture import ItemPicture
from .libedit import Editor

STATUS_FILTERS = (("active", "Draft and approved"), ("draft", "Draft"), ("approved", "Approved"), ("retired", "Retired"), ("all", "Every status"))
STATUS_WORDS = dict(TL.STATUSES)


class LibraryScreen(QWidget):
    def __init__(self, host, library="formatting"):
        super().__init__()
        self.host, self.library = host, library
        self.lib = TL.Library(host.config_dir)
        self.names = {}
        self.pending = None                              # values edited and not saved yet
        self.converted = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(D.SPACE["m"])
        self.import_btn = D.button("Import from a Word file...", "primary", lambda: self.import_file(),
                                   "Read a template or Word document (only read, never written); its items land in their categories")
        more = QToolButton(); more.setText("More"); more.setPopupMode(QToolButton.InstantPopup)
        self.more_menu = QMenu(more); more.setMenu(self.more_menu)
        self.more_menu.aboutToShow.connect(self.fill_more)
        top = D.Card("Library", "Import a template or Word document and each item lands in its category. Select an item to see "
                     "and edit every value it holds.", actions=(self.import_btn, more), key=True)
        fr = QHBoxLayout(); fr.setSpacing(D.SPACE["s"])
        fr.addWidget(D.label("Effort type", "label", wrap=False))
        self.et_box = QComboBox(); self.et_box.currentIndexChanged.connect(lambda _i: self.fill())
        fr.addWidget(self.et_box)
        fr.addWidget(D.label("Status", "label", wrap=False))
        self.st_box = QComboBox()
        for k, t in STATUS_FILTERS:
            self.st_box.addItem(t, k)
        self.st_box.currentIndexChanged.connect(lambda _i: self.fill())
        fr.addWidget(self.st_box)
        self.search = QLineEdit(); self.search.setPlaceholderText("Find by name, where it came from or what it is")
        self.search.textChanged.connect(lambda _t: self.fill())
        fr.addWidget(self.search, 1)
        top.body.addLayout(fr)
        self.note = D.label("", "muted"); top.body.addWidget(self.note)
        outer.addWidget(top)
        sp = QSplitter(Qt.Horizontal); outer.addWidget(sp, 1)
        self.cats = QListWidget(); self.cats.setMinimumWidth(200)
        self.cats.currentRowChanged.connect(lambda _r: self.fill())
        sp.addWidget(self.cats)
        mid = QWidget(); mv = QVBoxLayout(mid); mv.setContentsMargins(0, 0, 0, 0)
        self.cols = ["Name", "Effort types", "Status", "Version", "From"] + (["Pages"] if library == "quickparts" else [])
        self.t = QTableWidget(0, len(self.cols)); self.t.setHorizontalHeaderLabels(self.cols)
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QTableWidget.SelectRows)
        self.t.setSelectionMode(QAbstractItemView.ExtendedSelection); self.t.setEditTriggers(QTableWidget.NoEditTriggers)
        self.t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.t.setColumnWidth(1, 170); self.t.setColumnWidth(2, 80); self.t.setColumnWidth(3, 64); self.t.setColumnWidth(4, 150)
        self.t.currentCellChanged.connect(lambda *_a: self.show_item())
        mv.addWidget(self.t, 1)
        arw = QWidget(); ar = FlowLayout(arw, D.SPACE["s"]); mv.addWidget(arw)      # wraps on a narrow window
        self.row_actions = arw
        ar.addWidget(D.button("Rename...", None, lambda: self.rename()))
        ar.addWidget(D.button("Effort types...", None, lambda: self.tag_effort_types(), "The effort types the selected items are for"))
        st = QToolButton(); st.setText("Status"); st.setPopupMode(QToolButton.InstantPopup)
        sm = QMenu(st)
        for k, t in TL.STATUSES:
            sm.addAction(t).triggered.connect(lambda _c=False, kk=k: self.set_status(kk))
        st.setMenu(sm); ar.addWidget(st)
        ar.addWidget(D.button("Compare...", None, lambda: self.compare(), "Two selected items side by side, or the selected item "
                              "and its previous version"))
        ar.addWidget(D.button("Put in a standard...", None, lambda: self.put_in(), "Until Effort Profiles arrive: carry the selected "
                              "items into the Company Standards (Default), a profile or an effort type"))
        ar.addWidget(D.button("Take out", "ghost", lambda: self.take_out()))
        self.draw_btn = QToolButton(); self.draw_btn.setText("Draw with Word"); self.draw_btn.setPopupMode(QToolButton.InstantPopup)
        self.draw_btn.setToolTip("Word on this PC draws items as they will print (Quick Parts' pages are counted in the same "
                                 "pass). Each picture is kept until the item changes.")
        dm = QMenu(self.draw_btn)
        dm.addAction("Draw the selected items").triggered.connect(lambda: self.draw_word())
        dm.addAction("Draw every item in this category").triggered.connect(lambda: self.draw_word(every=True))
        self.draw_btn.setMenu(dm)
        ar.addWidget(self.draw_btn)
        self.extra_actions(ar)
        ar.addStretch(1)
        sp.addWidget(mid)
        right = QSplitter(Qt.Vertical)
        self.picture = ItemPicture(); self.picture.setMinimumSize(240, 200)
        right.addWidget(self.picture)
        ew = QWidget(); ev = QVBoxLayout(ew); ev.setContentsMargins(0, 0, 0, 0)
        self.ed_head = D.label("", "title"); ev.addWidget(self.ed_head)
        self.editor = Editor(self.edited, self.host.status); ev.addWidget(self.editor, 1)
        ebw = QWidget(); eb = FlowLayout(ebw, D.SPACE["s"]); ev.addWidget(ebw)
        self.save_btn = D.button("Save changes", "primary", lambda: self.save_changes(), "Keep the edits in this version")
        self.ver_btn = D.button("Save as a new version", None, lambda: self.save_version(), "Keep the edits as the next version; "
                                "this one stays as it is")
        self.revert_btn = D.button("Undo changes", "ghost", lambda: self.show_item())
        for b in (self.save_btn, self.ver_btn, self.revert_btn):
            b.setEnabled(False); eb.addWidget(b)
        eb.addStretch(1)
        right.addWidget(ew)
        right.setSizes([260, 460])
        sp.addWidget(right)
        sp.setSizes([220, 560, 520])
        self.shown = []

    # ------------------------------------------------------------------ filling
    def refresh(self):
        if self.converted is None:                      # the first time the libraries open: the standards become items
            try:
                self.converted = CV.ensure(self.host.config_dir) or {}
                if self.converted:
                    self.lib.load()
                    self.note.setText(f"Your standards are now library items: {self.converted['new'] + self.converted['version']} "
                                      "item(s) from the Company Standards (Default), profiles and effort types. The standards themselves are unchanged.")
            except Exception:  # noqa: BLE001  the libraries still open; More > Bring in my standards again retries
                diag.error("library_convert", "The standards could not be converted to library items")
                self.converted = {}
        self.lib.fresh()
        self.names = dict(effort_type_names(self.host.config_dir))
        cur = self.et_box.currentData()
        self.et_box.blockSignals(True); self.et_box.clear()
        self.et_box.addItem("Every effort type", None)
        for eid, nm in self.names.items():
            self.et_box.addItem(nm, eid)
        self.et_box.addItem("Not tagged", "")
        i = self.et_box.findData(cur)
        self.et_box.setCurrentIndex(i if i >= 0 else 0)
        self.et_box.blockSignals(False)
        self.fill_cats()

    def library_changed(self):
        self.lib.load()
        self.fill_cats()

    def filters(self):
        st = self.st_box.currentData()
        return self.et_box.currentData(), (None if st in ("active", "all") else st), st == "active"

    def fill_cats(self):
        cur = self.cats.currentItem().data(Qt.UserRole) if self.cats.currentItem() else None
        eid, st, active = self.filters()
        self.cats.blockSignals(True); self.cats.clear()
        for k, t in LC.categories(self.lib, self.library):
            if k in getattr(self, "moved", ()) and k != getattr(self, "reveal", None):   # 3.90.0: covers live in Parts
                continue
            n = sum(1 for i in LC.items_in(self.lib, self.library, k, eid, st) if not (active and LC.status(i) == "retired"))
            it = QListWidgetItem(f"{t} ({n})"); it.setData(Qt.UserRole, k); self.cats.addItem(it)
        self.cats.blockSignals(False)
        row = next((r for r in range(self.cats.count()) if self.cats.item(r).data(Qt.UserRole) == cur), 0)
        self.cats.setCurrentRow(row if self.cats.count() else -1)
        self.fill()

    def category(self):
        it = self.cats.currentItem()
        return it.data(Qt.UserRole) if it else None

    def select_category(self, key):
        for r in range(self.cats.count()):
            if self.cats.item(r).data(Qt.UserRole) == key:
                self.cats.setCurrentRow(r)
                return True
        return False

    def fill(self):
        if self.cats.count() == 0:
            self.shown = []
        else:
            eid, st, active = self.filters()
            self.shown = [i for i in LC.items_in(self.lib, self.library, self.category(), eid, st, self.search.text())
                          if not (active and LC.status(i) == "retired")]
        cur = self.current()
        self.t.blockSignals(True)
        self.t.setRowCount(0)
        for i in self.shown:
            r = self.t.rowCount(); self.t.insertRow(r)
            vals = (self.lib.shown_name(i), LC.effort_type_words(i, self.names), STATUS_WORDS[LC.status(i)], f"v{int(i.get('version') or 1)}",
                    i.get("source") or "") + ((self.pages_words(i),) if self.library == "quickparts" else ())
            for c, txt in enumerate(vals):
                cell = QTableWidgetItem(txt); cell.setData(Qt.UserRole, i["id"]); cell.setToolTip(i.get("summary") or txt)
                if c == 2 and LC.status(i) != "approved":
                    cell.setForeground(D.color("warn" if LC.status(i) == "draft" else "muted"))
                self.t.setItem(r, c, cell)
        self.t.blockSignals(False)
        ids = [i["id"] for i in self.shown]
        if self.shown:
            self.t.setCurrentCell(ids.index(cur["id"]) if cur and cur["id"] in ids else 0, 0)
        self.show_item()

    def current(self):
        r = self.t.currentRow()
        it = self.t.item(r, 0) if r >= 0 else None
        return self.lib.get(it.data(Qt.UserRole)) if it else None

    def selected_ids(self):
        rows = sorted({i.row() for i in self.t.selectionModel().selectedRows()}) if self.t.selectionModel() else []
        ids = [self.t.item(r, 0).data(Qt.UserRole) for r in rows if self.t.item(r, 0)]
        cur = self.current()
        return ids or ([cur["id"]] if cur else [])

    def select(self, iid):
        """Select an item (switching category when needed)."""
        it = self.lib.get(iid)
        if it is None:
            return False
        self.select_category(LC.place(self.lib, it)[1])
        for r in range(self.t.rowCount()):
            if self.t.item(r, 0).data(Qt.UserRole) == iid:
                self.t.setCurrentCell(r, 0)
                return True
        return False

    # ------------------------------------------------------------------ the selected item
    def show_item(self):
        it = self.current()
        self.pending = None
        for b in (self.save_btn, self.ver_btn, self.revert_btn):
            b.setEnabled(False)
        if it is None:
            self.picture.show_item(None); self.editor.set_item(self.lib, None, None); self.ed_head.setText("")
            return
        vals = self.lib.values(it) or {}
        self.ed_head.setText(f"{self.lib.shown_name(it)}: every value")
        self.picture.show_item(self.picture_of(it, vals))
        self.editor.set_item(self.lib, it, vals)

    def edited(self, values):
        it = self.current()
        if it is None:
            return
        self.pending = values
        for b in (self.save_btn, self.ver_btn, self.revert_btn):
            b.setEnabled(True)
        self.picture.show_item(dict(self.picture_of(it, values), png=""))      # edits not saved: the sketch shows them

    def picture_of(self, it, vals):
        """What the picture pane draws: Word's picture when it drew this item as it is now, else the sketch."""
        d = {"kind": it["kind"], "name": self.lib.base_of(it), "values": vals, "summary": it.get("summary") or "",
             "png": LP.cached(self.lib, it), "word_can": LP.word_can(it)}
        if it["kind"] in ("cover", "backer", "title") and vals.get("file"):
            try:
                with open(self.lib.source_path(vals["file"]), "rb") as f:
                    d["page_bytes"] = f.read()
            except OSError:
                pass
        return d

    def pages_words(self, i):
        return (f"{i['pages']} ({'measured' if i.get('pages_how') == 'measured' else 'typed'})") if i.get("pages") else ""

    def extra_actions(self, row):
        """Buttons a library adds to the row under its list."""

    def draw_word(self, ids=None, every=False, fn=None):
        """Word draws the selected items (every: the category's) in the background, one Word job at a time. Returns the
        job, or None (and says why)."""
        from . import qpjobs
        ids = ids if ids is not None else ([i["id"] for i in self.shown] if every else self.selected_ids())
        ids = [i for i in ids if LP.word_can(self.lib.get(i)) and not (LP.cached(self.lib, self.lib.get(i)) and self.lib.get(i)["kind"] != "quickpart")]
        if not ids:
            self.host.status("Word has drawn these already, or the app draws this kind of item.")
            return None
        job = qpjobs.draw(self.host.config_dir, ids, after=self.drawn, fn=fn)
        self.host.status(f"Word is drawing {len(ids)} item(s) in the background." if job else qpjobs.why_not())
        return job

    def drawn(self, pics):
        self.lib.load()
        self.fill()
        n = sum(1 for v in (pics or {}).values() if isinstance(v, str) and v.endswith(".png"))
        bad = [v for v in (pics or {}).values() if not (isinstance(v, str) and v.endswith(".png"))]
        self.host.toast(f"Word drew {n} item(s)." + (f" {len(bad)} not: {bad[0]}" if bad else ""))

    def save_changes(self):
        it = self.current()
        if it is None or self.pending is None:
            return False
        ok = self.lib.update(it["id"], self.pending)
        self.host.status(f"Saved: {self.lib.shown_name(it)}.")
        diag.activity("library_item_edited")
        self.fill()
        return ok

    def save_version(self, label=None):
        it = self.current()
        if it is None or self.pending is None:
            return None
        if label is None:
            label, ok = QInputDialog.getText(self, "Save as a new version", "A label for the new version (optional), for example "
                                             "11 pt body:")
            if not ok:
                return None
        new, state = self.lib.save_version(it["id"], self.pending, label=label)
        if state == "version":
            new["status"] = "draft"
            self.lib.save()
        self.fill(); self.select(new["id"])
        self.host.status(f"{self.lib.shown_name(new)}" + (" kept as a new version (Draft)." if state == "version" else
                                                          " already holds these values."))
        return new

    # ------------------------------------------------------------------ actions on the selected items
    def rename(self, name=None):
        it = self.current()
        if it is None:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename", "Name:", text=it["name"])
            if not ok:
                return False
        ok = self.lib.rename(it["id"], name)
        self.fill()
        return ok

    def tag_effort_types(self, ets=None, run=True):
        """The effort types the selected items are for. ets: [LC.ALL] or ids (tests). Returns how many changed."""
        ids = self.selected_ids()
        if not ids:
            return 0
        if ets is None:
            d = QDialog(self); d.setWindowTitle("Effort types"); v = QVBoxLayout(d)
            v.addWidget(D.label(f"The effort types {len(ids)} item(s) are for. A profile for an effort type offers the items tagged "
                                "for it.", "muted"))
            have = LC.effort_types(self.lib.get(ids[0]))
            every = QCheckBox("Every effort type"); every.setChecked(LC.ALL in have); v.addWidget(every)
            boxes = {}
            for eid, nm in self.names.items():
                cb = QCheckBox(nm); cb.setChecked(eid in have); v.addWidget(cb); boxes[eid] = cb
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if not run or d.exec() != QDialog.Accepted:
                return 0
            ets = [LC.ALL] if every.isChecked() else [e for e, cb in boxes.items() if cb.isChecked()]
        n = LC.set_effort_types(self.lib, ids, ets)
        self.fill_cats()
        return n

    def set_status(self, st):
        n = LC.set_status(self.lib, self.selected_ids(), st)
        self.fill_cats()
        self.host.status(f"{n} item(s) now {STATUS_WORDS.get(st, st)}.")
        return n

    def compare(self, run=True):
        """Two selected items, or the selected item and its previous version: what differs. Returns the rows."""
        ids = self.selected_ids()
        if len(ids) >= 2:
            a, b = ids[0], ids[1]
        elif ids:
            fam = self.lib.family(ids[0])
            older = [x for x in fam if int(x.get("version") or 1) < int(self.lib.get(ids[0]).get("version") or 1)]
            if not older:
                self.host.status("Select two items, or an item with an earlier version, to compare.")
                return []
            a, b = older[0]["id"], ids[0]
        else:
            return []
        rows = self.lib.compare(a, b)
        na, nb = self.lib.shown_name(self.lib.get(a)), self.lib.shown_name(self.lib.get(b))
        body = ("<p>The same values.</p>" if not rows else
                f"<table cellpadding=4><tr><th align=left>What</th><th align=left>{html.escape(na)}</th><th align=left>{html.escape(nb)}</th></tr>"
                + "".join(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(x))}</td><td>{html.escape(str(y))}</td></tr>"
                          for k, x, y in rows[:200]) + "</table>")
        if run:
            d = QDialog(self); d.setWindowTitle(f"Compare {na} and {nb}"); d.resize(680, 520)
            v = QVBoxLayout(d); tb = QTextBrowser(); tb.setHtml(body); v.addWidget(tb)
            v.addWidget(D.button("Close", "ghost", d.accept)); d.exec()
        return rows

    def targets(self):
        """[(key, words)] the standards an item can go into: the Company Standards (Default), each profile, each effort type."""
        import prodrules as PRL
        data = PRL.load(self.host.config_dir)
        return ([("company", "Company Standards (Default)")] + [("type:" + t["id"], f"Profile: {t['name']}") for t in data["types"]]
                + [("etype:" + e["id"], f"Effort type: {e['name']}") for e in data.get("effort_types", [])])

    def put_in(self, target=None):
        """Carries the selected items into a standard (until Effort Profiles arrive). Returns what changed, in words."""
        import prodrules as PRL
        ids = self.selected_ids()
        if not ids:
            return []
        if target is None:
            tg = self.targets()
            pick, ok = QInputDialog.getItem(self, "Put in a standard", "Put the selected item(s) into:", [t for _k, t in tg], 0, False)
            if not ok:
                return []
            target = next(k for k, t in tg if t == pick)
        ps = getattr(self.host, "prodstd_page", None)
        if ps is not None and getattr(ps, "dirty", False):
            ps.save(quiet=True)                         # what Production Standards was editing is kept first
        data = PRL.load(self.host.config_dir)
        if target == "company":
            work = data["company"]
        elif target.startswith("type:"):
            work = PRL.type_of(data, target[5:])
        else:
            work = PRL.effort_type_of(data, target[6:])
        if work is None:
            return []
        said = [s for s in (TL.use_in_standard(self.lib, iid, work) for iid in ids) if s]
        PRL.save(self.host.config_dir, data)
        self.host.status(f"Put in the standard: {', '.join(said) or 'nothing'}.")
        diag.activity("library_put_in_standard", n=len(said))
        return said

    def take_out(self, ask=True):
        ids = self.selected_ids()
        if not ids:
            return 0
        if ask and QMessageBox.question(self, "Take out", f"Take {len(ids)} item(s) out of the library? Standards that carry them "
                                        "keep their own copy. Retired keeps an item without offering it.") != QMessageBox.Yes:
            return 0
        n = 0
        with self.lib.transaction():
            for iid in ids:
                n += bool(self.lib.remove(iid))
        for iid in ids:
            try:
                os.remove(os.path.join(self.lib.root, "items", iid + ".json"))
            except OSError:
                pass
        self.fill_cats()
        return n

    # ------------------------------------------------------------------ import, undo, convert
    def import_file(self, path=None, run=True):
        from PySide6.QtWidgets import QFileDialog
        from .importbrowser import ImportBrowser
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import from a template or Word document (it is only read)", os.path.expanduser("~"),
                                                  "Word and themes (*.dotx *.dotm *.docx *.docm *.thmx)")
            if not path:
                return None
        d = ImportBrowser(self, path)
        lk = {"formatting": "lib:formatting", "quickparts": "lib:quickparts", "layout": "lib:layout"}[self.library]
        d.select(lk)
        if run:
            d.exec()
            self.library_changed()
        return d

    def fill_more(self):
        m = self.more_menu
        m.clear()
        m.addAction("Bring in my standards again").triggered.connect(lambda: self.convert_again())
        um = m.addMenu("Undo an import")
        imps = LI.imports(self.lib)
        for rid, fn, at in imps[:12]:
            um.addAction(f"{fn} ({at.replace('T', ' ')})").triggered.connect(lambda _c=False, r=rid: self.undo_import(r))
        um.setEnabled(bool(imps))

    def undo_import(self, rid):
        n = LI.undo(self.lib, rid)
        self.library_changed()
        self.host.status(f"Import taken back: {max(n, 0)} item(s)." if n >= 0 else "That import's record is not on this PC.")
        return n

    def convert_again(self):
        try:
            rep = CV.convert(self.host.config_dir, self.lib)
        except Exception:  # noqa: BLE001
            diag.error("library_convert", "The standards could not be converted to library items")
            self.host.status("The standards could not be brought in. Nothing changed; the log has the details.")
            return None
        self.library_changed()
        self.host.status(f"From your standards: {rep['new']} new item(s), {rep['version']} new version(s), {rep['same']} already here.")
        return rep


class FormattingStandardsPage(LibraryScreen):
    """3.98.0: paragraph and character styles are on Styles (one home); a style opened from there with Every value...
    shows here with its every value, its category shown only while it is open."""
    moved = ("para_styles", "char_styles")

    def __init__(self, host):
        super().__init__(host, "formatting")
        self.reveal = None
        self.moved_note = D.label("Paragraph and character styles are on Styles (the first tab): right-click a style there, "
                                  "Every value..., to see and change every value here.", "muted")
        self.layout().insertWidget(1, self.moved_note)

    def select_category(self, key):
        if key in self.moved and key != self.reveal:
            self.reveal = key
            self.fill_cats()
        return super().select_category(key)

    def select(self, iid):
        it = self.lib.get(iid)
        if it is not None and LC.place(self.lib, it)[1] in self.moved:
            self.select_category(LC.place(self.lib, it)[1])
        return super().select(iid)

    def extra_actions(self, row):
        row.addWidget(D.button("Allowed styles...", None, lambda: self.style_rules(),       # 3.69.0: from Production Standards
                               "The styles a finished document may use, what Fix a Copy does to the rest, and the styles "
                               "the rules read"))

    def style_rules(self, modal=True):
        from .stdeditor import GlobalStore, window
        dlg = window(self.host, GlobalStore(self.host.config_dir), ["styles", "style_roles"], "Allowed styles and the styles the rules read")
        if modal:
            dlg.exec()
        return dlg


class QuickPartsPage(LibraryScreen):
    """3.50.0: every Quick Part by its numbered category; its gallery, behavior and the pages it fills."""
    def __init__(self, host):
        super().__init__(host, "quickparts")

    def extra_actions(self, row):
        row.addWidget(D.button("Category...", None, lambda: self.set_category(), "Move the selected Quick Parts to another "
                               "category (01 Front matter, 05 Callouts, ...)"))
        row.addWidget(D.button("Pages...", None, lambda: self.type_pages(), "Type the pages a Quick Part fills (Draw with Word "
                               "counts them)"))

    def set_category(self, cat=None):
        ids = self.selected_ids()
        if not ids:
            return 0
        if cat is None:
            cats = [c for c, _t in LC.categories(self.lib, "quickparts") if c != LC.NO_CATEGORY]
            cat, ok = QInputDialog.getItem(self, "Category", "Category (type a new one, for example 07 Graphics):", cats, 0, True)
            if not ok:
                return 0
        cat = " ".join(str(cat).split())
        n = 0
        with self.lib.transaction():
            for iid in ids:
                v = dict(self.lib.values(self.lib.get(iid)) or {})
                if v.get("category") != cat:
                    v["category"] = cat
                    self.lib.update(iid, v)
                    n += 1
        self.fill_cats(); self.select_category(cat or LC.NO_CATEGORY)
        return n

    def type_pages(self, pages=None):
        it = self.current()
        if it is None:
            return False
        if pages is None:
            pages, ok = QInputDialog.getInt(self, "Pages", f"Pages {it['name']} fills (0 takes them off):", int(it.get("pages") or 1), 0, 500)
            if not ok:
                return False
        ok = self.lib.set_pages(it["id"], pages or None, "typed")
        self.fill()
        return ok


class LayoutPage(LibraryScreen):
    """3.50.0: headers and footers, sections, table looks, captions and the TOC. 3.90.0 (decision 13): covers, title
    pages and back covers moved to Section designs; headers, footers and page setup stay here."""
    moved = ("covers", "titles", "backers")

    def __init__(self, host):
        super().__init__(host, "layout")
        self.moved_note = D.label("Covers, title pages and back covers are in Parts (the next tab). Headers, "
                                  "footers and page setup stay here.", "muted")
        self.layout().insertWidget(1, self.moved_note)


class PageLayoutPage(FormattingStandardsPage):
    """4.28.0 (answer 21): Page Layout. Formatting and Layout are one screen with one list at the left: the page first
    (page setups, pagination, headers and footers, sections, the contents), then the text and tables (theme, fonts,
    heading numbering, lists, table styles, table looks, captions). Each row knows which library holds it; the items,
    the import and the pictures are the same as before. Styles are on Styles; covers and title pages on Quick Parts."""
    moved = FormattingStandardsPage.moved + LayoutPage.moved
    GROUPS = (("The page", (("formatting", "page_setup"), ("formatting", "pagination"), ("layout", "hf"), ("layout", "sections"), ("layout", "toc"))),
              ("Text and tables", (("formatting", "theme"), ("formatting", "fonts"), ("formatting", "heading_numbering"), ("formatting", "lists"),
                                   ("formatting", "table_styles"), ("layout", "table_looks"), ("layout", "captions"))))
    LIB = Qt.UserRole + 1

    def __init__(self, host):
        self._library = "formatting"
        super().__init__(host)
        self.moved_note.setText("Paragraph and character styles are on Styles; covers, title pages and back covers are on Quick Parts. "
                                "Right-click an item to rename it, set its status, compare it or draw it with Word.")
        self.row_actions.hide(); self.ver_btn.hide(); self.revert_btn.hide()     # one Save; the rest on a right-click
        self.t.setContextMenuPolicy(Qt.CustomContextMenu); self.t.customContextMenuRequested.connect(self.row_menu)

    @property
    def library(self):
        it = self.cats.currentItem() if hasattr(self, "cats") else None
        return (it.data(self.LIB) if it is not None else None) or self._library

    @library.setter
    def library(self, v):
        self._library = v

    def row_menu(self, pos=None, run=True):
        """One Save on the face; everything else about the selected items is on a right-click."""
        m = QMenu(self)
        m.addAction("Rename...", lambda: self.rename())
        m.addAction("Effort types...", lambda: self.tag_effort_types())
        sm = m.addMenu("Status")
        for k, t in TL.STATUSES:
            sm.addAction(t, lambda kk=k: self.set_status(kk))
        m.addAction("Compare...", lambda: self.compare())
        m.addAction("Put in a standard...", lambda: self.put_in())
        m.addAction("Take out", lambda: self.take_out())
        m.addSeparator()
        m.addAction("Draw the selected items with Word", lambda: self.draw_word())
        m.addAction("Draw every item in this category with Word", lambda: self.draw_word(every=True))
        m.addAction("Allowed styles...", lambda: self.style_rules())
        m.addSeparator()
        a = m.addAction("Save as a new version", lambda: self.save_version()); a.setEnabled(self.ver_btn.isEnabled())
        a = m.addAction("Undo changes", lambda: self.show_item()); a.setEnabled(self.revert_btn.isEnabled())
        for a in m.actions()[:6]:
            a.setEnabled(bool(self.selected_ids()))
        if run:
            m.exec(self.t.viewport().mapToGlobal(pos) if pos is not None else self.cursor().pos())
        return m

    def fill_cats(self):
        cur = self.category()
        eid, st, active = self.filters()
        titles = {(lb, k): t for lb in ("formatting", "layout") for k, t in LC.categories(self.lib, lb)}
        groups = [(g, list(rows)) for g, rows in self.GROUPS]
        listed = {r for _g, rows in groups for r in rows}
        for lb, k in titles:                              # a category added later still shows; a style opened from Styles too
            if (lb, k) not in listed and (k not in self.moved or k == self.reveal):
                groups[-1][1].append((lb, k))
        self.cats.blockSignals(True); self.cats.clear()
        for g, rows in groups:
            head = QListWidgetItem(g.upper()); head.setFlags(Qt.NoItemFlags); head.setForeground(D.color("muted")); self.cats.addItem(head)
            for lb, k in rows:
                if (lb, k) not in titles:
                    continue
                n = sum(1 for i in LC.items_in(self.lib, lb, k, eid, st) if not (active and LC.status(i) == "retired"))
                it = QListWidgetItem(f"{titles[(lb, k)]} ({n})"); it.setData(Qt.UserRole, k); it.setData(self.LIB, lb); self.cats.addItem(it)
        self.cats.blockSignals(False)
        row = next((r for r in range(self.cats.count()) if cur and self.cats.item(r).data(Qt.UserRole) == cur), 1)
        self.cats.setCurrentRow(row if self.cats.count() > 1 else -1)
        self.fill()
