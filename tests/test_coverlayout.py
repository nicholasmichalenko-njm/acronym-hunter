"""3.27.0 the cover layout and volumes that continue, no window: a kept cover read into its pieces (a picture behind
the text, a floating table, a text box placed by alignment, the lines of text and where they sit); pieces moved and
resized and a line set to show a field, in a new copy (the original unchanged); the template made with that cover
finds the volume name on it, so its headers are built; a volume that continues the one before starts its pages and
chapters there, suggested from the draft before."""
import hashlib, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import copy
import coverlayout as CL
import prodrules as PRL, prodtemplate as PT, prodparts as PP, setuptemplate as ST
import _coverfixture as F

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cov = F.make(os.path.join(tmp, "cover.docx"))
data = open(cov, "rb").read()
h0 = hashlib.sha256(data).hexdigest()
lay = CL.read(data)
kinds = [p["kind"] for p in lay["pieces"]]
check("the page and its margins", lay["page"]["w"] == 8.5 and lay["page"]["h"] == 11 and lay["page"]["margins"]["left"] == 1.25)
pic = next(p for p in lay["pieces"] if p["kind"] == "picture")
check("a picture behind the text, floating, from the page's corner", pic["floating"] and pic["behind"] and pic["x"] == 0 and pic["w"] == 8.5)
tb = next(p for p in lay["pieces"] if p["kind"] == "textbox")
check("a text box placed by alignment: centered between the margins", tb["floating"] and abs(tb["x"] - 2.75) < 0.01 and tb["y"] == 9.0 and tb["text"] == "Company Name")
tbl = next(p for p in lay["pieces"] if p["kind"] == "table")
check("a floating table over the picture, at its place", tbl["floating"] and tbl["x"] == 1.0 and tbl["y"] == 3.0 and tbl["rows"] == 2)
paras = [p for p in lay["pieces"] if p["kind"] == "paragraph"]
check("each line of text and where it sits", [(p["text"], p["where"]) for p in paras] == [("Prepared for the United States Space Force", "the page"),
      ("VOLUME I TECHNICAL", "a table cell"), ("FA8810-26-R-0042", "a table cell"), ("Company Name", "a text box")], [(p["text"], p["where"]) for p in paras])
check("the picture's bytes come with it", CL.picture_bytes(data, pic["embed"])[:4] == b"\x89PNG")
vn = next(p["id"] for p in paras if p["text"] == "VOLUME I TECHNICAL")
so = next(p["id"] for p in paras if p["text"] == "FA8810-26-R-0042")
out = CL.apply(data, {pic["id"]: {"x": 0.25, "y": 0.5, "w": 8.0, "h": 3.2}, tbl["id"]: {"x": 1.5, "y": 3.75},
                      tb["id"]: {"x": 2.0, "y": 9.5}, vn: {"field": "volume_name"}, so: {"field": "solicitation"}})
lay2 = CL.read(out)
p2 = {p["id"]: p for p in lay2["pieces"]}
check("moved and resized in the copy", (p2[pic["id"]]["x"], p2[pic["id"]]["y"], p2[pic["id"]]["w"], p2[pic["id"]]["h"]) == (0.25, 0.5, 8.0, 3.2)
      and (p2[tbl["id"]]["x"], p2[tbl["id"]]["y"]) == (1.5, 3.75) and (p2[tb["id"]]["x"], p2[tb["id"]]["y"]) == (2.0, 9.5))
check("lines show their fields", p2[vn]["field"] == "volume_name" and p2[so]["field"] == "solicitation")
check("the kept cover is unchanged", hashlib.sha256(open(cov, "rb").read()).hexdigest() == h0)
check("the field styles the cover uses but does not define are listed (the template has them)", "PEVolumeName" in CL.missing_styles(out))
# a template made with the edited cover: the headers read the volume name from it
pdir = os.path.join(tmp, "parts")
name = PP.save_part(pdir, out, "cover layout")
std = PRL.engine_ready(copy.deepcopy(PRL.COMPANY))
std["page_parts"] = {"cover": name}
std["variables"].update({"volume_name": "Volume I Technical", "solicitation": "FA8810-26-R-0042"})
std["name"] = "Cover layout"
job = PT.make(std, os.path.join(tmp, "out"), "", parts_dir=pdir)
z = zipfile.ZipFile(job.copy)
doc = z.read("word/document.xml").decode("utf-8")
check("the template carries the edited cover", "VOLUME I TECHNICAL" in doc and 'w:pStyle w:val="PEVolumeName"' in doc)
hf = [st for st in job.steps if st.get("key") == "hf_build"]
check("the headers are built: the volume name is on the cover", hf and not hf[0].get("refused"), hf)
# volumes that continue
vdir = os.path.join(tmp, "Volumes"); os.makedirs(vdir)
import docx
d = docx.Document()
for i in range(3):
    d.add_paragraph(f"Chapter {i + 1}", style="Heading 1"); d.add_paragraph("Text.")
d.save(os.path.join(vdir, "Kestrel Volume I Technical draft.docx"))
zz = zipfile.ZipFile(os.path.join(vdir, "Kestrel Volume I Technical draft.docx"))
files = {i.filename: zz.read(i.filename) for i in zz.infolist()}
app = files.get("docProps/app.xml", b'<?xml version="1.0"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"></Properties>')
files["docProps/app.xml"] = app.replace(b"</Properties>", b"<Pages>24</Pages></Properties>") if b"<Pages>" not in app else app
zz.close()
with zipfile.ZipFile(os.path.join(vdir, "Kestrel Volume I Technical draft.docx"), "w") as zo:
    for k, v in files.items():
        zo.writestr(k, v)
check("a draft's pages and chapters", ST.draft_counts(os.path.join(vdir, "Kestrel Volume I Technical draft.docx"))[1] == 3)
plans = [{"volume": "Volume I Technical"}, {"volume": "Volume II Management"}, {"volume": "Volume III Cost"}]
sg = ST.suggest_starts(plans, vdir)
check("Volume II continues Volume I: suggested from its draft", sg[0]["page"] == 1 and sg[1]["chapter"] == 4
      and "Kestrel Volume I Technical draft.docx" in sg[1]["why"], sg)
check("a volume with no draft before it says to type where it starts", "type where it starts" in sg[2]["why"])
std2 = PRL.engine_ready(copy.deepcopy(PRL.COMPANY))
for p in std2["pagination"]["parts"]:
    if p["key"] == "body":
        p["numbers"]["chapter_level"] = None
std2["heading_numbering"]["on"] = True
ST.with_starts(std2, 25, 4)
body = next(p for p in std2["pagination"]["parts"] if p["key"] == "body")
check("the response's pages start where the volume before ended", body["numbers"]["start_at"] == 25)
check("its chapters start after the volume before's", std2["heading_numbering"]["levels"][0]["start"] == 4)
std2["name"] = "Volume II"
std2["variables"].update({"volume_name": "Volume II", "solicitation": "S"})
job2 = PT.make(std2, os.path.join(tmp, "out2"), "")
z2 = zipfile.ZipFile(job2.copy)
d2 = z2.read("word/document.xml").decode("utf-8"); n2 = z2.read("word/numbering.xml").decode("utf-8")
check("the template's response starts at page 25", 'w:start="25"' in d2)
check("its Heading 1 numbers start at 4", '<w:start w:val="4"/>' in n2)
std3 = PRL.engine_ready(copy.deepcopy(PRL.COMPANY)); ST.with_starts(std3, 25, 1)
check("pages numbered by chapter (1-1) are left alone: the chapters carry on instead",
      next(p for p in std3["pagination"]["parts"] if p["key"] == "body")["numbers"]["start_at"] == 1)
print(f"COVER LAYOUT {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
