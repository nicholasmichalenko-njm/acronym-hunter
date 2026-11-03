"""3.35.0 the outline matrix: one row per outline item (section, header, subheader) with Assigned To, Initial Page
Allocation, % Complete, and Section L beside Section M; a sentence in several items is in each of their rows;
requirements in no item keep a row; the same columns on sentence rows; % complete follows a renamed item and goes with a
deleted one; a design kept before 3.35.0 keeps its sentence rows; named matrix views in the template library, versioned;
an effort type's starting view."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import compliance as C, matrixdesign as MD, setupdoc as SD, pagebudget as PB, outline_ops as O, prodrules as PRL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
M = C.Matrix(os.path.join(tmp, "m.xlsx"))
M.outline = C.parse_outline("Volume I Technical\n1 Technical Approach\n1.1 Transition Plan\n1.2 Risk")
labs = [C.outline_label(o) for o in M.outline]


def add(i, text, sec, lm="", dec="Keep", m=""):
    it = {"id": i, "text": text, "section": sec, "decision": dec, "map": m, "lm": lm, "file": "RFP.pdf", "loc": "RFP.pdf (p.3)"}
    M.items.append(it)
    return it


add("R1", "The offeror shall describe its transition approach.", "L.4.2.1", "L", m=labs[2])
add("R2", "The Government will evaluate the realism of the transition plan.", "M.2.1", "M", m=labs[2])
r3 = add("R3", "The contractor shall manage risk.", "C.3.1", "C", m=labs[3])
SD.add_section(M, r3, labs[2])
add("R4", "The offeror shall provide a staffing plan.", "L.4.3", "L")
SD.set_people(M, labs[1], "J. Doe", "A. Lee")
PB.set_pages(M, labs[1], 10); PB.set_pages(M, labs[2], 3)
check("% complete is kept per item, 0 to 100", SD.set_progress(M, labs[2], 40) == 40 and SD.set_progress(M, labs[3], 140) == 100
      and SD.progress_of(M, labs[3]) == 100 and SD.set_progress(M, labs[3], None) is None and SD.progress_of(M, labs[3]) is None)
d = MD.default()
check("the default is the outline matrix with the eight columns, in order",
      d["layout"] == "outline" and [c["heading"] for c in d["columns"]] == [
          "Response Section No. Item", "Assigned To", "Initial Page Allocation", "% Complete",
          "RFP Solicitation Requirements (Section L)", "Section L Content", "Evaluation Section (Section M)", "Evaluation Content"])
heads, rows, n = MD.preview(M, d)
items, _ = MD.rows(M, d)
by = {r[0]: r for r in rows}
check("one row per outline item, in order, every level", [r[0] for r in rows][:4] == ["Volume I Technical", "1 Technical Approach",
                                                                                    "1.1 Transition Plan", "1.2 Risk"]
      and [it.get("_level") for it in items][:4] == [1, 1, 2, 2], [r[0] for r in rows])
t = by["1.1 Transition Plan"]
check("the item's own values: assigned to (from its parent), pages, % complete", t[1] == "J. Doe, A. Lee" and t[2] == "3" and t[3] == "40%", t[:4])
check("Section L beside Section M: L and SOW sentences in L, M in M", t[4] == "L.4.2.1\nC.3.1" and "describe its transition" in t[5]
      and "manage risk" in t[5] and t[6] == "M.2.1" and "realism" in t[7] and "realism" not in t[5], t[4:])
check("a sentence in two items is in both rows", "manage risk" in by["1.2 Risk"][5] and "manage risk" in t[5])
check("a requirement in no item keeps a row of its own at the end", rows[-1][0] == MD.UNPLACED and "staffing plan" in rows[-1][5])
d2 = dict(d, empty_sections=False)
_h, rows2, _n = MD.preview(M, d2)
check("items with nothing in them can be left out (a parent of items stays)", "1 Technical Approach" in [r[0] for r in rows2]
      and "Volume I Technical" not in [r[0] for r in rows2], [r[0] for r in rows2])
p = MD.export(M, os.path.join(tmp, "x.xlsx"), d, "Test")
from openpyxl import load_workbook
ws = load_workbook(p["path"])["Compliance Matrix"]
hrow = [c.value for c in ws[4]]
sub = next(r for r in ws.iter_rows(min_row=5) if r[0].value == "1.1 Transition Plan")
top = next(r for r in ws.iter_rows(min_row=5) if r[0].value == "Volume I Technical")
check("Excel: the eight headings, a subheader indented, a top item bold", hrow == heads and sub[0].alignment.indent == 2
      and top[0].font.bold, (sub[0].alignment.indent, top[0].font.bold))
ds = MD.default("sentences"); ds["columns"] += [{"key": k, "heading": MD.COLUMNS[k][0]} for k in MD.OUTLINE_KEYS]
_h, rs, _n = MD.preview(M, ds)
r2 = next(r for r in rs if r[-1].startswith("The Government"))
r1 = next(r for r in rs if r[-3].startswith("The offeror shall describe"))
check("the same columns on sentence rows: an M sentence in Evaluation, an L sentence in Section L", r2[-2] == "M.2.1" and not r2[-3]
      and r1[-4] == "L.4.2.1" and r1[-8] == "1.1 Transition Plan")
O.relabel(M, {labs[2]: "1.1 Transition"})
check("% complete follows a renamed item", SD.progress_of(M, "1.1 Transition") == 40 and SD.progress_of(M, labs[2]) is None)
check("a design kept before 3.35.0 keeps its sentence rows", MD.clean({"columns": [{"key": "text"}], "v": 2})["layout"] == "sentences"
      and MD.clean({})["layout"] == "outline")
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
iid, shown, st = MD.save_view(cfg, "Shipley outline", d)
check("a named view in the template library", st == "new" and shown == "Shipley outline" and MD.views(cfg) == [(iid, shown)]
      and "matrix_view" in dict(__import__("templatelib").SHELVES))
dd = dict(d, columns=d["columns"][:4])
iid2, shown2, st2 = MD.save_view_version(cfg, iid, dd, "four columns")
check("a new version keeps the old one", st2 == "version" and shown2 == "Shipley outline v2: four columns" and len(MD.views(cfg)) == 2)
vd = MD.view_design(cfg, iid2)
check("a view's design says where it came from", vd["view"]["id"] == iid2 and len(vd["columns"]) == 4)
data = PRL.load(cfg); et = data["effort_types"][0]["id"]; PRL.save(cfg, data)
check("an effort type starts its efforts with a view", MD.set_type_view(cfg, et, iid2) and MD.type_view(cfg, et) == iid2
      and len(MD.design_for(C.Matrix(os.path.join(tmp, "n.xlsx")), cfg, et)["columns"]) == 4)
check("the matrix's own design wins over the type's view", (MD.set_matrix(M, d) or True)
      and len(MD.design_for(M, cfg, et)["columns"]) == 8)
n_ = sum(checks)
print(f"MATRIX OUTLINE PASS ({n_}/{len(checks)})" if n_ == len(checks) else f"MATRIX OUTLINE FAIL ({n_}/{len(checks)})")
sys.exit(0 if n_ == len(checks) else 1)
