"""Shred > Evaluation (3.63.0; 4.1.0 moved from Matrix & Outline): how the customer will judge the proposal. The factors and subfactors with their
importance (captured in Review or added here), the deliverables each one judges, and the evaluation sentences from Review
(Section M) to make into factors. custfocus holds the rules."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLineEdit, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)
import custfocus as F
import deliverables as DL
import diag
import effortrec as R
import shredtypes as ST
from . import design as D


class EvalPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.ids, self.m_ids = [], []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.sumlab = D.label("", "title"); v.addWidget(self.sumlab)
        v.addWidget(D.label("The factors and subfactors the customer will score, with their relative importance, and the "
                            "deliverables each one judges. Capture them in the shred (More captures > Evaluation factor) or add "
                            "them here; make one from an evaluation piece below.", "muted"))
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["Factor", "Importance", "Judges", "From"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        v.addWidget(self.table, 2)
        add = QHBoxLayout(); add.setSpacing(D.SPACE["s"]); v.addLayout(add)
        self.f_name = QLineEdit(); self.f_name.setPlaceholderText("Factor or subfactor (for example Technical Approach)"); add.addWidget(self.f_name, 2)
        self.f_parent = QComboBox(); add.addWidget(self.f_parent, 1)
        self.f_imp = QComboBox(); self.f_imp.addItems(F.IMPORTANCE); self.f_imp.setCurrentText("Not stated"); add.addWidget(self.f_imp, 1)
        add.addWidget(D.button("Add", "primary", lambda: self.add(self.f_name.text(), self.f_parent.currentData() or "", self.f_imp.currentText())))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); v.addLayout(row)
        row.addWidget(D.button("Deliverables it judges...", None, lambda: self.tie_dialog()))
        self.imp_set = QComboBox(); self.imp_set.addItems(F.IMPORTANCE)
        row.addWidget(self.imp_set)
        row.addWidget(D.button("Set importance", "ghost", lambda: self.set_importance(self.imp_set.currentText())))
        row.addWidget(D.button("Remove", "danger", lambda: self.remove()))
        row.addStretch(1)
        # 4.29.4 (the capture audit, Nicholas 2026-11-13): a Hot button captured in Shred is read here. Before, only All
        # cards showed it, and All cards retires.
        self.hot_title = D.SectionTitle("Hot buttons"); v.addWidget(self.hot_title)
        self.hot_list = D.label("", None); self.hot_list.setWordWrap(True); self.hot_list.setTextFormat(Qt.RichText)
        self.hot_list.linkActivated.connect(lambda h: self.remove_hot(h))
        v.addWidget(self.hot_list)
        v.addWidget(D.SectionTitle("Evaluation pieces from the shred (Section M, and pieces said to be an Evaluation Criterion)"))
        self.mtab = QTableWidget(0, 3); self.mtab.setHorizontalHeaderLabels(["ID", "The customer's words", "In the shred"])
        self.mtab.verticalHeader().setVisible(False); self.mtab.setEditTriggers(QTableWidget.NoEditTriggers)
        self.mtab.setSelectionBehavior(QTableWidget.SelectRows); self.mtab.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.mtab, 2)
        mr = QHBoxLayout(); v.addLayout(mr)
        mr.addWidget(D.button("Make it a factor", None, lambda: self.from_sentence()))
        mr.addWidget(D.button("Show it on the page", "ghost", lambda: self.open_in_review()))
        mr.addStretch(1)

    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        r = self.rec()
        self.setEnabled(r is not None)
        if r is None:
            return
        self.fill_hot(r)
        fs = F.factors(r)
        names = {d["id"]: d["name"] for d in DL.items(r)}
        self.ids = [f["id"] for f in fs]
        self.table.setRowCount(len(fs))
        for i, f in enumerate(fs):
            tied = ", ".join(names[x] for x in f.get("deliverables") or [] if x in names)
            vals = [("    " if f.get("parent") else "") + f["name"], f.get("importance", "Not stated"), tied or "not tied yet",
                    f.get("doc") or "added here"]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(val); it.setToolTip(f.get("text", ""))
                if j == 2 and not tied:
                    it.setForeground(D.color("muted"))
                self.table.setItem(i, j, it)
        self.f_parent.clear(); self.f_parent.addItem("(a factor)", "")
        for f in fs:
            if not f.get("parent"):
                self.f_parent.addItem("under " + f["name"], f["id"])
        tops = sum(1 for f in fs if not f.get("parent"))
        self.sumlab.setText(f"{tops} factor(s), {len(fs) - tops} subfactor(s)" if fs else "No evaluation factors yet")
        M = self.host.review.M if self.host.review is not None else None
        ms = F.m_items(M)
        tnames = {k: v["name"] for k, v in ST.load(self.host.config_dir).items()}      # 4.1.0: what the shred said it is
        self.m_ids = [it["id"] for it in ms]
        self.mtab.setRowCount(len(ms))
        for i, it in enumerate(ms):
            ts = ST.types_of(it)                                                     # 4.5.0: every type it has
            for j, val in enumerate((it["id"], it.get("text", ""), ", ".join(tnames.get(t, t) for t in ts) or "not shredded yet")):
                self.mtab.setItem(i, j, QTableWidgetItem(val))

    def fill_hot(self, r):
        """The hot buttons captured in Shred: what the customer cares about most, each with where it was said."""
        import html
        hs = F.hot_buttons(r)
        rows = []
        for h in hs:
            where = " ".join(x for x in (h.get("doc", ""), h.get("loc", "")) if x)
            rows.append(f"<b>{html.escape(h.get('text', ''))}</b>" + (f" &nbsp;<span style='color:{D.tokens()['muted']}'>{html.escape(where)}</span>" if where else "")
                        + f" &nbsp;<a href='{html.escape(h.get('id', ''))}'>Remove</a>")
        self.hot_list.setText("<br>".join(rows) if rows else
                              f"<span style='color:{D.tokens()['muted']}'>None yet. In Shred, select a piece and pick Capture &gt; Hot button.</span>")
        self.hots = hs
        return hs

    def remove_hot(self, hid):
        r = self.rec()
        if r is None or not F.remove_hot(r, hid):
            return False
        self.refresh()
        return True

    def current(self):
        i = self.table.currentRow()
        return self.ids[i] if 0 <= i < len(self.ids) else None

    def add(self, name, parent="", importance="Not stated"):
        fid = F.add_factor(self.rec(), name, parent, importance)
        if fid:
            diag.activity("eval_factor_added")
            self.f_name.clear()
        self.refresh()
        return fid

    def set_importance(self, imp, fid=None):
        fid = fid or self.current()
        ok = F.update_factor(self.rec(), fid, importance=imp) if fid else False
        self.refresh()
        return ok

    def remove(self, fid=None):
        fid = fid or self.current()
        ok = F.remove_factor(self.rec(), fid) if fid else False
        self.refresh()
        return ok

    def tie_dialog(self, fid=None, answer=None):
        """The deliverables a factor judges. answer (tests): deliverable ids."""
        fid = fid or self.current()
        r = self.rec()
        f = F.factor(r, fid) if fid else None
        if f is None:
            self.host.status("Pick a factor first.")
            return None
        if answer is None:
            d = QDialog(self); d.setWindowTitle(f"What {f['name']} judges"); v = QVBoxLayout(d)
            boxes = []
            for x in DL.items(r):
                cb = QCheckBox(x["name"]); cb.setChecked(x["id"] in (f.get("deliverables") or [])); cb.did = x["id"]
                v.addWidget(cb); boxes.append(cb)
            if not boxes:
                v.addWidget(D.label("No deliverables yet. Add them on Deliverables.", "muted"))
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = [cb.did for cb in boxes if cb.isChecked()]
        F.tie(r, fid, answer)
        diag.activity("eval_factor_tied")
        self.refresh()
        return answer

    def from_sentence(self, iid=None):
        i = self.mtab.currentRow()
        iid = iid or (self.m_ids[i] if 0 <= i < len(self.m_ids) else None)
        M = self.host.review.M if self.host.review is not None else None
        it = next((x for x in (M.items if M is not None else []) if x["id"] == iid), None)
        if it is None:
            return None
        g = F.factor_guess(it.get("text", "")) or {}
        name = g.get("name") or it.get("text", "")[:60]
        fid = F.add_factor(self.rec(), name, "", g.get("importance") or F.importance_guess(it.get("text", "")) or "Not stated",
                           it.get("text", ""), {"doc": it.get("doc", ""), "loc": it.get("loc", ""), "sid": it["id"]})
        self.refresh()
        return fid

    def open_in_review(self):
        i = self.mtab.currentRow()
        if 0 <= i < len(self.m_ids):
            self.host.go("assign")
            self.host.assign_page.select(self.m_ids[i])
            return True
        return False
