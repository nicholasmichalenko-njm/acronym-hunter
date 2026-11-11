"""Effort Profiles (3.52.0, plan decisions 1, 3 and 5): a profile is built by picking. Each effort type lists its profiles
(Technical Volume, Management Volume, Cost Volume...); each profile fills one slot per decision (cover, headers and
footers, theme, base fonts, heading numbering, lists, pagination, table looks, TOC) from the libraries, offered only the
items tagged for its effort type (or for every effort type, or not tagged yet); Show all lifts the filter. The RFP's
font size limits sit on the profile (and on the effort, in Effort Formatting) and are checked as you pick.

Stored in production_standards.json as it already is: a profile's picks and limits are its changes in the effort type
(effort type "profile_over"), so the same profile in another effort type keeps its own. The volumes a profile makes are
the effort type's "volumes" ({profile id: [names]}; the profile's name when none are set). Additive keys only.
profiles(data) / layer / resolved / volumes / set_volumes / add / rename / remove / choices / pick / limits / set_limit.
Rules only; nothing leaves the PC."""
import copy

import prodrules as PRL
import templateprofile as TP

LIMIT_SCOPES = ("body", "table", "caption", "header_footer", "footnote", "heading")


def profiles(data):
    """[{eid, ename, pid, pname, volumes}] every effort type's profiles, in the effort types' order."""
    out = []
    for e in data.get("effort_types") or []:
        for pid in e.get("profiles") or []:
            t = PRL.type_of(data, pid)
            if t["id"] != pid:
                continue
            out.append({"eid": e["id"], "ename": e["name"], "pid": pid, "pname": t["name"], "volumes": volumes(data, e["id"], pid)})
    return out


def layer(data, eid, pid):
    """The profile's changes in this effort type: where picks and limits are written."""
    e = PRL.effort_type_of(data, eid)
    if e is None:
        return None
    return e.setdefault("profile_over", {}).setdefault(pid, {})


def resolved(data, eid, pid):
    """The standard the profile makes, everything merged (Company Standards (Default), profile, effort type, its changes)."""
    return PRL.resolved_type(data, pid, eid)


def volumes(data, eid, pid):
    e = PRL.effort_type_of(data, eid) or {}
    got = [v for v in ((e.get("volumes") or {}).get(pid) or []) if str(v).strip()]
    return got or [PRL.type_of(data, pid)["name"]]


def set_volumes(data, eid, pid, names):
    e = PRL.effort_type_of(data, eid)
    if e is None:
        return []
    clean = []
    for n in names:
        n = " ".join(str(n).split())
        if n and n.casefold() not in (c.casefold() for c in clean):
            clean.append(n)
    e.setdefault("volumes", {})[pid] = clean
    return volumes(data, eid, pid)


def add(data, eid, name, copy_from=None):
    """A new profile in an effort type, empty or a copy of another profile (its values and its changes in this effort
    type). Returns its id, or "" when the name is empty or taken in this effort type."""
    e = PRL.effort_type_of(data, eid)
    name = " ".join((name or "").split())
    if e is None or not name or any(PRL.type_of(data, p)["name"].casefold() == name.casefold() for p in e.get("profiles") or []):
        return ""
    pid = PRL.slug(name, {t["id"] for t in data["types"]})
    t = {"id": pid, "name": name, "match": [w for w in name.lower().split() if w not in ("volume", "the", "and")][:2]}
    if copy_from:
        src = PRL.type_of(data, copy_from)
        t.update({k: copy.deepcopy(v) for k, v in PRL.layer_of(src).items()})
        over = (e.get("profile_over") or {}).get(copy_from)
        if over:
            e.setdefault("profile_over", {})[pid] = copy.deepcopy(over)
    data["types"].append(t)
    e.setdefault("profiles", []).append(pid)
    return pid


def rename(data, pid, name):
    """The profile's name (every effort type that holds it shows the new name). Returns True when renamed."""
    name = " ".join((name or "").split())
    t = next((x for x in data["types"] if x["id"] == pid), None)
    if t is None or not name or any(x["name"].casefold() == name.casefold() and x["id"] != pid for x in data["types"]):
        return False
    t["name"] = name
    return True


def used_by(data, pid):
    return [e["name"] for e in data.get("effort_types") or [] if pid in (e.get("profiles") or [])]


def remove(data, eid, pid):
    """Takes the profile out of this effort type (its changes there go; the profile stays for other effort types).
    An effort type keeps at least one profile. Returns True when taken out."""
    e = PRL.effort_type_of(data, eid)
    if e is None or pid not in (e.get("profiles") or []) or len(e["profiles"]) < 2:
        return False
    e["profiles"].remove(pid)
    (e.get("profile_over") or {}).pop(pid, None)
    (e.get("volumes") or {}).pop(pid, None)
    if e.get("default_profile") == pid:
        e["default_profile"] = e["profiles"][0]
    return True


def choices(lib, slot, eid, show_all=False):
    """The library items that can fill a slot. Filtered: tagged for this effort type, for every effort type, or not
    tagged yet, and not retired. show_all: every item of the slot's kind."""
    import libcats as LC
    got = TP.choices(lib, slot)
    if show_all:
        return got
    return [i for i in got if LC.status(i) != "retired" and (LC.fits(i, eid) or not LC.effort_types(i))]


def slot_state(data, eid, pid, lib, slot):
    """TP.state on what the profile resolves to (a pin can come from the profile, the effort type or this profile's changes)."""
    return TP.state(resolved(data, eid, pid), lib, slot)


def pick(data, eid, pid, lib, slot, iid, config_dir):
    lay = layer(data, eid, pid)
    if lay is None:
        return ""
    return TP.pick(lay, lib, slot, iid, config_dir)


# ------------------------------------------------------------------ the RFP's limits (decision 3)
def limits(std):
    """[{scope, what, min, value, ok}] each limit set on the standard, against the size the profile gives that text.
    ok is None when the profile sets no size for it (nothing to check yet)."""
    out = []
    v = std.get("variables") or {}
    for scope in LIMIT_SCOPES:
        r = (std.get("fonts") or {}).get(scope) or {}
        lo = r.get("min_size")
        try:
            lo = float(lo) if lo not in (None, "") else None
        except (TypeError, ValueError):
            lo = None
        size_key = (PRL.VAR_FOR_SCOPE.get(scope) or (None, None))[1]
        try:
            size = float(v.get(size_key)) if size_key and v.get(size_key) not in (None, "") else None
        except (TypeError, ValueError):
            size = None
        ok = None if lo is None or size is None else size >= lo - 1e-6
        out.append({"scope": scope, "what": PRL.SCOPE_NAMES.get(scope, scope), "min": lo, "value": size, "ok": ok})
    return out


def broken_limits(std):
    return [f"{r['what']} {r['value']:g} pt is under the {r['min']:g} pt limit" for r in limits(std) if r["ok"] is False]


def set_limit(data, eid, pid, scope, min_size):
    """The smallest size the RFP allows for one kind of text, on this profile (None takes it off)."""
    lay = layer(data, eid, pid)
    if lay is None or scope not in LIMIT_SCOPES:
        return False
    f = lay.setdefault("fonts", {}).setdefault(scope, {})
    f["min_size"] = float(min_size) if min_size not in (None, "", 0) else None
    return True
