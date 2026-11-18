"""The four decisions on the acronym card in the margin (4.56.0; UX decisions 107 to 110, his answer 8). Add to effort
list (Enter), Not a term (X, for the whole effort), Skip (N), Later (L); Not a term on this page only is the smaller
second choice. While the Candidate box differs from what was read, the four read Fix and...: one press saves the corrected
read where a fixed read is saved when a term is added on the list's card (acrpart.read_as: the PC's misread rules and the
effort's training data, for a read from a picture) and makes the decision on the corrected term. After each press one
line with Undo says what happened, both things when there were two. Rules only (No AI); nothing leaves the PC."""
import acrlater as LT
import acrpages as AG
import diag

# kind: (the words, the words once the Candidate differs, the key)
WORDS = {"add": ("Add to effort list", "Fix and add to effort list", "Enter"),
         "not": ("Not a term", "Fix and mark Not a term", "X"),
         "skip": ("Skip", "Fix and skip", "N"),
         "later": ("Later", "Fix and mark Later", "L")}
ORDER = ("add", "not", "skip", "later")
HERE = "Not a term on this page only"
TAKE_OFF = "Take the mark off"
SAVED_BOTH = " The corrected read is saved on this PC and in the training data."
SAVED_PC = " The corrected read is saved on this PC."


def label(kind, fixed=False):
    w = WORDS[kind]
    return f"{w[1] if fixed else w[0]}  {w[2]}"


def candidate(f):
    """The corrected read typed in the Candidate box, or "" when it is what was read (or there is no box)."""
    box = getattr(f, "cand", None)
    if box is None or len(getattr(f, "terms", [])) != 1:
        return ""
    try:
        right = " ".join(box.text().split())
    except RuntimeError:
        return ""
    return right if right and right != f.terms[0] else ""


def relabel(f):
    """The four buttons' words follow the Candidate box; this page only waits while a fix is typed (it takes no fix)."""
    fixed = bool(candidate(f))
    for k, b in getattr(f, "four", {}).items():
        b.setText(label(k, fixed))
    if getattr(f, "b_here", None) is not None:
        f.b_here.setEnabled(not fixed)
        f.b_here.setToolTip("Clear the Candidate box first: a fixed read goes with one of the four decisions above" if fixed
                            else "Only on this page. The term stays a find everywhere else in the effort")
    return fixed


# ------------------------------------------------------------------ the fix
def fix(op, term, right, box=None):
    """Saves the corrected read and lists the corrected term at the find's places. Returns (sentence, undo function).
    The misread term becomes part of the corrected one where the corrected one holds it (DC in DC-RVM); otherwise it is
    Not a term in this effort, and a read from a picture is kept for every later scan on this PC (ocrfixes) and as a
    training sample of the effort (efftrain)."""
    import acrmore as AM
    import acrparts as APS
    import efftrain as ET
    from . import acrextras as AX
    from . import acrselbar as SB
    s = op.session
    d = s.results.get(term) or {}
    created = right not in s.results
    had_place = op.key in ((s.results.get(right) or {}).get("locations") or [])
    AM.add_manual(s, right, AG.type_of(d) or "Acronym", "", document=op.key, to=("results",))
    if created and right in s.results:
        s.results[right]["locations"] = sorted(set(d.get("locations") or []) | {op.key})
        s.results[right]["count"] = d.get("count", 0)
    undo = []
    if created:
        undo.append(lambda: AM.remove_manual(s, right))
    elif not had_place:
        undo.append(lambda: (s.results.get(right) or {}).get("locations", []).remove(op.key)
                    if op.key in (s.results.get(right) or {}).get("locations", []) else None)
    if term in right and APS.set_part(s, term, right):
        undo.append(lambda: APS.clear_part(s, term))
        said = f" {term} is part of {right} here."
    else:
        said = f" {term} is read as {right} in this effort."
        if op.state == "picture" or AX.in_pictures(d):
            import ocrfixes as OF
            try:
                OF.add(term, right, note="fixed on the Acronyms page")
                undo.append(OF.undo)
                said = SAVED_PC
            except PermissionError:
                op.page.host.status(__import__("app_gui").DB_LOCKED_MSG)
            sid = ET.sample_id("misread", term, right, op.key)
            root = ET._root(s)
            there = any(r.get("id") == sid for r in ET.load(root)) if root else True
            got = ET.add(s, "misread", term, right, [op.key], crop=SB.crop(op, box) if box else None)
            if got is not None and not there:
                undo.append(lambda: ET.remove(s, sid))
                if said == SAVED_PC:
                    said = SAVED_BOTH
        was = AG.before(s, [term])
        if s.effort is None:
            s.exclude([term], True)
        else:
            s.set_status([term], "Not a term")
        undo.append(lambda: AG.undo_not_term(s, was))
    s.save()
    diag.activity("acronym_page_fixed")

    def back():
        for fn in reversed(undo):
            try:
                fn()
            except Exception:  # noqa: BLE001  take back what can be taken back
                diag.swallowed()
        s.save()
    return said, back


def already(s, t):
    """The sentence when a corrected term is decided in this effort already, or ""."""
    st = AG.state_of(s.results.get(t) or {})
    if st in ("list", "tied"):
        return f"{t} is already in the effort list."
    if st == "not":
        return f"{t} is already Not a term in this effort."
    return ""


# ------------------------------------------------------------------ the presses
def _not_term(s, terms):
    if s.effort is None:
        s.exclude(terms, True)
    else:
        s.set_status(terms, "Not a term")


def press(op, f, kind, reason=None, note=""):
    """One of the four on the card for one find or several. Returns the line said."""
    from . import acrmove as MV
    from . import acrselbar as SB
    s = op.session
    terms = list(f.terms)
    right = candidate(f)
    extra, back_fix = "", None
    if right:
        x = op.selected()[0] if op.selected() else {}
        extra, back_fix = fix(op, terms[0], right, x.get("box"))
        terms = [right]
    words = ", ".join(terms[:4]) + ("..." if len(terms) > 4 else "")
    if kind == "skip":
        if back_fix is None:
            return MV.skip(op) and ""
        line = f"{words} stands as a find to decide." + extra
        return op.decided("", undo=back_fix, line=line.strip())
    said = already(s, terms[0]) if right else ""
    was = AG.before(s, terms)
    marks = LT.marks(s)
    was_mark = {t: marks.get(t) for t in terms}
    if said:
        line = said
    elif kind == "add":
        typ = SB.chosen_type(f)
        if typ:
            AG.set_type(s, terms, typ)
        if len(terms) == 1:
            s.add(terms, SB.definition_of(f))
        else:
            import acrsuggest as AS
            for t in terms:
                sg = AS.suggestions(s.results.get(t) or {})
                s.add([t], sg[0]["definition"] if sg else "")
        diag.activity("acronym_page_added", n=len(terms))
        line = f"{words} added to the effort list."
    elif kind == "not":
        _not_term(s, terms)
        diag.activity("acronym_page_not_term", n=len(terms))
        line = f"{words} marked Not a term in this effort. It will not be offered here again."
    else:
        reason = reason or LT.DEFAULT
        LT.mark(s, terms, reason, note)
        diag.activity("acronym_page_later", n=len(terms))
        line = LT.notice(words, reason)
    if kind in ("add", "not") and not said:
        LT.unmark(s, terms)

    def back():
        if not said and kind in ("add", "not"):
            AG.undo_not_term(s, was)
        LT.put_back(s, was_mark)
        if back_fix is not None:
            back_fix()
        s.save()
    return op.decided("", undo=back, line=(line + extra).strip())


def here(op, terms):
    """Not a term on this page only (what X did from 4.26.1): the term stays a find everywhere else."""
    import acrplace as AP
    s = op.session
    took = AP.not_here(s, terms, op.key)
    words = ", ".join(terms[:4]) + ("..." if len(terms) > 4 else "")
    diag.activity("acronym_page_not_term_here", n=len(terms))
    return op.decided("", undo=lambda: AP.undo(s, took), line=f"{words} marked Not a term on this page only.")


def take_off(op, terms):
    """Take the mark off (Later): the term is to decide again, here and in the counts."""
    s = op.session
    was = LT.unmark(s, terms)
    words = ", ".join(terms[:4])
    return op.decided("", undo=lambda: LT.put_back(s, was), line=f"{words}: the mark for later is taken off.", move=False)
