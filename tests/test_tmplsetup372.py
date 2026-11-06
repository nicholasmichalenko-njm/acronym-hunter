"""3.72.0 without a screen: the setup made from a Word template the team brings. Read: its sections in order (cover,
front matter, body, appendix) with numbering and headers, Heading 1 to 4 and the numbering each uses, its Quick Parts by
gallery. Blank by default: the body only, in the template's look, its sample pages gone, the structure on its numbered
headings with no number typed twice, each kind of setup text in its setup style. Picks: the cover and front matter kept,
a cover page Quick Part first and a front matter Quick Part (its picture carried) before the body, a part without a header
and footer. Numbers: a list started where the outline starts; a gap keeps the typed number with Word's turned off. A
.dotm's macros are left out. The check after the make finds a foreign style and a missing requirement. The copy is kept
with the effort. Fictional content (Kestrel)."""
import io, os, re, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import compliance as C, outlinexl as OX, setupdoc as SD, setuptemplate as ST, templatefile as TF, templatesetup as TS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


from _tmplfixture import W, PNG, add_glossary


class _Z:
    def __init__(self, path):
        with zipfile.ZipFile(path) as z:
            self.parts = {n: z.read(n) for n in z.namelist()}

    def read(self, n):
        return self.parts[n]


def body_of(path):
    z = _Z(path)
    return z.read("word/document.xml").decode(), list(z.parts), z


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
# ---- the effort: the 3.71.0 outline workbook into a matrix
import test_outline371 as T
book = OX.read(T.make_outline(os.path.join(tmp, "Kestrel Outline.xlsx")))
prof = {"columns": OX.guess(book["headers"]), "rules": {"Supporting RFP Content": {"-Iauto": "support", "--6B21A8": "customer"}}}
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
M = C.Matrix(os.path.join(ED, "Kestrel_Matrix.xlsx"), "Kestrel")
OX.apply(M, OX.parse(book, prof), "Kestrel Outline.xlsx")
effort_path = os.path.join(ED, "Kestrel_Effort_List.xlsx")
# ---- the team's template: the app's own template, with a glossary
made = ST.make_all(M, os.path.join(tmp, "made"), cfg, effort_name="Kestrel", record=False)
team = add_glossary(made[0]["template"], os.path.join(tmp, "Kestrel Team Template.dotx"))
info = TF.read(team)
check("read: its sections in order with their kinds", [s["kind"] for s in info["sections"]] == ["cover", "front", "body", "appendix"],
      [s["kind"] for s in info["sections"]])
check("read: numbering and headers per section", info["sections"][1]["format"] == "i" and info["sections"][2]["page_number"]
      and info["sections"][2]["header"] and info["sections"][2]["footer"])
check("read: Heading 1 to 4 and the numbering each uses", [(h["level"], h["numbered"], h["sample"]) for h in info["headings"][:3]]
      == [(1, True, "1"), (2, True, "1.1"), (3, True, "1.1.1")], info["headings"][:3])
check("read: its Quick Parts by gallery", sorted((q["name"], q["gallery_name"]) for q in info["quick_parts"])
      == [("Kestrel Cover", "Cover Pages"), ("Kestrel Front Matter", "Quick Parts")], info["quick_parts"])
st = dict((s, h) for _k, s, h in TF.setup_styles_status(info, ST.options(M)))
check("read: which setup styles it has and which are added", st.get("SK RFP Requirement") ==
      ("in the template" if "sk rfp requirement" in info["styles"] else "added"), st)
try:
    TF.read(os.path.join(tmp, "Kestrel Outline.xlsx")); bad = False
except ValueError as e:
    bad = "Word template" in str(e)
check("... a spreadsheet is refused with plain words", bad)
# ---- blank by default
TS.set_choice(M, "*", team, TF.default_picks(info), effort_path)
kept = os.path.join(ED, "Templates", "Kestrel Team Template.dotx")
check("the template is kept with the effort, in its Templates folder", os.path.isfile(kept) and TS.choice(M)["*"]["file"] == "Templates/Kestrel Team Template.dotx")
out = TS.make(M, os.path.join(tmp, "exports"), cfg, effort_name="Kestrel", effort_path=effort_path)
check("one setup per volume, made on the kept template", len(out) == 1 and os.path.isfile(out[0]["setup"]) and out[0]["template"] == kept, out)
doc, names, _z = body_of(out[0]["setup"])
rows = out[0]["check"]
check("the check after the make finds nothing wrong", not TS.problems(rows), [r for r in rows if not r["ok"]])
check("the header's fields still find the cover's volume name: it comes along as hidden text, and the check looks",
      out[0]["plan"]["anchors"] and any(r["what"].startswith("Every header and footer field") and r["ok"] for r in rows), out[0]["plan"]["anchors"])
check("blank: no cover, no table of contents, the sample pages gone", "Table of Contents" not in doc and "Chapter title" not in doc
      and "Appendix title" not in doc and "TOC \\" not in doc)
h = re.findall(r'<w:p><w:pPr><w:pStyle w:val="Heading(\d)"/>(.*?)</w:p>', doc, re.S)
txt = [(lv, re.sub(r"<[^>]+>", "", x)) for lv, x in h]
check("the structure on the template's headings, numbered by its own list (no typed numbers)",
      ("2", "Ground Segment Architecture") in txt and not any(re.match(r"\d", t) for _l, t in txt)
      and not any('w:numId w:val="0"' in x for _l, x in h), txt)
check("each kind in its setup style; the requirement with its reference", 'w:pStyle w:val="SKRFPRequirement"' in doc
      and "L.4.2.1: The offeror shall describe its ground segment architecture." in doc)
sects = doc.count("<w:sectPr")
check("the body keeps the template's section, header and footer (no appendix in the outline: its section goes too)",
      sects == 1 and "headerReference" in doc and 'w:chapStyle="1"' in doc, sects)
import templatecheck as TC
v1, v2 = TC.validate(out[0]["setup"]), None
check("the validation report finds nothing: every style defined, every field and link points somewhere", not v1.problems(), v1.text())
check("a plain Word document", "document.main+xml" in _z.read("[Content_Types].xml").decode())
# ---- picks: cover and front matter kept, Quick Parts, a part without a header and footer
picks = {"keep": [0, 1], "quick_parts": ["Kestrel Cover", "Kestrel Front Matter"], "no_hf": [1]}
TS.set_choice(M, "*", team, picks, effort_path)
out2 = TS.make(M, os.path.join(tmp, "exports2"), cfg, effort_name="Kestrel", effort_path=effort_path)
doc2, names2, z2 = body_of(out2[0]["setup"])
rows2 = out2[0]["check"]
check("picks: the check still finds nothing wrong", not TS.problems(rows2), [r for r in rows2 if not r["ok"]])
check("a cover page Quick Part is a page of its own", re.search(r'KESTREL GROUND SEGMENT PROPOSAL.*?<w:br w:type="page"/>', doc2, re.S))
check("the cover page Quick Part comes first, then the template's cover", doc2.find("KESTREL GROUND SEGMENT PROPOSAL") < doc2.find("Table of Contents")
      and doc2.find("KESTREL GROUND SEGMENT PROPOSAL") >= 0)
check("the front matter Quick Part sits just before the body, its picture carried in",
      doc2.find("Table of Contents") < doc2.find("Proprietary notice for Kestrel") < doc2.find("Ground Segment Architecture")
      and "word/media/sk_seal.png" in names2 and "media/sk_seal.png" in z2.read("word/_rels/document.xml.rels").decode())
check("the front matter has no header or footer (blank ones, as Word needs)", "word/headerSKblank.xml" in names2 and "rIdSK" in doc2)
check("the template's own table of contents stays when its front matter is kept", "TOC \\" in doc2)
v2 = TC.validate(out2[0]["setup"])
check("... and with the picks: the validation report finds nothing", not v2.problems(), v2.text())
# ---- numbers: a list started where the outline starts; a gap keeps its typed number
M2 = C.Matrix(os.path.join(ED, "Kestrel_Matrix2.xlsx"), "Kestrel")
M2.outline = C.parse_outline("3 Management Approach\n3.1 Staffing\n3.3 Transition")
TS.set_choice(M2, "*", team, TF.default_picks(info), effort_path)
out3 = TS.make(M2, os.path.join(tmp, "exports3"), cfg, effort_name="Kestrel", effort_path=effort_path)
doc3, _n3, z3 = body_of(out3[0]["setup"])
num3 = z3.read("word/numbering.xml").decode()
h3 = {re.sub(r"<[^>]+>", "", x): x for _l, x in re.findall(r'<w:p><w:pPr><w:pStyle w:val="Heading(\d)"/>(.*?)</w:p>', doc3, re.S)}
check("the list starts where the outline starts (3, not 1)", "Management Approach" in h3 and 'w:startOverride w:val="3"' in num3, list(h3))
check("3.1 matches Word's number: typed number gone", "Staffing" in h3)
check("3.3 after 3.1 (a gap): the typed number stays and Word's is turned off for it, and the check says so",
      "3.3 Transition" in h3 and 'w:numId w:val="0"' in h3["3.3 Transition"]
      and any("3.3 Transition" in r["where"] for r in out3[0]["check"]), list(h3))
# ---- a .dotm: the macros are left out
dotm = os.path.join(tmp, "Kestrel Macro Template.dotm")
with zipfile.ZipFile(team) as zi, zipfile.ZipFile(dotm, "w", zipfile.ZIP_DEFLATED) as zo:
    for i in zi.infolist():
        b = zi.read(i)
        if i.filename == "[Content_Types].xml":
            b = b.decode().replace("</Types>", '<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/></Types>')
            b = b.replace("wordprocessingml.template.main+xml", "-not-used-").replace("-not-used-", "wordprocessingml.template.main+xml").encode()
        if i.filename == "word/_rels/document.xml.rels":
            b = b.decode().replace("</Relationships>", '<Relationship Id="rIdVba" Type="http://schemas.microsoft.com/office/2006/relationships/vbaProject" '
                                   'Target="vbaProject.bin"/></Relationships>').encode()
        zo.writestr(i, b)
    zo.writestr("word/vbaProject.bin", b"not a real macro project")
TS.set_choice(M2, "*", dotm, TF.default_picks(None), effort_path)
check("read: a .dotm says it has macros", TF.read(dotm)["macros"] is True)
out4 = TS.make(M2, os.path.join(tmp, "exports4"), cfg, effort_name="Kestrel", effort_path=effort_path)
with zipfile.ZipFile(out4[0]["setup"]) as z4:
    nm4 = z4.namelist(); rel4 = z4.read("word/_rels/document.xml.rels").decode()
check("a .dotm: the macros are left out of the setup", not any("vbaProject" in n for n in nm4) and "vbaProject" not in rel4
      and next(r for r in out4[0]["check"] if r["what"].startswith("A plain Word"))["ok"])
# ---- the check finds what is wrong
bad = os.path.join(tmp, "bad.docx")
with zipfile.ZipFile(out[0]["setup"]) as zi, zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED) as zo:
    for i in zi.infolist():
        b = zi.read(i)
        if i.filename == "word/document.xml":
            b = b.decode().replace('w:pStyle w:val="SKRFPRequirement"', 'w:pStyle w:val="Bogus"', 1)
            b = b.replace("L.4.2.2: The offeror shall describe its approach to cybersecurity.", "").encode()
        zo.writestr(i, b)
req = [("1.1 Ground Segment Architecture", "The offeror shall describe its approach to cybersecurity.")]
bad_rows = TS.problems(TS.check(bad, out[0]["plan"], req))
check("the check finds a style outside the template and a requirement left out, and says where",
      any("Bogus" in r["where"] for r in bad_rows) and any("missing" in r["where"] for r in bad_rows), bad_rows)

print(f"TEMPLATE SETUP 372 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
