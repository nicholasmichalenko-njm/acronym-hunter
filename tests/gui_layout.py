"""2.9.0 layout: menu bar (every menu fills, state-dependent ones rebuild), sidebar hide/show (button, View menu, Ctrl+B),
the choice persists, menu clicks log only internal names, the action bar fits a 1280 px window."""
import os, sys, tempfile, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, diag
from tkinter import messagebox
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a)
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "s.json")
app = A.AcronymAppGUI(); app.geometry("1280x760+0+0")
res = {}


def go():
    app.update()
    mb = app.menubar
    labels = [mb.entrycget(i, "label") for i in range(mb.index("end") + 1)]
    counts = {}
    for i, lab in enumerate(labels):
        sub = app.nametowidget(mb.entrycget(i, "menu"))
        pc = sub.cget("postcommand")
        if pc:
            app.tk.eval(pc)                       # what Tk runs when the menu opens
        counts[lab] = sub.index("end") + 1 if sub.index("end") is not None else 0
    print("menus:", counts)
    # sidebar: button, View menu variable, Ctrl+B
    app.btn_hide_side.invoke(); app.update()
    hidden = len(app.body.panes()) == 1 and app.btn_show_side.winfo_ismapped()
    saved = json.load(open(A.SETTINGS_FILE)).get("sidebar")
    app.side_var.set(True); app.toggle_sidebar(var=True); app.update()
    shown = len(app.body.panes()) == 2
    app.focus_force(); app.update()
    app.event_generate("<Control-b>"); app.update()
    ctrl_b = len(app.body.panes()) == 1
    app.toggle_sidebar(); app.update()
    print("hide button:", hidden, "| saved off:", saved is False, "| View menu shows:", shown, "| Ctrl+B hides:", ctrl_b)
    # a menu command logs its internal name only
    before = len(diag.recent_activity(200))
    v = app.nametowidget(mb.entrycget(labels.index("View"), "menu"))
    for i in range(v.index("end") + 1):
        if v.type(i) == "command" and v.entrycget(i, "label") == "Larger text":
            v.invoke(i)
    last = diag.recent_activity(3)
    logged = any(e.get("action") == "menu" and e.get("w") == "view_text_larger" for e in last)
    print("menu logged:", logged, "| font now:", app.font_size)
    # action bar fits at 1280
    right = app.btn_exc.winfo_rootx() + app.btn_exc.winfo_width()
    fits = app.btn_exc.winfo_ismapped() and right <= app.winfo_rootx() + app.winfo_width()
    print("Exclude visible at 1280:", fits)
    res["ok"] = (labels == ["File", "Edit", "Effort", "Compliance", "Tools", "View", "Help"] and all(n >= 1 for n in counts.values())
                 and counts["Effort"] >= 5 and hidden and saved is False and shown and ctrl_b and logged and fits)
    print("GUI LAYOUT", "PASS" if res["ok"] else "FAIL")
    app.destroy()


app.after(1500, go); app.mainloop()
