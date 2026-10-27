"""2.52.0 the effort's team (Effort > Team...) in every drop-down where a lead, owner or assignee is picked; dates from
a calendar (Effort details due date, task due date, stage start and end); each stage's planned start and end with
how many days are left (or past the plan) on the current stage, and nothing changing by itself."""
import os, sys, tempfile, datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, datepick as DP
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel"); app.shell_go("home"); app.update()
    w = app.rec_team_dialog(); app.update()
    w._api["items"][0][:] = ["J. Smith", "Volume lead"]
    w._api["items"].append(["K. Park", "Author"])
    app.rec_team_dialog(rows=[tuple(x) for x in w._api["items"]]); w.destroy()
    check("Effort > Team...: the people and their roles are kept", [(m["name"], m["role"]) for m in app.effrec().team()]
          == [("J. Smith", "Volume lead"), ("K. Park", "Author")])
    check("the team comes first in every drop-down of people", app.rec_people()[:2] == ["J. Smith", "K. Park"], app.rec_people())
    tw = app.rec_task_dialog(); app.update()
    check("a task's owner is a drop-down of the team", "K. Park" in tw._api["entries"]["owner"].cget("values"))
    tw._api["entries"]["title"].insert(0, "Draft 1.1"); tw._api["entries"]["owner"].set("K. Park")
    tw._api["entries"]["due"].set("2026-11-20"); tw._api["ok"](); app.update()
    t = [x for x in app.effrec().tasks() if x["title"] == "Draft 1.1"][0]
    check("a task's due date from the calendar field", t["due"] == "2026-11-20" and t["owner"] == "K. Park", (t["due"], t["owner"]))
    check("Owner picks from the team (a name can be typed too)", app.rec_pick_person("Owner", "x", answer="K. Park") == "K. Park")
    df = DP.DateField(app, "December 15, 2026")
    pop = df.open(); app.update()
    pop.pick(datetime.date(2026, 12, 18)); app.update()
    check("Pick opens a calendar; a picked day fills the field", df.get() == "2026-12-18" and df.entry.get() == "Dec 18, 2026", df.entry.get())
    d = app.rec_details_dialog(); d.update()
    d._api["date"].set("2026-12-15"); d._api["time"].insert(0, "2:00 p.m."); d._api["zone"].insert(0, "MT"); d._api["ok"](); app.update()
    check("Effort details: the due date from a calendar with the time and zone beside it", app.effrec().data["due"].startswith("2026-12-15T14:00")
          and app.effrec().data["zone"] == "MT", app.effrec().data["due"])
    r = app.effrec()
    today = datetime.date.today()
    rows = [(s["id"], s["name"], s["planned"], s.get("planned_end", "")) for s in r.stages]
    rows[0] = (rows[0][0], rows[0][1], (today - datetime.timedelta(days=3)).isoformat(), (today + datetime.timedelta(days=4)).isoformat())
    app.rec_stages_dialog(rows=rows); app.update()
    tm = r.stage_timing()
    def texts(w):
        out = []
        for c in w.winfo_children():
            try:
                out.append(str(c.cget("text")))
            except Exception:
                pass
            out += texts(c)
        return out
    track = " | ".join(texts(app.rec_track))
    check("each stage has a planned start and end; the current one says the days left", tm["days"] == 8 and tm["left"] == 4
          and "4 days left" in track, (tm, track[:200]))
    rows[0] = (rows[0][0], rows[0][1], (today - datetime.timedelta(days=10)).isoformat(), (today - datetime.timedelta(days=2)).isoformat())
    app.rec_stages_dialog(rows=rows); app._rec_force(); app.update()
    track = " | ".join(texts(app.rec_track))
    check("past the planned end it says so, and the stage does not move by itself", r.stage_timing()["over"] == 2 and "2 days past plan" in track
          and r.stage()["name"] == rows[0][1], track[:200])
    sw = app.rec_stages_dialog(); sw.update()
    check("Edit stages has a start and an end date, each with a calendar", len(sw._api["widgets"][0]) == 3
          and sw._api["widgets"][0][2].get() == rows[0][3])
    sw.destroy()
    cal = r.calendar()
    check("the calendar shows a stage's planned end", any("(planned end)" in t for v in cal.values() for _k, t in v))
    n = sum(checks)
    print(f"GUI TEAM PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI TEAM FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
