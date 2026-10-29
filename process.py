"""Stages, gates and roles (2.93.0): the team's way of running an effort, set once in Settings > Stages, gates and
roles, kept in the config folder (process.json) and carried by a team pack.

- Default stages for new efforts: name and gate, in order (start: Intake ... Final to pubs).
- Gates: the choices a stage's gate offers. Each has a name, what it does (none: no hold; soft: moving on with open
  goals is allowed and logged; hard: held until the goals are met, or overridden with a reason) and a description. The
  three built-in ones stay (they can be renamed and described); more can be added (Color team sign-off: hard).
- Roles: what the role drop-downs offer for the people on an effort (Proposal Manager, Volume Lead, Author...); anyone
  can still type another.
Standard library only.
"""
import json, os, re

FILE = "process.json"
BEHAVIORS = {"": "No hold", "soft": "Logged: moving on with open goals is allowed and logged",
             "hard": "Held: held until the goals are met, or overridden with a reason"}
BUILT_IN_GATES = [{"id": "", "name": "No gate", "behavior": "", "about": "The stage can be left at any time."},
                  {"id": "soft", "name": "Soft gate: warn and log", "behavior": "soft",
                   "about": "Leaving with open goals is allowed; the open goals and the reason are logged."},
                  {"id": "hard", "name": "Hard gate: hold until the goals are met", "behavior": "hard",
                   "about": "Leaving is held until every goal is met, unless the proposal manager overrides it with a reason."}]
DEFAULT_STAGES = [("Intake", ""), ("Author drafts", ""), ("Red team", ""), ("Red team recovery", ""), ("Gold team", ""),
                  ("Gold team recovery", ""), ("Final to pubs", "")]
DEFAULT_ROLES = ["Proposal Manager", "Capture Manager", "Volume Lead", "Author", "Contributor", "Reviewer", "Production",
                 "Pricing", "Contracts", "Graphics", "Subject Matter Expert", "Orals Coach", "Executive Sponsor"]


def _clean(s, n=80):
    return " ".join(str(s or "").split())[:n]


def load(config_dir):
    """{"stages": [(name, gate id)], "gates": [{id, name, behavior, about}], "roles": [name]} with the defaults filled in."""
    d = {}
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    gates = {g["id"]: dict(g) for g in BUILT_IN_GATES}
    order = [g["id"] for g in BUILT_IN_GATES]
    for g in d.get("gates", []) if isinstance(d.get("gates"), list) else []:
        if not isinstance(g, dict):
            continue
        gid = str(g.get("id", ""))
        beh = g.get("behavior", "") if g.get("behavior", "") in BEHAVIORS else ""
        if gid in gates:
            gates[gid].update({"name": _clean(g.get("name")) or gates[gid]["name"], "about": _clean(g.get("about"), 300) or gates[gid]["about"]})
        elif gid and _clean(g.get("name")):
            gates[gid] = {"id": gid, "name": _clean(g.get("name")), "behavior": beh, "about": _clean(g.get("about"), 300)}
            order.append(gid)
    stages = [(_clean(s[0]), s[1] if len(s) > 1 and s[1] in gates else "") for s in d.get("stages", [])
              if isinstance(s, (list, tuple)) and s and _clean(s[0])] or list(DEFAULT_STAGES)
    roles = [r for r in (_clean(x) for x in d.get("roles", [])) if r] or list(DEFAULT_ROLES)
    return {"stages": stages, "gates": [gates[k] for k in order], "roles": roles}


def save(config_dir, stages=None, gates=None, roles=None):
    cur = load(config_dir)
    if stages is not None:
        cur["stages"] = [(_clean(n), g) for n, g in stages if _clean(n)]
    if gates is not None:
        out, seen = [], set()
        for g in gates:
            gid = str(g["id"]) if "id" in g and g["id"] is not None else \
                "g_" + re.sub(r"[^a-z0-9]+", "_", _clean(g.get("name")).lower()).strip("_")[:30]
            if gid in seen or not _clean(g.get("name")):
                continue
            seen.add(gid)
            beh = g.get("behavior", "") if g.get("behavior", "") in BEHAVIORS else ""
            if gid in ("", "soft", "hard"):
                beh = gid                                      # the built-in ones keep what they do
            out.append({"id": gid, "name": _clean(g.get("name")), "behavior": beh, "about": _clean(g.get("about"), 300)})
        for b in BUILT_IN_GATES:                                # the built-in ones always stay
            if b["id"] not in seen:
                out.insert(0, dict(b))
        cur["gates"] = out
    ok = {g["id"] for g in cur["gates"]}
    cur["stages"] = [(n, g if g in ok else "") for n, g in cur["stages"]]
    if roles is not None:
        cur["roles"] = list(dict.fromkeys(r for r in (_clean(x) for x in roles) if r))
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, FILE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"stages": [list(x) for x in cur["stages"]], "gates": cur["gates"], "roles": cur["roles"]}, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    apply(config_dir)
    return load(config_dir)


def apply(config_dir):
    """Hand the gates and default stages to the effort record (once at start, and after a change)."""
    import effortrec as R
    P = load(config_dir)
    R.set_process(P)
    return P
