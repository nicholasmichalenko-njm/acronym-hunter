"""Setup > Bring in a file... with an Excel workbook (3.71.0): the team's outline read into the setup. 3.73.0: one list,
What's in your workbook (each look found in each column, with one pick for what it is), and the cells piece by piece
(click a piece to change it); then the preview (the structure as
the setup will be, every block drawn in its setup style's look, hidden text marked), the problems, and Use this
structure. outlinexl holds the rules; the workbook is only read."""
import html, os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                               QListWidget, QMenu, QSplitter, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)
import diag
import outlinelayouts as OL
import outlinexl as OX
import setuptemplate as ST
from . import design as D

MIXED_ROLES = OX.TEXT_ROLES
# 3.73.0 (decision 10): one pick for each row of What's in your workbook, the kinds of text first, then the structure
PICKS = (("rfp", "Compliance requirement"), ("customer", "Customer requirement text"), ("support", "Supporting RFP text"),
         ("pm", "Management guidance"), ("section_number", "Section number"), ("section_name", "Section name"),
         ("reference", "RFP reference"), ("authors", "Authors"), ("skip", "Not used"))
PICK = dict(PICKS)
KIND_ROLE = {"rfp": "requirement", "customer": "requirement", "support": "support", "pm": "guidance", "skip": "support"}
TINT = {"rfp": "#FDECEC", "customer": "#F1EAFB", "support": "#E8F1FB", "pm": "#EAF6EC", "skip": "#EEEEEE",
        "section_number": "#FFF6DD", "section_name": "#FFF6DD", "reference": "#FFF6DD", "authors": "#FFF6DD"}


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
        self.profile.setdefault("rules", {})
        self.layout_now = OL.load(self.host.config_dir).get(self.profile.get("name") or OL.STARTING) or OL.new_layout()
        nr.addWidget(self.b_keep_new)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(D.SectionTitle("What's in your workbook"))          # 3.73.0, decision 10: one list
        lv.addWidget(D.label("Each kind of text found in each column, as it looks in the workbook. Say what each one is. "
                             "A column whose cells mix kinds of text has a row for each.", "muted"))
        self.list = QTableWidget(0, 4); self.list.setHorizontalHeaderLabels(["Column", "Text that looks like this", "Places", "It is"])
        self.list.verticalHeader().setVisible(False); self.list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for c, wd in ((0, 150), (2, 64), (3, 210)):
            self.list.horizontalHeader().setSectionResizeMode(c, QHeaderView.Fixed); self.list.setColumnWidth(c, wd)
        self.list.setSelectionBehavior(QAbstractItemView.SelectRows); self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.currentCellChanged.connect(lambda r, _c, _r2, _c2: self.show_cells(self.list_rows[r][0] if 0 <= r < len(self.list_rows) else None))
        lv.addWidget(self.list, 3)
        lv.addWidget(D.SectionTitle("Cells, piece by piece"))
        self.cells_note = D.label("", "muted"); lv.addWidget(self.cells_note)
        self.cells = QTextBrowser(); self.cells.setOpenLinks(False); self.cells.setOpenExternalLinks(False)
        self.cells.setStyleSheet("QTextBrowser{background:#FFFFFF;color:#000000}")
        self.cells.anchorClicked.connect(lambda url: self.piece_menu(url.toString()))
        lv.addWidget(self.cells, 2)
        split.addWidget(left)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(D.SectionTitle("The setup, as it will be"))
        self.preview = QTextBrowser(); rv.addWidget(self.preview, 4)
        self.preview.setStyleSheet("QTextBrowser{background:#FFFFFF;color:#000000}")   # a page, as Word shows it
        rv.addWidget(D.SectionTitle("To look at"))
        self.problems = QListWidget(); rv.addWidget(self.problems, 1)
        split.addWidget(right)
        split.setSizes([680, 620])
        bar = QHBoxLayout(); v.addLayout(bar)
        bar.addWidget(D.button("Setup styles...", None, lambda: self.styles()))
        bar.addWidget(D.button("Save as a layout...", None, lambda: self.save_profile(),
                               "Kept for the next workbook laid out the same way (Use this structure keeps it too)"))
        bar.addStretch(1)
        bb = QDialogButtonBox(); self.b_use = bb.addButton("Use this structure", QDialogButtonBox.AcceptRole)
        bb.addButton(QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        bar.addWidget(bb)
        self.fill_columns()

    # ------------------------------------------------------------ what's in the workbook (3.73.0, decision 10)
    def pick_of(self, header, look):
        """What a row of the list is now: a setup kind for a look in a column of text, else the column's role (or skip)."""
        role = (self.profile.get("columns") or {}).get(header, "ignore")
        if role in OX.TEXT_ROLES and look is not None:
            return (self.profile["rules"].get(header) or {}).get(look) or OX.DEFAULT_KIND[role]
        return "skip" if role == "ignore" else role

    def fill_columns(self):
        """One row per look in each column of text; one row for any other column."""
        self.list_rows = []
        for h in [h for h in self.book["headers"] if h]:
            role = (self.profile.get("columns") or {}).get(h, "ignore")
            lk = OX.looks(self.book, h)
            if role in OX.TEXT_ROLES and lk:
                for x in lk:
                    self.profile["rules"].setdefault(h, {}).setdefault(x["look"], self.pick_of(h, x["look"]))   # shown, and kept
                    self.list_rows.append((h, x["look"], x["sample"], x["count"]))
            else:
                self.list_rows.append((h, None, lk[0]["sample"] if lk else "", sum(x["count"] for x in lk)))
        self.list.blockSignals(True); self.list.setRowCount(len(self.list_rows))
        first = {}
        for i, (h, look, sample, count) in enumerate(self.list_rows):
            new = first.setdefault(h, i) == i
            it = QTableWidgetItem(h if new else ""); it.setToolTip(h); it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            if new and h in (self.profile.get("unknown") or []):
                it.setToolTip("Not in the layout yet: what you pick here is remembered")
                f = it.font(); f.setBold(True); it.setFont(f)
            self.list.setItem(i, 0, it)
            lkk = look or (OX.looks(self.book, h)[0]["look"] if OX.looks(self.book, h) else "--auto")
            words = OX.look_words(lkk).replace("black", "black text") if look else "whole column"
            words = words.split(" (#")[0]
            lab = QLabel(f'<span style="color:gray">{html.escape(words)}:</span> '
                         f'<span style="{run_css(lkk)}">{html.escape(sample or "(empty)")}</span>')
            lab.setTextFormat(Qt.RichText); lab.setToolTip(f"{OX.look_words(lkk) if look else 'The whole column'}: {sample}")
            self.list.setCellWidget(i, 1, lab)
            n = QTableWidgetItem(str(count)); n.setFlags(n.flags() & ~Qt.ItemIsEditable); self.list.setItem(i, 2, n)
            cb = QComboBox()
            for k, t in PICKS:
                cb.addItem(t, k)
            cb.setCurrentIndex(max(0, cb.findData(self.pick_of(h, look))))
            cb.currentIndexChanged.connect(lambda _i, hh=h, lk=look, c=cb: self.set_pick(hh, lk, c.currentData()))
            self.list.setCellWidget(i, 3, cb)
        self.list.blockSignals(False)
        self.list.resizeRowsToContents()
        self.say_new()
        self.redraw()
        keep = getattr(self, "cells_col", None)
        self.show_cells(keep if keep in first else next((h for h, lk, _s, _n in self.list_rows if lk), None))

    def row_of(self, header, look=None):
        return next((i for i, (h, lk, _s, _n) in enumerate(self.list_rows) if h == header and (look is None or lk == look)), -1)

    def set_pick(self, header, look, pick):
        """A pick on a row. A structure pick takes the whole column; a kind of text on a look sets that look; a kind of
        text on a whole column makes it a column of text, its looks by the layout's rules where they have one."""
        cols, rules = self.profile.setdefault("columns", {}), self.profile["rules"]
        role = cols.get(header, "ignore")
        if pick in OX.STRUCT_ROLES or (pick == "skip" and (look is None or role not in OX.TEXT_ROLES)):
            cols[header] = "ignore" if pick == "skip" else pick
            rules.pop(header, None)
        elif role in OX.TEXT_ROLES and look is not None:
            rules.setdefault(header, {})[look] = pick
            main = [(x["count"], rules[header].get(x["look"])) for x in OX.looks(self.book, header)]
            main = [k for _c, k in sorted(main, key=lambda t: -t[0]) if k and k != "skip"]
            if main:
                cols[header] = KIND_ROLE[main[0]]
        else:
            cols[header] = KIND_ROLE[pick]
            rules[header] = {x["look"]: OL.rule_kind(self.layout_now, cols[header], x["look"]) or pick
                             for x in OX.looks(self.book, header)}
        if header in (self.profile.get("unknown") or []):          # asked once, remembered in the layout
            OL.remember(self.host.config_dir, self.profile.get("name") or OL.STARTING, header, cols[header])
            self.profile["unknown"].remove(header)
        self.cells_col = header
        self.fill_columns()

    def set_role(self, header, role):
        """A column's role, as 3.71.0 set it (tests and callers): the whole column's row."""
        self.set_pick(header, None, "skip" if role == "ignore" else role if role in OX.STRUCT_ROLES else OX.DEFAULT_KIND[role])

    def set_rule(self, header, look, kind):
        self.set_pick(header, look, kind)

    def show_cells(self, header):
        """The column's cells with the most kinds of text first, each piece marked by what it is; a click changes it."""
        self.cells_col = header
        if not header or header not in self.book["headers"]:
            self.cells_note.setText("Pick a row above to see its column's cells."); self.cells.setHtml(""); self.cell_html = ""
            return
        i = self.book["headers"].index(header)
        cells = [(r["row"], r["cells"][i]) for r in self.book["rows"] if i < len(r["cells"]) and any(t.strip() for t, _lk in r["cells"][i])]
        cells.sort(key=lambda rc: -len({lk for _t, lk in rc[1]}))
        role = (self.profile.get("columns") or {}).get(header, "ignore")
        out = ['<div style="font-family:Arial;font-size:10pt">']
        for row, runs in cells[:5]:
            out.append(f'<p style="margin:6px 0 2px 0;color:gray;font-size:8pt">Row {row}</p><p style="margin:0 0 6px 0">')
            for t, lk in runs:
                k = self.pick_of(header, lk) if role in OX.TEXT_ROLES else self.pick_of(header, None)
                body = t.rstrip("\n")
                out.append(f'<a href="pick:{i}:{lk}" style="{run_css(lk)};text-decoration:none;background-color:{TINT.get(k, "#FFFFFF")}">'
                           f'{html.escape(body).replace(chr(10), "<br>")}</a><span style="color:gray;font-size:8pt"> [{html.escape(PICK[k])}]</span>'
                           + ("<br>" if body != t else " "))
            out.append("</p>")
        out.append("</div>")
        self.cell_html = "".join(out)
        self.cells.setHtml(self.cell_html)
        self.cells_note.setText(f"{header}: each piece is marked with what it is. Click a piece to change it; every piece that "
                                "looks the same in this column follows.")

    def piece_menu(self, link, pick=None):
        """A clicked piece: the kinds to choose from (pick, for tests: chosen without the menu)."""
        try:
            _p, i, look = link.split(":", 2)
            header = self.book["headers"][int(i)]
        except (ValueError, IndexError):
            return None
        role = (self.profile.get("columns") or {}).get(header, "ignore")
        if pick is None:
            m = QMenu(self)
            for k, t in PICKS:
                a = m.addAction(t); a.setData(k); a.setCheckable(True); a.setChecked(k == self.pick_of(header, look if role in OX.TEXT_ROLES else None))
            a = m.exec(self.cursor().pos())
            if a is None:
                return None
            pick = a.data()
        self.set_pick(header, look if role in OX.TEXT_ROLES else None, pick)
        return pick

    def remember_new(self):
        """3.73.0: every new column kept in the layout as it is set now. Returns how many."""
        un = list(self.profile.get("unknown") or [])
        for h in un:
            OL.remember(self.host.config_dir, self.profile.get("name") or OL.STARTING, h, (self.profile.get("columns") or {}).get(h, "ignore"))
        self.profile["unknown"] = []
        self.say_new()
        return len(un)

    def learn(self):
        """Use this structure keeps every pick in the layout (decision 10). Returns how many things were kept."""
        return self.remember_new() + OL.learn(self.host.config_dir, self.profile.get("name") or OL.STARTING, self.book, self.profile)

    def say_new(self):
        un = self.profile.get("unknown") or []
        self.b_keep_new.setVisible(bool(un))
        self.new_cols.setText(("Layout: " + (self.profile.get("name") or "none yet") + ". ")
                              + (f"New column(s) the layout does not know: {', '.join(un)}. Say what each holds; it is remembered."
                                 if un else "Every column is in the layout. What you pick is kept when you use the structure."))

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
    dlg.learn()                                         # 3.73.0: using the structure keeps every pick in the layout
    return page.use_outline(dlg.parsed, os.path.basename(path), path=path, headers=dlg.book["headers"],
                            layout=dlg.profile.get("name") or "", accept=accept)
