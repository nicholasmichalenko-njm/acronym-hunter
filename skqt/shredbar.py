"""The shred's decide bar says what each piece IS (4.1.0; claude/stationkeeper-shred-plan-4.1.md, step 2): Requirement,
Instruction, Rule, Date, Evaluation, Deliverable, Information, Not applicable (shredtypes). Requirement, Instruction and
Evaluation are the review's SOW, L and M; Information is the customer's (identified, not answered); Not applicable is
Ignore. Rule, Date and Deliverable are new: a rule or a date is the customer's and kept as that type; a deliverable is a
requirement kept as a deliverable. Every decision on the bar also keeps the piece's type, in the same Undo step.
Placing stays on the page until Matrix & Outline > Place (4.2.0). Rules only (No AI); nothing leaves the PC."""
import diag
import shredtypes as ST

# the review's decision codes (reviewitems.DECISIONS) and the piece type each says
CODE_TYPE = {"C": "requirement", "L": "instruction", "M": "evaluation", "I": "requirement", "cust": "information",
             "ctx": "information", "ignore": "not_applicable", "rule": "rule", "date": "date", "deliv": "deliverable"}
NEW_CODES = ("rule", "date", "deliv")


def keep_type(page, code, rows):
    """After a decision on the bar: the pieces keep the type it says (inside the decision's Undo step)."""
    key = CODE_TYPE.get(code)
    if not key or not rows:
        return 0
    M = page.R.M
    n = ST.set_type(rows, key, lambda i, m: M.log(i, m))
    if n and hasattr(M, "pending"):
        M.pending = True
    return n


def decide(page, code, action):
    """Run a decision on the selected pieces and keep their type, as one Undo step."""
    if page.cx is not None or page.R is None:
        return action()
    rows = page.selected()
    with page.R.group():
        out = action()
        keep_type(page, code, rows)
    return out


def do_piece(page, code):
    """Rule, Date or Deliverable on the selected pieces."""
    if page.cx is not None:
        return page.host.status("Rule, Date and Deliverable are for the documents being shredded.")
    rows = page.selected()
    if not rows:
        return 0
    with page.R.group():
        if code == "deliv":
            page.place_reqs([it for it in rows if it.get("decision") != "Keep"])
            page.R.set_lm(rows, "C")
        else:
            page.R.customer(rows)
        keep_type(page, code, rows)
    diag.activity("shred_typed", n=len(rows))
    name = ST.load(page.host.config_dir)[CODE_TYPE[code]]["name"]
    page.after(f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: {name}")
    return len(rows)
