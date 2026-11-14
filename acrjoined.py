"""Terms joined by a mark: one rule for every join, and one remembered answer (4.30.8; Nicholas 2026-11-13).

Capital-letter pieces written together with "/", "&", "-", "." or "_" and no space are either one term (a pair that
is always named together) or separate terms that happen to sit side by side. The reader used to offer both: the joined
term and its pieces, each a decision, one of them never wanted. Now it offers one or the other:

  1. the joined term is in the database: the joined term, as before;
  2. the person has answered for this joined term in this effort: that answer;
  3. every piece is a term of its own (in the database, in the effort's list, or found standing alone elsewhere in
     these files) and the joined term is not known: the pieces;
  4. otherwise: the joined term, whole. Its pieces are not offered at that place.

The rule answers only for runs whose every piece has two capitals or more. A run with a number or a single letter
among its pieces (GSFC-STD-7000, PCU-28, TT&C) is a designator and is read as it always was: the whole, and the
letters in front too. The accuracy floor holds that (the PC build of 2026-11-14 00:13 stopped when it was lost).

The answer in 2 is given once, on the card's More menu: "These are separate terms" on a joined term, "This is one
term" on a piece. It is kept with the effort (rules_extra["joined"]) and holds on every later scan.

Also here: a joined find cut at the reader's eight-character limit is taken whole (whole()), and a Roman numeral is
not a term (roman()).

Rules only (No AI). Standard library only; nothing leaves the PC."""
import re

CHAIN = re.compile(r"[A-Z][A-Z0-9]*(?:[/&][A-Z][A-Z0-9]*)+s?(?![A-Za-z0-9])")
MOST = 30            # a chain longer than this is a line of text, not a term
MARKS = "/&._-"
RUN = re.compile(r"(?<![\w/&.\-])([A-Z][A-Z0-9]*(?:[/&._\-][A-Z0-9]+)+)(s?)(?![\w/&\-])")
_SPLIT = re.compile(r"[/&._\-]")
WHOLE, PIECES = "whole", "pieces"

ANSWERS = {}         # {joined term: "whole" | "pieces"}: the effort's remembered answers, set before a scan
KNOWN = set()        # the effort's own list, set before a scan
HYPHEN_WHOLE = False  # the effort's hyphen rule (3.92.0): letters joined by a hyphen are always one term


def whole(text, start, raw):
    """(the find to use, where it ends in the text) for a capital-letter find at start. A find inside a joined chain
    becomes the whole chain; one ending in a join mark with nothing after loses the mark; any other find is as it was."""
    end = start + len(raw)
    nxt = text[end:end + 1]
    if "/" in raw or "&" in raw or nxt in ("/", "&"):
        m = CHAIN.match(text, start)
        if m and len(m.group(0)) > len(raw.rstrip("/&")) and len(m.group(0)) <= MOST:
            return m.group(0), m.end()
    trimmed = raw.rstrip("/&")
    if trimmed != raw:
        return (trimmed if len(trimmed) >= 2 else ""), end
    return raw, end


def pieces_of(term):
    return [p for p in _SPLIT.split(term) if p]


def lettered(piece):
    """A piece that could be a term of its own: two capitals or more."""
    return sum(1 for c in piece if c.isupper()) >= 2


def runs(text, common=()):
    """[(start, end, joined term, its pieces)] for each joined run in the text that this rule answers for: two lettered
    pieces or more, none an ordinary word. Others are left to the reader's own patterns."""
    out = []
    for m in RUN.finditer(text):
        term = m.group(1)
        if len(term) > MOST:
            continue
        ps = pieces_of(term)
        if not all(lettered(p) for p in ps) or any(p.lower() in common for p in ps):
            continue                 # a number or a single letter among the pieces: a designator, read as it always was
        out.append((m.start(1), m.end(2), term, ps))
    return out


def hold(text, loc, m, caps=None):
    """The spans of the joined runs in this text that are settled at the end of the scan (settle), not by the reader's
    patterns. A run whose joined term is in the database either way is left to the patterns."""
    spans = []
    for a, b, term, ps in runs(text, m.get("common_words") or ()):
        if term in m["include_db"] or term in m["exclude_db"] or term.upper() in m["exclude_upper"]:
            continue
        m.setdefault("joined", []).append((term, ps, loc, bool(caps and caps(text, a, b)), text))
        spans.append((a, b))
    return spans


def _inside(d, term, locs, n):
    """Note on a piece's record that n of its finds, at locs, sit inside the joined term (for This is one term)."""
    j = d.setdefault("in_joined", {}).setdefault(term, {"at": [], "n": 0})
    j["at"] += [l for l in locs if l not in j["at"]]
    j["n"] += n


def choose(term, ps, findings, m):
    a = ANSWERS.get(term)
    if a in (WHOLE, PIECES):
        return a
    if HYPHEN_WHOLE and set(c for c in term if c in MARKS) == {"-"}:
        return WHOLE
    if not all(lettered(p) for p in ps):
        return WHOLE                                   # a number or a single letter among them: a designator, kept whole
    own = lambda p: p in m["include_db"] or p in m["exclude_db"] or p in KNOWN or p in findings
    return PIECES if all(own(p) for p in ps) else WHOLE


def settle(findings, m, A):
    """After every file is matched: each held joined run becomes the joined term or its pieces. A: the engine module."""
    settle_long(findings, m, A)
    held = m.pop("joined", None) or []
    if not held:
        return 0
    how = {}
    for term, ps, _loc, _caps, _text in held:
        if term not in how:
            how[term] = choose(term, ps, findings, m)
    for term, ps, loc, caps, text in held:
        if how[term] == WHOLE:
            kind = "Designator (Candidate)" if "-" in term or any(c.isdigit() for c in term) else "Acronym (Candidate)"
            A.record_candidate(findings, term, kind, loc, caps_run=caps)
            findings[term]["joined"] = list(ps)
            A.note_first_use(findings, [term], loc, text)
            continue
        said = []
        for p in ps:
            if not lettered(p):
                continue
            if p in m["include_db"]:
                A.record_included(findings, p, loc, m["include_db"])
            elif p in m["exclude_db"]:
                A.record_excluded(findings, p, loc, m["exclude_db"])
            elif p.upper() in m["exclude_upper"]:
                continue
            else:
                A.record_candidate(findings, p, "Acronym (Candidate)", loc, caps_run=caps)
            _inside(findings[p], term, [loc], 1)
            said.append(p)
        A.note_first_use(findings, said, loc, text)
    return len(held)


_WORD = re.compile(r"\b[A-Za-z][a-z]{8,14}\b")
_ENDS = ("TION", "TIONS", "MENT", "MENTS", "NESS", "ABLE", "IBLE", "ANCE", "ENCE", "ANCES", "ENCES", "ING", "INGS", "ITY", "ITIES",
         "IVE", "IVES", "OUS", "ICAL", "ALLY", "IZED", "ISED", "ATED", "SHIP", "SHIPS", "LESS", "ARY", "ORY", "IAL", "IALS")


def words_seen(text, m):
    """The long words these files write in small letters: a run of capitals that is one of them is a word, not a term."""
    m.setdefault("words_seen", set()).update(w.lower() for w in _WORD.findall(text))


def settle_long(findings, m, A):
    """A run of nine to fifteen capitals is a term unless these files also write it in small letters, or it ends the
    way an ordinary word does and has no digit."""
    seen = m.get("words_seen") or set()
    for cand, loc, text in m.pop("long", None) or []:
        low = cand.lower()
        if low in seen or low + "s" in seen or (low.endswith("s") and low[:-1] in seen):
            continue
        if cand.isalpha() and cand.endswith(_ENDS):
            continue
        A.record_candidate(findings, cand, "Acronym (Candidate)", loc)
        A.note_first_use(findings, [cand], loc, text)


# 4.30.8: capitals written against a number that are a unit, not the tail of a term that starts with a digit
UNITS_ON_A_NUMBER = {"HZ", "KHZ", "MHZ", "GHZ", "THZ", "KB", "MB", "GB", "TB", "PB", "KW", "MW", "GW", "KWH", "MWH", "KV", "KVA",
                   "MVA", "VDC", "VAC", "AC", "DC", "DB", "DBM", "RPM", "PSI", "PSIG", "PSIA", "KG", "LB", "LBS", "FT", "IN", "MM", "CM", "KM",
                   "NM", "MS", "MA", "MV", "BTU", "CFM", "GPM", "MPH", "KPH", "PPM", "HP", "AH", "WH", "RU", "KN", "KPA", "MPA", "GPA",
                   "ML", "MG", "OZ", "YD", "MI", "HR", "HRS", "MIN", "SEC", "AM", "PM", "FTE", "FTES", "CFR", "USC", "ST", "ND",
                   "RD", "TH", "EA", "QTY", "PCS", "GAL", "MIL", "KT", "KTS", "BPS", "KBPS", "MBPS", "GBPS", "FPS", "DPI", "PPI", "UTC",
                   "GMT", "EST", "EDT", "CST", "CDT", "MST", "MDT", "PST", "PDT", "AWG", "VA", "CY", "FY", "PY", "OY", "BY", "TY", "DOF"}


def digit_led(findings, m, text, match, loc, A):
    """True when a number and capitals written together are one term that starts with a digit (recorded here)."""
    lead, tail = text[match.start():match.start(1)], match.group(1)
    if not (lead.isdigit() and len(lead) <= 2 and len(tail) >= 2 and tail.isalpha() and tail.isupper()) or tail in UNITS_ON_A_NUMBER:
        return False
    tok = lead + tail
    if tok in m["include_db"]:
        A.record_included(findings, tok, loc, m["include_db"])
    elif tok not in m["exclude_db"] and tok.upper() not in m["exclude_upper"]:
        A.record_candidate(findings, tok, "Acronym (Candidate)", loc)
    return True


def hold_long(text, loc, m, skip):
    """A run of nine to fifteen capitals was never read (the reader's pattern stops at eight). Held until every file
    is matched (settle_long). skip(span): inside a joined term, a code, or a line of capitals."""
    for match in m["long_re"].finditer(text):
        raw = match.group(1)
        cand = raw[:-1] if raw.endswith("s") else raw
        if skip(match.span(1)):
            continue
        if cand not in m["include_db"] and cand not in m["exclude_db"] and cand.upper() not in m["exclude_upper"]:
            m.setdefault("long", []).append((cand, loc, text))
    words_seen(text, m)


_ROMAN = re.compile(r"^(?=[IVX])X{0,3}(?:IX|IV|V?I{0,3})$")
_ALSO_TERMS = {"IV", "VI", "IX", "XI", "XV", "XX", "XXX"}       # numerals that are also terms: a numeral only after a label
_LABELS = {"section", "appendix", "table", "figure", "option", "phase", "part", "item", "step", "annex", "attachment",
           "exhibit", "paragraph", "block", "level", "tier", "type", "class", "group", "task", "volume", "tab", "stage",
           "chapter", "article", "title", "book", "schedule", "category", "factor", "subfactor", "enclosure", "mark", "mod",
           "year", "quarter", "increment", "spiral", "lot", "war", "bowl"}


def roman(text, start, tok):
    """True when the capitals at start are a Roman numeral (Volume III, Phase II), not a term."""
    base = tok[:-1] if len(tok) > 2 and tok[-1] in "ABCab" and _ROMAN.match(tok[:-1]) else tok   # Phase IIB
    if len(base) < 2 or not _ROMAN.match(base):
        return False
    if base not in _ALSO_TERMS:
        return True
    before = re.search(r"([A-Za-z]+)\s+$", text[max(0, start - 24):start])
    return bool(before and before.group(1).lower() in _LABELS)


# ---------------------------------------------------------------- the effort's answers
def prime(s):
    """Before a scan: the effort's answers, its list and its hyphen rule, for settle."""
    global ANSWERS, KNOWN, HYPHEN_WHOLE
    extra = getattr(s, "rules_extra", None) or {}
    ANSWERS = dict(extra.get("joined") or {})
    HYPHEN_WHOLE = bool(extra.get("hyphen_whole"))
    try:
        KNOWN = {t for t, d in (getattr(s, "results", None) or {}).items() if d.get("effort") == "In the list"}
        L = getattr(s, "effort", None)
        KNOWN |= set(getattr(L, "terms", None) or ())
    except Exception:                                             # noqa: BLE001  the list is a help, never a need
        pass


def can_flip(s, term):
    """"pieces" when the term is a joined term that can be taken apart, "whole" when it is a piece found inside one,
    "" when neither."""
    d = (s.results or {}).get(term) or {}
    if d.get("joined") and sum(1 for p in d["joined"] if lettered(p)) >= 2:
        return PIECES
    if d.get("in_joined"):
        return WHOLE
    return ""


def _remember(s, term, how):
    extra = dict(getattr(s, "rules_extra", None) or {})
    j = dict(extra.get("joined") or {})
    j[term] = how
    extra["joined"] = j
    s.rules_extra = extra


def _settle_session(s):
    s.apply_saved_decisions()
    s.apply_effort()
    s.save()


def separate(s, term, A):
    """These are separate terms: the joined term leaves, its pieces take its places. Remembered for this effort."""
    d = (s.results or {}).get(term)
    if not d or not d.get("joined"):
        return []
    m = A.build_matcher()
    locs = list(d.get("locations") or [])
    n = max(len(locs), int(d.get("count") or 0))
    out = []
    for p in d["joined"]:
        if not lettered(p):
            continue
        if p not in s.results:
            if p in m["include_db"]:
                A.record_included(s.results, p, locs[0] if locs else "", m["include_db"])
            else:
                A.record_candidate(s.results, p, "Acronym (Candidate)", locs[0] if locs else "")
            s.results[p].update(count=0, locations=[])
        pd = s.results[p]
        pd["count"] = int(pd.get("count") or 0) + n
        pd["locations"] = list(pd.get("locations") or []) + [l for l in locs if l not in (pd.get("locations") or [])]
        _inside(pd, term, locs, n)
        out.append(p)
    s.results.pop(term, None)
    s.manual_items.pop(term, None)
    _remember(s, term, PIECES)
    _settle_session(s)
    return out


def one_term(s, piece, A, term=None):
    """This is one term: the joined term takes its places back from every piece. Remembered for this effort. A piece
    with finds left over stays (which of its places those are is known again at the next scan)."""
    d = (s.results or {}).get(piece) or {}
    inside = d.get("in_joined") or {}
    term = term or next(iter(inside), "")
    if not term or term not in inside:
        return ""
    locs, n = list(inside[term]["at"]), int(inside[term]["n"])
    ps = pieces_of(term)
    for p in ps:
        pd = s.results.get(p)
        if not pd or term not in (pd.get("in_joined") or {}):
            continue
        mine = pd["in_joined"].pop(term)
        if not pd["in_joined"]:
            pd.pop("in_joined")
        pd["count"] = max(0, int(pd.get("count") or 0) - int(mine["n"]))
        decided = pd.get("effort") or pd.get("in_db") or pd.get("known") or pd.get("excluded") or pd.get("manual")
        if pd["count"] == 0:
            pd["locations"] = [l for l in pd.get("locations") or [] if l not in mine["at"]]
            if not decided:
                s.results.pop(p, None)
    kind = "Designator (Candidate)" if "-" in term or any(c.isdigit() for c in term) else "Acronym (Candidate)"
    for loc in locs:
        A.record_candidate(s.results, term, kind, loc)
    s.results[term].update(count=max(n, len(locs)), joined=ps)
    _remember(s, term, WHOLE)
    _settle_session(s)
    return term
