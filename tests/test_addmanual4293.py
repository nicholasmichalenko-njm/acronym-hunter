"""4.29.3 (Nicholas 2026-11-13 11:12): a reading fixed to a term the scan already holds must not reset that term. Before,
the term's record was replaced, so a term already added to the effort list went back to undecided on the same page.
Fictional data."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import acrmore as AM, acrpages as AG

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


class S:
    effort = None

    def __init__(self):
        self.results = {"GEO": {"category": "Acronym", "count": 4, "locations": ["Osprey_SOW.pdf (page 3)", "Osprey_SOW.pdf (page 9)"],
                                "definitions": ["Geostationary Earth Orbit"], "selected_definition": "Geostationary Earth Orbit",
                                "effort": "In the list", "status": "Effort list: In the list"}}
        self.manual_items = {}
        self.saved = 0

    def save(self):
        self.saved += 1


s = S()
said = AM.add_manual(s, "GEO", "Acronym", "", document="Osprey_SOW.pdf (page 5, image 1)", to=("results",))
d = s.results["GEO"]
check("a term the scan holds keeps its record: still in the effort list, its definition and its places", d["effort"] == "In the list"
      and d["selected_definition"] == "Geostationary Earth Orbit" and d["count"] == 4 and AG.state_of(d) == "list", d)
check("... the new place is added to it, once", d["locations"] == ["Osprey_SOW.pdf (page 3)", "Osprey_SOW.pdf (page 9)", "Osprey_SOW.pdf (page 5, image 1)"]
      and AM.add_manual(s, "GEO", document="Osprey_SOW.pdf (page 5, image 1)") and len(s.results["GEO"]["locations"]) == 3)
check("... it is not turned into a term added by hand, and the words say what happened", "GEO" not in s.manual_items and not d.get("manual")
      and "already found by the scan" in said, said)
AM.add_manual(s, "LEO", "Acronym", "Low Earth Orbit", document="Osprey_SOW.pdf (page 2)")
check("a term the scan never found is listed as added by hand, as before", s.results["LEO"]["manual"] and s.manual_items["LEO"]["locations"] == ["Osprey_SOW.pdf (page 2)"]
      and AG.state_of(s.results["LEO"]) == "decide")
s.results["LEO"]["effort"] = "In the list"
AM.add_manual(s, "LEO", "Acronym", "", document="Osprey_SOW.pdf (page 7)")
check("a term added by hand and then added again elsewhere keeps its place in the list and both places", s.results["LEO"]["effort"] == "In the list"
      and s.results["LEO"]["locations"] == ["Osprey_SOW.pdf (page 2)", "Osprey_SOW.pdf (page 7)"], s.results["LEO"])
n = sum(checks)
print(f"ADD MANUAL 4293 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
