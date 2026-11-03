"""Document parts (3.26.0): each part of the document in one place, over the same settings as the other menus.

Cover, Front matter, Response, Appendices and Back cover each show what applies to that part: where it starts and how
its pages are numbered, its header and footer (tab stops, a table, or a Quick Part kept as built), its cover page, its
caption scheme and table of contents, and what it shares with every part (page size and margins, base fonts, styles).
Nothing is copied: a change here is the same value the Pages and Numbering menus show. Each part has a drawn preview,
Open a sample in Word, and Save this part as a design (the template library's Part designs) to use on any volume.
"""
import copy
import os
import re

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QInputDialog, QLineEdit, QListWidget,
                               QSpinBox, QVBoxLayout, QWidget)

import diag
import numtext as NT
import prodrules as PRL
from partdesigns import part_of, design_of, apply_design  # noqa: F401
from prodengine.pe import rules as PR
from . import design as D

PARTS = [("part_cover", "cover", "Cover"), ("part_front", "front", "Front matter"), ("part_body", "body", "Response"),
         ("part_appendix", "appendix", "Appendices"), ("part_backer", "backer", "Back cover")]
PART_OF = {s: k for s, k, _t in PARTS}
FMT = [("", "No page numbers"), ("decimal", "1, 2, 3"), ("lowerRoman", "i, ii, iii"), ("upperRoman", "I, II, III"),
       ("lowerLetter", "a, b, c"), ("upperLetter", "A, B, C")]
RESTART = [("part", "At the start of this part"), ("each", "At each chapter"), ("never", "Continue from before")]
ROMAN = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
SAMPLE = {"volume_name": "Volume I Technical", "solicitation": "Solicitation number", "company": "Company",
          "chapter": "Chapter title", "classification": "", "project": "Project"}


def _roman(n):
    out = ""
    for v, s in ROMAN:
        while n >= v:
            out += s; n -= v
    return out


def page_number(numbers, n=1, chapter=1):
    """How page n of a part reads: 'ii', '2-1', 'A-1' (the numbers of a pagination part)."""
    if not numbers or not numbers.get("fmt"):
        return ""
    f = numbers["fmt"]
    k = n + int(numbers.get("start_at") or 1) - 1
    s = {"decimal": str(k), "lowerRoman": _roman(k), "upperRoman": _roman(k).upper(),
         "lowerLetter": chr(96 + min(k, 26)), "upperLetter": chr(64 + min(k, 26))}.get(f, str(k))
    if numbers.get("chapter_level"):
        lvl = int(numbers["chapter_level"])
        ch = chr(64 + chapter) if lvl >= 7 else str(chapter)
        s = f"{ch}{PR.SEPARATORS.get(numbers.get('separator', 'hyphen'), '-')}{s}"
    return s


def token_text(text, work, numbers=None):
    """A header or footer slot as it will read: tokens filled with the volume's values or a sample."""
    v = work.get("variables") or {}

    def one(m):
        k = m.group(1)
        if k == "page":
            return page_number(numbers, 1) or "1"
        if k == "pages":
            return "12"
        if v.get(k):
            return str(v[k])
        for f in work.get("fill_ins") or []:
            if f.get("key") == k:
                return f.get("value") or f.get("name") or k
        return SAMPLE.get(k, k)
    return re.sub(r"\{(\w+)\}", one, text or "")


# ------------------------------------------------------------------ the drawn page
class PartPreview(QWidget):
    """One page of the part: its margins, header and footer (as tab stops, a table, or a kept design), the page number
    as it reads, and what the page holds."""

    def __init__(self, page, key):
        super().__init__()
        self.page, self.key = page, key
        self.setMinimumSize(300, 380)

    def paintEvent(self, _e):
        work = self.page.work or {}
        tk = D.tokens()
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        ps = (work.get("page_setups") or {}).get("portrait") or {}
        pw, ph = float(ps.get("w") or 8.5), float(ps.get("h") or 11)
        scale = min((self.width() - 20) / pw, (self.height() - 20) / ph)
        x0, y0 = (self.width() - pw * scale) / 2, 10
        page = QRectF(x0, y0, pw * scale, ph * scale)
        p.fillRect(page, QColor("#ffffff")); p.setPen(QPen(QColor(tk["border"]), 1)); p.drawRect(page)
        var = work.get("variables") or {}

        def num(x, d):
            try:
                return float(PR.value(work, x) if isinstance(x, str) else x)
            except (TypeError, ValueError):
                return d
        mt, mb = num(ps.get("top", var.get("margin_top")), 1), num(ps.get("bottom", var.get("margin_bottom")), 1)
        ml, mr = num(ps.get("left", var.get("margin_left")), 1), num(ps.get("right", var.get("margin_right")), 1)
        body = QRectF(x0 + ml * scale, y0 + mt * scale, (pw - ml - mr) * scale, (ph - mt - mb) * scale)
        dash = QPen(QColor("#c7cdd8"), 1, Qt.DashLine); p.setPen(dash); p.drawRect(body)
        part = part_of(work, self.key) or {}
        numbers = part.get("numbers")
        lay = (work.get("hf_layouts") or {}).get(self.key) or {}
        des = (work.get("hf_designs") or {}).get(self.key) or {}
        small = QFont(self.font()); small.setPointSizeF(7)
        p.setFont(small); p.setPen(QColor("#1f2937"))
        for kind, top in (("header", y0 + 0.45 * scale), ("footer", y0 + (ph - 0.75) * scale)):
            band = QRectF(body.left(), top, body.width(), 0.3 * scale)
            if des.get(kind):
                p.setPen(QColor("#0f766e")); p.drawText(band, Qt.AlignCenter, f"{kind.title()}: kept design (as built)")
                p.setPen(QColor("#1f2937")); continue
            spec = lay.get(kind) or {}
            tbl = (spec.get("table") or {}).get("widths_in") or []
            texts = {s: token_text(spec.get(s, ""), work, numbers) for s in ("left", "center", "right")}
            if kind == "footer" and spec.get("marking") and var.get("marking"):
                p.drawText(QRectF(body.left(), top - 0.25 * scale, body.width(), 0.25 * scale), Qt.AlignCenter, str(var["marking"]))
            if tbl:
                slots = {1: ["center"], 2: ["left", "right"]}.get(len(tbl), ["left", "center", "right"])
                xx = band.left()
                for i, wi in enumerate(tbl):
                    cell = QRectF(xx, band.top(), wi * scale, band.height())
                    p.setPen(QPen(QColor("#9aa3b2"), 0.8, Qt.DotLine)); p.drawRect(cell); p.setPen(QColor("#1f2937"))
                    s = slots[i] if i < len(slots) else ""
                    p.drawText(cell.adjusted(3, 0, -3, 0), {"left": Qt.AlignLeft, "center": Qt.AlignHCenter, "right": Qt.AlignRight}.get(s, Qt.AlignLeft)
                               | Qt.AlignVCenter, texts.get(s, ""))
                    xx += wi * scale
            else:
                for s, al in (("left", Qt.AlignLeft), ("center", Qt.AlignHCenter), ("right", Qt.AlignRight)):
                    p.drawText(band, al | Qt.AlignVCenter, texts[s])
            if kind == "header" and spec.get("rule_below"):
                p.drawLine(band.bottomLeft(), band.bottomRight())
        big = QFont(self.font()); big.setPointSizeF(9); big.setBold(True)
        p.setFont(big)
        inner = body.adjusted(6, 8, -6, -8)
        what = {"cover": "Cover", "front": "TABLE OF CONTENTS", "body": "", "appendix": "", "backer": "Back cover"}[self.key]
        if self.key in ("cover", "backer"):
            f = (work.get("page_parts") or {}).get(self.key)
            p.drawText(inner, Qt.AlignCenter | Qt.TextWordWrap, f"{what}\n{'kept as built: ' + f if f else 'the Stationkeeper base page'}")
        elif self.key == "front":
            p.drawText(inner, Qt.AlignTop | Qt.AlignHCenter, what)
            p.setFont(small)
            for i, (st, lv) in enumerate((work.get("toc") or {}).get("levels") or []):
                if i > 6:
                    break
                p.drawText(QRectF(inner.left() + (int(lv) - 1) * 12, inner.top() + 22 + i * 13, inner.width() - (int(lv) - 1) * 12, 12),
                           Qt.AlignLeft, f"{st} ........................ {page_number(numbers, i + 1) or i + 1}")
        else:
            hn = work.get("heading_numbering") or {}
            lv = hn.get("levels") or []
            fm = [x.get("fmt") or "decimal" for x in lv]
            want = "Heading 7" if self.key == "appendix" else "Heading 1"
            lvl = next((x for x in lv if x.get("style") == want), None)
            numtxt = NT.show(lvl.get("text") or "", fm) if (lvl and hn.get("on")) else ("Appendix A" if self.key == "appendix" else "1")
            p.drawText(QRectF(inner.left(), inner.top(), inner.width(), 18), Qt.AlignLeft, f"{numtxt}  {'Appendix title' if self.key == 'appendix' else 'Chapter title'}")
            p.setPen(QColor("#9aa3b2"))
            for i in range(10):
                yy = inner.top() + 26 + i * 9
                p.drawLine(int(inner.left()), int(yy), int(inner.right() - (40 if i % 4 == 3 else 0)), int(yy))
            cap = next((c for c in work.get("captions") or [] if c.get("part") == self.key), None)
            if cap:
                p.setPen(QColor("#1f2937")); p.setFont(small)
                ch = "A" if self.key == "appendix" else "1"
                n = (f"{ch}{cap.get('separator', '-')}1" if cap.get("chapter_level") else "1")
                p.drawText(QRectF(inner.left(), inner.top() + 125, inner.width(), 12), Qt.AlignLeft, f"{cap.get('label', 'Table')} {n}. Caption")
        p.setFont(small); p.setPen(QColor(tk["muted"]))
        pn = page_number(numbers, 1)
        p.drawText(QRectF(x0, page.bottom() - 14, page.width() - 4, 12), Qt.AlignRight, f"page reads: {pn}" if pn else "no page number")
        p.end()


# ------------------------------------------------------------------ building a part's page
def build(page, v, section):
    key = PART_OF[section]
    st = {"key": key, "w": {}}
    page.part_ui = getattr(page, "part_ui", {})
    page.part_ui[key] = st
    top = QHBoxLayout(); v.addLayout(top)
    left = QVBoxLayout(); top.addLayout(left, 3)
    prev = PartPreview(page, key); st["preview"] = prev
    pv = QVBoxLayout(); pv.addWidget(prev)
    bb = QHBoxLayout()
    bb.addWidget(D.button("Open a sample in Word", None, lambda: open_sample(page, key),
                          "A sample template with every part (this one included) in the Samples folder, opened in Word"))
    pv.addLayout(bb)
    bb2 = QHBoxLayout()
    bb2.addWidget(D.button("Save this part as a design...", None, lambda: save_design(page, key),
                           "Its numbering, header and footer, kept designs, cover page and captions, kept in the template library"))
    bb2.addWidget(D.button("Use a saved design...", None, lambda: use_design(page, key), "A part design from the template library"))
    pv.addLayout(bb2)
    top.addLayout(pv, 2)
    w = st["w"]
    # where it starts and how it is numbered
    c = D.Card("Where it starts and how it is numbered", "This part only. The same values as Pages > Pagination and covers.")
    f = QFormLayout(); c.body.addLayout(f); left.addWidget(c)
    w["start"] = QLineEdit(); w["start"].setPlaceholderText("The style its first paragraph has (for example Heading 1)")
    if key in ("cover", "backer"):
        w["start"].setEnabled(False)
        w["start"].setPlaceholderText("The first section" if key == "cover" else "The last section, starting with one of its styles")
    f.addRow("Starts at the style", w["start"])
    w["fmt"] = QComboBox()
    for k, t in FMT:
        w["fmt"].addItem(t, k)
    f.addRow("Page numbers", w["fmt"])
    w["restart"] = QComboBox()
    for k, t in RESTART:
        w["restart"].addItem(t, k)
    f.addRow("Numbers restart", w["restart"])
    w["start_at"] = QSpinBox(); w["start_at"].setRange(1, 999); f.addRow("Starting at", w["start_at"])
    w["chapter_level"] = QSpinBox(); w["chapter_level"].setRange(0, 9); w["chapter_level"].setSpecialValueText("none (page only)")
    f.addRow("Chapter number from heading level", w["chapter_level"])
    w["separator"] = QComboBox()
    for k, val in PR.SEPARATORS.items():
        w["separator"].addItem(f"{val}  ({k})", k)
    f.addRow("Between chapter and page", w["separator"])
    w["linked"] = QCheckBox("Same header and footer as the part before"); f.addRow("", w["linked"])
    # header and footer
    c2 = D.Card("Header and footer", "This part only. Word's tab stops, a table at inch widths (one width: center; two: left "
                "and right; three: all three), or a Quick Part kept as built. Tokens: {volume_name} {solicitation} {company} "
                "{page} {pages} {chapter} and your fields as {key}.")
    f2 = QFormLayout(); c2.body.addLayout(f2); left.addWidget(c2)
    for kind in ("header", "footer"):
        row = QHBoxLayout()
        for s in ("left", "center", "right"):
            e = QLineEdit(); e.setPlaceholderText(s.title()); w[f"{kind}_{s}"] = e; row.addWidget(e)
        holder = QWidget(); holder.setLayout(row); row.setContentsMargins(0, 0, 0, 0)
        f2.addRow(kind.title(), holder)
        tw = QLineEdit(); tw.setPlaceholderText("Blank: tab stops. Column widths in inches for a table: 4.5, 2"); w[f"{kind}_table"] = tw
        f2.addRow(f"{kind.title()} as a table", tw)
    w["rule_below"] = QCheckBox("A rule under the header"); f2.addRow("", w["rule_below"])
    w["marking"] = QCheckBox("The restriction marking in the footer"); f2.addRow("", w["marking"])
    w["borders"] = QComboBox()
    for k, t in (("none", "None"), ("bottom", "A line under"), ("grid", "Grid")):
        w["borders"].addItem(t, k)
    f2.addRow("Table borders", w["borders"])
    qh = QHBoxLayout()
    qh.addWidget(D.button("Use a Quick Part as the header...", None, lambda: _qp(page, key, "header")))
    qh.addWidget(D.button("Use a Quick Part as the footer...", None, lambda: _qp(page, key, "footer")))
    qh.addWidget(D.button("Clear this part's kept design", "ghost", lambda: clear_design(page, key)))
    qh.addStretch(1); c2.body.addLayout(qh)
    st["design_lab"] = D.label("", "muted"); c2.body.addWidget(st["design_lab"])
    # the part's own pages
    if key in ("cover", "backer"):
        c3 = D.Card("The page", "Kept exactly as built (pictures, tables over them, text boxes and placeholders). Import one from "
                    "a template or document, or take one from the template library.")
        left.addWidget(c3)
        st["page_lab"] = D.label("", None); c3.body.addWidget(st["page_lab"])
        ph = QHBoxLayout()
        ph.addWidget(D.button("Import from a file...", None, lambda: page.import_file(section="pages")))
        ph.addWidget(D.button("Template library...", None, lambda: page.library()))
        ph.addWidget(D.button("Clear", "ghost", lambda: clear_page(page, key)))
        ph.addStretch(1); c3.body.addLayout(ph)
    if key == "front":
        c3 = D.Card("Table of contents and lists", "The TOC's levels and switches and the lists of tables and figures this part "
                    "carries. Change them in Pages > Table of contents.")
        left.addWidget(c3)
        st["toc_lab"] = D.label("", None); c3.body.addWidget(st["toc_lab"])
        c3.body.addWidget(D.button("Go to Table of contents", "ghost", lambda: page.nav.setCurrentRow(page.section_index("toc"))))
        c4 = D.Card("Title page and acronym list", "The title page is the cover's companion: its text comes from Fields on the "
                    "cover. The acronym list is made from the effort's acronyms (Acronyms) when the volume is exported.")
        left.addWidget(c4)
    if key in ("body", "appendix"):
        c3 = D.Card("Captions in this part", "The caption rules for this part. Change them in Numbering > Captions.")
        left.addWidget(c3)
        st["cap_lab"] = D.label("", None); c3.body.addWidget(st["cap_lab"])
        c3.body.addWidget(D.button("Go to Captions", "ghost", lambda: page.nav.setCurrentRow(page.section_index("captions"))))
    c5 = D.Card("Shared with every part", "Word applies these to the whole document; change them in their own menus.")
    left.addWidget(c5)
    st["shared_lab"] = D.label("", None); c5.body.addWidget(st["shared_lab"])
    sh = QHBoxLayout()
    sh.addWidget(D.button("Page sizes and margins", "ghost", lambda: page.nav.setCurrentRow(page.section_index("setups"))))
    sh.addWidget(D.button("Base fonts and sizes", "ghost", lambda: page.nav.setCurrentRow(page.section_index("variables"))))
    sh.addWidget(D.button("Styles", "ghost", lambda: page.nav.setCurrentRow(page.section_index("styledefs"))))
    sh.addStretch(1); c5.body.addLayout(sh)
    for name, wd in w.items():
        if isinstance(wd, QLineEdit):
            wd.textEdited.connect(lambda _t, k=key: write(page, k))
        elif isinstance(wd, QComboBox):
            wd.currentIndexChanged.connect(lambda _i, k=key: write(page, k))
        elif isinstance(wd, QSpinBox):
            wd.valueChanged.connect(lambda _v, k=key: write(page, k))
        elif isinstance(wd, QCheckBox):
            wd.toggled.connect(lambda _v, k=key: write(page, k))


def _widths(text):
    out = []
    for x in (text or "").split(","):
        try:
            out.append(round(float(x.strip()), 3))
        except ValueError:
            pass
    return out


def fill(page, key):
    """The part's widgets from what is being edited."""
    st = (getattr(page, "part_ui", {}) or {}).get(key)
    if not st or getattr(page, "_part_writing", None) == key:
        return
    work = page.work or {}
    w = st["w"]
    part = part_of(work, key) or {}
    n = part.get("numbers") or {}
    lay = (work.get("hf_layouts") or {}).get(key) or {}
    h, ft = lay.get("header") or {}, lay.get("footer") or {}
    for wd in w.values():
        wd.blockSignals(True)
    s = part.get("starts") or {}
    w["start"].setText(s.get("style") or ", ".join(s.get("styles") or []))
    w["fmt"].setCurrentIndex(max(0, w["fmt"].findData(n.get("fmt") or "")))
    w["restart"].setCurrentIndex(max(0, w["restart"].findData(n.get("restart") or "part")))
    w["start_at"].setValue(int(n.get("start_at") or 1))
    w["chapter_level"].setValue(int(n.get("chapter_level") or 0))
    w["separator"].setCurrentIndex(max(0, w["separator"].findData(n.get("separator") or "hyphen")))
    w["linked"].setChecked(bool(part.get("linked")))
    for kind, spec in (("header", h), ("footer", ft)):
        for sl in ("left", "center", "right"):
            w[f"{kind}_{sl}"].setText(spec.get(sl, ""))
        w[f"{kind}_table"].setText(", ".join(f"{x:g}" for x in (spec.get("table") or {}).get("widths_in") or []))
    w["rule_below"].setChecked(bool(h.get("rule_below")))
    w["marking"].setChecked(bool(ft.get("marking")))
    w["borders"].setCurrentIndex(max(0, w["borders"].findData((h.get("table") or ft.get("table") or {}).get("borders", "none"))))
    for wd in w.values():
        wd.blockSignals(False)
    for k in ("fmt", "restart", "start_at", "chapter_level", "separator"):
        w[k].setEnabled(key not in ("cover", "backer") or k == "fmt")
    des = (work.get("hf_designs") or {}).get(key) or {}
    st["design_lab"].setText(("Kept design in use (it replaces the layout above): " + ", ".join(k for k in ("header", "footer") if des.get(k)))
                             if des else "No kept design: the layout above is used.")
    if "page_lab" in st:
        f = (work.get("page_parts") or {}).get(key)
        st["page_lab"].setText(f"{f} (kept as built)" if f else "The Stationkeeper base page.")
    if "toc_lab" in st:
        toc = work.get("toc") or {}
        st["toc_lab"].setText("Levels: " + ", ".join(f"{a} ({b})" for a, b in toc.get("levels") or []) + ". Lists: "
                              + (", ".join(x.get("title", "") for x in toc.get("lists") or []) or "none") + ".")
    if "cap_lab" in st:
        caps = [c for c in work.get("captions") or [] if c.get("part") == key]
        st["cap_lab"].setText("; ".join(f"{c.get('label')} ({c.get('position', 'above')}, "
                                        f"{'chapter level ' + str(c['chapter_level']) if c.get('chapter_level') else 'sequence only'})"
                                        for c in caps) or "No caption rule for this part.")
    var = work.get("variables") or {}
    styles = [x for x in [s.get("style")] + list(s.get("styles") or []) if x]
    st["shared_lab"].setText(f"Margins {var.get('margin_top', '')} / {var.get('margin_bottom', '')} / {var.get('margin_left', '')} / "
                             f"{var.get('margin_right', '')} in (top / bottom / left / right), paper {var.get('paper', 'letter')}. "
                             f"Body {var.get('body_font', '')} {var.get('body_size', '')} pt; tables {var.get('table_font', '')} "
                             f"{var.get('table_size', '')} pt." + (f" This part starts with {', '.join(styles)}." if styles else ""))
    st["preview"].update()


def fill_all(page):
    for _s, key, _t in PARTS:
        fill(page, key)


def write(page, key):
    """The part's widgets into what is being edited (the same values the other menus show)."""
    st = page.part_ui[key]
    w = st["w"]
    work = page.work
    part = part_of(work, key)
    if part is not None:
        if key not in ("cover", "backer"):
            stl = w["start"].text().strip()
            if stl:
                part["starts"] = {"style": stl}
        fmt = w["fmt"].currentData()
        if fmt:
            n = {"fmt": fmt, "restart": w["restart"].currentData() or "part", "start_at": w["start_at"].value(),
                 "chapter_level": w["chapter_level"].value() or None}
            if n["chapter_level"]:
                n["separator"] = w["separator"].currentData() or "hyphen"
            part["numbers"] = n
        else:
            part["numbers"] = None
        part["linked"] = w["linked"].isChecked()
    lay = work.setdefault("hf_layouts", {}).setdefault(key, {})
    for kind in ("header", "footer"):
        spec = {sl: w[f"{kind}_{sl}"].text() for sl in ("left", "center", "right") if w[f"{kind}_{sl}"].text()}
        ws = _widths(w[f"{kind}_table"].text())
        if ws:
            spec["table"] = {"widths_in": ws, "borders": w["borders"].currentData() or "none"}
        if kind == "header" and w["rule_below"].isChecked():
            spec["rule_below"] = True
        if kind == "footer" and w["marking"].isChecked():
            spec["marking"] = True
        lay[kind] = spec
    page._part_writing = key
    try:
        page.load_tables()
        page.changed()
    finally:
        page._part_writing = None
    st["preview"].update()


def _qp(page, key, kind):
    entries = [e for e in ((page.work.get("quick_parts") or {}).get("entries") or [])
               if os.path.isfile(os.path.join(page.parts_dir(), e.get("source") or ""))]
    if not entries:
        page.host.status("Add Quick Parts first (Content > Quick Parts), then use one here.")
        return None
    names = [f"{e.get('category') or 'no category'} / {e['name']}" for e in entries]
    pick, ok = QInputDialog.getItem(page, f"Use a Quick Part as the {kind}", f"The Quick Part for this part's {kind}:", names, 0, False)
    if not ok:
        return None
    r = page.hf_from_quick_part(key, kind, entries[names.index(pick)]["name"])
    fill(page, key)
    return r


def clear_design(page, key):
    (page.work.get("hf_designs") or {}).pop(key, None)
    page.show_hf_designs(); page.changed(); fill(page, key)


def clear_page(page, key):
    (page.work.get("page_parts") or {}).pop(key, None)
    page.show_parts(); page.changed(); fill(page, key)


# ------------------------------------------------------------------ part designs in the template library
def save_design(page, key, name=None):
    import templatelib as TL
    if name is None:
        title = dict((k, t) for _s, k, t in PARTS)[key]
        name, ok = QInputDialog.getText(page, "Save this part as a design", f"A name for this {title.lower()} design (for example: "
                                        f"Space Force {title.lower()}):")
        if not ok or not name.strip():
            return None
    lib = TL.Library(page.host.config_dir)
    v = design_of(page.work, key)
    if v["page_file"]:
        src = os.path.join(page.parts_dir(), v["page_file"])
        if os.path.isfile(src):
            v["page_file"] = lib.keep_file(src, v["page_file"])
        else:
            v["page_file"] = ""
    item, state = lib.add("part", " ".join(name.split()), v, tags={"use": []}, summary=f"{key}: numbering, header and footer"
                          + (", kept design" if v["hf_design"] else "") + (", page" if v["page_file"] else ""))
    diag.activity("part_design_saved")
    page.host.status(f"Saved in the template library: {item['name']} ({state}).")
    return item


def use_design(page, key, iid=None):
    import templatelib as TL
    lib = TL.Library(page.host.config_dir)
    items = [i for i in lib.items if i.get("kind") == "part"]
    if not items:
        page.host.status("No part designs yet: Save this part as a design... keeps one.")
        return None
    if iid is None:
        names = [f"{i['name']} (from {lib.values(i).get('part', '?')})" for i in items]
        pick, ok = QInputDialog.getItem(page, "Use a saved design", "The part design to use on this part:", names, 0, False)
        if not ok:
            return None
        iid = items[names.index(pick)]["id"]
    said = TL.use_in_standard(lib, iid, page.work, category=key)
    page.after_library(said)
    fill(page, key)
    return said
