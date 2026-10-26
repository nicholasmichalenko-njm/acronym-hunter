"""2.32.0 the app shell and compliance in passes: feature rail in work order, one feature's tools at a time, step
strip with each feature's Export step, compliance inside the main window, Decide in Page view (keys, accept, back,
split by clicking in the page, boilerplate), Place one sentence at a time (keys, run), owner/status/page on Prove."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, shell_ui as SH
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
base = {"lead": "", "page": "", "actor": "Offeror", "type": "Instruction", "strength": "Mandatory", "suggest": "Keep",
        "modal": "shall", "xrefs": "", "compound": False, "owner": "", "status": "", "response_page": "", "notes": "", "links": "",
        "learned": "", "new": "", "context": "", "loc": "", "decision": "", "map": ""}
ROWS = [("L.4", "TECHNICAL VOLUME", "The Technical Volume shall not exceed 25 pages.", "Keep", "Instruction"),
        ("L.4", "TECHNICAL VOLUME", "Resumes do not count toward the page limit.", "Context", "Context"),
        ("L.4.1", "Technical Approach", "The Offeror shall describe the thermal design and shall provide the analysis results.", "Keep", "Instruction"),
        ("L.4.1", "Technical Approach", "The Offeror shall provide thermal margins for each mode.", "Keep", "Instruction"),
        ("L.4.1", "Technical Approach", "Page 4 of 12", "Drop", "Context"),
        ("L.4.2", "Schedule", "The Offeror shall provide an integrated master schedule.", "Keep", "Instruction")]
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = [dict(base, id=f"{sec}-{i:02d}", file="Section_L.docx", section=sec, section_title=st, text=t, suggest=sug, type=ty,
                key=C.text_key(t)) for i, (sec, st, t, sug, ty) in enumerate(ROWS, 1)]
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Schedule")
M.save()
app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def go():
    # the rail and the strip
    names = [b.cget("text").split("   ", 1)[1] for b, _s in app._rail.values()]
    check("rail lists the features in work order", names == ["Effort home", "Compliance", "Acronyms", "QA/QC", "Keywords"], names)
    check("each feature ends in its own Export step", all(SH.STEPS[k][-1][1] == "Export" for k in ("compliance", "acronyms", "qaqc", "keywords")))
    app.shell_go("acronyms", "scan"); app.update()
    check("Acronyms > Scan shows the scan buttons", app.btn_files.winfo_ismapped() and not app.scan_view.winfo_ismapped())
    check("no sidebar sections on screen", not app._legacy.winfo_ismapped())
    app.shell_go("acronyms", "review"); app.update()
    check("Review shows the results with its filters", app.scan_view.winfo_ismapped() and app.opt_type.winfo_ismapped())
    app.shell_go("keywords"); app.update()
    check("Keywords needs an effort", app.shell_page("noeffort").winfo_ismapped())
    L = E.EffortList(LIST, "Kestrel", client="USSF", solicitation="FA0000"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, client="USSF", solicitation="FA0000")
    app.open_effort("Kestrel"); app.update()
    check("opening an effort lands on Effort home", app.shell_feature == "home" and app.shell_page("overview").winfo_ismapped())
    check("Effort home offers Export all", app.btn_ov_xall.winfo_ismapped())
    # compliance inside the main window
    app.ws.set("compliance_path", M.path)
    win = app.open_compliance(); app.update()
    check("compliance lives inside the main window", isinstance(win, SH.EmbeddedWindow) and win.winfo_toplevel() is app)
    check("opens on Decide in Page view", app.shell_step == "decide" and win.cp_text.winfo_ismapped() and not win.c_left.winfo_ismapped())
    pills = [w.cget("text") for w in app.strip_pills.winfo_children()]
    check("step strip shows the compliance steps", [p.split("  ")[0] for p in pills] ==
          ["1 Read RFP", "2 Decide", "3 Outline", "4 Place", "5 Prove", "6 Export"], pills)
    t = win.cp_text
    page = t.get("1.0", "end")
    check("the page reads like the RFP: headings and every sentence", "L.4.1 Technical Approach" in page and all(r[2] in page for r in ROWS))
    tagged = [t.get(a, b) for a, b in zip(t.tag_ranges("cword")[0::2], t.tag_ranges("cword")[1::2])]
    check("compliance words styled in the page", "shall not" in tagged and "describe" in tagged, tagged[:6])
    first = app._c_selected()
    check("the first undecided sentence is current", first and first[0]["id"] == "L.4-01", first and first[0]["id"])
    t.focus_set(); app.update()
    t.event_generate("<Key>", keysym="Return"); app.update()
    it1 = app._c_item("L.4-01")
    check("Enter accepts the suggestion as a draft and moves on", it1["draft"] == "Keep" and it1["decision"] == ""
          and app._c_selected()[0]["id"] == "L.4-02", (it1["draft"], it1["decision"], app._c_selected()[0]["id"]))
    check("a draft is shaded lighter and underlined", "p_Keep" in t.tag_names(t.tag_ranges("r:L.4-01")[0]))
    # 2.35.0: commit, with the message on the dock
    app._cp_select("L.4-01"); app.update()
    t.focus_set(); t.event_generate("<Key>", keysym="Return", state=4); app.update()
    check("Ctrl+Enter commits what is on screen and says so", it1["decision"] == "Keep" and not it1["draft"]
          and win.cp_l0.cget("text").startswith("Committed 1 decision: 1 Keep."), win.cp_l0.cget("text"))
    check("the page shades it solid green", "d_Keep" in t.tag_names(t.tag_ranges("r:L.4-01")[0]))
    app._cp_select("L.4-02"); app.update()
    t.event_generate("<Key>", keysym="c"); app.update()
    it2 = app._c_item("L.4-02")
    check("C drafts Context and stays on the sentence", C.eff(it2) == "Context" and app._c_selected()[0]["id"] == "L.4-02")
    # 2.33.0: Context is linked to the requirement it explains
    check("Context linked to the nearest requirement", C.eff_cf(it2) == "L.4-01", C.eff_cf(it2))
    app._cp_select("L.4-02"); app.update()
    check("the dock names the requirement and the page marks it", "Context for L.4-01" in win.cp_l3.cget("text")
          and bool(t.tag_ranges("linked")) and t.tag_ranges("linked")[0] == t.tag_ranges("r:L.4-01")[0], win.cp_l3.cget("text"))
    t.event_generate("<Key>", keysym="l"); app.update()
    r6 = t.tag_ranges("r:L.4.2-06"); t.see(r6[0]); app.update(); b6 = t.bbox(r6[0])
    t.event_generate("<ButtonRelease-1>", x=b6[0] + 3, y=b6[1] + b6[3] // 2); app.update()
    check("linking to a sentence that is not a requirement is refused", C.eff_cf(it2) == "L.4-01"
          and "not a requirement" in win.cp_l3.cget("text"), win.cp_l3.cget("text"))
    app._c_item("L.4.2-06")["decision"] = "Keep"; app._c_changed(); app.update()
    t.see(r6[0]); app.update(); b6 = t.bbox(t.tag_ranges("r:L.4.2-06")[0])
    t.event_generate("<ButtonRelease-1>", x=b6[0] + 3, y=b6[1] + b6[3] // 2); app.update()
    check("link mode stays open: a second requirement is added", C.cf_ids(C.eff_cf(it2)) == ["L.4-01", "L.4.2-06"]
          and win.cp_linking is not None, (C.eff_cf(it2), win.cp_linking))
    t.event_generate("<ButtonRelease-1>", x=b6[0] + 3, y=b6[1] + b6[3] // 2); app.update()
    check("clicking it again removes it", C.cf_ids(C.eff_cf(it2)) == ["L.4-01"], C.eff_cf(it2))
    t.event_generate("<ButtonRelease-1>", x=b6[0] + 3, y=b6[1] + b6[3] // 2); app.update()
    t.event_generate("<Key>", keysym="Return"); app.update()
    check("Enter ends link mode", win.cp_linking is None and C.cf_ids(C.eff_cf(it2)) == ["L.4-01", "L.4.2-06"])
    check("pointing at the Context lights up both requirements", app._cp_hover("L.4-02") == ["L.4-01", "L.4.2-06"])
    check("pointing at a requirement lights up its Context", app._cp_hover("L.4-01") == ["L.4-02"])
    app._cp_hover(None)
    # drafts are saved as they are made: the file and the recovery copy both have them
    app._c_save_now(); N = C.Matrix(app.matrix.path).load()
    nit = next(x for x in N.items if x["id"] == "L.4-02")
    check("drafts are saved in the matrix before they are committed", nit["draft"] == "Context" and nit["draft_cf"] == "L.4-01; L.4.2-06"
          and nit["decision"] == "", (nit["draft"], nit["draft_cf"]))
    app.cp_commit("all"); app.update()
    check("committing makes the links count", it2["decision"] == "Context" and it2["context_for"] == "L.4-01; L.4.2-06"
          and "with 2 links" in win.cp_l0.cget("text"), (it2["context_for"], win.cp_l0.cget("text")))
    # L on a requirement picks its Context sentences
    app._cp_select("L.4.2-06"); app.update()
    t.event_generate("<Key>", keysym="l"); app.update()
    check("L on a requirement picks its Context", win.cp_linking == ("rev", "L.4.2-06"), win.cp_linking)
    r7 = t.tag_ranges("r:L.4.1-04"); t.see(r7[0]); app.update(); b7 = t.bbox(r7[0])
    t.event_generate("<ButtonRelease-1>", x=b7[0] + 3, y=b7[1] + b7[3] // 2); app.update()
    it7 = app._c_item("L.4.1-04")
    check("a clicked sentence becomes Context for it (draft)", C.eff(it7) == "Context" and C.eff_cf(it7) == "L.4.2-06", (C.eff(it7), C.eff_cf(it7)))
    t.event_generate("<Key>", keysym="Escape"); app.update()
    # a range: drag across sentences, one key decides them all
    app.cp_set_range(["L.4.1-04", "L.4.1-05"]); app.update()
    check("a dragged range is marked and named on the dock", len(t.tag_ranges("rng")) == 4 and "2 sentences selected" in win.cp_l1.cget("text"),
          win.cp_l1.cget("text"))
    t.event_generate("<Key>", keysym="d"); app.update()
    check("one key decides the whole range", all(C.eff(app._c_item(i)) == "Drop" for i in ("L.4.1-04", "L.4.1-05")))
    r = app.cp_commit("selected"); app.update()
    check("commit the selected sentences", r["n"] == 2 and all(app._c_item(i)["decision"] == "Drop" for i in ("L.4.1-04", "L.4.1-05")), r)
    t.event_generate("<Key>", keysym="Escape"); app.update()
    check("Esc clears the range", not win.cp_range)
    # the strip maps the file
    app.update(); hs = win.cp_strip.winfo_height()
    marks = win.cp_strip.find_all()
    check("the strip has a mark for every sentence", len(marks) >= len(app._cp_items_of(win.cp_file)), (len(marks), hs))
    class Ev: y = 1
    check("clicking the strip jumps there", app._cp_strip_click(Ev) == app._cp_items_of(win.cp_file)[0]["id"])
    app._c_item("L.4-02")["context_for"] = "L.4-01"
    for i in ("L.4.2-06", "L.4.1-04", "L.4.1-05"):
        app._c_item(i).update(decision="", draft="", draft_cf="", context_for="")
    app._c_changed(); app._cp_select("L.4-02"); app.update()
    t.event_generate("<Key>", keysym="BackSpace"); app.update()
    check("Back returns to the previous sentence", app._c_selected()[0]["id"] == "L.4-02")
    # split by clicking between two words of the current sentence
    app._cp_select("L.4.1-03"); app.update()
    r = t.tag_ranges("r:L.4.1-03")
    k = ROWS[2][2].index("and shall")
    t.see(r[0]); app.update()
    bx = t.bbox(f"{r[0]}+{k}c")
    t.event_generate("<ButtonRelease-1>", x=bx[0] + 1, y=bx[1] + bx[3] // 2); app.update()
    t.event_generate("<Key>", keysym="s"); app.update()
    parts = [x["text"] for x in app.matrix.items if x["id"].startswith("L.4.1-03")]
    check("split where clicked in the page", parts == ["The Offeror shall describe the thermal design", "and shall provide the analysis results."], parts)
    check("the page shows both parts", all(p in t.get("1.0", "end") for p in parts))
    # clear the boilerplate
    n = app.cp_drop_boilerplate(ask=False)
    app.cp_commit("all")
    check("boilerplate dropped in one go", n == 1 and app._c_item("L.4.1-05")["decision"] == "Drop")
    for x in app.matrix.items:
        if not x["decision"]:
            x["decision"] = "Keep"
    app._c_changed(); app.update()
    # Place: one sentence at a time
    app.shell_go("compliance", "place"); app.update()
    cur = app._cwin.pl_cur
    check("Place shows the first sentence that needs a home", cur == "L.4-01", cur)
    keys = list(app._cwin.pl_keys)
    app.pl_place("1.1 Thermal Design"); app.update()
    check("placing moves to the next one", app._c_item("L.4-01")["map"] == "1.1 Thermal Design" and app._cwin.pl_cur != "L.4-01")
    check("its Context goes with it", app._c_item("L.4-02")["map"] == "1.1 Thermal Design")
    app._cwin.pl_cur = "L.4.1-03a"; app.pl_refresh(); app.update()
    app._cwin.pl_keys = ["1.1 Thermal Design"]
    nrun = app.pl_place_run(); app.update()
    run_ok = all(app._c_item(i)["map"] == "1.1 Thermal Design" for i in ("L.4.1-03a", "L.4.1-03b", "L.4.1-04"))
    check("a whole RFP paragraph placed at once", nrun == 3 and run_ok, nrun)
    app._cwin.pl_cur = "L.4.2-06"; app.pl_refresh()
    app._cwin.pl_keys = ["1.2 Schedule"]
    app._cwin.pl_card.event_generate("<Key>", keysym="1"); app.update()
    check("key 1 places in choice 1", app._c_item("L.4.2-06")["map"] == "1.2 Schedule")
    # Prove: owner, status, page
    app.shell_go("compliance", "prove"); app.update()
    pv = app._cwin.pv_tv
    check("Prove lists the kept requirements", "L.4.2-06" in pv.get_children(), len(pv.get_children()))
    pv.selection_set(("L.4.2-06", "L.4-01")); app.update(); app._pv_fill_fields()
    app._cwin.pv_fields["owner"].insert(0, "J. Smith"); app._cwin.pv_fields["response_page"].insert(0, "12")
    app.pv_apply()
    check("owner and page set on several at once", app._c_item("L.4-01")["owner"] == "J. Smith" and app._c_item("L.4.2-06")["response_page"] == "12")
    check("Prove says every sentence has a decision", "✓ All" in app._cwin.lbl_prove.cget("text"), app._cwin.lbl_prove.cget("text"))
    app.shell_go("compliance", "export"); app.update()
    check("Export step shows the compliance outputs", app._cwin.tabs.get() == "Export")
    app._c_save_now()
    N = C.Matrix(M.path).load()
    check("decisions, splits, homes and owners saved", sum(1 for x in N.items if x["decision"]) == len(N.items) and
          next(x for x in N.items if x["id"] == "L.4-01")["owner"] == "J. Smith")
    # one status line
    check("one status line at the bottom", app.status.master is app.statusbar and app.lbl_aistate.master is app.statusbar)
    app.shell_go("qaqc"); app.update()
    check("QA/QC opens its own view", app.qa_view.winfo_ismapped() and not app._cwin.winfo_ismapped())
    print(f"GUI SHELL {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
    app.after(200, app.destroy)


A.set_ai_ml(True)
app.after(900, go)
app.mainloop()
