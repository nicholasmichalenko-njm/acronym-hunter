"""3.57.0 file safety and the leftovers check, standard library only. Leftovers: the setup's SK reference styles and
file properties, hidden text, white text (not on a dark table header), comments, tracked changes, placeholders; a clean
file is clean. File safety: a OneDrive or SharePoint folder, Word's owner file, other people's tracked changes, .doc and
.docm, a new dated path that never exists, and the guard that refuses to write over a file read (Technical Edit, Shred,
Compare). Fictional content."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import leftovers as LO
import filesafety as FS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
STYLES = (f'<w:styles {WNS}>'
          '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
          '<w:style w:type="paragraph" w:styleId="SKRFPRequirement"><w:name w:val="SK RFP Requirement"/>'
          '<w:rPr><w:vanish/><w:color w:val="7030A0"/></w:rPr></w:style>'
          '<w:style w:type="paragraph" w:styleId="SKPMDirection"><w:name w:val="SK PM Direction"/><w:rPr><w:vanish/></w:rPr></w:style>'
          '</w:styles>')


def docx(path, body, custom="", comments=0, styles=STYLES):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}</w:body></w:document>')
        z.writestr("word/styles.xml", styles)
        if custom:
            z.writestr("docProps/custom.xml", custom)
        if comments:
            z.writestr("word/comments.xml", f'<w:comments {WNS}>' + "".join(f'<w:comment w:id="{i}"><w:p/></w:comment>' for i in range(comments)) + "</w:comments>")
    return path


def p(text, style="", rpr=""):
    ps = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{ps}<w:r>{"<w:rPr>" + rpr + "</w:rPr>" if rpr else ""}<w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


body = (p("1 Technical Approach", "Heading1")
        + p("The Offeror shall describe its orbit operations.", "SKRFPRequirement")
        + p("Lead with the ground station handover.", "SKPMDirection")
        + p("Our approach keeps the Kestrel network on station.")
        + p("A note to self", rpr="<w:vanish/>")
        + p("invisible keywords", rpr='<w:color w:val="FFFFFF"/>')
        + '<w:tbl><w:tr><w:tc><w:tcPr><w:shd w:val="clear" w:fill="1E3A8A"/></w:tcPr>' + p("Header cell", rpr='<w:color w:val="FFFFFF"/>') + "</w:tc></w:tr></w:tbl>"
        + p("Staffing is TBD until the [insert name] review.")
        + '<w:p><w:ins w:id="1" w:author="Avery Pine"><w:r><w:t>added words</w:t></w:r></w:ins>'
          '<w:del w:id="2" w:author="Rowan Hale"><w:r><w:delText>old words</w:delText></w:r></w:del></w:p>'
        + '<w:p><w:r><w:t>Commented line</w:t></w:r><w:r><w:commentReference w:id="0"/></w:r></w:p>')
custom = ('<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties">'
          '<property name="StationkeeperMatrix"/><property name="StationkeeperSetupChangesSince"/></Properties>')
dirty = docx(os.path.join(tmp, "Volume I.docx"), body, custom, comments=2)
r = LO.check(dirty)
c = r["counts"]
check("the setup's reference text, by its SK styles", c[LO.SETUP] == 2, c)
check("... with the heading it sits under", all(i["where"] == "1 Technical Approach" for i in r["items"] if i["kind"] == LO.SETUP))
check("the setup's file properties", c[LO.PROPS] == 2, c)
check("hidden text", c[LO.HIDDEN] == 1 and any("note to self" in i["text"] for i in r["items"] if i["kind"] == LO.HIDDEN), c)
check("white text on a light page, not on a dark table header", c[LO.WHITE] == 1
      and any("invisible" in i["text"] for i in r["items"] if i["kind"] == LO.WHITE), c)
check("placeholders", c[LO.PLACE] == 2, c)
check("tracked changes with who made them", c[LO.TRACKED] == 2 and r["authors"] == {"Avery Pine": 1, "Rowan Hale": 1}, r["authors"])
check("comments, anchored and not", c[LO.COMMENT] == 2, c)
check("a summary line", "2 setup reference text" in LO.summary(r) and "comment" in LO.summary(r), LO.summary(r))
clean = docx(os.path.join(tmp, "Clean.docx"), p("1 Technical Approach", "Heading1") + p("Our approach keeps the network on station."))
check("a clean file is clean", not any(LO.check(clean)["counts"].values()) and LO.summary(LO.check(clean)) == "Nothing left behind.")
xl = LO.export(os.path.join(tmp, "left.xlsx"), [("Volume I", r)], "Kestrel")
import openpyxl
wb = openpyxl.load_workbook(xl)
check("the report in Excel: a summary and every item with why it matters", wb["Items"].max_row == len(r["items"]) + 1
      and wb["Items"]["E2"].value)
wb.close()

# ---------------------------------------------------------------- file safety
od = os.path.join(tmp, "OneDrive - Kestrel Works", "Proposals"); os.makedirs(od)
os.environ["OneDriveCommercial"] = os.path.join(tmp, "OneDrive - Kestrel Works")
f = docx(os.path.join(od, "Volume II Management.docx"), p("Text"))
check("a file in a OneDrive folder", FS.sync_folder(f) == "OneDrive")
sp = os.path.join(tmp, "Kestrel Works", "Proposals - SharePoint"); os.makedirs(sp)
check("a file in a SharePoint library folder", FS.sync_folder(os.path.join(sp, "x.docx")) == "SharePoint")
check("a file elsewhere", FS.sync_folder(clean) == "")
with open(os.path.join(od, "~$lume II Management.docx"), "wb") as fh:
    fh.write(bytes([10]) + b"Avery Pine" + b"\0" * 40)
check("Word has it open (its owner file), with who", FS.word_owner(f) == (True, "Avery Pine"))
check("not open", FS.word_owner(clean) == (False, ""))
check("other people's tracked changes", FS.others_changes(dirty, "Avery Pine") == {"Rowan Hale": 1})
w = FS.warnings(f)
check("warnings in plain words", any("OneDrive" in x and "never saves over it" in x for x in w) and any("Word has this file open" in x for x in w), w)
check("... tracked changes by others", any("tracked change" in x and "Rowan Hale" in x for x in FS.warnings(dirty, "Avery Pine")))
check("... an old .doc and a macro file", any(".doc file" in x for x in FS.warnings(os.path.join(tmp, "a.doc")))
      and any("macros" in x for x in FS.warnings(os.path.join(tmp, "a.docm"))))
import datetime
when = datetime.datetime(2026, 11, 5, 14, 30)
n1 = FS.new_path(clean, "SKedit", when)
open(n1, "wb").close()
n2 = FS.new_path(clean, "SKedit", when)
check("a new dated path beside the original, never an existing file", os.path.basename(n1) == "Clean_SKedit_2026-11-05_1430.docx"
      and n2 != n1 and not os.path.exists(n2), (n1, n2))
try:
    FS.guard(clean, dirty, clean); ok = False
except FS.WouldOverwrite:
    ok = True
check("the guard refuses to write over a file read", ok and FS.guard(n2, clean) == n2)
import techeditdocx as TD
try:
    TD.write(clean, [], clean); ok = False
except FS.WouldOverwrite:
    ok = True
check("Technical Edit's edited copy never goes over the draft", ok)
import shredquick as SQ
try:
    SQ.export({"file": clean, "rows": []}, clean); ok = False
except FS.WouldOverwrite:
    ok = True
check("Shred's matrix never goes over the file read", ok)
n = sum(checks)
print(f"LEFTOVERS AND FILE SAFETY {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
