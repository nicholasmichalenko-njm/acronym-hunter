"""Version history of a Quick Part (4.40.0; Nicholas's ST28 of 2026-11-14: Quick Parts work as styles do, ST15, ST24
and ST26). Every change to a Quick Part is a version of it: numbered, dated, kept. The newest is Latest and every
Quick Part set that uses the Quick Part gets it; this replaces 3.95.0's "sets that use an older one keep it".
Restoring an earlier version puts it on top as a new version, so nothing is overwritten or lost. A set that needs its
own Quick Part under the same name gets another version, tagged with the sets it is for (a version line, as styles
have): each line has its own history and its own Latest, and a set holds one Quick Part of a name.

    changed(lib, origin, new, state)   after Change it...: the new one joins the origin's line; its sets get it
    history(lib, iid)                  the versions of this Quick Part's line, newest first, with the sets on each
    restore(lib, iid)                  that version on top as a new Latest
    create_version(lib, iid, sets)     another version of the name, for the part sets named
    lines(lib, iid)                    the Latest of every line of the name, with its sets
    tops(lib, family)                  the Latest of each line of a family (what the Parts page lists)
    behind(lib)                        [(set, the version it holds, Latest)] for sets still on an earlier version

Part sets hold a Quick Part as "q:<item id>". Standard library only. Rules only (No AI); nothing leaves the PC."""
import stylehistory as SH
import stylelib as SL

line_of, line, top, number = SH.line_of, SH.line, SH.top, SH.number


def _q(iid):
    return "q:" + iid


def sets_on(lib, iid):
    """The names of the part sets that hold this exact version."""
    return [k["name"] for k in SL.sets(lib, "part") if _q(iid) in k["items"]]


def _move(lib, family, new_id):
    """Every part set that holds a version of the new one's line holds the new one instead. Returns the sets' names."""
    ln, moved = line_of(lib.get(new_id)), []
    for k in SL.sets(lib, "part"):
        hit = [p for p in k["items"] if p.startswith("q:") and p != _q(new_id) and (lib.get(p[2:]) or {}).get("family") == family
               and line_of(lib.get(p[2:])) == ln]
        if not hit:
            continue
        at = k["items"].index(hit[0])
        k["items"] = [p for p in k["items"] if p not in hit and p != _q(new_id)]
        k["items"].insert(min(at, len(k["items"])), _q(new_id))
        moved.append(k["name"])
    if moved:
        lib.save()
    return moved


def changed(lib, origin, new, state=""):
    """A Quick Part was changed (the styles decide, a variant, brought back from Word): the new version joins the line
    of the one it was changed from and every part set on that line gets it. Returns the sets' names; [] when the
    library held these values already or nothing new was made."""
    if origin is None or new is None or new["id"] == origin["id"] or state == "same" or new.get("family") != origin.get("family"):
        return []
    if line_of(origin):
        new["line"] = line_of(origin)
    else:
        new.pop("line", None)
    lib.save()
    return _move(lib, new["family"], new["id"])


def history(lib, iid):
    """The versions of this Quick Part's line, newest first: {"id", "version" (its number in the line), "latest", "at",
    "by", "note", "sets"}."""
    ln = list(reversed(line(lib, iid)))
    return [{"id": it["id"], "version": len(ln) - n, "latest": n == 0, "at": str(it.get("at") or "").replace("T", " "), "by": it.get("by") or "",
             "note": it.get("note") or it.get("label") or ("The first version" if n == len(ln) - 1 else "Changed"), "sets": sets_on(lib, it["id"])}
            for n, it in enumerate(ln)]


def restore(lib, iid, who=None):
    """That version becomes the new Latest of its line; every part set on that line gets it. Returns (item, [sets]);
    (None, []) when it is the Latest already."""
    it, t = lib.get(iid), top(lib, iid)
    if it is None or t is None or it["id"] == t["id"]:
        return None, []
    new = SH._on_top(lib, t, lib.values(it) or {}, who, note=f"Restored from version {number(lib, it)}")
    new["summary"] = it.get("summary", ""); lib.save()
    return new, _move(lib, it["family"], new["id"])


def create_version(lib, iid, set_ids, who=None):
    """ST26 for Quick Parts: another version of this Quick Part's name, for the part sets named (their ids). It starts
    as the one it was made from and has its own history from there. Each of those sets gives up the one it had.
    Returns (item, [the sets' names])."""
    import uuid
    it = lib.get(iid)
    if it is None:
        return None, []
    ks = [k for k in SL.sets(lib, "part") if k["id"] in set(set_ids or [])]
    names = [k["name"] for k in ks]
    new, _st = lib._new(it["kind"], lib.base_of(it), lib.values(it) or {}, it.get("tags"), it.get("source", ""), it.get("summary", ""), who,
                        family=it["family"], note="Another version" + (f", for {', '.join(names)}" if names else ""))
    new["line"] = uuid.uuid4().hex[:8]
    for k in ks:
        k["items"] = [p for p in k["items"] if not (p.startswith("q:") and (lib.get(p[2:]) or {}).get("family") == it["family"])] + [_q(new["id"])]
    lib.save()
    return new, names


def tops(lib, family):
    """The Latest of each line of a family, the first line first."""
    seen, out = [], []
    for x in sorted((x for x in lib.items if x.get("family") == family), key=SH._ver):
        if line_of(x) not in seen:
            seen.append(line_of(x)); out.append(top(lib, x["id"]))
    return out


def lines(lib, iid):
    """[(the Latest of a line, [the part sets on that line])] for every line of this Quick Part's name."""
    it = lib.get(iid)
    out = []
    for t in (tops(lib, it["family"]) if it else []):
        names = []
        for x in line(lib, t["id"]):
            names += [n for n in sets_on(lib, x["id"]) if n not in names]
        out.append((t, names))
    return out


def behind(lib):
    """[(set, the version it holds, the Latest of that line)] for part sets still on an earlier version."""
    out = []
    for k in SL.sets(lib, "part"):
        for p in k["items"]:
            it = lib.get(p[2:]) if p.startswith("q:") else None
            t = top(lib, it["id"]) if it else None
            if t is not None and t["id"] != it["id"]:
                out.append((k, it, t))
    return out


def use_latest(lib):
    """Moves every part set that is behind to the Latest of its line. Returns how many Quick Parts moved."""
    n = 0
    for k, it, t in behind(lib):
        k["items"] = [_q(t["id"]) if p == _q(it["id"]) else p for p in k["items"] if p != _q(t["id"]) or p == _q(it["id"])]
        n += 1
    if n:
        lib.save()
    return n
