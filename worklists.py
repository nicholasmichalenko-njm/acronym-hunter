"""Tasks, the calendar's lists and Activity (4.27.1; Nicholas 2026-11-12 21:25, answer 2: Tasks and Calendar are menu
entries, Activity is a tab of the effort's page). The lists those three pages show, worked out from what the effort
record already keeps (tasks, the calendar, the timeline). Nothing new is stored. Standard library only; rules only."""
import datetime

BUCKETS = ("Late", "Today", "This week", "Later", "No date")
KIND_NAMES = {"effort": "Effort", "deliverable": "Deliverables", "customer": "Customer", "stage": "Stages", "task": "Tasks",
              "outline": "Outline", "matrix": "Matrix", "document": "Documents", "assign": "Assignments", "qa": "Customer Q&A",
              "note": "Notes", "graphic": "Graphics", "datacall": "Data calls", "review": "Color reviews", "requirement": "Rules",
              "production": "Production", "gate": "Gates", "check": "Checks", "truth": "Wall of Truth", "theme": "Themes"}
REF_PAGE = {"task": "tasks", "graphic": "graphics", "deliverable": "deliverables", "truth": "truth", "note": "home", "theme": "home"}
PERIODS = (("7", "The last 7 days"), ("30", "The last 30 days"), ("", "Everything"))


def _date(text):
    try:
        return datetime.date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def task_groups(tasks, stages, today=None, overdue=None):
    """This effort's tasks by gate: [(gate name, [task])], the effort's stages in order, then tasks with no gate; open
    ones first inside each, late ones before those. Each task gets "late"."""
    today = today or datetime.date.today()
    names = {s["id"]: s["name"] for s in stages}
    order = [s["id"] for s in stages]
    by = {}
    for t in tasks:
        d = _date(t.get("due"))
        late = (overdue(t) if overdue is not None else bool(d and d < today)) and t.get("status") != "Done"
        by.setdefault(t.get("stage") if t.get("stage") in names else "", []).append(dict(t, late=late))
    out = []
    for sid in order + [""]:
        mine = by.get(sid)
        if not mine:
            continue
        mine.sort(key=lambda t: (t.get("status") == "Done", not t["late"], t.get("due") or "9999", t.get("title", "").casefold()))
        out.append((names.get(sid, "No gate"), mine))
    return out


def task_counts(tasks, overdue=None, today=None):
    """(open, late, done)."""
    today = today or datetime.date.today()
    op = [t for t in tasks if t.get("status") != "Done"]
    late = sum(1 for t in op if (overdue(t) if overdue is not None else bool(_date(t.get("due")) and _date(t.get("due")) < today)))
    return len(op), late, len(tasks) - len(op)


def bucket(due, today=None):
    """Late, Today, This week (through Sunday), Later, or No date, for a datetime or a date."""
    today = today or datetime.date.today()
    if due is None:
        return "No date"
    d = due.date() if isinstance(due, datetime.datetime) else due
    if d < today:
        return "Late"
    if d == today:
        return "Today"
    return "This week" if d <= today + datetime.timedelta(days=6 - today.weekday()) else "Later"


def mine_groups(rows, today=None):
    """One person's items across efforts (mywork.soonest rows) as [(bucket, [row])], in BUCKETS order, empty ones left out."""
    by = {}
    for r in rows:
        by.setdefault(bucket(r.get("due_date"), today), []).append(r)
    return [(b, by[b]) for b in BUCKETS if by.get(b)]


def day_items(cal, day):
    """What falls on one day: [(kind, text)]."""
    return list(cal.get(day, []))


def activity(events, who="", kind="", days="", today=None):
    """The timeline as rows grouped by day, newest first: [(day in words, [(time, who, kind, text, ref)])]. who, kind
    and days (a number of days back, or "") narrow it."""
    today = today or datetime.date.today()
    since = (today - datetime.timedelta(days=int(days))) if str(days).isdigit() else None
    out, cur = [], None
    for e in events:
        at = str(e.get("at") or "")
        d = _date(at)
        if since is not None and (d is None or d < since):
            continue
        if who and (e.get("who") or "").strip().casefold() != who.strip().casefold():
            continue
        if kind and e.get("kind") != kind:
            continue
        label = day_words(d, today)
        if cur is None or cur[0] != label:
            cur = (label, [])
            out.append(cur)
        cur[1].append((at[11:16], e.get("who", ""), KIND_NAMES.get(e.get("kind", ""), str(e.get("kind", "")).capitalize()),
                       e.get("text", ""), e.get("ref") or {}))
    return out


def day_words(d, today):
    if d is None:
        return "No date"
    n = (today - d).days
    if n == 0:
        return "Today"
    if n == 1:
        return "Yesterday"
    return f"{d.strftime('%A')}, {d.strftime('%b')} {d.day}" + (f", {d.year}" if d.year != today.year else "")


def people(events):
    return sorted({(e.get("who") or "").strip() for e in events if (e.get("who") or "").strip()}, key=str.casefold)


def kinds(events):
    """[(kind, name)] of the kinds that happened, by name."""
    return sorted(((k, KIND_NAMES.get(k, k.capitalize())) for k in {e.get("kind", "") for e in events} if k), key=lambda x: x[1])


def page_of(ref):
    """The page that shows what a row is about, or ""."""
    for k in (ref or {}):
        if k in REF_PAGE:
            return REF_PAGE[k]
    return ""
