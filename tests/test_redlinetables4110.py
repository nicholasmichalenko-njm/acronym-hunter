"""4.11.0: Redline's copy makes real Word tables from the PDF's columns (morning answer 17). A run of rows whose pieces
line up is a table; a cell that wrapped stays in its cell; a list or numbered headings with a gap after the marker is
not a table; the check reads a table's words as the copy holds them, so a faithful copy shows no difference, and an
edit to a cell made with Track Changes off is found. Fictional content (the Kestrel samples)."""
import os, re, shutil, sys, tempfile, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "data")
import pagesent as PS, redlinecheck as CK, redlinecopy as RC, redlinetables as RT

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


S = os.path.join(ROOT, "test_samples")
hard = os.path.join(tmp, "Hard_RFP.pdf"); shutil.copy2(os.path.join(S, "rfp_hard", "Hard_RFP.pdf"), hard)
doc = PS.read(hard); doc["skip"] = PS.running(doc)
ts = RT.find(doc, doc["skip"])
check("the page-limit table is found: three columns, a header and two rows", len(ts) == 1 and ts[0]["rows"][0] == ["Volume", "Title", "Page Limit"]
      and len(ts[0]["rows"]) == 3, ts)
check("... a cell that wrapped onto a second line stays in its cell", ts and ts[0]["rows"][2] == ["II", "Management",
                                                                                                 "The management volume shall not exceed 25 pages."],
      ts and ts[0]["rows"])
check("... a line written with a tab in it is not a table", ts and all("tabs badly" not in RT.text_of(t) for t in ts))
manual = PS.read(os.path.join(S, "Kestrel_Program_Manual.pdf")); manual["skip"] = PS.running(manual)
check("a document of headings, paragraphs and lists has no tables", RT.find(manual, manual["skip"]) == [])


def page(rows):                                   # a made-up page: each row one line of pieces at given x positions
    lines = []
    for k, segs in enumerate(rows):
        y = 100 + 14 * k
        lines.append({"text": "  ".join(t for _x, t in segs), "box": (segs[0][0], y, segs[-1][0] + 60, y + 10),
                      "segs": [(x, x + 6 * len(t), t) for x, t in segs]})
    return {"pages": [{"w": 612, "h": 792, "lines": lines}]}


lst = page([[(72, "(a)"), (108, "the approach to thermal control")], [(72, "(b)"), (108, "the test philosophy")],
            [(72, "(c)"), (108, "the schedule risk")]])
check("a list with a gap after each marker is not a table", RT.find(lst, set()) == [])
heads = page([[(72, "3.1"), (120, "Scope")], [(72, "3.2"), (120, "Deliverables")]])
check("numbered headings with a gap after the number are not a table", RT.find(heads, set()) == [])
grid = page([[(72, "Item"), (200, "Quantity")], [(72, "Spare valves"), (200, "12")], [(72, "Seals"), (200, "40")]])
g = RT.find(grid, set())
check("two columns of words are a table", len(g) == 1 and g[0]["rows"] == [["Item", "Quantity"], ["Spare valves", "12"], ["Seals", "40"]], g)
out = os.path.join(tmp, "Hard_RFP - redline copy.docx")
res = RC.build(hard, out)
with zipfile.ZipFile(out) as z:
    x = z.read("word/document.xml").decode("utf-8")
check("the copy has one Word table with the PDF's cells", res["tables"] == 1 and x.count("<w:tbl>") == 1
      and all(s in x for s in ("Technical Approach", "The management volume shall not exceed 25 pages.")), res)
f = CK.faithful(hard, out)
check("the check finds every word of the PDF in the copy, the table's too", not f["differences"] and f["tables"] == 1, f["differences"][:3])
x2 = x.replace(">Technical Approach<", ">Technical Plan<", 1)          # typed over with Track Changes off
back = os.path.join(tmp, "returned.docx")
with zipfile.ZipFile(out) as zi, zipfile.ZipFile(back, "w") as zo:
    for n in zi.namelist():
        zo.writestr(n, x2.encode("utf-8") if n == "word/document.xml" else zi.read(n))
r = CK.returned(out, back)
check("an edit to a table cell made with Track Changes off is found", any(d["was"] == "Approach" or "Approach" in d["was"] for d in r["differences"]),
      r["differences"])
print(f"REDLINE TABLES 4110 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
