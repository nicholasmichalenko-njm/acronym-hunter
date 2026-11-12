"""The fictional commented PDFs for Redline's comments (4.16.0; claude/stationkeeper-pdf-comments-plan-4.16.html).

Writes test_samples/comments/: C01_prose.docx (python-docx) and its PDF (LibreOffice), then for each base PDF a copy
with comments written the way Acrobat writes them (pypdf, this tool only; nothing ships with it):
- markups (Highlight, Underline, StrikeOut) carry QuadPoints in Acrobat's order (top left, top right, bottom left, bottom
  right per line), drawn from the letters' loose boxes (ascent to descent), as Acrobat does from a text selection;
- Insert text is a Caret (Subj "Inserted Text") below the line at the letter; Replace text is a StrikeOut with IRT to a
  Caret and RT /Group, the new words in the Caret's Contents;
- a sticky note is a Text annotation with a Popup; a reply is a Text annotation with IRT; a review status is a Text
  annotation with IRT, State and StateModel /Review;
- a text callout is a FreeText /FreeTextCallout with CL and an appearance stream (its box and its line, as Acrobat draws
  them); a shape is a Square; a stamp is a Stamp /Name /Approved.
comments_truth.json holds each comment's right answer. Fictional content only (the Kestrel program).
Run: python tools/make_comment_fixtures.py"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "test_samples", "comments")
WHEN = "D:20261103091500-07'00'"


def prose_docx(path):
    from docx import Document
    from docx.shared import Pt
    d = Document()
    sec = d.sections[0]
    sec.header.paragraphs[0].text = "Kestrel Ground Station RFP - Section L"
    sec.footer.paragraphs[0].text = "Fictional sample for testing"
    st = d.styles["Normal"]; st.font.name = "Liberation Serif"; st.font.size = Pt(11)
    H = lambda t, n=1: d.add_heading(t, n)                                   # noqa: E731
    P = d.add_paragraph
    H("L.1 General Instructions")
    P("The Contractor shall deliver the Kestrel test plan within 30 days after award. The test plan describes how each "
      "requirement of the Kestrel ground station is verified, who witnesses each test, and how the results are reported "
      "to the Government.")
    P("All deliverables shall be are reviewed by the program office before release. Reports are due monthly and follow "
      "the format in Attachment J-4.")
    H("L.2 Proposal Organization", 2)
    P("The offeror shall submit two copies of each volume. Each volume begins with a cover page and a table of contents. "
      "The requirements of Section M apply to every volume, and the requirements of this section apply to the format.")
    P("The schedule is fixed. Volume I holds the technical approach; Volume II holds the management approach; Volume III "
      "holds the price.")
    for t in ("(a) The technical volume shall not exceed 25 pages.",
              "(b) The management volume shall not exceed 15 pages.",
              "(c) The price volume has no page limit."):
        P(t)
    H("L.3 Page Limits and Format", 2)
    P("Section L.3 sets the page limit for each volume. Pages are 8.5 by 11 inches with one inch margins. Text is 11 point "
      "or larger; tables and figures may use 8 point.")
    P("The site survey is in Ridgeline. The offeror may visit the Ridgeline site once before proposals are due, with the "
      "contracting officer's approval.")
    t = d.add_table(rows=4, cols=3); t.style = "Table Grid"
    for r, row in enumerate((("Volume", "Title", "Page limit"), ("I", "Technical approach", "25 pages"),
                             ("II", "Management approach", "15 pages"), ("III", "Price", "No limit"))):
        for c, v in enumerate(row):
            t.cell(r, c).text = v
    P("")
    H("L.4 Questions", 2)
    for i in range(6):
        P(f"Question period {i + 1}. Offerors may send questions about the Kestrel ground station to the contracting "
          "officer by electronic mail. Each question names the section and paragraph it is about, and the Government "
          "answers every question in writing to all offerors at the same time.")
    P("The Kestrel test plan is reviewed again at the critical design review.")
    d.save(path)


def to_pdf(docx, pdf):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", td, docx], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(os.path.join(td, os.path.splitext(os.path.basename(docx))[0] + ".pdf"), pdf)


class Page:
    """A page's letters through PDFium: text, and each letter's loose box in PDF space (y up)."""
    def __init__(self, pdf, pi):
        import pypdfium2 as pdfium
        import pypdfium2.raw as R
        import ctypes
        self.doc = pdfium.PdfDocument(pdf)
        pg = self.doc[pi]
        self.w, self.h = pg.get_size()
        tp = pg.get_textpage()
        n = tp.count_chars()
        self.text = tp.get_text_range(0, n) if n else ""
        self.boxes = []
        for k in range(min(n, len(self.text))):
            r = R.FS_RECTF()
            R.FPDFText_GetLooseCharBox(tp.raw, k, ctypes.byref(r))
            self.boxes.append((r.left, r.bottom, r.right, r.top))
        tp.close()

    def find(self, s, nth=0):
        """Letter indexes of the nth time s appears (spaces in s match any run of spaces and line breaks)."""
        import re
        pat = r"\s+".join(re.escape(x) for x in s.split())
        ms = list(re.finditer(pat, self.text))
        m = ms[nth]
        return m.start(), m.end()

    def quads(self, a, b):
        """Acrobat's QuadPoints for letters a..b-1: one quad per line."""
        lines, cur = [], []
        for k in range(a, b):
            if self.text[k] in "\r\n":
                continue
            bx = self.boxes[k]
            if bx[2] - bx[0] <= 0 and self.text[k].isspace():
                continue
            if cur and abs(bx[1] - self.boxes[cur[-1]][1]) > 2:
                lines.append(cur); cur = []
            cur.append(k)
        if cur:
            lines.append(cur)
        q = []
        for ln in lines:
            bs = [self.boxes[k] for k in ln if not self.text[k].isspace()] or [self.boxes[k] for k in ln]
            l, r = min(x[0] for x in bs), max(x[2] for x in bs)
            bot, top = min(x[1] for x in bs), max(x[3] for x in bs)
            q += [l, top, r, top, l, bot, r, bot]
        return q

    def caret_at(self, k):
        """An Acrobat caret's Rect for an insert before letter k (after k-1 when k ends the text)."""
        bx = self.boxes[k] if k < len(self.boxes) and not self.text[k].isspace() else self.boxes[k - 1]
        x = bx[0] if k < len(self.boxes) and not self.text[k].isspace() else bx[2]
        if k < len(self.text) and self.text[k].isspace():
            x = self.boxes[k - 1][2]
        bot = bx[1]
        return [x - 4.5, bot - 3.0, x + 4.5, bot + 5.0]


def _rect_of(q, pad=1.0):
    xs, ys = q[0::2], q[1::2]
    return [min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad]


class Writer:
    """Acrobat-shaped annotations added to a PDF with pypdf."""
    def __init__(self, src):
        from pypdf import PdfReader, PdfWriter
        self.w = PdfWriter(clone_from=PdfReader(src))
        self.n = 0

    def _base(self, pi, sub, rect, author, note, subj, flags=4, extra=None):
        from pypdf.generic import (ArrayObject, DictionaryObject, FloatObject, NameObject, NumberObject, TextStringObject)
        self.n += 1
        page = self.w.pages[pi]
        d = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject(sub),
            NameObject("/Rect"): ArrayObject([FloatObject(round(v, 3)) for v in rect]),
            NameObject("/T"): TextStringObject(author), NameObject("/M"): TextStringObject(WHEN),
            NameObject("/CreationDate"): TextStringObject(WHEN), NameObject("/F"): NumberObject(flags),
            NameObject("/NM"): TextStringObject(f"kestrel-{self.n:04d}"), NameObject("/Subj"): TextStringObject(subj),
            NameObject("/P"): page.indirect_reference})
        if note is not None:
            d[NameObject("/Contents")] = TextStringObject(note)
        for k, v in (extra or {}).items():
            d[NameObject(k)] = v
        ref = self.w._add_object(d)
        if "/Annots" not in page:
            page[NameObject("/Annots")] = ArrayObject()
        page["/Annots"].append(ref)
        if sub in ("/Text", "/Highlight", "/Underline", "/StrikeOut", "/Caret", "/Square", "/Stamp"):
            pop = DictionaryObject({NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Popup"),
                                    NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (rect[2] + 10, rect[1] - 80, rect[2] + 190, rect[1] + 20)]),
                                    NameObject("/Parent"): ref, NameObject("/Open"): __import__("pypdf").generic.BooleanObject(False),
                                    NameObject("/F"): NumberObject(28)})
            pref = self.w._add_object(pop)
            d[NameObject("/Popup")] = pref
            page["/Annots"].append(pref)
        return ref

    def markup(self, pi, sub, quads, author, note, subj, color, extra=None):
        from pypdf.generic import ArrayObject, FloatObject, NameObject
        ex = {"/QuadPoints": ArrayObject([FloatObject(round(v, 3)) for v in quads]),
              "/C": ArrayObject([FloatObject(c) for c in color]), "/CA": FloatObject(1)}
        ex.update(extra or {})
        return self._base(pi, sub, _rect_of(quads), author, note, subj, extra=ex)

    def caret(self, pi, rect, author, text, subj="Inserted Text"):
        from pypdf.generic import ArrayObject, FloatObject, NameObject
        return self._base(pi, "/Caret", rect, author, text, subj, extra={
            "/C": ArrayObject([FloatObject(0), FloatObject(0), FloatObject(1)]), "/Sy": NameObject("/None"),
            "/RD": ArrayObject([FloatObject(0)] * 4)})

    def note(self, pi, x, y, author, text, irt=None, state=None):
        from pypdf.generic import NameObject, TextStringObject
        ex = {"/Name": NameObject("/Comment")}
        if irt is not None:
            ex["/IRT"] = irt
        if state:
            ex["/State"] = TextStringObject(state); ex["/StateModel"] = TextStringObject("Review")
        return self._base(pi, "/Text", [x, y - 20, x + 20, y], author, text, "Sticky Note",
                          flags=(30 if state else 28), extra=ex)

    def callout(self, pi, box, tip, knee, author, text):
        """Acrobat's text callout: its box, a line from the box to the tip, an appearance stream drawing both."""
        from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject
        xs = [box[0], box[2], tip[0], knee[0]]; ys = [box[1], box[3], tip[1], knee[1]]
        rect = [min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2]
        ap = DecodedStreamObject()
        ap.set_data((f"1 0 0 RG 1 w {box[0]:.2f} {box[1]:.2f} {box[2] - box[0]:.2f} {box[3] - box[1]:.2f} re S "
                     f"{tip[0]:.2f} {tip[1]:.2f} m {knee[0]:.2f} {knee[1]:.2f} l {box[0]:.2f} {(box[1] + box[3]) / 2:.2f} l S").encode())
        ap.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Form"),
                   NameObject("/BBox"): ArrayObject([FloatObject(v) for v in rect])})
        apref = self.w._add_object(ap)
        ex = {"/IT": NameObject("/FreeTextCallout"),
              "/CL": ArrayObject([FloatObject(v) for v in (tip[0], tip[1], knee[0], knee[1], box[0], (box[1] + box[3]) / 2)]),
              "/DA": __import__("pypdf").generic.TextStringObject("0 0 1 rg /Helv 10 Tf"),
              "/AP": DictionaryObject({NameObject("/N"): apref})}
        return self._base(pi, "/FreeText", rect, author, text, "Callout", extra=ex)

    def square(self, pi, rect, author, text):
        from pypdf.generic import ArrayObject, FloatObject
        return self._base(pi, "/Square", rect, author, text, "Rectangle",
                          extra={"/C": ArrayObject([FloatObject(1), FloatObject(0), FloatObject(0)])})

    def stamp(self, pi, rect, author):
        from pypdf.generic import NameObject
        return self._base(pi, "/Stamp", rect, author, None, "Approved", extra={"/Name": NameObject("/Approved")})

    def save(self, path):
        with open(path, "wb") as f:
            self.w.write(f)


YEL, BLU, RED = (1, 0.82, 0), (0, 0.4, 1), (1, 0, 0)
A, B, C = "Dana Whitfield", "Marcus Reyes", "Priya Natarajan"


def _word_box(pg, s, nth=0):
    a, b = pg.find(s, nth)
    q = pg.quads(a, b)
    return _rect_of(q, 0)


def comment_prose(base, out):
    """C01: every Acrobat markup on the prose document. Returns the truth."""
    wr, truth = Writer(base), []
    pages = {}

    def pg(i):
        if i not in pages:
            pages[i] = Page(base, i)
        return pages[i]

    def mark(i, kind, s, nth=0, note=None, author=A, sub=None, part=None, expect=None, near=None):
        p = pg(i)
        a, b = p.find(s, nth)
        if part:                                                     # a piece inside the found text
            off = p.text[a:b].index(part)
            a, b = a + off, a + off + len(part)
        sub = sub or {"highlight": "/Highlight", "underline": "/Underline", "strike": "/StrikeOut"}[kind]
        color = {"/Highlight": YEL, "/Underline": BLU, "/StrikeOut": RED}[sub]
        subj = {"/Highlight": "Highlight", "/Underline": "Underline", "/StrikeOut": "Cross-Out"}[sub]
        ref = wr.markup(i, sub, p.quads(a, b), author, note, subj, color)
        return ref, a, b

    r1, *_ = mark(0, "highlight", "Kestrel test plan", 0, note="Which test plan revision?")
    truth.append({"id": "hl_note", "page": 1, "want": "comment", "words": "Kestrel test plan", "note": "Which test plan revision?", "author": A})
    wr.note(0, 50, 700, B, "Revision C, per the draft.", irt=r1)
    truth.append({"id": "reply", "page": 1, "want": "reply", "to": "hl_note", "note": "Revision C, per the draft.", "author": B})
    wr.note(0, 50, 700, A, "Completed", irt=r1, state="Completed")
    truth.append({"id": "status", "page": 1, "want": "done", "to": "hl_note"})
    mark(0, "highlight", "who witnesses each test, and how the results are reported to the Government", 0, note=None)
    truth.append({"id": "hl_lines", "page": 1, "want": "comment", "words": "who witnesses each test, and how the results are reported to the Government",
                  "note": "Highlighted", "author": A})
    mark(0, "strike", "shall be are reviewed", part="shall be", note=None, author=B)
    truth.append({"id": "strike", "page": 1, "want": "delete", "words": "shall be", "accepted": "All deliverables are reviewed", "author": B})
    ru, *_ = mark(0, "underline", "Reports are due monthly", part="monthly", note="Monthly or quarterly?")
    truth.append({"id": "underline", "page": 1, "want": "comment", "words": "monthly", "note": "Monthly or quarterly?", "author": A})
    wr.note(0, 50, 650, C, "Accepted", irt=ru, state="Accepted")
    truth.append({"id": "accepted", "page": 1, "want": "reply", "to": "underline", "note": "Marked Accepted", "author": C})
    p0 = pg(0)
    a, b = p0.find("submit two copies")
    k = a + p0.text[a:b].index("two")
    st = wr.markup(0, "/StrikeOut", p0.quads(k, k + 3), C, None, "Cross-Out", RED)
    cr = wr.caret(0, p0.caret_at(k + 3), C, "three")
    wr.w.get_object(st)[__import__("pypdf").generic.NameObject("/IRT")] = cr
    wr.w.get_object(st)[__import__("pypdf").generic.NameObject("/RT")] = __import__("pypdf").generic.NameObject("/Group")
    truth.append({"id": "replace", "page": 1, "want": "replace", "words": "two", "insert": "three",
                  "accepted": "The offeror shall submit three copies of each volume", "author": C})
    mark(0, "highlight", "program office", note="program office", author=C)          # Acrobat copied the words into the note
    truth.append({"id": "hl_copied", "page": 1, "want": "comment", "words": "program office", "note": "Highlighted", "author": C})
    a, b = p0.find("Attachment J-4.")
    wr.caret(0, p0.caret_at(a + len("Attachment J-4")), A, "and J-5")
    truth.append({"id": "insert_end", "page": 1, "want": "insert", "insert": "and J-5", "accepted": "the format in Attachment J-4 and J-5.", "author": A})
    a, b = p0.find("The schedule is fixed")
    k = a + len("The ")
    wr.caret(0, p0.caret_at(k), B, "revised")
    truth.append({"id": "insert", "page": 1, "want": "insert", "insert": "revised", "accepted": "The revised schedule is fixed", "author": B})
    a, b = p0.find("The requirements of Section M")
    k = a + p0.text[a:b].index("requirements") + len("requirement")
    wr.markup(0, "/StrikeOut", p0.quads(k, k + 1), B, None, "Cross-Out", RED)
    truth.append({"id": "strike_letter", "page": 1, "want": "delete", "words": "s", "accepted": "The requirement of Section M", "author": B})
    a, b = p0.find("the requirements of this section")
    mark(0, "highlight", "the requirements of this section", 0, note="Which section: L or M?", author=C)
    truth.append({"id": "hl_twice", "page": 1, "want": "comment", "words": "the requirements of this section",
                  "note": "Which section: L or M?", "author": C, "context": "apply to the format"})
    mark(0, "highlight", "Offerors may send questions about the Kestrel ground station", 1, note="Is e-mail the only way?", author=B)
    truth.append({"id": "same_twice", "page": 1, "want": "comment", "words": "Offerors may send questions about the Kestrel ground station",
                  "note": "Is e-mail the only way?", "author": B, "context": "Question period 2."})
    hb = _word_box(p0, "Kestrel Ground Station RFP")
    wr.markup(0, "/Highlight", p0.quads(*p0.find("Kestrel Ground Station RFP")), A, "Header says RFP; the cover says draft RFP.", "Highlight", YEL)
    truth.append({"id": "header", "page": 1, "want": "comment", "note": "Header says RFP; the cover says draft RFP.", "author": A,
                  "how": "position", "near": "L.1 General Instructions"})
    p1i = 0
    for i in range(len(wr.w.pages)):
        try:
            pg(i).find("Section L.3 sets the page limit"); p1i = i; break
        except IndexError:
            continue
    pp = pg(p1i)
    lb = _word_box(pp, "Section L.3 sets the page limit")
    wr.note(p1i, lb[0] - 28, lb[3] + 2, A, "Confirm 25 pages for Volume I.")
    truth.append({"id": "sticky", "page": p1i + 1, "want": "comment", "note": "Confirm 25 pages for Volume I.", "author": A,
                  "how": "position", "near": "Section L.3 sets the page limit"})
    sb = _word_box(pp, "Ridgeline", 0)
    box = (pp.w - 150, sb[3] + 30, pp.w - 40, sb[3] + 60)
    wr.callout(p1i, box, ((sb[0] + sb[2]) / 2, sb[3]), (box[0] - 20, (box[1] + box[3]) / 2), B, "Wrong site: the survey is at Ridgeline North.")
    truth.append({"id": "callout", "page": p1i + 1, "want": "comment", "note": "Wrong site: the survey is at Ridgeline North.", "author": B,
                  "how": "position", "words": "Ridgeline"})
    vb = _word_box(pp, "Pages are 8.5 by 11 inches")
    wr.square(p1i, [vb[0] - 2, vb[1] - 2, vb[2] + 2, vb[3] + 2], C, "Check this against Attachment J-2.")
    truth.append({"id": "square", "page": p1i + 1, "want": "comment", "note": "Check this against Attachment J-2.", "author": C,
                  "how": "position", "words": "Pages are 8.5 by 11 inches"})
    tb = _word_box(pp, "Management approach")
    mark(p1i, "highlight", "Management approach", note="Rename to Management volume?", author=B)
    truth.append({"id": "cell", "page": p1i + 1, "want": "comment", "words": "Management approach", "note": "Rename to Management volume?", "author": B})
    a, b = pp.find("No limit")
    wr.markup(p1i, "/StrikeOut", pp.quads(a, a + 2), C, "Price has a limit now.", "Cross-Out", RED)
    truth.append({"id": "cell_strike", "page": p1i + 1, "want": "delete", "words": "No", "note": "Price has a limit now.", "author": C,
                  "accepted": "limit"})
    last = len(wr.w.pages) - 1
    pl = pg(last)
    a, b = pl.find("Kestrel test plan")
    wr.markup(last, "/Highlight", pl.quads(a, b), A, "Same plan as L.1.", "Highlight", YEL)
    truth.append({"id": "hl_last", "page": last + 1, "want": "comment", "words": "Kestrel test plan", "note": "Same plan as L.1.",
                  "author": A, "context": "reviewed again at the critical design review"})
    stb = _word_box(pl, "reviewed again")
    wr.stamp(last, [stb[2] + 20, stb[1] - 10, stb[2] + 120, stb[3] + 20], C)
    truth.append({"id": "stamp", "page": last + 1, "want": "comment", "note": "Stamp: Approved", "author": C, "how": "position",
                  "near": "reviewed again at the critical design review"})
    wr.save(out)
    return truth


def comment_slides(base, out):
    wr, truth = Writer(base), []
    p = Page(base, 1)
    import re
    words = [m.group(0) for m in re.finditer(r"\S+", p.text)]
    title = p.text.split("\r\n")[0].strip() if "\r\n" in p.text else p.text.split("\n")[0].strip()
    tw = title.split()[-1]
    a, b = p.find(tw)
    wr.markup(1, "/StrikeOut", p.quads(a, b), B, None, "Cross-Out", RED)
    truth.append({"id": "s_title", "page": 2, "want": "delete", "words": tw, "author": B})
    long = max((ln.strip() for ln in re.split(r"[\r\n]+", p.text) if len(ln.split()) >= 4), key=len)
    phrase = " ".join(long.split()[1:4])
    a, b = p.find(phrase)
    wr.markup(1, "/Highlight", p.quads(a, b), A, "Is this still true for Block 2?", "Highlight", YEL)
    truth.append({"id": "s_hl", "page": 2, "want": "comment", "words": phrase, "note": "Is this still true for Block 2?", "author": A})
    wr.note(1, p.w - 60, p.h / 2, C, "Chart needs a source line.")
    truth.append({"id": "s_note", "page": 2, "want": "comment", "note": "Chart needs a source line.", "author": C, "how": "position"})
    wr.save(out)
    return truth


def comment_tables(f06, f13, out06, out13):
    """Comments in table cells: across a wrapped cell's lines, across two cells, a cell on a later page of a long table."""
    truth = {}
    wr, t = Writer(f06), []
    p = Page(f06, 0)
    a, b = p.find("plan for integrating legacy telemetry")
    wr.markup(0, "/Highlight", p.quads(a, b), A, "Name the legacy systems.", "Highlight", YEL)
    t.append({"id": "t_wrap", "page": 1, "want": "comment", "words": "plan for integrating legacy telemetry", "note": "Name the legacy systems.", "author": A})
    a, b = p.find("integration carries")
    wr.markup(0, "/StrikeOut", p.quads(a + len("integration "), b), B, None, "Cross-Out", RED)
    t.append({"id": "t_strike", "page": 1, "want": "delete", "words": "carries", "author": B})
    a, b = p.find("Management Key")
    wr.markup(0, "/Highlight", p.quads(a, b), C, "Two cells: one comment.", "Highlight", YEL)
    t.append({"id": "t_cells", "page": 1, "want": "comment", "words": "Management Key", "note": "Two cells: one comment.", "author": C})
    wr.save(out06)
    truth[os.path.basename(out06)] = {"base": "../fidelity/pdf_word_tagged/F06_wrapped_cells.pdf", "comments": t}
    wr, t = Writer(f13), []
    p = Page(f13, 1)
    a, b = p.find("Kestrel spare part number 45")
    wr.markup(1, "/Highlight", p.quads(a, b), A, "Part 45 is out of stock.", "Highlight", YEL)
    t.append({"id": "t_page2", "page": 2, "want": "comment", "words": "Kestrel spare part number 45", "note": "Part 45 is out of stock.",
              "author": A})
    a, b = p.find("Kestrel spare part number 47")
    k = a + len("Kestrel spare part number 4")
    wr.markup(1, "/StrikeOut", p.quads(k, k + 1), B, None, "Cross-Out", RED)
    cr = wr.caret(1, p.caret_at(k + 1), B, "8")
    from pypdf.generic import NameObject
    so = wr.w.pages[1]["/Annots"][-4].get_object()
    so[NameObject("/IRT")] = cr; so[NameObject("/RT")] = NameObject("/Group")
    t.append({"id": "t_replace", "page": 2, "want": "replace", "words": "7", "insert": "8", "accepted": "Kestrel spare part number 48", "author": B})
    wr.save(out13)
    truth[os.path.basename(out13)] = {"base": "../fidelity/pdf_word_tagged/F13_header_repeat.pdf", "comments": t}
    return truth


def main():
    os.makedirs(OUT, exist_ok=True)
    dx = os.path.join(OUT, "C01_prose.docx")
    prose_docx(dx)
    base = os.path.join(OUT, "C01_prose.pdf")
    to_pdf(dx, base)
    truth = {"C01_prose_commented.pdf": {"base": "C01_prose.pdf", "comments": comment_prose(base, os.path.join(OUT, "C01_prose_commented.pdf"))}}
    deck = os.path.join(ROOT, "test_samples", "fidelity", "pdf_ppt", "S01_deck_16x9.pdf")
    if os.path.isfile(deck):
        truth["S01_deck_commented.pdf"] = {"base": "../fidelity/pdf_ppt/S01_deck_16x9.pdf",
                                           "comments": comment_slides(deck, os.path.join(OUT, "S01_deck_commented.pdf"))}
    tg = os.path.join(ROOT, "test_samples", "fidelity", "pdf_word_tagged")
    if os.path.isfile(os.path.join(tg, "F06_wrapped_cells.pdf")):
        truth.update(comment_tables(os.path.join(tg, "F06_wrapped_cells.pdf"), os.path.join(tg, "F13_header_repeat.pdf"),
                                    os.path.join(OUT, "T01_cells_commented.pdf"), os.path.join(OUT, "T02_long_table_commented.pdf")))
    with open(os.path.join(OUT, "comments_truth.json"), "w", encoding="utf-8") as f:
        json.dump(truth, f, indent=1)
    print({k: len(v["comments"]) for k, v in truth.items()})


if __name__ == "__main__":
    main()
