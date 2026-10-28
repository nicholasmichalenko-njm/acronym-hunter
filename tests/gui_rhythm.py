"""2.32.0 one decision then the next: Acronyms > Review keys (A add, X not a term, Space skip, More menu), Keywords
(K keep, R reject), QA/QC worst first with Next fix (N)."""
import os, sys, tempfile, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import tkinter as tk
import app_gui as A, effort as E
from tkinter import messagebox
tk.Menu.tk_popup = lambda self, *a, **k: None          # never pop up a menu in tests
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True
SAMPLES = os.path.join(A.BASE_DIR, "test_samples")
VOL = os.path.join(SAMPLES, "Kestrel_Technical_Volume.docx")
LIST = os.path.join(tmp, "Kestrel_Effort_List.xlsx")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def wait(cond, then, n=0):
    if not cond() and n < 240:
        app.after(500, lambda: wait(cond, then, n + 1)); return
    then()


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.shell_go("acronyms", "scan")
    app.start_batch([VOL])
    wait(lambda: not app.busy() and not app.btn_cancel.winfo_ismapped() and app.results, review)


def review():
    app.update()
    check("a scan lands on Review", app.shell_feature == "acronyms" and app.shell_step == "review")
    tv = app.tree
    rows = [r for r in tv.get_children() if r in app.results and not app.results[r].get("file_error")]
    tv.selection_set(rows[0]); tv.focus(rows[0]); tv.focus_set(); app.on_select(None); app.update()
    check("the everyday row: Add, Not a term, Skip, More", app.btn_effort_add.winfo_ismapped() and app.btn_rv_more.winfo_ismapped()
          and not app.btn_exc.winfo_ismapped() and "(A)" in app.btn_effort_add.cget("text"))
    tv.event_generate("<KeyPress-a>"); app.update()
    check("A adds it and moves on", rows[0] in app.effort.rows and tv.selection() and tv.selection()[0] != rows[0],
          (rows[0] in app.effort.rows, tv.selection()))
    cur = tv.selection()[0]
    tv.event_generate("<KeyPress-x>"); app.update()
    check("X marks it Not a term and moves on", app.effort.rows.get(cur, {}).get("Status") == "Rejected" and tv.selection()[0] != cur)
    cur = tv.selection()[0]
    tv.event_generate("<space>"); app.update()
    check("Space skips without deciding", app.effort.rows.get(cur, {}).get("Status", "") in ("", "Proposed") and tv.selection()[0] != cur, (cur, app.effort.rows.get(cur, {}).get("Status"), tv.selection()))
    m = app.rv_more_menu()
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1)]
    check("More holds the rarer actions", "Include in the database" in labels and any(l.startswith("Exclude") for l in labels), labels)
    # Keywords: K keep, R reject
    for t in ("thermal control system", "radiator panel sizing"):
        app.kw_add(t, "Our solution", "Typed in")
    app.shell_go("keywords"); app.update()
    kt = app.kw_tree
    kids = kt.get_children()
    kt.selection_set(kids[0]); kt.focus(kids[0]); kt.focus_set(); app.update()
    first = app.kw_selected()[0]
    kt.event_generate("<KeyPress-k>"); app.update()
    st = {k["Keyword"]: k["Status"] for k in app.effort.keywords}
    check("K keeps the keyword and moves on", st.get(first) == "Keep" and app.kw_selected() and app.kw_selected()[0] != first, st)
    # QA/QC: worst first, Next fix
    app.shell_go("qaqc"); app.check_volumes([VOL])
    wait(lambda: not app.busy() and getattr(app, "volume_report", None), qa)


def qa():
    app.update()
    win = app._volwin
    tv, data = win._trees["First use"]
    levels = [data[i].get("level") for i in tv.get_children()]
    rank = {"bad": 0, "warn": 1, "info": 2, "ok": 3}
    check("QA/QC rows worst first", levels == sorted(levels, key=lambda l: rank.get(l, 4)), levels[:8])
    r1 = app.qa_next_fix()
    r2 = app.qa_next_fix()
    check("Next fix walks the red rows", r1 and r2 and r1[1].get("level") == "bad" and r2[1].get("level") == "bad" and r1[1] is not r2[1],
          (r1 and r1[1].get("term"), r2 and r2[1].get("term")))
    check("the fix is on the status line", app.status.cget("text").startswith("Fix:"), app.status.cget("text")[:60])
    print(f"GUI RHYTHM {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
    app.after(200, app.on_close)


app.after(900, go)
app.mainloop()
