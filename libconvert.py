"""Your standards become library items (3.49.0), once, from what this PC holds. Nothing is deleted: the standards stay
as they are and keep making templates until profiles replace them (3.51.0).

  The Global Standards's styles, numbering, lists, page setups, pagination, theme and base fonts, its headers and
  footers, covers, title pages, back covers, table looks, captions, TOC and Quick Parts: items tagged every effort
  type, from "Global Standards".
  A profile's changes: new versions of those items, labelled with the profile's name and tagged with the effort types
  that hold the profile.
  An effort type's changes (shared, and for one profile): new versions labelled with its name, tagged that effort type.

Each item holds the whole value as that layer makes it (the Global Standards merged with the layer), so it builds the
same on its own. The same values met twice are one item (its effort-type tags grow). Converting again adds only what
changed. converted.json in the library folder records that it ran."""
import hashlib, json, os

import libcats as LC
import prodrules as PRL
import templatelib as TL

MARK = "converted.json"
NAMED = (("style_defs", "style"), ("page_setups", "page_setup"), ("table_styles", "table_style"), ("hf_layouts", "hf"))
PAGE_KIND = {"cover": ("cover", "Cover"), "backer": ("backer", "Back cover"), "title": ("title", "Title page")}


def items_of(layer, resolved, config_dir, whole=False):
    """[(kind, name, values, summary)] for what a layer sets (whole: everything the resolved standard holds), each value
    taken from the resolved standard."""
    out = []
    has = (lambda k: bool(resolved.get(k))) if whole else (lambda k: k in layer)
    for key, kind in NAMED:
        names = (resolved.get(key) or {}) if whole else (layer.get(key) or {})
        for n in names:
            v = (resolved.get(key) or {}).get(n)
            if isinstance(v, dict):
                out.append((kind, n, v, TL._summary_style(v) if kind == "style" else ""))
    for k, v in ((resolved.get("hf_designs") or {}) if whole else (layer.get("hf_designs") or {})).items():
        v = (resolved.get("hf_designs") or {}).get(k)
        if isinstance(v, dict):
            out.append(("hf_design", f"Header and footer design: {k}", dict(v, part=k), f"{k}: header and footer as built"))
    if has("variables"):
        va = {k: v for k, v in (resolved.get("variables") or {}).items() if v not in (None, "")}
        out.append(("variables", "Base fonts and sizes", va, ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in list(va.items())[:8])))
    if has("pagination") and resolved.get("pagination"):
        p = resolved["pagination"]
        out.append(("pagination", p.get("name") or "Pagination", p, ", ".join(str(x.get("name") or x.get("key") or "") for x in p.get("parts", []))))
    hn = resolved.get("heading_numbering") or {}
    if has("heading_numbering") and hn.get("levels"):
        out.append(("heading_numbering", "Heading numbering", hn, "; ".join(f"{l.get('style')} {l.get('text')}" for l in hn["levels"][:4])))
    ln = resolved.get("list_numbering") or {}
    if has("list_numbering"):
        want = {l.get("name") for l in (layer.get("list_numbering") or {}).get("lists", [])} if not whole else None
        for l in ln.get("lists", []):
            if want is None or l.get("name") in want:
                out.append(("list_numbering", l.get("name") or "List", l, ", ".join(f"{v.get('style')} {v.get('text')}" for v in l.get("levels", [])[:3])))
    if has("theme") and (resolved.get("theme") or {}).get("xml"):
        th = resolved["theme"]
        out.append(("theme", th.get("name") or "Theme", th, "Word's 12 theme colors and the theme fonts"))
    if any(has(k) for k in ("row_types", "table_types")):
        out.append(("table_look", "Table looks", {k: resolved[k] for k in ("row_types", "table_types") if resolved.get(k)},
                    "; ".join(f"{r}: fill {(lk or {}).get('fill') or 'none'}" for r, lk in (resolved.get("row_types") or {}).items())))
    if has("toc") and resolved.get("toc"):
        out.append(("toc", "Table of contents", resolved["toc"], " ".join(resolved["toc"].get("switches", []))))
    if has("captions") and resolved.get("captions"):
        out.append(("captions", "Captions", {"captions": resolved["captions"]},
                    ", ".join(f"{c.get('label')} {c.get('position')} ({c.get('part')})" for c in resolved["captions"][:4])))
    import prodparts as PP
    pdir = PP.parts_dir(config_dir)
    for where, fn in ((resolved.get("page_parts") or {}) if whole else (layer.get("page_parts") or {})).items():
        fn = (resolved.get("page_parts") or {}).get(where)
        if where in PAGE_KIND and fn and os.path.isfile(os.path.join(pdir, fn)):
            kind, name = PAGE_KIND[where]
            out.append((kind, name, {"file": fn, "_from": os.path.join(pdir, fn)}, "the page as built"))
    qp = resolved.get("quick_parts") or {}
    if has("quick_parts"):
        for e in qp.get("entries", []):
            if e.get("source") and os.path.isfile(os.path.join(pdir, e["source"])):
                out.append(("quickpart", e["name"], {"entry": e["name"], "category": e.get("category") or "", "gallery": e.get("gallery") or "",
                                                     "description": e.get("description") or "", "_from": os.path.join(pdir, e["source"]),
                                                     **({"as_built": True} if e.get("as_built") else {})},
                            f"{e.get('category') or 'no category'}"))
    return out


def layers(data):
    """[(label, layer, resolved, effort types, whole)] in the order they convert: the Global Standards, each profile,
    each effort type's shared changes, each effort type's changes for one profile."""
    ets_all = [e["id"] for e in data.get("effort_types", [])]
    out = [("Global Standards", data["company"], data["company"], [LC.ALL], True)]
    for t in data["types"]:
        lay = PRL.layer_of(t)
        if lay:
            holds = [e["id"] for e in data.get("effort_types", []) if t["id"] in (e.get("profiles") or [])]
            ets = [LC.ALL] if not ets_all or set(holds) == set(ets_all) else holds
            out.append((t["name"], lay, PRL.merge(data["company"], lay), ets, False))
    for e in data.get("effort_types", []):
        lay = PRL.effort_layer_of(e)
        if lay:
            out.append((e["name"], lay, PRL.merge(data["company"], lay), [e["id"]], False))
        for tid, over in (e.get("profile_over") or {}).items():
            if over:
                t = PRL.type_of(data, tid)
                out.append((f"{e['name']}, {t['name']}", over, PRL.resolved_type(data, tid, e["id"]), [e["id"]], False))
    return out


def _fingerprint(config_dir):
    try:
        return hashlib.sha256(open(os.path.join(config_dir, PRL.FILE), "rb").read()).hexdigest()[:16]
    except OSError:
        return ""


def done(config_dir):
    return os.path.isfile(os.path.join(TL.folder(config_dir), MARK))


def convert(config_dir, lib=None, who=None):
    """Converts the standards on this PC into library items, all or nothing. Returns {"new", "same", "version",
    "layers"} (counts)."""
    lib = lib or TL.Library(config_dir)
    lib.fresh()
    data = PRL.load(config_dir)
    rep = {"new": 0, "same": 0, "version": 0, "layers": 0}
    with lib.transaction():
        for label, lay, res, ets, whole in layers(data):
            rep["layers"] += 1
            src = label if whole else label
            for kind, name, values, summary in items_of(lay, res, config_dir, whole):
                values = dict(values)
                frm = values.pop("_from", None)
                if frm:
                    fn = lib.keep_file(frm, os.path.basename(frm))
                    values["file" if kind != "quickpart" else "source"] = fn
                st, hit = lib.match(kind, name, values)
                if st == "same":
                    t = hit.setdefault("tags", {})
                    have = LC.effort_types(hit)
                    t["effort_types"] = [LC.ALL] if LC.ALL in have + ets else sorted(set(have) | set(ets))
                    rep["same"] += 1
                    continue
                if st == "variant":
                    item, _s = lib.save_version(hit["id"], values, label=label, who=who)
                    rep["version"] += 1
                else:
                    item, _s = lib._new(kind, name, values, None, "", summary, who)
                    rep["new"] += 1
                item.setdefault("tags", {})["effort_types"] = list(ets)
                item["source"] = src
                item["summary"] = (summary or item.get("summary") or "")[:300]
                item["status"] = "approved"
                item["converted"] = True
        p = os.path.join(lib.root, MARK)
        lib._wrote(p)
        os.makedirs(lib.root, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"at": TL._now(), "standards": _fingerprint(config_dir), "counts": rep}, f, indent=1)
    return rep


def ensure(config_dir):
    """Converts once (the first time the libraries open). Returns the counts, or None when it ran before."""
    if done(config_dir):
        return None
    return convert(config_dir)


def rebuild_check(config_dir, lib=None):
    """The Global Standards rebuilt from its converted items: [(what, standard's value, from the library)] that differ.
    Empty when the library holds the Global Standards whole."""
    lib = lib or TL.Library(config_dir)
    data = PRL.load(config_dir)
    company = data["company"]
    work = {}
    for i in lib.items:
        if i.get("converted") and i.get("source") in ("Global Standards", "Global standard"):   # 4.7.0: the old name too
            TL.use_in_standard(lib, i["id"], work)
    out = []
    for key in ("style_defs", "page_setups", "table_styles", "hf_layouts", "variables", "pagination", "toc", "captions",
                "row_types", "table_types", "hf_designs"):
        a, b = company.get(key), work.get(key)
        if key == "variables":
            a = {k: v for k, v in (a or {}).items() if v not in (None, "")}
        if (a or None) != (b or None):
            out.append((key, a, b))
    return out
