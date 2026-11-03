"""3.23.0 the validation report: a clean template reports no problem; a style used but not defined, a STYLEREF to a
missing style, a DOCPROPERTY to a missing property, MERGEFORMAT, a list number with no definition, direct formatting in
a Quick Part and a font not installed are each reported; hidden text styles are noted; Make a template carries the
report."""
import io, os, re, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodrules as PRL, prodtemplate as PT, templatecheck as TC

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


std = PRL.for_effort(tempfile.mkdtemp())
std["style_defs"]["SK RFP Reference"] = {"type": "paragraph", "based_on": "Normal", "color": "7030A0", "hidden": True}
std["fill_ins"] = [{"name": "Proposal number", "kind": "docprop", "property": "Proposal Number", "value": "P-1"}]
std["hf_layouts"]["body"]["header"] = {"left": "{volume_name}", "right": "{proposal_number}"}
std["variables"]["volume_name"] = "Volume I"
tj = PT.make(std, os.path.join(tempfile.mkdtemp(), "out"))
rep = TC.validate(tj.copy, installed_fonts=["Times New Roman", "Arial", "Calibri", "Cambria"])
check("a template Stationkeeper made reports no problem", not rep.problems(), rep.text())
check("hidden text styles are noted", any(i["area"] == "hidden" and "SK RFP Reference" in i["what"] for i in rep.items))
check("Make a template carries the report", getattr(tj, "validation", None) is not None and not tj.validation.problems())

# plant problems
raw = open(tj.copy, "rb").read()
zin = zipfile.ZipFile(io.BytesIO(raw)); out = io.BytesIO(); zo = zipfile.ZipFile(out, "w")
for i in zin.infolist():
    b = zin.read(i.filename)
    if i.filename == "word/document.xml":
        b = b.replace(b"</w:body>", b'<w:p><w:pPr><w:pStyle w:val="GhostStyle"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="77"/></w:numPr></w:pPr>'
                      b'<w:fldSimple w:instr=" STYLEREF &quot;Missing Title&quot; \\* MERGEFORMAT "><w:r><w:t>x</w:t></w:r></w:fldSimple>'
                      b'<w:fldSimple w:instr=" DOCPROPERTY &quot;Nope&quot; "><w:r><w:t>y</w:t></w:r></w:fldSimple></w:p></w:body>', 1)
        b = b.replace(b"<w:sectPr", b"<w:p><w:r><w:rPr><w:rFonts w:ascii=\"Futura PT\"/></w:rPr><w:t>z</w:t></w:r></w:p><w:sectPr", 0)
    zo.writestr(i, b)
zo.close()
bad = TC.validate(data=out.getvalue(), installed_fonts=["Times New Roman"])
whats = " | ".join(i["what"] for i in bad.items)
check("a style used but not defined", any("GhostStyle" in i["what"] for i in bad.problems()), whats)
check("a STYLEREF to a style that is not defined", any('STYLEREF "Missing Title"' in i["what"] for i in bad.problems()), whats)
check("a DOCPROPERTY the file does not hold", any('DOCPROPERTY "Nope"' in i["what"] for i in bad.problems()), whats)
check("a field that keeps old formatting", any("MERGEFORMAT" in i["what"] for i in bad.warnings()), whats)
check("a list number with no definition", any("list number 77" in i["what"] for i in bad.problems()), whats)
check("a font this PC does not have", any("is not installed" in i["what"] for i in bad.warnings()), whats)
sys.path.insert(0, HERE)
from _qpfixture import with_glossary
src = os.path.join(tempfile.mkdtemp(), "qp.dotx")
with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), src)
zin = zipfile.ZipFile(src); out2 = io.BytesIO(); zo = zipfile.ZipFile(out2, "w")
for i in zin.infolist():
    b = zin.read(i.filename)
    if i.filename == "word/glossary/document.xml":
        b = b.replace(b"<w:r><w:t>VOLUME TITLE", b'<w:r><w:rPr><w:sz w:val="72"/><w:color w:val="FF0000"/></w:rPr><w:t>VOLUME TITLE', 1)
    zo.writestr(i, b)
zo.close()
qrep = TC.validate(data=out2.getvalue())
check("direct formatting inside a Quick Part", any("Volume cover" in i["what"] and "direct formatting" in i["what"] for i in qrep.warnings()), qrep.text())
check("the report reads in words", "Problems" in bad.text() and "Warnings" in bad.text())
print(f"TEMPLATE CHECK {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
