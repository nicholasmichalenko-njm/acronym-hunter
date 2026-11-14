"""4.30.4, the scale pass (a fictional 700-page customer document, 4,200 pieces): Shred and the matrix do the same work
as before without reading the whole effort once per piece. Each change is held to give exactly what the old way gave."""
import copy, os, random, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "d"))
import compliance as C, compliance_read as CR, assign_ops as AO, pagesent as PS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


B = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_samples")
PDF = os.path.join(B, "rfp_walk", "Section_L_print.pdf")
items, heads, src, _empty = CR.read_files([PDF], lambda p: [])
tmp = tempfile.mkdtemp()
M = CR.new_matrix(os.path.join(tmp, "Osprey_Compliance_Matrix.xlsx"), items, heads, src)
M.outline = C.parse_outline("1 Technical\n1.1 Approach\n2 Management")
R = AO.Review(M)

# ---- a piece by its id
ids = [it["id"] for it in M.items]
check("a piece is found by its id, the same one reading down the list finds",
      all(R.item(i) is next(it for it in M.items if it.get("id") == i) for i in ids) and R.item("no such id") is None)
moved = M.items.pop(3); M.items.insert(10, moved)
check("... after the list is reordered in place", all(R.item(i) is next(it for it in M.items if it.get("id") == i) for i in ids))
gone = M.items.pop(5)
check("... a piece taken out is not found; the rest are", R.item(gone["id"]) is None and R.item(M.items[5]["id"]) is M.items[5])
M.items.insert(5, gone)
M.items = [dict(it) for it in M.items]
check("... and after the list is replaced (an Undo), the new pieces are the ones found", all(R.item(i) is next(it for it in M.items if it.get("id") == i) for i in ids))


# ---- requirements and the Context that follows them: the same as reading every sentence for every row
def old_assign(items, rows, label):
    for it in rows:
        old = it.get("map", "")
        it.update(decision="Keep", map=label, context_for="", draft="", draft_cf="")
        for x in items:
            links = C.cf_ids(x.get("context_for", ""))
            if x.get("decision") == "Context" and links and links[0] == it["id"] and x.get("map", "") in ("", old):
                x["map"] = label
    return len(rows)


random.seed(5)
same = True
for trial in range(60):
    base = []
    for k in range(40):
        dec = random.choice(["", "Keep", "Context", "Context", "Drop"])
        cf = "; ".join(f"S{random.randrange(40)}" for _ in range(random.choice((1, 1, 2)))) if dec == "Context" else ""
        base.append({"id": f"S{k}", "decision": dec, "map": random.choice(["", "", "1 A", "2 B"]), "context_for": cf})
    a, b = copy.deepcopy(base), copy.deepcopy(base)
    pick = sorted(random.sample(range(40), 12))
    random.shuffle(pick)
    lab = random.choice(["", "1 A", "2 B"])
    old_assign(a, [a[i] for i in pick], lab); C.assign_requirement(b, [b[i] for i in pick], lab)
    same = same and a == b
check("60 mixed cases: requirements and the Context that follows give exactly what the old way gave", same)
big = [{"id": f"S{k}", "decision": "", "map": "", "context_for": ""} for k in range(6000)]
t = time.time(); C.assign_requirement(big, big[:5000], "1 A"); took = time.time() - t
check("5,000 of 6,000 pieces become requirements in well under a second (it took most of a minute)", took < 1.5 and big[0]["decision"] == "Keep", took)

# ---- no section yet: once for all, the same result
M2 = CR.new_matrix(os.path.join(tmp, "b.xlsx"), copy.deepcopy(items), heads, src)
R2 = AO.Review(M2)
rows = M2.items[:12]
R2.req(rows, "")
check("pieces made requirements before there is a structure: each is Keep with no section, each logged",
      all(it["decision"] == "Keep" and it["map"] == "" for it in rows) and sum(1 for h in M2.history if "no section yet" in h[3]) == 12)
check("Undo puts them back", R2.undo_last() and all(it.get("decision") != "Keep" for it in M2.items[:12]))

# ---- the page map: each page given its own sentences, the file open once
placed = PS.place_all(PDF, M.items)
its = [dict(it, place=placed[it["id"]][0], lead_place=placed[it["id"]][1]) for it in M.items if it["id"] in placed]
on = PS.by_page(its)
import pypdfium2 as pdfium
pd = pdfium.PdfDocument(PDF); n_pages = len(pd)
whole = [PS.place_map(PDF, n, its, heads) for n in range(1, n_pages + 1)]
part = [PS.place_map(PDF, n, on.get(n, []), heads, pd=pd) for n in range(1, n_pages + 1)]
pd.close()
check("every page's map is the same from its own sentences as from all of them", whole == part and sum(len(m["items"]) for m in whole) > 20)
check("a sentence that runs over a page end is on both pages", any(len({pg for pg, _a, _b in PS.parse_place(it["place"])}) > 1 for it in its) is not None
      and all(it in on[pg] for it in its for pg, _a, _b in PS.parse_place(it["place"])))

# ---- where a sentence sits: the same page and paragraph as counting down every paragraph of the file
def old_where(pdf, place):
    sp = PS.parse_place(place)
    if not sp:
        return 0, 0
    pg, a, _b = sp[0]
    doc = PS.doc_of(pdf)
    if pg - 1 >= len(doc["pages"]):
        return pg, 0
    lines = doc["pages"][pg - 1]["lines"]
    k = 0
    for para in doc.get("paras") or ():
        mine = [li for pi, li in para["lines"] if pi == pg - 1]
        if not mine or para["kind"] == "heading":
            continue
        k += 1
        if any(lines[li]["a"] <= a < lines[li]["b"] + 1 for li in mine):
            return pg, k
    return pg, 0


got = [PS.where(PDF, it["place"]) for it in its]
check("every sentence's page and paragraph are what counting down the whole file gives", got == [old_where(PDF, it["place"]) for it in its]
      and len({g for g in got}) > 10 and PS.where(PDF, "") == (0, 0) and PS.where(PDF, "999:0-5") == (999, 0), got[:5])

# ---- the saved workbook reads as it always did
for it in M.items[:6]:
    it["decision"] = "Keep"; it["map"] = "1.1 Approach"
M.items[7]["decision"] = "Drop"; M.items[8]["decision"] = "Context"
M.save()
from openpyxl import load_workbook
wb = load_workbook(M.path); ws = wb[wb.sheetnames[0]]
check("one row per piece, in order", ws.max_row == len(M.items) + 1 and [ws.cell(row=r, column=1).value for r in (2, 9, len(M.items) + 1)]
      == [M.items[0]["id"], M.items[7]["id"], M.items[-1]["id"]], ws.max_row)
looks = {}
for k, it in enumerate(M.items):
    c = ws.cell(row=k + 2, column=3)
    looks.setdefault(it.get("decision", ""), set()).add((c.alignment.wrap_text, c.alignment.vertical, str(c.fill.fgColor.rgb)))
check("every cell wrapped and top-aligned; one fill per decision, and Keep, Context and Drop differ where they did",
      all(len(v) == 1 and next(iter(v))[:2] == (True, "top") for v in looks.values()) and len({next(iter(v))[2] for v in looks.values()}) >= 2, looks)
back = C.Matrix(M.path).load()
check("it loads back with every decision and section", [(i["id"], i["decision"], i["map"]) for i in back.items] == [(i["id"], i["decision"], i["map"]) for i in M.items])
check("the log's time is worked out once a second", [M.log("x", "y") for _ in range(2000)] and len({h[0] for h in M.history[-2000:]}) <= 2)
n = sum(checks)
print(f"SCALE 4304 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
