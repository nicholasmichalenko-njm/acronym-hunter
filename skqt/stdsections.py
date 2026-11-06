"""The eight sections that lived only in Production Standards (3.69.0), built for LayerEditor (stdeditor). Each builder
takes the editor and a layout: the same values and words as Production Standards had, in their new homes.

Rules > Checks:                    graphics, office, terms
Formatting Standards:              styles (allowed styles), style_roles
Effort Profiles:                   content_map, fillins, fonts"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFontComboBox, QGridLayout, QLabel, QLineEdit, QTableWidget,
                               QTableWidgetItem)
import prodrules as PRL
from . import design as D
from .stdeditor import _set, enum, num


def build_graphics(ed, v):
    f, _c = ed.form(v, "Graphics", "What every figure must meet. Fix a Copy and Audit check every picture, chart and text "
                    "box against these; a picture is never re-encoded, resized or moved. Blank fonts: the Graphic row of "
                    "the font rules, else the volume's body, table and caption fonts.")
    wide = lambda: (lambda e: (e.setMinimumWidth(320), e)[1])(QLineEdit())
    ed.row(f, "Picture types allowed (comma)", wide(), ("graphics", "types"), "list", "png, jpeg, emf, wmf, svg, gif, tiff, bmp")
    ed.row(f, "Smallest resolution where placed (ppi)", num(0, 1200, 25, "any", 0), ("graphics", "min_ppi"), "num",
           "Pixels divided by the size the picture is placed at. 150 for screen, 300 for print")
    ed.row(f, "Widest a figure may be", enum([("", "Any width"), ("margins", "The text width (inside the margins)"),
                                              ("set", "A set width (below)")]), ("graphics", "max_width"), "enum")
    ed.row(f, "Set width (in)", num(0, 20, 0.25, "not set"), ("graphics", "max_width_in"), "num")
    ed.row(f, "Fonts allowed in drawings and charts (comma)", wide(), ("graphics", "fonts"), "list")
    ed.row(f, "Smallest text in drawings and charts (pt)", num(0, 72, 0.5, "any"), ("graphics", "min_text_pt"), "num")
    ed.row(f, "Estimate the text size inside pictures (OCR)", QCheckBox(), ("graphics", "ocr_text"), "bool",
           "Reads the words in each picture on this PC and estimates their size where placed. Shown as an estimate")
    ed.row(f, "Every figure has a caption", QCheckBox(), ("graphics", "caption"), "bool")
    ed.row(f, "Every picture has alt text", QCheckBox(), ("graphics", "alt_text"), "bool")
    ed.row(f, "RGB only (no CMYK pictures)", QCheckBox(), ("graphics", "rgb_only"), "bool")
    ed.row(f, "Largest picture file (MB)", num(0, 200, 1, "any", 0), ("graphics", "max_file_mb"), "num")


def build_office(ed, v):
    f, _c = ed.form(v, "Excel workbooks", "Fix a Copy checks a workbook against these and lists what differs; you fix it in "
                    "Excel. Blank font or size: the volume's table font and size.")
    w = QFontComboBox(); w.setEditable(True)
    ed.row(f, "Font", w, ("excel", "font"), "enum")
    ed.row(f, "Size (pt)", num(0, 72, 0.5), ("excel", "size"), "num")
    ed.row(f, "Header row bold", QCheckBox(), ("excel", "header", "bold"), "bool")
    ed.row(f, "Header row fill (hex, blank: any)", QLineEdit(), ("excel", "header", "fill"), "text")
    ed.row(f, "Header row text color (hex, blank: any)", QLineEdit(), ("excel", "header", "color"), "text")
    ed.row(f, "Header row frozen", QCheckBox(), ("excel", "freeze_header"), "bool")
    ed.row(f, "Print orientation", enum([("", "Either"), ("portrait", "Portrait"), ("landscape", "Landscape")]),
           ("excel", "print", "orientation"), "enum")
    ed.row(f, "Print fits one page wide", QCheckBox(), ("excel", "print", "fit_width"), "bool")
    ed.row(f, "Header row repeats on each printed page", QCheckBox(), ("excel", "print", "repeat_header"), "bool")
    ed.row(f, "Page number in the printed footer", QCheckBox(), ("excel", "print", "footer_page"), "bool")
    ed.row(f, "Restriction marking in the printed header or footer", QCheckBox(), ("excel", "print", "marking"), "bool")
    f2, _c2 = ed.form(v, "PowerPoint decks", "Fix a Copy checks a deck against these and lists what differs; you fix it in "
                      "PowerPoint. Blank fonts: the volume's body and table fonts.")
    ed.row(f2, "Fonts allowed (comma)", QLineEdit(), ("powerpoint", "fonts"), "text")
    ed.row(f2, "Smallest text (pt)", num(0, 72, 0.5), ("powerpoint", "min_size"), "num")
    ed.row(f2, "Smallest title (pt)", num(0, 96, 0.5), ("powerpoint", "title_min_size"), "num")
    ed.row(f2, "Slide size", enum([("", "Either"), ("16:9", "16:9"), ("4:3", "4:3")]), ("powerpoint", "slide_size"), "enum")
    ed.row(f2, "Restriction marking on every slide", QCheckBox(), ("powerpoint", "marking"), "bool")
    ed.row(f2, "Every slide has a title", QCheckBox(), ("powerpoint", "titles"), "bool")


def build_terms(ed, v):
    c = D.Card("Words Fix a Copy reports", "Reported in every copy; a suggestion is offered for review, never applied without "
               "you. (Team References > Banned phrases is the list Technical Edit, Final Check and Apply in Word read.)")
    v.addWidget(c)
    ed.table(c.body, ("terms", "banned"), [("find", "Word or phrase", "text"), ("suggest", "Suggest", "text"), ("why", "Why", "text")])
    c2 = D.Card("Fix automatically", "Misspellings and trademark or registered marks, applied with Fix all. Case: exact, or "
                "match (keeps the writer's first capital). When: first use or every use.")
    v.addWidget(c2)
    ed.table(c2.body, ("terms", "replace"), [("find", "Find", "text"), ("replace", "Replace with", "text"),
                                             ("case", "Case", ("enum", [("match", "Match"), ("exact", "Exact")])),
                                             ("when", "When", ("enum", [("", "Every use"), ("first", "First use")])),
                                             ("superscript", "Mark in superscript", "bool"), ("why", "Why", "text")])
    f, _c = ed.form(v, "Word lists", "Team terms, names and acronyms Word should accept (exported as custom dictionaries).")
    ed.row(f, "Team terms (comma)", QLineEdit(), ("terms", "lists", "team_terms"), "list")
    ed.row(f, "Employee names (comma)", QLineEdit(), ("terms", "lists", "employee_names"), "list")
    ed.row(f, "Acronyms (comma)", QLineEdit(), ("terms", "lists", "acronyms"), "list")
    ed.row(f, "Flag names one letter off", QCheckBox(), ("terms", "name_check"), "bool")


def _style_names(ed):
    names = set((ed.work.get("style_defs") or {}).keys())
    try:
        import templatelib as TL
        lib = TL.Library(ed.host.config_dir); lib.load()
        names |= {it.get("name") for it in lib.items if it.get("kind") == "style" and it.get("name")}
    except Exception:  # noqa: BLE001  no library yet
        pass
    names |= set(((ed.work.get("styles") or {}).get("allowed")) or [])
    return sorted((n for n in names if n), key=str.casefold)


def build_styles(ed, v):
    f, _c = ed.form(v, "Allowed styles", "Which styles a finished document may use, and what Fix a Copy does to the rest.")
    ed.row(f, "Set style fonts and sizes from the format variables", QCheckBox(), ("styles", "apply_variables"), "bool")
    ed.row(f, "Remove custom styles nobody uses", QCheckBox(), ("styles", "remove_unused_custom"), "bool")
    ed.row(f, "Hide built-in styles nobody uses from the gallery", QCheckBox(), ("styles", "hide_unused_builtin"), "bool")
    t = QLineEdit(); t.setMinimumWidth(420); t.setPlaceholderText("A .dotx or .dotm whose styles every fixed copy takes")
    ed.row(f, "Bring in the styles of this template", t, ("styles", "template"), "text")

    def pick():
        p, _ = QFileDialog.getOpenFileName(ed, "Template whose styles the copies take", "", "Word templates (*.dotx *.dotm *.docx)")
        if p:
            t.setText(p); t.textEdited.emit(p)
    f.addRow("", D.button("Choose a template...", None, pick))
    c2 = D.Card("The styles a document may use", "Tick each style a finished document may use; Fix a Copy reports any other. "
                "Nothing ticked: any style is allowed. The list holds this standard's styles and the libraries' styles.")
    v.addWidget(c2)
    ed.allowed = QTableWidget(0, 1); ed.allowed.setHorizontalHeaderLabels(["Style"]); ed.allowed.setMinimumHeight(240)
    ed.allowed.verticalHeader().setVisible(False); ed.allowed.horizontalHeader().setStretchLastSection(True)
    c2.body.addWidget(ed.allowed)

    def fill():
        on = {n.casefold() for n in ((ed.work.get("styles") or {}).get("allowed") or [])}
        ed.allowed.blockSignals(True); ed.allowed.setRowCount(0)
        for n in _style_names(ed):
            i = ed.allowed.rowCount(); ed.allowed.insertRow(i)
            it = QTableWidgetItem(n); it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if n.casefold() in on else Qt.Unchecked); ed.allowed.setItem(i, 0, it)
        ed.allowed.blockSignals(False)

    def changed(_it=None):
        ticked = [ed.allowed.item(i, 0).text() for i in range(ed.allowed.rowCount()) if ed.allowed.item(i, 0).checkState() == Qt.Checked]
        _set(ed.work, ("styles", "allowed"), ticked)
        ed.changed()
    ed.allowed.itemChanged.connect(changed)
    ed.__dict__.setdefault("after_fill", []).append(fill)


def build_style_roles(ed, v):
    f, _c = ed.form(v, "Styles the rules read", "Name the style each one is typed in on the cover or title page. Rule 2 checks "
                    "the A number sits right under the restriction and Warning block, right-justified; Rule 7 checks the "
                    "footer's left cell reads the A number.")
    boxes = []
    for key, text in (("a_number", "The A number's style"), ("restriction", "The restriction and Warning block's style")):
        w = QComboBox(); w.setEditable(True); w.setMinimumWidth(320); w.lineEdit().setPlaceholderText("Not set")
        boxes.append(w)
        ed.row(f, text, w, ("style_roles", key), "enum")

    def fill():
        for w in boxes:
            cur = w.currentText()
            w.blockSignals(True); w.clear(); w.addItems(_style_names(ed)); w.setEditText(cur); w.blockSignals(False)
    ed.__dict__.setdefault("after_fill", []).insert(0, fill)


def build_content_map(ed, v):
    from .profileview import ContentMap
    c = D.Card("Content map", "Which style each kind of placed item takes, hidden or shown, in the file or not. The setup "
               "template made for this profile reads it.")
    v.addWidget(c)
    ed.content_map = ContentMap(ed); c.body.addWidget(ed.content_map)
    ed.__dict__.setdefault("after_fill", []).append(lambda: ed.content_map.refresh())


def build_fillins(ed, v):
    import fillins as FI
    c = D.Card("Fields", "Values you type once that show everywhere they are referenced. Style on the cover (STYLEREF): the "
               "value sits once on the cover in its own style. Document property (DOCPROPERTY): a property of the file. Use "
               "a field in a header or footer as {key}. Volume name, solicitation and company are built in.")
    v.addWidget(c)
    ed.table(c.body, ("fill_ins",), [("key", "Key (use as {key})", "text"), ("name", "Name", "text"),
                                     ("kind", "Works by", ("enum", list(FI.KINDS))),
                                     ("style", "Cover style (STYLEREF)", "text"), ("property", "Document property", "text"),
                                     ("value", "Value", "text")])


def build_fonts(ed, v):
    c = D.Card("Font rules", "What the RFP allows for each kind of text. Blank means not checked. Fix a Copy reports text "
               "that breaks these, and says whether the style or typed formatting is the cause.")
    g = QGridLayout(); g.setHorizontalSpacing(D.SPACE["m"])
    for i, h in enumerate(("Text", "Allowed fonts (comma between)", "Smallest (pt)", "Largest (pt)", "RFP reference")):
        g.addWidget(D.label(h, "label"), 0, i)
    for r, sc in enumerate(PRL.SCOPES, 1):
        lab = QLabel(PRL.SCOPE_NAMES[sc]); g.addWidget(lab, r, 0)
        fl = QLineEdit(); fl.setPlaceholderText("any font"); g.addWidget(fl, r, 1)
        lo = num(0, 72, 0.5, "any"); g.addWidget(lo, r, 2)
        hi = num(0, 72, 0.5, "any"); g.addWidget(hi, r, 3)
        ref = QLineEdit(); ref.setPlaceholderText("L.4.2.1"); g.addWidget(ref, r, 4)
        ed.binder.bind(fl, ("fonts", sc, "fonts"), "list", lab)
        ed.binder.bind(lo, ("fonts", sc, "min_size"), "num", lab)
        ed.binder.bind(hi, ("fonts", sc, "max_size"), "num", lab)
        ed.binder.bind(ref, ("fonts", sc, "rfp_ref"), "text", lab)
    g.setColumnStretch(1, 1)
    c.body.addLayout(g)
    v.addWidget(c)

