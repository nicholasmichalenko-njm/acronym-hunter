"""4.66.0 (Nicholas 2026-11-24): Assign. The list of kept requirements and criteria, and the four things done to it,
on the links the app has always kept (the Outline column and its copies). Fictional (Kestrel)."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_OCR_ENGINE"] = "tesseract"
import assignlinks as AL, compliance as C, setupdoc as SD

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def item(i, text, decision="Keep", **kw):
    it = {"id": i, "text": text, "decision": decision, "suggest": "Keep", "file": "Kestrel_Section_L.pdf", "section": "L.4",
          "type": "Requirement", "map": "", "lead": "", "context_for": "", "where": "", "page": 1}
    it.update(kw)
    return it


d = tempfile.mkdtemp()
M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design [L.4.1]\n1.2 Risk Management")
A, B = "1.1 Thermal Design [L.4.1]", "1.2 Risk Management"
M.items = [item("K-1", "The Offeror shall describe the thermal design.", section="L.4.1"),
           item("K-2", "Thermal margins are reported at each review.", decision="Context", context_for="K-1"),
           item("K-3", "The Offeror shall name the risk owner.", section="L.5"),
           item("K-4", "The Government will evaluate the risk approach.", type="Evaluation", section="M.2"),
           item("K-5", "This sentence was dropped.", decision="Drop"),
           item("K-6", "Not decided yet.", decision="")]
check("the pieces are the kept requirements and criteria: no context, nothing dropped or undecided",
      [it["id"] for it in AL.pieces(M)] == ["K-1", "K-3", "K-4"], [it["id"] for it in AL.pieces(M)])
check("nothing assigned yet", AL.counts(M) == ({}, 3, 3), AL.counts(M))
r = AL.rows(M)
check("a row: where it is from, its words, its kind, no section, a suggestion when the section number matches",
      r[0] == {"id": "K-1", "ref": "L.4.1", "text": "The Offeror shall describe the thermal design.", "kind": "Requirement", "sections": [], "suggested": A, "mark": "Not started"}, r[0])   # 4.68.0: and its mark
check("only one kind when asked", [x["id"] for x in AL.rows(M, kind="Evaluation")] == ["K-4"])
check("Find looks in the words and the reference", [x["id"] for x in AL.rows(M, find="risk owner")] == ["K-3"] and [x["id"] for x in AL.rows(M, find="m.2")] == ["K-4"])
check("Take the suggestions places the ones that have one", AL.take_suggestions(M) == 1 and M.items[0]["map"] == A and AL.counts(M) == ({A: 1}, 2, 3), AL.counts(M))
check("Assign to section", AL.assign(M, ["K-3", "K-4"], B) == 2 and AL.counts(M) == ({A: 1, B: 2}, 0, 3), AL.counts(M))
check("... again changes nothing", AL.assign(M, ["K-3"], B) == 0)
check("Not assigned is now empty; All has the three with their sections", AL.rows(M) == [] and [x["sections"] for x in AL.rows(M, "all")] == [[A], [B], [B]])
check("Also in this section keeps it where it is and adds it", AL.also(M, ["K-1"], B) == 1 and SD.item_sections(M, M.items[0]) == [A, B]
      and AL.counts(M)[0] == {A: 1, B: 3}, AL.counts(M))
check("... once", AL.also(M, ["K-1"], B) == 0)
check("a section's own list", [x["id"] for x in AL.rows(M, B)] == ["K-1", "K-3", "K-4"] and [x["id"] for x in AL.rows(M, A)] == ["K-1"])
check("the setup and the matrix read the same links", "K-1" in SD.placed_in(M)[A] and "K-1" in SD.placed_in(M)[B] and "K-3" in SD.placed_in(M)[B])
check("Assign moves a piece: the copy becomes its section", AL.assign(M, ["K-1"], B) == 1 and M.items[0]["map"] == B, (M.items[0]["map"], SD.item_sections(M, M.items[0])))
check("Take out of one section", AL.take_out(M, ["K-4"], B) == 1 and SD.item_sections(M, M.items[3]) == [])
check("Take out of every section", AL.take_out(M, ["K-1"]) >= 1 and SD.item_sections(M, M.items[0]) == [] and AL.counts(M)[1] == 2, AL.counts(M))
check("a piece that is not there is passed over", AL.assign(M, ["nope"], B) == 0 and AL.take_out(M, ["nope"]) == 0)
print(f"ASSIGN LINKS 4660 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
