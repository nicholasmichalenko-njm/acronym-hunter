"""Pieces the page break touched (4.2.0; claude/stationkeeper-fix-text-decisions-2026-11-10.md, decisions 5 and 6).
The page reader (pagesent) already joins a paragraph that runs onto the next page and leaves the running headers and
footers out. This module says so and lists what is worth a look:
- mark(items): a piece that runs over two pages is marked "Joined across p.N to N+1" (Enter keeps it, Undo the join
  splits it back at the page break); a page number left inside it ("Page 3 of 12") is taken out;
- suspects(items): joins not kept yet; a piece that ends a page without a full stop and was not joined; fragments of
  under four words; a word hyphenated across a line ("manage- ment"); characters the reader could not read.
Rules only (No AI); nothing leaves the PC."""
import re

JOINED = "Joined across p."
KEPT = " (kept)"
_PAGE_IN = re.compile(r"\s+(?:Page|PAGE)\s+\d{1,4}\s+of\s+\d{1,4}\s+")
_END = re.compile(r"[.?!:;)\]\"”]\s*$")
_HYPH = re.compile(r"[A-Za-z]{2,}-\s+[a-z]{2,}")
_BAD = re.compile(r"[�ﬀ-ﬆ]")


def _spans(it):
    import pagesent as PS
    return PS.parse_place(it.get("place") or "")


def pages_of(it):
    """The pages (1-based) a piece runs over, from its place on the page ("1:98-181;2:22-58")."""
    return sorted({p[0] for p in _spans(it)})


def mark(items):
    """After a read: mark the pieces joined across a page break; take a page number out of their middle. Returns them."""
    out = []
    for it in items:
        pg = pages_of(it)
        if len(pg) < 2:
            continue
        t = it.get("text", "")
        t2 = _PAGE_IN.sub(" ", t)
        if t2 != t:
            it["text"] = " ".join(t2.split())
        if not (it.get("new") or ""):
            it["new"] = f"{JOINED}{pg[0]} to {pg[-1]}"
        out.append(it)
    return out


def joined(it):
    return (it.get("new") or "").startswith(JOINED)


def keep(it):
    """Enter on a join: kept, and off the suspects."""
    if joined(it) and not it["new"].endswith(KEPT):
        it["new"] += KEPT
        return True
    return False


def unjoin_at(it):
    """The character where the page break falls in a joined piece (the words placed on its first page), or None."""
    sp = _spans(it)
    if len({p[0] for p in sp}) < 2:
        return None
    first = sp[0][0]
    rest = sum(b - a for pg, a, b in sp if pg != first) + sum(1 for pg, _a, _b in sp if pg != first) - 1
    text = it.get("text", "")
    guess = len(text) - rest
    starts = [m.start() for m in re.finditer(r"\S+", text)][1:]
    if not starts:
        return None
    return min(starts, key=lambda s_: abs(s_ - guess))


def suspects(items, file=None):
    """[(kind, item, why)] in reading order: what Fix text's Suspects walks through."""
    rows = [it for it in items if (file is None or it.get("file") == file) and it.get("header") != "Yes"
            and it.get("decision") != "Drop"]
    out = []
    last_on = {}
    for it in rows:
        pg = pages_of(it)
        if pg:
            last_on[(it.get("file"), pg[-1])] = it
    tails = {id(v) for v in last_on.values()}
    for it in rows:
        t = it.get("text", "")
        if joined(it) and not it["new"].endswith(KEPT):
            out.append(("join", it, it["new"] + ": keep it, or undo the join"))
        elif id(it) in tails and len(pages_of(it)) == 1 and t and not _END.search(t):
            out.append(("end", it, f"Ends page {pages_of(it)[0]} without a full stop: does it go on overleaf?"))
        elif 0 < len(t.split()) < 4 and it.get("type") != "Heading":
            out.append(("short", it, "A fragment of under four words"))
        if _HYPH.search(t):
            out.append(("hyphen", it, "A word broken across a line"))
        if _BAD.search(t):
            out.append(("bad", it, "Characters the reader could not read"))
    return out
