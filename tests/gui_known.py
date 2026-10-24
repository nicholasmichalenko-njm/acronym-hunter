"""2.13.0 Known names: a name marked Known (company, product, program) is recognized and kept in the database with
Action "Known name", shows its own status and colour, is never asked to be defined at first use, stays out of the
Not in effort list filter and the CSV export, survives Scan Again, and can be listed again."""
import os, sys, tempfile, csv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
from tkinter import messagebox, simpledialog, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.DB_FILE = os.path.join(tmp, "db.csv")
with open(A.DB_FILE, "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow(["Term", "Category", "Definition", "Action"])
messagebox.showinfo = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
simpledialog.askstring = lambda *a, **k: "Kestrel Space Systems"
OUT = os.path.join(tmp, "out.csv")
filedialog.asksaveasfilename = lambda **k: OUT
FILES = [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")]
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


app = A.AcronymAppGUI()
st = {}


def wait_scan(then):
    if app.btn_cancel.winfo_ismapped() or app.busy():
        app.after(400, lambda: wait_scan(then)); return
    then()


def step1():
    app.start_batch(FILES); app.after(500, lambda: wait_scan(step2))


def step2():
    cands = [t for t, d in app.results.items() if A.status_kind(d["status"]) == "candidate" and d["category"].startswith("Acronym")]
    term = sorted(cands)[0]
    st["term"] = term
    app.tree.selection_set(term); app.update()
    app.mark_known([term]); app.update()
    d = app.results[term]
    check("marked known: status and definition", d["status"] == A.KNOWN_STATUS and d["selected_definition"] == "Kestrel Space Systems", d["status"])
    check("own colour", "known" in app.tree.item(term, "tags"))
    rows = list(csv.reader(open(A.DB_FILE, encoding="utf-8")))
    check("saved in the database as Known name", any(r[0] == term and r[3] == A.KNOWN_ACTION and r[2] == "Kestrel Space Systems" for r in rows[1:]), rows[1:])
    check("not asked to define at first use", not A.first_use_lines(d))
    app.status_var.set("Not in effort list"); app.populate_table()
    check("left out of Not in effort list", term not in app.tree.get_children())
    app.status_var.set("Known names (not listed)"); app.populate_table()
    check("listed under Known names", list(app.tree.get_children()) == [term], app.tree.get_children())
    app.status_var.set(A.STATUS_FILTERS[0]); app.populate_table()
    app.export_csv()
    exported = [r[0] for r in csv.reader(open(OUT, encoding="utf-8-sig"))][1:]
    check("left off the CSV export", term not in exported and len(exported) > 3, len(exported))
    app.scan_again(); app.after(500, lambda: wait_scan(step3))


def step3():
    term = st["term"]
    d = app.results[term]
    check("still known after Scan Again", d.get("known") and d["status"] == A.KNOWN_STATUS and d["selected_definition"] == "Kestrel Space Systems",
          (d.get("known"), d["status"]))
    app.tree.selection_set(term); app.unmark_known([term]); app.update()
    d = app.results[term]
    rows = list(csv.reader(open(A.DB_FILE, encoding="utf-8")))
    check("listed again: database row back to Include", not d.get("known") and any(r[0] == term and r[3] == "Include" for r in rows[1:]),
          (d["status"], rows[1:]))
    ok = all(checks.values())
    print("GUI KNOWN", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.on_close()


app.after(1500, step1)
app.mainloop()
