"""4.76.0, 4.77.0: the Deliverables pass, the logic. Four kinds; a mark is a row of the deliverables list at once with the
customer's words attached; a piece on a deliverable only changes its kind; off detaches and removes what the mark made.
Fictional (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import deliverables as DL, delivmark as DM, compmark as CM, effortrec as R

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


class Mx:
    def __init__(self, items):
        self.items, self.setup, self.outline, self.logged = items, {}, [], []

    def log(self, *a):
        self.logged.append(a)


tmp = tempfile.mkdtemp()
rec = R.Record(tmp)
items = [{"id": "S1", "file": "L.pdf", "page": 3, "section": "L.4", "text": "The Offeror shall submit a Small Business Subcontracting Plan in accordance with the clause."},
         {"id": "S2", "file": "L.pdf", "text": "Offerors shall complete and return the Past Performance Questionnaire, Attachment 4."},
         {"id": "S3", "file": "L.pdf", "text": "The Government will evaluate the technical approach."},
         {"id": "S4", "file": "SOW.pdf", "text": "The Contractor shall provide a redline of the draft contract with its proposal."},
         {"id": "H1", "file": "L.pdf", "type": "Heading", "text": "Attachments to submit"}]
M = Mx(items)
check("four kinds, in order", [n for _k, n in DM.KINDS] == ["Document We Write", "Form We Fill In", "File We Submit", "Redline We Return"])
check("a name from the customer's words", DM.suggest_name(items[0]["text"]) == "Small Business Subcontracting Plan"
      and DM.suggest_name(items[1]["text"]).startswith("Past Performance Questionnaire"), (DM.suggest_name(items[0]["text"]), DM.suggest_name(items[1]["text"])))
did, how = DM.mark(rec, items[0], "write")
d = DL.get(rec, did)
check("a mark adds a row to the deliverables list at once", how == "added" and d["name"] == "Small Business Subcontracting Plan" and d["kind"] == "Plan"
      and d["shred_kind"] == "write", d)
check("... with the customer's words attached", [p["sid"] for p in d["pieces"]] == ["S1"] and d["pieces"][0]["doc"] == "L.pdf" and "Subcontracting" in d["pieces"][0]["text"])
check("... and it is saved", DL.of_piece(R.Record(tmp), "S1")["id"] == did)
check("the same mark again changes nothing", DM.mark(rec, items[0], "write") == (did, "same") and len(DL.items(rec)) == 1)
check("another kind changes the deliverable, no second row", DM.mark(rec, items[0], "form") == (did, "changed") and len(DL.items(rec)) == 1
      and DL.get(rec, did)["kind"] == "Form" and DM.kind_of(rec, items[0]) == "form")
d2, _h = DM.mark(rec, items[1], "form")
d4, _h = DM.mark(rec, items[3], "redline")
check("Form We Fill In and Redline We Return land as the list's own kinds", DL.get(rec, d2)["kind"] == "Form" and DL.get(rec, d4)["kind"] == "Customer file")
check("the count and each document's state", DM.count(rec) == 3 and [(x["file"], x["state"]) for x in DM.docs(M, rec)] == [("L.pdf", "Has finds (2)"), ("SOW.pdf", "Has finds (1)")],
      DM.docs(M, rec))
check("taking the mark off removes the deliverable it made", DM.unmark(rec, items[3]) == "removed" and DL.get(rec, d4) is None and DM.kind_of(rec, items[3]) == "")
mine = DL.add(rec, "Pricing workbook", kind="Attachment")
DL.attach_piece(rec, mine, DM.piece_of(items[2]))
DM.mark(rec, items[2], "file")
check("a piece on a deliverable made elsewhere: the mark sets the kind; off only detaches", DM.unmark(rec, items[2]) == "detached" and DL.get(rec, mine) is not None)
check("the pass goes to pieces that read like a hand-in, not ones on the list, not headings", [x["id"] for x in DM.open_rows(M, rec, "SOW.pdf")] == ["S4"]
      and [x["id"] for x in DM.open_rows(M, rec, "L.pdf")] == [], ([x["id"] for x in DM.open_rows(M, rec, "SOW.pdf")], [x["id"] for x in DM.open_rows(M, rec, "L.pdf")]))
CM.not_needed(M, items[3], True, DM.MARKS)
check("Not needed here is the pass's own, apart from Compliance's", CM.state(M, items[3], DM.MARKS) == "x" and CM.state(M, items[3]) == ""
      and DM.open_rows(M, rec, "SOW.pdf") == [])
CM.set_none(M, "SOW.pdf", True, DM.NONE)
check("Nothing of this kind here, per pass", [x["state"] for x in DM.docs(M, rec) if x["file"] == "SOW.pdf"] == ["Nothing of this kind here"]
      and [x["state"] for x in CM.docs(M) if x["file"] == "SOW.pdf"] != ["Nothing of this kind here"])
# 4.77.0
rec2 = R.Record(tempfile.mkdtemp())
it = lambda i, t, **k: dict({"id": i, "file": "L.pdf", "text": t}, **k)
p1, p2, p3, p4 = it("P1", "The Offeror shall submit a Pricing Workbook."), it("P2", "The pricing workbook shall use Attachment 7."), it("P3", "Offerors shall complete the Past Performance Form."), it("P4", "Sign the form.")
d1, how = DM.mark(rec2, p1, "file", "Pricing Workbook", ref="L.5.2")
check("the customer's reference is kept on the row and with the words", how == "added" and DL.get(rec2, d1)["cust_ref"] == "L.5.2" and DL.get(rec2, d1)["pieces"][0]["loc"] == "L.5.2", DL.get(rec2, d1))
check("a name already on the list is the same but for capitals and punctuation", DM.match(rec2, "pricing workbook.")[0] == "same" and DM.match(rec2, "pricing workbook.")[1]["id"] == d1)
check("a near name is told apart from a new one", DM.match(rec2, "The Pricing Workbook File")[0] == "near" and DM.match(rec2, "Small Business Plan") == ("", None), DM.match(rec2, "The Pricing Workbook File"))
check("attach puts the piece on that row: no second row", DM.attach(rec2, p2, d1, "file") == "attached" and len(DL.items(rec2)) == 1
      and [p["sid"] for p in DL.get(rec2, d1)["pieces"]] == ["P1", "P2"] and DM.kind_of(rec2, p2) == "file")
d3, how3 = DM.mark_many(rec2, [p3, p4], "form", "Past Performance Form", refs={"P3": "L.6", "P4": "L.6"})
check("pieces marked together are one deliverable", how3 == "added" and len(DL.items(rec2)) == 2 and [p["sid"] for p in DL.get(rec2, d3)["pieces"]] == ["P3", "P4"])
check("taking the mark off a deliverable with another piece on it asks; nothing changes", DM.unmark(rec2, p3) == "ask" and DL.get(rec2, d3) is not None and DM.of_piece(rec2, p3) is not None)
check("... keep: the deliverable stays without the piece", DM.unmark(rec2, p3, remove=False) == "detached" and DL.get(rec2, d3) is not None and DM.of_piece(rec2, p3) is None)
d5, _h = DM.mark(rec2, p3, "form", "Representations Form")
DL.update(rec2, d5, owner="Avery")
check("... an owner counts as work done; remove takes it away", DM.unmark(rec2, p3) == "ask" and DM.unmark(rec2, p3, remove=True) == "removed" and DL.get(rec2, d5) is None)
old = it("O1", "A plan is required.", piece="deliverable")
old2 = it("O2", "Another older mark.")
dold = DL.add(rec2, "Older deliverable"); DL.attach_piece(rec2, dold, DM.piece_of(old2))
check("an older Deliverable mark is known as one with no kind said", DM.older(rec2, old) and DM.older(rec2, old2) and not DM.older(rec2, p1) and DM.kind_of(rec2, old2) == "")
M2 = Mx([p1, p2, old, old2])
check("... and the pass goes to it", [x["id"] for x in DM.open_rows(M2, rec2, "L.pdf")] == ["O1", "O2"], [x["id"] for x in DM.open_rows(M2, rec2, "L.pdf")])
check("... a kind said on it keeps its row", DM.mark(rec2, old2, "write") == (dold, "changed") and not DM.older(rec2, old2))
try:
    DM.mark(rec, items[0], "nope"); bad = False
except ValueError:
    bad = True
check("an unknown kind is refused", bad)
print(f"{sum(checks)}/{len(checks)}")
if not all(checks):
    sys.exit(1)
print("ok test_delivmark4770")
