"""Technical Edit (3.54.0): copy review in its own space. Pick a draft (the effort's Volumes folder, or Add files... for
any Word file; Unfiled works the same), pick the level (Full copy review, Consistency and mechanics, Last look) and
Review. Findings by group, level, section and status; the selected one shows its sentence with the words marked, the
suggestion and why: Accept, Skip here, Skip in this effort, Add to the style sheet. Make the edited copy writes the
accepted ones as tracked changes with a comment each into a dated copy (the draft is only read). Readability by section.
The Style sheet tab holds the effort's own decisions and exports them for authors. Rules only (techedit.py); nothing
leaves the PC."""
import html
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog,
                               QListWidget, QListWidgetItem, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextBrowser,
                               QVBoxLayout, QWidget)

import diag
import techedit as T
from . import design as D

COLS = ["Level", "Found", "Words", "Suggested", "Section", "Status"]
STATUSES = ("Every status", "To decide", "Accepted", "Skipped")


class TechEditPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.files, self.found, self.status, self.cur = [], [], {}, None      # status: {key: "Accepted" | "Skipped"}
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        outer.setSpacing(D.SPACE["m"])
        outer.addWidget(D.label("Copy review: the editor's pass on the words. Every finding is a suggestion you accept or skip; "
                                "the edited copy holds the accepted ones as tracked changes, and the draft itself is never changed.", "muted"))
        self.tabs = QTabWidget(); outer.addWidget(self.tabs, 1)
        self.tabs.addTab(self._review_tab(), "Copy review")
        self.tabs.addTab(self._sheet_tab(), "Style sheet")

    # ------------------------------------------------------------ building
    def _review_tab(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, D.SPACE["s"], 0, 0)
        top = QHBoxLayout(); v.addLayout(top)
        top.addWidget(D.label("Draft", "label", wrap=False))
        self.draft = QComboBox(); self.draft.setMinimumWidth(260); top.addWidget(self.draft, 1)
        top.addWidget(D.button("Add files...", None, lambda: self.add_files()))
        top.addWidget(D.label("Level", "label", wrap=False))
        self.level = QComboBox()
        for k, (t, _g) in T.LEVELS.items():
            self.level.addItem(t, k)
        top.addWidget(self.level)
        self.b_run = D.button("Review", "primary", lambda: self.run()); top.addWidget(self.b_run)
        self.b_copy = D.button("Make the edited copy", None, lambda: self.make_copy(), "The accepted findings as tracked changes, "
                               "each with a comment, in a dated copy beside the draft")
        top.addWidget(self.b_copy)
        flt = QHBoxLayout(); v.addLayout(flt)
        self.f_group = QComboBox(); self.f_group.addItem("Every group"); self.f_group.addItems(list(T.GROUPS))
        self.f_level = QComboBox(); self.f_level.addItems(["Fix and Check", T.FIX, T.CHECK])
        self.f_status = QComboBox(); self.f_status.addItems(list(STATUSES))
        for b in (self.f_group, self.f_level, self.f_status):
            b.currentIndexChanged.connect(lambda _i: self.fill()); flt.addWidget(b)
        self.sum = D.label("", "muted"); flt.addWidget(self.sum, 1)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels(COLS)
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i, wd in ((0, 60), (2, 150), (3, 150), (4, 150), (5, 80)):
            self.t.setColumnWidth(i, wd)
        self.t.itemSelectionChanged.connect(self.show_one)
        split.addWidget(self.t)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.detail = QTextBrowser(); rv.addWidget(self.detail, 1)
        b1 = QHBoxLayout(); rv.addLayout(b1)
        self.b_acc = D.button("Accept", "primary", lambda: self.mark("Accepted"))
        self.b_skip = D.button("Skip here", None, lambda: self.mark("Skipped"))
        self.b_off = D.button("Skip in this effort", None, lambda: self.rule_off(), "Turn this rule off for this effort")
        self.b_sheet = D.button("Add to the style sheet", None, lambda: self.to_sheet())
        for b in (self.b_acc, self.b_skip, self.b_off, self.b_sheet):
            b1.addWidget(b)
        stats = D.Card("Readability by section", "Grade level, words per sentence and the share of sentences in the passive.")
        self.st = QTableWidget(0, 4); self.st.setHorizontalHeaderLabels(["Section", "Grade", "Words a sentence", "Passive"])
        self.st.verticalHeader().setVisible(False); self.st.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.st.setMaximumHeight(170); stats.add(self.st); rv.addWidget(stats)
        split.addWidget(right); split.setSizes([700, 460])
        return w

    def _sheet_tab(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, D.SPACE["s"], 0, 0)
        v.addWidget(D.label("The effort's own decisions, on top of the starter rules and the team's lists. They travel with the "
                            "effort and go to authors with Export the style sheet....", "muted"))
        row = QHBoxLayout(); v.addLayout(row)
        terms = D.Card("Terms", "Written one way in this effort: the left form is flagged and the right one suggested.")
        self.terms = QTableWidget(0, 2); self.terms.setHorizontalHeaderLabels(["Written", "Write"])
        self.terms.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); terms.add(self.terms)
        tb = QHBoxLayout(); tw = QWidget(); tw.setLayout(tb)
        tb.addWidget(D.button("Add a term...", None, lambda: self.add_term())); tb.addWidget(D.button("Remove", "ghost", lambda: self.remove_term()))
        tb.addStretch(1); terms.add(tw)
        row.addWidget(terms, 1)
        rules = D.Card("Rules on in this effort", "Untick a rule to leave it out of this effort's reviews.")
        self.rules = QListWidget(); rules.add(self.rules)
        self.rules.itemChanged.connect(lambda it: self.rule_toggled(it))
        row.addWidget(rules, 1)
        words = D.Card("Words known in this effort", "Not flagged by the spelling check (program names, terms of art).")
        self.words = QListWidget(); words.add(self.words)
        wb = QHBoxLayout(); ww = QWidget(); ww.setLayout(wb)
        wb.addWidget(D.button("Add words...", None, lambda: self.add_words())); wb.addWidget(D.button("Remove", "ghost", lambda: self.remove_words()))
        wb.addStretch(1); words.add(ww)
        row.addWidget(words, 1)
        v.addWidget(D.button("Export the style sheet...", "primary", lambda: self.export_sheet()), 0, Qt.AlignLeft)
        return w

    # ------------------------------------------------------------ the effort's sheet and lists
    def sheet(self):
        ws = self.host.ws
        s = (ws.get("techedit_sheet") if ws is not None else None) or {}
        return {"terms": dict(s.get("terms") or {}), "off": list(s.get("off") or []), "skips": list(s.get("skips") or []),
                "words": list(s.get("words") or []), "customer_terms": dict(s.get("customer_terms") or {})}

    def save_sheet(self, s):
        if self.host.ws is not None:
            self.host.ws.set("techedit_sheet", s)

    def refs(self):
        """What the review reads: the team's dictionaries and banned phrases, the acronym list, other efforts' names."""
        import banned as BN
        import customdict as CD
        import unfiled as UF
        h = self.host
        words = set(self.sheet()["words"])
        try:
            for dct in CD.Store(h.config_dir).dicts:
                words |= set(dct.get("words") or [])
        except Exception:  # noqa: BLE001
            diag.swallowed()
        acr = {}
        s = getattr(getattr(h, "acronym_page", None), "session", None)
        if s is not None and s.effort is not None:
            acr = {t: r.get("Definition", "") for t, r in s.effort.rows.items()}
        others = [n for n in h.efforts.names() if n not in (h.effort_name, UF.NAME)]
        return {"dictionaries": words, "acronyms": acr, "banned": BN.load(), "other_names": others,
                "customer_terms": self.sheet()["customer_terms"]}

    # ------------------------------------------------------------ drafts and the review
    def volumes(self):
        h = self.host
        if not getattr(h, "effort_path", None):
            return []
        import effortfolders as EF
        d = EF.folder(h.effort_path, "volumes", make=False)
        return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".docx") and not f.startswith("~$")
                      and " - edited " not in f) if d and os.path.isdir(d) else []

    def refresh(self):
        keep = self.draft.currentData()
        self.files = list(dict.fromkeys(self.volumes() + [f for f in self.files if os.path.isfile(f)]))
        self.draft.blockSignals(True); self.draft.clear()
        for f in self.files:
            self.draft.addItem(os.path.basename(f), f)
        i = self.draft.findData(keep)
        self.draft.setCurrentIndex(max(0, i)); self.draft.blockSignals(False)
        self.fill_sheet()
        self.fill()

    def add_files(self, paths=None, run=False):
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Drafts to review", "", "Word (*.docx)")
        paths = [p for p in (paths or []) if p.lower().endswith(".docx") and os.path.isfile(p)]
        for p in paths:
            if p not in self.files:
                self.files.append(p)
        self.refresh()
        if paths:
            self.draft.setCurrentIndex(self.draft.findData(paths[0]))
            if run:
                return self.run()
        return paths

    def run(self, path=None, level=None):
        path = path or self.draft.currentData()
        if not path or not os.path.isfile(path):
            self.host.status("Pick a draft first: Add files..., or put drafts in the effort's Volumes folder.")
            return []
        level = level or self.level.currentData()
        try:
            src = T.read(path)
            self.found = T.review(src, level, self.sheet(), self.refs())
            stats = T.section_stats(src[0])
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"The draft could not be read ({type(e).__name__}).")
            return []
        self.cur = path
        self.status = {k: v for k, v in self.status.items() if any(f["key"] == k for f in self.found)}
        self.st.setRowCount(0)
        for s in stats:
            r = self.st.rowCount(); self.st.insertRow(r)
            for c, v in enumerate((s["section"], f"{s['grade']:g}", f"{s['per_sentence']:g}", f"{round(s['passive_share'] * 100)}%")):
                self.st.setItem(r, c, QTableWidgetItem(v))
        self.fill()
        diag.activity("techedit_reviewed", n=len(self.found))
        self.host.status(f"{len(self.found)} finding(s) in {os.path.basename(path)}.")
        return self.found

    def shown(self):
        g, lv, st = self.f_group.currentText(), self.f_level.currentText(), self.f_status.currentText()
        out = []
        for f in self.found:
            s = self.status.get(f["key"], "To decide")
            if (g == "Every group" or f["group"] == g) and (lv == "Fix and Check" or f["level"] == lv) and (st == STATUSES[0] or s == st):
                out.append(f)
        return out

    def fill(self):
        rows = self.shown()
        self.t.setRowCount(0)
        for f in rows:
            r = self.t.rowCount(); self.t.insertRow(r)
            vals = (f["level"], f["title"], f["hit"][:60], f["fix"][:60], f["section"][:40], self.status.get(f["key"], ""))
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setData(Qt.UserRole, f["key"])
                if c == 0:
                    it.setForeground(D.color("crit" if f["level"] == T.FIX else "warn"))
                self.t.setItem(r, c, it)
        n_fix = sum(1 for f in self.found if f["level"] == T.FIX)
        acc = sum(1 for v in self.status.values() if v == "Accepted")
        self.sum.setText(f"{len(rows)} shown · {n_fix} Fix, {len(self.found) - n_fix} Check · {acc} accepted" if self.found else "")
        self.b_copy.setEnabled(acc > 0)

    def selected(self):
        keys = {self.t.item(i.row(), 0).data(Qt.UserRole) for i in self.t.selectedIndexes()}
        return [f for f in self.found if f["key"] in keys]

    def show_one(self):
        sel = self.selected()
        if not sel:
            self.detail.setHtml("")
            return
        f = sel[0]
        sent = html.escape(f["sentence"])
        if f["hit"]:
            sent = sent.replace(html.escape(f["hit"]), f"<span style='background:#FCEFD9'>{html.escape(f['hit'])}</span>", 1)
        self.detail.setHtml(f"<p><b>{html.escape(f['title'])}</b> ({f['level']}, {html.escape(f['group'])})</p>"
                            f"<p style='color:gray'>{html.escape(f['section'])}</p><p>{sent}</p>"
                            f"<p><b>Suggested:</b> {html.escape(f['fix'] or '')}</p><p style='color:gray'>{html.escape(f['why'])}</p>")
        self.b_sheet.setEnabled(f["rule"] in ("variants", "customer_terms", "spelling", "hyphen_forms"))

    # ------------------------------------------------------------ decisions
    def mark(self, st, findings=None):
        fs = findings if findings is not None else self.selected()
        for f in fs:
            self.status[f["key"]] = st
        if st == "Skipped" and fs:                        # skipped places stay skipped on the next review
            s = self.sheet(); s["skips"] = sorted(set(s["skips"]) | {f["key"] for f in fs}); self.save_sheet(s)
        self.fill()
        return len(fs)

    def rule_off(self, findings=None):
        fs = findings if findings is not None else self.selected()
        if not fs:
            return []
        s = self.sheet(); s["off"] = sorted(set(s["off"]) | {f["rule"] for f in fs}); self.save_sheet(s)
        self.found = [f for f in self.found if f["rule"] not in s["off"]]
        self.fill(); self.fill_sheet()
        return s["off"]

    def to_sheet(self, findings=None):
        """A term the editor chose becomes the effort's: the written form flagged, the right one suggested; a word the
        spelling check did not know becomes known."""
        fs = findings if findings is not None else self.selected()
        s = self.sheet()
        for f in fs:
            if f["rule"] == "spelling":
                s["words"] = sorted(set(s["words"]) | {f["hit"]})
            elif f["rule"] in ("variants", "hyphen_forms") and f["fix"]:
                s["terms"][f["hit"].lower()] = f["fix"]
            elif f["rule"] == "customer_terms":
                s["customer_terms"][f["hit"].lower()] = f["fix"]
        self.save_sheet(s)
        self.fill_sheet()
        return s

    def make_copy(self, out=None):
        import techeditdocx as TD
        acc = [f for f in self.found if self.status.get(f["key"]) == "Accepted"]
        if not acc or not self.cur:
            self.host.status("Accept findings first: the copy holds the accepted ones.")
            return None
        out = out or TD.copy_path(self.cur)
        try:
            got = TD.write(self.cur, acc, out)
        except PermissionError:
            self.host.status("That copy is open in Word. Close it, then make it again.")
            return None
        diag.activity("techedit_copy_made", n=got["changes"] + got["comments"])
        self.host.toast(f"{os.path.basename(out)}: {got['changes']} tracked change(s), {got['comments']} comment(s)"
                        + (f", {got['skipped']} left out (the draft changed since the review)" if got["skipped"] else "") + ".")
        return out

    # ------------------------------------------------------------ the style sheet tab
    def fill_sheet(self):
        s = self.sheet()
        self.terms.setRowCount(0)
        for a, b in sorted(s["terms"].items()):
            r = self.terms.rowCount(); self.terms.insertRow(r)
            self.terms.setItem(r, 0, QTableWidgetItem(a)); self.terms.setItem(r, 1, QTableWidgetItem(b))
        self.rules.blockSignals(True); self.rules.clear()
        for r_ in T.rules():
            it = QListWidgetItem(f"{r_['group']}: {r_['finds']}"); it.setData(Qt.UserRole, r_["id"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked if r_["id"] in s["off"] else Qt.Checked)
            self.rules.addItem(it)
        self.rules.blockSignals(False)
        self.words.clear(); self.words.addItems(s["words"])

    def rule_toggled(self, it):
        s = self.sheet(); rid = it.data(Qt.UserRole)
        off = set(s["off"])
        (off.discard if it.checkState() == Qt.Checked else off.add)(rid)
        s["off"] = sorted(off); self.save_sheet(s)
        return s["off"]

    def add_term(self, written=None, write=None):
        if written is None:
            written, ok = QInputDialog.getText(self, "Add a term", "Written (flagged):")
            if not ok or not written.strip():
                return None
            write, ok = QInputDialog.getText(self, "Add a term", f"Write instead of {written}:")
            if not ok or not write.strip():
                return None
        s = self.sheet(); s["terms"][" ".join(written.split()).lower()] = " ".join(write.split()); self.save_sheet(s)
        self.fill_sheet()
        return s["terms"]

    def remove_term(self):
        s = self.sheet()
        for i in sorted({x.row() for x in self.terms.selectedIndexes()}, reverse=True):
            s["terms"].pop(self.terms.item(i, 0).text(), None)
        self.save_sheet(s); self.fill_sheet()

    def add_words(self, words=None):
        if words is None:
            text, ok = QInputDialog.getText(self, "Add words", "Words known in this effort (separated by spaces or commas):")
            if not ok:
                return None
            words = [w for w in text.replace(",", " ").split() if w]
        s = self.sheet(); s["words"] = sorted(set(s["words"]) | set(words)); self.save_sheet(s)
        self.fill_sheet()
        return s["words"]

    def remove_words(self):
        gone = {i.text() for i in self.words.selectedItems()}
        s = self.sheet(); s["words"] = [w for w in s["words"] if w not in gone]; self.save_sheet(s); self.fill_sheet()

    def export_sheet(self, path=None):
        import volcheck as V
        s = self.sheet()
        rows = [(a, b) for a, b in sorted(s["terms"].items())] + [(w, "known word") for w in s["words"]]
        rows += [(T.RULE[r]["finds"], "off in this effort") for r in s["off"] if r in T.RULE]
        rows += [("Numbers", "one to nine spelled out; 10 and up as numerals; numerals with units"),
                 ("Sentences", f"at most {T.SENTENCE_MAX} words"), ("Lists of three or more", "a comma before and or or")]
        if path is None:
            start = os.path.join(os.path.dirname(self.cur) if self.cur else os.path.expanduser("~"), "Style sheet.docx")
            path, _ = QFileDialog.getSaveFileName(self, "Export the style sheet", start, "Word (*.docx)")
            if not path:
                return None
        V.write_docx(rows, path)
        return path
