"""Effort List in the app: create an effort, add and approve terms, reject a false alarm, Scan Again, locked-file case."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, effort as E, effort_ui
from tkinter import simpledialog, messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
simpledialog.askstring = lambda *a, **k: "J. Smith; A. Lee"
messagebox.showinfo = lambda *a, **k: None
asked = []
messagebox.askretrycancel = lambda *a, **k: (asked.append(1), False)[1]
app = A.AcronymAppGUI()
LIST = os.path.join(tmp, "Kestrel_Effort_List.xlsx")
files = [os.path.join(A.BASE_DIR, "test_samples", f) for f in ("Kestrel_Technical_Volume.docx", "Kestrel_Compliance_Matrix.xlsx")]
st = {"scan": 0}
def go():
    w = app.new_effort_dialog(); api = w._api
    api["name"].insert(0, "Kestrel"); api["path"].delete(0, "end"); api["path"].insert(0, LIST); api["rule"].set("submission")
    w.update(); api["ok"]()   # let the dialog draw first: closing it in the same instant crashes Tk on Windows
    print("effort open:", app.effort.name, os.path.isfile(LIST), "| label:", app.lbl_effort.cget("text")[:90])
    app.start_batch(files); app.after(500, wait)
def wait():
    if app.btn_cancel.winfo_ismapped():
        app.after(500, wait); return
    st["scan"] += 1
    if st["scan"] == 1:
        app.tree.selection_set("SOW"); app.update()
        print("add button:", app.btn_effort_add.cget("state"), app.btn_effort_add.cget("text"))
        app.entry_def.configure(state="normal"); app.entry_def.insert(0, "Statement of Work"); app.add_to_effort(["SOW"]); app.add_to_effort(["TT&C"])
        app.set_effort_status("Approved", ["SOW"])
        app.set_effort_status("Rejected", ["SCOPE"])
        print("SOW now:", app.results["SOW"]["status"], "|", app.results["SOW"]["selected_definition"][:50])
        print("SCOPE now:", app.results["SCOPE"]["status"], "excluded:", app.results["SCOPE"]["excluded"])
        app.scan_again(); app.after(500, wait)
    elif st["scan"] == 2:
        print("after Scan Again SOW:", app.results["SOW"]["status"], "| SCOPE excluded:", app.results["SCOPE"]["excluded"])
        L = E.EffortList(LIST).load()
        print("file rows:", {t: (r["Status"], r["SS Approver"]) for t, r in L.rows.items()}, "| first use:", L.first_use, "| history:", len(L.history))
        # Excel holds the file: save must fail politely and keep the change pending
        real = os.replace
        def locked(a, b):
            if b == LIST: raise PermissionError(13, "locked")
            return real(a, b)
        os.replace = locked
        app.set_effort_status("Needs author", ["TT&C"])
        print("locked: asked to retry:", bool(asked), "| pending:", app.effort.pending, "| label says NOT SAVED:", "NOT SAVED" in app.lbl_effort.cget("text"))
        os.replace = real
        app.save_effort()
        print("after closing Excel: pending:", app.effort.pending, "| TT&C in file:", E.EffortList(LIST).load().rows["TT&C"]["Status"])
        app.close_effort()
        print("closed: SOW restored to:", app.results["SOW"]["status"][:30], "| SCOPE excluded:", app.results["SCOPE"]["excluded"])
        app.destroy()
app.after(1500, go); app.mainloop()
