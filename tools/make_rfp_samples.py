"""Fictional RFP test samples for the compliance matrix (2.8.0): test_samples/rfp/.
Word file with real Heading styles (Sections C, L, M) and a PDF of Section L whose lines wrap mid-sentence.
The PDF needs reportlab (a development tool, not shipped): python -m pip install reportlab."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import docxw

OUT = os.path.join(ROOT, "test_samples", "rfp")
RFP = [
    ("h", 1, "SECTION C - STATEMENT OF WORK"),
    ("p", "This document is a fictional test sample. This acquisition is for one Kestrel spacecraft bus."),
    ("h", 2, "C.1 SCOPE"),
    ("p", "The Contractor shall design, build, and test one Kestrel spacecraft bus."),
    ("h", 2, "C.2 TECHNICAL REQUIREMENTS"),
    ("p", "C.2.1 The Contractor shall provide a thermal design that maintains all components within qualification temperature limits."),
    ("p", "C.2.2 The Contractor shall deliver the Interface Control Document (CDRL A003) and shall maintain it through launch."),
    ("p", "The Government will provide the launch vehicle interface definition within 30 days after award."),
    ("p", "The Contractor should use flight-proven components where practical."),
    ("h", 1, "SECTION L - INSTRUCTIONS, CONDITIONS, AND NOTICES TO OFFERORS"),
    ("h", 2, "L.1 GENERAL INSTRUCTIONS"),
    ("p", "Proposals shall not exceed 50 pages, excluding the cover page and table of contents."),
    ("p", "Text shall be 12-point Times New Roman with 1-inch margins on 8.5 x 11 inch pages."),
    ("p", "Proposals are due no later than 2:00 p.m. Mountain Time on December 15, 2026."),
    ("h", 2, "L.4 TECHNICAL VOLUME"),
    ("h", 3, "L.4.1 Technical Approach"),
    ("p", "The Offeror shall describe its approach to the thermal design required by C.2.1, including analysis methods and margins."),
    ("p", "The offeror shall: (a) identify the five highest technical risks; (b) describe mitigation plans for each risk; and (c) provide a risk register as Attachment J-3."),
    ("p", "Describe the verification approach for each requirement in Section C."),
    ("h", 3, "L.4.2 Management Approach"),
    ("p", "The Offeror must provide an Integrated Master Schedule (IMS) as Attachment J-2."),
    ("p", "The Offeror may include resumes of key personnel. Resumes do not count toward the page limit."),
    ("h", 1, "SECTION M - EVALUATION FACTORS FOR AWARD"),
    ("h", 2, "M.1 BASIS FOR AWARD"),
    ("p", "The Government will award a contract to the offeror whose proposal represents the best value to the Government."),
    ("h", 2, "M.2 TECHNICAL FACTOR"),
    ("p", "The Government will evaluate the offeror's thermal design approach and analysis methods for feasibility and risk."),
    ("p", "The Government will assess the risk register and mitigation plans for completeness."),
]

L_PDF = """SECTION L - INSTRUCTIONS TO OFFERORS
This document is a fictional test sample.
L.2 VOLUME ORGANIZATION
L.2.1 The Offeror shall organize the proposal into three volumes: Volume I Technical, Volume II
Management, and Volume III Cost. Each volume shall begin with a table of contents.
The Government will not evaluate information submitted outside the designated volume.
L.2.2 Electronic copies shall be submitted as searchable PDF files. File names shall follow
the convention Offeror_Volume_Number.pdf.
L.3 PAST PERFORMANCE
The Offeror shall provide no more than three past performance references for contracts
performed within the last five years. For each reference, the Offeror shall:
(a) state the contract number and value;
(b) describe the relevance to this effort; and
(c) identify a point of contact.
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    d = docxw.Doc()
    for row in RFP:
        if row[0] == "h":
            d.heading(row[2], row[1])
        else:
            d.para(row[1])
    p = os.path.join(OUT, "Kestrel_RFP_Sections_C_L_M.docx")
    d.save(p)
    print("wrote", p)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        print("reportlab not installed: PDF sample skipped"); return
    p = os.path.join(OUT, "Kestrel_RFP_Section_L_Part2.pdf")
    c = canvas.Canvas(p, pagesize=letter)
    c.setFont("Helvetica", 11)
    y = 740
    for i, line in enumerate(L_PDF.splitlines()):
        if i == 9:                                   # page break inside L.3 (mid-paragraph)
            c.showPage(); c.setFont("Helvetica", 11); y = 740
        c.drawString(72, y, line); y -= 16
    c.save()
    print("wrote", p)


if __name__ == "__main__":
    main()
