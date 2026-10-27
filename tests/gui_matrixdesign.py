"""2.48.0 Compliance > Export: Compliance matrix (Excel), designed here: the preview shows the designed columns; hiding,
moving and adding a column changes the preview; Context rows can be added; Export writes the workbook (and a dated copy
is kept in the effort's exports folder); Matrix and Response Setup together writes both into one dated folder."""
import os, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, compliance as C, matrixdesign as MD, keepsafe_ui as KU
from tkinter import messagebox
from test_matrixdesign import build
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
OUT = os.path.join(tmp, "Shared"); os.makedirs(OUT)
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")
answer = {}
KU._ORIG["save"] = lambda *a, **k: answer.get("save", "")
KU._ORIG["dir"] = lambda *a, **k: answer.get("dir", "")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel"); app.update()
    M0 = build()
    mpath = os.path.join(tmp, "Kestrel", "Kestrel_Matrix.xlsx")
    M0.path = mpath; M0.save()
    app.ws.set("compliance_path", mpath)
    app.open_compliance(show=False); app.update()
    app._c_load(mpath, quiet=True); app._c_refresh()
    app.shell_go("compliance", "export"); app.update()
    app.shell_go("compliance", "matrix"); app.update()                     # 2.51.0: a step of its own
    pills = [x.cget("text").split("  ")[0] for x in app.strip_pills.winfo_children()]
    check("Compliance has a Matrix step after Assign", "4 Matrix" in pills and app._cwin.tabs.get() == "Matrix", pills)
    w = app._cwin.md_page
    api = w._api
    tv = api["tree"]
    heads = [tv.heading(c, "text") for c in tv["columns"]]
    check("the preview shows the designed columns", heads == [c["heading"] for c in MD.DEFAULT["columns"]], heads)
    kids = tv.get_children()
    check("every row, in the response structure, context under its requirement", len(kids) == 3
          and tv.item(kids[0], "values")[2].startswith("The Offeror shall describe")
          and tv.item(kids[1], "tags") == ("ctx",) and tv.item(kids[1], "values")[2].startswith("      Thermal margins")
          and "All 3 rows" in api["info"].cget("text"), [tv.item(k, "values")[:3] for k in kids])
    api["lb"].selection_clear(0, "end"); api["lb"].selection_set(10); api["toggle"](); app.update()         # hide Notes (the 11th column)
    check("hiding a column changes the preview", "Notes" not in [tv.heading(c, "text") for c in tv["columns"]])
    for i in (2, 1):                                                                                        # Requirement first
        api["lb"].selection_clear(0, "end"); api["lb"].selection_set(i); api["move"](-1); app.update()
    check("moving a column changes the order", tv.heading(tv["columns"][0], "text") == "RFP text")
    k = api["add"]("Reviewer"); app.update()
    check("a column of the team's own is added", k == "custom:Reviewer" and tv.heading(tv["columns"][-1], "text") == "Reviewer")
    api["lb"].selection_clear(0, "end"); api["lb"].selection_set(len(api["state"]["d"]["columns"]) - 1); api["toggle"](); app.update()
    check("and removed", "Reviewer" not in [tv.heading(c, "text") for c in tv["columns"]])
    api["roles"]["Context"].set(True)
    api["state"]["d"]["roles"] = ["Keep", "Context"]; app.update()
    answer["save"] = os.path.join(OUT, "Kestrel_Compliance_Matrix.xlsx")
    res = api["export"](); app.update()
    check("Export writes the workbook with the design", res and res["rows"] == 3 and os.path.isfile(answer["save"]), res)
    for _ in range(4):
        app._keep.process(now=time.time() + 30); app.update()
    kept = os.listdir(app.exports_folder()) if os.path.isdir(app.exports_folder()) else []
    check("a dated copy is kept in the effort's exports folder", any(k.startswith("Kestrel_Compliance_Matrix 20") for k in kept), kept)
    check("the design is kept with the matrix", MD.of_matrix(app.matrix)["roles"] == ["Keep", "Context"]
          and MD.of_matrix(app.matrix)["columns"][0]["key"] == "text")
    t = api["together"](OUT); app.update()
    names = [os.path.basename(p) for p in t["files"]] if t else []
    check("Matrix and Response Setup together: one dated folder with both", t and os.path.basename(t["folder"]).startswith("Kestrel compliance export")
          and any(n.endswith(".xlsx") for n in names) and any(n.endswith(".docx") for n in names), names)
    n = sum(checks)
    print(f"GUI MATRIXDESIGN PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI MATRIXDESIGN FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
