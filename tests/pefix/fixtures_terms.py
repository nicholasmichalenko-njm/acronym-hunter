"""Text with banned phrases, misspellings, missing marks and a near-miss name, with the answer key. No real content."""
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

EXPECTED = {"W1": 3, "W2": 3, "W3": 2, "W4": 1}       # hits, not groups


def _field(par, instr, result):
    for kind in ("begin", "instr", "separate", "result", "end"):
        r = par.add_run()
        if kind in ("begin", "separate", "end"):
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        elif kind == "instr":
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; r._r.append(it)
        else:
            r.text = result


def make(path):
    doc = Document()
    doc.sections[0].header.paragraphs[0].text = "Seperate volume for the technical approach"   # W2 in a header
    toc = doc.add_paragraph()
    _field(toc, 'TOC \\h \\z', "How we recieve data")                                        # skipped (field result)
    doc.add_paragraph("We will utilize a world-class approach.")                              # W1 x2
    p = doc.add_paragraph("The team works ")
    p.add_run("in or"); p.add_run("der to").bold = True; p.add_run(" deliver on time.")        # W1 across runs
    p = doc.add_paragraph("Each site will ")
    p.add_run("recieve").bold = True; p.add_run(" the build.")                                  # W2, bold kept
    doc.add_paragraph("Seperate the data from the model.")                                      # W2, capital kept
    doc.add_paragraph("Kestrel Mission Suite runs the ground segment.")                         # W3 first use
    doc.add_paragraph("Kestrel Mission Suite also plans passes.")                               # not first: no hit
    doc.add_paragraph("OrbitLink® carries the data; OrbitLink routes it.")                 # W3 on the second
    doc.add_paragraph("Jordon Reyes leads the program with Avery Chen.")                        # W4
    doc.save(path)
    return EXPECTED
