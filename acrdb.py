"""This PC's acronym database, from the acronym pages (3.51.0).

The provided database is the foundation; a person adds select items to it, apart from adding them to an effort's
acronym list (usually after submission: the terms worth knowing for every effort).

add_terms(items)            [(term, category, meaning)] added as known meanings (Include rows); counts
exclusion_list()            the Exclusion List: terms never shown in any effort on this PC (database Exclude rows)
exclusion_add(items)        [(term, category, reason)] onto the Exclusion List; a term the database already explains is
                            set to Exclude and remembers that, so taking it off puts its meanings back
exclusion_remove(terms)     off the Exclusion List
Writes go through app_gui's atomic database write; a database open in Excel raises PermissionError. Rules only."""
import app_gui as A

WAS = "Excluded from"            # extra column: the action a row had before it went onto the Exclusion List


def add_terms(items):
    """Adds meanings to the database. Returns {"added", "updated", "same"}."""
    out = {"added": 0, "updated": 0, "same": 0}
    for term, cat, defn in items:
        defn = (defn or "").strip()
        if not term or not defn or defn.startswith("["):
            continue
        st, _row = A.db_add(term, (cat or "Acronym").replace(" (Candidate)", ""), defn, "Include")
        out["added" if st == "added" else "updated" if st == "updated" else "same"] += 1
    return out


def exclusion_list():
    """[(term, category, reason)] on the Exclusion List, sorted."""
    rows = [(r[0], r[1], r[2]) for r in A.read_db_rows() if A._action_kind(r[3]) == "exclude"]
    seen, out = set(), []
    for t, c, d in sorted(rows, key=lambda r: r[0].casefold()):
        if A.fold(t) not in seen:
            seen.add(A.fold(t)); out.append((t, c, d))
    return out


def on_exclusion_list(term):
    ft = A.fold(term)
    return any(A.fold(t) == ft for t, _c, _d in exclusion_list())


def exclusion_add(items):
    """Puts terms on the Exclusion List. Returns how many."""
    rows = A.read_db_rows()
    n = 0
    for term, cat, reason in items:
        ft = A.fold(term)
        mine = [r for r in rows if A.fold(r[0]) == ft]
        if mine:
            for r in mine:
                if A._action_kind(r[3]) != "exclude":
                    r[4] = dict(r[4] if len(r) > 4 and isinstance(r[4], dict) else {}, **{WAS: r[3]})
                    r[3] = "Exclude"
        else:
            rows.append([term, (cat or "Acronym").replace(" (Candidate)", ""), reason or "On the Exclusion List", "Exclude", {}])
        n += 1
    A.write_db_rows(rows)
    return n


def exclusion_remove(terms):
    """Takes terms off the Exclusion List: rows that had meanings get them back; rows made only to exclude go. Returns how many."""
    want = {A.fold(t) for t in terms}
    keep, n = [], 0
    for r in A.read_db_rows():
        if A.fold(r[0]) in want and A._action_kind(r[3]) == "exclude":
            n += 1
            extra = r[4] if len(r) > 4 and isinstance(r[4], dict) else {}
            was = extra.pop(WAS, None)
            if was:
                r[3] = was
                keep.append(r)
        else:
            keep.append(r)
    A.write_db_rows(keep)
    return n
