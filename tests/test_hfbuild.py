"""3.42.0 headers and footers built here as tables (hfbuild.py, prodengine/pe/hf.py) and Quick Parts made here (qpmake.py):
Rule 7's footer is the default and passes Rule 7, a cells table writes its widths, lines, bold and sizes and a logo, an
empty (cover) footer is not a Rule 7 finding, the volume tokens in cells are read, and a header or footer saved as a
Quick Part is a Word file whose glossary Make templates copies into the template in the gallery it was saved to.
Fictional content."""
import base64, os, re, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import hfbuild as HB, prodrules as PRL, prodtemplate as PT, qpmake as QM, rulecheck as RC
from prodengine.engine.pkg import Package
from prodengine.pe import rules as PR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
MK = "Use or disclosure of data on this page is subject to the Kestrel restriction."


def std_():
    s = PRL.for_effort(tempfile.mkdtemp())
    s["style_roles"]["a_number"] = "Heading 2"
    s["variables"]["marking"] = MK
    return s


def footers(path):
    z = zipfile.ZipFile(path)
    return {n: z.read(n).decode("utf-8") for n in z.namelist() if re.match(r"word/footer\d+\.xml$", n)}


check("the standard footers are Rule 7's (front, body, appendix); the cover footer is empty",
      all(HB.is_r7(PR.COMPANY["hf_layouts"][k]["footer"]) for k in ("front", "body", "appendix"))
      and PR.COMPANY["hf_layouts"]["cover"]["footer"] == {})
check("Make templates checks every rule now (nothing left for later)", PT.RULES_LATER == {})
r7 = HB.r7_footer({"hf_r7": {"line2": "Kestrel standard line"}})
mid = r7["table"]["cells"][1]["lines"]
check("Rule 7's footer: the marking bold, then the team's line", mid[0]["text"] == "{marking}" and mid[0]["bold"]
      and mid[1]["text"] == "Kestrel standard line" and HB.r7_footer()["table"]["cells"][1]["lines"][1]["text"] == "")

s = std_()
job = PT.make(s, tempfile.mkdtemp(), "")
ru = [(f.get("rule"), f.get("what")) for f in job.check.findings if str(f.get("rule", "")).startswith("RU7")]
check("a template made from the standard keeps Rule 7 (no RU7 finding)", ru == [], ru)
fx = footers(job.copy)
body = next((x for x in fx.values() if "PAGE" in x), "")
check("the footer reads the A number's style and the page, with the marking in the middle",
      'STYLEREF "Heading 2"' in body and " PAGE " in body and MK in body and body.count("<w:tc>") + body.count("<w:tc ") == 3, body[:300])
rc = RC.check(Package(job.copy), s, marking=MK)
check("Rule 7 reads the built footer as kept, and Rule 3 finds the marking at the bottom center of the response",
      not [c for c, _w in rc if c == "RU7"] and not [w for c, w in rc if c == "RU3" and "bottom" in w and ("Section 2" in w or "Section 3" in w)], rc)

s2 = std_(); s2["style_roles"]["a_number"] = ""
job2 = PT.make(s2, tempfile.mkdtemp(), "")
body2 = next((x for x in footers(job2.copy).values() if "PAGE" in x), "")
check("with no style chosen for the A number, the left cell stays blank (no stray token)", "{a_number}" not in body2
      and "STYLEREF" not in body2 and not [f for f in job2.check.findings if str(f.get("rule", "")).startswith("RU7")])

png = os.path.join(tmp, "kestrel_logo.png")
from PIL import Image
Image.new("RGB", (200, 50), (20, 90, 160)).save(png)
lg = HB.logo(png, w_in=1.0, align="right")
check("a logo keeps the picture's proportions", lg["h_in"] == 0.25 and lg["ct"] == "image/png" and lg["align"] == "right", lg)
s3 = std_()
s3["hf_layouts"]["body"]["header"] = {"table": {"borders": "below", "cells": [
    {"width_in": 1.5, "lines": [], "logo": lg},
    {"width_in": 0, "lines": [{"text": "{volume_name}", "align": "center", "size": 9, "bold": True},
                              {"text": "Kestrel", "align": "center", "size": None, "bold": False}], "logo": None}]}}
s3["variables"]["volume_name"] = "Volume I Technical"
job3 = PT.make(s3, tempfile.mkdtemp(), "")
z = zipfile.ZipFile(job3.copy)
hdr = [z.read(n).decode() for n in z.namelist() if re.match(r"word/header\d+\.xml$", n) and "Kestrel" in z.read(n).decode()]
h = hdr[0] if hdr else ""
check("a header table writes its columns (1.5 in and the rest), the line under, bold and size",
      '<w:gridCol w:w="2160"/>' in h and 'w:val="single"' in h and "<w:b/>" in h and '<w:sz w:val="18"/>' in h, h[:400])
rels = [n for n in z.namelist() if n.startswith("word/_rels/header")]
media = [n for n in z.namelist() if n.startswith("word/media/")]
check("the logo is in the header as a picture with its part", "<a:blip" in h and media and any("image" in z.read(r).decode() for r in rels), media)
check("the cells' tokens are volume tokens the layouts use", "volume_name" in PRL.hf_tokens(s3))

# an empty footer (a cover's) is not a Rule 7 finding
s4 = std_()
s4["pagination"] = PRL.presets()["team"] if hasattr(PRL, "presets") else s4["pagination"]
job4 = PT.make(s4, tempfile.mkdtemp(), "")
empty = [n for n, x in footers(job4.copy).items() if not re.findall(r"<w:t[ >]", x) and "instrText" not in x]
check("the cover's empty footer is skipped by Rule 7", not [f for f in job4.check.findings if str(f.get("rule", "")).startswith("RU7")],
      [f.get("what") for f in job4.check.findings if str(f.get("rule", "")).startswith("RU7")])

# Quick Parts made here
qdir = os.path.join(tmp, "parts")
built = HB.build_part(s3, "body", "header", parts_dir=qdir)
check("a built header is read back with its picture", "<w:tbl" in built["header"] and len(built["header_media"]) == 1)
e = HB.make_quick_part(s3, "body", "header", "Kestrel header", category="Kestrel", parts_dir=qdir, built=built)
src = os.path.join(qdir, e["source"])
zq = zipfile.ZipFile(src)
gl = zq.read("word/glossary/document.xml").decode()
check("Save as a Quick Part writes a Word file whose glossary holds it in the Headers gallery",
      'w:val="Kestrel header"' in gl and 'w:val="hdrs"' in gl and 'w:val="Kestrel"' in gl and any(n.startswith("word/media/") for n in zq.namelist()))
check("the picture's link points at the Quick Part's own copy", re.search(r'r:embed="rIdQp1"', gl) is not None
      and "rIdQp1" in zq.read("word/glossary/_rels/document.xml.rels").decode())
check("the standard lists it once (saving again replaces it)", [x["name"] for x in s3["quick_parts"]["entries"]].count("Kestrel header") == 1
      and HB.make_quick_part(s3, "body", "header", "Kestrel header", parts_dir=qdir, built=built)
      and [x["name"] for x in s3["quick_parts"]["entries"]].count("Kestrel header") == 1)
check("the same Quick Part is written once (named by its content)", QM.make_source(qdir, [{"name": "Kestrel header", "category": "Kestrel",
      "gallery": "hdrs", "xml": built["header"], "media": built["header_media"]}], label="Kestrel header") == src)
check("nothing to save is refused", HB.make_quick_part(s3, "body", "header", "  ", parts_dir=qdir, built=built) is None
      and HB.make_quick_part(s3, "body", "header", "Empty", parts_dir=qdir, built={"header": ""}) is None)
s3["quick_parts"]["entries"] = [x for x in s3["quick_parts"]["entries"] if x["name"] == "Kestrel header"]
s3["quick_parts"]["entries"][0]["category"] = "Kestrel"
job5 = PT.make(s3, tempfile.mkdtemp(), "", parts_dir=qdir)
z5 = zipfile.ZipFile(job5.copy)
g5 = next((z5.read(n).decode() for n in z5.namelist() if n.startswith("word/glossary/") and n.endswith("document.xml")), "")
check("Make templates puts it in the template, in the Headers gallery it was saved to", 'w:val="Kestrel header"' in g5
      and re.search(r'Kestrel header.*?w:gallery w:val="hdrs"', g5, re.S) is not None, g5[:300])

n = sum(checks)
print(f"HF BUILD {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
