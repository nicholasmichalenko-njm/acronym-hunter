"""2.50.0 Training Studio: five step tabs; Gather adds past matrices; Review shows the lines set aside as the test set;
Measure fills the scorecard and leaves out what got worse; double-click leaves an area out; Build writes one .skknow.
Stationkeeper: File > Install Knowledge Pack... and the install card (what was tested, what it adds), Install."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A
import corrections as C
import compliance as CM
from tkinter import messagebox
from PIL import Image
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); os.makedirs(A.CONFIG_DIR)
A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\nSOW,Acronym,Statement of Work,Include\nTT&C,Acronym,\"Telemetry, Tracking and Command\",Include\n")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
open(A.OCR_FIXES_FILE, "w", encoding="utf-8").write("Misread,Correct,Note\nTT8C,TT&C,\n")
for n in ("showinfo", "showwarning"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
messagebox.askyesno = lambda *a, **k: True
C.set_dir(os.path.join(tmp, "team_td"))
img = Image.new("RGB", (80, 24), "white")
for i in range(40):
    C.save_sample(img, f"TT&C link {i}", f"TT8C link {i}", 0.5, "Deck.pptx (Slide 2)", (0, 0, 80, 24))
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def matrix(name, n):
    text = "L.4 Technical Volume\n" + " ".join([f"The Offeror shall describe item {i} of the thermal design." for i in range(n)] +
                                               [f"Background paragraph {i} explains the history of the office." for i in range(n)])
    M = CM.Matrix(os.path.join(tmp, name), "K")
    M.items = CM.extract([("Section L.docx", [("Page 1", text)])])
    M.outline = CM.parse_outline("Volume I\n1.1 Thermal\n1.2 History")
    for it in M.items:
        if "shall" in it["text"]:
            it["decision"], it["map"] = "Keep", "1.1 Thermal"
        elif "Background" in it["text"]:
            it["decision"] = "Drop"
    M.save()
    return M.path


import training_app as T
tapp = T.TrainingApp()
PACK = os.path.join(tmp, "Stationkeeper Knowledge 2026-11-03.skknow")


def team():
    tabs = list(tapp.tabs._tab_dict)
    check("five steps: Gather, Review, Train, Measure, Build the pack", tabs == T.STEPS, tabs)
    res = tapp.gather_matrices([matrix("Kestrel_Matrix.xlsx", 20), matrix("Osprey_Matrix.xlsx", 18)])
    g = tapp.lbl_gather.cget("text")
    check("Gather: matrices learned, lines counted with the test set", [n for _f, n in res] == [40, 36] and "Past compliance matrices gathered: 2" in g
          and "set aside as the test set" in g, g)
    tapp.filter.set("Test set (set aside)"); tapp.fill()
    ts = [tapp.tv.set(i, "state") for i in tapp.tv.get_children()]
    check("Review: the test set shows, marked", ts and all(x == "Test set" for x in ts), len(ts))
    tapp.filter.set(T.FILTERS[0]); tapp.fill()
    rows = tapp.measure(); tapp.update()
    by = {r["area"]: r for r in rows}
    vals = {tapp.sc.set(i, "title"): tapp.sc.set(i, "pack") for i in tapp.sc.get_children()}
    check("Measure: the scorecard", by["fixes"]["include"] and by["fixes"]["after"] == 100.0 and by["compliance"]["include"]
          and vals.get("OCR fixes and ignore list") == "Yes", vals)
    tapp.toggle_area("acronyms"); tapp.update()
    check("an area left out by the trainer", not {r["area"]: r for r in tapp.score_rows}["acronyms"]["include"]
          and "Left out by you" in {tapp.sc.set(i, "title"): tapp.sc.set(i, "pack") for i in tapp.sc.get_children()}["Acronyms master database"])
    tapp.toggle_area("acronyms")
    tapp.build_notes.insert(0, "Kestrel and Osprey")
    info = tapp.build_pack(PACK)
    check("Build: one .skknow file with the areas kept", os.path.isfile(PACK) and "ocr_corrections.csv" in info["files"]
          and info.get("scorecard") and "Built Stationkeeper Knowledge 2026-11-03.skknow" in tapp.lbl_build.cget("text"))
    tapp.destroy()


tapp.after(1200, team)
tapp.mainloop()

open(A.OCR_FIXES_FILE, "w", encoding="utf-8").write("Misread,Correct,Note\n")            # another PC: no fixes yet
app = A.AcronymAppGUI()


def user():
    m = app.menubar
    fm = app.nametowidget(m.entrycget(0, "menu"))
    app.show_file_menu(fm)
    labels = [fm.entrycget(i, "label") for i in range(fm.index("end") + 1) if fm.type(i) == "command"]
    check("File > Install Knowledge Pack...", "Install Knowledge Pack..." in labels, labels)
    w = app.knowledge_card(PACK); app.update()
    t = w._api["tested"]
    check("the card says what was tested", any(x.startswith("OCR fixes and ignore list: Words right on corrected lines") and "100.0%" in x for x in t), t)
    check("and what it adds", any("database rows" in a for a in w._api["adds"]), w._api["adds"])
    w._api["install"](); app.update()
    fixes = A.read_ocr_fix_rows()
    check("Install: the knowledge is here", any(r[0] == "TT8C" for r in fixes) and not w.winfo_exists())
    check("Undo puts it back", A.restore_last_knowledge_backup() and not A.read_ocr_fix_rows())
    n = sum(checks)
    print(f"GUI STUDIO PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI STUDIO FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(1200, user)
app.mainloop()
