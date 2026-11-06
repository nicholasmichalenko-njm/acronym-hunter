"""Parts and numbering (3.66.0): for each volume, its parts in order and, for each, how its pages are numbered and
counted. Page format (none, i, I, 1, A-1), where numbering restarts, the chapter style and separator for A-1 (Heading 7
for appendices), the header and footer it uses, orientation and paper, and whether its pages count toward the limit
(with how many pages a foldout counts as and whether blank pages count). Final Check reads the same plan.

Kept in the effort record ("part_plans" {volume: [parts]}). claude/stationkeeper-studio-decisions-2026-11-06.md.
Rules only; nothing leaves the PC."""
import uuid

KINDS = ("Cover", "Front matter", "Body", "Appendix", "Customer form", "Other")
FORMATS = ("none", "i", "I", "1", "A-1")
FORMAT_SAYS = {"none": "No page number", "i": "i, ii, iii", "I": "I, II, III", "1": "1, 2, 3", "A-1": "A-1, A-2 (chapter-page)"}
HEADERS = ("Front matter", "Response", "Appendices", "None", "Its own (customer form)")
ORIENT = ("Portrait", "Landscape")
PAPER = ("Letter", "11x17")
COUNTS = ("Counts", "Does not count")
# Final Check's tick-out kinds a part that does not count stands for
EXCLUDES = {"Cover": ["cover"], "Front matter": ["toc", "acronyms"], "Appendix": ["appendices"], "Customer form": []}


def _id():
    return uuid.uuid4().hex[:8]


def default_parts():
    """The usual volume: a cover, front matter in i, the response in 1 restarting, appendices A-1 on Heading 7."""
    ps = [part("Cover", "Cover", fmt="none", header="None", counts="Does not count"),
          part("Front matter", "Front matter", fmt="i", restart=True, header="Front matter", counts="Does not count"),
          part("Response", "Body", fmt="1", restart=True, header="Response", counts="Counts"),
          part("Appendices", "Appendix", fmt="A-1", restart=True, chapter="Heading 7", header="Appendices", counts="Does not count")]
    for p, i in zip(ps, ("cover", "front", "body", "appendices")):     # fixed ids: a plan not saved yet still names its parts
        p["id"] = i
    return ps


def part(name, kind="Body", fmt="1", restart=False, start=1, chapter="", sep="-", header="Response", orient="Portrait",
         paper="Letter", counts="Counts", foldout=2, blanks="Do not count"):
    return {"id": _id(), "name": " ".join(str(name).split()) or kind, "kind": kind if kind in KINDS else "Other",
            "format": fmt if fmt in FORMATS else "1", "restart": bool(restart), "start": max(1, int(start or 1)),
            "chapter": chapter or ("Heading 7" if fmt == "A-1" else ""), "sep": sep or "-",
            "header": header if header in HEADERS else "Response", "orient": orient if orient in ORIENT else "Portrait",
            "paper": paper if paper in PAPER else "Letter", "counts": counts if counts in COUNTS else "Counts",
            "foldout": max(1, int(foldout or 2)), "blanks": blanks if blanks in ("Count", "Do not count") else "Do not count"}


def plans(rec):
    return rec.data.setdefault("part_plans", {})


def plan_of(rec, volume):
    """The volume's parts, or the usual ones when none are set (not saved until changed)."""
    p = (rec.data.get("part_plans") or {}).get(volume)
    return [dict(x) for x in p] if isinstance(p, list) and p else default_parts()


def _norm(x):
    p = part(x.get("name", ""), x.get("kind", "Body"), x.get("format", "1"), x.get("restart", False), x.get("start", 1),
             x.get("chapter", ""), x.get("sep", "-"), x.get("header", "Response"), x.get("orient", "Portrait"),
             x.get("paper", "Letter"), x.get("counts", "Counts"), x.get("foldout", 2), x.get("blanks", "Do not count"))
    p["id"] = x.get("id") or p["id"]
    return p


def set_plan(rec, volume, parts, who=None):
    plans(rec)[volume] = [_norm(x) for x in parts]
    rec.log("effort", f"Parts and numbering set for {volume}", who=who)
    rec.save()
    return plans(rec)[volume]


def update_part(rec, volume, pid, **fields):
    ps = plan_of(rec, volume)
    for x in ps:
        if x["id"] == pid:
            x.update(fields)
    return set_plan(rec, volume, ps)


def add_part(rec, volume, name, kind="Body", after=None):
    ps = plan_of(rec, volume)
    p = part(name, kind)
    i = next((n + 1 for n, x in enumerate(ps) if x["id"] == after), len(ps))
    ps.insert(i, p)
    set_plan(rec, volume, ps)
    return p["id"]


def remove_part(rec, volume, pid):
    ps = [x for x in plan_of(rec, volume) if x["id"] != pid]
    set_plan(rec, volume, ps)
    return True


def move_part(rec, volume, pid, step):
    ps = plan_of(rec, volume)
    i = next((n for n, x in enumerate(ps) if x["id"] == pid), None)
    if i is None or not (0 <= i + step < len(ps)):
        return False
    ps[i], ps[i + step] = ps[i + step], ps[i]
    set_plan(rec, volume, ps)
    return True


def page_label(p, n):
    """How page n (1-based within the part) reads: 'iii', '3', 'A-3'."""
    f = p.get("format")
    k = n + (int(p.get("start") or 1) - 1)
    if f == "none":
        return ""
    if f in ("i", "I"):
        r = _roman(k)
        return r if f == "I" else r.lower()
    if f == "A-1":
        return f"A{p.get('sep') or '-'}{k}"
    return str(k)


def _roman(n):
    out = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"),
                 (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s; n -= v
    return out


def says(p):
    """One line for a part: 'Response: 1, 2, 3 restarting at 1; Response header; counts'."""
    bits = [FORMAT_SAYS.get(p["format"], p["format"])]
    if p["format"] != "none" and p.get("restart"):
        bits[-1] += f" restarting at {page_label(p, 1)}"
    if p["format"] == "A-1":
        bits.append(f"chapter from {p.get('chapter') or 'Heading 7'}")
    bits.append(f"{p['header']} header and footer" if p["header"] not in ("None",) else "no header or footer")
    if p["orient"] != "Portrait" or p["paper"] != "Letter":
        bits.append(f"{p['orient'].lower()} {p['paper']}")
    bits.append("counts toward the limit" if p["counts"] == "Counts" else "does not count")
    return f"{p['name']}: " + "; ".join(bits)


def final_check_rules(rec, volume):
    """What Final Check reads: {"exclude": [tick-out kinds], "foldout": pages an 11x17 sheet counts as, "blanks": bool
    (blank pages count)}. Only from a plan the person set."""
    p = (rec.data.get("part_plans") or {}).get(volume)
    if not (isinstance(p, list) and p):
        return None
    ex = []
    for x in p:
        if x["counts"] != "Counts":
            ex += EXCLUDES.get(x["kind"], [])
    blanks = any(x.get("blanks") == "Count" for x in p if x["counts"] == "Counts")
    if not blanks:
        ex.append("dividers")
    fold = max([x.get("foldout", 2) for x in p if x.get("paper") == "11x17" and x["counts"] == "Counts"] or [2])
    return {"exclude": list(dict.fromkeys(ex)), "foldout": fold, "blanks": blanks}
