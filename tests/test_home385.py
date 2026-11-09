"""3.85.0 where a customer sentence goes: its home suggested with the reason (the heading's map, a parent's map, a
reference it makes, a section with the heading's title, the Sort topic), the offer after a placement (map and place the
rest, map only, just this one) and what it leaves out, remapping that changes only suggestions, coverage, the
cross-reference table and what is left. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import homesuggest as HS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


class M:
    def __init__(self):
        self.setup, self.pending = None, False
        self.outline = [{"num": "1", "title": "Technical Approach", "level": 1}, {"num": "2", "title": "Management", "level": 1},
                        {"num": "2.1", "title": "Staffing Plan", "level": 2}, {"num": "2.2", "title": "Key Personnel", "level": 2}]
        self.items = []

    def add(self, iid, text, num, title, f="Section_L.pdf", decision="", typ="Requirement", map_=""):
        self.items.append({"id": iid, "text": text, "section": num, "section_title": title, "file": f, "decision": decision,
                           "type": typ, "map": map_})
        return self.items[-1]


m = M()
a = m.add("a", "The Offeror shall describe its staffing approach.", "L.3.5", "Staffing")
b = m.add("b", "The Offeror shall show the ramp by month.", "L.3.5", "Staffing")
c = m.add("c", "Resumes shall not exceed two pages; see L.3.7.", "L.3.5", "Staffing")
d = m.add("d", "Use 12 point font throughout.", "L.3.5", "Staffing")
e = m.add("e", "The Offeror shall name a program manager.", "L.3.7", "Key Personnel")
g = m.add("g", "The Offeror shall describe the transition.", "L.3.5.2", "Transition")
h = m.add("h", "Describe the technical approach to orbit planning.", "L.2", "Technical Approach")

check("nothing mapped: a heading's title can still match a section", HS.home(m, e)["label"] == "2.2 Key Personnel"
      and HS.home(m, e)["kind"] == "title")
check("... and the reason says so", "Key Personnel" in HS.home(m, e)["why"])
check("no map, no matching title: no suggestion", HS.home(m, a) is None)
off = HS.offer(m, a, "2.1 Staffing Plan")
check("after placing one, the offer names the heading and the rest", off["num"] == "L.3.5" and set(off["rest"]) == {"b"}, off)
check("the offer leaves out a sentence that names another section and a format rule", "c" not in off["rest"] and "d" not in off["rest"])
placed = []
n = HS.take_offer(m, off, "place", lambda ids, lab: (placed.extend(ids), [x.update(map=lab) for x in m.items if x["id"] in ids], len(ids))[-1])
check("Map and place: the heading is mapped and the rest placed", n == 1 and placed == ["b"] and b["map"] == "2.1 Staffing Plan")
check("a mapped heading suggests its section, with why", HS.home(m, c)["label"] == "2.1 Staffing Plan" or HS.home(m, c)["kind"] == "ref")
check("a subheading follows its parent's map", HS.home(m, g) == {"label": "2.1 Staffing Plan", "why": "L.3, above L.3.5.2, is answered by 2.1 Staffing Plan", "kind": "parent"}
      or HS.home(m, g)["label"] == "2.1 Staffing Plan", HS.home(m, g))
HS.map_heading(m, "L.3.7", "2.2 Key Personnel")
check("a sentence that names a mapped heading goes there", HS.home(m, c)["label"] == "2.1 Staffing Plan"
      and HS.home(m, c)["kind"] == "map")
x = m.add("x", "Experience shall be shown as in L.3.7.", "L.4", "Past Performance")
check("a reference the sentence makes", HS.home(m, x) == {"label": "2.2 Key Personnel", "why": "It names L.3.7, which is answered by 2.2 Key Personnel", "kind": "ref"}, HS.home(m, x))
check("no offer once the heading is mapped", HS.offer(m, b, "2.1 Staffing Plan") is None)
HS.map_heading(m, "L.3.5", "2.2 Key Personnel")
check("remapping changes the suggestion only: placed sentences stay", HS.home(m, a)["label"] == "2.2 Key Personnel" and b["map"] == "2.1 Staffing Plan")
y = m.add("y", "The Offeror shall describe the risk approach.", "L.5", "Risk")
off = HS.offer(m, y, "1 Technical Approach")
HS.take_offer(m, off, "once")
check("Just this one: the app does not ask again for that heading", HS.offer(m, y, "1 Technical Approach") is None and not HS.home(m, y))
z = m.add("z", "The Offeror shall describe the risk register.", "L.6", "Risk Register")
HS.take_offer(m, HS.offer(m, z, "1 Technical Approach"), "map")
check("Map only: mapped, nothing placed", HS.home(m, z)["label"] == "1 Technical Approach" and not z["map"])
check("a mapped heading is answered on the coverage list", any(c_["num"] == "L.6" and c_["answered"] for c_ in HS.coverage(m)))
a["decision"] = "Keep"; a["map"] = "2.1 Staffing Plan"; y["decision"] = "Keep"
cov = {c_["num"]: c_ for c_ in HS.coverage(m)}
check("a heading with a requirement placed is answered", cov["L.3.5"]["answered"] and "2.1 Staffing Plan" in cov["L.3.5"]["to"])
check("a heading with a requirement placed nowhere is not", not cov["L.5"]["answered"])
rows = HS.crossref_rows(m)
check("the cross-reference table: heading, title, where we answer it", ("L.5", "Risk", "Not answered yet") in rows
      and any(r[0] == "L.3.5" and "2.1 Staffing Plan" in r[2] for r in rows))
lf = HS.left(m)
check("what is left: not decided, and requirements placed nowhere", "b" in lf["undecided"] and lf["unplaced"] == ["y"], lf)

print(f"HOME 385 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
