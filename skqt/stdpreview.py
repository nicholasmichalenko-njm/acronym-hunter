"""Production Standards previews (3.17.0): what the values you are editing produce, drawn for the section you are on,
and a list of every value this layer changes (what it was, what it is now, and the layer it came from).

Drawn from the page's working standard (page.work), so a change shows at once. A sketch at reduced size, not a Word
rendering: the fonts, sizes, spacing, numbering and positions are the standard's own."""
import re
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget
from . import design as D

INK, MUTED, RULE, PAGE, MARGIN = "#1B2433", "#6B778A", "#B9C3D1", "#FFFFFF", "#E7EDF5"
TOK = {"volume_name": "Volume I: Technical", "solicitation": "Solicitation number", "page": "1-1", "date": "Month Day, Year",
       "company": "Company", "marking": "Restriction marking", "title": "Proposal title", "customer": "Customer"}
ROMAN = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]


def _roman(n):
    out = ""
    for v, s in ROMAN:
        while n >= v:
            out += s; n -= v
    return out


def num_text(fmt, n):
    return {"lowerRoman": _roman(n), "upperRoman": _roman(n).upper(), "lowerLetter": "abcdefghij"[(n - 1) % 10],
            "upperLetter": "ABCDEFGHIJ"[(n - 1) % 10], "decimalZero": f"{n:02d}", "bullet": "•"}.get(fmt or "decimal", str(n))


def _v(std, key, default=None):
    """A format variable's value (a style value may name one: =body_font)."""
    x = (std.get("variables") or {}).get(key)
    return default if x in (None, "") else x


def _resolve(std, x, default=None):
    if isinstance(x, str) and x.startswith("="):
        return _v(std, x[1:], default)
    return default if x in (None, "") else x


def _font(name, size, bold=False, italic=False, scale=1.0):
    f = QFont(name or "Arial")
    f.setPointSizeF(max(3.0, float(size or 10) * scale))
    f.setBold(bool(bold)); f.setItalic(bool(italic))
    return f


def _fill(text, n=1):
    return re.sub(r"\{(\w+)\}", lambda m: TOK.get(m.group(1), m.group(1)), str(text or "")).replace("%1", str(n))


class Canvas(QWidget):
    """One section's sketch. section: the Production Standards section key."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.section = "variables"
        self.setMinimumHeight(420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @property
    def std(self):
        return self.page.work or {}

    # ------------------------------------------------------------------ a page to draw on
    def _page(self, p, w_in=8.5, h_in=11.0, top=None, bottom=None, left=None, right=None, box=None):
        """Draw a page to scale inside box (or the widget); returns (page rect, text rect, inches to pixels)."""
        std = self.std
        box = box or QRectF(10, 10, self.width() - 20, self.height() - 20)
        s = min(box.width() / w_in, box.height() / h_in)
        pg = QRectF(box.x() + (box.width() - w_in * s) / 2, box.y(), w_in * s, h_in * s)
        p.fillRect(pg.adjusted(3, 3, 3, 3), QColor("#D5DCE6"))
        p.fillRect(pg, QColor(PAGE))
        p.setPen(QPen(QColor(RULE), 1)); p.drawRect(pg)
        t = float(top if top is not None else _v(std, "margin_top", 1)) * s
        b = float(bottom if bottom is not None else _v(std, "margin_bottom", 1)) * s
        l_ = float(left if left is not None else _v(std, "margin_left", 1)) * s
        r = float(right if right is not None else _v(std, "margin_right", 1)) * s
        tx = QRectF(pg.x() + l_, pg.y() + t, pg.width() - l_ - r, pg.height() - t - b)
        pen = QPen(QColor(MARGIN), 1, Qt.DashLine); p.setPen(pen); p.drawRect(tx)
        return pg, tx, s

    def _text(self, p, rect, text, font, color=INK, align=Qt.AlignLeft | Qt.AlignTop, wrap=True):
        p.setFont(font); p.setPen(QColor(color))
        flags = int(align) | (int(Qt.TextWordWrap) if wrap else 0)
        br = p.boundingRect(rect, flags, text)
        p.drawText(rect, flags, text)
        return br.height()

    def _scale(self, s):
        """Points on the sketch: a page s pixels per inch shows 1 pt as s/72 pixels."""
        return s / 72.0 * 0.75 * 1.333       # QFont points are drawn at the screen's 96 dpi: keep the page's proportion

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True); p.setRenderHint(QPainter.TextAntialiasing, True)
        p.fillRect(self.rect(), QColor("#EEF2F7"))
        try:
            getattr(self, "draw_" + self.section, self.draw_variables)(p)
        except Exception:  # noqa: BLE001  a value being typed must never break the page
            import diag
            diag.swallowed()
            self._text(p, QRectF(16, 16, self.width() - 32, 60), "No preview while this value is being typed.",
                       _font("Segoe UI", 9), MUTED)
        p.end()

    def _body_page(self, p, heading=True):
        std = self.std
        pg, tx, s = self._page(p)
        k = self._scale(s)
        y = tx.y()
        if heading:
            sd = (std.get("style_defs") or {}).get("Heading 1") or {}
            h1 = _font(_resolve(std, sd.get("font"), _v(std, "body_font", "Arial")), _v(std, "heading1_size", sd.get("size") or 14),
                       bold=sd.get("bold", True), scale=k)
            lev = ((std.get("heading_numbering") or {}).get("levels") or [{}])[0]
            num = _fill(lev.get("text") or "%1") if (std.get("heading_numbering") or {}).get("on") else "1"
            y += self._text(p, QRectF(tx.x(), y, tx.width(), 200), f"{num}  Technical Approach", h1) + 6 * k
        bf = _font(_v(std, "body_font", "Arial"), _v(std, "body_size", 11), scale=k)
        ls = {"single": 1.0, "1.15": 1.15, "1.5": 1.5, "double": 2.0}.get(str(_v(std, "line_spacing", "single")), 1.0)
        para = ("Our approach meets every requirement of the Statement of Work. The team brings proven processes, "
                "trained staff and the tools to deliver on schedule.")
        fm = QFontMetricsF(bf)
        lines = max(1, int(fm.horizontalAdvance(para) / max(1.0, tx.width())) + 1)
        for _i in range(2):
            p.setFont(bf); p.setPen(QColor(INK))
            r = QRectF(tx.x(), y, tx.width(), fm.height() * ls * lines + 4)
            opt_h = 0.0
            words, line_, yy = para.split(), "", y
            for w_ in words + [""]:
                trial = (line_ + " " + w_).strip()
                if w_ and fm.horizontalAdvance(trial) <= tx.width():
                    line_ = trial
                    continue
                p.drawText(QRectF(tx.x(), yy, tx.width(), fm.height()), int(Qt.AlignLeft), line_)
                yy += fm.height() * ls; opt_h += fm.height() * ls
                line_ = w_
            y += opt_h + float(_v(std, "space_after_body", 6) or 0) * k
            del r
        return pg, tx, s, k, y

    def draw_variables(self, p):
        std = self.std
        pg, tx, s, k, y = self._body_page(p)
        cf = _font(_v(std, "caption_font", "Arial"), _v(std, "caption_size", 10), bold=True, scale=k)
        y += self._text(p, QRectF(tx.x(), y, tx.width(), 80), "Table 1-1.  Staffing by labor category", cf) + 2
        tf = _font(_v(std, "table_font", "Arial"), _v(std, "table_size", 10), scale=k)
        rh = QFontMetricsF(tf).height() + 4
        for i, row in enumerate((("Labor category", "Hours"), ("Systems engineer", "1,920"), ("Software engineer", "3,840"))):
            r = QRectF(tx.x(), y, tx.width(), rh)
            if i == 0:
                p.fillRect(r, QColor("#DCE6F2"))
            p.setPen(QPen(QColor(RULE), 1)); p.drawRect(r)
            f = QFont(tf); f.setBold(i == 0)
            self._text(p, r.adjusted(4, 2, -tx.width() / 2, 0), row[0], f, wrap=False)
            self._text(p, r.adjusted(tx.width() / 2, 2, -4, 0), row[1], f, align=Qt.AlignRight | Qt.AlignTop, wrap=False)
            y += rh
        self._legend(p, pg, [f"Body: {_v(std, 'body_font', '?')} {_v(std, 'body_size', '?')} pt, {_v(std, 'line_spacing', 'single')}",
                             f"Tables: {_v(std, 'table_font', '?')} {_v(std, 'table_size', '?')} pt",
                             f"Captions: {_v(std, 'caption_font', '?')} {_v(std, 'caption_size', '?')} pt",
                             f"Margins: {_v(std, 'margin_top', 1)} / {_v(std, 'margin_bottom', 1)} / {_v(std, 'margin_left', 1)} / "
                             f"{_v(std, 'margin_right', 1)} in, {_v(std, 'paper', 'Letter')}"])

    def _legend(self, p, pg, lines):
        y = pg.bottom() + 10
        for t in lines:
            y += self._text(p, QRectF(pg.x(), y, self.width() - pg.x() - 10, 40), t, _font("Segoe UI", 8.5), MUTED) + 1
        self.setMinimumHeight(int(y + 10))

    def draw_fonts(self, p):
        import prodrules as PRL
        std = self.std
        y, x = 14.0, 14.0
        y += self._text(p, QRectF(x, y, self.width() - 28, 30), "Each kind of text, in its first allowed font at its smallest "
                        "and largest size:", _font("Segoe UI", 9), MUTED) + 8
        for sc in PRL.SCOPES:
            r = (std.get("fonts") or {}).get(sc) or {}
            fonts = r.get("fonts") or []
            fonts = fonts if isinstance(fonts, list) else [f.strip() for f in str(fonts).split(",") if f.strip()]
            fam = fonts[0] if fonts else _v(std, "body_font", "Arial")
            lo, hi = r.get("min_size"), r.get("max_size")
            name = PRL.SCOPE_NAMES.get(sc, sc)
            self._text(p, QRectF(x, y, 150, 20), name, _font("Segoe UI", 9, bold=True))
            rule = (", ".join(fonts) if fonts else "any font") + (f";  {lo or 'any'} to {hi or 'any'} pt")
            self._text(p, QRectF(x + 150, y, self.width() - x - 160, 20), rule, _font("Segoe UI", 8.5), MUTED)
            y += 18
            sample = "Aa Bb 123"
            for size in [z for z in (lo, hi) if z] or [_v(std, "body_size", 11)]:
                self._text(p, QRectF(x + 10, y, self.width() - 40, 60), f"{sample}  ({size} pt)", _font(fam, size, scale=0.9), wrap=False)
                y += QFontMetricsF(_font(fam, size, scale=0.9)).height() + 2
            y += 8
        self.setMinimumHeight(int(y + 10))

    def draw_styles(self, p):
        std = self.std
        hn = std.get("heading_numbering") or {}
        levels = hn.get("levels") or []
        sd = std.get("style_defs") or {}
        y, x = 14.0, 14.0
        counters = [0] * 9
        plan = [0, 1, 2, 2, 1, 0, 1]
        for lvl in plan:
            counters[lvl] += 1
            for j in range(lvl + 1, 9):
                counters[j] = 0
            lev = levels[lvl] if lvl < len(levels) else {}
            text = lev.get("text") or "%" + str(lvl + 1)
            for j in range(9):
                text = text.replace("%" + str(j + 1), num_text((levels[j] if j < len(levels) else {}).get("fmt"), max(1, counters[j])))
            style = lev.get("style") or f"Heading {lvl + 1}"
            d = sd.get(style) or {}
            size = d.get("size") or ([_v(std, "heading1_size", 14), 13, 12][min(lvl, 2)])
            f = _font(_resolve(std, d.get("font"), _v(std, "body_font", "Arial")), size, bold=d.get("bold", True), italic=d.get("italic"), scale=0.95)
            nx = x + float(lev.get("number_at") or 0) * 60
            tx_ = x + float(lev.get("text_at") or 0.5) * 60
            shown = text if hn.get("on") else ""
            self._text(p, QRectF(nx, y, 120, 40), shown, f, wrap=False)
            h = self._text(p, QRectF(max(tx_, nx + QFontMetricsF(f).horizontalAdvance(shown) + 6), y, self.width() - tx_ - 10, 60),
                           f"{style} sample", f, wrap=False)
            y += h + 6
        bf = _font(_v(std, "body_font", "Arial"), _v(std, "body_size", 11), scale=0.95)
        y += self._text(p, QRectF(x, y, self.width() - 28, 80), "Body text follows the headings in the body style.", bf) + 10
        note = ("Heading numbers are set when fixing." if hn.get("on") else "Heading numbering is off: Fix a Copy leaves the "
                "numbers as the draft has them.")
        y += self._text(p, QRectF(x, y, self.width() - 28, 60), note, _font("Segoe UI", 8.5), MUTED)
        allowed = (std.get("styles") or {}).get("allowed") or []
        if allowed:
            y += 6 + self._text(p, QRectF(x, y + 6, self.width() - 28, 200), "Allowed styles: " + ", ".join(allowed),
                                _font("Segoe UI", 8.5), MUTED)
        self.setMinimumHeight(int(y + 20))

    def draw_styledefs(self, p):
        std = self.std
        y, x = 14.0, 14.0
        sd = std.get("style_defs") or {}
        if not sd:
            self._text(p, QRectF(x, y, self.width() - 28, 60), "No styles defined here. Learn from a file... fills this from a "
                       "template.", _font("Segoe UI", 9), MUTED)
            return
        for name, d in list(sd.items())[:24]:
            f = _font(_resolve(std, d.get("font"), _v(std, "body_font", "Arial")), _resolve(std, d.get("size"), 11), bold=d.get("bold"),
                      italic=d.get("italic"), scale=0.9)
            col = "#" + d["color"] if d.get("color") else INK
            y += self._text(p, QRectF(x, y, self.width() - 28, 60), name, f, col, wrap=False) + float(d.get("after") or 2) * 0.5 + 2
        self.setMinimumHeight(int(y + 20))

    def draw_rows(self, p):
        self._text(p, QRectF(14, 14, self.width() - 28, 60), "The table under Table rows shows each row's look as you change it.",
                   _font("Segoe UI", 9), MUTED)

    draw_ttypes = draw_rows
    draw_rules = draw_rows

    def draw_captions(self, p):
        std = self.std
        pg, tx, s, k, y = self._body_page(p, heading=True)
        cf = _font(_v(std, "caption_font", "Arial"), _v(std, "caption_size", 10), bold=True, scale=k)
        after = {"period_tab": ". ", "period_space": ". ", "tab": " ", "colon_space": ": ", "space": " "}
        for c in [c for c in (std.get("captions") or []) if c.get("part", "body") == "body"][:2]:
            label = c.get("label") or "Table"
            chap = "A" if c.get("part") == "appendix" else "3"
            sep = c.get("separator") or "-"
            numtxt = f"{chap}{sep}1" if c.get("chapter_level") else "1"
            cap = f"{label} {numtxt}{after.get(c.get('after_number'), '. ')}A {label.lower()} title"
            box_h = 34 * k * 2
            if c.get("position", "above") == "above":
                y += self._text(p, QRectF(tx.x(), y, tx.width(), 60), cap, cf) + 2
                p.setPen(QPen(QColor(RULE), 1)); p.fillRect(QRectF(tx.x(), y, tx.width(), box_h), QColor("#F1F4F8")); p.drawRect(QRectF(tx.x(), y, tx.width(), box_h))
                y += box_h + 8
            else:
                p.setPen(QPen(QColor(RULE), 1)); p.fillRect(QRectF(tx.x(), y, tx.width(), box_h), QColor("#F1F4F8")); p.drawRect(QRectF(tx.x(), y, tx.width(), box_h))
                y += box_h + 2
                y += self._text(p, QRectF(tx.x(), y, tx.width(), 60), cap, cf, align=Qt.AlignHCenter | Qt.AlignTop) + 8
        self._legend(p, pg, [f"{c.get('label')} ({c.get('part')}): {c.get('position')}, chapter level {c.get('chapter_level') or 'none'}, "
                             f"list {c.get('identifier')}" for c in (std.get("captions") or [])][:6])

    def draw_pages(self, p):
        std = self.std
        parts = (std.get("pagination") or {}).get("parts") or []
        n = max(1, len(parts))
        bw = (self.width() - 20) / min(n, 4)
        y0 = 10
        for i, part in enumerate(parts):
            col, row = i % 4, i // 4
            box = QRectF(10 + col * bw + 4, y0 + row * 190, bw - 8, 150)
            pg, tx, s = self._page(p, box=box)
            nums = part.get("numbers") or {}
            if nums:
                start = int(nums.get("start_at") or 1)
                n_ = num_text(nums.get("fmt"), start)
                if nums.get("chapter_level"):
                    sep = {"hyphen": "-", "period": ".", "colon": ":", "emdash": "—", "endash": "–"}.get(nums.get("separator"), "-")
                    n_ = ("A" if part.get("key") == "appendix" else "1") + sep + n_
            else:
                n_ = "(no number)"
            self._text(p, QRectF(pg.x(), pg.bottom() - 16, pg.width(), 14), n_, _font("Segoe UI", 7.5), INK, Qt.AlignHCenter | Qt.AlignTop, False)
            if part.get("header"):
                self._text(p, QRectF(tx.x(), pg.y() + 3, tx.width(), 12), _fill(part["header"]), _font("Segoe UI", 6), MUTED, wrap=False)
            self._text(p, QRectF(box.x(), pg.bottom() + 3, box.width(), 30), part.get("name") or part.get("key", ""), _font("Segoe UI", 8, bold=True),
                       INK, Qt.AlignHCenter | Qt.AlignTop)
        self.setMinimumHeight(int(y0 + ((n - 1) // 4 + 1) * 190 + 10))

    def draw_setups(self, p):
        std = self.std
        sets = list((std.get("page_setups") or {}).items())
        bw = (self.width() - 20) / max(1, min(len(sets), 3))
        for i, (k_, su) in enumerate(sets):
            col, row = i % 3, i // 3
            box = QRectF(10 + col * bw + 4, 10 + row * 200, bw - 8, 160)
            pg, tx, s = self._page(p, float(su.get("w") or 8.5), float(su.get("h") or 11),
                                   *[float(_resolve(std, su.get(e), 1)) for e in ("top", "bottom", "left", "right")], box=box)
            self._text(p, QRectF(box.x(), pg.bottom() + 3, box.width(), 30), su.get("name") or k_, _font("Segoe UI", 8, bold=True), INK,
                       Qt.AlignHCenter | Qt.AlignTop)
        self.setMinimumHeight(int(10 + ((len(sets) - 1) // 3 + 1) * 200 + 10))

    def draw_hf(self, p):
        std = self.std
        lay = std.get("hf_layouts") or {}
        key = next((k for k in ("body", "front") if k in lay), next(iter(lay), ""))
        hf = lay.get(key) or {}
        pg, tx, s = self._page(p)
        f = _font(_v(std, "body_font", "Arial"), 9, scale=self._scale(s))
        hy = pg.y() + 0.5 * s
        h, ft = hf.get("header") or {}, hf.get("footer") or {}
        for where, al in (("left", Qt.AlignLeft), ("center", Qt.AlignHCenter), ("right", Qt.AlignRight)):
            if h.get(where):
                self._text(p, QRectF(tx.x(), hy, tx.width(), 20), _fill(h[where]), f, align=al | Qt.AlignTop, wrap=False)
            if ft.get(where):
                self._text(p, QRectF(tx.x(), pg.bottom() - 0.6 * s, tx.width(), 20), _fill(ft[where]), f, align=al | Qt.AlignTop, wrap=False)
        if h.get("rule_below"):
            p.setPen(QPen(QColor(INK), 1)); p.drawLine(int(tx.x()), int(hy + 14), int(tx.right()), int(hy + 14))
        if ft.get("marking"):
            self._text(p, QRectF(tx.x(), pg.bottom() - 0.35 * s, tx.width(), 20), TOK["marking"], f, MUTED, Qt.AlignHCenter | Qt.AlignTop, False)
        self._legend(p, pg, [f"Shown: the {key} part. Every part: " + ", ".join(lay.keys())])

    def draw_toc(self, p):
        std = self.std
        toc = std.get("toc") or {}
        es = toc.get("entry_styles") or {}
        pg, tx, s = self._page(p)
        k = self._scale(s)
        f = _font(_v(std, "body_font", "Arial"), _v(std, "body_size", 11), scale=k)
        y = tx.y()
        y += self._text(p, QRectF(tx.x(), y, tx.width(), 40), "Table of Contents", _font(_v(std, "body_font", "Arial"), 14, True, scale=k)) + 8
        lines = [("TOC 1", "1", "Technical Approach", "1-1"), ("TOC 2", "1.1", "Engineering", "1-2"), ("TOC 3", "1.1.1", "Design reviews", "1-4"),
                 ("TOC 1", "2", "Management Approach", "2-1"), ("Table of Figures", "", "Figure 1-1. Architecture", "1-3")]
        fm = QFontMetricsF(f)
        for st, n, t, pgno in lines:
            e = es.get(st) or {}
            tab = e.get("tab") or [6.5, "right", "dot"]
            nx = tx.x() + float(e.get("number_at") or 0) * s
            tx2 = tx.x() + float(e.get("text_at") or 0.4) * s
            right = tx.x() + float(tab[0] if isinstance(tab, list) else e.get("tab_pos") or 6.5) * s
            right = min(right, tx.right())
            p.setFont(f); p.setPen(QColor(INK))
            if n:
                p.drawText(QRectF(nx, y, tx2 - nx, fm.height()), int(Qt.AlignLeft), n)
            p.drawText(QRectF(tx2, y, right - tx2, fm.height()), int(Qt.AlignLeft), t)
            pw = fm.horizontalAdvance(pgno)
            p.drawText(QRectF(right - pw, y, pw + 2, fm.height()), int(Qt.AlignLeft), pgno)
            lead = (tab[2] if isinstance(tab, list) and len(tab) > 2 else e.get("tab_leader")) or "dot"
            if lead != "none":
                ch = {"dot": ".", "hyphen": "-", "underscore": "_"}.get(lead, ".")
                start = tx2 + fm.horizontalAdvance(t) + 4
                p.setPen(QColor(MUTED))
                p.drawText(QRectF(start, y, max(0.0, right - pw - start - 2), fm.height()), int(Qt.AlignLeft),
                           ch * int(max(0.0, right - pw - start - 2) / max(1.0, fm.horizontalAdvance(ch))))
            y += fm.height() * 1.25
        self._legend(p, pg, ["Levels: " + ", ".join(f"{a} = {b}" for a, b in (toc.get("levels") or [])),
                             "Switches: " + " ".join(toc.get("switches") or [])])

    def draw_lists(self, p):
        std = self.std
        x, y = 14.0, 14.0
        f = _font(_v(std, "body_font", "Arial"), _v(std, "body_size", 11), scale=0.95)
        fm = QFontMetricsF(f)
        for lst in ((std.get("list_numbering") or {}).get("lists") or []):
            y += self._text(p, QRectF(x, y, self.width() - 28, 20), lst.get("name", ""), _font("Segoe UI", 9, bold=True)) + 4
            for i, lev in enumerate(lst.get("levels") or []):
                left = float(lev.get("left") or 0.25 * (i + 1)) * 72
                hang = float(lev.get("hanging") or 0.25) * 72
                mark = lev.get("text") or "•"
                if lev.get("fmt") and lev["fmt"] != "bullet":
                    mark = mark.replace("%" + str(i + 1), num_text(lev["fmt"], 1))
                mf = _font(lev.get("font") or _v(std, "body_font", "Arial"), _v(std, "body_size", 11), scale=0.95)
                self._text(p, QRectF(x + left - hang, y, hang, fm.height()), mark, mf, wrap=False)
                self._text(p, QRectF(x + left, y, self.width() - x - left - 10, fm.height()), f"{lev.get('style', '')}: a list item",
                           f, wrap=False)
                y += fm.height() + 4
            y += 10
        lists = std.get("lists") or {}
        y += self._text(p, QRectF(x, y, self.width() - 28, 60), "Typed bullets that become list styles: " +
                        " ".join(lists.get("typed_bullets") or []), _font("Segoe UI", 8.5), MUTED)
        self.setMinimumHeight(int(y + 20))

    def draw_terms(self, p):
        std = self.std
        t = std.get("terms") or {}
        x, y = 14.0, 14.0
        f = _font(_v(std, "body_font", "Arial"), 10)
        rep = t.get("replace") or []
        y += self._text(p, QRectF(x, y, self.width() - 28, 20), "Fixed automatically", _font("Segoe UI", 9, bold=True)) + 4
        for r in rep[:6]:
            y += self._text(p, QRectF(x, y, self.width() - 28, 40), f"{r.get('find')}  →  {r.get('replace')}"
                            + ("  (first use)" if r.get("when") == "first" else ""), f) + 2
        if not rep:
            y += self._text(p, QRectF(x, y, self.width() - 28, 40), "None.", f, MUTED) + 2
        y += 10
        y += self._text(p, QRectF(x, y, self.width() - 28, 20), "Reported, never changed", _font("Segoe UI", 9, bold=True)) + 4
        for b in (t.get("banned") or [])[:6]:
            y += self._text(p, QRectF(x, y, self.width() - 28, 40), f"{b.get('find')}" + (f"  (suggest: {b['suggest']})" if b.get("suggest") else ""),
                            f, "#9A4508") + 2
        if not t.get("banned"):
            y += self._text(p, QRectF(x, y, self.width() - 28, 40), "The team's banned words are added for each run.", f, MUTED)
        self.setMinimumHeight(int(y + 20))

    def draw_office(self, p):
        std = self.std
        ex, pp = std.get("excel") or {}, std.get("powerpoint") or {}
        x, y = 14.0, 14.0
        fam = ex.get("font") or _v(std, "table_font", "Arial")
        size = ex.get("size") or _v(std, "table_size", 10)
        f = _font(fam, size, scale=0.9)
        hd = ex.get("header") or {}
        y += self._text(p, QRectF(x, y, self.width() - 28, 20), "Excel", _font("Segoe UI", 9, bold=True)) + 4
        cw, rh = (self.width() - 28) / 3, QFontMetricsF(f).height() + 6
        for i, row in enumerate((("Item", "Qty", "Cost"), ("Labor", "1,920", "$271,680"), ("Travel", "12", "$18,400"))):
            for j, cell in enumerate(row):
                r = QRectF(x + j * cw, y, cw, rh)
                if i == 0 and hd.get("fill"):
                    p.fillRect(r, QColor("#" + str(hd["fill"]).lstrip("#")))
                p.setPen(QPen(QColor(RULE), 1)); p.drawRect(r)
                ff = QFont(f); ff.setBold(i == 0 and bool(hd.get("bold")))
                self._text(p, r.adjusted(4, 3, -4, 0), cell, ff, "#" + str(hd.get("color")).lstrip("#") if i == 0 and hd.get("color") else INK, wrap=False)
            y += rh
        y += 16
        y += self._text(p, QRectF(x, y, self.width() - 28, 20), "PowerPoint", _font("Segoe UI", 9, bold=True)) + 4
        ratio = 9 / 16 if pp.get("slide_size", "16:9") in ("16:9", "") else 3 / 4
        sw = self.width() - 28
        slide = QRectF(x, y, sw, sw * ratio)
        p.fillRect(slide, QColor(PAGE)); p.setPen(QPen(QColor(RULE), 1)); p.drawRect(slide)
        fonts = [f_.strip() for f_ in str(pp.get("fonts") or "").split(",") if f_.strip()] or [_v(std, "body_font", "Arial")]
        tsz = pp.get("title_min_size") or 28
        self._text(p, slide.adjusted(14, 10, -14, 0), "Slide title", _font(fonts[0], tsz, True, scale=0.45), wrap=False)
        self._text(p, slide.adjusted(14, 10 + tsz * 0.8, -14, 0), f"Body text at the smallest size, {pp.get('min_size') or 12} pt",
                   _font(fonts[0], pp.get("min_size") or 12, scale=0.45))
        if pp.get("marking"):
            self._text(p, QRectF(slide.x(), slide.bottom() - 14, slide.width(), 12), TOK["marking"], _font("Segoe UI", 6), MUTED, Qt.AlignHCenter | Qt.AlignTop, False)
        self.setMinimumHeight(int(slide.bottom() + 20))

    def draw_graphics(self, p):
        import prodgraphics as PG
        std = self.std
        g = PG.rules_of(std)
        pg, tx, s = self._page(p)
        k = self._scale(s)
        y = tx.y() + 8
        if g.get("max_width") == "set" and g.get("max_width_in"):
            w = min(tx.width(), float(g["max_width_in"]) * s)
        else:
            w = tx.width()
        h = w * 0.55
        fig = QRectF(tx.x() + (tx.width() - w) / 2, y, w, h)
        p.fillRect(fig, QColor("#E3ECF8")); p.setPen(QPen(QColor("#5B7FB0"), 1)); p.drawRect(fig)
        ff = _font((g.get("fonts") or ["Arial"])[0], g.get("min_text_pt") or 8, scale=k)
        for i, t in enumerate(("Ground segment", "Space segment", "Users")):
            r = QRectF(fig.x() + 10 + i * (fig.width() - 20) / 3, fig.y() + fig.height() / 3, (fig.width() - 20) / 3 - 8, fig.height() / 3)
            p.fillRect(r, QColor(PAGE)); p.setPen(QPen(QColor("#5B7FB0"), 1)); p.drawRect(r)
            self._text(p, r.adjusted(2, 2, -2, -2), t, ff, align=Qt.AlignCenter, wrap=True)
        y = fig.bottom() + 4
        if g.get("caption"):
            cf = _font(_v(std, "caption_font", "Arial"), _v(std, "caption_size", 10), bold=True, scale=k)
            self._text(p, QRectF(tx.x(), y, tx.width(), 40), "Figure 1-1.  System architecture", cf, align=Qt.AlignHCenter | Qt.AlignTop)
        width = ("the text width (margins)" if g.get("max_width") == "margins" else
                 f"{g.get('max_width_in')} in" if g.get("max_width") == "set" else "any width")
        self._legend(p, pg, [f"Pictures: {', '.join(PG.TYPE_NAMES.get(t, t.upper()) for t in g.get('types') or []) or 'any type'}; "
                             f"at least {g.get('min_ppi') or 'any'} ppi where placed; {width}",
                             f"Text in drawings and charts: {', '.join(g.get('fonts') or ['any font'])}, at least {g.get('min_text_pt') or 'any'} pt"
                             + ("; text inside pictures estimated by OCR" if g.get("ocr_text") else ""),
                             "Every figure: " + ", ".join(x for x, on in (("a caption", g.get("caption")), ("alt text", g.get("alt_text")),
                                                                         ("RGB, not CMYK", g.get("rgb_only"))) if on)
                             + (f"; pictures up to {g.get('max_file_mb')} MB" if g.get("max_file_mb") else "")])

    def draw_checks(self, p):
        std = self.std
        c = std.get("checks") or {}
        lines = [("Every section's footer has a page number field", c.get("page_numbers")),
                 ("Caption numbers must be fields", c.get("caption_fields")),
                 (f"Table captions: {c.get('table_caption_position') or 'any'}", True),
                 ("Landscape sections allowed", c.get("landscape_ok")),
                 ("TOC switches never used: " + " ".join(c.get("toc_forbid") or []), bool(c.get("toc_forbid")))]
        y = 14.0
        for t, on in lines:
            y += self._text(p, QRectF(14, y, self.width() - 28, 40), ("✓  " if on else "–  ") + t, _font("Segoe UI", 9.5),
                            INK if on else MUTED) + 6


class Preview(QWidget):
    """The panel beside the sections: what changed at this layer, then the sketch."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["s"])
        self.title = D.label("Preview", "label", wrap=False); v.addWidget(self.title)
        self.changes = QLabel(""); self.changes.setWordWrap(True); self.changes.setTextFormat(Qt.RichText)
        self.changes.setObjectName("stdchanges"); v.addWidget(self.changes)
        self.canvas = Canvas(page)
        from PySide6.QtWidgets import QFrame, QScrollArea
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame); sc.setWidget(self.canvas)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(sc, 1)
        self.setMinimumWidth(320); self.setMaximumWidth(420)

    def show_section(self, key, title):
        self.canvas.section = key
        self.title.setText(f"Preview: {title}")
        self.refresh()

    def refresh(self):
        rows = self.page.changed_here(self.canvas.section)
        if rows:
            body = "".join(f"<div style='margin:2px 0'><b>{_esc(name)}</b>: was {_esc(was)}, now <b>{_esc(now)}</b></div>"
                           for name, was, now in rows[:12])
            more = f"<div>and {len(rows) - 12} more</div>" if len(rows) > 12 else ""
            self.changes.setText(f"<div style='color:{D.tokens()['warn']}'><b>{len(rows)} value(s) set at this layer</b> "
                                 f"(the layer below: {_esc(self.page.base_name())})</div>{body}{more}")
        else:
            self.changes.setText(f"<span style='color:{D.tokens()['muted']}'>Nothing set at this layer in this section: every "
                                 f"value comes from {_esc(self.page.base_name())}.</span>")
        self.canvas.update()


def _esc(x):
    s = "Not set" if x in (None, "", [], {}) else (", ".join(map(str, x)) if isinstance(x, list) else str(x))
    s = s if len(s) < 70 else s[:67] + "..."
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
