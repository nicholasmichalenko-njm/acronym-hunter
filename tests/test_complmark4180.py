"""4.18.0: compliance language marked on words of a piece (asked 2026-11-11 17:51). Words marked on a piece are
compliance language there (whether the list has them or not); words the list marks can be taken off one piece; the
piece keeps its type; the marks come out in the compliance style in the Excel matrix, the Word outline and the setup
document parts, and the matrix keeps them when saved and opened again; everywhere adds them to the compliance words
list. Fictional (Kestrel)."""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
import compliance as C, cwords as CW

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


tmp = tempfile.mkdtemp()
cfg = CW._clean({})
text = "Offerors may not exceed the page limit of 25 pages and shall submit one copy."
it = {"id": "L-1", "text": text, "type": "Instruction"}
before = [t for t, w in CW.segments(text, cfg, *CW._marks(it)) if w]
CW.mark(it, "page limit", True)
CW.mark(it, "shall", False)
after = [t for t, w in CW.segments(text, cfg, *CW._marks(it)) if w]
check("words marked on a piece are compliance language there", "page limit" in after and "page limit" not in before, after)
check("... and a word the list marks can be taken off one piece", "shall" in before and "shall" not in after)
check("... the piece keeps its type", it["type"] == "Instruction")
check("... other pieces are untouched", "shall" in [t for t, w in CW.segments(text, cfg) if w])
parts = CW.docx_parts(text, None, cfg, it=it)
check("the setup and the Word outline write the marked words bold (the compliance style)",
      any(t == "page limit" and f.get("bold") for t, f in parts) and not any(t == "shall" and f.get("bold") for t, f in parts))
val = CW.xlsx_value(text, cfg, it=it)
check("the Excel matrix writes them bold too", "page limit" in [str(b.text) for b in val if hasattr(b, "font") and b.font.b], list(val))
check("the piece pane shows them in the style", '<span style="font-weight:700">page limit</span>' in CW.html(text, cfg, it))
check("a mark set twice is set once; Not undoes an earlier mark", CW.mark(it, "page limit", True) and it["cl"]["add"].count("page limit") == 1
      and CW.mark(it, "page limit", False) and "page limit" in it["cl"]["not"] and "page limit" not in it["cl"]["add"])
CW.mark(it, "page limit", True)
mx = os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx")
M = C.Matrix(mx)
base = {k: "" for k in C.FIELD.values()}
M.items = [dict(base, id="L-1", text=text, type="Instruction", decision="Keep", section="L.3", key="k1", loc="1", cl=it["cl"]),
           dict(base, id="L-2", text="Text is 11 point or larger.", type="Format", decision="Keep", section="L.3", key="k2", loc="1")]
M.save()
back = C.Matrix(mx).load()
check("the matrix keeps the marks when saved and opened", back.items[0].get("cl") == it["cl"] and "cl" not in back.items[1],
      back.items[0].get("cl"))
from openpyxl import load_workbook
ws = load_workbook(mx, rich_text=True)["Compliance Matrix"]
col = C.COLUMNS.index("Requirement") + 1
cell = ws.cell(row=2, column=col).value
check("... and the Requirement cell shows them bold", "page limit" in [str(b.text) for b in cell if hasattr(b, "font") and b.font.b],
      cell)
cdir = os.path.join(tmp, "config"); os.makedirs(cdir)
got = CW.add_words(["delivery schedule"], cdir)
check("everywhere: the words join the compliance words list", got == ["delivery schedule"] and "delivery schedule" in CW.load(cdir)["words"])
k = sum(checks)
print(f"COMPLMARK 4180 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
