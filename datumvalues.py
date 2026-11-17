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
keep(config_dir)     write the file when it is not there; add a value the file lacks (4.48.1); never change one it
                     holds; True when anything was written
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
    import banned, coverlayout, effortrec, effortsched, fieldrecipes, folderplan, placelearn, postsub, process
    import prodrules, responseelements, rulebook, topics
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
        # 4.48.1: the smaller lists that are the team's practice (sorted 2026-11-16)
        "stage_days": effortsched.BUILT_IN,
        "field_recipes": fieldrecipes.STARTERS,
        "after_submission": postsub.BUILT_IN,
        "cover_properties": coverlayout.BUILTIN,
        "front_matter_kit": responseelements.DEFAULT_KIT,
        "section_synonyms": placelearn.STARTER_SYNONYMS,
    }
    return _plain(out)


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def _write(config_dir, values):
    p = _path(config_dir)
    os.makedirs(config_dir, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, "values": values}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def keep(config_dir):
    """Write the file when it is not there; when it is, add only the values it lacks (4.48.1: lists sorted after the
    first file was made). A value the file holds is never changed: what a Datum holds is not replaced by the code.
    A file that cannot be read is left alone."""
    p = _path(config_dir)
    c = collect()
    if not os.path.isfile(p):
        _write(config_dir, c)
        return True
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return False
    have = d.get("values") if isinstance(d, dict) else None
    if not isinstance(have, dict):
        return False
    new = {k: v for k, v in c.items() if k not in have}
    if not new:
        return False
    _write(config_dir, dict(have, **new))
    return True


def read(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        return {}
    v = d.get("values")
    return v if isinstance(v, dict) else {}
