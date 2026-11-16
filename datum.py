"""The Production Datum (4.47.0; UX decisions 34, 36, 39, 40 and 59, Nicholas 2026-11-16): the name of the foundational
set a PC installs, and what the app says about it. The set itself is what the Global Standards code already keeps
(globalstd: a version number, its parts, the acronym database and the dictionaries among them; globalfile and
globalfolder: a file or a folder it comes from). Nothing is stored here and no saved file changes.

state(config_dir, folder)   {"kind": NONE | INSTALLED | READY, "number", "taken", "ready"}
mark(st)                    the top bar's words: "No Production Datum installed", "Production Datum 14",
                            "Production Datum 14, 15 is ready"
line(st)                    where something is produced: "Production Datum: none installed" / "Production Datum 14"
record_start(ws, config_dir)   a new effort remembers which one it was started on (4.47.1; decision 36, point 5)
started(ws)                 "Started on Production Datum 12" / "Started with no Production Datum installed" / ""
holds(config_dir, db_file)  what the installed one holds, one (name, count, word) per line
will_change(config_dir, folder)   before a newer one is installed: the parts that differ, in counts

"Datum" is never used for anything of an effort (an effort handed off is an effort package). Rules only (No AI)."""
import csv
import json
import os

import globalstd as GS

NAME = "Production Datum"
NONE, INSTALLED, READY = "none", "installed", "ready"
NOTHING = "Stationkeeper has no standards, acronym database or dictionaries yet."      # the panel's one sentence (59)
NOT_TOUCHED = "Your work is not touched."


def state(config_dir, folder=""):
    """Which of the three states this PC is in. folder: the folder it is connected to ("" when it is not)."""
    st = GS.state(config_dir)
    n, newer = st["version"], 0
    if folder and os.path.isdir(folder):
        try:
            import globalfolder as GF
            man = GF.ready(config_dir, folder)
            newer = int(man["version"]) if man else 0
        except Exception:  # noqa: BLE001  a folder that cannot be read is no newer one
            newer = 0
    kind = READY if newer and newer > n else INSTALLED if n else NONE
    return {"kind": kind, "number": n, "taken": st["taken"], "ready": newer if kind == READY else 0}


def mark(st):
    if st["kind"] == NONE:
        return f"No {NAME} installed"
    if st["kind"] == READY and st["number"]:
        return f"{NAME} {st['number']}, {st['ready']} is ready"
    if st["kind"] == READY:
        return f"No {NAME} installed, {st['ready']} is ready"
    return f"{NAME} {st['number']}"


def line(st):
    """The line where something is produced (a setup, a template, the checks before submission)."""
    return f"{NAME}: none installed" if not st["number"] else f"{NAME} {st['number']}"


def _db_rows(db_file):
    try:
        with open(db_file, encoding="utf-8-sig", newline="") as f:
            return max(0, sum(1 for r in csv.reader(f) if any(c.strip() for c in r)) - 1)
    except OSError:
        return 0


def _dictionaries(config_dir):
    try:
        with open(os.path.join(config_dir, "custom_dictionaries.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return 0
    for key in ("dictionaries", "items", "lists"):
        if isinstance(d, dict) and isinstance(d.get(key), (list, dict)):
            return len(d[key])
    return len(d) if isinstance(d, (list, dict)) else 0


def _n(count, one, many):
    return f"{count} {one if count == 1 else many}"


def holds(config_dir, db_file=""):
    """What the installed one holds: [(name, count, the line as said)]."""
    parts = len(GS.parts(config_dir))
    rows = _db_rows(db_file) if db_file else 0
    dics = _dictionaries(config_dir)
    return [("Global Standards", parts, f"Global Standards: {_n(parts, 'part', 'parts')}"),
            ("Acronym database", rows, f"Acronym database: {_n(rows, 'term', 'terms')}"),
            ("Custom dictionaries", dics, f"Custom dictionaries: {dics}")]


def will_change(config_dir, folder):
    """Before a newer one is installed: {"number", "parts": [names of the parts that differ], "words"}; None when
    nothing newer is there. Counts only: the parts are named, their values are not read out."""
    st = state(config_dir, folder)
    if st["kind"] != READY:
        return None
    names = []
    try:
        import globalfolder as GF
        man = GF.read(folder, st["ready"]) or {}
        theirs = man.get("files") or {}
        mine = {m: (k, GS._sha_file(p)) for m, (k, p) in GF._members(config_dir).items()}
        part_of = {m: k for k, d in (man.get("parts") or {}).items() for m in d.get("files", [])}
        part_of.update({m: k for m, (k, _sha) in mine.items()})
        nm = GS.names()
        differ = {part_of.get(m, m) for m in set(mine) | set(theirs) if (mine.get(m) or ("", ""))[1] != theirs.get(m)}
        names = sorted(nm.get(k, k) for k in differ)
    except Exception:  # noqa: BLE001  the count is a courtesy; installing does not depend on it
        names = []
    words = (f"{_n(len(names), 'part', 'parts')} will change: " + ", ".join(names[:6])
             + (f" and {len(names) - 6} more" if len(names) > 6 else "") + ".") if names else "It replaces the one installed."
    return {"number": st["ready"], "parts": names, "words": words}


STARTED_KEY = "datum_started"          # in the effort's own settings: the number it was started on (0: none installed)


def record_start(ws, config_dir):
    """A new effort remembers the Production Datum it was started on. Returns the number kept (0 when none)."""
    n = GS.state(config_dir)["version"]
    ws.set(STARTED_KEY, int(n))
    return n


def started(ws):
    """What an effort's details say; "" for an effort started before this was kept (nothing is guessed)."""
    n = ws.get(STARTED_KEY, None) if ws is not None else None
    if not isinstance(n, int) or isinstance(n, bool):
        return ""
    return f"Started on {NAME} {n}" if n else f"Started with no {NAME} installed"
