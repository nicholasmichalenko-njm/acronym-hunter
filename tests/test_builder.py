"""3.30.0 the Structure Builder's rules: response elements (built-ins, the team's changes and its own, kits by effort
type), added to a volume in order in their parts; kinds of section (unnumbered, divider, placeholder, element) that take
no number; Heading 1 to 9 set directly; a section that starts a Word section; drag and drop before, after or into;
library items placed in a section; all of it kept in the matrix file."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import compliance as C, outline_ops as O, responseelements as RE, structparts as SP, setupdoc as SD

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg")
# ---------------------------------------------------------------- the elements
d = RE.load(cfg)
names = [e["name"] for e in d["elements"]]
check("the built-in elements, in part order", names[:3] == ["Cover", "Title page", "Cover letter"] and "List of Appendices" in names
      and "Units of Measurement" in names and "Appendices" in names and names[-1] == "Back cover", names)
check("the team's default kit", RE.kit(d) == ["cover", "toc", "lof", "lot", "acr"])
RE.get(d, "acr")["pages"] = 3
e = RE.add(d, "Past performance summary", part="front", source="quickpart", pages=2, lib="PP summary block")
RE.set_kit(d, "rfi", ["toc"])
RE.move(d, "uom", -1)
RE.save(cfg, d)
d2 = RE.load(cfg)
check("saved: only the changes, the team's own element and kits", RE.get(d2, "acr")["pages"] == 3 and RE.get(d2, e["id"])["lib"] == "PP summary block"
      and RE.kit(d2, "rfi") == ["toc"] and RE.kit(d2, "proposal") == RE.kit(d2))
fr = [x["id"] for x in d2["elements"] if x["part"] == "front"]
check("Up moves an element earlier in its part", fr.index("uom") < fr.index("acr"), fr)
check("a built-in cannot be taken out; the team's own can", not RE.remove(d2, "toc") and RE.remove(d2, e["id"]))
check("back to the built-ins", RE.get(RE.reset(cfg), "acr")["pages"] == 2)

# ---------------------------------------------------------------- the structure
M = C.Matrix(os.path.join(tmp, "m.xlsx"), "m")
vol = O.add_volume(M, "Technical")
t1 = O.add(M, "Technical Approach", parent=vol)
O.add(M, "Systems Engineering", parent=t1)
O.add(M, "Management", after=t1)
check("a volume made here, numbered by place", O.labels(M) == ["Volume I Technical", "1 Technical Approach", "1.1 Systems Engineering", "2 Management"], O.labels(M))
d = RE.load(cfg)
added, removed = RE.apply_kit(M, d, ["acr", "toc", "lot", "appendices"], "Volume I Technical")
labs = O.labels(M)
check("elements go into the volume, each in its part", labs[1] == "Table of Contents" and labs[-1] == "Appendices", labs)
fr = [C.outline_label(o) for o in M.outline if SP.part_of(o) == "front"]
check("... front matter in the team's order (TOC, List of Tables, Acronyms)", fr == ["Table of Contents", "List of Tables", "Acronyms and Abbreviations"], fr)
check("elements carry no number", all(not o["num"] for o in M.outline if o.get("element")))
check("the response keeps its numbers", "1 Technical Approach" in labs and "1.1 Systems Engineering" in labs)
RE.apply_kit(M, d, ["toc", "lot", "appendices"], "Volume I Technical")
check("unticked: the element comes out", "Acronyms and Abbreviations" not in O.labels(M))
check("in the volume: the elements by id", set(RE.in_volume(M, "Volume I Technical")) == {"toc", "lot", "appendices"})
# kinds and levels
tag = RE.tag(M.outline[O.index_of(M, "1.1 Systems Engineering")], O.heading_level(M, "1.1 Systems Engineering"))
check("tags: H2 for a subsection", tag == "H2", tag)
new = O.set_kind(M, "1 Technical Approach", "unnumbered")
check("an unnumbered heading has no number; the next takes its place", new == "Technical Approach" and "1 Management" in O.labels(M), O.labels(M))
new = O.set_kind(M, "Technical Approach", "")
check("numbered again", new == "1 Technical Approach" and "2 Management" in O.labels(M), O.labels(M))
new = O.set_level(M, "2 Management", 2)
check("Heading 2: it goes under the section before it", new == "1.2 Management", O.labels(M))
new = O.set_level(M, "1.2 Management", 4)
check("... at most one level below the section before it", new == "1.1.1 Management" or O.heading_level(M, new) <= 3, (new, O.labels(M)))
new = O.set_level(M, new, 1)
check("Heading 1 again", O.heading_level(M, new) == 1, new)
lab = "1.1 Systems Engineering"
for n in range(2, 11):
    lab = O.add(M, f"Level {n + 1}", parent=lab)
check("subheadings go as deep as needed (Heading 11 here)", O.heading_level(M, lab) == 11 and lab.count(".") == 10, lab)
ta = next(l for l in O.labels(M) if l.endswith(" Technical Approach"))
O.set_break(M, ta, "landscape")
check("a section can start a Word section, landscape", M.outline[O.index_of(M, ta)]["brk"] == {"orient": "landscape"}
      and RE.tag(M.outline[O.index_of(M, ta)], O.heading_level(M, ta)) == "H1 SEC", (ta, O.labels(M)))
# drag and drop
mg = next(l for l in O.labels(M) if l.endswith(" Management"))
new = O.move_to(M, mg, ta, "before")
check("drop before: Management first, renumbered", new == "1 Management" and "2 Technical Approach" in O.labels(M), O.labels(M))
new = O.move_to(M, "1 Management", "2 Technical Approach", "into")
check("drop into: Management under Technical Approach, last", new.endswith(" Management") and O.heading_level(M, new) == 2, new)
check("not into itself", O.move_to(M, "1 Technical Approach", new, "into") is None)
# library items
tech = next(l for l in O.labels(M) if l.endswith("Technical Approach"))
O.place_lib(M, tech, {"id": "abc", "kind": "quickpart", "name": "Org chart block"})
O.place_lib(M, tech, {"id": "def", "kind": "quickpart", "name": "Company overview"}, where="after")
O.move_lib(M, tech, 1, -1)
check("library items placed in a section, in order", [x["name"] for x in O.lib_items(M, tech)] == ["Company overview", "Org chart block"])
# kept in the file
M.save()
M2 = C.Matrix(M.path, "m"); M2.load()
o2 = M2.outline[O.index_of(M2, tech)]
check("kept in the matrix file: Word section and library items", o2.get("brk") == {"orient": "landscape"} and len(o2.get("lib", [])) == 2)
check("... and the elements", any(o.get("element") == "toc" and o.get("kind") == "element" for o in M2.outline))
import structure_ops as STR
STR.apply(M2, C.outline_text(M2.outline))
check("Apply from the text keeps them", any(o.get("element") == "toc" for o in M2.outline) and M2.outline[O.index_of(M2, tech)].get("lib"))
n = sum(checks)
print(f"BUILDER PASS ({n}/{len(checks)})" if n == len(checks) else f"BUILDER FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
