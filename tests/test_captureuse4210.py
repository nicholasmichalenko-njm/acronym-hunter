"""4.21.0: captured means delivered. Every piece type says where it goes, each use names a page that exists and the code
that reads it (the proof is still in the file). A required heading's page limit reaches the page budget; Final Check
reports the required structure. Fictional (Kestrel)."""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
import captureuse as CU, compliance as C, pagebudget as PB, shredtypes as ST, structfrom as SF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


check("every piece type says where it goes", set(CU.TYPES) == set(ST.KEYS), set(ST.KEYS) ^ set(CU.TYPES))
check("... in a sentence, with no retired word", all(say and "Review" not in say and "Library" not in say for say, _u in CU.TYPES.values()))
from skqt.pagetitles import TITLES
check("every page named is a page", all(p in TITLES for p in CU.pages()), [p for p in CU.pages() if p not in TITLES])
gone = []
for k, (_say, uses) in list(CU.TYPES.items()) + list(CU.MARKS.items()):
    for _page, f, words in uses:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or words not in open(p, encoding="utf-8").read():
            gone.append((k, f, words))
check("the code that reads each one is still there", not gone, gone)
check("only Information and Not applicable go nowhere", sorted(k for k, (_s, u) in CU.TYPES.items() if not u) == ["information", "not_applicable"])
check("the pane's line: one type", CU.line(["structure"]).startswith("Goes to: Matrix & Outline > Outline"))
check("... two types, each named", CU.line(["requirement", "date"], {"requirement": "Requirement", "date": "Date"}).startswith("Goes to: Requirement: ")
      and "; Date: Shred > Rules & Dates" in CU.line(["requirement", "date"], {"requirement": "Requirement", "date": "Date"}))
check("... no type, no line", CU.line([]) == "")
# a required heading's page limit reaches the page budget
tmp = tempfile.mkdtemp()
base = {k: "" for k in C.FIELD.values()}
M = C.Matrix(os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx"))
M.items = [dict(base, id="L-2", key="L-2", loc="1", compound=False, lead="Volume II shall be organized as follows:",
                text="(1) Management Approach (not to exceed 15 pages); (2) Key Personnel; (3) Transition Plan.",
                section="L.3.2", section_title="Management Volume", page="13", file="Section L.pdf")]
ST.set_type(M.items, "structure")
ents = SF.put(M, SF.read(M))
o = next(x for x in M.outline if x.get("title") == "Management Approach")
lab = C.outline_label(o)
check("Put in our outline: the limit is the section's pages, set by the customer", PB.pages(M, lab) == 15.0 and PB.source(M, lab) == "rfp",
      (PB.pages(M, lab), PB.source(M, lab)))
other = C.outline_label(next(x for x in M.outline if x.get("title") == "Key Personnel"))
check("... a heading with no limit gets none", PB.pages(M, other) is None)
PB.set_pages(M, lab, 12, "team")
check("... pages the team typed stay", SF.deliver_limits(M) == [] and PB.pages(M, lab) == 12.0)
M.save()
back = C.Matrix(M.path).load()
check("... kept when the matrix is saved and opened", PB.pages(back, lab) == 12.0)
# Final Check reports the required structure
import finalcheck as FC
rep = FC.run({"name": "Volume II"}, {"matrix": M})
ln = [x for x in rep["lines"] if x["check"] == "The required structure"]
check("Final Check: the required structure, kept", len(ln) == 1 and ln[0]["status"] == FC.PASS, ln)
M.outline[1]["title"] = "Our People"
ln = [x for x in FC.run({"name": "Volume II"}, {"matrix": M})["lines"] if x["check"] == "The required structure"]
check("... a renamed required heading fails it and says which", len(ln) == 1 and ln[0]["status"] == FC.FAIL and "Management Approach is now Our People" in ln[0]["detail"], ln)
M2 = C.Matrix(os.path.join(tmp, "two.xlsx"))
check("... no required structure, no line", not [x for x in FC.run({"name": "V"}, {"matrix": M2})["lines"] if x["check"] == "The required structure"])
k = sum(checks)
print(f"CAPTUREUSE 4210 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
