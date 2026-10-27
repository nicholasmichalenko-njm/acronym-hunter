"""2.51.0 a matrix read before 2.51.0 that is missing lines gets them back, in their place, when it opens (once); a
line added from the text check goes where it is in the document even when it has no letters (a phone number)."""
import os, sys, tempfile, shutil
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
SRC = os.path.join(os.path.dirname(HERE), "test_samples", "rfp_stress", "Stress_RFP.docx")
DOC = os.path.join(EDIR, "Stress_RFP.docx"); shutil.copy2(SRC, DOC)
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("Stress_RFP.docx", A.rfp_chunks(DOC))])
M.sources = [["Stress_RFP.docx", "", "2026-10-27", DOC]]
gone = [it for it in M.items if "555-0142" in it["text"] or it["text"] == "Margins: 1 inch"]
before = [M.items[M.items.index(g) - 1]["text"] for g in gone]
for g in gone:
    M.items.remove(g)
M.save()
app = A.AcronymAppGUI()


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    win = app.open_compliance(); win.update()
    items = app.matrix.items
    texts = [it["text"] for it in items]
    back = [it for it in items if it.get("new") == "Added by the text check"]
    check("the missing lines came back when the matrix opened", len(back) == 2 and any("555-0142" in t for t in texts)
          and "Margins: 1 inch" in texts, [it["text"] for it in back])
    where = [next((k for k, t in enumerate(texts) if t == g["text"]), None) for g in gone]
    check("each in its place (after the line before it in the document)",
          all(k is not None and texts[k - 1] == b for k, b in zip(where, before)), (where, before))
    check("only once", app._c_complete_once() == 0)
    res = app.compliance_text_check(show=False)
    check("the text check finds nothing missing now", sum(r["missing"] for r in res) == 0)
    n = sum(checks)
    print(f"GUI COMPLETE PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI COMPLETE FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
