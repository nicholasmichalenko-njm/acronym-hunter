"""3.86.0 references and notes for authors as Word comments: each section's references go on its heading as comments by
Stationkeeper (SK), matched by the heading's words whatever numbers it; no reference, no comment; a person's own comment
stays through Strip setup while Stationkeeper's go; the leftovers check names any left as Reference for authors.
Fictional content (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AH_TEST", "1")
import setupcomments as SCM, setupstrip as SS, leftovers as LO

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
STY = (f'<w:styles {WNS}><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
       '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style></w:styles>')


def p(t, style=""):
    ps = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{ps}<w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'


body = (p("Management Approach", "Heading1") + p("Staffing Plan", "Heading2") + p("Staffing Plan is in this sentence too.")
        + p("2.2 Key Personnel", "Heading2") + p("Our team keeps the network on station."))
src = os.path.join(tmp, "Kestrel Volume II.docx")
with zipfile.ZipFile(src, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
               '<Default Extension="xml" ContentType="application/xml"/></Types>')
    z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
    z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}</w:body></w:document>')
    z.writestr("word/styles.xml", STY)

n = SCM.add(src, {"2.1 Staffing Plan": ["Reference: Kestrel Staffing Plan.docx (pages 4 to 6)", "Use the 30-60-90 day framing."],
                  "2.2 Key Personnel": ["Reference: Kestrel Resumes.docx"], "2 Management Approach": [],
                  "3 Not In This Volume": ["Nothing to attach to"]})
check("one comment per reference, on its heading", n == 3, n)
cs = SCM.comments_of(src)
check("by Stationkeeper, with the reference's words", all(a == "Stationkeeper" for a, _t in cs)
      and ("Stationkeeper", "Reference: Kestrel Staffing Plan.docx (pages 4 to 6)") in cs, cs)
with zipfile.ZipFile(src) as z:
    doc = z.read("word/document.xml").decode()
    ct = z.read("[Content_Types].xml").decode(); rels = z.read("word/_rels/document.xml.rels").decode()
check("the comments part is in the file's parts list and its relationships", "/word/comments.xml" in ct and "comments.xml" in rels)
check("anchored on the headings only, not on a sentence with the same words", doc.count("commentReference") == 3
      and doc.index("commentRangeStart") < doc.index("Staffing Plan</w:t>"))
check("a heading Word numbers matches by its words; one with a number matches too", "Key Personnel" in doc)
check("no reference, no comment", SCM.count(src) == 3)
# a person's own comment, then Strip setup
with zipfile.ZipFile(src) as z:
    parts = {nm: z.read(nm) for nm in z.namelist()}
parts["word/comments.xml"] = parts["word/comments.xml"].replace(
    b"</w:comments>", b'<w:comment w:id="40" w:author="A. Lee" w:initials="AL"><w:p><w:r><w:t>Check this number.</w:t></w:r></w:p></w:comment></w:comments>')
parts["word/document.xml"] = parts["word/document.xml"].replace(
    b"Our team keeps", b'</w:t></w:r><w:commentRangeStart w:id="40"/><w:r><w:t>Our team keeps').replace(
    b"on station.</w:t></w:r>", b'on station.</w:t></w:r><w:commentRangeEnd w:id="40"/><w:r><w:commentReference w:id="40"/></w:r>')
with zipfile.ZipFile(src, "w") as z:
    for nm, b in parts.items():
        z.writestr(nm, b)
lo = LO.check(src)
check("the leftovers check names the references for authors apart from a person's comment",
      lo["counts"].get(LO.REFS) == 3 and lo["counts"].get(LO.COMMENT) == 1, lo["counts"])
r = SS.strip(src)
check("Strip setup takes Stationkeeper's comments out", r["comments"] == 3 and SCM.count(r["out"]) == 0, r)
left = SCM.comments_of(r["out"])
with zipfile.ZipFile(r["out"]) as z:
    doc2 = z.read("word/document.xml").decode()
check("a person's own comment stays, anchored", left == [("A. Lee", "Check this number.")] and 'w:id="40"' in doc2
      and doc2.count("commentReference") == 1, left)
check("the headings stay", "Staffing Plan" in doc2 and "Key Personnel" in doc2)
lo2 = LO.check(r["out"])
check("the check finds no reference for authors after Strip", lo2["counts"].get(LO.REFS) == 0)
check("a file with none: nothing to do", SCM.add(r["out"], {}) == 0)

print(f"COMMENTS 386 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
