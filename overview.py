"""The effort's page on one screen (4.27.0; Nicholas's recording 2026-11-12 07:55 to 08:45; answer 20; the plan board
claude/stationkeeper-recording-plan-2026-11-12.html). What the Overview shows, as plain numbers and short lists, read
from what the effort already keeps: nothing is stored here.

A block is on that screen only when it changes what someone does today or this week, has a date, or is a count that
links to where the problem is fixed. So: the next step; the path with what is left on each step; up to four counts,
each with the page that fixes it; the deliverables, one row each; the Wall of Truth as one line; the next ten dated
things; the customer; the last three things that happened. Standard library only; rules only."""
import datetime

MOST_NUMBERS = 4
MOST_DATES = 10
MOST_DELIVERABLES = 6
KIND_WORDS = {"due": "Due", "deadline": "Due", "questions": "Questions due", "stage": "Stage", "task": "Task", "done": "Done",
              "goal": "Gate goal", "deliverable": "Deliverable", "section": "Section due", "meeting": "Meeting"}


def _plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def numbers(f, late_tasks=0, graphics_left=0, review_open=0, questions=0):
    """[(count, words, page)]: the counts that link to where each is fixed, the largest worry first; none that is 0."""
    r = f.get("reqs") or {}
    cands = [(int(r.get("undecided") or 0), "not shredded", "assign"),
             (int((r.get("reqs") or 0) - (r.get("placed") or 0)) if r else 0, "to place", "place"),
             (int(f.get("compare") or 0), "changes to review", "compare"),
             (int(late_tasks or 0), "tasks late", "tasks"),
             (int(f.get("acronyms") or 0), "acros and abs undecided", "acronyms"),
             (int(graphics_left or 0), "graphics not swept", "graphics"),
             (int(review_open or 0), "review items open", "drafts"),
             (int(questions or 0), "questions open", "home")]
    return [(n, w, go) for n, w, go in cands if n > 0][:MOST_NUMBERS]


def path(sts):
    """[(key, number, name, badge, state)] for the six steps."""
    return [(s["key"], s.get("n"), s["name"], s.get("badge", ""), s.get("state", "later")) for s in sts if s.get("key") != "home"]


def dates(cal, today=None):
    """The next dated things from the effort's calendar {date: [(kind, text)]}: [(date, in words, kind, text)], soonest
    first, today's included."""
    today = today or datetime.date.today()
    out = []
    for d in sorted(k for k in cal if k and k >= today):
        for kind, text in cal[d]:
            if kind in ("done", "event"):          # what happened is Latest activity's, not a date ahead
                continue
            out.append((d, when(d, today), KIND_WORDS.get(kind, kind.capitalize()), text))
    return out[:MOST_DATES]


def when(d, today):
    n = (d - today).days
    if n == 0:
        return "Today"
    if n == 1:
        return "Tomorrow"
    if n < 7:
        return d.strftime("%a")
    return f"{d.strftime('%b')} {d.day}"


def due_words(days):
    if days is None:
        return "No due date yet"
    if days < 0:
        return f"Due {_plural(-days, 'day')} ago"
    return "Due today" if days == 0 else f"Due in {_plural(days, 'day')}"


def deliverables(ds, states):
    """One row each: (id, name, owner, status, what changed), the ones that need someone first."""
    rows = []
    for d, st in zip(ds, states):
        ch = st.get("changed")
        changed = (str(ch[0]) if isinstance(ch, (list, tuple)) and ch else "changed" if ch else "") or ("Over its limit" if st.get("over") else "")
        rows.append((d.get("id", ""), d.get("name", ""), d.get("owner", "") or "No owner", d.get("status", ""), changed))
    rows.sort(key=lambda r: (not r[4], r[2] != "No owner", r[3] in ("Final", "Submitted"), r[1].casefold()))
    return rows


def customer(client, solicitation, contacts, info):
    """The customer card's lines: who, the solicitation, up to three contacts, how many facts are filed."""
    lines = []
    if client:
        lines.append(("Customer", client))
    if solicitation:
        lines.append(("Solicitation", solicitation))
    for c in (contacts or [])[:3]:
        who = ", ".join(x for x in (c.get("name", ""), c.get("title", "")) if x)
        how = next((v for k in ("email", "phone") for v in _values(c.get(k)) if v), "")
        if who or how:
            lines.append((c.get("org", "") or "Contact", who + (f"  ·  {how}" if how else "")))
    if info:
        lines.append(("Filed", _plural(len(info), "fact") + " about the customer"))
    return lines


def _values(v):
    if isinstance(v, str):
        return [v]
    out = []
    for x in v or []:
        out.append(x.get("value", "") if isinstance(x, dict) else str(x))
    return out


def activity(events, n=3):
    """The last things that happened: [(when, who, what)]."""
    return [((e.get("at") or "").replace("T", " ")[:16], e.get("who", ""), e.get("text", "")) for e in (events or [])[:n]]
