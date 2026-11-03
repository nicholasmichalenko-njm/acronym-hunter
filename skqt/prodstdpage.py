"""Production > Production Standards (3.6.0): every rule the checks and fixes use, editable value by value, in three
layers: the team standard, a document type, and this effort (the RFP's own rules). A value set at the layer being
edited shows in bold with a Reset button that takes it back to the layer below; everything else is inherited.

Sections: format variables, font rules, styles and heading numbering, table rows (each role's look with every border
edge), table types, row rules, captions and numbering, pages and sections (the page scheme, cover and back cover),
page setups, headers and footers, the table of contents and the lists of tables and figures, bulleted and numbered
lists, terms, Excel and PowerPoint, check options. Saved to the config folder (team, types) and the effort's settings (effort)."""
import copy, os, sys
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QFontComboBox,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import prodrules as PRL
import numtext as NT
from prodengine.pe import rules as PR
from . import design as D

GROUPS = [                                               # 3.25.0: a menu across the top, in the order a document is built
    ("Template profile", [("profile_parts", "Parts and versions"), ("content_map", "Content map")]),     # 3.33.0
    ("Document parts", [("part_cover", "Cover"), ("part_front", "Front matter"), ("part_body", "Response"),    # 3.26.0
                        ("part_appendix", "Appendices"), ("part_backer", "Back cover")]),
    ("Pages", [("setups", "Page sizes and margins"), ("pages", "Pagination and covers"), ("hf", "Headers and footers"),
               ("toc", "Table of contents")]),
    ("Styles", [("variables", "Base fonts and sizes"), ("styledefs", "Styles"), ("fonts", "Font rules"), ("styles", "Allowed styles")]),
    ("Numbering", [("headnum", "Heading numbering"), ("lists", "Lists"), ("captions", "Captions")]),
    ("Tables", [("ttypes", "Table types"), ("rows", "Row looks"), ("rules", "How rows are recognized")]),
    ("Content", [("quickparts", "Quick Parts"), ("fillins", "Fields")]),
    ("Check", [("terms", "Words to avoid and fix"), ("graphics", "Graphics"), ("office", "Excel and PowerPoint")]),
]
SECTIONS = [x for _g, items in GROUPS for x in items]
# 3.25.0: what each section's own Import from a file brings in (template library item kinds)
IMPORT_KINDS = {"styledefs": ("style", "theme", "font"), "variables": ("variables",), "headnum": ("heading_numbering",),
                "lists": ("list_numbering",), "ttypes": ("table_style",), "rows": ("table_look",), "setups": ("page_setup",),
                "pages": ("cover", "backer"), "hf": ("hf", "hf_design"), "toc": ("toc",), "quickparts": ("quickpart",)}
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
TOKENS = "{volume_name} {solicitation} {company} {page} {pages} {chapter}, and your fields as {key}"
TRI = [("", "Not set"), ("on", "On"), ("off", "Off")]
STYLE_COLS = [("key", "Style", "text"), ("type", "Type", ("enum", [("paragraph", "Paragraph"), ("character", "Character")])),
              ("based_on", "Based on", "text"), ("next", "Next style", "text"), ("font", "Font", "text"), ("size", "Size (pt)", "num0"),
              ("bold", "Bold", ("enum", TRI)), ("italic", "Italic", ("enum", TRI)), ("underline", "Underline", ("enum", TRI)),
              ("caps", "All caps", ("enum", TRI)), ("hidden", "Hidden text", ("enum", TRI)), ("color", "Color (hex)", "text"),
              ("jc", "Alignment", ("enum", [("", "Not set")] + ALIGN)), ("before", "Space before (pt)", "num0"),
              ("after", "Space after (pt)", "num0"), ("line", "Line spacing (lines, or pt if exact)", "num0"),
              ("line_rule", "Line rule", ("enum", [("", "Not set"), ("auto", "Multiple"), ("exact", "Exactly"), ("atLeast", "At least")])),
              ("left", "Left indent (pt)", "num0"), ("right", "Right indent (pt)", "num0"), ("first", "First line (pt)", "num0"),
              ("hanging", "Hanging (pt)", "num0"), ("keep_next", "Keep with next", ("enum", TRI)),
              ("keep_lines", "Keep lines together", ("enum", TRI)), ("page_break_before", "Page break before", ("enum", TRI)),
              ("widow", "Widow control", ("enum", TRI)),
              ("tabs", "Tab stops (pt align leader; ...)", "text"), ("border_top", "Border above (pt color, or none)", "text"),
              ("border_bottom", "Border below", "text"), ("border_left", "Border left", "text"), ("border_right", "Border right", "text"),
              ("shading", "Shading (hex, or none)", "text")]


def tabs_text(tabs):
    return "; ".join(f"{float(p):g} {a}" + (f" {l}" if l and l != "none" else "") for p, a, l in (tabs or []))


def tabs_parse(text):
    out = []
    for part in (text or "").split(";"):
        w = part.split()
        if not w:
            continue
        try:
            out.append([float(w[0]), w[1] if len(w) > 1 else "left", w[2] if len(w) > 2 else "none"])
        except ValueError:
            continue
    return out
TRI_KEYS = ("bold", "italic", "underline", "caps", "small_caps", "keep_next", "keep_lines", "page_break_before", "widow", "hidden")


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



class _LazyTables(dict):
    """3.28.1: the page's tables by key; a table not filled since the values last changed is filled when it is used."""
    def __init__(self, page):
        super().__init__()
        self.page = page

    def __getitem__(self, key):
        spec = dict.__getitem__(self, key)
        if spec.get("stale"):
            self.page._fill_table(key, spec)
        return spec

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
            elif k == "list":                            # 3.32.1: a Symbol-font bullet shows as the bullet it is
                from prodengine.pe import bullets as BU
                w.setText(", ".join(dict.fromkeys(BU.shown(x) for x in (v or []))))
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
        if it.get("was") is not None:                  # 3.17.0: was, and where it came from
            b = _get(self.page.base, it["path"])
            it["was"].setText(f"was {_shown(b)}" if own else "")
            it["was"].setToolTip(f"What {self.page.base_name()} says" if own else "")
            it["was"].setVisible(own)


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


def _shown(v):
    if v in (None, "", [], {}):
        return "not set"
    if isinstance(v, bool):
        return "on" if v else "off"
    if isinstance(v, list):
        return ", ".join(map(str, v))
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


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


def WG_line(res):
    """The Word check in one line."""
    if not res.get("ok"):
        return "Word check not run: " + res.get("why", "")
    bad = sum(1 for e in res["entries"] if not e.get("ok"))
    return f"Word check: {len(res['entries'])} Quick Part(s), {bad} with a problem; {len(res['field_errors'])} field error(s)"


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
        top = D.Card("Production Standards", "Every rule Fix a Copy uses, in layers: the team standard, then a "
                     "volume (one kind of document you deliver), then an effort type (the rules of a kind of effort, "
                     "for every volume in it, and its changes for one volume), then this effort. A value set at the layer you "
                     "edit shows in bold, and Reset takes it back to the layer below.",
                     actions=[D.button("+ Effort type...", None, lambda: self.add_effort_type(), "A kind of effort (RFP, page-limited RFP, "
                                       "white paper, program): the volumes its deliverables use and the rules every one of them follows"),
                              D.button("Effort types...", "ghost", lambda: self.manage_effort_types(), "Rename, order or take "
                                       "out effort types (3.18.2)"),
                              D.button("+ Volume...", None, lambda: self.add_type(), "A volume: the full set of formatting values for one kind of document you deliver"),
                              D.button("Import from a file...", None, lambda: self.import_file(), "Read a template or Word "  # 3.25.0
                                       "document and take what it carries, item by item: into what you are editing, into the "
                                       "library, or both. Each section has its own Import for just its items"),
                              D.button("Template library...", None, lambda: self.library(), "Everything collected: styles, pages, "
                                       "headers and footers, numbering, tables, covers, Quick Parts and fonts"),
                              D.button("Make templates...", None, lambda: self.make_templates(), "Read each template in full, then make the "
                                       ".dotx: what you are editing, every volume of an effort type, or this effort's volumes and setup. "
                                       "A Word template (.dotx) with every "
                                       "value in force here, written to the output folder"),
                              D.button("Save", "primary", lambda: self.save())])
        bar = QHBoxLayout()
        bar.addWidget(D.label("Editing", "label", wrap=False))
        self.scope_box = QComboBox(); self.scope_box.setMinimumWidth(300)     # every layer in one list (kept for keys)
        self.scope_box.currentIndexChanged.connect(lambda _i: (self.switch(), self._sync_pickers()))
        self.scope_box.setVisible(False)
        bar.addWidget(self.scope_box)
        # 3.25.0: two short boxes in place of one long list: the effort type, then the volume
        bar.addWidget(D.label("Effort type", "label", wrap=False))
        self.etype_pick = QComboBox(); self.etype_pick.setMinimumWidth(200); bar.addWidget(self.etype_pick)
        bar.addWidget(D.label("Volume", "label", wrap=False))
        self.vol_pick = QComboBox(); self.vol_pick.setMinimumWidth(200); bar.addWidget(self.vol_pick)
        self.this_effort = QCheckBox("This effort only"); bar.addWidget(self.this_effort)
        self.etype_pick.activated.connect(lambda _i: self.picked(fill_volumes=True))
        self.vol_pick.activated.connect(lambda _i: self.picked())
        self.this_effort.toggled.connect(lambda _on: self.picked())
        bar.addStretch(1)
        self.state = D.label("", "muted", wrap=False); bar.addWidget(self.state)
        top.body.addLayout(bar)
        # 3.8.0: a profile's match words; an effort type's profiles and default
        self.match_row = QHBoxLayout()
        self.match_row.addWidget(D.label("Deliverables this volume fits (words in their names)", "label", wrap=False))
        self.match_edit = QLineEdit(); self.match_edit.setPlaceholderText("technical, management (comma between)")
        self.match_edit.textEdited.connect(lambda _t: self.changed()); self.match_row.addWidget(self.match_edit, 1)
        top.body.addLayout(self.match_row)
        self.et_row = QHBoxLayout()
        self.et_row.addWidget(D.label("Volumes in this effort type", "label", wrap=False))
        self.et_profiles = QListWidget(); self.et_profiles.setFixedHeight(96); self.et_profiles.setMinimumWidth(320)
        self.et_profiles.itemChanged.connect(lambda _it: self.changed()); self.et_row.addWidget(self.et_profiles)
        self.et_row.addWidget(D.label("Default volume", "label", wrap=False))
        self.et_default = QComboBox(); self.et_default.setMinimumWidth(200); self.et_row.addWidget(self.et_default)
        self.et_default.activated.connect(lambda _i: self.changed())
        self.et_row.addStretch(1)
        top.body.addLayout(self.et_row)
        self.eff_row = QHBoxLayout()
        self.eff_row.addWidget(D.label("This effort's type", "label", wrap=False))
        self.eff_etype = QComboBox(); self.eff_etype.setMinimumWidth(220); self.eff_row.addWidget(self.eff_etype)
        self.eff_etype.activated.connect(lambda _i: self.effort_etype_changed())
        self.eff_row.addWidget(D.label("default volume", "label", wrap=False))
        self.eff_type = QComboBox(); self.eff_type.setMinimumWidth(240); self.eff_row.addWidget(self.eff_type)
        self.eff_type.currentIndexChanged.connect(lambda _i: self.effort_type_changed())
        self.eff_row.addWidget(D.button("Fill from the RFP's formatting rules", None, lambda: self.fill_from_rfp()))
        self.eff_row.addWidget(D.button("Clear the effort's values", "ghost", lambda: self.clear_effort()))
        self.eff_row.addStretch(1)
        top.body.addLayout(self.eff_row)
        self.eff_said = top.add(D.label("", "muted"))
        outer.addWidget(top)
        from PySide6.QtWidgets import QTabBar          # 3.25.0: the sections as a menu across the top
        self.group_bar = QTabBar(); self.group_bar.setExpanding(False); self.group_bar.setDrawBase(False)
        for g, _items in GROUPS:
            self.group_bar.addTab(g)
        self.section_bar = QTabBar(); self.section_bar.setExpanding(False); self.section_bar.setDrawBase(False)
        self.section_bar.setObjectName("sectionbar")
        self.group_bar.currentChanged.connect(lambda i: self.pick_group(i))
        self.section_bar.currentChanged.connect(lambda i: self.pick_section(i))
        self.group_bar.setObjectName("groupbar")         # 3.29.1: the menu stands out: a tinted band, the group as a pill
        band = QFrame(); band.setObjectName("navband"); bl = QVBoxLayout(band)
        bl.setContentsMargins(D.SPACE["m"], 0, D.SPACE["m"], 0); bl.setSpacing(0)
        bl.addWidget(self.group_bar); bl.addWidget(self.section_bar)
        outer.addWidget(band)
        self.nav = QListWidget(); self.nav.setVisible(False)  # the sections in order (kept for keys and tests)
        for _k, t in SECTIONS:
            self.nav.addItem(t)
        self.nav.currentRowChanged.connect(lambda i: self.show_section(i))
        body = QHBoxLayout(); body.setSpacing(D.SPACE["m"])
        body.addWidget(self.nav)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        from .stdpreview import Preview                 # 3.17.0: what the values make, and what this layer changes
        self.std_preview = Preview(self)
        body.addWidget(self.std_preview)
        outer.addLayout(body, 1)
        self.problems = D.label("", "muted"); outer.addWidget(self.problems)
        self.tables = _LazyTables(self)               # 3.28.1: a table is filled when it is shown or used
        self.pages = {}
        for k, _t in SECTIONS:
            page = QWidget(); v = QVBoxLayout(page); v.setContentsMargins(0, 0, 0, 0)
            sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame)
            inner = QWidget(); inner.setObjectName("page"); iv = QVBoxLayout(inner); iv.setContentsMargins(D.SPACE["s"], 0, D.SPACE["s"], 0)
            sc.setWidget(inner); v.addWidget(sc)
            if k in IMPORT_KINDS:                       # 3.25.0: each section imports its own items
                ib = QHBoxLayout(); ib.addStretch(1)
                ib.addWidget(D.button("Import from a file...", None, lambda _=False, kk=k: self.import_file(section=kk),
                                      "Only this section's items from a template or Word document: take one, some or all"))
                iv.addLayout(ib)
            getattr(self, "build_" + k)(iv)
            iv.addStretch(1)
            self.stack.addWidget(page)
            self.pages[k] = inner
        first = [k for k, _t in SECTIONS].index("part_cover")       # 3.33.0: it still opens on the cover
        self.nav.setCurrentRow(first)
        self.show_section(first)

    SECTION_KEYS = {**{s_: ("pagination", ("hf_layouts", k_), ("hf_designs", k_), ("page_parts", k_))
                       for s_, k_ in (("part_cover", "cover"), ("part_front", "front"), ("part_body", "body"),
                                      ("part_appendix", "appendix"), ("part_backer", "backer"))},
                    "profile_parts": ("library_pins",), "content_map": ("content_map",),           # 3.33.0
                    "variables": ("variables",), "fonts": ("fonts",), "styles": ("styles",), "headnum": ("heading_numbering",),
                    "styledefs": ("style_defs",), "rows": ("row_types",), "ttypes": ("table_types", "table_styles"),
                    "rules": ("row_rules",), "captions": ("captions", ("checks", "caption_fields"), ("checks", "table_caption_position")),
                    "pages": ("pagination", "page_parts"), "quickparts": ("quick_parts",), "fillins": ("fill_ins",),
                    "setups": ("page_setups", ("checks", "landscape_ok")), "hf": ("hf_layouts", "hf_designs", ("checks", "page_numbers")),
                    "toc": ("toc", ("checks", "toc_forbid")), "lists": ("lists", "list_numbering"),
                    "terms": ("terms",), "office": ("excel", "powerpoint"), "graphics": ("graphics",)}
    LAYER_BELOW = {"team": "the built-in defaults", "type": "the team standard", "etype": "the team standard",
                   "etp": "the volume in this effort type", "effort": "the effort's volume"}

    def show_section(self, i):
        """3.17.0: the section's form, and its preview beside it. 3.25.0: the menu across the top follows."""
        if not (0 <= i < len(SECTIONS)):
            return
        self.stack.setCurrentIndex(i)
        self.fill_shown_tables()
        if hasattr(self, "std_preview"):
            self.std_preview.show_section(*SECTIONS[i])
        if hasattr(self, "group_bar"):
            key = SECTIONS[i][0]
            gi = next(n for n, (_g, items) in enumerate(GROUPS) if key in [k for k, _t in items])
            self._syncing = True
            if self.group_bar.currentIndex() != gi or self.section_bar.count() != len(GROUPS[gi][1]):
                self.group_bar.setCurrentIndex(gi)
                self._fill_section_bar(gi)
            self.section_bar.setCurrentIndex([k for k, _t in GROUPS[gi][1]].index(key))
            self._syncing = False

    def _fill_section_bar(self, gi):
        self.section_bar.blockSignals(True)
        while self.section_bar.count():
            self.section_bar.removeTab(0)
        for _k, t in GROUPS[gi][1]:
            self.section_bar.addTab(t)
        self.section_bar.blockSignals(False)

    def pick_group(self, gi):
        if getattr(self, "_syncing", False) or not (0 <= gi < len(GROUPS)):
            return
        self.nav.setCurrentRow([k for k, _t in SECTIONS].index(GROUPS[gi][1][0][0]))

    def pick_section(self, si):
        if getattr(self, "_syncing", False):
            return
        gi = self.group_bar.currentIndex()
        if 0 <= gi < len(GROUPS) and 0 <= si < len(GROUPS[gi][1]):
            self.nav.setCurrentRow([k for k, _t in SECTIONS].index(GROUPS[gi][1][si][0]))

    def section_key(self):
        i = self.nav.currentRow()
        return SECTIONS[i][0] if 0 <= i < len(SECTIONS) else ""

    def base_name(self):
        return self.LAYER_BELOW.get(self.scope, "the layer below")

    def changed_here(self, section):
        """[(what, was, now)] for every value this layer sets differently from the layer below, in one section."""
        out = []
        names = {tuple(it["path"]): (it["label"].text() if it.get("label") is not None else "") for it in self.binder.items}

        def walk(a, b, path):
            if isinstance(a, dict) and isinstance(b, dict):
                for k in list(dict.fromkeys(list(b.keys()) + list(a.keys()))):
                    walk(a.get(k), b.get(k), path + (k,))
                return
            if (a if a not in ("", [], {}) else None) == (b if b not in ("", [], {}) else None):
                return
            label = names.get(path) or " > ".join(str(x).replace("_", " ") for x in path[1:] or path)
            if isinstance(a, list) and a and isinstance(a[0], dict) or isinstance(b, list) and b and isinstance(b[0], dict):
                a_n, b_n = len(a or []), len(b or [])
                out.append((label, f"{b_n} row(s)", f"{a_n} row(s), changed"))
                return
            out.append((label, b, a))
        for key in self.SECTION_KEYS.get(section, ()):
            path = key if isinstance(key, tuple) else (key,)
            walk(_get(self.work or {}, path), _get(self.base or {}, path), path)
        return out

    # ------------------------------------------------------------------ helpers to build forms
    def row(self, form, text, w, path, kind, help=""):
        lab = QLabel(text); lab.setToolTip(help)
        rb = QPushButton("Reset"); rb.setFlat(True); rb.setVisible(False); rb.setToolTip("Back to the layer below")
        was = QLabel(""); was.setObjectName("stdwas"); was.setVisible(False)        # 3.17.0: what the layer below says
        was.setMaximumWidth(200)
        box = QHBoxLayout(); box.setContentsMargins(0, 0, 0, 0); box.addWidget(w); box.addWidget(rb); box.addWidget(was); box.addStretch(1)
        holder = QWidget(); holder.setLayout(box)
        form.addRow(lab, holder)
        self.binder.bind(w, path, kind, lab, rb)
        self.binder.items[-1]["was"] = was
        return w

    def form(self, v, title, subtitle=""):
        c = D.Card(title, subtitle)
        f = QFormLayout(); f.setLabelAlignment(Qt.AlignLeft); f.setHorizontalSpacing(D.SPACE["l"])
        c.body.addLayout(f)
        v.addWidget(c)
        return f, c

    # ------------------------------------------------------------------ sections
    # 3.26.0: Document parts: each part over the same settings (docparts.py)
    def build_profile_parts(self, v):
        """3.33.0: the profile as its parts, each from a pinned library version."""
        from .profileview import ProfileParts
        self.profile_parts = ProfileParts(self)
        v.addWidget(self.profile_parts)

    def build_content_map(self, v):
        """3.33.0: which style each kind of placed item takes, hidden or shown, in the file or not."""
        from .profileview import ContentMap
        self.content_map = ContentMap(self)
        v.addWidget(self.content_map)

    def fill_profile(self):
        for w in (getattr(self, "profile_parts", None), getattr(self, "content_map", None)):
            if w is not None:
                try:
                    w.refresh()
                except Exception:  # noqa: BLE001
                    diag.swallowed()

    def build_part_cover(self, v):
        from . import docparts as DP
        DP.build(self, v, "part_cover")

    def build_part_front(self, v):
        from . import docparts as DP
        DP.build(self, v, "part_front")

    def build_part_body(self, v):
        from . import docparts as DP
        DP.build(self, v, "part_body")

    def build_part_appendix(self, v):
        from . import docparts as DP
        DP.build(self, v, "part_appendix")

    def build_part_backer(self, v):
        from . import docparts as DP
        DP.build(self, v, "part_backer")

    def section_index(self, key):
        return [k for k, _t in SECTIONS].index(key)

    def build_variables(self, v):
        f, _c = self.form(v, "Base fonts and sizes", "The values the styles and checks are built from. A table font or size "
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
        c = D.Card("Font rules", "What the RFP allows for each kind of text. Blank means not checked. Fix a Copy reports "
                   "text that breaks these, and says whether the style or typed formatting is the cause.")
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
        f, c = self.form(v, "Allowed styles", "Which styles a finished document may use, and what Fix a Copy does to the rest.")
        self.row(f, "Set style fonts and sizes from the format variables", QCheckBox(), ("styles", "apply_variables"), "bool")
        self.row(f, "Remove custom styles nobody uses", QCheckBox(), ("styles", "remove_unused_custom"), "bool")
        self.row(f, "Hide built-in styles nobody uses from the gallery", QCheckBox(), ("styles", "hide_unused_builtin"), "bool")
        t = QLineEdit(); t.setMinimumWidth(420); t.setPlaceholderText("A .dotx or .dotm whose styles every fixed copy takes")
        self.row(f, "Bring in the styles of this template", t, ("styles", "template"), "text")
        b = D.button("Choose a template...", None, lambda: self.pick_template(t)); f.addRow("", b)
        # 3.25.0: tick the allowed styles from this standard's styles and the library's, sorted and filtered
        c2 = D.Card("The styles a document may use", "Tick each style a finished document may use; Fix a Copy reports any "
                    "other. Off: any style is allowed. The list holds this standard's styles and every style in the template "
                    "library; click a column heading to sort, or show one kind.")
        v.addWidget(c2)
        oh = QHBoxLayout()
        self.allow_only = QCheckBox("Only the ticked styles are allowed"); self.allow_only.toggled.connect(lambda on: self.allow_on(on))
        oh.addWidget(self.allow_only); oh.addStretch(1)
        oh.addWidget(D.label("Show", "label", wrap=False))
        self.allow_show = QComboBox(); self.allow_show.setMinimumWidth(200)
        self.allow_show.currentIndexChanged.connect(lambda _i: self.filter_allowed()); oh.addWidget(self.allow_show)
        self.allow_find = QLineEdit(); self.allow_find.setPlaceholderText("Find a style"); self.allow_find.setMaximumWidth(200)
        self.allow_find.textEdited.connect(lambda _t: self.filter_allowed()); oh.addWidget(self.allow_find)
        oh.addWidget(D.button("Tick all shown", "ghost", lambda: self.tick_allowed(True)))
        oh.addWidget(D.button("Clear all shown", "ghost", lambda: self.tick_allowed(False)))
        c2.body.addLayout(oh)
        self.allow_t = QTableWidget(0, 5); self.allow_t.setHorizontalHeaderLabels(["Style", "Type", "Group", "Use case", "From"])
        self.allow_t.verticalHeader().setVisible(False); self.allow_t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.allow_t.horizontalHeader().setStretchLastSection(True); self.allow_t.setMinimumHeight(320)
        self.allow_t.setSortingEnabled(True)
        self.allow_t.itemChanged.connect(lambda _it: self.allowed_changed())
        c2.body.addWidget(self.allow_t)

    def build_headnum(self, v):
        f2, _c2 = self.form(v, "Heading numbering", "The nine heading levels: number format, what the number reads as (type it "
                            "as it shows, such as 1.1.1 or Section A: the last number is this level's, the ones before it the "
                            "levels above), where the number and the text start, and which level restarts it.")
        self.row(f2, "Set heading numbering when fixing", QCheckBox(), ("heading_numbering", "on"), "bool")
        cols = [("style", "Style", "text"), ("fmt", "Format", ("enum", [(k, t) for k, t in PAGE_FMT if k])),
                ("text", "Number reads", "lvltext"), ("number_at", "Number at (in)", "num"), ("text_at", "Text at (in)", "num"),
                ("restart", "Restart after level", "int")]
        self.table_editor(v, "heading_levels", ("heading_numbering", "levels"), cols, fixed=True)

    def build_styledefs(self, v):
        c = D.Card("Styles", "Every style this volume defines, whole (hidden text styles included): font, size, bold, italic, underline, caps, color, "
                   "alignment, spacing, line spacing, indents, keeps, page break before, widow control, based on and next style. "
                   "Fix a Copy checks each style in a draft against these values and sets the ones that differ; Make a .dotx template "
                   "writes them. Blank or Not set leaves that property as the draft has it. Format variables win where they "
                   "drive a style (body, table and caption fonts and sizes). Import from a file... fills this from a template.")
        v.addWidget(c)
        self.table_editor(v, "styledefs", ("style_defs",), STYLE_COLS, dict_rows=True, adapter="styledefs")
        self.tables["styledefs"]["w"].setMinimumHeight(420)

    def pick_template(self, edit):
        p, _ = QFileDialog.getOpenFileName(self, "Template whose styles the copies take", os.path.expanduser("~"),
                                           "Word templates (*.dotx *.dotm *.docx)")
        if p:
            edit.setText(p); edit.textEdited.emit(p)

    def build_rows(self, v):
        c = D.Card("Row looks", "How each kind of row looks. Every table type shares these looks; choose a table type to "
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
        cols = [("key", "Key", "text"), ("name", "Name", "text"),
                ("width_unit", "Width set in", ("enum", [("", "Not set"), ("pct", "Percent of the page"), ("in", "Inches")])),
                ("width_pct", "Width (%)", "num"), ("width_in", "Width (in)", "num"), ("col_widths_in", "Column widths (in, comma)", "list"),
                ("align", "Table align", ("enum", ALIGN[:3])), ("cm_top", "Cell margin top (pt)", "num"),
                ("cm_bottom", "Bottom", "num"), ("cm_left", "Left", "num"), ("cm_right", "Right", "num"),
                ("roles", "Rows it has (comma)", "list"), ("caption_position", "Caption row", ("enum", [("", "First row"), ("below", "Last row (figures)")])),
                ("word_style", "Word table style (3.10.0)", "text")]
        c = D.Card("Table types", "What differs between table types: width, alignment, cell margins, which rows it has, and "
                   "where its caption row sits. Each type's own row looks are set in Table rows (Applies to).")
        v.addWidget(c)
        self.table_editor(v, "ttypes", ("table_types",), cols, dict_rows=True)

    def build_rules(self, v):
        c = D.Card("How rows are recognized", "How a row's role is found, in order; the first rule that matches decides. Sure rules apply; "
                   "the others ask, grouped so one answer covers every row like it. The caption row, header row and second "
                   "header row are found by position first. The last rule must be Any other row.")
        v.addWidget(c)
        cols = [("key", "Key", "text"), ("kind", "Looks at", ("enum", RULE_KINDS)), ("value", "Values (comma)", "list"),
                ("role", "Gives the role", ("enum", [(r, t) for r, t in ROLE_NAMES.items()] + [("keep", "Keep as is")])),
                ("sure", "Sure (apply without asking)", "bool"), ("why", "Why (shown with the row)", "text")]
        self.table_editor(v, "rules", ("row_rules",), cols)

    def build_captions(self, v):
        c = D.Card("Captions", "Each caption rule: its label, body or appendix, above or below, the chapter "
                   "level the number takes (1 for Heading 1 gives 2-1; 7 for the appendix heading gives A-1), the separator, "
                   "the caption list (SEQ identifier) and what follows the number. Lists of tables and figures collect by "
                   "these identifiers.")
        v.addWidget(c)
        cols = [("label", "Label", "text"), ("part", "Part", ("enum", [("body", "Body"), ("appendix", "Appendix")])),
                ("position", "Caption", ("enum", [("above", "Above"), ("below", "Below")])),
                ("chapter_level", "Chapter level", "int"), ("separator", "Separator", ("enum", [(v_, v_) for v_ in ("-", ".", ":", "–", "—")])),
                ("identifier", "Caption list (SEQ)", "text"),
                ("number_format", "Number shows as", ("enum", [("", "1, 2, 3"), ("ARABIC", "1, 2, 3"), ("ROMAN", "I, II, III"), ("roman", "i, ii, iii"),
                                                               ("ALPHABETIC", "A, B, C"), ("alphabetic", "a, b, c")])),
                ("after_number", "After the number", ("enum", AFTER)), ("style", "Style", "text")]
        self.table_editor(v, "captions", ("captions",), cols)
        f, _c = self.form(v, "What Check reports", "Read only: Check reports these in a draft; nothing is changed.")   # 3.25.0
        self.row(f, "Caption numbers must be fields", QCheckBox(), ("checks", "caption_fields"), "bool")
        self.row(f, "Table captions", enum([("first row", "In the table's first row"), ("above", "Above the table"),
                                            ("below", "Below the table"), ("either", "Any of these")]), ("checks", "table_caption_position"), "enum")

    def build_pages(self, v):
        c = D.Card("Pagination and covers", "The page scheme: an ordered list of parts. Each part starts at a style "
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
        # 3.10.0: the profile's own cover and back cover pages (from Import from a file)
        self.part_rows = {}
        for where, label in (("cover", "Cover page"), ("backer", "Back cover page")):
            row = QHBoxLayout(); row.addWidget(D.label(label, "label", wrap=False))
            lab = D.label("", "muted"); row.addWidget(lab, 1)
            row.addWidget(D.button("Clear", "ghost", lambda _=False, w_=where: self.clear_part(w_)))
            c.body.addLayout(row)
            self.part_rows[where] = lab
        v.addWidget(c)
        cols = [("key", "Key", "text"), ("name", "Name", "text"), ("start", "Starts at style", "text"),
                ("first", "First section", "bool"), ("last", "Last section only", "bool"),
                ("fmt", "Numbers", ("enum", PAGE_FMT)), ("restart", "Restart", ("enum", RESTART)), ("start_at", "Start at", "int"),
                ("chapter_level", "Chapter level", "int"), ("separator", "Separator", ("enum", SEPS)),
                ("chapter_style", "Chapter heading", "text"), ("linked", "Same header and footer as before", "bool")]
        self.table_editor(v, "pages", ("pagination", "parts"), cols, adapter="pages")

    def build_fillins(self, v):
        """3.23.0: tokens typed once and shown everywhere they are referenced."""
        c = D.Card("Fields", "Field codes for a value you type once that shows everywhere it is referenced. Style on the cover (STYLEREF, as the "
                   "team works today): the value sits once on the cover or title page in its own style, and every STYLEREF to "
                   "that style in headers, footers and Quick Parts shows it. Document property (DOCPROPERTY): a property of the "
                   "file (Title, Subject, Company, or one of your own). Use a field in a header or footer as {key}. Fields "
                   "are written without MERGEFORMAT, so each one takes the formatting where it sits. Volume name, solicitation "
                   "and company are built in.")
        v.addWidget(c)
        import fillins as FI
        cols = [("key", "Key (use as {key})", "text"), ("name", "Name", "text"), ("kind", "Works by", ("enum", list(FI.KINDS))),
                ("style", "Cover style (STYLEREF)", "text"), ("property", "Document property", "text"), ("value", "Value", "text")]
        self.table_editor(v, "fillins", ("fill_ins",), cols)

    def build_quickparts(self, v):
        """3.22.0: the Quick Parts the template carries: picked from a template or document, kept with this PC's standards
        (never in the program folder), put into the one Quick Parts gallery in your categories by Make a template."""
        f, _c = self.form(v, "Quick Parts", "The building blocks every template made from this standard carries: covers, title "
                          "pages, headers, footers, page numbers, tables, captions, callouts. Add them from any template or "
                          "Word document (.dotx, .dotm, .docx; macros never run). Word lists Quick Parts by category, then name, "
                          "so numbered categories set the order: 01 Covers, 02 Title pages, 03 Headers.")
        self.row(f, "Put every Quick Part in the Quick Parts gallery (not Word's Covers, Headers or Footers menus)", QCheckBox(),
                 ("quick_parts", "one_gallery"), "bool")
        row = QHBoxLayout()
        row.addWidget(D.button("Add from a template or document...", "primary", lambda: self.add_quick_parts(),
                               "Pick Quick Parts from a .dotx, .dotm or .docx: a copy of the file is kept with this PC's standards"))
        row.addStretch(1)
        v.addLayout(row)
        self.table_editor(v, "quickparts", ("quick_parts", "entries"),
                          [("name", "Name", "text"), ("category", "Category", "text"), ("gallery", "Gallery in the file", "text"),
                           ("description", "Description", "text"), ("source", "From (kept copy)", "text")])
        self.qp_note = D.label("", "muted"); v.addWidget(self.qp_note)

    def add_quick_parts(self, path=None, picks=None):
        """Read a file's Quick Parts (read-only), tick the ones to carry, keep a copy of the file with this PC's standards,
        and list them here. picks (tests): the names to take. Returns how many were added."""
        import prodquickparts as QP
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Quick Parts from", "", "Word templates and documents (*.dotx *.dotm *.docx)")
            if not path:
                return 0
        try:
            found = QP.read(path)
        except Exception as e:                       # noqa: BLE001  a file Word could not open either
            diag.swallowed()
            self.qp_note.setText(f"That file could not be read ({type(e).__name__}).")
            return 0
        if not found:
            self.qp_note.setText("That file has no Quick Parts. Import from a file... takes its styles, tables and pages.")
            return 0
        if picks is None:
            from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem
            d = QDialog(self); d.setWindowTitle("Quick Parts to carry"); d.resize(720, 520); dv = QVBoxLayout(d)
            dv.addWidget(D.label(f"{len(found)} Quick Part(s) in {os.path.basename(path)}. Tick the ones every template from this "
                                 "standard should carry.", "muted"))
            lst = QListWidget(); dv.addWidget(lst, 1)
            for e in found:
                it = QListWidgetItem(f"{e['category'] or '(no category)'}  /  {e['name']}   [{QP.gallery_name(e['gallery'])}]"
                                     + (f"   {e['pictures']} picture(s)" if e["pictures"] else ""))
                it.setToolTip((e.get("text") or "")[:600]); it.setData(Qt.UserRole, e["name"])
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked); lst.addItem(it)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            dv.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return 0
            picks = [lst.item(i).data(Qt.UserRole) for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked]
        kept = QP.keep_source(self.host.config_dir, path)
        qp = dict(self.work.get("quick_parts") or {"one_gallery": True, "entries": []})
        entries = list(qp.get("entries") or [])
        have = {(x.get("name"), x.get("category")) for x in entries}
        n = 0
        for e in found:
            if e["name"] in picks and (e["name"], e["category"]) not in have:
                entries.append({"name": e["name"], "category": e["category"] or "", "gallery": e["gallery"] or "",
                                "description": e.get("description") or "", "source": kept})
                n += 1
        qp["entries"] = entries
        self.work["quick_parts"] = qp
        self.changed(); self.load_tables()
        self.qp_note.setText(f"{n} Quick Part(s) added from {os.path.basename(path)}. Make a .dotx template puts them in.")
        diag.activity("std_quick_parts_added", n=n)
        return n

    def show_hf_designs(self):
        d = self.work.get("hf_designs") or {}
        if hasattr(self, "hf_designs_lab"):
            self.hf_designs_lab.setText(("Kept whole from the Template library (they replace the layout above): " + ", ".join(sorted(d)))
                                        if d else "Template library > Header and footer designs puts a design kept whole on a part.")

    def clear_hf_designs(self):
        self.work["hf_designs"] = {}
        self.show_hf_designs(); self.changed()

    def parts_dir(self):
        import prodparts as PP
        return PP.parts_dir(self.host.config_dir)

    def show_parts(self):
        for where, lab in getattr(self, "part_rows", {}).items():
            f = (self.work.get("page_parts") or {}).get(where)
            lab.setText(f"{f} (Make a .dotx template puts it in; Fix a Copy reports a draft whose page is built differently)" if f else
                        "none: Import from a file... takes it from a template or finished volume")

    def clear_part(self, where):
        pp = dict(self.work.get("page_parts") or {})
        pp.pop(where, None)
        self.work["page_parts"] = pp
        self.show_parts()
        self.changed()

    def use_preset(self):
        self.work["pagination"] = copy.deepcopy(PRL.presets()[self.preset_box.currentData()])
        self.changed(); self.load_tables()

    def build_setups(self, v):
        c = D.Card("Page sizes and margins", "Paper, orientation and margins for each kind of page. Portrait takes the margin variables; "
                   "landscape and tabloid foldouts continue the page numbers and keep the headers and footers.")
        v.addWidget(c)
        cols = [("key", "Key", "text"), ("name", "Name", "text"), ("w", "Width (in)", "num"), ("h", "Height (in)", "num"),
                ("orient", "Orientation", ("enum", [("portrait", "Portrait"), ("landscape", "Landscape")])),
                ("top", "Top", "text"), ("bottom", "Bottom", "text"), ("left", "Left", "text"), ("right", "Right", "text"),
                ("header", "Header (in)", "num"), ("footer", "Footer (in)", "num")]
        self.table_editor(v, "setups", ("page_setups",), cols, dict_rows=True)
        f, _c = self.form(v, "What Check reports", "Read only: Check reports these in a draft; nothing is changed.")   # 3.25.0
        self.row(f, "Landscape sections allowed", QCheckBox(), ("checks", "landscape_ok"), "bool")

    def build_hf(self, v):
        c = D.Card("Headers and footers", "For each part of the page scheme: what the left, center and right of the header and "
                   "footer carry, a rule under the header, and the restriction marking. Word's way puts them on tab stops; "
                   "type column widths in inches (2, 2.5, 2) to build it as a table instead, the way the team's Quick Parts "
                   "do (one width: the center text; two: left and right; three: all three). Or use one of your Quick Parts "
                   "as a part's header or footer, kept exactly as built. Tokens: " + TOKENS + ".")
        v.addWidget(c)
        cols = [("key", "Part", "text"), ("h_left", "Header left", "text"), ("h_center", "Header center", "text"),
                ("h_right", "Header right", "text"), ("rule_below", "Rule under header", "bool"),
                ("h_table", "Header as a table: column widths (in)", "list"), ("f_left", "Footer left", "text"),
                ("f_center", "Footer center", "text"), ("f_right", "Footer right", "text"), ("marking", "Marking", "bool"),
                ("f_table", "Footer as a table: column widths (in)", "list"),
                ("borders", "Table borders", ("enum", [("none", "None"), ("bottom", "A line under"), ("grid", "Grid")]))]
        self.table_editor(v, "hf", ("hf_layouts",), cols, adapter="hf")
        qr = QHBoxLayout()
        qr.addWidget(D.button("Use a Quick Part as a header or footer...", None, lambda: self.hf_from_quick_part(),
                              "One of this standard's Quick Parts, kept exactly as built (its table, widths, pictures and "
                              "fields), as a part's header or footer"))
        qr.addStretch(1); v.addLayout(qr)
        row = QHBoxLayout()                                       # 3.24.0: designs kept whole replace a part's layout
        self.hf_designs_lab = D.label("", "muted"); row.addWidget(self.hf_designs_lab, 1)
        row.addWidget(D.button("Clear the kept designs", "ghost", lambda: self.clear_hf_designs(),
                               "Back to the layouts above for every part"))
        v.addLayout(row)
        f, _c = self.form(v, "What Check reports", "Read only: Check reports these in a draft; nothing is changed.")   # 3.25.0
        self.row(f, "Every section's footer has a page number field", QCheckBox(), ("checks", "page_numbers"), "bool")

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
        f, _c = self.form(v, "What Check reports", "Read only: Check reports these in a draft; nothing is changed.")   # 3.25.0
        self.row(f, "TOC switches never used (comma)", QLineEdit(), ("checks", "toc_forbid"), "list")

    def build_lists(self, v):
        f, _c = self.form(v, "Lists", "The team's bulleted and numbered list styles, the typed bullets and numbers that become "
                          "them, and how numbering restarts.")
        self.row(f, "Bullet styles by level (comma)", QLineEdit(), ("lists", "bullet_styles"), "list")
        self.row(f, "Number styles by level (comma)", QLineEdit(), ("lists", "number_styles"), "list")
        self.row(f, "Typed bullets to convert (comma)", QLineEdit(), ("lists", "typed_bullets"), "list")
        self.row(f, "A list after a heading starts at 1", QCheckBox(), ("lists", "restart_after_heading"), "bool")
        self.row(f, "Styles never treated as lists (comma)", QLineEdit(), ("lists", "skip_styles"), "list")
        f2, _c2 = self.form(v, "List numbering", "What each list style shows, level by level: a bullet (its character and "
                            "font) or a number (its format and what it shows, typed as it looks, such as 1. or a)), and where the number and the "
                            "text start. Fix a Copy checks each list style against these and sets the ones that differ; "
                            "Make a .dotx template writes them.")
        self.row(f2, "Set list numbering when fixing", QCheckBox(), ("list_numbering", "on"), "bool")
        cols = [("list", "List", "text"), ("style", "Style", "text"),
                ("fmt", "Format", ("enum", [("bullet", "Bullet"), ("decimal", "1, 2, 3"), ("lowerLetter", "a, b, c"),
                                            ("upperLetter", "A, B, C"), ("lowerRoman", "i, ii, iii"), ("upperRoman", "I, II, III"),
                                            ("decimalZero", "01, 02, 03")])),
                ("text", "Shows (bullet, or 1.)", "lvltext"), ("font", "Bullet font (blank: the text's)", "text"),
                ("left", "Text at (in)", "num0"), ("hanging", "Number before the text (in)", "num0")]
        self.table_editor(v, "listnum", ("list_numbering", "lists"), cols, adapter="listnum")

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

    def build_office(self, v):
        """3.11.0: what Check reads in workbooks and decks (prodoffice). Check only: these files are never changed."""
        f, _c = self.form(v, "Excel workbooks", "Fix a Copy checks a workbook against these and lists what differs; you fix it "
                          "in Excel. Blank font or size: the volume's table font and size.")
        w = QFontComboBox(); w.setEditable(True)
        self.row(f, "Font", w, ("excel", "font"), "font")
        self.row(f, "Size (pt)", num(0, 72, 0.5), ("excel", "size"), "num")
        self.row(f, "Header row bold", QCheckBox(), ("excel", "header", "bold"), "bool")
        self.row(f, "Header row fill (hex, blank: any)", QLineEdit(), ("excel", "header", "fill"), "text")
        self.row(f, "Header row text color (hex, blank: any)", QLineEdit(), ("excel", "header", "color"), "text")
        self.row(f, "Header row frozen", QCheckBox(), ("excel", "freeze_header"), "bool")
        self.row(f, "Print orientation", enum([("", "Either"), ("portrait", "Portrait"), ("landscape", "Landscape")]),
                 ("excel", "print", "orientation"), "enum")
        self.row(f, "Print fits one page wide", QCheckBox(), ("excel", "print", "fit_width"), "bool")
        self.row(f, "Header row repeats on each printed page", QCheckBox(), ("excel", "print", "repeat_header"), "bool")
        self.row(f, "Page number in the printed footer", QCheckBox(), ("excel", "print", "footer_page"), "bool")
        self.row(f, "Restriction marking in the printed header or footer", QCheckBox(), ("excel", "print", "marking"), "bool")
        f2, _c2 = self.form(v, "PowerPoint decks", "Fix a Copy checks a deck against these and lists what differs; you fix it "
                            "in PowerPoint. Blank fonts: the volume's body and table fonts.")
        self.row(f2, "Fonts allowed (comma)", QLineEdit(), ("powerpoint", "fonts"), "text")
        self.row(f2, "Smallest text (pt)", num(0, 72, 0.5), ("powerpoint", "min_size"), "num")
        self.row(f2, "Smallest title (pt)", num(0, 96, 0.5), ("powerpoint", "title_min_size"), "num")
        self.row(f2, "Slide size", enum([("", "Either"), ("16:9", "16:9"), ("4:3", "4:3")]), ("powerpoint", "slide_size"), "enum")
        self.row(f2, "Restriction marking on every slide", QCheckBox(), ("powerpoint", "marking"), "bool")
        self.row(f2, "Every slide has a title", QCheckBox(), ("powerpoint", "titles"), "bool")

    def build_graphics(self, v):
        """3.17.0: graphics standards; Fix a Copy and Audit check every picture, chart and text box against them."""
        import prodgraphics as PG
        f, _c = self.form(v, "Graphics", "What every figure must meet: picture types, resolution where placed, width, the "
                          "fonts and smallest text in drawings, charts and text boxes, captions and alt text. Check only: a "
                          "picture is never re-encoded, resized or moved. Blank fonts: the Graphic row of the font rules, else "
                          "the volume's body, table and caption fonts.")
        wide = lambda: (lambda e: (e.setMinimumWidth(320), e)[1])(QLineEdit())
        self.row(f, "Picture types allowed (comma)", wide(), ("graphics", "types"), "list",
                 "png, jpeg, emf, wmf, svg, gif, tiff, bmp")
        self.row(f, "Smallest resolution where placed (ppi)", num(0, 1200, 25, "any", 0), ("graphics", "min_ppi"), "num",
                 "Pixels divided by the size the picture is placed at. 150 for screen, 300 for print")
        self.row(f, "Widest a figure may be", enum([("", "Any width"), ("margins", "The text width (inside the margins)"),
                                                    ("set", "A set width (below)")]), ("graphics", "max_width"), "enum")
        self.row(f, "Set width (in)", num(0, 20, 0.25, "not set"), ("graphics", "max_width_in"), "num")
        self.row(f, "Fonts allowed in drawings and charts (comma)", wide(), ("graphics", "fonts"), "list")
        self.row(f, "Smallest text in drawings and charts (pt)", num(0, 72, 0.5, "any"), ("graphics", "min_text_pt"), "num")
        self.row(f, "Estimate the text size inside pictures (OCR, AI and ML)", QCheckBox(), ("graphics", "ocr_text"), "bool",
                 "Reads the words in each picture on this PC and estimates their size where placed. Shown as an estimate")
        self.row(f, "Every figure has a caption", QCheckBox(), ("graphics", "caption"), "bool")
        self.row(f, "Every picture has alt text", QCheckBox(), ("graphics", "alt_text"), "bool")
        self.row(f, "RGB only (no CMYK pictures)", QCheckBox(), ("graphics", "rgb_only"), "bool")
        self.row(f, "Largest picture file (MB)", num(0, 200, 1, "any", 0), ("graphics", "max_file_mb"), "num")
        del PG

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
                            "f_right": f.get("right", ""), "marking": bool(f.get("marking")),
                            "h_table": [f"{x:g}" for x in (h.get("table") or {}).get("widths_in") or []],
                            "f_table": [f"{x:g}" for x in (f.get("table") or {}).get("widths_in") or []],
                            "borders": (h.get("table") or f.get("table") or {}).get("borders", "none")})
            return out
        if ad == "listnum":                              # 3.32.1: bullets as the character they show, not Word's symbol form
            from prodengine.pe import bullets as BU
            out = []
            for l in (data or []):
                for lv in (l.get("levels") or []):
                    r = dict(lv, list=l.get("name", ""))
                    if lv.get("fmt") == "bullet":
                        r["text"], r["font"] = BU.for_display(lv.get("text", ""), lv.get("font", ""))
                    out.append(r)
            return out
        if ad == "styledefs":
            out = []
            for k, d in sorted((data or {}).items(), key=lambda x: x[0].casefold()):
                row = {"key": k}
                for f, _h, _kind in STYLE_COLS[1:]:
                    val = (d or {}).get(f)
                    row[f] = ("on" if val else "off") if (f in TRI_KEYS and val is not None) else (tabs_text(val) if f == "tabs" else val)
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
                for d, key in ((h, "h_table"), (f, "f_table")):       # 3.25.0: built as a table
                    ws = []
                    for x in r.get(key) or []:
                        try:
                            ws.append(round(float(x), 3))
                        except (TypeError, ValueError):
                            pass
                    if ws:
                        d["table"] = {"widths_in": ws, "borders": r.get("borders") or "none"}
                out[r["key"] or "part"] = {"header": h, "footer": f}
            _set(self.work, spec["path"], out)
            return
        if ad == "listnum":
            lists = []
            for r in rows:
                if not (r.get("style") or "").strip():
                    continue
                name = (r.get("list") or "List").strip()
                cur = next((l for l in lists if l["name"] == name), None)
                if cur is None:
                    cur = {"name": name, "levels": []}; lists.append(cur)
                cur["levels"].append({"style": r["style"].strip(), "fmt": r.get("fmt") or "decimal", "text": r.get("text") or "",
                                      "font": (r.get("font") or "").strip(), "left": r.get("left") or 0, "hanging": r.get("hanging") or 0})
            _set(self.work, spec["path"], lists)
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
                    d[f] = (val == "on") if f in TRI_KEYS else (tabs_parse(val) if f == "tabs" else val)
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
                if not d.get("word_style"):
                    d.pop("word_style", None)
                if d.get("caption_position") in ("", None):
                    d.pop("caption_position", None)
                out[k] = d
            _set(self.work, spec["path"], out)
            return
        _set(self.work, spec["path"], rows)

    def load_tables(self):
        self.show_hf_designs()
        self.fill_allowed()
        from . import docparts as DP                # 3.26.0
        DP.fill_all(self)
        for key, spec in self.tables.items():      # 3.28.1: only the tables on show are filled now; the rest when
            spec["stale"] = True                       # their section opens or anything reads them
        self.fill_shown_tables()

    def fill_shown_tables(self):
        for key, spec in self.tables.items():
            if spec.get("stale") and spec["w"].isVisibleTo(self):
                self.tables[key]

    def _fill_table(self, key, spec):
        spec["stale"] = False
        t = spec["w"]
        rows = self._rows_of(spec)
        spec["rows"] = rows
        t.blockSignals(True)
        t.setRowCount(0)
        for r in rows:
            self._add_table_row(key, r)
        self._show_lvltext(key)
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
            elif kind == "lvltext":                    # 3.24.1: shown as it looks (1.1), kept as Word's codes (%1.%2)
                w = QLineEdit(); w.setProperty("raw", "" if val is None else str(val))
                w.textEdited.connect(lambda _x, k=key: self.table_changed(k))
                w.editingFinished.connect(lambda k=key: self._show_lvltext(k))
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
                elif kind == "lvltext":
                    r[field] = w
                else:
                    r[field] = w.text().strip()
            rows.append(r)
        for i, (lvl, fmts) in enumerate(self._lvl_of(rows)):
            for field, _h, kind in spec["cols"]:
                if kind == "lvltext":
                    w = rows[i][field]                 # a bullet is its character, kept as typed
                    rows[i][field] = (w.text().strip() if rows[i].get("fmt") == "bullet"
                                      else NT.keep_or_parse(w.text(), w.property("raw"), fmts, lvl))
                    w.setProperty("raw", rows[i][field])
        return rows

    @staticmethod
    def _lvl_of(rows):
        """3.24.1: each row's level and the formats of its levels: rows in order, a new list (List column) starting at 1."""
        out, seen = [], {}
        for r in rows:
            g = r.get("list") or ""
            seen.setdefault(g, []).append(r.get("fmt") or "decimal")
            out.append((len(seen[g]), seen[g]))
        return out

    def _show_lvltext(self, key, skip=None):
        """3.24.1: every Number reads cell shown as it will look, from the codes kept."""
        spec = self.tables[key]
        cols = [c for c, (_f, _h, kind) in enumerate(spec["cols"]) if kind == "lvltext"]
        if not cols:
            return
        t = spec["w"]
        rows = []
        for i in range(t.rowCount()):
            r = {}
            for c, (field, _h, kind) in enumerate(spec["cols"]):
                if field in ("list", "fmt"):
                    w = t.cellWidget(i, c)
                    r[field] = (w.currentData() if isinstance(kind, tuple) else w.text().strip()) if w is not None else ""
            rows.append(r)
        for i, (_lvl, fmts) in enumerate(self._lvl_of(rows)):
            for c in cols:
                w = t.cellWidget(i, c)
                if w is None or w is skip:
                    continue
                w.blockSignals(True); w.setText(NT.show(w.property("raw") or "", fmts)); w.blockSignals(False)

    def table_changed(self, key):
        self._store(self.tables[key], self._read_table(key))
        self._show_lvltext(key, skip=QApplication.focusWidget())
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
        self.scope_box.addItem("Team standard (every volume starts here)", "team:")
        for t in self.data["types"]:
            self.scope_box.addItem(f"Volume: {t['name']}", "type:" + t["id"])
        for e in self.data.get("effort_types", []):
            self.scope_box.addItem(f"Effort type: {e['name']} (every volume in it)", "etype:" + e["id"])
            for pid in e["profiles"]:
                self.scope_box.addItem(f"Effort type: {e['name']} > {PRL.type_of(self.data, pid)['name']}", f"etp:{e['id']}:{pid}")
        if self.host.ws is not None:
            self.scope_box.addItem(f"This effort: {self.host.effort_name}", "effort:")
        i = self.scope_box.findData(cur) if cur else -1
        self.scope_box.setCurrentIndex(i if i >= 0 else (self.scope_box.count() - 1 if self.host.ws is not None else 0))
        self.scope_box.blockSignals(False)
        self._sync_pickers()
        eff = (self.host.ws.get("prod_std", {}) or {}) if self.host.ws is not None else {}
        self.eff_etype.blockSignals(True); self.eff_etype.clear()
        self.eff_etype.addItem("None (volumes only)", "")
        for e in self.data.get("effort_types", []):
            self.eff_etype.addItem(e["name"], e["id"])
        self.eff_etype.setCurrentIndex(max(0, self.eff_etype.findData(eff.get("effort_type") or "")))
        self.eff_etype.blockSignals(False)
        self.fill_effort_profiles(eff)
        self.switch(force=True)

    def fill_effort_profiles(self, eff=None):
        """This effort's default volume: one of its effort type's volumes (every volume without an effort type)."""
        eff = eff if eff is not None else ((self.host.ws.get("prod_std", {}) or {}) if self.host.ws is not None else {})
        et = PRL.effort_type_of(self.data, eff.get("effort_type"))
        ids = et["profiles"] if et else [t["id"] for t in self.data["types"]]
        self.eff_type.blockSignals(True); self.eff_type.clear()
        for pid in ids:
            self.eff_type.addItem(PRL.type_of(self.data, pid)["name"], pid)
        want = eff.get("type") if eff.get("type") in ids else ((et or {}).get("default_profile") or self.data["default"])
        self.eff_type.setCurrentIndex(max(0, self.eff_type.findData(want)))
        self.eff_type.blockSignals(False)

    # ------------------------------------------------------------------ 3.25.0: the two Editing boxes
    def _fill_volumes(self, eid):
        cur = self.vol_pick.currentData()
        self.vol_pick.blockSignals(True); self.vol_pick.clear()
        self.vol_pick.addItem("Any volume", "")
        et = PRL.effort_type_of(self.data, eid) if eid else None
        for tid in (et["profiles"] if et else [t["id"] for t in self.data.get("types", [])]):
            self.vol_pick.addItem(PRL.type_of(self.data, tid)["name"], tid)
        self.vol_pick.setCurrentIndex(max(0, self.vol_pick.findData(cur)))
        self.vol_pick.blockSignals(False)

    def _sync_pickers(self):
        """The two boxes and This effort only follow the layer being edited."""
        if not hasattr(self, "etype_pick"):
            return
        scope, rest = (self.scope_box.currentData() or "team:").split(":", 1)
        eid, tid = (rest.split(":", 1) if scope == "etp" else ((rest, "") if scope == "etype" else ("", rest if scope == "type" else "")))
        for w in (self.etype_pick, self.vol_pick, self.this_effort):
            w.blockSignals(True)
        self.etype_pick.clear(); self.etype_pick.addItem("Any effort type", "")
        for e in self.data.get("effort_types", []):
            self.etype_pick.addItem(e["name"], e["id"])
        self.etype_pick.setCurrentIndex(max(0, self.etype_pick.findData(eid)))
        self.vol_pick.blockSignals(False)
        self._fill_volumes(eid)
        self.vol_pick.blockSignals(True)
        self.vol_pick.setCurrentIndex(max(0, self.vol_pick.findData(tid)))
        self.this_effort.setVisible(self.host.ws is not None)
        self.this_effort.setText(f"This effort only: {self.host.effort_name}" if self.host.ws is not None else "This effort only")
        self.this_effort.setChecked(scope == "effort")
        self.etype_pick.setEnabled(scope != "effort"); self.vol_pick.setEnabled(scope != "effort")
        for w in (self.etype_pick, self.vol_pick, self.this_effort):
            w.blockSignals(False)

    def picked(self, fill_volumes=False):
        """A choice in the two boxes (or This effort only) picks the layer to edit."""
        if fill_volumes:
            self._fill_volumes(self.etype_pick.currentData())
        if self.this_effort.isChecked() and self.host.ws is not None:
            key = "effort:"
        else:
            eid, tid = self.etype_pick.currentData() or "", self.vol_pick.currentData() or ""
            key = (f"etp:{eid}:{tid}" if eid and tid else f"etype:{eid}" if eid else f"type:{tid}" if tid else "team:")
        i = self.scope_box.findData(key)
        if i >= 0 and i != self.scope_box.currentIndex():
            self.scope_box.setCurrentIndex(i)
        else:
            self._sync_pickers()
        return key

    def switch(self, force=False):
        if self.dirty and not force:
            self.save(quiet=True)
        scope, rest = (self.scope_box.currentData() or "team:").split(":", 1)
        eid, tid = (rest.split(":", 1) if scope == "etp" else ((rest, "") if scope == "etype" else ("", rest)))
        self.scope, self.type_id, self.etype_id = scope, tid, eid
        d = self.data
        if scope == "team":
            self.base = copy.deepcopy(PRL.COMPANY)
            self.work = copy.deepcopy(d["company"])
        elif scope == "type":
            self.base = copy.deepcopy(d["company"])
            self.work = PRL.resolved_type(d, tid)
        elif scope == "etype":
            e = PRL.effort_type_of(d, eid)
            self.base = copy.deepcopy(d["company"])
            self.work = PRL.merge(d["company"], PRL.effort_layer_of(e))
            self.work["name"] = e["name"]
        elif scope == "etp":
            e = PRL.effort_type_of(d, eid)
            self.base = PRL.merge(PRL.merge(d["company"], PRL.layer_of(PRL.type_of(d, tid))), PRL.effort_layer_of(e))
            self.work = PRL.merge(self.base, (e.get("profile_over") or {}).get(tid) or {})
            self.work["name"] = PRL.type_of(d, tid)["name"]
        else:
            eff = self.host.ws.get("prod_std", {}) or {}
            eid = eff.get("effort_type") if PRL.effort_type_of(d, eff.get("effort_type")) else None
            et = PRL.effort_type_of(d, eid)
            pt = eff.get("type") or (et or {}).get("default_profile") or d["default"]
            self.base = PRL.resolved_type(d, pt, eid)
            self.work = PRL.merge(self.base, eff.get("over") or {})
        self.work.setdefault("variables", {})
        if PRL.repair_rows(self.work):                 # 3.32.1: row looks an import left without their settings
            diag.activity("prodstd_rows_repaired")
        for row, show in ((self.eff_row, scope == "effort"), (self.match_row, scope == "type"), (self.et_row, scope == "etype")):
            for i in range(row.count()):
                x = row.itemAt(i).widget()
                if x is not None:
                    x.setVisible(show)
        if scope == "type":
            self.match_edit.setText(", ".join(PRL.type_of(d, tid).get("match") or []))
        if scope == "etype":
            e = PRL.effort_type_of(d, eid)
            self.et_profiles.blockSignals(True); self.et_profiles.clear()
            from PySide6.QtWidgets import QListWidgetItem
            for t in d["types"]:
                it = QListWidgetItem(t["name"]); it.setData(Qt.UserRole, t["id"])
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if t["id"] in e["profiles"] else Qt.Unchecked)
                self.et_profiles.addItem(it)
            self.et_profiles.blockSignals(False)
            self.et_default.blockSignals(True); self.et_default.clear()
            for pid in e["profiles"]:
                self.et_default.addItem(PRL.type_of(d, pid)["name"], pid)
            self.et_default.setCurrentIndex(max(0, self.et_default.findData(e.get("default_profile"))))
            self.et_default.blockSignals(False)
        self.eff_said.setVisible(scope == "effort")
        if scope == "effort":
            said = (self.host.ws.get("prod_std", {}) or {}).get("said") or []
            self.eff_said.setText(("From the RFP: " + "; ".join(said)) if said else
                                  "Nothing read from the RFP yet. Fill from the RFP's formatting rules reads Submission Rules.")
        self.binder.load()
        self.fill_row_scope()
        self.load_tables()
        self.show_parts()
        self.fill_profile()                            # 3.33.0
        self.dirty = False
        self.state.setText({"team": "Team standard", "type": "Volume", "etype": "Effort type, every volume",
                            "etp": "Effort type, this volume", "effort": "This effort only"}[scope])
        self.show_problems()
        if hasattr(self, "std_preview"):
            self.std_preview.refresh()

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
        if hasattr(self, "std_preview"):
            self.std_preview.refresh()

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
            match = [w.strip() for w in self.match_edit.text().split(",") if w.strip()]
            if match:
                keep["match"] = match
            t.clear(); t.update(keep); t.update(layer)
        elif self.scope == "etype":
            e = PRL.effort_type_of(d, self.etype_id)
            layer = PRL.diff(self.work, d["company"])
            layer.pop("name", None); layer.pop("variable_source", None)
            keep = {k: e[k] for k in PRL.EFFORT_TYPE_KEYS if k in e}
            chosen = [self.et_profiles.item(i).data(Qt.UserRole) for i in range(self.et_profiles.count())
                      if self.et_profiles.item(i).checkState() == Qt.Checked]
            if chosen:
                keep["profiles"] = chosen
            dp = self.et_default.currentData()
            keep["default_profile"] = dp if dp in keep["profiles"] else keep["profiles"][0]
            e.clear(); e.update(keep); e.update(layer)
        elif self.scope == "etp":
            e = PRL.effort_type_of(d, self.etype_id)
            over = PRL.diff(self.work, self.base)
            over.pop("name", None); over.pop("variable_source", None)
            e.setdefault("profile_over", {})[self.type_id] = over
            if not over:
                e["profile_over"].pop(self.type_id, None)
        else:
            eff = dict(self.host.ws.get("prod_std", {}) or {})
            over = PRL.diff(self.work, self.base)
            over.pop("name", None); over.pop("variable_source", None)
            eff["over"] = over
            eff["type"] = self.eff_type.currentData() or d["default"]
            eff["effort_type"] = self.eff_etype.currentData() or ""
            self.host.ws.set("prod_std", eff)
        PRL.save(self.host.config_dir, d)
        self.dirty = False
        self.state.setText("Saved")
        if self.scope == "team":
            diag.activity("prod_standards_saved_team")
        elif self.scope in ("type", "etype", "etp"):
            diag.activity("prod_standards_saved_type")
        else:
            diag.activity("prod_standards_saved_effort")
        if not quiet:
            self.host.toast("Production standards saved")
        return True

    def add_type(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New volume", "Its name (for example: Technical volume, Cost volume, White paper):")
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
        for e in self.data.get("effort_types", []):      # 3.8.0: a new profile is offered in every effort type (untick to drop)
            e.setdefault("profiles", []).append(t["id"])
        PRL.save(self.host.config_dir, self.data)
        self.refresh()
        self.scope_box.setCurrentIndex(self.scope_box.findData("type:" + t["id"]))
        return t["id"]

    def add_effort_type(self, name=None):
        """3.8.0: a new effort type holding every volume (choose which it keeps, and its default)."""
        if name is None:
            name, ok = QInputDialog.getText(self, "New effort type", "Its name (for example: RFP response, Page-limited RFP "
                                            "response, White paper, Program deliverables):")
            if not ok:
                return ""
        name = " ".join((name or "").split())
        if not name or name in [e["name"] for e in self.data.get("effort_types", [])]:
            self.host.status("Give it a name not already used.")
            return ""
        if self.dirty:
            self.save(quiet=True)
        e = {"id": PRL.slug(name, {x["id"] for x in self.data.get("effort_types", [])}), "name": name,
             "profiles": [t["id"] for t in self.data["types"]], "default_profile": self.data["default"]}
        self.data.setdefault("effort_types", []).append(e)
        PRL.save(self.host.config_dir, self.data)
        self.refresh()
        self.scope_box.setCurrentIndex(self.scope_box.findData("etype:" + e["id"]))
        diag.activity("prod_effort_type_added")
        return e["id"]

    def manage_effort_types(self, run=True):
        """3.18.2: add, rename, order and take out effort types (Start an effort opens the same)."""
        from .efforttypes import manage
        if self.dirty:
            self.save(quiet=True)
        d = manage(self, self.host.config_dir, run=run)
        if run and d.changed:
            self.data = PRL.load(self.host.config_dir)
            self.refresh()
        return d

    def effort_etype_changed(self):
        """This effort's type: its volumes become the choices; the effort keeps its own values."""
        if self.host.ws is None:
            return
        eff = dict(self.host.ws.get("prod_std", {}) or {})
        eff["effort_type"] = self.eff_etype.currentData() or ""
        et = PRL.effort_type_of(self.data, eff["effort_type"])
        if et and eff.get("type") not in et["profiles"]:
            eff["type"] = et["default_profile"]
        self.host.ws.set("prod_std", eff)
        self.fill_effort_profiles(eff)
        self.switch(force=True)

    def template_ready(self):
        """3.13.0: Make a .dotx template is a Preview tool: it works once the team turns it on."""
        import roleaccess as RA
        if RA.preview_on(self.host.config_dir, "template"):
            return True
        self.host.notice_page.show_for({"kind": "preview", "step": "template", "profile": self.host.profile()[0]})
        self.host.stack.setCurrentWidget(self.host.notice_page)
        self.host.page_title.setText("Make a .dotx template")
        return False

    def make_templates_all(self, word=None, eid=None, start_from=""):
        """3.8.0: one template for each volume of an effort type (the one being edited unless eid names another), each
        with the effort type's rules. 3.25.0: Make templates calls this for the effort type chosen there."""
        eid = eid or (self.etype_id if self.scope == "etype" else None)
        if not eid or not PRL.effort_type_of(self.data, eid):
            return []
        if not self.template_ready():
            return []
        if self.dirty:
            self.save(quiet=True)
        import prodtemplate as PT
        e = PRL.effort_type_of(self.data, eid)
        if word is None and sys.platform.startswith("win"):
            import prodword
            word = prodword.update_fields
        out = []
        folder = os.path.join(self.template_folder(), e["name"])
        for pid in e["profiles"]:
            std = PRL.engine_ready(PRL.resolved_type(self.data, pid, e["id"]))
            std["name"] = f"{e['name']} - {PRL.type_of(self.data, pid)['name']}"
            try:
                out.append(PT.make(std, folder, start_from or "", word=word or None, parts_dir=self.parts_dir()))
            except Exception:  # noqa: BLE001
                diag.swallowed()
        clean = sum(1 for j in out if j.check.count() == 0)
        self.host.status(f"{len(out)} template(s) made in {folder}; {clean} pass their own check.")
        diag.activity("prod_templates_made", n=len(out))
        return out

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

    # ------------------------------------------------------------------ 3.25.0: allowed styles, ticked from a list
    def _allowed_rows(self):
        """[(name, type, group, uses, from)]: this standard's styles, then the library's (one row per name)."""
        import templatelib as TL
        rows, seen = [], set()

        def group(n, d):
            low = n.lower()
            if low.startswith("heading") or low == "title":
                return "Headings"
            if low.startswith(("caption", "toc", "table of figures")):
                return "Captions and TOC"
            if d.get("hidden"):
                return "Hidden text"
            if "list" in low:
                return "Lists"
            if low in ("header", "footer"):
                return "Headers and footers"
            return "Body and the rest"
        spec = PRL.style_spec(PRL.engine_ready(copy.deepcopy(self.work))) if self.work else {}
        for n in sorted(set(spec) | set((self.work or {}).get("style_defs") or {}), key=str.casefold):
            d = dict(spec.get(n) or {}, **((self.work.get("style_defs") or {}).get(n) or {}))
            rows.append((n, (d.get("type") or "paragraph").title(), group(n, d), "", "This standard")); seen.add(n.casefold())
        try:
            lib = TL.Library(self.host.config_dir)
            for it in lib.items:
                if it.get("kind") != "style":
                    continue
                n = it.get("base_name") or it["name"]
                if n.casefold() in seen:
                    continue
                d = lib.values(it) or {}
                rows.append((n, (d.get("type") or "paragraph").title(), group(n, d), ", ".join((it.get("tags") or {}).get("use") or []),
                             it.get("source") or "Template library"))
                seen.add(n.casefold())
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return rows

    def fill_allowed(self):
        if not hasattr(self, "allow_t"):
            return
        allowed = list(((self.work or {}).get("styles") or {}).get("allowed") or [])
        rows = self._allowed_rows()
        have = {r[0].casefold() for r in rows}
        rows += [(n, "", "Not defined here", "", "Allowed list") for n in allowed if n.casefold() not in have]
        on = {n.casefold() for n in allowed}
        t = self.allow_t
        t.blockSignals(True); t.setSortingEnabled(False); t.setRowCount(0)
        for r in rows:
            i = t.rowCount(); t.insertRow(i)
            for c, val in enumerate(r):
                it = QTableWidgetItem(val)
                if c == 0:
                    it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    it.setCheckState(Qt.Checked if r[0].casefold() in on else Qt.Unchecked)
                t.setItem(i, c, it)
        t.setSortingEnabled(True); t.blockSignals(False)
        t.resizeColumnsToContents()
        cur = self.allow_show.currentData()
        self.allow_show.blockSignals(True); self.allow_show.clear()
        self.allow_show.addItem("Every style", None)
        for label, col in (("Type", 1), ("Group", 2), ("Use case", 3), ("From", 4)):
            vals = sorted({x.strip() for r in rows for x in r[col].split(",") if x.strip()}, key=str.casefold)
            for val in vals:
                self.allow_show.addItem(f"{label}: {val}", (col, val))
        self.allow_show.setCurrentIndex(max(0, self.allow_show.findData(cur)))
        self.allow_show.blockSignals(False)
        self.allow_only.blockSignals(True); self.allow_only.setChecked(bool(allowed)); self.allow_only.blockSignals(False)
        t.setEnabled(bool(allowed))
        self.filter_allowed()

    def filter_allowed(self):
        want, text = self.allow_show.currentData(), self.allow_find.text().strip().casefold()
        t = self.allow_t
        for i in range(t.rowCount()):
            name = t.item(i, 0).text()
            ok = (not text or text in name.casefold())
            if ok and want:
                col, val = want
                ok = val in [x.strip() for x in t.item(i, col).text().split(",")]
            t.setRowHidden(i, not ok)

    def tick_allowed(self, on):
        if not self.allow_only.isChecked():
            self.allow_only.setChecked(True)
        t = self.allow_t
        t.blockSignals(True)
        for i in range(t.rowCount()):
            if not t.isRowHidden(i):
                t.item(i, 0).setCheckState(Qt.Checked if on else Qt.Unchecked)
        t.blockSignals(False)
        self.allowed_changed()

    def allow_on(self, on):
        """Only the ticked styles: turned on, this standard's own styles start ticked; off, any style is allowed."""
        t = self.allow_t
        t.setEnabled(on)
        t.blockSignals(True)
        for i in range(t.rowCount()):
            t.item(i, 0).setCheckState(Qt.Checked if (on and t.item(i, 4).text() == "This standard") else Qt.Unchecked)
        t.blockSignals(False)
        self.allowed_changed()

    def allowed_changed(self):
        t = self.allow_t
        names = [t.item(i, 0).text() for i in range(t.rowCount()) if t.item(i, 0).checkState() == Qt.Checked]
        _set(self.work, ("styles", "allowed"), sorted(names, key=str.casefold) if self.allow_only.isChecked() else [])
        self.changed()
        return names

    # ------------------------------------------------------------------ 3.25.0: import from a file, make templates
    def import_file(self, path=None, section="", run=True, use_here=True, keep=True):
        """One Import: read a template or Word document once and take its items, one, some or all, into what is being
        edited (Use here) and the library (Keep in the library). section: only that section's items. Returns the dialog."""
        from .collectview import CollectDialog
        title = dict(SECTIONS).get(section, "")
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import from a template or Word document (it is only read)" + (f": {title}" if title else ""),
                                                  os.path.expanduser("~"), "Word and themes (*.dotx *.dotm *.docx *.docm *.thmx)")
            if not path:
                return None
        d = CollectDialog(self, path, only=IMPORT_KINDS.get(section), section=title)
        d.use_here.setChecked(use_here); d.keep_lib.setChecked(keep)
        if run:
            d.exec()
        return d

    def collect(self, path=None, run=True):
        """3.22.0: from the Template library: Import into the library only (Use here off). Returns the dialog."""
        return self.import_file(path, run=run, use_here=False)

    def hf_from_quick_part(self, part=None, kind=None, entry=None):
        """3.25.0: one of this standard's Quick Parts as a part's header or footer, kept exactly as built."""
        import prodquickparts as QP
        entries = [e for e in ((self.work.get("quick_parts") or {}).get("entries") or [])
                   if os.path.isfile(os.path.join(self.parts_dir(), e.get("source") or ""))]
        if not entries:
            self.host.status("Add Quick Parts first (Content > Quick Parts), then use one here.")
            return None
        parts = [p.get("key") for p in ((self.work.get("pagination") or {}).get("parts") or [])] or ["body"]
        if part is None:
            from PySide6.QtWidgets import QDialog, QDialogButtonBox
            dlg = QDialog(self); dlg.setWindowTitle("Use a Quick Part as a header or footer")
            fl = QFormLayout(dlg)
            pc = QComboBox(); pc.addItems(parts); fl.addRow("Part", pc)
            kc = QComboBox(); kc.addItem("Header", "header"); kc.addItem("Footer", "footer"); fl.addRow("Header or footer", kc)
            ec = QComboBox()
            for e in entries:
                ec.addItem(f"{e.get('category') or 'no category'} / {e['name']}", e["name"])
            fl.addRow("Quick Part", ec)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
            fl.addRow(bb)
            if dlg.exec() != QDialog.Accepted:
                return None
            part, kind, entry = pc.currentText(), kc.currentData(), ec.currentData()
        e = next((x for x in entries if x["name"] == entry), None)
        if e is None:
            return None
        d = QP.as_design(os.path.join(self.parts_dir(), e["source"]), e["name"], kind)
        if not d:
            self.host.status(f"{entry} is not in its kept file any more.")
            return None
        self.work.setdefault("hf_designs", {}).setdefault(part, {}).update(d)
        self.show_hf_designs()
        self.changed()
        self.host.status(f"{entry} is the {part} {kind}, kept as built. Save keeps it in this standard.")
        return d

    def make_templates(self, start=None):
        """3.25.0: Make templates: read each template in full, then make it."""
        from . import maketemplates as MT
        return MT.run(self, start)

    def library(self, run=True):
        from .collectview import LibraryDialog
        d = LibraryDialog(self)
        if run:
            d.exec()
        return d

    def after_library(self, said):
        """An item from the library went into what is being edited."""
        self.show_hf_designs()
        self.binder.load()
        self.fill_row_scope()
        self.load_tables()
        self.show_parts()
        self.changed()
        self.host.status(f"From the library: {said}. Save keeps it in this standard.")

    def learn(self, path=None, keys=None):
        """Read a template or document (once; it is never written) and take the areas chosen into what is being edited.
        keys (tests): the areas to take without asking. Returns the areas taken."""
        import prodlearn as PL
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A template or finished volume to learn from (it is only read)",
                                                  os.path.expanduser("~"), "Word (*.dotx *.docx *.dotm *.docm)")
            if not path:
                return []
        got = PL.learn(path, PRL.engine_ready(copy.deepcopy(self.work)), parts_dir=self.parts_dir())
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
        self.show_parts()
        self.changed()
        self.show_problems()
        diag.activity("prod_learned", n=len(keys))
        self.host.status(f"Learned {len(keys)} area(s) from {os.path.basename(path)}. Review them, then Save.")
        return keys

    def _pick_areas(self, got, name):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem
        dlg = QDialog(self); dlg.setWindowTitle(f"Import from {name}")
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

    def make_template(self, start_from=None, word=None, wait=True, name=None):
        """A Word template with every value in force at this layer, in the output folder's Templates folder.
        start_from: "" for the Stationkeeper base, a path to start from a template (read once), None to ask.
        name (3.23.0): what the template is called (asked when start_from is asked); its version counts up."""
        import prodtemplate as PT
        import templatereg as TR
        ask_name = start_from is None and name is None
        if not self.template_ready():
            return None
        probs = self.show_problems()
        if probs:
            self.host.status("Fix these first: " + probs[0])
            return None
        if start_from is None:
            from PySide6.QtWidgets import QMessageBox
            mb = QMessageBox(self); mb.setWindowTitle("Make a .dotx template")
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
        if ask_name:
            known = TR.names(self.host.config_dir)
            name, ok = QInputDialog.getItem(self, "Name the template", "What the template is called (where or how it is used). "
                                            "Making it again under the same name makes the next version:",
                                            [std["name"]] + [k for k in known if k != std["name"]], 0, True)
            if not ok:
                return None
        name = TR.clean_name(name or std["name"]) or "Template"
        ver = TR.next_version(self.host.config_dir, name)
        std["_template_name"], std["_template_version"], std["_standard"] = name, ver, std["name"]
        std["name"] = f"{name} v{ver}"
        try:
            from .collectview import installed_fonts
            std["_installed_fonts"] = installed_fonts()
        except Exception:
            diag.swallowed()
        if word is None and sys.platform.startswith("win"):
            import prodword
            word = prodword.update_fields
        self.host.status("Making the template...")
        folder = self.template_folder()
        self._tres = None
        self._tmeta, self._tmeta_std = (name, ver), std.get("_standard", "")

        def run():
            try:
                job = PT.make(std, folder, start_from, word=word, parts_dir=self.parts_dir())
                import prodwordgate as WG                  # 3.23.0: Word's own check, when Word is on this PC
                job.word_gate = WG.gate(job.copy) if (word and WG.available()) else None
                self._tres = ("job", job)
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
        val = getattr(job, "validation", None)
        rep_path = ""
        if val is not None:                            # 3.23.0: the validation report beside the template
            rep_path = os.path.splitext(job.copy)[0] + " - validation report.txt"
            try:
                import prodwordgate as WG
                with open(rep_path, "w", encoding="utf-8") as f:
                    f.write(val.text() + ("\n\n" + WG.text(job.word_gate) if getattr(job, "word_gate", None) else ""))
            except OSError:
                diag.swallowed(); rep_path = ""
        try:                                           # 3.23.0: its name and version, and the effort that made it
            import templatereg as TR
            name, ver = self._tmeta if getattr(self, "_tmeta", None) else (None, None)
            if name:
                e = TR.record(self.host.config_dir, name, ver, job.copy, self._tmeta_std, val, self.host.effort_name or "")
                if self.scope == "effort":
                    TR.note_on_effort(self.host.ws, name, e)
                job.template_name, job.template_version = name, ver
        except Exception:
            diag.swallowed()
        self.host.status(f"Template made: {os.path.basename(job.copy)} in {os.path.dirname(job.copy)}. Checked against this "
                         f"standard: {job.check.count()} finding(s)" + (f"; {len(refused)} step(s) refused" if refused else "")
                         + (f". Validation: {len(val.problems())} problem(s), {len(val.warnings())} warning(s) (report saved beside it)"
                            if val is not None else "")
                         + (". " + WG_line(job.word_gate) if getattr(job, "word_gate", None) else "") + ".")
        diag.activity("prod_template_made", n=job.check.count())
        return job
