"""Shred > List (4.19.0; claude/stationkeeper-response-structure-plan-4.19.html): the shred as a tree of the customer's
structure. Asked 2026-11-11 18:13: "I was expecting the list to really just show the work that I'd already been doing".

Each heading (the reference every piece takes: its number and title, H1 to H9 from the numbering and the headings marked
in Fix text) with its pieces and counts (pieces, decided, undecided); each piece with its type, decision, owner, page and
first words. Undecided only, a type, a document. Double-click a piece: it opens on its page in Shred. Reads only.
Rules only (No AI); nothing leaves the PC."""
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

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


class ListPage(QWidget):
    COLS = ["The customer's structure and its pieces", "Type", "Decision", "Owner", "Page", "ID"]

    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.say = D.label("", "muted"); top.addWidget(self.say, 1)
        self.doc = QComboBox(); self.doc.setMinimumWidth(220); self.doc.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.doc)
        self.kind = QComboBox(); self.kind.currentIndexChanged.connect(lambda _i: self.fill()); top.addWidget(self.kind)
        self.only = QCheckBox("Undecided only"); self.only.toggled.connect(lambda _on: self.fill()); top.addWidget(self.only)
        self.t = QTreeWidget(); self.t.setHeaderLabels(self.COLS); self.t.setColumnWidth(0, 560)
        for c, w in ((1, 120), (2, 90), (3, 120), (4, 50)):
            self.t.setColumnWidth(c, w)
        self.t.itemDoubleClicked.connect(lambda it, _c: self.open_piece(it))
        v.addWidget(self.t, 1)
        self.empty = D.EmptyState("Nothing shredded yet", "Extract a customer document and shred it on the page; its pieces "
                                  "show here under the customer's headings.", "Go to Shred", lambda: self.host.go("assign"))
        v.addWidget(self.empty); self.empty.hide()

    def refresh(self):
        import shredtypes as ST
        R = self.host.review
        keep_doc, keep_kind = self.doc.currentText(), self.kind.currentData()
        for cb in (self.doc, self.kind):
            cb.blockSignals(True); cb.clear()
        self.doc.addItem(ALL)
        if R is not None:
            for f in R.files():
                self.doc.addItem(f)
        if keep_doc and self.doc.findText(keep_doc) >= 0:
            self.doc.setCurrentText(keep_doc)
        self.kind.addItem("Every type", "")
        try:
            types = ST.load(self.host.config_dir)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            types = {}
        for k in ST.KEYS:
            self.kind.addItem((types.get(k) or {}).get("name", k), k)
        if keep_kind:
            self.kind.setCurrentIndex(max(0, self.kind.findData(keep_kind)))
        for cb in (self.doc, self.kind):
            cb.blockSignals(False)
        self.fill()

    def fill(self):
        import shredtypes as ST
        R = self.host.review
        self.t.clear()
        if R is None or not R.M.items:
            self.t.hide(); self.empty.show(); self.say.setText("")
            return 0
        self.t.show(); self.empty.hide()
        try:
            types = ST.load(self.host.config_dir)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            types = {}
        got = tree(R.M, self.doc.currentText(), self.only.isChecked(), self.kind.currentData() or "")
        total = done = 0

        def add(parent, n):
            head = (f"H{n['level']}  " + " ".join(x for x in (n["num"], n["title"]) if x)).strip()
            it = QTreeWidgetItem([f"{head}    {n['done']} of {n['n']} decided"])
            f = it.font(0); f.setBold(True); it.setFont(0, f)
            parent.addChild(it)
            for p in n["pieces"]:
                ks = ST.types_of(p)
                txt = re.sub(r"\s+", " ", p.get("text", ""))
                c = QTreeWidgetItem([txt[:140] + ("..." if len(txt) > 140 else ""), ", ".join((types.get(k) or {}).get("name", k) for k in ks),
                                     p.get("decision", ""), p.get("owner", ""), str(p.get("page", "") or ""), p.get("id", "")])
                c.setData(0, Qt.UserRole, (p.get("file", ""), p.get("id", "")))
                c.setToolTip(0, txt)
                it.addChild(c)
            for k in n["kids"]:
                add(it, k)
            it.setExpanded(n["level"] <= 2)
        for f, roots in got:
            fi = QTreeWidgetItem([f])
            ff = fi.font(0); ff.setBold(True); fi.setFont(0, ff)
            self.t.addTopLevelItem(fi)
            for r in roots:
                add(fi, r)
                total += r["n"]; done += r["done"]
            fi.setText(0, f"{f}    {sum(r['done'] for r in roots)} of {sum(r['n'] for r in roots)} decided")
            fi.setExpanded(True)
        self.say.setText(f"{done} of {total} piece(s) decided, under the customer's headings. Double-click a piece to open it "
                         "on its page." if total else "No piece matches.")
        return total

    def open_piece(self, item):
        data = item.data(0, Qt.UserRole)
        if not data:
            return False
        f, iid = data
        h = self.host
        h.go("assign")
        pg = h.assign_page
        try:
            if pg.file != f:
                pg.files.setCurrentText(f)
                pg.open_file(f)
            pg.select(iid)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return False
        return True
