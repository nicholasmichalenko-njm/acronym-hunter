"""Set as first use (3.51.0): the person says which place counts as an acronym's first use in a file, when the first
place it appears is not where it should be defined (a title, a heading the reader skims, a list). Table of contents
entries never count (app_gui.loc_kind 'toc').

overrides live in the session ({term: {file name: location}}), kept for every later check of that effort or tool.
apply(results, overrides, path_of) rewrites each overridden term's first use for that file before the report is built:
the chosen place, whether the acronym is defined there ("Spelled Out Words (ACR)"), and where else it is spelled out.
Rules only; the files are only read."""
import re

import app_gui as A


def _text_at(path, loc, cache):
    """The typed text of one place (a passage label as the scan writes it), or None."""
    if path not in cache:
        try:
            cache[path] = dict(A.typed_chunks(path))
        except Exception:  # noqa: BLE001  a file that cannot be read keeps the scan's first use
            import diag
            diag.swallowed()
            cache[path] = {}
    return cache[path].get(loc)


def first_use_at(term, text, loc):
    """The first-use record for a chosen place: {"loc", "defined", "lf"}."""
    pat = re.escape(term) + r"s?"
    mt = re.search(r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z0-9])", text or "")
    defined = bool(mt) and (text[max(0, mt.start() - 1):mt.start()] == "(")
    u = {"loc": loc, "defined": defined, "chosen": True}
    if defined:
        u["lf"] = A._long_form_before(term, text, mt.start() - 1)
    return u


def apply(results, overrides, path_of):
    """Rewrites results[term]["first_use"][file] for every override whose place can be read. Returns how many."""
    cache, n = {}, 0
    for term, per_file in (overrides or {}).items():
        d = results.get(term)
        if not d:
            continue
        for fname, loc in (per_file or {}).items():
            path = path_of(fname)
            text = _text_at(path, loc, cache) if path else None
            if text is None:
                continue
            old = (d.setdefault("first_use", {}) or {}).get(fname) or {}
            u = first_use_at(term, text, loc)
            others = [old.get("loc")] if old.get("defined") and old.get("loc") != loc else []
            others += [r for r in old.get("redefs", []) if r != loc]
            if old.get("later") and old.get("later") != loc:
                others.append(old["later"])
            others = list(dict.fromkeys(x for x in others if x))
            if u["defined"]:
                if others:
                    u["redefs"] = others[:5]
            elif others:
                u["later"] = others[0]
            d["first_use"][fname] = u
            n += 1
    return n


def set_first_use(overrides, term, loc):
    """Records the chosen place (file name taken from the place). Returns the overrides."""
    fname = A._file_of(loc)
    overrides.setdefault(term, {})[fname] = loc
    return overrides


def clear_first_use(overrides, term, fname=None):
    if term in overrides:
        if fname:
            overrides[term].pop(fname, None)
        if not fname or not overrides[term]:
            overrides.pop(term, None)
    return overrides
