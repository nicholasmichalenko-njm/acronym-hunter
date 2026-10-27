"""2.53.0 the relationships you decide in Assign, visible: a REQ label on each compliance requirement and a SUPPORTS
label on each support sentence (naming what it supports); lines in the left margin from the selected sentence to the
sentences it is tied to; a Relationships panel with Jump and Unlink; a banner saying what Support linked to; a label
click jumps to the requirement; splitting still works with the labels in place."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
for n in ("showinfo", "showwarning"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
TEXT = ("L.4 Technical Volume\nThe Offeror shall describe the thermal design. Thermal margins matter because the orbit has long "
        "eclipses. The radiators were sized in 2019. The Offeror shall provide a schedule. Schedules slip when parts arrive late. "
        "The program office is in Colorado.")
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("Section L.docx", [("Page 1", TEXT)])])
M.outline = C.parse_outline("Volume I\n1.1 Thermal\n1.2 Schedule")
M.save()
app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    win = app.open_compliance(); win.update()
    app._c_load(M.path, quiet=True); app._c_refresh(); win.update()
    app.shell_go("compliance", "decide"); app.update()
    items = app.matrix.items
    by = lambda w: next(it for it in items if w in it["text"])
    th, mg, rad, sc, slip = by("thermal design"), by("Thermal margins"), by("radiators"), by("provide a schedule"), by("Schedules slip")
    for x, sec in ((th, "1.1 Thermal"), (sc, "1.2 Schedule")):
        C.assign_requirement(items, [x], sec)
    app._c_changed(); app._cwin.cp_sig = None; app._c_refresh(); app.update()
    app._cp_select(mg["id"]); app.update()
    r = app.cp_ctx(); app.update()
    t = app._cwin.cp_text
    check("C (Support) links to the nearest requirement and the banner says so", mg["context_for"] == th["id"]
          and "supports " + th["id"] in app._cwin.cp_banner.cget("text") and app._cwin.cp_banner.winfo_manager(), app._cwin.cp_banner.cget("text"))
    C.assign_context(items, [rad], [th["id"], sc["id"]]); C.assign_context(items, [slip], [sc["id"]])
    app._c_changed(); app.update()
    whole = t.get("1.0", "end").replace("\u00a0", " ")
    check("labels: REQ on each requirement, SUPPORTS naming what each support sentence supports",
          f" REQ {th['id']} " in whole and f" SUPPORTS {th['id']} " in whole and f" SUPPORTS {th['id']}, {sc['id']} " in whole, whole[:300])
    app._cp_select(th["id"]); app.update()
    n = app._cp_lines()
    check("a requirement selected: a line to each sentence that supports it", n == 2, n)
    def texts(w):
        out = []
        for c in w.winfo_children():
            try:
                out.append(str(c.cget("text")))
            except Exception:
                pass
            out += texts(c)
        return out
    rel = " | ".join(texts(app._cwin.cp_rel))
    check("Relationships: supported by, each with Jump and Unlink", "Supported by 2" in rel and f"SUPPORT {mg['id']}" in rel and "Unlink" in rel, rel[:200])
    app._cp_select(rad["id"]); app.update()
    check("a support sentence selected: a line to each requirement it supports", app._cp_lines() == 2)
    app.cp_unlink(rad["id"], th["id"]); app.update()
    check("Unlink takes one tie away, the other stays", C.cf_ids(rad["context_for"]) == [sc["id"]]
          and f" SUPPORTS {sc['id']} " in t.get("1.0", "end").replace("\u00a0", " "))
    rr = t.tag_ranges("b:" + slip["id"])
    bb = t.bbox(rr[0])
    class Ev: pass
    e = Ev(); e.x, e.y = bb[0] + 2, bb[1] + 2
    app._cp_badge_click(e); app.update()
    check("clicking a SUPPORTS label jumps to the requirement", app._c_selected()[0]["id"] == sc["id"])
    app._cp_select(sc["id"]); app.update()
    rng = t.tag_ranges("r:" + sc["id"])
    check("the labels sit outside the sentence (its own text is unchanged)", t.get(rng[0], rng[1]) == sc["text"])
    app.cp_link_more(rad["id"]); app.update()
    check("Link to another requirement...: the Support banner says what to do", "Click each compliance requirement" in app._cwin.cp_banner.cget("text"))
    app.cp_ctx_click(th["id"]); app.cp_mode_end(quiet=True); app.update()
    check("and clicking a requirement adds it", th["id"] in C.cf_ids(rad["context_for"]) and not app._cwin.cp_banner.winfo_manager())
    n = sum(checks)
    print(f"GUI RELATIONS PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI RELATIONS FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
