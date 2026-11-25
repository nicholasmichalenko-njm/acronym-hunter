"""Shred in passes, the Response Structure pass (4.70.0; UX decisions 164 to 166, 168, 209; the brief
claude/stationkeeper-ux-build-brief-addition-shred-in-passes-2026-11-19.md). The person says what a piece of the
customer's text is in our response: a Volume, Heading 1, Heading 2 or Heading 3. The mark fills the outline at once,
under the volume or heading marked above it, in the customer's order. A mark attaches or adds, never replaces:

- the same title in the same volume (capitals, spacing, punctuation and a number in front left out) attaches;
- a near match is asked once (the caller gets {"ask": ...}; attach=True attaches, attach=False adds as new);
- no match adds a heading.

Each heading keeps the piece that required it (the outline's own "req", "req_title", "ref": Required by, 4.19.0) and a
page limit said in the same words. The marks are kept in the matrix's setup as "struct_marks" ({piece id: {"level",
"titles", "same"}}), read only when there; "struct_none" lists the documents a person said hold nothing of this kind.
A piece typed Response Structure by an earlier version shows at the level its words read as; nothing is rewritten
until someone marks it. Rules only (No AI); nothing leaves the PC. Standard library only."""
import difflib
import re

import compliance as C
import outline_ops as OO
import setupdoc as SD
import shredtypes as ST
import structfrom as SF

LEVELS = (("volume", "Volume"), ("h1", "Heading 1"), ("h2", "Heading 2"), ("h3", "Heading 3"))
NAME = dict(LEVELS)
DEPTH = {"volume": 0, "h1": 1, "h2": 2, "h3": 3}
NOT_NEEDED = "x"
FOR_SETUP = "s"                 # 4.71.0: sent to a section as text for the author
NEAR = 0.8                      # how alike two titles are before the app asks "Same as ...?" (to be shown to him)
_FRONT = re.compile(r"^\s*(?:volume\s+(?:[ivx]{1,4}|\d{1,2})\b[\s:,\-–—]*|(?:\d+(?:\.\d+)*|[a-z])[.)]?\s+)", re.I)
_VOLHEAD = re.compile(r"^\s*(Volume\s+(?:[IVX]{1,4}|\d{1,2}))\b[\s:,\-–—]*(.*)$", re.I)


def marks(M):
    return SD.setup_of(M).setdefault("struct_marks", {})


def norm(title):
    """A title for matching: no number in front, no capitals, no punctuation, single spaces."""
    t = " ".join((title or "").split())
    t = _FRONT.sub("", t) or t
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t.lower()).split())


def _order(M):
    return {it.get("id"): i for i, it in enumerate(M.items)}


def lines(M, it):
    """The headings a piece would make, as titles in the customer's order: one for a plain piece; one per item for a
    piece that lists several sections (with the list it leads in)."""
    heads = SF.read(M, SF.group(M, it))
    out = [h["title"] for h in heads if h.get("title")]
    if not out:
        t = SF._title(SF._MARK.sub("", it.get("text") or ""))
        out = [" ".join(t.split()[:14])] if t else []
    seen, res = set(), []
    for t in out:
        if norm(t) not in seen:
            seen.add(norm(t)); res.append(t)
    return res


def _read_level(M, it):
    heads = SF.read(M, [it])
    if not heads:
        return ""
    h = heads[0]
    if h["title"].startswith("Volume ") and h["level"] == 1:
        return "volume"
    return f"h{max(1, min(3, h['level'] - (1 if h.get('vol') else 0)))}"


def suggest(M, it):
    """The level the customer's own words read as, for a piece that reads as setting the structure; else ""."""
    if it.get("id") in marks(M):
        return ""
    import custstruct as CS
    if ST.has(it, "structure") or any(x is it for x in SF.suggested(M)) or any(x is it for x in CS.sent(M)):
        return _read_level(M, it)
    return ""


def level_of(M, it):
    """The level a piece is marked at ("volume", "h1", "h2", "h3"), "x" for Not needed, or "". A piece typed Response
    Structure before 4.70.0 shows at the level its words read as."""
    m = marks(M).get(it.get("id"))
    if m:
        return m.get("level", "")
    return _read_level(M, it) if ST.has(it, "structure") else ""


def suggestions(M):
    """The pieces the pass would look at next, in the customer's order: the ones that read as setting the structure and
    the ones typed Response Structure before, not yet marked or set aside here."""
    got = marks(M)
    ids = {id(x) for x in SF.suggested(M)}
    import custstruct as CS                          # 4.74.0: pieces sent from Shred with Send to Outline come first
    first = [it for it in CS.sent(M) if it.get("id") not in got]
    fid = {id(x) for x in first}
    return first + [it for it in M.items if id(it) not in fid and it.get("id") not in got and (id(it) in ids or ST.has(it, "structure"))]


def next_suggestion(M, after_id=None):
    """The next piece the pass suggests after after_id, across the documents; the first one when none follows."""
    rows = suggestions(M)
    if not rows:
        return None
    import custstruct as CS
    waiting = [it for it in CS.sent(M) if it.get("id") in {x.get("id") for x in rows} and it.get("id") != after_id]
    if waiting:                                      # 4.74.0: what was sent here is looked at before the app's own suggestions
        return waiting[0]
    order = _order(M)
    at = order.get(after_id, -1)
    return next((it for it in rows if order[it.get("id")] > at), rows[0])


# ------------------------------------------------------------------ where a heading goes
def entries_of(M, iid):
    """Indices of the outline's headings this piece's mark made or attached to."""
    m = marks(M).get(iid) or {}
    ids = {iid, m.get("same")} - {None, ""}
    want = {norm(t) for t in m.get("titles", [])}
    return [i for i, o in enumerate(M.outline) if o.get("req") in ids
            and (not want or norm(o.get("req_title") or o.get("title")) in want or norm(C.outline_label(o)) in want)]


def _volume_of(M, i):
    """The index of the volume heading entry i sits under (itself when it is one), or None."""
    heads = OO.volume_heads(M)
    j = i
    while j is not None:
        if C.outline_label(M.outline[j]) in heads:
            return j
        j = OO.parent_of(M, j)
    return None


def _above(M, it, depth):
    """The outline index of the heading marked above this piece at a shallower level, or None."""
    order = _order(M)
    me = order.get(it.get("id"), len(order))
    best = None
    for iid, m in marks(M).items():
        if iid == it.get("id") or m.get("level") not in DEPTH or DEPTH[m["level"]] >= depth or order.get(iid, me) >= me:
            continue
        ent = entries_of(M, iid)
        if ent and (best is None or order[iid] > best[0]):
            best = (order[iid], ent[-1])
    return best[1] if best else None


def _later_sibling(M, it, parent, level):
    """The first heading under the same parent made by a piece that comes after this one in the customer's documents:
    the new heading goes before it."""
    order = _order(M)
    me = order.get(it.get("id"), len(order))
    best = None
    for iid, m in marks(M).items():
        if order.get(iid, -1) <= me or m.get("level") not in DEPTH:
            continue
        for i in entries_of(M, iid):
            if OO.parent_of(M, i) == parent and M.outline[i]["level"] == level and (best is None or order[iid] < best[0]):
                best = (order[iid], i)
    return best[1] if best else None


def _scope(M, parent):
    """The outline indices a title is matched against: the same volume, or the whole outline with none."""
    if parent is None:
        return list(range(len(M.outline)))
    v = _volume_of(M, parent)
    return OO.subtree(M, v) if v is not None else list(range(len(M.outline)))


def match(M, title, scope, volume=False):
    """("same", index), ("near", index) or ("", None) for a title against the headings in scope."""
    n = norm(title)
    if not n:
        return "", None
    best = (0.0, None)
    for i in scope:
        o = M.outline[i]
        if volume and o.get("level", 1) != 1:
            continue
        cand = {norm(o.get("title")), norm(C.outline_label(o))} - {""}
        if n in cand:
            return "same", i
        for c in cand:
            r = difflib.SequenceMatcher(None, n, c).ratio()
            a, b = set(n.split()), set(c.split())
            if min(len(a), len(b)) >= 2 and (a <= b or b <= a):
                r = max(r, NEAR)
            if r > best[0]:
                best = (r, i)
    return ("near", best[1]) if best[0] >= NEAR else ("", None)


def asks(M, it, level, titles=None):
    """Before a mark: the near matches a person is asked about, [{"title", "label"}]. Nothing changes."""
    parent = None if level == "volume" else _above(M, it, DEPTH[level])
    scope = _scope(M, parent)
    out = []
    for t in (titles if titles is not None else lines(M, it)):
        kind, i = match(M, t, scope, level == "volume")
        if kind == "near":
            out.append({"title": t, "label": C.outline_label(M.outline[i])})
    return out


def _keep(M, o, it, title, text):
    if not o.get("req"):
        o["req"] = it.get("id", "")
        o["req_title"] = o.get("title", "")
        o["ref"] = SF._ref(it)
    lim = SF._limit(title) or (SF._limit(text) if text else 0)
    if lim and not o.get("limit"):
        o["limit"] = lim
    return o


def _add_volume(M, title):
    m = _VOLHEAD.match(title)
    if not m:
        lab = OO.add_volume(M, title)
        return OO.index_of(M, lab)
    mode, _name, heads = SD.volumes_of(M)
    heads = list(heads) if mode == "several" else []
    num = " ".join(m.group(1).split())
    num = num[0].upper() + num[1:]
    o = {"num": num, "title": " ".join(m.group(2).split()).strip(" .,:;-()") or num, "level": 1}
    M.outline.append(o)
    SD.set_volumes(M, "several", "", heads + [C.outline_label(o)])
    M.log("outline", f"volume added: {C.outline_label(o)}")
    return len(M.outline) - 1


def _add_heading(M, it, title, parent):
    plab = C.outline_label(M.outline[parent]) if parent is not None else None
    lab = OO.add(M, title, parent=plab) if plab else OO.add(M, title)
    i = OO.index_of(M, lab)
    p = OO.parent_of(M, i)
    nxt = _later_sibling(M, it, p, M.outline[i]["level"])
    if nxt is not None and nxt != i:
        lab = OO.move_to(M, lab, C.outline_label(M.outline[nxt]), "before") or lab
        i = OO.index_of(M, lab)
    return i


def mark(M, it, level, titles=None, attach=None):
    """Mark a piece Volume, Heading 1, 2 or 3 and fill the outline. titles: the lines kept ticked (all of them when
    None). attach: what to do with a near match (None: change nothing and return {"ask": [...]}; True: attach; False:
    add as new). Returns {"made": [labels], "attached": [labels], "ask": [...]}."""
    if level not in DEPTH:
        raise ValueError(level)
    titles = [t for t in (titles if titles is not None else lines(M, it)) if norm(t)]
    if not titles:
        return {"made": [], "attached": [], "ask": []}
    ask = asks(M, it, level, titles)
    if ask and attach is None:
        return {"made": [], "attached": [], "ask": ask}
    if it.get("id") in marks(M):
        unmark(M, it)
    text = " ".join((it.get("text") or "").split()) if len(titles) == 1 else ""
    made, attached, same = [], [], ""
    objs = []
    for t in titles:
        parent = None if level == "volume" else _above(M, it, DEPTH[level])
        kind, i = match(M, t, _scope(M, parent), level == "volume")
        if kind == "same" or (kind == "near" and attach):
            o = M.outline[i]
            if o.get("req") and o["req"] != it.get("id"):
                same = o["req"]
            _keep(M, o, it, t, text)
            attached.append(o)
        else:
            i = _add_volume(M, t) if level == "volume" else _add_heading(M, it, t, parent)
            o = M.outline[i]
            _keep(M, o, it, t, text)
            made.append(o)
        objs.append(o)
        marks(M)[it.get("id")] = dict(level=level, titles=[x.get("req_title") or x.get("title") for x in objs],
                                      made=[x.get("req_title") or x.get("title") for x in made], **({"same": same} if same else {}))
    S = SD.setup_of(M)
    S.pop("outline_auto", None)
    S.pop("struct_closed", None)                    # 4.71.0: a mark opens a closed pass again
    req = S.setdefault("required", [])
    for o in made:
        req.append({"title": o["title"], "num": o.get("num", ""), "level": o["level"], "req": it.get("id", ""), "ref": o.get("ref", "")})
    ST.set_types([it], ST.combine(ST._keys(it.get(ST.FIELD)), "structure", True), lambda i, m: M.log(i, m))
    SF.deliver_limits(M)
    M.log(it.get("id", ""), f"Response Structure: {NAME[level]}")
    M.pending = True
    return {"made": [C.outline_label(o) for o in made], "attached": [C.outline_label(o) for o in attached], "ask": []}


def unmark(M, it):
    """Take the mark off. A heading the mark made, with nothing under it and nothing assigned to it, goes; any other
    heading stays and only loses its link to this piece. Returns the labels taken out."""
    iid = it.get("id")
    m = marks(M).get(iid)
    if not m:
        return []
    gone = []
    if m.get("level") in DEPTH:
        made = {norm(t) for t in m.get("made", [])}
        for i in sorted(entries_of(M, iid), reverse=True):
            o = M.outline[i]
            lab = C.outline_label(o)
            mine = o.get("req") == iid
            empty = len(OO.subtree(M, i)) == 1 and not any(lab in SD.item_sections(M, x) for x in M.items)
            if mine and empty and norm(o.get("req_title") or o.get("title")) in made:
                OO.delete(M, lab)
                gone.append(lab)
            elif mine:
                for k in ("req", "req_title", "ref"):
                    o.pop(k, None)
        req = SD.setup_of(M).get("required")
        if isinstance(req, list):
            req[:] = [r for r in req if r.get("req") != iid]
        ST.set_types([it], ST.combine(ST._keys(it.get(ST.FIELD)), "structure", False), lambda i, x: M.log(i, x))
    marks(M).pop(iid, None)
    M.pending = True
    return gone


def not_needed(M, it, on=True):
    """Looked at; nothing for this pass. It leaves the pass's "next" and can be reopened (on=False)."""
    iid = it.get("id")
    if not on:
        if (marks(M).get(iid) or {}).get("level") == NOT_NEEDED:
            marks(M).pop(iid)
            M.pending = True
        return False
    if (marks(M).get(iid) or {}).get("level") in DEPTH:
        unmark(M, it)
    marks(M)[iid] = {"level": NOT_NEEDED}
    M.pending = True
    return True


def for_setup(M, it, label):
    """For the setup (4.71.0; decision 167): the piece goes into a section of the outline as text for the author. A
    piece nobody has decided on becomes the customer's own (identified, not answered), which the setup writes in its own
    style; a piece already decided keeps its decision and is put in the section too. It leaves the pass's next."""
    if OO.index_of(M, label) < 0:
        return False
    iid = it.get("id")
    if (marks(M).get(iid) or {}).get("level") in DEPTH:
        unmark(M, it)
    if not it.get("decision"):
        C.assign_customer(M.items, [it])
        SD.clear_sections(M, it)
    if label not in SD.item_sections(M, it):
        SD.place(M, iid, label, copy=bool(it.get("map")))
    marks(M)[iid] = {"level": FOR_SETUP}
    M.log(iid, f"Response Structure: for the setup, under {label}")
    M.pending = True
    return True


def closed(M):
    """Not required by the customer (4.71.0): the customer prescribes no structure; the pass is closed."""
    return bool(SD.setup_of(M).get("struct_closed"))


def set_closed(M, on=True):
    S = SD.setup_of(M)
    if on:
        S["struct_closed"] = True
    else:
        S.pop("struct_closed", None)
    M.pending = True
    return bool(on)


def move(M, label, target, where):
    """A heading dragged on the tree (4.71.0; 209): before, after or into another, with everything under it. Returns
    its new label, or None when it cannot go there."""
    if where not in ("before", "after", "into"):
        return None
    return OO.move_to(M, label, target, where)


# ------------------------------------------------------------------ each document's state in this pass
def docs(M):
    """[{"file", "finds", "none", "state"}] for every customer document, in order: Not looked at; Has finds (count);
    Nothing of this kind here (said by a person)."""
    files, finds = [], {}
    got = marks(M)
    for it in M.items:
        f = it.get("file", "")
        if f and f not in files:
            files.append(f)
        if (got.get(it.get("id")) or {}).get("level") in DEPTH:
            finds[f] = finds.get(f, 0) + 1
    none = set(SD.setup_of(M).get("struct_none") or [])
    out = []
    for f in files:
        n = finds.get(f, 0)
        state = f"Has finds ({n})" if n else ("Nothing of this kind here" if f in none else "Not looked at")
        out.append({"file": f, "finds": n, "none": f in none and not n, "state": state})
    return out


def set_none(M, file, on=True):
    """Nothing of this kind here, for one document (one click; it can be taken back)."""
    S = SD.setup_of(M)
    cur = [f for f in (S.get("struct_none") or []) if f != file]
    if on:
        cur.append(file)
    S["struct_none"] = cur
    M.pending = True
    return on


def tree(M):
    """The outline as rows for the tree beside the page: [{"label", "level", "req", "ref"}]."""
    return [{"label": C.outline_label(o), "level": o.get("level", 1), "req": o.get("req", ""), "ref": o.get("ref", "")}
            for o in M.outline]
