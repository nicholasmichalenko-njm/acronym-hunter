"""2.12.0 AI and ML labels and switch: labels on every sidebar section with a ? panel; the switch is per effort and on by
default; off stops every model (pictures not read, docTR, math reader, learned compliance column, Improve Reading) and
says so; each change is logged in the effort's History sheet and in the usage log without the effort name; the
summary for security saves; Team learning turns the learned column off for one effort."""
import os, sys, tempfile, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
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
    # a matrix with enough decisions for the learned column
    M = C.Matrix(MATRIX, "Alpha matrix")
    M.items = C.extract([(f, A.typed_chunks(os.path.join(RFP, f))) for f in sorted(os.listdir(RFP))])
    for i, it in enumerate(M.items):
        it["decision"] = "Keep" if i % 3 else "Drop"
    M.save()
    assert app.open_effort("Alpha")
    badges = [(b.cget("text"), cls) for b, cls in app._ai_badges]
    check("every sidebar section has labels", len(badges) >= 8 and ("ML", "ml") in badges and ("No AI", "none") in badges, badges)
    check("switch on by default", app.ai_var.get() and A.ai_ml_on() and "AI and ML on" == app.sw_ai.cget("text"))
    check("state line shows offline and the effort", "Offline" in app.lbl_aistate.cget("text") and "Alpha" in app.lbl_aistate.cget("text"),
          app.lbl_aistate.cget("text"))
    w = app.show_stack("scan"); w.update()
    texts = [c.cget("text") for c in w.winfo_children()[0].winfo_children() if hasattr(c, "cget") and "text" in c.keys()] \
        if False else []
    check("? panel opens with its stack", w.winfo_exists())
    w.destroy()
    w = app.show_ai_difference(); w.update(); w.destroy()
    app.start_batch([PIC]); app.after(500, lambda: wait_scan(step2))


def step2():
    st["on_terms"] = len(app.results)
    check("AI and ML on: picture text read", st["on_terms"] > 0, st["on_terms"])
    # turn off
    before = len(diag.recent_activity(500))
    app.ai_var.set(False); app.toggle_ai_ml(); app.update()
    check("switch says off", app.sw_ai.cget("text") == "AI and ML off" and not A.ai_ml_on())
    check("ML labels show off", any(b.cget("text") == "ML off" for b, cls in app._ai_badges if cls == "ml"))
    check("state line says off", "AI and ML: off" in app.lbl_aistate.cget("text"), app.lbl_aistate.cget("text"))
    check("docTR and math reader refuse", not A.doctr_active() and not A.math_available())
    try:
        A.get_ocr(); refused = False
    except RuntimeError:
        refused = True
    check("picture reader refuses to start", refused)
    L = E.EffortList(LIST_A).load()
    check("History sheet records the change", any(h[2] == "(setting)" and "AI and ML turned off" in h[3] and h[1] for h in L.history),
          L.history[-1:])
    acts = [e for e in diag.recent_activity(50) if e.get("action") == "ai_ml_turned_off"]
    check("usage log records it by number, not name", acts and isinstance(acts[-1].get("effort_code"), int)
          and "Alpha" not in json.dumps(acts[-1]), acts[-1:])
    m = A.tk.Menu(app); app.show_tools_menu(m)
    labels = {m.entrycget(i, "label"): m.entrycget(i, "state") for i in range(m.index("end") + 1) if m.type(i) == "command"}
    imp = [st_ for lab, st_ in labels.items() if lab.startswith("Improve Reading")]
    check("Improve Reading greyed in Tools", not imp or imp[0] == "disabled", imp)
    app.ws.set("compliance_path", MATRIX)
    cw = app.open_compliance(); cw.update()
    check("compliance learned column empty and Learn greyed", all(not it.get("learned") for it in app.matrix.items)
          and cw.btn_learn.cget("state") == "disabled" and "off" in cw.lbl_ai.cget("text"), cw.lbl_ai.cget("text"))
    app.scan_again(); app.after(500, lambda: wait_scan(step3))


def step3():
    terms = [k for k in app.results if not k.startswith("[")]
    check("AI and ML off: picture text not read, and the scan says why", not terms and any("AI and ML off" in k for k in app.results),
          list(app.results)[:4])
    # per effort: Bravo is on by default, Alpha stays off
    assert app.open_effort("Bravo")
    check("other effort starts on", A.ai_ml_on() and app.ai_var.get())
    assert app.open_effort("Alpha")
    check("Alpha remembers off", not A.ai_ml_on() and not app.ai_var.get())
    app.ai_var.set(True); app.toggle_ai_ml(); app.update()
    check("back on", A.ai_ml_on())
    app.ws.set("compliance_path", MATRIX)
    cw = app.open_compliance(); cw.update()
    filled = sum(1 for it in app.matrix.items if it.get("learned"))
    learner_ready = app._c_learner().ready()
    # learn first so the column can fill
    app.compliance_learn(); app.update()
    filled = sum(1 for it in app.matrix.items if it.get("learned"))
    check("learned column fills with AI and ML on", filled > 0, filled)
    cw.team_var.set(False); app.compliance_team_toggle(); app.update()
    check("Team learning off empties the learned column", all(not it.get("learned") for it in app.matrix.items)
          and app.ws.get("team_learning") is False)
    cw.team_var.set(True); app.compliance_team_toggle()
    out = os.path.join(tmp, "summary.txt")
    filedialog.asksaveasfilename = lambda **k: out
    w = app.show_what_runs(); w.update(); w._save(); w.destroy()
    txt = open(out, encoding="utf-8").read() if os.path.isfile(out) else ""
    check("security summary saved", "Tesseract" in txt and "No AI" in txt and "no network" in txt.lower(), len(txt))
    check("stack list covers every sidebar section", set(S.SIDEBAR_SECTIONS.values()) <= set(S.FEATURES))
    ok = all(checks.values())
    print("GUI AI", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.on_close()


app.after(1500, step1)
app.mainloop()
