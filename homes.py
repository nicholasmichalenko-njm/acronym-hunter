"""Homes (4.51.0): what a home for work is, for the question "Where does it go?". Work is always attached to something
(decision 44): an effort or a program. A file dropped on Quick tools always gets a named home: the one open now, another
effort or program, a new effort or a new program. A new one takes a name only, filled in from the file's name (decision
60). The tool and the home are asked in one step, every time (decision 9).

Unfiled takes no new work (Nicholas 2026-11-17). What it already holds stays where it is, can be opened, and is shown as
"Unfiled, from before"; its registry name stays unfiled.NAME. The app offers once, at start, to name it as an effort or
a program; the answer is kept on Unfiled's registry entry (named_offer: "" not offered yet, "later" not now, "named").
Nothing here moves, renames or removes a file. Standard library plus the effort modules.
"""
import os
import re

SHOWN = "Unfiled, from before"
OFFER_KEY = "named_offer"
LATER, NAMED = "later", "named"
NEW_EFFORT, NEW_PROGRAM, HOME = "new_effort", "new_program", "home"
MAX_NAME = 60


def _info(registry, name):
    return (registry.get(name) or {}) if name else {}


def suggest_name(paths):
    """A name from the first file's name: its stem, underscores and hyphens as spaces, at most 60 characters."""
    if not paths:
        return ""
    stem = os.path.splitext(os.path.basename(str(paths[0])))[0]
    name = re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", stem)).strip()
    return name[:MAX_NAME].strip()


def _taken(registry, name):
    import unfiled as UF
    n = name.casefold()
    return n == UF.NAME.casefold() or any(x.casefold() == n for x in registry.names())


def free_name(registry, name):
    """The name, or the name with " 2", " 3"... until no effort, program or Unfiled has it (any case)."""
    name = (name or "").strip()
    if not name:
        return ""
    got, k = name, 2
    while _taken(registry, got):
        got = f"{name} {k}"
        k += 1
    return got


def _live(registry, name):
    import unfiled as UF
    info = _info(registry, name)
    return bool(info) and not info.get("archived") and not info.get("unfiled") and name != UF.NAME


def choices(registry, open_name, paths=None, programs=True):
    """The answers to "Where does it go?", in order: the open home (not Unfiled), the other efforts A to Z, the other
    programs A to Z, a new effort, a new program. With programs=False no program is offered (a use only an effort has)."""
    import programs as PG
    out = []
    is_prog = PG.is_program(registry, open_name)
    if open_name and _live(registry, open_name) and (programs or not is_prog):
        out.append({"key": (HOME, open_name), "label": f"{open_name} (open now)", "kind": "program" if is_prog else "effort"})
    others = [n for n in registry.names() if n != open_name and _live(registry, n)]
    for n in sorted((n for n in others if not PG.is_program(registry, n)), key=str.casefold):
        out.append({"key": (HOME, n), "label": n, "kind": "effort"})
    if programs:
        for n in sorted((n for n in others if PG.is_program(registry, n)), key=str.casefold):
            out.append({"key": (HOME, n), "label": f"{n} (program)", "kind": "program"})
    out.append({"key": (NEW_EFFORT, None), "label": "A new effort", "kind": "effort"})
    if programs:
        out.append({"key": (NEW_PROGRAM, None), "label": "A new program", "kind": "program"})
    return out


def check_new(registry, name, kind="effort"):
    """'' when a new effort (or program) can take the name, else one plain sentence (programs.check_name's words)."""
    import programs as PG
    why = PG.check_name(registry, name)
    if kind != "program":
        why = why.replace("Give the program a name.", "Give the effort a name.")
    return why


def holds_work(registry):
    """Unfiled exists and holds something. Never makes Unfiled."""
    import unfiled as UF
    if not _info(registry, UF.NAME).get("unfiled"):
        return False
    return not UF.empty(UF.counts(registry))


def shown_name(registry, name):
    """The name a person sees for a home: Unfiled reads "Unfiled, from before"."""
    import unfiled as UF
    return SHOWN if name and name == UF.NAME and UF.is_unfiled(registry, name) else (name or "")


def offer_state(registry):
    import unfiled as UF
    return _info(registry, UF.NAME).get(OFFER_KEY) or ""


def set_offer_state(registry, value):
    """Keep the answer on Unfiled's registry entry. False when there is no Unfiled (nothing is made)."""
    import unfiled as UF
    if not _info(registry, UF.NAME):
        return False
    registry.put(UF.NAME, **{OFFER_KEY: value or ""})
    return True


def start_offer_due(registry):
    return holds_work(registry) and offer_state(registry) == ""
