"""Build the response structure while you assign (2.68.0): add a volume, a heading, or a subheading under any section
(as many levels deep as you need), rename, move up or down, indent or outdent, delete, or make a section from a
sentence. Sections made here number themselves by where they sit (1, 1.1, 1.1.1 ...), restarting in each volume; a
section brought in from the RFP or typed keeps its own number. When numbers change, every requirement, support
sentence, owner and setup entry follows its section. Rules only (No AI); nothing leaves the PC.
"""
import re
import compliance as C
import setupdoc as SD
import structparts as SP

ROMAN = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))


def roman(n):
    out = ""
    for v, r in ROMAN:
        while n >= v:
            out += r
            n -= v
    return out


def labels(M):
    return [C.outline_label(o) for o in M.outline]


def index_of(M, label):
    return next((i for i, o in enumerate(M.outline) if C.outline_label(o) == label), -1)


def subtree(M, i):
    """Indices of entry i and everything under it."""
    lvl = M.outline[i]["level"]
    j = i + 1
    while j < len(M.outline) and M.outline[j]["level"] > lvl:
        j += 1
    return list(range(i, j))


def parent_of(M, i):
    lvl = M.outline[i]["level"]
    for j in range(i - 1, -1, -1):
        if M.outline[j]["level"] < lvl:
            return j
    return None


def volume_heads(M):
    return set(SD.volumes_of(M)[2]) if SD.volumes_of(M)[0] == "several" else set()


# ------------------------------------------------------------------ labels follow their sections
UNNUMBERED = ("unnumbered", "divider", "placeholder", "element")    # 3.30.0: kinds of section that carry no number
HOOKS = []          # 3.29.1: fn(mapping) for what lives outside the matrix (captures and topics in the effort record)


def _hooks(mapping):
    for h in list(HOOKS):
        try:
            h(dict(mapping))
        except Exception:  # noqa: BLE001
            import diag
            diag.swallowed()


def relabel(M, mapping):
    """Move everything kept under an old section label to its new label: the sentences' sections, their copies and
    order in the setup, section people, notes, volume headings; 3.29.1: and (through HOOKS) the captures and topics
    placed in it."""
    mapping = {a: b for a, b in mapping.items() if a != b}
    if not mapping:
        return 0
    _hooks(mapping)
    S = SD.setup_of(M)
    for it in M.items:
        if it.get("map") in mapping:
            it["map"] = mapping[it["map"]]
    bud = S.get("budget") if isinstance(S.get("budget"), dict) else {}
    for d in [S.get(k) for k in ("copies", "order", "owners", "mgmt", "item_counts", "progress", "authorrefs")] + [bud.get("pages"), bud.get("source")]:
        if isinstance(d, dict):                    # 3.20.1: page lengths and what counts follow their section too
            moved = {a: d.pop(a) for a in list(mapping) if a in d}   # all at once: 3 -> 2 while 2 -> 1
            for a, v in moved.items():
                d[mapping[a]] = v
    V = S.get("volumes") or {}
    if V.get("heads"):
        V["heads"] = [mapping.get(h, h) for h in V["heads"]]
    for c in S.get("context", []):
        if c.get("loc") in mapping:
            c["loc"] = mapping[c["loc"]]
    rm = S.get("rfp_map")
    if isinstance(rm, dict):                       # 2.69.0: RFP sections mapped to our sections follow them
        for k, v in list(rm.items()):
            if v in mapping:
                rm[k] = mapping[v]
    M.pending = True
    return len(mapping)


def _letter(n):
    out = ""
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def renumber(M, before=None):
    """Number every section made here by where it sits: within a volume heading, 1, 2, 3 at its first level, 1.1 under
    1, and so on, as deep as it goes. 3.19.0: by part: the response is numbered as before; appendices are lettered
    (Appendix A, then A.1 under it); cover, title page, front matter and back cover items carry no number. Returns
    {old label: new label}. before: {id(section): its label before a change made ahead of this call."""
    heads = volume_heads(M)
    old = [before.get(id(o), C.outline_label(o)) for o in M.outline] if before else labels(M)
    counters = {}                                  # (parent index, numbered kind) -> sections seen under it so far
    nums = {}
    for i, o in enumerate(M.outline):
        p = parent_of(M, i)
        part = SP.part_of(o)
        kind = part if (part in SP.NUMBERED and o.get("kind") not in UNNUMBERED) else ""   # 3.30.0: kinds with no number
        if kind:
            counters[(p, kind)] = counters.get((p, kind), 0) + 1   # 2.69.0: every sibling counts, typed or made here
        if not o.get("auto"):
            nums[i] = o.get("num", "")
            continue
        if not kind:
            o["num"] = ""
            nums[i] = ""
            continue
        n = counters[(p, kind)]
        top = p is None or C.outline_label(M.outline[p]) in heads
        if kind == "appendix" and top:
            o["num"] = f"Appendix {_letter(n)}"
            nums[i] = o["num"]
            continue
        base = ""
        if not top:
            base = nums.get(p, M.outline[p].get("num", ""))
            if base.lower().startswith("appendix "):
                base = base.split(" ", 1)[1]
            base = base if re.match(r"^[0-9A-Za-z]+(\.[0-9A-Za-z]+)*$", base or "") else ""
        o["num"] = f"{base}.{n}" if base else str(n)
        nums[i] = o["num"]
    mapping = {a: C.outline_label(o) for a, o in zip(old, M.outline)}
    relabel(M, mapping)
    return {a: b for a, b in mapping.items() if a != b}


# ------------------------------------------------------------------ edits
VOLUME_STYLES = (("roman", "Volume I, II, III"), ("number", "Volume 1, 2, 3"), ("alpha", "Volume A, B, C"))   # 3.28.1
_VOLNUM = re.compile(r"^(\S+)\s+([IVXLCDM]+|\d+|[A-Z]{1,2})$")


def volume_style(M):
    return (SD.setup_of(M).get("volumes") or {}).get("style") or "roman"


def volume_number(style, n):
    return {"number": str(n), "alpha": _letter(n)}.get(style, roman(n))


def set_volume_style(M, style):
    """3.28.1: every volume numbered one way: Volume I, II, III; 1, 2, 3; or A, B, C (the word before the number stays).
    Everything kept under a volume's label follows it. Returns {old label: new label}."""
    if style not in dict(VOLUME_STYLES):
        return {}
    mode, _name, heads = SD.volumes_of(M)
    if mode != "several":
        V = SD.setup_of(M).setdefault("volumes", {})
        V["style"] = style
        return {}
    mapping, new_heads = {}, []
    for n, lab in enumerate(heads, 1):
        i = index_of(M, lab)
        o = M.outline[i]
        m = _VOLNUM.match((o.get("num") or "").strip())
        if m:
            o["num"] = f"{m.group(1)} {volume_number(style, n)}"
        elif not o.get("num"):
            o["num"] = f"Volume {volume_number(style, n)}"
        new = C.outline_label(o)
        mapping[lab] = new
        new_heads.append(new)
    SD.set_volumes(M, "several", "", new_heads)
    SD.setup_of(M)["volumes"]["style"] = style
    relabel(M, mapping)
    M.log("outline", f"volumes numbered {dict(VOLUME_STYLES)[style]}")
    M.pending = True
    return {a: b for a, b in mapping.items() if a != b}


def add_volume(M, title):
    """A new volume at the end of the structure ("Volume III Cost"), numbered the volumes' way. Returns its label."""
    title = " ".join((title or "").split()) or "New volume"
    mode, _name, heads = SD.volumes_of(M)                       # before the new heading joins the structure
    heads = list(heads) if mode == "several" else []
    o = {"num": f"Volume {volume_number(volume_style(M), len(heads) + 1)}", "title": title, "level": 1}
    M.outline.append(o)
    lab = C.outline_label(o)
    SD.set_volumes(M, "several", "", heads + [lab])
    M.log("outline", f"volume added: {lab}")
    M.pending = True
    return lab


def add(M, title, parent=None, after=None):
    """A section titled title: under parent (a label: the last child of it), or right after the section after (same
    level), or at the end of the structure at the first level. Returns its new label."""
    title = " ".join((title or "").split())[:160] or "New section"
    if parent:
        pi = index_of(M, parent)
        if pi < 0:
            return None
        at = subtree(M, pi)[-1] + 1
        lvl = M.outline[pi]["level"] + 1
    elif after:
        ai = index_of(M, after)
        if ai < 0:
            return None
        at = subtree(M, ai)[-1] + 1
        lvl = M.outline[ai]["level"]
    else:
        at, lvl = len(M.outline), 1
    o = {"num": "", "title": title, "level": lvl, "auto": True}
    near = M.outline[pi] if parent else (M.outline[ai] if after else None)
    if near is not None and SP.part_of(near) != "body" and near.get("level", 1) <= lvl and C.outline_label(near) not in volume_heads(M):
        o["part"] = SP.part_of(near)               # 3.19.0: a section under (or after) a part's item is in that part
        o["title"] = unique_title(M, o["title"])
    M.outline.insert(at, o)
    renumber(M)
    M.log("outline", f"section added: {C.outline_label(o)}")
    M.pending = True
    return C.outline_label(o)


# ------------------------------------------------------------------ 3.19.0: parts (cover, title page, front matter ...)
def unique_title(M, title, volume=""):
    """An unnumbered item's label is its title: one already used gets the volume's number or a count after it."""
    have = set(labels(M))
    if title not in have:
        return title
    short = (volume.split(" ")[1] if volume.lower().startswith("volume ") and len(volume.split(" ")) > 1 else "")
    cand = f"{title} (Vol {short})" if short else f"{title} (2)"
    n = 2
    while cand in have:
        n += 1
        cand = f"{title} ({n})" if not short else f"{title} (Vol {short}, {n})"
    return cand


def _scope(M, volume=""):
    """(first index, end index, level) of the top-level items of a volume (or of the whole structure)."""
    heads = volume_heads(M)
    if volume and volume in heads:
        vi = index_of(M, volume)
        sub = subtree(M, vi)
        return vi + 1, sub[-1] + 1, M.outline[vi]["level"] + 1
    if heads:
        return None
    return 0, len(M.outline), min((o.get("level", 1) for o in M.outline), default=1)


def _blocks(M, a, b, lvl):
    """[(start, end)] of the top-level blocks between a and b."""
    out, i = [], a
    while i < b:
        if M.outline[i]["level"] == lvl:
            j = subtree(M, i)[-1] + 1
            out.append((i, j)); i = j
        else:
            i += 1
    return out


def add_part_item(M, part, title, volume=""):
    """A cover, title page, front matter item, response section, appendix or back cover at its place in a volume (or the
    response): after the items of its part and of the parts before it. Returns its label, or None."""
    if part not in SP.PART_NAME:
        return None
    heads = volume_heads(M)
    if heads and volume not in heads:
        volume = next(iter(l for l in labels(M) if l in heads), "")
    sc = _scope(M, volume)
    if sc is None:
        return None
    a, b, lvl = sc
    title = " ".join((title or "").split())[:160] or SP.ITEM_NAME[part]
    at = a
    for s, e in _blocks(M, a, b, lvl):
        if SP.ORDER[SP.part_of(M.outline[s])] <= SP.ORDER[part]:
            at = e
    o = {"num": "", "title": title if part in SP.NUMBERED else unique_title(M, title, volume), "level": lvl, "auto": True}
    if part != "body":
        o["part"] = part
    M.outline.insert(at, o)
    renumber(M)
    M.log("outline", f"{SP.ITEM_NAME[part].lower()} added: {C.outline_label(o)}")
    M.pending = True
    return C.outline_label(o)


def set_part(M, label, part):
    """Move an item (with everything under it) to another part of its volume: it takes the part's numbering and its
    place in the order. Only a volume's top-level items move between parts. Returns the new label, or None."""
    i = index_of(M, label)
    if i < 0 or part not in SP.PART_NAME or label in volume_heads(M):
        return None
    p = parent_of(M, i)
    heads = volume_heads(M)
    if p is not None and C.outline_label(M.outline[p]) not in heads:
        return None
    o = M.outline[i]
    before = {id(x): C.outline_label(x) for x in M.outline}
    if not o.get("auto") and (part not in SP.NUMBERED or SP.part_of(o) not in SP.NUMBERED):
        o["auto"] = True                           # the part numbers it (or takes its number off), in renumber
    for k in subtree(M, i):
        if part == "body":
            M.outline[k].pop("part", None)
        else:
            M.outline[k]["part"] = part
    volume = C.outline_label(M.outline[p]) if p is not None else ""
    sc = _scope(M, volume) if (not heads or volume in heads) else None
    if sc is not None:                             # the volume's blocks in part order (a stable sort)
        a, b, lvl = sc
        bl = _blocks(M, a, b, lvl)
        keep = [M.outline[x] for x in range(a, b)]
        order = sorted(bl, key=lambda se: SP.ORDER[SP.part_of(M.outline[se[0]])])
        new = [M.outline[x] for s, e in order for x in range(s, e)]
        loose = [x for x in keep if not any(x is y for y in new)]
        M.outline[a:b] = new + loose
    if part not in SP.NUMBERED and o["title"] in [C.outline_label(x) for x in M.outline if x is not o]:
        o["title"] = unique_title(M, o["title"], volume)     # an unnumbered title already used: say which one
    renumber(M, before)
    M.log("outline", f"moved to {SP.PART_NAME[part]}: {C.outline_label(o)}")
    M.pending = True
    return C.outline_label(o)


def from_sentence(M, it, parent=None, after=None):
    """A section titled with a sentence (its first words, up to 12): the RFP's own wording."""
    words = (it.get("text") or "").split()
    title = " ".join(words[:12]).rstrip(".,;:") + ("..." if len(words) > 12 else "")
    return add(M, title, parent, after)


def rename(M, label, title):
    i = index_of(M, label)
    title = " ".join((title or "").split())[:160]
    if i < 0 or not title:
        return None
    old = C.outline_label(M.outline[i])
    M.outline[i]["title"] = title
    new = C.outline_label(M.outline[i])
    V = SD.setup_of(M).get("volumes") or {}
    if old in (V.get("heads") or []):                             # 3.28.1: a renamed volume stays a volume
        V["heads"] = [new if h == old else h for h in V["heads"]]
    relabel(M, {old: new})
    M.log("outline", f"section renamed: {old} to {new}")
    return new


def delete(M, label):
    """Take a section out: what is under it moves up a level, its sentences go to the section above it (or to no
    section). Returns the label its sentences went to ('' for none)."""
    i = index_of(M, label)
    if i < 0:
        return None
    p = parent_of(M, i)
    to = C.outline_label(M.outline[p]) if p is not None else ""
    for j in subtree(M, i)[1:]:
        M.outline[j]["level"] = max(1, M.outline[j]["level"] - 1)
    M.outline.pop(i)
    S = SD.setup_of(M)
    for it in M.items:
        if it.get("map") == label:
            it["map"] = to
    if label in S["copies"]:
        ids = S["copies"].pop(label)
        if to:
            S["copies"].setdefault(to, []).extend(x for x in ids if x not in S["copies"].get(to, []))
    S["order"].pop(label, None)
    S["owners"].pop(label, None)
    S["progress"].pop(label, None)                 # 3.35.0
    rm = S.get("rfp_map")
    if isinstance(rm, dict):
        for k in [k for k, v in rm.items() if v == label]:
            rm.pop(k)
    V = S.get("volumes") or {}
    if label in (V.get("heads") or []):
        V["heads"] = [h for h in V["heads"] if h != label]
    _hooks({label: to})                            # 3.29.1: its captures go where its sentences go
    renumber(M)
    M.log("outline", f"section removed: {label}")
    M.pending = True
    return to


def move(M, label, delta):
    """Up (-1) or down (+1) past its neighbor at the same level, with everything under it."""
    i = index_of(M, label)
    if i < 0:
        return None
    me = subtree(M, i)
    lvl = M.outline[i]["level"]
    block = [M.outline[k] for k in me]
    if delta < 0:
        j = i - 1
        while j >= 0 and M.outline[j]["level"] > lvl:
            j -= 1
        if j < 0 or M.outline[j]["level"] != lvl:
            return None
        rest = M.outline[:j] + block + M.outline[j:i] + M.outline[me[-1] + 1:]
    else:
        k = me[-1] + 1
        if k >= len(M.outline) or M.outline[k]["level"] != lvl:
            return None
        other = subtree(M, k)
        rest = M.outline[:i] + [M.outline[x] for x in other] + block + M.outline[other[-1] + 1:]
    M.outline[:] = rest
    renumber(M)
    M.pending = True
    return C.outline_label(block[0])


def indent(M, label):
    """Make a section the last child of the section above it at its level (with everything under it)."""
    i = index_of(M, label)
    if i <= 0:
        return None
    lvl = M.outline[i]["level"]
    j = i - 1
    while j >= 0 and M.outline[j]["level"] > lvl:
        j -= 1
    if j < 0 or M.outline[j]["level"] != lvl:
        return None
    for k in subtree(M, i):
        M.outline[k]["level"] += 1
    renumber(M)
    M.pending = True
    return C.outline_label(M.outline[i])


def outdent(M, label):
    i = index_of(M, label)
    if i < 0 or M.outline[i]["level"] <= 1:
        return None
    me = subtree(M, i)
    p = parent_of(M, i)
    block = [M.outline[k] for k in me]
    for o in block:
        o["level"] -= 1
    end = subtree(M, p)[-1] if p is not None else me[-1]       # after the old parent's other children
    rest = [o for k, o in enumerate(M.outline) if k not in me]
    at = rest.index(M.outline[end]) + 1 if end not in me else len(rest)
    M.outline[:] = rest[:at] + block + rest[at:]
    renumber(M)
    M.pending = True
    return C.outline_label(block[0])


def in_volume(M, volume):
    """The labels of the sections in one volume (its heading and everything under it); every label when volume is ''."""
    if not volume:
        return labels(M)
    vos = SD.volume_of_sections(M)
    return [lab for lab in labels(M) if vos.get(lab) == volume]


def volumes_of_item(M, it):
    """The volumes a sentence is in, by the sections it is in."""
    vos = SD.volume_of_sections(M)
    return list(dict.fromkeys(vos.get(s) for s in SD.item_sections(M, it) if vos.get(s)))


# ------------------------------------------------------------------ 3.30.0: the Structure Builder
KINDS = (("", "Numbered heading"), ("unnumbered", "Unnumbered heading"), ("divider", "Divider page"),
         ("placeholder", "Placeholder"), ("element", "Element"))
ORIENTS = (("portrait", "Portrait"), ("landscape", "Landscape"))


def base_level(M, label):
    """The outline level that is Heading 1 for a section: the first level under its volume (1 with no volumes)."""
    heads = volume_heads(M)
    i = index_of(M, label)
    j = i
    while j is not None and j >= 0:
        if C.outline_label(M.outline[j]) in heads:
            return M.outline[j]["level"] + 1
        j = parent_of(M, j)
    return 1


def heading_level(M, label):
    """1 for Heading 1 ... as Word will number it (0 for a volume's own heading)."""
    i = index_of(M, label)
    if i < 0:
        return 0
    if label in volume_heads(M):
        return 0
    return M.outline[i]["level"] - base_level(M, label) + 1


def set_level(M, label, n):
    """Make a section Heading n (with everything under it moving the same way). A heading can go at most one level
    below the section before it. Returns its label, or None."""
    i = index_of(M, label)
    if i < 0 or label in volume_heads(M) or n < 1:
        return None
    base = base_level(M, label)
    want = base + n - 1
    prev = M.outline[i - 1]["level"] if i > 0 else base
    want = max(base, min(want, max(prev, base - 1) + 1))
    d = want - M.outline[i]["level"]
    if d == 0:
        return label
    before = {id(x): C.outline_label(x) for x in M.outline}
    for k in subtree(M, i):
        M.outline[k]["level"] = max(1, M.outline[k]["level"] + d)
    renumber(M, before)
    M.pending = True
    return C.outline_label(M.outline[i])


def set_kind(M, label, kind):
    """A numbered heading, an unnumbered heading, a divider page or a placeholder. Returns the new label."""
    i = index_of(M, label)
    if i < 0 or kind not in dict(KINDS) or label in volume_heads(M):
        return None
    o = M.outline[i]
    if (o.get("kind") or "") == kind:
        return label
    before = {id(x): C.outline_label(x) for x in M.outline}
    if kind:
        o["kind"] = kind
    else:
        o.pop("kind", None)
        o.pop("element", None)
    o["auto"] = True
    if kind in UNNUMBERED:
        o["num"] = ""
        o["title"] = unique_title(M, o["title"]) if o["title"] in [C.outline_label(x) for x in M.outline if x is not o] else o["title"]
    renumber(M, before)
    M.pending = True
    return C.outline_label(o)


def set_break(M, label, orient=None):
    """3.30.0: the section starts a Word section of its own (a new page, its own page setup: portrait or landscape), or
    not (orient None)."""
    i = index_of(M, label)
    if i < 0:
        return None
    o = M.outline[i]
    if orient:
        o["brk"] = {"orient": orient if orient in dict(ORIENTS) else "portrait"}
    else:
        o.pop("brk", None)
    M.pending = True
    return label


def move_to(M, label, target, where="after"):
    """Drag and drop: a section (with everything under it) before, after or into (as the last child of) target.
    Returns its new label, or None."""
    i, t = index_of(M, label), index_of(M, target)
    if i < 0 or t < 0 or label == target:
        return None
    me = subtree(M, i)
    if t in me:
        return None                                 # not into itself
    before = {id(x): C.outline_label(x) for x in M.outline}
    block = [M.outline[k] for k in me]
    tgt = M.outline[t]
    rest = [o for k, o in enumerate(M.outline) if k not in me]
    ti = next(n for n, o in enumerate(rest) if o is tgt)
    tsub = [ti]
    while tsub[-1] + 1 < len(rest) and rest[tsub[-1] + 1]["level"] > tgt["level"]:
        tsub.append(tsub[-1] + 1)
    if where == "into":
        lvl, at = tgt["level"] + 1, tsub[-1] + 1
    elif where == "before":
        lvl, at = tgt["level"], ti
    else:
        lvl, at = tgt["level"], tsub[-1] + 1
    d = lvl - block[0]["level"]
    for o in block:
        o["level"] = max(1, o["level"] + d)
    M.outline[:] = rest[:at] + block + rest[at:]
    renumber(M, before)
    M.pending = True
    return C.outline_label(block[0])


def lib_items(M, label):
    """3.30.0: the library items placed in a section, in order: [{"id", "kind", "name", "where"}] (where: before or
    after the section's requirements)."""
    i = index_of(M, label)
    return list(M.outline[i].get("lib") or []) if i >= 0 else []


def place_lib(M, label, item, where="before"):
    """Place a library item (a Quick Part, a table look, a cover...) in a section. Returns its place in the list."""
    i = index_of(M, label)
    if i < 0 or not item or not item.get("id"):
        return None
    lst = M.outline[i].setdefault("lib", [])
    lst.append({"id": str(item["id"]), "kind": str(item.get("kind", "")), "name": str(item.get("name", ""))[:160],
                "where": "after" if where == "after" else "before"})
    M.pending = True
    return len(lst) - 1


def unplace_lib(M, label, n):
    i = index_of(M, label)
    lst = M.outline[i].get("lib") or [] if i >= 0 else []
    if not 0 <= n < len(lst):
        return False
    lst.pop(n)
    M.pending = True
    return True


def move_lib(M, label, n, delta):
    i = index_of(M, label)
    lst = M.outline[i].get("lib") or [] if i >= 0 else []
    j = n + delta
    if not (0 <= n < len(lst) and 0 <= j < len(lst)):
        return False
    lst[n], lst[j] = lst[j], lst[n]
    M.pending = True
    return True
