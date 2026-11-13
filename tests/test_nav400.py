"""4.0.0 the effort's path (navsteps; 3.96.0's five steps became six, claude/stationkeeper-six-steps-plan-4.0.md): Documents,
Shred, Matrix & Outline, Setup, Drafts, Submit; each done, now, next or later; what the menu shows beside each (done, a
count, next, the due date); how far along each is; Your next step with the page it opens; the bar at the bottom of a page
in a step. Plain numbers only (fictional, as the effort would hold them)."""
import datetime, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import navsteps as NS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def facts(**kw):
    f = {"today": datetime.date(2026, 11, 9), "docs": 0, "to_check": 0, "reqs": None, "compare": 0, "sections": 0, "made": False,
         "acronyms": 0, "acr_total": 0, "drafts_read": False, "drafts_on": False, "check": None, "due_date": None, "days": None,
         "due": "", "items": 0}
    f.update(kw)
    return f


sts = NS.steps(facts())
check("six steps in the menu's order", [s["key"] for s in sts] == ["library", "assign", "matrix", "setups", "drafts", "finalcheck"]
      and [s["n"] for s in sts] == [1, 2, 3, 4, 5, 6]
      and [s["name"] for s in sts] == ["Documents", "Shred", "Matrix & Outline", "Setup", "Drafts", "Submit"])
check("a new effort: Documents now, Shred next, the rest later", [s["state"] for s in sts] == ["now", "next", "later", "later", "later", "later"])
check("... the menu says add files and next", sts[0]["badge"] == "add files" and sts[1]["badge"] == "next")
n = NS.next_step(sts, facts())
check("Your next step: add the customer's documents", n["go"] == "library" and n["title"] == "Add the customer's documents"
      and n["then"] == "then: shred, then matrix & outline", n)

reqs = {"sentences": 412, "decided": 400, "pct": 97, "reqs": 300, "placed": 274, "owned": 0, "context": 0, "customer": 0, "dropped": 0,
        "undecided": 12}
f = facts(docs=9, reqs=reqs, compare=4, items=412, sections=14, acronyms=14, acr_total=40,
          due_date=datetime.date(2026, 12, 4), due="Dec 4, 2:00 PM", days=25)
sts = NS.steps(f)
by = {s["key"]: s for s in sts}
check("Documents: a new version's changes to review keep it open", by["library"]["state"] == "now" and by["library"]["badge"] == "4 changes to review"
      and "9 documents in; 4 changes to review" == by["library"]["summary"], by["library"])
n = NS.next_step(sts, f)
check("Your next step: review the changes first, in Documents > Changes", n["go"] == "compare" and "4 changes" in n["title"]
      and n["button"] == "Open Changes")
f = dict(f, compare=0)
sts = NS.steps(f)
by = {s["key"]: s for s in sts}
check("files in and checked: done", by["library"]["state"] == "done" and by["library"]["badge"] == "done" and by["library"]["progress"] == 1.0)
check("Shred now: pieces to shred and acros to decide", by["assign"]["state"] == "now" and by["assign"]["badge"] == "12 not shredded"
      and "400 of 412 pieces shredded" in by["assign"]["summary"] and "14 acros and abs to decide" in by["assign"]["summary"], by["assign"])
check("... how far along", 0.9 < by["assign"]["progress"] < 1.0, by["assign"]["progress"])
check("Matrix & Outline next: requirements to place (4.6.0: its count, not 'next'); Submit its due date", by["matrix"]["state"] == "next"
      and by["matrix"]["badge"] == "26 to place"
      and "274 of 300 requirements placed" in by["matrix"]["summary"] and by["finalcheck"]["badge"] == "Dec 4")
n = NS.next_step(sts, f)
check("... Your next step: the pieces left to shred", n["go"] == "assign" and "12 pieces" in n["title"] and n["button"] == "Open Shred")
f2 = dict(f, reqs=dict(reqs, undecided=0, decided=412))
n = NS.next_step(NS.steps(f2), f2)
check("... then the acros and abs left to decide", n["go"] == "acronyms" and n["title"] == "Decide the 14 acros and abs left"
      and n["button"] == "Open Acros & Abs")
f2 = dict(f2, acronyms=0)
sts = NS.steps(f2)
n = NS.next_step(sts, f2)
check("... then the requirements left to place (4.4.0: on Place)", n["go"] == "place" and n["title"] == "Place the 26 requirements left"
      and sts[2]["state"] == "now" and sts[2]["badge"] == "26 to place")


class M:
    history = [["2026-11-09 10:00", "x", "(setup)", "setup made: 2 file(s)"]]


check("the setup counts as made once Make the setup wrote it", NS.made(M) and not NS.made(type("E", (), {"history": []})))
f3 = dict(f2, reqs=dict(reqs, undecided=0, decided=412, placed=300), made=True)
sts = NS.steps(f3)
check("Shred, Matrix & Outline and Setup done; Drafts now until the drafts are read back",
      [s["state"] for s in sts] == ["done", "done", "done", "done", "now", "next"], [s["state"] for s in sts])
n = NS.next_step(sts, f3)
check("... Your next step: read the drafts back", n["go"] == "drafts" and n["title"] == "Read the drafts back" and n["button"] == "Open Drafts")
f3 = dict(f3, drafts_read=True)
n = NS.next_step(NS.steps(f3), f3)
check("... then run the Final Check", n["go"] == "finalcheck" and n["title"] == "Run the Final Check")
f4 = dict(f3, check={"at": "2026-12-01", "ok": True})
check("every step done: the next step says so", NS.next_step(NS.steps(f4), f4)["title"] == "Every step is done")
check("Shred with nothing read in", NS.steps(facts(docs=1))[1]["summary"] == "Nothing shredded yet."
      and NS.next_step(NS.steps(facts(docs=1)), facts(docs=1))["go"] == "assign")         # 4.4.0: adding extracts it; Shred opens
b = NS.bar("matrix", NS.steps(f))
check("the bar at the bottom: what is left on this step and the next step's button",
      b["left"].startswith("274 of 300") and b["button"] == "Next: Setup, make the setup from the outline" and b["go"] == "setups")
check("... Submit is the last step: no next button", NS.bar("finalcheck", NS.steps(f))["button"] == "")
check("... a step done says so", NS.bar("library", NS.steps(f))["left"] == "This step is done.")
check("a short date for the menu", NS.short_date(datetime.date(2026, 12, 4)) == "Dec 4")
check("no effort: nothing to read", NS.facts(None)["docs"] == 0)
# 4.6.0: every step says what is left, not only the step at hand
f2 = facts(docs=9, reqs=dict(reqs, undecided=0, placed=300), compare=0, items=412, sections=14, acronyms=0, acr_total=40,
           due_date=datetime.date(2026, 12, 4), due="Dec 4, 2:00 PM", days=25, reshred=4)
by = {s["key"]: s for s in NS.steps(f2)}
check("4.6.0: Shred says how many passages wait to be shredded again", by["assign"]["badge"] == "4 to re-shred", by["assign"])
check("4.6.0: Setup says it is to make while the structure has sections", by["setups"]["badge"] == "to make", by["setups"])
f3 = dict(f2, reshred=0, made=True)
by = {s["key"]: s for s in NS.steps(f3)}
check("4.6.0: Drafts says to read back once the setup is made", by["drafts"]["badge"] == "to read back" and by["finalcheck"]["badge"] == "Dec 4", by["drafts"])

print(f"NAV 400 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
