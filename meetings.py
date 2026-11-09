"""Meetings and their topics (3.20.0): a meeting (title, date and time, participants, notes) and the topics it raised,
each one followed until someone marks it considered (or not needed), with who and when. A topic can point at a section
of the response structure or a requirement, and name an owner; open topics show on the Effort Dashboard, in My Work for
their owner, and on the card of what they point at, and a gate goal can hold a stage until every topic is considered.

Kept in the effort record (record.json, "meetings"); each meeting is also an entry on the effort calendar. Topics are
never made up: a person types them, or picks lines of the notes that start with a bullet or "Topic:", "Action:" or
"Decision:" (Topics from notes). Rules only (No AI); nothing leaves the PC."""
import datetime, getpass, re, uuid

STATUS = (("open", "Open"), ("considered", "Considered"), ("not_needed", "Not needed"))
STATUS_NAME = dict(STATUS)
_BULLET = re.compile(r"^\s*(?:[-*•▪–]|\d+[.)]|(?:topic|action|decision|follow[- ]?up|todo|to do)\s*:)\s*(.+?)\s*$", re.I)


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _who(who=None):
    return who or getpass.getuser()


def _clean(t, n=400):
    return " ".join(str(t or "").split())[:n]


def meetings(rec):
    """Newest first."""
    ms = [m for m in rec.data.get("meetings", []) if isinstance(m, dict)]
    return sorted(ms, key=lambda m: (m.get("date", ""), m.get("start", "")), reverse=True)


def get(rec, mid):
    return next((m for m in rec.data.get("meetings", []) if m.get("id") == mid), None)


def add_meeting(rec, title, date, start="", end="", zone="", participants=(), notes="", who=None):
    """A meeting, on the effort calendar too. Returns its id (None without a title or a date)."""
    title, date = _clean(title, 200), _clean(date, 10)
    if not title or not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return None
    m = {"id": uuid.uuid4().hex[:10], "title": title, "date": date, "start": _clean(start, 5), "end": _clean(end, 5),
         "zone": _clean(zone, 40), "participants": _names(participants), "notes": str(notes or "")[:20000], "topics": [],
         "created": _now(), "by": _who(who), "event": ""}
    try:
        import effortcal as EC
        m["event"] = EC.add_entry(rec, who=who, kind="Meeting", date=date, start=m["start"], end=m["end"], zone=m["zone"],
                                  title=title, details="Participants: " + ", ".join(m["participants"])) or ""
    except Exception:
        import diag
        diag.swallowed()
    rec.data.setdefault("meetings", []).append(m)
    rec.log("effort", f"Meeting: {title} ({date})", who=who)
    rec.save()
    return m["id"]


def of_event(rec, event_id):
    """3.92.1: the meeting whose notes belong to this calendar event, or None."""
    return next((m for m in rec.data.get("meetings", []) if event_id and m.get("event") == event_id), None)


def for_event(rec, event_id, who=None):
    """3.92.1: the notes of a calendar event: its meeting, made from the event the first time (title, date, times,
    participants from its details), linked to it. Returns the meeting's id (None for an unknown event)."""
    m = of_event(rec, event_id)
    if m is not None:
        return m["id"]
    e = next((x for x in rec.data.get("events", []) if x.get("id") == event_id), None)
    if e is None:
        return None
    det = str(e.get("details") or "")
    who_line = det.split("Participants:", 1)[1].split("\n")[0] if "Participants:" in det else ""
    names = _names(who_line)
    if names and len(names[-1].split()) > 3:              # the details' next sentence ran onto the last name
        names[-1] = " ".join(names[-1].split()[:2])
    parts = names or ([e["owner"]] if e.get("owner") else [])
    m = {"id": uuid.uuid4().hex[:10], "title": _clean(e.get("title") or "Meeting", 200), "date": _clean(e.get("date"), 10),
         "start": _clean(e.get("start"), 5), "end": _clean(e.get("end"), 5), "zone": _clean(e.get("zone"), 40),
         "participants": parts, "notes": "", "topics": [], "created": _now(), "by": _who(who), "event": event_id}
    rec.data.setdefault("meetings", []).append(m)
    rec.log("effort", f"Meeting notes started: {m['title']} ({m['date']})", who=who)
    rec.save()
    return m["id"]


def _names(names):
    if isinstance(names, str):
        names = re.split(r"[;,\n]", names)
    out = []
    for n in names or []:
        n = _clean(n, 80)
        if n and n.casefold() not in {x.casefold() for x in out}:
            out.append(n)
    return out


def update_meeting(rec, mid, who=None, **f):
    m = get(rec, mid)
    if m is None:
        return False
    for k in ("title", "date", "start", "end", "zone"):
        if k in f:
            m[k] = _clean(f[k], 200 if k == "title" else 40)
    if "participants" in f:
        m["participants"] = _names(f["participants"])
    if "notes" in f:
        m["notes"] = str(f["notes"] or "")[:20000]
    try:
        import effortcal as EC
        if m.get("event") and set(f) - {"notes"}:            # 3.92.1: notes alone never rewrite the calendar entry
            EC.update_entry(rec, m["event"], who=who, date=m["date"], start=m["start"], end=m["end"], zone=m["zone"],
                            title=m["title"], details="Participants: " + ", ".join(m["participants"]))
    except Exception:
        import diag
        diag.swallowed()
    rec.save()
    return True


def delete_meeting(rec, mid, who=None):
    m = get(rec, mid)
    if m is None:
        return False
    rec.data["meetings"] = [x for x in rec.data.get("meetings", []) if x.get("id") != mid]
    if m.get("event"):
        rec.data["events"] = [e for e in rec.data.get("events", []) if e.get("id") != m["event"]]
    rec.log("effort", f"Meeting removed: {m['title']} ({m['date']})", who=who)
    rec.save()
    return True


# ------------------------------------------------------------------ topics
def add_topic(rec, mid, text, owner="", target="", who=None):
    """A topic the meeting raised. target: a section label or a requirement ID (what it points at). Returns its id."""
    m = get(rec, mid)
    text = _clean(text, 600)
    if m is None or not text:
        return None
    t = {"id": uuid.uuid4().hex[:10], "text": text, "owner": _clean(owner, 80), "target": _clean(target, 200),
         "status": "open", "by": "", "at": "", "why": "", "added": _now(), "added_by": _who(who)}
    m.setdefault("topics", []).append(t)
    rec.log("effort", f"Meeting topic: {text[:120]}", who=who)
    rec.save()
    return t["id"]


def update_topic(rec, mid, tid, **f):
    t = topic(rec, mid, tid)
    if t is None:
        return False
    for k in ("text", "owner", "target"):
        if k in f:
            t[k] = _clean(f[k], 600 if k == "text" else 200)
    rec.save()
    return True


def topic(rec, mid, tid):
    m = get(rec, mid)
    return next((t for t in (m or {}).get("topics", []) if t["id"] == tid), None)


def set_status(rec, mid, tid, status, why="", who=None):
    """Considered, not needed, or open again, with who and when."""
    t = topic(rec, mid, tid)
    if t is None or status not in STATUS_NAME:
        return False
    t["status"] = status
    t["by"], t["at"] = ("", "") if status == "open" else (_who(who), _now())
    t["why"] = _clean(why, 400) if status != "open" else ""
    rec.log("effort", f"Meeting topic {STATUS_NAME[status].lower()}: {t['text'][:120]}", who=who)
    rec.save()
    return True


def remove_topic(rec, mid, tid):
    m = get(rec, mid)
    if m is None:
        return False
    before = len(m.get("topics", []))
    m["topics"] = [t for t in m.get("topics", []) if t["id"] != tid]
    rec.save()
    return len(m["topics"]) < before


def topics(rec, open_only=False, owner=None, target=None):
    """[(meeting, topic)] across the effort's meetings, newest meeting first."""
    out = []
    for m in meetings(rec):
        for t in m.get("topics", []):
            if open_only and t.get("status") != "open":
                continue
            if owner is not None and (t.get("owner") or "").casefold() != (owner or "").casefold():
                continue
            if target is not None and t.get("target") not in (target if isinstance(target, (list, tuple, set)) else [target]):
                continue
            out.append((m, t))
    return out


def open_count(rec):
    return len(topics(rec, open_only=True))


def topics_from_notes(notes):
    """The lines of the notes that read as topics: a bullet (-, *, 1.) or Topic:, Action:, Decision:, Follow-up:, To do:."""
    out = []
    for line in str(notes or "").splitlines():
        m = _BULLET.match(line)
        if m and len(m.group(1)) >= 4 and m.group(1) not in out:
            out.append(m.group(1))
    return out


def all_considered(rec):
    """For the gate goal: True when every topic is considered or not needed, None with no topics at all."""
    ts = topics(rec)
    if not ts:
        return None
    return all(t.get("status") != "open" for _m, t in ts)


# ------------------------------------------------------------------ Word
def export_docx(rec, mid, path):
    """The meeting, its participants, notes and topics with their status, in Word."""
    import docxw
    m = get(rec, mid)
    if m is None:
        return None
    d = docxw.Doc()
    d.heading(m["title"], 1)
    d.para(m["date"] + (f"  {m['start']}" if m.get("start") else "") + (f" to {m['end']}" if m.get("end") else "")
           + (f" {m['zone']}" if m.get("zone") else ""), color="4E5D71")
    if m.get("participants"):
        d.para("Participants: " + ", ".join(m["participants"]))
    d.heading("Notes", 2)
    for line in (m.get("notes") or "").splitlines() or [""]:
        d.para(line)
    d.heading("Topics", 2)
    rows = [[t["text"], t.get("target", ""), t.get("owner", ""), STATUS_NAME.get(t.get("status"), "")
             + (f" ({t['by']}, {t['at'][:10]})" if t.get("by") else "") + (f": {t['why']}" if t.get("why") else "")]
            for t in m.get("topics", [])]
    if rows:
        d.table(["Topic", "Points at", "Owner", "Status"], rows, [4200, 1900, 1400, 1860])
    else:
        d.para("No topics.")
    d.save(path)
    return path
