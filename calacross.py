"""Calendar across efforts (4.52.0; decision 63, narrowed by 81). The dated things of every effort on this PC in one list,
for the Calendar with no effort open and for its "Other efforts" block while one is open. Every effort that is not
archived, not a program and not Unfiled is read from its saved files the way the open effort's calendar is (its record:
the due date, stages, tasks, gate goals, events; the dates its deliverables carry; questions due read from its
customer documents), without opening it: no lock is taken, no Workspace is made, no folder is created. An effort whose
files are missing or cannot be read is left out, never an error. A program has no calendar. Standard library plus the
effort modules; rules only (No AI); nothing leaves the PC.
"""
import datetime
import os

DAYS_BACK = 0           # the list is what is ahead: today's things and later, as the Calendar's "Coming up" reads
DAYS_AHEAD = 730


def _homes(registry, skip=()):
    import programs as PG
    import unfiled as UF
    return [n for n in PG.effort_names(registry) if n != UF.NAME and n not in set(skip or ())]


def _calendar(root, first, last):
    """{date: [(kind, text)]} for one effort's data folder, read only."""
    import effortrec as R
    import effortstate as ES
    rec = R.Record(root)
    extra = []
    try:
        import delivmore as DM
        extra += DM.cal_items(rec)
    except Exception:  # noqa: BLE001  a part that cannot be read adds nothing
        pass
    docs = os.path.join(root, "documents")
    if os.path.isfile(os.path.join(docs, "index.json")):
        try:
            import docversions as DV
            import subreq as SR
            rows = SR.Register(DV.Library(docs).load()).rows()
            extra += ES.cal_extra_of(rec, rows)
        except Exception:  # noqa: BLE001
            pass
    return rec.calendar(first=first, last=last, extra=extra)


def collect(registry, today=None, skip=()):
    """[{"effort", "date", "what", "kind", "days"}] for every effort (skip: names left out, such as the one open), soonest
    first; what has happened ("done", "event") is the effort's activity, not a date ahead."""
    import workspace as W
    import overview as OV
    today = today or datetime.date.today()
    first, last = today - datetime.timedelta(days=DAYS_BACK), today + datetime.timedelta(days=DAYS_AHEAD)
    out = []
    for name in _homes(registry, skip):
        path = (registry.get(name) or {}).get("path") or ""
        if not path or not os.path.isfile(path):
            continue
        root = W.data_dir_for(path)
        if not os.path.isfile(os.path.join(root, "record.json")):
            continue                                  # never opened, nothing dated yet: nothing to read, nothing made
        try:
            cal = _calendar(root, first, last)
        except Exception:  # noqa: BLE001  an effort that cannot be read is left out
            continue
        for d, items in cal.items():
            if d is None:
                continue
            for kind, text in items:
                if kind in ("done", "event"):
                    continue
                out.append({"effort": name, "date": d, "what": text, "kind": OV.KIND_WORDS.get(kind, kind.capitalize()),
                            "days": (d - today).days})
    out.sort(key=lambda r: (r["date"], r["effort"].casefold(), r["what"].casefold()))
    return out


def when(row, today=None):
    """The date in words, as the Calendar's other lists say it."""
    import overview as OV
    return OV.when(row["date"], today or datetime.date.today())
