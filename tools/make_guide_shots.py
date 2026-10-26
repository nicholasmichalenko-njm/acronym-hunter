"""Guide screenshots for 2.14 to 2.21 features (run on the Windows build PC with the desktop unlocked).

    venv\\Scripts\\python.exe tools\\make_guide_shots.py

Uses the fictional test_samples only, in a temporary config folder, and writes assets\\help\\topbar.png, shell.png,
home.png, scanreview.png, keywords.png, suggest.png, compliance.png, prove.png, setup.png, whatruns.png, stack.png,
qa.png and training.png (2.33.0: the one-feature-at-a-time layout). Each picture is the window region of one view, captured
with PIL ImageGrab, so the window must be on screen and not covered.
"""
import os, sys, shutil, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, effort_home as H
from tkinter import messagebox
from PIL import ImageGrab, Image

OUT = os.environ.get("AH_SHOTS_OUT") or os.path.join(A.BASE_DIR, "assets", "help")
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(A.CONFIG_DIR, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
SAMPLES = os.path.join(A.BASE_DIR, "test_samples")
CDIR = os.path.join(tmp, "Kestrel Thermal", "Customer documents"); os.makedirs(CDIR)
for f in os.listdir(os.path.join(SAMPLES, "rfp")):
    shutil.copy2(os.path.join(SAMPLES, "rfp", f), CDIR)
LIST = os.path.join(tmp, "Kestrel Thermal", "Kestrel_Thermal_Effort_List.xlsx")
VOL = os.path.join(SAMPLES, "Kestrel_Technical_Volume.docx")
made = []


def grab(widget, name, pad=0):
    widget.update_idletasks(); widget.update()
    time.sleep(0.6); widget.update()
    x, y = widget.winfo_rootx() - pad, widget.winfo_rooty() - pad
    w, h = widget.winfo_width() + 2 * pad, widget.winfo_height() + 2 * pad
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    img.save(os.path.join(OUT, name))
    made.append(f"{name} {img.width}x{img.height}")


import customtkinter as ctk


def fit(win, w=0.8, h=0.78):
    """Size a window to fit on screen above the taskbar (geometry is in scaled units)."""
    sc = float(ctk.ScalingTracker.get_window_scaling(win))
    win.geometry(f"{int(win.winfo_screenwidth() * w / sc)}x{int(win.winfo_screenheight() * h / sc)}+10+10")


app = A.AcronymAppGUI()
fit(app)


def zoom():
    try:
        app.state("zoomed")              # Windows; elsewhere the window stays as it is
    except Exception:
        pass
    app.update()


def wait(cond, then, n=0):
    if not cond() and n < 240:
        app.after(500, lambda: wait(cond, then, n + 1)); return
    then()


def step1():
    L = E.EffortList(LIST, "Kestrel Thermal", client="USSF SSC", solicitation="FA8810-27-R-0042"); L.pending = True; L.save()
    app.efforts.put("Kestrel Thermal", path=LIST, customer_dir=CDIR, client="USSF SSC", solicitation="FA8810-27-R-0042")
    app.open_effort("Kestrel Thermal")
    app.start_batch([VOL] + [os.path.join(CDIR, f) for f in sorted(os.listdir(CDIR))])
    wait(lambda: not app.busy() and not app.btn_cancel.winfo_ismapped(), step2)


def step2():
    terms = [t for t, d in app.results.items() if not d.get("excluded") and not d.get("file_error")][:14]
    app.add_to_effort(terms)
    app.add_volume("Vol I Technical", [VOL])
    app.effort.set_status(terms[:4], "Approved", approver="J. Smith"); app._save_effort_list()
    app.shell_go("home"); app.update()
    grab(app, "shell.png")
    app.shell_go("acronyms", "review"); app.update()
    grab(app.topbar, "topbar.png")
    if app.tree.get_children():
        first = app.tree.get_children()[0]
        app.tree.selection_set(first); app.on_select(None)
    grab(app.scan_view, "scanreview.png")
    app.shell_go("acronyms", "approve"); app.update()
    grab(app.home_view, "home.png")
    app.shell_go("keywords")
    for t, c in (("thermal control system", "Our solution"), ("radiator panel sizing", "Differentiator"),
                 ("Integrated Master Schedule", "Customer emphasis")):
        app.kw_add(t, c, "Typed in")
    app.kw_set_status("Keep", ["thermal control system"])
    grab(app.kw_view, "keywords.png")
    sw = app.kw_suggest_dialog(wait=True)
    fit(sw, 0.7, 0.7); sw.update()
    tv = sw._api["tree"]
    if tv.get_children():
        tv.selection_set(tv.get_children()[0]); sw.update()
    grab(sw, "suggest.png")
    sw.destroy()
    app.after(800, step3)


def step3():
    """Setup tab with suggestions accepted, the What runs where window and one ? panel (2.22.0)."""
    import compliance as C
    mpath = os.path.join(tmp, "Kestrel Thermal", "Kestrel_Matrix.xlsx")
    files = sorted(os.listdir(CDIR))
    heads = []
    M = C.Matrix(mpath, "Kestrel Thermal")
    M.items = C.extract([(f, A.typed_chunks(os.path.join(CDIR, f))) for f in files], heads)
    M.headings = heads
    M.sources = [[f, "", "2026-10-24", os.path.join(CDIR, f)] for f in files]
    M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management\n"
                                "Volume II Management\n2.1 Schedule\n2.2 Staffing")
    labs = [C.outline_label(o) for o in M.outline if o["level"] > 1]   # 2.36.0: assigned into sections as it goes
    stats = C.word_df(M.items)
    for i, it in enumerate(M.items[:-12]):
        if it["suggest"] == "Drop":
            continue
        lab = C.suggest_map(it, M.outline, stats)[0] or labs[i % len(labs)]
        C.assign_requirement(M.items, [it], lab if lab in labs else labs[0])
    ctx = M.items[-12]
    keeps = [x["id"] for x in M.items if x.get("file") == ctx.get("file") and x["decision"] == "Keep"][-2:]
    C.assign_context(M.items, [ctx], keeps)
    M.save()
    app.ws.set("compliance_path", mpath)
    app.open_compliance(); app.update()
    app._c_load(mpath, quiet=True); app._c_refresh()
    app.shell_go("compliance", "decide"); app.update()
    app.cp_section_click(app.matrix.items[0]["map"] or labs[0]); app.update()
    app._cp_select(ctx["id"]); app.update()

    def shot_setup():
        zoom(); time.sleep(0.8); app.update()
        grab(app.main, "compliance.png")
        app.setup_accept(); app.update()
        app._cwin.tabs.set("Setup"); app.update()          # the setup board opens from Assign
        out = app._cwin.s_out
        for iid in out.get_children()[:3]:
            out.item(iid, open=True)
        grab(app.main, "setup.png")
        app.shell_go("compliance", "prove"); app.update()
        grab(app.main, "prove.png")
        w = app.show_what_runs(); w.update()
        app.after(1200, lambda: shot_runs(w))

    def shot_runs(w):
        w.geometry("1100x680+10+10"); w.update(); time.sleep(0.8); w.update()
        print("what runs geometry:", w.winfo_width(), w.winfo_height(), w.wm_geometry())
        grab(w, "whatruns.png")
        w.destroy(); app.update()
        s = app.show_stack("scan"); s.update()
        app.after(1000, lambda: (grab(s, "stack.png"), s.destroy(), app.after(800, step4)))

    app.after(1500, shot_setup)


def step4():
    """QA/QC view after checking the sample technical volume (2.24.0)."""
    zoom()
    app.shell_go("qaqc"); app.update()
    app.check_volumes([VOL])
    wait(lambda: not app.busy() and not app.btn_cancel.winfo_ismapped() and getattr(app, "volume_report", None),
         lambda: app.after(1500, lambda: (grab(app.qa_view, "qa.png"), app.after(500, finish))))


def finish():
    app.on_close()


app.after(1500, step1)
app.mainloop()

# Acronym Hunter Training with one corrections pack
import corrections as C, training_app as T
C.set_dir(os.path.join(tmp, "user_td"))
img = Image.new("RGB", (160, 36), "white")
from PIL import ImageDraw
for t, r in (("RFP", "RFF"), ("SE&I", "SE8I"), ("TT&C", "TT8C")):
    im = img.copy(); ImageDraw.Draw(im).text((10, 10), r, fill="black")
    C.save_sample(im, t, r, 0.55, "Kestrel_PDR_Briefing.pptx (Slide 5, image 'Diagram')", (0, 0, 160, 36))
pack = os.path.join(tmp, "AcronymHunter_Corrections_sample.zip")
C.export_pack(pack)
C.set_dir(os.path.join(tmp, "team_td"))
tapp = T.TrainingApp(); fit(tapp)


def team():
    tapp.import_packs([pack], ask=False)
    kids = tapp.tv.get_children()
    if kids:
        tapp.tv.selection_set(kids[0]); tapp.show_picture()
    grab(tapp, "training.png")
    tapp.after(500, tapp.destroy)


tapp.after(1500, team)
tapp.mainloop()
print("GUIDE SHOTS:", "; ".join(made))
