"""The decide bar in Compare (3.89.0, claude/stationkeeper-compare-on-the-page-plan-3.89.md): opened beside the selected
change, never over it. It shows the change in words (the old words struck, the new marked), the suggested choice with its
reason, and three choices (4.1.0): No impact, Re-shred (into Shred's queue), Ask a question; More holds Update our
wording, Add to a section, Remove, Context for a requirement, Updates a submission rule, Task and Note. A click on a sentence or a section in Our response
changes the target. Enter takes the suggestion and goes on to the next change to decide. Decisions already taken show as
chips, each with its undo. Every decision lands where people work (changereview has the rules).
Rules only (No AI); nothing leaves the PC."""
import datetime
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QMenu, QVBoxLayout, QWidget

import diag
import changereview as CR
from . import design as D
from .adaptive import FlowLayout

# 4.1.0 (claude/stationkeeper-shred-plan-4.1.md, step 7): three ways lead; the full list is under More
MAIN = (("none", "No impact", "Recorded with the reason, so the question never comes back"),
        ("reshred", "Re-shred", "The passage joins Shred's queue with its old and new wording; the requirement built from it "
         "shows Changed by this version until it is shredded again"),
        ("question", "Ask a question", "A question in the Q&A log, citing the old and the new wording"))
MORE = (("updates", "Update our wording"), ("new", "Add to a section"), ("removes", "Remove"),
        ("context", "Context for a requirement"), ("rule", "Updates a submission rule"), ("task", "Task"), ("note", "Note"))
WORDS = {"changed": "Changed", "added": "Added", "removed": "Removed"}


def diff_html(r):
    t = D.tokens()
    if r["kind"] == "added":
        return f"<span style='color:{t['ok']}'>{html.escape(r['new'])}</span>"
    if r["kind"] == "removed":
        return f"<span style='color:{t['crit']};text-decoration:line-through'>{html.escape(r['old'])}</span>"
    out = []
    import docversions as DV
    for k, s in DV.word_diff(r.get("old", ""), r.get("new", "")):
        if k == "=":
            out.append(html.escape(s))
        elif k == "-":
            out.append(f"<span style='color:{t['crit']};text-decoration:line-through'>{html.escape(s)}</span>")
        else:
            out.append(f"<b style='color:{t['ok']}'>{html.escape(s)}</b>")
    return " ".join(out)


class DecideBar(QFrame):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.i, self.sugg = None, None
        self.req_target, self.sec_target = "", ""
        self.why_text = ""
        self.setObjectName("cardhead")
        self.setAutoFillBackground(True)
        self.setStyleSheet("QFrame#cardhead { background: %s; border: 1px solid %s; border-radius: 6px; }"
                           % (D.tokens()["surface"], D.tokens()["border_strong"]))
        v = QVBoxLayout(self); v.setContentsMargins(8, 6, 8, 6); v.setSpacing(4)
        self.title = D.label("", "label"); v.addWidget(self.title)
        self.words = D.label("", None); self.words.setTextFormat(Qt.RichText); v.addWidget(self.words)
        self.hint = D.label("", "muted"); self.hint.setTextFormat(Qt.RichText); v.addWidget(self.hint)
        self.row = QWidget(); fl = FlowLayout(self.row, 4); v.addWidget(self.row)
        self.btns = {}
        for kind, text, tip in MAIN:
            b = D.button(text, None, lambda _=False, kd=kind: self.decide(kd), tip)
            fl.addWidget(b)
            self.btns[kind] = b
        self.b_more = D.button("More", None, None, "Other things a change can mean")
        self.more_menu = QMenu(self.b_more); self.b_more.setMenu(self.more_menu)
        self.more_acts = {}
        for kind, text in MORE:
            a = self.more_menu.addAction(text)
            a.triggered.connect(lambda _=False, kd=kind: self.decide(kd))
            self.more_acts[kind] = a
        fl.addWidget(self.b_more)
        self.chips = QWidget(); self.chips_l = QVBoxLayout(self.chips); self.chips_l.setContentsMargins(0, 0, 0, 0)
        self.chips_l.setSpacing(2); v.addWidget(self.chips)

    def measure(self, width):
        """The bar's height at this width, label by label (a wrapped rich-text label measures short in a layout)."""
        inner = width - 16 - 2
        h = 12 + 2
        shown = [w for w in (self.title, self.words, self.hint, self.row, self.chips) if not w.isHidden()]
        for w in shown:
            if w is self.row:
                hw = self.row.layout().heightForWidth(inner)
            elif w is self.chips:
                n = self.chips_l.count()
                hw = n * 28 + max(0, n - 1) * 2
            else:
                hw = w.heightForWidth(inner) if w.hasHeightForWidth() else w.sizeHint().height()
            h += max(hw, 0)
        return h + 4 * (len(shown) - 1) + 6

    # ------------------------------------------------------------ fill
    def show_change(self, i):
        self.i = i
        pg = self.page
        while self.chips_l.count():
            x = self.chips_l.takeAt(0).widget()
            if x is not None:
                x.setParent(None)
        r = pg.rows[i] if i is not None and 0 <= i < len(pg.rows) else None
        if r is None or r["kind"] == "same":
            self.sugg = None
            self.title.setText("")
            self.words.setText(""); self.hint.setText("")
            return
        links = pg.links[i] if i < len(pg.links) else []
        self.sugg = pg.suggest[i] if i < len(getattr(pg, "suggest", [])) else None
        placed = [h for h in links if h.get("map")]
        self.req_target = (self.sugg or {}).get("target") if (self.sugg or {}).get("kind") in ("updates", "removes") else \
            ((placed or links or [{}])[0].get("id", ""))
        self.sec_target = (self.sugg or {}).get("target", "") if (self.sugg or {}).get("kind") == "new" else ""
        where = r.get("section", "")
        self.title.setText(f"{WORDS[r['kind']]} piece" + (f", under {where}" if where else ""))
        self.words.setText(diff_html(r))
        for kind, b in self.btns.items():
            b.setProperty("kind", "primary" if self.sugg and self.sugg["kind"] == kind else "")
            b.style().unpolish(b); b.style().polish(b)
        self.more_acts["rule"].setVisible("rule" in (pg.tags[i] if i < len(getattr(pg, "tags", [])) else ()))
        self.more_acts["updates"].setEnabled(r["kind"] != "removed")
        self.more_acts["new"].setEnabled(r["kind"] != "removed")
        decs = pg.review.decisions(pg.pk, r["key"])
        from .assign import Chip
        for x in decs:
            text = CR.KIND_NAMES[x["kind"]] + (f": {x['target']}" if x.get("target") else "") + (f" ({x['why']})" if x.get("why") else "") \
                + f"  ·  {x.get('who', '')} {x.get('when', '')[:10]}"
            self.chips_l.addWidget(Chip(text, "ok", on_remove=lambda _=False, did=x["id"]: self.undo(did)))
        self.say_target()

    def say_target(self):
        r = self.page.rows[self.i] if self.i is not None else None
        if r is None:
            return
        bits = []
        if self.sugg:
            name = dict((k, t) for k, t, _x in MAIN).get(self.sugg["kind"]) or dict(MORE).get(self.sugg["kind"], "")
            bits.append(f"Suggested: <b>{html.escape(name)}</b>. {html.escape(self.sugg['why'])}. Enter takes it.")
        tg = []
        if self.req_target and r["kind"] != "added":
            it = self.page.item(self.req_target)
            tg.append(f"our piece <b>{html.escape(self.req_target)}</b>" + (f" in {html.escape(it['map'])}" if it and it.get("map") else ""))
        if self.sec_target:
            tg.append(f"section <b>{html.escape(self.sec_target)}</b>")
        if tg:
            bits.append("Target: " + ", ".join(tg))
        self.hint.setText("<br>".join(bits))
        self.hint.setToolTip("Click a piece or a section in Our response to change the target.")

    def set_req(self, iid):
        self.req_target = iid or ""
        self.say_target()

    def set_sec(self, label):
        self.sec_target = label or ""
        self.say_target()

    # ------------------------------------------------------------ decide
    def take(self):
        """Enter: the suggested choice, then the next change to decide."""
        if not self.sugg or self.i is None:
            return None
        dec = self.decide(self.sugg["kind"], self.sugg.get("target") or None, why="editorial" if self.sugg["kind"] == "none" else "")
        if dec:
            self.page.next_open()
        return dec

    def decide(self, kind, target=None, why=None, i=None):
        """Give the selected change (or row i) a decision; it lands where it belongs. Returns the decision."""
        pg = self.page
        i = self.i if i is None else i
        if i is None:
            return None
        r = pg.rows[i]
        d, va, vb = pg.cur
        why = self.why_text if why is None else why
        if kind == "none" and not (why or "").strip():
            why = "editorial"
        if target is None:
            target = self.req_target if kind in ("updates", "context", "removes") else self.sec_target if kind == "new" else ""
        M = pg.M()
        if kind in CR.NEEDS_TARGET and (M is None or not target):
            pg.host.status(("Click the section for it in Our response first." if kind == "new" else
                            "Click our piece for it in Our response first.") if M is not None else
                           "Read the documents into Shred first (Documents): decisions on requirements need the matrix.")
            return None
        rv = pg.review
        ref = ""
        if kind == "updates":
            if not r.get("new"):
                pg.host.status("A removed piece cannot update a requirement: use Remove.")
                return None
            e = CR.apply_update(M, rv, target, r["new"], d["name"], vb["label"])
            ref = e["id"] if e else ""
        elif kind == "removes":
            e = CR.apply_remove(M, rv, target, d["name"], vb["label"])
            ref = e["id"] if e else ""
        elif kind == "new":
            ref = self._new_requirement(M, d, vb, r.get("new") or r.get("old"), target, r)
            if not ref:
                return None
        elif kind == "context":
            ref = self._context(d, vb, r, target)
        elif kind in ("task", "question", "note"):
            ref = self._record(kind, d, vb, r)
        elif kind == "reshred":                                        # 4.1.0: into Shred's queue
            import reshred as RS
            q = RS.Queue(pg.host.ws.root).load()
            e = q.add(pg.pk, r["key"], d["name"], vb["label"], r.get("old", ""), r.get("new", ""), r.get("section", ""),
                      self.req_target if r["kind"] != "added" else "")
            ref = e["id"]
            pg.host.status(f"In Shred's queue: {len(q.open_items())} to re-shred.")
        elif kind == "rule":
            ref = self._rule(r, vb)
        dec = rv.decide(pg.pk, r["key"], kind, target or "", why, ref)
        self.why_text = ""
        diag.activity("change_decided")
        if kind in ("updates", "removes", "new"):
            pg.host.changed()
        self.after(va, vb)
        pg.redraw(i)
        return dec

    def after(self, va, vb):
        pg = self.page
        dn, n = pg.review.progress(pg.pk, pg.rows)
        if n and dn == n:
            try:
                pg.ctx.lib.mark_reviewed(vb["id"])
            except Exception:  # noqa: BLE001
                diag.swallowed()
            pg.host.toast(f"Every change from {va['label']} to {vb['label']} is decided: the version is marked reviewed")

    def no_action_all(self, keys):
        """No action (editorial) for each of these changes still to decide. Returns how many."""
        pg = self.page
        n = 0
        for i, r in enumerate(pg.rows):
            if r["key"] in keys and not pg.review.decisions(pg.pk, r["key"]):
                pg.review.decide(pg.pk, r["key"], "none", "", "editorial", "", save=False)
                n += 1
        pg.review.save()
        d, va, vb = pg.cur
        self.after(va, vb)
        diag.activity("change_editorial_all", n=n)
        return n

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
        it["loc"] = f"{f} ({r.get('section') or vb['label']}, from Changes)"
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
        nid = rec.add_note(q, on="version", on_id=vb["id"], label=f"{d['name']} {vb['label']}", question=kind == "question") or ""
        if kind == "question":                                         # 2.98.0: a draft in the Q&A log, quoting the change
            import custqa as Q
            rec = R_.Record(self.page.host.ws.root)
            words = r.get("new") or r.get("old") or ""
            if r.get("old") and r.get("new") and r["old"] != r["new"]:  # 4.1.0: both wordings
                words = f"{r['new']} (was: \u201c{r['old']}\u201d)"
            qid = Q.add(rec, "", words, doc=f"{d['name']} ({vb['label']})", section=r.get("section", ""),
                        category="Other")
            if qid:
                Q.get(rec, qid)["change_key"] = r.get("key", "")
                rec.save()
        return nid

    def undo(self, dec_id):
        pg = self.page
        if self.i is None:
            return False
        r = pg.rows[self.i]
        gone = pg.review.undo(pg.pk, r["key"], dec_id)
        if gone is None:
            return False
        M = pg.M()
        if gone["kind"] in ("updates", "removes") and M is not None:
            CR.undo_effect(M, pg.review, gone)
            pg.host.changed()
        elif gone["kind"] == "new" and M is not None and pg.host.review.item(gone.get("ref", "")) is not None:
            pg.host.review.clear([pg.host.review.item(gone["ref"])])
            pg.host.changed()
        elif gone["kind"] == "reshred":                                # 4.1.0: off Shred's queue
            import reshred as RS
            RS.Queue(pg.host.ws.root).load().drop(pg.pk, r["key"])
        elif gone["kind"] == "context" and gone.get("ref"):
            import ctxdocs as CX
            CX.Store(pg.host.ws.root).load().remove(att_id=gone["ref"])
        elif gone["kind"] == "question":                               # 2.98.0: its Customer Q&A draft, if still a draft
            import custqa as Q
            import effortrec as R_
            rec = R_.Record(pg.host.ws.root)
            for q in Q.items(rec):
                if q.get("change_key") == r.get("key") and q.get("status") == "Draft" and r.get("key"):
                    Q.remove(rec, q["id"])
        diag.activity("change_decision_undone")
        pg.redraw(self.i)
        return True

