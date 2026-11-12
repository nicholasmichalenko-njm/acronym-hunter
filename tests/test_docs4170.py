"""4.17.0: replace a document's file, delete into the Trash, headings with levels (claude/stationkeeper-documents-replace-
delete-plan-4.17.md). Without a window: a PDF edited where it sits and added again is offered as the same document
(replace), not a new version; replace keeps the version, moves the old file to the Trash and marks it to be read again;
the shred's merge keeps the pieces that stayed with their decisions, carries a changed sentence's decisions, adds new
pieces and moves the gone ones to the Trash; delete moves a document or a version (and its pieces) to the Trash and
restore puts everything back; a file another version still uses stays; Empty removes for good; a heading at a level
gives the pieces below it its reference, an unnumbered subheading reads under its parent. Fictional (Kestrel)."""
import copy, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
import docintake as DI, docremove as DR, docreplace as RP, doctrash as T, docversions as DV, headinglevels as HL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def full(it):
    for k, val in (("type", "Requirement"), ("header", ""), ("section", "L.1"), ("section_title", ""), ("decision", ""),
                   ("owner", ""), ("key", ""), ("lead", ""), ("context_for", ""), ("links", ""), ("map", ""), ("text", "")):
        it.setdefault(k, val)
    return it


class M:
    def __init__(self, items):
        items = [full(it) for it in items]
        self.items, self.sources, self.headings, self.logs, self.pending = items, [], [], [], False

    def log(self, *a):
        self.logs.append(a)


tmp = tempfile.mkdtemp()
data = os.path.join(tmp, "data"); os.makedirs(os.path.join(data, "documents"))
cd = os.path.join(tmp, "Customer documents"); os.makedirs(cd)
lib = DV.Library(os.path.join(data, "documents")).load()
v1 = [{"x": "L.1 General Instructions."}, {"x": "The Contractor shall deliver the Kestrel test plan within 30 days."},
      {"x": "The schedule is fixed."}, {"x": "Reports are due monthly."}]
v2 = [{"x": "L.1 General Instructions."}, {"x": "The Contractor shall deliver the Kestrel test plan within 30 days."},
      {"x": "The schedule is fixed by the contracting officer."}, {"x": "Late proposals are not accepted."}]
reads = {}
reader = lambda p: reads[p]                                                       # noqa: E731
src = os.path.join(tmp, "Section L.pdf")
open(src, "wb").write(b"%PDF-1.4 version one")
reads[os.path.join(cd, "Section L.pdf")] = v1; reads[src] = v1
plan = DI.plan(lib, [src], reader=reader)
made = DI.apply(lib, plan, customer_dir=cd)
d, v = made[0]
inside = lib.path_of(v)
check("a new document is added as before", plan[0]["choice"] == "new" and os.path.isfile(inside))
open(inside, "wb").write(b"%PDF-1.4 version two, edited where it sits")
reads[inside] = v2
check("an edit where it sits is noticed", [x[0]["id"] for x in RP.changed_on_disk(lib)] == [d["id"]])
plan = DI.plan(lib, [inside], reader=reader, edited="replace")
watch = DI.plan(lib, [inside], reader=reader)
check("... from the watch (the customer's newer file saved over it) it is the next version", watch[0]["choice"] == "version" and watch[0].get("replace_of") == d["id"])
check("added again, it is offered as the same document, its file replaced", plan[0]["choice"] == "replace"
      and plan[0]["doc"] == d["id"], (plan[0]["choice"], plan[0]["doc"]))
items = [{"id": "L-1", "file": "Section L.pdf", "text": "The Contractor shall deliver the Kestrel test plan within 30 days.",
          "decision": "Keep", "owner": "Pat", "page": 1, "section": "L.1", "section_title": ""},
         {"id": "L-2", "file": "Section L.pdf", "text": "The schedule is fixed.", "decision": "Keep", "page": 1, "section": "L.1", "section_title": ""},
         {"id": "L-3", "file": "Section L.pdf", "text": "Reports are due monthly.", "decision": "Keep", "page": 1, "section": "L.1", "section_title": ""}]
mx = M(copy.deepcopy(items))
made = DI.apply(lib, plan, customer_dir=cd)
lib = DV.Library(os.path.join(data, "documents")).load()
d = lib.doc(d["id"])
check("... the same version: no Amendment 1, its fingerprint the new file's, marked to read again",
      len(d["versions"]) == 1 and d["versions"][0]["sha256"] == DV.sha256(inside) and d["versions"][0].get("reread")
      and d["versions"][0]["sentences"] == 4, [(x["label"], x.get("reread")) for x in d["versions"]])
check("... and it is no longer reported edited", not RP.changed_on_disk(lib))
news = [full({"file": "Section L.pdf", "text": x["x"], "page": 1, "key": f"k{k}", "section": "L.1", "section_title": ""}) for k, x in enumerate(v2[1:])]
got = RP.merge(mx, "Section L.pdf", news, [], [["Section L.pdf", "", "", inside]], ws=data)
ids = {it["id"]: it for it in mx.items}
check("the shred: what stayed keeps its piece and decisions", got["kept"] == 1 and ids["L-1"]["owner"] == "Pat")
check("... a changed sentence keeps its piece, its decision and gets the new words", got["changed"] == 1
      and ids["L-2"]["text"] == "The schedule is fixed by the contracting officer." and ids["L-2"]["decision"] == "Keep"
      and ids["L-2"]["new"] == RP.MARK)
check("... a new sentence is a new piece", got["added"] == 1 and any(it["text"].startswith("Late proposals") and it["id"] for it in mx.items))
check("... a piece whose sentence is gone goes to the Trash", got["gone"] == 1 and "L-3" not in ids
      and any(e["kind"] == "pieces" for e in T.entries(data)))
# a second file replaced from elsewhere: the old file is kept in the Trash and comes back on restore
other = os.path.join(tmp, "Section L edited.pdf"); open(other, "wb").write(b"%PDF-1.4 three"); reads[inside] = v1
res = RP.replace(data, lib, d["id"], new_path=other, reader=reader)
kept = [e for e in T.entries(data) if e["kind"] == "replaced"][0]
check("Replace the file...: the new file takes the old one's place and name; the old one is in the Trash",
      open(inside, "rb").read() == b"%PDF-1.4 three" and any(r["kept"] for r in kept["files"]) and res["version"]["label"] == "Original")
RP.restore(data, lib, None, kept["id"])
check("... Restore puts the old file back", open(inside, "rb").read() == b"%PDF-1.4 version two, edited where it sits")
# delete a version, then the document; restore each
reads[os.path.join(cd, "Section L amendment.pdf")] = v2
amd = os.path.join(tmp, "Section L amendment.pdf"); open(amd, "wb").write(b"%PDF-1.4 amendment"); reads[amd] = v2 + [{"x": "One more."}]
lib = DV.Library(os.path.join(data, "documents")).load()
d, va = lib.add(amd, reads[amd], doc_id=d["id"])
mx = M([{"id": "L-1", "file": "Section L.pdf", "text": "a", "decision": "Keep", "section": "L.1"},
        {"id": "L-9", "file": "Section L amendment.pdf", "text": "b", "decision": "Keep", "section": "L.1"}])
info = DR.what_goes(lib, mx, d["id"], va["id"])
check("what a version's delete takes is said first", info["versions"] == ["Amendment 1"] and info["pieces"] == 1
      and info["decided"] == 1 and not info["whole"] and "Trash" in DR.question(info), info)
eid = DR.delete(data, lib, mx, d["id"], va["id"])
lib = DV.Library(os.path.join(data, "documents")).load()
check("... the version, its file and its pieces go to the Trash; the rest stays", len(lib.doc(d["id"])["versions"]) == 1
      and not os.path.isfile(amd) and [it["id"] for it in mx.items] == ["L-1"] and os.path.isfile(inside))
DR.restore(data, lib, mx, eid)
lib = DV.Library(os.path.join(data, "documents")).load()
check("... Restore puts the version, its file and its pieces back", len(lib.doc(d["id"])["versions"]) == 2
      and os.path.isfile(amd) and {it["id"] for it in mx.items} == {"L-1", "L-9"})
eid = DR.delete(data, lib, mx, d["id"])
lib = DV.Library(os.path.join(data, "documents")).load()
check("delete the document: its record, files, text and pieces go to the Trash", lib.doc(d["id"]) is None and not mx.items
      and not os.path.isfile(inside) and T.entry(data, eid)["kind"] == "document")
DR.restore(data, lib, mx, eid)
lib = DV.Library(os.path.join(data, "documents")).load()
check("... Restore puts all of it back, with its kept text", lib.doc(d["id"]) is not None and len(mx.items) == 2
      and os.path.isfile(inside) and lib.text(lib.doc(d["id"])["versions"][0]))
# two versions sharing one file (an edit added as a new version before 4.17.0): the shared file stays
lib.doc(d["id"])["versions"][1]["path"] = inside; lib.doc(d["id"])["versions"][1]["file"] = "Section L.pdf"
info = DR.what_goes(lib, mx, d["id"], lib.doc(d["id"])["versions"][1]["id"])
check("a version sharing its file with another leaves the file and its pieces", not info["files"] and not info["pieces"], info)
n = T.empty(data)
check("Empty the Trash removes every entry for good", n >= 1 and not T.entries(data))
# headings with levels
its = [{"id": "1", "file": "f", "text": "L.3 Page Limits and Format", "type": "", "header": ""},
       {"id": "2", "file": "f", "text": "Pages are 8.5 by 11 inches.", "section": "", "section_title": ""},
       {"id": "3", "file": "f", "text": "Technical Approach", "type": "", "header": ""},
       {"id": "4", "file": "f", "text": "The approach shall not exceed 25 pages.", "section": "", "section_title": ""},
       {"id": "5", "file": "f", "text": "Text is 11 point.", "section": "", "section_title": ""}]
got = HL.mark(its, "1", HL.level_of(its[0]))
check("a numbered heading: its level from its number, the pieces below take its reference", HL.level_of(its[0]) == 1
      and its[1]["section"] == "L.3" and its[1]["section_title"] == "Page Limits and Format" and got == ["2", "3", "4", "5"])
HL.mark(its, "3", 2)
check("an unnumbered subheading reads under its parent, and so do the pieces below it",
      HL.found_under(its[3]) == "L.3 Page Limits and Format > Technical Approach" and its[1]["section_title"] == "Page Limits and Format",
      HL.found_under(its[3]))
import compliance as C
mxp = os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx")
MM = C.Matrix(mxp); MM.items = [full(dict(x, key=f"k{x['id']}", loc="1")) for x in its]; MM.save()
back = C.Matrix(mxp).load()
h3 = next(x for x in back.items if x["id"] == "3")
check("the matrix keeps a heading's level and what it reads under", h3.get("hlevel") == 2 and h3.get("base") == ["L.3", "Page Limits and Format"]
      and next(x for x in back.items if x["id"] == "4")["section_title"] == "Page Limits and Format > Technical Approach",
      (h3.get("hlevel"), h3.get("base")))
HL.unmark(its, "3")
check("Not a heading: it is a piece again, and the pieces below go back under L.3", its[2]["type"] == "" and not its[2].get("hlevel")
      and HL.found_under(its[3]) == "L.3 Page Limits and Format")
k = sum(checks)
print(f"DOCS 4170 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
