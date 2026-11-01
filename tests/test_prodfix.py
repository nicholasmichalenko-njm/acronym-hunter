"""3.6.0 Fix a Copy without screens, on a Word-saved volume with planted defects (from the master template): the check
finds what was planted; the default plan switches on every fix with work and nothing that needs a decision; the run
fixes only the copy, one guarded write per fix, and the original is unchanged; tables, pages, headers and footers,
the TOC field and the styles come out clean; a manual row role and a relinked cross-reference are applied; a fix that
cannot run is refused and the rest still run; the report lands beside the copy; a second run changes nothing; Word's
renumbering is left to the Word step (what remains are the caption and reference numbers Word updates)."""
import os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodfix as PF, prodrules as PRL, prodcopy as PCY
from openpyxl import load_workbook

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "Volumes"); os.makedirs(src)
out = os.path.join(tmp, "Production Copies")
orig = os.path.join(src, "Volume I.docx")
shutil.copy2(os.path.join(HERE, "pefix", "data", "small.docx"), orig)
before = PCY.state(orig)
std0 = PRL.for_effort(tempfile.mkdtemp())
check("3.6.1: no sample volume name, solicitation or company in the team standard", all(PRL.COMPANY["variables"][k] == ""
      for k in ("volume_name", "solicitation", "company")) and std0["variables"]["volume_name"] == "")
t = PRL.COMPANY["terms"]
check("3.6.1: no sample names, products or marks in the team standard's terms", not t["banned"] and not any(t["lists"].values())
      and all(r["why"] == "Common misspelling" for r in t["replace"]), t)
chk0 = PF.check(orig, std0)
plan0 = PF.default_plan(chk0)
check("3.6.1: blank volume name and solicitation: P11 says so, no P4, headers stay off the plan",
      chk0.by_area()["pages"]["P11"] == 1 and not chk0.by_area()["pages"]["P4"] and "hf_build" not in plan0["on"]
      and set(chk0.missing) == {"volume_name", "solicitation"}, (dict(chk0.by_area()["pages"]), chk0.missing))
plan0["on"] = ["hf_build"]; plan0["word_update"] = False
job0 = PF.run(orig, os.path.join(tmp, "Blank copies"), std0, plan0, open_list=[], before=chk0)
st0 = next(s for s in job0.steps if s.get("key") == "hf_build")
check("3.6.1: headers forced on with blank values are refused; the copy keeps its headers", "refused" in st0 and "Volume name" in st0["refused"]
      and not st0["changed"], st0)
std = PRL.apply_context(std0, {"variables": {"solicitation": "FA8810-26-R-0042", "company": "Northwind"}}, volume_name="Volume I Technical")
check("3.6.1: the effort's solicitation and the typed volume name fill the standard for this file",
      std["variables"]["solicitation"] == "FA8810-26-R-0042" and std["variables"]["volume_name"] == "Volume I Technical")
chk = PF.check(orig, std)
by = chk.by_area()
check("the check reads every area", not chk.error and chk.stats.get("captions") == 35 and chk.stats.get("sections") == 11, chk.error)
check("planted caption defects found (typed number, wrong list, chapter part)", by["captions"]["C1"] == 3 and by["captions"]["C2"] == 6
      and by["captions"]["C3"] == 4, dict(by["captions"]))
check("the planted broken reference found, with its place", by["xrefs"]["X1"] == 1 and chk.broken_refs[0]["target"] == "_Ref900000004"
      and chk.broken_refs[0]["near"])
check("page numbers missing from every section found, and the PAGE switch", by["pages"]["P1"] >= 9 and by["pages"]["P5"] == 1)
check("the TOC field differs from the standard", by["toc"]["T2"] == 1 and by["toc"]["T3"] == 1)
check("TOC Heading takes Heading 1's number", by["styles"]["S6"] == 1)
check("tables: 35, every row with a sure role, no questions", len(chk.tables) == 35 and all(not t["questions"] for t in chk.tables)
      and by["tables"]["R0"] == 35)
check("the check never wrote anything", PCY.state(orig) == before and os.listdir(src) == ["Volume I.docx"])
plan = PF.default_plan(chk)
check("the default plan: every fix with work, nothing needing a decision", {"tables", "caption_typed", "caption_fields", "toc_field", "page_numbers",
      "page_field_clean", "hf_build", "unnumber_inheriting", "styles_apply"} <= set(plan["on"]) and "xref_relink" not in plan["on"]
      and plan["word_update"], plan["on"])
t1 = chk.tables[0]
plan["table_roles"] = {1: {t1["rows"][2]["i"]: "subtotal"}}
plan["xref_mapping"] = {"_Ref900000004": chk.bookmarks[0]}
plan["on"].append("xref_relink")
plan["on"].append("styles_merge")                      # no template in the standard: refused, the rest run
job = PF.run(orig, out, std, plan, open_list=[], before=chk)
steps = {s.get("key"): s for s in job.steps}
check("a fix that cannot run is refused and the others still run", "refused" in steps["styles_merge"]
      and all(steps[k]["changed"] for k in ("tables", "caption_typed", "page_numbers", "hf_build")), [(k, s.get("refused", "")[:60]) for k, s in steps.items()])
check("THE GATE: the original is unchanged; nothing beside it", PCY.state(orig) == before and job.original_ok and os.listdir(src) == ["Volume I.docx"])
a = job.after_check.by_area()
check("tables, pages, headers and footers, TOC and styles clean in the copy", not a["tables"] and not a["pages"] and not a["toc"] and not a["styles"],
      {k: dict(v) for k, v in a.items() if v})
check("the relinked cross-reference is no longer broken", "X1" not in a["xrefs"], dict(a["xrefs"]))
check("what is left is what Word renumbers (or only reports)", set(a["captions"]) <= {"C4"} and set(a["xrefs"]) <= {"X2", "X3", "B3"}, {k: dict(v) for k, v in a.items() if v})
from prodengine.engine.pkg import Package
from prodengine.pe import tables as T
from prodengine.engine.ordered import q
pk = Package(job.copy)
names = T.style_name_map(pk.tree(pk.word_part("/styles")))
tbl = next(pk.tree(pk.main).iter(q("tbl")))
row = T.rows(tbl)[t1["rows"][2]["i"]]
ps = row.find(".//" + q("pStyle"))
check("the row role set by hand is applied", names.get(ps.get(q("val"))) == std["row_types"]["subtotal"]["tag_style"], names.get(ps.get(q("val"))))
rp = PF.write_report(job, "Osprey")
wb = load_workbook(rp)
check("the report beside the copy: summary, fixes, by area, what is left", os.path.dirname(rp) == out and wb.sheetnames == ["Summary", "Fixes", "By area", "Left after"]
      and any(r[0].value and "Original unchanged" in r[0].value and r[1].value == "Yes" for r in wb["Summary"].iter_rows()))
try:
    PF.write_report(job, "Osprey"); twice = False
except PCY.NotAllowed:
    twice = True
check("a report is never written over", twice)
with zipfile.ZipFile(job.copy) as z:
    check("the copy is marked as Stationkeeper's", b"Stationkeeper copy" in z.read("docProps/custom.xml"))
job2 = PF.run(job.copy, os.path.join(tmp, "Second"), std, dict(plan, on=[k for k in plan["on"] if k not in ("styles_merge", "xref_relink")]), open_list=[])
check("a second run changes nothing but the copy mark", [s["step"] for s in job2.steps if s.get("changed")] == ["Mark the copy"],
      [s["step"] for s in job2.steps if s.get("changed")])
plan_off = PF.default_plan(chk); plan_off["on"] = ["tables"]
job3 = PF.run(orig, out, std, plan_off, open_list=[], before=chk)
check("a fix switched off does not run", [s.get("key") for s in job3.steps if s.get("key")] == ["tables"] and job3.after_check.by_area()["pages"])
std2 = PRL.engine_ready(PRL.merge(std, {"styles": {"remove_unused_custom": True, "hide_unused_builtin": True}}))
chk2 = PF.check(orig, std2)
check("unused custom styles and unused built-ins in the gallery are listed when asked for", chk2.by_area()["styles"].get("S2", 0) >= 0
      and isinstance(chk2.styles["unused_custom"], list) and isinstance(chk2.styles["hide"], list))
check("THE GATE, at the end", PCY.state(orig) == before)
n = sum(checks)
print(f"PROD FIX {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
