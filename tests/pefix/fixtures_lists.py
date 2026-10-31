"""Lists as writers paste them, with the answer key. No real content.

Blocks: A typed bullets (one Symbol-font, one "o" level 2 with a manual indent) | B typed 1. 2. a) 3. |
C team List Number that continues B (a question) | heading with a typed "2.1" | D team List Number after a
heading (must restart) | E Word numbering pasted from another document, with manual indents | F typed 4. 5.
(continues on purpose) | a typed bullet in a table cell | one unused list definition
"""
from docx import Document
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

EXPECTED = {"L1": 1, "L2": 2, "L3": 1, "L4": 2, "L5": 2, "L5?": 1, "L6": 1, "L7": 1, "L8": 1}


def _numbering_add(doc, fmt="decimal", text="%1."):
    nb = doc.part.numbering_part.element
    aids = [int(a.get(qn("w:abstractNumId"))) for a in nb.findall(qn("w:abstractNum"))]
    nids = [int(n.get(qn("w:numId"))) for n in nb.findall(qn("w:num"))]
    aid, nid = max(aids) + 1, max(nids) + 1
    a = OxmlElement("w:abstractNum"); a.set(qn("w:abstractNumId"), str(aid))
    ml = OxmlElement("w:multiLevelType"); ml.set(qn("w:val"), "hybridMultilevel"); a.append(ml)
    lv = OxmlElement("w:lvl"); lv.set(qn("w:ilvl"), "0")
    for tag, val in (("w:start", "1"), ("w:numFmt", fmt), ("w:lvlText", text), ("w:lvlJc", "left")):
        e = OxmlElement(tag); e.set(qn("w:val"), val); lv.append(e)
    a.append(lv)
    first_num = nb.find(qn("w:num"))
    first_num.addprevious(a)
    n = OxmlElement("w:num"); n.set(qn("w:numId"), str(nid))
    an = OxmlElement("w:abstractNumId"); an.set(qn("w:val"), str(aid)); n.append(an)
    nb.append(n)
    return str(nid)


def _numpr(par, nid, ilvl=0):
    ppr = par._p.get_or_add_pPr()
    npr = OxmlElement("w:numPr")
    il = OxmlElement("w:ilvl"); il.set(qn("w:val"), str(ilvl)); npr.append(il)
    ni = OxmlElement("w:numId"); ni.set(qn("w:val"), nid); npr.append(ni)
    ppr.insert(1 if ppr.find(qn("w:pStyle")) is not None else 0, npr)


def _typed(doc, prefix, text, indent=None, style=None):
    p = doc.add_paragraph(style=style)
    p.add_run(prefix); p.add_run(text)
    if indent is not None:
        p.paragraph_format.left_indent = Inches(indent)
    return p


def make(path):
    doc = Document()
    doc.add_paragraph("Approach", "Heading 1")
    doc.add_paragraph("The plan has these parts.")
    _typed(doc, "•\t", "Program management")                      # A: L1
    _typed(doc, "•\t", "Systems engineering")
    _typed(doc, "o\t", "Requirements analysis", indent=0.5)            # level 2, manual indent (L4)
    p = doc.add_paragraph()
    r = p.add_run(); sym = OxmlElement("w:sym"); sym.set(qn("w:font"), "Symbol"); sym.set(qn("w:char"), "F0B7"); r._r.append(sym)
    r.add_tab(); p.add_run("Integration and test")                    # Symbol-font bullet
    doc.add_paragraph("The steps follow.")
    _typed(doc, "1. ", "Plan the work")                                # B: L2, first numbered list
    _typed(doc, "2. ", "Staff the team")
    _typed(doc, "a) ", "Hire to the plan")
    _typed(doc, "3. ", "Run the program")
    doc.add_paragraph("Then the program office does these.")
    doc.add_paragraph("Holds reviews", "List Number")                  # C: continues B (question)
    doc.add_paragraph("Reports status", "List Number")
    h = doc.add_paragraph("2.1 Staffing", "Heading 2")                  # L6 (Heading 2 is numbered below)
    doc.add_paragraph("Hire key personnel", "List Number")             # D: after a heading, must restart
    doc.add_paragraph("Train the staff", "List Number")
    doc.add_paragraph("A list pasted from a partner's document:")
    nid = _numbering_add(doc)
    for t in ("Partner task one", "Partner task two"):                 # E: L3, with manual indents (L4)
        p = doc.add_paragraph(t); _numpr(p, nid); p.paragraph_format.left_indent = Inches(0.6)
    doc.add_paragraph("The writer continued the first list by hand:")
    _typed(doc, "4. ", "Close out")                                     # F: L2, continues on purpose
    _typed(doc, "5. ", "Report lessons learned")
    t = doc.add_table(rows=1, cols=2)
    t.rows[0].cells[0].paragraphs[0].add_run("• Cell bullet")      # L7
    _numbering_add(doc, "bullet", "•")                            # L8: defined, never used
    # Heading 2 numbered through its style (as in the team template)
    st = doc.styles["Heading 2"].element
    ppr = st.get_or_add_pPr()
    hnum = _numbering_add(doc, "decimal", "2.%1")
    npr = OxmlElement("w:numPr"); ni = OxmlElement("w:numId"); ni.set(qn("w:val"), hnum); npr.append(ni)
    ppr.insert(0, npr)
    doc.save(path)
    return EXPECTED
