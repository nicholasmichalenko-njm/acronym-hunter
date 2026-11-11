"""4.13.0 and 4.14.0: Redline's copy against fictional fixtures (claude/stationkeeper-pdf-fidelity-plan-4.13.html). Tables come from
the borders each page draws: merged cells across and down, a 2x2 block, empty cells, wrapped cells, rules only, shading,
a landscape page, cell spacing, rotated headers, lists in cells and note marks come out cell for cell; every copy holds
every word of its PDF; each page keeps its size and orientation; and the copy beats the 4.12.0 way on every fixture.
4.14.0: a table across three pages is one table with its header row once; a table in a cell and a table with no borders
come from the PDF's tags.
PDFs made by LibreOffice here (pdf_lo) and by Word on the build PC (pdf_word_tagged, pdf_word_untagged) when present.
Fictional content (Kestrel)."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["AH_TEST"] = "1"
import tempfile
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "data"))
import fidelity as F

checks = []
# 4.14.0: tags give borderless and nested tables where the PDF keeps them; 4.15.0: and with no tags
LATER = {}


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


for kind in ("pdf_lo", "pdf_word_tagged", "pdf_word_untagged"):
    folder = os.path.join(F.FIX, kind)
    if not os.path.isdir(folder):
        continue
    rows = F.score(folder)
    print(F.report(rows))
    now = [r for r in rows if r["fixture"] not in LATER.get(kind, ())]
    check(f"{kind}: every table cell for cell" + (" (but tables with no borders and no tags)" if kind in LATER else ""), all(r["exact"] == r["tables"] for r in now),
          [r["fixture"] for r in now if r["exact"] < r["tables"]])
    check(f"{kind}: every copy holds every word of its PDF", all(r["word_diffs"] == 0 for r in rows),
          [(r["fixture"], r["word_diffs"]) for r in rows if r["word_diffs"]])
    check(f"{kind}: every page keeps its size and orientation", all(r["pages_ok"] for r in rows),
          [r["fixture"] for r in rows if not r["pages_ok"]])
    check(f"{kind}: better than the 4.12.0 way", sum(r["exact"] for r in rows) > sum(r["baseline"] for r in rows)
          and all(r["exact"] >= r["baseline"] for r in rows))

n = sum(checks)
print(f"FIDELITY 4130 {'PASS' if n == len(checks) and checks else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if checks and n == len(checks) else 1)
