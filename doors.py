"""The three doors (4.52.0; decisions 7, 80, 8, 9 of the UX build brief). What a person can do with a document from the
Overview: Acronyms (the customer's document or ours), Shred to setup (the customer's; efforts only) and Check a document
(ours; today it is Audit, which changes nothing, until the ordered checks of decision 79 are built). Each door asks
where the work goes in the same step (homes.choices). Inside an open program only Acronyms and Check a document show.

What a door reads comes from the Quick tools uses it stands for (skqt/toolshome.USES): Acronyms is the use "acronyms",
Shred to setup adds to Documents and shreds there ("library" and the use "shred"'s extensions), Check a document is
"audit". Standard library plus app_gui's list of the files the readers take; rules only (No AI); nothing leaves the PC.
"""
import os

DOORS = (("acronyms", "Acronyms", "Find the acronyms in a document, the customer's or ours"),
         ("shred", "Shred to setup", "The customer's document: its requirements, then the outline, the matrix and the setup"),
         ("check", "Check a document", "Our own document, checked against the standards. Changes nothing."))
KEYS = tuple(k for k, _n, _w in DOORS)
NAMES = {k: n for k, n, _w in DOORS}
WHAT = {k: w for k, _n, w in DOORS}
# the doors each kind of home shows: nothing open, an effort open, a program open (decision 80)
FOR_HOME = {"none": KEYS, "effort": KEYS, "program": ("acronyms", "check")}
EFFORT_ONLY = ("shred",)


def for_home(kind):
    """The door keys for a kind of home: "none" (nothing open), "effort" or "program"."""
    return tuple(FOR_HOME.get(kind or "none", KEYS))


def _uses():
    from skqt import toolshome as TH        # the extensions live with the uses; reading them does not build a window
    return {k: ok for k, _t, ok in TH.USES}


def exts(door):
    """The extensions a door reads (lower case, with the dot), from the uses it stands for."""
    import app_gui as A
    every = set(A.SUPPORTED_EXTS)
    u = _uses()
    if door == "acronyms":
        got = u.get("acronyms")
    elif door == "shred":
        lib, shred = u.get("library"), u.get("shred")
        got = (set(lib) if lib is not None else every) & (set(shred) if shred is not None else every)
    elif door == "check":
        got = u.get("audit")
    else:
        return set()
    return (set(got) if got is not None else every) & every


def takes(door, paths):
    """True when the door reads every one of the files (and there is at least one)."""
    if not paths:
        return False
    ok = exts(door)
    return all(os.path.splitext(str(p))[1].lower() in ok for p in paths)


def doors_for(kind, paths):
    """The doors of that kind of home that take the files, in the doors' order."""
    return tuple(k for k in for_home(kind) if takes(k, paths))


def wants_programs(door):
    """Whether a program is offered as where the work goes: Shred to setup works in an effort only."""
    return door not in EFFORT_ONLY


def home_kind(registry, ws_open, name):
    """The kind of home open now: "none", "program" or "effort"."""
    if not ws_open:
        return "none"
    import programs as PG
    return "program" if PG.is_program(registry, name) else "effort"
