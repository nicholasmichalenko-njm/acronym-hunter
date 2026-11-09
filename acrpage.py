"""Acronyms on the page (3.92.0; claude/stationkeeper-acronyms-on-the-page-3.92.md): the rules behind the page, with no
window. The filters as counts, a find that sits inside a longer term (DC in DC-RVM), where a meaning comes from and
which source wins, the effort's timeline, the row a term adds to a volume's A to Z Acronyms table, and the effort's
rule that letters joined by a hyphen are one term.

COUNTS                     the filters, in their order on the page
count_of(results, kind_of) {filter: number}
passes(d, name, kind)      whether a term is in a filter
longer(results, term)      {"whole", "shared", "places"} when a longer term holds this one in at least half its places
SOURCE_ORDER               which source wins, highest first
sources(d, chosen, team_db=None, library=None) -> [{"source", "says", "against"}]
timeline(ws) / note(ws, what, **counts)   the effort's acronym timeline (newest last), kept with the effort
table_rows(entries, term, definition, around=2) -> [(term, definition, is_new)]   the A to Z rows around the new one
hyphen_whole(s) / set_hyphen_whole(s, on)  the effort's hyphen rule; join_hyphenated(s) applies it
Rules only (No AI); nothing leaves the PC."""
import datetime
import re

import acrparts as AP

COUNTS = ("To decide", "Needs a choice", "No definition yet", "On pictures", "In the list", "Not a term")
SOURCE_ORDER = ("Your decision", "The customer's list", "The customer's words", "The team database", "Earlier efforts")
_HYPHEN = re.compile(r"^[A-Z0-9&]+(?:-[A-Z0-9&]+)+$")


def _clean(s):
    return " ".join(str(s or "").split())


def _pictures(d):
    import app_gui as A
    return any(A.loc_kind(l) == "figure" for l in d.get("locations", []) if l)


def passes(d, name, kind):
    """A filter on the page (the 3.34.1 status filters, and On pictures)."""
    if name == "On pictures":
        return _pictures(d) and not d.get("excluded") and d.get("effort") != "Not a term"
    if name == "To decide":
        return not d.get("excluded") and not d.get("known") and not d.get("effort") and kind != "error" and not d.get("gone")
    if name == "In the list":
        return d.get("effort") == "In the list"
    if name == "No definition yet":
        return d.get("effort") == "In the list" and not _clean(d.get("list_definition"))
    if name == "Needs a choice":
        return kind == "choice"
    if name == "Not a term":
        return bool(d.get("excluded")) or d.get("effort") == "Not a term"
    return True


def count_of(results, kind_of):
    out = {k: 0 for k in COUNTS}
    for d in results.values():
        if d.get("plural_of") or d.get("form_of") or d.get("part_of"):
            continue
        kind = kind_of(d)
        for k in COUNTS:
            if passes(d, k, kind):
                out[k] += 1
    return out


def longer(results, term):
    """The longer term this find sits inside in at least half its places (DC in DC-RVM), or None."""
    d = results.get(term) or {}
    mine = {AP.place(l) for l in d.get("locations", []) if l}
    if not mine:
        return None
    best = None
    for whole in AP.longer_forms(results, term):
        theirs = {AP.place(l) for l in (results.get(whole) or {}).get("locations", []) if l}
        shared = len(mine & theirs)
        if shared * 2 >= len(mine) and (best is None or shared > best["shared"]):
            best = {"whole": whole, "shared": shared, "places": len(mine)}
    return best


def sources(d, chosen=None, team_db=None, library=None):
    """Every source of a term's meaning, highest first, each against the decision: Agrees, Differs, or In use (the
    decision itself). A source lower down never changes a decision."""
    chosen = _clean(chosen if chosen is not None else (d.get("list_definition") or d.get("selected_definition")))
    rows = []

    def add(src, says):
        says = _clean(says)
        if not says:
            return
        against = "In use" if src == SOURCE_ORDER[0] else ("Agrees" if chosen and says.casefold() == chosen.casefold() else
                                                             "Differs" if chosen else "")
        rows.append({"source": src, "says": says, "against": against})
    if d.get("effort") == "In the list" and chosen:
        add(SOURCE_ORDER[0], chosen)
    for x in d.get("client_definitions") or []:                  # the customer's acronym list
        add(SOURCE_ORDER[1], x)
    seen = set()
    for h in d.get("custdef_all") or []:
        k = _clean(h.get("definition")).casefold()
        if k and k not in seen:
            seen.add(k); add(SOURCE_ORDER[2], h.get("definition"))
    for x in d.get("customer_definitions") or []:
        if _clean(x).casefold() not in seen:
            seen.add(_clean(x).casefold()); add(SOURCE_ORDER[2], x)
    for x in (team_db if team_db is not None else d.get("db_definitions") or []):
        add(SOURCE_ORDER[3], x)
    for x in library or []:
        add(SOURCE_ORDER[4], x)
    return rows


def differs(rows):
    """True when a source other than the decision says something else (the term goes back to To decide)."""
    return any(r["against"] == "Differs" for r in rows if r["source"] in SOURCE_ORDER[1:3])


# ---------------------------------------------------------------- the timeline
def timeline(ws):
    return list((ws.get("acronym_timeline", []) if ws is not None else []) or [])


def note(ws, what, when=None, **counts):
    """One line on the effort's timeline: a scan, the customer's list, an amendment, a drafts check, with its counts."""
    if ws is None:
        return None
    row = {"when": (when or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"), "what": _clean(what),
           "counts": {k: int(v) for k, v in counts.items() if v is not None}}
    t = timeline(ws)
    t.append(row)
    ws.set("acronym_timeline", t[-200:])
    return row


def counts_text(c):
    words = {"found": "found", "to_decide": "to decide", "new": "new", "agree": "agree", "differ": "differ",
             "changed": "meanings changed", "doubt": "read with doubt", "to_fix": "to fix", "pictures": "on pictures"}
    return ", ".join(f"{v} {words.get(k, k.replace('_', ' '))}" for k, v in c.items())


# ---------------------------------------------------------------- where it goes
def _az(t):
    return (t or "").casefold()


def table_rows(entries, term, definition, around=2):
    """The A to Z rows around the term in a volume's Acronyms table, the term's own row marked new when it was not
    there. entries: [(term, definition)]."""
    rows = {t: dfn for t, dfn in entries if t}
    new = term not in rows
    rows[term] = definition or rows.get(term, "")
    order = sorted(rows, key=_az)
    i = order.index(term)
    lo, hi = max(0, i - around), min(len(order), i + around + 1)
    return [(t, rows[t], t == term and new) for t in order[lo:hi]]


# ---------------------------------------------------------------- the hyphen rule
def hyphen_whole(s):
    return bool((getattr(s, "rules_extra", None) or {}).get("hyphen_whole"))


def set_hyphen_whole(s, on):
    extra = dict(getattr(s, "rules_extra", None) or {})
    extra["hyphen_whole"] = bool(on)
    s.rules_extra = extra
    n = join_hyphenated(s) if on else 0
    try:
        s.save()
    except Exception:                                             # noqa: BLE001  a session that cannot save (tests)
        pass
    return n


def join_hyphenated(s):
    """Letters joined by a hyphen are one term (DC-RVM): a piece found only inside it is set as part of it there.
    Returns how many pieces were joined."""
    if not hyphen_whole(s):
        return 0
    n = 0
    for whole, d in list(s.results.items()):
        if not _HYPHEN.match(whole) or d.get("excluded"):
            continue
        theirs = {AP.place(l) for l in d.get("locations", []) if l}
        for piece in whole.split("-"):
            pd = s.results.get(piece)
            if not pd or pd.get("part_of") or pd.get("effort") == "In the list":
                continue
            mine = {AP.place(l) for l in pd.get("locations", []) if l}
            if mine and mine <= theirs and AP.set_part(s, piece, whole, places=sorted(pd.get("locations", []))):
                n += 1
    return n
