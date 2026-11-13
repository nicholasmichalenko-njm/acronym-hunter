"""4.29.3 (Nicholas 2026-11-13 11:12): finds combined into one term on one page are part of it wherever the same finds
sit side by side, so the duplicates are not left to decide again. Fictional data."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import acrplace as AP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


class S:
    results = {"TT": {"locations": ["Osprey_SOW.pdf (page 3, para 2)", "Osprey_SOW.pdf (page 9, para 1)", "Osprey_L.pdf (page 2, para 4)"]},
               "C": {"locations": ["Osprey_SOW.pdf (page 3, para 2)", "Osprey_SOW.pdf (page 9, para 5)", "Osprey_L.pdf (page 7, para 1)"]},
               "RF": {"locations": ["Osprey_SOW.pdf (page 4, para 1)"]}}


got = AP.together(S, ["TT", "C"])
check("both parts on the same page: that page counts, in every document", sorted(got) == ["C", "TT"]
      and got["TT"] == ["Osprey_SOW.pdf (page 3, para 2)", "Osprey_SOW.pdf (page 9, para 1)"]
      and got["C"] == ["Osprey_SOW.pdf (page 3, para 2)", "Osprey_SOW.pdf (page 9, para 5)"], got)
check("a page with only one of the parts is left alone: that find still shows on its own", "Osprey_L.pdf (page 2, para 4)" not in got["TT"]
      and "Osprey_L.pdf (page 7, para 1)" not in got["C"])
check("parts that never share a page: nothing", AP.together(S, ["TT", "RF"]) == {})
check("a part the scan does not hold: nothing to join", AP.together(S, ["ZZ"]) == {} and AP.together(S, []) == {})
n = sum(checks)
print(f"TOGETHER 4293 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
