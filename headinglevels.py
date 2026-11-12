"""The customer's headings, with their levels, in the shred (4.17.0; claude/stationkeeper-documents-replace-delete-plan-4.17.html).
Asked 2026-11-11 17:45: "where in the shred do I assign items as headings ... which items are headers, subheaders and such
since this directly influences the reference where it was found in the compliance matrix and setup".

mark(items, iid, level): the piece is a heading at that level, H1 to H9. Its number and title come
from its words (compliance.parse_header). A heading with no number takes its place under the nearest heading above it
of a higher level: its reference reads "L.3 Page Limits > Technical Approach". Every piece after it in the same file,
up to the next heading, takes its reference (Section and Section title in the matrix).
unmark(items, iid): not a heading after all: it becomes a piece to shred again, and it and the pieces after it take the
reference of the heading above. level_of(it): a heading's level, as marked or from its number.
Rules only (No AI); nothing leaves the PC."""
import compliance as C

NAMES = [(n, f"H{n}") for n in range(1, 10)]          # H1 to H9 (Nicholas 18:04: how the team says it)


def level_of(it):
    if it.get("hlevel"):
        return int(it["hlevel"])
    num = C.parse_header(it.get("text", ""))[0] or (it.get("section", "") if it.get("type") == "Heading" else "")
    if not num:
        return 1
    return max(1, num.count(".") if num[0].isalpha() else num.count(".") + 1)


def _is_head(it):
    """A heading of the customer's: marked so, or a line the reader took for a numbered heading."""
    if it.get("type") == "Heading" or it.get("hlevel"):
        return True
    return it.get("header") == "Yes" and bool(C.parse_header(it.get("text", ""))[0]) and it.get("type") not in ("Aside",)


def _parent(items, i, level):
    f = items[i].get("file", "")
    for it in reversed(items[:i]):
        if it.get("file", "") == f and _is_head(it) and level_of(it) < level:
            return it
    return None


def _flow(items, i, num, title):
    """The pieces after items[i] in its file, up to the next heading, take (num, title). Returns their ids."""
    f, done = items[i].get("file", ""), []
    for it in items[i + 1:]:
        if it.get("file", "") != f:
            continue
        if _is_head(it):
            break
        it["section"], it["section_title"] = num, title
        done.append(it.get("id", ""))
    return done


def mark(items, iid, level):
    """Make the piece a heading at level. Returns the ids whose reference changed."""
    i = next((k for k, it in enumerate(items) if it.get("id") == iid), None)
    if i is None:
        return []
    h = items[i]
    num, title = C.parse_header(h.get("text", ""))
    level = max(1, min(9, int(level)))
    if not num:                                         # an unnumbered heading sits under the one above it: a heading
        par = _parent(items, i, level)                  # marked at a higher level, else the numbered section it is in
        if par is not None:
            base = (par.get("section", ""), par.get("section_title", ""))
        else:
            sib = next((it for it in reversed(items[:i]) if it.get("file") == h.get("file") and it.get("hlevel")
                        and int(it["hlevel"]) == level and it.get("base")), None)
            base = tuple(sib["base"]) if sib is not None else (h.get("section", ""), (h.get("section_title", "") or "").split(" > ")[0])
        h["base"] = list(base)
        num = base[0]
        title = " > ".join(x for x in (base[1], title) if x)
    h.update(type="Heading", header="Yes", hlevel=level, section=num, section_title=title, decision="Drop")
    h.pop("draft", None)
    return _flow(items, i, num, title)


def unmark(items, iid):
    """Not a heading: a piece to shred again; it and the pieces after it take the reference above. Returns the ids."""
    i = next((k for k, it in enumerate(items) if it.get("id") == iid), None)
    if i is None:
        return []
    h = items[i]
    for k in ("hlevel", "base"):
        h.pop(k, None)
    h.update(type="", header="", decision="")
    f = h.get("file", "")
    above = next((it for it in reversed(items[:i]) if it.get("file", "") == f and _is_head(it)), None)
    num, title = (above.get("section", ""), above.get("section_title", "")) if above is not None else ("", "")
    h["section"], h["section_title"] = num, title
    return [h.get("id", "")] + _flow(items, i, num, title)


def register(M, it):
    """Keep a marked heading among the matrix's headings (with its level and page), so Start from the customer's
    headings puts it in the outline, numbered or not."""
    M.headings = [x for x in getattr(M, "headings", []) if x.get("iid") != it.get("id")]
    num, own = C.parse_header(it.get("text", ""))
    M.headings.append({"num": num, "title": own or it.get("text", ""), "file": it.get("file", ""), "level": int(it.get("hlevel") or 1),
                       "page": it.get("page", ""), "iid": it.get("id", ""), "mark": True,
                       "base": (it.get("base") or [""])[0] if not num else ""})


def unregister(M, it):
    M.headings = [x for x in getattr(M, "headings", []) if x.get("iid") != it.get("id")]


def found_under(it):
    return " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
