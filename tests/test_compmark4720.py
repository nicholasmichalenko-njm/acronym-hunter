"""4.72.0: the Compliance pass under the screen (compmark): the kinds a piece has, Not needed and For the setup as the
pass's own marks, each document's state, the pieces still to look at. Fictional (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import compliance as C, compmark as CM, setupdoc as SD, shredtypes as ST

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def item(i, text, **kw):
    it = {"id": i, "text": text, "decision": "", "suggest": "", "file": "Kestrel_SOW.pdf", "section": "3.1", "type": "Requirement",
          "map": "", "lead": "", "context_for": "", "where": "", "page": 1}
    it.update(kw)
    return it


d = tempfile.mkdtemp()
M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M.outline = C.parse_outline("1 Technical Approach\n2 Management")
M.items = [item("K-1", "The contractor shall provide thermal control."), item("K-2", "The Offeror shall describe its approach."),
           item("K-3", "Proposals are due Friday."), item("K-4", "Background."), item("K-5", "Section heading", type="Heading"),
           item("K-6", "The Government will evaluate risk.", file="Kestrel_Section_M.pdf")]
ST.set_types([M.items[0]], ["requirement"]); ST.set_types([M.items[1]], ["instruction", "evaluation"])
check("the kinds a piece has, in the bar's order", CM.kinds_of(M.items[0]) == ["requirement"] and CM.kinds_of(M.items[1]) == ["instruction", "evaluation"]
      and CM.kinds_of(M.items[2]) == [] and CM.count(M) == 2)
check("the pieces still to look at: no kind, no decision, no type, headings out", [x["id"] for x in CM.open_rows(M, "Kestrel_SOW.pdf")] == ["K-3", "K-4"])
check("Not needed is the pass's own: out of next, the piece not dropped, and reopened", CM.not_needed(M, M.items[3]) and CM.state(M, M.items[3]) == "x"
      and not M.items[3]["decision"] and [x["id"] for x in CM.open_rows(M, "Kestrel_SOW.pdf")] == ["K-3"]
      and not CM.not_needed(M, M.items[3], False) and CM.state(M, M.items[3]) == "")
check("For the setup: the customer's own, in the section picked; a heading that is not there is refused", CM.for_setup(M, M.items[2], "2 Management")
      and M.items[2]["decision"] == "Customer" and M.items[2]["map"] == "2 Management" and CM.state(M, M.items[2]) == "s"
      and not CM.for_setup(M, M.items[3], "9 Nowhere"))
check("a piece with a kind sent to the setup keeps its kind and is put there too", CM.for_setup(M, M.items[0], "1 Technical Approach")
      and CM.kinds_of(M.items[0]) == ["requirement"] and "1 Technical Approach" in SD.item_sections(M, M.items[0]) and CM.state(M, M.items[0]) == "")
check("each document's state", [(x["file"], x["state"]) for x in CM.docs(M)] == [("Kestrel_SOW.pdf", "Has finds (2)"), ("Kestrel_Section_M.pdf", "Not looked at")], CM.docs(M))
check("Nothing of this kind here, and taken back", CM.set_none(M, "Kestrel_Section_M.pdf") and CM.docs(M)[1]["state"] == "Nothing of this kind here"
      and not CM.set_none(M, "Kestrel_Section_M.pdf", False) and CM.docs(M)[1]["state"] == "Not looked at")
check("the suggested section is one of our outline's, or nothing", CM.suggested_section(M, M.items[1]) in ("", "1 Technical Approach", "2 Management"))
M.outline = []
check("with no outline nothing is suggested", CM.suggested_section(M, M.items[1]) == "")
M.outline = C.parse_outline("1 Technical Approach")
M.save(); M2 = C.Matrix(M.path if hasattr(M, "path") else os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel"); M2.load()
check("saved and opened again: the pass's marks are there", CM.marks(M2) == CM.marks(M) and CM.state(M2, M2.items[2]) == "s", CM.marks(M2))
print(f"COMPMARK 4720 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
