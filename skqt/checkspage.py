"""Deliver > Final Checks (3.4.0): the last checks before the proposal goes out. The final PDF package (every PDF in the
package folder against the page limits, page size, embedded fonts, searchable text, file size and naming, and every
required volume and form present); cross-references and numbering in the Word drafts; and Compare two drafts (what
changed between the red team copy and today's, as a Word redline). Nothing is changed; each check exports a file."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import effortrec as R
from . import design as D


def _table(cols, widths, stretch, h=220):
    t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setWordWrap(True)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    for i, w in enumerate(widths):
        if w:
            t.setColumnWidth(i, w)
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    t.setMinimumHeight(h)
    return t


class ChecksPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.pkg = None
        self.xref = []
        self.cmp = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
        v = QVBoxLayout(inner); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        # ---- the final PDF package
        self.pkg_card = D.Card("Final PDF package", "Every PDF in the package folder, checked the way the portal and the evaluators "
                               "will see it.", actions=[D.button("Check the package", "primary", lambda: self.check_package()),
                                                        D.button("Export...", None, lambda: self.export_package())])
        f = QFormLayout(); self.pkg_card.body.addLayout(f)
        self.folder = QLineEdit(); self.folder.setPlaceholderText("The folder that holds the PDFs you will upload")
        frow = QHBoxLayout(); frow.addWidget(self.folder, 1)
        frow.addWidget(D.button("Choose...", None, lambda: self.choose_folder()))
        f.addRow("Package folder", frow)
        self.size = QComboBox(); self.size.addItems(["Letter", "A4", "Letter or A4"]); f.addRow("Page size", self.size)
        self.mb = QDoubleSpinBox(); self.mb.setRange(0, 2000); self.mb.setSuffix(" MB"); self.mb.setSpecialValueText("no limit")
        f.addRow("Largest file allowed", self.mb)
        self.contain = QLineEdit(); self.contain.setPlaceholderText("Words every file name must hold, with commas between them")
        f.addRow("File names must contain", self.contain)
        self.naming = D.label("", "muted"); f.addRow("", self.naming)
        self.required = QPlainTextEdit(); self.required.setFixedHeight(80)
        self.required.setPlaceholderText("One a line: each volume and form that must have a file (filled from the deliverables)")
        f.addRow("Must be in the package", self.required)
        self.pkg_sum = self.pkg_card.add(D.label("Not checked yet.", "muted"))
        self.pkg_table = _table(["File", "Pages", "Limit", "MB", "Problems", "Notes"], [230, 60, 60, 60, 0, 220], 4)
        self.pkg_card.add(self.pkg_table)
        v.addWidget(self.pkg_card)
        # ---- 3.29.0: the RFP's written formatting rules (from Review): a phrase looked for, or an item someone ticks
        self.w_card = D.Card("The RFP's written rules", "Formatting rules the RFP states in words (a marking, a legend, a "
                             "label), taken in Shred. One that quotes the words to carry is looked for in the drafts below; "
                             "the rest are ticked by a person.", actions=[D.button("Look for the phrases", "primary", lambda: self.check_written())])
        self.w_sum = self.w_card.add(D.label("", "muted"))
        self.w_table = _table(["Done", "Rule (the RFP's words)", "Where", "Checked by", "Result"], [50, 0, 200, 150, 220], 1, 180)
        self.w_table.itemChanged.connect(lambda it: self.tick_written(it))
        self.w_card.add(self.w_table)
        v.addWidget(self.w_card)
        # ---- 3.32.0: the response elements (the TOC, the lists, Acronyms...) the RFP names, and their order
        self.e_card = D.Card("Response elements", "Each volume against the RFP: an element the RFP names that the volume does "
                             "not have, elements out of the order the RFP lists them in, and an element outside its part.",
                             actions=[D.button("Check the elements", "primary", lambda: self.check_elements()),
                                      D.button("Export...", None, lambda: self.export_elements())])
        self.e_sum = self.e_card.add(D.label("Not checked yet.", "muted"))
        self.e_table = _table(["Volume", "Check", "Element", "What", "Where"], [170, 70, 170, 0, 200], 3, 160)
        self.e_card.add(self.e_table)
        self.elements = None
        v.addWidget(self.e_card)
        # ---- cross-references
        self.l_card = D.Card("Leftovers", "What must not go out: the setup's reference text and file properties, hidden "  # 3.57.0
                             "text, white text, comments, tracked changes and placeholders. Changes nothing.",
                             actions=[D.button("Check for leftovers", "primary", lambda: self.check_leftovers()),
                                      D.button("Add files...", None, lambda: self.add_leftover_files()),
                                      D.button("Export...", None, lambda: self.export_leftovers())])
        self.l_files = QListWidget(); self.l_files.setFixedHeight(90); self.l_card.add(self.l_files)
        self.l_sum = self.l_card.add(D.label("Not checked yet.", "muted"))
        self.l_table = _table(["File", "What", "Under", "Text"], [180, 170, 200, 0], 3)
        self.l_card.add(self.l_table)
        self.leftover = []
        v.addWidget(self.l_card)
        self.x_card = D.Card("Cross-references and numbering", "Figure, table and exhibit numbers in order; every one the text "
                             "mentions has a caption, every caption is mentioned; pictures and tables with no caption; Word's "
                             "broken references.", actions=[D.button("Check the drafts", "primary", lambda: self.check_xref()),
                                                            D.button("Export...", None, lambda: self.export_xref())])
        self.drafts = QListWidget(); self.drafts.setFixedHeight(110); self.x_card.add(self.drafts)
        self.x_sum = self.x_card.add(D.label("Not checked yet.", "muted"))
        self.x_table = _table(["Draft", "Problem", "Section", "Detail"], [200, 190, 200, 0], 3)
        self.x_card.add(self.x_table)
        v.addWidget(self.x_card)
        # ---- compare two drafts
        self.c_card = D.Card("Compare two drafts", "What changed between two versions of a volume: the red team copy and today's, "
                             "say. Open in Amendments shows them side by side, with the redline in Word.",       # 3.55.0: one Compare
                             actions=[D.button("Open in Amendments", "primary", lambda: self.open_compare())])
        cf = QFormLayout(); self.c_card.body.addLayout(cf)
        self.older, self.newer = QComboBox(), QComboBox()
        for label, cb in (("Earlier version", self.older), ("Later version", self.newer)):
            cb.setMinimumWidth(320)
            row = QHBoxLayout(); row.addWidget(cb, 1)
            row.addWidget(D.button("Other file...", None, lambda _=False, c=cb: self.pick_file(c)))
            cf.addRow(label, row)
        self.c_sum = self.c_card.add(D.label("", "muted")); self.c_sum.setTextFormat(Qt.RichText)
        v.addWidget(self.c_card)
        v.addStretch(1)

    # ------------------------------------------------------------ state
    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            return
        self.folder.setText(h.ws.get("final_dir", "") or self.folder.text())
        info = h.efforts.get(h.effort_name) or {}
        if not self.contain.text():
            self.contain.setText(info.get("solicitation", "") or "")
        rows = self._rows()
        size = next((r["value"] for r in rows if r.get("subject") == "Page size"), "")
        if "a4" in size.lower():
            self.size.setCurrentText("A4")
        naming = next((r["value"] for r in rows if r.get("subject") == "File naming"), "")
        self.naming.setText(f"The customer's naming rule: {naming}" if naming else "")
        self.naming.setVisible(bool(naming))
        if not self.required.toPlainText().strip():
            try:
                import deliverables as DL
                self.required.setPlainText("\n".join(d["name"] for d in DL.items(R.Record(h.ws.root))))
            except Exception:
                diag.swallowed()
        drafts = h.home_page.theme_drafts()
        extra = [self.l_files.item(i).data(Qt.UserRole) for i in range(self.l_files.count())]
        self.l_files.clear()
        for name, p in list(drafts) + [(os.path.basename(x), x) for x in extra if x not in dict(drafts).values()]:
            self._add_leftover_item(name, p)
        self.drafts.clear()
        for name, p in drafts:
            it = QListWidgetItem(name); it.setData(Qt.UserRole, p); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked); self.drafts.addItem(it)
        for cb in (self.older, self.newer):
            keep = cb.currentData()
            cb.clear()
            for name, p in drafts:
                cb.addItem(name, p)
            if keep:
                if cb.findData(keep) < 0:
                    cb.addItem(os.path.basename(keep), keep)
                cb.setCurrentIndex(cb.findData(keep))
        if self.newer.count() > 1 and self.newer.currentIndex() == self.older.currentIndex():
            self.newer.setCurrentIndex(1)
        self.fill_written()

    # ------------------------------------------------------------ 3.29.0: written rules
    def fill_written(self, results=None):
        import excerpts as EX
        rules = EX.written_rules(R.Record(self.host.ws.root)) if self.host.ws is not None else []
        t = self.w_table
        t.blockSignals(True); t.setRowCount(0)
        for r in rules:
            i = t.rowCount(); t.insertRow(i)
            tick = QTableWidgetItem(); tick.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            tick.setCheckState(Qt.Checked if r["done"] else Qt.Unchecked); tick.setData(Qt.UserRole, r["id"])
            t.setItem(i, 0, tick)
            for c, val in ((1, r["text"]), (2, r["where"]),
                           (3, f"the phrase \u201c{r['phrase']}\u201d" if r["check"] == "phrase" and r["phrase"] else "a person (tick it)"),
                           (4, (results or {}).get(r["id"], (f"ticked by {r['by']}" if r["done"] and r["by"] else "")))):
                t.setItem(i, c, QTableWidgetItem(val))
        t.blockSignals(False)
        open_n = sum(1 for r in rules if not r["done"])
        self.w_sum.setText(f"{len(rules)} written rule(s); {open_n} not done yet." if rules else
                           "None yet: capture one from a piece in Shred (Written formatting rule).")
        self.w_card.setVisible(True)
        return rules

    def tick_written(self, it):
        import excerpts as EX
        if it.column() != 0 or self.host.ws is None:
            return
        EX.tick(R.Record(self.host.ws.root), it.data(Qt.UserRole), it.checkState() == Qt.Checked)
        diag.activity("written_rule_ticked")
        self.fill_written()

    def check_written(self, paths=None):
        """Each phrase rule looked for in the checked drafts: in every draft's headers or footers, or not. A rule found
        everywhere it should be is ticked."""
        import excerpts as EX
        if self.host.ws is None:
            return {}
        rec = R.Record(self.host.ws.root)
        if paths is None:
            paths = [self.drafts.item(i).data(Qt.UserRole) for i in range(self.drafts.count())
                     if self.drafts.item(i).checkState() == Qt.Checked]
        res = {}
        for r in EX.written_rules(rec):
            if r["check"] != "phrase" or not r["phrase"]:
                continue
            missing = []
            for p in paths:
                got = EX.phrase_in(p, r["phrase"])
                if not (got["headers"] or got["footers"] or got["body"]):
                    missing.append(os.path.basename(p))
            if not paths:
                res[r["id"]] = "no drafts to look in"
            elif missing:
                res[r["id"]] = "missing in " + ", ".join(missing)
            else:
                res[r["id"]] = f"found in every draft ({len(paths)})"
                EX.tick(rec, r["id"], True, who="Final Checks")
        diag.activity("written_rules_checked", n=len(res))
        self.fill_written(res)
        return res

    def _rows(self):
        try:
            from .custdocs import Ctx
            return Ctx(self.host).reg.rows()
        except Exception:
            diag.swallowed()
            return []

    def choose_folder(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "The folder with the final PDFs", self.folder.text() or os.path.expanduser("~"))
            if not folder:
                return ""
        self.folder.setText(folder)
        if self.host.ws is not None:
            self.host.ws.set("final_dir", folder)
        return folder

    # ------------------------------------------------------------ the package
    def check_package(self):
        import pkgcheck as PK
        d = self.folder.text().strip()
        if not d or not os.path.isdir(d):
            self.pkg_sum.setText("Choose the package folder first.")
            return None
        if self.host.ws is not None:
            self.host.ws.set("final_dir", d)
        paths = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".pdf")]
        allowed = ("Letter", "A4") if self.size.currentText() == "Letter or A4" else (self.size.currentText(),)
        self.pkg = PK.check(paths, [r for r in self._rows() if r.get("kind") == "Page limit"], self.mb.value() or None,
                            [w.strip() for w in self.contain.text().split(",") if w.strip()],
                            [x.strip() for x in self.required.toPlainText().splitlines() if x.strip()], allowed)
        t = self.pkg_table
        t.setRowCount(0)
        for fi in self.pkg["files"]:
            k = t.rowCount(); t.insertRow(k)
            for c, text in enumerate((fi["file"], str(fi["pages"]), str(fi["limit"] or ""), f"{fi['mb']:.1f}",
                                      "; ".join(fi["problems"]) or "OK", "; ".join(fi["notes"]))):
                it = QTableWidgetItem(text)
                if c == 4:
                    it.setForeground(D.color("crit" if fi["problems"] else "ok"))
                t.setItem(k, c, it)
        for m in self.pkg["missing"]:
            k = t.rowCount(); t.insertRow(k)
            t.setItem(k, 0, QTableWidgetItem(f"(missing) {m}"))
            it = QTableWidgetItem("no file for it in the package"); it.setForeground(D.color("crit")); t.setItem(k, 4, it)
        t.resizeRowsToContents()
        n, files = self.pkg["problems"], len(self.pkg["files"])
        self.pkg_sum.setText(f"{files} PDF{'s' if files != 1 else ''} checked: " + (f"{n} problem{'s' if n != 1 else ''} to fix before upload."
                                                                                    if n else "ready to upload."))
        diag.activity("package_checked", n=files)
        return self.pkg

    def export_package(self, path=None):
        import pkgcheck as PK
        if not self.pkg:
            self.host.status("Check the package first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the package check", self.host.out_path("package_check"), "Excel (*.xlsx)")
            if not path:
                return ""
        PK.export(path, self.pkg, self.host.effort_name)
        self.host.toast("Package check exported")
        return path

    # ------------------------------------------------------------ cross-references
    def check_elements(self):
        """3.32.0: the volumes' elements against the RFP (elementcheck)."""
        import elementcheck as EC
        import responseelements as RE
        R_ = self.host.review
        if R_ is None or not getattr(R_.M, "outline", None):
            self.e_sum.setText("Open an effort with a response structure (Matrix) first.")
            self.elements = []
            return []
        rows = EC.check(R_.M, RE.load(self.host.config_dir))
        self.elements = rows
        t = self.e_table
        t.setRowCount(0)
        for r in rows:
            k = t.rowCount(); t.insertRow(k)
            for c, text in enumerate((r["volume"], r["check"], r["element"], r["detail"], r["where"])):
                t.setItem(k, c, QTableWidgetItem(text))
        t.resizeRowsToContents()
        n = len(rows)
        self.e_sum.setText(f"{n} thing{'s' if n != 1 else ''} to look at." if n else
                           "Every element the RFP names is in its volume, in the RFP's order and in its part.")
        diag.activity("elements_checked", n=n)
        return rows

    def export_elements(self, path=None):
        import elementcheck as EC
        if self.elements is None:
            self.host.status("Check the elements first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the elements check", self.host.out_path("element_check"), "Excel (*.xlsx)")
            if not path:
                return ""
        EC.export(path, self.elements, self.host.effort_name)
        self.host.toast("Elements check exported")
        return path

    def check_xref(self):
        import xrefcheck as X
        out = []
        for i in range(self.drafts.count()):
            it = self.drafts.item(i)
            if it.checkState() == Qt.Checked:
                try:
                    out.append((it.text(), X.check(it.data(Qt.UserRole))))
                except Exception:
                    diag.swallowed()
        self.xref = out
        t = self.x_table
        t.setRowCount(0)
        for name, r in out:
            for p in r["problems"]:
                k = t.rowCount(); t.insertRow(k)
                for c, text in enumerate((name, p["kind"], p["where"], p["text"])):
                    t.setItem(k, c, QTableWidgetItem(text))
        t.resizeRowsToContents()
        n = t.rowCount()
        self.x_sum.setText("No drafts in the Volumes folder yet." if not out else
                           f"{len(out)} draft{'s' if len(out) != 1 else ''} read: " + (f"{n} problem{'s' if n != 1 else ''}." if n else
                                                                                         "numbering and references are clean."))
        diag.activity("xref_checked", n=n)
        return out

    # ------------------------------------------------------------ 3.57.0: leftovers
    def _add_leftover_item(self, name, p):
        it = QListWidgetItem(name); it.setData(Qt.UserRole, p); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked); self.l_files.addItem(it)

    def add_leftover_files(self, paths=None):
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Word files to check", "", "Word (*.docx)")
        have = {self.l_files.item(i).data(Qt.UserRole) for i in range(self.l_files.count())}
        for p in paths or []:
            if p.lower().endswith(".docx") and os.path.isfile(p) and p not in have:
                self._add_leftover_item(os.path.basename(p), p)
        return paths or []

    def check_leftovers(self, paths=None):
        import leftovers as LO
        from . import filewarn
        if paths:
            self.add_leftover_files(paths)
            want = set(paths)
        else:
            want = None
        out = []
        for i in range(self.l_files.count()):
            it = self.l_files.item(i)
            p = it.data(Qt.UserRole)
            if (want is None and it.checkState() == Qt.Checked) or (want is not None and p in want):
                try:
                    out.append((it.text(), LO.check(p)))
                except Exception:
                    diag.swallowed()
                filewarn.say(self.host, [p])
        self.leftover = out
        t = self.l_table
        t.setRowCount(0)
        for name, r in out:
            for x in r["items"]:
                k = t.rowCount(); t.insertRow(k)
                for c, text in enumerate((name, x["kind"], x["where"], x["text"])):
                    t.setItem(k, c, QTableWidgetItem(text))
                t.item(k, 1).setToolTip(LO.WHY.get(x["kind"], ""))
        t.resizeRowsToContents()
        self.l_sum.setText("No Word files to check: add files, or put drafts in the effort's Volumes folder." if not out else
                           "; ".join(f"{name}: {LO.summary(r)}" for name, r in out))
        diag.activity("leftovers_checked", n=t.rowCount())
        return out

    def export_leftovers(self, path=None):
        import leftovers as LO
        if not self.leftover:
            self.host.status("Check for leftovers first.")
            return ""
        if path is None:
            start = os.path.join(os.path.dirname(self.host.out_path("xref_check")), "Leftovers check.xlsx") if self.host.effort_path else ""
            path, _ = QFileDialog.getSaveFileName(self, "Export the leftovers check", start, "Excel (*.xlsx)")
            if not path:
                return ""
        LO.export(path, self.leftover, self.host.effort_name)
        self.host.toast("Leftovers check exported")
        return path

    def export_xref(self, path=None):
        import xrefcheck as X
        if not self.xref:
            self.host.status("Check the drafts first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the cross-reference check", self.host.out_path("xref_check"), "Excel (*.xlsx)")
            if not path:
                return ""
        X.export(path, self.xref, self.host.effort_name)
        self.host.toast("Cross-reference check exported")
        return path

    # ------------------------------------------------------------ compare
    def pick_file(self, cb, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A version of the draft", os.path.expanduser("~"), "Word (*.docx)")
            if not path:
                return ""
        if cb.findData(path) < 0:
            cb.addItem(os.path.basename(path), path)
        cb.setCurrentIndex(cb.findData(path))
        return path

    def open_compare(self):
        """3.55.0: the two versions picked here, compared in the Compare space (Any two files)."""
        a, b = self.older.currentData(), self.newer.currentData()
        if not a or not b or a == b:
            self.c_sum.setText("Pick two different versions.")
            return None
        self.host.go("compare")
        return self.host.compare_space.show_files(a, b)

    def compare(self):
        import draftcompare as DC
        import html
        a, b = self.older.currentData(), self.newer.currentData()
        if not a or not b or a == b:
            self.c_sum.setText("Pick two different versions.")
            return None
        self.cmp = DC.compare(a, b)
        c = self.cmp["counts"]
        secs = DC.by_section(self.cmp["rows"])
        lines = "".join(f"<br>&nbsp;&nbsp;{html.escape(s)}: {d['changed']} changed, {d['added']} added, {d['removed']} removed"
                        for s, d in list(secs.items())[:20])
        self.c_sum.setText(f"<b>{c['changed']} changed, {c['added']} added, {c['removed']} removed</b> "
                           f"({html.escape(os.path.basename(a))} to {html.escape(os.path.basename(b))}).{lines}"
                           + ("<br>&nbsp;&nbsp;..." if len(secs) > 20 else ""))
        diag.activity("drafts_compared", n=c["changed"] + c["added"] + c["removed"])
        return self.cmp

    def export_redline(self, path=None):
        import draftcompare as DC
        if not self.cmp:
            self.host.status("Compare two versions first.")
            return ""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the redline", self.host.out_path(
                "draft_redline", Doc=os.path.splitext(self.cmp["new"]["file"])[0].replace(" ", "_")), "Word (*.docx)")
            if not path:
                return ""
        DC.export(path, self.cmp, os.path.splitext(self.cmp["new"]["file"])[0])
        self.host.toast("Redline exported")
        return path
