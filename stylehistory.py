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


def _move(lib, family, new_id, only_from=None):
    """Every set that holds a version of this style (or only the given one) holds new_id instead. Returns the sets' names."""
    moved = []
    for k in SL.sets(lib):
        hit = [i for i in k["items"] if (lib.get(i) or {}).get("family") == family and i != new_id
               and (only_from is None or i == only_from)]
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
    return new


def save(lib, iid, values, who=None):
    """The style's form saved. Returns (item, state, [names of the sets that now use it]); state "version" when a new
    Latest was made, "same" when nothing changed."""
    it = lib.get(iid)
    if it is None:
        return None, "missing", []
    top = lib.latest(iid)
    new, st = SL.save_edit(lib, iid, values, who=who)
    if new is None:
        return None, st, []
    if new["id"] == top["id"]:
        return new, "same", []
    if st == "same":                                             # the values of an earlier version: still a new Latest, never a step back
        new = _on_top(lib, it, lib.values(new) or {}, who, note=f"The same values as version {_ver(new)}")
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
    """The style's versions, newest first: {"id", "version", "latest", "at", "by", "note", "changes", "sets"}."""
    fam = lib.family(iid)
    rows = []
    for n, it in enumerate(fam):
        older = fam[n + 1] if n + 1 < len(fam) else None
        ch = changes(lib.values(older) or {}, lib.values(it) or {}) if older is not None else []
        rows.append({"id": it["id"], "version": _ver(it), "latest": n == 0, "at": str(it.get("at") or "").replace("T", " "),
                     "by": it.get("by") or "", "note": it.get("note") or it.get("label") or ("The first version" if older is None else ""),
                     "changes": ch, "sets": [k["name"] for k in SL.sets_of(lib, it["id"])]})
    return rows


def restore(lib, iid, who=None):
    """That version's values become a new Latest; every set that uses the style gets it. Returns (item, [sets]);
    (None, []) when it is the Latest already."""
    it, top = lib.get(iid), lib.latest(iid)
    if it is None or top is None or it["id"] == top["id"]:
        return None, []
    new = _on_top(lib, it, lib.values(it) or {}, who, note=f"Restored from version {_ver(it)}")
    return new, _move(lib, it["family"], new["id"])


def _styles(lib):
    return [i for i in lib.items if i.get("kind") == KIND]


def moments(lib):
    """The times any style changed, newest first ("2026-11-14 13:05")."""
    return sorted({str(i.get("at") or "").replace("T", " ") for i in _styles(lib) if i.get("at")}, reverse=True)


def as_of(lib, when):
    """What the wide restore to that time would do: [(the Latest, the version in force at that time)] for each style
    whose Latest is newer than `when` and that existed then. A style made after that time is left as it is."""
    when = str(when).replace("T", " ")
    fams = {}
    for i in _styles(lib):
        fams.setdefault(i.get("family"), []).append(i)
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
    for top, then in as_of(lib, when):
        new = _on_top(lib, then, lib.values(then) or {}, who, note=f"Restored to {str(when).replace('T', ' ')} (version {_ver(then)})")
        _move(lib, then["family"], new["id"])
        token.append((then["family"], top["id"]))
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
    """Sets still on an earlier version of a style: [(set, the version it holds, Latest)] (from before 4.35.0)."""
    out = []
    for k in SL.sets(lib):
        if sid and k["id"] != sid:
            continue
        out += [(k, a, b) for a, b in SL.newer(lib, k["id"])]
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
    top = lib.latest(row["mine"]["id"])
    old = lib.values(top) or {}
    doc = row["values"]
    if mode == REPLACE:
        return top, dict(doc, _xml=row.get("xml", ""))
    diff = {k: doc.get(k, "") for k, _t in SHOW if k in doc and _say(k, doc.get(k)) != _say(k, old.get(k))}
    v = SL._edited(old, diff)
    if diff:
        v["_xml"] = SL._xml_for(lib.base_of(top), old, v)
    return top, v


def plan(lib, row, mode):
    """What bringing this style in would change in the one you have, in words: [(what, was, now)]. Empty when the
    style is new, identical, or the mode changes nothing."""
    if row.get("state") != "variant" or not row.get("mine"):
        return []
    top, v = _target(lib, row, mode)
    return changes(lib.values(top) or {}, v)


def bring(lib, row, mode, path="", who=None):
    """The document's style over the one you have, as its new Latest for every set that uses it. Returns the new
    version, or None when the mode changes nothing."""
    import os
    top, v = _target(lib, row, mode)
    if not changes(lib.values(top) or {}, v):
        return None
    v["_from"] = os.path.basename(path or "")
    new = _on_top(lib, top, v, who, note=f"Brought in from {os.path.basename(path or 'a document')}: {dict(MODES)[mode].lower()}")
    _move(lib, top["family"], new["id"])
    return new
