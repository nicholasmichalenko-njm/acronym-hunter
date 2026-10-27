"""2.47.0 after a crash the app opens where you were: the effort, the Compliance page at Assign, and the same sentence
selected (the app is closed without saving anything, as a crash would, then started again)."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, compliance as C, pdfmini
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
PDF = pdfmini.write(os.path.join(CDIR, "RFP.pdf"), [
    ["L.4 TECHNICAL VOLUME", "The Offeror shall describe its thermal design approach.",
     "The Offeror shall provide a risk register.", "The Offeror should keep the volume under 30 pages."]])
checks = []
state = {}


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def first_run(app):
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    mpath = os.path.join(tmp, "Kestrel", "Kestrel_Matrix.xlsx")
    M = C.Matrix(mpath, "Kestrel")
    heads = []
    M.items = C.extract([("RFP.pdf", A.typed_chunks(PDF))], heads)
    M.headings, M.sources = heads, [["RFP.pdf", "", "2026-10-27", PDF]]
    M.save()
    app.ws.set("compliance_path", mpath)
    app.open_compliance(show=False); app.update()
    app._c_load(mpath, quiet=True); app._c_refresh()
    app.shell_go("compliance", "decide"); app.update()
    target = app.matrix.items[2]["id"]
    app._cp_select(target); app.update()
    app.save_resume_now()
    state["target"] = target
    app.after(200, app.destroy)                      # a crash: nothing else is saved, nothing released


app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")
app.after(400, first_run, app)
app.mainloop()

app2 = A.AcronymAppGUI()                             # started again: it resumes the last effort by itself
app2.geometry("1400x900+0+0")


def second_run():
    for _ in range(20):
        app2.update()
    check("the effort is open again", app2.effort is not None and app2.effort.name == "Kestrel")
    check("on the Compliance page at Assign", getattr(app2, "shell_feature", "") == "compliance" and getattr(app2, "shell_step", "") == "decide",
          (getattr(app2, "shell_feature", ""), getattr(app2, "shell_step", "")))
    sel = app2._c_selected() if app2.matrix is not None else []
    check("the same sentence is selected in Assign", sel and sel[0]["id"] == state["target"], (sel and sel[0]["id"], state["target"]))
    n = sum(checks)
    print(f"GUI CRASHRESUME PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI CRASHRESUME FAIL ({n}/{len(checks)})")
    app2.after(300, app2.destroy)


app2.after(1500, second_run)
app2.mainloop()
