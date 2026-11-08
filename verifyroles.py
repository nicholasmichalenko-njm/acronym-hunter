"""Verify's roles (3.84.0, claude/stationkeeper-verify-hands-on-2026-11-08.md): what each block on a customer page is.

Every block gets one role. A role "acts as" one of seven things, and that decides what happens to the block next:
    heading   builds the outline (with its level, 1 to 6)
    text      is split into sentences for Review
    bullet    is split into sentences, as a list item
    object    a figure or a table: kept as it is (its cells or its picture)
    caption   names a figure or a table and is linked to it; a linked pair is one item from here on
    running   a header or footer: never in Review
    skip      not needed: never in Review
The menu can be changed per effort (show or hide a role, rename it, change its key, reorder it, add a role of your own
with an "acts as"); Save as team default puts it in the team's config folder so new efforts start with it.

defaults() / menu(saved, team) / clean(menu) / by_id(menu) / acts(menu, role id) / level(menu, role id) / key_map(menu)
add_role(menu, name, acts, key="", level=1) / load_team(config_dir) / save_team(config_dir, menu). Rules only."""
import json, os, re

ACTS = ("heading", "text", "bullet", "object", "caption", "running", "skip")
ACTS_NAME = {"heading": "Heading", "text": "Text", "bullet": "List item", "object": "Figure or table",
             "caption": "Caption", "running": "Header or footer", "skip": "Not needed"}
TEAM_FILE = "verify_menu.json"
FORMAT = 1


def defaults():
    out = [{"id": f"h{n}", "name": f"H{n}", "acts": "heading", "level": n, "key": str(n), "on": True} for n in range(1, 7)]
    out += [{"id": "text", "name": "Text", "acts": "text", "key": "T", "on": True},
            {"id": "bullet", "name": "Bullet", "acts": "bullet", "key": "B", "on": True},
            {"id": "figure", "name": "Figure", "acts": "object", "object": "figure", "key": "F", "on": True},
            {"id": "figcap", "name": "Figure caption", "acts": "caption", "object": "figure", "key": "Shift+F", "on": True},
            {"id": "table", "name": "Table", "acts": "object", "object": "table", "key": "M", "on": True},
            {"id": "tabcap", "name": "Table caption", "acts": "caption", "object": "table", "key": "Shift+M", "on": True},
            {"id": "footnote", "name": "Footnote", "acts": "text", "key": "N", "on": True},
            {"id": "running", "name": "Running", "acts": "running", "key": "R", "on": True},
            {"id": "skip", "name": "Not needed", "acts": "skip", "key": "X", "on": True}]
    return out


BUILTIN = {r["id"] for r in defaults()}


def clean(menu):
    """A menu as saved, made safe: every built-in role present (hidden ones stay hidden), known acts, unique keys."""
    got, seen_ids, seen_keys = [], set(), set()
    base = {r["id"]: r for r in defaults()}
    for r in menu or []:
        if not isinstance(r, dict) or not r.get("id") or r["id"] in seen_ids:
            continue
        acts = r.get("acts") if r.get("acts") in ACTS else base.get(r["id"], {}).get("acts", "text")
        x = {"id": str(r["id"])[:40], "name": " ".join(str(r.get("name") or base.get(r["id"], {}).get("name", r["id"])).split())[:40],
             "acts": acts, "key": str(r.get("key") or "")[:12], "on": bool(r.get("on", True))}
        if acts == "heading":
            try:
                x["level"] = max(1, min(6, int(r.get("level") or base.get(r["id"], {}).get("level") or 1)))
            except (TypeError, ValueError):
                x["level"] = 1
        if acts in ("object", "caption"):
            x["object"] = r.get("object") if r.get("object") in ("figure", "table") else base.get(r["id"], {}).get("object", "figure")
        if x["key"] and x["key"].casefold() in seen_keys:
            x["key"] = ""
        if x["key"]:
            seen_keys.add(x["key"].casefold())
        seen_ids.add(x["id"])
        got.append(x)
    for r in defaults():
        if r["id"] not in seen_ids:
            r = dict(r)
            if r["key"].casefold() in seen_keys:
                r["key"] = ""
            got.append(r)
    return got


def menu(saved=None, team=None):
    """The effort's menu, else the team default, else the built-in one."""
    return clean(saved or team or defaults())


def by_id(m):
    return {r["id"]: r for r in m}


def acts(m, rid):
    return by_id(m).get(rid, {}).get("acts", "text")


def level(m, rid):
    return by_id(m).get(rid, {}).get("level", 0)


def name(m, rid):
    return by_id(m).get(rid, {}).get("name", rid or "")


def key_map(m):
    """{key text: role id} for the roles shown."""
    return {r["key"]: r["id"] for r in m if r["on"] and r["key"]}


def heading_role(m, n):
    """The shown role that is a heading at level n (the nearest level when that one is hidden)."""
    hs = [r for r in m if r["acts"] == "heading" and r["on"]]
    if not hs:
        return "text"
    return min(hs, key=lambda r: (abs(r["level"] - n), r["level"]))["id"]


def add_role(m, name_, acts_, key="", level_=1, obj="figure"):
    """A role of your own. Returns (menu, id); a name already in the menu returns that role."""
    name_ = " ".join((name_ or "").split())[:40]
    if not name_ or acts_ not in ACTS:
        return m, None
    for r in m:
        if r["name"].casefold() == name_.casefold():
            return m, r["id"]
    base = re.sub(r"[^a-z0-9]+", "_", name_.lower()).strip("_") or "role"
    rid, n = "u_" + base, 2
    while rid in by_id(m):
        rid, n = f"u_{base}{n}", n + 1
    r = {"id": rid, "name": name_, "acts": acts_, "key": key, "on": True, "level": level_, "object": obj}
    return clean(m + [r]), rid


def load_team(config_dir):
    try:
        with open(os.path.join(config_dir, TEAM_FILE), encoding="utf-8") as f:
            d = json.load(f)
        return clean(d.get("menu")) if isinstance(d, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def save_team(config_dir, m):
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, TEAM_FILE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, "menu": clean(m)}, f, indent=1)
    os.replace(p + ".tmp", p)
    return p
