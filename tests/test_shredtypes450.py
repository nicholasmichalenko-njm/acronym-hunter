"""4.5.0: several types on one piece (shredtypes): toggle on and off, Not applicable clears the rest and any other type
clears it, counts per tab, placed_any, and a single key reads as before. Fictional pieces."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import shredtypes as ST

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


a, b = {"id": "a"}, {"id": "b", "piece": "rule"}
on, _ = ST.toggle([a], "requirement")
check("a click puts a type on", on and a["piece"] == "requirement" and ST.types_of(a) == ["requirement"])
ST.toggle([a], "date")
check("a second type joins the first", a["piece"] == "requirement;date" and ST.type_of(a) == "requirement"
      and ST.tabs_of(a) == ["requirements", "rules"])
on, _ = ST.toggle([a], "requirement")
check("a second click takes it off", on is False and ST.types_of(a) == ["date"])
ST.toggle([a], "not_applicable")
check("Not applicable clears the others", ST.types_of(a) == ["not_applicable"])
ST.toggle([a], "rule")
check("... and any other type clears Not applicable", ST.types_of(a) == ["rule"])
on, _ = ST.toggle([a, b], "rule")
check("on several pieces: when all have it, it comes off all", on is False and ST.types_of(a) == [] and b["piece"] == "")
c = {"id": "c", "piece": "date"}
on, _ = ST.toggle([b, c], "date")
check("... when some lack it, it goes on all", on and ST.types_of(b) == ["date"] and ST.types_of(c) == ["date"])
by_tab, by_type = ST.counts([{"piece": "requirement;date"}, {"piece": "evaluation"}, {}])
check("a piece counts once in each tab its types reach", by_tab["requirements"]["total"] == 2 and by_tab["rules"]["total"] == 1
      and by_tab["evaluation"]["total"] == 1 and by_tab["requirements"]["unsorted"] == 1, by_tab)
check("... and once for each type", by_type["requirement"] == 1 and by_type["date"] == 1 and by_type["evaluation"] == 1)
check("Place offers a piece when any type is placed", ST.placed_any(["date", "requirement"]) and not ST.placed_any(["date", "rule"]))
check("a single key from before 4.5.0 reads as before", ST.types_of({"piece": "deliverable"}) == ["deliverable"]
      and ST.type_of({"decision": "Keep", "lm": "L"}) == "instruction")
check("set_types keeps one Not applicable", ST.set_types([a], ["rule", "not_applicable"]) == 1 and a["piece"] == "not_applicable")
n = sum(checks)
print(f"TEST SHREDTYPES 450 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
