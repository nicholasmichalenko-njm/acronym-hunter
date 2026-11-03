"""3.22.0 table widths in inches: a table type's width is set in percent or in inches; in inches the table gets a fixed
width and, when the type lists column widths and the table has that many columns, every column and cell (a merged cell
takes the sum); the template passes its own check; learning a file takes inch widths back as inches, not percent."""
import os, sys, tempfile, zipfile, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodlearn as PL, prodrules as PRL, prodtemplate as PT

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


std = PRL.for_effort(tempfile.mkdtemp())
tt = std["table_types"]["std"]
tt.update(width_unit="in", width_in=6.5, col_widths_in=[2.0, 1.5, 1.5, 1.5])
tj = PT.make(std, os.path.join(tempfile.mkdtemp(), "out"))
doc = zipfile.ZipFile(tj.copy).read("word/document.xml").decode()
tbl = re.search(r"<w:tbl>.*?</w:tbl>", doc, re.S).group(0)
check("in inches: the table gets its fixed width (6.5 in), not a percent", 'w:tblW w:w="9360" w:type="dxa"' in tbl and 'type="pct"' not in tbl.split("</w:tblPr>")[0], tbl[:300])
check("every column takes its inch width", re.findall(r'<w:gridCol w:w="(\d+)"', tbl) == ["2880", "2160", "2160", "2160"])
check("a merged caption cell takes the sum of its columns", 'w:tcW w:w="9360" w:type="dxa"' in tbl and 'w:tblLayout w:type="fixed"' in tbl)
check("the template passes its own check", tj.check.count() == 0 and not [s for s in tj.steps if s.get("refused")],
      ([f["what"][:80] for f in tj.check.findings], [s.get("refused") for s in tj.steps if s.get("refused")]))
back = PL.learn(tj.copy, std).layer(["tables"]).get("table_types", {})
lt = next(iter(back.values()), {})
check("learning takes inch widths back as inches", lt.get("width_unit") == "in" and lt.get("width_in") == 6.5
      and lt.get("col_widths_in") == [2.0, 1.5, 1.5, 1.5], lt)
std2 = PRL.for_effort(tempfile.mkdtemp())
tj2 = PT.make(std2, os.path.join(tempfile.mkdtemp(), "out"))
d2 = zipfile.ZipFile(tj2.copy).read("word/document.xml").decode()
check("in percent (the default): the table stays a percent of the page", 'w:tblW w:w="5000" w:type="pct"' in d2)
print(f"TABLE WIDTHS {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
