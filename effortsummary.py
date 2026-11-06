"""Every effort at a glance (2.91.0), for Home: read from each effort's saved files without opening it (no lock is
taken, nothing is written), so Home stays quick with many efforts.

For each effort: its name, client and solicitation (the registry), picture, sensitivity and proposal manager (its
record's identity), stage, due date and days left, open tasks and questions (and how many are late), deliverables and
how many have no owner, when it was last worked on, and whether someone has it open now (its lock). Unfiled work is
left to its own card. Standard library plus the effort record.
"""
import datetime, os

ORDER = ("due_soon", "open", "later", "no_date")


def _read(path):
    import workspace as W
    return W.read_json(path, None)


def summary(name, info, now=None):
    import branding as BR
    import effortrec as R
    import workspace as W
    now = now or datetime.datetime.now()
    path = info.get("path", "")
    data = W.data_dir_for(path) if path else ""
    out = {"name": name, "path": path, "data": data, "missing": not (path and os.path.isfile(path)),
           "client": info.get("client", ""), "solicitation": info.get("solicitation", ""), "picture": "",
           "sensitivity": "", "pm": "", "stage": "", "stage_i": 0, "stages": 0, "due": "", "zone": "", "days": None,
           "tasks": 0, "late": 0, "questions": 0, "deliverables": 0, "no_owner": 0, "last": "", "open_by": "",
           "gate": "", "gate_mode": "", "goals_open": 0, "goals": 0, "factors": 0, "request": ""}
    if out["missing"]:
        return out
    rec = _read(os.path.join(data, "record.json")) or {}
    ident = rec.get("identity") or {}
    out["sensitivity"] = ident.get("sensitivity", "")
    out["pm"] = ident.get("pm", "") or next((m.get("name", "") for m in rec.get("team", [])
                                            if "proposal manager" in (m.get("role") or "").casefold()), "")
    if BR.has_picture(data):
        out["picture"] = BR.picture_path(data)
    stages = rec.get("stages") or []
    cur = next((i for i, s in enumerate(stages) if s.get("id") == rec.get("stage")), 0)
    out["stages"], out["stage_i"] = len(stages), cur
    out["stage"] = stages[cur]["name"] if stages else ""
    if stages:                                                   # 3.12.0: the stage's gate, where every effort shows
        gid = stages[cur].get("gate", "")
        if gid in R.GATES and gid:
            out["gate_mode"] = R.GATE_BEHAVIOR.get(gid, "")
            out["gate"] = ("Hard gate" if out["gate_mode"] == "hard" else "Soft gate") if gid in ("soft", "hard") else R.GATES[gid].split(":")[0]
        goals = stages[cur].get("goals") or []
        out["goals"], out["goals_open"] = len(goals), sum(1 for g in goals if not g.get("done"))
    out["due"], out["zone"] = rec.get("due", ""), rec.get("zone", "")
    if out["due"]:
        import tzones as TZ
        zk = rec.get("zone_key") or TZ.guess(out["zone"])
        c = BR.countdown(out["due"], None, zk) if zk and len(out["due"]) > 10 else BR.countdown(out["due"], now)
        out["days"] = (-c[1] if c and c[0] == "passed" else c[0]) if c else None
    today = now.date()
    for t in rec.get("tasks", []):
        if t.get("status") != "Done":
            out["tasks"] += 1
            d = R.parse_date(t.get("due", "")) if t.get("due") else None
            if d and d < today:
                out["late"] += 1
    out["questions"] = sum(1 for n in rec.get("notes", []) if n.get("question") and not n.get("resolved"))
    dl = rec.get("deliverables", [])
    out["deliverables"] = len(dl)
    out["no_owner"] = sum(1 for d in dl if not d.get("owner"))
    out["factors"] = sum(1 for f in rec.get("eval_factors", []) if isinstance(f, dict) and not f.get("parent"))   # 3.63.0
    out["request"] = ((rec.get("path") or {}).get("type") or "") if isinstance(rec.get("path"), dict) else ""
    times = [e.get("at", "") for e in rec.get("timeline", []) if e.get("at")]
    out["last"] = max(times) if times else ""
    lock = _read(os.path.join(data, "lock.json")) or {}
    if lock.get("user"):
        out["open_by"] = f"{lock.get('user')} on {lock.get('computer', 'another PC')}"
    return out


def all_efforts(registry, skip=(), now=None, archived=False):
    """[summary] for every effort but the ones in skip, the soonest due first, then the ones with no due date.
    3.70.0: archived efforts only when archived is True (then only them)."""
    rows = [summary(n, registry.get(n) or {}, now) for n in registry.names() if n not in skip and not (registry.get(n) or {}).get("unfiled")
            and bool((registry.get(n) or {}).get("archived")) == bool(archived)]
    return sorted(rows, key=lambda r: (r["missing"], r["days"] is None, r["days"] if r["days"] is not None else 0, r["name"].casefold()))


def days_text(days):
    if days is None:
        return "No due date"
    if days < 0:
        return f"Due {-days} day(s) ago"
    if days == 0:
        return "Due today"
    return f"{days} day{'s' if days != 1 else ''} left"


def days_tone(days):
    if days is None:
        return "head"
    if days < 3:
        return "crit"
    return "warn" if days < 10 else "accent"
