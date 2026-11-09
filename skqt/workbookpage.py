"""Setup from a workbook, on the page (3.91.0; claude/stationkeeper-setup-from-workbook-3.91.md). Two panes: the
workbook on the left (click a column's tag to say what the column is, its style and its place in the order; click any
text to give it a character style, make it its own paragraph or leave it out) and the page Word gets on the right, drawn
in each style's look (click a paragraph to move its kind of text, for every section or this one, or to find it in the
workbook). The styles in use sit in a row above both; click one to change its look here. Make the setup in Word writes
it on the chosen template. workbooksetup holds the rules; the workbook is only read."""
import html, os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QCursor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu, QPushButton, QSplitter, QTextBrowser,
                               QVBoxLayout, QWidget)
import diag
import outlinelayouts as OL
import outlinexl as OX
import workbooksetup as WB
from . import design as D
from .commandbar import CommandBar

TINT = {"heading": "#E6EBF1", "guidance": "#DCF3E4", "source": "#FCEFD9", "rfp": "#EDE6F7", "support": "#E2ECF8",
        "authors": "#F1F5F9", "skip": "#EEEEEE"}
INK = {"heading": "#334155", "guidance": "#146C36", "source": "#9A4508", "rfp": "#4B1C80", "support": "#1F5FAD",
       "authors": "#475569", "skip": "#6B7280"}
FOCUS = "#2E7BE0"


def css_of(lk):
    """A style's look as CSS for the page (hidden text on a gray band: Qt draws no dotted underline)."""
    css = [f"color:#{str(lk.get('color') or '000000').lstrip('#')}"]
    if lk.get("bold"):
        css.append("font-weight:bold")
    if lk.get("italic"):
        css.append("font-style:italic")
    if lk.get("underline"):
        css.append("text-decoration:underline")
    if lk.get("font"):
        css.append(f"font-family:'{html.escape(str(lk['font']))}'")
    if lk.get("size"):
        css.append(f"font-size:{float(lk['size']):g}pt")
    if lk.get("hidden"):
        css.append("background-color:#ECEEF3")
    return ";".join(css)


def tint(color, keep=0.18):
    """A light wash of a style's color: how text with that character style is marked in the workbook."""
    c = str(color or "888888").lstrip("#")
    try:
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        r = g = b = 136
    return "#%02X%02X%02X" % tuple(int(x * keep + 255 * (1 - keep)) for x in (r, g, b))


def run_css(look):
    css = ["color:" + ("#000000" if look[2:] == "auto" else "#" + look[2:])]
    if look[0] == "B":
        css.append("font-weight:bold")
    if look[1] == "I":
        css.append("font-style:italic")
    return ";".join(css)


class StyleDialog(QDialog):
    """One style's look, changed on this page: font, size, color, bold, italic, underline, hidden."""

    def __init__(self, parent, name, kind, look, from_template):
        super().__init__(parent)
        self.setWindowTitle(name)
        self.look = dict(look)
        v = QVBoxLayout(self)
        v.addWidget(D.label(("Character style: inside the text, where it is" if kind == "character" else "Paragraph style")
                            + (". The template has it; what you change here goes over its look." if from_template else
                               ". The template does not have it: it is made when the setup is written."), "muted"))
        f = QFormLayout(); v.addLayout(f)
        self.font = QLineEdit(str(look.get("font") or "")); self.font.setPlaceholderText("As the text around it")
        self.size = QDoubleSpinBox(); self.size.setRange(0, 72); self.size.setSingleStep(0.5); self.size.setSpecialValueText("As the text around it")
        self.size.setValue(float(look.get("size") or 0))
        crow = QHBoxLayout()
        self.color = QLineEdit(str(look.get("color") or "").lstrip("#")); self.color.setMaxLength(6); self.color.setMaximumWidth(90)
        crow.addWidget(self.color); crow.addWidget(D.button("Pick...", None, lambda: self.pick())); crow.addStretch(1)
        self.bold = QCheckBox("Bold"); self.italic = QCheckBox("Italic"); self.under = QCheckBox("Underline")
        self.hidden = QCheckBox("Hidden (Show/Hide shows it; Strip setup takes it out)")
        for cb, k in ((self.bold, "bold"), (self.italic, "italic"), (self.under, "underline"), (self.hidden, "hidden")):
            cb.setChecked(bool(look.get(k)))
        lrow = QHBoxLayout(); lrow.addWidget(self.bold); lrow.addWidget(self.italic); lrow.addWidget(self.under); lrow.addStretch(1)
        f.addRow("Font", self.font); f.addRow("Size", self.size); f.addRow("Color", crow); f.addRow("Look", lrow); f.addRow("", self.hidden)
        self.sample = QLabel("The Offeror shall describe its ground segment architecture.")
        self.sample.setStyleSheet("QLabel{background:#FFFFFF;padding:8px;border:1px solid #D3DBE6}")
        v.addWidget(self.sample)
        for wdg in (self.bold, self.italic, self.under, self.hidden):
            wdg.toggled.connect(lambda _x: self.show_sample())
        self.color.textChanged.connect(lambda _x: self.show_sample()); self.font.textChanged.connect(lambda _x: self.show_sample())
        self.size.valueChanged.connect(lambda _x: self.show_sample())
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); v.addWidget(bb)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        self.show_sample()

    def pick(self):
        c = QColorDialog.getColor(QColor("#" + (self.color.text() or "000000")), self, "Color")
        if c.isValid():
            self.color.setText(c.name()[1:].upper())

    def value(self):
        c = self.color.text().strip().lstrip("#").upper()
        return {"font": self.font.text().strip(), "size": self.size.value() or 0, "color": c if len(c) == 6 else "",
                "bold": self.bold.isChecked(), "italic": self.italic.isChecked(), "underline": self.under.isChecked(),
                "hidden": self.hidden.isChecked()}

    def show_sample(self):
        self.sample.setText(f'<span style="{css_of(self.value())}">The Offeror shall describe its ground segment architecture.</span>')


class WorkbookPage(QDialog):
    def __init__(self, page, path):
        super().__init__(page)
        self.page, self.host, self.path = page, page.host, path
        self.cfg = self.host.config_dir
        self.setWindowTitle(f"Setup from {os.path.basename(path)}")
        self.resize(1440, 900)
        self.book = OX.read(path, known=OL.known_names(self.cfg))
        self.profile = OL.profile(self.cfg, self.book)
        self.layout_name = self.profile.get("name") or OL.STARTING
        self.pg = WB.page(self.book, self.profile, WB.saved(self.cfg, self.layout_name))
        self.tlooks = WB.template_looks(self.pg["template"]) if self.pg.get("template") else {}
        self.sel = None                                   # ("col", index) or ("look", index, look) or ("para", n)
        v = QVBoxLayout(self)
        top = QHBoxLayout(); v.addLayout(top)
        self.top = D.label("", "muted"); top.addWidget(self.top, 1)
        self.bar = CommandBar(self)
        self.b_make = self.bar.primary("Make the setup in Word", lambda: self.make(), "The page on the right as a Word file, "
                                   "on the template, every style applied")
        self.b_use = self.bar.add("Use this structure", lambda: self.use(), "The sections and requirements into this effort's "
                                  "Setup and compliance matrix, as before")
        self.b_tpl = self.bar.add("Template...", lambda: self.pick_template(), "The Word template the setup is written on")
        self.bar.more("Save the layout as...", lambda: self.save_as())
        self.bar.more("Kinds of text, as a list...", lambda: self.as_list())
        self.bar.more("Every section in the same order", lambda: self.every_section())
        top.addWidget(self.bar)
        srow = QHBoxLayout(); v.addLayout(srow)
        srow.addWidget(D.label("Styles", "muted"))
        self.style_row = QHBoxLayout(); srow.addLayout(self.style_row); srow.addStretch(1)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(D.label("Your workbook. Click a column's tag to say what it is and where it goes; click any text to give "
                             "it a character style. Rows keep the workbook's order.", "muted"))
        self.left = QTextBrowser(); self.left.setOpenLinks(False); self.left.setOpenExternalLinks(False)
        self.left.setStyleSheet("QTextBrowser{background:#FFFFFF;color:#000000}")
        self.left.anchorClicked.connect(lambda url: self.left_click(url.toString()))
        lv.addWidget(self.left, 1)
        split.addWidget(left)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.page_note = D.label("", "muted"); rv.addWidget(self.page_note)
        self.right = QTextBrowser(); self.right.setOpenLinks(False); self.right.setOpenExternalLinks(False)
        self.right.setStyleSheet("QTextBrowser{background:#FFFFFF;color:#000000}")    # a page, as Word shows it
        self.right.anchorClicked.connect(lambda url: self.right_click(url.toString()))
        rv.addWidget(self.right, 1)
        split.addWidget(right)
        split.setSizes([720, 680])
        self.redraw()

    # ------------------------------------------------------------ drawing
    def look(self, style):
        return WB.look_of(self.pg, style, self.tlooks)

    def tag_label(self, i, h):
        t = self.pg["tags"].get(h, "skip")
        order = WB.tag_order(self.pg)
        n = order.index(t) + 1 if t in order else 0
        return (f"{n} " if n and t != "skip" else "") + WB.TAG[t]

    def redraw(self):
        self.paras = WB.paragraphs(self.book, self.profile, self.pg)
        self.draw_left(); self.draw_right(); self.draw_styles()
        n = sum(1 for p in self.paras if p["tag"] == "heading")
        self.top.setText(f"{os.path.basename(self.path)}: {len(self.book['rows'])} row(s), {n} heading(s), "
                         f"{len(self.paras)} paragraph(s). Layout: {self.layout_name}. Template: "
                         + (os.path.basename(self.pg["template"]) if self.pg.get("template") else "none (a plain document)") + ".")

    def draw_left(self):
        hs = self.book["headers"]
        cols = [(i, h) for i, h in enumerate(hs) if h]
        out = ['<table cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-family:Calibri,Arial;font-size:10pt">', "<tr>"]
        for i, h in cols:
            t = self.pg["tags"].get(h, "skip")
            ring = f"border:2px solid {FOCUS};" if self.sel == ("col", i) else ""
            out.append(f'<th style="background:#F6F8FB;border:1px solid #D3DBE6;text-align:left;color:#4E5D71;font-weight:normal">'
                       f'{html.escape(h)}<br><a href="tag:{i}" style="text-decoration:none;color:{INK[t]};background:{TINT[t]};{ring}">'
                       f'&nbsp;{html.escape(self.tag_label(i, h))} &#9662;&nbsp;</a></th>')
        out.append("</tr>")
        for r in self.book["rows"]:
            out.append(f'<tr><a name="r{r["row"]}"></a>')
            for i, h in cols:
                t = self.pg["tags"].get(h, "skip")
                bits = []
                for txt, lk in (r["cells"][i] if i < len(r["cells"]) else []):
                    k = WB.key(h, lk)
                    ch = self.pg["chars"].get(k, "")
                    own = self.pg["own"].get(k)
                    deco = "text-decoration:line-through;color:#9CA3AF" if ch == "-" else run_css(lk)
                    mark = ""
                    if ch and ch != "-":
                        mark = f";background-color:{tint(self.look(ch).get('color') or '6B21A8')}"   # Qt draws no underline color
                    if own:
                        mark += ";background:#FFF6DD"
                    if self.sel == ("look", i, lk):
                        mark += f";background:#CFE1FB"
                    bits.append(f'<a href="run:{i}:{html.escape(lk)}" style="text-decoration:none;{deco}{mark}">'
                                + html.escape(txt).replace("\n", "<br>") + "</a>")
                bg = "#FBFBFC" if t == "skip" else "#FFFFFF"
                out.append(f'<td valign="top" style="border:1px solid #E6EBF1;background:{bg}">{"".join(bits)}</td>')
            out.append("</tr>")
        out.append("</table>")
        sb = self.left.verticalScrollBar().value()
        self.left.setHtml("".join(out))
        self.left.verticalScrollBar().setValue(sb)

    def draw_right(self):
        out = ['<div style="font-family:Calibri,Arial;font-size:11pt;color:#111111">']
        for n, p in enumerate(self.paras):
            sel = f"border:2px solid {FOCUS};" if self.sel == ("para", n) else ""
            if p["tag"] == "heading":
                sz = max(11, 17 - 2 * (p["level"] - 1))
                body = html.escape(p["runs"][0][0])
                out.append(f'<p style="margin:12px 0 4px 0;font-weight:bold;color:#1F3864;font-size:{sz}pt;{sel}"><a name="p{n}"></a>'
                           f'<a href="para:{n}" style="text-decoration:none;color:#1F3864">{body}</a>'
                           + (' <span style="font-size:8pt;color:#9A4508;font-weight:normal">own order</span>' if p["section"] in self.pg["sections"] else "")
                           + "</p>")
                continue
            plk = self.look(p["style"])
            runs = "".join((f'<span style="{css_of(dict(plk, **{k: v for k, v in self.look(ch).items() if k != "type"}))}">' if ch else
                            f'<span style="{css_of(plk)}">') + html.escape(t) + "</span>" for t, ch in p["runs"])
            out.append(f'<p style="margin:3px 0 3px 0;{sel}"><a name="p{n}"></a><a href="para:{n}" style="text-decoration:none">{runs}</a>'
                       f' <span style="font-size:7pt;color:#9CA3AF">{html.escape(p["style"])}</span></p>')
        out.append("</div>")
        sb = self.right.verticalScrollBar().value()
        self.right.setHtml("".join(out))
        self.right.verticalScrollBar().setValue(sb)
        own = len(self.pg["sections"])
        self.page_note.setText("The page Word gets. Hidden text shows on a gray band (Word shows it with Show/Hide on). "
                               "Click a paragraph to move its kind of text." + (f" {own} section(s) have their own order." if own else ""))

    def draw_styles(self):
        while self.style_row.count():
            it = self.style_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.style_buttons = {}
        for name, kind in WB.styles_in_use(self.pg, self.paras):
            if name.startswith("Heading "):
                continue
            lk = self.look(name)
            b = QPushButton(("a  " if kind == "character" else "¶  ") + name)
            b.setToolTip(("Character style" if kind == "character" else "Paragraph style") + ": click to change its look here")
            b.setStyleSheet(f"QPushButton{{border:1px solid #AEB9C9;border-radius:11px;padding:2px 10px;"
                            f"border-left:6px solid #{str(lk.get('color') or '888888').lstrip('#')}}}")
            b.clicked.connect(lambda _c=False, nm=name, kd=kind: self.edit_style(nm, kd))
            self.style_row.addWidget(b)
            self.style_buttons[name] = b

    # ------------------------------------------------------------ the left: tags and text
    def left_click(self, href):
        kind, _, rest = href.partition(":")
        if kind == "tag":
            self.sel = ("col", int(rest)); self.redraw()
            return self.tag_menu(int(rest))
        if kind == "run":
            i, _, lk = rest.partition(":")
            self.sel = ("look", int(i), lk); self.redraw()
            return self.text_menu(int(i), lk)
        return None

    def _style_names(self, kind):
        mine = [n for n, k in WB.styles_in_use(self.pg, self.paras) if k == kind]
        base = ([WB.SOURCE_CHAR] + sorted(set(WB.KIND_CHAR.values()) - {"-"})) if kind == "character" else sorted(set(WB.STYLES.values()))
        tpl = sorted(n for n, lk in self.tlooks.items() if lk.get("type") == kind and not n.lower().startswith(("heading", "toc ")))
        out = []
        for n in mine + tpl + base + list(self.pg.get("looks") or {}):
            if n not in out and (n not in self.pg.get("looks", {}) or n in mine + tpl + base or self._kind_of(n) == kind):
                out.append(n)
        return out

    def _kind_of(self, name):
        return (self.pg.get("looks", {}).get(name) or {}).get("type") or (self.tlooks.get(name) or {}).get("type") or "paragraph"

    def tag_menu(self, i, act=None):
        """A column's tag: what it is, its style, its place in the order (and for the source, where it goes)."""
        h = self.book["headers"][i]
        t = self.pg["tags"].get(h, "skip")
        m = QMenu(self)
        m.addSection(f"{h}: this column is")
        for k, lab in WB.TAGS:
            a = m.addAction(lab); a.setCheckable(True); a.setChecked(k == t); a.setData(("tag", k))
        if t not in ("skip", "heading"):
            sm = m.addMenu(f"Its style: {self.pg['styles'].get(t, '')}")
            for n in self._style_names("paragraph"):
                a = sm.addAction(n); a.setCheckable(True); a.setChecked(n == self.pg["styles"].get(t)); a.setData(("style", n))
            sm.addSeparator(); a = sm.addAction("New paragraph style..."); a.setData(("newstyle", "paragraph"))
            order = WB.tag_order(self.pg)
            m.addSection(f"Order in the row: {order.index(t) + 1} of {len(order)}" if t in order else "Order in the row")
            a = m.addAction("Earlier"); a.setData(("earlier", None)); a.setEnabled(t in order and order.index(t) > 1)
            a = m.addAction("Later"); a.setData(("later", None)); a.setEnabled(t in order and order.index(t) < len(order) - 1)
        if t == "source":
            src = self.pg["source"]
            m.addSection("Where the source goes")
            a = m.addAction("Its own line"); a.setCheckable(True); a.setChecked(src.get("place") == "line"); a.setData(("place", "line"))
            a = m.addAction(f"At the start of the text when shorter than {src.get('limit') or 40} characters")
            a.setCheckable(True); a.setChecked(src.get("place") == "inline"); a.setData(("place", "inline"))
            a = m.addAction("Change the length..."); a.setData(("limit", None))
            cm = m.addMenu(f"At the start: {src.get('char') or WB.SOURCE_CHAR}")
            for n in self._style_names("character"):
                a = cm.addAction(n); a.setCheckable(True); a.setChecked(n == src.get("char")); a.setData(("srcchar", n))
            cm.addSeparator(); a = cm.addAction("New character style..."); a.setData(("newsrcchar", None))
        act = act if act is not None else m.exec(QCursor.pos())
        if act is None:
            return None
        what, val = act.data() if isinstance(act, QAction) else act
        if what == "tag":
            self.pg["tags"][h] = val
        elif what == "style":
            self.pg["styles"][t] = val
        elif what == "newstyle":
            n = self.new_style("paragraph")
            if not n:
                return None
            self.pg["styles"][t] = n
        elif what in ("earlier", "later"):
            o = WB.tag_order(self.pg)
            WB.move(self.pg, t, o.index(t) + (-1 if what == "earlier" else 1))
        elif what == "place":
            self.pg["source"]["place"] = val
        elif what == "limit":
            n, ok = QInputDialog.getInt(self, "The source", "At the start of the text when shorter than (characters):",
                                        int(self.pg["source"].get("limit") or 40), 1, 400)
            if not ok:
                return None
            self.pg["source"]["limit"] = n
        elif what == "srcchar":
            self.pg["source"]["char"] = val
        elif what == "newsrcchar":
            n = self.new_style("character")
            if not n:
                return None
            self.pg["source"]["char"] = n
        self.redraw()
        return what

    def text_menu(self, i, lk, act=None):
        """Text that looks like this in this column: its character style, its own paragraph, or left out."""
        h = self.book["headers"][i]
        k = WB.key(h, lk)
        ch = self.pg["chars"].get(k, "")
        own = self.pg["own"].get(k)
        m = QMenu(self)
        m.addSection(f"Text in {OX.look_words(lk)} in {h}")
        a = m.addAction("No character style (the column's own text)"); a.setCheckable(True); a.setChecked(ch == "" and not own); a.setData(("char", ""))
        for n in self._style_names("character"):
            a = m.addAction(n); a.setCheckable(True); a.setChecked(n == ch and not own); a.setData(("char", n))
        a = m.addAction("New character style..."); a.setData(("newchar", None))
        m.addSeparator()
        om = m.addMenu("Its own paragraph, after the...")
        for t in WB.tag_order(self.pg):
            if t == "heading":
                continue
            a = om.addAction(WB.TAG[t]); a.setCheckable(True); a.setChecked(own == t); a.setData(("own", t))
        if own:
            a = m.addAction("Back inside its cell"); a.setData(("inside", None))
        a = m.addAction("Leave this text out"); a.setCheckable(True); a.setChecked(ch == "-"); a.setData(("char", "-"))
        act = act if act is not None else m.exec(QCursor.pos())
        if act is None:
            return None
        what, val = act.data() if isinstance(act, QAction) else act
        if what == "char":
            self.pg["chars"][k] = val; self.pg["own"].pop(k, None)
        elif what == "newchar":
            n = self.new_style("character")
            if not n:
                return None
            self.pg["chars"][k] = n; self.pg["own"].pop(k, None)
        elif what == "own":
            self.pg["own"][k] = val
            if self.pg["chars"].get(k) == "-":
                self.pg["chars"][k] = ""
        elif what == "inside":
            self.pg["own"].pop(k, None)
        self.redraw()
        return what

    # ------------------------------------------------------------ the right: the page
    def right_click(self, href, act=None):
        if not href.startswith("para:"):
            return None
        n = int(href.split(":")[1])
        p = self.paras[n]
        self.sel = ("para", n); self.redraw()
        m = QMenu(self)
        a = m.addAction("Find it in the workbook"); a.setData(("find", None))
        if p["tag"] != "heading":
            order = WB.tag_order(self.pg, p["section"])
            m.addSection(f"{WB.TAG[p['tag']]}: its place in the row")
            for where, lab in (("earlier", "Earlier, in every section"), ("later", "Later, in every section"),
                               ("earlier1", f"Earlier, in {p['section'] or 'this section'} only"),
                               ("later1", f"Later, in {p['section'] or 'this section'} only")):
                a = m.addAction(lab); a.setData((where, None))
                if p["tag"] in order:
                    i = order.index(p["tag"])
                    a.setEnabled(i > 1 if where.startswith("earlier") else i < len(order) - 1)
            sm = m.addMenu(f"Its style: {p['style']}")
            for nm in self._style_names("paragraph"):
                a = sm.addAction(nm); a.setCheckable(True); a.setChecked(nm == p["style"]); a.setData(("style", nm))
        if p["section"] in self.pg["sections"]:
            a = m.addAction(f"Back to every section ({p['section']})"); a.setData(("back", None))
        act = act if act is not None else m.exec(QCursor.pos())
        if act is None:
            return None
        what, val = act.data() if isinstance(act, QAction) else act
        if what == "find":
            self.find(p)
            return what
        if what in ("earlier", "later", "earlier1", "later1"):
            one = what.endswith("1")
            order = WB.tag_order(self.pg, p["section"] if one else "")
            i = order.index(p["tag"]) if p["tag"] in order else len(order)
            WB.move(self.pg, p["tag"], i + (-1 if what.startswith("earlier") else 1), section=p["section"] if one else None)
        elif what == "style":
            self.pg["styles"][p["tag"]] = val
        elif what == "back":
            WB.back_to_every(self.pg, p["section"])
        self.redraw()
        return what

    def find(self, p):
        """The paragraph's text in the workbook: its column (or its look), scrolled to its row."""
        i = p.get("col", -1)
        if i is not None and i >= 0:
            h = self.book["headers"][i]
            r = next((r for r in self.book["rows"] if r["row"] == p["row"]), None)
            lk = next((lk for _t, lk in (r["cells"][i] if r and i < len(r["cells"]) else []) if WB.key(h, lk) in self.pg["chars"]), None)
            self.sel = ("look", i, lk) if lk else ("col", i)
        self.draw_left()
        self.left.scrollToAnchor(f"r{p['row']}")
        return self.sel

    # ------------------------------------------------------------ styles
    def new_style(self, kind, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "A new style", ("Character" if kind == "character" else "Paragraph") + " style name:")
            if not ok:
                return None
        name = " ".join(str(name).split())[:60]
        if not name:
            return None
        self.pg.setdefault("looks", {}).setdefault(name, {"hidden": True})["type"] = kind
        return name

    def edit_style(self, name, kind, value=None):
        lk = self.look(name)
        if value is None:
            dlg = StyleDialog(self, name, kind, lk, name in self.tlooks)
            if dlg.exec() != QDialog.Accepted:
                return None
            value = dlg.value()
        self.pg.setdefault("looks", {})[name] = dict(value, type=kind)
        self.redraw()
        return self.pg["looks"][name]

    # ------------------------------------------------------------ commands
    def pick_template(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "The template the setup is written on", os.path.dirname(self.path),
                                                  "Word template or document (*.dotx *.dotm *.docx)")
            if not path:
                return None
        self.pg["template"] = path
        self.tlooks = WB.template_looks(path)
        self.redraw()
        return path

    def save_layout(self):
        return WB.save(self.cfg, self.layout_name, self.pg)

    def save_as(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "Save the layout", "A name for this workbook's layout:", text=self.layout_name)
            if not ok:
                return None
        name = " ".join(str(name).split())
        if not name:
            return None
        OL.from_profile(self.cfg, name, self.profile)
        self.layout_name = name
        self.save_layout()
        self.host.toast(f"Saved: {name}")
        self.redraw()
        return name

    def every_section(self):
        n = len(self.pg["sections"])
        self.pg["sections"] = {}
        self.redraw()
        return n

    def make(self, out_path=None):
        """The page as a Word file on the template; the settings kept with the layout. Returns the path."""
        if out_path is None:
            folder = os.path.dirname(self.path)
            stem = os.path.splitext(os.path.basename(self.path))[0]
            out_path, _ = QFileDialog.getSaveFileName(self, "The setup", os.path.join(folder, f"{stem} setup.docx"), "Word (*.docx)")
            if not out_path:
                return None
        try:
            WB.write(self.paras, self.pg, out_path, template=self.pg.get("template") or None)
        except Exception as e:                             # noqa: BLE001  a template it cannot read, a file open in Word
            diag.swallowed()
            self.host.status(f"The setup was not written: {e}. Close it in Word if it is open, or pick another template.")
            return None
        self.save_layout()
        diag.activity("setup_from_workbook_made", paragraphs=len(self.paras))
        self.host.toast(f"Made: {os.path.basename(out_path)}")
        self.host.status(f"The setup is in {out_path}. Its styles are set as on this page; the layout keeps them for next time.")
        return out_path

    def use(self, accept=True):
        """3.71.0's Use this structure: the sections and requirements into the effort (the page's settings kept too)."""
        from .outlineimport import import_outline
        self.save_layout()
        n = import_outline(self.page, self.path, profile=self.profile, accept=accept)
        if n is not None:
            self.accept()
        return n

    def as_list(self):
        from .outlineimport import OutlineImport
        dlg = OutlineImport(self.page, self.path)
        dlg.profile = self.profile; dlg.fill_columns()
        used = dlg.exec() == QDialog.Accepted
        self.profile = dlg.profile                         # its picks are this page's too
        self.redraw()
        return self.use() if used else dlg


def open_page(page, path=None):
    """Setup > Bring in a file with a workbook (3.91.0): the two panes. Returns the window."""
    if path is None:
        path, _ = QFileDialog.getOpenFileName(page, "The outline workbook", "", "Excel (*.xlsx *.xlsm)")
        if not path:
            return None
    try:
        dlg = WorkbookPage(page, path)
    except Exception:                                      # noqa: BLE001  not a workbook it can read
        diag.swallowed()
        page.host.status("That file does not read as an Excel workbook.")
        return None
    page.workbook_page = dlg
    dlg.show()
    return dlg
