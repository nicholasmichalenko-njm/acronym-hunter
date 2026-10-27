"""2.49.0 Effort home: sections that open and close (remembered); gate goals edited and removed; notes and questions
edited, assigned to a person and removed; Show one person's questions; a month calendar with the due date and tasks,
a day picked shows what falls on it; the Effort status export carries the calendar and who a question is assigned to."""
import os, sys, tempfile, zipfile, datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def texts_of(w):
    out = []
    for c in w.winfo_children():
        try:
            t = c.cget("text")
            if t:
                out.append(t)
        except Exception:
            pass
        out += texts_of(c)
    return out


app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel"); app.shell_go("home"); app.update()
    today = datetime.date.today()
    due = today.replace(day=min(today.day + 1, 28)) if today.day < 28 else today
    app.rec_details_dialog(values={"due": due.strftime("%B %d, %Y").replace(" 0", " ") + ", 2:00 p.m. MT"})
    app._rec_force(); app.update()
    keys = list(app.rec_cards)
    check("Effort home sections: goals, tasks, notes and questions, calendar, timeline", keys == ["goals", "tasks", "notes", "custinfo", "calendar", "timeline"], keys)
    check("the timeline starts closed, the others open", not app.rec_frames["timeline"]._body.winfo_manager()
          and app.rec_frames["goals"]._body.winfo_manager())
    app.rec_toggle("goals"); app.update()
    check("a section closes, and that is remembered", not app.rec_frames["goals"]._body.winfo_manager()
          and app.settings["home_sections"]["goals"] is False)
    app.rec_toggle("goals"); app.update()
    r = app.effrec()
    gid = app.rec_add_goal_dialog(text="Kickoff held")
    sid = r.data["stage"]
    app.rec_goal_edit(sid, gid, "Kickoff held with the whole team"); app.update()
    g = " | ".join(texts_of(app.rec_cards["goals"][2]))
    check("a goal edited", "Kickoff held with the whole team" in g and "Edit" in g and "Remove" in g, g[:200])
    app.rec_goal_remove(sid, gid); app.update()
    check("a goal removed", "Kickoff held" not in " | ".join(texts_of(app.rec_cards["goals"][2])))
    q1 = app.rec_note_dialog(text="Does the page limit include the cover?", question=True)
    q2 = app.rec_note_dialog(text="Who signs the cover letter?", question=True)
    n1 = app.rec_note_dialog(text="Kickoff notes.")
    w = app.rec_note_edit_dialog(q1, focus="assignee"); w.update()
    w._api["assignee"].set("K. Park"); w._api["ok"](); app.update()
    nt = " | ".join(texts_of(app.rec_cards["notes"][2]))
    check("a question assigned to a person shows who", "assigned to K. Park" in nt and "Assign..." in nt, nt[:300])
    check("the person can be picked in Show", "K. Park" in app.rec_people())
    app.rec_who.set("K. Park"); app._rec_force(); app.update()
    nt = " | ".join(texts_of(app.rec_cards["notes"][2]))
    check("Show one person: only their open questions", "Does the page limit" in nt and "Who signs" not in nt and "Kickoff notes" not in nt
          and "1 open for K. Park" in app.rec_cards["notes"][1].cget("text"), nt[:200])
    app.rec_who.set("Everyone"); app._rec_force()
    app.rec_note_edit_dialog(n1, values={"text": "Kickoff notes: capture lead attended."}); app.update()
    check("a note edited", "Kickoff notes: capture lead attended." in " | ".join(texts_of(app.rec_cards["notes"][2])))
    app.rec_note_remove(q2); app.update()
    check("a question removed", "Who signs" not in " | ".join(texts_of(app.rec_cards["notes"][2])))
    check("assigning is on the timeline", any("assigned to K. Park" in e["text"] for e in r.events()))
    app.rec_task_dialog(values={"title": "Draft the thermal section", "owner": "J. Smith", "due": today.isoformat()})
    app.update()
    cal = app.rec_cal_days()
    check("the calendar holds the due date and the task", any(k == "due" for k, _t in cal.get(due, []))
          and any("Draft the thermal section" in t for _k, t in cal.get(today, [])), {str(k): v for k, v in cal.items()})
    ct = " | ".join(texts_of(app.rec_cards["calendar"][2]))
    check("the month grid shows them", "Proposal due" in ct and "Draft the thermal" in ct
          and app.rec_cards["calendar"][1].cget("text") == f"Calendar   {today.strftime('%B %Y')}", ct[:300])
    app.rec_cal_pick(today); app.update()
    ct = " | ".join(texts_of(app.rec_cards["calendar"][2]))
    check("a day picked shows everything on it and offers a task due that day", "Draft the thermal section (J. Smith)" in ct
          and "+ Task due this day" in ct, ct[-300:])
    nxt = app.rec_cal_step(1); app.update()
    check("Next goes to the next month", (nxt.year, nxt.month) == ((today.year + today.month // 12), today.month % 12 + 1))
    app.rec_cal_step(0)
    out = os.path.join(tmp, "status.docx")
    app.status_export(path=out)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    check("the Effort status export has the calendar", "Calendar" in xml and today.strftime("%B %Y") in xml and "Draft the thermal section" in xml)
    check("and who an open question is assigned to", "assigned to K. Park" in xml)
    n = sum(checks)
    print(f"GUI EFFORTHOME PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI EFFORTHOME FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
