"""Fictional equation test files for tools\\evaluate.py (test_samples\\equations\\):
  Kestrel_Propulsion_Note.docx   Word equation-editor math (OMML) + nomenclature table + typed math + "where" definitions
  Kestrel_Equation_Slide.pptx    PowerPoint equation-editor math
  Kestrel_Loads_Typed.pdf        typed Unicode math (made from a .docx by Word, if Word is installed)
  Kestrel_Equation_Picture.png   an equation as a picture
"""
import os, sys, copy
from docx import Document
from docx.oxml import parse_xml
from pptx import Presentation
from pptx.util import Inches
from PIL import Image, ImageDraw, ImageFont
from lxml import etree

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_samples", "equations")
os.makedirs(OUT, exist_ok=True)
M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'
r = lambda t: f'<m:r><m:t>{t}</m:t></m:r>'
sub = lambda b, s: f'<m:sSub><m:e>{r(b)}</m:e><m:sub>{r(s)}</m:sub></m:sSub>'
sup = lambda b, s: f'<m:sSup><m:e>{r(b)}</m:e><m:sup>{r(s)}</m:sup></m:sSup>'
dot = lambda b: f'<m:acc><m:accPr><m:chr m:val="&#729;"/></m:accPr><m:e>{r(b)}</m:e></m:acc>'
frac = lambda n, d: f'<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>'
func = lambda name, arg: f'<m:func><m:fName>{r(name)}</m:fName><m:e>{arg}</m:e></m:func>'
paren = lambda x: f'<m:d><m:e>{x}</m:e></m:d>'
omath = lambda body: f'<m:oMath {M}>{body}</m:oMath>'

EQ_ROCKET = omath(r("Δv=") + sub("I", "sp") + sub("g", "0") + func("ln", paren(frac(sub("m", "0"), sub("m", "f")))))
EQ_THRUST = omath(r("F=") + dot("m") + sub("v", "e") + r("+") + paren(sub("p", "e") + r("−") + sub("p", "a")) + sub("A", "e"))
EQ_STRESS = omath(r("σ=") + frac(r("P"), r("A")) + r("≤") + sub("σ", "y") + r("/") + sub("n", "s"))
EQ_DRAG = omath(sub("F", "D") + r("=") + frac(r("1"), r("2")) + r("ρ") + sup("V", "2") + sub("C", "D") + r("S"))

def add_math(par, xml):
    par._p.append(parse_xml(xml))

d = Document()
d.add_heading("Kestrel Propulsion Design Note (fictional test sample)", 1)
d.add_paragraph("The vehicle velocity change follows the rocket equation:")
add_math(d.add_paragraph(), EQ_ROCKET)
d.add_paragraph("Engine thrust at the nozzle exit is:")
add_math(d.add_paragraph(), EQ_THRUST)
d.add_paragraph("where ṁ is the propellant mass flow rate and v_e is the effective exhaust velocity.")
d.add_heading("Structural Margin", 2)
add_math(d.add_paragraph(), EQ_STRESS)
d.add_paragraph("The aerodynamic drag on the fairing is estimated as F_D = ½ ρ V² C_D S during ascent.")
d.add_heading("Nomenclature", 2)
t = d.add_table(rows=1, cols=2)
t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Symbol", "Meaning"
for sym_xml, meaning in [(omath(r("Δv")), "change in velocity"), (omath(sub("I", "sp")), "specific impulse"),
                         (omath(sub("g", "0")), "standard gravity"), (omath(sub("m", "0")), "initial mass"),
                         (omath(sub("m", "f")), "final mass"), (omath(r("σ")), "applied stress"),
                         (omath(sub("σ", "y")), "yield strength"), (omath(r("ρ")), "air density")]:
    row = t.add_row()
    row.cells[0].paragraphs[0]._p.append(parse_xml(sym_xml))
    row.cells[1].text = meaning
d.save(os.path.join(OUT, "Kestrel_Propulsion_Note.docx"))

# PowerPoint: an equation-editor equation inside a text box paragraph (as Office writes it, minus the picture fallback)
prs = Presentation(); sl = prs.slides.add_slide(prs.slide_layouts[5]); sl.shapes.title.text = "Drag Estimate"
tb = sl.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1)); p = tb.text_frame.paragraphs[0]
a14 = '<a14:m xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main">' + \
      f'<m:oMathPara {M}>' + EQ_DRAG.replace(f' {M}', '') + '</m:oMathPara></a14:m>'
p._p.append(parse_xml(a14))
prs.save(os.path.join(OUT, "Kestrel_Equation_Slide.pptx"))

# Typed math -> PDF through Word
d2 = Document()
d2.add_heading("Kestrel Loads Summary (fictional test sample)", 1)
for line in ["Dynamic pressure: q = ½ ρ V²",
             "Mach number: M = V / a, where a is the local speed of sound.",
             "Bending stress σ_b = M_b · c / I_x must stay below σ_y / n_s.",
             "Reynolds number Re = ρ V L / μ, where μ is the dynamic viscosity.",
             "TRL = 6 and the total budget = $4.2M are not equations."]:
    d2.add_paragraph(line)
typed = os.path.join(OUT, "_typed.docx"); d2.save(typed)
pdf = os.path.join(OUT, "Kestrel_Loads_Typed.pdf")
try:
    import win32com.client  # optional
    w = win32com.client.Dispatch("Word.Application"); w.Visible = False
    doc = w.Documents.Open(typed); doc.SaveAs(pdf, FileFormat=17); doc.Close(); w.Quit()
except Exception as e:
    print("PDF not made (needs Word):", e)

# Equation picture
im = Image.new("RGB", (1400, 260), "white"); dr = ImageDraw.Draw(im)
font = ImageFont.truetype(r"C:\Windows\Fonts\cambria.ttc", 64)
dr.text((60, 80), "Δv = Isp · g0 · ln(m0 / mf)", fill="black", font=font)
im.save(os.path.join(OUT, "Kestrel_Equation_Picture.png"))
print("made", sorted(os.listdir(OUT)))
