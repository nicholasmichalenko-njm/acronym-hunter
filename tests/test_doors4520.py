"""4.52.0 doors.py and calacross.py alone, in a temp folder. The doors: three, in order, with their words; which a home kind
shows (a program has no Shred to setup); which files each takes (from the Quick tools uses it stands for); which doors
take a set of files; Shred to setup offers no program. Calendar across efforts: two efforts' dates (a due date, an event,
a task, as an effort's calendar saves them) in one list, soonest first, each naming its effort; a program, an archived
effort, Unfiled, an effort whose folder is gone and one never opened are left out without an error; nothing is written
in any effort's folder and no folder is made; skip leaves the open one out. Fictional (Kestrel, Heron, Osprey)."""
import datetime, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import calacross as CA, doors as DR, effort as E, effortcal as EC, effortrec as R, programs as PG, unfiled as UF, workspace as W

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the doors
check("three doors, in order, with their names", [k for k, _n, _w in DR.DOORS] == ["acronyms", "shred", "check"]
      and [n for _k, n, _w in DR.DOORS] == ["Acronyms", "Shred to setup", "Check a document"])
check("... each with one plain line, no emoji", all(w and w[0].isupper() and all(ord(c) < 128 or c in "'" for c in w) for _k, _n, w in DR.DOORS))
check("for_home: nothing open and an effort show all three", DR.for_home("none") == DR.KEYS and DR.for_home("effort") == DR.KEYS)
check("for_home: a program shows Acronyms and Check a document", DR.for_home("program") == ("acronyms", "check"))
check("takes: Acronyms reads a Word file, a PDF and a picture", all(DR.takes("acronyms", [p]) for p in ("a.docx", "b.pdf", "c.png")))
check("takes: Shred to setup reads a PDF and a Word file, not a picture", DR.takes("shred", ["a.pdf", "b.docx"]) and not DR.takes("shred", ["c.png"]))
check("takes: Check a document reads our Office files only", DR.takes("check", ["a.docx", "b.xlsx", "c.pptx"]) and not DR.takes("check", ["d.pdf"]))
check("takes: no file, or a kind no reader takes, is never taken", not DR.takes("acronyms", []) and not DR.takes("acronyms", ["x.zzz"])
      and not DR.takes("nothing", ["a.docx"]))
check("takes: every file must be readable", not DR.takes("check", ["a.docx", "b.pdf"]))
check("doors_for: a PDF with nothing open", DR.doors_for("none", ["a.pdf"]) == ("acronyms", "shred"))
check("doors_for: a Word file in a program", DR.doors_for("program", ["a.docx"]) == ("acronyms", "check"))
check("doors_for: a picture", DR.doors_for("effort", ["a.png"]) == ("acronyms",))
check("wants_programs: Shred to setup offers no program; the others do", not DR.wants_programs("shred")
      and DR.wants_programs("acronyms") and DR.wants_programs("check"))

# ---- calendar across efforts
data = os.path.join(tmp, "Stationkeeper Data")
reg = E.Registry(os.path.join(data, "config", "efforts.json"))
today = datetime.date(2030, 3, 10)


def effort(name, opened=True, **kw):
    p = os.path.join(data, "Efforts", name, f"{name}_Effort_List.xlsx")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    L = E.EffortList(p, name); L.pending = True; L.save()
    reg.put(name, path=p, **kw)
    if opened:
        root = W.data_dir_for(p)
        os.makedirs(root, exist_ok=True)
        rec = R.Record(root)
        rec.save()
        return rec
    return None


def ahead(rec, days):
    return (today + datetime.timedelta(days=days)).isoformat()


k = effort("Kestrel")
k.data["due"] = ahead(k, 20); k.save()
EC.add_entry(k, kind="Review", title="Pink team", date=ahead(k, 5))
h = effort("Heron")
h.add_task("Send the past performance", owner="Pat", due=ahead(h, 2)); h.save()
EC.add_entry(h, kind="Meeting", title="Kickoff", date=ahead(h, 12))
EC.add_entry(h, kind="Meeting", title="Old meeting", date=(today - datetime.timedelta(days=3)).isoformat())
o = effort("Osprey", program=True)
EC.add_entry(o, kind="Meeting", title="Program review", date=ahead(o, 1))
a = effort("Plover", archived=True)
EC.add_entry(a, kind="Meeting", title="Archived meeting", date=ahead(a, 1))
g = effort("Gone")
EC.add_entry(g, kind="Meeting", title="Gone meeting", date=ahead(g, 1))
shutil.rmtree(os.path.dirname(reg.get("Gone")["path"]))
effort("Fresh", opened=False)
UF.ensure(reg, data)


def listing(folder):
    out = []
    for r_, ds, fs in os.walk(folder):
        out += [os.path.relpath(os.path.join(r_, d), folder) + "/" for d in ds]
        for f in fs:
            p = os.path.join(r_, f)
            out.append((os.path.relpath(p, folder), os.path.getsize(p), os.path.getmtime(p)))
    return sorted(map(str, out))


was = listing(os.path.join(data, "Efforts"))
rows = CA.collect(reg, today)
names = {r["effort"] for r in rows}
whats = [r["what"] for r in rows]
check("both efforts' dates are listed, each naming its effort", names == {"Kestrel", "Heron"}, names)
check("... the due date, the review, the task and the meeting", any("Proposal due" in w for w in whats) and any("Pink team" in w for w in whats)
      and any("Send the past performance" in w for w in whats) and any("Kickoff" in w for w in whats), whats)
check("... soonest first", [r["date"] for r in rows] == sorted(r["date"] for r in rows) and rows[0]["effort"] == "Heron"
      and "Send the past performance" in rows[0]["what"], rows[:2])
check("... days counted from today, and what is past left out", rows[0]["days"] == 2 and not any("Old meeting" in w for w in whats))
check("... the kind in words", {r["kind"] for r in rows} >= {"Due", "Task"}, {r["kind"] for r in rows})
check("a program, an archived effort, Unfiled, a missing folder and one never opened are left out", not names & {"Osprey", "Plover", UF.NAME, "Gone", "Fresh"})
check("nothing written in any effort's folder and no folder made", listing(os.path.join(data, "Efforts")) == was)
check("the effort never opened still has no data folder", not os.path.exists(W.data_dir_for(reg.get("Fresh")["path"])))
rows2 = CA.collect(reg, today, skip=("Heron",))
check("skip leaves the open one out", {r["effort"] for r in rows2} == {"Kestrel"})
check("when: the date in words", CA.when(rows[0], today) == (today + datetime.timedelta(days=2)).strftime("%a"))
check("no efforts: an empty list", CA.collect(E.Registry(os.path.join(tmp, "none.json")), today) == [])
check("programs.effort_names agrees: Kestrel, Heron, Gone, Fresh", sorted(PG.effort_names(reg)) == ["Fresh", "Gone", "Heron", "Kestrel"])

n = sum(checks)
print(f"DOORS 4520 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
