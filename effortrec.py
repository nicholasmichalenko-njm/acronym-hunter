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
        self.data = {**extra, "v": 1, "due": d.get("due", ""), "zone": d.get("zone", ""), "opportunity": d.get("opportunity", ""),
                     "stages": d.get("stages") or [], "stage": d.get("stage", ""), "timeline": d.get("timeline", []),
                     "notes": d.get("notes", []), "tasks": d.get("tasks", [])}
        if not self.data["stages"]:
            self.data["stages"] = [self._new_stage(n) for n in DEFAULT_STAGES]
            self.data["stage"] = self.data["stages"][0]["id"]
            self.data["stages"][0]["started"] = _now()
        return self

    def save(self):
        import workspace as W
        W.write_json(self.path, self.data)

    # ------------------------------------------------------------ basics
    def set_due(self, due_iso, zone="", who=None):
        old = self.data["due"]
        self.data["due"], self.data["zone"] = due_iso or "", _clean(zone)
        if old != self.data["due"]:
            self.log("effort", ("Due date set to " + due_text(due_iso, zone)) if due_iso else "Due date cleared", who=who)
        self.save()

    # ------------------------------------------------------------ stages
    @staticmethod
    def _new_stage(name, planned=""):
        goals = []
        for g in DEFAULT_GOALS.get(name, []):
            goals.append({"id": _id(), "text": AUTO.get(g, g), "auto": g if g in AUTO else "", "done": False, "by": "", "at": ""})
        return {"id": _id(), "name": name, "planned": planned, "started": "", "ended": "", "goals": goals}

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
        for sid, name, planned in rows:
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
            new.append(s); names.append(s["id"])
        if cur not in names:
            raise ValueError("The current stage cannot be removed.")
        for sid, s in old.items():
            if sid not in names:
                self.log("stage", f"Stage removed: {s['name']}", who=who)
        self.data["stages"] = new
        self.save()
        return new

    def move_to(self, sid, carry=(), who=None, planned=None):
        """The proposal manager moves the effort to another stage. carry: ids of the left stage's open goals to copy."""
        to, frm = self.stage(sid), self.stage()
        if to is None or to is frm:
            return False
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

    def calendar(self, first=None, last=None, extra=()):
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
                put(parse_date(s["planned"]), "stage", f"{s['name']} (planned)")
            if s.get("started"):
                put(parse_date(s["started"][:10]), "stage", f"{s['name']} started")
        for t in self.data.get("tasks", []):
            if t.get("due"):
                put(parse_date(t["due"]), "done" if t["status"] == "Done" else "task",
                    t["title"] + (f" ({t['owner']})" if t.get("owner") else ""))
        for e in self.data.get("timeline", []):
            if e["kind"] in ("document", "stage", "deliverable", "assign") and e.get("at") and not e["text"].startswith("Goal "):
                put(parse_date(e["at"][:10]), "event", e["text"][:80])
        for d, kind, text in extra:
            put(d, kind, text)
        return out

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
        d = parse_date(t.get("due", ""))
        return bool(d) and t["status"] != "Done" and d < (today or datetime.date.today())
