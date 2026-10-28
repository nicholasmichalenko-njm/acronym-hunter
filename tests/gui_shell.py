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
M.items[5]["draft"] = "Keep"                     # a draft left by 2.35.0
M.save()
app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def go():
    # the rail and the strip
    names = [b.cget("text").split("   ", 1)[1] for b, _s in app._rail.values()]
    check("rail lists the features in work order", names == ["Effort home", "Customer Documents", "Compliance", "Acronyms", "QA/QC", "Keywords"], names)
    check("each feature ends in its own Export step", all(SH.STEPS[k][-1][1] == "Export" for k in ("submission", "compliance", "acronyms", "qaqc", "keywords")))
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
    d6 = app._c_item("L.4.2-06")
    check("a draft from 2.35.0 counts when the matrix opens", d6["decision"] == "Keep" and not d6.get("draft"), (d6["decision"], d6.get("draft")))
    check("opens on Assign in Page view", app.shell_step == "decide" and win.cp_text.winfo_ismapped() and not win.c_left.winfo_ismapped())
    pills = [w.cget("text") for w in app.strip_pills.winfo_children()]
    check("step strip shows the compliance steps", [p.split("  ")[0] for p in pills] ==
          ["1 Read RFP", "2 Structure", "3 Assign", "4 Matrix", "5 Prove", "6 Export"], pills)
    t = win.cp_text
    page = t.get("1.0", "end")
    check("the page reads like the RFP: headings and every sentence", "L.4.1 Technical Approach" in page and all(r[2] in page for r in ROWS))
    tagged = [t.get(a, b) for a, b in zip(t.tag_ranges("cword")[0::2], t.tag_ranges("cword")[1::2])]
    check("compliance words styled in the page", "shall not" in tagged and "describe" in tagged, tagged[:6])
    first = app._c_selected()
    check("the first sentence not assigned is current", first and first[0]["id"] == "L.4-01", first and first[0]["id"])
    check("the response structure is always on the right", {"1.1 Thermal Design", "1.2 Schedule"} <= set(win.cp_orows)
          and win.cp_orows["1.1 Thermal Design"].winfo_ismapped())
    # 2.36.0: R with no target asks for a section; the click assigns and counts at once
    t.focus_set(); t.event_generate("<Key>", keysym="r"); app.update()
    check("R with no target section asks for one", win.cp_mode and win.cp_mode[0] == "req" and "click the section" in win.cp_l3.cget("text"),
          win.cp_mode)
    win.cp_orows["1.1 Thermal Design"].invoke(); app.update()
    it1 = app._c_item("L.4-01")
    check("clicking a section assigns the compliance requirement there", it1["decision"] == "Keep" and it1["map"] == "1.1 Thermal Design"
          and not it1.get("draft"), (it1["decision"], it1["map"]))
    check("it moves on to the next sentence not assigned", app._c_selected()[0]["id"] == "L.4-02")
    check("the dock says what was assigned", "compliance requirement in 1.1 Thermal Design" in win.cp_l0.cget("text"), win.cp_l0.cget("text"))
    check("the page shades it green", "d_Keep" in t.tag_names(t.tag_ranges("r:L.4-01")[0]))
    # a target section: R assigns straight there
    win.cp_orows["1.2 Schedule"].invoke(); app.update()
    check("clicking a section makes it the target", win.cp_target == "1.2 Schedule" and "Target: 1.2 Schedule" in win.cp_l2.cget("text"))
    app._cp_select("L.4.2-06"); app.update(); t.focus_set()
    t.event_generate("<Key>", keysym="r"); app.update()
    it6 = app._c_item("L.4.2-06")
    check("R assigns to the target section", it6["decision"] == "Keep" and it6["map"] == "1.2 Schedule")
    n_own = app.cp_owner("K. Ito"); app.update()
    check("2.47.0: O right after R gives the sentence just assigned its owner (Assign has moved on)",
          n_own == 1 and app._c_item("L.4.2-06")["owner"] == "K. Ito", app._c_item("L.4.2-06").get("owner"))
    app._cp_select("L.4.2-06"); app.update()
    check("sentences in the target section are underlined", bool(t.tag_ranges("insec")) and t.tag_ranges("insec")[0] == t.tag_ranges("r:L.4.2-06")[0])
    # Context (2.47.0): C makes it context for the nearest requirement and moves on; C again on it changes what it supports
    app._cp_select("L.4-02"); app.update(); t.focus_set()
    t.event_generate("<Key>", keysym="c"); app.update()
    it2 = app._c_item("L.4-02")
    check("C makes it Context for the nearest requirement and moves on to the next sentence", it2["decision"] == "Context"
          and it2["context_for"] == "L.4-01" and win.cp_mode is None and app._c_selected()[0]["id"] != "L.4-02",
          (it2["context_for"], win.cp_mode, app._c_selected()[0]["id"]))
    app._cp_select("L.4-02"); app.update(); t.focus_set()
    t.event_generate("<Key>", keysym="c"); app.update()
    check("C again on it: choose what it supports", win.cp_mode and win.cp_mode[0] == "ctx" and not win.cp_done_btn.winfo_ismapped(), win.cp_mode)
    def click(iid):
        r = t.tag_ranges("r:" + iid); t.see(r[0]); app.update(); bx = t.bbox(r[0])
        t.event_generate("<ButtonRelease-1>", x=bx[0] + 3, y=bx[1] + bx[3] // 2); app.update()
    click("L.4.2-06")
    check("clicking another requirement adds it", C.cf_ids(it2["context_for"]) == ["L.4-01", "L.4.2-06"] and win.cp_mode is not None,
          it2["context_for"])
    click("L.4.2-06")
    check("clicking it again removes it", it2["context_for"] == "L.4-01", it2["context_for"])
    click("L.4.2-06")
    click("L.4.1-05")
    check("no Done step: clicking another sentence just moves on", win.cp_mode is None and app._c_selected()[0]["id"] == "L.4.1-05"
          and it2["context_for"] == "L.4-01; L.4.2-06" and it2["map"] == "1.1 Thermal Design", (win.cp_mode, it2["context_for"]))
    app._cp_select("L.4.1-04"); app.update(); t.focus_set()
    t.event_generate("<Key>", keysym="c"); app.update()
    check("C on another sentence moves on by itself", win.cp_mode is None and app._c_selected()[0]["id"] != "L.4.1-04"
          and app._c_item("L.4.1-04")["decision"] == "Context")
    C.clear_assignment(app.matrix.items, [app._c_item("L.4.1-04")]); app._c_changed(); app.update()
    check("pointing at the Context lights up its requirements", app._cp_hover("L.4-02") == ["L.4-01", "L.4.2-06"])
    check("pointing at a requirement lights up its Context", app._cp_hover("L.4-01") == ["L.4-02"])
    app._cp_hover(None)
    # context for a section itself: C, back to it, C again, click the section
    app._cp_select("L.4.1-04"); app.update(); t.focus_set()
    t.event_generate("<Key>", keysym="c"); app.update()
    app._cp_select("L.4.1-04"); app.update(); t.focus_set()
    t.event_generate("<Key>", keysym="c"); app.update()
    win.cp_orows["1.1 Thermal Design"].invoke(); app.update()
    it4 = app._c_item("L.4.1-04")
    check("context for a section: click the section while choosing", it4["decision"] == "Context" and not it4["context_for"]
          and it4["map"] == "1.1 Thermal Design" and win.cp_mode is None, (it4["context_for"], it4["map"]))
    app._cp_select("L.4.1-04"); app.update()
    check("clicking a sentence any time shows how it is assigned", "Support for section 1.1 Thermal Design" in win.cp_l1.cget("text"),
          win.cp_l1.cget("text"))
    t.focus_set(); t.event_generate("<Key>", keysym="x"); app.update()
    check("X clears it: not used", it4["decision"] == "" and not it4["map"])
    # suggestions on 1, 2, 3
    sug6 = app._cp_suggestions(app._c_item("L.4.2-06"))
    check("suggested sections come from the rules", "1.2 Schedule" in sug6, sug6)
    app._cp_select("L.4.1-04"); app.update()
    win.cp_sugg = ["1.2 Schedule"]
    t.focus_set(); t.event_generate("<Key>", keysym="1"); app.update()
    check("1 assigns to the first suggested section", it4["decision"] == "Keep" and it4["map"] == "1.2 Schedule", it4["map"])
    C.clear_assignment(app.matrix.items, [it4]); app._c_changed(); app.update()
    # saved at once: no commit step
    app._c_save_now(); N = C.Matrix(app.matrix.path).load()
    n2 = next(x for x in N.items if x["id"] == "L.4-02")
    check("every choice is saved at once, no commit", n2["decision"] == "Context" and n2["context_for"] == "L.4-01; L.4.2-06"
          and not n2["draft"], (n2["decision"], n2["draft"]))
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
    # drag across several: assign them together, or combine them
    win.cp_orows["1.1 Thermal Design"].invoke(); app.update()
    app.cp_set_range(["L.4.1-03a", "L.4.1-03b"]); app.update()
    check("a dragged range is marked and named on the dock", len(t.tag_ranges("rng")) == 4 and "2 sentences selected" in win.cp_l1.cget("text"))
    t.focus_set(); t.event_generate("<Key>", keysym="r"); app.update()
    check("one key assigns the whole range", all(app._c_item(i)["decision"] == "Keep" and app._c_item(i)["map"] == "1.1 Thermal Design"
                                                for i in ("L.4.1-03a", "L.4.1-03b")))
    n0 = len(app.matrix.items)
    app.cp_set_range(["L.4.1-03a", "L.4.1-03b"]); app.update()
    got = app.cp_combine(); app.update()
    check("Combine joins the selected sentences", len(app.matrix.items) == n0 - 1 and got == "L.4.1-03a"
          and "analysis results" in app._c_item("L.4.1-03a")["text"], got)
    check("Esc-free: the range is gone after combining", not win.cp_range)
    # the strip maps the file
    app.update()
    marks = win.cp_strip.find_all()
    check("the strip has a mark for every sentence", len(marks) >= len(app._cp_items_of(win.cp_file)), len(marks))
    class Ev: y = 1
    check("clicking the strip jumps there", app._cp_strip_click(Ev) == app._cp_items_of(win.cp_file)[0]["id"])
    # Prove: owner, status, page
    app.shell_go("compliance", "prove"); app.update()
    pv = app._cwin.pv_tv
    check("Prove lists the kept requirements", "L.4.2-06" in pv.get_children(), len(pv.get_children()))
    pv.selection_set(("L.4.2-06", "L.4-01")); app.update(); app._pv_fill_fields()
    app._cwin.pv_fields["owner"].insert(0, "J. Smith"); app._cwin.pv_fields["response_page"].insert(0, "12")
    app.pv_apply()
    check("owner and page set on several at once", app._c_item("L.4-01")["owner"] == "J. Smith" and app._c_item("L.4.2-06")["response_page"] == "12")
    check("Prove says every sentence was read and what is not used", "Every sentence read" in app._cwin.lbl_prove.cget("text")
          and "not used" in app._cwin.lbl_prove.cget("text"), app._cwin.lbl_prove.cget("text"))
    # 2.38.0: Prove as categories to clear
    cw = app._cwin
    counts = app.pv_refresh()
    unused = app.prove_items("unused")
    check("Prove shows a tile per category with its count", set(cw.pv_tiles) == {k for k, _l in app.PROVE_CATS}
          and cw.pv_tiles["unused"].cget("text").startswith(f"{len(unused)}\n"), cw.pv_tiles["unused"].cget("text"))
    items = app.pv_show("unused"); app.update()
    check("clicking a category lists its sentences, with what to do", [cw.pv_tv.item(i, "values")[0] for i in cw.pv_tv.get_children()]
          and len(cw.pv_tv.get_children()) == len(items) and cw.pv_confirm_btn.winfo_manager()
          and "Confirm not used" in cw.pv_help.cget("text"), cw.pv_help.cget("text")[:60])
    if items:
        cw.pv_tv.selection_set(cw.pv_tv.get_children()[0]); app.update()
        n0 = len(items)
        check("Confirm not used clears it from the list", app.pv_confirm_unused() == 1 and len(app.prove_items("unused")) == n0 - 1)
    app.pv_show("noowner"); app.update()
    nob = len(app.prove_items("noowner"))
    w = app.cp_people_dialog(); w.update()
    rows = w._api["rows"]
    vol = next(r for r in rows if r[0] == "Volume I Technical")
    vol[1].set("M. Ortiz"); vol[2].insert(0, "A. Lee, B. Chen")
    w._api["save"](); app.update()
    import setupdoc as SD
    check("People: a section's lead owns its requirements unless they have their own owner",
          SD.owner_of(app.matrix, app._c_item("L.4.2-06")) == "J. Smith" and len(app.prove_items("noowner")) < max(1, nob)
          and SD.section_people(app.matrix, "1.1 Thermal Design")["lead"] == "M. Ortiz", nob)
    app.shell_go("compliance", "decide"); app.update()
    check("the structure panel shows each section's lead", "M. Ortiz" in cw.cp_orows["Volume I Technical"].cget("text"))
    cw.cp_who.set("A. Lee"); app._cp_side(); app.update()
    check("Show sections for one person", all(b.winfo_manager() for b in cw.cp_orows.values()))
    cw.cp_who.set("Everyone"); app._cp_side()
    rw = app.compliance_ask_references(["Section_L.docx"]); rw.update()
    f, var, nm, px = rw._api["rows"][0]
    var.set("prefix"); px.insert(0, "SL"); rw._api["apply"](); app.update()
    app._cp_select("L.4-01"); app.update()
    check("a file can be referenced by the document itself", cw.cp_ref.cget("text").startswith("Referenced as: SL-1")
          and cw.cp_l1.cget("text").startswith("SL-1:"), cw.cp_ref.cget("text"))
    SD.setup_of(app.matrix)["refmode"].pop("Section_L.docx", None); app._c_changed(); app.update()
    app.shell_go("compliance", "export"); app.update()
    labels = [w.cget("text") for w in cw.tabs.tab("Export").winfo_children() if hasattr(w, "cget") and isinstance(w, __import__("customtkinter").CTkButton)]
    check("one Response Setup export, no separate Word outline", any("Response Setup (Word)" in l for l in labels)
          and not any("Word outline" in l for l in labels), labels)
    check("Export step shows the compliance outputs", app._cwin.tabs.get() == "Export")
    app._c_save_now()
    N = C.Matrix(M.path).load()
    check("assignments, splits, sections and owners saved", next(x for x in N.items if x["id"] == "L.4-01")["owner"] == "J. Smith"
          and next(x for x in N.items if x["id"] == "L.4.1-03a")["map"] == "1.1 Thermal Design")
    # 2.37.0: no response structure yet: still the RFP text, with buttons to start the structure
    saved = list(app.matrix.outline)
    app.matrix.outline = []; app._c_changed(); app.update()
    check("with no structure the app still opens on the RFP text", app._c_next_step() == "decide")
    app.shell_go("compliance", "decide"); app.update()
    check("Assign offers to start the structure", app._cwin.cp_nostruct.winfo_manager() and app._cwin.cp_text.winfo_ismapped())
    app.matrix.headings = [{"num": "L.4", "title": "TECHNICAL VOLUME", "file": "Section_L.docx"},
                           {"num": "L.4.1", "title": "Technical Approach", "file": "Section_L.docx"}]
    n = app.compliance_structure_from_headings(); app.update()
    check("start it from the RFP headings", n == 2 and not app._cwin.cp_nostruct.winfo_manager()
          and "L.4.1 Technical Approach" in app._cwin.cp_orows, list(app._cwin.cp_orows)[:3])
    app.matrix.outline = saved; app._c_changed(); app.update()
    # one status line
    check("one status line at the bottom", app.status.master is app.statusbar and app.lbl_aistate.master is app.statusbar)
    app.shell_go("qaqc"); app.update()
    check("QA/QC opens its own view", app.qa_view.winfo_ismapped() and not app._cwin.winfo_ismapped())
    print(f"GUI SHELL {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
    app.after(200, app.destroy)


app.after(900, go)
app.mainloop()
