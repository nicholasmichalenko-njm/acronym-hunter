"""Why is a term not listed? (3.61.0) One term in, the reasons out, in plain words, from what is on this PC: the
Exclusion List, Omit in this effort, a plural or form you set, the omit list, places excluded one by one, the filters,
and whether the last scan read the term at all (typed text or a picture).

why(session, term, shown=None) -> {"verdict": str, "reasons": [str], "read": {"typed": n, "picture": n},
                                    "near": [str]}
Rules only; nothing leaves the PC."""
import re

import app_gui as A


def _db_rule(term):
    try:
        _inc, exc, exc_up = A.load_database()
    except Exception:  # noqa: BLE001  a locked or missing database: say nothing about it
        return None
    if A.fold(term) in exc:
        return f"{term} is on this PC's Exclusion List, so no effort shows it. Team References > Exclusion List takes it off."
    if term.upper() in exc_up:
        hit = next((k for k in exc if k.upper() == term.upper()), term.upper())
        return (f"The Exclusion List has {hit}, and the list ignores capital letters for codes with numbers, so {term} is left "
                f"out too. Team References > Exclusion List takes it off.")
    return None


def _picture(label):
    return A.loc_kind(label) == "figure" or bool(re.search(r"\((?:p\.\d+|Image|Vector graphic)\)|, (?:image|vector) ", label))


def scan_reads(session, term):
    """How often the last scan's text holds the term exactly, and near misses read in pictures (one letter off)."""
    cache = ((getattr(session, "last_scan", None) or {}).get("cache") or {})
    read = {"typed": 0, "picture": 0}
    other_case, near = set(), set()
    t_low = term.casefold()
    pat = re.compile(r"(?<![\w&])" + re.escape(term) + r"(?![\w&])")
    for entry in cache.values():
        for label, text in entry.get("chunks") or []:
            n = len(pat.findall(text or ""))
            read["picture" if _picture(label) else "typed"] += n
            for tok in re.findall(r"[\w&/-]+", text or ""):
                if tok != term and tok.casefold() == t_low:
                    other_case.add(tok)
                elif _picture(label) and len(tok) == len(term) and len(term) >= 2 and \
                        sum(a != b for a, b in zip(tok.upper(), term.upper())) == 1:
                    near.add(tok)
    return read, sorted(other_case), sorted(near)[:8]


def why(session, term, shown=None):
    term = (term or "").strip()
    out = {"verdict": "", "reasons": [], "read": {"typed": 0, "picture": 0}, "near": []}
    if not term:
        out["verdict"] = "Type the term you expected to see."
        return out
    r = out["reasons"]
    res = getattr(session, "results", None) or {}
    d = res.get(term)
    if d is not None:
        if term in (getattr(session, "omitted", None) or {}):
            r.append(f"{term} is omitted in this effort (Omit). Tick Show omitted, select it and choose Bring back.")
        elif d.get("excluded") and "DB RULE" in (d.get("status") or "").upper():
            r.append(_db_rule(term) or f"{term} is on this PC's Exclusion List.")
        elif d.get("excluded"):
            r.append(f"{term} is left out of this effort ({d.get('status') or 'excluded'}). Tick Show omitted to see it.")
        if d.get("plural_of"):
            r.append(f"You set {term} as the plural of {d['plural_of']}: it is listed with {d['plural_of']}. Tick Show plurals and forms.")
        if d.get("form_of"):
            r.append(f"You set {term} as a form of {d['form_of']}: it is listed with {d['form_of']}. Tick Show plurals and forms.")
        if d.get("gone"):
            r.append(f"{term} was found before but not in the last scan of these files.")
        if shown is not None and term not in shown and not r:
            r.append(f"{term} is in the results; the filters above hide it. Set the filters back to All and clear the search.")
        try:
            ex = session.ws.instance_excludes().get(term) or []
        except Exception:  # noqa: BLE001  no effort folder
            ex = []
        if ex:
            r.append(f"{len(ex)} place(s) of {term} were excluded one by one in this effort.")
        out["verdict"] = (f"{term} is listed." if not r else f"{term} was found and is held back.")
        out["read"] = {"typed": len([x for x in d.get("locations", []) if not _picture(x)]),
                       "picture": len([x for x in d.get("locations", []) if _picture(x)])}
        return out
    rule = _db_rule(term)
    if rule:
        r.append(rule)
    read, other_case, near = scan_reads(session, term)
    out["read"], out["near"] = read, near
    if read["typed"] or read["picture"]:
        r.append(f"The last scan read {term} {read['typed']} time(s) in typed text and {read['picture']} time(s) in pictures, "
                 "but the finding rules did not take it as a term (a common word, too short, or lower case). Add it by hand "
                 "to keep it.")
    elif other_case:
        r.append(f"The last scan read it only as {', '.join(other_case[:4])} (other capital letters).")
    elif not getattr(session, "last_scan", None):
        r.append("There is no scan in this session to look in. Scan the files, then ask again.")
    else:
        r.append(f"The last scan never read {term} in these files.")
        if near:
            r.append("In pictures it read: " + ", ".join(near) + ". If one of these is the term, open that picture in the "
                     "preview, click the box and Fix the reading.")
        else:
            r.append("If it is in a picture, the picture may be too small or faint to read; the preview shows every reading.")
    out["verdict"] = f"{term} is not in the results."
    return out
