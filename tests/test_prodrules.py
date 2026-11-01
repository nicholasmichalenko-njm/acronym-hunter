"""3.6.0 production standards in three layers: the team standard, document types and the effort keep only what they
change; a 3.5 file becomes document types with the same values; the RFP's rules fill the effort; Format Check reads the
same standard; the format variables drive the styles; a back cover is recognised only as the last section starting
with one of its styles, so a volume without one keeps its page numbers."""
import json, os, sys, tempfile, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodrules as P
from prodengine.pe import sections as S
from prodengine.engine.pkg import Package

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = tempfile.mkdtemp()
d = P.load(cfg)
check("nothing saved: one document type on the team standard", [t["id"] for t in d["types"]] == ["proposal"] and d["default"] == "proposal")
check("the team standard has every section", all(k in d["company"] for k in ("variables", "fonts", "styles", "heading_numbering", "row_types",
      "table_types", "row_rules", "captions", "pagination", "page_setups", "hf_layouts", "toc", "lists", "terms", "checks")))
check("every page scheme has a back cover part", all(p["parts"][-1]["key"] == "backer" for p in P.presets().values()))
check("the engine's own presets are not changed", all(x["key"] != "backer" for p in P.PR.PAGINATION_PRESETS.values() for x in p["parts"]))
d["company"]["variables"]["body_size"] = 12
d["types"].append({"id": "cost", "name": "Cost volume", "variables": {"table_size": 8}})
P.save(cfg, d)
raw = json.load(open(os.path.join(cfg, P.FILE)))
check("the team file keeps only what differs from the built-in standard", raw["company"] == {"variables": {"body_size": 12}}, raw["company"])
d2 = P.load(cfg)
cost = P.resolved_type(d2, "cost")
check("a document type is the team standard with its own changes on top", cost["variables"]["body_size"] == 12 and cost["variables"]["table_size"] == 8
      and cost["name"] == "Cost volume")


class WS:
    def __init__(self, v): self.v = v
    def get(self, k, default=None): return self.v.get(k, default)


eff = P.for_effort(cfg, WS({"prod_std": {"type": "cost", "over": {"variables": {"body_font": "Arial"}, "fonts": {"body": {"min_size": 11}}}}}))
check("the effort sits on its document type", eff["variables"]["body_font"] == "Arial" and eff["variables"]["table_size"] == 8 and eff["effort_over"]
      and eff["fonts"]["body"]["min_size"] == 11 and eff["fonts"]["body"]["fonts"] is None)
check("an unknown document type falls back to the default", P.for_effort(cfg, WS({"prod_std": {"type": "gone"}}))["name"] == "Proposal volume")
lay = P.diff(cost, d2["company"])
check("diff gives exactly the changes", lay == {"variables": {"table_size": 8}, "name": "Cost volume"}, lay)
check("merge then diff is the layer again", P.diff(P.merge(d2["company"], {"captions": [{"label": "Exhibit"}]}), d2["company"]) == {"captions": [{"label": "Exhibit"}]})
# a 3.5 file
cfg35 = tempfile.mkdtemp()
json.dump({"types": [{"name": "Proposal volume", "fonts": {"body": {"font": "Times New Roman", "min": 12, "max": 12},
                                                           "table": {"font": "Arial", "min": 10, "max": 0}},
                      "margins_in": 1.0, "page": "Letter", "caption_numbers": "plain", "caption_sep": "space", "toc_forbid": ["\\o"],
                      "page_numbers": False},
                     {"name": "Cost volume", "fonts": {"table": {"font": "Arial Narrow", "min": 8}}}], "default": "Cost volume"},
          open(os.path.join(cfg35, P.FILE), "w"))
m = P.load(cfg35)
pv = P.resolved_type(m, "proposal_volume")
check("a 3.5 file becomes document types with the same values", [t["name"] for t in m["types"]] == ["Proposal volume", "Cost volume"]
      and m["default"] == "cost_volume" and pv["fonts"]["body"] == {"min_size": 12.0, "max_size": 12.0, "fonts": ["Times New Roman"], "rfp_ref": ""}
      and pv["variables"]["body_size"] == 12.0 and pv["checks"]["toc_forbid"] == ["\\o"] and pv["checks"]["page_numbers"] is False
      and all(c["chapter_level"] is None and c["after_number"] == "period_space" for c in pv["captions"]), pv["fonts"]["body"])
c35 = P.to_check(P.engine_ready(copy.deepcopy(pv)))
check("Format Check reads the migrated standard as 3.5 did", c35["fonts"]["body"] == {"font": "Times New Roman", "min": 12.0, "max": 12.0}
      and c35["fonts"]["table"]["font"] == "Arial" and c35["caption_numbers"] == "plain" and c35["caption_sep"] == "space"
      and c35["page_numbers"] is False and c35["margins_in"] == 1.0, c35)
# the RFP
rows = [{"kind": "Format", "subject": "Font", "value": "12-point Times New Roman"},
        {"kind": "Format", "subject": "Font in tables and figures", "value": "10-point Arial, no smaller"},
        {"kind": "Format", "subject": "Margins", "value": "1-inch margins"}, {"kind": "Format", "subject": "Page size", "value": "A4"},
        {"kind": "Instruction", "subject": "Font", "value": "ignored"}]
over, said = P.from_rfp(rows)
check("the RFP's formatting rules become the effort's values", over["variables"]["body_font"] == "Times New Roman" and over["variables"]["body_size"] == 12.0
      and over["variables"]["table_font"] == "Arial" and over["fonts"]["table"]["min_size"] == 10.0 and over["fonts"]["caption"]["min_size"] == 10.0
      and over["variables"]["margin_left"] == 1.0 and over["variables"]["paper"] == "A4" and len(said) == 4, over)
spec = P.variable_style_spec(P.engine_ready(P.merge(P.COMPANY, over)))
check("the variables drive the styles", spec["Normal"]["font"] == "Times New Roman" and spec["Normal"]["size"] == 12.0
      and spec["PE Table Text"]["font"] == "Arial" and spec["Caption"]["size"] == 10.0, spec.get("Normal"))
bad = P.engine_ready(P.merge(P.COMPANY, {"fonts": {"body": {"min_size": 12, "max_size": 10}}}))
check("validation names a smallest size above the largest", any("smallest size is larger" in x for x in P.validate(bad)))
check("blank and zero mean not set", P.engine_ready({"fonts": {"body": {"min_size": 0, "max_size": "", "fonts": ""}}})["fonts"]["body"]
      == {"min_size": None, "max_size": None, "fonts": None})
# a back cover only with its style
std = P.engine_ready(P.merge(P.COMPANY, {}))
sm = S.map_sections(Package(os.path.join(HERE, "pefix", "data", "small.docx")), std)
check("a volume without a back cover keeps its last section in the appendices", sm.sections[-1].part == "appendix",
      [(s.i, s.part, s.first_style) for s in sm.sections[-2:]])
part = std["pagination"]["parts"][-1]


class Sec:
    first_style = "Back Cover"


check("the last section starting with a back cover style is the back cover", S._starts(part, Sec(), 10, 11)
      and not S._starts(part, Sec(), 9, 11) and not S._starts(part, type("X", (), {"first_style": "Heading 7"})(), 10, 11))
# ---------------------------------------------------------------- 3.6.1: the effort's own values, never a sample
os.environ["AH_TEST"] = "1"
import app_gui as A
A.CONFIG_DIR = os.path.join(tempfile.mkdtemp(), "config"); os.makedirs(A.CONFIG_DIR)
over, said = P.from_rfp([{"kind": "Format", "subject": "Line spacing", "value": "double-spaced"}])
o2, _ = P.from_rfp([{"kind": "Format", "subject": "Line spacing", "value": "single-spaced"}])
o3, _ = P.from_rfp([{"kind": "Format", "subject": "Line spacing", "value": "1.5 line spacing"}])
check("3.6.1: the RFP's line spacing fills the effort", over["variables"]["line_spacing"] == "double" and o2["variables"]["line_spacing"] == "single"
      and o3["variables"]["line_spacing"] == "1.5" and said == ["Line spacing: double-spaced"], (over, o2, o3))
import banned as BN, customdict as CD, authorlist as AL, effortrec as ER, deliverables as DL
BN.save([{"Phrase": "world-class", "Level": "Banned", "Use instead": "", "Why": "Unsupported"},
         {"Phrase": "utilize", "Level": "Avoid", "Use instead": "use", "Why": ""}])
st = CD.Store(A.CONFIG_DIR); st.add("Team words", ["cislunar", "MBSE"]); st.save()
al = AL.load(A.CONFIG_DIR); al.add("Dana Whitfield"); al.add("Lee Osei", efforts=["Other effort"]); al.save()


class Lst:
    rows = {"CDRL": {"Status": "Approved"}, "XYZ": {"Status": "Proposed"}}


efdir = tempfile.mkdtemp()
rec = ER.Record(efdir)
draft = os.path.join(efdir, "Tech v3.docx"); open(draft, "wb").close()
DL.add(rec, "Volume II Management", file=draft, limit="25 pages")
ctx = P.context(A.CONFIG_DIR, "Osprey", {"solicitation": " FA8810-26-R-0042 "}, Lst(), rec, draft)
check("3.6.1: the solicitation comes from the effort's basics", ctx["variables"]["solicitation"] == "FA8810-26-R-0042", ctx["variables"])
check("3.6.1: a draft on the Deliverables board takes the deliverable's name as its volume name",
      ctx["variables"]["volume_name"] == "Volume II Management" and ctx["deliverable"]["limit"] == "25 pages", ctx["deliverable"])
check("3.6.1: banned phrases from the team's list, with their suggestion", [b["find"] for b in ctx["banned"]] == ["utilize", "world-class"]
      and ctx["banned"][0]["suggest"] == "use")
check("3.6.1: dictionary words, this effort's authors and its approved acronyms",
      ctx["lists"]["team_terms"] == CD.sort_words(["cislunar", "MBSE"]) and ctx["lists"]["employee_names"] == ["Dana Whitfield"]
      and ctx["lists"]["acronyms"] == ["CDRL"], ctx["lists"])
none = P.context(A.CONFIG_DIR, "", {}, None, rec, os.path.join(efdir, "elsewhere.docx"))
check("3.6.1: a draft not on the board has no volume name; no effort, no solicitation", "volume_name" not in none["variables"]
      and "solicitation" not in none["variables"] and none["deliverable"] is None)
std = P.for_effort(cfg)
lay = P.merge(std, {"variables": {"solicitation": "SET-BY-LAYER"}})
got = P.apply_context(lay, ctx)
check("3.6.1: a value a layer sets wins over the effort's; blank values are filled", got["variables"]["solicitation"] == "SET-BY-LAYER"
      and got["variables"]["volume_name"] == "Volume II Management")
got2 = P.apply_context(std, ctx, volume_name="Volume II  Management Approach")
check("3.6.1: the volume name typed on Fix a Copy wins", got2["variables"]["volume_name"] == "Volume II Management Approach")
check("3.6.1: team lists are added to the standard, which is not changed", "MBSE" in got2["terms"]["lists"]["team_terms"]
      and not std["terms"]["lists"]["team_terms"] and any(b["find"] == "utilize" for b in got2["terms"]["banned"]))
check("3.6.1: the layouts' tokens are known, and blank ones without a cover paragraph are missing",
      set(P.hf_tokens(std)) == {"volume_name", "solicitation"} and P.missing_values(std) == ["volume_name", "solicitation"]
      and P.missing_values(std, ["PE Volume Name", "PE Solicitation"]) == [] and P.missing_values(got2) == [])
import prodcopy as PCY
check("3.6.1: each effort's copies go in its own folder, named safely", PCY.effort_folder("C:/Out", "Osprey: Phase 2?") == os.path.join("C:/Out", "Osprey Phase 2")
      and PCY.effort_folder("C:/Out", "") == "C:/Out" and PCY.effort_folder("C:/Out", "CON") == os.path.join("C:/Out", "_CON")
      and PCY.effort_folder("C:/Out", "Draft. ") == os.path.join("C:/Out", "Draft"))
n = sum(checks)
print(f"PROD RULES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
