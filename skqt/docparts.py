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
_WORD_JOBS = {}                                       # 3.40.0: {page fingerprint: the thread Word draws it in}


class PartPreview(QWidget):
    """One page of the part: its margins, header and footer (as tab stops, a table, or a kept design), the page number
    as it reads, and what the page holds."""

    def __init__(self, page, key):
        super().__init__()
        self.page, self.key = page, key
        self.setMinimumSize(300, 380)

    # ------------------------------------------------------------ 3.40.0 Word draws the page
    def draw_word(self, p, rect, data):
        """Draw Word's picture of the page when one is kept; on a PC with Word, start drawing one (once) and repaint
        when it is ready. Returns True when Word's picture was drawn."""
        import wordpreview as WP
        if not data:
            return False
        png = WP.cached(self.page.parts_dir(), data)
        if png:
            from PySide6.QtGui import QImage
            img = QImage(png)
            if not img.isNull():
                p.drawImage(rect, img)
                p.setPen(QColor("#64748b")); f = QFont(self.font()); f.setPointSizeF(7); p.setFont(f)
                p.drawText(QRectF(rect.left(), rect.bottom() + 1, rect.width(), 10), Qt.AlignRight, "Drawn by Word")
                return True
        if WP.available():
            fp = WP.fingerprint(data)
            if fp not in _WORD_JOBS:
                import threading
                _WORD_JOBS[fp] = threading.Thread(target=WP.draw, args=(self.page.parts_dir(), data), daemon=True)
                _WORD_JOBS[fp].start()
            if _WORD_JOBS[fp].is_alive():
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1500, self.update)
        return False

    def sketch_note(self, p, rect):
        import wordpreview as WP
        p.setPen(QColor("#64748b")); f = QFont(self.font()); f.setPointSizeF(7); p.setFont(f)
        note = "Sketch: Word is drawing the exact page" if WP.available() else "Sketch: Word draws the exact page on a PC with Word"
        p.drawText(QRectF(rect.left(), rect.bottom() + 1, rect.width(), 10), Qt.AlignRight, note)

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
            if (spec.get("table") or {}).get("cells"):         # 3.42.0: a table built here, drawn cell by cell
                from .hfbuilder import draw_cells
                draw_cells(p, QRectF(band.left(), band.top() - (0.15 * scale if kind == "footer" else 0), band.width(), 0.45 * scale),
                           spec, work, text_width_in=max(1.0, pw - ml - mr))
                p.setFont(small); p.setPen(QColor("#1f2937"))
                continue
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
            path = os.path.join(self.page.parts_dir(), f) if f else ""
            drawn = False
            if path and os.path.isfile(path):                # 3.34.0: the kept page as it will look
                from .coverdraw import draw_page
                try:
                    with open(path, "rb") as fh:
                        data = fh.read()
                except OSError:
                    data = b""
                drawn = self.draw_word(p, page, data)        # 3.40.0: Word's own picture of the page, when there is one
                if not drawn and data:
                    drawn = draw_page(p, page, data, work)
                    if drawn:
                        self.sketch_note(p, page)
            if not drawn:
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
    th = QHBoxLayout()                                     # 3.42.0: built here as a table, logos and Rule 7's footer too
    th.addWidget(D.button("Build the header as a table...", None, lambda: build_table(page, key, "header"),
                          "Columns at inch widths, lines of words and fields, a logo; save it as a Quick Part"))
    th.addWidget(D.button("Build the footer as a table...", None, lambda: build_table(page, key, "footer"),
                          "Columns at inch widths, lines of words and fields, a logo; or Rule 7's footer"))
    th.addStretch(1); c2.body.addLayout(th)
    st["table_lab"] = D.label("", "muted"); c2.body.addWidget(st["table_lab"])
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
        ph.addWidget(D.button("Edit the layout...", "primary", lambda: edit_layout(page, key),
                              "A placed page: move or resize its pieces and set the text on the page"))
        ph.addWidget(D.button("Edit in Word", None, lambda: edit_in_word(page, key),
                              "A dated copy opens in Word; what you save is kept as a new version (the page before it stays)"))
        ph.addWidget(D.button("Clear", "ghost", lambda: clear_page(page, key)))
        ph.addStretch(1); c3.body.addLayout(ph)
        nh = QHBoxLayout()                                 # 3.34.0: built here, from a blank page or a saved layout
        nh.addWidget(D.button("New from a blank page...", None, lambda: new_page(page, key),
                              "A blank page in the standard's paper and margins: add a background picture and text blocks"))
        nh.addWidget(D.button("From a saved cover layout...", None, lambda: new_page(page, key, from_layout=True),
                              "A page built from a cover layout kept in the template library"))
        nh.addStretch(1); c3.body.addLayout(nh)
    if key == "cover":                                     # 3.34.0: the title page, the cover's companion
        c5 = D.Card("The title page", "A page of its own after the cover, built like a cover: a background picture and text "
                    "blocks that show the volume's fields. The structure's Title page element is replaced by it in Make templates.")
        left.addWidget(c5)
        st["title_lab"] = D.label("", None); c5.body.addWidget(st["title_lab"])
        th = QHBoxLayout()
        th.addWidget(D.button("New from a blank page...", None, lambda: new_page(page, "title")))
        th.addWidget(D.button("From a saved cover layout...", None, lambda: new_page(page, "title", from_layout=True)))
        th.addWidget(D.button("Edit the layout...", "primary", lambda: edit_layout(page, "title")))
        th.addWidget(D.button("Edit in Word", None, lambda: edit_in_word(page, "title"),
                              "A dated copy opens in Word; what you save is kept as a new version (the page before it stays)"))
        th.addWidget(D.button("Clear", "ghost", lambda: clear_page(page, "title")))
        th.addStretch(1); c5.body.addLayout(th)
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
    built = [k for k, spec in (("header", h), ("footer", ft)) if (spec.get("table") or {}).get("cells")]
    for kind in ("header", "footer"):                      # 3.42.0: a table built here replaces these boxes
        for sl in ("left", "center", "right", "table"):
            w[f"{kind}_{sl}"].setEnabled(kind not in built)
    st["table_lab"].setText(("Built as a table here: " + " and ".join(built) + " (Build ... as a table to change it)."
                             + (" The footer is Rule 7's." if "footer" in built and _is_r7(ft) else "")) if built else "")
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
        st["page_lab"].setText(f"{f}. {page_kind_text(page, f)}" if f else "The Stationkeeper base page.")
    if "title_lab" in st:
        f = (work.get("page_parts") or {}).get("title")
        st["title_lab"].setText(f"{f}. {page_kind_text(page, f)}" if f else "No title page: the structure's Title page element is a placeholder.")
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
        if ((lay.get(kind) or {}).get("table") or {}).get("cells"):
            continue                                       # 3.42.0: a table built here is changed in its builder only
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


def _is_r7(spec):
    import hfbuild as HB
    return HB.is_r7(spec)


def build_table(page, key, kind, run=True):
    """3.42.0: build this part's header or footer as a table (columns, lines, logos; Rule 7's footer)."""
    from .hfbuilder import HFBuilder
    dlg = HFBuilder(page, page.work, key, kind, page.parts_dir())
    page.hf_dialog = dlg
    if not run:
        return dlg
    if dlg.exec():
        finish_table(page, key, kind, dlg)
    return dlg


def finish_table(page, key, kind, dlg):
    """The builder's table into the part's layout; a kept design for the same header or footer gives way to it."""
    from .hfbuilder import apply
    apply(page.work, key, kind, dlg.result_spec())
    des = (page.work.get("hf_designs") or {}).get(key)
    if des:
        des.pop(kind, None); des.pop(kind + "_media", None)
        if not (des.get("header") or des.get("footer")):
            page.work["hf_designs"].pop(key, None)
    page._part_writing = key
    try:
        page.load_tables()
        page.changed()
    finally:
        page._part_writing = None
    if hasattr(page, "show_hf_designs"):
        page.show_hf_designs()
    fill(page, key)


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
    page.show_parts(); page.changed(); fill(page, "cover" if key == "title" else key)


def new_page(page, key, from_layout=False, layout_id=None, run=True):
    """3.34.0: a cover, title page or back cover built here: a blank page in the standard's paper and margins, or one
    built from a cover layout in the template library. Opens the layout editor on it; Save keeps it. Returns the dialog."""
    import coverbuild as CB
    import templatelib as TL
    from .coverview import CoverLayoutDialog
    if from_layout:
        lib = TL.Library(page.host.config_dir)
        if layout_id is None:
            items = sorted(lib.shelf("cover_design"), key=lambda i: lib.shown_name(i).casefold())
            if not items:
                page.host.status("No cover layout kept yet: Save as a cover layout... in the layout editor keeps one.")
                return None
            from PySide6.QtWidgets import QInputDialog
            names = [lib.shown_name(i) for i in items]
            nm, ok = QInputDialog.getItem(page, "From a saved cover layout", "Cover layout:", names, 0, False)
            if not ok:
                return None
            layout_id = items[names.index(nm)]["id"]
        design = lib.values(lib.get(layout_id)) or {}
        data = CB.from_design(design, page.work)
    else:
        data = CB.blank(page.work)
    d = CoverLayoutDialog(page, key, data=data)
    if run:
        d.exec()
    return d


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


def open_sample(page, key, open_it=True):
    """A sample template with every part (this one included) in the Samples folder, opened in Word on Windows."""
    import sys
    import prodtemplate as PT
    std = PRL.engine_ready(copy.deepcopy(page.work))
    std["name"] = f"Sample {dict((k, t) for _s, k, t in PARTS)[key]}"
    std["variables"].setdefault("volume_name", std["variables"].get("volume_name") or "Volume I Technical")
    try:
        job = PT.make(std, os.path.join(page.template_folder(), "Samples"), "", parts_dir=page.parts_dir())
    except Exception as e:  # noqa: BLE001
        diag.swallowed()
        page.host.status(f"The sample could not be made ({type(e).__name__}).")
        return None
    if open_it and sys.platform.startswith("win"):
        try:
            os.startfile(job.copy)                   # noqa: S606  the sample copy only
        except OSError:
            diag.swallowed()
    page.host.status(f"Sample: {job.copy}")
    return job.copy


def page_kind(page, fname):
    """3.40.0: 'flow', 'table' or 'placed' for a kept page file ('' when it cannot be read)."""
    import pagekinds as PK
    p = os.path.join(page.parts_dir(), fname) if fname else ""
    if not (p and os.path.isfile(p)):
        return ""
    try:
        with open(p, "rb") as f:
            return PK.kind_of(f.read(), page.work)
    except OSError:
        return ""


def page_kind_text(page, fname):
    import pagekinds as PK
    k = page_kind(page, fname)
    if not k:
        return "Kept as built."
    return PK.describe(k) + (". Kept as built: change it with Edit in Word." if PK.editor_for(k) == "word" else ". Kept as built.")


def edit_layout(page, key, run=True):
    """3.27.0: Edit the cover (or back cover) layout. 3.40.0: a placed page only; a flow or table page is changed in
    Word, so its paragraphs and tables stay as they are. Returns the dialog."""
    import pagekinds as PK
    from .coverview import CoverLayoutDialog
    fname = (page.work.get("page_parts") or {}).get(key)
    if not fname:
        page.host.status("No kept page yet: Import from a file... or New from a blank page... makes one first.")
        return None
    k = page_kind(page, fname)
    if k and PK.editor_for(k) == "word":
        page.host.status(f"{PK.describe(k)}. Change it with Edit in Word, so it stays as it was built.")
        return None
    d = CoverLayoutDialog(page, key)
    if run:
        d.exec()
    return d


# ------------------------------------------------------------------ 3.40.0 Edit in Word
def edit_in_word(page, key, opener=None):
    """Open a dated working copy of the kept page in Word; when Word lets go of it after a save, it is kept as a new
    version. Returns the working copy's path, or ''."""
    import wordedit as WE
    fname = (page.work.get("page_parts") or {}).get(key)
    if not fname:
        page.host.status("No kept page yet: Import from a file... or New from a blank page... makes one first.")
        return ""
    try:
        path, since = WE.start(page.parts_dir(), fname)
    except OSError:
        page.host.status("The kept page file is missing; import it again.")
        return ""
    page._word_edit = {"key": key, "path": path, "since": since, "label": {"cover": "cover", "title": "title page"}.get(key, "back cover")}
    if not WE.open_in_word(path, opener):
        page.host.status(f"Open this copy in Word, change it, save and close: {path}. The app keeps what you save as a new version.")
    else:
        page.host.status("Editing in Word: save and close Word when you are done; the app keeps what you saved as a new version.")
    from PySide6.QtCore import QTimer
    if getattr(page, "_word_timer", None) is None:
        page._word_timer = QTimer(page); page._word_timer.setInterval(2000)
        page._word_timer.timeout.connect(lambda: check_word_edit(page))
    page._word_timer.start()
    diag.activity("page_edit_in_word")
    return path


def check_word_edit(page, force=False):
    """While a page is open in Word: once it is saved and Word lets go of it, keep it. Returns the new file name, or ''."""
    import wordedit as WE
    ed = getattr(page, "_word_edit", None)
    if not ed:
        return ""
    st = WE.state(ed["path"], ed["since"])
    if st == "editing" and not force:
        return ""
    if st == "unchanged" and not force:
        if not os.path.exists(ed["path"]):
            _stop_word_edit(page)
        return ""
    new = WE.keep(page.parts_dir(), ed["path"], ed["label"])
    _stop_word_edit(page)
    if not new:
        page.host.status("What Word saved could not be read as a Word file; the page before it stays.")
        return ""
    old = (page.work.get("page_parts") or {}).get(ed["key"])
    if new != old:
        page.work.setdefault("page_parts", {})[ed["key"]] = new
        page.changed()
        try:
            page.show_parts()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        page.host.status(f"Kept as a new version: {new}. The page before it ({old}) stays.")
    else:
        page.host.status("Nothing changed in Word; the page stays as it was.")
    diag.activity("page_kept_from_word")
    return new


def _stop_word_edit(page):
    t = getattr(page, "_word_timer", None)
    if t is not None:
        t.stop()
    page._word_edit = None
