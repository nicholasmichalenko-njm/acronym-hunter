"""Template names and versions (3.23.0): every template Stationkeeper makes has a name you choose (where or how it is
used, such as "USSF page-limited RFP, Volume I") and a version that counts up each time that name is made again. The
file carries both as document properties (SK Template, SK Template Version), the list is kept on this PC
(<config>\\template_registry.json), and an effort records which template and version it used. Nothing leaves the PC."""
import datetime, getpass, json, os, re

FILE = "template_registry.json"


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def load(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
        return {k: v for k, v in d.items() if isinstance(v, dict)}
    except (OSError, ValueError):
        return {}


def save(config_dir, reg):
    os.makedirs(config_dir, exist_ok=True)
    p = _path(config_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def clean_name(name):
    return re.sub(r"[\\/:*?\"<>|]+", " ", " ".join(str(name or "").split())).strip()[:80]


def next_version(config_dir, name):
    vs = (load(config_dir).get(clean_name(name)) or {}).get("versions", [])
    return max((int(v.get("v", 0)) for v in vs), default=0) + 1


def names(config_dir):
    reg = load(config_dir)
    return sorted(reg, key=lambda k: (reg[k].get("versions") or [{}])[-1].get("at", ""), reverse=True)


def record(config_dir, name, version, path, standard="", validation=None, effort=""):
    """Keeps a made template in the list. Returns the entry."""
    reg = load(config_dir)
    name = clean_name(name)
    e = {"v": int(version), "file": os.path.basename(path), "folder": os.path.dirname(path), "standard": standard,
         "at": datetime.datetime.now().isoformat(timespec="minutes"), "by": getpass.getuser(), "effort": effort,
         "problems": len(validation.problems()) if validation is not None else None,
         "warnings": len(validation.warnings()) if validation is not None else None}
    reg.setdefault(name, {"versions": []})["versions"].append(e)
    save(config_dir, reg)
    return e


def latest(config_dir, name):
    vs = (load(config_dir).get(clean_name(name)) or {}).get("versions", [])
    return vs[-1] if vs else None


def note_on_effort(ws, name, entry):
    """The effort records the template it used (newest last)."""
    if ws is None:
        return
    used = [x for x in (ws.get("templates_used") or []) if isinstance(x, dict)]
    used.append({"name": clean_name(name), "v": entry["v"], "file": entry["file"], "at": entry["at"]})
    ws.set("templates_used", used[-20:])


def newer_than_effort(config_dir, ws):
    """[(name, the effort's version, the newest version)] for templates the effort used that have been made again since."""
    out = []
    for u in (ws.get("templates_used") or []) if ws is not None else []:
        lt = latest(config_dir, u.get("name"))
        if lt and int(lt["v"]) > int(u.get("v", 0)):
            out.append((u["name"], u["v"], lt["v"]))
    seen, uniq = set(), []
    for x in reversed(out):
        if x[0] not in seen:
            seen.add(x[0]); uniq.append(x)
    return uniq
