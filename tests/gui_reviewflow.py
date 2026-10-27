"""2.47.0 Acronyms review keeps your place: X (Not a term) on a row in the middle of the list goes to the next row, with
no jump to the top; A does the same; the preview follows the selected row (clicked, or moved to by X, A or Space);
Not a term in the effort list (home) keeps the list where it was and moves to the next row."""
import os, sys, tempfile, csv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
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
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1500x900+0+0")


def wait_scan(then):
    if app.btn_cancel.winfo_ismapped() or app.busy():
        app.after(400, lambda: wait_scan(then)); return
    then()


def step1():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save(); app.efforts.put("Kestrel", path=LIST)
    assert app.open_effort("Kestrel")
    app.start_batch(FILES); app.after(500, lambda: wait_scan(step2))


def step2():
    app.shell_go("acronyms", "review"); app.update()
    if not app.preview_var.get():
        app.preview_var.set(True); app.toggle_preview()
    tv = app.tree
    rows = list(tv.get_children())
    check("the scan found enough terms", len(rows) >= 8, len(rows))
    mid = rows[len(rows) // 2]
    tv.selection_set(mid); tv.focus(mid); tv.see(mid); app.update()
    check("the preview shows the clicked row", app.preview.term == mid, (app.preview.term, mid))
    nxt = rows[rows.index(mid) + 1]
    app.rv_reject(); app.update()
    sel = tv.selection()
    check("X goes to the next row, not the top of the list", sel and sel[0] == nxt, (sel, nxt, rows[0]))
    check("the preview follows to that row", app.preview.term == nxt, (app.preview.term, nxt))
    rows2 = list(tv.get_children())
    after = rows2[rows2.index(nxt) + 1]
    app.rv_add(); app.update()
    sel = tv.selection()
    check("A goes to the next row too", sel and sel[0] == after and app.preview.term == after, (sel, after, app.preview.term))
    # F: an alt form of another term, then the next row
    rows3 = list(tv.get_children())
    t3 = tv.selection()[0]
    after3 = rows3[rows3.index(t3) + 1]
    prim = next(t for t in rows3 if t != t3 and t not in (after3,))
    app.rv_alt(primary=prim); app.update()
    check("F: alt form of another term, then the next row", t3 in app.effort.alts(prim) and tv.selection() and tv.selection()[0] == after3,
          (app.effort.alts(prim), tv.selection(), after3))
    w = app.rv_alt(); app.update()
    check("F with no term given asks which term (likely ones first)", w is not None and w._api["var"].get(), w and w._api["var"].get())
    w.destroy()
    # the effort list (home): Not a term moves down, no jump
    app.shell_go("acronyms", "approve"); app.update()
    for t in list(app.results)[:12]:
        if t not in app.effort.rows:
            app.add_to_effort([t])
    app.home_filter.set("Proposed"); app.home_refresh(); app.update()
    ht = app.home_tree
    hr = list(ht.get_children())
    if len(hr) >= 4:
        m = hr[len(hr) // 2]
        ht.selection_set(m); ht.see(m); app.update()
        app.home_set_status("Rejected"); app.update()
        hs = ht.selection()
        check("Not a term in the effort list moves to the next row", hs and hs[0] == hr[hr.index(m) + 1], (hs, hr[hr.index(m) + 1]))
        h1 = ht.selection()[0]
        hr2 = list(ht.get_children())
        tgt = next(t for t in hr2 if t != h1)
        app.home_alt_of(primary=tgt); app.update()
        check("Effort list > Alt form of...: folds into the other term", h1 in app.effort.alts(tgt) and h1 not in app.effort.rows,
              (app.effort.alts(tgt), h1 in app.effort.rows))
    else:
        check("enough proposed terms in the effort list", False, len(hr))
    n = sum(checks)
    print(f"GUI REVIEWFLOW PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI REVIEWFLOW FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(500, step1)
app.mainloop()
