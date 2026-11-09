"""3.90.0 the outline import with Section L and M (decision 13): an outline matrix with Section L and Section M side by side
(the app's own outline layout: RFP Solicitation Requirements (Section L), Section L Content, Evaluation Section (Section M),
Evaluation Content) is read without setup: each column guessed by its heading; the L content's requirements are L with
their L reference, the M content's are M with their M reference; a column that says L or M (L, M, L/M, LNM, both); a
reference alone (L.3.5, M.2.1, "L.3.5; M.2.1") says it when nothing else does; a sentence for both shows L/M in the
matrix and in both columns of the outline matrix; red text in an L column is still L. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import compliance as C, outlinexl as OX, matrixdesign as MDZ, setupdoc as SD

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


check("references say L, M or both", [OX.lm_of_ref(r) for r in ("L.3.5", "M.2.1", "L.3.5; M.2.1", "Section L 3.5 / Section M 2", "C.4", "3.2.1", "LNM 3.2")]
      == ["L", "M", "LM", "LM", "", "", "LM"])
check("an L or M cell: L, M, or both (L/M, L&M, L and M, LNM, both)", [OX.lm_of_cell(c) for c in ("L", "m", "L/M", "L&M", "L and M", "LNM", "Both", "x", "")]
      == ["L", "M", "LM", "LM", "LM", "LM", "LM", "", ""])
check("the outline matrix's headings are guessed", [OX.guess_one(h) for h in ("RFP Solicitation Requirements (Section L)", "Section L Content",
      "Evaluation Section (Section M)", "Evaluation Content", "L/M", "LNM", "RFPL Number", "Compliance Requirement")]
      == ["reference_l", "requirement_l", "reference_m", "requirement_m", "lm", "lm", "reference", "requirement"])

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
tmp = tempfile.mkdtemp()
xl = os.path.join(tmp, "Kestrel Outline Matrix.xlsx")
wb = Workbook(); ws = wb.active
ws.append(["Response Section Number", "Response Section Name", "RFP Solicitation Requirements (Section L)", "Section L Content",
           "Evaluation Section (Section M)", "Evaluation Content", "Management Guidance"])
red = InlineFont(color="FFFF0000"); plain = InlineFont(color="FF000000")
ws.append(["1", "Technical Approach", "L.4.2", "The offeror shall describe its ground segment architecture.", "M.2.1",
           "The Government will evaluate the resilience of the architecture.", "Lead with the dual-site design."])
ws.append(["1.1", "Cybersecurity", "L.4.3", None, "", "", ""])
ws.cell(row=3, column=4).value = CellRichText([TextBlock(red, "The offeror shall describe its cybersecurity approach.")])
wb.save(xl)
# a second workbook: one requirement column, an L or M column, and the reference
xl2 = os.path.join(tmp, "Kestrel Outline LM.xlsx")
wb = Workbook(); ws = wb.active
ws.append(["Response Section Number", "Response Section Name", "RFPL Number", "Compliance Requirement", "LNM"])
ws.append(["2", "Management", "L.5.1", "The offeror shall describe its management approach.", "L"])
ws.append(["2", "Management", "M.3.1", "Management will be evaluated for realism.", ""])
ws.append(["2", "Management", "L.5.2", "The offeror shall provide a staffing plan that is evaluated for risk.", "L and M"])
wb.save(xl2)

book = OX.read(xl)
prof = OX.profile_for(tmp, book["headers"])
check("its columns are guessed: Section L and M side by side", [prof["columns"][h] for h in book["headers"]]
      == ["section_number", "section_name", "reference_l", "requirement_l", "reference_m", "requirement_m", "guidance"], prof["columns"])
p = OX.parse(book, prof)
bl = [b for s in p["sections"] for b in s["blocks"] if b["kind"] == "rfp"]
check("the L content is L with its L reference; the M content is M with its M reference",
      [(b["lm"], b["ref"]) for b in bl[:2]] == [("L", "L.4.2"), ("M", "M.2.1")], bl)
check("red text in an L column is still L", bl[2]["lm"] == "L" and bl[2]["ref"] == "L.4.3", bl[2])
check("no reference problem for a row with a side reference", not any("no RFP reference" in x for x in p["problems"]), p["problems"])
M = C.Matrix(os.path.join(tmp, "Kestrel_Matrix.xlsx"), "Kestrel")
OX.apply(M, p, os.path.basename(xl))
ga = next(it for it in M.items if "ground segment architecture" in it["text"])
ev = next(it for it in M.items if it["text"].startswith("The Government will"))
check("into the matrix: L and M as the workbook says", SD.lm_of(M, ga) == "L" and SD.lm_of(M, ev) == "M" and ga["map"] == ev["map"] == "1 Technical Approach")

book2 = OX.read(xl2)
prof2 = OX.profile_for(tmp, book2["headers"])
check("an L or M column is guessed", prof2["columns"]["LNM"] == "lm", prof2["columns"])
p2 = OX.parse(book2, prof2)
b2 = [b for s in p2["sections"] for b in s["blocks"] if b["kind"] == "rfp"]
check("the L or M column first, then the reference", [b["lm"] for b in b2] == ["L", "M", "LM"], b2)
M2 = C.Matrix(os.path.join(tmp, "Kestrel_Matrix2.xlsx"), "Kestrel")
OX.apply(M2, p2, os.path.basename(xl2))
both = next(it for it in M2.items if "staffing plan" in it["text"])
check("both: L, marked for M too", both["lm"] == "L" and both.get("lm_both"))
check("... the matrix says L/M", MDZ._value(M2, both, "lm", {}, {}) == "L/M", MDZ._value(M2, both, "lm", {}, {}))
print(f"LM 390 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
