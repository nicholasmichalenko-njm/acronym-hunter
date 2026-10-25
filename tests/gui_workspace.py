"""2.11.0 effort profiles in the app: two efforts never share results or choices; switching saves and restores results,
filters, selection and the compliance window; unsaved matrix and Effort List changes come back after a failed save;
a foreign lock asks first; archive hides an effort; a restart resumes the last effort."""
import os, sys, tempfile, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"   # no first-start wizard during tests
import app_gui as A, compliance as C, effort as E, workspace as W
from tkinter import messagebox, simpledialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
answers = {"askyesno": True}
asked = []
messagebox.showinfo = lambda *a, **k: None
messagebox.showwarning = lambda *a, **k: print("WARNING BOX:", a[:2])
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
messagebox.askyesno = lambda *a, **k: (asked.append(a[0] if a else ""), answers["askyesno"])[1]
messagebox.askretrycancel = lambda *a, **k: False
simpledialog.askstring = lambda *a, **k: "J. Smith"
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
FILES = [os.path.join(A.BASE_DIR, "test_samples", f) for f in ("Kestrel_Technical_Volume.docx", "Kestrel_Design_Note.docx")]
LIST_A = os.path.join(tmp, "Alpha", "Alpha_Effort_List.xlsx")
LIST_B = os.path.join(tmp, "Bravo", "Bravo_Effort_List.xlsx")
MATRIX = os.path.join(tmp, "Alpha", "Alpha_Matrix.xlsx")
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


def setup_efforts(app):
    for name, path in (("Alpha", LIST_A), ("Bravo", LIST_B)):
        L = E.EffortList(path, name); L.pending = True; L.save()
        app.efforts.put(name, path=path, first_use="volume")
    heads = []
    M = C.Matrix(MATRIX, "Alpha matrix")
    M.items = C.extract([(f, A.typed_chunks(os.path.join(RFP, f))) for f in sorted(os.listdir(RFP))], heads)
    M.headings = heads
    M.save()


app = A.AcronymAppGUI()
st = {"phase": 0}


def wait_scan(then):
    if app.btn_cancel.winfo_ismapped() or app.busy():
        app.after(400, lambda: wait_scan(then)); return
    then()


def step1():
    setup_efforts(app); app.refresh_effort_bar()
    check("switcher lists both efforts", {"Alpha", "Bravo"} <= set(app.opt_effort.cget("values")))
    assert app.open_effort("Alpha")
    check("title shows the effort", "Alpha" in app.title(), app.title())
    app.start_batch(FILES)
    app.after(500, lambda: wait_scan(step2))


def step2():
    n = len(app.results)
    check("scan in Alpha found terms", n > 5, n)
    term = sorted(app.results)[0]
    app.save_choice(term, "Alpha's choice")
    app.search_var.set(term[:2]); app.populate_table()
    app.tree.selection_set(term); app.on_select(None); app.update()
    app.ws.set("compliance_path", MATRIX)
    cw = app.open_compliance(); cw.update()
    check("matrix opened for Alpha", app.matrix is not None and app.matrix.path == MATRIX)
    first = app.matrix.items[0]["id"]
    cw.f_dec.set("All"); app._c_fill()
    cw.tv.selection_set(first); app._c_show(); app.update()
    st.update(term=term, n=n, first=first)
    # an unsaved compliance change while Excel holds the workbook
    real_save = C.Matrix.save
    C.Matrix.save = lambda self: (_ for _ in ()).throw(C.Locked(self.path))
    app.matrix.items[0]["decision"] = "Keep"; app.matrix.log(first, "decision Keep"); app._c_changed()
    app.update(); app.after(700, lambda: step3(real_save))


def step3(real_save):
    rec = os.listdir(app.ws.p("recovery"))
    check("matrix recovery copy written right after the change", any(f.startswith("matrix_") for f in rec), rec)
    app.flush_session(); app.save_resume_now()
    # Effort List change that cannot be saved (Excel has it open)
    real_list_save = E.EffortList.save
    E.EffortList.save = lambda self: (_ for _ in ()).throw(E.ListLocked(self.path))
    app.add_to_effort([st["term"]])
    check("list change kept pending", app.effort.pending)
    E.EffortList.save = real_list_save
    app.effort.pending = False             # as if the app crashed: the change only lives in the recovery copy
    assert app.open_effort("Bravo")
    C.Matrix.save = real_save
    check("Bravo starts empty", not app.results and app.matrix is None, len(app.results))
    check("Bravo has no Alpha choices", app.load_choices() == {}, app.load_choices())
    check("Alpha's compliance window closed on switch", app._cwin is None)
    app.save_choice(st["term"], "Bravo's choice")
    asked.clear()
    assert app.open_effort("Alpha")
    app.update()
    check("Alpha results restored", len(app.results) == st["n"], len(app.results))
    check("Alpha filter restored", app.search_var.get() == st["term"][:2], app.search_var.get())
    check("Alpha selection restored", app.selected_term == st["term"], app.selected_term)
    check("Alpha choice is its own", app.load_choices().get(st["term"]) == "Alpha's choice", app.load_choices())
    check("recovery offered for the list and the matrix", sum("Recover" in a for a in asked) == 2, asked)
    check("list change recovered and saved", st["term"] in E.EffortList(LIST_A).load().rows)
    cw = app._cwin
    check("compliance window reopened", cw is not None and cw.winfo_exists())
    check("matrix change recovered", app.matrix is not None and app.matrix.items[0]["decision"] == "Keep")
    check("compliance row reselected", cw is not None and cw.tv.selection() and cw.tv.selection()[0] == st["first"],
          cw.tv.selection() if cw else None)
    app._c_save_now()
    check("saved matrix holds the change", C.Matrix(MATRIX).load().items[0]["decision"] == "Keep")
    check("backups kept", any(r[1] == "effort" for r in app.ws.backups()) and any(r[1] == "matrix" for r in app.ws.backups()),
          [r[1] for r in app.ws.backups()])
    # foreign lock on Bravo
    bws = W.Workspace(W.data_dir_for(LIST_B), "Bravo")
    W.write_json(bws.p("lock.json"), {"user": "colleague", "computer": "OTHER-PC", "pid": 1,
                                      "time": __import__("datetime").datetime.now().isoformat(timespec="seconds")})
    answers["askyesno"] = False
    check("foreign lock: stays on Alpha when declined", not app.open_effort("Bravo") and app.effort.name == "Alpha")
    answers["askyesno"] = True
    check("foreign lock: opens when confirmed", app.open_effort("Bravo") and app.effort.name == "Bravo")
    # restore an earlier version of Bravo's list
    w = app.restore_dialog(); w.update(); w.destroy()
    # archive Alpha
    assert app.open_effort("Alpha")
    app.archive_effort()
    check("archived effort hidden from the switcher", "Alpha" not in app.opt_effort.cget("values") and app.effort is None,
          app.opt_effort.cget("values"))
    app.unarchive_effort("Alpha")
    check("unarchive reopens it", app.effort is not None and app.effort.name == "Alpha")
    app.on_close()                       # saves and releases; then a new window resumes Alpha
    app2 = A.AcronymAppGUI()
    def after_start():
        check("restart resumes the last effort", app2.effort is not None and app2.effort.name == "Alpha" and len(app2.results) == st["n"],
              (app2.effort.name if app2.effort else None, len(app2.results)))
        check("restart says which effort", "Resumed Alpha" in app2.status.cget("text"), app2.status.cget("text")[:60])
        ok = all(checks.values())
        print("GUI WORKSPACE", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
        app2.on_close()
    app2.after(1500, after_start)
    app2.mainloop()


app.after(1500, step1)
app.mainloop()
