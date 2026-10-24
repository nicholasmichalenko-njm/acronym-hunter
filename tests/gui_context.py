"""2.13.0 Meaning from context: a term with two database meanings gets a suggestion from the words around it (shared
words, role and document cues, the long form spelled out in the file); each place can point to a different meaning;
the person accepts it (saved like Apply Choice); the CSV export carries it."""
import os, sys, tempfile, csv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, docxw
from tkinter import messagebox, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.DB_FILE = os.path.join(tmp, "db.csv")
with open(A.DB_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["Term", "Category", "Definition", "Action"])
    for t, d in (("SOW", "Statement of Work"), ("SOW", "Scope of Work"), ("PM", "Program Manager"), ("PM", "Program Management")):
        w.writerow([t, "Acronym", d, "Include"])
messagebox.showinfo = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
OUT = os.path.join(tmp, "out.csv")
filedialog.asksaveasfilename = lambda **k: OUT
PMDOC = os.path.join(tmp, "Roles_and_Plans.docx")
d = docxw.Doc()
d.heading("1 Roles", 1)
d.para("The PM shall approve every change request before work starts.")
d.heading("2 Management", 1)
d.para("Work follows the PM plan and the PM process described in Section 3.")
d.save(PMDOC)
FILES = [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), PMDOC]
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


app = A.AcronymAppGUI()
st = {"tries": 0}


def wait_scan(then):
    if app.btn_cancel.winfo_ismapped() or app.busy():
        app.after(400, lambda: wait_scan(then)); return
    then()


def wait_context():
    st["tries"] += 1
    if "context" not in app.results.get("SOW", {}) and st["tries"] < 60:
        app.after(300, wait_context); return
    step2()


def step2():
    s = app.results["SOW"]
    c = s.get("context") or {}
    check("SOW: context suggests Statement of Work", c.get("definition") == "Statement of Work", c)
    check("SOW: says why", any("spelled out" in x or "nearby" in x for x in c.get("cues", [])), c.get("cues"))
    check("status says a suggestion exists", s["status"] == "CHOOSE DEFINITION (context suggests one)", s["status"])
    p = app.results["PM"]
    by = (p.get("context") or {}).get("by_loc", {})
    means = {v[0] for v in by.values()}
    check("PM: each place can mean something different", means == {"Program Manager", "Program Management"}, by)
    check("PM: no single answer when the places disagree", not (p.get("context") or {}).get("definition")
          and p["status"] == "CHOOSE DEFINITION (meaning differs by place)", p["status"])
    check("PM: definition column shows both meanings", "Program Manager / Program Management" in A.ctx_text(p), A.ctx_text(p))
    app.status_var.set("Context suggests a meaning"); app.populate_table()
    check("filter lists rows with a suggestion", list(app.tree.get_children()) == ["SOW"], app.tree.get_children())
    app.status_var.set(A.STATUS_FILTERS[0]); app.populate_table()
    app.tree.selection_set("SOW"); app.on_select(None); app.update()
    check("Apply Choice box starts on the suggestion", app.combo.get() == "Statement of Work", app.combo.get())
    if not app.preview_var.get():
        app.preview_var.set(True); app.toggle_preview()
    pv = app.preview
    pv.show("PM")
    notes = []
    for i, loc in enumerate(pv.locs):
        pv._show_location(i); app.update(); notes.append(pv.lbl_msg.cget("text"))
    check("preview says what it likely means at each place", any("Program Manager" in n for n in notes)
          and any("Program Management" in n for n in notes), notes)
    app.export_csv()
    rows = {r[0]: r for r in csv.reader(open(OUT, encoding="utf-8-sig"))}
    check("CSV export carries the suggestion", rows["SOW"][-1].startswith("Statement of Work"), rows["SOW"][-1])
    n = app.accept_context(["SOW"])
    s = app.results["SOW"]
    check("accepted: applied and saved like Apply Choice", n == 1 and s["selected_definition"] == "Statement of Work"
          and app.load_choices().get("SOW") == "Statement of Work", (s["status"], app.load_choices()))
    ok = all(checks.values())
    print("GUI CONTEXT", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.on_close()


def step1():
    app.start_batch(FILES); app.after(500, lambda: wait_scan(wait_context))


app.after(1500, step1)
app.mainloop()
