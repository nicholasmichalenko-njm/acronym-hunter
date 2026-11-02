"""3.17.0 graphics standards, no window: pictures in a Word document and a PowerPoint deck read against the profile's
graphics rules: the picture type, its resolution at the size it is placed, its width against the text width, alt text,
a caption next to it, CMYK, its file size, and the fonts and sizes of text in charts and text boxes; Check in Fix a Copy
lists them under Graphics, check only (the file is never changed)."""
import io, os, sys, tempfile, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
import docx
from docx.shared import Inches
import pptx
import prodgraphics as PG, prodfix as PF, prodrules as PRL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()


def png(w, h, mode="RGB", fmt="PNG"):
    b = io.BytesIO(); Image.new(mode, (w, h), (40, 90, 160) if mode == "RGB" else (10, 20, 30, 0)).save(b, fmt); b.seek(0)
    return b


# a document: a sharp figure with caption and alt text; a blurry one too wide with neither; a CMYK JPEG
d = docx.Document()
d.add_paragraph("Our approach")
d.add_picture(png(1500, 900), width=Inches(5))                    # 300 ppi at 5 in
d.paragraphs[-1].runs[0]._r.xpath(".//wp:docPr")[0].set("descr", "Architecture diagram")
d.add_paragraph("Figure 1-1. Architecture", style="Caption")
d.add_paragraph("More text")
d.add_picture(png(600, 300), width=Inches(7.5))                   # 80 ppi, wider than 6.5 in of text
d.add_paragraph("Closing text")
d.add_picture(png(900, 600, "RGB", "JPEG"), width=Inches(3))     # made CMYK below (python-docx cannot read a CMYK header)
d.add_paragraph("Figure 1-2. Site", style="Caption")
src = os.path.join(tmp, "Volume I.docx"); d.save(src)
import zipfile
zin = zipfile.ZipFile(src); parts = {n: zin.read(n) for n in zin.namelist()}; zin.close()
jp = next(n for n in parts if n.startswith("word/media/") and n.endswith((".jpg", ".jpeg")))
parts[jp] = png(900, 600, "CMYK", "JPEG").read()
with zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED) as zo:
    for n, b in parts.items():
        zo.writestr(n, b)
before = hashlib.sha256(open(src, "rb").read()).hexdigest()
std = PRL.COMPANY
seen, found = None, []
seen = PG.check_word(open(src, "rb").read(), std, lambda r, w, where: found.append((r, w, where)))
rules = [r for r, _w, _x in found]
check("three pictures are read, with their placed sizes", len(seen) == 3 and abs(seen[0]["w_in"] - 5) < 0.01 and seen[0]["ppi"] == 300,
      [(s["type"], s["ppi"], round(s["w_in"], 2)) for s in seen])
check("the sharp, captioned, described figure passes", not any(x[2].startswith("Picture 1") or "Picture 1 " in x[2] for x in found), found)
check("the blurry one: below the resolution, wider than the text, no alt text, no caption",
      {"G2", "G3", "G7", "G6"} <= set(r for r, _w, x in found if x.startswith("Picture 2")), found)
check("... each says what and how much", any(r == "G2" and "80 ppi" in w and "150 ppi" in w for r, w, _x in found)
      and any(r == "G3" and "7.50 in" in w and "6.00 in" in w for r, w, _x in found), [w for _r, w, _x in found])
check("the CMYK picture is reported", any(r == "G8" for r, _w, x in found if x.startswith("Picture 3")), found)
g2 = dict(std, graphics=dict(PG.DEFAULT, types=["png"], min_ppi=None, alt_text=False, caption=False, rgb_only=False))
found2 = []
PG.check_word(open(src, "rb").read(), g2, lambda r, w, where: found2.append((r, w, where)))
check("only PNG allowed: the JPEG is a type not allowed; rules switched off are not checked",
      [r for r, _w, _x in found2] == ["G1", "G3"] or sorted(r for r, _w, _x in found2) == ["G1", "G3"], found2)
# text in a chart part and a text box: fonts and the smallest size
r = PG.rules_of(dict(std, graphics=dict(PG.DEFAULT, fonts=["Arial"], min_text_pt=8)))
hits = []
PG._font_findings([("Arial", 10.0), ("Comic Sans MS", 6.0)], r, "Chart 1", lambda *a: hits.append(a))
check("text in a drawing: a font not allowed and text below the smallest size", [h[0] for h in hits] == ["G4", "G5"]
      and "Comic Sans MS" in hits[0][1] and "6 pt" in hits[1][1], hits)
check("blank fonts: the profile's body, table and caption fonts", set(PG.rules_of(std)["fonts"]) ==
      {v for v in (std["variables"].get("body_font"), std["variables"].get("table_font"), std["variables"].get("caption_font")) if v})
# Fix a Copy's Check: the findings under Graphics, the file unchanged
chk = PF.check(src, std)
gf = [f for f in chk.findings if f["area"] == "graphics"]
check("Check lists them under Graphics, each to review by hand", len(gf) >= 5 and all(f["fix"] == "" for f in gf)
      and "graphics" in PF.AREAS and PF.RULE_TEXT["G2"].startswith("Resolution"), len(gf))
check("the file is never changed", hashlib.sha256(open(src, "rb").read()).hexdigest() == before)
# a deck
p = pptx.Presentation()
s = p.slides.add_slide(p.slide_layouts[6])
pic = s.shapes.add_picture(png(400, 300), pptx.util.Inches(1), pptx.util.Inches(1), width=pptx.util.Inches(8))   # 50 ppi
pic._element.nvPicPr.cNvPr.set("descr", "")
deck = os.path.join(tmp, "Orals.pptx"); p.save(deck)
chk2 = PF.check(deck, std)
gd = [f for f in chk2.findings if f["area"] == "graphics"]
check("a deck: its pictures by slide, resolution and alt text", any(f["rule"] == "G2" and f["near"].startswith("Slide 1") for f in gd)
      and any(f["rule"] == "G7" for f in gd), [(f["rule"], f["near"]) for f in gd])
from docx.enum.section import WD_SECTION
dc = docx.Document(); dc.add_picture(png(1500, 900), width=Inches(5))      # cover art: no caption, no alt text
dc.add_section(WD_SECTION.NEW_PAGE); dc.add_paragraph("Body text.")
cv = os.path.join(tmp, "Covered.docx"); dc.save(cv)
fc = []
PG.check_word(open(cv, "rb").read(), std, lambda r, w, where: fc.append(r))
check("cover art (the first of several sections) needs no caption and no alt text", not {"G6", "G7"} & set(fc), fc)
check("the profile carries graphics rules from the team standard", PRL.COMPANY["graphics"]["min_ppi"] == 150
      and PRL.COMPANY["graphics"]["max_width"] == "margins")
n = sum(checks)
print(f"PRODGRAPHICS {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
