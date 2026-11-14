"""A template as its own named thing (4.28.2; Nicholas 2026-11-12, answer 23). A template has a name you choose and a
pick of what goes in: style sets in order, the Setup style set, a Quick Part set and the pages a document starts with
(templatesets holds those rules). The page and the text's layout come from the Global Standards. It belongs
to no effort type and no profile. Made, it is a .dotx in the output folder's Templates\\Named folder with its name and
version in it (templatereg). An effort picks one for each volume: the pick is kept as that volume's template file
(templatesetup), so the setup is written on it exactly as on a template the team brings.

<config>\\templates_named.json: {id: {name, sets, made: {fp, path, version, at}}}. Rules only; nothing leaves the PC."""
import copy, datetime, hashlib, json, os, uuid

FILE = "templates_named.json"
PICKS = "volume_templates"                         # in the effort's settings: {volume: {id, name, v}}
NEW, READY, REVIEW = "Not made yet", "Ready", "Needs review"


def _path(config_dir):
    return os.path.join(__import__("effortset").base(config_dir), FILE)


def load(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
        return {k: v for k, v in d.items() if isinstance(v, dict) and v.get("name")}
    except (OSError, ValueError):
        return {}


def save(config_dir, d):
    os.makedirs(config_dir, exist_ok=True)
    p = _path(config_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def every(config_dir):
    """[{id, name, sets, made}] by name."""
    return sorted((dict(v, id=k) for k, v in load(config_dir).items()), key=lambda t: t["name"].casefold())


def get(config_dir, tid):
    t = load(config_dir).get(tid)
    return dict(t, id=tid) if t else None


def _name(name):
    import templatereg as TR
    return " ".join(TR.clean_name(name).split())


def _free(d, name, but=None):
    return bool(name) and not any(v["name"].casefold() == name.casefold() for k, v in d.items() if k != but)


def new(config_dir, name):
    """A new template with nothing in it yet. Its name must be free. Returns it, or None."""
    import templatereg as TR
    d = load(config_dir)
    name = _name(name)
    if not _free(d, name):
        return None
    tid = uuid.uuid4().hex[:10]
    d[tid] = {"name": name, "sets": {}}
    save(config_dir, d)
    return dict(d[tid], id=tid)


def rename(config_dir, tid, name):
    import templatereg as TR
    d = load(config_dir)
    name = _name(name)
    if tid not in d or not _free(d, name, tid):
        return False
    d[tid]["name"] = name
    save(config_dir, d)
    return True


def remove(config_dir, tid):
    """Takes the template off the list. A file already made stays where it is."""
    d = load(config_dir)
    if d.pop(tid, None) is None:
        return False
    save(config_dir, d)
    return True


def set_recipe(config_dir, tid, sets):
    import templatesets as TS
    d = load(config_dir)
    if tid not in d:
        return None
    d[tid]["sets"] = TS.recipe({TS.KEY: sets})
    save(config_dir, d)
    return d[tid]["sets"]


def std_of(config_dir, t, data=None):
    """The standard the template is made from: the Global Standards with this template's pick."""
    import prodrules as PRL
    import templatesets as TS
    data = data or PRL.load(config_dir)
    std = copy.deepcopy(data["company"])
    std[TS.KEY] = TS.recipe({TS.KEY: t.get("sets") or {}})
    std["_parts_dir"] = os.path.join(__import__("effortset").base(config_dir), "production_parts")
    return std


def fingerprint(config_dir, t, data=None, lib=None):
    """What the template is made from, as one short value: the standard, its pick and what each picked set holds now."""
    import stylelib as SL
    import templatelib as TL
    import templatesets as TS
    std = std_of(config_dir, t, data)
    lib = lib or TL.Library(config_dir)
    rec = TS.recipe(std)
    held = {sid: list((SL.get_set(lib, sid) or {}).get("items") or []) for sid in rec["style_sets"] + [rec["setup_set"], rec["part_set"]] if sid}
    keep = {k: v for k, v in std.items() if not str(k).startswith("_") and k != "name"}
    return hashlib.sha256(json.dumps([keep, held], sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def words(config_dir, t, lib=None):
    """What goes in, in a line: "2 style sets, a Quick Part set, starts with 3 pages"."""
    import stylelib as SL
    import templatelib as TL
    import templatesets as TS
    lib = lib or TL.Library(config_dir)
    r = TS.recipe({TS.KEY: t.get("sets") or {}})
    bits = []
    names = [k["name"] for k in (SL.get_set(lib, s) for s in r["style_sets"]) if k]
    if names:
        bits.append("Styles: " + ", ".join(names))
    k = SL.get_set(lib, r["part_set"]) if r["part_set"] else None
    if k:
        bits.append(f"Quick Parts: {k['name']}")
    if r["starts"]:
        bits.append(f"starts with {len(r['starts'])} page{'' if len(r['starts']) == 1 else 's'}")
    return "; ".join(bits) or "Nothing picked yet: the Global Standards alone"


def state(config_dir, t, data=None, lib=None):
    """(Not made yet | Ready | Needs review, why)."""
    m = t.get("made") or {}
    if not m or not os.path.isfile(m.get("path") or ""):
        return NEW, "Make it to use it in an effort" if not m else "Its file is gone from the folder: make it again"
    if m.get("fp") != fingerprint(config_dir, t, data, lib):
        return REVIEW, "What goes in changed since it was made"
    return READY, f"Made {str(m.get('at', ''))[:16].replace('T', ' ')}, version {m.get('version', 1)}"


def folder(out_root):
    return os.path.join(out_root, "Named")


def make(config_dir, out_root, tid, word=None, when=None):
    """Makes the template's .dotx in out_root\\Named. Returns the TemplateJob (its .copy is the file)."""
    import prodparts as PP
    import prodrules as PRL
    import prodtemplate as PT
    import templatereg as TR
    d = load(config_dir)
    t = d[tid]
    data = PRL.load(config_dir)
    fp = fingerprint(config_dir, t, data)
    std = PRL.engine_ready(std_of(config_dir, t, data))
    name = _name(t["name"]) or "Template"
    ver = max(TR.next_version(config_dir, name), int((t.get("made") or {}).get("version") or 0) + 1)   # the count is the template's: a rename keeps it
    std["_template_name"], std["_template_version"], std["_standard"] = name, ver, "Global Standards"
    std["name"] = f"{name} v{ver}"
    out = folder(out_root)
    os.makedirs(out, exist_ok=True)
    job = PT.make(std, out, "", word=word, when=when, parts_dir=PP.parts_dir(config_dir))
    try:
        TR.record(config_dir, name, ver, job.copy, standard="Global Standards")
    except Exception:  # noqa: BLE001  the registry is a convenience; the template is made
        pass
    d = load(config_dir)
    if tid in d:
        d[tid]["made"] = {"fp": fp, "path": job.copy, "version": ver, "at": (when or datetime.datetime.now()).isoformat(timespec="minutes")}
        save(config_dir, d)
    return job


# ------------------------------------------------------------------ an effort picks one for each volume
def picks(ws):
    try:
        return {k: dict(v) for k, v in (ws.get(PICKS) or {}).items() if isinstance(v, dict)} if ws is not None else {}
    except (OSError, ValueError, AttributeError):
        return {}


def pick(M, ws, config_dir, volume, tid, effort_path=""):
    """The volume's setup is written on this template. It must be made first. Returns the pick, or None."""
    import templatefile as TF
    import templatesetup as TS
    t = get(config_dir, tid)
    m = (t or {}).get("made") or {}
    if not t or not os.path.isfile(m.get("path") or ""):
        return None
    TS.set_choice(M, volume, m["path"], TF.default_picks(None), effort_path)
    p = picks(ws)
    p[volume] = {"id": tid, "name": t["name"], "v": int(m.get("version") or 1)}
    if ws is not None:
        ws.set(PICKS, p)
    return p[volume]


def unpick(M, ws, volume):
    """The volume goes back to the effort's own formatting."""
    import templatesetup as TS
    TS.clear_choice(M, volume)
    p = picks(ws)
    had = p.pop(volume, None)
    if ws is not None:
        ws.set(PICKS, p)
    return had is not None


def newer(config_dir, ws):
    """[(volume, name, the effort's version, the newest)] for picked templates made again since."""
    out = []
    for vol, p in picks(ws).items():
        t = get(config_dir, p.get("id"))
        v = int(((t or {}).get("made") or {}).get("version") or 0)
        if t and v > int(p.get("v") or 0):
            out.append((vol, t["name"], int(p.get("v") or 0), v))
    return out
