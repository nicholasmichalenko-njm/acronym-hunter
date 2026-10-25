"""2.26.0 in the app: make a found term an alt form of another (Scan review), edit alt forms on the effort list, the
home table and exports show "TT&C (TTC)", and Effort > Add this effort to the master database writes one row per term
and meaning with the efforts that used it (a second run adds nothing)."""
import os, sys, tempfile, csv, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, docxw, effort_home as H, master_db as M
from tkinter import messagebox, simpledialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.DB_FILE = os.path.join(tmp, "db.csv")
with open(A.DB_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["Term", "Category", "Definition", "Action"])
    w.writerow(["SOW", "Acronym", "Statement of Work", "Include"])
messagebox.showinfo = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
messagebox.askyesno = lambda *a, **k: True
simpledialog.askstring = lambda *a, **k: "J. Smith"
V1 = os.path.join(tmp, "Vol_1_Technical.docx")
d = docxw.Doc(); d.heading("1 Approach", 1)
d.para("The Telemetry, Tracking and Command (TT&C) radios link the bus. The TTC link closes at 2 Mbps. The SOW applies.")
d.save(V1)
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
MASTER = os.path.join(tmp, "Master_Acronym_Database.xlsx")
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


app = A.AcronymAppGUI()
st = {"t": 0}


def wait(cond, then, limit=120):
    st["t"] += 1
    if not cond() and st["t"] < limit:
        app.after(400, lambda: wait(cond, then, limit)); return
    st["t"] = 0
    then()


def step1():
    L = E.EffortList(LIST, "Kestrel", solicitation="FA8810-27-R-0042"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, first_use="volume")
    assert app.open_effort("Kestrel")
    app.start_batch([V1])
    app.after(500, lambda: wait(lambda: not (app.btn_cancel.winfo_ismapped() or app.busy()), step2))


def step2():
    app.update()
    check("TT&C and TTC found", "TT&C" in app.results and "TTC" in app.results, sorted(app.results)[:12])
    app.add_to_effort(["TT&C"])
    app.home_set_definition("TT&C", "Telemetry, Tracking and Command")
    m = A.tk.Menu(app)
    app.tree.selection_set("TTC")
    app.effort_context_menu(m, "TTC")
    sub = m.nametowidget(m.entrycget(m.index("end"), "menu"))
    labels = [sub.entrycget(i, "label") for i in range(sub.index("end") + 1) if sub.type(i) == "command"]
    check("Scan review menu offers Make an alt form", any("an alt form of" in x for x in labels), labels[-2:])
    win = app.alt_make_dialog("TTC")
    win.update(); time.sleep(0.3); win.update()
    check("the dialog suggests TT&C first", win._api["var"].get() == "TT&C", win._api["var"].get())
    win._api["ok"]("TT&C")
    app.update()
    L = app.effort
    check("TTC is an alt form of TT&C in the effort list", L.alts("TT&C") == ["TTC"] and "TTC" not in L.rows, L.rows.get("TT&C"))
    d = app.results["TTC"]
    check("TTC keeps its own row, labelled with the primary", d.get("alt_of") == "TT&C" and d["status"].startswith(A.ALT_STATUS)
          and d["selected_definition"] == "Telemetry, Tracking and Command", (d["status"], d["selected_definition"]))
    app.status_var.set("Alt forms"); app.populate_table()
    check("Status > Alt forms shows it", list(app.tree.get_children()) == ["TTC"], app.tree.get_children())
    app.status_var.set(A.STATUS_FILTERS[0]); app.populate_table()
    app.show_view(H.VIEW_HOME); app.update()
    check("home shows TT&C (TTC)", app.home_tree.set("TT&C", "term") == "TT&C (TTC)", app.home_tree.set("TT&C", "term"))
    app.home_search.set("TTC"); app.home_refresh()
    check("home search finds a term by its alt form", list(app.home_tree.get_children()) == ["TT&C"], app.home_tree.get_children())
    app.home_search.set(""); app.home_refresh()
    w2 = app.alt_edit_dialog("TT&C"); w2.update(); time.sleep(0.3); w2.update()
    w2._api["ok"]("TTC, T&C")
    check("alt forms edited", L.alts("TT&C") == ["TTC", "T&C"], L.alts("TT&C"))
    out = os.path.join(tmp, "list.csv")
    app.export_terms(out, ["Term", "Definition"], fmt="csv")
    with open(out, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    check("export writes the alt forms in parentheses", ["TT&C (TTC, T&C)", "Telemetry, Tracking and Command"] in rows, rows)
    # the master database
    L.set_status(["TT&C"], "Approved", approver="J. Smith"); app._save_effort_list()
    M.write_master(MASTER, [["SOW", "Acronym", "Statement of Work", "Include", {}]])
    rep = app.master_add_effort(MASTER, confirm=False)
    check("effort added to the master", rep and rep["added"] == ["TT&C (TTC, T&C)"], rep)
    mrows = {r[0]: r for r in M.read_master_file(MASTER)}
    tc = mrows.get("TT&C")
    check("master row keeps the effort and alt forms", tc and tc[4].get(M.USED_COL) == "Kestrel (FA8810-27-R-0042)"
          and tc[4].get("Alt forms") == "TTC | T&C" and tc[4].get(M.TIMES_COL) == "1", tc)
    check("old master kept in Master database backups", os.path.isdir(os.path.join(tmp, "Master database backups"))
          and len(os.listdir(os.path.join(tmp, "Master database backups"))) == 1)
    check("this PC loaded the new master version", M.master_info().get("path") == os.path.abspath(MASTER))
    rep2 = app.master_add_effort(confirm=False)
    check("adding the effort again changes nothing", rep2 and not rep2["added"] and not rep2["updated"], rep2)
    check("the master file still has one TT&C row", [r[0] for r in M.read_master_file(MASTER)].count("TT&C") == 1)
    imp = os.path.join(tmp, "Vol_2_Acronyms.csv")
    with open(imp, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["Acronym", "Definition"], ["SATCOM (SatCom)", "Satellite Communications"],
                                 ["TT&C (TTCM)", "Telemetry, Tracking and Command"]])
    app.import_volume_list(imp, ask=False)
    check("an imported list's \"SATCOM (SatCom)\" becomes a term with an alt form", L.alts("SATCOM") == ["SatCom"]
          and "SATCOM (SatCom)" not in L.rows and "TTCM" in L.alts("TT&C"), (L.alts("SATCOM"), L.alts("TT&C")))
    app.remove_alt("T&C", "TT&C")
    check("an alt form can be removed", L.alts("TT&C") == ["TTC", "TTCM"], L.alts("TT&C"))
    ok = all(checks.values())
    print("GUI ALT", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.update(); app.after(500, app.on_close)


app.after(1500, step1)
app.mainloop()
