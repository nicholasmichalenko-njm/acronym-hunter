"""A volume with sections, headers and footers shaped like the team's, with planted problems as the answer key.
No real content.

Sections: 0 cover | 1 front matter (i) | 2 chapter 1, with chapter 2 inside it | 3 placed landscape page |
4 rest of chapter 2 | 5 appendix A

Planted (rule -> count):
  P1 appendix numbers take the chapter from Heading 1, not Heading 7   P2 the landscape page restarts at 1
  P3 chapter 2 is not its own section                                  P4 front matter header names Volume II
  P5 PAGE field with a roman format switch                             P6 appendix footer has a typed page number
  P8 the landscape page has its own footer                             P9 chapter 1 has a 0.75 in left margin
  P10 the appendix footer has no restriction marking
"""
from docx import Document
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

EXPECTED = {"P1": 1, "P2": 1, "P3": 1, "P4": 1, "P5": 1, "P6": 1, "P8": 1, "P9": 1, "P10": 1}
MARK = "Use or disclosure of data contained on this page is subject to the restriction on the title page of this proposal."


def _field(par, instr, result):
    for kind in ("begin", "instr", "separate", "result", "end"):
        r = par.add_run()
        if kind in ("begin", "separate", "end"):
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        elif kind == "instr":
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; r._r.append(it)
        else:
            r.text = result


def _pgnum(section, **kw):
    sp = section._sectPr
    for old in sp.findall(qn("w:pgNumType")):
        sp.remove(old)
    el = OxmlElement("w:pgNumType")
    for k, v in kw.items():
        el.set(qn(f"w:{k}"), v)
    # schema order: after pgMar / paperSrc / pgBorders / lnNumType, before cols
    cols = sp.find(qn("w:cols"))
    if cols is not None:
        cols.addprevious(el)
    else:
        sp.append(el)


def _margins(section, left=1.0, right=1.0, top=1.0, bottom=1.0):
    section.left_margin, section.right_margin = Inches(left), Inches(right)
    section.top_margin, section.bottom_margin = Inches(top), Inches(bottom)
    section.header_distance, section.footer_distance = Inches(0.5), Inches(0.5)


def _footer(section, marking=True, page_instr="PAGE", typed=None):
    f = section.footer
    f.is_linked_to_previous = False
    p = f.paragraphs[0]
    if marking:
        p.add_run(MARK)
        p = f.add_paragraph()
    if typed:
        p.add_run(typed)
    elif page_instr:
        _field(p, page_instr, "1")


def _header(section, text):
    h = section.header
    h.is_linked_to_previous = False
    h.paragraphs[0].text = text


def body(doc, n=6):
    for k in range(n):
        doc.add_paragraph("The approach section describes how the work is planned, staffed and controlled. " * 4)


def make(path):
    doc = Document()
    s0 = doc.sections[0]
    _margins(s0)
    doc.add_paragraph("Example Program", "Title")
    doc.add_paragraph("Volume I Technical")

    s1 = doc.add_section(WD_SECTION.NEW_PAGE)                     # front matter
    _margins(s1)
    doc.add_paragraph("Table of Contents", "TOC Heading")
    doc.add_paragraph("1 Introduction\t1-1")
    _header(s1, "Volume II Management")                            # P4
    _footer(s1, page_instr="PAGE \\* roman")                       # P5 (format on the field)
    _pgnum(s1, fmt="lowerRoman", start="1")

    s2 = doc.add_section(WD_SECTION.NEW_PAGE)                     # chapter 1
    _margins(s2, left=0.75)                                        # P9
    doc.add_paragraph("Introduction", "Heading 1")
    body(doc)
    _header(s2, "Volume I Technical")
    _footer(s2)
    _pgnum(s2, start="1", chapStyle="1", chapSep="hyphen")
    doc.add_paragraph("Technical Approach", "Heading 1")             # P3 (inside section 2)
    body(doc, 3)

    s3 = doc.add_section(WD_SECTION.NEW_PAGE)                     # placed landscape page
    s3.orientation = WD_ORIENT.LANDSCAPE
    s3.page_width, s3.page_height = Inches(11), Inches(8.5)
    _margins(s3)
    doc.add_paragraph("A wide schedule table goes on this page.")
    _footer(s3)                                                    # P8 (own footer)
    _pgnum(s3, start="1", chapStyle="1", chapSep="hyphen")          # P2 (restart)

    s4 = doc.add_section(WD_SECTION.NEW_PAGE)                     # rest of chapter 2, portrait again
    s4.orientation = WD_ORIENT.PORTRAIT
    s4.page_width, s4.page_height = Inches(8.5), Inches(11)
    _margins(s4)
    body(doc, 3)
    _pgnum(s4, chapStyle="1", chapSep="hyphen")
    s4.footer.is_linked_to_previous = True

    s5 = doc.add_section(WD_SECTION.NEW_PAGE)                     # appendix A
    _margins(s5)
    doc.add_paragraph("Glossary", "Heading 7")
    body(doc, 2)
    _footer(s5, marking=False, typed="Page A-1")                   # P10 and P6
    _pgnum(s5, start="1", chapStyle="1", chapSep="hyphen")          # P1
    doc.save(path)
    return EXPECTED
