"""Schedule from the due date (3.1.0): date every stage of an effort backward from the proposal due date, from how many
working days each stage takes (the team's defaults by stage name, changed per effort), or fit the same proportions
between a start date and the due date. Weekends are skipped unless asked; the team's holidays too. The proposal
manager sees every date before anything is set, and the stages keep their names, goals and gates. Rules only."""
import datetime, json, os

FILE = "schedule_defaults.json"
# working days each of the built-in stages usually takes; a stage not named here takes FALLBACK
BUILT_IN = {"Intake": 3, "Kickoff": 2, "Storyboards": 5, "Author drafts": 10, "Pink team": 2, "Pink team recovery": 4,
            "Red team": 2, "Red team recovery": 5, "Gold team": 1, "Gold team recovery": 3, "Final to pubs": 3,
            "Production": 3, "Submission": 1}
FALLBACK = 3


def _key(name):
    return " ".join((name or "").split()).casefold()


def load_defaults(config_dir):
    """{"days": {stage name: working days}, "weekends": bool, "holidays": ["YYYY-MM-DD"]}, the team's over the built-in."""
    d = {}
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    days = dict(BUILT_IN)
    for k, v in (d.get("days") or {}).items():
        try:
            days[" ".join(str(k).split())] = max(0, min(200, int(v)))
        except (TypeError, ValueError):
            continue
    hol = sorted({h for h in d.get("holidays", []) if _date(h)})
    return {"days": days, "weekends": bool(d.get("weekends", False)), "holidays": hol}


def save_defaults(config_dir, days=None, weekends=None, holidays=None):
    cur = load_defaults(config_dir)
    if days:
        cur["days"].update({" ".join(str(k).split()): max(0, min(200, int(v))) for k, v in days.items()})
    if weekends is not None:
        cur["weekends"] = bool(weekends)
    if holidays is not None:
        cur["holidays"] = sorted({h for h in holidays if _date(h)})
    os.makedirs(config_dir, exist_ok=True)
    out = {"days": {k: v for k, v in cur["days"].items() if BUILT_IN.get(k) != v}, "weekends": cur["weekends"],
           "holidays": cur["holidays"]}
    tmp = os.path.join(config_dir, FILE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, os.path.join(config_dir, FILE))
    return cur


def days_for(name, defaults):
    """Working days for a stage name: the team's, matched without case, else FALLBACK."""
    by = {_key(k): v for k, v in defaults["days"].items()}
    return by.get(_key(name), FALLBACK)


def _date(x):
    if isinstance(x, datetime.datetime):
        return x.date()
    if isinstance(x, datetime.date):
        return x
    try:
        return datetime.date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


class Calendar:
    """Which days count: every day when weekends count, else Monday to Friday; never a holiday."""

    def __init__(self, weekends=False, holidays=()):
        self.weekends = weekends
        self.holidays = {_date(h) for h in holidays if _date(h)}

    def works(self, d):
        return d not in self.holidays and (self.weekends or d.weekday() < 5)

    def back(self, d, n=1):
        """The working day n working days before d."""
        while n > 0:
            d -= datetime.timedelta(days=1)
            if self.works(d):
                n -= 1
        return d

    def on_or_before(self, d):
        while not self.works(d):
            d -= datetime.timedelta(days=1)
        return d

    def on_or_after(self, d):
        while not self.works(d):
            d += datetime.timedelta(days=1)
        return d

    def count(self, a, b):
        """Working days from a to b, both counted."""
        n, d = 0, a
        while d <= b:
            n += self.works(d)
            d += datetime.timedelta(days=1)
        return n


def plan_back(names_days, due, cal, last_ends_on_due=True):
    """[(name, start date, end date)] working backward from the due date: the last stage ends on the due date (or the
    working day before it), each stage before ends the working day before the next one starts. A stage of 0 days takes
    one day: it shares its day with the next stage's start."""
    due = _date(due)
    end = cal.on_or_before(due if last_ends_on_due else cal.back(due))
    out = []
    for name, n in reversed(list(names_days)):
        n = max(1, int(n))
        start = end
        for _ in range(n - 1):
            start = cal.back(start)
        out.append((name, start, end))
        end = cal.back(start)
    return list(reversed(out))


def fit(names_days, start, due, cal, last_ends_on_due=True):
    """The same proportions squeezed or stretched to start on start and end on (or the working day before) the due
    date. Every stage keeps at least one day; days left over by rounding go to the longest stages."""
    start, due = cal.on_or_after(_date(start)), _date(due)
    end = cal.on_or_before(due if last_ends_on_due else cal.back(due))
    avail = cal.count(start, end)
    items = list(names_days)
    if not items or avail <= 0:
        return [], 0
    want = [max(1, int(n)) for _name, n in items]
    if avail < len(items):
        return [], avail
    total = sum(want)
    exact = [w * avail / total for w in want]
    got = [max(1, int(x)) for x in exact]
    while sum(got) > avail:                            # take from the biggest
        i = max(range(len(got)), key=lambda k: (got[k] - exact[k], got[k]))
        if got[i] > 1:
            got[i] -= 1
        else:
            break
    while sum(got) < avail:                            # give to whoever lost most to rounding
        i = max(range(len(got)), key=lambda k: (exact[k] - got[k], want[k]))
        got[i] += 1
    return plan_back([(items[k][0], got[k]) for k in range(len(items))], due, cal, last_ends_on_due), avail


def apply(rec, plan, who=None):
    """Sets each stage's planned start and end from the plan [(stage id, start, end)]; names, goals, gates and times
    stay. Returns how many stages got dates."""
    by = {sid: (a, b) for sid, a, b in plan}
    rows = []
    for s in rec.stages:
        a, b = by.get(s["id"], (None, None))
        rows.append((s["id"], s["name"], a.isoformat() if a else s.get("planned", ""), b.isoformat() if b else s.get("planned_end", ""),
                     s.get("planned_time", ""), s.get("planned_end_time", "")))
    rec.edit_stages(rows, who=who)
    n = sum(1 for s in rec.stages if s["id"] in by)
    first, last = (min(a for _s, a, _b in plan), max(b for _s, _a, b in plan)) if plan else (None, None)
    rec.log("stage", f"Schedule set from the due date: {n} stages, {first} to {last}" if plan else "Schedule cleared", who=who)
    rec.save()
    return n
