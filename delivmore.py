"""More on each deliverable (3.62.0): its own page's content, kept in the effort record with the deliverable.

- Format groups: the formatting and submission values shared by deliverables of the same kind (set once per group);
  any deliverable can set its own value for one field, which wins.
- Parts: who writes what. A volume deliverable's parts are its Structure volume's sections (their leads and
  contributors come from Setup); any deliverable can carry parts of its own, each with an owner and an optional section.
- Attachments: the named files it carries, each from the customer or ours.
- References: documents or items that matter to it, with a note on why.
- Discussion: dated notes with the writer's name, filter by person, pin; each one also goes in the effort's timeline.
- Dates: its due date and its own dates, on the effort's calendar.
- Order: the team's own order of the deliverables (drag in Arrange).
Rules only (No AI); nothing leaves the PC."""
import datetime

FIELDS = (("format", "File format"), ("limit", "Page limit"), ("font", "Font and size"), ("margins", "Margins"),
          ("spacing", "Line spacing"), ("paper", "Paper and orientation"), ("naming", "File name"),
          ("submit_how", "How it is sent"), ("submit_when", "When it is due"), ("copies", "Copies"))
SOURCES = ("Customer", "Ours")


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(s):
    return " ".join((s or "").split())


def _id():
    import effortrec as ER
    return ER._id()


def _who(who):
    import effortrec as ER
    return ER._who(who)


def _d(rec, did):
    import deliverables as DL
    return DL.get(rec, did)


# ------------------------------------------------------------------ format groups
def groups(rec):
    return rec.data.setdefault("format_groups", [])


def group(rec, gid):
    return next((g for g in groups(rec) if g["id"] == gid), None)


def add_group(rec, name, values=None, who=None):
    name = _clean(name)
    if not name or any(g["name"].casefold() == name.casefold() for g in groups(rec)):
        return None
    g = {"id": _id(), "name": name, "values": {k: _clean(v) for k, v in (values or {}).items() if k in dict(FIELDS) and _clean(v)}}
    groups(rec).append(g)
    rec.log("deliverable", f"Format group added: {name}", who=who)
    rec.save()
    return g["id"]


def set_group_value(rec, gid, field, value, who=None):
    g = group(rec, gid)
    if g is None or field not in dict(FIELDS):
        return False
    v = _clean(value)
    if v:
        g["values"][field] = v
    else:
        g["values"].pop(field, None)
    rec.save()
    return True


def rename_group(rec, gid, name):
    g, name = group(rec, gid), _clean(name)
    if g is None or not name:
        return False
    g["name"] = name
    rec.save()
    return True


def remove_group(rec, gid, who=None):
    g = group(rec, gid)
    if g is None:
        return False
    groups(rec).remove(g)
    import deliverables as DL
    for d in DL.items(rec):
        if d.get("group") == gid:
            d["group"] = ""
    rec.log("deliverable", f"Format group removed: {g['name']}", who=who)
    rec.save()
    return True


def set_group(rec, did, gid, who=None):
    d = _d(rec, did)
    if d is None or (gid and group(rec, gid) is None):
        return False
    d["group"] = gid or ""
    rec.save()
    return True


def set_own(rec, did, field, value):
    """This deliverable's own value for one field (wins over its group); '' gives the field back to the group."""
    d = _d(rec, did)
    if d is None or field not in dict(FIELDS):
        return False
    own = d.setdefault("own", {})
    v = _clean(value)
    if field in ("format", "limit"):                 # the deliverable's long-standing fields
        d[field] = v
        own.pop(field, None)
        if v:
            own[field] = v
    elif v:
        own[field] = v
    else:
        own.pop(field, None)
    rec.save()
    return True


def effective(rec, d):
    """[(field, label, value, where)]: where is "this deliverable", "group <name>" or "" (not set)."""
    g = group(rec, d.get("group", "")) if d.get("group") else None
    own = dict(d.get("own") or {})
    for k in ("format", "limit"):
        if d.get(k) and k not in own:
            own[k] = d[k]
    out = []
    for k, lab in FIELDS:
        if own.get(k):
            out.append((k, lab, own[k], "this deliverable"))
        elif g and g["values"].get(k):
            out.append((k, lab, g["values"][k], f"group {g['name']}"))
        else:
            out.append((k, lab, "", ""))
    return out


def value(rec, d, field):
    return next((v for k, _l, v, _w in effective(rec, d) if k == field), "")


# ------------------------------------------------------------------ parts
def add_part(rec, did, name, owner="", with_="", section="", who=None):
    d, name = _d(rec, did), _clean(name)
    if d is None or not name:
        return None
    p = {"id": _id(), "name": name, "owner": _clean(owner), "with": _clean(with_), "section": _clean(section)}
    d.setdefault("parts", []).append(p)
    rec.log("deliverable", f"Part added to {d['name']}: {name}" + (f" (owner {p['owner']})" if p["owner"] else ""),
            ref={"deliverable": did}, who=who)
    rec.save()
    return p["id"]


def update_part(rec, did, pid, **fields):
    d = _d(rec, did)
    p = next((x for x in (d or {}).get("parts", []) if x["id"] == pid), None)
    if p is None:
        return False
    for k in ("name", "owner", "with", "section"):
        if k in fields:
            p[k] = _clean(fields[k])
    rec.save()
    return True


def remove_part(rec, did, pid):
    d = _d(rec, did)
    ps = (d or {}).get("parts", [])
    p = next((x for x in ps if x["id"] == pid), None)
    if p is None:
        return False
    ps.remove(p)
    rec.save()
    return True


def structure_parts(d, M):
    """[(section label, lead, contributors)] of the deliverable's Structure volume, from Setup's people."""
    if M is None or not d.get("volume"):
        return []
    import outline_ops as O
    import setupdoc as SD
    out = []
    for lab in O.in_volume(M, d["volume"]):
        if lab == d["volume"]:
            continue
        p = SD.section_people(M, lab)
        out.append((lab, p.get("lead", ""), p.get("with", "")))
    return out


def people(d, M=None):
    """Everyone on the deliverable: its owner, its parts' owners and contributors, its Structure sections' people."""
    names = [d.get("owner", "")]
    for p in d.get("parts", []):
        names += [p.get("owner", "")] + [x.strip() for x in (p.get("with") or "").split(",")]
    for _lab, lead, with_ in structure_parts(d, M):
        names += [lead] + [x.strip() for x in (with_ or "").split(",")]
    seen, out = set(), []
    for n in names:
        if n and n.casefold() not in seen:
            seen.add(n.casefold()); out.append(n)
    return out


# ------------------------------------------------------------------ attachments and references
def add_attachment(rec, did, name, source="Ours", file="", note="", who=None):
    d, name = _d(rec, did), _clean(name)
    if d is None or not name:
        return None
    a = {"id": _id(), "name": name, "source": source if source in SOURCES else "Ours", "file": (file or "").strip(),
         "note": (note or "").strip(), "added": _now()}
    d.setdefault("attachments", []).append(a)
    rec.log("deliverable", f"Attachment on {d['name']}: {name} ({a['source'].lower()})", ref={"deliverable": did}, who=who)
    rec.save()
    return a["id"]


def remove_attachment(rec, did, aid):
    d = _d(rec, did)
    xs = (d or {}).get("attachments", [])
    a = next((x for x in xs if x["id"] == aid), None)
    if a is None:
        return False
    xs.remove(a)
    rec.save()
    return True


def add_reference(rec, did, label, where="", note="", who=None):
    d, label = _d(rec, did), _clean(label)
    if d is None or not label:
        return None
    r = {"id": _id(), "label": label, "where": (where or "").strip(), "note": (note or "").strip(), "added": _now()}
    d.setdefault("references", []).append(r)
    rec.save()
    return r["id"]


def remove_reference(rec, did, rid):
    d = _d(rec, did)
    xs = (d or {}).get("references", [])
    r = next((x for x in xs if x["id"] == rid), None)
    if r is None:
        return False
    xs.remove(r)
    rec.save()
    return True


# ------------------------------------------------------------------ discussion
def post(rec, did, text, who=None, when=None):
    d, text = _d(rec, did), (text or "").strip()
    if d is None or not text:
        return None
    e = {"id": _id(), "text": text, "by": _who(who), "at": when or _now(), "pinned": False}
    d.setdefault("discussion", []).append(e)
    rec.log("deliverable", f"Discussion on {d['name']}: {text[:70]}", ref={"deliverable": did, "post": e["id"]}, who=who)
    rec.save()
    return e["id"]


def pin(rec, did, eid, on=True):
    d = _d(rec, did)
    e = next((x for x in (d or {}).get("discussion", []) if x["id"] == eid), None)
    if e is None:
        return False
    e["pinned"] = bool(on)
    rec.save()
    return True


def remove_post(rec, did, eid):
    d = _d(rec, did)
    xs = (d or {}).get("discussion", [])
    e = next((x for x in xs if x["id"] == eid), None)
    if e is None:
        return False
    xs.remove(e)
    rec.save()
    return True


def discussion(d, person="", newest_first=True):
    """The deliverable's notes: pinned first, then by date; only one person's when person is given."""
    xs = [e for e in d.get("discussion", []) if not person or (e.get("by") or "").casefold() == person.casefold()]
    xs.sort(key=lambda e: e.get("at", ""), reverse=newest_first)
    return [e for e in xs if e.get("pinned")] + [e for e in xs if not e.get("pinned")]


def writers(d):
    return sorted({e.get("by") for e in d.get("discussion", []) if e.get("by")}, key=str.casefold)


# ------------------------------------------------------------------ dates
def add_date(rec, did, date, what, who=None):
    d, what = _d(rec, did), _clean(what)
    if d is None or not what or len(date or "") < 10:
        return None
    x = {"id": _id(), "date": date[:10], "what": what}
    d.setdefault("dates", []).append(x)
    rec.log("deliverable", f"Date on {d['name']}: {what} {date[:10]}", ref={"deliverable": did}, who=who)
    rec.save()
    return x["id"]


def remove_date(rec, did, xid):
    d = _d(rec, did)
    xs = (d or {}).get("dates", [])
    x = next((y for y in xs if y["id"] == xid), None)
    if x is None:
        return False
    xs.remove(x)
    rec.save()
    return True


def cal_items(rec):
    """(date, kind, text, owner) for the effort's calendar: each deliverable's due date and its own dates."""
    import effortrec as ER
    import deliverables as DL
    out = []
    for d in DL.items(rec):
        if (d.get("due") or "")[:10]:
            out.append((ER.parse_date(d["due"][:10]), "deadline", f"Due: {d['name']}", d.get("owner", "")))
        for x in d.get("dates", []):
            out.append((ER.parse_date(x["date"]), "task", f"{d['name']}: {x['what']}", d.get("owner", "")))
    return [x for x in out if x[0]]


# ------------------------------------------------------------------ order
def arrange(rec, ids):
    """Put the deliverables in the team's order (ids first, in that order; any left out keep theirs after)."""
    import deliverables as DL
    ds = DL.items(rec)
    by = {d["id"]: d for d in ds}
    new = [by[i] for i in ids if i in by] + [d for d in ds if d["id"] not in ids]
    ds[:] = new
    rec.data["deliv_order_set"] = True
    rec.save()
    return [d["id"] for d in ds]


def make_volume(R, d, title=None):
    """A Structure volume for a volume deliverable (R: the effort's review); returns its label and links it."""
    import outline_ops as O
    if R is None or d is None:
        return None
    R.snap(f"add volume {d['name']}")
    title = title or d["name"]
    import re
    title = re.sub(r"^\s*volume\s+[ivx0-9a-z]+\s*[:.\-]?\s*", "", title, flags=re.I).strip() or title
    lab = O.add_volume(R.M, title)
    if lab:
        d["volume"] = lab
    return lab
