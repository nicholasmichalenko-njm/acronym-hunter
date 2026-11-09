"""Acronyms v2 (3.88.0, claude/stationkeeper-acronyms-v2-2026-11-08.md): what each term's definition could be, in a
stated order, each with its source and its reason; the terms one click can add; meanings that need a choice, each with
its place; table and figure numbers suggested as Not a term; plurals joined to their term.

Definition order (stated on screen): the effort's list, then the customer's documents, then client lists, then this PC's
database. Suggest, never decide: the bulk add names its terms and its reason.

suggestions(d) -> [{"definition", "source", "why", "where"}]     source: "List" | "Customer" | "Client list" | "This PC"
one_customer(results, kind_of=None) -> [terms]: to decide, exactly one customer definition, nothing that disagrees
meanings(d) -> [{"definition", "where"}] for a term the customer spells out more than one way
not_a_term_hint(term) -> reason or "": "Looks like a table or figure number" (L-3, J-1, F-2.1)
plural_base(term, results) -> the singular term this plural joins (FTEs -> FTE), or ""
Rules only (No AI); nothing leaves the PC."""
import re

ORDER = ("List", "Customer", "Client list", "This PC")
_NUMBERED = re.compile(r"^(?:[A-Z]{1,2}-\d+(?:\.\d+)*[a-z]?|[A-Z]\.\d+(?:\.\d+)*|\d+[A-Z]?)$")


def _clean(s):
    return " ".join((s or "").split())


def suggestions(d):
    out, seen = [], set()

    def add(defn, source, why, where=""):
        k = _clean(defn).casefold()
        if not k or k in seen or k.startswith(("[", "multiple", "rescan")):
            return
        seen.add(k)
        out.append({"definition": _clean(defn), "source": source, "why": why, "where": where})
    if _clean(d.get("list_definition")):
        add(d["list_definition"], "List", "In the effort's list")
    for h in d.get("custdef_all") or []:
        w = h.get("where", "")
        add(h.get("definition", ""), "Customer", f"Spelled out by the customer, {w}" if w else "Spelled out by the customer", w)
    for x in d.get("customer_definitions") or []:
        add(x, "Customer", "Spelled out by the customer")
    for x in d.get("client_definitions") or []:
        add(x, "Client list", "In a client list")
    if d.get("in_db"):
        for x in d.get("definitions") or []:
            add(x, "This PC", "In this PC's database")
    return out


def meanings(d):
    """A term the customer spells out two or more ways: each meaning with the place it is spelled out."""
    by = {}
    for h in d.get("custdef_all") or []:
        k = _clean(h.get("definition")).casefold()
        if k and k not in by:
            by[k] = {"definition": _clean(h["definition"]), "where": h.get("where", "")}
    return list(by.values()) if len(by) > 1 else []


def one_customer(results, to_decide=None):
    """Terms one click can add: still to decide, exactly one customer definition, and no list or client definition that
    says otherwise. to_decide(d) -> bool (the page's own filter); default: not excluded, not in the list, not gone."""
    out = []
    for term, d in sorted(results.items()):
        ok = to_decide(d) if to_decide else (not d.get("excluded") and not d.get("effort") and not d.get("gone")
                                             and not d.get("file_error"))
        if not ok:
            continue
        cust = {_clean(x).casefold() for x in (d.get("customer_definitions") or []) if _clean(x)}
        if len(cust) != 1:
            continue
        others = {_clean(x).casefold() for x in (d.get("client_definitions") or []) if _clean(x)}
        if _clean(d.get("list_definition")):
            others.add(_clean(d["list_definition"]).casefold())
        if others - cust:
            continue
        out.append(term)
    return out


def not_a_term_hint(term):
    t = (term or "").strip()
    if _NUMBERED.match(t):
        return "Looks like a table or figure number"
    return ""


def plural_base(term, results):
    """FTEs joins FTE when FTE is a term too (the scan's own plural_of wins when it set one)."""
    d = results.get(term) or {}
    if d.get("plural_of"):
        return d["plural_of"]
    if len(term) > 2 and term.endswith("s") and term[:-1] in results and term[:-1].isupper():
        return term[:-1]
    return ""
