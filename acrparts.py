"""Part of a longer term (3.76.0): VW is part of MOC-VW where they sit together.

The person says a find is part of a longer term. The decision holds where it sits: every later scan of this effort joins
the part to the whole at the places where it was decided (a file and its page or slide); a VW found on its own
elsewhere still shows. The whole term takes the row, and the part's finds there count for it. Effort-scoped: kept with
the effort's scan (session.json), never on this PC for other efforts.
Rules only (No AI); nothing leaves the PC."""
import re

PART = "Part of"
_SPLIT = re.compile(r"[-/\s_.&]+")


def place(loc):
    """The file and page part of a location ('Spec.pdf p.3 (figure 2)' -> 'spec.pdf p.3'): where two finds sit together."""
    t = re.sub(r"\s*\[OCR fix:[^\]]*\]", "", str(loc or "")).strip()
    m = re.match(r"^(.*?\b(?:p\.|page|slide|sheet|para\.?|line)\s*\d+)", t, re.I)
    return (m.group(1) if m else t).casefold()


def longer_forms(results, part):
    """Terms the scan found that hold the part as a piece (MOC-VW for VW), the ones sharing a place first."""
    if not part:
        return []
    mine = {place(l) for l in (results.get(part) or {}).get("locations", [])}
    out = []
    for t, d in results.items():
        if t == part or len(t) <= len(part):
            continue
        pieces = [p for p in _SPLIT.split(t) if p]
        if part not in pieces:
            continue
        shared = len(mine & {place(l) for l in d.get("locations", [])})
        out.append((-shared, t))
    return [t for _n, t in sorted(out)]


def set_part(s, part, whole, places=None):
    """part sits inside whole at places (default: every place the part is found now). Returns True when set."""
    whole = " ".join((whole or "").split())
    d = s.results.get(part)
    if not part or not whole or whole == part or d is None:
        return False
    keep = sorted({place(l) for l in (places if places is not None else d.get("locations", []))})
    parts = dict(getattr(s, "parts", {}) or {})
    old = parts.get(part) or {}
    parts[part] = {"whole": whole, "places": sorted(set(keep) | set(old.get("places", []) if old.get("whole") == whole else []))}
    s.parts = parts
    apply_parts(s)
    s.save()
    return True


def clear_part(s, part):
    parts = dict(getattr(s, "parts", {}) or {})
    if parts.pop(part, None) is None:
        return False
    s.parts = parts
    d = s.results.get(part)
    if d is not None:
        d.pop("part_of", None)
        if str(d.get("status", "")).startswith(PART):
            d["status"] = "Needs Review"
    s.save()
    return True


def apply_parts(s):
    """After every scan: the part's finds at the decided places move to the whole (made a term when the scan did not
    find it whole); the part keeps its other finds, or is tied to the whole when none are left."""
    parts = getattr(s, "parts", None) or {}
    for part, rule in parts.items():
        d = s.results.get(part)
        whole, where = rule.get("whole", ""), set(rule.get("places", []))
        if d is None or not whole:
            continue
        locs = d.get("locations", [])
        moved = [l for l in locs if place(l) in where]
        if not moved:
            continue
        rest = [l for l in locs if place(l) not in where]
        wd = s.results.get(whole)
        if wd is None:
            wd = {k: v for k, v in d.items() if k not in ("part_of", "selected_definition", "excluded", "status", "effort",
                                                        "known", "plural_of", "form_of", "alt_of", "definitions")}
            wd.update(locations=[], count=0, definitions=[], status="Needs Review", from_parts=True)
            s.results[whole] = wd
            s.manual_items[whole] = dict(wd)
        for l in moved:
            if l not in wd.setdefault("locations", []):
                wd["locations"].append(l)
        share = round(int(d.get("count") or 0) * len(moved) / max(1, len(locs)))
        wd["count"] = int(wd.get("count") or 0) + max(1, share)
        if rest:
            d["locations"] = rest
            d["count"] = max(1, int(d.get("count") or 0) - share)
            d.pop("part_of", None)
        else:
            d["part_of"] = whole
            d["status"] = f"{PART} {whole}"
    return parts
