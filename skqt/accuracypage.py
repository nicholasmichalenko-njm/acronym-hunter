"""Shred > Accuracy (3.59.0, claude/stationkeeper-shred-accuracy-decisions-2026-11-05.md): how well the shred finds
requirements, measured on the person's own set of public RFPs with answer keys labeled in Review. Every RFP in the set,
labeled or not; each one's recall and precision; the set's scores by kind against the 95% target; and the trend as
releases come. Save this effort's Review as answer keys writes a key beside each RFP the effort read. Reads only."""
import os

from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

import diag
import shredeval as SE
from . import design as D

HIST_FILE = "shred_history.csv"


def _t(cols):
    t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return t


def _p(v):
    return "" if v is None else f"{v:g}%"


class AccuracyPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.result = None
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.p_set = D.Pill("0 RFPs", "accent")
        self.p_recall = D.Pill("Recall: not scored", "muted")
        self.p_prec = D.Pill("Precision: not scored", "muted")
        self.p_kind = D.Pill("Kind right: not scored", "muted")
        for p in (self.p_set, self.p_recall, self.p_prec, self.p_kind):
            top.addWidget(p)
        top.addStretch(1)
        card = D.Card("The shred set", "Public RFPs you saved on this PC, each with an answer key you labeled in Shred. "
                      f"Recall is the share of real requirements the shred finds (the target is {SE.TARGET:g}%); precision "
                      "is the share of its flags that are real.", key=True,
                      actions=[D.button("Score the set", "primary", lambda: self.score()),
                               D.button("Save this effort's shred as answer keys", None, lambda: self.save_keys(),
                                        "A key beside each RFP this effort read: every piece's decision and kind")])
        fr = QHBoxLayout()
        self.folder = D.label("", None); fr.addWidget(self.folder, 1)
        fr.addWidget(D.button("Choose the folder...", "ghost", lambda: self.choose()))
        card.body.addLayout(fr)
        self.files = _t(["RFP", "Answer key", "Requirements", "Recall", "Precision", "Kind right"])
        self.files.setMinimumHeight(180)
        card.add(self.files)
        self.kinds = card.add(D.label("", "muted"))
        v.addWidget(card, 1)
        hc = D.Card("By release", "Each scoring, newest first: the set grows and the scores move.")
        self.hist = _t(["When", "Version", "RFPs labeled", "Requirements", "Recall", "Precision", "Kind right"])
        self.hist.setMaximumHeight(200)
        hc.add(self.hist)
        v.addWidget(hc)
        self.how = D.label("To add an RFP: save it in the folder, add it to a test effort's Documents, shred every piece, then "
                           "Save this effort's shred as answer keys. The build scores the set each release.", "muted")
        v.addWidget(self.how)

    # ------------------------------------------------------------ the folder
    def set_dir(self):
        from .modes import settings
        return (settings() or {}).get("shred_set_dir") or SE.default_folder()

    def choose(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "The shred set folder", self.set_dir())
            if not folder:
                return ""
        from .modes import save
        save(shred_set_dir=folder)
        self.refresh()
        return folder

    def hist_path(self):
        return os.path.join(self.host.config_dir, HIST_FILE)

    def refresh(self):
        d = self.set_dir()
        here = os.path.isdir(d)
        self.folder.setText(d + ("" if here else "   (not made yet: make the folder and save RFPs in it)"))
        if self.result is None:
            files = SE.set_files(d) if here else []
            self.files.setRowCount(0)
            for p, kp in files:
                self._row([os.path.relpath(p, d), "labeled" if kp else "not labeled yet", "", "", "", ""])
            self.p_set.setText(f"{len(files)} RFP file(s), {sum(1 for _p_, k in files if k)} labeled")
        self.fill_hist()

    def _row(self, vals):
        k = self.files.rowCount(); self.files.insertRow(k)
        for c, x in enumerate(vals):
            self.files.setItem(k, c, QTableWidgetItem(str(x)))

    def fill_hist(self):
        rows = list(reversed(SE.history(self.hist_path())))
        self.hist.setRowCount(0)
        for r in rows[:50]:
            k = self.hist.rowCount(); self.hist.insertRow(k)
            for c, col in enumerate(("Date", "Version", "RFPs", "Requirements", "Recall", "Precision", "Kind right")):
                x = r.get(col, "")
                self.hist.setItem(k, c, QTableWidgetItem(f"{x}%" if col in ("Recall", "Precision", "Kind right") and x else x))

    # ------------------------------------------------------------ labels and scores
    def save_keys(self):
        R = self.host.review
        if R is None:
            self.host.status("Open the test effort that read the RFP, decide its pieces in Shred, then save the keys.")
            return []
        got = SE.save_keys(R.M)
        diag.activity("shred_keys_saved", n=len(got))
        if not got:
            self.host.status("None of this effort's RFP files is on this PC any more.")
            return []
        open_ = sum(n - d for _p, _k, n, d in got)
        self.result = None
        self.host.toast(f"{len(got)} answer key(s) saved" + (f"; {open_} piece(s) still undecided are left out" if open_ else ""))
        self.refresh()
        return got

    def score(self, record=True):
        d = self.set_dir()
        r = SE.score_set(d)
        self.result = r
        self.files.setRowCount(0)
        for f in r["files"]:
            if not f["labeled"]:
                self._row([os.path.relpath(f["path"], d), "not labeled yet", "", "", "", ""])
            elif "error" in f:
                self._row([os.path.relpath(f["path"], d), "labeled", "", f"not read ({f['error']})", "", ""])
            else:
                self._row([os.path.relpath(f["path"], d), f"{f['decided']} of {f['sentences']} decided", f["truth"],
                           _p(f["recall"]), _p(f["precision"]), _p(round(100 * f["kind_right"] / f["kind_total"], 1) if f["kind_total"] else None)])
        self.p_set.setText(f"{r['rfps']} RFP file(s), {r['labeled']} labeled")
        rec = r["recall"]
        self.p_recall.setText(f"Recall: {_p(rec) or 'nothing labeled'}" + (f" (target {SE.TARGET:g}%)" if rec is not None else ""))
        self.p_recall.set_tone("muted" if rec is None else ("ok" if rec >= SE.TARGET else "warn"))
        self.p_prec.setText(f"Precision: {_p(r['precision']) or 'nothing labeled'}"); self.p_prec.set_tone("muted" if r["precision"] is None else "accent")
        self.p_kind.setText(f"Kind right: {_p(r['kind_right']) or 'nothing labeled'}"); self.p_kind.set_tone("muted" if r["kind_right"] is None else "accent")
        self.kinds.setText("Recall by kind: " + ", ".join(f"{k} {_p(x)}" for k, x in r["by_kind"].items() if x is not None)
                           if r["labeled"] else "Label an RFP to see the scores by kind.")
        if record and r["labeled"]:
            import app_gui as A
            SE.append_history(self.hist_path(), r, A.APP_VERSION)
        self.fill_hist()
        diag.activity("shred_scored", n=r["labeled"])
        return r
