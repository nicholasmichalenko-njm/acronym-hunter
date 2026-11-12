"""The fictional PDF for Prepare for redline's look (4.22.0): a solicitation with a cover (a banner, a logo, a picture,
a band at the foot), a running header with a rule, a footer with the page number and the logo, a ruled table, a figure
with its caption, headings in another font, and text that runs across pages. And the same PDF with a reviewer's
comments, written the way Acrobat writes them (tools/make_comment_fixtures.py's writer).

Writes test_samples/redline/R01_cover_figure.pdf, test_samples/comments/R01_cover_figure_commented.pdf, and its right
answers into test_samples/comments/comments_truth.json (the other entries are kept).
reportlab, Pillow and pypdf are used by this tool only; nothing ships with it. Fictional content only (the Kestrel
program). Run: python tools/make_redline_fixtures.py"""
import json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tools"))
OUT = os.path.join(ROOT, "test_samples", "redline")
COM = os.path.join(ROOT, "test_samples", "comments")
NAME = "R01_cover_figure"


def pictures(folder):
    """A drawn 'photograph' (a dish on a ridge) and a logo, as PNG files."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (840, 520), (203, 222, 240))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 520), (0, 380), (220, 300), (460, 360), (700, 280), (840, 330), (840, 520)], fill=(92, 120, 84))
    d.rectangle((400, 250, 420, 360), fill=(70, 70, 76))
    d.pieslice((320, 150, 500, 330), 200, 340, fill=(236, 236, 240), outline=(60, 60, 66), width=4)
    d.ellipse((640, 60, 720, 140), fill=(250, 226, 150))
    photo = os.path.join(folder, "photo.png"); im.save(photo)
    lg = Image.new("RGBA", (240, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(lg)
    d.ellipse((10, 20, 90, 100), fill=(200, 16, 46, 255))
    d.polygon([(50, 30), (78, 88), (22, 88)], fill=(255, 255, 255, 255))
    d.rectangle((104, 44, 228, 56), fill=(255, 255, 255, 255)); d.rectangle((104, 68, 196, 80), fill=(255, 255, 255, 255))
    logo = os.path.join(folder, "logo.png"); lg.save(logo)
    return photo, logo


def build(out, img, img2):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer,
                                    Table, TableStyle)
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["Normal"], fontName="Times-Roman", fontSize=11, leading=13.5, spaceAfter=7, alignment=4)
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=15, spaceBefore=10, spaceAfter=8,
                        textColor=colors.HexColor("#1f3a6e"))
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceBefore=8, spaceAfter=6)
    cap = ParagraphStyle("cap", parent=body, fontName="Helvetica-Oblique", fontSize=9, alignment=1)
    title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=28, leading=34, alignment=1, textColor=colors.HexColor("#1f3a6e"))
    sub = ParagraphStyle("s", fontName="Helvetica", fontSize=14, leading=20, alignment=1)

    def cover(c, d):
        c.saveState(); c.setFillColor(colors.HexColor("#1f3a6e")); c.rect(0, letter[1] - 90, letter[0], 90, stroke=0, fill=1)
        c.drawImage(img2, 54, letter[1] - 78, width=120, height=60, mask="auto")
        c.setFillColor(colors.HexColor("#c8102e")); c.rect(0, 0, letter[0], 36, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Helvetica", 9)
        c.drawCentredString(letter[0] / 2, 14, "Kestrel Ground Systems Program Office")
        c.restoreState()

    def later(c, d):
        c.saveState(); c.setFont("Helvetica", 8); c.setFillColor(colors.grey)
        c.drawString(72, letter[1] - 48, "Solicitation KGS-26-R-0007")
        c.drawRightString(letter[0] - 72, letter[1] - 48, "Section L: Instructions to Offerors")
        c.line(72, letter[1] - 54, letter[0] - 72, letter[1] - 54)
        c.drawCentredString(letter[0] / 2, 40, f"Page {d.page - 1}")
        c.drawImage(img2, letter[0] - 72 - 40, 30, width=40, height=20, mask="auto")
        c.restoreState()

    doc = BaseDocTemplate(out, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72, invariant=1)
    doc.addPageTemplates([PageTemplate("cover", [Frame(72, 72, letter[0] - 144, letter[1] - 190, id="c")], onPage=cover),
                          PageTemplate("body", [Frame(72, 64, letter[0] - 144, letter[1] - 136, id="b")], onPage=later)])
    P = lambda t, s=body: Paragraph(t, s)                                    # noqa: E731
    st = [Spacer(1, 60), P("Kestrel Ground Station Modernization", title), Spacer(1, 14), P("Request for Proposal KGS-26-R-0007", sub),
          Spacer(1, 30), Image(img, width=4.2 * inch, height=2.6 * inch), Spacer(1, 24), P("Issued 12 November 2026", sub),
          P("Proposals due 15 December 2026, 2:00 PM Mountain", sub), NextPageTemplate("body"), PageBreak(),
          P("L.1 General Instructions", h1),
          P("The Offeror shall submit its proposal in three volumes as described in this section. Each volume shall be complete "
            "in itself so that evaluation of one volume may be accomplished independently of the others. The Government will "
            "evaluate proposals in accordance with Section M of this solicitation."),
          P("L.1.1 Proposal Format", h2),
          P("Proposals shall be prepared on 8.5 by 11 inch pages with one inch margins. Text shall be no smaller than 11-point "
            "Times New Roman. Text in tables and figures shall be no smaller than 9-point. Page limits are stated in Table L-1 "
            "and shall not be exceeded."),
          Spacer(1, 6),
          Table([["Volume", "Title", "Page limit"], ["I", "Technical Approach", "25 pages"], ["II", "Management Approach", "15 pages"],
                 ["III", "Price", "No limit"]], colWidths=[1.0 * inch, 3.2 * inch, 1.6 * inch],
                style=TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe6f2")),
                                  ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10), ("FONT", (0, 1), (-1, -1), "Times-Roman", 10)])),
          P("Table L-1. Volumes and page limits", cap),
          P("L.2 Technical Volume", h1),
          P("The Offeror shall describe its approach to operating the Kestrel ground station twenty-four hours a day. The "
            "description shall address antenna scheduling, anomaly response and the transition from the incumbent system "
            "shown in Figure L-1."),
          Image(img, width=3.6 * inch, height=2.2 * inch), P("Figure L-1. Kestrel ground station architecture", cap),
          P("The Offeror shall identify the key personnel proposed for the effort and shall provide a resume for each. Resumes "
            "do not count against the page limit of Volume I."),
          P("L.2.1 Antenna Scheduling", h2)]
    for i in range(9):
        st.append(P("The Offeror shall explain how contacts are deconflicted across the antenna network, how priority missions "
                    "preempt routine contacts, and how the schedule is published to mission operations. Paragraph %d of the "
                    "scheduling discussion continues so that the text runs onto another page of the document." % (i + 1)))
    st += [P("L.3 Management Volume", h1),
           P("The Offeror shall describe its management approach, organization and lines of authority. The Offeror shall provide "
             "a transition plan covering the first ninety days after award.")]
    doc.build(st)


def comment(base, out):
    """The reviewer's comments on it. Returns the truth (make_comment_fixtures' form)."""
    import make_comment_fixtures as MC
    from pypdf.generic import NameObject
    A, B = MC.A, MC.B
    wr, t = MC.Writer(base), []
    pages = {i: MC.Page(base, i) for i in range(3)}

    def hl(i, s, note, who=A, nth=0, **more):
        a, b = pages[i].find(s, nth)
        wr.markup(i, "/Highlight", pages[i].quads(a, b), who, note, "Highlight", MC.YEL)
        t.append(dict({"id": f"r_{len(t)}", "page": i + 1, "want": "comment", "words": s, "note": note, "author": who}, **more))

    hl(0, "15 December 2026", "Confirm the due date against the amendment.")
    hl(1, "three volumes", "Four with the past performance volume?", who=B)
    a, b = pages[1].find("one inch margins")
    wr.markup(1, "/StrikeOut", pages[1].quads(a, a + len("one")), B, None, "Cross-Out", MC.RED)
    cr = wr.caret(1, pages[1].caret_at(a + len("one")), B, "1.25")
    so = wr.w.pages[1]["/Annots"][-4].get_object()
    so[NameObject("/IRT")] = cr; so[NameObject("/RT")] = NameObject("/Group")
    t.append({"id": "r_replace", "page": 2, "want": "replace", "words": "one", "insert": "1.25",
              "accepted": "with 1.25 inch margins", "author": B})
    hl(1, "Management Approach", "Rename to Management and Staffing?")
    hl(1, "Kestrel ground station architecture", "Figure needs the backup site.", who=B)
    a, b = pages[1].find("do not count against")
    wr.markup(1, "/StrikeOut", pages[1].quads(a + 3, a + 7), A, None, "Cross-Out", MC.RED)
    t.append({"id": "r_strike", "page": 2, "want": "delete", "words": "not", "accepted": "Resumes do count against", "author": A})
    hl(2, "2 of the scheduling discussion continues", "This paragraph starts on the page before.", context="antenna network")
    hl(2, "Paragraph 9 of the scheduling discussion", "Last one: cut it.", who=B)
    hl(2, "transition plan", "Ninety or sixty days?", who=B)
    wr.save(out)
    return t


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp()
    photo, logo = pictures(tmp)
    base = os.path.join(OUT, NAME + ".pdf")
    build(base, photo, logo)
    commented = os.path.join(COM, NAME + "_commented.pdf")
    got = comment(base, commented)
    tp = os.path.join(COM, "comments_truth.json")
    truth = json.load(open(tp, encoding="utf-8"))
    truth[NAME + "_commented.pdf"] = {"base": "../redline/" + NAME + ".pdf", "comments": got}
    with open(tp, "w", encoding="utf-8") as f:
        json.dump(truth, f, indent=1)
    print(len(got), "comments on", NAME)


if __name__ == "__main__":
    main()
