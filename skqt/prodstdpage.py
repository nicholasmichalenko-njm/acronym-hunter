"""Production > Production Standards (3.6.0): every rule the checks and fixes use, editable value by value, in three
layers: the team standard, a document type, and this effort (the RFP's own rules). A value set at the layer being
edited shows in bold with a Reset button that takes it back to the layer below; everything else is inherited.

Sections: format variables, font rules, styles and heading numbering, table rows (each role's look with every border
edge), table types, row rules, captions and numbering, pages and sections (the page scheme, cover and back cover),
page setups, headers and footers, the table of contents and the lists of tables and figures, bulleted and numbered
lists, terms, Format Check options. Saved to the config folder (team, types) and the effort's settings (effort)."""
import copy, os, sys
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QFontComboBox,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget,
                               QTableWidget, QVBoxLayout, QWidget)
import diag
import prodrules as PRL
from prodengine.pe import rules as PR
from . import design as D

SECTIONS = [
    ("variables", "Format variables"), ("fonts", "Font rules"), ("styles", "Styles and heading numbering"),
    ("styledefs", "Style library"),
    ("rows", "Table rows"), ("ttypes", "Table types"), ("rules", "Row rules"), ("captions", "Captions and numbering"),
    ("pages", "Pages, cover and back cover"), ("setups", "Page setups"), ("hf", "Headers and footers"),
    ("toc", "Table of contents and lists"), ("lists", "Bulleted and numbered lists"), ("terms", "Terms"),
    ("checks", "Format Check options"),
]
ROLE_NAMES = {"caption": "Caption row", "header": "Header row", "header2": "Second header row", "subhead": "Subhead row",
              "body": "Body rows", "subtotal": "Subtotal row", "total": "Total row", "note": "Notes row"}
EDGE_NAMES = {"top": "Top", "bottom": "Bottom", "left": "Left", "right": "Right", "inside_v": "Between columns"}
ALIGN = [("left", "Left"), ("center", "Center"), ("right", "Right"), ("both", "Justified")]
VALIGN = [("top", "Top"), ("center", "Center"), ("bottom", "Bottom")]
PAGE_FMT = [("", "No page numbers"), ("decimal", "1, 2, 3"), ("lowerRoman", "i, ii, iii"), ("upperRoman", "I, II, III"),
            ("lowerLetter", "a, b, c"), ("upperLetter", "A, B, C")]
RESTART = [("part", "At the start of this part"), ("each", "At each chapter"), ("never", "Continue from before")]
SEPS = [(k, f"{v}  ({k})") for k, v in PR.SEPARATORS.items()]
AFTER = [("period_tab", "Period, then a tab"), ("period_space", "Period, then a space"), ("tab", "A tab"),
         ("colon_space", "Colon, then a space")]
RULE_KINDS = [("fill_in", "Cell fill is one of"), ("first_cell_starts", "First cell starts with"),
              ("first_cell_contains_word", "First cell contains the word"), ("last_row_merged", "Last row is one merged cell"),
              ("single_merged_cell", "One merged cell across"), ("bold_row", "Only bold text"), ("other", "Any other row")]
TOKENS = "{volume_name} {solicitation} {company} {page} {pages} {chapter}"
TRI = [("", "Not set"), ("on", "On"), ("off", "Off")]
STYLE_COLS = [("key", "Style", "text"), ("type", "Type", ("enum", [("paragraph", "Paragraph"), ("character", "Character")])),
              ("based_on", "Based on", "text"), ("next", "Next style", "text"), ("font", "Font", "text"), ("size", "Size (pt)", "num0"),
              ("bold", "Bold", ("enum", TRI)), ("italic", "Italic", ("enum", TRI)), ("underline", "Underline", ("enum", TRI)),
              ("caps", "All caps", ("enum", TRI)), ("color", "Color (hex)", "text"),
              ("jc", "Alignment", ("enum", [("", "Not set")] + ALIGN)), ("before", "Space before (pt)", "num0"),
              ("after", "Space after (pt)", "num0"), ("line", "Line spacing (lines, or pt if exact)", "num0"),
              ("line_rule", "Line rule", ("enum", [("", "Not set"), ("auto", "Multiple"), ("exact", "Exactly"), ("atLeast", "At least")])),
              ("left", "Left indent (pt)", "num0"), ("right", "Right indent (pt)", "num0"), ("first", "First line (pt)", "num0"),
              ("hanging", "Hanging (pt)", "num0"), ("keep_next", "Keep with next", ("enum", TRI)),
              ("keep_lines", "Keep lines together", ("enum", TRI)), ("page_break_before", "Page break before", ("enum", TRI)),
              ("widow", "Widow control", ("enum", TRI))]
TRI_KEYS = ("bold", "italic", "underline", "caps", "small_caps", "keep_next", "keep_lines", "page_break_before", "widow")


def _get(d, path, default=None):
    for k in path:
        if isinstance(d, dict) and k in d:
            d = d[k]
        elif isinstance(d, list) and isinstance(k, int) and 0 <= k < len(d):
            d = d[k]
        else:
            return default
    return d


def _set(d, path, v):
    for k in path[:-1]:
        if isinstance(d, list):
            d = d[k]
        else:
            if not isinstance(d.get(k), (dict, list)):
                d[k] = {}
            d = d[k]
    d[path[-1]] = v


class Binder:
    """Ties a widget to a path in the page's working standard; shows inherited or set-here."""

    def __init__(self, page):
        self.page = page
        self.items = []
        self.loading = False

    def bind(self, w, path, kind, label=None, reset=None):
        it = {"w": w, "path": tuple(path), "kind": kind, "label": label, "reset": reset}
        self.items.append(it)
        if kind == "text":
            w.textEdited.connect(lambda _t, i=it: self.write(i))
        elif kind == "lines":
            w.textChanged.connect(lambda i=it: self.write(i))
        elif kind in ("num", "int"):
            w.valueChanged.connect(lambda _v, i=it: self.write(i))
        elif kind == "bool":
            w.toggled.connect(lambda _v, i=it: self.write(i))
        elif kind in ("enum", "font"):
            w.currentIndexChanged.connect(lambda _i, i=it: self.write(i))
            if kind == "font" or w.isEditable():
                w.lineEdit().textEdited.connect(lambda _t, i=it: self.write(i))
        elif kind == "color":
            w.changed.connect(lambda i=it: self.write(i))
        elif kind == "list":
            w.textEdited.connect(lambda _t, i=it: self.write(i))
        if reset is not None:
            reset.clicked.connect(lambda _=False, i=it: self.reset(i))
        return w

    def value_of(self, it):
        w, k = it["w"], it["kind"]
        if k == "text":
            return w.text()
        if k == "lines":
            return [x.strip() for x in w.toPlainText().splitlines() if x.strip()]
        if k == "num":
            v = w.value()
            return None if (v == w.minimum() and w.specialValueText()) else round(v, 3)
        if k == "int":
            v = w.value()
            return None if (v == w.minimum() and w.specialValueText()) else int(v)
        if k == "bool":
            return w.isChecked()
        if k == "enum":
            if w.isEditable():
                t = w.currentText().strip()
                i = w.findText(t)
                if i >= 0:
                    d = w.itemData(i)
                    return d if d not in ("", None) else None
                if not t:
                    return None
                try:
                    return float(t) if t.replace(".", "", 1).isdigit() else t
                except ValueError:
                    return t
            d = w.currentData()
            return d if d != "" else None
        if k == "font":
            t = w.currentText().strip()
            return t or None
        if k == "color":
            return w.value
        if k == "list":
            return [x.strip() for x in w.text().split(",") if x.strip()] or None
        return None

    def show(self, it, v):
        w, k = it["w"], it["kind"]
        w.blockSignals(True)
        try:
            if k == "text":
                w.setText("" if v is None else str(v))
            elif k == "lines":
                w.setPlainText("\n".join(v or []))
            elif k in ("num", "int"):
                w.setValue(w.minimum() if v in (None, "") else float(v) if k == "num" else int(v))
            elif k == "bool":
                w.setChecked(bool(v))
            elif k == "enum":
                i = w.findData(v if v is not None else "")
                if i < 0 and w.isEditable():
                    w.setEditText("" if v is None else (f"{v:g}" if isinstance(v, float) else str(v)))
                else:
                    w.setCurrentIndex(max(0, i))
            elif k == "font":
                w.setEditText("" if v is None else str(v))
            elif k == "color":
                w.set(v)
            elif k == "list":
                w.setText(", ".join(v or []))
        finally:
            w.blockSignals(False)

    def load(self):
        self.loading = True
        for it in self.items:
            self.show(it, _get(self.page.work, it["path"]))
            self.mark(it)
        self.loading = False

    def write(self, it):
        if self.loading:
            return
        _set(self.page.work, it["path"], self.value_of(it))
        self.page.changed()
        self.mark(it)

    def reset(self, it):
        _set(self.page.work, it["path"], copy.deepcopy(_get(self.page.base, it["path"])))
        self.show(it, _get(self.page.work, it["path"]))
        self.page.changed()
        self.mark(it)

    def mark(self, it):
        own = _get(self.page.work, it["path"]) != _get(self.page.base, it["path"])
        if it["label"] is not None:
            f = it["label"].font(); f.setBold(own); it["label"].setFont(f)
            it["label"].setToolTip("Set at this layer" if own else "Inherited from the layer below")
        if it["reset"] is not None:
            it["reset"].setVisible(own and self.page.scope != "team")


class ColorButton(QPushButton):
    changed = Signal()

    def __init__(self, allow_none=True):
        super().__init__()
        self.value = None
        self.allow_none = allow_none
        self.setMinimumWidth(110)
        self.clicked.connect(self.pick)

    def set(self, v):
        self.value = v
        self.setText(f"#{v}" if v else "None")
        self.setStyleSheet(f"QPushButton {{ background: #{v}; color: {'#000' if v and _light(v) else '#fff'}; }}" if v else "")

    def pick(self):
        c = QColorDialog.getColor(QColor("#" + self.value) if self.value else QColor("#FFFFFF"), self, "Color",
                                  QColorDialog.DontUseNativeDialog)
        if c.isValid():
            self.set(c.name()[1:].upper())
            self.changed.emit()

    def contextMenuEvent(self, e):
        if self.allow_none:
            self.set(None)
            self.changed.emit()


def _light(hexv):
    c = QColor("#" + hexv)
    return (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) > 150


def num(lo=0.0, hi=72.0, step=0.5, blank="Not set", dec=2, suffix=""):
    w = QDoubleSpinBox(); w.setRange(lo - (step if blank else 0), hi); w.setSingleStep(step); w.setDecimals(dec)
    if blank:
        w.setSpecialValueText(blank)
    if suffix:
        w.setSuffix(suffix)
    w.setMinimumWidth(110)
    return w


def enum(items, editable=False):
    w = QComboBox(); w.setEditable(editable)
    for k, t in items:
        w.addItem(t, k)
    w.setMinimumWidth(170)
    return w


class TablePreview(QWidget):
    """A sample table drawn with the looks in force: fills, fonts, bold, italic, colors and every border edge."""

    ROWS = [("caption", ["Table 2-1.\tStaffing by labor category"]), ("header", ["Labor category", "Hours", "Rate"]),
            ("header2", ["", "Base year", "Option"]), ("subhead", ["Engineering"]), ("body", ["Systems engineer", "1,920", "$142"]),
            ("body", ["Software engineer", "3,840", "$136"]), ("subtotal", ["Subtotal", "5,760", ""]),
            ("total", ["Total", "7,680", ""]), ("note", ["Note: hours are for the base year."])]

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.table_type = "std"
        self.setMinimumHeight(300)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(self.rect(), QColor("#FFFFFF"))
        std = self.page.work
        tt = std["table_types"].get(self.table_type, {})
        roles = set(tt.get("roles") or PR.ROLES)
        W = self.width() - 24
        x0, y = 12, 12
        cols = [0.5, 0.25, 0.25]
        for role, cells in self.ROWS:
            if role not in roles or role not in std["row_types"]:
                continue
            look = PR.row_look(std, role, self.table_type)
            size = float(look.get("size") or 9)
            h = int(size * 2.1 + (look.get("before") or 0) + (look.get("after") or 0)) + 6
            merged = len(cells) == 1
            xs = [x0] + [x0 + int(W * sum(cols[:i + 1])) for i in range(3)]
            if merged:
                xs = [x0, x0 + W]
            if look.get("fill"):
                p.fillRect(x0, y, W, h, QColor("#" + look["fill"]))
            f = QFont(look.get("font") or "Arial")
            f.setPointSizeF(size * 0.95)
            f.setBold(bool(look.get("bold"))); f.setItalic(bool(look.get("italic")))
            p.setFont(f)
            p.setPen(QColor("#" + (look.get("color") or "000000")))
            al = {"left": Qt.AlignLeft, "center": Qt.AlignHCenter, "right": Qt.AlignRight}.get(look.get("align") or "left", Qt.AlignLeft)
            for i, text in enumerate(cells):
                r = QRectF(xs[i] + 5, y, xs[i + 1] - xs[i] - 10, h)
                a = al if i == 0 or merged else Qt.AlignRight
                p.drawText(r, int(a | Qt.AlignVCenter), text.replace("\t", "  "))
            edges = look.get("edges") or {}

            def line(spec, x1, y1, x2, y2):
                if spec:
                    pen = QPen(QColor("#" + spec[1])); pen.setWidthF(max(1.0, float(spec[0]) * 1.4)); p.setPen(pen)
                    p.drawLine(x1, y1, x2, y2)
            line(edges.get("top"), x0, y, x0 + W, y)
            line(edges.get("bottom"), x0, y + h, x0 + W, y + h)
            line(edges.get("left"), x0, y, x0, y + h)
            line(edges.get("right"), x0 + W, y, x0 + W, y + h)
            if not merged:
                for xi in xs[1:-1]:
                    line(edges.get("inside_v"), xi, y, xi, y + h)
            y += h
        p.end()


class StandardsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.data = None
        self.scope = "team"            # team | type | effort
        self.type_id = ""
        self.work, self.base = {}, {}
        self.dirty = False
        self.binder = Binder(self)
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); outer.setSpacing(D.SPACE["m"])
        top = D.Card("Production Standards", "Every rule Format Check and Fix a Copy use. Edit the team standard, a document type, "
                     "or this effort; a value set at the layer you edit shows in bold, and Reset takes it back to the layer below.",
                     actions=[D.button("+ Document type...", None, lambda: self.add_type()),
                              D.button("Learn from a file...", None, lambda: self.learn(), "Read a template or a finished volume and "
                                       "take its styles, table looks, pages, headers and numbering into what you are editing"),
                              D.button("Make a template...", None, lambda: self.make_template(), "A Word template (.dotx) with every "
                                       "value in force here, written to the output folder"),
                              D.button("Export for review...", None, lambda: self.export()),
                              D.button("Save", "primary", lambda: self.save())])
        bar = QHBoxLayout()
        bar.addWidget(D.label("Editing", "label", wrap=False))
        self.scope_box = QComboBox(); self.scope_box.setMinimumWidth(300)
        self.scope_box.currentIndexChanged.connect(lambda _i: self.switch())
        bar.addWidget(self.scope_box)
        self.default_cb = QCheckBox("New efforts use this document type"); bar.addWidget(self.default_cb)
        self.default_cb.toggled.connect(lambda _v: self.changed())
        bar.addStretch(1)
        self.state = D.label("", "muted", wrap=False); bar.addWidget(self.state)
        top.body.addLayout(bar)
        self.eff_row = QHBoxLayout()
        self.eff_row.addWidget(D.label("This effort's document type", "label", wrap=False))
        self.eff_type = QComboBox(); self.eff_type.setMinimumWidth(240); self.eff_row.addWidget(self.eff_type)
        self.eff_type.currentIndexChanged.connect(lambda _i: self.effort_type_changed())
        self.eff_row.addWidget(D.button("Fill from the RFP's formatting rules", None, lambda: self.fill_from_rfp()))
        self.eff_row.addWidget(D.button("Clear the effort's values", "ghost", lambda: self.clear_effort()))
        self.eff_row.addStretch(1)
        top.body.addLayout(self.eff_row)
        self.eff_said = top.add(D.label("", "muted"))
        outer.addWidget(top)
        body = QHBoxLayout(); body.setSpacing(D.SPACE["m"])
        self.nav = QListWidget(); self.nav.setFixedWidth(250)
        for _k, t in SECTIONS:
            self.nav.addItem(t)
        self.nav.currentRowChanged.connect(lambda i: self.stack.setCurrentIndex(i))
        body.addWidget(self.nav)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)
        self.problems = D.label("", "muted"); outer.addWidget(self.problems)
        self.tables = {}
        self.pages = {}
        for k, _t in SECTIONS:
            page = QWidget(); v = QVBoxLayout(page); v.setContentsMargins(0, 0, 0, 0)
            sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame)
            inner = QWidget(); inner.setObjectName("page"); iv = QVBoxLayout(inner); iv.setContentsMargins(D.SPACE["s"], 0, D.SPACE["s"], 0)
            sc.setWidget(inner); v.addWidget(sc)
            getattr(self, "build_" + k)(iv)
            iv.addStretch(1)
            self.stack.addWidget(page)
            self.pages[k] = inner
        self.nav.setCurrentRow(0)

    # ------------------------------------------------------------------ helpers to build forms
    def row(self, form, text, w, path, kind, help=""):
        lab = QLabel(text); lab.setToolTip(help)
        rb = QPushButton("Reset"); rb.setFlat(True); rb.setVisible(False); rb.setToolTip("Back to the layer below")
        box = QHBoxLayout(); box.setContentsMargins(0, 0, 0, 0); box.addWidget(w); box.addWidget(rb); box.addStretch(1)
        holder = QWidget(); holder.setLayout(box)
        form.addRow(lab, holder)
        self.binder.bind(w, path, kind, lab, rb)
        return w

    def form(self, v, title, subtitle=""):
        c = D.Card(title, subtitle)
        f = QFormLayout(); f.setLabelAlignment(Qt.AlignLeft); f.setHorizontalSpacing(D.SPACE["l"])
        c.body.addLayout(f)
        v.addWidget(c)
        return f, c

    # ------------------------------------------------------------------ sections
    def build_variables(self, v):
        f, _c = self.form(v, "Format variables", "The values the styles and checks are built from. A table font or size "
                          "names a variable (=table_font) so changing it here changes every row type that uses it.")
        names = {"body_font": "Body font", "body_size": "Body size (pt)", "table_font": "Table font", "table_size": "Table size (pt)",
                 "caption_font": "Caption font", "caption_size": "Caption size (pt)", "space_after_body": "Space after body text (pt)",
                 "line_spacing": "Line spacing", "heading1_size": "Heading 1 size (pt)", "margin_top": "Top margin (in)",
                 "margin_bottom": "Bottom margin (in)", "margin_left": "Left margin (in)", "margin_right": "Right margin (in)",
                 "paper": "Paper", "volume_name": "Volume name (blank: from the effort's deliverable)",
                 "solicitation": "Solicitation number (blank: from the effort's basics)",
                 "marking": "Restriction marking (footers)"}
        for k, t in names.items():
            if k.endswith("_font"):
                w = QFontComboBox(); w.setEditable(True); kind = "font"
            elif k.endswith("_size") or k == "space_after_body":
                w = num(0, 72, 0.5); kind = "num"
            elif k.startswith("margin"):
                w = num(0, 3, 0.05, suffix=" in"); kind = "num"
            elif k == "paper":
                w = enum([(p, p) for p in PRL.PAGE_SIZES]); kind = "enum"
            elif k == "line_spacing":
                w = enum([("single", "Single"), ("1.15", "1.15"), ("1.5", "1.5 lines"), ("double", "Double")]); kind = "enum"
            else:
                w = QLineEdit(); w.setMinimumWidth(420); kind = "text"
            drives = ", ".join(PR.VARIABLE_TARGETS.get(k, []))
            self.row(f, t, w, ("variables", k), kind, ("Drives: " + drives) if drives else "")

    def build_fonts(self, v):
        c = D.Card("Font rules", "What the RFP allows for each kind of text. Blank means not checked. Format Check and Fix a "
                   "Copy report text that breaks these, and say whether the style or typed formatting is the cause.")
        g = QGridLayout(); g.setHorizontalSpacing(D.SPACE["m"])
        for i, h in enumerate(("Text", "Allowed fonts (comma between)", "Smallest (pt)", "Largest (pt)", "RFP reference")):
            g.addWidget(D.label(h, "label"), 0, i)
        for r, sc in enumerate(PRL.SCOPES, 1):
            lab = QLabel(PRL.SCOPE_NAMES[sc]); g.addWidget(lab, r, 0)
            fl = QLineEdit(); fl.setPlaceholderText("any font"); g.addWidget(fl, r, 1)
            lo = num(0, 72, 0.5, "any"); g.addWidget(lo, r, 2)
            hi = num(0, 72, 0.5, "any"); g.addWidget(hi, r, 3)
            ref = QLineEdit(); ref.setPlaceholderText("L.4.2.1"); g.addWidget(ref, r, 4)
            self.binder.bind(fl, ("fonts", sc, "fonts"), "list", lab)
            self.binder.bind(lo, ("fonts", sc, "min_size"), "num", lab)
            self.binder.bind(hi, ("fonts", sc, "max_size"), "num", lab)
            self.binder.bind(ref, ("fonts", sc, "rfp_ref"), "text", lab)
        g.setColumnStretch(1, 1)
        c.body.addLayout(g)
        v.addWidget(c)

    def build_styles(self, v):
        f, c = self.form(v, "Styles", "Which styles a finished document may use, and what Fix a Copy does to the rest.")
        self.row(f, "Set style fonts and sizes from the format variables", QCheckBox(), ("styles", "apply_variables"), "bool")
        self.row(f, "Remove custom styles nobody uses", QCheckBox(), ("styles", "remove_unused_custom"), "bool")
        self.row(f, "Hide built-in styles nobody uses from the gallery", QCheckBox(), ("styles", "hide_unused_builtin"), "bool")
        t = QLineEdit(); t.setMinimumWidth(420); t.setPlaceholderText("A .dotx or .dotm whose styles every fixed copy takes")
        self.row(f, "Bring in the styles of this template", t, ("styles", "template"), "text")
        b = D.button("Choose a template...", None, lambda: self.pick_template(t)); f.addRow("", b)
        al = QPlainTextEdit(); al.setFixedHeight(130); al.setPlaceholderText("One style name per line. Blank: any style is allowed.")
        self.row(f, "Allowed styles", al, ("styles", "allowed"), "lines")
        f2, _c2 = self.form(v, "Heading numbering", "The nine heading levels: number format, what the number reads as (%1 is "
                            "the level 1 number), where the number and the text start, and which level restarts it.")
        self.row(f2, "Set heading numbering when fixing", QCheckBox(), ("heading_numbering", "on"), "bool")
        cols = [("style", "Style", "text"), ("fmt", "Format", ("enum", [(k, t) for k, t in PAGE_FMT if k])),
                ("text", "Number reads", "text"), ("number_at", "Number at (in)", "num"), ("text_at", "Text at (in)", "num"),
                ("restart", "Restart after level", "int")]
        self.table_editor(v, "heading_levels", ("heading_numbering", "levels"), cols, fixed=True)

    def build_styledefs(self, v):
        c = D.Card("Style library", "Every style this standard defines, whole: font, size, bold, italic, underline, caps, color, "
                   "alignment, spacing, line spacing, indents, keeps, page break before, widow control, based on and next style. "
                   "Fix a Copy checks each style in a draft against these values and sets the ones that differ; Make a template "
                   "writes them. Blank or Not set leaves that property as the draft has it. Format variables win where they "
                   "drive a style (body, table and caption fonts and sizes). Learn from a file... fills this from a template.")
        bar = QHBoxLayout()
        bar.addWidget(D.button("Learn from a file...", None, lambda: self.learn()))
        bar.addStretch(1)
        c.body.addLayout(bar)
        v.addWidget(c)
        self.table_editor(v, "styledefs", ("style_defs",), STYLE_COLS, dict_rows=True, adapter="styledefs")
        self.tables["styledefs"]["w"].setMinimumHeight(420)

    def pick_template(self, edit):
        p, _ = QFileDialog.getOpenFileName(self, "Template whose styles the copies take", os.path.expanduser("~"),
                                           "Word templates (*.dotx *.dotm *.docx)")
        if p:
            edit.setText(p); edit.textEdited.emit(p)

    def build_rows(self, v):
        c = D.Card("Table rows", "How each kind of row looks. Every table type shares these looks; choose a table type to "
                   "change a look for that type only.")
        top = QHBoxLayout()
        top.addWidget(D.label("Row", "label", wrap=False))
        self.role_box = QComboBox()
        for r, t in ROLE_NAMES.items():
            self.role_box.addItem(t, r)
        self.role_box.currentIndexChanged.connect(lambda _i: self.rebind_row())
        top.addWidget(self.role_box)
        top.addWidget(D.label("Applies to", "label", wrap=False))
        self.row_scope = QComboBox(); self.row_scope.setMinimumWidth(260)
        self.row_scope.currentIndexChanged.connect(lambda _i: self.rebind_row())
        top.addWidget(self.row_scope); top.addStretch(1)
        c.body.addLayout(top)
        split = QHBoxLayout()
        left = QVBoxLayout()
        self.row_form_host = QWidget(); self.row_form = QFormLayout(self.row_form_host)
        left.addWidget(self.row_form_host)
        eg = QGridLayout(); eg.setHorizontalSpacing(D.SPACE["m"])
        for i, h in enumerate(("Border", "On", "Width (pt)", "Color")):
            eg.addWidget(D.label(h, "label"), 0, i)
        self.edge_widgets = {}
        for r, e in enumerate(PR.EDGES, 1):
            eg.addWidget(QLabel(EDGE_NAMES[e]), r, 0)
            on = QCheckBox(); w = num(0.25, 6, 0.25, None, 2); col = ColorButton(False)
            eg.addWidget(on, r, 1); eg.addWidget(w, r, 2); eg.addWidget(col, r, 3)
            on.toggled.connect(lambda _v, e=e: self.edge_changed(e))
            w.valueChanged.connect(lambda _v, e=e: self.edge_changed(e))
            col.changed.connect(lambda e=e: self.edge_changed(e))
            self.edge_widgets[e] = (on, w, col)
        left.addLayout(eg)
        split.addLayout(left, 3)
        self.preview = TablePreview(self)
        pv = QVBoxLayout(); pv.addWidget(D.label("Preview", "label")); pv.addWidget(self.preview); pv.addStretch(1)
        split.addLayout(pv, 4)
        c.body.addLayout(split)
        v.addWidget(c)
        self.row_binder = Binder(self)

    def row_path(self, field):
        role = self.role_box.currentData()
        tt = self.row_scope.currentData()
        if tt:
            return ("table_types", tt, "override", role, field)
        return ("row_types", role, field)

    def rebind_row(self):
        if not self.work:
            return
        while self.row_form.rowCount():
            self.row_form.removeRow(0)
        self.row_binder = Binder(self)
        tt = self.row_scope.currentData()
        self.preview.table_type = tt or "std"
        role = self.role_box.currentData()
        look = PR.row_look(self.work, role, tt or "std")
        vars_ = [("=" + k, "= " + k) for k in self.work["variables"] if k.endswith(("_font", "_size"))]

        def add(text, w, field, kind):
            lab = QLabel(text)
            path = self.row_path(field)
            if tt and _get(self.work, path) is None:
                self.row_binder.loading = True
            self.row_form.addRow(lab, w)
            self.row_binder.bind(w, path, kind, lab)
            val = _get(self.work, path)
            self.row_binder.show(self.row_binder.items[-1], val if val is not None else look.get(field))
            self.row_binder.loading = False
        add("Tag style (marks the row's role)", QLineEdit(), "tag_style", "text")
        fw = enum(vars_ + [], editable=True); add("Font", fw, "font", "enum")
        sw = enum([x for x in vars_ if x[0].endswith("size")], editable=True); add("Size (pt)", sw, "size", "enum")
        add("Bold", QCheckBox(), "bold", "bool")
        add("Italic", QCheckBox(), "italic", "bool")
        add("Text color", ColorButton(), "color", "color")
        add("Fill", ColorButton(), "fill", "color")
        add("Align", enum(ALIGN), "align", "enum")
        add("Vertical align", enum(VALIGN), "valign", "enum")
        add("Space before (pt)", num(0, 24, 0.5, None, 1), "before", "num")
        add("Space after (pt)", num(0, 24, 0.5, None, 1), "after", "num")
        add("Repeat at the top of each page", QCheckBox(), "repeat", "bool")
        add("One merged cell across (only when the other cells are empty)", QCheckBox(), "merge", "bool")
        edges = look.get("edges") or {}
        for e, (on, w, col) in self.edge_widgets.items():
            spec = edges.get(e)
            for x in (on, w, col):
                x.blockSignals(True)
            on.setChecked(bool(spec)); w.setValue(float(spec[0]) if spec else 0.5); col.set(spec[1] if spec else "000000")
            w.setEnabled(bool(spec)); col.setEnabled(bool(spec))
            for x in (on, w, col):
                x.blockSignals(False)
        self.preview.update()

    def edge_changed(self, e):
        on, w, col = self.edge_widgets[e]
        w.setEnabled(on.isChecked()); col.setEnabled(on.isChecked())
        tt = self.row_scope.currentData()
        role = self.role_box.currentData()
        look = PR.row_look(self.work, role, tt or "std")
        edges = copy.deepcopy(look.get("edges") or {})
        edges[e] = [round(w.value(), 2), col.value or "000000"] if on.isChecked() else None
        _set(self.work, self.row_path("edges"), edges)
        self.changed()
        self.preview.update()

    def build_ttypes(self, v):
        cols = [("key", "Key", "text"), ("name", "Name", "text"), ("width_pct", "Width (%)", "num"),
                ("align", "Table align", ("enum", ALIGN[:3])), ("cm_top", "Cell margin top (pt)", "num"),
                ("cm_bottom", "Bottom", "num"), ("cm_left", "Left", "num"), ("cm_right", "Right", "num"),
                ("roles", "Rows it has (comma)", "list"), ("caption_position", "Caption row", ("enum", [("", "First row"), ("below", "Last row (figures)")]))]
        c = D.Card("Table types", "What differs between table types: width, alignment, cell margins, which rows it has, and "
                   "where its caption row sits. Each type's own row looks are set in Table rows (Applies to).")
        v.addWidget(c)
        self.table_editor(v, "ttypes", ("table_types",), cols, dict_rows=True)

    def build_rules(self, v):
        c = D.Card("Row rules", "How a row's role is found, in order; the first rule that matches decides. Sure rules apply; "
                   "the others ask, grouped so one answer covers every row like it. The caption row, header row and second "
                   "header row are found by position first. The last rule must be Any other row.")
        v.addWidget(c)
        cols = [("key", "Key", "text"), ("kind", "Looks at", ("enum", RULE_KINDS)), ("value", "Values (comma)", "list"),
                ("role", "Gives the role", ("enum", [(r, t) for r, t in ROLE_NAMES.items()] + [("keep", "Keep as is")])),
                ("sure", "Sure (apply without asking)", "bool"), ("why", "Why (shown with the row)", "text")]
        self.table_editor(v, "rules", ("row_rules",), cols)

    def build_captions(self, v):
        c = D.Card("Captions and numbering", "Each caption rule: its label, body or appendix, above or below, the chapter "
                   "level the number takes (1 for Heading 1 gives 2-1; 7 for the appendix heading gives A-1), the separator, "
                   "the caption list (SEQ identifier) and what follows the number. Lists of tables and figures collect by "
                   "these identifiers.")
        v.addWidget(c)
        cols = [("label", "Label", "text"), ("part", "Part", ("enum", [("body", "Body"), ("appendix", "Appendix")])),
                ("position", "Caption", ("enum", [("above", "Above"), ("below", "Below")])),
                ("chapter_level", "Chapter level", "int"), ("separator", "Separator", ("enum", [(v_, v_) for v_ in ("-", ".", ":", "–", "—")])),
                ("identifier", "Caption list (SEQ)", "text"), ("after_number", "After the number", ("enum", AFTER)), ("style", "Style", "text")]
        self.table_editor(v, "captions", ("captions",), cols)

    def build_pages(self, v):
        c = D.Card("Pages, cover and back cover", "The page scheme: an ordered list of parts. Each part starts at a style "
                   "(or the first or last section), numbers its pages its own way, and restarts where you say. The cover and "
                   "back cover carry no page number. A back cover is found only as the last section starting with one of its "
                   "styles, so a volume without one keeps its page numbers.")
        pr = QHBoxLayout(); pr.addWidget(D.label("Start from a preset", "label", wrap=False))
        self.preset_box = QComboBox()
        for k, p in PRL.presets().items():
            self.preset_box.addItem(p["name"], k)
        pr.addWidget(self.preset_box)
        pr.addWidget(D.button("Use this preset", None, lambda: self.use_preset())); pr.addStretch(1)
        c.body.addLayout(pr)
        v.addWidget(c)
        cols = [("key", "Key", "text"), ("name", "Name", "text"), ("start", "Starts at style", "text"),
                ("first", "First section", "bool"), ("last", "Last section only", "bool"),
                ("fmt", "Numbers", ("enum", PAGE_FMT)), ("restart", "Restart", ("enum", RESTART)), ("start_at", "Start at", "int"),
                ("chapter_level", "Chapter level", "int"), ("separator", "Separator", ("enum", SEPS)),
                ("chapter_style", "Chapter heading", "text"), ("linked", "Same header and footer as before", "bool")]
        self.table_editor(v, "pages", ("pagination", "parts"), cols, adapter="pages")

    def use_preset(self):
        self.work["pagination"] = copy.deepcopy(PRL.presets()[self.preset_box.currentData()])
        self.changed(); self.load_tables()

    def build_setups(self, v):
        c = D.Card("Page setups", "Paper, orientation and margins for each kind of page. Portrait takes the margin variables; "
                   "landscape and tabloid foldouts continue the page numbers and keep the headers and footers.")
        v.addWidget(c)
        cols = [("key", "Key", "text"), ("name", "Name", "text"), ("w", "Width (in)", "num"), ("h", "Height (in)", "num"),
                ("orient", "Orientation", ("enum", [("portrait", "Portrait"), ("landscape", "Landscape")])),
                ("top", "Top", "text"), ("bottom", "Bottom", "text"), ("left", "Left", "text"), ("right", "Right", "text"),
                ("header", "Header (in)", "num"), ("footer", "Footer (in)", "num")]
        self.table_editor(v, "setups", ("page_setups",), cols, dict_rows=True)

    def build_hf(self, v):
        c = D.Card("Headers and footers", "For each part of the page scheme: what the left, center and right of the header and "
                   "footer carry, a rule under the header, and the restriction marking. Tokens: " + TOKENS + ".")
        v.addWidget(c)
        cols = [("key", "Part", "text"), ("h_left", "Header left", "text"), ("h_center", "Header center", "text"),
                ("h_right", "Header right", "text"), ("rule_below", "Rule under header", "bool"), ("f_left", "Footer left", "text"),
                ("f_center", "Footer center", "text"), ("f_right", "Footer right", "text"), ("marking", "Marking", "bool")]
        self.table_editor(v, "hf", ("hf_layouts",), cols, adapter="hf")

    def build_toc(self, v):
        f, _c = self.form(v, "Table of contents", "The levels the TOC pulls by style name (Heading 7 and 8 as appendix "
                          "levels), its switches, and the title style.")
        self.row(f, "Switches", QLineEdit(), ("toc", "switches"), "list")
        self.row(f, "Title style", QLineEdit(), ("toc", "title_style"), "text")
        self.table_editor(v, "toc_levels", ("toc", "levels"), [("0", "Style", "text"), ("1", "TOC level", "int")], adapter="pairs")
        c = D.Card("TOC entry styles", "Where each level's number sits, where its text starts, the right indent, and the "
                   "page number tab with its leader.")
        v.addWidget(c)
        self.table_editor(v, "toc_styles", ("toc", "entry_styles"), [("key", "Style", "text"), ("number_at", "Number at (in)", "num"),
                          ("text_at", "Text at (in)", "num"), ("right_indent", "Right indent (in)", "num"), ("tab_pos", "Tab at (in)", "num"),
                          ("tab_leader", "Leader", ("enum", [("dot", "Dots"), ("none", "None"), ("hyphen", "Hyphens"), ("underscore", "Line")]))],
                          adapter="tocstyles")
        c2 = D.Card("Lists of tables and figures", "Each list's title and the caption lists (SEQ identifiers) it collects.")
        v.addWidget(c2)
        self.table_editor(v, "toc_lists", ("toc", "lists"), [("title", "Title", "text"), ("identifiers", "Collects (comma)", "list")])

    def build_lists(self, v):
        f, _c = self.form(v, "Bulleted and numbered lists", "The team's list styles, the typed bullets and numbers that become "
                          "them, and how numbering restarts.")
        self.row(f, "Bullet styles by level (comma)", QLineEdit(), ("lists", "bullet_styles"), "list")
        self.row(f, "Number styles by level (comma)", QLineEdit(), ("lists", "number_styles"), "list")
        self.row(f, "Typed bullets to convert (comma)", QLineEdit(), ("lists", "typed_bullets"), "list")
        self.row(f, "A list after a heading starts at 1", QCheckBox(), ("lists", "restart_after_heading"), "bool")
        self.row(f, "Styles never treated as lists (comma)", QLineEdit(), ("lists", "skip_styles"), "list")

    def build_terms(self, v):
        c = D.Card("Banned words and phrases", "Reported in every copy; a suggestion is offered for review, never applied without you.")
        v.addWidget(c)
        self.table_editor(v, "banned", ("terms", "banned"), [("find", "Word or phrase", "text"), ("suggest", "Suggest", "text"), ("why", "Why", "text")])
        c2 = D.Card("Fix automatically", "Misspellings and trademark or registered marks, applied with Fix all. Case: exact, or "
                    "match (keeps the writer's first capital). When: first use or every use.")
        v.addWidget(c2)
        self.table_editor(v, "replace", ("terms", "replace"), [("find", "Find", "text"), ("replace", "Replace with", "text"),
                          ("case", "Case", ("enum", [("match", "Match"), ("exact", "Exact")])),
                          ("when", "When", ("enum", [("", "Every use"), ("first", "First use"), ("every", "Every use")])),
                          ("superscript", "Mark in superscript", "bool"), ("why", "Why", "text")])
        f, _c = self.form(v, "Word lists", "Team terms, names and acronyms Word should accept (exported as custom dictionaries).")
        self.row(f, "Team terms (comma)", QLineEdit(), ("terms", "lists", "team_terms"), "list")
        self.row(f, "Employee names (comma)", QLineEdit(), ("terms", "lists", "employee_names"), "list")
        self.row(f, "Acronyms (comma)", QLineEdit(), ("terms", "lists", "acronyms"), "list")
        self.row(f, "Flag names one letter off", QCheckBox(), ("terms", "name_check"), "bool")

    def build_checks(self, v):
        f, _c = self.form(v, "Format Check options", "Read-only checks Format Check adds on top of the rules above.")
        self.row(f, "TOC switches never used (comma)", QLineEdit(), ("checks", "toc_forbid"), "list")
        self.row(f, "Every section's footer has a page number field", QCheckBox(), ("checks", "page_numbers"), "bool")
        self.row(f, "Caption numbers must be fields", QCheckBox(), ("checks", "caption_fields"), "bool")
        self.row(f, "Table captions", enum([("first row", "In the table's first row"), ("above", "Above the table"),
                                            ("below", "Below the table"), ("either", "Any of these")]), ("checks", "table_caption_position"), "enum")
        self.row(f, "Landscape sections allowed", QCheckBox(), ("checks", "landscape_ok"), "bool")

    # ------------------------------------------------------------------ list editors
    def table_editor(self, v, key, path, cols, dict_rows=False, fixed=False, adapter=None):
        t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels([c[1] for c in cols])
        t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        t.horizontalHeader().setStretchLastSection(True)
        t.setMinimumHeight(240)
        v.addWidget(t)
        if not fixed:
            bar = QHBoxLayout()
            bar.addWidget(D.button("+ Add", None, lambda _=False, k=key: self.add_row(k)))
            bar.addWidget(D.button("Remove", None, lambda _=False, k=key: self.remove_row(k)))
            bar.addWidget(D.button("Up", "ghost", lambda _=False, k=key: self.move_row(k, -1)))
            bar.addWidget(D.button("Down", "ghost", lambda _=False, k=key: self.move_row(k, 1)))
            bar.addStretch(1)
            v.addLayout(bar)
        self.tables[key] = {"w": t, "path": path, "cols": cols, "dict_rows": dict_rows, "adapter": adapter, "rows": []}

    def _rows_of(self, spec):
        """The section's data as a list of flat row dicts the table shows."""
        data = _get(self.work, spec["path"])
        ad = spec["adapter"]
        if ad == "pages":
            out = []
            for p in data or []:
                st, n = p.get("starts") or {}, p.get("numbers") or {}
                out.append({"key": p.get("key"), "name": p.get("name"), "start": st.get("style") or ", ".join(st.get("styles") or []),
                            "first": bool(st.get("first_section")), "last": bool(st.get("last_section")),
                            "fmt": n.get("fmt", "") if p.get("numbers") else "", "restart": n.get("restart", "part"),
                            "start_at": n.get("start_at", 1), "chapter_level": n.get("chapter_level"),
                            "separator": n.get("separator", "hyphen"), "chapter_style": p.get("chapter_style", ""), "linked": bool(p.get("linked"))})
            return out
        if ad == "hf":
            out = []
            for k, lay in (data or {}).items():
                h, f = lay.get("header") or {}, lay.get("footer") or {}
                out.append({"key": k, "h_left": h.get("left", ""), "h_center": h.get("center", ""), "h_right": h.get("right", ""),
                            "rule_below": bool(h.get("rule_below")), "f_left": f.get("left", ""), "f_center": f.get("center", ""),
                            "f_right": f.get("right", ""), "marking": bool(f.get("marking"))})
            return out
        if ad == "styledefs":
            out = []
            for k, d in sorted((data or {}).items(), key=lambda x: x[0].casefold()):
                row = {"key": k}
                for f, _h, _kind in STYLE_COLS[1:]:
                    val = (d or {}).get(f)
                    row[f] = ("on" if val else "off") if (f in TRI_KEYS and val is not None) else val
                out.append(row)
            return out
        if ad == "pairs":
            return [{"0": a, "1": b} for a, b in (data or [])]
        if ad == "tocstyles":
            return [{"key": k, "number_at": s.get("number_at"), "text_at": s.get("text_at"), "right_indent": s.get("right_indent"),
                     "tab_pos": (s.get("tab") or [None])[0], "tab_leader": (s.get("tab") or [None, None, "dot"])[2]} for k, s in (data or {}).items()]
        if spec["dict_rows"]:
            out = []
            for k, d in (data or {}).items():
                row = dict(d); row["key"] = k
                cm = d.get("cell_margins") or {}
                for side in ("top", "bottom", "left", "right"):
                    row["cm_" + side] = cm.get(side)
                out.append(row)
            return out
        return [dict(x) for x in (data or [])]

    def _store(self, spec, rows):
        ad = spec["adapter"]
        if ad == "pages":
            parts = []
            old = {p.get("key"): p for p in (_get(self.work, spec["path"]) or [])}
            for r in rows:
                p = copy.deepcopy(old.get(r["key"], {}))
                p.update({"key": r["key"] or "part", "name": r["name"] or r["key"]})
                st = {}
                if r["first"]:
                    st["first_section"] = True
                elif r["last"]:
                    st["last_section"] = True
                    st["styles"] = [x.strip() for x in (r["start"] or "").split(",") if x.strip()]
                elif r["start"]:
                    st["style"] = r["start"]
                p["starts"] = st
                if r["fmt"]:
                    n = {"fmt": r["fmt"], "restart": r["restart"] or "part", "start_at": r["start_at"] or 1,
                         "chapter_level": r["chapter_level"] or None}
                    if r["chapter_level"]:
                        n["separator"] = r["separator"] or "hyphen"
                    p["numbers"] = n
                else:
                    p["numbers"] = None
                if r["chapter_style"]:
                    p["chapter_style"] = r["chapter_style"]
                else:
                    p.pop("chapter_style", None)
                p["linked"] = bool(r["linked"])
                parts.append(p)
            _set(self.work, spec["path"], parts)
            return
        if ad == "hf":
            out = {}
            for r in rows:
                h = {k: r["h_" + k] for k in ("left", "center", "right") if r.get("h_" + k)}
                if r.get("rule_below"):
                    h["rule_below"] = True
                f = {k: r["f_" + k] for k in ("left", "center", "right") if r.get("f_" + k)}
                if r.get("marking"):
                    f["marking"] = True
                out[r["key"] or "part"] = {"header": h, "footer": f}
            _set(self.work, spec["path"], out)
            return
        if ad == "styledefs":
            out = {}
            for r in rows:
                name = (r.get("key") or "").strip()
                if not name:
                    continue
                d = {}
                for f, _h, _kind in STYLE_COLS[1:]:
                    val = r.get(f)
                    if val in (None, ""):
                        continue
                    d[f] = (val == "on") if f in TRI_KEYS else val
                d.setdefault("type", "paragraph")
                out[name] = d
            _set(self.work, spec["path"], out)
            return
        if ad == "pairs":
            _set(self.work, spec["path"], [[r["0"], r["1"]] for r in rows if r.get("0")])
            return
        if ad == "tocstyles":
            _set(self.work, spec["path"], {r["key"]: {"number_at": r["number_at"], "text_at": r["text_at"], "right_indent": r["right_indent"],
                                                      "tab": [r["tab_pos"], "right", r["tab_leader"] or "dot"]} for r in rows if r.get("key")})
            return
        if spec["dict_rows"]:
            old = _get(self.work, spec["path"]) or {}
            out = {}
            for r in rows:
                k = r.pop("key", None) or "type"
                d = copy.deepcopy(old.get(k, {}))
                cm = {}
                for side in ("top", "bottom", "left", "right"):
                    val = r.pop("cm_" + side, None)
                    if val is not None:
                        cm[side] = val
                d.update({kk: vv for kk, vv in r.items()})
                if cm:
                    d["cell_margins"] = cm
                if d.get("caption_position") in ("", None):
                    d.pop("caption_position", None)
                out[k] = d
            _set(self.work, spec["path"], out)
            return
        _set(self.work, spec["path"], rows)

    def load_tables(self):
        for key, spec in self.tables.items():
            t = spec["w"]
            rows = self._rows_of(spec)
            spec["rows"] = rows
            t.blockSignals(True)
            t.setRowCount(0)
            for r in rows:
                self._add_table_row(key, r)
            t.blockSignals(False)
            t.resizeColumnsToContents()

    def _add_table_row(self, key, r):
        spec = self.tables[key]
        t = spec["w"]
        i = t.rowCount(); t.insertRow(i)
        for c, (field, _h, kind) in enumerate(spec["cols"]):
            val = r.get(field)
            if isinstance(kind, tuple) and kind[0] == "enum":
                w = enum(kind[1]); idx = w.findData(val if val is not None else ""); w.setCurrentIndex(max(0, idx))
                w.currentIndexChanged.connect(lambda _x, k=key: self.table_changed(k))
            elif kind == "bool":
                w = QCheckBox(); w.setChecked(bool(val)); w.toggled.connect(lambda _x, k=key: self.table_changed(k))
            elif kind == "num":
                w = num(0, 400, 0.05, "", 2); w.setValue(float(val) if val not in (None, "") else w.minimum())
                w.valueChanged.connect(lambda _x, k=key: self.table_changed(k))
            elif kind == "num0":                       # 3.7.0: zero is a value; the lowest step is "not set"
                w = QDoubleSpinBox(); w.setRange(-1, 400); w.setSingleStep(0.5); w.setDecimals(2); w.setSpecialValueText("not set")
                w.setValue(float(val) if val not in (None, "") else -1); w.setMinimumWidth(90)
                w.valueChanged.connect(lambda _x, k=key: self.table_changed(k))
            elif kind == "int":
                w = QSpinBox(); w.setRange(-1, 99); w.setSpecialValueText("none"); w.setValue(int(val) if val not in (None, "") else -1)
                w.valueChanged.connect(lambda _x, k=key: self.table_changed(k))
            elif kind == "list":
                w = QLineEdit(", ".join(val if isinstance(val, list) else ([] if val in (None, "") else [str(val)])))
                w.textEdited.connect(lambda _x, k=key: self.table_changed(k))
            else:
                w = QLineEdit("" if val is None else str(val)); w.textEdited.connect(lambda _x, k=key: self.table_changed(k))
            t.setCellWidget(i, c, w)

    def _read_table(self, key):
        spec = self.tables[key]
        t = spec["w"]
        rows = []
        for i in range(t.rowCount()):
            r = {}
            for c, (field, _h, kind) in enumerate(spec["cols"]):
                w = t.cellWidget(i, c)
                if isinstance(kind, tuple):
                    r[field] = w.currentData() if w.currentData() != "" else (None if field not in ("fmt", "when", "caption_position") else "")
                elif kind == "bool":
                    r[field] = w.isChecked()
                elif kind == "num":
                    r[field] = None if w.value() == w.minimum() else round(w.value(), 3)
                elif kind == "num0":
                    r[field] = None if w.value() < 0 else round(w.value(), 3)
                elif kind == "int":
                    r[field] = None if w.value() < 0 else int(w.value())
                elif kind == "list":
                    r[field] = [x.strip() for x in w.text().split(",") if x.strip()]
                else:
                    r[field] = w.text().strip()
            rows.append(r)
        return rows

    def table_changed(self, key):
        self._store(self.tables[key], self._read_table(key))
        self.changed()
        if key in ("ttypes",):
            self.fill_row_scope()

    def add_row(self, key):
        spec = self.tables[key]
        blank = {f: (False if k == "bool" else None) for f, _h, k in spec["cols"]}
        blank[spec["cols"][0][0]] = "new"
        self._add_table_row(key, blank)
        self.table_changed(key)

    def remove_row(self, key):
        t = self.tables[key]["w"]
        r = t.currentRow()
        if r >= 0:
            t.removeRow(r)
            self.table_changed(key)

    def move_row(self, key, d):
        rows = self._read_table(key)
        t = self.tables[key]["w"]
        r = t.currentRow()
        if r < 0 or not (0 <= r + d < len(rows)):
            return
        rows[r], rows[r + d] = rows[r + d], rows[r]
        self._store(self.tables[key], rows)
        self.load_tables()
        t.selectRow(r + d)
        self.changed()

    # ------------------------------------------------------------------ layers
    def refresh(self):
        self.data = PRL.load(self.host.config_dir)
        cur = self.scope_box.currentData()
        self.scope_box.blockSignals(True)
        self.scope_box.clear()
        self.scope_box.addItem("Team standard (every document type starts here)", "team:")
        for t in self.data["types"]:
            self.scope_box.addItem(f"Document type: {t['name']}", "type:" + t["id"])
        if self.host.ws is not None:
            self.scope_box.addItem(f"This effort: {self.host.effort_name}", "effort:")
        i = self.scope_box.findData(cur) if cur else -1
        self.scope_box.setCurrentIndex(i if i >= 0 else (self.scope_box.count() - 1 if self.host.ws is not None else 0))
        self.scope_box.blockSignals(False)
        self.eff_type.blockSignals(True); self.eff_type.clear()
        for t in self.data["types"]:
            self.eff_type.addItem(t["name"], t["id"])
        if self.host.ws is not None:
            eff = self.host.ws.get("prod_std", {}) or {}
            self.eff_type.setCurrentIndex(max(0, self.eff_type.findData(eff.get("type") or self.data["default"])))
        self.eff_type.blockSignals(False)
        self.switch(force=True)

    def switch(self, force=False):
        if self.dirty and not force:
            self.save(quiet=True)
        scope, tid = (self.scope_box.currentData() or "team:").split(":", 1)
        self.scope, self.type_id = scope, tid
        d = self.data
        if scope == "team":
            self.base = copy.deepcopy(PRL.COMPANY)
            self.work = copy.deepcopy(d["company"])
        elif scope == "type":
            self.base = copy.deepcopy(d["company"])
            self.work = PRL.resolved_type(d, tid)
        else:
            eff = self.host.ws.get("prod_std", {}) or {}
            et = eff.get("type") or d["default"]
            self.base = PRL.resolved_type(d, et)
            self.work = PRL.merge(self.base, eff.get("over") or {})
        self.work.setdefault("variables", {})
        for w in (self.default_cb,):
            w.setVisible(scope == "type")
        self.default_cb.blockSignals(True); self.default_cb.setChecked(scope == "type" and d["default"] == tid); self.default_cb.blockSignals(False)
        for i in range(self.eff_row.count()):
            x = self.eff_row.itemAt(i).widget()
            if x is not None:
                x.setVisible(scope == "effort")
        self.eff_said.setVisible(scope == "effort")
        if scope == "effort":
            said = (self.host.ws.get("prod_std", {}) or {}).get("said") or []
            self.eff_said.setText(("From the RFP: " + "; ".join(said)) if said else
                                  "Nothing read from the RFP yet. Fill from the RFP's formatting rules reads Submission Rules.")
        self.binder.load()
        self.fill_row_scope()
        self.load_tables()
        self.dirty = False
        self.state.setText({"team": "Team standard", "type": "Document type", "effort": "This effort only"}[scope])
        self.show_problems()

    def fill_row_scope(self):
        cur = self.row_scope.currentData()
        self.row_scope.blockSignals(True); self.row_scope.clear()
        self.row_scope.addItem("All table types", None)
        for k, t in (self.work.get("table_types") or {}).items():
            self.row_scope.addItem(f"Only {t.get('name') or k}", k)
        i = self.row_scope.findData(cur); self.row_scope.setCurrentIndex(max(0, i))
        self.row_scope.blockSignals(False)
        self.rebind_row()

    def changed(self):
        self.dirty = True
        self.state.setText("Not saved")
        if hasattr(self, "preview"):
            self.preview.update()

    def show_problems(self):
        probs = PRL.validate(PRL.engine_ready(copy.deepcopy(self.work))) if self.work.get("row_types") else []
        self.problems.setText(("To fix before saving: " + "; ".join(probs[:6])) if probs else "")
        return probs

    def save(self, quiet=False):
        if not self.work:
            return False
        probs = self.show_problems()
        if probs:
            if not quiet:
                self.host.status("Not saved: " + probs[0])
            return False
        d = self.data
        if self.scope == "team":
            d["company"] = copy.deepcopy(self.work)
        elif self.scope == "type":
            t = PRL.type_of(d, self.type_id)
            layer = PRL.diff(self.work, d["company"])
            layer.pop("name", None); layer.pop("variable_source", None)
            keep = {"id": t["id"], "name": t["name"]}
            t.clear(); t.update(keep); t.update(layer)
            if self.default_cb.isChecked():
                d["default"] = t["id"]
        else:
            eff = dict(self.host.ws.get("prod_std", {}) or {})
            over = PRL.diff(self.work, self.base)
            over.pop("name", None); over.pop("variable_source", None)
            eff["over"] = over
            eff["type"] = self.eff_type.currentData() or d["default"]
            self.host.ws.set("prod_std", eff)
        PRL.save(self.host.config_dir, d)
        self.dirty = False
        self.state.setText("Saved")
        if self.scope == "team":
            diag.activity("prod_standards_saved_team")
        elif self.scope == "type":
            diag.activity("prod_standards_saved_type")
        else:
            diag.activity("prod_standards_saved_effort")
        if not quiet:
            self.host.toast("Production standards saved")
        return True

    def add_type(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New document type", "Its name (for example: Cost volume, Customer deliverable):")
            if not ok:
                return ""
        name = " ".join((name or "").split())
        if not name or name in [t["name"] for t in self.data["types"]]:
            self.host.status("Give it a name not already used.")
            return ""
        if self.dirty:
            self.save(quiet=True)
        base_layer = PRL.layer_of(PRL.type_of(self.data, self.type_id)) if self.scope == "type" else {}
        t = {"id": PRL.slug(name, {x["id"] for x in self.data["types"]}), "name": name}
        t.update(copy.deepcopy(base_layer))
        self.data["types"].append(t)
        PRL.save(self.host.config_dir, self.data)
        self.refresh()
        self.scope_box.setCurrentIndex(self.scope_box.findData("type:" + t["id"]))
        return t["id"]

    def effort_type_changed(self):
        if self.host.ws is None or self.scope != "effort":
            return
        eff = dict(self.host.ws.get("prod_std", {}) or {})
        eff["type"] = self.eff_type.currentData()
        self.host.ws.set("prod_std", eff)
        self.switch(force=True)

    def fill_from_rfp(self):
        if self.host.ws is None:
            return {}
        try:
            from .custdocs import Ctx
            rows = Ctx(self.host).reg.rows()
        except Exception:
            diag.swallowed()
            rows = []
        over, said = PRL.from_rfp(rows)
        eff = dict(self.host.ws.get("prod_std", {}) or {})
        eff["over"] = PRL.merge(eff.get("over") or {}, over)
        eff["said"] = said
        eff["type"] = self.eff_type.currentData() or self.data["default"]
        self.host.ws.set("prod_std", eff)
        diag.activity("prod_standards_from_rfp", n=len(said))
        self.host.status(f"{len(said)} formatting rule(s) read from the RFP." if said else
                         "The RFP's formatting rules are not in Submission Rules yet (capture them in Review).")
        self.switch(force=True)
        return over

    def clear_effort(self):
        if self.host.ws is not None:
            eff = dict(self.host.ws.get("prod_std", {}) or {})
            eff.pop("over", None); eff.pop("said", None)
            self.host.ws.set("prod_std", eff)
            self.switch(force=True)

    # ------------------------------------------------------------------ 3.7.0: learn from a file, make a template
    def learn(self, path=None, keys=None):
        """Read a template or document (once; it is never written) and take the areas chosen into what is being edited.
        keys (tests): the areas to take without asking. Returns the areas taken."""
        import prodlearn as PL
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A template or finished volume to learn from (it is only read)",
                                                  os.path.expanduser("~"), "Word (*.dotx *.docx *.dotm *.docm)")
            if not path:
                return []
        got = PL.learn(path, PRL.engine_ready(copy.deepcopy(self.work)))
        if got.error or not got.areas:
            self.host.status(got.error or "Nothing to learn in that file.")
            return []
        if keys is None:
            keys = self._pick_areas(got, os.path.basename(path))
            if not keys:
                return []
        keys = [k for k in keys if k in got.areas]
        layer = got.layer(keys)
        self.work = PRL.merge(self.work, layer)
        if "styles" in keys:                       # the file's style library replaces this layer's, style by style
            self.work.setdefault("style_defs", {}).update(layer.get("style_defs", {}))
        self.binder.load()
        self.fill_row_scope()
        self.load_tables()
        self.changed()
        self.show_problems()
        diag.activity("prod_learned", n=len(keys))
        self.host.status(f"Learned {len(keys)} area(s) from {os.path.basename(path)}. Review them, then Save.")
        return keys

    def _pick_areas(self, got, name):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem
        dlg = QDialog(self); dlg.setWindowTitle(f"Learn from {name}")
        v = QVBoxLayout(dlg)
        v.addWidget(D.label(f"What {name} carries. Untick anything you do not want; nothing is saved until you press Save.", None))
        lst = QListWidget(); lst.setMinimumSize(720, 360)
        for k, a in got.areas.items():
            it = QListWidgetItem(f"{a['label']}\n    " + "\n    ".join(a["summary"][:6]))
            it.setData(Qt.UserRole, k); it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked)
            lst.addItem(it)
        v.addWidget(lst)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return []
        return [lst.item(i).data(Qt.UserRole) for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked]

    def template_folder(self):
        import app_gui
        import prodcopy as PCY
        return os.path.join(PCY.output_folder(app_gui.load_settings() or {}, app_gui.DATA_DIR), "Templates")

    def make_template(self, start_from=None, word=None, wait=True):
        """A Word template with every value in force at this layer, in the output folder's Templates folder.
        start_from: "" for the Stationkeeper base, a path to start from a template (read once), None to ask."""
        import prodtemplate as PT
        probs = self.show_problems()
        if probs:
            self.host.status("Fix these first: " + probs[0])
            return None
        if start_from is None:
            from PySide6.QtWidgets import QMessageBox
            mb = QMessageBox(self); mb.setWindowTitle("Make a template")
            mb.setText("Start from the Stationkeeper base (cover, front matter, a chapter with a sample table, an appendix), or "
                       "from a template of yours (it is only read; its pages, logos and text are kept)?")
            base_b = mb.addButton("Stationkeeper base", QMessageBox.AcceptRole)
            mine_b = mb.addButton("A template of mine...", QMessageBox.ActionRole)
            mb.addButton(QMessageBox.Cancel)
            mb.exec()
            if mb.clickedButton() is base_b:
                start_from = ""
            elif mb.clickedButton() is mine_b:
                start_from, _ = QFileDialog.getOpenFileName(self, "Start from (only read)", os.path.expanduser("~"), "Word (*.dotx *.docx)")
                if not start_from:
                    return None
            else:
                return None
        std = PRL.engine_ready(copy.deepcopy(self.work))
        std["name"] = self.scope_box.currentText().split(": ", 1)[-1]
        if word is None and sys.platform.startswith("win"):
            import prodword
            word = prodword.update_fields
        self.host.status("Making the template...")
        folder = self.template_folder()
        self._tres = None

        def run():
            try:
                self._tres = ("job", PT.make(std, folder, start_from, word=word))
            except Exception as e:  # noqa: BLE001
                diag.swallowed()
                self._tres = ("error", f"The template was not made ({type(e).__name__}).")
        import bgwork
        self._twork = bgwork.start(run, "stationkeeper-template")
        if wait:
            bgwork.wait(self._twork)
            return self.template_done()
        from PySide6.QtCore import QTimer
        self._ttimer = QTimer(self, interval=500, timeout=lambda: self.template_done() if not self._twork.is_alive() else None)
        self._ttimer.start()
        return None

    def template_done(self):
        if getattr(self, "_ttimer", None) is not None:
            self._ttimer.stop()
        res, self._tres = getattr(self, "_tres", None), None
        if res is None:
            return None
        kind, job = res
        if kind != "job":
            self.host.status(job)
            return None
        refused = [x for x in job.steps if x.get("refused")]
        self.last_template = job
        self.host.status(f"Template made: {os.path.basename(job.copy)} in {os.path.dirname(job.copy)}. Checked against this "
                         f"standard: {job.check.count()} finding(s)" + (f"; {len(refused)} step(s) refused" if refused else "") + ".")
        diag.activity("prod_template_made", n=job.check.count())
        return job

    def export(self, path=None):
        """Every value in force at this layer, with where it comes from, as a workbook for review."""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the standards", self.host.out_path("prod_standards"), "Excel (*.xlsx)")
            if not path:
                return ""
        from openpyxl import Workbook
        from openpyxl.styles import Font
        wb = Workbook(); ws = wb.active; ws.title = "Standards"
        ws.append(["Setting", "Value", "Set at this layer"])
        for c in ws[1]:
            c.font = Font(bold=True)

        def walk(d, b, prefix):
            if isinstance(d, dict):
                for k, val in d.items():
                    if k in ("variable_source", "effort_over"):
                        continue
                    walk(val, b.get(k) if isinstance(b, dict) else None, prefix + [str(k)])
            else:
                ws.append([" > ".join(prefix), str(d) if d is not None else "", "Yes" if d != b else ""])
        walk(self.work, self.base, [])
        ws.column_dimensions["A"].width = 60; ws.column_dimensions["B"].width = 60
        wb.save(path)
        self.host.toast("Standards exported")
        return path
