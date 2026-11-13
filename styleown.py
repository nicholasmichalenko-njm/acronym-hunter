"""A set owns its styles (4.30.2; Nicholas 2026-11-13 14:34 and 14:43). Sets are usually kinds of effort (RFPs, RFIs,
program documents), and each may hold a style of the same name with its own values. So:

- the same name with other values in two sets is two styles, one for each set; neither is "the newer version";
- an identical style used by several sets is one style, shown once with the sets that use it;
- two of the same name sit in one set only when a person chose Keep both: the one place a v1 / v2 switch shows;
- bringing styles into a set asks only when that set already has the name with other values: keep the set's, take the
  file's, or keep both;
- changing a style from inside a set changes it for that set only, unless the person says every set that uses it.

How it is kept does not change (templatelib's families and versions; a set lists the versions it holds), so every saved
library opens as before. A set may carry what it is used for ("used_for": a kind of effort), an optional key.
Standard library only. Rules only (No AI); nothing leaves the PC."""
import stylelib as SL

CHOICES = (("mine", "Keep the set's"), ("file", "Take the file's"), ("both", "Keep both"))
USED_FOR = ("RFP", "RFI", "Program documents", "White paper", "Other")


def fam(it):
    return it.get("family") or it["id"]


def held(lib, sid, family):
    """The versions of this style the set holds, oldest first."""
    k = lib.kit(sid) if sid else None
    out = [lib.get(i) for i in (k or {}).get("items", [])]
    return sorted((i for i in out if i is not None and fam(i) == family), key=lambda i: int(i.get("version") or 0))


def used_in(lib, iid):
    """The names of the sets that use this exact style."""
    return [k["name"] for k in SL.sets_of(lib, iid)]


def owned(lib):
    """The ids of every style version some set holds."""
    return {i for k in SL.sets(lib) for i in k.get("items", [])}


def against(lib, styles, sid=None):
    """Each style read from a file against the set it is going into (sid) and the library. Adds to stylelib.against:
    "clash" (the set's own style of that name, when it has other values), "choice" (mine / file / both; asked only on a
    clash, and it starts on the set's so nothing in a set is replaced unasked) and the words for its row."""
    out = SL.against(lib, styles)
    for r in out:
        mine = r.get("mine")
        mine_fam = fam(mine) if mine else None
        own = held(lib, sid, mine_fam) if (sid and mine_fam) else []
        clash = None
        if own and not (r["state"] == "same" and any(o["id"] == mine["id"] for o in own)):
            clash = own[-1]
        r["clash"], r["choice"] = clash, ("mine" if clash else "")
        r["words"] = words(lib, r, sid)
    return out


def words(lib, r, sid=None):
    """What bringing this one in does, on its row."""
    k = lib.kit(sid) if sid else None
    here = f"{k['name']}" if k else "the set you pick"
    if r.get("clash"):
        return f"{here} has this name with other values: choose"
    if r["state"] == "new":
        return "New: comes in" + (f", in {here}" if k else "")
    if r["state"] == "same":
        others = [n for n in used_in(lib, r["mine"]["id"]) if not k or n != k["name"]]
        return "Identical to one you have: one style" + (f", used in {', '.join(others)} too" if others else "") + ("" if k else "; it joins the set you pick")
    others = sorted({n for x in lib.items if x["kind"] == "style" and fam(x) == fam(r["mine"]) for n in used_in(lib, x["id"])})
    return ("Same name, other values" + (f" than {', '.join(others)}'s" if others else " than the one you have")
            + f": {here} gets its own; " + ("theirs stay" if others else "yours stays"))


def retarget(lib, rows, sid):
    """The set picked for the import changed: every row is judged against the new set (a choice already made is kept
    where the clash is the same)."""
    for r in rows:
        before = (r.get("clash") or {}).get("id"), r.get("choice")
        mine = r.get("mine")
        own = held(lib, sid, fam(mine)) if (sid and mine) else []
        clash = None
        if own and not (r["state"] == "same" and any(o["id"] == mine["id"] for o in own)):
            clash = own[-1]
        r["clash"] = clash
        r["choice"] = (before[1] if clash and before[0] == clash["id"] and before[1] else ("mine" if clash else ""))
        r["words"] = words(lib, r, sid)
    return rows


def rows(lib, sid=None, find="", shown=None):
    """The rows of the Styles list.
    In a set: one row per style the set holds; "versions" has more than one only when the set holds both.
    Every style: one row per style in use (each version some set holds) plus each name's newest when no set holds it;
    never a version switch. "earlier": the versions no row shows (reached from the row's menu)."""
    shown = shown or {}
    q = (find or "").strip().casefold()
    live = owned(lib)
    out = []
    items = [i for i in lib.items if i["kind"] == "style" and (not q or q in i["name"].casefold() or q in (i.get("summary") or "").casefold())]
    fams = {}
    for i in items:
        fams.setdefault(fam(i), []).append(i)
    for f, vers in fams.items():
        vers.sort(key=lambda i: int(i.get("version") or 0))
        if sid:
            mine = held(lib, sid, f)
            if not mine:
                continue
            pick = shown.get(f) if shown.get(f) in [x["id"] for x in mine] else mine[-1]["id"]
            out.append({"family": f, "versions": mine if len(mine) > 1 else [], "shown": pick, "earlier": []})
            continue
        used = [i for i in vers if i["id"] in live]
        top = vers[-1]
        show = used if top in used or not used else used + [top]
        if not used:
            show = [top]
        rest = [i for i in vers if i not in show]
        for i in show:
            pick = i["id"]
            if i is top and shown.get(f) in [x["id"] for x in rest]:
                pick = shown[f]                          # an earlier version opened from the menu shows in the newest's row
            out.append({"family": f, "versions": [], "shown": pick, "earlier": rest if i is top else []})
    out.sort(key=lambda r: (lib.base_of(lib.get(r["shown"])).casefold(), int(lib.get(r["shown"]).get("version") or 0)))
    return out


def source_words(lib, it, v=None, version=False):
    """Under the style's name: where it came from (and its version only where a set holds two of the name)."""
    v = v if v is not None else (lib.values(it) or {})
    bits = []
    if version:
        bits.append(f"v{int(it.get('version') or 1)}")
    if it.get("label"):
        bits.append(it["label"])
    if v.get("_made") == "app":
        bits.append("made in the app")
    elif v.get("_copy_of"):
        bits.append(f"copied from {v['_copy_of']}")
    elif v.get("_from") or it.get("source"):
        bits.append(f"from {v.get('_from') or it.get('source')}")
    return " · ".join(bits)


def newer(lib, sid):
    """stylelib.newer, less the ones that are another set's own style: a set is told about a newer version only when
    no set holds it (a change saved from Every style, or brought in with no set)."""
    live = owned(lib)
    return [(a, b) for a, b in SL.newer(lib, sid) if b["id"] not in live]


def save(lib, iid, values, sid=None, every=False, who=None):
    """The style's form saved. From inside a set (sid) the change is that set's alone: the set moves to the changed
    style and every other set keeps the one it has. every=True: every set that used it moves. With no set, it is kept
    as the style's newest and no set moves. Returns (item, state, [names of the sets that moved])."""
    new, st = SL.save_edit(lib, iid, values, who=who)
    if new is None or new["id"] == iid:
        return new, st, []
    moved = []
    for k in SL.sets(lib):
        if iid in k["items"] and (every or k["id"] == sid):
            if new["id"] in k["items"]:
                k["items"].remove(iid)
            else:
                k["items"][k["items"].index(iid)] = new["id"]
            moved.append(k["name"])
    if moved:
        lib.save()
    return new, st, moved


def set_used_for(lib, sid, word):
    """What the set is used for (a kind of effort), or nothing."""
    k = lib.kit(sid)
    if k is None:
        return False
    word = " ".join(str(word or "").split())[:40]
    if word:
        k["used_for"] = word
    else:
        k.pop("used_for", None)
    lib.save()
    return True
