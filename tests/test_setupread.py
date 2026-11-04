"""3.43.0 read the setup back (setupread.py): a setup written on the template, then filled the way an author does
(words under one heading, more than the budget under another, a requirement's hidden text deleted, another moved under
a different heading, a paragraph pasted with its own style). Each section's status, words and pages against its budget,
the requirements removed and moved, the styles brought in; the draft is never changed; the record keeps a line; the
export has its three sheets. Fictional content (the Kestrel set)."""
import os, re, sys, tempfile, zipfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import app_gui as A
import compliance as C, setupdoc as SD, setuptemplate as ST, pagebudget as PB, setupread as SR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


RFP = os.path.join(os.path.dirname(HERE), "test_samples", "rfp_walk")
d = tempfile.mkdtemp()
files = sorted(f for f in os.listdir(RFP) if f.lower().endswith((".pdf", ".docx")))
heads = []
M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([(f, A.typed_chunks(os.path.join(RFP, f))) for f in files], heads)
M.headings = heads
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management\n1.3 Test Campaign\nVolume II Management\n2.1 Schedule")
for it in M.items:
    it["decision"] = "Keep" if it["suggest"] != "Drop" else "Drop"
reqs = [it for it in M.items if it["decision"] == "Keep" and SD.kind_of(it) == "Requirement" and len(SD._norm(it["text"])) >= 30]
r1, r2, r3, r4 = reqs[:4]
SD.place(M, r1["id"], "1.1 Thermal Design"); SD.place(M, r2["id"], "1.1 Thermal Design")
SD.place(M, r3["id"], "1.2 Risk Management"); SD.place(M, r4["id"], "2.1 Schedule")
PB.set_pages(M, "1.1 Thermal Design", 2); PB.set_pages(M, "1.2 Risk Management", 0.5)
cfg = os.path.join(d, "config"); os.makedirs(cfg)
out = ST.make_all(M, os.path.join(d, "exports"), cfg, effort_name="Kestrel")
vol1 = out[0]["setup"]

# ---- the author fills it in
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
from lxml import etree
q = lambda t: f"{{{W}}}{t}"
z = zipfile.ZipFile(vol1)
files_ = {n: z.read(n) for n in z.namelist()}
root = etree.fromstring(files_["word/document.xml"])
sroot = etree.fromstring(files_["word/styles.xml"])
names = {s.get(q("styleId")): s.find(q("name")).get(q("val")) for s in sroot.iter(q("style")) if s.find(q("name")) is not None}


def para(text, sid=None):
    p = etree.Element(q("p"))
    if sid:
        etree.SubElement(etree.SubElement(p, q("pPr")), q("pStyle")).set(q("val"), sid)
    r = etree.SubElement(p, q("r")); t = etree.SubElement(r, q("t")); t.text = text
    return p


def heading_p(title):
    return next(p for p in root.iter(q("p")) if SD._norm("".join(t.text or "" for t in p.iter(q("t")))) in (SD._norm(title), SD._norm(title.split(" ", 1)[1])))


words = lambda n: " ".join(f"kestrel{i}" for i in range(n))
h11, h12, h13 = heading_p("1.1 Thermal Design"), heading_p("1.2 Risk Management"), heading_p("1.3 Test Campaign")
h11.addnext(para(words(500)))                      # 500 words of two pages: Near budget (at 450 a page)
h12.addnext(para(words(300)))                      # 300 words of half a page: Over budget
rid = SD._norm(r2["text"])
gone = [p for p in root.iter(q("p")) if SD._norm("".join(t.text or "" for t in p.iter(q("t")))).find(rid) >= 0]
check("the setup holds the requirement before the author deletes it", len(gone) >= 1)
for p in gone:
    p.getparent().remove(p)                         # r2's hidden text deleted
mv = [p for p in root.iter(q("p")) if SD._norm(r3["text"]) in SD._norm("".join(t.text or "" for t in p.iter(q("t"))))]
for p in mv:
    p.getparent().remove(p); h13.addnext(p)        # r3 moved under 1.3
sty = etree.SubElement(sroot, q("style")); sty.set(q("type"), "paragraph"); sty.set(q("styleId"), "NormalWeb")
etree.SubElement(sty, q("name")).set(q("val"), "Normal (Web)")
h11.addnext(para("Pasted from an old proposal.", "NormalWeb"))
files_["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
files_["word/styles.xml"] = etree.tostring(sroot, xml_declaration=True, encoding="UTF-8", standalone=True)
filled = os.path.join(d, "Volume I Technical - filled.docx")
with zipfile.ZipFile(filled, "w", zipfile.ZIP_DEFLATED) as zo:
    for n, b in files_.items():
        zo.writestr(n, b)
before = hashlib.sha256(open(filled, "rb").read()).hexdigest()

# ---- read it back
rep = SR.read(M, filled, template=out[0]["template"])
by = {r["section"]: r for r in rep["sections"]}
check("the volume's sections are read by their headings (Volume II's are not in this file)", set(by) >= {"1.1 Thermal Design", "1.2 Risk Management",
      "1.3 Test Campaign"} and "2.1 Schedule" not in by and rep["matched"], list(by))
check("the author's own words are counted (not the headings or the setup's text)", by["1.1 Thermal Design"]["words"] == 505
      and by["1.2 Risk Management"]["words"] == 300, (by["1.1 Thermal Design"]["words"], by["1.2 Risk Management"]["words"]))
check("Near budget: half the budget or more", by["1.1 Thermal Design"]["status"] == "Near budget" and by["1.1 Thermal Design"]["pages"] == 1.1)
check("Over budget: past it", by["1.2 Risk Management"]["status"] == "Over budget")
check("Not started: no words of the author's own", by["1.3 Test Campaign"]["status"] == "Not started")
check("a requirement whose text was deleted is listed as removed", [x["id"] for x in by["1.1 Thermal Design"]["removed"]] == [r2["id"]],
      by["1.1 Thermal Design"]["removed"])
check("a requirement now under another heading is listed as moved", [x["id"] for x in by["1.2 Risk Management"]["moved"]] == [r3["id"]]
      and "1.3 Test Campaign" in by["1.2 Risk Management"]["moved"][0]["to"], by["1.2 Risk Management"]["moved"])
check("the requirement left in place is neither", not by["1.1 Thermal Design"]["moved"] and r1["id"] not in [x["id"] for x in by["1.1 Thermal Design"]["removed"]])
check("the pasted style is listed as brought in, with where it first shows", [(s["style"], s["count"], s["first"]) for s in rep["styles"]]
      == [("Normal (Web)", 1, "1.1 Thermal Design")], rep["styles"])
check("the template's and the setup's own styles are not", not [s for s in rep["styles"] if s["style"].startswith("SK ") or s["style"].startswith("Heading")])
check("the summary line says it in a sentence", "1 near budget" in SR.summary_line(rep) and "1 requirement(s) removed" in SR.summary_line(rep)
      and "1 style(s) brought in" in SR.summary_line(rep), SR.summary_line(rep))
check("the draft is never changed", hashlib.sha256(open(filled, "rb").read()).hexdigest() == before)
check("the setup as written: every section Not started, nothing removed", all(r["status"] == "Not started" and not r["removed"]
      for r in SR.read(M, vol1)["sections"]), [(r["section"], r["status"], r["removed"]) for r in SR.read(M, vol1)["sections"]])
check("pages follow the words a page set", {r["section"]: r for r in SR.read(M, filled, wpp=250)["sections"]}["1.1 Thermal Design"]["status"] == "Over budget")
check("the template is found from the file's SK Template property", SR.file_template(vol1).endswith(".dotx")
      and os.path.basename(SR.file_template(vol1)).startswith("Kestrel Volume I Technical"), SR.file_template(vol1))
other = os.path.join(d, "unrelated.docx")
import docxw
dd = docxw.Doc(); dd.rich([("A Kestrel memo with no structure in it.", None)]); dd.save(other)
r0 = SR.read(M, other)
check("a document with none of the structure's headings says so", not r0["matched"] and "No heading" in SR.summary_line(r0))


import effortrec as RR
rc = RR.Record(tempfile.mkdtemp())
SR.keep(rc, rep); SR.keep(rc, rep)
check("the record keeps one line per file, newest first", len(SR.latest(rc)) == 1 and SR.latest(rc)[0]["removed"] == 1)
xl = SR.export_xlsx(rep, os.path.join(d, "status.xlsx"))
import openpyxl
wb = openpyxl.load_workbook(xl)
check("the export has Sections, Requirements and Styles brought in", wb.sheetnames == ["Sections", "Requirements", "Styles brought in"]
      and wb["Sections"].max_row == 1 + len(rep["sections"]) and wb["Requirements"].max_row == 3 and wb["Styles brought in"]["A2"].value == "Normal (Web)")

n = sum(checks)
print(f"SETUP READ {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
