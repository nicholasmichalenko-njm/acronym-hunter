"""Compliance window, placement learning across proposals (2.30.0): learned top 3 in the detail pane, click to map,
Suggest sections uses strong learned matches, the self-check in Learn from decisions, the synonym list, AI and ML off."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, complearn as CL, placelearn as PL
import test_placelearn as T
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
said = []
messagebox.showinfo = lambda *a, **k: said.append(a[1] if len(a) > 1 else "")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


# the team placed rows in five earlier proposals (outlines titled and numbered differently)
LP = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
L0 = CL.Learner(LP)
for i in range(1, 6):
    o, items = T.proposal(i)
    L0.placer().learn(f"earlier{i}", items, o)
L0.save()

KEYS = ("id", "text", "lead", "file", "page", "section", "section_title", "actor", "type", "strength", "suggest", "modal",
        "xrefs", "compound", "decision", "map", "owner", "status", "response_page", "notes", "links", "learned", "new", "context")
outline, items = T.proposal(42)
for it in items:
    for k in KEYS:
        it.setdefault(k, "" if k != "compound" else False)
    it["decision"] = "Keep"
truth = {it["id"]: it["map"] for it in items}
for it in items:
    it["map"] = ""
M = C.Matrix(os.path.join(tmp, "New_Compliance_Matrix.xlsx"))
M.items, M.outline = items, outline
M.save()
app = A.AcronymAppGUI()


def go():
    win = app.open_compliance(); win.update()
    app._c_load(M.path, quiet=True); app._c_refresh(); win.update()
    Mx = app.matrix
    tv = win.tv
    thermal = next(it for it in Mx.items if "temperature" in it["text"] or "heater" in it["text"])
    tv.selection_set(thermal["id"]); win.update(); app._c_show(); win.update()
    kids = win.d_learn.winfo_children()
    btns = [w for w in kids if w.winfo_class() != "Label" and hasattr(w, "cget") and str(w.cget("text"))[:2] in ("1.", "2.", "3.")]
    head = kids[0].cget("text") if kids else ""
    check("detail pane shows the top 3 from past proposals", win.d_learn.winfo_ismapped() and len(btns) == 3, head)
    check("the right section is first", btns and truth[thermal["id"]] in btns[0].cget("text"), btns and btns[0].cget("text"))
    btns[0].invoke(); win.update()
    check("clicking a learned section maps the row", app._c_item(thermal["id"])["map"] == truth[thermal["id"]])
    app.compliance_suggest_all(); win.update()
    mapped = [it for it in Mx.items if it["map"]]
    right = sum(1 for it in mapped if it["map"] == truth[it["id"]])
    for it in mapped:
        if it["map"] != truth[it["id"]]:
            print("  WRONG", it["text"][:60], "->", it["map"], "| truth", truth[it["id"]], "| rule", C.suggest_map(it, Mx.outline, C.word_df(Mx.items))[0], "| learned", app._c_learned_places(it)[:2])
    check("Suggest sections fills strong learned matches", len(mapped) >= len(Mx.items) * 0.6 and right >= len(mapped) * 0.9,
          f"{len(mapped)} of {len(Mx.items)} mapped, {right} right")
    for it in Mx.items:
        it["map"] = truth[it["id"]]
    L = app._c_learner(); pl0 = L.placer()          # 2.55.0: the training team learns this; a Knowledge Pack brings it
    chk = pl0.check(app._c_learner().source_id(Mx.path), Mx.items, Mx.outline)
    L.learn(Mx.path, Mx.items, Mx.outline); L.save(); app._c_refresh(); win.update()
    msg = app._c_place_text(chk)
    check("the placement self-check still reports", "top 3" in msg and "Placement across proposals" in msg, msg[-260:])
    pl = app._c_learner().placer()
    check("this matrix's placements were learned", pl.matrices() == 6, pl.matrices())
    check("Outline tab shows the placement summary", "placed rows from 6 matrices" in win.o_learn.cget("text"), win.o_learn.cget("text")[:90])
    # synonym list: dialog opens with the starter list; saving through it reloads the learner
    w = app.compliance_synonyms(); w.update()
    check("synonym window opens with the starter list", "solution, approach" in w.box.get("1.0", "end"))
    w.destroy()
    app.compliance_synonyms("thermal, heat, temperature\n")
    check("saved synonyms are used", "~thermal" in app._c_learner().placer().syn.values() and
          os.path.isfile(PL.synonyms_path(A.CONFIG_DIR)))
    # the Knowledge Pack carries the synonym list
    check("Knowledge Packs include the synonym list", "placement_synonyms.csv" in A.PACK_DATA_FILES)
    print(f"GUI PLACEMENT {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
    app.after(200, app.destroy)


app.after(800, go)
app.mainloop()
