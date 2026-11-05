"""Templates (3.52.0, plan decision 1): the list of Word templates follows from the Effort Profiles. One row per effort
type, profile and volume, each Ready, Needs review or Blocked, with why:
- Blocked: the profile breaks the RFP's limits (a size under its minimum) or its values do not make a template.
- Needs review: a library item the profile is pinned to has a newer version, or the profile changed since its template
  was last made.
- Ready: made, and nothing changed since. Not made yet: nothing stops it.
Make keeps the template in the output folder's Templates\\<effort type> folder, records it (templatereg: name and
version) and remembers what it was made from (<config>\\templates_made.json: {row key: {fp, path, at, version}}).
rows / fingerprint / make / made. Rules only; nothing leaves the PC."""
import datetime, hashlib, json, os

import effortprofiles as EP
import prodrules as PRL
import templateprofile as TP

FILE = "templates_made.json"
READY, REVIEW, BLOCKED, NEW = "Ready", "Needs review", "Blocked", "Not made yet"


def key(eid, pid, volume):
    return f"{eid}|{pid}|{volume}"


def made(config_dir):
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_made(config_dir, d):
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, FILE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(p + ".tmp", p)


def fingerprint(std):
    """What the template is made from, as one short value (names and private keys left out)."""
    keep = {k: v for k, v in std.items() if not str(k).startswith("_") and k not in ("name", "effort_type", "effort_over")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def template_name(ename, volume):
    return f"{ename} - {volume}"


def rows(config_dir, data=None, lib=None):
    """[{eid, ename, pid, pname, volume, name, state, why, path}] every template the profiles make."""
    import templatelib as TL
    data = data or PRL.load(config_dir)
    lib = lib or TL.Library(config_dir)
    done = made(config_dir)
    out = []
    for p in EP.profiles(data):
        std = EP.resolved(data, p["eid"], p["pid"])
        probs = list(EP.broken_limits(std))
        try:
            probs += PRL.validate(PRL.engine_ready(json.loads(json.dumps(std))))
        except Exception as e:  # noqa: BLE001
            probs.append(f"the values do not make a template ({type(e).__name__})")
        newer = [w for s, _part, w, _k in TP.slots(std) if TP.state(std, lib, s)["newer"] is not None]
        fp = fingerprint(std)
        for vol in p["volumes"]:
            rec = done.get(key(p["eid"], p["pid"], vol)) or {}
            if probs:
                st, why = BLOCKED, "; ".join(probs[:3])
            elif newer:
                st, why = REVIEW, "A newer library version waits: " + ", ".join(newer[:3])
            elif rec and rec.get("fp") != fp:
                st, why = REVIEW, "The profile changed since this template was made"
            elif rec:
                st, why = READY, f"Made {str(rec.get('at', ''))[:16]}, version {rec.get('version', 1)}"
            else:
                st, why = NEW, "Nothing stops it"
            out.append(dict(p, volume=vol, name=template_name(p["ename"], vol), state=st, why=why, path=rec.get("path", "")))
    return out


def make(config_dir, folder, row, data=None, word=None, start_from="", when=None):
    """Makes one row's template in folder\\<effort type>. Returns the TemplateJob (its .copy is the file)."""
    import prodtemplate as PT
    import prodparts as PP
    import templatereg as TR
    data = data or PRL.load(config_dir)
    std = PRL.engine_ready(EP.resolved(data, row["eid"], row["pid"]))
    fp = fingerprint(EP.resolved(data, row["eid"], row["pid"]))
    name = TR.clean_name(row["name"]) or "Template"
    ver = TR.next_version(config_dir, name)
    std["_template_name"], std["_template_version"], std["_standard"] = name, ver, f"{row['ename']} / {row['pname']}"
    std["name"] = f"{name} v{ver}"
    out = os.path.join(folder, row["ename"])
    os.makedirs(out, exist_ok=True)
    job = PT.make(std, out, start_from or "", word=word, when=when, parts_dir=PP.parts_dir(config_dir))
    try:
        TR.record(config_dir, name, ver, job.copy, standard=f"{row['ename']} / {row['pname']}")
    except Exception:  # noqa: BLE001  the registry is a convenience; the template is made
        pass
    d = made(config_dir)
    d[key(row["eid"], row["pid"], row["volume"])] = {"fp": fp, "path": job.copy, "version": ver,
                                                      "at": (when or datetime.datetime.now()).isoformat(timespec="minutes")}
    _save_made(config_dir, d)
    return job
