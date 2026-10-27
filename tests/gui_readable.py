"""2.46.0 the readable copy follows the app: opening an effort writes it; a note, a task, an acronym approval or a
compliance decision lands in it a few seconds after it is saved (once the files are quiet); Effort > Open the readable
copy folder."""
import csv, os, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, readable as RD
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
CDIR = os.path.join(tmp, "Kestrel", "Customer documents"); os.makedirs(CDIR)
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def rows(name):
    p = os.path.join(RD.folder_for(LIST, "Kestrel"), name)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def settle():
    """Let the readable copy catch up: the files changed, then stayed quiet for a moment."""
    for _ in range(3):
        app.readable_tick()
        app.readable_wait()
        app._rd_since = time.time() - 10
    r = app.readable_tick()
    app.readable_wait()
    return r


app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    settle()
    folder = RD.folder_for(LIST, "Kestrel")
    check("opening an effort writes its readable copy beside the effort list", os.path.isfile(os.path.join(folder, "READ ME FIRST.txt"))
          and os.path.dirname(folder) == os.path.dirname(LIST), folder)
    app.rec_note_dialog(text="Asked the CO about the page limit.", question=True, label="RFP Section L"); app.update()
    check("a change waits until the files are quiet", (app.readable_wait(), app.readable_tick())[1] is False and not any("Asked the CO" in r["Text"] for r in rows("Notes and open questions.csv")))
    settle()
    check("then the open question is in the copy", any(r["Kind"] == "Open question" and r["Text"] == "Asked the CO about the page limit."
                                                        for r in rows("Notes and open questions.csv")))
    app.rec_task_dialog(values={"title": "Draft the thermal design section", "owner": "J. Smith", "due": "2030-11-06"}); app.update()
    settle()
    check("a task is in the copy", any(r["Task"] == "Draft the thermal design section" and r["Owner"] == "J. Smith" for r in rows("Tasks.csv")))
    app.effort.add_or_update("TT&C", Type="Acronym", Definition="Telemetry, Tracking and Command")
    app.effort.set_status(["TT&C"], "Approved", approver="R. Diaz"); app._save_effort_list(); app.update()
    time.sleep(1.1)                                   # file times move on whole seconds on some file systems
    app._save_effort_list(); settle()
    acr = {r["Term"]: r for r in rows("Acronyms.csv")}
    check("an acronym approval is in the copy", acr.get("TT&C", {}).get("Status") == "Approved" and acr["TT&C"]["SS Approver"] == "R. Diaz", acr)
    summ = open(os.path.join(folder, "Effort summary.txt"), encoding="utf-8-sig").read()
    check("the summary has the open question and the task", "OPEN QUESTIONS (1)" in summ and "Draft the thermal design section, J. Smith" in summ)
    m = __import__("tkinter").Menu(app)
    app.show_effort_top_menu(m)
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) == "command"]
    check("Effort > Open the readable copy folder", "Open the readable copy folder" in labels, labels)
    check("it returns the folder (Windows opens it)", app.readable_open() == folder)
    n = sum(checks)
    print(f"GUI READABLE PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI READABLE FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
