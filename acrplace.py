"""Not a term, in this place only (4.26.1; Nicholas 2026-11-12, the sixth answers, 3: "Not a term dismisses this place
only by default; everywhere in this effort (n) is the second choice"). The S read out of DEFENSE on one page is not a
term there; a real S elsewhere in the effort stays found. This uses the effort's excluded instances (kept in the
effort's working data since 2.13.0 and applied after every scan), keyed by the page. Standard library only."""
import acrpages as AG


def here(s, term, key):
    """The term's places on the page key."""
    d = s.results.get(term) or {}
    return [l for l in d.get("locations", []) if AG.place_of(l) == key]


def places(s, term):
    """How many places the term is found in, over the effort."""
    return len((s.results.get(term) or {}).get("locations", []))


def not_here(s, terms, key):
    """Each term is not a term on this page. Returns {term: [the places taken out]} for Undo."""
    was = {}
    for t in terms:
        took = [l for l in here(s, t, key) if s.exclude_instance(t, l)]
        if took:
            was[t] = took
    if was:
        s.save()
    return was


def undo(s, was):
    """Puts back the places not_here took out. Returns how many."""
    n = 0
    ex = s.ws.instance_excludes()
    for t, locs in (was or {}).items():
        d = s.results.get(t)
        ex[t] = [l for l in ex.get(t, []) if l not in locs]
        if d is None:
            continue
        for l in locs:
            if l not in d.setdefault("locations", []):
                d["locations"].append(l)
                d["count"] = int(d.get("count", 0)) + 1
                n += 1
        d["excluded_instances"] = [l for l in d.get("excluded_instances", []) if l not in locs]
        if not d["excluded_instances"]:
            d.pop("excluded_instances", None)
        pre = d.pop("_pre_instances", None)
        if pre is not None:                       # every place had been taken out: the term is back as it was
            d["excluded"] = False
            d["status"], d["selected_definition"] = pre[0], pre[1]
    s.ws.save_instance_excludes(ex)
    s.save()
    return n


def combined(items):
    """The one term several finds side by side spell (U and S: US; the letters of a spaced title). Finds on a picture
    are read left to right on their line and joined with no space when they touch, with a space when they stand apart;
    finds in typed text are joined in reading order the same way, by what lies between them."""
    its = [x for x in items if x.get("term")]
    if len(its) < 2:
        return its[0]["term"] if its else ""
    if all("box" in x for x in its):
        its = sorted(its, key=lambda x: (round(x["box"][1] / max(1.0, (x["box"][3] - x["box"][1]) * 0.6)), x["box"][0]))
        out = its[0]["term"]
        for a, b in zip(its, its[1:]):
            h = max(1.0, a["box"][3] - a["box"][1])
            gap = b["box"][0] - a["box"][2]
            out += ("" if gap < 0.45 * h else " ") + b["term"]
        return out
    if all("span" in x for x in its):
        its = sorted(its, key=lambda x: x["span"][0])
        out = its[0]["term"]
        for a, b in zip(its, its[1:]):
            out += ("" if b["span"][0] - a["span"][1] <= 0 else " ") + b["term"]
        return out
    return " ".join(x["term"] for x in its)
