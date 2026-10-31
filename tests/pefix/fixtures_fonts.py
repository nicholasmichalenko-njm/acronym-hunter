"""Font compliance test document with the answer key. RFP rules for the test: body Times New Roman 11 or larger,
tables Arial or Arial Narrow 9 or larger, captions Arial 10 or larger, headers and footers 8 or larger,
footnotes 10 or larger. No real content.

Planted (rule -> groups):
  F1  body: 3 paragraphs pasted in Calibri (hand formatting; the style is fine)
  F2  table: one cell at 8 pt by hand
  F2s table: the style PE Table Text is 8.5 pt (the style is the source)
  F1s caption: the Caption style is Calibri
  F2  header: 7 pt by hand
"""
from docx import Document
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE

EXPECTED = {"F1": 1, "F2": 2, "F1s": 1, "F2s": 1}
RULES = {"body": {"min_size": 11, "fonts": ["Times New Roman"]}, "table": {"min_size": 9, "fonts": ["Arial", "Arial Narrow"]},
         "caption": {"min_size": 10, "fonts": ["Arial"]}, "header_footer": {"min_size": 8, "fonts": None},
         "footnote": {"min_size": 10, "fonts": None}, "graphic": {"min_size": None, "fonts": None}}


def make(path):
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"; normal.font.size = Pt(12)
    cap = doc.styles["Caption"]
    cap.font.name = "Calibri"; cap.font.size = Pt(10)                     # F1s
    tt = doc.styles.add_style("PE Table Text", WD_STYLE_TYPE.PARAGRAPH)
    tt.base_style = normal; tt.font.name = "Arial"; tt.font.size = Pt(8.5)  # F2s
    h = doc.sections[0].header.paragraphs[0]
    r = h.add_run("Volume I Technical"); r.font.size = Pt(7)               # F2 header
    doc.add_paragraph("Introduction", "Heading 1")
    for k in range(3):
        p = doc.add_paragraph()
        r = p.add_run("Text pasted from another document keeps its Calibri font. " * 2); r.font.name = "Calibri"   # F1
    doc.add_paragraph("Body text in the style's own font passes.")
    c = doc.add_paragraph("Table 1-1. Staffing", "Caption")
    t = doc.add_table(rows=2, cols=2)
    for i in range(2):
        for j in range(2):
            par = t.rows[i].cells[j].paragraphs[0]
            par.style = tt
            run = par.add_run(f"cell {i}{j}")
            if (i, j) == (1, 1):
                run.font.size = Pt(8)                                        # F2 table (hand)
    s = doc.add_paragraph("Symbol text is skipped: ")
    r = s.add_run("abc"); r.font.name = "Wingdings"
    hidden = doc.add_paragraph(); r = hidden.add_run("hidden note"); r.font.size = Pt(6); r.font.hidden = True
    doc.save(path)
    return EXPECTED
