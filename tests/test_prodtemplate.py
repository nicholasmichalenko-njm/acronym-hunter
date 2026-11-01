"""3.7.0 document types as templates: learn a document type from a template or a finished volume (styles whole, table
looks, page setups, headers and footers, heading numbering, the TOC); check and set every style property a style
library defines (indents, keeps, page break before, caps, underline, next style...) on a copy; make a Word template
from a standard, which passes its own check and teaches back the same style library; per-deliverable document types
and the page limit."""
import hashlib, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodcopy as PCY
import prodfix as PF
import prodlearn as PL
import prodrules as PRL
import prodtemplate as PT
from prodengine.engine.pkg import Package
from prodengine.engine.ops import word_ops as WO

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


DATA = os.path.join(HERE, "pefix", "data")
MASTER, SMALL = os.path.join(DATA, "PE_Master_Effort_Template.dotx"), os.path.join(DATA, "small.docx")
m0, s0 = sha(MASTER), sha(SMALL)
std = PRL.for_effort(tempfile.mkdtemp())

# ---------------------------------------------------------------- learn
lm = PL.learn(MASTER, std)
ls = PL.learn(SMALL, std)
check("learn reads the master template: styles, variables, page setups, heading numbering", not lm.error
      and {"styles", "variables", "pages", "heading_numbering"} <= set(lm.areas), list(lm.areas))
check("learn reads a finished volume: also headers and footers, the TOC", {"styles", "headers", "toc", "pages"} <= set(ls.areas), list(ls.areas))
h1 = lm.layer(["styles"])["style_defs"]["Heading 1"]
check("a style is learned whole (font through theme, size, bold, color, spacing, keeps, based on, next; a numbered "
      "style's indents belong to its numbering)",
      h1["font"] and h1["size"] == 14.0 and h1["bold"] is True and h1["keep_next"] is True and h1["based_on"] == "Normal"
      and h1["next"] == "Normal" and "left" not in h1 and "page_break_before" in h1, h1)
check("Word's default character style and linked Char styles are not learned",
      "Default Paragraph Font" not in lm.layer()["style_defs"] and not any(n.endswith(" Char") for n in lm.layer()["style_defs"]))
hn = lm.layer(["heading_numbering"])["heading_numbering"]
check("heading numbering learned level by level", hn["on"] and hn["levels"][0]["style"] == "Heading 1" and hn["levels"][1]["text"] == "%1.%2")
hf = ls.layer(["headers"])["hf_layouts"]
check("headers learned: the chapter title field becomes {chapter}, the page field {page}",
      hf["body"]["header"]["left"].startswith("{chapter}") and "Example Program" in hf["body"]["header"]["left"]
      and hf["body"]["footer"]["right"] == "{page}" and hf["cover"] == {"header": {}, "footer": {}}, hf)
toc = ls.layer(["toc"])["toc"]
check("the TOC's switches and levels learned", toc["switches"] == ["\\h", "\\u", "\\z"] and len(toc["levels"]) == 3, toc)
check("learning never writes the file", sha(MASTER) == m0 and sha(SMALL) == s0)
only = lm.layer(["variables"])
check("only the chosen areas are taken", set(only) == {"variables"})

# ---------------------------------------------------------------- the style library on a copy
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "Volumes"); os.makedirs(src)
orig = os.path.join(src, "Volume I.docx"); shutil.copy2(SMALL, orig)
lib = PRL.merge(std, {"style_defs": {"Heading 2": {"type": "paragraph", "size": 13, "left": 18, "hanging": 18, "keep_lines": True,
                                                    "page_break_before": False, "caps": True, "underline": True, "next": "Normal",
                                                    "color": "1F3864", "before": 12, "after": 6},
                                      "PE Callout": {"type": "paragraph", "based_on": "Normal", "italic": True, "jc": "center", "left": 36,
                                                     "right": 36, "line": 14, "line_rule": "exact"}}})
chk = PF.check(orig, lib)
s4 = [f for f in chk.findings if f["rule"] == "S4" and f["what"].startswith("Heading 2:")]
s7 = [f for f in chk.findings if f["rule"] == "S7"]
check("Check lists each property of a style that differs, with the file's value and the standard's",
      s4 and all(w in s4[0]["what"] for w in ("left indent", "hanging indent", "all caps", "underline", "standard 1F3864")), s4)
check("a style the library defines and the file lacks is listed once (the fix adds it)", len(s7) == 1 and "PE Callout" in s7[0]["what"])
plan = PF.default_plan(chk)
check("the style fix is on by default", "styles_apply" in plan["on"])
plan["on"] = ["styles_apply"]; plan["word_update"] = False
job = PF.run(orig, os.path.join(tmp, "out"), lib, plan, open_list=[], before=chk)
step = next(s for s in job.steps if s.get("key") == "styles_apply")
root = WO.styles_root(Package(job.copy))
h2 = WO.find_style(root, "Heading 2")
got = {k: WO.effective(root, h2, k) for k in ("size", "left", "hanging", "keep_lines", "caps", "underline", "color", "before", "after")}
check("every property set on the copy, through the guard", step["changed"] and "refused" not in step and got == {
      "size": 13.0, "left": 18.0, "hanging": 18.0, "keep_lines": True, "caps": True, "underline": True, "color": "1F3864",
      "before": 12.0, "after": 6.0}, (step.get("refused"), got))
co = WO.find_style(root, "PE Callout")
check("a new style made with its definition (exact line spacing in points, both indents)", co is not None
      and WO.effective(root, co, "line") == 14.0 and WO.effective(root, co, "line_rule") == "exact"
      and WO.effective(root, co, "right") == 36.0 and WO.effective(root, co, "jc") == "center")
check("the copy is clean on styles afterwards; the original unchanged", not [f for f in job.after_check.findings if f["rule"] in ("S4", "S7")]
      and job.original_ok and sha(orig) == s0)
plan2 = {"on": ["styles_apply"], "word_update": False}
job2 = PF.run(job.copy, os.path.join(tmp, "out2"), lib, plan2, open_list=[])
check("a second run changes no style", not next(s for s in job2.steps if s.get("key") == "styles_apply")["changed"])
skip = PF.FIX["styles_apply"]["args"](lib, {"style_skip": ["Heading 2"]})["spec"]
check("a style can be left out of the fix", "Heading 2" not in skip and "PE Callout" in skip)

# ---------------------------------------------------------------- 3.8.0: tab stops, borders and shading in a style
lib8 = PRL.merge(std, {"style_defs": {"PE Callout": {"type": "paragraph", "based_on": "Normal", "tabs": [[72, "left", "dot"], [468, "right", "none"]],
                                                       "border_top": "1 1F3864", "border_bottom": "0.5 1F3864", "shading": "D9E2F3"}}})
j8 = PF.run(orig, os.path.join(tmp, "out8"), lib8, {"on": ["styles_apply"], "word_update": False}, open_list=[])
r8 = WO.styles_root(Package(j8.copy)); c8 = WO.find_style(r8, "PE Callout")
check("3.8: a style's tab stops, borders and shading are set and read back", WO.effective(r8, c8, "tabs") == [[72.0, "left", "dot"], [468.0, "right", "none"]]
      and WO.effective(r8, c8, "border_top") == "1 1F3864" and WO.effective(r8, c8, "shading") == "D9E2F3"
      and not [f for f in j8.after_check.findings if f["rule"] in ("S4", "S7")])
back8 = PL.learn(j8.copy, std).layer(["styles"])["style_defs"]["PE Callout"]
check("3.8: learning takes them back", back8.get("tabs") == [[72.0, "left", "dot"], [468.0, "right", "none"]] and back8.get("border_bottom") == "0.5 1F3864"
      and back8.get("shading") == "D9E2F3" and "border_left" not in back8)

# ---------------------------------------------------------------- make a template
out = os.path.join(tmp, "Production Copies", "Templates")
tj = PT.make(std, out)
check("a template from the team standard: a dated .dotx in the output folder, marked as a template",
      os.path.dirname(tj.copy) == out and tj.copy.endswith(".dotx") and PCY.is_copy_name(tj.copy)
      and PT.TEMPLATE_CT in zipfile.ZipFile(tj.copy).read("[Content_Types].xml").decode())
check("every step ran, none refused", not [s for s in tj.steps if s.get("refused")], [s for s in tj.steps if s.get("refused")])
check("THE TEMPLATE PASSES ITS OWN CHECK: no finding in any area", tj.check.count() == 0 and not tj.check.error,
      [f["what"][:90] for f in tj.check.findings])
check("it has the cover, front matter, a chapter and an appendix; captions as fields; the TOC and lists",
      tj.check.stats.get("sections") == 4 and tj.check.stats.get("captions") == 3 and tj.check.stats.get("tocs") == 3, tj.check.stats)
learned_std = PRL.merge(std, lm.layer(["styles", "variables", "heading_numbering", "pages"]))
learned_std["name"] = "Learned volume"
tj2 = PT.make(learned_std, out)
check("a template from a learned document type passes its own check too", tj2.check.count() == 0, [f["what"][:90] for f in tj2.check.findings])
back = PL.learn(tj2.copy, learned_std).layer(["styles"])["style_defs"]
want = lm.layer(["styles"])["style_defs"]
diffs = [(n, k) for n in want for k in want[n] if back.get(n, {}).get(k) != want[n][k]]
check("ROUND TRIP: learning from the template made gives back the same style library", not diffs, diffs[:8])
tj3 = PT.make(learned_std, out, start_from=MASTER)
check("a template started from your own template keeps it untouched and passes its style check",
      sha(MASTER) == m0 and tj3.start == os.path.basename(MASTER)
      and not [f for f in tj3.check.findings if f["rule"] in ("S4", "S7")], [f["what"][:80] for f in tj3.check.findings][:6])
hfstep = next((s for s in tj3.steps if s.get("key") == "hf_build"), {})
check("headers are not built into a template whose cover lacks the volume values (nothing blank typed)",
      "refused" in hfstep and "Volume name" in hfstep["refused"], hfstep)
check("two templates in the same minute never overwrite each other", tj.copy != tj2.copy and len(os.listdir(out)) == 3)
try:
    PT.make(std, out, start_from=os.path.join(DATA, "Logo.png"))
    check("only Word files are started from", False)
except PCY.NotAllowed:
    check("only Word files are started from", True)

# ---------------------------------------------------------------- what Word keeps when it saves (from the template gate)
from lxml import etree as _et
from prodengine.engine.ordered import q as _q
sr = WO.styles_root(Package(tj2.copy))
sub = WO.find_style(sr, "Subtitle")
check("a built-in style is written the way Word writes it (not as a custom style, which Word drops on save)",
      sub is not None and sub.get(_q("customStyle")) is None and sub.find("w:name", WO.NS).get(_q("val")) == "Subtitle"
      and WO.builtin_name(sr, "Caption") == "caption" and WO.builtin_name(sr, "PE Callout") is None)
pk = Package(tj.copy)
nb = pk.tree(pk.word_part("/numbering"))
a = nb.find("w:abstractNum", WO.NS)
a2 = _et.fromstring(_et.tostring(a))
for el in a2.iter(_q("suff")):
    el.getparent().remove(el)
check("heading numbering compares the same after Word drops the default tab after the number",
      a is not None and WO._lvl_signature(a) == WO._lvl_signature(a2))
check("a template whose captions and pages use chapter numbers gets numbered headings (2-1, A-1 need them)",
      WO.find_style(WO.styles_root(pk), "Heading 1").find("w:pPr/w:numPr", WO.NS) is not None)

# ---------------------------------------------------------------- 3.9.0: list numbering by level
from prodengine.pe import listnum as LN
ln_std = PRL.merge(std, {"list_numbering": {"on": True}})
want_ln = ln_std["list_numbering"]["lists"]
chk9 = PF.check(orig, ln_std)
l9 = [f for f in chk9.findings if f["rule"] == "L9"]
check("3.9: Check lists each list style whose bullets or numbers differ from the profile", len(l9) == 6
      and any(f["what"].startswith("List Number 2") for f in l9), [f["what"][:60] for f in l9])
j9 = PF.run(orig, os.path.join(tmp, "out9"), ln_std, {"on": ["list_numbering"], "word_update": False}, open_list=[], before=chk9)
st9 = next(x for x in j9.steps if x.get("key") == "list_numbering")
got9 = LN.read_levels(Package(j9.copy), [lv["style"] for l in want_ln for lv in l["levels"]], strict=True)
check("3.9: the fix gives each list style its level (bullet or number, text, positions), through the guard",
      st9["changed"] and "refused" not in st9 and got9["List Bullet 2"]["text"] == "\u2013" and got9["List Number 3"]["fmt"] == "lowerRoman"
      and got9["List Number"]["left"] == 0.25 and not [f for f in j9.after_check.findings if f["rule"] == "L9"], (st9.get("refused"), got9))
j9b = PF.run(j9.copy, os.path.join(tmp, "out9b"), ln_std, {"on": ["list_numbering"], "word_update": False}, open_list=[])
check("3.9: a second run changes no list numbering", not next(x for x in j9b.steps if x.get("key") == "list_numbering")["changed"])
lt = PL.learn(j9.copy, std).layer(["list_numbering"]).get("list_numbering")
check("3.9: learning takes the list numbering back", lt and [[{k: v for k, v in lv.items()} for lv in l["levels"]] for l in lt["lists"]]
      == [[dict(lv) for lv in l["levels"]] for l in want_ln], lt)
check("3.9: a list style borrowing another list's level is not learned as its own (the master's List Bullet uses the heading list)",
      PL.learn(MASTER, std).layer().get("list_numbering") is None)
tj9 = PT.make(std, out)
got_t = LN.read_levels(Package(tj9.copy), ["List Bullet", "List Number"], strict=True)
check("3.9: a template's list styles show their bullets and numbers", got_t.get("List Bullet", {}).get("text") == "\u2022"
      and got_t.get("List Number", {}).get("text") == "%1." and tj9.check.count() == 0, (got_t, [f["what"] for f in tj9.check.findings]))

# ---------------------------------------------------------------- 3.10.0: Word table styles
from prodengine.pe import tablestyles as TSS
TS_XML = ('<w:style xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:type="table" w:customStyle="1">'
          '<w:name w:val="PE Data Table"/><w:uiPriority w:val="59"/><w:pPr><w:spacing w:after="0"/></w:pPr>'
          '<w:tblPr><w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="1F3864"/>'
          '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="1F3864"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="8EA9DB"/>'
          '</w:tblBorders></w:tblPr><w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:color w:val="FFFFFF"/></w:rPr>'
          '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="1F3864"/></w:tcPr></w:tblStylePr></w:style>')
ts_std = PRL.merge(std, {"table_styles": {"PE Data Table": {"xml": TS_XML, "based_on": "Normal Table"}},
                         "table_types": {"std": {"word_style": "PE Data Table"}}})
c10 = PF.check(orig, ts_std)
r5 = [f for f in c10.findings if f["rule"] == "R5"]; r6 = [f for f in c10.findings if f["rule"] == "R6"]
check("3.10: Check lists a Word table style the profile has and the file lacks, and tables not using their type's style",
      len(r5) == 1 and "not in the file" in r5[0]["what"] and len(r6) >= 10, (len(r5), len(r6)))
pl10 = PF.default_plan(c10)
check("3.10: the table style and table fixes are on by default", {"table_styles", "tables"} <= set(pl10["on"]))
j10 = PF.run(orig, os.path.join(tmp, "out10"), ts_std, {"on": ["table_styles", "tables"], "word_update": False,
                                                       "table_answers": {}, "table_roles": {}, "table_types": {}}, open_list=[], before=c10)
st10 = {x.get("key"): x for x in j10.steps}
p10 = Package(j10.copy)
sid = TSS.style_id(p10, "PE Data Table")
from prodengine.pe import tables as _T
std_tables = [t for t in p10.tree(p10.main).iter(_q("tbl")) if not list(t.iterancestors(_q("tbl"))) and not _T.is_figure_table(t)]
check("3.10: the style is added through the guard and every standard table uses it", st10["table_styles"]["changed"]
      and "refused" not in st10["table_styles"] and sid and all(t.find("w:tblPr/w:tblStyle", WO.NS) is not None
                                                                 and t.find("w:tblPr/w:tblStyle", WO.NS).get(_q("val")) == sid for t in std_tables)
      and not [f for f in j10.after_check.findings if f["rule"] in ("R5", "R6")], (st10["table_styles"].get("refused"), sid))
j10b = PF.run(j10.copy, os.path.join(tmp, "out10b"), ts_std, {"on": ["table_styles"], "word_update": False}, open_list=[])
check("3.10: a second run changes no table style", not next(x for x in j10b.steps if x.get("key") == "table_styles")["changed"])
back10 = PL.learn(j10.copy, ts_std).layer(["table_styles", "tables"])
check("3.10: learning takes the table style back whole, and the table type's style", "PE Data Table" in back10.get("table_styles", {})
      and TSS._sig(_et.fromstring(back10["table_styles"]["PE Data Table"]["xml"])) == TSS._sig(_et.fromstring(TS_XML))
      and back10.get("table_types", {}).get("std", {}).get("word_style") == "PE Data Table", back10.get("table_types"))
changed_xml = TS_XML.replace('w:fill="1F3864"', 'w:fill="C00000"')
diff_std = PRL.merge(ts_std, {"table_styles": {"PE Data Table": {"xml": changed_xml, "based_on": "Normal Table"}}})
check("3.10: a table style that differs is reported as differing", any(f["rule"] == "R5" and "differs" in f["what"]
                                                                        for f in PF.check(j10.copy, diff_std).findings))
tj10 = PT.make(ts_std, out)
check("3.10: a template carries the table style, its sample table uses it, and it passes its own check",
      TSS.style_id(Package(tj10.copy), "PE Data Table") and tj10.check.count() == 0, [f["what"] for f in tj10.check.findings])

# ---------------------------------------------------------------- 3.10.0: covers and back covers
import docx as _docx
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Inches
import prodparts as PP
vdoc = _docx.Document()
vdoc.add_picture(os.path.join(DATA, "Logo.png"), width=Inches(2))
vdoc.add_paragraph("Program Technical Volume", style="Title")
vdoc.add_section(WD_SECTION.NEW_PAGE)
vdoc.add_paragraph("Introduction", style="Heading 1"); vdoc.add_paragraph("Body text.")
bc = vdoc.styles.add_style("Back Cover", WD_STYLE_TYPE.PARAGRAPH)
vdoc.add_section(WD_SECTION.NEW_PAGE)
vdoc.add_paragraph("Company address and contact", style="Back Cover")
vdoc.add_picture(os.path.join(DATA, "Logo.png"), width=Inches(1))
vpath = os.path.join(tmp, "Volumes", "Cover volume.docx"); vdoc.save(vpath)
v0 = sha(vpath)
pdir = os.path.join(tmp, "config", "production_parts")
lp = PL.learn(vpath, std, parts_dir=pdir)
pp = lp.layer(["page_parts"]).get("page_parts") or {}
check("3.10: Learn from a file keeps the cover and the back cover, each as a Word file of its own",
      set(pp) == {"cover", "backer"} and all(os.path.isfile(os.path.join(pdir, f)) for f in pp.values()) and sha(vpath) == v0, pp)
cov = open(os.path.join(pdir, pp["cover"]), "rb").read()
check("3.10: the cover keeps its picture", PP.part_signature(cov) == (("Title",), 0, 1), PP.part_signature(cov))
pstd = PRL.merge(std, {"page_parts": pp}); pstd["_parts_dir"] = pdir; pstd["name"] = "With pages"
tjp = PT.make(pstd, out)
traw = open(tjp.copy, "rb").read()
check("3.10: a template made from the profile has its cover (picture included) and back cover", PP.signature(traw, "cover", pstd) == (("Title",), 0, 1)
      and PP.signature(traw, "backer", pstd) == (("Back Cover",), 0, 1) and any(n.startswith("word/media/sk_part") for n in zipfile.ZipFile(tjp.copy).namelist()),
      (PP.signature(traw, "cover", pstd), PP.signature(traw, "backer", pstd)))
check("3.10: and it passes its own check, headers built, every step run", tjp.check.count() == 0 and not [x for x in tjp.steps if x.get("refused")],
      ([f["what"][:80] for f in tjp.check.findings], [x.get("refused") for x in tjp.steps if x.get("refused")]))
cp = PF.check(SMALL, pstd)
p12 = [f for f in cp.findings if f["rule"] == "P12"]; p13 = [f for f in cp.findings if f["rule"] == "P13"]
check("3.10: Check reports a cover built differently and a missing back cover (reported, never changed)",
      len(p12) == 1 and "differently" in p12[0]["what"] and len(p13) == 1 and "no back cover" in p13[0]["what"]
      and not p12[0]["fix"] and not p13[0]["fix"], ([f["what"][:80] for f in p12 + p13]))

# 3.10.0, from the template gate: Word recomputes theme-linked colors from the file's theme when it saves, and
# writes a table style without an empty tblPr or a property that only repeats the defaults
from lxml import etree as _et
from prodengine.engine.ops import word_ops as _WO
from prodengine.pe import tablestyles as _TS
_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
_c = _et.fromstring(f'<w:color {_W} w:val="17365D" w:themeColor="text2" w:themeShade="BF"/>')
check("3.10: a theme-linked color reads as the file's theme shows it", _WO.theme_hex(_c, {"_colors": {"dk2": "0E2841"}}) == "0A1D30"
      and _WO.theme_hex(_c, {"_colors": {"dk2": "1F497D"}}) == "17365D", _WO.theme_hex(_c, {"_colors": {"dk2": "0E2841"}}))
check("3.10: with no theme in the file it never matches a color, so the fix writes the color itself",
      _WO.theme_hex(_c, {}) == "THEME" and _WO.theme_hex(_c, None) is None
      and _WO.theme_hex(_et.fromstring(f'<w:color {_W} w:val="FFFFFF" w:themeColor="background1" w:themeTint="99"/>'), {"_colors": {"lt1": "000000"}}) is None)
_ts_want = _et.fromstring(f'<w:style {_W} w:type="table"><w:name w:val="T"/><w:pPr><w:spacing w:after="0"/></w:pPr><w:tblStylePr w:type="firstRow"><w:rPr><w:b/></w:rPr></w:tblStylePr></w:style>')
_ts_word = _et.fromstring(f'<w:style {_W} w:type="table" w:styleId="T"><w:name w:val="T"/><w:basedOn w:val="TableNormal"/><w:tblStylePr w:type="firstRow"><w:rPr><w:b/></w:rPr><w:tblPr/></w:tblStylePr></w:style>')
_ts_root = _et.fromstring(f'<w:styles {_W}><w:docDefaults><w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240"/></w:pPr></w:pPrDefault></w:docDefaults></w:styles>')
_ts_root2 = _et.fromstring(f'<w:styles {_W}><w:docDefaults><w:pPrDefault><w:pPr><w:spacing w:after="160"/></w:pPr></w:pPrDefault></w:docDefaults></w:styles>')
check("3.10: a table style Word re-saved reads the same; a real difference still shows", _TS._sig(_ts_want, _ts_root) == _TS._sig(_ts_word, _ts_root)
      and _TS._sig(_ts_want, _ts_root2) != _TS._sig(_ts_word, _ts_root2)
      and _TS._sig(_ts_want, _et.fromstring(f'<w:styles {_W}><w:docDefaults><w:pPrDefault/></w:docDefaults></w:styles>')) == _TS._sig(_ts_word, _ts_root))

# ---------------------------------------------------------------- per-deliverable types, page limits
check("page limits read from the Deliverables board's wording", PRL.page_limit("25 pages") == 25 and PRL.page_limit("15-page limit") == 15
      and PRL.page_limit("30") == 30 and PRL.page_limit("no limit") is None)
check("Word's page count against the limit", "limit is 25" in PRL.limit_note("25 pages", 27) and "Check what the RFP counts" in
      PRL.limit_note("25 pages", 27) and "Check" not in PRL.limit_note("25 pages", 20) and PRL.limit_note("", 20) == "")
cfg = tempfile.mkdtemp()
d = PRL.load(cfg); d["types"].append({"id": "cost", "name": "Cost volume", "variables": {"table_size": 8}}); PRL.save(cfg, d)
check("a deliverable's own document type is used instead of the effort's", PRL.for_effort(cfg, None, type_id="cost")["name"] == "Cost volume"
      and PRL.for_effort(cfg, None, type_id="cost")["variables"]["table_size"] == 8 and PRL.for_effort(cfg)["name"] == "Proposal volume")
n = sum(checks)
print(f"PROD TEMPLATE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
