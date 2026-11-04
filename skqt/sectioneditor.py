"""A document section's page setup and contents (3.45.0), for Document sections: the page setup the section follows,
and the ordered components at its start (response elements, Quick Parts, placeholders for authors), with buttons to
build its header or footer as a table. Used on each built-in section and, with a section picker, on Sections in order
for every section, your own included. The values are the standard's (pagination parts' "setup", section_contents).
3.48.0: the Library list beside the contents (response elements, this standard's Quick Parts, the template library's
Quick Parts) drags onto the section; a template library Quick Part comes into the standard as it lands. The contents
reorder by dragging too."""
import json

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFormLayout, QHBoxLayout, QInputDialog, QListWidget,
                               QListWidgetItem, QVBoxLayout, QWidget)

import sectioncontents as SC
from partdesigns import part_of
from . import design as D


MIME = "application/x-stationkeeper-section-item"


class LibraryList(QListWidget):
    """What can go in a section, to drag: each row carries what it puts in."""
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def mimeData(self, items):
        md = QMimeData()
        md.setData(MIME, json.dumps([it.data(Qt.UserRole) for it in items]).encode("utf-8"))
        return md

    def mimeTypes(self):
        return [MIME]


class ContentsList(QListWidget):
    """The section's contents: takes library rows dropped on it, and reorders by dragging its own rows."""
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)

    def mimeTypes(self):
        return [MIME]

    def mimeData(self, items):
        md = QMimeData()
        md.setData(MIME, json.dumps([{"move": self.row(it)} for it in items]).encode("utf-8"))
        return md

    def _ok(self, e):
        return e.mimeData().hasFormat(MIME) and self.isEnabled()

    def dragEnterEvent(self, e):
        e.acceptProposedAction() if self._ok(e) else e.ignore()

    def dragMoveEvent(self, e):
        e.acceptProposedAction() if self._ok(e) else e.ignore()

    def dropEvent(self, e):
        if not self._ok(e):
            e.ignore()
            return
        it = self.itemAt(e.position().toPoint())
        at = self.row(it) if it is not None else self.count()
        self.editor.drop(json.loads(bytes(e.mimeData().data(MIME)).decode("utf-8")), at)
        e.setDropAction(Qt.CopyAction)
        e.accept()


class SectionEditor(QWidget):
    def __init__(self, page, key=None):
        super().__init__()
        self.page, self.fixed = page, key
        self.key = key
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        f = QFormLayout(); v.addLayout(f)
        self.pick = QComboBox()
        if key is None:
            self.pick.currentIndexChanged.connect(lambda _i: self.show_key(self.pick.currentData()))
            f.addRow("Section", self.pick)
        self.setup = QComboBox()
        self.setup.currentIndexChanged.connect(lambda _i: self.write_setup())
        f.addRow("Page setup", self.setup)
        self.note = D.label("", "muted"); v.addWidget(self.note)
        both = QHBoxLayout(); v.addLayout(both)
        self.list = ContentsList(self); self.list.setMaximumHeight(170)
        both.addWidget(self.list, 3)
        lib = QVBoxLayout(); both.addLayout(lib, 2)
        lib.addWidget(D.label("Library: drag onto the section", "label"))
        self.library = LibraryList(); self.library.setMaximumHeight(150)
        self.library.itemDoubleClicked.connect(lambda it: self.drop([it.data(Qt.UserRole)], self.list.count()))
        lib.addWidget(self.library)
        row = QHBoxLayout(); v.addLayout(row)
        self.add_btns = [D.button("+ Element...", None, lambda: self.add_element(), "A table of contents, list, acronyms or another response element"),
                         D.button("+ Quick Part...", None, lambda: self.add_quickpart(), "One of this standard's Quick Parts"),
                         D.button("+ Placeholder...", None, lambda: self.add_placeholder(), "A heading and the pages authors fill")]
        for b in self.add_btns:
            row.addWidget(b)
        self.up_btn = D.button("Up", "ghost", lambda: self.move(-1)); row.addWidget(self.up_btn)
        self.down_btn = D.button("Down", "ghost", lambda: self.move(1)); row.addWidget(self.down_btn)
        self.del_btn = D.button("Take out", "ghost", lambda: self.remove()); row.addWidget(self.del_btn)
        row.addStretch(1)
        if key is None:
            hb = QHBoxLayout(); v.addLayout(hb)
            hb.addWidget(D.button("Build its header as a table...", None, lambda: self.build("header")))
            hb.addWidget(D.button("Build its footer as a table...", None, lambda: self.build("footer")))
            hb.addStretch(1)
        self.fill()

    # ---- state
    def work(self):
        return self.page.work or {}

    def fill(self):
        """The section list (picker), the page setups, the contents, from what is being edited."""
        if self.fixed is None:
            keep = self.pick.currentData() or self.key
            self.pick.blockSignals(True); self.pick.clear()
            for p in (self.work().get("pagination") or {}).get("parts") or []:
                if p.get("key"):
                    self.pick.addItem(f"{p.get('name') or p['key']} ({p['key']})", p["key"])
            i = self.pick.findData(keep)
            self.pick.setCurrentIndex(i if i >= 0 else 0)
            self.pick.blockSignals(False)
            self.key = self.pick.currentData()
        self.show_key(self.key)

    def show_key(self, key):
        self.key = key
        part = part_of(self.work(), key) or {}
        self.setup.blockSignals(True); self.setup.clear()
        self.setup.addItem("By orientation (portrait or landscape)", "")
        for k, s in (self.work().get("page_setups") or {}).items():
            self.setup.addItem(f"{(s or {}).get('name') or k} ({k})", k)
        i = self.setup.findData(part.get("setup") or "")
        self.setup.setCurrentIndex(max(0, i))
        self.setup.blockSignals(False)
        self.setup.setEnabled(bool(part))
        kept = key in SC.NO_CONTENTS
        for w in self.add_btns + [self.up_btn, self.down_btn, self.del_btn, self.list, self.library]:
            w.setEnabled(bool(key) and not kept)
        self.fill_library()
        self.note.setText("A kept page: it holds no components." if kept else
                          "What this section starts with, in order. Make templates puts them at its start." if key else "")
        self.list.clear()
        for r in SC.items(self.work(), key) if key else []:
            it = QListWidgetItem(SC.label(r)); it.setData(Qt.UserRole, r); self.list.addItem(it)

    def rows(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def save_rows(self, rows, select=None):
        SC.set_items(self.page.work, self.key, rows)
        self.page.changed()
        self.show_key(self.key)
        if select is not None and 0 <= select < self.list.count():
            self.list.setCurrentRow(select)

    def write_setup(self):
        part = part_of(self.page.work, self.key)
        if part is None:
            return
        k = self.setup.currentData() or ""
        if k:
            part["setup"] = k
        else:
            part.pop("setup", None)
        self.page.changed()

    # ---- the library to drag from
    def _template_library(self):
        try:
            import templatelib as TL
            return TL.Library(self.page.host.config_dir)
        except Exception:  # noqa: BLE001  no library on this PC yet: elements and the standard's Quick Parts still list
            return None

    def fill_library(self):
        """Response elements, this standard's Quick Parts, then the template library's Quick Parts not in the standard."""
        import responseelements as RE
        self.library.clear()

        def add(text, payload, tip=""):
            it = QListWidgetItem(text); it.setData(Qt.UserRole, payload)
            if tip:
                it.setToolTip(tip)
            self.library.addItem(it)
        for e in RE.builtins().get("elements", []):
            if e.get("source") not in ("cover", "backer"):
                add(f"{e['name']} (element)", {"kind": "element", "id": e["id"], "title": e.get("name", "")})
        mine = [e.get("name") for e in ((self.work().get("quick_parts") or {}).get("entries") or []) if e.get("name")]
        for n in mine:
            add(f"{n} (Quick Part)", {"kind": "quickpart", "name": n})
        lib = self._template_library()
        for i in (lib.shelf("quickpart") if lib else []):
            name = i.get("base_name") or i.get("name")
            if name and name not in mine:
                add(f"{name} (Quick Part, template library)", {"kind": "libquickpart", "iid": i["id"], "name": name},
                    "Comes into this standard's Quick Parts when it lands")

    def drop(self, payloads, at=None):
        """Rows dropped on the contents at position at: library rows go in (a template library Quick Part comes into the
        standard first); the contents' own rows move. Returns the rows put in."""
        rows = self.rows()
        at = len(rows) if at is None else max(0, min(int(at), len(rows)))
        moves = [p["move"] for p in payloads if isinstance(p, dict) and isinstance(p.get("move"), int)]
        if moves:
            picked = [rows[m] for m in sorted(moves) if 0 <= m < len(rows)]
            rest = [r for k, r in enumerate(rows) if k not in moves]
            at -= sum(1 for m in moves if m < at)
            rows = rest[:at] + picked + rest[at:]
            self.save_rows(rows, at)
            return picked
        new = []
        for p in payloads:
            if not isinstance(p, dict):
                continue
            if p.get("kind") == "libquickpart":
                lib = self._template_library()
                import templatelib as TL
                item = lib.get(p.get("iid")) if lib else None
                vals = lib.values(item) if item else None
                try:
                    said = TL.use_in_standard(lib, p.get("iid"), self.page.work) if vals else ""
                except (OSError, KeyError, TypeError):
                    said = ""
                if not said:
                    self.page.host.status(f"The Quick Part {p.get('name')} could not come from the template library.")
                    continue
                p = {"kind": "quickpart", "name": (vals or {}).get("entry") or p.get("name")}
            r = SC.clean(p)
            if r:
                new.append(r)
        if new:
            rows = rows[:at] + new + rows[at:]
            self.save_rows(rows, at + len(new) - 1)
        return new

    # ---- contents
    def add(self, r):
        r = SC.clean(r)
        if r:
            rows = self.rows() + [r]
            self.save_rows(rows, len(rows) - 1)
        return r

    def add_element(self, eid=None):
        import responseelements as RE
        data = RE.builtins()
        els = [e for e in data.get("elements", []) if e.get("source") not in ("cover", "backer")]
        if eid is None:
            names = [e["name"] for e in els]
            pick, ok = QInputDialog.getItem(self, "A response element", "The element:", names, 0, False)
            if not ok:
                return None
            eid = els[names.index(pick)]["id"]
        e = RE.get(data, eid) or {}
        return self.add({"kind": "element", "id": eid, "title": e.get("name", "")})

    def add_quickpart(self, name=None):
        names = [e.get("name") for e in ((self.work().get("quick_parts") or {}).get("entries") or []) if e.get("name")]
        if name is None:
            if not names:
                self.page.host.status("Add Quick Parts first (Components > Quick Parts), then put one in a section.")
                return None
            name, ok = QInputDialog.getItem(self, "A Quick Part", "The Quick Part:", names, 0, False)
            if not ok:
                return None
        return self.add({"kind": "quickpart", "name": name})

    def add_placeholder(self, title=None, pages=None):
        if title is None:
            title, ok = QInputDialog.getText(self, "A placeholder", "Its heading (for example Executive Summary):")
            if not ok:
                return None
            pages, ok = QInputDialog.getInt(self, "A placeholder", "Pages authors fill:", 1, 1, 200)
            if not ok:
                return None
        return self.add({"kind": "placeholder", "title": title, "pages": pages or 1})

    def move(self, d):
        r = self.list.currentRow()
        rows = self.rows()
        if 0 <= r < len(rows) and 0 <= r + d < len(rows):
            rows[r], rows[r + d] = rows[r + d], rows[r]
            self.save_rows(rows, r + d)

    def remove(self):
        r = self.list.currentRow()
        rows = self.rows()
        if 0 <= r < len(rows):
            rows.pop(r)
            self.save_rows(rows, min(r, len(rows) - 1))

    def build(self, kind, run=True):
        from . import docparts as DP
        if not self.key:
            return None
        return DP.build_table(self.page, self.key, kind, run=run)
