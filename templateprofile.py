"""Template profiles (3.33.0): a document profile seen as the parts a template is built from, in the order a response
runs, each filled from a version kept in the template library and pinned to it.

A slot is one part of the profile: its cover, the header and footer of each part, its base fonts and sizes, theme,
heading and list numbering, pagination scheme, table looks and table of contents. A slot either holds the profile's
own values or a library version, recorded on the profile as a pin ({"id", "family", "version"} in std["library_pins"]).
A newer version of a pinned family waits until the person chooses it (Use v4), so a template already made never
changes under it. Save as a new version keeps what the profile holds now as the next version of that family (or a new
family). Rules only; nothing leaves the PC."""
import copy, hashlib, os

# (slot key, the profile part it belongs to, what it is, library kind)
SLOTS = (("cover", "Cover", "Cover page", "cover"),
         ("hf:front", "Front matter", "Header and footer", "hf_design"),
         ("toc", "Front matter", "Table of contents", "toc"),
         ("hf:body", "Response", "Header and footer", "hf_design"),
         ("hf:appendix", "Appendices", "Header and footer", "hf_design"),
         ("backer", "Back cover", "Back cover page", "backer"),
         ("variables", "Whole document", "Base fonts and sizes", "variables"),
         ("theme", "Whole document", "Theme (colors and fonts)", "theme"),
         ("heading_numbering", "Whole document", "Heading numbering", "heading_numbering"),
         ("pagination", "Whole document", "Pagination scheme", "pagination"),
         ("table_look", "Whole document", "Table looks", "table_look"))
KIND_OF = {s: k for s, _p, _w, k in SLOTS}


def slots(std):
    """The slots of a profile: the fixed ones, then one per list of its list numbering (Bullets, Numbers...)."""
    out = list(SLOTS)
    for lst in ((std or {}).get("list_numbering") or {}).get("lists") or []:
        if lst.get("name"):
            out.append((f"list:{lst['name']}", "Whole document", f"List numbering: {lst['name']}", "list_numbering"))
    return out


def kind_of(slot):
    return "list_numbering" if slot.startswith("list:") else KIND_OF.get(slot, "")


def pins(std):
    return (std or {}).get("library_pins") or {}


def state(std, lib, slot):
    """{"pin", "item", "newer"} for a slot: the pinned library version (None when the slot holds the profile's own
    values) and the family's newest version when it is newer than the pin."""
    p = pins(std).get(slot)
    item = lib.get(p["id"]) if p and p.get("id") else None
    newer = None
    if item is not None:
        top = lib.latest(item["id"])
        if top is not None and int(top.get("version") or 0) > int(item.get("version") or 0):
            newer = top
    return {"pin": p, "item": item, "newer": newer}


def choices(lib, slot):
    """The library items that can fill a slot, family by family, newest version first."""
    k = kind_of(slot)
    items = [i for i in lib.items if i["kind"] == k]           # a header and footer design serves any part
    return sorted(items, key=lambda i: (lib.base_of(i).casefold(), -int(i.get("version") or 0)))


def current_values(std, slot, parts_dir=""):
    """What the profile holds now for a slot, as the library keeps that kind (None when it holds nothing)."""
    std = std or {}
    k = kind_of(slot)
    if k in ("cover", "backer"):
        fn = (std.get("page_parts") or {}).get(slot)
        p = os.path.join(parts_dir or "", fn or "")
        if not fn or not os.path.isfile(p):
            return None
        return {"file": fn, "sha": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "_tmp": p}
    if k == "hf_design":
        part = slot.split(":", 1)[1]
        d = (std.get("hf_designs") or {}).get(part)
        return dict(copy.deepcopy(d), part=part) if d else None
    if k == "table_look":
        return {"row_types": copy.deepcopy(std.get("row_types") or {}), "table_types": copy.deepcopy(std.get("table_types") or {})}
    if k == "list_numbering":
        name = slot.split(":", 1)[1]
        return copy.deepcopy(next((l for l in (std.get("list_numbering") or {}).get("lists") or [] if l.get("name") == name), None))
    v = std.get(k)
    return copy.deepcopy(v) if v else None


def pick(std, lib, slot, iid, config_dir):
    """Fill a slot from a library version and pin it. Returns what it changed, in words."""
    import templatelib as TL
    item = lib.get(iid)
    if item is None or item["kind"] != kind_of(slot):
        return ""
    v = lib.values(item) or {}
    cat = slot.split(":", 1)[1] if slot.startswith("hf:") else ""
    said = TL.use_values(config_dir, item["kind"], lib.base_of(item), v, std, category=cat, file_path=lib.source_path)
    std.setdefault("library_pins", {})[slot] = {"id": item["id"], "family": item.get("family", item["id"]),
                                                "version": int(item.get("version") or 1)}
    return said or lib.shown_name(item)


def unpin(std, slot):
    """The slot keeps the values it has as the profile's own; the pin comes off."""
    return bool((std.get("library_pins") or {}).pop(slot, None))


def save_version(std, lib, slot, name="", label="", note="", parts_dir=""):
    """What the profile holds now for a slot, kept in the library: the next version of the pinned family (or of the
    family of that name), else a new family named name. The slot is pinned to it. Returns (item, state)."""
    v = current_values(std, slot, parts_dir)
    if v is None:
        return None, "empty"
    k = kind_of(slot)
    if k in ("cover", "backer"):
        v["file"] = lib.keep_file(v.pop("_tmp"), v["file"])
    p = pins(std).get(slot)
    fam = lib.get(p["id"]) if p and p.get("id") else None
    if fam is None and name:
        fam = next((i for i in lib.items if i["kind"] == k and lib.base_of(i).casefold() == name.casefold()), None)
    if fam is not None:
        item, st = lib.save_version(fam["id"], v, label=label, note=note)
    else:
        item, st = lib.add(k, name or slot, v, summary=f"saved from a profile: {slot}")
        if label or note:
            lib.set_label(item["id"], label, note)
    std.setdefault("library_pins", {})[slot] = {"id": item["id"], "family": item.get("family", item["id"]),
                                                "version": int(item.get("version") or 1)}
    return item, st
