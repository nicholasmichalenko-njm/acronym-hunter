"""3.66.0 Template Studio I, without a screen: field recipes are data (starters, add, change, remove, put back, an
effort's own code), a Word file's fields read from its XML (complex and simple, body and header) and checked against the
recipes (match, differs with the closest recipe, no recipe; STYLEREF "Heading 1" reads as STYLEREF 1), missing
bookmarks; parts and numbering (the usual parts, change, move, page labels i/1/A-1, one line per part, what Final Check
reads); Final Check counts an 11x17 sheet as the plan says, leaves out appendices and the parts that do not count, and
checks the fields against the recipes. Fictional content."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import fieldrecipes as FR, partplan as PP, finalcheck as FC

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config")
# ---- recipes as data
rs = FR.load(cfg)
check("the starters until the list is first saved (appendices on Heading 7)", len(rs) == 8
      and any(r["codes"] == ["STYLEREF 7 \\s", "SEQ Table \\* ARABIC \\s 7"] for r in rs) and not os.path.exists(os.path.join(cfg, FR.FILE)))
rid = FR.add(cfg, {"name": "Volume title in the footer", "where": "Header or footer", "codes": ["DOCPROPERTY VolumeTitle"]})
check("add a recipe: the list is saved with it", any(r["id"] == rid for r in FR.load(cfg)) and len(FR.load(cfg)) == 9)
FR.update(cfg, "s3", codes=["STYLEREF 1 \\s", "SEQ Table \\* ARABIC \\s 1 \\* MERGEFORMAT"])
check("change a starter's code", next(r for r in FR.load(cfg) if r["id"] == "s3")["codes"][1].endswith("MERGEFORMAT"))
FR.remove(cfg, "s8"); FR.remove(cfg, rid)
check("remove one", not any(r["id"] in ("s8", rid) for r in FR.load(cfg)))
FR.restore_starters(cfg)
check("Put back the starters: removed ones come back, changed ones stay", any(r["id"] == "s8" for r in FR.load(cfg))
      and next(r for r in FR.load(cfg) if r["id"] == "s3")["codes"][1].endswith("MERGEFORMAT"))
FR.update(cfg, "s3", codes=["STYLEREF 1 \\s", "SEQ Table \\* ARABIC \\s 1"])


class WS:
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


ws = WS()
FR.set_effort_codes(ws, "s1", ['TOC \\o "1-2" \\h \\z \\b Response'])
eff = {r["id"]: r for r in FR.effective(cfg, ws)}
check("an effort's own code wins for that effort only", eff["s1"]["codes"] == ['TOC \\o "1-2" \\h \\z \\b Response'] and eff["s1"]["effort_own"]
      and FR.load(cfg)[0]["codes"] == ['TOC \\o "1-3" \\h \\z \\b Response'])
FR.set_effort_codes(ws, "s1", [])
check("... and clearing it gives it back to the team's", not FR.effective(cfg, ws)[0].get("effort_own"))
# ---- a Word file's fields
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def cfield(code):
    return (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve">{code}</w:instrText></w:r>'
            f'<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>')


TOC_R = cfield('TOC \\o &quot;1-3&quot; \\h \\z \\b Response')        # built outside the f-strings: older Python refuses a backslash there
CAP = cfield("STYLEREF 1 \\s") + "<w:r><w:t>-</w:t></w:r>" + cfield("SEQ Table \\* ARABIC")
TOC_A = cfield('TOC \\o &quot;7-8&quot; \\h \\z \\b Appendices')
body = ('<w:document ' + W + '><w:body>'
        '<w:p><w:bookmarkStart w:id="0" w:name="Response"/>' + TOC_R + '</w:p>'
        '<w:p><w:r><w:t>Table </w:t></w:r>' + CAP + '</w:p>'
        '<w:p>' + TOC_A + '</w:p>'
        '<w:p><w:fldSimple w:instr=" REF _Ref123 \\h "><w:r><w:t>x</w:t></w:r></w:fldSimple><w:bookmarkEnd w:id="0"/></w:p>'
        '</w:body></w:document>')
header = '<w:hdr ' + W + '><w:p>' + cfield("STYLEREF &quot;Heading 1&quot;") + '</w:p></w:hdr>'
doc = os.path.join(tmp, "Kestrel_Volume_I.docx")
with zipfile.ZipFile(doc, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    z.writestr("word/document.xml", body)
    z.writestr("word/header1.xml", header)
fs = FR.read_fields(doc)
check("read a file's fields: complex and simple, body and header", [p for p, _c in fs] == ["Body"] * 5 + ["Header 1"]
      and any(c.startswith("REF _Ref123") for _p, c in fs), fs)
rows = FR.check(fs, FR.effective(cfg, ws))
st = {r["code"]: r for r in rows}
check("a field that is a recipe matches", st['TOC \\o "1-3" \\h \\z \\b Response']["status"] == "matches")
check("a field that differs names the recipe and what it says", st["SEQ Table \\* ARABIC"]["status"] == "differs"
      and st["SEQ Table \\* ARABIC"]["recipe"] == "Table caption" and st["SEQ Table \\* ARABIC"]["expected"] == "SEQ Table \\* ARABIC \\s 1")
check('STYLEREF "Heading 1" in the header matches the header recipe (STYLEREF 1)', st['STYLEREF "Heading 1"']["status"] == "matches"
      and st['STYLEREF "Heading 1"']["recipe"] == "Section title in the header")
check("a field with no recipe says so", next(r for r in rows if r["code"].startswith("REF"))["status"] == "no recipe")
check("missing bookmarks: a TOC reads Appendices and the file has no such bookmark", FR.missing_bookmarks(doc, FR.load(cfg)) == ["Appendices"])
# ---- parts and numbering
class Rec:
    def __init__(self):
        self.data = {}

    def log(self, *a, **k):
        pass

    def save(self):
        pass


rec = Rec()
ps = PP.plan_of(rec, "Volume I Technical")
check("the usual parts: cover, front matter in i, the response in 1, appendices A-1 on Heading 7",
      [(p["name"], p["format"]) for p in ps] == [("Cover", "none"), ("Front matter", "i"), ("Response", "1"), ("Appendices", "A-1")]
      and ps[3]["chapter"] == "Heading 7" and "part_plans" not in rec.data)
check("page labels read as they print", PP.page_label(ps[1], 3) == "iii" and PP.page_label(ps[2], 7) == "7" and PP.page_label(ps[3], 2) == "A-2")
check("no plan set: Final Check reads none", PP.final_check_rules(rec, "Volume I Technical") is None)
pid = PP.add_part(rec, "Volume I Technical", "Foldout drawings", "Body", after=ps[2]["id"])
PP.update_part(rec, "Volume I Technical", pid, paper="11x17", orient="Landscape", foldout=2, format="1", restart=False)
ps2 = PP.plan_of(rec, "Volume I Technical")
check("add a part after another and set it (11x17 landscape, counts as 2)", [p["name"] for p in ps2][3] == "Foldout drawings"
      and ps2[3]["paper"] == "11x17" and ps2[3]["foldout"] == 2)
PP.move_part(rec, "Volume I Technical", pid, 1)
check("move a part", [p["name"] for p in PP.plan_of(rec, "Volume I Technical")][4] == "Foldout drawings")
check("one line per part says it all", "A-1, A-2 (chapter-page) restarting at A-1; chapter from Heading 7" in PP.says(ps2[4])
      and "landscape 11x17" in PP.says(ps2[3]) and "counts toward the limit" in PP.says(ps2[3]))
fr = PP.final_check_rules(rec, "Volume I Technical")
check("what Final Check reads: the parts that do not count, blank pages out, an 11x17 sheet as 2", set(fr["exclude"]) == {"cover", "toc", "acronyms", "appendices", "dividers"}
      and fr["foldout"] == 2 and fr["blanks"] is False, fr)
# ---- Final Check counting
words = "The offeror describes the approach to the ground system with enough words to count as a page of text here today."
texts = ["Kestrel Volume I Technical cover", "Table of Contents\n1 Intro ..... 1\n2 Approach ..... 2\n3 Management ..... 3",
         "1 Introduction\n" + words, "2 Approach\n" + words, "Foldout drawing\n" + words, "Appendix A Resumes\n" + words, words]
sizes = [(612, 792)] * 4 + [(1224, 792)] + [(612, 792)] * 2
n, out = FC.count_pages(texts, fr["exclude"], sizes, fr["foldout"])
check("Final Check by the plan: the cover, TOC and appendices left out; the 11x17 sheet counts as 2", n == 4 and out.get("appendices") == [6, 7]
      and out.get("cover") == [1] and out.get("toc") == [2], (n, out))
n1, _o = FC.count_pages(texts, [], sizes, 1)
check("with no plan every sheet counts once, as before", n1 == 7)
ctx = {"part_plans": rec.data["part_plans"]}
check("the plan is found by the volume's name in its file name", (FC.plan_rules(ctx, "Kestrel_Volume_I") or {}).get("volume") == "Volume I Technical")
rep = FC.run({"name": "Kestrel_Volume_I", "docx": doc, "pdf": ""}, {"recipes": FR.load(cfg)})
line = next((l for l in rep["lines"] if l["check"] == "Fields match the field recipes"), None) if isinstance(rep, dict) else None
check("Final Check: fields against the recipes, with what differs and the missing bookmark", line is not None and line["status"] == FC.FAIL
      and "SEQ Table" in line["detail"] and "Appendices is missing" in line["detail"], line)

print(f"STUDIO 366 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
