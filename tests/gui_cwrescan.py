"""2.50.0 in Compliance: select words in the review text, right-click > Add to compliance words; Rescan with compliance
words finds the sentences that hold them (marked Found by a compliance word), decisions stay; the words show in the
compliance word style; the Compliance words window rescans when the list changes."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, cwords as W
import tkinter as tk
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
said = []
messagebox.showinfo = lambda *a, **k: said.append(a[1] if len(a) > 1 else "")
messagebox.askyesno = lambda *a, **k: True
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
TEXT = ("L.4 Technical Volume\nThe Offeror shall describe the thermal design. The Offeror is responsible for quarterly "
        "program reviews. The program office is located in Colorado. Key personnel are responsible for safety training.")
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
C.set_extra_words([])
M.items = C.extract([("Section L Instructions.docx", [("Page 1", TEXT)])])
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal")
next(it for it in M.items if "safety" in it["text"])["decision"] = "Drop"
M.save()
app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")
menus = []
_orig_popup = tk.Menu.tk_popup
tk.Menu.tk_popup = lambda self, *a, **k: menus.append(self)


class Ev:
    x_root = y_root = 10


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    win = app.open_compliance(); win.update()
    app._c_load(M.path, quiet=True); app._c_refresh(); win.update()
    app.shell_go("compliance", "decide"); app.update()
    resp = next(it for it in app.matrix.items if "quarterly" in it["text"])
    app._cp_select(resp["id"]); app.update()
    t = win.cp_text
    r = t.tag_ranges("r:" + resp["id"])
    s = t.get(r[0], r[1])
    a = s.index("responsible for")
    t.tag_add("sel", f"{r[0]}+{a}c", f"{r[0]}+{a + len('responsible for')}c")
    app.cp_text_menu(Ev); app.update()
    m = menus[-1]
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) == "command"]
    check("right-click on selected words offers Add to compliance words", labels[0] == "Add to compliance words: responsible for"
          and labels[1].startswith("Add as keyword"), labels)
    m.invoke(0); app.update()
    check("the words are added to the list", "responsible for" in W.load()["words"])
    check("and the rescan found the sentence: a requirement candidate now", resp["type"] != "Context" and resp["new"] == C.FOUND
          and resp["suggest"] == "Keep", (resp["type"], resp["new"]))
    safety = next(it for it in app.matrix.items if "safety" in it["text"])
    check("a decided sentence keeps its decision", safety["decision"] == "Drop" and safety["type"] == "Context")
    check("the rescan says what it found", any("1 sentence(s) now look like requirements" in x and "already decided" in x for x in said), said[-1:])
    r = t.tag_ranges("r:" + resp["id"])
    hit = [t.get(a_, b_) for a_, b_ in zip(t.tag_ranges("cword")[::2], t.tag_ranges("cword")[1::2])]
    check("the new words show in the compliance word style", any(h.lower() == "responsible for" for h in hit), hit[:8])
    rows = {app._cwin.tv.item(i, "values")[0] if False else i: app._cwin.tv.item(i, "values") for i in app._cwin.tv.get_children()}
    check("the list marks it Found", any("[Found] " in str(v) for v in rows.values()))
    tk.Menu.tk_popup = lambda self, *a, **k: menus.append(self)
    app.kw_text_menu(Ev, win.d_text._textbox, "Compliance requirement"); app.update()
    m = menus[-1]
    check("the requirement text's right-click menu has it too", m.entrycget(0, "label").startswith("Add to compliance words"))
    cfg = W.load(); cfg["words"] = [w for w in cfg["words"] if w != "responsible for"]
    app.compliance_word_style(cfg, rescan=True); app.update()
    check("a word taken off the list in Compliance words: the sentence is Context again", resp["type"] == "Context" and resp["new"] == "")
    res = app.compliance_rescan_words(show=False)
    check("Rescan with compliance words with nothing new finds nothing", res == {"found": [], "back": [], "decided": []}, res)
    C.set_extra_words([])
    n = sum(checks)
    print(f"GUI CWRESCAN PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI CWRESCAN FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
