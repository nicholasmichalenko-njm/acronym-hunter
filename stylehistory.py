"""Version history of a style (4.35.0; Nicholas's ST15, ST16 and ST24 of 2026-11-14): as Google Docs and SharePoint
keep it. Every saved change to a style is a version of that style: numbered, dated, kept. The newest is Latest and
Latest is what every style set uses; there is no assigned version. Restoring an earlier version copies its values into
a new version on top, so nothing is ever overwritten or lost, and a restore is undone by restoring the one before it.
The wide restore ("every style as of...") is the same act for many styles and is undone the same way.

A set that needs a different look uses a copy under its own name (Duplicate...), with its own history (ST24: this
replaces 4.30.2's change for one set only).

    save(lib, iid, values)          the style's form saved: a new Latest; every set that used the style gets it
    history(lib, iid)               the style's versions, newest first, each with what changed from the one before
    restore(lib, iid)               that version's values become a new Latest
    moments(lib)                    the times styles changed, newest first, for the wide restore
    as_of(lib, when)                what the wide restore would do: [(latest, the version of that time)]
    restore_as_of(lib, when)        do it; returns a token for undo(lib, token)
    behind(lib, sid=None)           [(set, the version it holds, Latest)] for sets still on an earlier version

Standard library only. Rules only (No AI); nothing leaves the PC."""
import stylelib as SL

KIND = "style"
SHOW = (("font", "Font"), ("size", "Size"), ("color", "Color"), ("bold", "Bold"), ("italic", "Italic"), ("underline", "Underline"),
        ("caps", "All caps"), ("hidden", "Hidden"), ("jc", "Alignment"), ("before", "Space before"), ("after", "Space after"),
        ("keep_next", "Keep with next"), ("line", "Line spacing"), ("line_rule", "Line spacing rule"), ("left", "Left indent"),
        ("right", "Right indent"), ("first", "First line"), ("hanging", "Hanging"), ("tabs", "Tabs"))


def _ver(it):
    return int(it.get("version") or 1)


# 4.35.1 (ST26): a style name can have more than one version line, each for the sets it is tagged with ("Body" for RFP
# and Program documents, another "Body" for Page-limited RFP). A line is the items of one family that share "line"
# (none: the first line). Each line has its own history and its own Latest; a set holds one style of a name.
def line_of(it):
    return (it or {}).get("line") or ""


def line(lib, iid):
    """The versions of this style's line, oldest first."""
    it = lib.get(iid)
    if it is None:
        return []
    return sorted((x for x in lib.items if x.get("family") == it.get("family") and line_of(x) == line_of(it)), key=_ver)


def top(lib, iid):
    """The Latest of this style's line."""
    ln = line(lib, iid)
    return ln[-1] if ln else None


def number(lib, it):
    """The version's number within its line, from 1 (what the lists and messages say)."""
    ln = line(lib, it["id"])
    return 1 + next((n for n, x in enumerate(ln) if x["id"] == it["id"]), 0)


def _move(lib, family, new_id, only_from=None):
    """Every set that holds a version of this style's line holds new_id instead. Returns the sets' names."""
    moved = []
    ln = line_of(lib.get(new_id))
    for k in SL.sets(lib):
        hit = [i for i in k["items"] if (lib.get(i) or {}).get("family") == family and i != new_id
               and line_of(lib.get(i)) == ln and (only_from is None or i == only_from)]
        if not hit:
            continue
        at = k["items"].index(hit[0])
        k["items"] = [i for i in k["items"] if i not in hit and i != new_id]
        k["items"].insert(min(at, len(k["items"])), new_id)
        moved.append(k["name"])
    if moved:
        lib.save()
    return moved


def _on_top(lib, it, values, who=None, note=""):
    """A new version at the top of the style's history with these values, whatever earlier version holds the same."""
    new, _st = lib._new(it["kind"], lib.base_of(it), values, it.get("tags"), it.get("source", ""), it.get("summary", ""), who,
                        family=it["family"], note=note)
    if line_of(it):
        new["line"] = line_of(it); lib.save()
    if it["kind"] == "style":
        import templatelib as TL
        new["summary"] = TL._summary_style(values); lib.save()
    return new


def save(lib, iid, values, who=None):
    """The style's form saved. Returns (item, state, [names of the sets that now use it]); state "version" when a new
    Latest of its line was made, "same" when nothing changed."""
    it = lib.get(iid)
    if it is None:
        return None, "missing", []
    old = lib.values(it) or {}
    v = SL._edited(old, values)
    if not changes(old, v) and v == old:
        return it, "same", []
    v["_xml"] = SL._xml_for(lib.base_of(it), old, v)
    new = _on_top(lib, top(lib, iid), v, who)
    return new, "version", _move(lib, it["family"], new["id"])


def _say(k, v):
    if v in ("", None, [], False):
        return "none" if k not in ("bold", "italic", "underline", "caps", "hidden", "keep_next") else "off"
    if v is True:
        return "on"
    if k == "tabs":
        return SL.tabs_text(v) or "none"
    if k in ("size", "before", "after", "left", "right", "first", "hanging"):
        return f"{v:g} pt" if isinstance(v, (int, float)) else str(v)
    return str(v)


def changes(a, b):
    """What differs between two versions' values, in words: [(what, was, now)]."""
    out = [(t, _say(k, (a or {}).get(k)), _say(k, (b or {}).get(k))) for k, t in SHOW
           if _say(k, (a or {}).get(k)) != _say(k, (b or {}).get(k))]
    if not out and (a or {}).get("_xml") != (b or {}).get("_xml"):
        out.append(("Other values Word wrote", "as it was", "changed"))
    return out


def history(lib, iid):
    """The versions of this style's line, newest first: {"id", "version" (its number in the line), "latest", "at",
    "by", "note", "changes", "sets"}."""
    ln = list(reversed(line(lib, iid)))
    rows = []
    for n, it in enumerate(ln):
        older = ln[n + 1] if n + 1 < len(ln) else None
        ch = changes(lib.values(older) or {}, lib.values(it) or {}) if older is not None else []
        rows.append({"id": it["id"], "version": len(ln) - n, "latest": n == 0, "at": str(it.get("at") or "").replace("T", " "),
                     "by": it.get("by") or "", "note": it.get("note") or it.get("label") or ("The first version" if older is None else ""),
                     "changes": ch, "sets": [k["name"] for k in SL.sets_of(lib, it["id"])]})
    return rows


def restore(lib, iid, who=None):
    """That version's values become the new Latest of its line; every set on that line gets it. Returns (item,
    [sets]); (None, []) when it is the Latest already."""
    it, t = lib.get(iid), top(lib, iid)
    if it is None or t is None or it["id"] == t["id"]:
        return None, []
    new = _on_top(lib, t, lib.values(it) or {}, who, note=f"Restored from version {number(lib, it)}")
    return new, _move(lib, it["family"], new["id"])


def create_version(lib, iid, set_ids, who=None):
    """ST26: another version of this style's name, for the sets named (their ids). It starts with the values of the
    style it was made from and has its own history from there. A set holds one style of a name, so each of those sets
    gives up the one it had. Returns (item, [the sets' names])."""
    import uuid
    it = lib.get(iid)
    if it is None:
        return None, []
    names = [k["name"] for k in SL.sets(lib) if k["id"] in set(set_ids or [])]
    new, _st = lib._new(it["kind"], lib.base_of(it), lib.values(it) or {}, it.get("tags"), it.get("source", ""), it.get("summary", ""), who,
                        family=it["family"], note="Another version" + (f", for {', '.join(names)}" if names else ""))
    new["line"] = uuid.uuid4().hex[:8]
    lib.save()
    for sid in set_ids or []:
        SL.add_to_set(lib, sid, [new["id"]])
    return new, names


def lines(lib, iid):
    """The Latest of every line of this style's name, with the sets on it: [(item, [set names])], the first line first."""
    it = lib.get(iid)
    seen, out = set(), []
    for x in sorted((x for x in lib.items if it is not None and x.get("family") == it.get("family")), key=_ver):
        if line_of(x) not in seen:
            seen.add(line_of(x))
            t = top(lib, x["id"])
            out.append((t, [k["name"] for k in SL.sets_of(lib, t["id"])]))
    return out


def _styles(lib):
    return [i for i in lib.items if i.get("kind") == KIND]


def moments(lib):
    """The times any style changed, newest first ("2026-11-14 13:05")."""
    return sorted({str(i.get("at") or "").replace("T", " ") for i in _styles(lib) if i.get("at")}, reverse=True)


def as_of(lib, when):
    """What the wide restore to that time would do: [(the Latest, the version in force at that time)] for each line of
    each style whose Latest is newer than `when` and that existed then. A style made after that time is left as it is."""
    when = str(when).replace("T", " ")
    fams = {}
    for i in _styles(lib):
        fams.setdefault((i.get("family"), line_of(i)), []).append(i)
    out = []
    for its in fams.values():
        its.sort(key=_ver)
        then = [i for i in its if str(i.get("at") or "").replace("T", " ") <= when]
        if then and then[-1]["id"] != its[-1]["id"] and then[-1].get("hash") != its[-1].get("hash"):
            out.append((its[-1], then[-1]))
    return sorted(out, key=lambda p: lib.base_of(p[0]).lower())


def restore_as_of(lib, when, who=None):
    """Every style as it was at that time, each as a new Latest. Returns the token for undo: [(family, the Latest
    before the restore)]."""
    token = []
    for was, then in as_of(lib, when):
        new = _on_top(lib, then, lib.values(then) or {}, who, note=f"Restored to {str(when).replace('T', ' ')} (version {number(lib, then)})")
        _move(lib, then["family"], new["id"])
        token.append((then["family"], was["id"]))
    return token


def undo(lib, token, who=None):
    """Undo a wide restore: each style's Latest of before becomes the Latest again (a new version; nothing is removed).
    Returns how many."""
    n = 0
    for _family, before in token or []:
        new, _sets = restore(lib, before, who)
        n += new is not None
    return n


def behind(lib, sid=None):
    """Sets still on an earlier version of their style's line: [(set, the version it holds, that line's Latest)]."""
    out = []
    for k in SL.sets(lib):
        if sid and k["id"] != sid:
            continue
        for iid in k["items"]:
            it = lib.get(iid)
            t = top(lib, iid) if it is not None and it.get("kind") == KIND else None
            if t is not None and t["id"] != iid:
                out.append((k, it, t))
    return out


def use_latest(lib, sid=None):
    """Those sets move to Latest. Returns how many styles moved."""
    n = 0
    for k, a, b in behind(lib, sid):
        n += bool(_move(lib, a["family"], b["id"]))
    return n


# ---------------------------------------------------------------- a document's style over one you have (4.35.1, ST17, ST25)
MERGE, REPLACE = "merge", "replace"
MODES = ((MERGE, "Only what differs"), (REPLACE, "Everything the document has"))
MODE_SAYS = {MERGE: "Your style takes the values that differ and keeps everything else it has.",
             REPLACE: "Your style becomes exactly the document's; what the document's does not have is removed."}


def _target(lib, row, mode):
    """(the Latest of the style, the values it would have)."""
    t = top(lib, (row.get("clash") or row["mine"])["id"])        # the line the set picked is on, else the one matched
    old = lib.values(t) or {}
    doc = row["values"]
    if mode == REPLACE:
        return t, dict(doc, _xml=row.get("xml", ""))
    diff = {k: doc.get(k, "") for k, _t in SHOW if k in doc and _say(k, doc.get(k)) != _say(k, old.get(k))}
    v = SL._edited(old, diff)
    if diff:
        v["_xml"] = SL._xml_for(lib.base_of(t), old, v)
    return t, v


def plan(lib, row, mode):
    """What bringing this style in would change in the one you have, in words: [(what, was, now)]. Empty when the
    style is new, identical, or the mode changes nothing."""
    if row.get("state") != "variant" or not row.get("mine"):
        return []
    t, v = _target(lib, row, mode)
    return changes(lib.values(t) or {}, v)


def bring(lib, row, mode, path="", who=None):
    """The document's style over the one you have, as its new Latest for every set that uses it. Returns the new
    version, or None when the mode changes nothing."""
    import os
    t, v = _target(lib, row, mode)
    if not changes(lib.values(t) or {}, v):
        return None
    v["_from"] = os.path.basename(path or "")
    new = _on_top(lib, t, v, who, note=f"Brought in from {os.path.basename(path or 'a document')}: {dict(MODES)[mode].lower()}")
    _move(lib, t["family"], new["id"])
    return new
