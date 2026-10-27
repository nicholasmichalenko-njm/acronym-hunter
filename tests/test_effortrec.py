"""2.40.0 effort record: due date parsing and countdown; editable stages with the team's default goals; the proposal
manager moves the stage and open goals carry over; automatic and written goals; the timeline logs every change;
notes and open questions; tasks with owners, status and overdue; saved and read back."""
import os, sys, tempfile, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import effortrec as R


def run():
    assert R.parse_due_text("December 15, 2026, 2:00 p.m. Mountain Time") == ("2026-12-15T14:00", "MT")
    assert R.parse_due_text("Proposals are due no later than 1600 hours EST on 12/15/2026.") == ("2026-12-15T16:00", "ET")
    assert R.parse_due_text("no date here") == (None, "")
    assert R.parse_time("2 PM") == (14, 0) and R.parse_time("09:30") == (9, 30) and R.parse_time("noonish") is None
    now = datetime.datetime(2026, 10, 26, 18, 0)
    assert R.countdown("2026-12-15T14:00", now) == (49, 20)
    assert R.countdown_text("2026-12-15T14:00", now) == "49 d  20 h"
    assert R.countdown_text("2026-10-26T12:00", now) == "Due date passed" and R.countdown_text("", now) == ""
    assert R.due_text("2026-12-15T14:00", "MT") == "Dec 15, 2026, 2:00 p.m. MT"
    assert R.short_date("2026-10-26T09:14") == "Oct 26"
    d = tempfile.mkdtemp()
    rec = R.Record(d)
    assert [s["name"] for s in rec.stages] == list(R.DEFAULT_STAGES) and rec.stage()["name"] == "Intake"
    intake = rec.stage()
    assert [g["auto"] for g in intake["goals"]] == ["docs_added", "reqs_reviewed", "structure_set", "sections_led"]
    rec.set_due("2026-12-15T14:00", "MT", who="pm")
    # goals: automatic ones follow the checks; written ones are ticked by hand
    checks = {"docs_added": True, "reqs_reviewed": False, "structure_set": None, "sections_led": True}
    assert rec.goal_progress(checks=checks) == (2, 4)
    sg = next(g for g in intake["goals"] if g["auto"] == "structure_set")
    rec.set_goal(intake["id"], sg["id"], True, who="pm")             # the app cannot tell yet: ticked by hand
    assert rec.goal_progress(checks=checks) == (3, 4)
    gid = rec.add_goal(intake["id"], "Kickoff held", who="pm")
    assert rec.goal_progress(checks=checks) == (3, 5)
    # edit the stages: rename, add, remove, reorder; goals stay with their stage
    ids = {s["name"]: s["id"] for s in rec.stages}
    rows = [(ids["Intake"], "Intake", "2026-10-02"), (ids["Author drafts"], "Author drafts", "2026-10-06"),
            (None, "Pink team", "2026-10-12"), (ids["Red team"], "Red team review", "2026-10-17"),
            (ids["Red team recovery"], "Red team recovery", ""), (ids["Final to pubs"], "Final to pubs", "2026-12-11")]
    rec.edit_stages(rows, who="pm")
    assert [s["name"] for s in rec.stages] == ["Intake", "Author drafts", "Pink team", "Red team review", "Red team recovery", "Final to pubs"]
    assert rec.stage(ids["Red team"])["goals"] and rec.stages[2]["goals"] == [] and rec.stages[0]["planned"] == "2026-10-02"
    try:
        rec.edit_stages([(ids["Author drafts"], "Author drafts", "")]); assert False, "removing the current stage"
    except ValueError:
        pass
    # move: open goals carry over
    open_ids = [g["id"] for g in intake["goals"] if not rec.goal_done(g, checks)]
    assert rec.move_to(ids["Author drafts"], carry=open_ids[:1], who="pm")
    ad = rec.stage()
    assert ad["name"] == "Author drafts" and intake["ended"] and ad["started"] and rec.state_of(intake) == "done"
    carried = [g for g in ad["goals"] if g.get("from") == "Intake"]
    assert len(carried) == 1 and not carried[0]["done"]
    assert rec.state_of(rec.stages[-1]) == "ahead" and rec.state_of(ad) == "current"
    assert not rec.move_to(ad["id"])
    # notes and open questions
    q = rec.add_note("Does the 25-page limit include the executive summary?", on="version", on_id="v3", label="RFP, Amendment 3",
                     question=True, who="pm")
    rec.add_note("Gold team reviewers confirmed: 5 of 6.", on="stage", on_id=ad["id"], label="Author drafts", who="pm")
    assert len(rec.open_questions()) == 1 and rec.notes(on="version", on_id="v3")[0]["id"] == q
    assert rec.resolve_note(q, "CO: no, it is excluded", who="pm") and not rec.open_questions()
    assert rec.add_note("   ") is None
    # tasks
    t1 = rec.add_task("Cut Vol I to 25 pages", owner="J. Smith", due="2026-10-30", about="Vol I Technical", who="pm")
    t2 = rec.add_task("Move pricing to J-3 v2", owner="B. Chen", due="2026-10-20", who="pm")
    assert [t["id"] for t in rec.tasks(open_only=True)] == [t2, t1]
    assert rec.task_overdue(rec.task(t2), today=datetime.date(2026, 10, 26)) and not rec.task_overdue(rec.task(t1), today=datetime.date(2026, 10, 26))
    assert rec.update_task(t2, status="Done", who="bchen") and rec.task(t2)["done"]
    assert not rec.update_task(t2, status="Done") and not rec.update_task(t2, status="Finished")
    assert rec.update_task(t1, owner="A. Lee", who="pm") and rec.tasks(owner="A. Lee")[0]["id"] == t1
    # the timeline holds the whole story, newest first
    kinds = [e["kind"] for e in rec.events()]
    texts = " | ".join(e["text"] for e in rec.events())
    assert {"effort", "stage", "note", "task", "assign"} <= set(kinds), kinds
    assert "Due date set to Dec 15, 2026, 2:00 p.m. MT" in texts and "Moved to Author drafts from Intake; 1 open goal carried over" in texts
    assert "Stage renamed: Red team to Red team review" in texts and "Stage added: Pink team" in texts and "Stage removed: Gold team" in texts
    assert "Task done: Move pricing to J-3 v2 (B. Chen)" in texts and "Task assigned to A. Lee: Cut Vol I to 25 pages" in texts
    assert rec.events(kinds=("note",))[0]["text"].startswith("Resolved:")
    # read back
    rec2 = R.Record(d)
    assert rec2.data == rec.data and rec2.stage()["name"] == "Author drafts" and rec2.data["due"] == "2026-12-15T14:00"
    assert rec2.remove_goal(intake["id"], gid) and rec2.remove_task(t2) and rec2.remove_note(q)
    print("effortrec ok")


if __name__ == "__main__":
    run()
