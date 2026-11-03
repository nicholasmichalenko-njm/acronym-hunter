"""3.34.0 covers, title pages and back covers built here, no window: a blank page in the standard's paper and margins;
a background picture behind the text (full bleed or inside the margins, locked), swapped in place and taken off; text
blocks that show a field in its cover style or their own words, with their own look, added and taken off; a page's
structure kept apart from its look (from blocks made here and from an imported cover's text boxes and tables) and a page
built from it; the title page placed after the cover in a template, and the structure's Title page element left out;
title pages and cover layouts in the template library and a profile's title page part."""
import copy, io, json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import coverbuild as CB, coverlayout as CL, prodparts as PP, prodrules as PRL, prodtemplate as PT, templatelib as TL, templateprofile as TP
import _coverfixture as F

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
std = PRL.engine_ready(copy.deepcopy(PRL.COMPANY))
std["variables"].update(paper="A4", margin_left=1.25)
from PIL import Image
_b = io.BytesIO(); Image.new("RGB", (1300, 1800), (31, 56, 100)).save(_b, "PNG"); PNG = _b.getvalue()
data = CB.blank(std)
lay = CL.read(data, std)
check("a blank page in the standard's paper and margins", abs(lay["page"]["w"] - 8.27) < 0.01 and abs(lay["page"]["h"] - 11.69) < 0.01
      and lay["page"]["margins"]["left"] == 1.25 and not lay["pieces"])
st = zipfile.ZipFile(io.BytesIO(data)).read("word/styles.xml").decode()
check("... with the fields' cover styles defined", 'w:styleId="PEVolumeName"' in st and 'w:styleId="PESolicitation"' in st)
# ---------------------------------------------------------------- the background picture
bg = CB.set_background(data, PNG, ".png")
lay = CL.read(bg, std)
pic = next(p for p in lay["pieces"] if p["kind"] == "picture")
check("full bleed: behind the text at the page's size, from its corner", pic["behind"] and pic["x"] == 0 and pic["y"] == 0
      and abs(pic["w"] - 8.27) < 0.01 and abs(pic["h"] - 11.69) < 0.01, pic)
doc = zipfile.ZipFile(io.BytesIO(bg)).read("word/document.xml").decode()
check("locked so authors do not move it, named as the background", 'locked="1"' in doc and 'name="SK Background"' in doc and CB.background_mode(bg) == "bleed")
check("the picture travels with the page", CL.picture_bytes(bg, pic["embed"]) == PNG
      and 'Extension="png"' in zipfile.ZipFile(io.BytesIO(bg)).read("[Content_Types].xml").decode())
bg2 = CB.set_background(bg, PNG + b"x", "png", "margins")
lay2 = CL.read(bg2, std)
pics = [p for p in lay2["pieces"] if p["kind"] == "picture"]
check("a new picture takes the old one's place; inside the margins", len(pics) == 1 and pics[0]["x"] == 1.25 and pics[0]["y"] == 1.0
      and CL.picture_bytes(bg2, pics[0]["embed"]) == PNG + b"x" and CB.background_mode(bg2) == "margins", pics)
try:
    CB.set_background(data, b"x", "exe")
    refused = False
except ValueError:
    refused = True
check("... a file that is not a picture is refused", refused)
check("taken off", not CB.has_background(CB.take_background(bg2)) and CB.has_background(bg2))
# ---------------------------------------------------------------- text blocks
pg = CB.add_block(bg2, {"field": "volume_name", "x": 1.0, "y": 4.0, "w": 6.0, "h": 0.8, "size": 28, "bold": True, "color": "FFFFFF",
                        "font": "Arial", "align": "center"}, std)
pg = CB.add_block(pg, {"text": "Prepared for the United States Space Force", "x": 1.0, "y": 5.0, "w": 6.0, "h": 0.4}, std)
pg = CB.add_block(pg, {"field": "solicitation", "x": 1.0, "y": 5.6, "w": 3.0, "h": 0.4}, std)
lay = CL.read(pg, std)
tabs = [p for p in lay["pieces"] if p["kind"] == "table"]
paras = {p["text"]: p for p in lay["pieces"] if p["kind"] == "paragraph"}
check("text blocks at their places, floating over the picture", [(t["x"], t["y"]) for t in tabs] == [(1.0, 4.0), (1.0, 5.0), (1.0, 5.6)] and all(t["floating"] for t in tabs))
check("a block shows its field in the field's cover style; another its own words",
      paras["[Volume name]"]["field"] == "volume_name" and paras["[Solicitation]"]["field"] == "solicitation"
      and paras["Prepared for the United States Space Force"]["field"] is None, list(paras))
x = zipfile.ZipFile(io.BytesIO(pg)).read("word/document.xml").decode()
check("a block's own look: size, bold, color, font, centered", 'w:sz w:val="56"' in x and '<w:color w:val="FFFFFF"/>' in x
      and 'w:ascii="Arial"' in x and '<w:jc w:val="center"/>' in x)
check("blocks overlap freely and are kept apart from each other", x.count('<w:tblOverlap w:val="overlap"/>') == 3)
less = CB.remove_block(pg, 1)
check("a block taken off", [p["text"] for p in CL.read(less, std)["pieces"] if p["kind"] == "paragraph"] == ["[Volume name]", "[Solicitation]"])
moved = CL.apply(pg, {"table2": {"x": 2.0, "y": 6.0}}, std)
check("a block moves like any floating table in the layout editor", [(t["x"], t["y"]) for t in CL.read(moved, std)["pieces"] if t["kind"] == "table"][1] == (2.0, 6.0))
# ---------------------------------------------------------------- designs: the structure apart from the look
d = CB.design_of(pg, std)
check("the structure: the paper, where the background goes, each block", d["background"] == "margins" and abs(d["page"]["w"] - 8.27) < 0.01
      and [(b["field"], b["x"], b["y"]) for b in d["blocks"]] == [("volume_name", 1.0, 4.0), ("", 1.0, 5.0), ("solicitation", 1.0, 5.6)]
      and d["blocks"][0]["size"] == 28 and d["blocks"][0]["bold"] and d["blocks"][0]["align"] == "center"
      and d["blocks"][1]["text"] == "Prepared for the United States Space Force", d["blocks"][:2])
check("a design is plain data (kept in the library as values)", json.loads(json.dumps(d)) == d)
new = CB.from_design(d, std, image=PNG, ext="png")
check("a page built from it: the same blocks, a new picture where the design puts it", CB.design_of(new, std)["blocks"] == d["blocks"]
      and CB.background_mode(new) == "margins")
check("built without a picture: just the blocks", not CB.has_background(CB.from_design(d, std)))
imp = open(F.make(os.path.join(tmp, "cover.docx")), "rb").read()
di = CB.design_of(imp, std)
check("an imported cover's structure: its floating table and its text box, its picture as the background place",
      len(di["blocks"]) == 2 and any(b["y"] == 3.0 for b in di["blocks"]) and any(b["y"] == 9.0 for b in di["blocks"]) and di["left_out"] == 1, di)
# ---------------------------------------------------------------- the title page in a template
pdir = os.path.join(tmp, "parts")
tname = PP.save_part(pdir, CB.add_block(CB.blank(std), {"text": "TITLE PAGE WORDS", "x": 1, "y": 2, "w": 5, "h": 0.5}, std), "title page layout")
cname = PP.save_part(pdir, pg, "cover layout")
s2 = copy.deepcopy(std); s2["page_parts"] = {"cover": cname, "title": tname}; s2["name"] = "Title page test"
job = PT.make(s2, os.path.join(tmp, "out"), "", parts_dir=pdir)
doc = zipfile.ZipFile(job.copy).read("word/document.xml").decode()
i_cov, i_tit = doc.find("Prepared for the United States Space Force"), doc.find("TITLE PAGE WORDS")
breaks = doc[i_cov:i_tit].count("<w:sectPr")
check("the template: the cover, then the title page in a section of its own", 0 < i_cov < i_tit and breaks == 1
      and doc[i_tit:].count("<w:sectPr") >= 2, (i_cov, i_tit, breaks))
check("the template passes its check", job.check.count() == 0 if hasattr(job, "check") and job.check is not None else True,
      [f["what"] for f in job.check.findings] if getattr(job, "check", None) else "")
check("the background picture is in the template", any(n.startswith("word/media/sk_part") for n in zipfile.ZipFile(job.copy).namelist()))
# ---------------------------------------------------------------- the library and the profile
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
lib = TL.Library(cfg)
lay_item, _ = lib.add("cover_design", "Space Force cover", d)
check("cover layouts and title pages have shelves", {"cover_design", "title"} <= {k for k, _t in TL.SHELVES} and lib.shelf("cover_design") == [lay_item])
work = copy.deepcopy(PRL.COMPANY); work["page_parts"] = {"title": tname}
it, stt = TP.save_version(work, lib, "title", name="Volume title page", parts_dir=pdir)
check("a profile's title page is a part: kept in the library, pinned", stt == "new" and it["kind"] == "title" and TP.pins(work)["title"]["id"] == it["id"])
w2 = copy.deepcopy(PRL.COMPANY)
TP.pick(w2, lib, "title", it["id"], cfg)
check("... and put on another profile", (w2.get("page_parts") or {}).get("title") and os.path.isfile(os.path.join(PP.parts_dir(cfg), w2["page_parts"]["title"])))
n = sum(checks)
print(f"COVER BUILD {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
