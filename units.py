"""Units of measurement (3.31.0): the team's list (a unit, what it means, its system, and whether it goes in every
volume's Units of Measurement table) and the units an effort captured in Review. Make templates fills the Units of
Measurement element from both: the team's "every table" units, then the effort's own, each unit once, in order.

Kept in <config>/units.json, carried by the Our data file and a team pack. Rules only; nothing leaves the PC."""
import json, os

FILE = "units.json"
SYSTEMS = ("", "SI", "US customary", "Imperial", "Other")


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def _clean(u):
    return {"unit": " ".join(str(u.get("unit") or "").split())[:40], "meaning": " ".join(str(u.get("meaning") or "").split())[:160],
            "system": str(u.get("system") or "") if str(u.get("system") or "") in SYSTEMS else "", "always": bool(u.get("always"))}


def load(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f)
        rows = d.get("units") if isinstance(d, dict) else d
        return [_clean(u) for u in (rows or []) if isinstance(u, dict) and str(u.get("unit") or "").strip()]
    except (OSError, ValueError):
        return []


def save(config_dir, rows):
    rows = [_clean(u) for u in rows if str(u.get("unit") or "").strip()]
    os.makedirs(config_dir, exist_ok=True)
    with open(_path(config_dir) + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"format": 1, "units": rows}, f, indent=1, ensure_ascii=False)
    os.replace(_path(config_dir) + ".tmp", _path(config_dir))
    return rows


def for_effort(config_dir, rec=None):
    """[(unit, meaning, system)] for a Units of Measurement table: the team's units set for every table, then the units
    captured in this effort (the words as the unit, the value as what it means, the note as its system), each unit once;
    a team unit's meaning fills in a captured unit with none."""
    team = load(config_dir) if config_dir else []
    by = {u["unit"].casefold(): u for u in team}
    out, seen = [], set()
    for u in team:
        if u["always"]:
            out.append((u["unit"], u["meaning"], u["system"])); seen.add(u["unit"].casefold())
    if rec is not None:
        import excerpts as EX
        for x in EX.excerpts(rec, "unit"):
            unit = " ".join(EX.text_of(x).split())[:40]
            if not unit or unit.casefold() in seen:
                continue
            t = by.get(unit.casefold()) or {}
            out.append((unit, x.get("value") or t.get("meaning", ""), x.get("note") or t.get("system", "")))
            seen.add(unit.casefold())
    return out
