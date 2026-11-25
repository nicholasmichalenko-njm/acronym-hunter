"""4.74.0: the Customer Doc Structure under the screen (custstruct): the number, title and level proposed from a piece's
own words; the customer reference of every piece under a marked heading; Send to Outline's list. Fictional (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import compliance as C, custstruct as CS, matrixdesign as MD, setupdoc as SD, structmark as SM

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def item(i, text, **kw):
    it = {"id": i, "text": text, "decision": "", "suggest": "", "file": "Kestrel_Section_L.pdf", "section": "L", "type": "Requirement",
          "map": "", "lead": "", "context_for": "", "where": "", "page": 1}
    it.update(kw)
    return it


for text, want in (("L.3.2 Technical Approach", ("L.3.2", "Technical Approach", 2)), ("L.3.2.1 Thermal Design.", ("L.3.2.1", "Thermal Design", 3)),
                   ("4.2.3(b) Maintenance", ("4.2.3(b)", "Maintenance", 3)), ("Attachment J-3 Past Performance Questionnaire", ("Attachment J-3", "Past Performance Questionnaire", 1)),
                   ("Section L: Instructions to Offerors", ("Section L", "Instructions to Offerors", 1)), ("Instructions to Offerors", ("", "Instructions to Offerors", 2)),
                   ("3. Scope", ("3", "Scope", 1))):
    check(f"proposed from the words: {text}", CS.propose(item("x", text)) == want, CS.propose(item("x", text)))
check("typed on the bar: number, a colon, the title", CS.parse("L.3.2: Technical Approach") == ("L.3.2", "Technical Approach") and CS.parse("Our Understanding") == ("", "Our Understanding")
      and CS.parse("L.3.2 Technical Approach") == ("L.3.2", "Technical Approach"))
d = tempfile.mkdtemp()
M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M.outline = C.parse_outline("1 Technical Approach")
M.items = [item("K-1", "The Offeror shall read these instructions."), item("K-2", "L.3 Proposal Content"), item("K-3", "The Offeror shall describe its approach."),
           item("K-4", "L.3.2 Technical Approach"), item("K-5", "The Offeror shall describe thermal control.", decision="Keep"),
           item("K-6", "The contractor shall test.", file="Kestrel_SOW.pdf", section="3.1")]
it = {x["id"]: x for x in M.items}
check("with nothing marked, a piece's reference is the section the reader found", CS.ref_of(M, it["K-3"]) == "L" and CS.above(M, it["K-3"]) is None)
check("a customer heading is marked, and never added to our outline", CS.mark(M, it["K-2"], "L.3", "Proposal Content", 1) == "L.3 Proposal Content"
      and [C.outline_label(o) for o in M.outline] == ["1 Technical Approach"] and CS.is_head(M, it["K-2"]) and "K-2" not in SM.marks(M))
CS.mark(M, it["K-4"], "L.3.2", "Technical Approach", 2)
check("every piece takes its reference from the nearest heading marked above it", [CS.ref_of(M, it[k]) for k in ("K-1", "K-2", "K-3", "K-4", "K-5")] ==
      ["L", "L.3", "L.3", "L.3.2", "L.3.2"], [CS.ref_of(M, it[k]) for k in ("K-1", "K-2", "K-3", "K-4", "K-5")])
check("... only in its own document", CS.ref_of(M, it["K-6"]) == "3.1")
check("a heading with no number is known by its title", CS.mark(M, it["K-1"], "", "General Instructions") == "General Instructions" and CS.ref_of(M, it["K-1"]) == "General Instructions")
check("the marked headings in the customer's order", [(r["label"], r["level"]) for r in CS.tree(M, "Kestrel_Section_L.pdf")] ==
      [("General Instructions", 2), ("L.3 Proposal Content", 1), ("L.3.2 Technical Approach", 2)], CS.tree(M))
check("the matrix has the column Customer reference, with the heading's number", "cust_ref" in MD.COLUMNS and MD.COLUMNS["cust_ref"][0] == "Customer reference"
      and MD._value(M, it["K-5"], "cust_ref", {}, {}) == "L.3.2", MD._value(M, it["K-5"], "cust_ref", {}, {}))
check("... and is not in the default designs", all("cust_ref" not in [c["key"] for c in MD.default(k)["columns"]] for k, _l in MD.LAYOUTS))
check("a heading taken off: the pieces under it fall back to the one above", CS.unmark(M, it["K-4"]) and CS.ref_of(M, it["K-5"]) == "L.3" and not CS.unmark(M, it["K-4"]))
check("Send to Outline: the piece waits; sent twice is once; nothing else changes", CS.send(M, it["K-3"]) and not CS.send(M, it["K-3"]) and [x["id"] for x in CS.sent(M)] == ["K-3"]
      and not it["K-3"]["decision"] and len(M.outline) == 1)
check("... it leads what the Outline's marking suggests, and has a level suggested", SM.suggestions(M)[0]["id"] == "K-3" and SM.next_suggestion(M)["id"] == "K-3"
      and SM.suggest(M, it["K-3"]) in SM.DEPTH, (SM.suggestions(M)[:1], SM.suggest(M, it["K-3"])))
SM.not_needed(M, it["K-3"])
check("... dealt with there, it no longer leads", not SM.suggestions(M) or SM.suggestions(M)[0]["id"] != "K-3")
check("... and it can be taken back", CS.unsend(M, "K-3") and not CS.sent(M) and not CS.unsend(M, "K-3"))
CS.send(M, it["K-5"])
M.save(); M2 = C.Matrix(M.path if hasattr(M, "path") else os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel"); M2.load()
check("saved and opened again: the headings and what was sent are there", CS.heads(M2) == CS.heads(M) and [x["id"] for x in CS.sent(M2)] == ["K-5"], CS.heads(M2))
print(f"CUSTSTRUCT 4740 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
