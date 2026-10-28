"""Customer Documents in Qt (2.65.0): the customer's documents and every version of them, the submission requirements
they set, Compare (linked to the compliance matrix: each changed sentence shows the matrix requirement it touches, one
click opens it in Assign), the impact review of a new version, and the deliverables. The library, the register and the
record are the same files the classic window keeps. Rules only (No AI); nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                               QHeaderView, QInputDialog, QLineEdit, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
                               QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import diag
import docintake as DI
import docversions as DV
import effortrec as R
import subreq as SR
from . import design as D

REQ_GROUPS = (("deliver", "Submittal items", ("Deliverable",)), ("pages", "Page limits", ("Page limit",)), ("format", "Format", ("Format",)),
              ("files", "Files", ("File",)), ("how", "How, where and to whom", ("Delivery", "Copies", "Contact")),
              ("dates", "Dates", ("Due", "Questions due")))


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def diff_html(r):
    """A compare row as HTML: removed words struck through in red, added words in green."""
    t = D.tokens()
    if r["kind"] == "added":
        return f"<span style='color:{t['ok']}'>{_esc(r['new'])}</span>"
    if r["kind"] == "removed":
        return f"<span style='color:{t['crit']};text-decoration:line-through'>{_esc(r['old'])}</span>"
    if r["kind"] == "same":
        return _esc(r["new"])
    out = []
    for k, txt in r.get("diff") or DV.word_diff(r["old"], r["new"]):
        if k == "=":
            out.append(_esc(txt))
        elif k == "-":
            out.append(f"<span style='color:{t['crit']};text-decoration:line-through'>{_esc(txt)}</span>")
        else:
            out.append(f"<span style='color:{t['ok']};font-weight:600'>{_esc(txt)}</span>")
    return " ".join(out)


class Ctx:
    """The open effort's customer documents, read fresh from its files."""

    def __init__(self, host):
        self.host = host
        self.lib = DV.Library(host.ws.p("documents")).load()
        self.reg = SR.Register(self.lib)

    @property
    def rec(self):
        return R.Record(self.host.ws.root)

    def log(self, kind, text, ref=None):
        try:
            self.rec.log(kind, text, ref=ref, save=True)
        except Exception:
            diag.swallowed()

    def customer_dir(self):
        return (self.host.efforts.get(self.host.effort_name) or {}).get("customer_dir", "") or ""

    def volumes(self):
        v = self.host.ws.get("volumes", []) or []
        return [x for x in v if isinstance(x, dict) and x.get("name")]

    def unadded(self):
        """Files in the customer documents folder that are not in the library yet (by fingerprint)."""
        cd = self.customer_dir()
        if not cd or not os.path.isdir(cd):
            return []
        have = {v.get("sha256") for d in self.lib.docs for v in d["versions"]}
        out = []
        for f in sorted(os.listdir(cd)):
            p = os.path.join(cd, f)
            if os.path.isfile(p) and not f.startswith("~$") and f.lower().endswith((".docx", ".pdf", ".pptx", ".xlsx", ".txt")):
                try:
                    if DV.sha256(p) not in have:
                        out.append(p)
                except OSError:
                    diag.swallowed()
        return out


def _scroll_page(widget):
    outer = QVBoxLayout(widget); outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
    outer.addWidget(scroll)
    inner = QWidget(); inner.setObjectName("page"); scroll.setWidget(inner)
    v = QVBoxLayout(inner)
    v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
    return v


# ====================================================================== documents
class AddDialog(QDialog):
    """What each new file is: a new document, a version of one already here, or skip."""

    def __init__(self, parent, plan, lib):
        super().__init__(parent)
        self.setWindowTitle("Add customer documents"); self.setMinimumWidth(1000)
        self.plan = plan
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each file is matched by its name and its text to the documents already here. Check what each "
                            "one is, then Add.", "muted"))
        self.table = QTableWidget(len(plan), 4)
        self.table.setHorizontalHeaderLabels(["File", "What it is", "Name", "Version label"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 260); self.table.setColumnWidth(2, 220); self.table.setColumnWidth(3, 150)
        self.rows = []
        for i, e in enumerate(plan):
            self.table.setItem(i, 0, QTableWidgetItem(os.path.basename(e["path"])))
            cb = QComboBox()
            if e.get("dup"):
                cb.addItem("Already added (the same file)", ("skip", None))
            else:
                cb.addItem("A new document", ("new", None))
                for d, sc, how in e.get("cands", [])[:6]:
                    cb.addItem(f"A new version of {d['name']}  ({how})", ("version", d["id"]))
                cb.addItem("Skip it", ("skip", None))
                if e["choice"] == "version" and e.get("doc"):
                    cb.setCurrentIndex(max(0, next((k for k in range(cb.count()) if cb.itemData(k) == ("version", e["doc"])), 0)))
            name = QLineEdit(e.get("name", "")); label = QLineEdit(e.get("label", "")); label.setPlaceholderText("next number")
            self.table.setCellWidget(i, 1, cb); self.table.setCellWidget(i, 2, name); self.table.setCellWidget(i, 3, label)
            self.rows.append((cb, name, label))
        v.addWidget(self.table)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Add")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def result_plan(self):
        for e, (cb, name, label) in zip(self.plan, self.rows):
            choice, doc = cb.currentData()
            e["choice"], e["doc"] = choice, doc
            e["name"], e["label"] = name.text().strip() or e.get("name", ""), label.text().strip()
        return self.plan


class DocsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.ctx = None
        v = _scroll_page(self)
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.p_docs = D.Pill("0 documents", "accent"); self.p_ver = D.Pill("0 versions", "accent"); self.p_rev = D.Pill("0 to review", "ok")
        for p in (self.p_docs, self.p_ver, self.p_rev):
            top.addWidget(p)
        top.addStretch(1)
        self.b_folder = D.button("Add from the customer folder", None, lambda: self.add(self.ctx.unadded() if self.ctx else []),
                                 "Files in the effort's customer documents folder not added yet")
        top.addWidget(self.b_folder)
        top.addWidget(D.button("Add files...", "primary", lambda: self.add()))
        card = D.Card("Documents and their versions", "Every version is kept with its text, so Compare works even when the file moves.")
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Document / version", "File", "Added", "Sentences", "Changes", "Reviewed"])
        self.tree.setColumnWidth(0, 280); self.tree.setColumnWidth(1, 280); self.tree.setColumnWidth(2, 110); self.tree.setColumnWidth(3, 80)
        self.tree.setColumnWidth(4, 280); self.tree.setMinimumHeight(420)
        card.add(self.tree)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        for text, kind, fn in (("Mark reviewed", "primary", lambda: self.mark_reviewed()), ("Rename...", None, lambda: self.rename()),
                               ("A version of another document...", None, lambda: self.move()),
                               ("Compare with the one before", None, lambda: self.compare()), ("Impact review", None, lambda: self.impact())):
            row.addWidget(D.button(text, kind, fn))
        row.addStretch(1)
        card.body.addLayout(row)
        v.addWidget(card)
        v.addStretch(1)

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        self.tree.clear()
        if h.ws is None:
            self.ctx = None
            return
        self.ctx = c = Ctx(h)
        n = c.lib.counts()
        self.p_docs.setText(f"{n['docs']} documents"); self.p_ver.setText(f"{n['versions']} versions")
        self.p_rev.setText(f"{n['unreviewed']} to review"); self.p_rev.set_tone("warn" if n["unreviewed"] else "ok")
        un = c.unadded()
        self.b_folder.setText(f"Add from the customer folder ({len(un)})" if un else "Add from the customer folder")
        self.b_folder.setEnabled(bool(un))
        for d in c.lib.docs:
            top = QTreeWidgetItem([d["name"], "", "", "", f"{len(d['versions'])} version(s)", ""])
            f = top.font(0); f.setBold(True); top.setFont(0, f)
            top.setData(0, Qt.UserRole, ("doc", d["id"], None))
            self.tree.addTopLevelItem(top)
            for i, ver in enumerate(d["versions"]):
                ch = ""
                if i:
                    try:
                        ch = DV.summary_text(DV.summary(DV.compare(c.lib.text(d["versions"][i - 1]), c.lib.text(ver))))
                    except Exception:
                        diag.swallowed()
                rv = "first version" if not i else (ver.get("reviewed", "") or "not yet")
                it = QTreeWidgetItem([ver["label"], ver.get("file", ""), ver.get("added", "")[:10], str(ver.get("sentences", "")), ch, rv])
                if i and not ver.get("reviewed"):
                    it.setForeground(5, D.color("warn"))
                it.setData(0, Qt.UserRole, ("version", d["id"], ver["id"]))
                top.addChild(it)
        self.tree.expandAll()

    def _sel(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def select_version(self, vid):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                if top.child(j).data(0, Qt.UserRole)[2] == vid:
                    self.tree.setCurrentItem(top.child(j))
                    return True
        return False

    def add(self, paths=None, choices=None):
        """Pick files (or take the ones given), show what each is, add them. choices (tests): skip the dialog."""
        c = self.ctx
        if c is None:
            return None
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Add customer documents", c.customer_dir(),
                                                    "Documents (*.docx *.pdf *.pptx *.xlsx *.txt)")
        if not paths:
            return None
        plan = DI.plan(c.lib, list(paths))
        if choices is None:
            dlg = AddDialog(self, plan, c.lib)
            if dlg.exec() != QDialog.Accepted:
                return None
            plan = dlg.result_plan()
        else:
            for e, ch in zip(plan, choices):
                e.update(ch)
        made = DI.apply(c.lib, plan, c.customer_dir(), c.log)
        diag.activity("qt_documents_added", n=len(made))
        self.host.toast(f"{len(made)} document version(s) added")
        self.refresh()
        if made:
            self.select_version(made[-1][1]["id"])
        return made

    def mark_reviewed(self, vid=None):
        s = self._sel()
        vid = vid or (s[2] if s and s[0] == "version" else None)
        c = self.ctx
        if not vid or c is None or not c.lib.mark_reviewed(vid):
            return False
        d = next((x for x in c.lib.docs for v in x["versions"] if v["id"] == vid), None)
        v = next((v for v in d["versions"] if v["id"] == vid), None) if d else None
        if v is not None:
            c.log("customer", f"{d['name']}: {v['label']} changes reviewed", {"version": vid})
        diag.activity("qt_version_reviewed")
        self.refresh(); self.select_version(vid)
        return True

    def rename(self, name=None):
        s = self._sel()
        if not s:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename", "New name:")
            if not ok:
                return False
        ok = self.ctx.lib.rename(doc_id=s[1] if s[0] == "doc" else None, vid=s[2], name=name)
        self.refresh()
        return ok

    def move(self, to_doc=None):
        s = self._sel()
        if not s or s[0] != "version":
            return False
        lib = self.ctx.lib
        others = [d for d in lib.docs if d["id"] != s[1]]
        if not others:
            self.host.status("There is no other document yet.")
            return False
        if to_doc is None:
            names = [d["name"] for d in others]
            pick, ok = QInputDialog.getItem(self, "A version of another document", "This file is a version of:", names, 0, False)
            if not ok:
                return False
            to_doc = others[names.index(pick)]["id"]
        ok = lib.move_version(s[2], to_doc)
        diag.activity("qt_version_moved")
        self.refresh()
        return ok

    def compare(self):
        s = self._sel()
        if not s:
            return None
        self.host.go("compare")
        return self.host.compare_page.show(s[1], None, s[2])

    def impact(self):
        s = self._sel()
        if not s or s[0] != "version":
            return None
        self.host.go("impact")
        return self.host.impact_page.show(s[2])


# ====================================================================== submission requirements
class RequirementsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.ctx = None
        self.rows = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.facts = D.label("", "title"); top.addWidget(self.facts, 1)
        self.hidden = QCheckBox("Show items marked Not a requirement"); self.hidden.toggled.connect(lambda _on: self.refresh())
        top.addWidget(self.hidden)
        top.addWidget(D.button("Add a requirement...", None, lambda: self.add()))
        top.addWidget(D.button("Export...", None, lambda: self.export()))
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Requirement", "Says", "State", "Source"])
        self.tree.setColumnWidth(0, 230); self.tree.setColumnWidth(1, 330); self.tree.setColumnWidth(2, 160)
        self.tree.itemSelectionChanged.connect(self.show_detail)
        split.addWidget(self.tree)
        self.card = D.Card("Requirement"); self.card.setMinimumWidth(380)
        self.body = QVBoxLayout(); self.card.body.addLayout(self.body)
        split.addWidget(self.card); split.setSizes([900, 420])
        v.addWidget(split, 1)

    @staticmethod
    def state(r):
        if r["manual"]:
            return "Typed in", "accent"
        if r["to_review"]:
            return ("Removed: review" if r["removed"] else "Changed: review"), "warn"
        if r["hidden"]:
            return "Not a requirement", "faint"
        if r["removed"]:
            return "No longer in the documents", "faint"
        if r["confirmed"]:
            return "Confirmed", "ok"
        return "Found", "text"

    def refresh(self, want=None):
        h = self.host
        self.setEnabled(h.ws is not None)
        keep = want or self.current()
        self.tree.clear(); self.rows = {}
        if h.ws is None:
            self.ctx = None
            return []
        self.ctx = c = Ctx(h)
        allrows = c.reg.rows(include_hidden=True)
        shown = [r for r in allrows if self.hidden.isChecked() or not r["hidden"]]
        n_rev = sum(1 for r in allrows if r["to_review"])
        self.facts.setText(SR.summary_text([r for r in allrows if not r["hidden"]]) or
                           ("No submission requirements found yet." if c.lib.docs else "No customer documents yet: add them on Documents."))
        sel = None
        for _gk, label, kinds in REQ_GROUPS:
            mine = [r for r in shown if r["kind"] in kinds]
            nr = sum(1 for r in mine if r["to_review"])
            g = QTreeWidgetItem([f"{label} ({len(mine)})", "none found yet" if not mine else "", f"{nr} to review" if nr else "", ""])
            f = g.font(0); f.setBold(True); g.setFont(0, f)
            self.tree.addTopLevelItem(g)
            for r in mine:
                st, tone = self.state(r)
                it = QTreeWidgetItem([r["subject"], r["value"], st, "" if r["manual"] else f"{r['doc']}, {r['version']}"])
                it.setForeground(2, D.color(tone)); it.setData(0, Qt.UserRole, r["key"])
                g.addChild(it)
                self.rows[r["key"]] = r
                if r["key"] == keep:
                    sel = it
        self.tree.expandAll()
        if sel is not None:
            self.tree.setCurrentItem(sel)
        self.show_detail()
        diag.activity("qt_requirements_shown", n=n_rev)
        return shown

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it is not None else None

    def select(self, key):
        it = next((self.tree.topLevelItem(i).child(j) for i in range(self.tree.topLevelItemCount())
                   for j in range(self.tree.topLevelItem(i).childCount()) if self.tree.topLevelItem(i).child(j).data(0, Qt.UserRole) == key), None)
        if it is not None:
            self.tree.setCurrentItem(it)
        return it is not None

    def show_detail(self):
        while self.body.count():
            w = self.body.takeAt(0).widget()
            if w is not None:
                w.setParent(None); w.deleteLater()
        r = self.rows.get(self.current())
        if r is None:
            self.card.title.setText("Requirement")
            self.body.addWidget(D.label("Select a requirement to see what the documents say and its history.", "muted"))
            return
        st, tone = self.state(r)
        self.card.title.setText(f"{r['kind']}: {r['subject']}")
        self.body.addWidget(D.Pill(st, tone if tone != "text" else "accent"))
        self.body.addWidget(D.label(r["value"], "title"))
        if r.get("found") and r["found"] != r["value"]:
            self.body.addWidget(D.label(f"The documents say: {r['found']}", "muted"))
        if r.get("sentence"):
            self.body.addWidget(D.SectionTitle("The sentence"))
            self.body.addWidget(D.label(r["sentence"]))
        if r["history"]:
            self.body.addWidget(D.SectionTitle(f"History ({len(r['history'])})"))
            for e in r["history"]:
                self.body.addWidget(D.label(f"{e['doc']}, {e['version']} ({e['added'][:10]}): {e['change']}"
                                            + (f": {e['value']}" if e["value"] else ""), "muted"))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        k = r["key"]
        if r["to_review"]:
            row.addWidget(D.button("Mark reviewed", "primary", lambda: self.act("review", k)))
        if not r["manual"]:
            row.addWidget(D.button("Confirm", None, lambda: self.act("confirm", k)))
            row.addWidget(D.button("Edit...", None, lambda: self.edit(k)))
            row.addWidget(D.button("Show again" if r["hidden"] else "Not a requirement", "ghost", lambda: self.act("hide", k, not r["hidden"])))
        else:
            row.addWidget(D.button("Remove", "danger", lambda: self.act("remove", k)))
        w = QWidget(); w.setLayout(row)
        self.body.addWidget(w)

    def act(self, what, key, flag=True):
        reg, c = self.ctx.reg, self.ctx
        r = self.rows.get(key, {})
        ok = {"review": lambda: reg.review(key), "confirm": lambda: reg.confirm(key), "hide": lambda: reg.hide(key, flag),
              "remove": lambda: reg.remove_manual(key)}[what]()
        if ok:
            word = {"review": "change reviewed", "confirm": "confirmed", "hide": "marked not a requirement" if flag else "shown again",
                    "remove": "removed"}[what]
            c.log("requirement", f"{r.get('kind', '')}, {r.get('subject', '')}: {word}")
            diag.activity("qt_requirement_changed")
        self.refresh(None if what == "remove" else key)
        return bool(ok)

    def edit(self, key, value=None):
        r = self.rows.get(key)
        if r is None:
            return False
        if value is None:
            value, ok = QInputDialog.getText(self, "Edit requirement", f"{r['subject']} (leave empty to go back to what the documents say):",
                                             QLineEdit.Normal, r["value"])
            if not ok:
                return False
        self.ctx.reg.edit(key, value)
        self.ctx.log("requirement", f"{r['kind']}, {r['subject']}: " + (f"edited to: {value}" if value.strip() else "back to what the documents say"))
        diag.activity("qt_requirement_changed")
        self.refresh(key)
        return True

    def add(self, kind=None, subject=None, value=None):
        if self.ctx is None:
            return None
        if value is None:
            dlg = QDialog(self); dlg.setWindowTitle("Add a requirement")
            f = QFormLayout(dlg)
            kc = QComboBox(); kc.addItems(list(SR.KINDS)); kc.setCurrentText("Page limit")
            sj = QLineEdit(); sj.setPlaceholderText("Volume II, Font, Attachment J-3...")
            vl = QLineEdit(); vl.setPlaceholderText("15 pages")
            f.addRow("Kind", kc); f.addRow("Requirement", sj); f.addRow("Says", vl)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
            f.addRow(bb)
            if dlg.exec() != QDialog.Accepted:
                return None
            kind, subject, value = kc.currentText(), sj.text(), vl.text()
        k = self.ctx.reg.add(kind or "Format", subject or "", value)
        if k:
            self.ctx.log("requirement", f"{kind}, {subject}: typed in: {value.strip()}")
            diag.activity("qt_requirement_added")
        self.refresh(k)
        return k

    def export(self, path=None):
        if self.ctx is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the submission requirements", os.path.join(
                os.path.dirname(self.host.effort_path), f"{self.host.effort_name}_Submission_Requirements.xlsx".replace(" ", "_")), "Excel (*.xlsx)")
            if not path:
                return None
        try:
            SR.export_excel(path, self.ctx.reg.rows(include_hidden=True), self.host.effort_name)
        except PermissionError:
            self.host.status("That workbook is open in Excel. Close it, then export again.")
            return None
        self.host.toast("Submission requirements written")
        return path


# ====================================================================== compare, linked to the matrix
class ComparePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.ctx = None
        self.rows, self.links, self.shown = [], [], []
        self.sel = (None, None, None)
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.doc = QComboBox(); self.doc.setMinimumWidth(260); self.a = QComboBox(); self.b = QComboBox()
        for lab, w in (("Document", self.doc), ("From", self.a), ("To", self.b)):
            top.addWidget(D.label(lab, "label", wrap=False)); top.addWidget(w)
        self.doc.activated.connect(lambda _i: self.pick_doc())
        self.a.activated.connect(lambda _i: self.run()); self.b.activated.connect(lambda _i: self.run())
        self.only = QCheckBox("Only changes"); self.only.setChecked(True); self.only.toggled.connect(lambda _on: self.fill())
        self.in_matrix = QCheckBox("Only what touches the matrix"); self.in_matrix.toggled.connect(lambda _on: self.fill())
        top.addWidget(self.only); top.addWidget(self.in_matrix); top.addStretch(1)
        top.addWidget(D.button("Redline (Word)...", None, lambda: self.export_redline()))
        top.addWidget(D.button("Change list (Excel)...", None, lambda: self.export_list()))
        self.sum = D.label("", "muted"); v.addWidget(self.sum)
        split = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Change", "Sentence (was and now)", "In the compliance matrix", "Section"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 90); self.table.setColumnWidth(2, 330); self.table.setColumnWidth(3, 140)
        self.table.itemSelectionChanged.connect(self.show_row)
        self.table.cellDoubleClicked.connect(lambda r, _c: self.open_in_assign(r))
        split.addWidget(self.table)
        self.detail = QTextBrowser(); self.detail.setOpenLinks(False); self.detail.anchorClicked.connect(lambda u: self.open_item(u.toString()))
        split.addWidget(self.detail); split.setSizes([600, 220])
        v.addWidget(split, 1)

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            self.ctx = None
            return
        self.ctx = Ctx(h)
        self.fill_docs()

    def fill_docs(self):
        lib = self.ctx.lib
        docs = [d for d in lib.docs if d["versions"]]
        self.doc.clear()
        for d in docs:
            self.doc.addItem(f"{d['name']} ({len(d['versions'])} versions)", d["id"])
        if not docs:
            self.sum.setText("No customer documents yet: add them on Documents.")
            self.table.setRowCount(0)
            return
        want = self.sel[0] if self.sel[0] in [d["id"] for d in docs] else next((d["id"] for d in docs if len(d["versions"]) > 1), docs[0]["id"])
        self.doc.setCurrentIndex(self.doc.findData(want))
        self.pick_doc(keep=True)

    def pick_doc(self, keep=False):
        d = self.ctx.lib.doc(self.doc.currentData())
        if d is None:
            return
        self.a.clear(); self.b.clear()
        for v in d["versions"]:
            for cb in (self.a, self.b):
                cb.addItem(f"{v['label']} ({v['added'][:10]})", v["id"])
        ids = [v["id"] for v in d["versions"]]
        a = self.sel[1] if keep and self.sel[1] in ids else None
        b = self.sel[2] if keep and self.sel[2] in ids else ids[-1]
        if a is None:
            a = ids[max(0, ids.index(b) - 1)]
        self.a.setCurrentIndex(ids.index(a)); self.b.setCurrentIndex(ids.index(b))
        self.run()

    def show(self, doc_id, a=None, b=None):
        """Open Compare on two versions (b and the one before it by default)."""
        self.sel = (doc_id, a, b)
        if self.ctx is None:
            self.refresh()
        else:
            self.fill_docs()
        return self.rows

    def run(self):
        lib = self.ctx.lib
        d = lib.doc(self.doc.currentData())
        va = next((v for v in d["versions"] if v["id"] == self.a.currentData()), None) if d else None
        vb = next((v for v in d["versions"] if v["id"] == self.b.currentData()), None) if d else None
        self.cur = (d, va, vb)
        if d is None or va is None or vb is None or va is vb:
            self.rows, self.links = [], []
            self.sum.setText("Pick two different versions.")
            self.fill()
            return []
        self.sel = (d["id"], va["id"], vb["id"])
        self.rows = DV.compare(lib.text(va), lib.text(vb))
        M = self.host.review.M if self.host.review is not None else None
        owner_of = None
        if M is not None:
            import setupdoc as SD
            owner_of = lambda it: SD.owner_of(M, it)                  # noqa: E731
        self.links = DI.link(M, self.rows, owner_of, files=(va.get("file", ""), vb.get("file", "")))
        c = DV.summary(self.rows)
        n_m = sum(1 for x in self.links if x)
        self.sum.setText(f"{va['label']} to {vb['label']}: {DV.summary_text(c)} in {len(self.rows)} sentences. "
                         + (f"{n_m} change(s) touch the compliance matrix; double-click one to open it in Assign." if M is not None
                            else "Open the compliance matrix (Read RFP) to see which changes touch it."))
        diag.activity("qt_compared", n=c["changed"] + c["added"] + c["removed"])
        self.fill()
        return self.rows

    def fill(self):
        idx = [i for i, r in enumerate(self.rows) if (not self.only.isChecked() or r["kind"] != "same")
               and (not self.in_matrix.isChecked() or self.links[i])]
        self.shown = idx
        self.table.setRowCount(len(idx))
        tone = {"changed": "warn", "added": "ok", "removed": "crit", "same": "muted"}
        for k, i in enumerate(idx):
            r = self.rows[i]
            a = QTableWidgetItem(r["kind"].title()); a.setForeground(D.color(tone[r["kind"]]))
            self.table.setItem(k, 0, a)
            txt = r["new"] if r["kind"] in ("same", "added") else (r["old"] if r["kind"] == "removed" else f"Was: {r['old']}\nNow: {r['new']}")
            self.table.setItem(k, 1, QTableWidgetItem(txt))
            links = self.links[i] if i < len(self.links) else []
            m = QTableWidgetItem("\n".join(f"{h['id']}  {h['decision'] or 'not decided'}" + (f", {h['map']}" if h["map"] else "")
                                           + (f", {h['owner']}" if h["owner"] else "") for h in links))
            if links:
                m.setForeground(D.color("accent"))
            self.table.setItem(k, 2, m)
            self.table.setItem(k, 3, QTableWidgetItem(r.get("section", "")))
            if r.get("submission"):
                for c in range(4):
                    self.table.item(k, c).setBackground(D.color("warn_soft"))
        self.table.resizeRowsToContents()
        self.show_row()

    def show_row(self):
        k = self.table.currentRow()
        if not (0 <= k < len(self.shown)):
            self.detail.setHtml("")
            return
        i = self.shown[k]
        r = self.rows[i]
        links = self.links[i] if i < len(self.links) else []
        t = D.tokens()
        html = f"<p style='font-size:12pt'>{diff_html(r)}</p>"
        if links:
            html += "<p><b>In the compliance matrix:</b><br>" + "<br>".join(
                f"<a href='{h['id']}' style='color:{t['accent']}'>{h['id']}</a> {h['decision'] or 'not decided'}"
                + (f", in {_esc(h['map'])}" if h["map"] else "") + (f", owner {_esc(h['owner'])}" if h["owner"] else "")
                + f" <span style='color:{t['muted']}'>({h['how']})</span>" for h in links) + "</p>"
        self.detail.setHtml(html)

    def open_item(self, iid):
        if self.host.review is None or self.host.review.item(iid) is None:
            return None
        self.host.go("assign")
        self.host.assign_page.select(iid)
        diag.activity("qt_compare_opened_in_assign")
        return iid

    def open_in_assign(self, k):
        if not (0 <= k < len(self.shown)):
            return None
        links = self.links[self.shown[k]]
        return self.open_item(links[0]["id"]) if links else None

    def export_redline(self, path=None):
        d, va, vb = getattr(self, "cur", (None, None, None))
        if d is None or va is None or va is vb:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Redline", f"{d['name']}_{va['label']}_to_{vb['label']}_Redline.docx".replace(" ", "_"), "Word (*.docx)")
            if not path:
                return None
        DV.export_redline(path, d["name"], va, vb, self.rows, only_changes=self.only.isChecked())
        self.host.toast("Redline written")
        return path

    def export_list(self, path=None):
        d, va, vb = getattr(self, "cur", (None, None, None))
        if d is None or va is None or va is vb:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Change list", f"{d['name']}_{va['label']}_to_{vb['label']}_Changes.xlsx".replace(" ", "_"), "Excel (*.xlsx)")
            if not path:
                return None
        DV.export_list(path, self.ctx.lib, doc=d, compares=[(d, va, vb, self.rows)])
        self.host.toast("Change list written")
        return path


# ====================================================================== impact review
class ImpactPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.ctx = None
        self.r = None
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        top.addWidget(D.label("Version", "label", wrap=False))
        self.pick = QComboBox(); self.pick.setMinimumWidth(420); self.pick.activated.connect(lambda _i: self.build())
        top.addWidget(self.pick); top.addStretch(1)
        top.addWidget(D.button("Mark reviewed", "primary", lambda: self.mark_reviewed()))
        top.addWidget(D.button("Export (Word)...", None, lambda: self.export()))
        self.head = D.label("", "title"); v.addWidget(self.head)
        self.view = QTextBrowser(); self.view.setOpenLinks(False); self.view.anchorClicked.connect(lambda u: self.open(u.toString()))
        v.addWidget(self.view, 1)

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            self.ctx = None
            return
        self.ctx = Ctx(h)
        import impact as IM
        keep = self.pick.currentData()
        self.pick.clear()
        for d, v in IM.reviewable(self.ctx.lib):
            self.pick.addItem(f"{d['name'][:50]}: {v['label']}" + ("" if v.get("reviewed") else "  (not reviewed)"), v["id"])
        if self.pick.count() == 0:
            self.head.setText("No new versions yet: an impact review needs a document with two versions.")
            self.view.setHtml("")
            return
        i = self.pick.findData(keep)
        self.pick.setCurrentIndex(i if i >= 0 else self.pick.count() - 1)
        self.build()

    def show(self, vid):
        self.refresh()
        i = self.pick.findData(vid)
        if i >= 0:
            self.pick.setCurrentIndex(i)
            self.build()
        return self.r

    def build(self):
        import impact as IM
        c, h = self.ctx, self.host
        vid = self.pick.currentData()
        M = h.review.M if h.review is not None else None
        owner_of = None
        if M is not None:
            import setupdoc as SD
            owner_of = lambda it: SD.owner_of(M, it)                  # noqa: E731
        try:
            import effort as E
            L = E.EffortList(h.effort_path).load()
            listed = set(L.rows)
            kws = [k.get("Keyword", "") for k in (L.keywords or [])]
        except Exception:
            diag.swallowed(); listed, kws = set(), []
        rows = [r for r in c.reg.rows() if not r.get("hidden")]
        self.r = r = IM.build(c.lib, vid, rows, c.rec, M, owner_of, in_list=lambda t: t in listed, keyword_list=kws, volumes=c.volumes())
        if r is None:
            self.head.setText("Pick a version that has a version before it.")
            self.view.setHtml("")
            return None
        self.head.setText(IM.headline(r))
        t = D.tokens()

        def sec(title, items):
            return f"<h3>{_esc(title)} ({len(items)})</h3>" + ("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>" if items
                                                               else f"<p style='color:{t['muted']}'>Nothing.</p>")
        reqs = [f"<b>{_esc(x.get('kind', ''))}, {_esc(x.get('subject', ''))}</b>: was {_esc(x.get('was', '') or '-')}, now {_esc(x.get('now', '') or '-')}"
                for x in r["requirements"]]
        comp = r["compliance"]
        cl = [f"<a href='{x['id']}' style='color:{t['accent']}'>{x['id']}</a> {kind}"
              + (f" in {_esc(x['map'])}" if x.get("map") else "") + (f", owner {_esc(x['owner'])}" if x.get("owner") else "")
              + f": {diff_html({'kind': 'changed' if kind == 'changed' else 'removed', 'old': x['old'], 'new': x['new'], 'diff': x.get('diff')})}"
              for kind in ("changed", "removed") for x in comp[kind]]
        cl += [f"added{(' (in the matrix: ' + x['id'] + ')') if x['id'] else ' (not in the matrix yet)'}: {_esc(x['text'])}"
               for x in comp["added"] if not x["decision"]]
        dl = [f"<b>{_esc(x['name'])}</b>" + (f" ({_esc(x['owner'])})" if x.get("owner") else "") + ": " + _esc("; ".join(x["why"]))
              for x in r["deliverables"]] + \
             [f"suggested: {_esc(x.get('subject', ''))}" for x in r["suggested"]]
        st = [f"{_esc(x['num'])} {x['change']}: " + (f"was {_esc(x['was'])}, " if x.get("was") else "") + (f"now {_esc(x['now'])}" if x.get("now") else "")
              + (f"; our section {_esc(x['ours'])}" if x.get("ours") else "") for x in r["structure"]]
        ac = [f"new: {_esc(a['term'])} ({a['count']} times" + ("; in the effort list" if a["in_list"] else "") + ")" for a in r["acronyms"]["new"]] + \
             [f"no longer in it: {_esc(a['term'])}" for a in r["acronyms"]["gone"]]
        kw = [f"{_esc(x['phrase'])} ({x['count']} times)" for x in r["keywords"]]
        pp = [f"<b>{_esc(p)}</b>: " + "; ".join(_esc(x) for x in xs[:6]) for p, xs in r["people"].items()]
        self.view.setHtml(sec("Submission requirements", reqs) + sec("Compliance matrix", cl) + sec("Deliverables", dl)
                          + sec("Structure", st) + sec("Acronyms", ac) + sec("Keywords", kw) + sec("People it touches", pp))
        diag.activity("qt_impact_shown")
        return r

    def open(self, iid):
        if self.host.review is None or self.host.review.item(iid) is None:
            return None
        self.host.go("assign")
        self.host.assign_page.select(iid)
        return iid

    def mark_reviewed(self):
        vid = self.pick.currentData()
        if not vid or self.ctx is None or not self.ctx.lib.mark_reviewed(vid):
            return False
        r = self.r or {}
        self.ctx.log("customer", f"{r.get('doc', '')}: {r.get('version', '')} changes reviewed", {"version": vid})
        diag.activity("qt_version_reviewed")
        self.refresh()
        return True

    def export(self, path=None):
        import impact as IM
        if self.r is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Impact review", f"{self.r['doc']}_{self.r['version']}_Impact.docx".replace(" ", "_"), "Word (*.docx)")
            if not path:
                return None
        IM.export_word(path, self.r, self.host.effort_name)
        self.host.toast("Impact review written")
        return path


# ====================================================================== deliverables
class DeliverablesPage(QWidget):
    COLS = ["Deliverable", "Kind", "Owner", "Format", "Page limit", "Status", "Flags"]

    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.ctx = None
        self.ids = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.sumlab = D.label("", "title"); top.addWidget(self.sumlab, 1)
        top.addWidget(D.button("+ Deliverable...", "primary", lambda: self.edit()))
        top.addWidget(D.button("Export (Excel)...", None, lambda: self.export()))
        self.sugg = D.Card("The customer documents name these", "Add each one the effort owes, or say it is not ours.")
        self.sugg_box = QVBoxLayout(); self.sugg.body.addLayout(self.sugg_box)
        v.addWidget(self.sugg)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in enumerate((0, 110, 140, 140, 110, 220, 160)):
            if i:
                self.table.setColumnWidth(i, w)
        self.table.cellDoubleClicked.connect(lambda r, _c: self.edit(self.ids[r]))
        v.addWidget(self.table, 1)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); v.addLayout(row)
        row.addWidget(D.button("Edit...", None, lambda: self.edit(self.current())))
        row.addWidget(D.button("Done for this stage", None, lambda: self.mark_stage()))
        row.addWidget(D.button("Remove", "danger", lambda: self.remove()))
        row.addStretch(1)

    def current(self):
        i = self.table.currentRow()
        return self.ids[i] if 0 <= i < len(self.ids) else None

    def refresh(self):
        import deliverables as DL
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            self.ctx = None
            return
        self.ctx = c = Ctx(h)
        rec = c.rec
        rows = c.reg.rows()
        vols = c.volumes()
        ds = DL.items(rec)
        self.ids = [d["id"] for d in ds]
        self.table.setRowCount(len(ds))
        for i, d in enumerate(ds):
            st = DL.state(d, rows, c.lib, vols, rec)
            vals = [d["name"], d.get("kind", ""), d.get("owner", "") or "nobody yet", d.get("format", ""), st["limit"],
                    DL.status_text(d, st), ", ".join({"over": "over the limit", "changed": "changed", "noowner": "no owner"}[f] for f in st["flags"])]
            for col, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                if col == 6 and st["flags"]:
                    it.setForeground(D.color("crit" if "over" in st["flags"] else "warn"))
                self.table.setItem(i, col, it)
        sm = DL.summary(rec, rows, c.lib, vols)
        self.sumlab.setText(f"{sm['count']} deliverables: {sm['final']} final, {sm['over']} over the limit, {sm['changed']} changed, "
                            f"{sm['noowner']} without an owner")
        while self.sugg_box.count():
            it = self.sugg_box.takeAt(0)
            w = it.widget() or None
            if w is not None:
                w.setParent(None); w.deleteLater()
        sg = DL.suggestions(rec, rows)
        self.sugg.setVisible(bool(sg))
        for r in sg:
            line = QWidget(); hl = QHBoxLayout(line); hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(D.label(f"{r['subject']}: {r['value']}  ({r['doc']}, {r['version']})"), 1)
            hl.addWidget(D.button("Add", None, lambda _=False, k=r["key"]: self.add_suggested(k)))
            hl.addWidget(D.button("Not ours", "ghost", lambda _=False, k=r["key"], s=r["subject"]: self.dismiss(k, s)))
            self.sugg_box.addWidget(line)

    def add_suggested(self, key):
        import deliverables as DL
        rows = self.ctx.reg.rows()
        r = next((x for x in rows if x["key"] == key), None)
        if r is None:
            return None
        kind = DL.kind_of(r["subject"])
        did = DL.add(self.ctx.rec, r["subject"], kind, req_key=key, fmt=DL.default_format(kind, rows))
        diag.activity("qt_deliverable_added")
        self.refresh()
        return did

    def dismiss(self, key, label=""):
        import deliverables as DL
        DL.dismiss(self.ctx.rec, key, label)
        self.refresh()
        return True

    def edit(self, did=None, values=None):
        import deliverables as DL
        rec = self.ctx.rec
        d = DL.get(rec, did) if did else None
        if values is None:
            dlg = QDialog(self); dlg.setWindowTitle("Deliverable"); dlg.setMinimumWidth(520)
            f = QFormLayout(dlg)
            name = QLineEdit(d["name"] if d else "")
            kind = QComboBox(); kind.addItems(DL.KINDS); kind.setCurrentText(d.get("kind", "Volume") if d else "Volume")
            owner = QComboBox(); owner.setEditable(True)
            try:
                import effortstate as ES
                owner.addItems([""] + ES.people_of(rec, self.host.review.M if self.host.review else None))
            except Exception:
                diag.swallowed()
            owner.setCurrentText(d.get("owner", "") if d else "")
            fmt = QLineEdit(d.get("format", "") if d else ""); limit = QLineEdit(d.get("limit", "") if d else "")
            status = QComboBox(); status.addItems(DL.STATUSES); status.setCurrentText(d.get("status", "Not started") if d else "Not started")
            fl = QLineEdit(d.get("file", "") if d else ""); fl.setPlaceholderText("Our Word file (for the page count)")
            for lab, w in (("Name", name), ("Kind", kind), ("Owner", owner), ("Format", fmt), ("Page limit", limit), ("Status", status), ("Our file", fl)):
                f.addRow(lab, w)
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
            f.addRow(bb)
            if dlg.exec() != QDialog.Accepted:
                return None
            values = {"name": name.text(), "kind": kind.currentText(), "owner": owner.currentText(), "format": fmt.text(),
                      "limit": limit.text(), "status": status.currentText(), "file": fl.text()}
        if d is None:
            did = DL.add(rec, values.get("name", ""), values.get("kind", ""), fmt=values.get("format", ""), limit=values.get("limit", ""),
                         owner=values.get("owner", ""), file=values.get("file", ""))
            if did and values.get("status") and values["status"] != "Not started":
                DL.update(rec, did, status=values["status"])
        else:
            DL.update(rec, did, **{k: v for k, v in values.items() if k != "kind"})
        diag.activity("qt_deliverable_saved")
        self.refresh()
        return did

    def mark_stage(self, did=None):
        import deliverables as DL
        did = did or self.current()
        if not did:
            return False
        ok = DL.mark_stage(self.ctx.rec, did, True)
        self.refresh()
        return ok

    def remove(self, did=None):
        import deliverables as DL
        did = did or self.current()
        if not did:
            return False
        ok = DL.remove(self.ctx.rec, did)
        self.refresh()
        return ok

    def export(self, path=None):
        import deliverables as DL
        c = self.ctx
        if c is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Deliverables", os.path.join(os.path.dirname(self.host.effort_path),
                                                  f"{self.host.effort_name}_Deliverables_{datetime.date.today().isoformat()}.xlsx".replace(" ", "_")), "Excel (*.xlsx)")
            if not path:
                return None
        DL.export_excel(path, c.rec, c.reg.rows(), c.lib, c.volumes(), self.host.effort_name)
        self.host.toast("Deliverables written")
        return path
