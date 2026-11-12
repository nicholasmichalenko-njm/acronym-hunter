"""Sections and numbering (3.66.0): for each volume, its parts in order and, for each, how its pages are numbered and
counted. Page format (none, i, I, 1, A-1), where numbering restarts, the chapter style and separator for A-1 (Heading 7
for appendices), the header and footer it uses, orientation and paper, and whether its pages count toward the limit
(with how many pages a foldout counts as and whether blank pages count). Final Check reads the same plan.

3.68.0: a Customer form part is locked: the customer's own form, placed where the plan puts it, counted as the plan
says and checked for its marking, never restyled. It names the form's file and the marking its pages carry; Fix a Copy
refuses a fix that would change it, Apply in Word leaves it alone, Final Check finds its pages.

Kept in the effort record ("part_plans" {volume: [parts]}). claude/stationkeeper-studio-decisions-2026-11-06.md.
Rules only; nothing leaves the PC."""
import os, uuid

KINDS = ("Cover", "Front matter", "Body", "Appendix", "Customer form", "Other")
FORMATS = ("none", "i", "I", "1", "A-1")
FORMAT_SAYS = {"none": "No page number", "i": "i, ii, iii", "I": "I, II, III", "1": "1, 2, 3", "A-1": "A-1, A-2 (chapter-page)"}
HEADERS = ("Front matter", "Response", "Appendices", "None", "Its own (customer form)")
ORIENT = ("Portrait", "Landscape")
PAPER = ("Letter", "11x17")
COUNTS = ("Counts", "Does not count")
# Final Check's tick-out kinds a part that does not count stands for
EXCLUDES = {"Cover": ["cover"], "Front matter": ["toc", "acronyms"], "Appendix": ["appendices"], "Customer form": []}
LOCKED = "Customer form"


def locked(p):
    """A customer's form: placed, counted and checked, never restyled."""
    return (p or {}).get("kind") == LOCKED


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
         paper="Letter", counts="Counts", foldout=2, blanks="Do not count", form="", marking=""):
    return {"form": str(form or ""), "marking": " ".join(str(marking or "").split()),
            "id": _id(), "name": " ".join(str(name).split()) or kind, "kind": kind if kind in KINDS else "Other",
            "format": fmt if fmt in FORMATS else "1", "restart": bool(restart), "start": max(1, int(start or 1)),
            "chapter": chapter or ("Heading 7" if fmt == "A-1" else ""), "sep": sep or "-",
            "header": header if header in HEADERS else "Response", "orient": orient if orient in ORIENT else "Portrait",
            "paper": paper if paper in PAPER else "Letter", "counts": counts if counts in COUNTS else "Counts",
            "foldout": max(1, int(foldout or 2)), "blanks": blanks if blanks in ("Count", "Do not count") else "Do not count"}


def plans(rec):
    return rec.data.setdefault("part_plans", {})


def plan_of(rec, volume, shared=None):
    """The volume's parts: this effort's own, else the shared plan for its effort type or every effort (3.68.0), else
    the usual ones (not saved until changed)."""
    p = (rec.data.get("part_plans") or {}).get(volume)
    if isinstance(p, list) and p:
        return [dict(x) for x in p]
    if shared:
        return [_norm(x) for x in shared]
    return default_parts()


def own(rec, volume):
    """True when this effort holds its own plan for the volume."""
    p = (rec.data.get("part_plans") or {}).get(volume)
    return isinstance(p, list) and bool(p)


# ---------------------------------------------------------------- 3.68.0: save to this effort, its effort type, or every effort
SHARED = "part_plans.json"          # in the config folder: {"team": {profile id: parts}, "types": {effort type id: {profile id: parts}}}
WHERE = (("effort", "This effort only"), ("type", "Every effort of this effort type"), ("team", "Every effort"))


def load_shared(config_dir):
    import json
    try:
        with open(os.path.join(config_dir, SHARED), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    return {"team": dict(d.get("team") or {}), "types": dict(d.get("types") or {})}


def _save_shared(config_dir, d):
    import json
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, SHARED)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def shared_plan(config_dir, eid, pid):
    """The plan shared for this effort type and volume profile, else the one for every effort, else None."""
    d = load_shared(config_dir)
    return ((d["types"].get(eid or "") or {}).get(pid or "")) or d["team"].get(pid or "") or None


def shared_from(config_dir, eid, pid):
    """Where a shared plan comes from: 'type', 'team' or ''."""
    d = load_shared(config_dir)
    if (d["types"].get(eid or "") or {}).get(pid or ""):
        return "type"
    return "team" if d["team"].get(pid or "") else ""


def save_to(config_dir, rec, volume, parts, where="effort", eid=None, pid=None, who=None):
    """Saves the plan where the person chose. A broader save is kept by the volume profile; this effort then follows
    it (its own plan for the volume is cleared), and efforts with their own plan keep theirs."""
    parts = [_norm(x) for x in parts]
    if where == "effort" or not pid:
        return set_plan(rec, volume, parts, who=who)
    d = load_shared(config_dir)
    if where == "type" and eid:
        d["types"].setdefault(eid, {})[pid] = parts
    else:
        d["team"][pid] = parts
    _save_shared(config_dir, d)
    plans(rec).pop(volume, None)
    rec.log("effort", f"Sections and numbering for {volume} saved for " + ("every effort of its effort type" if where == "type" and eid
                                                                          else "every effort"), who=who)
    rec.save()
    return parts


def impact(efforts, where, eid=None):
    """What a save would change. efforts: [{"name", "eid", "own": volumes with their own plan}]. Returns
    {"efforts": n that follow it, "keep": n with their own plan, which keep it}."""
    hit = [e for e in efforts if where == "team" or (where == "type" and e.get("eid") == eid)] if where != "effort" else []
    keep = sum(1 for e in hit if e.get("own"))
    return {"efforts": len(hit), "keep": keep}


def efforts_on_pc(config_dir):
    """Every effort on this PC: [{"name", "eid", "own": [volumes with their own plan]}], read from each effort's files."""
    import effort as E, effortrec as RR, workspace as W
    out = []
    reg = E.Registry(os.path.join(config_dir, "efforts.json"))
    for name in reg.names():
        path = (reg.get(name) or {}).get("path") or ""
        if not path or not os.path.isdir(W.data_dir_for(path)):
            continue                                         # an effort whose folder is gone, or not opened yet
        try:
            ws = W.Workspace(W.data_dir_for(path), name)
            eid = (ws.get("prod_std", {}) or {}).get("effort_type") or ""
            own_ = [k for k, v in (RR.Record(ws.root).data.get("part_plans") or {}).items() if v]
        except Exception:  # noqa: BLE001  an effort whose folder is gone
            continue
        out.append({"name": name, "eid": eid, "own": own_})
    return out


def _norm(x):
    p = part(x.get("name", ""), x.get("kind", "Body"), x.get("format", "1"), x.get("restart", False), x.get("start", 1),
             x.get("chapter", ""), x.get("sep", "-"), x.get("header", "Response"), x.get("orient", "Portrait"),
             x.get("paper", "Letter"), x.get("counts", "Counts"), x.get("foldout", 2), x.get("blanks", "Do not count"),
             x.get("form", ""), x.get("marking", ""))
    p["id"] = x.get("id") or p["id"]
    return p


def set_plan(rec, volume, parts, who=None):
    plans(rec)[volume] = [_norm(x) for x in parts]
    rec.log("effort", f"Sections and numbering set for {volume}", who=who)
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
    if locked(p):
        bits.append("the customer's form, kept as it is" + (f", marked {p['marking']!r}" if p.get("marking") else ""))
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
    forms = [{"name": x["name"], "form": x.get("form", ""), "marking": x.get("marking", ""), "counts": x["counts"] == "Counts"}
             for x in p if locked(x)]
    return {"exclude": list(dict.fromkeys(ex)), "foldout": fold, "blanks": blanks, "forms": forms}


def parts_for_file(plans_, name):
    """(volume, parts) of the plan whose volume this file is, by its name; (None, None) when no plan is set for it."""
    import subreq as SR
    stem = os.path.splitext(os.path.basename(name or ""))[0]
    key = next((k for k in (plans_ or {}) if k == stem or SR.match_volume(k, stem)), None)
    if key is None:
        return None, None
    return key, [_norm(x) for x in plans_[key]]


def effective_plans(config_dir, rec, eid=None, data=None):
    """{volume: parts} as this effort uses them: a plan shared for its effort type (or every effort), by each volume
    its profiles make, then the effort's own plans over them. Final Check, Fix a Copy and Apply in Word read this."""
    out = {}
    if config_dir and os.path.isfile(os.path.join(config_dir, SHARED)):
        import effortprofiles as EP
        if data is None:
            import prodrules as PRL
            data = PRL.load(config_dir)
        for p in EP.profiles(data):
            if eid and p["eid"] != eid:
                continue
            sp = shared_plan(config_dir, eid or p["eid"], p["pid"])
            if sp:
                for v in p["volumes"]:
                    out.setdefault(v, [_norm(x) for x in sp])
    out.update({k: v for k, v in (rec.data.get("part_plans") or {}).items() if isinstance(v, list) and v})
    return out


def for_effort(config_dir, ws):
    """effective_plans for an open effort (its workspace)."""
    if ws is None:
        return {}
    import effortrec as RR
    eid = (ws.get("prod_std", {}) or {}).get("effort_type") or None
    return effective_plans(config_dir, RR.Record(ws.root), eid)
