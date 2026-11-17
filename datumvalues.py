"""The values Stationkeeper carried in its code, kept as a file of the Production Datum (4.48.0; UX decision 67,
Nicholas 2026-11-16 15:34 and 18:11).

Decision 67: the app holds nothing the team wrote. The team's rules, effort folders, stages, phrase list, topics,
effort types and page numbering scheme were built into the code and used whenever no file had been saved over them, so
a Production Datum made from a PC's files did not contain them. From this release, when the Datum's keeper saves and the
save becomes the next version (globalfolder.update), every such value is written once into the set, exactly as the code
has it, in one file: datum_values.json. It travels as a part of the Datum like any other.

Nothing reads the file yet and no value has left the code: this release only makes sure the first Production Datum
holds them. The release after reads them from the file and takes them out of the code.

collect()            every built-in value, by name, as plain data
keep(config_dir)     write the file when it is not there (never over one that is); True when it was written
read(config_dir)     {name: value} from the file ({} when there is none)

No effort data, no customer or company name: these are practices. Rules only (No AI)."""
import json
import os

FILE = "datum_values.json"
FORMAT = 1                                     # formats.py "datum values"
PART = ("values", "Values once built in", [FILE], [])


def _plain(x):
    """Tuples and sets as lists, so what is written reads back the same."""
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set, frozenset)):
        return [_plain(v) for v in (sorted(x) if isinstance(x, (set, frozenset)) else x)]
    return x


def collect():
    """Every value the code carries that the team wrote or that is the team's practice: {name: value}."""
    import banned, effortrec, folderplan, process, prodrules, rulebook, topics
    std = prodrules._company_default()
    out = {
        "effort_folders": folderplan.DEFAULT_TREE,
        "stages": process.DEFAULT_STAGES,
        "roles": process.DEFAULT_ROLES,
        "record_stages": effortrec.DEFAULT_STAGES,
        "gate_goals": effortrec.DEFAULT_GOALS,
        "rules": rulebook.BUILTIN,
        "banned_phrases": banned.STARTER,
        "topics": topics.STARTER,
        "effort_types": prodrules.STARTER_EFFORT_TYPES,
        "effort_type_response": prodrules.STARTER_RESPONSE,
        "marking": (std.get("variables") or {}).get("marking", ""),
        "pagination": std.get("pagination"),
        "table_of_contents": std.get("toc"),
        "captions": std.get("captions"),
        "checks": std.get("checks"),
        "style_roles": std.get("style_roles"),
    }
    return _plain(out)


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def keep(config_dir):
    """Write the file when it is not there. Never writes over one: what a Datum holds is not replaced by the code."""
    p = _path(config_dir)
    if os.path.isfile(p):
        return False
    os.makedirs(config_dir, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, "values": collect()}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)
    return True


def read(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        return {}
    v = d.get("values")
    return v if isinstance(v, dict) else {}
