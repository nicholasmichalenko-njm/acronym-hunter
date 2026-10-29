"""Change review in Compare (2.85.0): see the change in its place in both versions, see where every change sits in the
document, and give each change a decision that lands where people work (changereview has the rules).

- ChangeStrip: a strip beside the list, top to bottom like the document, with a mark per change in its color (changed
  amber, added green, removed red; a decided change is pale). Click a mark to go to it.
- SideBySide: the older and newer version side by side around the change (two sentences before and after), the
  removed words struck through in red on the left and the new words in green on the right.
- DecidePanel: the decisions on the selected change, and the buttons: Updates a requirement, New requirement, Context
  for a requirement, Removes a requirement, Task, Question, Note, No action (with why).
Rules only (No AI); nothing leaves the PC."""
import datetime
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QScrollArea, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)
import diag
import changereview as CR
from . import design as D

COLORS = {"changed": "warn", "added": "ok", "removed": "crit"}
TAG_NAMES = {"req": "REQ", "rule": "RULE", "deliv": "DELIV", "term": "TERM", "new": "NEW"}


def _words(s):
    import re
    return set(re.findall(r"[A-Za-z0-9&]+", s or ""))


def tag_rows(rows, links, impact):
    """What each change touches: req (a compliance requirement), new (an added sentence not in the matrix), rule (a
    submission rule), deliv (a deliverable), term (a term new in this version). [tuple of tags] aligned with rows."""
    rules = (impact or {}).get("requirements", [])
    dels = (impact or {}).get("deliverables", [])
    terms = {t["term"] if isinstance(t, dict) else t for t in ((impact or {}).get("acronyms") or {}).get("new", [])}
    out = []
    for i, r in enumerate(rows):
        if r["kind"] == "same":
            out.append(())
            continue
        tg = []
        txt = (r.get("new") or "") + " " + (r.get("old") or "")
        if i < len(links) and links[i]:
            tg.append("req")
        elif r["kind"] == "added":
            tg.append("new")
        rule_hit = r.get("submission") or any(q.get("sentence") and q["sentence"] in txt for q in rules)
        if rule_hit:
            tg.append("rule")
            if dels and any(("page" in txt.lower() and "limit" in " ".join(d_["why"]).lower()) or d_["name"].lower() in txt.lower()
                            for d_ in dels):
                tg.append("deliv")
        elif any(d_["name"].lower() in txt.lower() for d_ in dels):
            tg.append("deliv")
        if terms and (_words(r.get("new")) & terms):
            tg.append("term")
        out.append(tuple(tg))
    return out


class SummaryStrip(QWidget):
    """2.85.0: what the version touches, on one line of chips (what Impact review was for). Click one to filter."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.h = QHBoxLayout(self); self.h.setContentsMargins(0, 0, 0, 0); self.h.setSpacing(D.SPACE["s"])
        self.chips = {}

    def fill(self):
        pg = self.page
        while self.h.count():
            w = self.h.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        self.chips = {}
        rows = pg.rows or []
        if not rows:
            self.hide()
            return
        self.show()
        tags = getattr(pg, "tags", [])
        n = sum(1 for r in rows if r["kind"] != "same")
        cnt = lambda t: sum(1 for x in tags if t in x)                       # noqa: E731
        im = getattr(pg, "impact", None) or {}
        owners = sorted({h["owner"] for ls in pg.links for h in ls if h.get("owner")})
        rules = sorted({q["subject"] for q in im.get("requirements", [])})
        dels = sorted({d_["name"] for d_ in im.get("deliverables", [])})
        terms = [t["term"] if isinstance(t, dict) else t for t in (im.get("acronyms") or {}).get("new", [])]
        undec = sum(1 for r in rows if r["kind"] != "same" and not pg.decided_text(r.get("key", "")))
        items = [("all", f"{n} changes", ""), ("req", f"{cnt('req')} compliance requirements", ", ".join(owners[:3])),
                 ("new", f"{cnt('new')} not in the matrix yet", ""),
                 ("rule", f"{cnt('rule')} submission rules", ", ".join(rules[:3])),
                 ("deliv", f"{cnt('deliv')} deliverables", ", ".join(dels[:2])), ("term", f"{cnt('term')} new terms", ", ".join(terms[:3])),
                 ("open", f"{undec} to decide", "")]
        for key, text, sub in items:
            if key not in ("all", "open") and not cnt(key):
                continue
            b = D.button(text + (f"  \u00b7  {sub}" if sub else ""), "primary" if pg.tag_filter == key else None,
                         lambda _=False, k=key: pg.set_tag_filter(k))
            self.chips[key] = b
            self.h.addWidget(b)
        self.h.addStretch(1)


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ChangeStrip(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setFixedWidth(16)
        self.setToolTip("Where the changes are, top to bottom like the document. Click one to go to it.")

    def marks(self):
        rows = self.page.rows or []
        n = max(1, len(rows))
        return [(i, r, i / n) for i, r in enumerate(rows) if r["kind"] != "same"]

    def paintEvent(self, _e):
        p = QPainter(self)
        t = D.tokens()
        p.fillRect(self.rect(), QColor(t["surface2"]))
        h = max(1, self.height() - 4)
        cur = self.page.current_index()
        for i, r, f in self.marks():
            col = QColor(t[COLORS[r["kind"]]])
            if self.page.decided_text(r.get("key", "")):
                col.setAlpha(90)
            y = 2 + f * h
            p.fillRect(QRectF(2, y, self.width() - 4, 3 if i != cur else 6), col)
        p.end()

    def mousePressEvent(self, e):
        ms = self.marks()
        if not ms:
            return
        h = max(1, self.height() - 4)
        y = (e.position().y() - 2) / h
        i = min(ms, key=lambda m: abs(m[2] - y))[0]
        if i not in self.page.shown:
            self.page.only.setChecked(True); self.page.undec.setChecked(False); self.page.in_matrix.setChecked(False)
        self.page.select_index(i)


class SideBySide(QWidget):
    def __init__(self):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)
        self.left, self.right = QTextBrowser(), QTextBrowser()
        for b, title in ((self.left, "Was"), (self.right, "Now")):
            col = QVBoxLayout(); col.setSpacing(2)
            lab = D.label(title, "label", wrap=False); col.addWidget(lab)
            col.addWidget(b, 1)
            h.addLayout(col, 1)
            if b is self.left:
                self.l_title = lab
            else:
                self.r_title = lab

    def clear(self):
        self.left.setHtml(""); self.right.setHtml("")

    @staticmethod
    def _around(sents, i, mark_html, ctx=2):
        t = D.tokens()
        out = []
        for k in range(max(0, i - ctx), min(len(sents), i + ctx + 1)):
            txt = sents[k].get("x", "")
            if k == i:
                out.append(f"<p style='background:{t['warn_soft']};padding:4px'>{mark_html}</p>")
            else:
                out.append(f"<p style='color:{t['muted']}'>{_esc(txt)}</p>")
        return "".join(out)

    def show_change(self, r, texts, va, vb):
        t = D.tokens()
        old, new = texts
        self.l_title.setText(f"WAS: {va['label'].upper()}" if va else "WAS")
        self.r_title.setText(f"NOW: {vb['label'].upper()}" if vb else "NOW")
        dl, dr = [], []
        for k, txt in r.get("diff") or []:
            if k == "=":
                dl.append(_esc(txt)); dr.append(_esc(txt))
            elif k == "-":
                dl.append(f"<span style='color:{t['crit']};text-decoration:line-through;font-weight:600'>{_esc(txt)}</span>")
            else:
                dr.append(f"<span style='color:{t['ok']};font-weight:600'>{_esc(txt)}</span>")
        oi, nj = r.get("oi"), r.get("nj")
        if r["kind"] == "changed":
            self.left.setHtml(self._around(old, oi, " ".join(dl)))
            self.right.setHtml(self._around(new, nj, " ".join(dr)))
        elif r["kind"] == "removed":
            self.left.setHtml(self._around(old, oi, f"<span style='color:{t['crit']};text-decoration:line-through'>{_esc(r['old'])}</span>"))
            self.right.setHtml(f"<p style='color:{t['crit']}'><b>Removed.</b> The newer version does not have this sentence.</p>")
        elif r["kind"] == "added":
            self.left.setHtml(f"<p style='color:{t['ok']}'><b>Added.</b> The older version does not have this sentence.</p>")
            self.right.setHtml(self._around(new, nj, f"<span style='color:{t['ok']};font-weight:600'>{_esc(r['new'])}</span>"))
        else:
            self.left.setHtml(self._around(old, oi, _esc(r["old"])) if oi is not None else "")
            self.right.setHtml(self._around(new, nj, _esc(r["new"])) if nj is not None else "")


class DecidePanel(QScrollArea):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.i = None
        self.setWidgetResizable(True)
        w = QWidget(); self.setWidget(w)
        v = QVBoxLayout(w); v.setAlignment(Qt.AlignTop); v.setSpacing(D.SPACE["s"])
        self.title = D.label("Click a change", "title"); v.addWidget(self.title)
        self.done = QVBoxLayout(); v.addLayout(self.done)
        v.addWidget(D.label("Requirement (for update, context or removal)", "label", wrap=False))
        self.req = QComboBox(); v.addWidget(self.req)
        v.addWidget(D.label("Section (for a new requirement)", "label", wrap=False))
        self.sec = QComboBox(); v.addWidget(self.sec)
        self.why = QLineEdit(); self.why.setPlaceholderText("Why (optional; for No action, the reason: editorial, not ours...)")
        v.addWidget(self.why)
        g = QGridLayout(); g.setSpacing(4); v.addLayout(g)
        self.btns = {}
        for k, (kind, tone) in enumerate((("updates", "req"), ("new", "req"), ("rule", None), ("context", "ctx"), ("removes", "danger"),
                                          ("task", None), ("question", "cust"), ("note", None), ("none", "ghost"))):
            b = D.button(CR.KIND_NAMES[kind], tone, lambda _=False, kd=kind: self.decide(kd))
            g.addWidget(b, k // 2, k % 2)
            self.btns[kind] = b
        self.hint = D.label("", "muted"); v.addWidget(self.hint)
        self.show_change(None)

    # ------------------------------------------------------------ fill
    def show_change(self, i):
        self.i = i
        pg = self.page
        while self.done.count():
            x = self.done.takeAt(0).widget()
            if x is not None:
                x.setParent(None)
        r = pg.rows[i] if i is not None and i < len(pg.rows) else None
        on = r is not None and r["kind"] != "same"
        for b in self.btns.values():
            b.setEnabled(on)
        tags = pg.tags[i] if (r is not None and i < len(getattr(pg, "tags", []))) else ()
        self.btns["rule"].setVisible("rule" in tags)
        self.req.setEnabled(on); self.sec.setEnabled(on); self.why.setEnabled(on)
        if r is None:
            self.title.setText("Click a change"); self.hint.setText("Each change gets a decision; Compare counts what is left.")
            return
        if not on:
            self.title.setText("Unchanged sentence"); self.hint.setText("")
            return
        self.title.setText({"changed": "Changed", "added": "Added", "removed": "Removed"}[r["kind"]] + " sentence: what does it mean?")
        decs = pg.review.decisions(pg.pk, r["key"])
        from .assign import Chip
        for x in decs:
            text = CR.KIND_NAMES[x["kind"]] + (f": {x['target']}" if x.get("target") else "") + (f" ({x['why']})" if x.get("why") else "") \
                + f"  ·  {x.get('who', '')} {x.get('when', '')[:10]}"
            self.done.addWidget(Chip(text, "ok", on_remove=lambda _=False, did=x["id"]: self.undo(did)))
        self.fill_targets(i)
        self.hint.setText("Decided. Add another decision if it means more than one thing." if decs else
                          "Several decisions can apply to one change. Each keeps who, when and why.")

    def fill_targets(self, i):
        pg = self.page
        M = pg.host.review.M if pg.host.review is not None else None
        self.req.clear(); self.sec.clear()
        if M is None:
            self.req.addItem("(no compliance matrix yet: Read RFP)", "")
            self.sec.addItem("(no compliance matrix yet)", "")
            return
        linked = [h["id"] for h in (pg.links[i] if i < len(pg.links) else [])]
        for rid in linked:
            it = pg.host.review.item(rid)
            if it is not None:
                self.req.addItem(f"{rid}  (touched)  {it.get('map', '')}: {it['text'][:60]}", rid)
        for it in M.items:
            if it.get("decision") == "Keep" and it["id"] not in linked:
                self.req.addItem(f"{it['id']}  {it.get('map', '')}: {it['text'][:60]}", it["id"])
        import compliance as C
        target = pg.host.assign_page.target
        for o in M.outline:
            lab = C.outline_label(o)
            self.sec.addItem(lab, lab)
        if target:
            self.sec.setCurrentIndex(max(0, self.sec.findData(target)))

    # ------------------------------------------------------------ decide
    def decide(self, kind, target=None, why=None, i=None):
        """Give the selected change (or row i) a decision; it lands where it belongs. Returns the decision."""
        pg = self.page
        i = self.i if i is None else i
        if i is None:
            return None
        r = pg.rows[i]
        d, va, vb = pg.cur
        why = self.why.text() if why is None else why
        if kind == "none" and not why.strip():
            why = "editorial"
        if target is None:
            target = self.req.currentData() if kind in ("updates", "context", "removes") else self.sec.currentData() if kind == "new" else ""
        M = pg.host.review.M if pg.host.review is not None else None
        if kind in CR.NEEDS_TARGET and (M is None or not target):
            pg.host.status("Pick the requirement (or the section) first." if M is not None else "Read RFP first: decisions on requirements need the matrix.")
            return None
        rv = pg.review
        ref = ""
        if kind == "updates":
            if not r.get("new"):
                pg.host.status("A removed sentence cannot update a requirement: use Removes a requirement.")
                return None
            e = CR.apply_update(M, rv, target, r["new"], d["name"], vb["label"])
            ref = e["id"] if e else ""
        elif kind == "removes":
            e = CR.apply_remove(M, rv, target, d["name"], vb["label"])
            ref = e["id"] if e else ""
        elif kind == "new":
            text = r.get("new") or r.get("old")
            ref = self._new_requirement(M, d, vb, text, target, r)
            if not ref:
                return None
        elif kind == "context":
            ref = self._context(d, vb, r, target)
        elif kind in ("task", "question", "note"):
            ref = self._record(kind, d, vb, r)
        elif kind == "rule":
            ref = self._rule(r, vb)
        dec = rv.decide(pg.pk, r["key"], kind, target or "", why, ref)
        self.why.clear()
        diag.activity("change_decided")
        if kind in ("updates", "removes", "new"):
            pg.host.changed()
        dn, n = rv.progress(pg.pk, pg.rows)
        if n and dn == n:
            try:
                pg.ctx.lib.mark_reviewed(vb["id"])
            except Exception:
                diag.swallowed()
            pg.host.toast(f"Every change from {va['label']} to {vb['label']} is decided: the version is marked reviewed")
        k = pg.table.currentRow()
        pg.fill()
        if 0 <= k < pg.table.rowCount():
            pg.table.selectRow(k)
        elif pg.shown:
            pg.table.selectRow(min(k, len(pg.shown) - 1))
        return dec

    def _rule(self, r, vb):
        """The submission rules this change sets take the new value: reviewed in Submission rules; a new due date becomes
        the effort's due date."""
        pg = self.page
        reg = pg.ctx.reg
        txt = (r.get("new") or "") + " " + (r.get("old") or "")
        keys = []
        for q in ((getattr(pg, "impact", None) or {}).get("requirements", [])):
            if (q.get("sentence") and q["sentence"] in txt) or (q.get("now") and q["now"] in txt):
                keys.append(q["key"])
        for k in keys:
            reg.review(k)
            if k == "Due | Proposal":
                q = next(x for x in pg.impact["requirements"] if x["key"] == k)
                import effortrec as R_
                iso, zone = R_.parse_due_text(q["now"])
                if iso:
                    pg.ctx.rec.set_due(iso, zone)
        pg.host.status(f"{len(keys)} submission rule(s) updated" if keys else "Marked: this change updates a submission rule.")
        return ",".join(keys)

    def _quote(self, d, vb, r):
        return f"\"{(r.get('new') or r.get('old'))[:400]}\" ({d['name']} {vb['label']}, {r['kind']})"

    def _new_requirement(self, M, d, vb, text, section, r):
        import capture as CAP
        f = vb.get("file", "")
        if not any(s_ and s_[0] == f for s_ in M.sources):
            M.sources.append([f, vb.get("sha256", ""), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), vb.get("path", "")])
        R = self.page.host.review
        R.snap()
        it = CAP.add_sentence(M, f, text, how="typed")
        if it is None:
            return ""
        it["loc"] = f"{f} ({r.get('section') or vb['label']}, from Change review)"
        it["new"] = f"New in {d['name']} {vb['label']}"
        R.req([it], section)
        self.page.review.add_history(it["id"], "added", "", it["text"], d["name"], vb["label"])
        return it["id"]

    def _context(self, d, vb, r, req):
        import ctxdocs as CX
        lib = self.page.ctx.lib
        nj = r.get("nj") if r.get("nj") is not None else r.get("oi")
        row = next((x for x in CX.items_of(lib, d, vb) if x["n"] == nj), None)
        if row is None:
            return ""
        a = CX.Store(self.page.host.ws.root).load().attach(row, "requirement", req)
        return a["id"] if a else ""

    def _record(self, kind, d, vb, r):
        import effortrec as R_
        rec = R_.Record(self.page.host.ws.root)
        q = self._quote(d, vb, r)
        if kind == "task":
            return rec.add_task(f"Act on a change in {d['name']} {vb['label']}", notes=q) or ""
        return rec.add_note(q, on="version", on_id=vb["id"], label=f"{d['name']} {vb['label']}", question=kind == "question") or ""

    def undo(self, dec_id):
        pg = self.page
        r = pg.rows[self.i]
        gone = pg.review.undo(pg.pk, r["key"], dec_id)
        if gone is None:
            return False
        M = pg.host.review.M if pg.host.review is not None else None
        if gone["kind"] in ("updates", "removes") and M is not None:
            CR.undo_effect(M, pg.review, gone)
            pg.host.changed()
        elif gone["kind"] == "new" and M is not None and pg.host.review.item(gone.get("ref", "")) is not None:
            pg.host.review.clear([pg.host.review.item(gone["ref"])])
            pg.host.changed()
        elif gone["kind"] == "context" and gone.get("ref"):
            import ctxdocs as CX
            CX.Store(pg.host.ws.root).load().remove(att_id=gone["ref"])
        diag.activity("change_decision_undone")
        k = pg.table.currentRow()
        pg.fill()
        if 0 <= k < pg.table.rowCount():
            pg.table.selectRow(k)
        return True


# ====================================================================== requirement history
class HistoryDialog(QDialog):
    """Every requirement a version changed, removed or added, with its history; confirm that the answer still fits."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.setWindowTitle("Requirement history"); self.resize(1100, 560)
        self.rv = CR.Review(page.host.ws.root).load()
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each requirement a customer version touched: what it said, what it says now, which version did it, "
                            "and whether its owner has confirmed the answer still fits.", "muted"))
        bar = QHBoxLayout(); v.addLayout(bar)
        self.only = QComboBox(); self.only.addItems(["Every requirement with a history", "Awaiting the owner"])
        self.only.currentIndexChanged.connect(lambda _i: self.fill()); bar.addWidget(self.only); bar.addStretch(1)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Requirement", "What happened", "By", "Was", "Now", "Owner confirmed", "When"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(True)
        for c, wdt in ((0, 90), (1, 110), (2, 150), (5, 150), (6, 110)):
            self.table.setColumnWidth(c, wdt)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch); self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        v.addWidget(self.table, 1)
        row = QHBoxLayout(); v.addLayout(row)
        self.count = D.label("", "muted", wrap=False); row.addWidget(self.count); row.addStretch(1)
        row.addWidget(D.button("Confirm it still fits", "primary", lambda: self.confirm(), "The owner checked the answer against the new wording"))
        row.addWidget(D.button("Open in Assign", None, lambda: self.open()))
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); row.addWidget(bb)
        self.fill()

    def fill(self):
        wait = set(self.rv.awaiting())
        rows = []
        for rid, es in self.rv.lineage.items():
            if self.only.currentIndex() == 1 and rid not in wait:
                continue
            for e in es:
                rows.append((rid, e))
        self.rows = rows
        self.table.setRowCount(len(rows))
        names = {"updated": "Wording changed", "removed": "Removed", "added": "Added"}
        for k, (rid, e) in enumerate(rows):
            vals = (rid, names.get(e["kind"], e["kind"]), f"{e.get('doc', '')} {e.get('label', '')}", e.get("old", ""), e.get("new", ""),
                    e.get("confirmed", "") or ("awaiting the owner" if e["kind"] in ("updated", "removed") else ""), e.get("when", "")[:10])
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 5 and not e.get("confirmed") and e["kind"] in ("updated", "removed"):
                    it.setForeground(D.color("warn"))
                self.table.setItem(k, c, it)
        self.table.resizeRowsToContents()
        self.count.setText(f"{len(wait)} awaiting the owner")
        return len(rows)

    def current(self):
        k = self.table.currentRow()
        return self.rows[k][0] if 0 <= k < len(self.rows) else None

    def confirm(self, rid=None):
        rid = rid or self.current()
        if rid and self.rv.confirm(rid):
            M = self.page.host.review.M if self.page.host.review is not None else None
            it = self.page.host.review.item(rid) if M is not None else None
            if it is not None and (it.get("new") or "").endswith("owner to confirm"):
                it["new"] = it["new"].replace("owner to confirm", "owner confirmed")
                M.pending = True
                self.page.host.changed()
            diag.activity("change_confirmed")
            self.fill()
            return True
        return False

    def open(self):
        rid = self.current()
        if rid:
            self.accept()
            self.page.open_item(rid)


def history_dialog(page, run=True):
    if page.host.ws is None:
        return None
    dlg = HistoryDialog(page)
    if run:
        dlg.exec()
    return dlg
