"""After Add documents (4.85.0, step I3 of claude/stationkeeper-document-intake-direction-2026-11-24.md, "Compare at
intake"): one window says what the add brought, in place of one What changed card per new version (2.98.0).

- A line: "12 files: 7 new versions, 3 new documents, 2 already added."
- New versions: each new version of a customer document, what it changed against the version before it (pieces
  changed, added and removed, the submission rules and the compliance requirements it touches), ticked when its row was
  ticked Compare with in Add documents. Review the N in What changed (the main button) opens What changed on the first,
  and What changed names the next. Right-click a version: Show on the page.
- Not in this release: when the files arrived as a release of a package that held documents before, every document of
  that package that the release did not replace. An amendment re-posts only what changed, so each stays in force; tick
  one the customer no longer uses and it is marked no longer in force (kept, and it stops building the matrix;
  right-click > Back in force on Documents undoes it).
Shown only in an effort, and only when there is a new version or a document to confirm.

4.86.0 (step I4): Change notices and the Section J check.
- A change notice the add brought (a file typed Amendment, Q&A, Evaluation Notice or FPR request, or a type renamed
  from one) is listed first under "Change notice", with the change instructions an amendment holds; double-click or
  right-click > Show on the page opens it, and an amendment with instructions offers Apply its instructions.... A
  notice brings the window up on its own, and when the add said no release it stands for one (its own name), so the
  package's documents it did not replace are still listed.
- Under the line, Section J's count for the package the add was part of ("Section J lists 4 attachments; 3 are in
  this package. Not here: J-3 DD Form 254."). An attachment Section J lists that is not in the package brings the
  window up on its own, even for a first release.
Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QVBoxLayout

import diag
import docpackages as DP
import doctypes as DT
import docversions as DV
import sectionj as SJ
from . import design as D


def counts(plan):
    """{"files", "new", "versions", "same", "replaced"} of one add, the files taken out not counted."""
    c = {"files": 0, "new": 0, "versions": 0, "same": 0, "replaced": 0}
    for e in plan or []:
        ch = e.get("choice")
        if ch == "skip" and not e.get("dup"):
            continue                                   # taken out with its x: not part of the add
        c["files"] += 1
        c[{"new": "new", "version": "versions", "replace": "replaced"}.get(ch, "same")] += 1
    return c


def line(c):
    """ "12 files: 7 new versions, 3 new documents, 2 already added." """
    n = lambda k, one, many: f"{c[k]} {one if c[k] == 1 else many}"            # noqa: E731
    bits = [n(k, one, many) for k, one, many in (("versions", "new version", "new versions"), ("new", "new document", "new documents"),
                                                  ("replaced", "file replaced", "files replaced"), ("same", "already added", "already added"))
            if c[k]]
    return f"{n('files', 'file', 'files')}: " + ", ".join(bits) + "."


def what(s):
    """One new version's line: what it changed and what it touches."""
    bits = [f"{s['changed']} changed, {s['added']} added, {s['removed']} removed"]
    if s.get("rules"):
        bits.append(f"{len(s['rules'])} submission rule" + ("" if len(s["rules"]) == 1 else "s"))
    if s.get("requirements"):
        bits.append(f"{len(s['requirements'])} requirement" + ("" if len(s["requirements"]) == 1 else "s"))
    if s.get("not_in_matrix"):
        bits.append(f"{s['not_in_matrix']} new not in the matrix")
    return "  ·  ".join(bits)


def plan_of(page, plan, made, summaries):
    """What the window shows: {"line", "release", "versions": [(summary, ticked)], "confirm": [documents]}."""
    lib = page.lib
    ticked = {e.get("doc") for e in plan or [] if e.get("choice") == "version" and e.get("compare")}
    asked = {e.get("doc") for e in plan or [] if e.get("choice") == "version" and "compare" in e}
    versions = [(s, s["doc"]["id"] in ticked or s["doc"]["id"] not in asked) for s in summaries or []]
    notices = []
    for d, _v in made or []:                                       # 4.86.0: the change notices the add brought
        dd = (lib.doc(d["id"]) if lib is not None else None) or d
        if dd.get("category", "customer") in DP.CUSTOMER_SIDE and DT.is_change_notice(dd.get("type", "")) and dd not in notices:
            notices.append(dd)
    rel = DP.release_of_add(plan)
    said = rel is not None
    if rel is None and notices:
        rel = DP.release_of_notice(notices[0], lib)
    confirm = []
    touched = {d["id"] for d, _v in made or []} | {e.get("doc") for e in plan or [] if e.get("doc")}
    if rel is not None and lib is not None:
        confirm = DP.not_replaced(lib, rel[0], rel[1], touched)
    sj = None
    if lib is not None:
        part = rel[0] if rel else DP.PACKAGES[0]
        mine = [lib.doc(i) for i in touched if i and lib.doc(i)]
        if any(d.get("category", "customer") in DP.CUSTOMER_SIDE and DP.in_part(d, part) for d in mine):
            try:
                sj = SJ.check(lib, part)
            except Exception:  # noqa: BLE001
                diag.swallowed()
    return {"line": line(counts(plan)), "release": rel, "said": said, "versions": versions, "confirm": confirm,
            "notices": notices, "sectionj": sj}


def fit(lst, most=10):
    """A list as tall as its rows, up to most rows, then it scrolls."""
    h = lst.sizeHintForRow(0) if lst.count() else 20
    lst.setFixedHeight(h * min(max(lst.count(), 1), most) + 2 * lst.frameWidth() + 4)


def after_add(page, plan, made, summaries, run=None):
    """After the add: the summary window, when there is something in it. run: show it (default: not while tests run).
    Returns the window (not shown under tests), or None."""
    if page.effort_rec() is None or not made:
        return None
    p = plan_of(page, plan, made, summaries)
    if not p["versions"] and not p["confirm"] and not p["notices"] and not (p["sectionj"] and p["sectionj"]["missing"]):
        return None
    dlg = SummaryDialog(page, p)
    if run is None:
        run = not os.environ.get("AH_TEST")
    if run:
        dlg.exec()
    return dlg


class SummaryDialog(QDialog):
    def __init__(self, page, p):
        super().__init__(page)
        self.page, self.host, self.p = page, page.host, p
        rel = p["release"]
        self.release = rel[1] if rel else ""
        self.setWindowTitle("Added: " + DP.release_title(*rel) if rel else "Added")
        self.setMinimumWidth(720)
        v = QVBoxLayout(self)
        v.addWidget(D.label(p["line"], "title"))
        sj = p.get("sectionj")                                        # 4.86.0: the Section J check
        self.sj_line = D.label(" ".join(x for x in (SJ.line(sj), SJ.missing_text(sj)) if x), "muted" if not (sj and sj["missing"]) else None)
        self.sj_line.setWordWrap(True); self.sj_line.setVisible(bool(sj))
        if sj:
            self.sj_line.setToolTip(f"Read from Section J of {sj['doc'].get('name', '')}")
            v.addWidget(self.sj_line)
        self.notices = QListWidget()                                  # 4.86.0: the change notices the add brought
        for d in p.get("notices") or []:
            vs = d.get("versions") or [{}]
            n_ins = 0
            if str(DV.type_of(d.get("type", ""))).casefold().startswith("amend") or DP.is_amendment(d):
                try:
                    import amendinst as AI
                    n_ins = len(AI.instructions_of(page.lib, vs[-1]))
                except Exception:  # noqa: BLE001
                    diag.swallowed()
            lab = vs[-1].get("label", "")
            bits = [d.get("name", ""), d.get("type", "")] + ([lab] if lab not in ("", "Original", d.get("name")) else [])
            if n_ins:
                bits.append(f"{n_ins} change instruction" + ("" if n_ins == 1 else "s"))
            it = QListWidgetItem("   ·   ".join(b for b in bits if b))
            it.setData(Qt.UserRole, (d["id"], vs[-1].get("file", ""), n_ins))
            it.setToolTip("The customer's notice of what changed. Double-click to read it on the page.")
            self.notices.addItem(it)
        self.notices.setContextMenuPolicy(Qt.CustomContextMenu)
        self.notices.customContextMenuRequested.connect(self.notice_menu)
        self.notices.itemDoubleClicked.connect(lambda it: self.on_page(it.data(Qt.UserRole)[1]))
        if p.get("notices"):
            v.addWidget(D.label("Change notice" if len(p["notices"]) == 1 else "Change notices", "label"))
            v.addWidget(self.notices); fit(self.notices, 4)
        self.versions = QListWidget()
        for s, on in p["versions"]:
            it = QListWidgetItem(f"{s['doc'].get('name', '')}   {s['from'].get('label', '')} to {s['to'].get('label', '')}   ·   {what(s)}")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if on else Qt.Unchecked)
            it.setData(Qt.UserRole, (s["doc"]["id"], s["from"]["id"], s["to"]["id"]))
            it.setToolTip("\n".join([s.get("text", "")] + [f"Rule: {r[:160]}" for r in s.get("rules", [])[:4]]))
            self.versions.addItem(it)
        self.versions.setContextMenuPolicy(Qt.CustomContextMenu)
        self.versions.customContextMenuRequested.connect(self.version_menu)
        self.versions.itemChanged.connect(lambda _it: self.say_button())
        if p["versions"]:
            v.addWidget(D.label("New versions", "label"))
            v.addWidget(self.versions); fit(self.versions)
        self.confirm = QListWidget()
        for d in p["confirm"]:
            vs = d.get("versions") or [{}]
            it = QListWidgetItem(f"{d.get('name', '')}   ·   {vs[-1].get('label', '')}")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            it.setData(Qt.UserRole, d["id"])
            self.confirm.addItem(it)
        if p["confirm"]:
            v.addWidget(D.label(f"Not in {self.release}", "label"))
            v.addWidget(D.label(f"These were in the {rel[0] or 'package'} before and {self.release} has no new version of them. "
                                "They stay in force. Tick any the customer no longer uses.", "muted"))
            v.addWidget(self.confirm); fit(self.confirm)
        bb = QHBoxLayout(); v.addLayout(bb)
        bb.addStretch(1)
        self.b_done = D.button("Done", "ghost", self.done_now)
        self.b_compare = D.button("Review it in What changed", "primary", self.compare_now)
        bb.addWidget(self.b_done); bb.addWidget(self.b_compare)
        self.say_button()

    def ticked(self):
        return [self.versions.item(i).data(Qt.UserRole) for i in range(self.versions.count())
                if self.versions.item(i).checkState() == Qt.Checked]

    def say_button(self):
        n = len(self.ticked())
        self.b_compare.setVisible(n > 0)
        self.b_compare.setText("Review it in What changed" if n == 1 else f"Review the {n} in What changed")
        self.b_done.setProperty("kind", "ghost" if n else "primary")
        self.b_done.setDefault(not n); self.b_compare.setDefault(bool(n))
        self.b_done.style().unpolish(self.b_done); self.b_done.style().polish(self.b_done)

    def no_longer_ids(self):
        return [self.confirm.item(i).data(Qt.UserRole) for i in range(self.confirm.count())
                if self.confirm.item(i).checkState() == Qt.Checked]

    def keep(self):
        """The ticked documents are marked no longer in force. Returns how many."""
        ids = self.no_longer_ids()
        if not ids:
            return 0
        n = DP.not_in_force(self.page.lib, self.page.effort_rec(), ids, self.release)
        if n:
            diag.activity("documents_not_in_force", n=n)
            self.page.fill()
            self.host.toast(f"{n} document" + ("" if n == 1 else "s") + f" no longer in force with {self.release}")
        return n

    def done_now(self):
        self.keep()
        self.accept()

    def compare_now(self):
        pairs = self.ticked()
        self.keep()
        self.accept()
        if not pairs:
            return []
        diag.activity("intake_compare", n=len(pairs))
        self.host.go("compare")
        return self.host.compare_page.compare_these(pairs, self.release)

    def version_menu(self, pos, run=True):
        it = self.versions.itemAt(pos)
        if it is None:
            return None
        m = QMenu(self)
        did, _a, b = it.data(Qt.UserRole)
        d = self.page.lib.doc(did) or {}
        vb = next((x for x in d.get("versions") or [] if x["id"] == b), {})
        act = m.addAction("Show on the page", lambda: self.on_page(vb.get("file", "")))
        act.setEnabled(self.host.review is not None and bool(vb.get("file")))
        if run:
            m.exec(self.versions.viewport().mapToGlobal(pos))
        return m

    def notice_menu(self, pos, run=True):
        """4.86.0: right-click a change notice: Show on the page; Apply its instructions... for an amendment that has them."""
        it = self.notices.itemAt(pos)
        if it is None:
            return None
        did, file, n_ins = it.data(Qt.UserRole)
        m = QMenu(self)
        act = m.addAction("Show on the page", lambda: self.on_page(file))
        act.setEnabled(self.host.review is not None and bool(file))
        if n_ins:
            m.addAction("Apply its instructions...", lambda: self.apply_instructions(did))
        if run:
            m.exec(self.notices.viewport().mapToGlobal(pos))
        return m

    def apply_instructions(self, doc_id, answer=None):
        """Close the summary and open Apply its instructions for the amendment (Documents' own window)."""
        self.keep()
        self.accept()
        self.page.select(doc_id)
        return self.page.conform(answer=answer)

    def on_page(self, file):
        self.keep()
        self.accept()
        self.host.go("assign")
        return self.host.assign_page.open_file(file)
