"""The fictional fixtures for Redline's fidelity (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html).

Writes test_samples/fidelity/Fnn_<name>.docx (python-docx, tests only) and fidelity_truth.json: for every table its
grid as authored, row by row, each cell {"text", "cs" (columns it spans), "rs" (rows it spans)}; cells a merge covers
are left out. The PDFs are made from these by Word on the build PC (tools/fidelity_pdfs.ps1: Save as PDF with tags,
and without). Fictional content only (the Kestrel program). Run: python tools/make_fidelity_fixtures.py"""
import json, os, sys

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "test_samples", "fidelity")

C = lambda t, cs=1, rs=1: {"text": t, "cs": cs, "rs": rs}          # noqa: E731


def grid_rows(spec):
    """Rows of cells (C or str or None for covered) to the truth: [[{"text","cs","rs"}]]."""
    return [[c if isinstance(c, dict) else C(c) for c in row if c is not None] for row in spec]


def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), str(v))
    return e


def borders(table, outer=True, inside_h=True, inside_v=True, sz=4):
    tblPr = table._tbl.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    b = _el("w:tblBorders")
    for name, on in (("top", outer), ("left", outer and inside_v), ("bottom", outer), ("right", outer and inside_v),
                     ("insideH", inside_h), ("insideV", inside_v)):
        b.append(_el(f"w:{name}", **{"w:val": "single" if on else "nil", "w:sz": sz, "w:space": 0, "w:color": "000000"}))
    tblPr.append(b)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(_el("w:shd", **{"w:val": "clear", "w:color": "auto", "w:fill": fill}))


def header_repeat(row):
    trPr = row._tr.get_or_add_trPr()
    trPr.append(_el("w:tblHeader"))


def make_table(doc_or_cell, spec, style="Table Grid", widths=None):
    """A table from spec (rows of C/str/None); merges made from cs and rs. Returns the python-docx table."""
    nrows = len(spec)
    ncols = sum(c["cs"] if isinstance(c, dict) else 1 for c in spec[0] if c is not None) if spec else 0
    ncols = max(ncols, max(len(r) for r in spec))
    t = doc_or_cell.add_table(rows=nrows, cols=ncols)
    t.style = style
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    occupied = [[False] * ncols for _ in range(nrows)]
    for ri, row in enumerate(spec):
        ci = 0
        for c in row:
            while ci < ncols and occupied[ri][ci]:
                ci += 1
            if c is None:
                continue
            c = c if isinstance(c, dict) else C(c)
            cell = t.cell(ri, ci)
            if c["cs"] > 1 or c["rs"] > 1:
                cell = cell.merge(t.cell(ri + c["rs"] - 1, ci + c["cs"] - 1))
            for r2 in range(ri, ri + c["rs"]):
                for c2 in range(ci, ci + c["cs"]):
                    occupied[r2][c2] = True
            cell.text = c["text"]
            ci += c["cs"]
    if widths:
        for row in t.rows:
            for k, w in enumerate(widths):
                if k < len(row.cells):
                    row.cells[k].width = Inches(w)
    return t


def head(doc, n, title, lead):
    doc.add_heading(f"{n}. {title}", level=1)
    doc.add_paragraph(lead)


def fixtures():
    """[(file stem, builder(doc) -> [table specs as truth])]"""
    out = []

    def f01(d):
        head(d, 1, "Contract Line Items", "The Kestrel program delivers the following items under the basic period.")
        s = [["CLIN", "Description", "Quantity", "Unit"]] + [[f"000{k}", f"Kestrel ground station unit {k}", str(k * 2), "Each"]
                                                             for k in range(1, 6)]
        make_table(d, s)
        d.add_paragraph("Quantities are estimates for evaluation only.")
        return [s]
    out.append(("F01_ruled", f01))

    def f02(d):
        head(d, 2, "Staffing by Period", "Labor hours by category and period of performance.")
        s = [[C("Labor category"), C("Base period", 2), C("Option periods", 3)],
             ["", "Hours", "Rate", "Option 1", "Option 2", "Option 3"],
             ["Systems engineer", "1,920", "TBD", "1,920", "1,920", "960"],
             ["Test engineer", "960", "TBD", "960", "480", "480"]]
        make_table(d, s)
        return [s]
    out.append(("F02_merged_across", f02))

    def f03(d):
        head(d, 3, "Review Gates", "Each gate below is held at the Government site.")
        s = [[C("Phase"), C("Gate"), C("Entry criteria")],
             [C("Design", 1, 3), "SRR", "Requirements baselined"],
             [None, "PDR", "Preliminary design complete"],
             [None, "CDR", "Detailed design complete"],
             ["Test", "TRR", "Test procedures approved"]]
        make_table(d, s)
        return [s]
    out.append(("F03_merged_down", f03))

    def f04(d):
        head(d, 4, "Site Coverage", "The block below applies to both ground sites.")
        s = [["Item", "Site A", "Site B", "Notes"],
             ["Power", C("Commercial with backup generator", 2, 2), None, "Tested quarterly"],
             ["Cooling", None, None, "Redundant units"],
             ["Network", "Fiber", "Satellite", "Encrypted"]]
        make_table(d, s)
        return [s]
    out.append(("F04_merged_block", f04))

    def f05(d):
        head(d, 5, "Data Items Status", "Blank cells mean not yet assigned.")
        s = [["CDRL", "Title", "Owner", "Due"],
             ["A001", "Program Management Plan", "", "30 DAC"],
             ["A002", "", "", ""],
             ["A003", "Test Plan", "", "90 DAC"]]
        make_table(d, s)
        return [s]
    out.append(("F05_empty_cells", f05))

    def f06(d):
        head(d, 6, "Evaluation Notes", "Some cells hold several lines of text.")
        s = [["Factor", "What the Government evaluates"],
             ["Technical", "The offeror's approach to the Kestrel ground architecture, including its plan for integrating "
                           "legacy telemetry and the schedule risk that integration carries."],
             ["Management", "Key personnel."],
             ["Past performance", "Recency and relevance of at most three contracts, each described in no more than two pages "
                                  "with points of contact who can be reached during evaluation."]]
        make_table(d, s, widths=[1.6, 4.9])
        return [s]
    out.append(("F06_wrapped_cells", f06))

    def f07(d):
        head(d, 7, "Milestones", "Horizontal rules only, as many house styles draw them.")
        s = [["Milestone", "Month", "Payment"], ["Kickoff", "1", "10%"], ["Design review", "4", "20%"],
             ["Acceptance", "12", "70%"]]
        t = make_table(d, s)
        borders(t, outer=True, inside_h=True, inside_v=False)
        return [s]
    out.append(("F07_rules_only", f07))

    def f08(d):
        head(d, 8, "Risk Register", "The header is shaded and the rows are banded.")
        s = [["ID", "Risk", "Likelihood", "Impact"], ["R1", "Late antenna delivery", "Medium", "High"],
             ["R2", "Staff turnover", "Low", "Medium"], ["R3", "Software certification", "Medium", "Medium"],
             ["R4", "Site access", "Low", "Low"]]
        t = make_table(d, s)
        for c in t.rows[0].cells:
            shade(c, "1F3864")
            for r in c.paragraphs[0].runs:
                r.font.bold = True
        for k in (2, 4):
            for c in t.rows[k].cells:
                shade(c, "D9E2F3")
        return [s]
    out.append(("F08_shaded", f08))

    def f09(d):
        head(d, 9, "Contract Data Requirements", "The list follows on a landscape page.")
        sec = d.add_section()
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
        s = [["CDRL", "Title", "DID", "Frequency", "First submission", "Distribution", "Approval"],
             ["A001", "Program Management Plan", "DI-MGMT-81797", "Once", "30 DAC", "PCO, PM", "Required"],
             ["A002", "Integrated Master Schedule", "DI-MGMT-81861", "Monthly", "45 DAC", "PM", "Required"],
             ["A003", "Test Plan", "DI-NDTI-80566", "Once", "90 DAC", "PM, Test lead", "Required"]]
        make_table(d, s)
        sec2 = d.add_section()
        sec2.orientation = WD_ORIENT.PORTRAIT
        sec2.page_width, sec2.page_height = sec2.page_height, sec2.page_width
        d.add_paragraph("The list above is complete as of the solicitation date.")
        return [s]
    out.append(("F09_landscape", f09))

    def f10(d):
        head(d, 10, "Submission Copies", "")
        p = d.add_paragraph()
        r = p.add_run("Deliver the copies listed below to the contracting office.")
        r.font.underline = True
        s = [["Volume", "Paper copies", "Electronic"], ["I Technical", "3", "1"], ["II Price", "2", "1"]]
        make_table(d, s)
        return [s]
    out.append(("F10_underline_near", f10))

    def f11(d):
        head(d, 11, "Two Sites", "Each site's equipment, side by side.")
        sectPr = d.sections[-1]._sectPr
        a = [["Site A", "Units"], ["Antenna", "2"], ["Racks", "6"]]
        b = [["Site B", "Units"], ["Antenna", "1"], ["Racks", "4"]]
        outer = make_table(d, [["", ""]], style="Normal Table")
        borders(outer, outer=False, inside_h=False, inside_v=False)
        make_table(outer.cell(0, 0), a)
        make_table(outer.cell(0, 1), b)
        return [a, b]
    out.append(("F11_side_by_side", f11))

    def f12(d):
        head(d, 12, "Shipping Points", "This table uses cell spacing.")
        s = [["Point", "City", "Days"], ["North", "Kestrel Falls", "3"], ["South", "Osprey Bay", "5"]]
        t = make_table(d, s)
        t._tbl.tblPr.append(_el("w:tblCellSpacing", **{"w:w": 40, "w:type": "dxa"}))
        return [s]
    out.append(("F12_cell_spacing", f12))

    def f13(d):
        head(d, 13, "Parts List", "A long list whose header row repeats on each page.")
        s = [["Part", "Description", "Qty"]] + [[f"KP-{1000 + k}", f"Kestrel spare part number {k}", str(1 + k % 4)] for k in range(1, 101)]
        t = make_table(d, s)
        header_repeat(t.rows[0])
        return [s]
    out.append(("F13_header_repeat", f13))

    def f14(d):
        head(d, 14, "Long Answers", "A row is allowed to break across the page.")
        for _ in range(28):
            d.add_paragraph("Filler paragraph so the table starts near the bottom of the page.")
        long = " ".join(f"Sentence {k} of the Kestrel approach describes one step." for k in range(1, 26))
        s = [["Step", "Approach"], ["1", long], ["2", "Close out."]]
        make_table(d, s, widths=[0.8, 5.7])
        return [s]
    out.append(("F14_row_breaks", f14))

    def f15(d):
        head(d, 15, "Nested Table", "A cell holds its own table.")
        s = [["Area", "Detail"], ["Power", ""], ["Cooling", "Redundant units"]]
        t = make_table(d, s)
        inner = [["Source", "kW"], ["Grid", "40"], ["Generator", "35"]]
        make_table(t.cell(1, 1), inner)
        return [s, inner]
    out.append(("F15_nested", f15))

    def f16(d):
        head(d, 16, "Compliance Grid", "The column headers are rotated.")
        s = [["Requirement", "Volume I", "Volume II", "Volume III"], ["L.3.1", "X", "", ""], ["L.3.2", "", "X", ""], ["L.4.1", "", "", "X"]]
        t = make_table(d, s)
        for c in t.rows[0].cells[1:]:
            c._tc.get_or_add_tcPr().append(_el("w:textDirection", **{"w:val": "btLr"}))
        t.rows[0].height = Inches(1.0)
        return [s]
    out.append(("F16_rotated", f16))

    def f17(d):
        head(d, 17, "Instructions by Volume", "Lists inside cells.")
        t = make_table(d, [["Volume", "Instructions"], ["I", ""], ["II", ""]])
        c = t.cell(1, 1)
        c.paragraphs[0].text = "Describe the approach."
        for x in ("Architecture", "Integration", "Test"):
            c.add_paragraph(x, style="List Bullet")
        c = t.cell(2, 1)
        c.paragraphs[0].text = "Price each item."
        for x in ("Labor", "Materials"):
            c.add_paragraph(x, style="List Number")
        truth = [["Volume", "Instructions"], ["I", "Describe the approach. \u2022 Architecture \u2022 Integration \u2022 Test"],
                 ["II", "Price each item. 1. Labor 2. Materials"]]          # the markers show on the page: they are words
        return [truth]
    out.append(("F17_lists_in_cells", f17))

    def f18(d):
        head(d, 18, "Rates", "Some cells carry note marks.")
        t = make_table(d, [["Category", "Rate"], ["Engineer", "TBD"], ["Technician", "TBD"]])
        for ri in (1, 2):
            r = t.cell(ri, 1).paragraphs[0].add_run(str(ri))
            r.font.superscript = True
        d.add_paragraph("1 Fully burdened. 2 Includes travel.")
        return [[["Category", "Rate"], ["Engineer", "TBD1"], ["Technician", "TBD2"]]]
    out.append(("F18_note_marks", f18))

    def f19(d):
        head(d, 19, "Price Summary", "No borders; the numbers are right-aligned.")
        s = [["Period", "Labor", "Materials", "Total"], ["Base", "1,200,000", "300,000", "1,500,000"],
             ["Option 1", "1,250,000", "80,000", "1,330,000"], ["Option 2", "900,000", "15,000", "915,000"]]
        t = make_table(d, s, style="Normal Table")
        borders(t, outer=False, inside_h=False, inside_v=False)
        for row in t.rows:
            for c in row.cells[1:]:
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        return [s]
    out.append(("F19_borderless", f19))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    truth = {}
    for stem, fn in fixtures():
        d = Document()
        st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
        specs = fn(d)
        path = os.path.join(OUT, stem + ".docx")
        d.save(path)
        truth[stem] = [{"rows": grid_rows(s)} for s in specs]
        print("wrote", path)
    with open(os.path.join(OUT, "fidelity_truth.json"), "w", encoding="utf-8") as f:
        json.dump(truth, f, indent=1)
    return truth


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
