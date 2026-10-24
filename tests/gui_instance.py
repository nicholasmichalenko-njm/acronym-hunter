"""2.13.0 Exclude instance vs Exclude term: excluding the place shown in the preview removes only that location; the
term stays with its other locations; it stays excluded after Scan Again; it belongs to the effort; excluding every
instance hides the term (not a database rule); Restore instances brings them back."""
import os, sys, tempfile, csv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, effort as E
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
DB = os.path.join(tmp, "db.csv")
with open(DB, "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow(["Term", "Category", "Definition", "Action"])
A.DB_FILE = DB
messagebox.showinfo = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
messagebox.askyesno = lambda *a, **k: True
FILES = [os.path.join(A.BASE_DIR, "test_samples", f) for f in ("Kestrel_Technical_Volume.docx", "Kestrel_Design_Note.docx")]
LISTS = {n: os.path.join(tmp, n, f"{n}_Effort_List.xlsx") for n in ("Alpha", "Bravo")}
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
    for n, p in LISTS.items():
        L = E.EffortList(p, n); L.pending = True; L.save(); app.efforts.put(n, path=p)
    assert app.open_effort("Alpha")
    app.start_batch(FILES); app.after(500, lambda: wait_scan(step2))


def step2():
    multi = [t for t, d in app.results.items() if len(d.get("locations", [])) >= 2 and app.excludable(t)]
    check("a term found in several places", multi, len(multi))
    term = sorted(multi, key=lambda t: -len(app.results[t]["locations"]))[0]
    locs = list(app.results[term]["locations"])
    st.update(term=term, locs=locs)
    if not app.preview_var.get():
        app.preview_var.set(True); app.toggle_preview()
    app.tree.selection_set(term); app.on_select(None); app.update()
    pv = app.preview
    pv.show(term); pv._show_location(1); app.update()
    gone = pv.locs[1]
    pv.exclude_instance(); app.update()
    d = app.results[term]
    check("only the shown instance leaves", gone not in d["locations"] and len(d["locations"]) == len(locs) - 1, gone)
    check("the term itself stays", not d.get("excluded") and term in app.tree.get_children(), d.get("status"))
    check("restore button shows the count", pv.btn_restore.winfo_manager() == "pack" and "(1)" in pv.btn_restore.cget("text"))
    rows = list(csv.reader(open(DB, encoding="utf-8")))
    check("no database rule written", not any(r and r[0] == term for r in rows[1:]))
    st["gone"] = gone
    app.scan_again(); app.after(500, lambda: wait_scan(step3))


def step3():
    term, gone = st["term"], st["gone"]
    d = app.results[term]
    check("still excluded after Scan Again", gone not in d["locations"] and d.get("excluded_instances") == [gone])
    assert app.open_effort("Bravo")
    app.start_batch(FILES); app.after(500, lambda: wait_scan(step4))


def step4():
    term, gone = st["term"], st["gone"]
    check("other effort keeps every instance", gone in app.results[term]["locations"])
    assert app.open_effort("Alpha")
    d = app.results[term]
    for loc in list(d["locations"]):
        app.exclude_instance(term, loc)
    check("all instances excluded hides the term", d.get("excluded") and d["status"] == "All instances excluded"
          and term not in app.tree.get_children())
    app.restore_instances(term)
    d = app.results[term]
    check("restore brings every instance back", sorted(d["locations"]) == sorted(st["locs"]) and not d.get("excluded"),
          (len(d["locations"]), len(st["locs"])))
    check("restored on disk too", app.ws.instance_excludes() == {})
    ok = all(checks.values())
    print("GUI INSTANCE", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.on_close()


app.after(1500, step1)
app.mainloop()
