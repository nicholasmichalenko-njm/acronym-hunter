"""3.38.0 the production rules read from Word files (rulecheck.py), on two small files written by hand: one that keeps
every rule and one that breaks each. Rule 1 (STYLEREF style in a text box), Rule 2 (A number right-justified, right under
the restriction block), Rule 3 (marking at the top and bottom center), Rule 4 (style named with another response type),
Rule 5 (title page style with no title page, by "Used on", never by name), Rule 6 (heading numbers at 0, one text
position), Rule 7 (the footer table), Rule 8 (caption and notes rows at 0.0). Then Audit reports them under their rule,
a rule turned off is not reported, and Fix a Copy puts Rule 6 right without touching anything else. Fictional content."""
import copy, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodfix as PF, prodrules as PRL, rulebook as RB, rulecheck as RC
from prodengine.engine.pkg import Package

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


NSD = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml"')
MK = "UNCLASSIFIED"


def _p(text="", style="", jc="", ind=None, inner=""):
    ppr = (f'<w:pStyle w:val="{style}"/>' if style else "") + (f'<w:ind w:left="{ind[0]}" w:right="{ind[1]}"/>' if ind else "") + \
          (f'<w:jc w:val="{jc}"/>' if jc else "")
    return f'<w:p><w:pPr>{ppr}</w:pPr>{inner}<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def _fld(instr):
    return f'<w:fldSimple w:instr=" {instr} "><w:r><w:t>1</w:t></w:r></w:fldSimple>'


def _style(sid, name, jc="", num=None, kind="paragraph"):
    ppr = (f'<w:numPr><w:numId w:val="{num}"/></w:numPr>' if num else "") + (f'<w:jc w:val="{jc}"/>' if jc else "")
    return f'<w:style w:type="{kind}" w:styleId="{sid}"><w:name w:val="{name}"/><w:pPr>{ppr}</w:pPr></w:style>'


def make(path, good):
    styles = [_style("Normal", "Normal"), _style("AANumber", "AA A Number", jc="right" if good else ""),
              _style("AARestriction", "AA Restriction"), _style("AADocTitle", "AA Doc Title"),
              _style("Heading1", "heading 1", num=1), _style("Heading2", "heading 2"),
              _style("PETableCaption", "PE Table Caption"), _style("PETableNote", "PE Table Note")]
    if not good:
        styles += [_style("AARFPHeading", "AA RFP Heading"), _style("AATitlePageName", "AA Title Page Name")]
    lv = []
    for i in range(3):                             # good: every level number at 0, text at 0.5; bad: stepped
        left = 720 if good else 360 + 360 * i
        lv.append(f'<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%{i + 1}."/>'
                  f'<w:pPr><w:tabs><w:tab w:val="num" w:pos="{left}"/></w:tabs><w:ind w:left="{left}" w:hanging="{left}"/></w:pPr></w:lvl>')
    numbering = (f'<w:numbering {NSD}><w:abstractNum w:abstractNumId="0">{"".join(lv)}</w:abstractNum>'
                 f'<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>')
    box = (f'<w:r><w:pict><v:shape><v:textbox><w:txbxContent>{_p("Kestrel Flight Software Plan", "AADocTitle")}'
           f'</w:txbxContent></v:textbox></v:shape></w:pict></w:r>')
    body = []
    if good:
        body.append(_p("Kestrel Flight Software Plan", "AADocTitle"))
        body.append(_p("WARNING: this document holds fictional data rights text.", "AARestriction"))
    else:
        body.append(_p("WARNING: this document holds fictional data rights text.", "AARestriction"))
        body.append(_p("A note between the block and the number"))
        body.append(f'<w:p><w:pPr></w:pPr>{box}</w:p>')
    body.append(_p("A-2026-0042", "AANumber"))
    body.append(_p("Introduction", "Heading1"))
    ind = (0, 0) if good else (360, 0)
    body.append(f'<w:tbl><w:tr><w:tc>{_p("Table 1. Fictional rates", "PETableCaption", ind=ind)}</w:tc></w:tr>'
                f'<w:tr><w:tc>{_p("Note: illustrative only.", "PETableNote", ind=(0, 0))}</w:tc></w:tr></w:tbl>')
    sect = ('<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdF"/>'
            '<w:pgSz w:w="12240" w:h="15840"/></w:sectPr>')
    doc = f'<w:document {NSD}><w:body>{"".join(body)}{sect}</w:body></w:document>'
    header = f'<w:hdr {NSD}>{_p(MK if good else "", jc="center", inner=_fld("STYLEREF &quot;AA Doc Title&quot;"))}</w:hdr>'
    if good:
        footer = (f'<w:ftr {NSD}><w:tbl><w:tr><w:tc><w:p>{_fld("STYLEREF &quot;AA A Number&quot;")}</w:p></w:tc>'
                  f'<w:tc>{_p(MK)}{_p("Use or disclosure is subject to the restriction on the title page")}</w:tc>'
                  f'<w:tc><w:p><w:pPr><w:jc w:val="right"/></w:pPr>{_fld("PAGE")}</w:p></w:tc></w:tr></w:tbl><w:p/></w:ftr>')
    else:
        footer = f'<w:ftr {NSD}>{_p("Page ", jc="right", inner=_fld("PAGE"))}</w:ftr>'
    ct = ('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
          '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    base = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    drels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             f'<Relationship Id="rIdS" Type="{base}styles" Target="styles.xml"/>'
             f'<Relationship Id="rIdN" Type="{base}numbering" Target="numbering.xml"/>'
             f'<Relationship Id="rIdH" Type="{base}header" Target="header1.xml"/>'
             f'<Relationship Id="rIdF" Type="{base}footer" Target="footer1.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc); z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("word/styles.xml", f'<w:styles {NSD}>{"".join(styles)}</w:styles>')
        z.writestr("word/numbering.xml", numbering); z.writestr("word/header1.xml", header); z.writestr("word/footer1.xml", footer)
    return path


tmp = tempfile.mkdtemp()
good = make(os.path.join(tmp, "Kestrel good.docx"), True)
bad = make(os.path.join(tmp, "Kestrel bad.docx"), False)
std = PRL.engine_ready(copy.deepcopy(PRL.COMPANY))
std["style_roles"] = {"a_number": "AA A Number", "restriction": "AA Restriction"}
std.setdefault("style_defs", {})["AA Title Page Name"] = {"used_on": "Title page"}
std["page_parts"] = {}
std.setdefault("variables", {})["classification"] = MK
std["response_type"] = "RFI"

g = RC.check(Package(good), std, marking=MK, response_type="RFI")
check("a file that keeps every rule has no rule findings", g == [], g)
b = RC.check(Package(bad), std, marking=MK, response_type="RFI")
codes = {c for c, _w in b}
check("a file that breaks each rule gets every finding, RU1 to RU8", codes == {f"RU{i}" for i in range(1, 9)}, sorted(codes))
txt = {c: [w for cc, w in b if cc == c] for c in codes}
check("Rule 1: the style the header reads, in a text box", any("AA Doc Title" in w and "text box" in w for w in txt.get("RU1", [])), txt.get("RU1"))
check("Rule 2: not right-justified, and not right under the restriction block", len(txt.get("RU2", [])) == 2, txt.get("RU2"))
check("Rule 3: the marking missing at the top center (it is not in the bad header)", any("top center" in w for w in txt.get("RU3", [])),
      txt.get("RU3"))
check("Rule 4: a style named with RFP in an RFI response", any("AA RFP Heading" in w and "RFI" in w for w in txt.get("RU4", [])), txt.get("RU4"))
check("Rule 5: a title page style by its Used on, with no title page", any("AA Title Page Name" in w for w in txt.get("RU5", [])), txt.get("RU5"))
check("Rule 6: heading levels indented differently from level 1",
      any("indented differently" in w for w in txt.get("RU6", [])), txt.get("RU6"))
check("Rule 7: the footer is not the one-row, three-column table", any("not a one-row, three-column table" in w for w in txt.get("RU7", [])),
      txt.get("RU7"))
check("Rule 8: the caption row is indented; the notes row at 0.0 is not reported", len(txt.get("RU8", [])) == 1
      and "PE Table Caption" in txt["RU8"][0], txt.get("RU8"))

std5 = dict(std, style_defs={"AA Title Page Name": {"used_on": "Cover"}})
check("Rule 5 follows Used on, never the name: a style named 'Title Page' used on the cover is not reported",
      not [w for c, w in RC.check(Package(bad), std5, marking=MK, response_type="RFI") if c == "RU5"])
check("Rule 5: a response with a title page keeps its title page styles",
      not [w for c, w in RC.check(Package(bad), dict(std, page_parts={"title": "t.docx"}), marking=MK, response_type="RFI") if c == "RU5"])
check("Rule 4: in an RFP response the RFP style is right", not [w for c, w in RC.check(Package(bad), std, marking=MK, response_type="RFP")
                                                               if c == "RU4"])
check("Rule 3 needs a marking to check: none given, none reported", not [w for c, w in RC.check(Package(bad), std, marking="") if c == "RU3"])
std_nr = dict(std, style_roles={"a_number": "AA A Number", "restriction": ""})
check("Rule 2 without a restriction style: the block is found by its words (Warning)",
      not [w for c, w in RC.check(Package(good), std_nr, marking=MK) if c == "RU2"])

# Audit reports them by rule, with the fix that answers each
chk = PF.check(bad, std)
ru = [f for f in chk.findings if str(f["rule"]).startswith("RU")]
check("Audit reports the rule findings", {f["rule"] for f in ru} == {f"RU{i}" for i in range(1, 9)}, sorted({f["rule"] for f in ru}))
check("each finding names its rule", all(RB.rule_of_code(f["rule"]) for f in ru) and RB.rule_of_code("RU6") == "Rule 6")
fixes = {f["rule"]: f["fix"] for f in ru}
check("Rule 6 is fixed by putting heading positions right; Rule 8 by the table fix; Rule 7 has no fix yet",
      fixes.get("RU6") == "heading_positions" and fixes.get("RU8") == "tables" and not fixes.get("RU7"), fixes)
off = PF.check(bad, dict(std, _rules_off=["6", "7"]))
check("a rule turned off (globally or for the effort) is not reported", not [f for f in off.findings if f["rule"] in ("RU6", "RU7")]
      and [f for f in off.findings if f["rule"] == "RU8"])

# Fix a Copy puts Rule 6 right and nothing else
out = os.path.join(tmp, "Copies"); os.makedirs(out)
job = PF.run(bad, out, std, {"on": ["heading_positions"], "word_update": False}, open_list=[])
st = {s.get("key"): s for s in job.steps}
check("the Rule 6 fix ran on the copy", st.get("heading_positions", {}).get("changed"), st.get("heading_positions"))
after = RC.check(Package(job.copy), std, marking=MK, response_type="RFI")
check("after the fix: no Rule 6 finding, the others stay", not [c for c, _w in after if c == "RU6"]
      and len(after) == len(b) - len(txt["RU6"]), (len(after), len(b), [w for c, w in after if c == "RU6"]))
with zipfile.ZipFile(job.copy) as z:
    nb = z.read("word/numbering.xml").decode()
check("only positions changed: number formats and number text stay", nb.count('w:val="decimal"') == 3 and '%3.' in nb)
job2 = PF.run(job.copy, os.path.join(tmp, "Copies 2"), std, {"on": ["heading_positions"], "word_update": False}, open_list=[])
check("running it again changes nothing", not {s.get("key"): s for s in job2.steps}.get("heading_positions", {}).get("changed"))

# Rule 6 in the standards: stepped positions from a learned type become one position
s6 = {"heading_numbering": {"levels": [{"number_at": 0.25, "text_at": 0.3}, {"number_at": 0.3, "text_at": 0.4}]}}
PRL.rule6(s6)
check("Rule 6 in the standards: every level's number at 0 and level 1's text position", all(l["number_at"] == 0.0 and l["text_at"] == 0.3
      for l in s6["heading_numbering"]["levels"]), s6)

n = sum(checks)
print(f"RULE CHECK {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
