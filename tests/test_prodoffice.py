"""3.11.0: Excel and PowerPoint checks (prodoffice through prodfix.check). Read only: the source is never written."""
import hashlib, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prodfix as PF
import prodrules as PRL

ok = []


def check(name, cond):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name)


tmp = tempfile.mkdtemp()
std = PRL.engine_ready(PRL._company_default())
std["variables"].update({"table_font": "Arial", "table_size": 10, "body_font": "Times New Roman", "marking": "Proprietary"})
check("the team default has Excel and PowerPoint values", std.get("excel", {}).get("freeze_header") is True
      and std.get("powerpoint", {}).get("min_size") == 12)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rules(chk):
    return {f["rule"] for f in chk.findings}


# ------------------------------------------------------------------ Excel
from openpyxl import Workbook
from openpyxl.styles import Font

bad = os.path.join(tmp, "Cost Volume.xlsx")
wb = Workbook(); ws = wb.active; ws.title = "Labor"
ws.append(["Role", "Hours", "Rate"])
ws.append(["Engineer", 100, 150.5]); ws.append(["Analyst", 200, "=1/0"])
ws["A2"].font = Font(name="Calibri", size=11)
ws.append(["Manager", 50, 175]); ws.append(["Lead", 10, 160])
ws["C2"].number_format = "0.00"; ws["C4"].number_format = "$#,##0"
ws.column_dimensions["D"].hidden = True
h = wb.create_sheet("Notes"); h.sheet_state = "hidden"
wb.save(bad)
before, mt = sha(bad), os.path.getmtime(bad)
c = PF.check(bad, std)
r = rules(c)
check("a workbook is checked as Excel", c.office == "excel" and not c.error)
check("font off the profile (X1)", "X1" in r)
check("header row not bold (X2) and not frozen (X3)", {"X2", "X3"} <= r)
check("print setup (X4)", "X4" in r)
check("two number formats in a column (X5)", "X5" in r)
check("hidden sheet or column (X6)", "X6" in r)
check("every finding is in the sheets area, without a fix, and names its sheet",
      all(f["area"] == "sheets" and not f["fix"] and f.get("near") for f in c.findings))
check("the workbook is never written", sha(bad) == before and os.path.getmtime(bad) == mt)

good = os.path.join(tmp, "Clean.xlsx")
wb = Workbook(); ws = wb.active; ws.title = "Data"
ws.append(["Item", "Cost"]); ws.append(["A", 1]); ws.append(["B", 2])
for row in ws.iter_rows():
    for cell in row:
        cell.font = Font(name="Arial", size=10, bold=cell.row == 1)
ws.freeze_panes = "A2"
ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0; ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.print_title_rows = "1:1"; ws.oddFooter.center.text = "Page &P"
wb.save(good)
c = PF.check(good, std)
check("a workbook built to the profile has no findings", c.office == "excel" and not c.findings and not c.error)

junk = os.path.join(tmp, "Broken.xlsx")
open(junk, "wb").write(b"not a workbook")
c = PF.check(junk, std)
check("a damaged workbook reports an error, never a crash", c.error and not c.findings)

# ------------------------------------------------------------------ PowerPoint
from pptx import Presentation
from pptx.util import Inches, Pt

deck = os.path.join(tmp, "Orals.pptx")
p = Presentation()                       # 4:3 by default
s1 = p.slides.add_slide(p.slide_layouts[1])
s1.shapes.title.text = "Approach"
tb = s1.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
run = tb.text_frame.paragraphs[0].add_run(); run.text = "Small words"; run.font.size = Pt(8); run.font.name = "Comic Sans MS"
off = s1.shapes.add_textbox(Inches(9.5), Inches(1), Inches(2), Inches(1)); off.text_frame.text = "off"
s2 = p.slides.add_slide(p.slide_layouts[6])
s2.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)).text_frame.text = "No title here"
p.save(deck)
before = sha(deck)
std2 = PRL.engine_ready(PRL._company_default())
std2["variables"].update({"body_font": "Arial", "table_font": "Arial", "marking": "Proprietary"})
std2["powerpoint"].update({"slide_size": "16:9", "marking": True})
c = PF.check(deck, std2)
r = rules(c)
check("a deck is checked as PowerPoint", c.office == "powerpoint" and not c.error)
check("slide size (D1)", "D1" in r)
check("font not allowed (D2) and text too small (D3)", {"D2", "D3"} <= r)
check("off the slide (D4)", "D4" in r)
check("marking missing (D5)", "D5" in r)
check("placeholder left empty (D6)", "D6" in r)
check("slide without a title (D7)", "D7" in r)
check("every finding is in the slides area and names its slide",
      all(f["area"] == "slides" and not f["fix"] and (f.get("near") or "").startswith(("Slide", "Deck", "Theme")) for f in c.findings))
check("the deck is never written", sha(deck) == before)

print(f"TEST PRODOFFICE {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
sys.exit(0 if all(ok) else 1)
