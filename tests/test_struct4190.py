"""4.19.0: our response structure, two doors (claude/stationkeeper-response-structure-plan-4.19.html). Door 1: pieces
typed Structure read into headings (volumes H1, an organized-as-follows list under its volume, a heading at its own
level, page limits), numbered, put in our outline with Required by kept when saved; a renamed, removed or moved required
heading is found. Door 2: draft headings from the customer's headings, the SOW or PWS headings, or blank; Use it as our
structure takes Draft off. The List's tree follows the customer's references. Fictional (Kestrel)."""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
import compliance as C, shredtypes as ST, structfrom as SF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


tmp = tempfile.mkdtemp()
base = {k: "" for k in C.FIELD.values()}


def item(**k):
    d = dict(base); d.update(k); d.setdefault("key", k.get("id", "")); d.setdefault("loc", "1"); d["compound"] = False
    return d


M = C.Matrix(os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx"))
M.items = [item(id="L-1", text="The Offeror shall submit the proposal in three volumes: Volume I - Technical, Volume II - Management, "
                "and Volume III - Price.", section="L.3", section_title="Proposal Organization", page="12", file="Section L.pdf"),
           item(id="L-2", lead="Volume II shall be organized as follows:", text="(1) Management Approach (not to exceed 15 pages); "
                "(2) Key Personnel; (3) Transition Plan.", section="L.3.2", section_title="Management Volume", page="13", file="Section L.pdf"),
           item(id="L-3", text="The Offeror shall describe its approach to the Kestrel ground station.", section="L.4",
                section_title="Technical", page="14", file="Section L.pdf", decision="Keep"),
           item(id="C-1", text="The Contractor shall operate the ground station.", section="C.2.1", section_title="Operations",
                page="3", file="Kestrel SOW.pdf")]
M.headings = [{"num": "C.2", "title": "Ground Station Services", "file": "Kestrel SOW.pdf"},
              {"num": "C.2.1", "title": "Operations", "file": "Kestrel SOW.pdf"},
              {"num": "C.2.2", "title": "Maintenance", "file": "Kestrel SOW.pdf"}]
check("Structure is a piece type", "structure" in ST.KEYS)
ST.set_type([M.items[0], M.items[1]], "structure")
check("... the pieces typed Structure, in order", [it["id"] for it in SF.pieces(M)] == ["L-1", "L-2"])
heads = SF.read(M)
got = [(h["level"], h["title"], h.get("limit") or 0) for h in heads]
check("Door 1 reads volumes as H1 and the list under Volume II as H2, with the page limit", got == [
    (1, "Volume I Technical", 0), (1, "Volume II Management", 0), (2, "Management Approach", 15), (2, "Key Personnel", 0),
    (2, "Transition Plan", 0), (1, "Volume III Price", 0)], got)
check("... each says which piece required it and where", heads[2]["req"] == "L-2" and "L.3.2" in heads[2]["ref"] and "page 13" in heads[2]["ref"])
ents = SF.put(M, heads)
labs = [C.outline_label(o) for o in M.outline]
check("Put in our outline: numbered in each volume", labs[:3] == ["Volume I Technical", "Volume II Management", "1 Management Approach"]
      and labs[-1] == "Volume III Price", labs)
check("... Required by kept on the headings", M.outline[2].get("req") == "L-2" and M.outline[2].get("limit") == 15)
M.save()
back = C.Matrix(M.path).load()
check("... and kept when the matrix is saved and opened", back.outline[2].get("req") == "L-2" and back.outline[2].get("req_title") == "Management Approach",
      back.outline[2])
check("nothing drifted yet", SF.drift(M) == [])
M.outline[3]["title"] = "Our Key People"
M.outline.pop(4)
issues = SF.drift(M)
check("a renamed and a removed required heading are found", [k for k, _t in issues] == ["renamed", "gone"], issues)
# door 2
M2 = C.Matrix(os.path.join(tmp, "two.xlsx")); M2.items = list(M.items); M2.headings = list(M.headings)
d = SF.drafts(M2, "sow")
check("Door 2: draft headings from the SOW headings", [x["title"] for x in d] == ["Ground Station Services", "Operations", "Maintenance"]
      and all(x["draft"] for x in d), d)
SF.put_drafts(M2, d)
check("... they are our outline's own sections, marked Draft", SF.draft_count(M2) == 3 and len(M2.outline) == 3)
check("Use it as our structure takes Draft off", SF.use_as_ours(M2) == 3 and SF.draft_count(M2) == 0)
check("blank starts nothing", SF.drafts(M2, "blank") == [])
# the List's tree
from skqt import shredlist as SL
t = dict(SL.tree(M))
sec = t["Section L.pdf"]
names = [(n["num"], n["title"], n["n"]) for n in sec]
check("List: the customer's structure by its references, with counts", ("L.3", "Proposal Organization", 2) in names
      and any(k["num"] == "L.3.2" for n in sec for k in n["kids"]), names)
u = dict(SL.tree(M, undecided=True))
check("... Undecided only leaves out what is decided (a type or a decision)", sum(n["n"] for n in u["Section L.pdf"]) == 0
      and sum(n["n"] for n in u["Kestrel SOW.pdf"]) == 1, {f: [n["n"] for n in r] for f, r in u.items()})
k = sum(checks)
print(f"STRUCT 4190 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
