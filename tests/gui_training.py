"""2.15.0 training as its own program. Acronym Hunter: no Trainer, no Improve Reading, no model loading or pack
export; Report misreading saves corrections, the banner and Tools > Send corrections write a corrections pack.
Acronym Hunter Training: imports the pack, shows each line with its picture, rejects and fixes lines, opens the
Trainer, Improve Reading and the Knowledge Pack window with Export and Load Trained Models."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A
import secure, sensitivity
secure.EFFORT_LEVEL = sensitivity.CUI      # 2.97.0: training lines are kept for an effort at most CUI
import corrections as C
from tkinter import messagebox
from PIL import Image
import customtkinter as ctk
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
messagebox.showinfo = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
messagebox.askyesno = lambda *a, **k: True
C.set_dir(os.path.join(tmp, "user_td"))
img = Image.new("RGB", (80, 24), "white")
for t, r in (("RFP", "RFF"), ("SE&I", "SE8I")):
    C.save_sample(img, t, r, 0.5, "Deck.pptx (Slide 2)", (0, 0, 80, 24))
PACK = os.path.join(tmp, "AcronymHunter_Corrections_test.zip")
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


def texts(w):
    out = []
    for c in w.winfo_children():
        try:
            out.append(str(c.cget("text")))
        except Exception:
            pass
        out += texts(c)
    return out


app = A.AcronymAppGUI()


def user_steps():
    check("Acronym Hunter: training lives elsewhere", not A.trainer_available() and A.corrections_on())
    m = app.tools_menu
    app.show_tools_menu(m)           # passing the menu builds it without popping it up (a popup blocks on Windows)
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) == "command"]
    check("Tools: no Improve Reading or Trainer", not any(l.startswith(("Improve Reading", "Trainer")) for l in labels), labels)
    check("Tools: Send training data", any(l.startswith("Send training data") for l in labels))
    app.update_banner(); app.update()
    check("banner offers to send", app.banner.winfo_manager() and "not sent" in app.lbl_banner.cget("text")
          and app.btn_improve.cget("text") == "Send training data...", app.lbl_banner.cget("text"))
    check("preview button says Report misreading", app.preview.btn_teach.cget("text") == "Report misreading"
          and not app.preview.btn_trainer.winfo_manager())
    w = app.open_knowledge(); app.update()
    t = texts(app.know_win)
    check("Knowledge window: install and undo only", "Install Knowledge Pack..." in t and "Export Knowledge Pack..." not in t
          and "Load Trained Models..." not in t, [x for x in t if x.endswith("...")])
    app.know_win.destroy()
    r = app.send_corrections(PACK, ask=False)
    check("send writes a corrections pack", r and r["lines"] == 2 and os.path.isfile(PACK), r)
    app.update_banner(); app.update()
    check("banner goes away once sent", not app.banner.winfo_manager())
    check("nothing new to send twice", app.send_corrections(os.path.join(tmp, "again.zip"), ask=False) is None)
    app.on_close()


app.after(1500, user_steps)
app.mainloop()

# ---- Acronym Hunter Training (its own program) ----
import training_app as T
C.set_dir(os.path.join(tmp, "team_td"))
tapp = T.TrainingApp()


def team_steps():
    check("Training: training features on", A.TRAINING_APP and A.trainer_available())
    done, failed = tapp.import_packs([PACK], ask=False)
    check("import the pack", len(done) == 1 and not failed and len(tapp.tv.get_children()) == 2, (done, failed))
    rows = {tapp.tv.set(i, "text"): i for i in tapp.tv.get_children()}
    tapp.tv.selection_set(rows["RFP"]); tapp.update(); tapp.show_picture()
    check("picture shown for the selected line", tapp._thumb is not None and "RFF" in tapp.lbl_pic.cget("text"))
    tapp.set_rejected(True, [rows["RFP"]])
    check("reject: not taught", tapp.training_state()[0] == 1 and tapp.tv.set(rows["RFP"], "state") == "Rejected")
    check("fix the text", tapp.fix_text(rows["SE&I"], "SE&I (fixed)") and "SE&I (fixed)" in [tapp.tv.set(i, "text") for i in tapp.tv.get_children()])
    tapp.filter.set("Rejected"); tapp.fill()
    check("filter: rejected", list(tapp.tv.get_children()) == [rows["RFP"]])
    tapp.filter.set(T.FILTERS[0]); tapp.fill()
    done, failed = tapp.import_packs([PACK], ask=False)
    check("the same pack again adds nothing", "already here" in done[0], done)
    bad = os.path.join(tmp, "bad.zip"); open(bad, "wb").write(b"not a zip")
    done, failed = tapp.import_packs([bad], ask=False)
    check("a bad file is refused", failed and not done, failed)
    tapp.open_knowledge(); tapp.update()
    t = texts(tapp.know_win)
    check("Knowledge window: export and load trained models", "Export Knowledge Pack..." in t and "Load Trained Models..." in t)
    tapp.know_win.destroy()
    tapp.open_improve(); tapp.update()
    check("Improve Reading opens", tapp.improve_win is not None and tapp.improve_win.winfo_exists())
    tapp.improve_win.destroy()
    tapp.open_trainer(); tapp.update()
    check("Trainer opens", tapp.trainer_win is not None and tapp.trainer_win.winfo_exists())
    tapp.trainer_win.destroy()
    rep = tapp.prepare_package()
    check("package for the Training Kit", "Text-line samples" in rep, rep[:80])
    ok = all(checks.values())
    print("GUI TRAINING", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    tapp.destroy()


tapp.after(1200, team_steps)
tapp.mainloop()
