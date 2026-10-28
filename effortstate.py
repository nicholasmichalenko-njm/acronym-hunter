"""The open effort's state outside any window (2.62.0): its record (stages, goals, tasks, notes), customer document
library and submission requirements, acronym list, last QA/QC report, volumes and compliance matrix, read from the
effort's files. Both programs use it: the classic window for its gate goal checks, the Qt edition for Effort home and
the effort dashboard. Plain counts and dates from rules; nothing leaves the PC.
"""
import datetime
import diag
import effortrec as R

PROVE_CATS = ("unused", "nosection", "ctx", "noowner", "changed", "customer", "all")


def prove_items(M, cat):
    """The sentences in one Prove category (the classic Prove window and the gate goal checks)."""
    import compliance as C
    import setupdoc as SD
    if M is None:
        return []
    if cat == "unused":
        return [it for it in M.items if not it["decision"]]
    if cat == "nosection":
        return [it for it in M.items if it["decision"] in ("Keep", "Context") and not it.get("map")]
    if cat == "ctx":
        bad = {it["id"] for it, _w in C.context_problems(M.items) if not _w.startswith("placed in")}
        return [it for it in M.items if it["id"] in bad]
    if cat == "noowner":
        return [it for it in M.items if it["decision"] == "Keep" and not SD.owner_of(M, it)]
    if cat == "changed":
        return [it for it in M.items if it.get("new") == "New in latest read"]
    if cat == "customer":
        return [it for it in M.items if it["decision"] == "Customer"]
    return [it for it in M.items if it["decision"] == "Keep"]


def checks_of(rec, M=None, lib=None, rows=(), L=None, report=None, volumes=(), prove=None):
    """What the app can tell about the gate goals: {auto goal key: True, False or None (cannot tell yet)}."""
    c = {k: None for k in R.AUTO}
    prove = prove or (lambda cat: prove_items(M, cat))
    try:
        if lib is not None:
            c["docs_added"] = bool(lib.docs)
            if lib.docs:
                c["docs_reviewed"] = not lib.counts()["unreviewed"]
        if rows:
            c["reqs_reviewed"] = not any(x["to_review"] for x in rows)
        if M is not None and M.items:
            import setupdoc as SD
            cnt = M.counts()
            c["structure_set"] = bool(M.outline)
            c["reqs_placed"] = cnt["Keep"] > 0 and not cnt["needs_home"]
            keeps = [it for it in M.items if it["decision"] == "Keep"]
            c["reqs_owned"] = bool(keeps) and all(SD.owner_of(M, it) for it in keeps)
            tops = [o for o in M.outline if o.get("level", 1) <= 1] if M.outline else []
            if tops:
                import compliance as C
                c["sections_led"] = all(SD.section_people(M, C.outline_label(o))["lead"] for o in tops)
            try:
                c["prove_clear"] = all(not prove(k) for k in ("unused", "nosection", "ctx", "noowner"))
            except Exception:
                diag.swallowed()
        if L is not None and L.rows:
            c["acr_approved"] = all(x["Status"] in ("Approved", "Rejected") for x in L.rows.values())
        c["qa_run"] = bool(report) or None
        if report:
            s = report.get("summary", {})
            c["first_use_clean"] = not s.get("first_use_problems")
            if s.get("banned_checked"):
                c["banned_clean"] = not s.get("banned", {}).get("bad", 0)
            if report.get("pages"):
                c["pages_ok"] = not any(p["level"] == "bad" for p in report["pages"])
        if rec is not None:
            c["tasks_done"] = not rec.tasks(stage=rec.data["stage"], open_only=True)
            import deliverables as DL
            if DL.items(rec):
                sm = DL.summary(rec, rows, lib, volumes)
                c["deliverables_set"] = not sm["noowner"] and not sm["suggested"]
                c["deliverables_ok"] = not sm["over"] and not sm["changed"]
    except Exception:
        diag.swallowed()
    return c


def people_of(rec, M=None):
    """Everyone named in the effort: the team first (in its order), then section leads and contributors, requirement
    owners, task owners and question assignees."""
    names = set()
    if M is not None:
        try:
            import setupdoc as SD
            names.update(SD.people(M))
        except Exception:
            diag.swallowed()
    team = []
    if rec is not None:
        names.update(t["owner"] for t in rec.data["tasks"] if t["owner"])
        names.update(n["assignee"] for n in rec.data["notes"] if n.get("assignee"))
        team = [m["name"] for m in rec.team()]
    return team + sorted((n for n in names if n and n not in team), key=str.casefold)


def cal_extra_of(rec, rows):
    """Dates from the customer documents: questions due, and the due date when the effort has none of its own."""
    out = []
    try:
        import subreq as SR
        sm = SR.summary(rows or [])
        q = sm.get("questions_due")
        if q:
            d = R.parse_date(q["value"].split(" at ")[0]) or R.parse_date(",".join(q["value"].split(",")[:2]))
            out.append((d, "questions", "Questions due to the customer"))
        if sm.get("due") and rec is not None and not rec.data.get("due"):
            v = sm["due"]["value"]
            out.append((R.parse_date(",".join(v.split(",")[:2])) or R.parse_date(v.split(" at ")[0]), "due", "Proposal due"))
    except Exception:
        diag.swallowed()
    return [x for x in out if x[0]]


def coverage_by_volume(M):
    """[{"volume", "sections", "reqs", "owned", "context"}] for each volume of the response (the volumes decided in
    Structure), then a "Not in a section" row for compliance requirements and context with no section yet."""
    import setupdoc as SD
    if M is None:
        return []
    vos = SD.volume_of_sections(M)
    order = []
    for lab in vos:
        v = vos[lab] or "(no volume)"
        if v not in order:
            order.append(v)
    rows = {v: {"volume": v, "sections": 0, "reqs": 0, "owned": 0, "context": 0} for v in order}
    for lab, v in vos.items():
        rows[v or "(no volume)"]["sections"] += 1
    loose = {"volume": "Not in a section", "sections": 0, "reqs": 0, "owned": 0, "context": 0}
    for it in M.items:
        if it["decision"] not in ("Keep", "Context"):
            continue
        secs = SD.item_sections(M, it)
        vols = list(dict.fromkeys((vos.get(s) or "(no volume)") for s in secs if s in vos))
        targets = [rows[v] for v in vols if v in rows] or ([loose] if not (it["decision"] == "Context" and it.get("context_for")) else [])
        for r in targets:
            if it["decision"] == "Keep":
                r["reqs"] += 1
                r["owned"] += bool(SD.owner_of(M, it))
            else:
                r["context"] += 1
    out = list(rows.values())
    if loose["reqs"] or loose["context"]:
        out.append(loose)
    return out


def stage_plan(rec, today=None, checks=None):
    """[{"name", "state", "start", "end", "days_to_start", "left", "over", "late_start", "goals_met", "goals"}] for every
    stage: when it is planned, how many days to its start (stages ahead), days left or past plan (the current one), and
    a stage ahead whose planned start has passed; gate goals met (the app's checks count for the current stage)."""
    today = today or datetime.date.today()
    out = []
    for s in rec.stages:
        st = rec.state_of(s)
        tm = rec.stage_timing(s, today=today)
        start = tm["start"] or (R.parse_date(s["started"][:10]) if s.get("started") else None)
        d2s = (tm["start"] - today).days if st == "ahead" and tm["start"] else None
        met, total = rec.goal_progress(s["id"], checks=checks if st == "current" else None)
        out.append({"id": s["id"], "name": s["name"], "state": st, "start": tm["start"], "end": tm["end"],
                    "started": R.parse_date(s["started"][:10]) if s.get("started") else None,
                    "ended": R.parse_date(s["ended"][:10]) if s.get("ended") else None,
                    "days_to_start": d2s, "left": tm["left"], "over": tm["over"],
                    "late_start": st == "ahead" and d2s is not None and d2s < 0, "first": start,
                    "goals_met": met, "goals": total})
    return out


class State:
    """The open effort, read from its files. Cheap to make again after a change; nothing is held open."""

    def __init__(self, ws, effort_path="", M=None):
        self.ws, self.effort_path, self.M = ws, effort_path, M
        self.rec = R.Record(ws.root)
        self.lib = self.reg = None
        self.rows = []
        try:
            import docversions as DV
            import subreq as SR
            self.lib = DV.Library(ws.p("documents")).load()
            self.reg = SR.Register(self.lib)
            self.rows = self.reg.rows()
        except Exception:
            diag.swallowed()
        self._L = None
        v = ws.get("volumes", []) or []
        self.volumes = [x for x in v if isinstance(x, dict) and x.get("name")]
        s = ws.load_session() or {}
        self.report = s.get("volume_report") or None

    @property
    def L(self):
        """The effort's acronym list (read on first use)."""
        if self._L is None and self.effort_path:
            try:
                import effort as E
                self._L = E.EffortList(self.effort_path).load()
            except Exception:
                diag.swallowed()
        return self._L

    def checks(self):
        return checks_of(self.rec, self.M, self.lib, self.rows, self.L, self.report, self.volumes)

    def people(self):
        return people_of(self.rec, self.M)

    def cal_extra(self):
        return cal_extra_of(self.rec, self.rows)

    def calendar(self, first=None, last=None):
        return self.rec.calendar(first=first, last=last, extra=self.cal_extra())

    def acronyms(self):
        """{"total", "Approved", "Proposed", "Needs author", "Rejected"} from the effort's acronym list."""
        out = {"total": 0, "Approved": 0, "Proposed": 0, "Needs author": 0, "Rejected": 0}
        L = self.L
        for r in (L.rows.values() if L is not None else []):
            out["total"] += 1
            out[r.get("Status") or "Proposed"] = out.get(r.get("Status") or "Proposed", 0) + 1
        return out

    def qa(self):
        """The last QA/QC check of the drafts: None when it has not run; else volumes, first-use problems, banned words
        (banned and avoid), pages over their limit."""
        rep = self.report
        if not rep:
            return None
        s = rep.get("summary", {})
        b = s.get("banned", {}) or {}
        return {"volumes": s.get("volumes", 0), "first_use": s.get("first_use_problems", 0), "missing": s.get("missing", 0),
                "not_approved": s.get("not_approved", 0), "banned_checked": bool(s.get("banned_checked")),
                "banned": b.get("bad", 0), "avoid": b.get("warn", 0),
                "pages_over": sum(1 for p in rep.get("pages") or [] if p.get("level") == "bad")}

    def past_due(self, today=None):
        """[(kind, text, when)]: late tasks, a current stage past its planned end, stages that should have started."""
        today = today or datetime.date.today()
        r, out = self.rec, []
        for t in r.tasks(open_only=True):
            if r.task_overdue(t, today):
                d = R.parse_date(t["due"])
                out.append(("task", t["title"] + (f" ({t['owner']})" if t["owner"] else ""), d))
        for s in stage_plan(r, today):
            if s["state"] == "current" and s["over"]:
                out.append(("stage", f"{s['name']} is {s['over']} day{'s' if s['over'] != 1 else ''} past its planned end", s["end"]))
            if s["late_start"]:
                out.append(("stage", f"{s['name']} was planned to start {R.short_date(s['start'].isoformat())}", s["start"]))
        q = next((x for x in self.cal_extra() if x[1] == "questions"), None)
        if q and q[0] < today and r.open_questions():
            out.append(("questions", f"Questions were due to the customer {R.short_date(q[0].isoformat())}; "
                                     f"{len(r.open_questions())} still open here", q[0]))
        return sorted(out, key=lambda x: (x[2] or today))

    def dashboard(self, today=None):
        """Everything the effort dashboard shows, as plain numbers and lists."""
        today = today or datetime.date.today()
        r, M = self.rec, self.M
        checks = self.checks()
        met, total = r.goal_progress(checks=checks)
        due = r.data.get("due", "")
        due_date = R.parse_date(due[:10]) if due else None
        if due_date is None:
            x = next((d for d, k, _t in self.cal_extra() if k == "due"), None)
            due_date = x
        out = {"today": today, "stage": r.stage()["name"], "goals_met": met, "goals": total,
               "due": R.due_text(due, r.data.get("zone", "")) if due else (R.short_date(due_date.isoformat()) if due_date else ""),
               "days_to_due": (due_date - today).days if due_date else None, "due_date": due_date,
               "stages": stage_plan(r, today, checks), "questions": len(r.open_questions()),
               "questions_unassigned": sum(1 for q in r.open_questions() if not q.get("assignee")),
               "tasks_open": len(r.tasks(open_only=True)),
               "tasks_late": sum(1 for t in r.tasks(open_only=True) if r.task_overdue(t, today)),
               "past_due": self.past_due(today), "acronyms": self.acronyms(), "qa": self.qa(),
               "to_review": (self.lib.counts()["unreviewed"] if self.lib is not None and self.lib.docs else 0)
               + sum(1 for x in self.rows if x.get("to_review"))}
        if M is not None and M.items:
            import compliance as C
            import setupdoc as SD
            pg = C.progress(M.items)
            keeps = [it for it in M.items if it["decision"] == "Keep"]
            out["reqs"] = {"sentences": pg["total"], "decided": pg["decided"], "pct": pg["pct"], "reqs": len(keeps),
                           "placed": sum(1 for it in keeps if it.get("map")),
                           "owned": sum(1 for it in keeps if SD.owner_of(M, it)),
                           "context": pg["Context"], "customer": pg.get("Customer", 0), "dropped": pg["Drop"],
                           "undecided": pg["total"] - pg["decided"]}
            out["volumes"] = coverage_by_volume(M)
        else:
            out["reqs"], out["volumes"] = None, []
        import setupdoc as SD
        out["people"] = []
        for p in self.people():
            op = r.tasks(owner=p, open_only=True)
            out["people"].append({"person": p, "sections": len(SD.sections_of(M, p)) if M is not None else 0,
                                  "reqs": sum(1 for it in M.items if it["decision"] == "Keep" and p in SD.owners_list(M, it)) if M is not None else 0,
                                  "tasks": len(op), "late": sum(1 for t in op if r.task_overdue(t, today)),
                                  "questions": len(r.open_questions(assignee=p))})
        return out
