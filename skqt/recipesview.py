"""Rules > Field recipes (3.66.0): the team's field codes, written and changed here. A table of recipes, the one picked
in the boxes below (name, where it is used, its codes one per line, the text between them, the bookmark it needs and
what it spans, the style it reads, a note), Read a template (its fields, each matched to a recipe, differing, or with
none; make a recipe from one) and This effort's own codes. fieldrecipes holds the rules."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QPlainTextEdit, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import fieldrecipes as FR
from . import design as D


class RecipesView(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.rows, self.found = [], []
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["s"])
        v.addWidget(D.label("Your field codes, exactly as your templates use them. Every check reads this list: the template "
                            "check, Final Check and Read a template. Change one and the next check follows it. The starters "
                            "are yours to change or remove; appendices use Heading 7 to 9.", "muted"))
        split = QSplitter(Qt.Vertical); v.addWidget(split, 1)
        top = QWidget(); tv = QVBoxLayout(top); tv.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Recipe", "Where", "Field code", "Bookmark", "Style it reads"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.show_one)
        tv.addWidget(self.table, 1)
        tb = QHBoxLayout(); tv.addLayout(tb)
        tb.addWidget(D.button("+ Recipe", "primary", lambda: self.new()))
        tb.addWidget(D.button("Remove", "danger", lambda: self.remove()))
        tb.addWidget(D.button("Put back the starters", "ghost", lambda: self.restore(), "Any starter you removed comes back; ones you changed stay"))
        tb.addStretch(1)
        tb.addWidget(D.button("Read a template...", None, lambda: self.read_file(), "List the fields in a Word file or template you trust"))
        split.addWidget(top)
        ed = QWidget(); ev = QVBoxLayout(ed); ev.setContentsMargins(0, 0, 0, 0)
        f = QFormLayout(); f.setSpacing(D.SPACE["s"]); ev.addLayout(f)
        self.e_name = QLineEdit(); f.addRow("Name", self.e_name)
        self.e_where = QComboBox(); self.e_where.addItems(FR.WHERE); f.addRow("Where it is used", self.e_where)
        self.e_codes = QPlainTextEdit(); self.e_codes.setMaximumHeight(70)
        self.e_codes.setPlaceholderText('One field per line, as Word shows it with Alt+F9, without the braces. For example:\nSTYLEREF 1 \\s\nSEQ Table \\* ARABIC \\s 1')
        f.addRow("Field code(s)", self.e_codes)
        self.e_between = QLineEdit(); self.e_between.setPlaceholderText("The text between the fields (a caption's hyphen)"); f.addRow("Between", self.e_between)
        self.preview = D.label("", None); self.preview.setToolTip("What Word would show on a sample page: page 3 of 12, under "
                                                                   "Heading 1 \"2 Technical Approach\", after one table and two figures")
        f.addRow("It shows", self.preview)                   # 4.7.0: worked out while you type (fieldpreview)
        self.e_codes.textChanged.connect(self.show_preview); self.e_between.textChanged.connect(lambda _t: self.show_preview())
        self.e_bm = QLineEdit(); self.e_bm.setPlaceholderText("For example Response"); f.addRow("Bookmark it needs", self.e_bm)
        self.e_spans = QLineEdit(); self.e_spans.setPlaceholderText("What the bookmark must hold"); f.addRow("The bookmark spans", self.e_spans)
        self.e_style = QLineEdit(); f.addRow("Style it reads", self.e_style)
        self.e_note = QLineEdit(); f.addRow("Note", self.e_note)
        sr = QHBoxLayout(); ev.addLayout(sr)
        sr.addWidget(D.button("Save the recipe", "primary", lambda: self.save()))
        self.b_own = D.button("This effort's own code...", "ghost", lambda: self.effort_own(),
                              "Use a different code for this recipe in the open effort only (Effort Formatting lists it)")
        sr.addWidget(self.b_own)
        sr.addStretch(1)
        self.own_lab = D.label("", "muted"); ev.addWidget(self.own_lab)
        split.addWidget(ed)
        # Read a template
        rd = QWidget(); rv = QVBoxLayout(rd); rv.setContentsMargins(0, 0, 0, 0)
        self.found_lab = D.label("Read a template... lists a file's fields here, each against your recipes.", "muted"); rv.addWidget(self.found_lab)
        self.ftable = QTableWidget(0, 4); self.ftable.setHorizontalHeaderLabels(["Where", "Field code", "Against the recipes", "The recipe says"])
        self.ftable.verticalHeader().setVisible(False); self.ftable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ftable.setSelectionBehavior(QTableWidget.SelectRows); self.ftable.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        rv.addWidget(self.ftable, 1)
        fr = QHBoxLayout(); rv.addLayout(fr)
        fr.addWidget(D.button("Make a recipe from it", None, lambda: self.from_found()))
        fr.addStretch(1)
        split.addWidget(rd)
        split.setSizes([300, 260, 220])

    # ------------------------------------------------------------ the list
    def cfg(self):
        return self.host.config_dir

    def refresh(self, keep=None):
        keep = keep or self.current_id()
        self.rows = FR.effective(self.cfg(), self.host.ws)
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            code = (f" {r['between']} " if r.get("between") else "  then  ").join(r["codes"])
            for j, val in enumerate((r["name"] + (" (this effort's own)" if r.get("effort_own") else ""), r["where"], code,
                                     r.get("bookmark", ""), r.get("style", ""))):
                self.table.setItem(i, j, QTableWidgetItem(val))
        ids = [r["id"] for r in self.rows]
        if keep in ids:
            self.table.selectRow(ids.index(keep))
        elif self.rows:
            self.table.selectRow(0)
        self.b_own.setEnabled(self.host.ws is not None)

    def current_id(self):
        i = self.table.currentRow()
        return self.rows[i]["id"] if 0 <= i < len(self.rows) else None

    def show_one(self):
        rid = self.current_id()
        team = next((r for r in FR.load(self.cfg()) if r["id"] == rid), None)
        r = team or {}
        self.e_name.setText(r.get("name", "")); self.e_where.setCurrentText(r.get("where", "Other"))
        self.e_codes.setPlainText("\n".join(r.get("codes", []))); self.e_between.setText(r.get("between", ""))
        self.e_bm.setText(r.get("bookmark", "")); self.e_spans.setText(r.get("spans", ""))
        self.e_style.setText(r.get("style", "")); self.e_note.setText(r.get("note", ""))
        eff = next((x for x in self.rows if x["id"] == rid), None)
        self.own_lab.setText(f"{self.host.effort_name} uses its own code: " + "  then  ".join(eff["codes"]) if eff and eff.get("effort_own") else "")

    def show_preview(self):
        """4.7.0: the sample result of the codes typed, or what the rules cannot work out."""
        import fieldpreview as FP
        codes = [c for c in self.e_codes.toPlainText().splitlines() if c.strip()]
        if not codes:
            self.preview.setText("")
            return ""
        text, known = FP.recipe(codes, self.e_between.text(), label=FP.label_of(codes))
        shown = text if known else (text.replace(FP.OTHER, "").strip() + ("  " if text.replace(FP.OTHER, "").strip() else "")
                                    + "(Word shows this one: Check in Word updates it in a real copy)")
        self.preview.setText(shown)
        return shown

    def values(self):
        return {"name": self.e_name.text(), "where": self.e_where.currentText(), "codes": self.e_codes.toPlainText().splitlines(),
                "between": self.e_between.text(), "bookmark": self.e_bm.text(), "spans": self.e_spans.text(),
                "style": self.e_style.text(), "note": self.e_note.text()}

    def save(self, values=None):
        rid = self.current_id()
        v = values or self.values()
        if not [c for c in v.get("codes", []) if str(c).strip()]:
            self.host.status("Type the field code, one field per line.")
            return False
        ok = FR.update(self.cfg(), rid, **v) if rid else bool(FR.add(self.cfg(), v))
        diag.activity("field_recipe_saved")
        self.host.toast("Recipe saved: the next check reads it")
        self.refresh(rid)
        return ok

    def new(self, values=None):
        v = values or {"name": "A new recipe", "where": "Other", "codes": ["PAGE"]}
        rid = FR.add(self.cfg(), v)
        self.refresh(rid)
        self.e_name.setFocus(); self.e_name.selectAll()
        return rid

    def remove(self, rid=None):
        rid = rid or self.current_id()
        ok = FR.remove(self.cfg(), rid) if rid else False
        self.refresh()
        return ok

    def restore(self):
        FR.restore_starters(self.cfg())
        self.refresh()
        return len(self.rows)

    def effort_own(self, codes=None):
        rid = self.current_id()
        if self.host.ws is None or not rid:
            return None
        if codes is None:
            from PySide6.QtWidgets import QInputDialog
            cur = next((x for x in self.rows if x["id"] == rid), {})
            text, ok = QInputDialog.getMultiLineText(self, f"{self.host.effort_name}'s own code",
                                                     "One field per line. Leave it empty to use the team's recipe again.",
                                                     "\n".join(cur.get("codes", [])) if cur.get("effort_own") else "")
            if not ok:
                return None
            codes = text.splitlines()
        FR.set_effort_codes(self.host.ws, rid, codes)
        self.refresh(rid)
        return codes

    # ------------------------------------------------------------ Read a template
    def read_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A Word file or template you trust", "", "Word (*.docx *.dotx *.docm *.dotm)")
            if not path:
                return None
        fields = FR.read_fields(path)
        self.found = FR.check(fields, self.rows or FR.effective(self.cfg(), self.host.ws))
        self.ftable.setRowCount(len(self.found))
        for i, r in enumerate(self.found):
            for j, val in enumerate((r["part"], r["code"], {"matches": f"matches {r['recipe']}", "differs": f"differs from {r['recipe']}",
                                                            "no recipe": "no recipe"}[r["status"]], r["expected"])):
                c = QTableWidgetItem(val)
                if j == 2 and r["status"] != "matches":
                    c.setForeground(D.color("warn" if r["status"] == "differs" else "muted"))
                self.ftable.setItem(i, j, c)
        n = FR.summary(self.found)
        miss = FR.missing_bookmarks(path, self.rows)
        self.found_lab.setText(f"{len(fields)} field(s): {n['matches']} match a recipe, {n['differs']} differ, {n['no recipe']} have none."
                               + (f" Missing bookmark(s): {', '.join(miss)}." if miss else ""))
        diag.activity("template_fields_read", n=len(fields))
        return self.found

    def from_found(self, row=None):
        row = self.ftable.currentRow() if row is None else row
        if not (0 <= row < len(self.found)):
            self.host.status("Pick a field from the template first.")
            return None
        r = self.found[row]
        k = FR.kind(r["code"])[0]
        where = {"TOC": "Table of contents", "SEQ": "Caption", "PAGE": "Page number", "REF": "Cross-reference"}.get(k, "Header or footer" if r["part"].startswith(("Header", "Footer")) else "Other")
        bm = FR.kind(r["code"])[1] if k == "TOC" else ""
        rid = FR.add(self.cfg(), {"name": f"{k.title()} from the template", "where": where, "codes": [r["code"]], "bookmark": bm})
        self.refresh(rid)
        return rid
