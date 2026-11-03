"""Response elements (3.30.0): every piece of a response the team adds again and again, defined once. A Table of
Contents, the List of Figures, Tables and Appendices, Acronyms and Abbreviations, Units of Measurement, a cover letter,
the Appendices section: each has a name, the part of the volume it sits in, what fills it (its source), the pages it
takes, whether it counts toward the page limit, its order in its part, and, for library content, the library item it
uses. An effort type's kit is the elements a volume of that type starts with.

The Structure Builder adds them to a volume in one tick list; Make templates builds them (3.30.1).

Kept in <config>/response_elements.json: only what the team changed from the built-ins, its own elements and the kits.
Rules only; nothing leaves the PC, and the team data never goes to GitHub."""
import copy, json, os, re, uuid

FILE = "response_elements.json"
PARTS = (("cover", "Cover"), ("title", "Title page"), ("front", "Front matter"), ("body", "Response"),
         ("appendix", "Appendices"), ("back", "Back cover"))
PART_NAME = dict(PARTS)
SOURCES = (("toc", "Table of contents (a field from the TOC design)"),
           ("list_figure", "List of figures (a caption list)"),
           ("list_table", "List of tables (a caption list)"),
           ("list_appendix", "List of appendices (the appendix headings)"),
           ("acronyms", "Acronyms and abbreviations (the volume's approved acronyms)"),
           ("units", "Units of measurement (the units list)"),
           ("matrix", "Compliance matrix (a cross-reference table)"),
           ("quickpart", "Library content (a Quick Part)"),
           ("cover", "A cover from the library"),
           ("backer", "A back cover from the library"),
           ("divider", "A divider page (its title only)"),
           ("placeholder", "A placeholder (pages for authors to fill)"))
SOURCE_NAME = dict(SOURCES)
LIB_SHELF = {"quickpart": "quickpart", "cover": "cover", "backer": "backer"}     # a source that uses a library item
# id, name, part, source, pages, counts, order
BUILTIN = (("cover", "Cover", "cover", "cover", 1, False, 10),
           ("title", "Title page", "title", "placeholder", 1, False, 20),
           ("letter", "Cover letter", "front", "quickpart", 1, False, 30),
           ("toc", "Table of Contents", "front", "toc", 2, False, 40),
           ("lof", "List of Figures", "front", "list_figure", 1, False, 50),
           ("lot", "List of Tables", "front", "list_table", 1, False, 60),
           ("loa", "List of Appendices", "front", "list_appendix", 1, False, 70),
           ("acr", "Acronyms and Abbreviations", "front", "acronyms", 2, False, 80),
           ("uom", "Units of Measurement", "front", "units", 1, False, 90),
           ("matrix", "Compliance matrix", "front", "matrix", 2, False, 100),
           ("exec", "Executive Summary", "body", "placeholder", 2, True, 110),
           ("appendices", "Appendices", "appendix", "divider", 1, False, 120),
           ("back", "Back cover", "back", "backer", 1, False, 200))
DEFAULT_KIT = ["cover", "toc", "lof", "lot", "acr"]
FIELDS = ("name", "part", "source", "pages", "counts", "order", "lib", "shown")


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def _read(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _clean(e):
    out = {"id": str(e.get("id") or uuid.uuid4().hex[:8]), "name": " ".join(str(e.get("name") or "").split())[:120] or "Element",
           "part": e.get("part") if e.get("part") in PART_NAME else "front",
           "source": e.get("source") if e.get("source") in SOURCE_NAME else "placeholder",
           "pages": max(0, min(200, int(e.get("pages") or 0))) if str(e.get("pages") or "0").isdigit() else 1,
           "counts": bool(e.get("counts")), "order": int(e.get("order") or 0), "lib": str(e.get("lib") or "")[:160],
           "shown": e.get("shown", True) is not False}
    return out


def builtins():
    """3.30.1: the built-in elements and kit, with nothing of the team's (for a document made without the Settings)."""
    return load(None)


def load(config_dir):
    """{"elements": [element, in part and order], "kits": {effort type id ("" for any): [element ids]}}."""
    saved = _read(config_dir) if config_dir else {}
    changed = saved.get("changed") or {}
    out = []
    for eid, name, part, source, pages, counts, order in BUILTIN:
        e = {"id": eid, "name": name, "part": part, "source": source, "pages": pages, "counts": counts, "order": order,
             "lib": "", "shown": True, "builtin": True}
        e.update({k: v for k, v in (changed.get(eid) or {}).items() if k in FIELDS})
        out.append(_clean(e) | {"builtin": True})
    for e in saved.get("custom") or []:
        if isinstance(e, dict) and e.get("name"):
            out.append(_clean(e) | {"builtin": False})
    order = {k: n for n, (k, _t) in enumerate(PARTS)}
    out.sort(key=lambda e: (order[e["part"]], e["order"], e["name"].casefold()))
    kits = {"": list(DEFAULT_KIT)}
    for k, v in (saved.get("kits") or {}).items():
        if isinstance(v, list):
            kits[str(k)] = [x for x in v if any(e["id"] == x for e in out)]
    return {"elements": out, "kits": kits}


def save(config_dir, data):
    """Only what differs from the built-ins, the team's own elements and the kits are written."""
    base = {eid: {"name": name, "part": part, "source": source, "pages": pages, "counts": counts, "order": order, "lib": "",
                  "shown": True} for eid, name, part, source, pages, counts, order in BUILTIN}
    changed, custom = {}, []
    for e in data.get("elements") or []:
        e = dict(e)
        if e.get("id") in base:
            diff = {k: e[k] for k in FIELDS if k in e and e[k] != base[e["id"]][k]}
            if diff:
                changed[e["id"]] = diff
        else:
            c = _clean(e); c.pop("builtin", None)
            custom.append(c)
    kits = {k: list(v) for k, v in (data.get("kits") or {}).items() if k != "" or v != DEFAULT_KIT}
    out = {"format": 1, "changed": changed, "custom": custom, "kits": kits}
    os.makedirs(config_dir, exist_ok=True)
    with open(_path(config_dir) + ".tmp", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    os.replace(_path(config_dir) + ".tmp", _path(config_dir))
    return out


def reset(config_dir):
    try:
        os.remove(_path(config_dir))
    except OSError:
        pass
    return load(config_dir)


def get(data, eid):
    return next((e for e in data["elements"] if e["id"] == eid), None)


def add(data, name, part="front", source="placeholder", pages=1, counts=False, lib=""):
    """A team element of its own. Returns it."""
    same = [e for e in data["elements"] if e["part"] == part]
    e = _clean({"id": "e" + uuid.uuid4().hex[:7], "name": name, "part": part, "source": source, "pages": pages,
                "counts": counts, "lib": lib, "order": max([x["order"] for x in same] or [0]) + 10}) | {"builtin": False}
    data["elements"].append(e)
    return e


def remove(data, eid):
    e = get(data, eid)
    if e is None or e.get("builtin"):
        return False
    data["elements"] = [x for x in data["elements"] if x["id"] != eid]
    for k in data["kits"]:
        data["kits"][k] = [x for x in data["kits"][k] if x != eid]
    return True


def move(data, eid, delta):
    """Earlier (-1) or later (+1) within its part."""
    e = get(data, eid)
    if e is None:
        return False
    same = sorted([x for x in data["elements"] if x["part"] == e["part"]], key=lambda x: x["order"])
    i = same.index(e)
    j = i + delta
    if not 0 <= j < len(same):
        return False
    for n, x in enumerate(same):
        x["order"] = (n + 1) * 10
    same[i]["order"], same[j]["order"] = same[j]["order"], same[i]["order"]
    return True


def kit(data, effort_type=""):
    """The element ids a volume of this effort type starts with (the team's default kit when the type has none)."""
    return list(data["kits"].get(effort_type or "", data["kits"].get("", DEFAULT_KIT)))


def set_kit(data, effort_type, ids):
    data["kits"][effort_type or ""] = [x for x in ids if get(data, x)]


def in_volume(M, volume=""):
    """{element id: label} of the elements already in a volume of the structure."""
    import compliance as C
    import outline_ops as O
    labs = set(O.in_volume(M, volume))
    return {o["element"]: C.outline_label(o) for o in M.outline if o.get("element") and C.outline_label(o) in labs}


def add_to_volume(M, e, volume="", data=None):
    """An element into a volume: in its part, before the first element of that part that comes later in the team's
    order. Returns its label."""
    import compliance as C
    import outline_ops as O
    import structparts as SP
    lab = O.add_part_item(M, e["part"], e["name"], volume)
    if lab is None:
        return None
    o = M.outline[O.index_of(M, lab)]
    o["element"], o["kind"], o["auto"] = e["id"], "element", True
    rank = {x["id"]: x["order"] for x in (data or {}).get("elements", [])}
    rank.setdefault(e["id"], e["order"])
    sc = O._scope(M, volume if volume in O.volume_heads(M) else "")
    if sc is not None:
        a, b, lvl = sc
        blocks = O._blocks(M, a, b, lvl)
        me = next(((s_, t_) for s_, t_ in blocks if M.outline[s_] is o), None)
        later = next(((s_, t_) for s_, t_ in blocks if M.outline[s_] is not o and SP.part_of(M.outline[s_]) == e["part"]
                      and M.outline[s_].get("element") and rank.get(M.outline[s_]["element"], 10 ** 6) > rank[e["id"]]), None)
        if me is not None and later is not None and later[0] < me[0]:
            block = M.outline[me[0]:me[1]]
            del M.outline[me[0]:me[1]]
            M.outline[later[0]:later[0]] = block
    O.renumber(M)
    M.pending = True
    return C.outline_label(o)


def apply_kit(M, data, ids, volume=""):
    """The elements ticked for a volume: add those not in it yet, in order; the ones unticked come out. Returns
    (added labels, removed labels)."""
    import outline_ops as O
    have = in_volume(M, volume)
    added, removed = [], []
    for eid, lab in have.items():
        if eid not in ids:
            O.delete(M, lab)
            removed.append(lab)
    for e in data["elements"]:
        if e["id"] in ids and e["id"] not in have:
            lab = add_to_volume(M, e, volume, data)
            if lab:
                added.append(lab)
    return added, removed


def tag(o, level=None):
    """The short tag the structure shows for a section: H1 to H9 (deeper: H10...), UN, DIV, PH, EL, and SEC for one
    that starts a Word section."""
    k = o.get("kind") or ""
    if k == "element":
        t = "EL"
    elif k == "divider":
        t = "DIV"
    elif k == "placeholder":
        t = "PH"
    elif k == "unnumbered":
        t = "UN"
    else:
        t = f"H{int(level if level is not None else (o.get('level', 1) or 1))}"
    return t + (" SEC" if o.get("brk") else "")

