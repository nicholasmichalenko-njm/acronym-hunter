"""2.56.0 a compliance requirement in several proposal sections: R with another target section adds it there and keeps
the first; Relationships lists its sections with Remove; the matrix has one row per section (support under each);
the Response Setup prints it in each section; Remove takes it out of one; X clears every section."""
import os, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, setupdoc as SD, matrixdesign as MD
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
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("RFP.docx", [("Page 1", "L.4 Technical\nThe Offeror shall describe the thermal and schedule approach.\n"
                                                "Thermal margins matter because of long eclipses.\nThe Offeror shall provide a test plan.")])])
M.outline = C.parse_outline("1.1 Thermal\n1.2 Schedule\n1.3 Test")
SD.setup_of(M)["complete_v"] = 1
M.save()
app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    app.open_compliance(); app._c_load(M.path, quiet=True); app.update()
    app.shell_go("compliance", "decide"); app.update()
    win = app._cwin
    by = lambda w: next(it for it in app.matrix.items if it["text"].startswith(w))
    req, sup = by("The Offeror shall describe"), by("Thermal margins")
    app._cp_select(req["id"]); app.update()
    win.cp_next_var.set(False)
    app.cp_section_click("1.1 Thermal"); app.cp_req(); app.update()
    app.cp_section_click("1.1 Thermal")                       # clear the target
    app._cp_select(req["id"]); app.update()
    app.cp_section_click("1.2 Schedule"); app.cp_req(); app.update()
    check("R with another target adds the section and keeps the first", req["decision"] == "Keep"
          and SD.item_sections(app.matrix, req) == ["1.1 Thermal", "1.2 Schedule"], SD.item_sections(app.matrix, req))
    app.cp_section_click("1.2 Schedule")
    app._cp_select(req["id"]); app.update()
    def texts(w):
        out = []
        for c in w.winfo_children():
            try:
                out.append(str(c.cget("text")))
            except Exception:
                pass
            out += texts(c)
        return out
    rel = " | ".join(texts(win.cp_rel))
    check("Relationships lists both sections with Remove", "1.1 Thermal" in rel and "1.2 Schedule" in rel and rel.count("Remove") >= 2, rel[:200])
    app._cp_select(sup["id"]); app.update()
    app.cp_ctx(); app.update()
    check("C on the next sentence: support for that requirement (the last one clicked)", sup["decision"] == "Context"
          and sup["context_for"] == req["id"], sup.get("context_for"))
    d = dict(MD.DEFAULT); d["order"] = "structure"
    items, vals = MD.rows(app.matrix, d)
    mine = [(x.get("_kind"), x.get("id"), x.get("map")) for x in items if x.get("id") in (req["id"], sup["id"])]
    check("the matrix: one row per section, the support under each", mine == [("req", req["id"], "1.1 Thermal"), ("ctx", sup["id"], "1.1 Thermal"),
                                                                         ("req", req["id"], "1.2 Schedule"), ("ctx", sup["id"], "1.2 Schedule")]
          or mine[:1] == [("req", req["id"], "1.1 Thermal")] and [m for m in mine if m[0] == "req"] == [("req", req["id"], "1.1 Thermal"), ("req", req["id"], "1.2 Schedule")]
          and sum(1 for m in mine if m[0] == "ctx") == 2 and mine[-1] == ("ctx", sup["id"], "1.2 Schedule"), mine)
    P = SD.placed_in(app.matrix)
    check("the Response Setup prints it in each section", req["id"] in P["1.1 Thermal"] and req["id"] in P["1.2 Schedule"])
    app.cp_remove_section(req["id"], "1.1 Thermal"); app.update()
    check("Remove takes it out of one section; it stays in the other", SD.item_sections(app.matrix, req) == ["1.2 Schedule"]
          and req["map"] == "1.2 Schedule", SD.item_sections(app.matrix, req))
    app.cp_section_click("1.3 Test"); app._cp_select(req["id"]); app.cp_req(); app.cp_section_click("1.3 Test")
    app._c_save_now()
    M2 = C.Matrix(M.path).load()
    r2 = next(it for it in M2.items if it["id"] == req["id"])
    check("kept with the matrix", SD.item_sections(M2, r2) == ["1.2 Schedule", "1.3 Test"], SD.item_sections(M2, r2))
    app._cp_select(req["id"]); app.cp_clear(); app.update()
    check("X clears it from every section", req["decision"] == "" and SD.item_sections(app.matrix, req) == [])
    n = sum(checks)
    print(f"GUI MULTISEC PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI MULTISEC FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
