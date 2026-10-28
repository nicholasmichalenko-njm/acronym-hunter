"""Build the response structure while you assign (2.68.0): add a volume, a heading, or a subheading under any section
(as many levels deep as you need), rename, move up or down, indent or outdent, delete, or make a section from a
sentence. Sections made here number themselves by where they sit (1, 1.1, 1.1.1 ...), restarting in each volume; a
section brought in from the RFP or typed keeps its own number. When numbers change, every requirement, support
sentence, owner and setup entry follows its section. Rules only (No AI); nothing leaves the PC.
"""
import re
import compliance as C
import setupdoc as SD

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
def relabel(M, mapping):
    """Move everything kept under an old section label to its new label: the sentences' sections, their copies and
    order in the setup, section people, notes, volume headings."""
    mapping = {a: b for a, b in mapping.items() if a != b}
    if not mapping:
        return 0
    S = SD.setup_of(M)
    for it in M.items:
        if it.get("map") in mapping:
            it["map"] = mapping[it["map"]]
    for key in ("copies", "order", "owners", "mgmt"):
        d = S.get(key)
        if isinstance(d, dict):
            for a, b in mapping.items():
                if a in d:
                    d[b] = d.pop(a)
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


def renumber(M):
    """Number every section made here by where it sits: within a volume heading, 1, 2, 3 at its first level, 1.1 under
    1, and so on, as deep as it goes. Returns {old label: new label}."""
    heads = volume_heads(M)
    old = labels(M)
    counters = {}                                  # (parent index) -> sections seen under it so far
    nums = {}
    for i, o in enumerate(M.outline):
        p = parent_of(M, i)
        counters[p] = counters.get(p, 0) + 1       # 2.69.0: every sibling counts, typed or made here
        if not o.get("auto"):
            nums[i] = o.get("num", "")
            continue
        n = counters[p]
        base = ""
        if p is not None and C.outline_label(M.outline[p]) not in heads:
            base = nums.get(p, M.outline[p].get("num", ""))
            base = base if re.match(r"^[0-9A-Za-z]+(\.[0-9A-Za-z]+)*$", base or "") else ""
        o["num"] = f"{base}.{n}" if base else str(n)
        nums[i] = o["num"]
    mapping = {a: C.outline_label(o) for a, o in zip(old, M.outline)}
    relabel(M, mapping)
    return {a: b for a, b in mapping.items() if a != b}


# ------------------------------------------------------------------ edits
def add_volume(M, title):
    """A new volume at the end of the structure ("Volume III Cost"). Returns its label."""
    title = " ".join((title or "").split()) or "New volume"
    mode, _name, heads = SD.volumes_of(M)                       # before the new heading joins the structure
    heads = list(heads) if mode == "several" else []
    o = {"num": f"Volume {roman(len(heads) + 1)}", "title": title, "level": 1}
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
    M.outline.insert(at, o)
    renumber(M)
    M.log("outline", f"section added: {C.outline_label(o)}")
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
    rm = S.get("rfp_map")
    if isinstance(rm, dict):
        for k in [k for k, v in rm.items() if v == label]:
            rm.pop(k)
    V = S.get("volumes") or {}
    if label in (V.get("heads") or []):
        V["heads"] = [h for h in V["heads"] if h != label]
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
