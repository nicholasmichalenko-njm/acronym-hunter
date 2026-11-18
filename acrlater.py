"""Later on the Acronyms page (4.56.0; UX decisions 107 and 108, the mark only). Later is a mark on a term, never a
status: the term stays to decide, is not counted as to decide, and is stepped past until the rest are through. The mark
holds a reason, an optional note and when it was made. Deciding the term takes the mark off.

The reasons are one list (REASONS) so they are easy to change: the owner wants to look at them again after use.
Kept with the effort's workspace (ws.set under KEY, beside the page marks of acrpages), and in the Acronym Finder with
its list's own workspace the same way, so no saved file changes shape.

marks(s) {term: {"reason", "note", "when"}}   only terms still to decide
mark(s, terms, reason, note) / unmark(s, terms) -> what each term held before (for Undo) / put_back(s, was)
reason_of(s, term) / counts(s, terms=None) {reason key: n} / words(to_decide, counts) "12 to decide, 3 for author review"
Rules only (No AI); nothing leaves the PC."""
import datetime

KEY = "acronym_later"
# (key, the button, how the count and the notice say it). The first is what L or Enter takes; the second is R.
REASONS = (("come", "Come back to it", "for later"),
           ("author", "For author review", "for author review"))
DEFAULT = REASONS[0][0]
FILTERS = {r[2][0].upper() + r[2][1:]: r[0] for r in REASONS}    # the Everything found filters ("For later"): the reason key


def filter_name(key):
    return next(n for n, k in FILTERS.items() if k == key)


def _ws(s):
    return getattr(s, "ws", None) if s is not None else None


def _all(s):
    ws = _ws(s)
    d = (ws.get(KEY, {}) if ws is not None else {}) or {}
    return {t: m for t, m in d.items() if isinstance(m, dict)} if isinstance(d, dict) else {}


def _open(s, t):
    """True while the term is still to decide (not in the list, not Not a term, not tied to another term)."""
    import acrpages as AG
    d = (getattr(s, "results", None) or {}).get(t)
    return d is not None and AG.state_of(d) == "decide"


def marks(s):
    """{term: mark} for the terms marked Later that are still to decide. A mark on a term decided since is not shown
    (deciding a term takes its mark off; it is cleared from the store at the next change)."""
    return {t: m for t, m in _all(s).items() if _open(s, t)}


def reason_of(s, t):
    m = marks(s).get(t)
    return m.get("reason", DEFAULT) if m else None


def label(key):
    """The words for a reason key: (button, count words)."""
    for k, b, c in REASONS:
        if k == key:
            return b, c
    return REASONS[0][1], REASONS[0][2]


def _save(s, d):
    ws = _ws(s)
    if ws is None:
        return False
    keep = {t: m for t, m in d.items() if _open(s, t)}
    ws.set(KEY, keep)
    return True


def mark(s, terms, reason=DEFAULT, note=""):
    """Marks each term Later with a reason and a note. Returns what each held before ({term: mark or None})."""
    if reason not in {r[0] for r in REASONS}:
        reason = DEFAULT
    d = _all(s)
    was = {t: d.get(t) for t in terms}
    when = datetime.datetime.now().isoformat(timespec="seconds")
    for t in terms:
        d[t] = {"reason": reason, "note": " ".join(str(note or "").split()), "when": when}
    _save(s, d)
    return was


def unmark(s, terms):
    """Takes the mark off. Returns what each held before ({term: mark or None})."""
    d = _all(s)
    was = {t: d.get(t) for t in terms}
    for t in terms:
        d.pop(t, None)
    if any(v is not None for v in was.values()):
        _save(s, d)
    return was


def put_back(s, was):
    """Undo: each term's mark as it was (None: no mark)."""
    d = _all(s)
    for t, m in (was or {}).items():
        if m is None:
            d.pop(t, None)
        else:
            d[t] = m
    ws = _ws(s)
    if ws is not None:
        ws.set(KEY, d)
    return len(was or {})


def counts(s, terms=None):
    """{reason key: number of marked terms} (only the terms given, when given)."""
    out = {r[0]: 0 for r in REASONS}
    for t, m in marks(s).items():
        if terms is None or t in terms:
            k = m.get("reason", DEFAULT)
            out[k if k in out else DEFAULT] += 1
    return out


def words(to_decide, by_reason):
    """'12 to decide, 3 for author review, 1 for later': a reason is named only when it has any."""
    parts = [f"{to_decide} to decide"]
    for k, _b, c in sorted(REASONS, key=lambda r: r[0] != "author"):
        n = (by_reason or {}).get(k, 0)
        if n:
            parts.append(f"{n} {c}")
    return ", ".join(parts)


def notice(term, reason):
    """'T marked for later: come back to it.' / 'T marked for later: for author review.'"""
    b = label(reason)[0]
    return f"{term} marked for later: {b[0].lower() + b[1:]}."


def adjust_pages(s, pgs):
    """The pages of acrpages.pages with a term marked Later taken out of to_decide and counted by reason (p["later"]).
    Returns pgs (changed in place)."""
    mk = marks(s)
    for p in pgs:
        later = {}
        for t, st in p["terms"].items():
            if st == "decide" and t in mk:
                k = mk[t].get("reason", DEFAULT)
                later[k] = later.get(k, 0) + 1
        p["later"] = later
        p["to_decide"] = max(0, p["to_decide"] - sum(later.values()))
    return pgs
