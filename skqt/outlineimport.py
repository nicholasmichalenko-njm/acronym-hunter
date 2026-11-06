"""Setup > From an outline workbook... (3.71.0): the team's outline Excel read into the setup. Columns (what each one is,
guessed from its heading), formatting rules (the setup style each look in a column takes), the preview (the structure as
the setup will be, every block drawn in its setup style's look, hidden text marked), the problems, and Use this
structure. outlinexl holds the rules; the workbook is only read."""
import html, os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                               QListWidget, QSplitter, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)
import diag
import outlinelayouts as OL
import outlinexl as OX
import setuptemplate as ST
from . import design as D

MIXED_ROLES = ("requirement", "support", "guidance")


def look_css(lk):
    """A setup style's look as CSS for the preview."""
    css = [f"color:#{lk.get('color') or '000000'}"]
    if lk.get("bold"):
        css.append("font-weight:bold")
    if lk.get("italic"):
        css.append("font-style:italic")
    if lk.get("font"):
        css.append(f"font-family:'{html.escape(lk['font'])}'")
    if lk.get("size"):
        css.append(f"font-size:{float(lk['size']):g}pt")
    return ";".join(css)


def run_css(look):
    css = ["color:" + ("#000000" if look[2:] == "auto" else "#" + look[2:])]
    if look[0] == "B":
        css.append("font-weight:bold")
    if look[1] == "I":
        css.append("font-style:italic")
    return ";".join(css)


class OutlineImport(QDialog):
    def __init__(self, page, path):
        super().__init__(page)
        self.page, self.host, self.path = page, page.host, path
        self.setWindowTitle(f"Setup from {os.path.basename(path)}")
        self.resize(1200, 820)
        self.book = OX.read(path, known=OL.known_names(page.host.config_dir))
        self.profile = OL.profile(self.host.config_dir, self.book)          # 3.73.0: the closest layout set ahead of time
        self.opts = self.page.setup_opts()
        v = QVBoxLayout(self)
        self.top = D.label("", "muted"); v.addWidget(self.top)
        nr = QHBoxLayout(); v.addLayout(nr)
        self.new_cols = D.label("", "muted"); nr.addWidget(self.new_cols, 1)
        self.b_keep_new = D.button("Remember these columns", None, lambda: self.remember_new(),
                                   "Keep the new columns in the layout as they are set here")
        nr.addWidget(self.b_keep_new)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(D.SectionTitle("Columns"))
        self.cols = QTableWidget(0, 2); self.cols.setHorizontalHeaderLabels(["Column in the workbook", "It holds"])
        self.cols.verticalHeader().setVisible(False); self.cols.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cols.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed); self.cols.setColumnWidth(1, 210)
        lv.addWidget(self.cols, 2)
        lv.addWidget(D.SectionTitle("Formatting rules"))
        lv.addWidget(D.label("For a column whose cells mix kinds of text, the setup style each look takes.", "muted"))
        self.rules = QTableWidget(0, 4); self.rules.setHorizontalHeaderLabels(["Column", "Look (a sample)", "Times", "Setup style"])
        self.rules.verticalHeader().setVisible(False); self.rules.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for c, wd in ((0, 130), (2, 54), (3, 210)):
            self.rules.horizontalHeader().setSectionResizeMode(c, QHeaderView.Fixed); self.rules.setColumnWidth(c, wd)
        lv.addWidget(self.rules, 3)
        split.addWidget(left)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(D.SectionTitle("The setup, as it will be"))
        self.preview = QTextBrowser(); rv.addWidget(self.preview, 4)
        self.preview.setStyleSheet("QTextBrowser{background:#FFFFFF;color:#000000}")   # a page, as Word shows it
        rv.addWidget(D.SectionTitle("To look at"))
        self.problems = QListWidget(); rv.addWidget(self.problems, 1)
        split.addWidget(right)
        split.setSizes([560, 640])
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(D.button("Setup styles...", None, lambda: self.styles()))
        bar.addWidget(D.button("Save these columns and rules...", None, lambda: self.save_profile(),
                               "Kept for the next workbook laid out the same way"))
        bar.addStretch(1)
        bb = QDialogButtonBox(); self.b_use = bb.addButton("Use this structure", QDialogButtonBox.AcceptRole)
        bb.addButton(QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        bar.addWidget(bb)
        self.fill_columns()

    # ------------------------------------------------------------ columns and rules
    def fill_columns(self):
        hs = [h for h in self.book["headers"] if h]
        self.cols.blockSignals(True); self.cols.setRowCount(len(hs))
        for i, h in enumerate(hs):
            self.cols.setItem(i, 0, QTableWidgetItem(h))
            cb = QComboBox()
            for k, t in OX.ROLES:
                cb.addItem(t, k)
            cb.setCurrentIndex(max(0, cb.findData((self.profile["columns"] or {}).get(h, "ignore"))))
            cb.currentIndexChanged.connect(lambda _i, hh=h, c=cb: self.set_role(hh, c.currentData()))
            self.cols.setCellWidget(i, 1, cb)
            if h in (self.profile.get("unknown") or []):
                self.cols.item(i, 0).setToolTip("Not in the layout yet: what you pick here is remembered")
                f = self.cols.item(i, 0).font(); f.setBold(True); self.cols.item(i, 0).setFont(f)
        self.cols.blockSignals(False)
        self.say_new()
        self.fill_rules()

    def set_role(self, header, role):
        self.profile.setdefault("columns", {})[header] = role
        if header in (self.profile.get("unknown") or []):          # 3.73.0: asked once, remembered in the layout
            OL.remember(self.host.config_dir, self.profile.get("name") or OL.STARTING, header, role)
            self.profile["unknown"].remove(header)
            self.say_new()
        self.fill_rules()

    def remember_new(self):
        """3.73.0: every new column kept in the layout as it is set now. Returns how many."""
        un = list(self.profile.get("unknown") or [])
        for h in un:
            OL.remember(self.host.config_dir, self.profile.get("name") or OL.STARTING, h, (self.profile.get("columns") or {}).get(h, "ignore"))
        self.profile["unknown"] = []
        self.say_new()
        return len(un)

    def say_new(self):
        un = self.profile.get("unknown") or []
        self.b_keep_new.setVisible(bool(un))
        self.new_cols.setText(("Layout: " + (self.profile.get("name") or "none yet") + ". ")
                              + (f"New column(s) the layout does not know: {', '.join(un)}. Say what each holds; it is remembered."
                                 if un else "Every column is in the layout."))

    def fill_rules(self):
        rows = []
        for h, role in (self.profile.get("columns") or {}).items():
            if role in MIXED_ROLES:
                lk = OX.looks(self.book, h)
                if len(lk) > 1:
                    rows += [(h, role, x) for x in lk]
        self.rules.setRowCount(len(rows))
        for i, (h, role, x) in enumerate(rows):
            self.rules.setItem(i, 0, QTableWidgetItem(h))
            lab = QLabel(f'<span style="{run_css(x["look"])}">{html.escape(x["sample"])}</span>'
                         f'  <span style="color:gray">({html.escape(OX.look_words(x["look"]))})</span>')
            lab.setTextFormat(Qt.RichText); self.rules.setCellWidget(i, 1, lab)
            self.rules.setItem(i, 2, QTableWidgetItem(str(x["count"])))
            cb = QComboBox()
            for k, t in OX.KINDS:
                cb.addItem(t, k)
            have = (self.profile.get("rules") or {}).get(h, {}).get(x["look"])
            cb.setCurrentIndex(max(0, cb.findData(have or OX.DEFAULT_KIND[role])))
            if have is None:                               # shown, and kept, as the default until changed
                self.profile.setdefault("rules", {}).setdefault(h, {})[x["look"]] = cb.currentData()
            cb.currentIndexChanged.connect(lambda _i, hh=h, lk=x["look"], c=cb: self.set_rule(hh, lk, c.currentData()))
            self.rules.setCellWidget(i, 3, cb)
        self.redraw()

    def set_rule(self, header, look, kind):
        self.profile.setdefault("rules", {}).setdefault(header, {})[look] = kind
        self.redraw()

    # ------------------------------------------------------------ preview
    def redraw(self):
        self.parsed = OX.parse(self.book, self.profile)
        out = ['<div style="font-family:Arial;font-size:10pt">']
        for s in self.parsed["sections"]:
            sz = max(10, 16 - 2 * (s["level"] - 1))
            out.append(f'<p style="font-weight:bold;font-size:{sz}pt;margin:10px 0 3px {(s["level"] - 1) * 14}px">'
                       f'{html.escape((s["num"] + " ") if s["num"] else "")}{html.escape(s["title"])}'
                       + (f' <span style="font-weight:normal;font-size:9pt;color:gray">Authors: {html.escape(", ".join(s["authors"]))}</span>'
                          if s["authors"] else "") + "</p>")
            for b in s["blocks"]:
                lk = ST.look(self.opts, b["kind"])
                txt = (f'{b["ref"]}: ' if b["kind"] == "rfp" and b["ref"] else "") + b["text"]
                hid = "background-color:#ECEEF3;" if lk["hidden"] else ""       # Qt draws no dotted underline; a gray band instead
                out.append(f'<p style="margin:2px 0 2px {s["level"] * 14 + 10}px;{hid}{look_css(lk)}">{html.escape(txt)}'
                           f' <span style="color:gray;font-size:8pt;font-style:normal;font-weight:normal">{html.escape(lk["style"])}</span></p>')
        out.append("</div>")
        self.html = "".join(out)
        self.preview.setHtml(self.html)
        self.problems.clear()
        self.problems.addItems(self.parsed["problems"] or ["Nothing to look at: every row has a home and a style."])
        n = sum(1 for s in self.parsed["sections"] for b in s["blocks"] if b["kind"] == "rfp")
        self.top.setText(f"{os.path.basename(self.path)}: {len(self.parsed['sections'])} section(s), {n} requirement(s). "
                         "Hidden text shows on a gray band (Word shows it with Show/Hide on).")

    def styles(self):
        from .setupstyles import SetupStyles
        SetupStyles(self.page).exec()
        self.opts = self.page.setup_opts()
        self.redraw()

    def save_profile(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "Save these columns and rules", "A name for this outline layout:",
                                            text=self.profile.get("name") or "Our outline")
            if not ok or not name.strip():
                return None
        OL.from_profile(self.host.config_dir, name.strip(), self.profile)       # 3.73.0: kept as a layout
        self.profile["name"] = name.strip()
        self.host.toast(f"Saved: {name.strip()}")
        return name.strip()


def import_outline(page, path=None, profile=None, accept=None):
    """The import, start to end. accept (tests): True to use the structure without the window. Returns the counts."""
    if path is None:
        path, _ = QFileDialog.getOpenFileName(page, "The outline workbook", "", "Excel (*.xlsx *.xlsm)")
        if not path:
            return None
    try:
        dlg = OutlineImport(page, path)
    except Exception:  # noqa: BLE001  not a workbook it can read
        diag.swallowed()
        page.host.status("That file does not read as an Excel workbook.")
        return None
    if profile is not None:
        dlg.profile = profile; dlg.fill_columns()
    page.outline_dialog = dlg
    if accept is None:
        if dlg.exec() != QDialog.Accepted:
            return None
    elif not accept:
        return None
    dlg.remember_new()                                  # 3.73.0: using the structure confirms what the columns hold
    return page.use_outline(dlg.parsed, os.path.basename(path), path=path, headers=dlg.book["headers"],
                            layout=dlg.profile.get("name") or "", accept=accept)
