"""Which copy is newer (2.79.0). Every effort carries a lineage (one ID for the effort and all its copies) and a revision
history: each burst of saved work adds a revision with its own ID, who made it and when. Two copies of an effort can
then be compared: the same, one newer (the other's latest revision is in its history), or both changed since a common
revision. Kept in the effort's folder as revision.json, so it travels in every effort package.

diff_matrices says what differs between two compliance matrices, sentence by sentence, for the compare before replacing.
Pure Python, no network.
"""
import datetime, getpass, json, os, uuid

FILE = "revision.json"
KEEP = 400


def _path(data_dir):
    return os.path.join(data_dir, FILE)


def read(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and d.get("lineage") and isinstance(d.get("history"), list):
            return d
    except (OSError, ValueError):
        pass
    return None


def _write(data_dir, d):
    os.makedirs(data_dir, exist_ok=True)
    tmp = _path(data_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, _path(data_dir))


def ensure(data_dir, who=None):
    """The effort's revision record, started (revision 1) when it has none."""
    d = read(data_dir)
    if d is None:
        d = {"lineage": uuid.uuid4().hex, "history": []}
        _add(d, who, "started")
        _write(data_dir, d)
    return d


def _add(d, who=None, what="saved"):
    rev = (d["history"][-1]["rev"] + 1) if d["history"] else 1
    d["history"].append({"rev": rev, "id": uuid.uuid4().hex[:12], "who": who or getpass.getuser(),
                         "at": datetime.datetime.now().isoformat(timespec="seconds"), "what": what})
    d["history"] = d["history"][-KEEP:]
    return rev


def bump(data_dir, who=None, what="saved"):
    d = ensure(data_dir, who)
    rev = _add(d, who, what)
    _write(data_dir, d)
    return rev


def current(d):
    return d["history"][-1] if d and d.get("history") else None


def compare(mine, theirs):
    """mine, theirs: revision records (or None). Returns {"relation", "ahead", "behind", "common", "theirs", "mine"}:
    relation 'same', 'newer' (theirs is newer than mine), 'older', 'diverged' (both changed since 'common'), 'unrelated'
    (different efforts that share a name) or 'unknown' (a copy from before 2.79.0)."""
    out = {"relation": "unknown", "ahead": 0, "behind": 0, "common": None, "theirs": current(theirs), "mine": current(mine)}
    if not mine or not theirs:
        return out
    if mine["lineage"] != theirs["lineage"]:
        out["relation"] = "unrelated"
        return out
    mids = [h["id"] for h in mine["history"]]
    tids = [h["id"] for h in theirs["history"]]
    if mids[-1] == tids[-1]:
        out["relation"] = "same"
        return out
    if mids[-1] in tids:
        out["relation"], out["ahead"] = "newer", len(tids) - 1 - tids.index(mids[-1])
        return out
    if tids[-1] in mids:
        out["relation"], out["behind"] = "older", len(mids) - 1 - mids.index(tids[-1])
        return out
    common = next((h for h in reversed(mine["history"]) if h["id"] in set(tids)), None)
    out["relation"], out["common"] = "diverged", common
    if common:
        out["ahead"] = len(tids) - 1 - tids.index(common["id"])
        out["behind"] = len(mids) - 1 - mids.index(common["id"])
    return out


def _when(h):
    try:
        return datetime.datetime.fromisoformat(h["at"]).strftime("%b %d %I:%M %p").replace(" 0", " ")
    except (KeyError, ValueError, TypeError):
        return "?"


def describe(c):
    """One plain sentence for the import card."""
    t, m = c.get("theirs"), c.get("mine")
    r = c["relation"]
    if r == "same":
        return "This package holds the same work as your copy."
    if r == "newer":
        return (f"This package is {c['ahead']} save(s) newer than your copy (last saved by {t['who']}, {_when(t)}). "
                "Using it brings your copy up to date.")
    if r == "older":
        return (f"This package is {c['behind']} save(s) older than your copy (yours was last saved by {m['who']}, {_when(m)}). "
                "Using it would undo that work; keep both, or keep yours.")
    if r == "diverged":
        since = f" since {_when(c['common'])}" if c.get("common") else ""
        return (f"You and {t['who']} both changed this effort{since}: the package has {c['ahead']} save(s) yours does not, "
                f"and yours has {c['behind']} it does not. Keep both and compare, so no one's work is lost.")
    if r == "unrelated":
        return "This package is a different effort with the same name. Keep both."
    return "This package or your copy is from before 2.79.0, so which is newer cannot be told; check the dates."


def diff_matrices(mine_path, theirs_path):
    """What differs between two compliance matrices: {"changed", "only_theirs", "only_mine", "examples"}."""
    import compliance as C
    out = {"changed": 0, "only_theirs": 0, "only_mine": 0, "examples": []}
    try:
        a = {it["id"]: it for it in C.Matrix(mine_path).load().items} if mine_path and os.path.isfile(mine_path) else {}
        b = {it["id"]: it for it in C.Matrix(theirs_path).load().items} if theirs_path and os.path.isfile(theirs_path) else {}
    except Exception:
        return out
    keys = ("decision", "map", "owner", "lm", "notes")
    for k, it in b.items():
        if k not in a:
            out["only_theirs"] += 1
        elif any((it.get(x) or "") != (a[k].get(x) or "") for x in keys):
            out["changed"] += 1
            if len(out["examples"]) < 5:
                f = next(x for x in keys if (it.get(x) or "") != (a[k].get(x) or ""))
                out["examples"].append(f"{k}: {f} '{a[k].get(f) or ''}' -> '{it.get(f) or ''}'")
    out["only_mine"] = sum(1 for k in a if k not in b)
    return out


def diff_text(d):
    if not (d["changed"] or d["only_theirs"] or d["only_mine"]):
        return "The compliance matrices match."
    parts = []
    if d["changed"]:
        parts.append(f"{d['changed']} sentence(s) decided, assigned or noted differently")
    if d["only_theirs"]:
        parts.append(f"{d['only_theirs']} sentence(s) only in the package")
    if d["only_mine"]:
        parts.append(f"{d['only_mine']} only in your copy")
    return "Compliance matrix: " + "; ".join(parts) + "."
