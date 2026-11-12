"""Acronyms on the page, page by page (3.93.0; claude/stationkeeper-acronyms-two-tabs-3.93.md). The rules behind the On the
page tab: the pages (each place a scan found terms: a PDF page, a picture, a section of typed text) with the finds on
each and how many are left to decide; Page done, kept with the effort; where each term sits in a picture's readings or
in a passage of typed text; which bar a selection gets (decide, part of a longer term, read with doubt, not found
before); the type of a term; Not a term with its way back. Rules only (No AI); nothing leaves the PC."""
import re

import acrpage as P

DONE_KEY = "acronym_pages_done"
TYPES = (("Acronym", "A"), ("Abbreviation", "B"), ("Unit", "U"), ("Symbol", "S"))
COLORS = {"decide": "#E0A800", "list": "#16A34A", "doubt": "#C2410C", "sel": "#2E7BE0", "new": "#2E7BE0"}
_PAGE = re.compile(r"\(p\.(\d+)")


def _fold(t):
    import app_gui as A
    return A.fold(str(t or "")).casefold()


# ------------------------------------------------------------------ a term's state
def state_of(d):
    """decide, list (in the effort's list or known), not (Not a term) or tied (a plural, a form, part of a longer term)."""
    if d.get("excluded") or d.get("effort") == "Not a term":
        return "not"
    if d.get("plural_of") or d.get("form_of") or d.get("part_of"):
        return "tied"
    if d.get("effort") == "In the list" or d.get("known"):
        return "list"
    return "decide"


def _real(t, d):
    return not str(t).startswith("[") and "Not Scanned" not in str(d.get("category", ""))


def place_of(loc):
    """The page a location names (an OCR fix noted after it is the same page)."""
    return str(loc or "").split(" [OCR fix", 1)[0].strip()


# ------------------------------------------------------------------ the pages
def _order(key):
    from skqt.whereview import parse_loc
    name, _pg, _para = parse_loc(key)
    m = _PAGE.search(key)
    return (name.casefold(), int(m.group(1)) if m else 0, key.casefold())


def pages(results, done=()):
    """Every page with finds, by file then page: {key, name, label, terms {term: state}, to_decide, done}."""
    from skqt.whereview import parse_loc
    by = {}
    for t, d in results.items():
        if not _real(t, d):
            continue
        st = state_of(d)
        for loc in d.get("locations") or []:
            by.setdefault(place_of(loc), {})[t] = st
    done = set(done or ())
    out = []
    for key in sorted(by, key=_order):
        name = parse_loc(key)[0]
        label = short(key[len(name):].strip().strip("()") or name)
        terms = by[key]
        out.append({"key": key, "name": name, "label": label, "terms": terms,
                    "to_decide": sum(1 for s in terms.values() if s == "decide"), "done": key in done})
    return out


def short(label):
    """A place as the page list shows it: "section '1. SCOPE OF WORK', para 2-9" is 1. SCOPE OF WORK."""
    m = re.match(r"^section '(.*)'(, table)?, para [\d-]+$", label)
    return (m.group(1) + (" (table)" if m.group(2) else "")) if m else label


def totals(pgs):
    left = [p for p in pgs if p["to_decide"] and not p["done"]]
    return {"to_decide": sum(p["to_decide"] for p in left), "pages_left": len(left),
            "pages_done": sum(1 for p in pgs if p["done"] or not p["to_decide"])}


def next_page(pgs, cur=None):
    """The next page (after cur, round to the start) with finds to decide that is not marked done; None when none is left."""
    keys = [p["key"] for p in pgs]
    k = keys.index(cur) + 1 if cur in keys else 0
    for p in pgs[k:] + pgs[:k]:
        if p["to_decide"] and not p["done"] and p["key"] != cur:
            return p["key"]
    return None


def done_set(ws):
    return set((ws.get(DONE_KEY, []) if ws is not None else []) or [])


def set_done(ws, key, on=True):
    s = done_set(ws)
    (s.add if on else s.discard)(key)
    if ws is not None:
        ws.set(DONE_KEY, sorted(s))
    return s


# ------------------------------------------------------------------ where a term sits
def spans(text, term):
    """(start, end) of each place the term is written in the text as a whole word (not inside a longer word)."""
    if not term or not text:
        return []
    ft, fx = _fold(term), _fold(text)
    out, k = [], fx.find(ft)
    while k >= 0:
        a, b = k, k + len(ft)
        left = fx[a - 1] if a > 0 else " "
        right = fx[b] if b < len(fx) else " "
        if not (left.isalnum() or left == "&") and not (right.isalnum() or right == "&"):
            out.append((a, b))                 # a hyphen is a boundary: DC and RVM are found inside DC-RVM
        elif not (left.isalnum() or left == "&") and len(fx) == len(text) and _plural_at(text, b):
            out.append((a, b))                 # 4.23.1: RFPs marks RFP (the scan counts the plural as the term)
        k = fx.find(ft, k + 1)
    return out


def _plural_at(text, b):
    """A lower-case s (or 's) closes a term written in capitals or digits at b: RFPs, CDRLs, the SOW's."""
    if b < 1 or not (text[b - 1].isupper() or text[b - 1].isdigit()):
        return False
    rest = text[b:b + 3]
    for tail in ("s", "'s", "\u2019s"):
        if rest.startswith(tail):
            after = text[b + len(tail):b + len(tail) + 1]
            return not (after.isalnum() or after == "&")
    return False


def _within(f, g):
    """f's place lies inside g's (a span in typed text, or a box on a picture)."""
    if "span" in f:
        return g["span"][0] <= f["span"][0] and f["span"][1] <= g["span"][1]
    return f["box"][0] >= g["box"][0] - 1 and f["box"][2] <= g["box"][2] + 1 and abs(f["box"][1] - g["box"][1]) < 4


def resolve(finds, results):
    """Two terms on the same spot (DC inside DC-RVM): while the part is still to decide it stays, with the whole term
    behind it (drawn dashed: partly found); once the part is decided, the whole term takes the spot."""
    out = []
    for f in finds:
        outer = [g for g in finds if g is not f and len(g["term"]) > len(f["term"]) and _within(f, g)]
        inner = [g for g in finds if g is not f and len(g["term"]) < len(f["term"]) and _within(g, f)]
        if outer:
            if state_of(results.get(f["term"]) or {}) == "decide":
                out.append(dict(f, whole=max(outer, key=lambda g: len(g["term"]))))
            continue
        if any(state_of(results.get(g["term"]) or {}) == "decide" for g in inner):
            out.append(dict(f, behind=True))
            continue
        out.append(f)
    return out


def all_spans(text, terms):
    """Every place of every term in a passage, overlapping ones too: [{term, span, conf, line}] in reading order."""
    out = [{"term": t, "span": (a, b), "conf": None, "line": text[a:b]} for t in terms for a, b in spans(text, t)]
    return sorted(out, key=lambda x: (x["span"][0], -x["span"][1]))


def text_finds(text, terms):
    """The finds in a passage, longest term first, never overlapping: [(start, end, term)] in reading order."""
    taken, out = [], []
    for t in sorted(terms, key=lambda x: (-len(x), x)):
        for a, b in spans(text, t):
            if any(a < y and x < b for x, y in taken):
                continue
            taken.append((a, b)); out.append((a, b, t))
    return sorted(out)


def line_finds(lines, terms):
    """The finds in a picture's readings: [{term, box, conf, line}] (the box is the term's part of the line)."""
    out = []
    for (x0, y0, x1, y1), text, conf in lines:
        per = (x1 - x0) / max(1, len(text))
        for t in terms:                        # every term on its own: two on one spot are resolved after
            for a, b in spans(text, t):
                out.append({"term": t, "box": (x0 + a * per, y0, x0 + b * per, y1), "conf": float(conf), "line": text})
    return out


def inside(box, area):
    x0, y0, x1, y1 = area
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return x0 <= cx <= x1 and y0 <= cy <= y1


def area_pick(finds, lines, area):
    """What a box dragged on a picture holds: the finds inside, and the readings inside with no find (the words the
    scan never found), as the reader read them, top to bottom."""
    got = [f for f in finds if inside(f["box"], area)]
    seen = {f["line"] for f in got}
    rest = [(b, t, c) for b, t, c in lines if inside(b, area) and t not in seen]
    rest.sort(key=lambda r: (round(r[0][1] / 12), r[0][0]))
    return got, " ".join(t for _b, t, _c in rest)


def guess_term(text):
    """The word that looks most like a term in what the reader sees (capitals, digits, & or a hyphen)."""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9&/\-\.]*[A-Za-z0-9]|[A-Z]", text or "")
    for w in words:                            # the first one with two or more capitals, digits, & or -
        if sum(1 for c in w if c.isupper() or c.isdigit() or c in "&-") >= 2:
            return w
    return words[0] if words else ""


# ------------------------------------------------------------------ the bar a selection gets
def bar_kind(items, results, cutoff):
    """decide, partial (one term, inside a longer one), doubt (one find read with doubt) or new (words never found)."""
    if not items:
        return None
    if any(x.get("term") is None for x in items):
        return "new"
    terms = sorted({x["term"] for x in items})
    if len(terms) == 1:
        t = terms[0]
        d = results.get(t) or {}
        if P.longer(results, t) and not d.get("part_of"):
            return "partial"
        if len(items) == 1 and items[0].get("conf") is not None and items[0]["conf"] < cutoff:
            return "doubt"
    return "decide"


def type_of(d):
    import app_gui as A
    cat = A.base_type(str(d.get("category", "")))
    for name, _k in TYPES:
        if cat.casefold().startswith(name.casefold()):
            return name
    return cat


def set_type(s, terms, name):
    """The type said on the page (Acronym, Abbreviation, Unit or Symbol); a candidate stays a candidate."""
    n = 0
    for t in terms:
        d = s.results.get(t)
        if d is None:
            continue
        cand = "(Candidate)" in str(d.get("category", ""))
        new = name + (" (Candidate)" if cand else "")
        if d.get("category") != new:
            d["category"] = new
            n += 1
    if n:
        s.save()
    return n


# ------------------------------------------------------------------ Not a term, and back
def before(s, terms):
    """What each term was before Not a term, so Undo can put it back."""
    rows = getattr(s.effort, "rows", {}) if s.effort is not None else {}
    return {t: {"in_list": t in rows, "status": (s.results.get(t) or {}).get("effort"),
                "excluded": bool((s.results.get(t) or {}).get("excluded"))} for t in terms}


def undo_not_term(s, was):
    """Puts each term back as it was before Not a term."""
    for t, w in was.items():
        if s.effort is None:
            s.exclude([t], w["excluded"])
        elif not w["in_list"]:
            s.list_remove([t])
        elif w["status"] and w["status"] != "Not a term":
            s.list_status([t], w["status"])
        if not w["excluded"] and (s.results.get(t) or {}).get("excluded"):
            s.exclude([t], False)
    return len(was)
