"""3.32.0 exact preview and prepagination, without the window: Quick Parts measured by Word (a stand-in for Word's
answer) and their pages kept on the library item; the page plan using measured pages; a prepaginated setup (a section's
planned pages kept, the next section on a new page, placed Quick Parts counted); the exact preview's files made without
recording anything, Word's pages mapped to sections; Final Checks on the response elements (missing, order, part)."""
import json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import compliance as C, outline_ops as O, responseelements as RE, setupdoc as SD, pagebudget as PB, pageplan as PP
import templatelib as TL, qpmeasure as QM, elementbuild as EB, elementcheck as EC, exactpreview as EP, setuptemplate as ST

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
# ---------------------------------------------------------------- a Quick Part in the library, measured
from _qpfixture import with_glossary
import app_gui as A
src = os.path.join(tmp, "Boilerplate.docx")
with_glossary(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), src)
lib = TL.Library(cfg)
import prodrules as PRL
cards, err = TL.collect(src, PRL.for_effort(tempfile.mkdtemp()), lib)
qp_card = [c for c in cards if c.key == "quickparts"]
check("collect: the Quick Parts are on a card", bool(qp_card) and not err, err)
kept = []
TL.save_collected(lib, src, qp_card, quickparts=kept)
check("kept Quick Parts are listed to measure", len(kept) == 3, kept)
iid = next(i for i in kept if lib.get(i)["name"] == "Table caption")
dot = QM.as_template(lib.source_path(lib.values(lib.get(iid))["source"]), os.path.join(tmp, "w"))
ct = zipfile.ZipFile(dot).read("[Content_Types].xml").decode()
check("a .docx source is measured as a template (only its content type changes)", dot.endswith(".dotx") and "template.main+xml" in ct)
seen = {}


def word(cmd, env, timeout):                     # Word's answer, as the script prints it
    seen.update(env)
    return json.dumps([{"pages": 3, "why": ""}])


res = QM.measure(lib, [iid], runner=word)
lines = seen.get("SK_LIST", "").split("\t")
check("Word is asked for the entry by name and category, paths in the environment", lines[1:] == ["Table caption", "Captions"]
      and lines[0].endswith(".dotx"), lines)
check("the pages are kept on the library item (measured)", res == {iid: 3} and TL.Library(cfg).get(iid)["pages"] == 3
      and TL.Library(cfg).get(iid)["pages_how"] == "measured", res)
check("the work copy is taken away", not os.path.isdir(os.path.join(lib.root, "_measuring")))
r2 = QM.measure(TL.Library(cfg), [iid], runner=lambda *a: json.dumps([{"pages": 0, "why": "missing"}]))
check("a Quick Part Word cannot find says so, and keeps its pages", "did not find" in r2[iid] and TL.Library(cfg).get(iid)["pages"] == 3, r2)
check("no Word on this PC: it says so", "Word on this PC" in QM.measure(TL.Library(cfg), [iid])[iid] if not QM.available() else True)
lib = TL.Library(cfg)
check("typed pages; same Quick Part met again still matches", lib.set_pages(iid, 2) and lib.pages_of(iid) == 2
      and lib.match("quickpart", "Table caption", lib.values(lib.get(iid)))[0] == "same")
lib.set_pages(iid, 3, "measured")
ex = ST.element_extras(cfg)
check("the elements' extras carry the library's pages", ex["lib_pages"] == {iid: 3} and ex["lib_pages_by_name"] == {"table caption": 3})

# ---------------------------------------------------------------- the page plan uses measured pages
M = C.Matrix(os.path.join(tmp, "m.xlsx"), "m")
vol = O.add_volume(M, "Technical")
t1 = O.add(M, "Technical Approach", parent=vol)
t11 = O.add(M, "Past Performance", parent=t1)
t2 = O.add(M, "Management", after=t1)
SD.set_volumes(M, "several", "", [vol])
O.place_lib(M, t11, {"id": iid, "kind": "quickpart", "name": "Table caption"})
pages = PP.plan(M, vol, {}, ex)
body = [p["label"] for p in pages if p["part"] == "body"]
check("a 3-page Quick Part in a subsection adds its pages", body.count(t1) + body.count(t11) == 3 and body.count(t2) == 1, body)
lib_line = [l for p in pages for l, h in p["lines"] if h == "lib"]
check("... and says them", lib_line == ["Table caption (quickpart, 3 pages)"], lib_line)
PB.set_pages(M, t1, 5)
body = [p["label"] for p in PP.plan(M, vol, {}, ex) if p["part"] == "body"]
check("a section with pages set keeps them: the Quick Part is inside them", body.count(t1) + body.count(t11) == 5, body)
d = RE.load(cfg)
le = RE.get(d, "letter"); le["lib"] = "Table caption"
d["lib_pages_by_name"] = ex["lib_pages_by_name"]
RE.apply_kit(M, d, ["letter"], vol)
check("an element made of a Quick Part takes its measured pages", PB.pages(M, "Cover letter") == 3, PB.pages(M, "Cover letter"))
pl = PP.plan(M, vol, {}, dict(ex, data=d))
check("... in the plan too", [p["label"] for p in pl].count("Cover letter") == 3)

# ---------------------------------------------------------------- a prepaginated setup
P, inh = SD.placed_in(M), SD.inherited_sections(M)
entries = [o for o in M.outline if C.outline_label(o) != vol]
plain = SD._doc_for(M, vol, entries, P, inh, "now", extras={"data": d}).body
prep = SD._doc_for(M, vol, entries, P, inh, "now", extras={"data": d, "prepaginate": True, "lib_pages": ex["lib_pages"]}).body
n_plain = sum(x == EB.reserved_page() for x in plain)
n_prep = sum(x == EB.reserved_page() for x in prep)
check("plain: no pages kept", n_plain == 0)
check("prepaginated: 5 pages less the 3-page Quick Part leaves 2 kept pages", n_prep == 2, n_prep)
k = max(i for i, x in enumerate(prep) if x == EB.reserved_page())
nxt = next(x for x in prep[k + 1:] if x.startswith("<w:p"))
check("the next section starts on a new page (Page break before, after its style)",
      '<w:pStyle w:val="Heading1"/><w:pageBreakBefore/>' in nxt and t2 in nxt, nxt[:120])
check("break_before leaves a page break or a table as it is", EB.break_before(EB.page_break()) == EB.page_break()
      and EB.break_before("<w:tbl/>") == "<w:tbl/>" and EB.break_before("<w:p><w:r/></w:p>").startswith("<w:p><w:pPr><w:pageBreakBefore/>"))
O.set_break(M, t1, "landscape")
P = SD.placed_in(M)
prep = SD._doc_for(M, vol, entries, P, inh, "now", extras={"data": d, "prepaginate": True, "lib_pages": ex["lib_pages"]}).body
marks = [i for i, x in enumerate(prep) if "SKSectionMark" in x and "end:" in x]
kept = [i for i, x in enumerate(prep) if x == EB.reserved_page()]
check("a landscape Word section keeps its pages inside it (before it ends)", kept and marks and max(kept) < marks[0], (kept, marks))
O.set_break(M, t1, None)
ST.set_prepaginate(M, True)
check("the choice is kept with the structure", ST.prepaginate(M) and SD.setup_of(M)["prepaginate"] is True)

# ---------------------------------------------------------------- the exact preview's pages
heads = [("Table of Contents", 2), (t1, 3), (t11, 4), (t2, 7)]
secs = EP.section_of_pages(heads, O.labels(M), 8)
check("Word's pages mapped to sections (the last heading started on or before)", secs == ["", "", t1, t11, t11, t11, t2, t2], secs)
out = {}


def lay(cmd, env, timeout):
    out.update(env)
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument.new()
    for k in range(4):
        doc.new_page(792 if k == 3 else 612, 612 if k == 3 else 792)
    doc.save(env["SK_PDF"]); doc.close()
    return json.dumps({"ok": True, "pages": 4, "heads": [{"t": t1, "p": 2}]})


r = EP.lay_out(os.path.join(tmp, "x.docx"), os.path.join(tmp, "x.pdf"), runner=lay)
check("Word's layout: pages, headings and the PDF", r["ok"] and r["pages"] == 4 and r["heads"] == [(t1, 2)], r)
r = EP.lay_out(os.path.join(tmp, "y.docx"), os.path.join(tmp, "y.pdf"), runner=lambda *a: json.dumps({"ok": False, "why": "-2146822880"}))
check("Word failing says so", not r["ok"] and "could not lay out" in r["why"], r)
for n in range(5):
    os.makedirs(os.path.join(tmp, "prev", f"2026-11-0{n + 1}_120000"))
EP.prune(os.path.join(tmp, "prev"))
check("only the last three preview folders stay", sorted(os.listdir(os.path.join(tmp, "prev"))) == ["2026-11-03_120000", "2026-11-04_120000", "2026-11-05_120000"])

# ---------------------------------------------------------------- Final Checks: the elements
M2 = C.Matrix(os.path.join(tmp, "m2.xlsx"), "m2")
v1 = O.add_volume(M2, "Technical")
O.add(M2, "Approach", parent=v1)
v2 = O.add_volume(M2, "Cost")
O.add(M2, "Pricing", parent=v2)
SD.set_volumes(M2, "several", "", [v1, v2])
d = RE.load(cfg)
RE.apply_kit(M2, d, ["toc", "lof", "acr"], v1)
RE.apply_kit(M2, d, ["toc"], v2)
M2.items = [
    {"id": "L-1", "text": "Each volume shall include a table of contents, a list of figures and an acronym list.", "decision": "Keep",
     "loc": "Section L (p.3)", "file": "rfp.pdf"},
    {"id": "L-2", "text": "The Technical Volume shall include an executive summary.", "decision": "Keep", "loc": "Section L (p.4)", "file": "rfp.pdf"},
    {"id": "L-3", "text": "A glossary is not needed.", "decision": "Drop", "loc": "", "file": "rfp.pdf"},
]
rows = EC.check(M2, d)
got = {(r["volume"], r["check"], r["element"]) for r in rows}
check("missing: Cost lacks the list of figures and acronyms the RFP names for every volume",
      {(v2, "Missing", "List of Figures"), (v2, "Missing", "Acronyms and Abbreviations")} <= got, got)
check("missing: the volume a sentence names (the Technical Volume's executive summary)",
      (v1, "Missing", "Executive Summary") in got and (v2, "Missing", "Executive Summary") not in got, got)
check("a dropped sentence is not counted; the Technical volume has its TOC, lists and acronyms",
      not any(r["volume"] == v1 and r["check"] == "Missing" and r["element"] != "Executive Summary" for r in rows), rows)
check("where: the RFP sentence", any(r["where"] == "L-1 (Section L (p.3))" for r in rows))
fl = [o for o in M2.outline if o.get("element") == "lof"][0]
i = M2.outline.index(fl); M2.outline.insert(i - 1, M2.outline.pop(i))              # List of Figures before the TOC
rows = EC.check(M2, d)
check("order: the RFP lists the TOC before the List of Figures", any(r["check"] == "Order" and r["volume"] == v1
      and r["element"] == "Table of Contents" for r in rows), [r for r in rows if r["check"] == "Order"])
M2.outline.insert(i, M2.outline.pop(i - 1))
O.add(M2, "Executive Summary", parent=v1)
rows = EC.check(M2, d)
check("a section of that name counts as the element", not any(r["element"] == "Executive Summary" and r["volume"] == v1 for r in rows))
toc = [o for o in M2.outline if o.get("element") == "toc"][0]
toc["part"] = "body"
rows = EC.check(M2, d)
check("part: a Table of Contents in the response", any(r["check"] == "Part" and r["element"] == "Table of Contents" for r in rows), rows)
p = EC.export(os.path.join(tmp, "e.xlsx"), rows, "Kestrel")
from openpyxl import load_workbook
check("exported to Excel, a row a finding", load_workbook(p).active.max_row == 2 + len(rows))
n = sum(checks)
print(f"EXACT {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
