"""3.96.0 the effort's path (navsteps): five steps, each done, now, next or later; what the menu shows beside each (done,
a count, next, the due date); how far along each is; Your next step with the page it opens; the bar at the bottom of a
page in a step. Plain numbers only (fictional, as the effort would hold them)."""
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
check("five steps in the menu's order", [s["key"] for s in sts] == ["library", "assign", "setups", "acronyms", "finalcheck"]
      and [s["n"] for s in sts] == [1, 2, 3, 4, 5] and [s["name"] for s in sts] == ["Customer files", "Review", "Setup", "Write", "Submit"])
check("a new effort: Customer files now, Review next, the rest later", [s["state"] for s in sts] == ["now", "next", "later", "later", "later"])
check("... the menu says add files and next", sts[0]["badge"] == "add files" and sts[1]["badge"] == "next")
n = NS.next_step(sts, facts())
check("Your next step: add the customer's files", n["go"] == "library" and n["title"] == "Add the customer's files" and n["then"] == "then: review, then setup")

reqs = {"sentences": 412, "decided": 400, "pct": 97, "reqs": 300, "placed": 274, "owned": 0, "context": 0, "customer": 0, "dropped": 0,
        "undecided": 12}
f = facts(docs=9, reqs=reqs, compare=4, items=412, sections=14, acronyms=14, acr_total=40,
          due_date=datetime.date(2026, 12, 4), due="Dec 4, 2:00 PM", days=25)
sts = NS.steps(f)
by = {s["key"]: s for s in sts}
check("files in and checked: done", by["library"]["state"] == "done" and by["library"]["badge"] == "done" and by["library"]["progress"] == 1.0)
check("Review now: what is left (sentences, requirements, amendment changes)", by["assign"]["state"] == "now"
      and by["assign"]["badge"] == "42 left" and "274 of 300 requirements placed" in by["assign"]["summary"]
      and "4 amendment changes to decide" in by["assign"]["summary"])
check("... how far along", 0.9 < by["assign"]["progress"] < 1.0, by["assign"]["progress"])
check("Setup next; Write shows its acronyms; Submit its due date", by["setups"]["badge"] == "next" and by["acronyms"]["badge"] == "14 acronyms"
      and by["finalcheck"]["badge"] == "Dec 4")
n = NS.next_step(sts, f)
check("Your next step: decide the amendment's changes in Compare first", n["go"] == "compare" and "4 changes" in n["title"]
      and n["button"] == "Open Compare")
n = NS.next_step(NS.steps(dict(f, compare=0)), dict(f, compare=0))
check("... then the sentences left to decide", n["go"] == "assign" and "12 sentences" in n["title"])
f2 = dict(f, compare=0, reqs=dict(reqs, undecided=0, decided=412))
n = NS.next_step(NS.steps(f2), f2)
check("... then the requirements left to place", n["go"] == "assign" and n["title"] == "Place the 26 requirements left")

class M:
    history = [["2026-11-09 10:00", "x", "(setup)", "setup made: 2 file(s)"]]


check("the setup counts as made once Make the setup wrote it", NS.made(M) and not NS.made(type("E", (), {"history": []})))
f3 = dict(f2, reqs=dict(reqs, undecided=0, decided=412, placed=300), made=True, acronyms=0)
sts = NS.steps(f3)
check("Review and Setup done, Write done when every acronym is decided (drafts set aside), Submit now",
      [s["state"] for s in sts] == ["done", "done", "done", "done", "now"], [s["state"] for s in sts])
n = NS.next_step(sts, f3)
check("... Your next step: run the Final Check", n["go"] == "finalcheck" and n["title"] == "Run the Final Check")
f4 = dict(f3, check={"at": "2026-12-01", "ok": True})
check("every step done: the next step says so", NS.next_step(NS.steps(f4), f4)["title"] == "Every step is done")
check("Write with no acronyms scanned is not done", NS.steps(facts(docs=1))[3]["done"] is False
      and NS.steps(facts(docs=1))[3]["summary"].startswith("No acronyms scanned yet"))
b = NS.bar("assign", NS.steps(f))
check("the bar at the bottom: what is left on this step and the next step's button",
      b["left"].startswith("274 of 300") and b["button"] == "Next: Setup, make the setup from what you placed" and b["go"] == "setups")
check("... Submit is the last step: no next button", NS.bar("finalcheck", NS.steps(f))["button"] == "")
check("... a step done says so", NS.bar("library", NS.steps(f))["left"] == "This step is done.")
check("a short date for the menu", NS.short_date(datetime.date(2026, 12, 4)) == "Dec 4")
check("no effort: nothing to read", NS.facts(None)["docs"] == 0)

print(f"NAV 396 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
