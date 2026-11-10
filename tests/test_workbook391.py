"""3.91.0: Setup from a workbook, on the page (workbooksetup). A fictional Kestrel outline like the team's: section numbers
and headings, the source as typed, Section L content whose cells mix compliance language (red) and supporting text
(black italic) with plain RFP text, and management guidance. The tags and their order, guidance right after the heading,
a short source at the start of the text and a long one on its own line, character styles in place, text left out, text
made its own paragraph, one section's own order, and the Word file on a template and without one."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import outlinexl as OX
import outlinelayouts as OL
import workbooksetup as WB

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def make_book(path):
    from openpyxl import Workbook
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    wb = Workbook(); ws = wb.active; ws.title = "Outline"
    ws.append(["Response Section Number", "Response Section Name", "Source", "Section L Content", "Management Guidance"])
    plain = InlineFont(color="FF000000"); red = InlineFont(color="FFFF0000"); ital = InlineFont(i=True, color="FF000000")
    rows = [
        ("1", "Technical Approach", None, None, "Lead with the mission thread."),
        ("1.1", "Ground Segment Architecture", "L.4.2.1, p. 41",
         CellRichText([TextBlock(red, "The Offeror shall describe its ground segment architecture, "),
                       TextBlock(ital, "including the two station sites listed in Attachment J-3.")]),
         "Lead with the dual-site failover; tie it to M.2.1."),
        ("1.1", "Ground Segment Architecture", "RFP Section L, paragraph 4.2.2, Instructions to Offerors, page 42",
         CellRichText([TextBlock(plain, "Describe the approach to cybersecurity. "),
                       TextBlock(red, "The Offeror shall meet the controls in Attachment J-5.")]), "Keep it to one page."),
        ("1.2", "Telemetry, Tracking and Command", "L.4.2.3", "The Offeror shall describe its TT&C approach.\nInclude both sites.", None),
    ]
    for r in rows:
        ws.append([r[0], r[1], r[2], None, r[4]])
        ws.cell(row=ws.max_row, column=4).value = r[3]
    wb.save(path)
    return path


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
xl = make_book(os.path.join(tmp, "Kestrel Outline.xlsx"))
book = OX.read(xl, known=OL.known_names(cfg))
prof = OL.profile(cfg, book)
check("the columns read as the team's roles", prof["columns"].get("Source") == "reference" and prof["columns"].get("Section L Content") == "requirement_l",
      prof["columns"])
pg = WB.page(book, prof)
check("each column's tag comes from its role", pg["tags"] == {"Response Section Number": "heading", "Response Section Name": "heading",
      "Source": "source", "Section L Content": "rfp", "Management Guidance": "guidance"}, pg["tags"])
check("the order starts heading, guidance, source, RFP text", pg["order"][:4] == ["heading", "guidance", "source", "rfp"], pg["order"])
check("the column's own text has no character style; red is compliance; black italic is supporting",
      pg["chars"].get("Section L Content|-Iauto") == "SK RFP Support Char" and "SK Compliance Char" in pg["chars"].values()
      and "" in pg["chars"].values(), pg["chars"])
paras = WB.paragraphs(book, prof, pg)
tags = [p["tag"] for p in paras]
check("headings in the workbook's order, each guidance right after its heading",
      tags[:3] == ["heading", "guidance", "heading"] and tags[3:5] == ["guidance", "guidance"], tags)
h = [p for p in paras if p["tag"] == "heading"]
check("headings carry their number and level", [p["runs"][0][0] for p in h] == ["1 Technical Approach", "1.1 Ground Segment Architecture",
      "1.2 Telemetry, Tracking and Command"] and [p["level"] for p in h] == [1, 2, 2], [(p["runs"], p["level"]) for p in h])
first = next(p for p in paras if p["tag"] == "rfp")
check("a short source starts the text in its character style, exactly as typed",
      first["runs"][0] == ("L.4.2.1, p. 41 ", "SK Source Char"), first["runs"])
check("compliance language and supporting text keep their place, each in its character style",
      [c for _t, c in first["runs"][1:]] == ["SK Compliance Char", "SK RFP Support Char"]
      and first["runs"][2][0].startswith("including the two"), first["runs"])
src = [p for p in paras if p["tag"] == "source"]
check("a long source goes on its own line, before the text", len(src) == 1 and src[0]["runs"][0][0].startswith("RFP Section L, paragraph 4.2.2")
      and paras[paras.index(src[0]) + 1]["tag"] == "rfp", [p["runs"] for p in src])
tt = [p for p in paras if p["section"] == "1.2" and p["tag"] == "rfp"]
check("a new line in a cell starts a paragraph", len(tt) == 2 and "".join(t for t, _c in tt[1]["runs"]) == "Include both sites.", [p["runs"] for p in tt])
check("3.97.1: the compliance words list marks the RFP text, as when built in the app", ("shall", "SK Compliance Char") in tt[0]["runs"]
      and tt[1]["runs"][0] == ("Include", "SK Compliance Char"))

# guidance with its row: drag it after the RFP text
WB.move(pg, "guidance", 3)
p2 = WB.paragraphs(book, prof, pg)
sec11 = [p["tag"] for p in p2 if p["section"] == "1.1"]
check("guidance moved after the RFP text goes with each row", sec11 == ["heading", "source", "rfp", "guidance", "rfp", "guidance"]
      or sec11 == ["heading", "rfp", "guidance", "source", "rfp", "guidance"], sec11)
WB.move(pg, "guidance", 1)
# one section's own order
WB.move(pg, "rfp", 1, section="1.2")
p3 = WB.paragraphs(book, prof, pg)
check("one section can have its own order", [p["tag"] for p in p3 if p["section"] == "1.2"][:2] == ["heading", "rfp"]
      and [p["tag"] for p in p3 if p["section"] == "1.1"][:2] == ["heading", "guidance"], [p["tag"] for p in p3])
check("back to every section", WB.back_to_every(pg, "1.2") and "1.2" not in pg["sections"])
# leave the supporting text out; make the compliance language its own paragraph after the RFP text
red_key = next(k for k, v in pg["chars"].items() if v == "SK Compliance Char")
pg["chars"]["Section L Content|-Iauto"] = "-"
pg["own"][red_key] = "rfp"
p4 = WB.paragraphs(book, prof, pg)
r11 = [p for p in p4 if p["section"] == "1.1" and p["tag"] == "rfp"]
check("text left out is gone", not any("including the two" in t for p in p4 for t, _c in p["runs"]), [p["runs"] for p in r11])
check("text made its own paragraph follows the RFP text", any(p["own"] and p["runs"][0][0].startswith("The Offeror shall meet") for p in r11)
      and r11[-1]["own"], [(p["runs"], p["own"]) for p in r11])
pg["chars"]["Section L Content|-Iauto"] = "SK RFP Support Char"; pg["own"].pop(red_key)
check("the styles on the page, paragraph and character", ("SK Compliance Char", "character") in WB.styles_in_use(pg, paras)
      and ("SK RFP Requirement", "paragraph") in WB.styles_in_use(pg, paras), WB.styles_in_use(pg, paras))

# the Word file, without a template
out = WB.write(paras, pg, os.path.join(tmp, "out", "Setup.docx"))
with zipfile.ZipFile(out) as z:
    doc = z.read("word/document.xml").decode(); sty = z.read("word/styles.xml").decode()
_plain = __import__("re").sub(r"<[^>]+>", "", doc)
check("the Word file has every piece of text", "Lead with the dual-site failover" in _plain and "Include both sites." in _plain and "L.4.2.1, p. 41" in _plain)
check("character styles are made as character styles, hidden", 'w:type="character"' in sty and "SKComplianceChar" in sty and "<w:vanish/>" in sty)
check("runs carry their character style", '<w:rStyle w:val="SKComplianceChar"/>' in doc and '<w:rStyle w:val="SKSourceChar"/>' in doc)
check("headings take Heading styles", '<w:pStyle w:val="Heading2"/>' in doc)

# on a template that has its own style by that name: the template's is used; a look set on the page goes over it
import docxw
d = docxw.Doc(); d.heading("Sample", 1); d.para("Sample text")
tpl = os.path.join(tmp, "Team.docx"); d.save(tpl)
with zipfile.ZipFile(tpl) as z:
    files = {n: z.read(n) for n in z.namelist()}
files["word/styles.xml"] = files["word/styles.xml"].replace(b"</w:styles>", b'<w:style w:type="character" w:customStyle="1" w:styleId="TeamCompliance">'
                                                            b'<w:name w:val="AA Compliance"/><w:rPr><w:color w:val="7030A0"/></w:rPr></w:style></w:styles>')
with zipfile.ZipFile(tpl, "w") as z:
    for n, b in files.items():
        z.writestr(n, b)
check("the template's styles are read for the preview", WB.template_looks(tpl).get("AA Compliance", {}).get("color") == "7030A0")
for k, v in list(pg["chars"].items()):
    if v == "SK Compliance Char":
        pg["chars"][k] = "AA Compliance"
pg["looks"]["AA Compliance"] = {"bold": True}
paras = WB.paragraphs(book, prof, pg)
out2 = WB.write(paras, pg, os.path.join(tmp, "out", "Setup on template.docx"), template=tpl)
with zipfile.ZipFile(out2) as z:
    doc = z.read("word/document.xml").decode(); sty = z.read("word/styles.xml").decode()
check("the template's own style is used by name", '<w:rStyle w:val="TeamCompliance"/>' in doc and sty.count("AA Compliance") == 1)
check("a look set on the page goes over the template's", "TeamCompliance" in sty and "<w:b/>" in sty.split('w:styleId="TeamCompliance"')[1].split("</w:style>")[0])
check("the template's sample pages are replaced", "Sample text" not in doc and "Ground Segment Architecture" in doc)

# kept with the layout
WB.save(cfg, prof.get("name") or OL.STARTING, pg)
again = WB.page(book, prof, WB.saved(cfg, prof.get("name") or OL.STARTING))
check("the page's settings come back with the layout", again["chars"] == pg["chars"] and again["looks"] == pg["looks"], again["chars"])
check("the layout's columns and rules are kept", OL.load(cfg)[prof.get("name") or OL.STARTING].get("names") is not None)

print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
