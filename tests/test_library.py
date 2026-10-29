"""2.83.0 the document library, no window: the four categories plus the person's own; a document's category, folder,
tags (every folder name is a tag), and role (Builds the matrix, Context, Reference only, Not needed) suggested from its
category and type and confirmed with who, when and why; the customer documents are still what requirements, Compare and
Read RFP see; search finds names, tags and text across every document; a copy kept inside the effort is found again
wherever the effort goes, and a missing original is reported; an index from before 2.83 still opens as customer
documents."""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import docversions as DV
import workspace as W

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
data = os.path.join(tmp, "data"); docs = os.path.join(data, "documents"); os.makedirs(docs)
src = os.path.join(tmp, "in"); os.makedirs(src)


def f(name, body=b"x"):
    p = os.path.join(src, name); open(p, "wb").write(body + name.encode()); return p


S = lambda *xs: [{"x": x, "l": "1", "s": "", "t": ""} for x in xs]
# an index from before 2.83
W.write_json(os.path.join(docs, "index.json"), {"v": 1, "docs": [{"id": "old1", "name": "Section L", "initial": "L", "type": "Section L",
                                                                  "versions": [{"id": "v0", "label": "Original", "file": "L.docx", "path": "C:/x/L.docx"}]}]})
W.write_json(os.path.join(docs, "v0.json"), S("The Offeror shall describe the thermal design."))
lib = DV.Library(docs).load()
check("an index from before 2.83 opens as customer documents", [d["id"] for d in lib.docs] == ["old1"] and lib.role_of(lib.docs[0]) == "matrix")
check("the four categories", [k for k, _n in lib.categories()] == ["customer", "bidders", "qa", "ours"])
key = lib.add_category("Competitor intel")
check("plus the person's own, kept", key and DV.Library(docs).load().category_name(key) == "Competitor intel" and lib.add_category("competitor intel") == key)
# adding across categories
d1, v1 = lib.add(f("SOW.pdf"), S("The contractor shall deliver a monthly report."), doc_name="SOW", initial="S", dtype="SOW")
d2, _ = lib.add(f("J1 ICD.pdf"), S("Radiator panels shall reject 450 W."), doc_name="Attachment J-1", initial="J1", dtype="Attachment")
d3, _ = lib.add(f("MIL-STD-1540E.pdf"), S("Thermal vacuum testing per this standard."), category="bidders", folder="Standards/Test",
                tags=["Thermal"], initial="M", dtype="SOW")
d4, _ = lib.add(f("QA R1.xlsx"), S("Q: Is the page limit firm? A: Yes, seven pages."), category="qa", folder="Round 1")
check("roles suggested from category and type", [lib.role_of(d) for d in (d1, d2, d3, d4)] == ["matrix", "context", "reference", "context"])
check("only customer documents get an initial and a type", d3["initial"] == "" and d3["type"] == "" and d1["initial"] == "S")
check("every folder name is a tag, plus the person's", d3["tags"] == ["Thermal", "Standards", "Test"], d3["tags"])
check("the customer documents are what requirements, Compare and Read RFP see", [d["name"] for d in lib.docs] == ["Section L", "SOW", "Attachment J-1"])
check("folders by category, with their parents", lib.folders("bidders") == ["Standards", "Standards/Test"])
check("a suggested role is undecided until someone confirms it", d3 in lib.undecided() and lib.set_role(d3["id"], "context", "Test approach source", who="A. Lee")
      and d3 not in DV.Library(docs).load().undecided())
L2 = DV.Library(docs).load(); dd = L2.doc(d3["id"])
check("the role keeps who, when and why", dd["role"] == "context" and dd["role_by"]["who"] == "A. Lee" and dd["role_by"]["why"] == "Test approach source"
      and dd["role_by"]["when"])
check("tags edited", lib.set_tags(d4["id"], ["Schedule", "schedule", " Page limits "]) and lib.doc(d4["id"])["tags"] == ["Schedule", "Page limits"])
check("moving to another category", lib.set_category(d4["id"], "customer") and d4 in lib.docs and lib.set_category(d4["id"], "qa", "Round 1") and d4 not in lib.docs)
check("duplicates are found in every category", lib.find_sha(d3["versions"][0]["sha256"])[0] is d3)
# search
r = lib.search("thermal")
check("search: names and tags first, then text", [d["name"] for d, _h in r][:1] == ["MIL-STD-1540E"] and any(d["id"] == "old1" for d, _h in r), [d["name"] for d, _h in r])
r = lib.search("page limit firm")
check("search: every word in one sentence, with the sentence", len(r) == 1 and r[0][0] is d4 and "seven pages" in r[0][1][0][1])
check("search: nothing for nothing", lib.search("") == [] and lib.search("zebra") == [])
# copies kept inside the effort
inside = os.path.join(data, "library", "bidders", "Standards"); os.makedirs(inside)
p = os.path.join(inside, "NASA-STD-5001.pdf"); open(p, "wb").write(b"nasa")
d5, v5 = lib.add(p, S("Structural design factors."), category="bidders", folder="Standards")
check("a copy inside the effort is kept relative to it", v5["rel"] == "library/bidders/Standards/NASA-STD-5001.pdf" and lib.has_original(v5))
moved = os.path.join(tmp, "elsewhere", "data"); shutil.copytree(data, moved)
L3 = DV.Library(os.path.join(moved, "documents")).load()
v = L3.doc(d5["id"])["versions"][0]
check("and found again where the effort went", os.path.normcase(L3.path_of(v)).startswith(os.path.normcase(moved)) and L3.has_original(v))
os.remove(L3.path_of(v))
check("a missing original is reported, its text still searchable", not L3.has_original(v) and L3.search("structural")[0][0]["id"] == d5["id"])
c = lib.counts_by_category()
check("counts by category", c["customer"] == 3 and c["bidders"] == 2 and c["qa"] == 1 and c[key] == 0, c)
n = sum(checks)
print(f"LIBRARY PASS ({n}/{len(checks)})" if n == len(checks) else f"LIBRARY FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
