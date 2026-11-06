"""3.71.0 without a screen: the setup from an outline workbook. The header row found and every cell read run by run (a
cell that mixes black italic and colored text keeps both); columns guessed from their headings; the looks in a column;
a profile saved and found again by its headings; the sections (numbers, levels, authors) and each row's blocks (the
requirement with its RFPL reference, customer requirement text and supporting RFP text split by their formatting, the
guidance); problems said (out of order, no reference, a look with no rule); into the effort: the structure, kept and
placed requirements, the customer and supporting text beside them, guidance as each requirement's note, the authors as
the section's lead; an import again replaces its own items; the setup written on the template with each kind in its
style, the setup styles' look (font, size, color, bold, italic, hidden) as set, for every effort or into this effort's
template. Fictional content (Kestrel)."""
import os, re, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import compliance as C, outlinexl as OX, setupdoc as SD, setuptemplate as ST, prodrules as PRL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def make_outline(path):
    """A fictional outline laid out like the team's: a title row, the headings, rows of requirements."""
    from openpyxl import Workbook
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    from openpyxl.styles import Font
    wb = Workbook(); ws = wb.active; ws.title = "Outline"
    ws.append(["Kestrel Ground Segment: response outline"])
    ws.append(["Response Section Number", "Response Section Name", "RFPL Number", "Compliance Requirement", "Supporting RFP Content",
               "Authors", "Management Guidance"])
    ital = InlineFont(i=True, color="FF000000"); cust = InlineFont(color="FF6B21A8")
    rows = [
        ("1", "Technical Approach", "", "", "", "R. Diaz", "Lead with the mission thread."),
        ("1.1", "Ground Segment Architecture", "L.4.2.1", "The offeror shall describe its ground segment architecture.",
         CellRichText([TextBlock(cust, "The Government requires a resilient ground segment with no single point of failure. "),
                       TextBlock(ital, "See SOW C.3.4 for the station locations.")]), "R. Diaz; J. Okafor",
         "Lead with the dual-site design."),
        ("1.1", "Ground Segment Architecture", "L.4.2.2", "The offeror shall describe its approach to cybersecurity.",
         CellRichText([TextBlock(ital, "Attachment J-3 lists the controls.")]), "", ""),
        ("1.2", "Telemetry, Tracking and Command", "", "The offeror shall describe its TT&C approach.", "", "S. Patel", ""),
        ("1.1", "Ground Segment Architecture", "L.4.2.9", "Repeated section.", "", "", ""),
    ]
    for r in rows:
        ws.append([r[0], r[1], r[2], r[3], None, r[5], r[6]])
        ws.cell(row=ws.max_row, column=5).value = r[4] if r[4] else None
    ws.cell(row=3, column=1).font = Font(bold=True)
    wb.save(path)
    return path


tmp = tempfile.mkdtemp()
xl = make_outline(os.path.join(tmp, "Kestrel Outline.xlsx"))
book = OX.read(xl)
check("the header row is found under a title row", book["header_row"] == 2 and book["headers"][3] == "Compliance Requirement", book["headers"])
sup = book["rows"][1]["cells"][4]
check("a cell is read run by run: customer text and black italic support kept apart",
      [lk for _t, lk in sup] == ["--6B21A8", "-Iauto"] and sup[1][0].startswith("See SOW"), sup)
cols = OX.guess(book["headers"])
check("columns guessed from their headings", cols == {"Response Section Number": "section_number", "Response Section Name": "section_name",
      "RFPL Number": "reference", "Compliance Requirement": "requirement", "Supporting RFP Content": "support", "Authors": "authors",
      "Management Guidance": "guidance"}, cols)
lk = OX.looks(book, "Supporting RFP Content")
check("the looks in a column, most used first, with samples", [x["look"] for x in lk] == ["-Iauto", "--6B21A8"] and lk[0]["count"] == 2
      and OX.look_words("-Iauto") == "italic black" and OX.look_words("--6B21A8") == "purple (#6B21A8)")
cfg = os.path.join(tmp, "cfg")
prof = {"columns": cols, "rules": {"Supporting RFP Content": {"-Iauto": "support", "--6B21A8": "customer"}}}
OX.save_profile(cfg, "Kestrel outline", prof)
check("a saved profile is found again by the workbook's headings", OX.profile_for(cfg, book["headers"])["name"] == "Kestrel outline"
      and OX.profile_for(cfg, ["A", "B"])["name"] == "")
p = OX.parse(book, prof)
secs = p["sections"]
check("sections with their numbers, levels and authors", [(s["num"], s["title"], s["level"]) for s in secs[:3]] ==
      [("1", "Technical Approach", 1), ("1.1", "Ground Segment Architecture", 2), ("1.2", "Telemetry, Tracking and Command", 2)]
      and secs[1]["authors"] == ["R. Diaz", "J. Okafor"])
b11 = [(b["kind"], b["text"][:24], b["ref"]) for b in secs[1]["blocks"]]
check("each row's blocks in order: requirement with its reference, customer text, support text, guidance", b11 == [
      ("rfp", "The offeror shall descri", "L.4.2.1"), ("customer", "The Government requires ", ""), ("support", "See SOW C.3.4 for the st", ""),
      ("pm", "Lead with the dual-site ", ""), ("rfp", "The offeror shall descri", "L.4.2.2"), ("support", "Attachment J-3 lists the", ""),
      ("rfp", "Repeated section.", "L.4.2.9")], b11)
check("problems said: a requirement with no reference, a section out of order", any("Row 6: a requirement with no RFP reference" in x for x in p["problems"])
      and any("section 1.1 again after 1.2" in x for x in p["problems"]), p["problems"])
p2 = OX.parse(book, {"columns": cols, "rules": {}})
check("a look with no rule is said, and treated as supporting text", any("has no rule of its own" in x for x in p2["problems"])
      and all(b["kind"] != "customer" for s in p2["sections"] for b in s["blocks"]))
# ---- into the effort
M = C.Matrix(os.path.join(tmp, "Kestrel_Matrix.xlsx"), "Kestrel")
n = OX.apply(M, p, os.path.basename(xl))
S = SD.setup_of(M)
check("the structure comes from the outline", [C.outline_label(o) for o in M.outline][:3] == ["1 Technical Approach", "1.1 Ground Segment Architecture",
      "1.2 Telemetry, Tracking and Command"])
reqs = [it for it in M.items if it["decision"] == "Keep"]
check("each requirement is kept and placed, its RFPL number its reference", n["requirements"] == 4 and reqs[0]["map"] == "1.1 Ground Segment Architecture"
      and SD.ref_of(M, reqs[0])[0] == "L.4.2.1" and SD.block_text(M, reqs[0]).startswith("L.4.2.1: The offeror"))
cu = next(it for it in M.items if it["decision"] == "Customer")
su = [it for it in M.items if it["decision"] == "Context"]
check("customer and supporting text placed beside their requirement", cu["map"] == "1.1 Ground Segment Architecture" and su[0]["context_for"] == reqs[0]["id"]
      and SD.kind_of(su[0]) == "Context")
check("guidance is the requirement's note; a row with only guidance is the section's direction; authors the lead",
      S["notes"][reqs[0]["id"]] == "Lead with the dual-site design." and S["mgmt"]["1 Technical Approach"] == "Lead with the mission thread."
      and S["owners"]["1.1 Ground Segment Architecture"] == {"lead": "R. Diaz", "with": "J. Okafor"})
order = SD.placed_in(M)["1.1 Ground Segment Architecture"]
check("blocks keep the workbook's order in the section", [SD.by_id(M)[i]["text"][:10] for i in order] ==
      ["The offero", "The Govern", "See SOW C.", "The offero", "Attachment", "Repeated s"], [SD.by_id(M)[i]["text"][:10] for i in order])
other = {"id": "L.4.9-01", "file": "Kestrel RFP.pdf", "text": "Kept from the RFP.", "decision": "Keep", "map": "", "section": "L.4.9"}
M.items.append(other)
n2 = OX.apply(M, p, os.path.basename(xl))
check("an import again replaces its own items; requirements from the RFP stay", n2 == n
      and sum(1 for it in M.items if it.get("src") == "outline") == n["requirements"] + n["customer"] + n["support"]
      and any(it["id"] == "L.4.9-01" for it in M.items))
# ---- the setup written on the template, in the setup styles
opts = ST.options(M)
opts["rfp"].update(style="Compliance Requirement", color="7030A0", bold=True, font="Arial", size=11)
opts["customer"].update(style="Customer Requirement Text", color="6B21A8")
opts["support"].update(style="Supporting RFP Text", color="000000", italic=True)
opts["pm"].update(style="Management Guidance", color="00B050")
ST.set_options(M, opts)
check("the look is kept with the options", ST.options(M)["rfp"]["bold"] is True and ST.options(M)["support"]["italic"] is True
      and ST.look(ST.options(M), "rfp")["size"] == 11.0)
out = ST.make_all(M, os.path.join(tmp, "exports"), cfg, effort_name="Kestrel")
z = zipfile.ZipFile(out[0]["setup"])
doc = z.read("word/document.xml").decode(); sty = z.read("word/styles.xml").decode()
cr = re.search(r'<w:style[^>]*w:styleId="ComplianceRequirement".*?</w:style>', sty, re.S)
sp = re.search(r'<w:style[^>]*w:styleId="SupportingRFPText".*?</w:style>', sty, re.S)
check("each setup style is added with its look: bold, Arial 11, color, hidden", cr and "<w:b/>" in cr.group(0) and 'w:ascii="Arial"' in cr.group(0)
      and 'w:sz w:val="22"' in cr.group(0) and "<w:vanish/>" in cr.group(0) and "7030A0" in cr.group(0), cr.group(0) if cr else sty[:300])
check("supporting RFP text: black italic, hidden", sp and "<w:i/>" in sp.group(0) and "000000" in sp.group(0) and "<w:vanish/>" in sp.group(0))
check("the blocks are written in their styles, the requirement with its reference, no lead-ins",
      'w:val="ComplianceRequirement"/></w:pPr><w:r><w:t xml:space="preserve">L.4.2.1: The offeror' in doc.replace("<w:rPr></w:rPr>", "")
      or ("L.4.2.1: The offeror" in doc and 'w:val="ComplianceRequirement"' in doc)
      and 'w:val="CustomerRequirementText"' in doc and 'w:val="SupportingRFPText"' in doc and "Support for" not in doc
      and "Customer's (not answered)" not in doc)
check("the guidance in its style; the headings are Word's", 'w:val="ManagementGuidance"' in doc and "Lead with the dual-site design." in doc
      and 'w:pStyle w:val="Heading2"' in doc)
# ---- for every effort, and into this effort's template
cm = ST.set_team_options(cfg, opts)
check("Use for every effort: the setup styles in the global standard", PRL.load(cfg)["company"]["content_map"]["rfp"]["style"] == "Compliance Requirement"
      and cm["support"]["italic"] is True)


class WS:
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


ws = WS()
names = ST.to_effort_template(ws, opts)
sd = ws.get("prod_std")["over"]["style_defs"]
check("Put them in this effort's template: each style in the effort's own formatting, used on the setup", "Compliance Requirement" in names
      and sd["Compliance Requirement"]["used_on"] == "Setup" and sd["Supporting RFP Text"]["italic"] == "on" and sd["Compliance Requirement"]["hidden"] == "on")

print(f"OUTLINE 371 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
if __name__ == "__main__":                                   # qt_outline371 imports the workbook maker
    sys.exit(0 if all(checks) else 1)
