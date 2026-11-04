"""A picture of one library or import item (3.44.0; 3.50.0 its own module, every kind drawn). Word's own picture when
Word drew it (the item dict carries "png"), marked as Word's; otherwise the app's sketch, marked as a sketch:
  a style as sample text in it; a page setup or section as a page with its margins, header and footer; a header and
  footer on a page; a table look as a sample table; a table style as a grid; a theme as its 12 colors and two fonts;
  a font set as lines in each font and size; a font in itself; heading numbering and lists as numbered lines; the
  TOC as entries with leaders; captions as sample captions; pagination as its parts; a cover, title page or back
  cover drawn from its kept page; a Quick Part as its card."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

import importbrowse as IB
import templatelib as TL
from . import design as D


class ItemPicture(QWidget):
    def __init__(self):
        super().__init__()
        self.it = None
        self._pix = None
        self.setMinimumSize(260, 300)

    def show_item(self, it):
        self.it = it
        self._pix = QPixmap(it["png"]) if it and it.get("png") else None
        if self._pix is not None and self._pix.isNull():
            self._pix = None
        self.update()

    def source(self):
        """'word', 'sketch' or '' (nothing shown)."""
        return "" if not self.it else ("word" if self._pix is not None else "sketch")

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(D.tokens()["surface2"]))
        it = self.it
        r = QRectF(self.rect()).adjusted(10, 10, -10, -24)
        p.setPen(QColor(D.tokens()["text"]))
        if not it:
            p.drawText(r, Qt.AlignCenter | Qt.TextWordWrap, "Select an item to see it.")
            p.end()
            return
        if self._pix is not None:
            pm = self._pix.scaled(int(r.width()), int(r.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(int(r.left() + (r.width() - pm.width()) / 2), int(r.top()), pm)
            note = "Word's picture"
        else:
            try:
                draw_item(p, r, it)
            except Exception:  # noqa: BLE001  an item that cannot be drawn shows its summary
                import diag
                diag.swallowed()
                p.drawText(r, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, f"{it['name']}\n\n{it.get('summary') or ''}")
            note = "Sketch" + (": Draw with Word for Word's own picture" if it.get("word_can") else "")
        small = QFont(); small.setPointSizeF(7.5); p.setFont(small); p.setPen(QColor(D.tokens()["muted"]))
        p.drawText(QRectF(10, self.height() - 20, self.width() - 20, 16), Qt.AlignLeft | Qt.AlignVCenter, note)
        p.end()


def draw_item(p, r, it):
    k, v = it["kind"], it.get("values") or {}
    if k == "style":
        if v.get("type") == "table":
            return draw_grid(p, r, it["name"], v)
        return draw_style(p, r, it["name"], v)
    if k in ("page_setup", "section"):
        return draw_page(p, r, v.get("page") if k == "section" else v, it)
    if k == "table_look":
        return draw_table(p, r, v)
    if k == "table_style":
        return draw_grid(p, r, it["name"], v)
    if k == "theme":
        return draw_theme(p, r, v)
    if k == "variables":
        return draw_fonts(p, r, v)
    if k == "font":
        return draw_font(p, r, v.get("font") or it["name"])
    if k in ("hf", "hf_design"):
        return draw_hf(p, r, k, v)
    if k in ("heading_numbering", "list_numbering"):
        return draw_levels(p, r, v.get("levels") or [])
    if k == "toc":
        return draw_toc(p, r, v)
    if k == "captions":
        return draw_captions(p, r, v.get("captions") or [])
    if k == "pagination":
        return draw_pagination(p, r, v)
    if k in ("cover", "backer", "title") and it.get("page_bytes"):
        from .coverdraw import draw_page as cover_page
        w, h = 8.5, 11
        s = min(r.width() / w, r.height() / h)
        page = QRectF(r.left() + (r.width() - w * s) / 2, r.top(), w * s, h * s)
        p.setPen(QPen(QColor("#9aa3b2"), 1)); p.setBrush(QColor("#ffffff")); p.drawRect(page); p.setBrush(Qt.NoBrush)
        return cover_page(p, page, it["page_bytes"], None)
    if k == "quickpart":
        return draw_card(p, r, it["name"], [f"Category: {v.get('category') or 'none'}", f"Gallery: {v.get('gallery') or 'Quick Parts'}",
                                            "Kept as built" if v.get("as_built") else "Follows the template's fonts",
                                            v.get("description") or "", it.get("summary") or ""])
    return draw_card(p, r, it["name"], [it.get("summary") or ""])


def _sheet(p, r):
    """A white page area inside r (letter shape, top aligned)."""
    w, h = 8.5, 11
    s = min(r.width() / w, r.height() / h)
    page = QRectF(r.left() + (r.width() - w * s) / 2, r.top(), w * s, h * s)
    p.setPen(QPen(QColor("#9aa3b2"), 1)); p.setBrush(QColor("#ffffff")); p.drawRect(page); p.setBrush(Qt.NoBrush)
    return page, s


def _font(family="", pt=9.0, bold=False, italic=False):
    f = QFont(str(family or "Calibri")); f.setPointSizeF(max(5.0, min(30.0, float(pt or 9)))); f.setBold(bool(bold)); f.setItalic(bool(italic))
    return f


def _hex(c, default="#1f2937"):
    return QColor("#" + c) if isinstance(c, str) and len(c) == 6 else QColor(default)


def draw_card(p, r, title, lines):
    p.setFont(_font("", 11, True)); p.setPen(QColor(D.tokens()["text"]))
    p.drawText(QRectF(r.left(), r.top(), r.width(), 24), Qt.AlignLeft | Qt.AlignVCenter, title)
    p.setFont(_font("", 8.5)); p.setPen(QColor(D.tokens()["muted"]))
    p.drawText(QRectF(r.left(), r.top() + 30, r.width(), r.height() - 30), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
               "\n".join(x for x in lines if x))


def draw_style(p, r, name, v):
    f = QFont(str(v.get("font") or "Calibri"))
    f.setPointSizeF(max(6.0, min(28.0, float(v.get("size") or 11))))
    f.setBold(bool(v.get("bold"))); f.setItalic(bool(v.get("italic")))
    f.setCapitalization(QFont.AllUppercase if v.get("caps") else QFont.MixedCase)
    p.setFont(f)
    col = v.get("color")
    p.setPen(QColor("#" + col) if isinstance(col, str) and len(col) == 6 else QColor(D.tokens()["text"]))
    sample = "Section heading" if name.lower().startswith(("heading", "title")) else \
        "Body text in this style: how a paragraph of the volume reads, line after line, at this size and spacing."
    al = {"center": Qt.AlignHCenter, "right": Qt.AlignRight, "both": Qt.AlignJustify}.get(v.get("jc"), Qt.AlignLeft)
    p.drawText(r.adjusted(0, 0, 0, -40), al | Qt.AlignTop | Qt.TextWordWrap, sample)
    small = QFont(); small.setPointSizeF(8); p.setFont(small); p.setPen(QColor(D.tokens()["muted"]))
    bits = [str(v.get("font") or ""), f"{v.get('size')} pt" if v.get("size") else "", "bold" if v.get("bold") else "",
            "hidden text" if v.get("hidden") else "", f"based on {v['based_on']}" if v.get("based_on") else ""]
    p.drawText(QRectF(r.left(), r.bottom() - 34, r.width(), 34), Qt.AlignLeft | Qt.TextWordWrap, f"{name}: " + ", ".join(b for b in bits if b))


def _num(x, d):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def draw_page(p, r, pg, it):
    pg = pg or {}
    w, h = _num(pg.get("w"), 8.5), _num(pg.get("h"), 11)
    s = min(r.width() / w, (r.height() - 40) / h)
    page = QRectF(r.left() + (r.width() - w * s) / 2, r.top(), w * s, h * s)
    p.setPen(QPen(QColor("#9aa3b2"), 1)); p.setBrush(QColor("#ffffff")); p.drawRect(page); p.setBrush(Qt.NoBrush)
    m = [_num(pg.get(k), 1) for k in ("top", "bottom", "left", "right")]
    body = QRectF(page.left() + m[2] * s, page.top() + m[0] * s, page.width() - (m[2] + m[3]) * s, page.height() - (m[0] + m[1]) * s)
    p.setPen(QPen(QColor("#c7cdd8"), 1, Qt.DashLine)); p.drawRect(body)
    small = QFont(); small.setPointSizeF(7); p.setFont(small); p.setPen(QColor("#1f2937"))
    v = it.get("values") or {}
    for kind, y in (("header", page.top() + 4), ("footer", page.bottom() - 16)):
        txt = IB.hf_text(v.get(kind)) if it["kind"] == "section" else ""
        if txt:
            p.drawText(QRectF(body.left(), y, body.width(), 12), Qt.AlignHCenter, p.fontMetrics().elidedText(txt, Qt.ElideRight, int(body.width())))
    p.setPen(QColor(D.tokens()["muted"]))
    p.drawText(QRectF(r.left(), page.bottom() + 6, r.width(), 30), Qt.AlignHCenter | Qt.TextWordWrap, it.get("summary") or "")


def draw_table(p, r, v):
    rows = (v.get("row_types") or {}) if isinstance(v, dict) else {}
    order = [x for x in ("caption", "header", "body", "subtotal", "total", "note") if x in rows] or list(rows)[:5]
    y = r.top()
    small = QFont(); small.setPointSizeF(8); p.setFont(small)
    for role in order:
        look = rows.get(role) or {}
        fill = look.get("fill")
        rr = QRectF(r.left(), y, r.width(), 22)
        if isinstance(fill, str) and len(fill) == 6:
            p.fillRect(rr, QColor("#" + fill))
        p.setPen(QPen(QColor("#64748b"), 0.8)); p.drawRect(rr)
        p.setPen(QColor("#" + look["color"]) if isinstance(look.get("color"), str) and len(look["color"]) == 6 else QColor("#1f2937"))
        p.drawText(rr.adjusted(6, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft, role.title())
        y += 24


def draw_grid(p, r, name, v):
    p.setFont(_font("", 9, True)); p.setPen(QColor(D.tokens()["text"]))
    p.drawText(QRectF(r.left(), r.top(), r.width(), 20), Qt.AlignLeft, name)
    rows = (("Item", "Approach", "Result"), ("Design", "Reviewed", "Approved"), ("Test", "Three campaigns", "Passed"))
    cw, y = r.width() / 3, r.top() + 26
    for n, row in enumerate(rows):
        for c, txt in enumerate(row):
            cell = QRectF(r.left() + c * cw, y, cw, 22)
            if n == 0:
                p.fillRect(cell, QColor("#dbe4f0"))
            p.setPen(QPen(QColor("#64748b"), 0.8)); p.drawRect(cell)
            p.setFont(_font("", 8, n == 0)); p.setPen(QColor("#1f2937"))
            p.drawText(cell.adjusted(4, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, txt)
        y += 22
    p.setFont(_font("", 7.5)); p.setPen(QColor(D.tokens()["muted"]))
    p.drawText(QRectF(r.left(), y + 8, r.width(), 40), Qt.AlignLeft | Qt.TextWordWrap, "Word table style: Draw with Word shows its "
               "own borders, shading and banding.")


def draw_theme(p, r, v):
    cols = v.get("colors") or {}
    p.setFont(_font("", 10, True)); p.setPen(QColor(D.tokens()["text"]))
    p.drawText(QRectF(r.left(), r.top(), r.width(), 20), Qt.AlignLeft, v.get("name") or "Theme")
    sw = (r.width() - 10) / 4
    for n, slot in enumerate(TL.THEME_SLOTS):
        x, y = r.left() + (n % 4) * (sw + 3), r.top() + 26 + (n // 4) * 58
        p.fillRect(QRectF(x, y, sw, 32), _hex(cols.get(slot), "#ffffff"))
        p.setPen(QPen(QColor("#9aa3b2"), 0.6)); p.drawRect(QRectF(x, y, sw, 32))
        p.setFont(_font("", 7)); p.setPen(QColor(D.tokens()["muted"]))
        p.drawText(QRectF(x, y + 33, sw, 20), Qt.AlignLeft | Qt.TextWordWrap, TL.THEME_NAMES.get(slot, slot))
    y = r.top() + 26 + 3 * 58 + 6
    p.setFont(_font(v.get("major"), 14, True)); p.setPen(QColor(D.tokens()["text"]))
    p.drawText(QRectF(r.left(), y, r.width(), 26), Qt.AlignLeft, f"Headings: {v.get('major') or 'not set'}")
    p.setFont(_font(v.get("minor"), 10))
    p.drawText(QRectF(r.left(), y + 28, r.width(), 22), Qt.AlignLeft, f"Body: {v.get('minor') or 'not set'}")


def draw_fonts(p, r, v):
    y = r.top()
    for role in ("body", "table", "caption", "heading", "header_footer", "footnote"):
        fam, size = v.get(f"{role}_font"), v.get(f"{role}_size")
        if not fam and not size:
            continue
        p.setFont(_font(fam, size or 10)); p.setPen(QColor(D.tokens()["text"]))
        txt = f"{role.replace('_', ' ').capitalize()}: {fam or 'the body font'} {size or ''} pt".replace("  ", " ")
        p.drawText(QRectF(r.left(), y, r.width(), 28), Qt.AlignLeft | Qt.AlignVCenter, txt)
        y += 30
    rest = [f"{k.replace('_', ' ')} {x}" for k, x in v.items() if not k.endswith(("_font", "_size")) and x not in (None, "")]
    p.setFont(_font("", 8)); p.setPen(QColor(D.tokens()["muted"]))
    p.drawText(QRectF(r.left(), y + 6, r.width(), r.bottom() - y), Qt.AlignLeft | Qt.TextWordWrap, "; ".join(rest[:12]))


def draw_font(p, r, fam):
    p.setPen(QColor(D.tokens()["text"]))
    y = r.top()
    for pt in (24, 14, 10):
        p.setFont(_font(fam, pt))
        p.drawText(QRectF(r.left(), y, r.width(), pt * 2), Qt.AlignLeft | Qt.AlignVCenter, f"{fam} {pt} pt")
        y += pt * 2 + 6
    p.setFont(_font(fam, 11))
    p.drawText(QRectF(r.left(), y, r.width(), 60), Qt.AlignLeft | Qt.TextWordWrap, "ABCDEFGHIJKLM abcdefghijklm 0123456789 (),.;:")


def _named(text):
    """Field tokens in words: {volume_name} as [Volume name]."""
    import re
    from .fieldpicker import choices
    names = dict(choices({}))
    return re.sub(r"\{(\w+)\}", lambda m: "[" + names.get(m.group(1), m.group(1).replace("_", " ").capitalize()) + "]", str(text or ""))


def _hf_words(part):
    """(left, center, right) words of a header or footer layout; a table's cells left to right."""
    return tuple(_named(x) for x in _hf_raw(part))


def _hf_raw(part):
    if not isinstance(part, dict):
        return ("", IB.hf_text(part) if isinstance(part, str) else "", "")
    cells = (part.get("table") or {}).get("cells")
    if cells:
        words = [" / ".join(ln.get("text") or "" for ln in c.get("lines") or [] if ln.get("text")) for c in cells]
        words += [""] * (3 - len(words))
        return tuple(words[:3])
    return (part.get("left") or "", part.get("center") or "", part.get("right") or "")


def draw_hf(p, r, kind, v):
    page, s = _sheet(p, r)
    p.setFont(_font("", 6.5)); p.setPen(QColor("#1f2937"))
    for which, y in (("header", page.top() + 0.35 * s), ("footer", page.bottom() - 0.7 * s)):
        if kind == "hf_design":
            words = ("", IB.hf_text(v.get(which)), "")
        else:
            words = _hf_words(v.get(which))
        box = QRectF(page.left() + 0.6 * s, y, page.width() - 1.2 * s, 0.35 * s)
        for txt, al in zip(words, (Qt.AlignLeft, Qt.AlignHCenter, Qt.AlignRight)):
            if txt:
                p.drawText(box, al | Qt.AlignVCenter, p.fontMetrics().elidedText(txt, Qt.ElideRight, int(box.width() / 2)))
        if which == "header" and isinstance(v.get("header"), dict) and v["header"].get("rule_below"):
            p.drawLine(box.bottomLeft(), box.bottomRight())
    p.setPen(QColor("#d1d5db"))
    for n in range(8):
        y = page.top() + (1.4 + n * 0.45) * s
        p.drawLine(int(page.left() + 0.9 * s), int(y), int(page.right() - 0.9 * s - (n % 3) * 0.6 * s), int(y))


def draw_levels(p, r, levels):
    y = r.top()
    for n, lv in enumerate(levels[:6]):
        import re
        txt = re.sub(r"%\d", "1", str(lv.get("text") or ""))
        x = r.left() + n * 18
        p.setFont(_font("", 11 - n * 0.6, n == 0)); p.setPen(QColor(D.tokens()["text"]))
        p.drawText(QRectF(x, y, r.width() - n * 18, 24), Qt.AlignLeft | Qt.AlignVCenter, f"{txt}  {lv.get('style') or f'Level {n + 1}'}")
        y += 26
    if not levels:
        draw_card(p, r, "No levels", [])


def draw_toc(p, r, v):
    p.setFont(_font("", 12, True)); p.setPen(QColor(D.tokens()["text"]))
    p.drawText(QRectF(r.left(), r.top(), r.width(), 24), Qt.AlignLeft, "Table of Contents")
    y = r.top() + 32
    for lvl, txt, pg in ((1, "1 Technical approach", 1), (2, "1.1 System design", 2), (2, "1.2 Test and verification", 4),
                         (1, "2 Management approach", 6), (2, "2.1 Schedule", 7)):
        x = r.left() + (lvl - 1) * 16
        p.setFont(_font("", 9, lvl == 1))
        p.drawText(QRectF(x, y, r.width(), 18), Qt.AlignLeft | Qt.AlignVCenter, txt)
        p.drawText(QRectF(r.left(), y, r.width(), 18), Qt.AlignRight | Qt.AlignVCenter, str(pg))
        p.setPen(QPen(QColor("#9aa3b2"), 1, Qt.DotLine))
        tw = p.fontMetrics().horizontalAdvance(txt)
        p.drawLine(int(x + tw + 6), int(y + 13), int(r.right() - 16), int(y + 13))
        p.setPen(QColor(D.tokens()["text"]))
        y += 22
    p.setFont(_font("", 7.5)); p.setPen(QColor(D.tokens()["muted"]))
    p.drawText(QRectF(r.left(), y + 8, r.width(), 40), Qt.AlignLeft | Qt.TextWordWrap, " ".join(v.get("switches") or []))


def draw_captions(p, r, caps):
    y = r.top()
    for c in caps[:6]:
        sep = c.get("separator") or "-"
        num = f"1{sep}1" if c.get("chapter_level") else "1"
        txt = f"{c.get('label') or 'Table'} {num}. A sample caption ({c.get('part') or 'body'}, {c.get('position') or 'above'})"
        p.setFont(_font("", 9, True)); p.setPen(QColor(D.tokens()["text"]))
        p.drawText(QRectF(r.left(), y, r.width(), 22), Qt.AlignLeft | Qt.AlignVCenter, txt)
        y += 26


def draw_pagination(p, r, v):
    y = r.top()
    p.setFont(_font("", 10, True)); p.setPen(QColor(D.tokens()["text"]))
    p.drawText(QRectF(r.left(), y, r.width(), 20), Qt.AlignLeft, v.get("name") or "Pagination")
    y += 28
    for part in v.get("parts") or []:
        nums = part.get("numbers") or {}
        fmt = {"lowerRoman": "i, ii, iii", "upperRoman": "I, II, III", "decimal": "1, 2, 3", "upperLetter": "A, B, C"}.get(nums.get("fmt"), "no numbers")
        restart = ", starts again" if nums.get("start") else ""
        p.setFont(_font("", 9))
        p.drawText(QRectF(r.left(), y, r.width(), 20), Qt.AlignLeft | Qt.AlignVCenter,
                   f"{part.get('name') or part.get('key')}: {fmt}{restart}")
        y += 22
