"""3.60.0 Strip setup and Compare's tracked changes, standard library only. Strip setup: every paragraph in an SK setup
style taken out of the body, headers and table cells; bookmarks, comment anchors and section breaks inside one kept;
the SK styles and the Stationkeeper file properties gone; the volume read unchanged; the leftovers check finds nothing
of the setup in the copy. Compare: the text of two files as tracked changes (insertions, deletions, words inside a
changed sentence); Word's own Compare run through a hidden Word (here a stand-in runner), never over a file read.
Fictional content."""
import hashlib, json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AH_TEST", "1")
import setupstrip as SS
import leftovers as LO
import filesafety as FS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
STY = (f'<w:styles {WNS}><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
       '<w:style w:type="paragraph" w:styleId="SKRFPRequirement"><w:name w:val="SK RFP Requirement"/><w:rPr><w:vanish/></w:rPr></w:style>'
       '<w:style w:type="paragraph" w:styleId="SKPMDirection"><w:name w:val="SK PM Direction"/><w:rPr><w:vanish/></w:rPr></w:style>'
       '<w:style w:type="paragraph" w:styleId="SKSetupNote"><w:name w:val="SK Setup Note"/></w:style></w:styles>')


def p(t, style="", inner=""):
    ps = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{ps}{inner}<w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'


body = (p("1 Technical Approach", "Heading1")
        + p("The Offeror shall describe its orbit operations.", "SKRFPRequirement", '<w:bookmarkStart w:id="0" w:name="Response"/>')
        + p("Lead: Avery Pine   Due: 2026-12-01", "SKSetupNote")
        + p("Our approach keeps the network on station.")
        + '<w:tbl><w:tr><w:tc>' + p("Lead with the handover.", "SKPMDirection") + '</w:tc><w:tc>' + p("Cell text") + '</w:tc></w:tr></w:tbl>'
        + '<w:p><w:pPr><w:pStyle w:val="SKPMDirection"/><w:sectPr/></w:pPr><w:r><w:t>Note at a section break</w:t></w:r></w:p>'
        + p("2 Management", "Heading1") + p("Staffing is by role.", inner='<w:bookmarkEnd w:id="0"/>'))
custom = ('<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties">'
          '<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="StationkeeperMatrix"/>'
          '<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="3" name="Program Office"/></Properties>')
src = os.path.join(tmp, "Volume I Technical.docx")
with zipfile.ZipFile(src, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}</w:body></w:document>')
    z.writestr("word/styles.xml", STY)
    z.writestr("word/header1.xml", f'<w:hdr {WNS}>' + p("Setup note in the header", "SKSetupNote") + p("Volume I") + "</w:hdr>")
    z.writestr("docProps/custom.xml", custom)
before = hashlib.sha256(open(src, "rb").read()).hexdigest()
r = SS.strip(src)
out = r["out"]
check("a new file beside the volume", os.path.isfile(out) and out != src and "_stripped_" in os.path.basename(out), out)
check("the volume read is unchanged", hashlib.sha256(open(src, "rb").read()).hexdigest() == before)
check("every setup paragraph taken out, the header's too", r["paragraphs"] == 5, r)
check("... counted by style", r["by_style"] == {"SK RFP Requirement": 1, "SK Setup Note": 2, "SK PM Direction": 2}, r["by_style"])
with zipfile.ZipFile(out) as z:
    doc = z.read("word/document.xml").decode(); sty = z.read("word/styles.xml").decode()
    hdr = z.read("word/header1.xml").decode(); cus = z.read("docProps/custom.xml").decode()
check("the author's text stays", "Our approach keeps" in doc and "Staffing is by role" in doc and "Cell text" in doc and "Volume I" in hdr)
check("the setup's text is gone", "orbit operations" not in doc and "Avery Pine" not in doc and "handover" not in doc
      and "Setup note" not in hdr and "Note at a section break" not in doc)
check("the bookmark the TOC reads is kept", 'w:name="Response"' in doc and "bookmarkEnd" in doc)
check("the section break is kept", "<w:sectPr" in doc)
check("a table cell keeps a paragraph", doc.count("<w:tc>") == 2 and all("<w:p" in c for c in doc.split("<w:tc>")[1:]))
check("the setup's styles are gone, the others stay", "SKRFPRequirement" not in sty and "SKSetupNote" not in sty and "Heading1" in sty, r["styles"])
check("the setup's file property is gone, the team's stays", "StationkeeperMatrix" not in cus and "Program Office" in cus
      and 'pid="2"' in cus and r["properties"] == 1)
lo = LO.check(out)
check("the leftovers check finds nothing of the setup in the copy", lo["counts"][LO.SETUP] == 0 and lo["counts"][LO.PROPS] == 0, lo["counts"])
try:
    SS.strip(src, src); ok = False
except FS.WouldOverwrite:
    ok = True
check("never over the volume", ok)

# Compare: tracked changes
import compareany as CA
import docxw
a, b = os.path.join(tmp, "Draft A.docx"), os.path.join(tmp, "Draft B.docx")
for path, lines in ((a, ["1 Approach", "The team keeps the network on station.", "Staffing is by role.", "A sentence that goes."]),
                    (b, ["1 Approach", "The team keeps the whole network on station daily.", "Staffing is by role.", "A new sentence."])):
    d = docxw.Doc()
    d.heading(lines[0], 1)
    for t in lines[1:]:
        d.para(t)
    d.save(path)
res = CA.compare(a, b)
tp = os.path.join(tmp, "tracked.docx")
n = CA.export_tracked(tp, res)
with zipfile.ZipFile(tp) as z:
    x = z.read("word/document.xml").decode()
check("tracked changes: insertions and deletions by Compare", n >= 3 and "<w:ins " in x and "<w:del " in x and 'w:author="Compare"' in x, n)
check("... a changed sentence keeps its unchanged words, the new words inserted", "whole" in x.split("<w:ins")[1] if "<w:ins" in x else False)
check("... removed words as deleted text", "<w:delText" in x and "goes" in x)
check("... the unchanged sentence as plain text", "Staffing is by role." in x)
try:
    CA.export_tracked(b, res); ok = False
except FS.WouldOverwrite:
    ok = True
check("never over a file compared", ok)

import wordcompare as WC
seen = {}


def runner(cmd, env, timeout):
    seen.update(env)
    open(env["SK_OUT"], "wb").write(open(tp, "rb").read())
    return json.dumps({"ok": True, "revisions": 7})


wo = os.path.join(tmp, "word.docx")
rr = WC.compare(a, b, wo, "Compare", runner=runner)
check("Word's Compare: both files and the result passed to Word, the revisions counted", rr["ok"] and rr["revisions"] == 7
      and seen["SK_OLD"].endswith("Draft A.docx") and seen["SK_NEW"].endswith("Draft B.docx") and os.path.isfile(wo))
check("... only two Word files", WC.compare(a, os.path.join(tmp, "x.pdf"), os.path.join(tmp, "w2.docx"), runner=runner)["ok"] is False)
check("... a result that is already there is refused", WC.compare(a, b, wo, runner=runner)["ok"] is False)
try:
    WC.compare(a, b, b, runner=runner); ok = False
except FS.WouldOverwrite:
    ok = True
check("... never over a file compared", ok)
bad = WC.compare(a, b, os.path.join(tmp, "w3.docx"), runner=lambda c, e, t: json.dumps({"ok": False, "why": "-2146822880"}))
check("... Word's failure said in words", bad["ok"] is False and "could not compare" in bad["why"])
n = sum(checks)
print(f"STRIP AND TRACKED {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
