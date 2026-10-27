"""2.46.0 exports kept and backups in the app: a real export (File > Effort status) and a folder export (Export all)
are copied, dated, into "<effort> - exports (Stationkeeper)"; creating the effort list is not; with no effort open
nothing is kept. Advanced > Backup location...: the suggested folder, the OneDrive caution, Back up now, a backup when
the effort closes, Turn off."""
import os, sys, tempfile, time, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, keepsafe as K, keepsafe_ui as KU
from tkinter import messagebox, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
CDIR = os.path.join(tmp, "Kestrel", "Customer documents"); os.makedirs(CDIR)
OUT = os.path.join(tmp, "Shared"); os.makedirs(OUT)
checks = []
answer = {"save": "", "dir": ""}


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")
KU._ORIG["save"] = lambda *a, **k: answer["save"]          # the save windows answer as a person would
KU._ORIG["dir"] = lambda *a, **k: answer["dir"]


def settle():
    for _ in range(4):
        app.update()
        app._keep.process(now=time.time() + 30)
        app.keep_tick()


def go():
    answer["save"] = os.path.join(OUT, "loose.docx")
    filedialog.asksaveasfilename(title="Save the list"); open(answer["save"], "w").write("x")
    check("no effort open: nothing is kept", not app._keep.pending)
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    ex = app.exports_folder()
    answer["save"] = LIST
    filedialog.asksaveasfilename(title="Where should the effort list live?")
    check("the window that creates the effort list is not an export", not app._keep.pending)
    answer["save"] = os.path.join(OUT, "Kestrel_Effort_Status.docx")
    p = app.status_export()
    check("File > Effort status writes where the person chose", p == answer["save"] and os.path.isfile(p))
    settle()
    kept = os.listdir(ex) if os.path.isdir(ex) else []
    check("a dated copy is kept in the effort's exports folder", len(kept) == 1 and kept[0].startswith("Kestrel_Effort_Status 20")
          and kept[0].endswith(".docx") and os.path.dirname(ex) == os.path.dirname(LIST), kept)
    answer["dir"] = OUT
    w = app.export_all_dialog(); app.update()
    for k, v in w.api["vars"].items():
        v.set(k in ("list",) or v.get())
    w.api["go"](); app.update()
    settle()
    trees = [k for k in os.listdir(ex) if os.path.isdir(os.path.join(ex, k))]
    inner = [f for dp, _d, fs in os.walk(os.path.join(ex, trees[0])) for f in fs] if trees else []
    check("Export all (a folder export) is kept as a dated folder", len(trees) == 1 and trees[0].startswith("Shared export 20") and inner and "loose.docx" not in inner, (trees, inner))
    # the backup location
    home = os.path.join(tmp, "home"); os.makedirs(os.path.join(home, "Documents"))
    os.environ["HOME"] = os.environ["USERPROFILE"] = home
    d = app.backup_location_dialog(); app.update()
    d._api["suggested"](); app.update()
    bdir = os.path.join(home, "Documents", "Stationkeeper backups")
    check("Use Documents\\Stationkeeper backups", app.backup_dir() == bdir and "Backing up to" in d._api["status"].cget("text"))
    check("a local folder shows no caution", d._api["warn"].cget("text") == "")
    od = os.path.join(home, "OneDrive - Sierra Space", "Documents", "Stationkeeper backups")
    app.backup_set(od); d._api["show"](); app.update()
    check("a OneDrive folder shows the caution", "OneDrive" in d._api["warn"].cget("text"))
    d._api["suggested"](); app.update()
    d._api["now"](); app.update()
    root = os.path.join(bdir, "Kestrel")
    pk = os.path.join(root, "Kestrel - latest.skpkg")
    check("Back up now writes the latest package, today's package and the settings zip", os.path.isfile(pk)
          and sum(1 for f in os.listdir(root) if f.endswith(".skpkg")) == 2
          and any(f.startswith("Stationkeeper settings and team lists") for f in os.listdir(bdir)), os.listdir(root))
    check("the exports and the readable copy are mirrored", os.path.isdir(os.path.join(root, "Exports"))
          and os.path.isfile(os.path.join(root, "Readable copy", "READ ME FIRST.txt")))
    check("the dialog shows the last backup", "Last backup:" in d._api["status"].cget("text"))
    d.destroy()
    t0 = os.path.getmtime(pk)
    time.sleep(1.1)
    app.rec_task_dialog(values={"title": "Confirm red team reviewers", "owner": "J. Smith"}); app.update()
    app.leave_workspace(); app.update()
    with zipfile.ZipFile(pk) as z:
        rec = z.read(next(n for n in z.namelist() if n.endswith("record.json"))).decode("utf-8")
    check("closing the effort backs it up with the latest change", os.path.getmtime(pk) > t0 and "Confirm red team reviewers" in rec)
    m = __import__("tkinter").Menu(app)
    labels = []
    for i in range(app.menubar.index("end") + 1):
        if app.menubar.type(i) == "cascade" and app.menubar.entrycget(i, "label") == "Advanced":
            sub = app.nametowidget(app.menubar.entrycget(i, "menu"))
            labels = [sub.entrycget(j, "label") for j in range(sub.index("end") + 1) if sub.type(j) == "command"]
    check("Advanced > Backup location...", "Backup location..." in labels, labels)
    app.backup_set("")
    check("Turn off", app.backup_dir() == "" and app.backup_now() is None)
    n = sum(checks)
    print(f"GUI KEEPSAFE PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI KEEPSAFE FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
