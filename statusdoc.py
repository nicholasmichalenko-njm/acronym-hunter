"""Effort status report (2.40.0): "Where are we?" in a Word file the proposal manager can hand to leadership, and the
effort summary at the end (the same report with the complete history).

build(snap, path, final=False) writes it from a snapshot (a plain dict the app gathers, see EffortRecordMixin.
status_snapshot), so the report can be made and tested without the screens:
1. Effort, client, numbers, due date and the days and hours left; the date and who made it.
2. The stage track: done, current, ahead, with dates.
3. Tiles: gate goals met, requirements placed, open questions, tasks late, changes to review.
4. Where we are: the current stage, what is done, in progress and left (its gate goals and tasks).
5. Open questions and the proposal manager's notes.
6. Projected timeline: the planned stage dates and the due date; 2.49.0: a month calendar (this month to the due date).
7. People and assignments: sections, compliance requirements and open tasks per person; requirements nobody owns.
8. What changed: customer documents, requirement changes and stage moves since the current stage began (or all of it).
9. Submission requirements: due date, page limits, format, files, and the changes not reviewed yet.
10. Each stage: goals met and left, dates.
11. Customer documents and their versions.
12. Effort summary only: the complete timeline.
Rules only (No AI); nothing leaves the PC.
"""
import datetime
import docxw

NAVY, GREEN, AMBER, RED, GRAY, INK = "1E3A8A", "15803D", "B45309", "B91C1C", "64748B", "0F172A"
FILL = {"done": "DCFCE7", "current": "1E3A8A", "ahead": "E2E8F0"}
TEXT = {"done": "14532D", "current": "FFFFFF", "ahead": "334155"}
PAGE_W = 9360          # 6.5 inches between 1-inch margins, in twentieths of a point


def _w(n, total=PAGE_W):
    base = total // n
    return [base] * (n - 1) + [total - base * (n - 1)]


def _head(d, text):
    d.heading(text, 2)


def build(snap, path, final=False):
    d = docxw.Doc()
    s = snap
    gen = s.get("generated") or datetime.datetime.now().strftime("%b %d, %Y, %I:%M %p").replace(" 0", " ")
    kind = "EFFORT SUMMARY" if final else "EFFORT STATUS"
    d.rich([(f"{kind}  |  {gen}" + (f"  |  {s['who']}" if s.get("who") else ""), {"color": GRAY, "size": 18, "bold": True})])
    d.rich([(s.get("effort", ""), {"bold": True, "size": 44, "color": INK})])
    ids = "  |  ".join(x for x in (s.get("client"), ("Solicitation " + s["solicitation"]) if s.get("solicitation") else "",
                                   ("Internal " + s["internal"]) if s.get("internal") else "") if x)
    if ids:
        d.rich([(ids, {"color": GRAY, "size": 22})])
    if s.get("due"):
        d.band([([(s.get("countdown") or "", {"bold": True, "size": 32, "color": "FFFFFF"}),
                  (f"\nto submission: {s['due']}", {"size": 18, "color": "FFFFFF"})], NAVY)], [PAGE_W])
    # the stage track
    st = s.get("stages") or []
    if st:
        d.rich([("STAGE", {"bold": True, "size": 16, "color": GRAY})])
        cells = []
        for x in st:
            when = x.get("when", "")
            cells.append(([(x["name"] + ("  ✓" if x["state"] == "done" else ""), {"bold": x["state"] == "current", "size": 17, "color": TEXT[x["state"]]}),
                           (("\n" + when) if when else "", {"size": 15, "color": TEXT[x["state"]]})], FILL[x["state"]]))
        d.band(cells, _w(len(cells)))
    tiles = s.get("tiles") or []
    if tiles:
        d.band([([(str(v), {"bold": True, "size": 34, "color": c}), ("\n" + lab, {"size": 17, "color": INK})], "F8FAFC")
                for v, lab, c in tiles], _w(len(tiles)), borders=True)
    # where we are
    cur = s.get("current") or {}
    if cur:
        _head(d, "Where we are")
        d.rich([(cur.get("name", ""), {"bold": True}), (f" since {cur['since']}" if cur.get("since") else "", {}),
                (f". {cur['summary']}" if cur.get("summary") else "", {})])
        rows = []
        done, prog, left = cur.get("done", []), cur.get("in_progress", []), cur.get("left", [])
        for i in range(max(len(done), len(prog), len(left), 1)):
            rows.append([done[i] if i < len(done) else "", prog[i] if i < len(prog) else "", left[i] if i < len(left) else ""])
        d.table([[("Done", {"bold": True, "color": GREEN})], [("In progress", {"bold": True, "color": NAVY})],
                 [("Left in this stage", {"bold": True, "color": AMBER})]], rows, _w(3))
    # questions and notes
    qs, notes = s.get("questions") or [], s.get("notes") or []
    if qs or notes:
        _head(d, "Open questions and notes")
        for q in qs:
            d.rich([("Question  ", {"bold": True, "color": AMBER}), (q["text"], {}),
                    (f"   {q['about']}" if q.get("about") else "", {"color": GRAY, "size": 18}),
                    (f"   {q['when']}, {q['who']}", {"color": GRAY, "size": 18}),
                    (f"   assigned to {q['assignee']}" if q.get("assignee") else "", {"color": NAVY, "size": 18, "bold": True})])
        for n in notes:
            d.rich([(("Answered  " if n.get("answer") else "Note  "), {"bold": True, "color": NAVY}), (n["text"], {}),
                    (f"  Answer: {n['answer']}" if n.get("answer") else "", {"italic": True}),
                    (f"   {n['about']}" if n.get("about") else "", {"color": GRAY, "size": 18}),
                    (f"   {n['when']}, {n['who']}", {"color": GRAY, "size": 18})])
    # projected timeline
    proj = s.get("projected") or []
    if proj:
        _head(d, "Projected timeline")
        d.table(["Stage", "Planned", "Status"], [[p["name"], p.get("planned", ""), p.get("status", "")] for p in proj], [4200, 2400, 2760])
    cal = s.get("calendar") or []
    if cal:
        _head(d, "Calendar")
        COL = {"due": RED, "questions": "7C3AED", "stage": NAVY, "task": AMBER, "done": GREEN, "event": GRAY}
        for m in cal:
            d.rich([(m["title"], {"bold": True, "size": 24, "color": INK})])
            rows = []
            for week in m["weeks"]:
                row = []
                for day, items in week:
                    if not day:
                        row.append("")
                        continue
                    parts = [(str(day), {"bold": True, "size": 16, "color": INK})]
                    for kind, text in items[:4]:
                        parts.append(("\n" + text[:40], {"size": 14, "color": COL.get(kind, INK)}))
                    if len(items) > 4:
                        parts.append((f"\n+{len(items) - 4} more", {"size": 14, "color": GRAY}))
                    row.append(parts)
                rows.append(row)
            d.table(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], rows, _w(7))
        d.rich([("Due  ", {"color": RED, "bold": True, "size": 16}), ("Questions due  ", {"color": "7C3AED", "bold": True, "size": 16}),
                ("Stages  ", {"color": NAVY, "bold": True, "size": 16}), ("Tasks due  ", {"color": AMBER, "bold": True, "size": 16}),
                ("Tasks done  ", {"color": GREEN, "bold": True, "size": 16}), ("What happened", {"color": GRAY, "bold": True, "size": 16})])
    # people
    ppl = s.get("people") or []
    if ppl:
        _head(d, "People and assignments")
        d.table(["Person", "Sections", "Compliance requirements", "Open tasks"],
                [[p["person"], p.get("sections", ""), str(p.get("reqs", 0)),
                  [(str(p.get("tasks", 0)), {}), ((f"  ({p['late']} late)" if p.get("late") else ""), {"color": RED, "bold": True})]]
                 for p in ppl], [2200, 3800, 1700, 1660])
        if s.get("no_owner"):
            d.rich([(f"{s['no_owner']} compliance requirement(s) have no owner yet.", {"color": RED, "bold": True})])
    tasks = s.get("tasks") or []
    if tasks:
        _head(d, "Tasks")
        d.table(["Task", "Owner", "Due", "Stage", "Status"],
                [[t["title"], t.get("owner", ""), t.get("due", ""), t.get("stage", ""),
                  [(t["status"], {"bold": True, "color": RED if t.get("late") else GREEN if t["status"] == "Done" else NAVY})]] for t in tasks],
                [3700, 1500, 1200, 1500, 1460])
    dl = s.get("deliverables") or []
    if dl or s.get("deliverables_suggested"):
        _head(d, "Deliverables")
        if dl:
            d.table(["Deliverable", "Format", "Limit", "Owner", "Status"],
                    [[x["name"], x.get("format", ""), x.get("limit", ""), x.get("owner", "") or "nobody yet",
                      [(x["status"], {"bold": bool(x.get("flag")), "color": RED if x.get("flag") == "over" else AMBER if x.get("flag") else INK})]]
                     for x in dl], [2600, 2000, 1100, 1500, 2160])
        if s.get("deliverables_suggested"):
            d.rich([("Named in the customer documents, not confirmed yet: ", {"bold": True, "color": AMBER}),
                    (", ".join(s["deliverables_suggested"]), {})])
    # changes
    ch = s.get("changes") or []
    if ch:
        _head(d, s.get("changes_title") or "What changed")
        d.table(["Date", "What", "Who"], [[c["when"], c["text"], c.get("who", "")] for c in ch], [1300, 6660, 1400])
    # submission requirements
    req = s.get("requirements") or {}
    if req.get("lines"):
        _head(d, "Submission requirements")
        for line in req["lines"]:
            d.para(line)
        for r in req.get("to_review", []):
            d.rich([("Not reviewed yet  ", {"bold": True, "color": AMBER}), (r, {})])
    # each stage
    if st:
        _head(d, "Each stage: done and left")
        rows = []
        for x in st:
            if x["state"] == "ahead":
                rows.append([x["name"], x.get("dates", ""), "not started", f"{x.get('goals', 0)} goal(s) set"])
            else:
                rows.append([x["name"], x.get("dates", ""), f"{x.get('met', 0)} of {x.get('goals', 0)}", "; ".join(x.get("open", [])) or "nothing left"])
        d.table(["Stage", "Dates", "Goals met", "Left"], rows, [2100, 2300, 1100, 3860])
    docs = s.get("documents") or []
    if docs:
        _head(d, "Customer documents")
        d.table(["Document", "Versions", "Latest"], [[x["name"], x["versions"], x["latest"]] for x in docs], [3400, 3900, 2060])
    if final and s.get("history"):
        _head(d, "Complete history")
        d.table(["Date", "Kind", "What", "Who"], [[h["when"], h["kind"], h["text"], h.get("who", "")] for h in s["history"]],
                [1300, 1300, 5460, 1300])
    d.rich([(f"Made by Stationkeeper {s.get('app', '')} on this PC. Rules only, no AI. It holds effort content: share it the way "
             "you share the proposal.", {"color": GRAY, "size": 16})])
    d.props = {"StationkeeperEffort": s.get("effort", ""), "StationkeeperReport": kind.title()}
    d.save(path)
    return path
