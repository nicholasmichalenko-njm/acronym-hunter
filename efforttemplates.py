"""An effort type names its templates (4.41.0; ST27 of 2026-11-14, step 5, and the Effort Start board's option A). An
effort type is the use case (RFP, Page-limited RFP, Program documents). For each of its profiles (Technical Volume,
Cost Volume...) it can name one of the templates you made (namedtemplates), so an effort of that type starts with the
whole template: its style sets, its Quick Part set, its starting pages. Kept on the effort type in
production_standards.json ("templates": {profile id: template id}), an added key; an effort type that names none
behaves as before.

    of(data, eid)                   {profile id: template id}
    put(config_dir, eid, pid, tid)  name a template for a profile ('' takes it off)
    brings(config_dir, eid)         what an effort of this type starts with, one row per profile
    for_volume(config_dir, eid, v)  the template the effort type names for a volume of this name, or None
    offer(config_dir, eid, volumes, picked)   the volumes with no template picked that the effort type has one for
    apply(M, ws, config_dir, eid, volumes, effort_path)   pick them; returns [(volume, template name)]

Rules only (No AI); nothing leaves the PC."""
import effortprofiles as EP
import namedtemplates as NT
import prodrules as PRL


def of(data, eid):
    e = PRL.effort_type_of(data, eid) if eid else None
    t = (e or {}).get("templates")
    return {k: v for k, v in t.items() if v} if isinstance(t, dict) else {}


def put(config_dir, eid, pid, tid):
    """Names the template for this profile in this effort type ('' or None takes it off). False when there is no such
    effort type, profile or template."""
    data = PRL.load(config_dir)
    e = PRL.effort_type_of(data, eid)
    if e is None or pid not in (e.get("profiles") or []) or (tid and NT.get(config_dir, tid) is None):
        return False
    t = dict(e.get("templates") or {})
    if tid:
        t[pid] = tid
    else:
        t.pop(pid, None)
    e["templates"] = t
    PRL.save(config_dir, data)
    return True


def brings(config_dir, eid, data=None):
    """[{"pid", "profile", "volumes", "tid", "template", "made", "holds"}] for the effort type's profiles; [] for no
    effort type. template is '' where none is named (or the named one is gone)."""
    data = data or PRL.load(config_dir)
    e = PRL.effort_type_of(data, eid) if eid else None
    if e is None:
        return []
    named = of(data, eid)
    out = []
    for pid in e.get("profiles") or []:
        p = PRL.type_of(data, pid)
        if p["id"] != pid:
            continue
        t = NT.get(config_dir, named.get(pid)) if named.get(pid) else None
        out.append({"pid": pid, "profile": p["name"], "volumes": EP.volumes(data, eid, pid), "tid": t["id"] if t else "",
                    "template": t["name"] if t else "", "made": bool(t) and NT.state(config_dir, t, data)[0] != NT.NEW,
                    "holds": NT.words(config_dir, t) if t else ""})
    return out


def words(rows):
    """One sentence for the start form."""
    got = [r for r in rows if r["template"]]
    if not rows:
        return ""
    if not got:
        return "This effort type names no templates yet. Effort types... > Templates... sets them."
    return "It starts with: " + "; ".join(f"{r['profile']}: {r['template']}" + ("" if r["made"] else " (not made yet)") for r in got) + "."


def for_volume(config_dir, eid, volume, data=None):
    """The template this effort type names for a volume of this name: by the profile whose volumes list holds the
    name, else the profile the name matches (prodrules.profile_for). None when it names none."""
    data = data or PRL.load(config_dir)
    e = PRL.effort_type_of(data, eid) if eid else None
    if e is None:
        return None
    named = of(data, eid)
    low = " ".join(str(volume or "").split()).casefold()
    pid = next((p for p in e.get("profiles") or [] if low in [v.casefold() for v in EP.volumes(data, eid, p)]), None) \
        or PRL.profile_for(data, eid, volume)
    return NT.get(config_dir, named.get(pid)) if named.get(pid) else None


def offer(config_dir, eid, volumes, picked, data=None):
    """[(volume, template)] for the volumes with no template picked that the effort type names a made template for."""
    data = data or PRL.load(config_dir)
    out = []
    for v in volumes:
        if v in (picked or {}):
            continue
        t = for_volume(config_dir, eid, v, data)
        if t is not None and NT.state(config_dir, t, data)[0] != NT.NEW:
            out.append((v, t))
    return out


def apply(M, ws, config_dir, eid, volumes, effort_path=""):
    """Picks the effort type's template for each volume that has none. Returns [(volume, template name)]."""
    done = []
    for v, t in offer(config_dir, eid, volumes, NT.picks(ws)):
        if NT.pick(M, ws, config_dir, v, t["id"], effort_path) is not None:
            done.append((v, t["name"]))
    return done
