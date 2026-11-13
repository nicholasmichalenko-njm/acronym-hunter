"""4.1.0 what a piece of the customer's text is (shredtypes): the eight types the team can rename or hide; the tab each
lands on (Requirements, Rules & Dates, Evaluation); what Place offers (only what the proposal must answer); a piece
from before 4.1.0 typed from what the review already said; the type kept in the matrix workbook's Piece column.
Fictional sentences (the Kestrel set)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import shredtypes as ST
import compliance as C

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


t = ST.load(None)
check("nine types in order (4.19.0 adds Structure)", [v["name"] for v in t.values()] == ["Requirement", "Content Instruction", "Format & Submission", "Key Date", "Evaluation Criterion",
                                                                    "Deliverable", "Information", "Not applicable", "Response Structure"])
check("four tabs, none named Shred", [n for _k, n in ST.TABS] == ["Requirements", "Submission Checklist", "Evaluation Criteria", "Acronyms"])
check("each type's tab", [ST.tab_of(k) for k in ST.KEYS] == ["requirements", "requirements", "rules", "rules", "evaluation",
                                                            "requirements", "requirements", "requirements", "requirements"])
check("Place offers only what the proposal must answer", [k for k in ST.KEYS if ST.placed(k)] ==
      ["requirement", "instruction", "evaluation", "deliverable"])
check("a piece not sorted yet starts on Requirements", ST.tab_of("") == "requirements" and not ST.placed(""))
tmp = tempfile.mkdtemp()
t["rule"]["name"] = "Format and submission rule"; t["information"]["shown"] = False
diff = ST.save(tmp, t)
t2 = ST.load(tmp)
check("the team renames and hides a type; only the change is kept", diff == {"rule": {"name": "Format and submission rule"},
      "information": {"shown": False}} and t2["rule"]["name"] == "Format and submission rule" and not t2["information"]["shown"]
      and t2["requirement"]["name"] == "Requirement", diff)
# from before 4.1.0
F = ST.from_review
check("a requirement in L is an Instruction, in M an Evaluation, else a Requirement",
      F({"decision": "Keep", "lm": "L"}) == "instruction" and F({"decision": "Keep", "lm": "M"}) == "evaluation"
      and F({"decision": "Keep"}) == "requirement")
check("... a requirement holding a deliverable capture is a Deliverable", F({"decision": "Keep"}, ["deliverable"]) == "deliverable")
check("ignored is Not applicable; support and the customer's are Information",
      F({"decision": "Drop"}) == "not_applicable" and F({"decision": "Context"}) == "information" and F({"decision": "Customer"}) == "information")
check("captures say what an undecided sentence is: a page limit a Rule, a key date a Date, a factor Evaluation",
      F({}, ["pagelimit"]) == "rule" and F({}, ["keydate"]) == "date" and F({"decision": "Context"}, ["factor"]) == "evaluation")
check("nothing said: not sorted", F({}) == "" and F({}, ["contact"]) == "")
it = {"id": "R-1", "decision": "Keep", "lm": "L", "text": "The offeror shall describe its approach to TT&C."}
check("type_of: the review's answer until the shred sets one", ST.type_of(it) == "instruction")
logged = []
check("set_type keeps it on the piece and logs it", ST.set_type([it], "requirement", lambda i, m: logged.append((i, m))) == 1
      and ST.type_of(it) == "requirement" and logged == [("R-1", "shred: requirement")])
check("... setting it again changes nothing", ST.set_type([it], "requirement") == 0)
try:
    ST.set_type([it], "bogus"); bad = False
except ValueError:
    bad = True
check("... an unknown type is refused", bad)
items = [{"decision": "Keep", "lm": "M"}, {"decision": "Drop"}, {}, {"piece": "date"}, {"piece": "rule"}]
by_tab, by_type = ST.counts(items)
check("counts by tab and by type", by_tab["evaluation"]["total"] == 1 and by_tab["rules"]["total"] == 2
      and by_tab["requirements"] == {"total": 2, "unsorted": 1} and by_type["not_applicable"] == 1 and by_type["date"] == 1, by_tab)
# the Piece column
check("the matrix workbook keeps the type in its Piece column", "Piece" in C.COLUMNS and C.FIELD["Piece"] == "piece"
      and len(C.WIDTHS) == len(C.COLUMNS))
print(f"SHRED TYPES 410 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
