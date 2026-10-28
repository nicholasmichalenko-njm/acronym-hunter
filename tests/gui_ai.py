"""2.55.0 What runs where, with no AI and ML switch and no generative AI: labels (No AI, ML) on every sidebar section
with a ? panel; no switch in the top bar; picture text is always read; the state line says No generative AI; the
compliance learned column comes from the installed Knowledge Pack learning (no Learn from decisions, no Team
learning); the summary for security saves and names no generative AI part."""
import os, sys, tempfile, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"   # no first-start wizard during tests
import app_gui as A, compliance as C, effort as E, ai_stack as S, diag
from tkinter import messagebox, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
infos = []
messagebox.showinfo = lambda *a, **k: infos.append(a[1] if len(a) > 1 else "")
messagebox.showwarning = lambda *a, **k: print("WARNING BOX:", a[:2])
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
messagebox.askyesno = lambda *a, **k: True
messagebox.askretrycancel = lambda *a, **k: False
PIC = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_System_Diagram.png")
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
LIST_A = os.path.join(tmp, "Alpha", "Alpha_Effort_List.xlsx")
LIST_B = os.path.join(tmp, "Bravo", "Bravo_Effort_List.xlsx")
MATRIX = os.path.join(tmp, "Alpha", "Alpha_Matrix.xlsx")
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
    for name, path in (("Alpha", LIST_A), ("Bravo", LIST_B)):
        L = E.EffortList(path, name); L.pending = True; L.save()
        app.efforts.put(name, path=path, first_use="volume")
    M = C.Matrix(MATRIX, "Alpha matrix")
    M.items = C.extract([(f, A.typed_chunks(os.path.join(RFP, f))) for f in sorted(os.listdir(RFP))])
    for i, it in enumerate(M.items):
        it["decision"] = "Keep" if i % 3 else "Drop"
    M.save()
    assert app.open_effort("Alpha")
    badges = [(b.cget("text"), cls) for b, cls in app._ai_badges]
    check("every feature has its labels, none Gen AI", len(badges) >= 6 and ("ML", "ml") in badges and ("No AI", "none") in badges
          and not any("Gen" in t for t, _c in badges), badges)
    check("no AI and ML switch", not hasattr(app, "sw_ai") and not hasattr(app, "toggle_ai_ml") and A.ai_ml_on())
    t = app.lbl_aistate.cget("text")
    check("state line: offline, the effort, no generative AI", "Offline" in t and "Alpha" in t and "No generative AI" in t, t)
    check("no math reader anywhere", not hasattr(A, "MATH_DIR") and not hasattr(A, "run_math_reader") and not hasattr(app, "read_equations"))
    w = app.show_stack("scan"); w.update()
    check("? panel opens with its stack", w.winfo_exists())
    w.destroy()
    w = app.show_ai_difference(); w.update(); w.destroy()
    m = A.tk.Menu(app); app.show_tools_menu(m)
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) == "command"]
    check("Tools has no equation reader entry", not any("equation" in l.lower() for l in labels), labels)
    app.start_batch([PIC]); app.after(500, lambda: wait_scan(step2))


def step2():
    terms = [k for k in app.results if not k.startswith("[")]
    no_tess = any("OCR engine" in k for k in app.results) and not os.path.isdir(os.path.join(A.BASE_DIR, "vendor", "tesseract"))
    check("picture text is always read (never skipped as AI and ML off)", (terms or no_tess)
          and not any("AI and ML" in k for k in app.results), list(app.results)[:5])
    import complearn as CL
    L = CL.Learner(os.path.join(A.CONFIG_DIR, "compliance_learned.json"))   # what an installed Knowledge Pack holds
    M = C.Matrix(MATRIX).load()
    L.learn("other.xlsx", M.items, M.outline); L.save()
    app._learner = None
    app.ws.set("compliance_path", MATRIX)
    cw = app.open_compliance(); cw.update()
    app._c_refresh(); cw.update()
    filled = sum(1 for it in app.matrix.items if it.get("learned"))
    check("learned column fills from the installed learning", filled > 0, filled)
    check("no Learn from decisions, no Team learning", not hasattr(cw, "btn_learn") and not hasattr(cw, "chk_team")
          and not hasattr(app, "compliance_learn") and "Knowledge Packs" in cw.lbl_ai.cget("text"), cw.lbl_ai.cget("text"))
    before = app._c_learner().summary()["decisions"]
    app.matrix.items[0]["decision"] = "Drop" if app.matrix.items[0]["decision"] == "Keep" else "Keep"
    app._c_save_now()
    app._learner = None
    check("saving does not learn on this PC", app._c_learner().summary()["decisions"] == before)
    out = os.path.join(tmp, "summary.txt")
    filedialog.asksaveasfilename = lambda **k: out
    w = app.show_what_runs(); w.update(); w._save(); w.destroy()
    txt = open(out, encoding="utf-8").read() if os.path.isfile(out) else ""
    check("security summary saved: rules, ML, no generative AI", "Tesseract" in txt and "No AI" in txt and "no network" in txt.lower()
          and "No generative AI" in txt and "Granite" not in txt and "switch" not in txt.lower(), len(txt))
    check("stack list covers every sidebar section", set(S.SIDEBAR_SECTIONS.values()) <= set(S.FEATURES))
    ok = all(checks.values())
    print("GUI AI", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.on_close()


app.after(1500, step1)
app.mainloop()
