"""3.24.0 the setup written on the effort's template: one template per planned volume (named for the effort and the
volume, next version, the volume on its cover) and the setup written into a document made from it: the template's
styles, cover and section breaks stay, its sample pages go, the structure's headings and every placed sentence come in,
each kind of reference text in its own style, hidden text as chosen; a style the template already has is used; the
template is never written; Ready to make lists what is still open."""
import os, re, sys, tempfile, zipfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import app_gui as A
import compliance as C, setupdoc as SD, setuptemplate as ST, templatereg as TR, effortrec as RR, excerpts as EX

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
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management\nVolume II Management\n2.1 Schedule")
for it in M.items:
    it["decision"] = "Keep" if it["suggest"] != "Drop" else "Drop"
kept = [it for it in M.items if it["decision"] == "Keep"]
SD.place(M, kept[0]["id"], "1.1 Thermal Design"); SD.place(M, kept[1]["id"], "2.1 Schedule")
SD.setup_of(M)["mgmt"]["1.1 Thermal Design"] = "Lead with the test campaign."
cfg = os.path.join(d, "config"); os.makedirs(cfg)
opts = ST.options(M)
check("every kind starts hidden, in its own style", all(o["hidden"] for o in opts.values()) and opts["rfp"]["style"] == "SK RFP Requirement")
opts["pm"]["hidden"] = False
ST.set_options(M, opts)
out = ST.make_all(M, os.path.join(d, "exports"), cfg, effort_name="Kestrel", info={"solicitation": "FA8810-26-R-0042"})
check("one template and one setup per planned volume", len(out) == 2 and all(os.path.isfile(x["template"]) and os.path.isfile(x["setup"]) for x in out),
      [(x["volume"], x["setup"]) for x in out])
check("each template is named for the effort and the volume, version 1", [x["template_name"] for x in out] == ["Kestrel Volume I Technical", "Kestrel Volume II Management"]
      and all(x["version"] == 1 for x in out) and TR.latest(cfg, "Kestrel Volume I Technical")["v"] == 1, [x["template_name"] for x in out])
z = zipfile.ZipFile(out[0]["setup"])
doc = z.read("word/document.xml").decode()
sty = z.read("word/styles.xml").decode()
check("the setup is a document made from the template (not a template)", "template.main+xml" not in z.read("[Content_Types].xml").decode()
      and "document.main+xml" in z.read("[Content_Types].xml").decode())
check("the volume sits on its cover, the solicitation too", ">Volume I Technical<" in doc and "FA8810-26-R-0042" in doc)
check("the template's sample pages are gone", "Sample data table" not in doc and "Chapter title" not in doc, re.findall(r"<w:t[^>]*>([^<]{0,40})", doc)[:30])
check("the structure's headings and the placed sentence come in", "Thermal Design" in doc and kept[0]["text"][:30] in doc.replace("&amp;", "&"))
h2 = re.search(r'<w:p><w:pPr><w:pStyle w:val="Heading2"/>(?:(?!</w:p>).)*Thermal Design.*?</w:p>', doc, re.S)
check("3.72.0: Word numbers the heading (the template numbers Heading 2): no typed 1.1, Word's numbering kept",
      h2 and ">1.1 " not in h2.group(0) and 'w:numId w:val="0"' not in h2.group(0), h2.group(0)[:300] if h2 else doc[:300])
check("the TOC and the section breaks stay", "TOC \\" in doc and doc.count("<w:sectPr") >= 3, doc.count("<w:sectPr"))
check("RFP text is in its own style, hidden", 'w:pStyle w:val="SKRFPRequirement"' in doc and re.search(r'w:styleId="SKRFPRequirement".*?<w:vanish/>', sty, re.S))
pm = re.search(r'w:styleId="SKPMDirection".*?</w:style>', sty, re.S).group(0)
check("PM direction in its style, shown (as chosen)", 'w:pStyle w:val="SKPMDirection"' in doc and "<w:vanish" not in pm and "Lead with the test campaign" in doc)
check("no colors typed on the text: the styles carry them", 'w:color w:val="7030A0"' not in doc.split("<w:body>")[1])
check("the file says which template and version it was written on", "SK Template Version" in z.read("docProps/custom.xml").decode())
import templatecheck as TC
vr = TC.validate(out[0]["setup"])
check("the setup passes the validation report: every style it uses is defined, every field points somewhere", not vr.problems(), vr.text())
# a template that already has the style: it is used
opts2 = ST.options(M); opts2["rfp"]["style"] = "Caption"
ST.set_options(M, opts2)
out2 = ST.make_all(M, os.path.join(d, "exports2"), cfg, effort_name="Kestrel")
d2 = zipfile.ZipFile(out2[0]["setup"]).read("word/document.xml").decode()
check("a style the template already has is used for a kind", 'w:pStyle w:val="Caption"' in d2 and out2[0]["version"] == 2, out2[0]["version"])
import prodwordgate as WG
if WG.available():                                  # the build PC: Word opens the setup, with its hidden reference text
    oc = WG.open_check(out[0]["setup"])
    print("WORD OPEN:", oc)
    check("Word opens the setup and paginates it, the reference text hidden", oc.get("ok") and oc.get("pages", 0) >= 3
          and oc.get("hidden_paragraphs", 0) >= 1, oc)
# ready to make
rec = RR.Record(d)
EX.add(rec, "objective", [EX.part_of(kept[0])])
r = {w: (ok, n) for ok, w, n in ST.ready(M, rec)}
check("Ready to make lists what is still open", r["Every requirement is in a section of the structure"][1] == len(kept) - 2
      and r["Every customer objective is mapped to a section"] == (False, 1) and r["Every sentence is decided or ignored"][0], r)
print(f"SETUP ON TEMPLATE {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
