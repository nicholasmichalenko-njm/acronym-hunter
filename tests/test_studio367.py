"""3.67.0 Template Studio II, without a screen: read-back (each section's numbering from its page number settings or its
PAGE field, restarts, chapter style, orientation and paper; sections matched to the parts in order, a landscape section
staying in its part; each part against its plan; Heading 7 on Heading 1's list; fields against the recipes), Word drawing
one page per part (a stand-in Word), the web-safe check (fields and STYLEREF targets in text boxes, content controls),
and the Apply in Word lab (banned phrases found with plain replacements ticked and advice kept as advice; a copy with
tracked changes and comments; the live plan last to first with the words before each place; Word's answers applied and
logged; nothing when Word is not open). Fictional content (Kestrel)."""
import json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import fieldrecipes as FR, partplan as PP, readback as RB, templatecheck as TC, wordlab as WL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
NSD = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def fld(code):
    return (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve">{code}</w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>')


def sect(foot=None, fmt=None, start=None, chap=None, land=False, paper=(12240, 15840)):
    w, h = (paper[1], paper[0]) if land else paper
    pn = ""
    if fmt or start or chap:
        pn = "<w:pgNumType" + (f' w:fmt="{fmt}"' if fmt else "") + (f' w:start="{start}"' if start else "") \
             + (f' w:chapStyle="{chap}" w:chapSep="hyphen"' if chap else "") + "/>"
    fr = f'<w:footerReference w:type="default" r:id="{foot}"/>' if foot else ""
    return f'<w:sectPr>{fr}<w:pgSz w:w="{w}" w:h="{h}"' + (' w:orient="landscape"' if land else "") + f'/>{pn}</w:sectPr>'


def para(text, sp="", style=""):
    ps = f'<w:pStyle w:val="{style}"/>' if style else ""
    return f'<w:p><w:pPr>{ps}{sp}</w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'


body = (para("Kestrel Volume I Technical", sect())                                                 # cover: no page number
        + para("Table of Contents", sect("rIdF1", fmt="lowerRoman", start=1))                       # front matter i
        + para("1 Introduction", sect("rIdF2", fmt="decimal", start=1), "Heading1")                 # response 1
        + para("Foldout drawing", sect("rIdF2", land=True, paper=(15840, 24480)))                  # landscape 11x17, carries on
        + para("Appendix A Resumes", "", "Heading7")
        + '<w:p><w:r><w:t>body</w:t></w:r></w:p>' + sect("rIdF2", start=1, chap="7"))             # appendices A-1
doc_xml = f'<w:document {NSD}><w:body>{body}</w:body></w:document>'
styles = (f'<w:styles {NSD}>'
          '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:numPr><w:numId w:val="5"/></w:numPr></w:pPr></w:style>'
          '<w:style w:type="paragraph" w:styleId="Heading7"><w:name w:val="heading 7"/><w:pPr><w:numPr><w:numId w:val="5"/></w:numPr></w:pPr></w:style>'
          '</w:styles>')
rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdF1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
        '<Relationship Id="rIdF2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/>'
        '</Relationships>')
vol = os.path.join(tmp, "Kestrel_Volume_I.docx")
with zipfile.ZipFile(vol, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    z.writestr("word/document.xml", doc_xml)
    z.writestr("word/styles.xml", styles)
    z.writestr("word/_rels/document.xml.rels", rels)
    z.writestr("word/footer1.xml", f'<w:ftr {NSD}><w:p>{fld("PAGE")}</w:p></w:ftr>')
    z.writestr("word/footer2.xml", f'<w:ftr {NSD}><w:p>{fld("PAGE")}</w:p></w:ftr>')
# ---- read-back
secs = RB.sections(vol)
check("each section read: none, i, 1, then a landscape 11x17 section carrying on, then A-1 from Heading 7",
      [(RB._kind_fmt(s), s["restart"], s["orient"], s["paper"]) for s in secs]
      == [("none", False, "Portrait", "Letter"), ("i", True, "Portrait", "Letter"), ("1", True, "Portrait", "Letter"),
          ("1", False, "Landscape", "11x17"), ("A-1", True, "Portrait", "Letter")] and secs[4]["chapter"] == "Heading 7",
      [(RB._kind_fmt(s), s["restart"], s["orient"], s["paper"], s["chapter"]) for s in secs])
parts = PP.default_parts()
check("sections matched to the parts in order; the foldout stays in the response", [i for _p, i in RB.assign(secs, parts)] == [[0], [1], [2, 3], [4]])
res = RB.check(vol, parts, FR.load(os.path.join(tmp, "cfg")))
check("read-back against the usual plan: every part matches", all(r["status"] == "matches" for r in res["rows"] if r["part"] != "Whole file")
      and "4 of 4 part(s)" in res["summary"], [r for r in res["rows"] if r["status"] != "matches"])
check("... the foldout is named as another section in the response", any(r["what"] == "Other sections in it" and "landscape 11x17" in r["file"] for r in res["rows"]))
check("Heading 7 numbers on Heading 1's list", next(r for r in res["rows"] if r["what"].startswith("Heading 7"))["file"] == "Yes")
ps2 = [dict(p) for p in parts]; ps2[1]["format"] = "I"; ps2[3]["chapter"] = "Heading 8"
rows = {(r["part"], r["what"]): r for r in RB.check(vol, ps2)["rows"]}
check("a plan that differs is said: front matter in I, appendices on Heading 8", rows[("Front matter", "Page numbers")]["status"] == "differs"
      and rows[("Front matter", "Page numbers")]["file"] == "i" and rows[("Appendices", "Chapter style")]["file"] == "Heading 7")
ps3 = parts + [PP.part("Customer form", "Customer form", fmt="1", restart=True)]
check("a part with no section is missing", RB.check(vol, ps3)["rows"][-2]["status"] == "missing")
# a PAGE field's own switch prints over the section's format
draft = os.path.join(tmp, "draft_front.docx")
with zipfile.ZipFile(vol) as zi, zipfile.ZipFile(draft, "w") as zo:
    for n in zi.namelist():
        data = zi.read(n)
        if n == "word/footer1.xml":
            data = f'<w:ftr {NSD}><w:p>{fld("PAGE \\* ROMAN")}</w:p></w:ftr>'.encode()
        zo.writestr(n, data)
check("a PAGE field's switch is what prints (ROMAN reads as I)", RB._kind_fmt(RB.sections(draft)[1]) == "I")
# ---- Word draws one page per part (a stand-in Word that writes a 5-page PDF)


def fake_word(cmd, env, timeout):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument.new()
    for _ in range(5):
        pdf.new_page(612, 792)
    pdf.save(env["SK_PDF"])
    check("Word lays out a temporary copy, never the file", env["SK_DOC"] != vol and os.path.dirname(env["SK_DOC"]) != tmp)
    return json.dumps({"ok": True, "pages": 5, "starts": [1, 2, 3, 4, 5]})


out = os.path.join(tmp, "pages")
dr = RB.draw_parts(vol, out, parts, runner=fake_word)
check("one picture per part, from the page its first section starts on", dr["ok"] and sorted(dr["pngs"]) == sorted(p["id"] for p in parts)
      and all(os.path.isfile(x) for x in dr["pngs"].values()), dr)
check("Word that does not answer says so", RB.draw_parts(vol, out, parts, runner=lambda c, e, t: "")["ok"] is False)
# ---- web-safe check
tb = (f'<w:document {NSD} xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"><w:body>'
      f'<w:p>{fld("STYLEREF 1 \\s")}</w:p>'
      '<w:p><w:r><w:txbxContent><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Title in a box</w:t></w:r></w:p>'
      f'<w:p>{fld("PAGE")}</w:p></w:txbxContent></w:r></w:p>'
      '<w:sdt><w:sdtContent><w:p><w:r><w:t>Kestrel</w:t></w:r></w:p></w:sdtContent></w:sdt></w:body></w:document>')
web = os.path.join(tmp, "web.dotx")
with zipfile.ZipFile(web, "w") as z:
    z.writestr("word/document.xml", tb)
    z.writestr("word/styles.xml", styles)
rep = TC.validate(web)
w = [i for i in rep.items if i["area"] == "web"]
check("web-safe: a field in a text box", any(i["severity"] == "warning" and "PAGE" in i["what"] for i in w), w)
check("web-safe: a STYLEREF target in a text box is a problem", any(i["severity"] == "problem" and "Heading1" in i["what"] for i in w), w)
check("web-safe: content controls are noted", any(i["severity"] == "note" and "1 content control" in i["what"] for i in w), w)
check("a template with none of these has no web line", not [i for i in TC.validate(vol).items if i["area"] == "web"])
# ---- Apply in Word lab
import docxw
d = docxw.Doc(); d.heading("Kestrel Ground Segment", 1)
d.para("Hopefully the Kestrel team will utilize a world-class approach. We will try to finish early.")
d.para("Our seamless interface will utilize the bus.")
src = os.path.join(tmp, "Kestrel draft.docx"); d.save(src)
before = open(src, "rb").read()
items = [{"Phrase": p, "Level": l, "Use instead": u, "Why": y} for p, l, u, y in
         (("world-class", "Banned", "say what makes it better, with a number", "Unsupported claim"), ("will try", "Banned", "will", "Weak commitment"),
          ("utiliz*", "Avoid", "use", "Plain language"), ("seamless", "Avoid", "describe the interface", "Vague"))]
ch = WL.find(WL.docx_paragraphs(src), items)
check("found in reading order; plain replacements ticked, advice kept as advice",
      [(c["hit"], c["fix"], c["on"]) for c in ch] == [("utilize", "use", True), ("world-class", "", False), ("will try", "will", True),
                                                       ("seamless", "", False), ("utilize", "use", True)]
      and ch[1]["advice"].startswith("say what"), [(c["hit"], c["fix"], c["on"]) for c in ch])
check("advice is never a replacement", not WL.plain_fix("describe the interface") and not WL.plain_fix("a firm commitment")
      and WL.plain_fix("use") and WL.plain_fix("and, or, or both") is False)
check("the replacement keeps the found words' case", WL._case_like("Utilize", "use") == "Use" and WL._case_like("UTILIZE", "use") == "USE")
ch[4]["on"] = False                                        # the person keeps one
cp = WL.to_copy(src, ch, os.path.join(tmp, "copy.docx"))
xml = zipfile.ZipFile(cp["path"]).read("word/document.xml").decode()
cm = zipfile.ZipFile(cp["path"]).read("word/comments.xml").decode()
check("the copy: ticked phrases as tracked changes, advice as comments, the kept one left alone", cp["changes"] == 2 and cp["comments"] == 2
      and xml.count("<w:ins ") == 2 and "Banned phrase: world-class" in cm and "Use instead: describe the interface" in cm, cp)
check("the draft is only read", open(src, "rb").read() == before)
check("the copy's name says what it is", WL.copy_path(src).endswith(".docx") and "banned phrases" in WL.copy_path(src))
# live: the plan Word gets
text = "\r".join(WL.docx_paragraphs(src)) + "\r"
ch = WL.find(text.split("\r"), items)
plan = WL.live_plan(text, ch)
check("live plan: only ticked changes, last to first, each with the words before it",
      [p["old"] for p in plan] == ["utilize", "will try", "utilize"] and plan[0]["k"] == 1 and plan[2]["k"] == 0
      and plan[1]["ctx"].endswith("approach. We will try"), plan)


def fake_live(results):
    seen = {}

    def run(cmd, env, timeout):
        s = cmd[-1]
        if "Documents) { $docs" in s:
            return json.dumps({"ok": True, "docs": {"name": "Kestrel draft.docx", "full": "C:\\\\Kestrel draft.docx", "saved": True, "track": False, "ro": False}})
        if "Content.Text" in s:
            return json.dumps({"ok": True, "text": text, "track": False})
        seen["plan"] = json.load(open(env["SK_PLAN"], encoding="utf-8"))
        seen["script"] = s
        return json.dumps({"ok": True, "results": results(seen["plan"]), "track_was": False})
    return run, seen


run, seen = fake_live(lambda plan: [{"id": p["id"], "done": p["old"] != "will try", **({} if p["old"] != "will try" else {"why": "moved"})} for p in plan])
docs = WL.open_documents(runner=run)
check("the documents open in Word (one comes back as a list)", docs["ok"] and docs["docs"][0]["name"] == "Kestrel draft.docx")
got = WL.read_open("C:\\Kestrel draft.docx", runner=run)
check("the open document's text, as paragraphs", got["ok"] and got["paragraphs"][1].startswith("Hopefully"))
res = WL.apply_open("C:\\Kestrel draft.docx", text, ch, runner=run)
check("Word applies the plan: applied and skipped counted", res["ok"] and res["applied"] == 2 and res["skipped"] == 1, res)
check("the live script switches tracked changes on and back, adds a comment, and never saves or closes",
      "$d.TrackRevisions = $true" in seen["script"] and "$d.TrackRevisions = $was" in seen["script"] and "Comments.Add" in seen["script"]
      and not any(w in seen["script"] for w in (".Save(", ".SaveAs", ".Close(", ".Quit(", "New-Object")))


class Rec:
    def __init__(self):
        self.data, self.logs = {}, []

    def log(self, *a, **k):
        self.logs.append(a)

    def save(self):
        pass


rec = Rec()
WL.log(rec, "C:\\Kestrel draft.docx", ch, res)
check("every live change logged, done or why not", len(rec.data["word_live"]) == 3 and sum(1 for e in rec.data["word_live"] if e["done"]) == 2
      and any(e["why"] == "moved" for e in rec.data["word_live"]) and "2 change(s)" in rec.logs[0][1])
check("Word not open: said plainly", WL.read_open("x", runner=lambda c, e, t: json.dumps({"ok": False, "why": "not running"}))["why"].startswith("Word is not open"))
check("nothing ticked: nothing sent to Word", WL.apply_open("x", text, [dict(c, on=False) for c in ch], runner=run)["ok"] is False)

print(f"STUDIO 367 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
