"""4.7.0: what a field shows, worked out by rules on the fictional sample page (fieldpreview): page numbers in their
formats, SEQ with its restart and reset switches, STYLEREF by level and by style, DOCPROPERTY, dates with pictures, a
TOC's levels and bookmark in words; any other field says Word shows it. A caption recipe reads "Table 2-2"; the Fields
sheet's Sample result is filled from it. Fictional values only."""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fieldpreview as FP
import fieldrecipes as FR
import prodrules as PRL
import standardsbook as SB

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


one = lambda c: FP.one(c)[0]                                                   # noqa: E731
check("PAGE, NUMPAGES, SECTIONPAGES on page 3 of 12", (one("PAGE"), one("NUMPAGES"), one("SECTIONPAGES")) == ("3", "12", "4"))
check("... in their number formats", (one("PAGE \\* roman"), one("PAGE \\* ROMAN"), one("PAGE \\* ALPHABETIC")) == ("iii", "III", "C"))
check("SEQ counts on from the tables already under the heading", one("SEQ Table \\* ARABIC \\s 1") == "2")
check("... \\r resets, \\h hides", one("SEQ Figure \\r 5") == "5" and one("SEQ Figure \\h") == "")
check("STYLEREF by level: the heading's text; with \\s its number", one("STYLEREF 1") == "Technical Approach" and one("STYLEREF 1 \\s") == "2")
check("STYLEREF by style name", one('STYLEREF "Heading 2"') == "Risk Management" and one('STYLEREF "Cover Title"') == "Volume I Technical")
check("... a style with no text says Word's error", one('STYLEREF "No Such Style"').startswith("Error!"))
check("DOCPROPERTY", one("DOCPROPERTY Title") == "Volume I Technical" and one("DOCPROPERTY Nope").startswith("Error!"))
check("DATE with its picture", one('DATE \\@ "MMMM d, yyyy"') == "November 10, 2026" and one('SAVEDATE \\@ "yyyy-MM-dd"') == "2026-11-10"
      and one('CREATEDATE \\@ "d MMM yy"') == "2 Oct 26", one('CREATEDATE \\@ "d MMM yy"'))
toc = one('TOC \\o "1-3" \\h \\z \\b Response')
check("TOC says its levels and its bookmark", "1-3" in toc and "Response" in toc, toc)
check("any other field: Word shows this one", FP.one("HYPERLINK x") == (FP.OTHER, False))
check("a caption recipe reads Table 2-2", FP.recipe(["STYLEREF 1 \\s", "SEQ Table \\* ARABIC \\s 1"], "-", label="Table") == ("Table 2-2", True))
check("an appendix caption reads Table A-1", FP.recipe(["STYLEREF 7 \\s", "SEQ TableApp \\* ARABIC \\s 7"], "-",
                                                       label=FP.label_of(["SEQ TableApp \\s 7"]))[0] == "Table A-1")
p = os.path.join(tempfile.mkdtemp(), "Global Standards.xlsx")
SB.write(p, PRL.load(tempfile.mkdtemp())["company"], FR.starters())
rows = SB.read(p)["sheets"]["Fields"]
cap = next(r for r in rows if r["Name"] == "Table caption")
check("the Fields sheet's Sample result is worked out", cap["Sample result"] == "Table 2-2", cap.get("Sample result"))
print(f"FIELDPREVIEW 470 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
