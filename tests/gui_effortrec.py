"""2.40.0 the effort record on screen: Effort details and the countdown in the top bar; the stage track, gate goals
(checked by the app or by hand), notes and open questions, tasks with owners, the timeline; Move stage and Edit stages;
the simpler menu bar (File: save and import an effort package; Help: ideas and problems, AI and ML, what it is built
on; Advanced); the compliance text check (every word of the RFP files in the review, and adding a missing line); an
owner for one compliance requirement (O); saving an effort package and importing it as a second effort."""
import os, sys, tempfile, shutil, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, compliance as C, effortrec as R, effortpkg as P
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True
messagebox.showwarning = lambda *a, **k: None      # a test that checks a refusal must not leave a box on screen
messagebox.showerror = lambda *a, **k: None
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
CDIR = os.path.join(tmp, "Kestrel", "Customer documents"); os.makedirs(CDIR)
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
for f in os.listdir(RFP):
    shutil.copy2(os.path.join(RFP, f), CDIR)
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def texts_of(w):
    out = []
    for c in w.winfo_children():
        try:
            t = c.cget("text")
            if isinstance(t, str):
                out.append(t)
        except Exception:
            pass
        out += texts_of(c)
    return out


def menu_labels(m):
    pc = m.cget("postcommand")
    if pc:
        app.tk.eval(pc)
    return [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) in ("command", "cascade")]


app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    w = app.sub_add_dialog(app.sub_unadded() or [os.path.join(CDIR, f) for f in sorted(os.listdir(CDIR))])
    w.update(); w._api["add"](); app.update()
    # details and the countdown
    check("the top bar asks for the due date until it is set", app.rec_strip_refresh() == "Set the due date...")
    app.rec_details_dialog(values={"client": "USSF SSC", "sol": "FA8810-26-R-0042", "internal": "SS-118", "due": "December 15, 2026, 2:00 p.m. MT"})
    top = app.rec_strip_refresh()
    check("Effort details: the due date counts down in the top bar", " d  " in top.split("\n")[0] and top.split("\n")[1] == "to Dec 15, 2:00 p.m. MT", top)
    check("client, solicitation and internal number are saved with the effort", (app.effort.client, app.effort.solicitation, app.effort.internal_no)
          == ("USSF SSC", "FA8810-26-R-0042", "SS-118") and app.efforts.get("Kestrel")["internal_no"] == "SS-118")
    d = app.rec_details_dialog(); d.update()
    check("Effort details offers the due date found in the customer documents", any("The customer documents say: December 15, 2026" in t for t in texts_of(d)))
    d.destroy()
    # Effort home: stage track, goals, notes, tasks, timeline
    app.shell_go("home"); app.update()
    track = texts_of(app.rec_track)
    check("the stage track shows the team's stages, Intake current", sum(1 for s in R.DEFAULT_STAGES if any(t.startswith(s) for t in track)) == 7
          and any(t.startswith("Move to Author drafts") for t in track), track[:10])
    g = " | ".join(texts_of(app.rec_cards["goals"][2]))
    check("gate goals: documents added is checked by the app", "Customer documents added" in g and "by the app" in g
          and app.rec_cards["goals"][1].cget("text").startswith("Intake: gate goals"), g[:200])
    app.rec_note_dialog(on="version", on_id="x", label="RFP, Original", text="Does the page limit include the cover?", question=True)
    app.rec_note_dialog(text="Kickoff held with the capture lead.")
    app.update()
    n = " | ".join(texts_of(app.rec_cards["notes"][2]))
    check("notes and open questions show on Effort home", "QUESTION" in n and "Does the page limit include the cover?" in n
          and "Kickoff held" in n and "1 open" in app.rec_cards["notes"][1].cget("text"), n[:200])
    qid = app.effrec().open_questions()[0]["id"]
    app.rec_resolve_dialog(qid, "No, the cover is excluded")
    check("Resolve closes the question with its answer", not app.effrec().open_questions() and "ANSWERED" in " ".join(texts_of(app.rec_cards["notes"][2])))
    t1 = app.rec_task_dialog(values={"title": "Cut Vol I to 25 pages", "owner": "J. Smith", "due": "2026-01-02", "stage": "Intake"})
    app.rec_task_dialog(values={"title": "Book the gold team room", "owner": "N. Michalenko", "due": "2030-01-01"})
    app.update()
    tt = " | ".join(texts_of(app.rec_cards["tasks"][2]))
    check("tasks with owner, due date and late status", "Cut Vol I to 25 pages" in tt and "Not started (late)" in tt and "J. Smith" in tt, tt[:200])
    app.rec_who.set("J. Smith"); app._rec_force(); app.update()
    tt = " | ".join(texts_of(app.rec_cards["tasks"][2]))
    check("show one person's work", "Book the gold team room" not in tt and "J. Smith:" in tt, tt[:160])
    app.rec_who.set("Everyone"); app._rec_force()
    w = app.rec_task_dialog(t1); w.update(); w._api["status"].set("Done"); w._api["ok"](); app.update()
    check("a task edited to Done", app.effrec().task(t1)["status"] == "Done")
    # stages
    rec = app.effrec()
    n0 = rec.goal_progress(checks=app.rec_checks())
    w = app.rec_move_dialog(); w.update()
    check("Move stage offers the next stage and the open goals to carry", w._api["to"].get() == "Author drafts" and len(w._api["carry"]) == n0[1] - n0[0],
          (w._api["to"].get(), len(w._api["carry"]), n0))
    w._api["planned"].insert(0, "2026-10-17"); w._api["ok"](); app.update()
    check("moved: Author drafts is current, the open goals came along", rec.stage()["name"] == "Author drafts" and rec.stage()["planned"] == "2026-10-17"
          and any(g.get("from") == "Intake" for g in rec.stage()["goals"]))
    w = app.rec_stages_dialog(); w.update()
    w._api["add"](); w.update()
    w._api["remove"](4); w.update()                              # Gold team
    w._api["items"][-1][1] = "Orals"                             # the new stage's name
    app.rec_stages_dialog(rows=[tuple(it) for it in w._api["items"]]); w.destroy(); app.update()
    names = [s["name"] for s in rec.stages]
    check("Edit stages: a stage removed and one added", "Gold team" not in names and names[-1] == "Orals" and len(names) == 7, names)
    check("the current stage cannot be removed", app.rec_stages_dialog(rows=[(rec.stages[0]["id"], "Intake", "")]) is False)
    # the timeline
    texts = [e["text"] for e in rec.events()]
    joined = " | ".join(texts)
    check("the timeline holds the paper trail", "Kestrel RFP Sections C L M added" in joined and "Effort details: client USSF SSC" in joined
          and "Due date set to Dec 15, 2026, 2:00 p.m. MT" in joined and "Moved to Author drafts from Intake" in joined
          and "Task done: Cut Vol I to 25 pages" in joined and "Stage added: Orals" in joined and "Question on RFP, Original" in joined, joined[:500])
    tw = app.rec_timeline_window(); tw.update()
    check("Full timeline lists every event", len(tw._api["events"]) == len(rec.data["timeline"]))
    tw.destroy()
    # menus
    mb = app.menubar
    top = [mb.entrycget(i, "label") for i in range(mb.index("end") + 1)]
    check("five menus: File, Effort, View, Help, Advanced", top == ["File", "Effort", "View", "Help", "Advanced"], top)
    fl = menu_labels(app.nametowidget(mb.entrycget(0, "menu")))
    check("File: new, open, save and import an effort package, details, exports", fl[:4] == ["New effort...", "Open effort", "Save effort package...",
          "Import effort package..."] and "Effort details..." in fl and "Export all for this effort..." in fl, fl)
    hl = menu_labels(app.nametowidget(mb.entrycget(3, "menu")))
    check("Help: Guide, ideas and problems, AI and ML, what it is built on", hl == ["How it works (Guide)", "Submit an idea or report a problem...", "Coming soon...",
          "What runs where (AI and ML)...", "AI and ML: the difference...", "What Stationkeeper is built on...", "About Stationkeeper"], hl)
    al = menu_labels(app.nametowidget(mb.entrycget(4, "menu")))
    check("Advanced holds everything else", "Scan files outside an effort" in al and "Master database" in al and "Effort list and all effort commands" in al, al)
    pw = app.show_components(); pw.update()
    check("What it is built on lists the parts and their versions", any(t.startswith("Python 3") for t in texts_of(pw)) and any(t.startswith("openpyxl") for t in texts_of(pw)))
    pw.destroy()
    # compliance: text check, owner
    files = sorted(os.listdir(CDIR))
    heads = []
    mpath = os.path.join(tmp, "Kestrel", "Kestrel_Matrix.xlsx")
    M = C.Matrix(mpath, "Kestrel")
    M.items = C.extract([(f, A.typed_chunks(os.path.join(CDIR, f))) for f in files if f.lower().endswith((".docx", ".pdf"))], heads)
    M.headings = heads
    M.sources = [[f, "", "2026-10-26", os.path.join(CDIR, f)] for f in files if f.lower().endswith((".docx", ".pdf"))]
    M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Schedule")
    M.save()
    app.ws.set("compliance_path", mpath)
    app.open_compliance(); app.update()
    app._c_load(mpath, quiet=True); app._c_refresh()
    res = app.compliance_text_check(show=False)
    check("text check: every word of the RFP files is in the review", res and all(r["missing"] == 0 and r["words"] for r in res)
          and app.text_check_line(res).startswith("Text check: all"), [(r["file"], r["missing"]) for r in res])
    gone = next(it for it in app.matrix.items if "five highest" in it["text"])
    app.matrix.items.remove(gone)
    res = app.compliance_text_check(show=False)
    check("a sentence missing from the review is found", sum(r["missing"] for r in res) > 0 and any("five highest" in l for r in res for _w, l, k in r["lines"] if k == "missing"))
    win = app._c_text_check_window(res); win.update()
    check("the Text check window lists it", any("NOT IN THE REVIEW" in t and "five highest" in t for t in texts_of(win)))
    win.destroy()
    added = app.compliance_add_missing(res)
    check("Add the missing lines: the sentence is back for review", added and any("five highest" in it["text"] for it in app.matrix.items)
          and added[0]["new"] == "Added by the text check" and not sum(r["missing"] for r in app.compliance_text_check(show=False)))
    keep = next(it for it in app.matrix.items if it.get("type") not in ("Context", "Heading"))
    C.assign_requirement(app.matrix.items, [keep], "1.1 Thermal Design")
    app.shell_go("compliance", "decide"); app.update()
    app._cp_select(keep["id"]); app.update()
    n = app.cp_owner("K. Park")
    check("Owner (O): one compliance requirement gets its own owner", n == 1 and keep["owner"] == "K. Park"
          and any(f"Compliance requirement {keep['id']} assigned to K. Park" in e["text"] for e in rec.events()))
    check("people in the effort include task and requirement owners", {"K. Park", "J. Smith", "N. Michalenko"} <= set(app.rec_people()), app.rec_people())
    app._c_save_now()
    # 2.41.0: deliverables
    import deliverables as DL
    app.shell_go("submission", "deliverables"); app.update()
    pills = [w.cget("text").split("  ")[0] for w in app.strip_pills.winfo_children()]
    check("Submission has a Deliverables step after Requirements", pills[:2] == ["1 Requirements", "2 Deliverables"], pills)
    vals = {app.dl_tree.set(i, "name"): app.dl_tree.set(i, "state") for i in app.dl_tree.get_children()}
    check("deliverables named in the customer documents are suggested", vals.get("Attachment J-2") == "Suggested: add it?", vals)
    sk = next(v[1] for v in app.dl_rows.values() if v[0] == "s")
    j2 = app.dl_add_suggested(sk)
    check("Add as a deliverable", DL.get(app.effrec(), j2)["name"] == "Attachment J-2" and DL.get(app.effrec(), j2)["kind"] == "Attachment")
    import zipfile as _z
    ourdir = os.path.join(tmp, "Our drafts"); os.makedirs(ourdir)
    vol = os.path.join(ourdir, "Kestrel_Vol_1_Technical.docx")
    with _z.ZipFile(vol, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
        z.writestr("docProps/app.xml", "<Properties><Pages>27</Pages></Properties>")
    v1 = app.dl_edit_dialog(values={"name": "Volume I Technical", "kind": "Volume", "limit": "25 pages", "owner": "J. Smith"})
    app.dl_set_file(v1, vol); app.update()
    row = next(i for i, v in app.dl_rows.items() if v == ("d", v1))
    check("our Word file's page count against the limit: over is red", app.dl_tree.set(row, "state") == "Over: 27 of 25 pages"
          and "over" in app.dl_tree.item(row, "tags"), app.dl_tree.set(row, "state"))
    app.dl_tree.selection_set(row); app.update()
    dt = " | ".join(texts_of(app.dl_detail))
    check("the panel shows owner, limit, pages and the stage mark", "J. Smith" in dt and "27 (as Word last saved it)" in dt and "Done for Author drafts" in dt, dt[:300])
    DL.mark_stage(app.effrec(), v1); app._dl_after(v1)
    check("Done for this stage is recorded", app.effrec().stage()["id"] in DL.get(app.effrec(), v1)["stages_done"])
    xp = app.dl_export(os.path.join(tmp, "deliv.xlsx"))
    check("the deliverables checklist (Excel)", os.path.isfile(xp))
    # 2.40.0: the effort status report and the effort summary
    import zipfile
    sp = app.status_export(os.path.join(tmp, "status.docx"))
    x = zipfile.ZipFile(sp).read("word/document.xml").decode("utf-8")
    check("Effort status: effort, countdown, stage track, tiles, where we are", "EFFORT STATUS" in x and "Kestrel" in x and "to submission: Dec 15, 2026" in x
          and "Author drafts" in x and "gate goals met" in x and "Where we are" in x and "Left in this stage" in x)
    check("it lists the deliverables (2.41.0)", ">Deliverables<" in x and "Over: 27 of 25 pages" in x and "deliverables final" in x)
    check("it holds the open questions and notes, people, tasks, changes and requirements", "Kickoff held" in x and "People and assignments" in x
          and "K. Park" in x and "Book the gold team room" in x and "What changed since Author drafts began" in x and "Submission requirements" in x
          and "Customer documents" in x and "Complete history" not in x)
    fp = app.status_export(os.path.join(tmp, "summary.docx"), final=True)
    y = zipfile.ZipFile(fp).read("word/document.xml").decode("utf-8")
    check("Effort summary: the same report with the complete history", "EFFORT SUMMARY" in y and "Complete history" in y and "Effort started" not in y
          and "Effort details: client USSF SSC" in y and "Cut Vol I to 25 pages" in y)
    if os.environ.get("AH_KEEP_STATUS"):
        shutil.copy2(sp, os.path.join(os.environ["AH_KEEP_STATUS"], "status.docx")); shutil.copy2(fp, os.path.join(os.environ["AH_KEEP_STATUS"], "summary.docx"))
    fl = menu_labels(app.nametowidget(app.menubar.entrycget(0, "menu")))
    check("File offers the status and the summary", "Effort status (Word)..." in fl and "Effort summary, complete history (Word)..." in fl)
    # effort package: save, then import as a second effort
    app.shell_go("home"); app.update()
    pkg = os.path.join(tmp, "out", "Kestrel_handoff.ahpkg"); os.makedirs(os.path.dirname(pkg))
    man = app.pkg_save_dialog(path=pkg, customer=True)
    check("Save effort package writes one file with the list, the saved work, the matrix and the customer files",
          os.path.isfile(pkg) and man["stage"] == "Author drafts" and man["has"]["matrix"] and man["has"]["customer"]
          and any(a.startswith("data/record.json") for a in man["files"]) and not any("lock.json" in a for a in man["files"]),
          sorted(man["files"])[:6])
    got = app.pkg_import_dialog(path=pkg, dest=os.path.join(tmp, "elsewhere"), mode="both"); print("IMPORT", got and {k: got[k] for k in ("list", "name") if k in got})
    app.update()
    check("Import effort package opens it as a second effort, where it was", got and app.effort.name.startswith("Kestrel (from ")
          and app.effrec().stage()["name"] == "Author drafts" and app.effrec().data["due"] == "2026-12-15T14:00"
          and len(app.effrec().tasks()) == 2, (app.effort.name if app.effort else None))
    lib = app.doclib()
    check("the customer documents and their versions came along, pointing at the new folder",
          lib.docs and all(v["path"].startswith(os.path.join(tmp, "elsewhere")) for d in lib.docs for v in d["versions"]))
    check("the matrix came along", os.path.normcase(app.ws.get("compliance_path", "")).startswith(os.path.normcase(os.path.join(tmp, "elsewhere"))))
    dl2 = DL.items(app.effrec())
    vrow = next(d for d in dl2 if d["name"] == "Volume I Technical")
    check("a deliverable's own file travelled and points at the new folder (2.41.0)", vrow["file"].startswith(os.path.join(tmp, "elsewhere"))
          and os.path.isfile(vrow["file"]) and len(dl2) == 2, vrow["file"])
    check("the import is in its timeline", app.effrec().events()[0]["text"].startswith("Effort package imported: saved by"))
    try:
        P.read_manifest(os.path.join(CDIR, files[0]))
        bad = False
    except P.PackageError:
        bad = True
    check("a file that is not a package is refused", bad)
    print(f"GUI EFFORTREC {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
    app.after(200, app.on_close)


A.set_ai_ml(True)
app.after(900, go)
app.mainloop()
