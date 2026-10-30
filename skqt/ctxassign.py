"""Read and assign any document in Review (2.84.0): a library document that does not build the matrix opens on the
same page, beside the same response structure, and the same rule applies: select text, then choose where it goes.

The decision buttons beside the structure change for a library document:
  Context for section  C   into the target section
  For a requirement    F   a compliance requirement of the target section (picked from a short list)
  Note  N, Question  Q, Task  T   in the effort record, quoting the sentence (and its section, when there is a target)
  Make it a requirement  R   into the matrix, in the target section, keeping its document and place
  Not needed  X        takes its attachments off
The work is ctxdocs'; this is the page around it. Rules only (No AI); nothing leaves the PC."""
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QGraphicsSimpleTextItem, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QVBoxLayout, QWidget)
import diag
import ctxdocs as CX
import docversions as DV
import effortrec as R_
import office_pdf as OP
import pagesent as PS
from . import design as D

PREFIX = "Library: "
CTX_COLOR = "#0F766E"                     # teal on the page: taken from a library document


def library_entries(page):
    """[(label in the file list, doc id)]: the library documents to read beside the structure: every document whose
    role is not Builds the matrix (and not Not needed), plus customer documents the matrix has not read."""
    ws = page.host.ws
    if ws is None:
        return []
    lib = DV.Library(ws.p("documents")).load()
    in_matrix = set(page.R.files()) if page.R is not None else set()
    out = []
    for d in lib.all:
        v = lib.latest(d)
        if v is None:
            continue
        role = lib.role_of(d)
        if role == "not_needed" or (role == "matrix" and v.get("file") in in_matrix):
            continue
        out.append((f"{PREFIX}{d['name']} ({CX.doc_tag(d, lib)})", d["id"]))
    return out


class CtxMode:
    """The library document open in Review."""

    def __init__(self, page, doc_id):
        self.page = page
        self.host = page.host
        self.lib = DV.Library(self.host.ws.p("documents")).load()
        self.doc = self.lib.doc(doc_id)
        self.ver = self.lib.latest(self.doc)
        self.rows = CX.items_of(self.lib, self.doc, self.ver)
        self.byid = {r["id"]: r for r in self.rows}
        self.store = CX.Store(self.host.ws.root).load()
        self.order = {r["id"]: k for k, r in enumerate(self.rows)}

    # ------------------------------------------------------------ the page
    def path(self):
        return self.lib.path_of(self.ver) if self.ver else ""

    def pdf(self):
        """(pdf, why not), like Assign's own: the file itself, or its PDF copy from Office."""
        pg = self.page
        path = self.path()
        if not path or not os.path.isfile(path):
            return "", f"{self.doc['name']}: the original file is not on this PC (its text is: search it in Library)"
        if path.lower().endswith(".pdf"):
            return path, ""
        if not OP.kind(path):
            return "", "Page view shows PDF, Word, Excel and PowerPoint files"
        folder = pg.copies_dir()
        c = OP.copy_path(path, folder) if folder else ""
        if c and os.path.isfile(c):
            return c, ""
        if path in pg.conv_err:
            return "", pg.conv_err[path]
        if not OP.available():
            return "", "the PDF copy needs Microsoft Office on this PC"
        if path not in pg.conv:
            pg.conv.add(path)
            from .assign import CopyWorker
            w = CopyWorker([path], folder)
            w.done.connect(pg.copies_done)
            pg.workers.append(w)
            w.start()
        return "", f"Microsoft {OP.kind(path).capitalize()} is making a PDF copy (once per file; about a minute)"

    def item(self, iid):
        return self.byid.get(iid)

    def selected(self):
        from .assign import SentenceBox
        ids = [b.iid for b in self.page.view.scene().selectedItems() if isinstance(b, SentenceBox)]
        return [self.byid[i] for i in sorted(ids, key=lambda i: self.order.get(i, 0)) if i in self.byid]

    def tag_of(self, iid):
        att = self.store.of_row(self.doc["id"], iid)
        if not att:
            return ""
        a = att[-1]
        t = CX.TAG[a["kind"]]
        tgt = a.get("target", "")
        return f"{t} {tgt}".strip() + (f" +{len(att) - 1}" if len(att) > 1 else "")

    def restyle(self):
        pg = self.page
        sc = pg.view.scene()
        for lab in pg.labels:
            sc.removeItem(lab)
        pg.labels = []
        last_y = -100.0
        for iid, box in sorted(pg.view.boxes.items(), key=lambda kv: kv[1].boundingRect().top()):
            tag = self.tag_of(iid)
            box.style("Context" if tag else "", iid == pg.cur)
            if not tag:
                continue
            y = max(box.boundingRect().top(), last_y + 11)
            last_y = y
            lab = QGraphicsSimpleTextItem(tag[:28])
            lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
            lab.setBrush(QColor(CTX_COLOR))
            from .assign import MARGIN
            lab.setPos(MARGIN - 8 - lab.boundingRect().width(), y)
            sc.addItem(lab)
            pg.labels.append(lab)

    def on_select(self):
        rows = self.selected()
        self.page.cur = rows[-1]["id"] if rows else None
        self.restyle()
        self.show_card(rows)

    # ------------------------------------------------------------ the card
    def show_card(self, rows):
        pg = self.page
        pg.clear_card()
        pg.notes = None
        if not rows:
            pg.add(D.EmptyState("No sentence selected", f"{self.doc['name']} is a library document ({DV.ROLE_NAMES[self.lib.role_of(self.doc)]}). "
                                "Click a sentence, then choose where it goes with the buttons beside the structure."))
            return
        it = rows[-1]
        top = QWidget(); th = QHBoxLayout(top); th.setContentsMargins(0, 0, 0, 0); th.setSpacing(D.SPACE["s"])
        att = self.store.of_row(self.doc["id"], it["id"])
        th.addWidget(D.Pill(f"{len(att)} attached" if att else "Not attached", "ctx" if att else "head"))
        if len(rows) > 1:
            th.addWidget(D.label(f"and {len(rows) - 1} more selected", "muted", wrap=False))
        th.addStretch(1)
        th.addWidget(D.label(it["id"], "mono", wrap=False))
        pg.add(top)
        t = pg.add(D.label(it.get("text", ""), "reading")); t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pg.head("Source")
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        cat = self.lib.category_name(self.doc.get("category", "customer"))
        src = [f"Document: {self.doc['name']} ({cat})", f"Version: {self.ver['label']} ({self.ver.get('file', '')})"] \
            + ([f"Where: {it['loc']}"] if it.get("loc") else []) + ([f"Section: {sec}"] if sec else [])
        pg.add(D.label("\n".join(src)))
        pg.head("Attached to")
        self.att_rows = []
        if not att:
            pg.add(D.label("Nothing yet. C: context for the target section. F: a requirement's context. N, Q, T: a note, a "
                           "question, a task. R: make it a requirement.", "muted"))
        from .assign import Chip
        for a in att:
            text = f"{CX.KIND_NAMES[a['kind']]}" + (f": {a['target']}" if a.get("target") else "")
            self.att_rows.append(pg.add(Chip(text, "ctx", on_remove=lambda _=False, i=a["id"]: self.remove(i))))
        if att:
            pg.head("Topics")
            tp = QLineEdit(", ".join(att[-1].get("topics", [])))
            tp.setPlaceholderText("Comma between topics (the document's tags, a section, anything)")
            tp.editingFinished.connect(lambda a=att[-1], tp=tp: self.store.set_topics(a["id"], tp.text().split(",")))
            self.topics = pg.add(tp)
            try:                                                   # 2.89.0: the team's topics, one click each
                import teampack as TP
                team = [t for t in TP.topics(self.page.host.config_dir) if t.casefold() not in {x.casefold() for x in att[-1].get("topics", [])}]
            except Exception:
                team = []
            if team:
                from .adaptive import FlowLayout
                box = QWidget(); fl = FlowLayout(box, 6)
                self.team_topic_btns = []
                for t in team[:16]:
                    b = D.button("+ " + t, "ghost", lambda _=False, a=att[-1], t=t: self.add_topic(a, t), "A team topic")
                    fl.addWidget(b); self.team_topic_btns.append(b)
                pg.add(box)
        QTimer.singleShot(0, pg.fit_card)

    def add_topic(self, a, t):
        self.store.set_topics(a["id"], list(a.get("topics", [])) + [t])
        self.show_card(self.selected())
        return True

    # ------------------------------------------------------------ decisions
    def _done(self, msg, n=0):
        self.restyle()
        self.page.fill_tree()
        self.show_card(self.selected())
        if n:
            diag.activity("library_text_attached", n=n)
        self.host.status(msg)

    def attach(self, kind, target=None, rows=None):
        rows = rows if rows is not None else self.selected()
        if not rows:
            self.host.status("Select a sentence on the page first.")
            return 0
        target = self.page.target if target is None else target
        if kind == "section" and not target:
            self.host.status("Click a section in your structure first: C puts the sentence there as context.")
            return 0
        for r in rows:
            self.store.attach(r, kind, target or "", save=False)
        self.store.save()
        self._done(f"{len(rows)} sentence(s): {CX.KIND_NAMES[kind].lower()}" + (f" {target}" if target else ""), len(rows))
        return len(rows)

    def for_requirement(self, req_id=None, rows=None):
        """F: context for a compliance requirement: one of the target section's (asked), or the one given."""
        rows = rows if rows is not None else self.selected()
        if not rows:
            self.host.status("Select a sentence on the page first.")
            return 0
        M = self.page.M
        if req_id is None:
            import setupdoc as SD
            P = SD.placed_in(M)
            ids = P.get(self.page.target or "", []) if self.page.target else []
            cands = [x for x in M.items if x.get("decision") == "Keep" and (not ids or x["id"] in ids)]
            if not cands:
                self.host.status("No compliance requirements to attach it to" + (f" in {self.page.target}" if self.page.target else "") + ".")
                return 0
            req_id = pick_requirement(self.page, cands)
            if not req_id:
                return 0
        for r in rows:
            self.store.attach(r, "requirement", req_id, save=False)
        self.store.save()
        self._done(f"{len(rows)} sentence(s): context for {req_id}", len(rows))
        return len(rows)

    def record(self, kind, rows=None, owner=""):
        """N, Q, T: a note, a question or a task in the effort record, quoting the sentence and where it is from."""
        rows = rows if rows is not None else self.selected()
        if not rows:
            self.host.status("Select a sentence on the page first.")
            return 0
        rec = R_.Record(self.host.ws.root)
        tgt = self.page.target or ""
        for r in rows:
            quote = f"\"{r['text'][:400]}\" ({self.doc['name']}, {r['id']})"
            if kind == "task":
                tid = rec.add_task(f"Act on {self.doc['name']} {r['id']}" + (f" for {tgt}" if tgt else ""), owner=owner, notes=quote)
                ref = tid if isinstance(tid, str) else (tid or {}).get("id", "") if isinstance(tid, dict) else ""
            else:
                ref = rec.add_note(quote, on="section" if tgt else "document", on_id=tgt or self.doc["id"], label=tgt or self.doc["name"],
                                   question=kind == "question") or ""
            self.store.attach(r, kind, tgt, note=str(ref or ""), save=False)
        self.store.save()
        self._done(f"{len(rows)} {CX.KIND_NAMES[kind].lower()}(s) in the effort record" + (f" for {tgt}" if tgt else ""), len(rows))
        return len(rows)

    def promote(self, rows=None):
        """R: the sentence becomes a compliance requirement in the matrix (in the target section), with its document."""
        rows = rows if rows is not None else self.selected()
        pg = self.page
        if not rows or pg.R is None:
            self.host.status("Select a sentence on the page first." if pg.R is not None else "Read RFP first: the matrix holds requirements.")
            return []
        import capture as CAP
        M = pg.M
        f = self.ver.get("file", "")
        if not any(s and s[0] == f for s in M.sources):
            import datetime
            M.sources.append([f, self.ver.get("sha256", ""), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), self.path()])
        pg.R.snap()
        made = []
        for r in rows:
            it = CAP.add_sentence(M, f, r["text"], how="typed")
            if it is None:
                continue
            it["loc"] = (r.get("loc") or f"{f} ({r['id']})") + ", from the library"
            it["new"] = f"From the library: {self.doc['name']} {r['id']}"
            made.append(it)
        if made:
            pg.R.req(made, pg.target or "")
            for r, it in zip(rows, made):
                self.store.attach(r, "promoted", it["id"], save=False)
            self.store.save()
            self.host.changed()
            pg.load_files_keep()
        self._done(f"{len(made)} sentence(s) made compliance requirements" + (f" in {pg.target}" if pg.target else "")
                   + (": " + ", ".join(it["id"] for it in made) if made else ""), len(made))
        return made

    def clear(self, rows=None):
        rows = rows if rows is not None else self.selected()
        n = sum(self.store.remove(doc=self.doc["id"], iid=r["id"], save=False) for r in rows)
        self.store.save()
        self._done(f"{n} attachment(s) taken off")
        return n

    def remove(self, att_id):
        self.store.remove(att_id=att_id)
        self._done("Attachment taken off")


def pick_requirement(page, cands, answer=None):
    d = QDialog(page); d.setWindowTitle("Context for which requirement?"); d.resize(720, 460)
    v = QVBoxLayout(d)
    v.addWidget(D.label("The compliance requirements" + (f" in {page.target}" if page.target else "") + ":", "muted"))
    lst = QListWidget(); v.addWidget(lst, 1)
    for x in cands:
        it = QListWidgetItem(f"{x['id']}   {x.get('map', '')}   {x['text'][:110]}"); it.setData(Qt.UserRole, x["id"]); lst.addItem(it)
    lst.setCurrentRow(0)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
    lst.itemDoubleClicked.connect(lambda _i: d.accept())
    v.addWidget(bb)
    if d.exec() != QDialog.Accepted or lst.currentItem() is None:
        return None
    return lst.currentItem().data(Qt.UserRole)


def library_for_requirement(page, iid):
    """For a matrix row's card: what people attached to it from the library: [(text, document, where, att id)]."""
    ws = page.host.ws
    if ws is None:
        return []
    st = CX.Store(ws.root).load()
    att = st.for_requirement(iid)
    if not att:
        return []
    lib = DV.Library(ws.p("documents")).load()
    return [(a["text"], (lib.doc(a["doc"]) or {}).get("name", a.get("file", "")), a.get("loc", ""), a["id"]) for a in att]
