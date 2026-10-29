"""Where a term was found, zoomed in (2.86.0): the spot on the page in the term's card, so the reviewer sees how the term
is used before deciding. A PDF shows a picture of the lines around the term with the term outlined; a Word file shows
the paragraph before, the paragraph with the term highlighted, and the paragraph after. Previous and Next step through
every place it was found. Files are only read. Rules only (No AI); nothing leaves the PC."""
import html, os, re, zipfile
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from . import design as D

PAGE = re.compile(r"\(p\.(\d+)")
PARA = re.compile(r"\((?:[^()]*?)para (\d+)")


def parse_loc(loc):
    """'Section L.pdf (p.3)' -> ('Section L.pdf', 3, None); 'Vol I.docx (para 12)' -> ('Vol I.docx', None, 12)."""
    name = (loc or "").split(" (")[0].strip()
    m, n = PAGE.search(loc or ""), PARA.search(loc or "")
    return name, (int(m.group(1)) if m else None), (int(n.group(1)) if n else None)


def pdf_zoom(path, page_no, term, scale=2.0, around=70):
    """A QImage of the lines around the first place the term is on that page, the term outlined; None if not found."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[page_no - 1]
        w, h = page.get_size()
        tp = page.get_textpage()
        box = None
        for case in (True, False):
            s = tp.search(term, match_case=case, match_whole_word=True)
            hit = s.get_next()
            if hit:
                i, n = hit
                rects = [tp.get_charbox(k) for k in range(i, i + n)]
                box = (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))
                break
        if box is None:
            return None
        l, b, r, t = box
        top = min(h, t + around)
        bot = max(0, b - around)
        crop = (0, bot, 0, h - top)                                      # left, bottom, right, top: points cut off each side
        img = page.render(scale=scale, crop=crop).to_pil().convert("RGB")
        from PIL import ImageDraw
        dr = ImageDraw.Draw(img)
        x0, x1 = l * scale - 3, r * scale + 3
        y0, y1 = (top - t) * scale - 3, (top - b) * scale + 3
        dr.rectangle([x0, y0, x1, y1], outline=(245, 158, 11), width=3)
        q = QImage(img.tobytes("raw", "RGB"), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
        return q
    finally:
        doc.close()


def _docx_paras(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        out.append(html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))))
    return [x for x in out if x.strip()]


def docx_snippet(path, para, term):
    """HTML: the paragraph with the term highlighted, and the ones either side; None if the term is not there."""
    paras = _docx_paras(path)
    idx = None
    if para and 0 < para <= len(paras) and term in paras[para - 1]:
        idx = para - 1
    if idx is None:
        idx = next((k for k, x in enumerate(paras) if re.search(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", x)), None)
    if idx is None:
        return None
    t = D.tokens()
    mark = lambda s: re.sub(r"(?<![\w-])(" + re.escape(term) + r")(?![\w-])",                      # noqa: E731
                            rf"<span style='background:{t['warn_soft']};outline:2px solid {t['warn']};font-weight:700'>\1</span>",
                            html.escape(s))
    parts = []
    if idx > 0:
        parts.append(f"<p style='color:{t['muted']}'>{html.escape(paras[idx - 1][:400])}</p>")
    parts.append(f"<p>{mark(paras[idx][:900])}</p>")
    if idx + 1 < len(paras):
        parts.append(f"<p style='color:{t['muted']}'>{html.escape(paras[idx + 1][:400])}</p>")
    return "".join(parts)


class WhereView(QWidget):
    """The zoomed spot, with Previous and Next through the places a term was found."""

    def __init__(self, term, locs, path_of):
        super().__init__()
        self.term, self.locs, self.path_of, self.k = term, list(locs), path_of, 0
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(4)
        nav = QHBoxLayout(); v.addLayout(nav)
        self.where = D.label("", "muted"); nav.addWidget(self.where, 1)
        self.b_prev = D.button("Previous", "ghost", lambda: self.go(-1)); nav.addWidget(self.b_prev)
        self.b_next = D.button("Next place", "ghost", lambda: self.go(1)); nav.addWidget(self.b_next)
        self.pic = QLabel(); self.pic.setAlignment(Qt.AlignLeft | Qt.AlignTop); self.pic.setWordWrap(True)
        self.pic.setTextFormat(Qt.RichText)
        t = D.tokens()
        self.pic.setStyleSheet(f"background:{t['surface2']};border:1px solid {t['border']};border-radius:{D.RADIUS['control']}px;padding:6px")
        v.addWidget(self.pic)
        self.show_k()

    def go(self, d):
        if self.locs:
            self.k = (self.k + d) % len(self.locs)
            self.show_k()

    def show_k(self):
        n = len(self.locs)
        self.b_prev.setEnabled(n > 1); self.b_next.setEnabled(n > 1)
        if not n:
            self.where.setText("No place recorded."); self.pic.setText("")
            return
        loc = self.locs[self.k]
        self.where.setText(f"{self.k + 1} of {n}: {loc}")
        self.state = "none"
        try:
            name, page, para = parse_loc(loc)
            path = self.path_of(name)
            if not path or not os.path.isfile(path):
                self.pic.setText(f"{html.escape(name)} is not on this PC, so the spot cannot be shown.")
                return
            if path.lower().endswith(".pdf") and page:
                img = pdf_zoom(path, page, self.term)
                if img is not None:
                    pm = QPixmap.fromImage(img)
                    if pm.width() > 520:
                        pm = pm.scaledToWidth(520, Qt.SmoothTransformation)
                    self.pic.setPixmap(pm)
                    self.state = "picture"
                    return
            if path.lower().endswith(".docx"):
                sn = docx_snippet(path, para, self.term)
                if sn:
                    self.pic.setText(sn)
                    self.state = "text"
                    return
            self.pic.setText("The term is in a picture or a part of the file the zoom cannot show; the place is listed below.")
        except Exception:
            import diag
            diag.swallowed()
            self.pic.setText("The spot could not be shown; the place is listed below.")
