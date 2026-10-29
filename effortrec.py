"""The effort record (2.40.0): what the proposal manager keeps for one effort, beside the features' own files.

- Basics: the due date and time (with its time zone as written) and the opportunity number; client, solicitation and
  internal number stay in the effort list as before. countdown() gives days and hours to the due time.
- Stages: the team's gates, editable per effort (rename, add, remove, reorder) with a planned date each. Only the
  proposal manager moves the stage (move_to); the open goals of the stage being left can carry over.
- Gate goals per stage: written by the person, or checked by the app from the features (AUTO keys, see goal_done).
- Timeline: the paper trail. Every customer document version, requirement change, stage move, note, task and
  assignment is logged with who and when, so the effort's history can be shown and exported at any moment.
- Notes: on the effort, a stage, a customer document or version, a requirement, a section, a task; a note can be an
  open question, resolved later.
- Tasks: title, owner, due date, stage, status, what it is about, notes.

Saved as record.json in the effort's app data folder (beside settings.json). Rules only (No AI); nothing leaves the PC.
"""
import datetime, getpass, os, re, uuid

DEFAULT_STAGES = ("Intake", "Author drafts", "Red team", "Red team recovery", "Gold team", "Gold team recovery", "Final to pubs")
TASK_STATUS = ("Not started", "In progress", "Done")
# 2.63.0 stage gates: none; soft (moving on with open goals is allowed, and logged with the open goals and any reason);
# hard (moving on is held until every goal is met, unless the proposal manager overrides it with a written reason)
GATES = {"": "No gate", "soft": "Soft gate: warn and log", "hard": "Hard gate: hold until the goals are met"}
GATE_BEHAVIOR = {"": "", "soft": "soft", "hard": "hard"}   # 2.93.0: a gate's id -> what it does ("", soft, hard)
DEFAULT_STAGE_GATES = {}                                   # 2.93.0: the team's default gate for a new effort's stage
GATE_ABOUT = {}                                            # 2.93.0: what each gate means, in the team's words


def set_process(P):
    """2.93.0: the team's gates and default stages (process.py)."""
    global DEFAULT_STAGES
    GATES.clear(); GATE_BEHAVIOR.clear(); GATE_ABOUT.clear()
    for g in P.get("gates", []):
        GATES[g["id"]] = g["name"]
        GATE_BEHAVIOR[g["id"]] = g.get("behavior", "")
        GATE_ABOUT[g["id"]] = g.get("about", "")
    for k, b in (("", ""), ("soft", "soft"), ("hard", "hard")):
        GATES.setdefault(k, {"": "No gate", "soft": "Soft gate: warn and log", "hard": "Hard gate: hold until the goals are met"}[k])
        GATE_BEHAVIOR.setdefault(k, b)
    if P.get("stages"):
        DEFAULT_STAGES = tuple(n for n, _g in P["stages"])
        DEFAULT_STAGE_GATES.clear()
        DEFAULT_STAGE_GATES.update({n: g for n, g in P["stages"]})


class GateClosed(Exception):
    """The current stage has a hard gate with open goals, and no reason to override it was given."""

NOTE_ON = ("effort", "stage", "document", "version", "requirement", "section", "task", "deliverable")

# Goals the app can check from the features. Each maps to a key of the checks dict the app builds (see checks() in the
# UI): True met, False not met, None when the app cannot tell yet (shown as not checked).
AUTO = {
    "docs_added": "Customer documents added",
    "docs_reviewed": "Every customer document change reviewed",
    "reqs_reviewed": "Every submission requirement change reviewed",
    "structure_set": "Response structure set",
    "reqs_placed": "Every compliance requirement in a section",
    "sections_led": "Every section has a lead",
    "reqs_owned": "Every compliance requirement has an owner",
    "prove_clear": "Prove: nothing left to clear",
    "acr_approved": "Every acronym approved or rejected",
    "qa_run": "Drafts checked in QA/QC",
    "first_use_clean": "First use clean in every volume",
    "banned_clean": "No banned words left",
    "pages_ok": "Every volume within its page limit",
    "tasks_done": "Every task for this stage done",
    "deliverables_set": "Deliverables confirmed, each with an owner",           # 2.41.0
    "deliverables_ok": "No deliverable over its limit or changed without review",
}
DEFAULT_GOALS = {
    "Intake": ["docs_added", "reqs_reviewed", "structure_set", "sections_led"],
    "Author drafts": ["reqs_placed", "reqs_owned", "deliverables_set", "Author briefs sent to every section lead"],
    "Red team": ["qa_run", "Red team reviewers confirmed", "tasks_done"],
    "Red team recovery": ["Every red team comment has an owner", "docs_reviewed", "reqs_reviewed", "acr_approved", "pages_ok"],
    "Gold team": ["pages_ok", "first_use_clean", "banned_clean", "acr_approved", "prove_clear", "deliverables_ok"],
    "Gold team recovery": ["Every gold team comment has an owner", "docs_reviewed", "reqs_reviewed", "pages_ok", "first_use_clean"],
    "Final to pubs": ["pages_ok", "first_use_clean", "banned_clean", "deliverables_ok", "Files named as the customer requires", "Forms signed", "tasks_done"],
}
CUSTOM_GOALS = {}                    # 2.86.0: {stage name: [goal key or text]}: this PC's (or team's) defaults for new efforts
GOALS_FILE = "stage_goals.json"


def load_default_goals(config_dir):
    """2.86.0: the default gate goals for new efforts saved on this PC, over the built-in ones."""
    import json
    CUSTOM_GOALS.clear()
    try:
        with open(os.path.join(config_dir, GOALS_FILE), encoding="utf-8") as f:
            d = json.load(f)
        for k, v in (d.get("stages") or {}).items():
            if isinstance(v, list):
                CUSTOM_GOALS[k] = [str(x) for x in v if str(x).strip()]
    except (OSError, ValueError, AttributeError):
        pass
    return dict(CUSTOM_GOALS)


def save_default_goals(config_dir, stage, goals):
    """Save a stage's goals ([goal dict]) as the default for new efforts. Returns the keys saved."""
    import json
    keys = [g["auto"] if g.get("auto") else _clean(g.get("text", "")) for g in goals if g.get("auto") or _clean(g.get("text", ""))]
    path = os.path.join(config_dir, GOALS_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("stages", {})[stage] = keys
    os.makedirs(config_dir, exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(path + ".tmp", path)
    CUSTOM_GOALS[stage] = keys
    return keys


MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def _id():
    return uuid.uuid4().hex[:10]


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _who(who=None):
    return who or getpass.getuser()


def _clean(s):
    return " ".join((s or "").split())


# ------------------------------------------------------------------ dates
def parse_date(text):
    """'2026-12-15', '12/15/2026', 'December 15, 2026', 'Dec 15 2026' -> date, else None."""
    t = _clean(text).replace(".", "")
    if not t:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t), fmt).date()
        except ValueError:
            continue
    return None


def parse_time(text):
    """'2:00 p.m.', '14:00', '1600 hours', '2 PM' -> (hour, minute), else None."""
    t = _clean(text).lower().replace(".", "")
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", t)
    if m:
        h, mi = int(m.group(1)) % 12, int(m.group(2) or 0)
        return (h + (12 if m.group(3) == "pm" else 0), mi)
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", t)
    if m and int(m.group(1)) < 24:
        return (int(m.group(1)), int(m.group(2)))
    m = re.search(r"\b(\d{2})(\d{2})\s*(?:hours|hrs)\b", t)
    if m and int(m.group(1)) < 24:
        return (int(m.group(1)), int(m.group(2)))
    return None


ZONES = (("Mountain", "MT"), ("Eastern", "ET"), ("Central", "CT"), ("Pacific", "PT"), ("Alaska", "AKT"), ("Hawaii", "HT"))


def parse_due_text(text):
    """A due date as the customer wrote it ('December 15, 2026, 2:00 p.m. Mountain Time') -> (iso, zone) or (None, '')."""
    t = _clean(text)
    d = None
    m = re.search(r"\b[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|"
                  r"\b\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}\b", t)
    if m:
        d = parse_date(m.group(0))
    if d is None:
        return None, ""
    hm = parse_time(t) or (17, 0)
    zone = ""
    for long, short in ZONES:
        if re.search(r"\b" + long + r"\b", t, re.I):
            zone = short
            break
    else:
        z = re.search(r"\b(?-i:([ECMP])[SD]?T)\b", t)
        zone = (z.group(1) + "T") if z else ("local" if re.search(r"local time", t, re.I) else "")
    return datetime.datetime(d.year, d.month, d.day, *hm).isoformat(timespec="minutes"), zone


def countdown(due_iso, now=None):
    """(days, hours) from now to the due time; negative days when it has passed; None without a due time."""
    if not due_iso:
        return None
    try:
        due = datetime.datetime.fromisoformat(due_iso)
    except ValueError:
        return None
    now = now or datetime.datetime.now()
    secs = int((due - now).total_seconds())
    if secs < 0:
        return (secs // 86400, 0)                  # negative: the due time has passed
    return (secs // 86400, (secs % 86400) // 3600)


def countdown_text(due_iso, now=None):
    c = countdown(due_iso, now)
    if c is None:
        return ""
    d, h = c
    if d < 0:
        return "Due date passed"
    return f"{d} d  {h} h"


def due_text(due_iso, zone=""):
    """'Dec 15, 2026, 2:00 p.m. MT'."""
    if not due_iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(due_iso)
    except ValueError:
        return due_iso
    h = dt.hour % 12 or 12
    ap = "a.m." if dt.hour < 12 else "p.m."
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}, {h}:{dt.minute:02d} {ap}" + (f" {zone}" if zone else "")


def nice_date(text, today=None):
    """A date as written in a task ('2026-10-30', '10/30/2026') -> 'Oct 30' this year, 'Oct 30, 2027' otherwise."""
    d = parse_date(text)
    if d is None:
        return text or ""
    return f"{d.strftime('%b')} {d.day}" + ("" if d.year == (today or datetime.date.today()).year else f", {d.year}")


def parse_when(text, end_of_day=False):
    """2.93.0: 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM' (or any date parse_date reads) -> datetime, else None. A date alone is
    its start of day (its end with end_of_day)."""
    t = _clean(text)
    if not t:
        return None
    if "T" in t:
        try:
            return datetime.datetime.fromisoformat(t[:16])
        except ValueError:
            return None
    d = parse_date(t)
    return datetime.datetime.combine(d, datetime.time(23, 59) if end_of_day else datetime.time(0, 0)) if d else None


def when_text(text):
    """'2026-11-20T14:00' -> 'Nov 20, 2:00 p.m.'; '2026-11-20' -> 'Nov 20'."""
    w = parse_when(text)
    if w is None:
        return text or ""
    s = f"{w.strftime('%b')} {w.day}"
    if "T" in (text or ""):
        s += f", {w.hour % 12 or 12}:{w.minute:02d} {'a.m.' if w.hour < 12 else 'p.m.'}"
    return s


def short_date(iso):
    """'2026-10-26T09:14' or '2026-10-26' -> 'Oct 26'."""
    if not iso:
        return ""
    try:
        d = datetime.datetime.fromisoformat(iso[:16] if "T" in iso else iso)
    except ValueError:
        return iso
    return f"{d.strftime('%b')} {d.day}"


# ------------------------------------------------------------------ customer information (2.51.0)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?")
_ADDR = re.compile(r"\b\d{1,6}\s+(?:[A-Z][\w.]*\s+){1,5}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|"
                   r"Place|Pl|Parkway|Pkwy|Circle|Highway|Hwy|Suite|Building|Bldg)\b[^;\n]*?(?:\b[A-Z]{2}\s+\d{5}(?:-\d{4})?|$)", re.I)
INFO_KINDS = ("E-mail", "Phone", "Address", "Name or other")


def info_pieces(text):
    """[(kind, value)]: e-mails, phone numbers and street addresses found in the text; what is left (a name, an office)
    is one 'Name or other' piece."""
    out, rest = [], text
    for kind, rx in (("E-mail", _EMAIL), ("Address", _ADDR), ("Phone", _PHONE)):
        for m in rx.finditer(rest):
            out.append((kind, m.group(0).strip(" ,;.")))
        rest = rx.sub(" ", rest)
    left = " ".join(re.sub(r"\b(?:e-?mail|phone|tel|telephone|fax|address|contact)\s*:?", " ", rest, flags=re.I).split()).strip(" ,;:.-")
    if re.search(r"[A-Za-z]{2}", left):
        out.append(("Name or other", left))
    return out


# ------------------------------------------------------------------ the record
class Record:
    def __init__(self, folder):
        self.folder = folder
        self.data = {}
        self.load()

    @property
    def path(self):
        return os.path.join(self.folder, "record.json")

    def load(self):
        import workspace as W
        d = W.read_json(self.path, None) or {}
        extra = {k: v for k, v in d.items() if k not in ("v", "due", "zone", "opportunity", "stages", "stage", "timeline", "notes", "tasks")}
        extra.setdefault("customer_info", [])
        extra.setdefault("team", [])
        self.data = {**extra, "v": 1, "due": d.get("due", ""), "zone": d.get("zone", ""), "opportunity": d.get("opportunity", ""),
                     "stages": d.get("stages") or [], "stage": d.get("stage", ""), "timeline": d.get("timeline", []),
                     "notes": d.get("notes", []), "tasks": d.get("tasks", [])}
        if not self.data["stages"]:
            self.data["stages"] = [self._new_stage(n) for n in DEFAULT_STAGES]
            self.data["stage"] = self.data["stages"][0]["id"]
            self.data["stages"][0]["started"] = _now()
            if os.path.isdir(self.folder):           # 2.93.0: kept at once, so every reader sees the same stages (and ids)
                try:
                    self.save()
                except OSError:
                    pass
        return self

    def save(self):
        import workspace as W
        W.write_json(self.path, self.data)

    # ------------------------------------------------------------ basics
    def set_due(self, due_iso, zone="", who=None, zone_key=None):
        """2.92.0: zone_key is the submission's time zone (tzones key); when not given it is read from zone, the zone as
        the customer wrote it."""
        import tzones as TZ
        old = self.data["due"]
        self.data["due"], self.data["zone"] = due_iso or "", _clean(zone)
        self.data["zone_key"] = zone_key if zone_key is not None and (TZ.valid(zone_key) or zone_key == "") else TZ.guess(zone)
        if old != self.data["due"]:
            self.log("effort", ("Due date set to " + due_text(due_iso, zone)) if due_iso else "Due date cleared", who=who)
        self.save()

    def zone_key(self):
        """2.92.0: the submission's time zone key ('' when unknown)."""
        import tzones as TZ
        k = self.data.get("zone_key")
        return k if k and TZ.valid(k) else TZ.guess(self.data.get("zone", ""))

    def due_utc(self):
        """The due time in UTC (naive), or None without a due time or a known zone."""
        import tzones as TZ
        due, k = self.data.get("due", ""), self.zone_key()
        if not due or not k or len(due) <= 10:
            return None
        try:
            return TZ.to_utc(datetime.datetime.fromisoformat(due), k)
        except ValueError:
            return None

    # ------------------------------------------------------------ stages
    @staticmethod
    def _new_stage(name, planned=""):
        goals = []
        for g in CUSTOM_GOALS.get(name, DEFAULT_GOALS.get(name, [])):
            goals.append({"id": _id(), "text": AUTO.get(g, g), "auto": g if g in AUTO else "", "done": False, "by": "", "at": ""})
        return {"id": _id(), "name": name, "planned": planned, "started": "", "ended": "", "goals": goals,
                "gate": DEFAULT_STAGE_GATES.get(name, "")}

    @property
    def stages(self):
        return self.data["stages"]

    def stage(self, sid=None):
        sid = sid or self.data["stage"]
        return next((s for s in self.stages if s["id"] == sid), None)

    def index(self, sid=None):
        s = self.stage(sid)
        return self.stages.index(s) if s else -1

    def state_of(self, s):
        """'done', 'current' or 'ahead'."""
        i, cur = self.stages.index(s), self.index()
        return "current" if i == cur else "done" if i < cur else "ahead"

    def edit_stages(self, rows, who=None):
        """rows: [(id or None, name, planned)] in the new order. Existing ids keep their goals and dates; new rows get the
        team's default goals for that name. The current stage cannot be removed."""
        cur = self.data["stage"]
        old = {s["id"]: s for s in self.stages}
        new, names = [], []
        for row in rows:
            sid, name, planned = row[:3]
            planned_end = row[3] if len(row) > 3 else None       # 2.52.0: a planned end date too
            times = row[4:6] if len(row) > 5 else None           # 2.93.0: and the times they start and end
            name = _clean(name)
            if not name:
                continue
            if sid in old:
                s = old[sid]
                if s["name"] != name:
                    self.log("stage", f"Stage renamed: {s['name']} to {name}", who=who)
                s["name"], s["planned"] = name, _clean(planned)
            else:
                s = self._new_stage(name, _clean(planned))
                self.log("stage", f"Stage added: {name}", who=who)
            if planned_end is not None:
                s["planned_end"] = _clean(planned_end)
            if times is not None:
                s["planned_time"], s["planned_end_time"] = _clean(times[0]), _clean(times[1])
            new.append(s); names.append(s["id"])
        if cur not in names:
            raise ValueError("The current stage cannot be removed.")
        for sid, s in old.items():
            if sid not in names:
                self.log("stage", f"Stage removed: {s['name']}", who=who)
        self.data["stages"] = new
        self.save()
        return new

    def stage_timing(self, s=None, today=None):
        """2.52.0: the plan for a stage against today: {"start", "end", "days", "left", "over"} (dates or None; days
        planned, days left, days past the planned end). Nothing changes by itself: the stage moves only when the
        proposal manager moves it."""
        s = s or self.stage()
        today = today or datetime.date.today()
        a, b = parse_date(s.get("planned", "") or ""), parse_date(s.get("planned_end", "") or "")
        out = {"start": a, "end": b, "days": (b - a).days + 1 if a and b and b >= a else None, "left": None, "over": None}
        if b and self.state_of(s) == "current":
            d = (b - today).days
            out["left" if d >= 0 else "over"] = d if d >= 0 else -d
        return out

    # ------------------------------------------------------------ stage gates (2.63.0)
    def gate_id(self, s=None):
        """2.93.0: the gate chosen for the stage (one of the team's gates)."""
        s = s or self.stage()
        return s.get("gate", "") if s.get("gate", "") in GATES else ""

    def gate_of(self, s=None):
        """What the stage's gate does: '' (no hold), 'soft' or 'hard'."""
        return GATE_BEHAVIOR.get(self.gate_id(s), "")

    def set_gate(self, sid, mode, who=None):
        s = self.stage(sid)
        mode = mode if mode in GATES else ""
        if s is None or s.get("gate", "") == mode:
            return False
        s["gate"] = mode
        self.log("stage", f"Gate for {s['name']}: {GATES[mode].split(':')[0].lower()}", who=who)
        self.save()
        return True

    # ------------------------------------------------------------ 2.93.0 a stage's window and deadlines inside it
    def stage_window(self, s=None):
        """(start, end) datetimes of the stage's planned window: start at its planned date and time (00:00 when no
        time), end at its planned end date and time (23:59 when no time). None for a side not set."""
        s = s or self.stage()

        def at(d, t, default):
            dd = parse_date(d or "")
            if not dd:
                return None
            hm = t if t and len(t) == 5 else default
            return datetime.datetime.combine(dd, datetime.time(int(hm[:2]), int(hm[3:5])))
        return at(s.get("planned"), s.get("planned_time"), "00:00"), at(s.get("planned_end"), s.get("planned_end_time"), "23:59")

    def window_text(self, s=None):
        a, b = self.stage_window(s)
        f = lambda x: f"{x.strftime('%b')} {x.day}, {x.hour % 12 or 12}:{x.minute:02d} {'a.m.' if x.hour < 12 else 'p.m.'}"  # noqa: E731
        return (f"{f(a)} to {f(b)}" if a and b else f"from {f(a)}" if a else f"until {f(b)}" if b else "")

    def deadline_problem(self, sid, when):
        """'' when the deadline (a datetime, or a date: its end of day) falls inside the stage's planned window, else
        why not, in words the person reads."""
        s = self.stage(sid)
        if s is None or when is None:
            return ""
        if isinstance(when, datetime.date) and not isinstance(when, datetime.datetime):
            when = datetime.datetime.combine(when, datetime.time(23, 59))
        a, b = self.stage_window(s)
        if (a and when < a) or (b and when > b):
            return (f"{s['name']} runs {self.window_text(s)}; pick a time inside it, or change the stage's dates "
                    "(Edit stages...).")
        return ""

    def due_problem(self, sid, due):
        """'' when a deadline written as text ('YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM') fits the stage's dates, else why not."""
        if not due:
            return ""
        w = parse_when(due, end_of_day=True)
        return "The deadline was not understood." if w is None else self.deadline_problem(sid, w)

    def set_goal_deadline(self, sid, gid, due="", owner=None, who=None):
        """2.93.0: a goal's deadline (YYYY-MM-DDTHH:MM, or '' for none) and owner. Returns '' when saved, else why not."""
        s = self.stage(sid)
        g = next((x for x in s["goals"] if x["id"] == gid), None) if s else None
        if g is None:
            return "No such goal."
        if due:
            when = parse_when(due, end_of_day=True)
            if when is None:
                return "The deadline was not understood."
            why = self.deadline_problem(sid, when)
            if why:
                return why
        changed = []
        if (g.get("due", "") or "") != (due or ""):
            g["due"] = due or ""
            changed.append(f"due {due.replace('T', ' ')}" if due else "no deadline")
        if owner is not None and (g.get("owner", "") or "") != _clean(owner):
            g["owner"] = _clean(owner)
            changed.append(f"owner {g['owner'] or '(none)'}")
        if changed:
            self.log("stage", f"Goal in {s['name']}: {g['text'][:80]} ({', '.join(changed)})", who=who)
            self.save()
        return ""

    def gate_check(self, sid, checks=None):
        """What moving to stage sid meets at the current stage's gate: {"mode", "open": [goal texts], "forward",
        "blocked"}. Moving back to an earlier stage is never held."""
        to, frm = self.stage(sid), self.stage()
        forward = to is not None and self.stages.index(to) > self.stages.index(frm)
        open_ = [g["text"] for g in frm["goals"] if not self.goal_done(g, checks)]
        mode = self.gate_of(frm)
        return {"mode": mode, "open": open_, "forward": forward, "blocked": forward and mode == "hard" and bool(open_)}

    def move_to(self, sid, carry=(), who=None, planned=None, reason="", checks=None):
        """The proposal manager moves the effort to another stage. carry: ids of the left stage's open goals to copy.
        2.63.0: a hard gate with open goals holds the move (GateClosed) unless a reason is given; a soft or overridden
        gate is logged with the open goals and the reason."""
        to, frm = self.stage(sid), self.stage()
        if to is None or to is frm:
            return False
        gc = self.gate_check(sid, checks)
        reason = _clean(reason)
        if gc["blocked"] and not reason:
            raise GateClosed(f"{frm['name']} has a hard gate and {len(gc['open'])} open goal{'s' if len(gc['open']) != 1 else ''}. "
                             "Meet them, or override the gate with a reason.")
        if gc["forward"] and gc["mode"] and gc["open"]:
            n = len(gc["open"])
            self.log("gate", (f"Hard gate overridden at {frm['name']}" if gc["mode"] == "hard" else f"Soft gate passed at {frm['name']}")
                     + f" with {n} open goal{'s' if n != 1 else ''}: " + "; ".join(gc["open"])[:300]
                     + (f". Reason: {reason}" if reason else ""), who=who)
        now = _now()
        frm["ended"] = now
        to["started"], to["ended"] = now, ""
        if planned is not None:
            to["planned"] = _clean(planned)
        for g in frm["goals"]:
            if g["id"] in carry:
                to["goals"].append({"id": _id(), "text": g["text"], "auto": g["auto"], "done": False, "by": "", "at": "",
                                    "from": frm["name"]})
        self.data["stage"] = to["id"]
        n = len([g for g in frm["goals"] if g["id"] in carry])
        self.log("stage", f"Moved to {to['name']} from {frm['name']}" + (f"; {n} open goal{'s' if n != 1 else ''} carried over" if n else ""),
                 who=who)
        self.save()
        return True

    # ------------------------------------------------------------ goals
    def goal_done(self, g, checks=None):
        if g.get("auto") and checks is not None and checks.get(g["auto"]) is not None:
            return bool(checks[g["auto"]])
        return bool(g.get("done"))

    def goal_progress(self, sid=None, checks=None):
        s = self.stage(sid)
        if s is None:
            return 0, 0
        return sum(1 for g in s["goals"] if self.goal_done(g, checks)), len(s["goals"])

    def set_goal(self, sid, gid, done, who=None):
        s = self.stage(sid)
        g = next((x for x in s["goals"] if x["id"] == gid), None) if s else None
        if g is None:
            return False
        g["done"], g["by"], g["at"] = bool(done), (_who(who) if done else ""), (_now() if done else "")
        if done:
            self.log("stage", f"Goal met in {s['name']}: {g['text']}", who=who)
        self.save()
        return True

    def add_goal(self, sid, text, auto="", who=None):
        s = self.stage(sid)
        text = _clean(text) or AUTO.get(auto, "")
        if s is None or not text:
            return None
        g = {"id": _id(), "text": text, "auto": auto if auto in AUTO else "", "done": False, "by": "", "at": ""}
        s["goals"].append(g)
        self.save()
        return g["id"]

    def edit_goal(self, sid, gid, text, who=None):
        """2.49.0: change a goal's wording."""
        s = self.stage(sid)
        g = next((x for x in s["goals"] if x["id"] == gid), None) if s else None
        text = _clean(text)
        if g is None or not text or text == g["text"]:
            return False
        old, g["text"] = g["text"], text
        self.log("stage", f"Goal changed in {s['name']}: {old} > {text}", who=who)
        self.save()
        return True

    def make_manual(self, sid, gid, who=None):
        """2.86.0: the app stops checking this goal; a person ticks it (its wording stays)."""
        s = self.stage(sid)
        g = next((x for x in s["goals"] if x["id"] == gid), None) if s else None
        if g is None or not g.get("auto"):
            return False
        g["auto"] = ""
        self.log("stage", f"Goal now ticked by hand in {s['name']}: {g['text']}", who=who)
        self.save()
        return True

    def remove_goal(self, sid, gid):
        s = self.stage(sid)
        if s is None:
            return False
        n = len(s["goals"])
        s["goals"] = [g for g in s["goals"] if g["id"] != gid]
        self.save()
        return len(s["goals"]) < n

    # ------------------------------------------------------------ timeline
    def log(self, kind, text, ref=None, who=None, at=None, save=False):
        e = {"at": at or _now(), "who": _who(who), "kind": kind, "text": _clean(text), "stage": self.data.get("stage", "")}
        if ref:
            e["ref"] = ref
        self.data["timeline"].append(e)
        if save:
            self.save()
        return e

    def events(self, since=None, kinds=None, limit=None):
        """Newest first."""
        ev = [(i, e) for i, e in enumerate(self.data["timeline"]) if (not since or e["at"] >= since) and (not kinds or e["kind"] in kinds)]
        ev = [e for _i, e in sorted(ev, key=lambda x: (x[1]["at"], x[0]), reverse=True)]      # same minute: last logged first
        return ev[:limit] if limit else ev

    # ------------------------------------------------------------ notes
    def add_note(self, text, on="effort", on_id="", label="", question=False, who=None):
        text = text.strip() if text else ""
        if not text:
            return None
        n = {"id": _id(), "at": _now(), "who": _who(who), "on": on if on in NOTE_ON else "effort", "on_id": on_id,
             "label": _clean(label), "text": text, "question": bool(question), "resolved": "", "stage": self.data["stage"]}
        self.data["notes"].append(n)
        self.log("note", ("Question" if question else "Note") + (f" on {n['label']}" if n["label"] else "") + f": {_clean(text)[:140]}",
                 ref={"note": n["id"]}, who=who)
        self.save()
        return n["id"]

    def resolve_note(self, nid, answer="", who=None):
        n = next((x for x in self.data["notes"] if x["id"] == nid), None)
        if n is None:
            return False
        n["resolved"] = f"{datetime.date.today().isoformat()} {_who(who)}"
        if answer.strip():
            n["answer"] = answer.strip()
        self.log("note", f"Resolved: {_clean(n['text'])[:100]}" + (f" ({_clean(answer)[:80]})" if answer.strip() else ""), ref={"note": nid}, who=who)
        self.save()
        return True

    def update_note(self, nid, who=None, **fields):
        """2.49.0: change a note's text, make it a question or a note, or assign it to a person (assignee)."""
        n = next((x for x in self.data["notes"] if x["id"] == nid), None)
        if n is None:
            return False
        changed = []
        for k, v in fields.items():
            if k == "text":
                v = (v or "").strip()
                if not v:
                    continue
            elif k == "assignee":
                v = _clean(v)
            elif k == "question":
                v = bool(v)
            else:
                continue
            if n.get(k, "" if k != "question" else False) != v:
                n[k] = v
                changed.append(k)
        if "assignee" in changed:
            self.log("assign", (("Question" if n["question"] else "Note") + f" assigned to {n['assignee'] or 'nobody'}: "
                                + _clean(n["text"])[:100]), ref={"note": nid}, who=who)
        if "text" in changed:
            self.log("note", f"{'Question' if n['question'] else 'Note'} changed: {_clean(n['text'])[:120]}", ref={"note": nid}, who=who)
        if changed:
            self.save()
        return bool(changed)

    def remove_note(self, nid):
        n = len(self.data["notes"])
        self.data["notes"] = [x for x in self.data["notes"] if x["id"] != nid]
        self.save()
        return len(self.data["notes"]) < n

    def notes(self, on=None, on_id=None, open_only=False):
        out = [n for n in self.data["notes"] if (on is None or n["on"] == on) and (on_id is None or n["on_id"] == on_id)
               and (not open_only or (n["question"] and not n["resolved"]))]
        return sorted(out, key=lambda n: n["at"], reverse=True)

    def open_questions(self, assignee=None):
        qs = self.notes(open_only=True)
        return qs if assignee is None else [q for q in qs if q.get("assignee", "") == assignee]

    def calendar(self, first=None, last=None, extra=(), mine=""):
        """2.49.0: what falls on each day: {date: [(kind, text)]}. kind: due, stage, task, done, event. extra: more
        (date, kind, text) from elsewhere (questions due from the customer documents). Between first and last when given."""
        out = {}

        def put(d, kind, text):
            if d and (first is None or d >= first) and (last is None or d <= last):
                out.setdefault(d, []).append((kind, text))
        due = self.data.get("due", "")
        if due:
            hm = due[11:16] if len(due) > 10 else ""
            if hm[:2].isdigit() and hm[3:5].isdigit():
                h, mi = int(hm[:2]), int(hm[3:5])
                hm = f"{h % 12 or 12}:{mi:02d} {'a.m.' if h < 12 else 'p.m.'}"
            put(parse_date(due[:10]), "due", "Proposal due" + (f" {hm}" if hm else ""))
        for s in self.stages:
            if s.get("planned"):
                put(parse_date(s["planned"]), "stage", f"{s['name']} (planned start)" if s.get("planned_end") else f"{s['name']} (planned)")
            if s.get("planned_end"):
                put(parse_date(s["planned_end"]), "stage", f"{s['name']} (planned end)")
            if s.get("started"):
                put(parse_date(s["started"][:10]), "stage", f"{s['name']} started")
        for t in self.data.get("tasks", []):
            if t.get("due"):
                hm = when_text(t["due"]).split(", ", 1)[1] + " " if "T" in t["due"] else ""
                put(parse_date(t["due"][:10]), "done" if t["status"] == "Done" else "task",
                    hm + t["title"] + (f" ({t['owner']})" if t.get("owner") else ""))
        for s in self.stages:                                   # 2.93.0: gate goals with a deadline
            for g in s.get("goals", []):
                if g.get("due"):
                    hm = when_text(g["due"]).split(", ", 1)[1] + " " if "T" in g["due"] else ""
                    put(parse_date(g["due"][:10]), "done" if g.get("done") else "task",
                        f"{hm}Gate goal ({s['name']}): {g['text']}" + (f" ({g['owner']})" if g.get("owner") else ""))
        import effortcal as EC
        for e in self.data.get("events", []):                 # 2.88.0: reviews, meetings, orals, milestones; 2.92.0: due dates
            when = EC.entry_times(e, mine)
            kind = "questions" if e["kind"] == "Questions due" else "deadline" if e["kind"] == "Due" else "meeting"
            put(parse_date(e["date"]), kind, ((("Due " if kind == "deadline" else "") + when + " ") if when else ("Due: " if kind == "deadline" else ""))
                + e["title"] + (f" ({e['location']})" if e.get("location") else ""))
        for e in self.data.get("timeline", []):
            if e["kind"] in ("document", "stage", "deliverable", "assign") and e.get("at") and not e["text"].startswith("Goal "):
                put(parse_date(e["at"][:10]), "event", e["text"][:80])
        for d, kind, text in extra:
            put(d, kind, text)
        return out

    # ------------------------------------------------------------ the team (2.52.0)
    def team(self):
        """[{name, role}]: the people on this effort, offered wherever a lead, author or owner is picked."""
        return list(self.data.get("team", []))

    def add_member(self, name, role="", who=None):
        name = _clean(name)
        if not name:
            return False
        lst = self.data.setdefault("team", [])
        if any(m["name"].casefold() == name.casefold() for m in lst):
            return False
        lst.append({"name": name, "role": _clean(role)})
        self.log("assign", f"Team: {name} added" + (f" ({_clean(role)})" if role else ""), who=who)
        self.save()
        return True

    def set_role(self, name, role, who=None):
        """2.93.0: one person's role on this effort (added to the team when missing). True when it changed."""
        name, role = _clean(name), _clean(role)
        if not name:
            return False
        lst = self.data.setdefault("team", [])
        m = next((x for x in lst if x["name"].casefold() == name.casefold()), None)
        if m is None:
            lst.append({"name": name, "role": role})
        elif m.get("role", "") == role:
            return False
        else:
            m["role"] = role
        self.log("assign", f"Role: {name} is {role}" if role else f"Role: {name} has no role", who=who)
        self.save()
        return True

    def role_of(self, name):
        m = next((x for x in self.data.get("team", []) if x["name"].casefold() == (name or "").casefold()), None)
        return m.get("role", "") if m else ""

    def set_team(self, rows, who=None):
        """rows: [(name, role)] in order; replaces the list."""
        new, seen = [], set()
        for name, role in rows:
            name = _clean(name)
            if name and name.casefold() not in seen:
                seen.add(name.casefold()); new.append({"name": name, "role": _clean(role)})
        old = [m["name"] for m in self.data.get("team", [])]
        self.data["team"] = new
        if old != [m["name"] for m in new]:
            self.log("assign", f"Team: {len(new)} people", who=who)
        self.save()
        return new

    # ------------------------------------------------------------ customer information (2.51.0)
    def customer_info(self):
        return list(self.data.get("customer_info", []))

    def add_customer_info(self, text, source="", who=None):
        """Names, e-mails, phone numbers, addresses picked from the customer documents. Each piece is filed by kind."""
        text = " ".join((text or "").split())
        if not text:
            return []
        lst = self.data.setdefault("customer_info", [])
        have = {(c["kind"], c["value"].casefold()) for c in lst}
        added = []
        for kind, value in info_pieces(text):
            if (kind, value.casefold()) in have:
                continue
            c = {"id": _id(), "kind": kind, "value": value, "source": _clean(source), "at": _now(), "who": _who(who)}
            lst.append(c); have.add((kind, value.casefold())); added.append(c)
        if added:
            self.log("customer", f"Customer information added: {', '.join(c['kind'].lower() for c in added)}", who=who)
            self.save()
        return added

    def remove_customer_info(self, cid):
        lst = self.data.get("customer_info", [])
        n = len(lst)
        self.data["customer_info"] = [c for c in lst if c["id"] != cid]
        self.save()
        return len(self.data["customer_info"]) < n

    # ------------------------------------------------------------ tasks
    def add_task(self, title, owner="", due="", stage="", about="", notes="", who=None):
        title = _clean(title)
        if not title:
            return None
        t = {"id": _id(), "title": title, "owner": _clean(owner), "due": _clean(due), "stage": stage or self.data["stage"],
             "about": _clean(about), "notes": (notes or "").strip(), "status": "Not started", "created": _now(),
             "by": _who(who), "done": ""}
        self.data["tasks"].append(t)
        self.log("task", f"Task added: {title}" + (f" (owner {t['owner']}" + (f", due {t['due']}" if t["due"] else "") + ")" if t["owner"] else ""),
                 ref={"task": t["id"]}, who=who)
        self.save()
        return t["id"]

    def task(self, tid):
        return next((t for t in self.data["tasks"] if t["id"] == tid), None)

    def update_task(self, tid, who=None, **fields):
        t = self.task(tid)
        if t is None:
            return False
        changes = []
        for k, v in fields.items():
            if k not in ("title", "owner", "due", "stage", "about", "notes", "status"):
                continue
            v = v.strip() if k == "notes" else _clean(v)
            if k == "status" and v not in TASK_STATUS:
                continue
            if t.get(k) != v:
                changes.append(k)
                t[k] = v
        if "status" in changes:
            t["done"] = _now() if t["status"] == "Done" else ""
            self.log("task", f"Task {t['status'].lower()}: {t['title']}" + (f" ({t['owner']})" if t["owner"] else ""), ref={"task": tid}, who=who)
        if "owner" in changes:
            self.log("assign", f"Task assigned to {t['owner'] or 'nobody'}: {t['title']}", ref={"task": tid}, who=who)
        if changes:
            self.save()
        return bool(changes)

    def remove_task(self, tid, who=None):
        t = self.task(tid)
        if t is None:
            return False
        self.data["tasks"].remove(t)
        self.log("task", f"Task removed: {t['title']}", who=who)
        self.save()
        return True

    def tasks(self, owner=None, stage=None, open_only=False):
        out = [t for t in self.data["tasks"] if (owner is None or t["owner"] == owner) and (stage is None or t["stage"] == stage)
               and (not open_only or t["status"] != "Done")]
        return sorted(out, key=lambda t: (t["status"] == "Done", t["due"] or "9999", t["created"]))

    def task_overdue(self, t, today=None):
        w = parse_when(t.get("due", ""), end_of_day=True)
        if not w or t["status"] == "Done":
            return False
        if today is not None or "T" not in t.get("due", ""):
            return w.date() < (today or datetime.date.today())
        return w < datetime.datetime.now()

    def deadlines_outside(self):
        """2.93.0: open goals and tasks whose deadline falls outside their stage's dates: [{"kind", "id", "stage", "text",
        "due"}] (the stage's dates were changed after the deadline was set)."""
        out = []
        for s in self.stages:
            for g in s.get("goals", []):
                if g.get("due") and not g.get("done") and self.deadline_problem(s["id"], parse_when(g["due"], True)):
                    out.append({"kind": "goal", "id": g["id"], "stage": s["name"], "text": g["text"], "due": g["due"]})
            for t in self.data.get("tasks", []):
                if t.get("stage") == s["id"] and t.get("due") and t.get("status") != "Done" \
                        and self.deadline_problem(s["id"], parse_when(t["due"], True)):
                    out.append({"kind": "task", "id": t["id"], "stage": s["name"], "text": t["title"], "due": t["due"]})
        return out
