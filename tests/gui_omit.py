"""2.13.0 Omit list and duplicate meanings.
Omit list: a term added to it (company name, location...) is found on every scan, says "Found in omit list: <why>",
is never flagged for first use, stays out of the CSV export and the Not in effort list filter, and survives Scan Again.
The Omit list window adds, flags the same meaning twice, accepts a second meaning, pastes many and removes.
Duplicates: one acronym may have several database rows when the meanings differ; the same meaning is flagged."""
import os, sys, tempfile, csv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
from tkinter import messagebox, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.DB_FILE = os.path.join(tmp, "db.csv")
with open(A.DB_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["Term", "Category", "Definition", "Action"]); w.writerow(["SOW", "Acronym", "Statement of Work", "Include"])
infos = []
messagebox.showinfo = lambda *a, **k: infos.append(a[1] if len(a) > 1 else "")
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
OUT = os.path.join(tmp, "out.csv")
filedialog.asksaveasfilename = lambda **k: OUT
FILES = [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")]
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


def db():
    return [r for r in csv.DictReader(open(A.DB_FILE, encoding="utf-8-sig"))]


app = A.AcronymAppGUI()
st = {}


def wait_scan(then):
    if app.btn_cancel.winfo_ismapped() or app.busy():
        app.after(400, lambda: wait_scan(then)); return
    then()


def step1():
    app.start_batch(FILES); app.after(500, lambda: wait_scan(step2))


def step2():
    # --- database rule: several meanings fine, the same meaning flagged ---
    check("same meaning is a duplicate", A.db_add("SOW", "Acronym", "statement of work", "Include")[0] == "duplicate")
    check("different meaning is added", A.db_add("SOW", "Acronym", "Scope of Work", "Include")[0] == "added"
          and sum(1 for r in db() if r["Term"] == "SOW") == 2)
    # --- omit list from the results ---
    cands = [t for t, d in app.results.items() if A.status_kind(d["status"]) == "candidate" and d["category"].startswith("Acronym")]
    term = sorted(cands)[0]; st["term"] = term
    app.tree.selection_set(term); app.update()
    w = app.mark_known([term]); w.update()
    w._api["defn"].delete(0, "end"); w._api["defn"].insert(0, "Kestrel Space Systems"); w._api["reason"].set("Company or organization")
    w._api["ok"](); app.update()
    d = app.results[term]
    check("says Found in omit list and why", d["status"] == "Found in omit list: Company or organization", d["status"])
    row = [r for r in db() if r["Term"] == term]
    check("saved: Action Omit, reason column", row and row[0]["Action"] == "Omit" and row[0]["Omit reason"] == "Company or organization", row)
    check("not flagged for first use", not A.first_use_lines(d))
    app.status_var.set("Not in effort list"); app.populate_table()
    check("out of Not in effort list", term not in app.tree.get_children())
    app.status_var.set("Found in omit list"); app.populate_table()
    check("Status > Found in omit list", list(app.tree.get_children()) == [term], app.tree.get_children())
    app.status_var.set(A.STATUS_FILTERS[0]); app.populate_table()
    app.export_csv()
    exported = [r[0] for r in csv.reader(open(OUT, encoding="utf-8-sig"))][1:]
    check("left off the CSV export", term not in exported and len(exported) > 3, len(exported))
    # --- Add Item: another meaning, and the same meaning flagged ---
    aw = app.open_add_item(); api = aw._add_api
    api["term"].insert(0, "SOW"); api["defn"].insert(0, "Statement of Work"); api["dest"].set("db"); api["add"](); aw.update()
    check("Add Item flags a meaning the term already has", "already has the meaning" in api["msg"].cget("text"), api["msg"].cget("text"))
    api["defn"].delete(0, "end"); api["defn"].insert(0, "Sequence of Work"); api["add"](); aw.update()
    s = app.results["SOW"]
    check("Add Item adds another meaning to a listed term", "Sequence of Work" in s["definitions"] and A.status_kind(s["status"]) == "choice"
          and sum(1 for r in db() if r["Term"] == "SOW") == 3, (s["status"], s["definitions"]))
    aw.destroy()
    app.scan_again(); app.after(500, lambda: wait_scan(step3))


def step3():
    term = st["term"]
    d = app.results[term]
    check("still on the omit list after Scan Again", d.get("known") and d["status"] == "Found in omit list: Company or organization"
          and d["selected_definition"] == "Kestrel Space Systems", d["status"])
    check("Scan Again offers every meaning", len(app.results["SOW"]["definitions"]) == 3, app.results["SOW"]["definitions"])
    # --- Omit list window ---
    ow = app.open_omit_list(); ow.update(); api = ow._api
    n0 = len(api["tree"].get_children())
    api["term"].insert(0, "COS"); api["defn"].insert(0, "Colorado Springs"); api["why"].set("Location"); api["add"]()
    check("window adds", len(api["tree"].get_children()) == n0 + 1)
    api["term"].insert(0, "COS"); api["defn"].insert(0, "colorado springs"); api["add"]()
    check("window flags the same meaning", "already has this meaning" in api["msg"].cget("text") and len(api["tree"].get_children()) == n0 + 1,
          api["msg"].cget("text"))
    api["term"].delete(0, "end"); api["defn"].delete(0, "end")
    api["term"].insert(0, "COS"); api["defn"].insert(0, "Cost of Sales"); api["why"].set("Other"); api["add"]()
    check("window accepts a second meaning", len(api["tree"].get_children()) == n0 + 2)
    box = api["paste"](); box.update()
    box._text.insert("1.0", "ULA, United Launch Alliance, Company or organization\nCOS, Colorado Springs\nDEN\tDenver\tLocation\n")
    box._go()
    check("paste adds new ones and skips the duplicate", len(api["tree"].get_children()) == n0 + 4 and "1 already on the list" in api["msg"].cget("text"),
          api["msg"].cget("text"))
    reasons = {r["Term"] + "|" + r["Definition"]: r["Omit reason"] for r in db() if r["Action"] == "Omit"}
    check("pasted reasons kept", reasons.get("DEN|Denver") == "Location" and reasons.get("ULA|United Launch Alliance") == "Company or organization", reasons)
    check("a duplicate changes nothing (its reason stays)", reasons.get("COS|Colorado Springs") == "Location", reasons.get("COS|Colorado Springs"))
    first = [i for i in api["tree"].get_children() if api["tree"].item(i, "values")[0] == "DEN"]
    api["tree"].selection_set(first); api["remove"]()
    check("remove takes it off", not any(r["Term"] == "DEN" for r in db()))
    ow.destroy()
    app.tree.selection_set(term); app.unmark_known([term]); app.update()
    check("take off the omit list from the results", not app.results[term].get("known"))
    ok = all(checks.values())
    print("GUI OMIT", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.on_close()


app.after(1500, step1)
app.mainloop()
