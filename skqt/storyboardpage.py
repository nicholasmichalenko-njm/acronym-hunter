"""Deliver > Storyboards (3.2.0): one storyboard per section, the step between the Response Setup and the first draft.
Pick a section on the left (its status and page budget show); on the right, what the structure already says (lead,
writers, page budget, the requirements it answers, its graphic needs) and what the author writes: the key message, the
win themes it carries, the approach, features with benefits and proof, graphic ideas, and the status. Saved as you go
into the effort record. Export makes the Word storyboard for one section or a whole volume, a page per section."""
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLineEdit,
                               QPlainTextEdit, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import effortrec as R
import pagebudget as PB
import storyboard as SB
from . import design as D

TONE = {"Not started": "head", "Drafting": "accent", "Ready for review": "warn", "Approved": "ok"}


class StoryboardPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.label = None
        self._loading = False
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["l"], D.SPACE["m"], D.SPACE["l"], D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.counts = D.label("", "muted", wrap=False); top.addWidget(self.counts)
        top.addStretch(1)
        self.vol = QComboBox(); self.vol.setMinimumWidth(200); top.addWidget(D.label("Volume", "label", wrap=False)); top.addWidget(self.vol)
        top.addWidget(D.button("Export this section...", None, lambda: self.export(False), "This section's storyboard in Word"))
        top.addWidget(D.button("Export the volume...", "primary", lambda: self.export(True),
                               "Every section of the volume in one Word file, a page each, for the storyboard review"))
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Section", "Status", "Pages"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.setColumnWidth(1, 130); self.tree.setColumnWidth(2, 60)
        self.tree.currentItemChanged.connect(lambda cur, _p: self.pick(cur.data(0, Qt.UserRole) if cur else None))
        split.addWidget(self.tree)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame)
        form = QWidget(); form.setObjectName("page"); sc.setWidget(form); split.addWidget(sc)
        split.setSizes([380, 900])
        f = QVBoxLayout(form); f.setContentsMargins(D.SPACE["m"], 0, D.SPACE["m"], D.SPACE["m"]); f.setSpacing(D.SPACE["s"])
        self.title = D.label("", "display"); f.addWidget(self.title)
        self.facts = D.label("", "muted"); self.facts.setTextFormat(Qt.RichText); f.addWidget(self.facts)
        srow = QHBoxLayout(); f.addLayout(srow)
        srow.addWidget(D.label("Status", "label", wrap=False))
        self.status = QComboBox(); self.status.addItems(list(SB.STATUS)); srow.addWidget(self.status); srow.addStretch(1)
        f.addWidget(D.label("Key message", "label"))
        self.message = QLineEdit(); self.message.setPlaceholderText("The one thing the evaluator must take away from this section")
        f.addWidget(self.message)
        f.addWidget(D.label("Win themes this section carries", "label"))
        self.theme_box = QVBoxLayout(); self.theme_box.setSpacing(2); f.addLayout(self.theme_box)
        f.addWidget(D.label("Requirements to answer", "label"))
        self.reqs = D.label("", None); self.reqs.setTextFormat(Qt.RichText); self.reqs.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addWidget(self.reqs)
        f.addWidget(D.label("Approach", "label"))
        self.approach = QPlainTextEdit(); self.approach.setPlaceholderText("How we will do it, in the order the section will tell it")
        self.approach.setMinimumHeight(120); f.addWidget(self.approach)
        f.addWidget(D.label("Features, benefits and proof", "label"))
        t = QTableWidget(0, 3); t.setHorizontalHeaderLabels(["Feature (what we offer)", "Benefit (to the customer)", "Proof"])
        t.verticalHeader().setVisible(False); t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setMinimumHeight(150); t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.itemChanged.connect(lambda _it: self.changed())
        self.feat = t; f.addWidget(t)
        frow = QHBoxLayout(); f.addLayout(frow)
        frow.addWidget(D.button("+ Feature", None, lambda: self.add_feature())); frow.addWidget(D.button("Remove", "ghost", lambda: self.remove_feature()))
        frow.addStretch(1)
        f.addWidget(D.label("Graphics", "label"))
        self.gfx_list = D.label("", "muted"); f.addWidget(self.gfx_list)
        self.graphics = QPlainTextEdit(); self.graphics.setPlaceholderText("Graphic ideas, one a line (Graphic need in Review lists one "
                                                                            "for the graphics team)")
        self.graphics.setFixedHeight(80); f.addWidget(self.graphics)
        self.saved_lbl = D.label("", "muted"); f.addWidget(self.saved_lbl)
        f.addStretch(1)
        self.timer = QTimer(self, singleShot=True, interval=800, timeout=lambda: self.save())
        self.status.currentIndexChanged.connect(lambda _i: self.changed())
        self.message.textChanged.connect(lambda _t: self.changed())
        self.approach.textChanged.connect(lambda: self.changed())
        self.graphics.textChanged.connect(lambda: self.changed())
        self.vol.currentIndexChanged.connect(lambda _i: self.fill_tree())
        self.theme_checks = {}

    def hideEvent(self, e):                      # leaving the page saves what was typed
        self.save()
        super().hideEvent(e)

    # ------------------------------------------------------------ state
    @property
    def M(self):
        return self.host.review.M if self.host.review is not None else None

    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        self.save()
        if self.host.ws is None or self.M is None or not self.M.outline:
            self.tree.clear(); self.vol.clear()
            self.title.setText("Storyboards")
            self.facts.setText("Build the response structure first (Structure, or + Heading in Review): each section gets a storyboard.")
            return
        cur = self.vol.currentData()
        self.vol.blockSignals(True); self.vol.clear()
        for name, _labs in PB.volumes(self.M):
            self.vol.addItem(name or "The response", name)
        if cur is not None:
            self.vol.setCurrentIndex(max(0, self.vol.findData(cur)))
        self.vol.blockSignals(False)
        self.fill_tree()

    def labels(self):
        return dict(PB.volumes(self.M)).get(self.vol.currentData() or "", []) if self.M is not None else []

    def fill_tree(self):
        import compliance as C
        r = self.rec()
        if r is None or self.M is None:
            return
        keep = self.label
        lv = {C.outline_label(o): o.get("level", 1) for o in self.M.outline}
        labs = self.labels()
        self.tree.blockSignals(True); self.tree.clear()
        stack, pick = [], None
        for lab in labs:
            sb = SB.get(r, lab)
            node = QTreeWidgetItem([lab, sb["status"], PB.fmt(PB.pages(self.M, lab))])
            node.setData(0, Qt.UserRole, lab)
            node.setForeground(1, D.color({"ok": "ok", "warn": "warn", "accent": "accent"}.get(TONE[sb["status"]], "muted")))
            while stack and stack[-1][0] >= lv.get(lab, 1):
                stack.pop()
            (stack[-1][1].addChild(node) if stack else self.tree.addTopLevelItem(node))
            stack.append((lv.get(lab, 1), node))
            if lab == keep or pick is None:
                pick = node if (lab == keep or pick is None) else pick
        self.tree.expandAll()
        self.tree.blockSignals(False)
        c = SB.status_counts(r, labs)
        self.counts.setText("  ·  ".join(f"{n} {s.lower()}" for s, n in c.items() if n))
        if pick is not None:
            self.tree.setCurrentItem(pick)
            self.pick(pick.data(0, Qt.UserRole))

    def pick(self, label):
        if label is None or label == self.label and not self._loading and self.title.text().endswith(label or ""):
            return
        self.save()
        self.label = label
        self.load()

    def load(self):
        import html
        r, M, lab = self.rec(), self.M, self.label
        if r is None or lab is None:
            return
        self._loading = True
        sb, f = SB.get(r, lab), SB.facts(r, M, lab)
        self.title.setText(f"Storyboard: {lab}")
        self.facts.setText(f"<b>Lead</b> {html.escape(f['lead'] or 'not named')}  ·  <b>Writers</b> {html.escape(f['with'] or '-')}"
                           f"  ·  <b>Page budget</b> {(PB.fmt(f['pages']) + ' pages') if f['pages'] else 'not set (Page budget... in Review)'}"
                           f"  ·  <b>{len(f['reqs'])}</b> requirement(s)")
        self.status.setCurrentText(sb["status"])
        self.message.setText(sb["message"])
        self.approach.setPlainText(sb["approach"])
        self.graphics.setPlainText(sb["graphics"])
        self.reqs.setText("<br>".join(f"<b>{html.escape(ref)}</b>  {html.escape(t[:400])}" for ref, t in f["reqs"])
                          or "<i>None placed in this section yet.</i>")
        while self.theme_box.count():
            x = self.theme_box.takeAt(0)
            if x.widget() is not None:
                x.widget().deleteLater()
        import themes as TH
        self.theme_checks = {}
        chosen = set(sb["themes"]) | {t["id"] for t in TH.for_section(r, lab)}
        for t in TH.items(r):
            cb = QCheckBox(t["title"] + (f"  ({t['discriminator']})" if t.get("discriminator") else ""))
            cb.setChecked(t["id"] in chosen)
            cb.toggled.connect(lambda _on: self.changed())
            self.theme_box.addWidget(cb); self.theme_checks[t["id"]] = cb
        if not self.theme_checks:
            self.theme_box.addWidget(D.label("No win themes yet: + Theme... on Effort Home.", "muted"))
        self.feat.blockSignals(True); self.feat.setRowCount(0)
        for x in sb["features"]:
            self._feature_row(x)
        self.feat.blockSignals(False)
        self.gfx_list.setText("Graphic needs for this section: " + "; ".join(f"{g['concept']} ({g.get('status', '')})" for g in f["graphics"])
                              if f["graphics"] else "No graphic needs tagged for this section.")
        self.saved_lbl.setText(f"Saved {sb['at'].replace('T', ' ')} by {sb['by']}" if sb.get("at") else "")
        self._loading = False

    def _feature_row(self, x=None):
        r = self.feat.rowCount(); self.feat.insertRow(r)
        for c, k in enumerate(("feature", "benefit", "proof")):
            self.feat.setItem(r, c, QTableWidgetItem((x or {}).get(k, "")))

    def add_feature(self):
        self.feat.blockSignals(True); self._feature_row(); self.feat.blockSignals(False)
        self.feat.setCurrentCell(self.feat.rowCount() - 1, 0)
        self.feat.editItem(self.feat.item(self.feat.rowCount() - 1, 0))

    def remove_feature(self):
        r = self.feat.currentRow()
        if r >= 0:
            self.feat.removeRow(r)
            self.changed()

    def changed(self):
        if not self._loading:
            self.timer.start()

    def values(self):
        feats = []
        for r in range(self.feat.rowCount()):
            g = lambda c: (self.feat.item(r, c).text() if self.feat.item(r, c) else "")   # noqa: E731
            feats.append({"feature": g(0), "benefit": g(1), "proof": g(2)})
        return {"message": self.message.text(), "approach": self.approach.toPlainText(), "graphics": self.graphics.toPlainText(),
                "features": feats, "themes": [tid for tid, cb in self.theme_checks.items() if cb.isChecked()],
                "status": self.status.currentText()}

    def save(self):
        self.timer.stop()
        r = self.rec()
        if r is None or not self.label or self._loading:
            return False
        try:
            ok = SB.save(r, self.label, **self.values())
        except RuntimeError:
            return False                                 # the form was rebuilt
        if ok:
            diag.activity("storyboard_saved")
            it = self.tree.currentItem()
            if it is not None and it.data(0, Qt.UserRole) == self.label:
                it.setText(1, self.status.currentText())
            self.saved_lbl.setText("Saved.")
        return ok

    def export(self, volume, path=None):
        self.save()
        r = self.rec()
        if r is None or self.M is None or (not volume and not self.label):
            return ""
        labs = self.labels() if volume else [self.label]
        if path is None:
            import re
            base = (self.vol.currentData() or self.host.effort_name) if volume else self.label
            path, _ = QFileDialog.getSaveFileName(self, "Export the storyboard", self.host.out_path(
                "storyboards", Doc=re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")), "Word (*.docx)")
            if not path:
                return ""
        marking = None
        try:
            import branding as BR
            mk = BR.marking(BR.identity(r)["sensitivity"])
            marking = (mk[0], "502B85" if mk[1] == "cui" else "9A4508") if mk else None
        except Exception:
            diag.swallowed()
        SB.export(path, r, self.M, labs, self.host.effort_name, marking)
        diag.activity("storyboard_exported", n=len(labs))
        self.host.toast(f"Storyboard exported: {len(labs)} section(s)")
        return path
