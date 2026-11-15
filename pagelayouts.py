"""Page layouts and numbering as named components (4.42.0; ST29 of 2026-11-14, way A of the board of 2026-11-15).
A page layout is a name and the page it describes: paper, the four margins and the page setups (header and footer
distances, the landscape and foldout pages). A numbering is a name and how things are numbered: heading numbering, page
numbers by part and captions. Each is taken from standards that exist (the Global Standards, or a profile as an effort
type sees it), so nothing is typed twice; a page layout's paper and margins can then be changed. A named template picks
one of each (templatesets.recipe: "layout", "numbering"); with no pick it reads the Global Standards as before.

One answer per volume: a volume's checks read its profile and effort type. differs() and disagree() say where a
template's pick and the volume's standards part ways, so the app can say so until profiles and effort types pick named
layouts too.

<config>\\layouts_named.json: {"format": 1, "layout": {id: {name, values}}, "numbering": {id: {name, values}}}.
Rules only; nothing leaves the PC."""
import copy, json, os, uuid

FILE = "layouts_named.json"
FORMAT = 1
KINDS = (("layout", "Page layout", "Page layouts"), ("numbering", "Numbering", "Numbering"))
MARGINS = ("margin_top", "margin_bottom", "margin_left", "margin_right")
VARS = ("paper",) + MARGINS                               # the variables a page layout holds
WHOLE = {"layout": ("page_setups",), "numbering": ("heading_numbering", "pagination", "captions")}
SHARED = "From the standards, the same for every template"


def _path(config_dir):
    return os.path.join(__import__("effortset").base(config_dir), FILE)


def load(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    out = {"format": FORMAT}
    for kind, _n, _p in KINDS:
        out[kind] = {k: v for k, v in (d.get(kind) or {}).items() if isinstance(v, dict) and v.get("name")}
    return out


def save(config_dir, d):
    p = _path(config_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    d["format"] = FORMAT
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def every(config_dir, kind):
    """[{id, name, values}] by name."""
    return sorted((dict(v, id=k) for k, v in load(config_dir)[kind].items()), key=lambda x: x["name"].casefold())


def get(config_dir, kind, iid):
    v = load(config_dir)[kind].get(iid) if iid else None
    return dict(v, id=iid) if v else None


def _clean(name):
    return " ".join(str(name or "").split())[:80]


def _free(d, kind, name, but=None):
    return bool(name) and not any(v["name"].casefold() == name.casefold() for k, v in d[kind].items() if k != but)


def extract(std, kind):
    """The values of this kind that a standard holds."""
    out = {}
    if kind == "layout":
        v = std.get("variables") or {}
        out["variables"] = {k: copy.deepcopy(v[k]) for k in VARS if k in v}
    for k in WHOLE[kind]:
        if k in std:
            out[k] = copy.deepcopy(std[k])
    return out


def sources(config_dir, data=None):
    """[(label, standard)] to take a new one from: the Global Standards, each profile, and each profile as an effort
    type sees it where that differs."""
    import prodrules as PRL
    data = data or PRL.load(config_dir)
    out = [("Global Standards", data["company"])]
    for t in data["types"]:
        std = PRL.resolved_type(data, t["id"])
        out.append((f"Effort Profile: {t['name']}", std))
        for e in data.get("effort_types") or []:
            if t["id"] not in (e.get("profiles") or []):
                continue
            es = PRL.resolved_type(data, t["id"], e["id"])
            if extract(es, "layout") != extract(std, "layout") or extract(es, "numbering") != extract(std, "numbering"):
                out.append((f"Effort type: {e['name']}, {t['name']}", es))
    return out


def new(config_dir, kind, name, std):
    """A new one of this kind, holding what std holds. Its name must be free among its kind. Returns it, or None."""
    d = load(config_dir)
    name = _clean(name)
    if not _free(d, kind, name):
        return None
    iid = uuid.uuid4().hex[:10]
    d[kind][iid] = {"name": name, "values": extract(std, kind)}
    save(config_dir, d)
    return dict(d[kind][iid], id=iid)


def rename(config_dir, kind, iid, name):
    d = load(config_dir)
    name = _clean(name)
    if iid not in d[kind] or not _free(d, kind, name, iid):
        return False
    d[kind][iid]["name"] = name
    save(config_dir, d)
    return True


def used_by(config_dir, kind, iid):
    """The names of the templates that pick it."""
    import namedtemplates as NT
    return [t["name"] for t in NT.every(config_dir) if ((t.get("sets") or {}).get(kind) or "") == iid]


def remove(config_dir, kind, iid):
    """Removes it unless a template picks it. Returns True when removed."""
    d = load(config_dir)
    if iid not in d[kind] or used_by(config_dir, kind, iid):
        return False
    del d[kind][iid]
    save(config_dir, d)
    return True


def set_page(config_dir, iid, paper=None, margins=None):
    """Changes a page layout's paper and its four margins (inches: top, bottom, left, right). Returns it, or None."""
    import prodrules as PRL
    d = load(config_dir)
    it = d["layout"].get(iid)
    if it is None:
        return None
    v = it["values"].setdefault("variables", {})
    if paper:
        if paper not in PRL.PAGE_SIZES:
            return None
        v["paper"] = paper
    if margins is not None:
        try:
            m = [round(float(x), 3) for x in margins]
        except (TypeError, ValueError):
            return None
        if len(m) != 4 or any(x < 0 or x > 5 for x in m):
            return None
        for k, x in zip(MARGINS, m):
            v[k] = x
    save(config_dir, d)
    return dict(it, id=iid)


def put(std, values):
    """Writes a component's values over a standard, in place. Returns std."""
    for k, v in (values or {}).items():
        if k == "variables":
            std.setdefault("variables", {}).update(copy.deepcopy(v))
        else:
            std[k] = copy.deepcopy(v)
    return std


def apply(std, config_dir, rec):
    """The template's picks written over its standard. A pick that is gone is read as no pick."""
    for kind, _n, _p in KINDS:
        it = get(config_dir, kind, (rec or {}).get(kind))
        if it:
            put(std, it["values"])
    return std


# ------------------------------------------------------------------ words
def _in(x):
    return f"{x:g} in"


def layout_words(values):
    """'Letter, 0.75 in margins; header and footer at 0.5 in'."""
    v = (values or {}).get("variables") or {}
    m = [v.get(k) for k in MARGINS]
    if all(isinstance(x, (int, float)) for x in m):
        marg = f"{_in(m[0])} margins" if len(set(m)) == 1 else \
            f"margins {_in(m[0])} top, {_in(m[1])} bottom, {_in(m[2])} left, {_in(m[3])} right"
    else:
        marg = "margins as the standards set them"
    out = f"{v.get('paper') or 'Letter'}, {marg}"
    p = ((values or {}).get("page_setups") or {}).get("portrait") or {}
    h, f = p.get("header"), p.get("footer")
    if isinstance(h, (int, float)) and isinstance(f, (int, float)):
        out += f"; header and footer at {_in(h)}" if h == f else f"; header at {_in(h)}, footer at {_in(f)}"
    return out


def numbering_words(values):
    """'Headings numbered to level 3 (%1.%2.%3); page numbers by part: Front matter, Response; captions: Table, Figure'."""
    values = values or {}
    hn = values.get("heading_numbering") or {}
    levels = [l for l in hn.get("levels") or [] if l.get("style")]
    out = f"Headings numbered to level {len(levels)} ({levels[-1].get('text', '')})" if hn.get("on") and levels else "Headings not numbered"
    parts = [p.get("name", "") for p in (values.get("pagination") or {}).get("parts") or [] if p.get("name") and p.get("numbers")]
    if parts:
        out += f"; page numbers by part: {', '.join(parts)}"
    labels = []
    for c in values.get("captions") or []:
        if c.get("label") and c["label"] not in labels:
            labels.append(c["label"])
    return out + (f"; captions: {', '.join(labels)}" if labels else "")


def words(kind, values):
    return layout_words(values) if kind == "layout" else numbering_words(values)


# ------------------------------------------------------------------ one answer per volume
def differs(kind, a, b):
    """What of this kind two standards hold differently, in words; [] when nothing. a is the template's, b the volume's."""
    va, vb = extract(a, kind), extract(b, kind)
    out = []
    if kind == "layout":
        x, y = va.get("variables") or {}, vb.get("variables") or {}
        if x.get("paper") != y.get("paper"):
            out.append(f"paper ({x.get('paper') or 'Letter'} in the template, {y.get('paper') or 'Letter'} in the volume's standards)")
        if [x.get(k) for k in MARGINS] != [y.get(k) for k in MARGINS]:
            out.append(f"margins ({layout_words({'variables': x}).split(', ', 1)[-1]} in the template, "
                       f"{layout_words({'variables': y}).split(', ', 1)[-1]} in the volume's standards)")
        if va.get("page_setups") != vb.get("page_setups"):
            out.append("page setups")
    else:
        for k, say in (("heading_numbering", "heading numbering"), ("pagination", "page numbers by part"), ("captions", "captions")):
            if va.get(k) != vb.get(k):
                out.append(say)
    return out


def volume_std(config_dir, ws, volume, data=None):
    """The standard a volume's checks read, before the rules shape it: the Global Standards, the volume's profile, the
    effort type, the effort's own values."""
    import prodrules as PRL
    data = data or PRL.load(config_dir)
    eff = (ws.get("prod_std", {}) if ws is not None else {}) or {}
    eid = eff.get("effort_type") if PRL.effort_type_of(data, eff.get("effort_type")) else None
    ids = [t["id"] for t in data["types"]]
    pid = None
    if eid:
        import effortprofiles as EP
        e = PRL.effort_type_of(data, eid)
        low = (volume or "").casefold()
        pid = next((p for p in e.get("profiles") or [] if low in [v.casefold() for v in EP.volumes(data, eid, p)]), None)
    pid = pid or PRL.profile_for(data, eid, volume, fallback=False) or (eff.get("type") if eff.get("type") in ids else None) \
        or PRL.profile_for(data, eid, volume)
    std = PRL.merge(PRL.resolved_type(data, pid, eid), eff.get("over") or {})
    return PRL.merge(std, (eff.get("over_vol") or {}).get(pid) or {})


def disagree(config_dir, ws, volume, t, data=None):
    """For a volume that picked template t: what the template's page layout and numbering picks hold differently from
    the volume's standards, in words; [] when they agree or the template picks neither."""
    import namedtemplates as NT
    import prodrules as PRL
    data = data or PRL.load(config_dir)
    sets = (t or {}).get("sets") or {}
    if not (sets.get("layout") or sets.get("numbering")):
        return []
    tstd = NT.std_of(config_dir, t, data)
    vstd = volume_std(config_dir, ws, volume, data)
    out = []
    for kind, _n, _p in KINDS:
        if get(config_dir, kind, sets.get(kind)):
            out += differs(kind, tstd, vstd)
    return out


def disagree_words(volume, name, what):
    return (f"{volume}: {name} and this volume's standards differ on {', '.join(what)}. The checks read the volume's "
            f"standards, so they will flag the template's pages.") if what else ""
