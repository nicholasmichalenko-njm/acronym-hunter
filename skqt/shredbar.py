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


def capture_types(page, kind, sids):
    """A capture that says what a piece is (a page limit, a key date, a factor, a deliverable) types it, when the piece
    has no type and no decision yet (plan step 2). Returns how many were typed."""
    key = ST.CAPTURE_TYPE.get(kind)
    if not key or page.R is None:
        return 0
    rows = [it for it in (page.R.item(i) for i in sids) if it is not None and not it.get(ST.FIELD) and not it.get("decision")]
    n = ST.set_type(rows, key, lambda i, m: page.R.M.log(i, m)) if rows else 0
    if n and hasattr(page.R.M, "pending"):
        page.R.M.pending = True
    return n



# ------------------------------------------------------------------ 4.5.0: type chips that toggle; several types a piece
KEY_OF_CODE = {"C": "requirement", "L": "instruction", "M": "evaluation", "rule": "rule", "date": "date",
               "deliv": "deliverable", "cust": "information", "ignore": "not_applicable"}
ANSWERED = ("requirement", "instruction", "evaluation", "deliverable")


def follow(page, rows):
    """The review's decision follows the piece's types (one Undo step with the toggle): Not applicable is Ignore; any
    answered type is a requirement (L from Instruction, M from Evaluation, else SOW); only Rule, Date or Information is
    the customer's; no type is not decided. Placing stays Place's: a new requirement has no section here."""
    R = page.R
    na, keep, cust, none = [], {}, [], []
    for it in rows:
        ks = ST._keys(it.get(ST.FIELD))
        if "not_applicable" in ks:
            na.append(it)
        elif any(k in ANSWERED for k in ks):
            lm = "L" if "instruction" in ks else "M" if "evaluation" in ks else "C"
            keep.setdefault(lm, []).append(it)
        elif ks:
            cust.append(it)
        else:
            none.append(it)
    if na:
        R.ignore([it for it in na if it.get("decision") != "Drop"])
    for lm, its in keep.items():
        new = [it for it in its if it.get("decision") != "Keep"]
        if new:
            R.req(new, "")
        R.set_lm([it for it in its if (it.get("lm") or "") != lm], lm)
    if cust:
        R.customer([it for it in cust if it.get("decision") != "Customer"])
    if none:
        R.clear([it for it in none if it.get("decision")])


def toggle_piece(page, key, rows=None):
    """A type chip or its key: on for every selected piece, or off when all of them have it. Returns True (on), False
    (off) or None (nothing selected)."""
    if page.cx is not None:
        page.host.status("The types are for the documents being shredded.")
        return None
    rows = rows if rows is not None else page.selected()
    if not rows or page.R is None:
        return None
    M = page.R.M
    names = {k: v["name"] for k, v in ST.load(page.host.config_dir).items()}
    with page.R.group():
        page.R.snap(f"{names.get(key, key)}")
        on, _after = ST.toggle(rows, key, log=lambda i, m: M.log(i, m))
        follow(page, rows)
    M.pending = True
    diag.activity("shred_toggled", n=len(rows), on=on)
    who = rows[0]["id"] if len(rows) == 1 else f"{len(rows)} pieces"
    page.after(f"{who}: {names.get(key, key)} {'on' if on else 'off'}")
    return on
