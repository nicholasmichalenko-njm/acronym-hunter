"""Deliver > Wall of Truth (3.3.0): the effort's approved facts, numbers, names and terms in one table, and the check of
the drafts against them. + Truth... adds one (what it is, the approved value, the words it appears beside in a draft,
the wrong forms, its owner); Add the team's facts brings in the company facts every effort shares; Check the drafts
reads the Word files in the Volumes folder and lists every disagreement with its volume, section and sentence.
Export the wall makes the page to post and hand to writers."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLineEdit, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import effortrec as R
import walloftruth as WT
from . import design as D


def _table(cols, widths, stretch):
    t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setWordWrap(True)
    for i, w in enumerate(widths):
        if w:
            t.setColumnWidth(i, w)
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    return t


class WallPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.findings = []
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
        v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.wall = D.Card("The wall", "One approved way to state each fact. Double-click a row to change it; a new value keeps the "
                           "old one, so the check finds it still in a draft.",
                           actions=[D.button("+ Truth...", "primary", lambda: self.truth_dialog()),
                                    D.button("Add the team's facts", None, lambda: self.add_team(),
                                             "The company facts on the team's wall that this effort does not have yet"),
                                    D.button("Export the wall...", None, lambda: self.export_wall(), "A page or two in Word to post and hand to writers")])
        self.table = _table(["Kind", "What", "Write it as", "Beside these words", "Not", "Owner", "Confirmed"],
                            [80, 190, 160, 0, 170, 110, 100], 3)
        self.table.setMinimumHeight(260)
        self.table.cellDoubleClicked.connect(lambda r, _c: self.truth_dialog(self.row_id(r)))
        self.wall.add(self.table)
        row = QHBoxLayout()
        for text, fn, tip in (("Confirm", lambda: self.confirm(), "The selected truths are still right: date them today"),
                              ("Save to the team's wall", lambda: self.to_team(), "Every effort can add it with Add the team's facts"),
                              ("Remove", lambda: self.remove(), "")):
            row.addWidget(D.button(text, "ghost" if text == "Remove" else None, fn, tip))
        row.addStretch(1)
        self.wall.body.addLayout(row)
        self.note = self.wall.add(D.label("", "muted"))
        v.addWidget(self.wall)
        self.check_card = D.Card("Check the drafts", "Every number beside a truth's words that does not match, every old value still "
                                 "in use, and every wrong form, in the Word files of the Volumes folder.",
                                 actions=[D.button("Check the drafts", "primary", lambda: self.check()),
                                          D.button("Export...", None, lambda: self.export_findings(), "The findings as a workbook for the editors")])
        self.summary = self.check_card.add(D.label("Not checked yet.", "muted"))
        self.found = _table(["Truth", "Volume", "Section", "Problem", "Sentence"], [160, 150, 150, 230, 0], 4)
        self.found.setMinimumHeight(240)
        self.check_card.add(self.found)
        frow = QHBoxLayout()
        frow.addWidget(D.button("Right as written", "ghost", lambda: self.ignore(), "Leave the selected findings out of the next check"))
        frow.addStretch(1)
        self.check_card.body.addLayout(frow)
        v.addWidget(self.check_card)
        v.addStretch(1)

    # ------------------------------------------------------------ state
    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        r = self.rec()
        self.setEnabled(r is not None)
        keep = set(self.selected_ids())                  # the selection stays after Confirm or Save to the team's wall
        self.table.setRowCount(0)
        if r is None:
            return
        for t in WT.items(r):
            k = self.table.rowCount(); self.table.insertRow(k)
            vals = (t["kind"], t["label"], t["value"], ", ".join(t.get("context", [])),
                    "; ".join(t.get("wrong", []) + [o["value"] for o in t.get("old", [])]), t.get("owner", ""), t.get("confirmed", ""))
            for c, text in enumerate(vals):
                it = QTableWidgetItem(text)
                if c == 0:
                    it.setData(Qt.UserRole, t["id"])
                if c == 2:
                    f = it.font(); f.setBold(True); it.setFont(f)
                if c == 6 and WT.stale(t):
                    it.setForeground(D.color("warn")); it.setToolTip("Not confirmed for over 30 days")
                self.table.setItem(k, c, it)
        self.table.resizeRowsToContents()
        for k in range(self.table.rowCount()):
            if self.row_id(k) in keep:
                self.table.selectRow(k)
        team = WT.team_load(self.host.config_dir)
        have = {t["label"].casefold() for t in WT.items(r)}
        new = sum(1 for x in team if x["label"].casefold() not in have)
        n = self.table.rowCount()
        self.note.setText((f"{n} truth{'s' if n != 1 else ''}" if n else "No truths yet: + Truth... adds the first.")
                          + (f"  ·  The team's wall has {new} more for this effort (Add the team's facts)." if new else "")
                          + (f"  ·  {sum(1 for t in WT.items(r) if WT.stale(t))} not confirmed for 30 days" if any(WT.stale(t) for t in WT.items(r)) else ""))

    def row_id(self, r):
        it = self.table.item(r, 0)
        return it.data(Qt.UserRole) if it is not None else None

    def selected_ids(self):
        return [self.row_id(i.row()) for i in self.table.selectionModel().selectedRows()] if self.table.selectionModel() else []

    # ------------------------------------------------------------ the wall
    def truth_dialog(self, tid=None, answer=None):
        """+ Truth... (tid None) or change one. answer (tests): {"label", "kind", "value", "context", "wrong", "owner",
        "source", "notes"}. Returns the id."""
        r = self.rec()
        if r is None:
            return None
        t = WT.get(r, tid) if tid else None
        if answer is None:
            d = QDialog(self); d.setWindowTitle("Truth" if t else "New truth"); d.setMinimumWidth(600)
            f = QFormLayout(d)
            label = QLineEdit(t["label"] if t else ""); label.setPlaceholderText("Cleared staff"); f.addRow("What", label)
            kind = QComboBox(); kind.addItems(list(WT.KINDS)); kind.setCurrentText(t["kind"] if t else "Number"); f.addRow("Kind", kind)
            value = QLineEdit(t["value"] if t else ""); value.setPlaceholderText("142"); f.addRow("Write it as", value)
            ctx = QLineEdit(", ".join(t.get("context", [])) if t else ""); ctx.setPlaceholderText("cleared staff, cleared employees, clearances")
            ctx.setToolTip("The check looks for numbers within a few words of these")
            f.addRow("Beside these words", ctx)
            wrong = QLineEdit(", ".join(t.get("wrong", [])) if t else ""); wrong.setPlaceholderText("the client, the customer agency")
            f.addRow("Never write", wrong)
            from .people import name_combo, combo_name
            own = name_combo(self.host, t.get("owner", "") if t else ""); f.addRow("Owner (who confirms it)", own)
            src = QLineEdit(t.get("source", "") if t else ""); src.setPlaceholderText("HR report, Oct 2026"); f.addRow("Source", src)
            notes = QLineEdit(t.get("notes", "") if t else ""); f.addRow("Notes", notes)
            if t and t.get("old"):
                f.addRow(D.label("Before: " + "; ".join(f"{o['value']} (until {o['until'][:10]})" for o in t["old"]), "muted"))
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            f.addRow(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = {"label": label.text(), "kind": kind.currentText(), "value": value.text(), "context": ctx.text(),
                      "wrong": wrong.text(), "owner": combo_name(own), "source": src.text(), "notes": notes.text()}
        if t:
            WT.update(r, t["id"], **answer)
            out = t["id"]
        else:
            out = WT.add(r, answer.get("label", ""), answer.get("value", ""), answer.get("kind", "Number"), answer.get("context") or (),
                         answer.get("wrong") or (), answer.get("owner", ""), answer.get("source", ""), answer.get("notes", ""))
            if not out:
                self.host.status("A truth needs what it is and how to write it.")
        if out:
            diag.activity("truth_saved")
            self.host.changed()
        self.refresh()
        return out

    def confirm(self, ids=None):
        r = self.rec()
        n = sum(1 for i in (ids if ids is not None else self.selected_ids()) if i and WT.confirm(r, i))
        self.refresh()
        return n

    def to_team(self, ids=None):
        r = self.rec()
        n = sum(1 for i in (ids if ids is not None else self.selected_ids()) if i and WT.to_team(self.host.config_dir, WT.get(r, i)))
        if n:
            diag.activity("truth_to_team", n=n)
            self.host.toast(f"{n} truth(s) on the team's wall: every effort can add them")
        self.refresh()
        return n

    def add_team(self):
        r = self.rec()
        n = WT.from_team(r, self.host.config_dir) if r is not None else 0
        diag.activity("truth_from_team", n=n)
        self.host.status(f"{n} truth(s) added from the team's wall." if n else "Nothing new on the team's wall for this effort.")
        self.refresh()
        return n

    def remove(self, ids=None):
        r = self.rec()
        n = sum(1 for i in (ids if ids is not None else self.selected_ids()) if i and WT.remove(r, i))
        self.refresh()
        return n

    def export_wall(self, path=None):
        r = self.rec()
        if r is None:
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the Wall of Truth", self.host.out_path("wall_of_truth"), "Word (*.docx)")
            if not path:
                return ""
        marking = None
        try:
            import branding as BR
            mk = BR.marking(BR.identity(r)["sensitivity"])
            marking = (mk[0], "502B85" if mk[1] == "cui" else "9A4508") if mk else None
        except Exception:
            diag.swallowed()
        WT.export_word(path, r, self.host.effort_name, marking)
        diag.activity("truth_wall_exported", n=len(WT.items(r)))
        self.host.toast("Wall of Truth exported")
        return path

    # ------------------------------------------------------------ the check
    def check(self, drafts=None):
        r = self.rec()
        if r is None:
            return []
        drafts = drafts if drafts is not None else self.host.home_page.theme_drafts()
        if not drafts:
            self.summary.setText("No drafts yet: put the volumes' Word files in the effort's Volumes folder.")
            return []
        labels = self.host.review.labels() if self.host.review is not None else []
        self.findings = WT.check(r, drafts, labels)
        self.show_findings(len(drafts))
        diag.activity("truth_checked", n=len(self.findings))
        return self.findings

    def show_findings(self, ndrafts=None):
        t = self.found
        t.setRowCount(0)
        for f in self.findings:
            k = t.rowCount(); t.insertRow(k)
            for c, text in enumerate((f["label"], f["volume"], f["section"] or "(before the first heading)", f["problem"], f["sentence"])):
                it = QTableWidgetItem(text)
                if c == 3:
                    it.setForeground(D.color("crit"))
                t.setItem(k, c, it)
        t.resizeRowsToContents()
        n = len(self.findings)
        self.summary.setText((f"{n} place{'s' if n != 1 else ''} disagree with the wall" if n else "Every draft agrees with the wall.")
                             + (f" ({ndrafts} draft{'s' if ndrafts != 1 else ''} read)." if ndrafts else "."))

    def ignore(self, rows=None):
        r = self.rec()
        rows = rows if rows is not None else sorted({i.row() for i in self.found.selectionModel().selectedRows()}, reverse=True)
        n = 0
        for k in sorted(rows, reverse=True):
            if 0 <= k < len(self.findings) and WT.ignore(r, self.findings[k]["key"]):
                del self.findings[k]
                n += 1
        self.show_findings()
        return n

    def export_findings(self, path=None):
        if not self.findings:
            self.host.status("Check the drafts first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the findings", self.host.out_path("wall_of_truth_check"), "Excel (*.xlsx)")
            if not path:
                return ""
        WT.export_findings(path, self.findings, self.host.effort_name)
        self.host.toast(f"{len(self.findings)} finding(s) exported")
        return path
