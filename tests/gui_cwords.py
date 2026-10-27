"""2.31.0 in the compliance window: compliance words styled in the sentence, Split at a clicked point or around
selected words, the style window, and Export all (File menu and Effort home)."""
import os, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, cwords as W
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
said = []
messagebox.showinfo = lambda *a, **k: said.append(a[1] if len(a) > 1 else "")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
base = {"lead": "", "file": "Section_L.docx", "page": "", "section": "L.4", "section_title": "Technical", "actor": "Offeror",
        "type": "Instruction", "strength": "Mandatory", "suggest": "Keep", "modal": "shall", "xrefs": "", "compound": False,
        "owner": "", "status": "", "response_page": "", "notes": "", "links": "", "learned": "", "new": "", "context": "",
        "loc": "", "decision": "", "map": ""}
TEXTS = ["The Offeror shall describe the thermal design and shall provide the analysis results.",
         "Proposals shall not exceed 25 pages, and resumes do not count toward the limit.",
         "The Offeror shall identify key personnel by name and role for the program.",
         "Resumes do not count."]
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = [dict(base, id=f"L.4-0{i + 1}", text=t, key=C.text_key(t)) for i, t in enumerate(TEXTS)]
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal\n1.2 Staffing")
M.items[2]["decision"] = "Keep"; M.items[2]["map"] = "1.2 Staffing"
M.save()
app = A.AcronymAppGUI()


def go():
    L = E.EffortList(LIST, "Kestrel", client="USSF", solicitation="FA0000"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, client="USSF", solicitation="FA0000")
    app.open_effort("Kestrel")
    app.effort.add_terms = getattr(app.effort, "add_terms", None)
    app.ws.set("compliance_path", M.path)
    win = app.open_compliance(); win.update()
    app._c_load(M.path, quiet=True); app._c_refresh(); win.update()
    tv, tb = win.tv, win.d_text._textbox
    # 1. compliance words styled in the sentence
    tv.selection_set("L.4-01"); win.update(); app._c_show(); win.update()
    tagged = [tb.get(a, b) for a, b in zip(tb.tag_ranges("cword")[0::2], tb.tag_ranges("cword")[1::2])]
    check("compliance words styled in the sentence", tagged == ["shall", "describe", "shall", "provide"], tagged)
    check("bold by default", "bold" in str(tb.tag_cget("cword", "font")), tb.tag_cget("cword", "font"))
    # 2. split where the person clicked (mid-word snaps to the gap)
    text = TEXTS[0]
    k = text.index("and shall") + 1                      # inside "and": snaps to the nearer gap (before it)
    tb.mark_set("insert", f"1.0+{k}c"); app._c_text_click()
    app.compliance_split(); win.update()
    parts = [it for it in app.matrix.items if it["id"].startswith("L.4-01")]
    check("split at the clicked point", [p["text"] for p in parts] == ["The Offeror shall describe the thermal design",
                                                                       "and shall provide the analysis results."],
          [p["text"] for p in parts])
    check("each part is its own row, undecided", [p["id"] for p in parts] == ["L.4-01a", "L.4-01b"] and not any(p["decision"] for p in parts))
    # 3. split around selected words: three parts
    tv.selection_set("L.4-02"); win.update(); app._c_show(); win.update()
    t2 = TEXTS[1]; a = t2.index("and resumes"); b = len(t2)
    tb.tag_add("sel", f"1.0+{a}c", f"1.0+{t2.index(' toward')}c"); app._c_text_click()
    app.compliance_split(); win.update()
    p2 = [it["text"] for it in app.matrix.items if it["id"].startswith("L.4-02")]
    check("split around selected words", p2 == ["Proposals shall not exceed 25 pages,", "and resumes do not count",
                                                "toward the limit."], p2)
    # 4. no point chosen: the rules' split; nothing to split says how
    tv.selection_set("L.4-04"); win.update(); app._c_show(); win.update()
    app.compliance_split(); win.update()
    check("nothing to split explains clicking", "click between two words" in win.d_head.cget("text"), win.d_head.cget("text"))
    # 5. style window: italic and dark blue, saved and used
    w = app.compliance_word_style(); w.update()
    w.api["vars"]["italic"].set(True); w.api["color"].set("Dark blue")
    cfg = w.api["gather"]()
    check("style window gathers the choices", cfg["style"]["italic"] and cfg["style"]["color"] == "1F3864", cfg["style"])
    w.destroy()
    app.compliance_word_style(cfg)
    check("style saved", W.load()["style"]["italic"] is True)
    tv.selection_set("L.4-03"); win.update(); app._c_show(); win.update()
    check("sentence shows the new style", "italic" in str(tb.tag_cget("cword", "font")) and
          str(tb.tag_cget("cword", "foreground")).lower() == "#1f3864", (tb.tag_cget("cword", "font"), tb.tag_cget("cword", "foreground")))
    # 6. Export all
    av = app.export_all_available()
    check("Export all knows what is available", av["matrix"][0] and av["coverage"][0] and av["setup"][0] and "outline" not in av and not av["qaqc"][0], av)
    dw = app.export_all_dialog(); dw.update()
    check("Export all window ticks what is available", dw.api["vars"]["matrix"].get() and not dw.api["vars"]["qaqc"].get())
    dw.destroy()
    out = os.path.join(tmp, "out"); os.makedirs(out)
    sub, made, problems = app.export_all(out)
    names = sorted(os.path.basename(p) for p in made)
    check("Export all writes every available part", any(n.endswith("_RFP_Coverage.docx") for n in names) and
          not any(n.endswith("_Outline_with_Requirements.docx") for n in names) and any("_Response_Setup" in n for n in names) and
          "Kestrel_Matrix.xlsx" in names and not problems, (names, problems))
    cx = zipfile.ZipFile(next(p for p in made if p.endswith("_RFP_Coverage.docx"))).read("word/document.xml").decode()
    check("exported report uses the style", "<w:i/>" in cx and "1F3864" in cx)
    check("the working matrix is untouched", app.matrix.path == M.path and os.path.isfile(M.path))
    menu_ok = False
    try:
        mb = app.nametowidget(app.cget("menu"))
        fm = app.nametowidget(mb.entrycget(0, "menu"))
        if fm.cget("postcommand"):
            app.tk.eval(fm.cget("postcommand"))     # 2.40.0: File is built when it opens
        menu_ok = any(fm.type(i) == "command" and fm.entrycget(i, "label") == "Export all for this effort..."
                      for i in range(fm.index("end") + 1))
    except Exception as ex:
        print("menu", ex)
    check("File menu has Export all", menu_ok)
    check("Effort home has Export all", hasattr(app, "btn_h_xall") and app.btn_h_xall.cget("text") == "Export all...")
    print(f"GUI CWORDS {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
    app.after(200, app.destroy)


A.set_ai_ml(True)
app.after(800, go)
app.mainloop()
