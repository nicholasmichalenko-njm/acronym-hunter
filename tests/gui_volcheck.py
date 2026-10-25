"""Volume check in the app: Effort > Check volumes on two volumes, report window, jump, exports, add missing, record use."""
import os, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"   # no first-start wizard during tests
import app_gui as A, effort as E
from tkinter import simpledialog, messagebox, filedialog
from tests.test_volcheck import make_docx
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
messagebox.showinfo = lambda *a, **k: None
simpledialog.askstring = lambda *a, **k: "J. Smith"
LIST = os.path.join(tmp, "Kestrel_Effort_List.xlsx")
v1, v2 = os.path.join(tmp, "Vol 2 Management.docx"), os.path.join(tmp, "Vol 10 Cost.docx")
make_docx(v1, ["This Statement of Work (SOW) covers the program.", "The GNX team owns pointing, and the QZR is in month nine."])
make_docx(v2, ["The SOW applies; GNX reports monthly."])
app = A.AcronymAppGUI()
out = {}


def go():
    w = app.new_effort_dialog(); api = w._api
    api["name"].insert(0, "Kestrel"); api["path"].delete(0, "end"); api["path"].insert(0, LIST); api["rule"].set("volume")
    w.update(); api["ok"]()   # let the dialog draw first: closing it in the same instant crashes Tk on Windows
    app.effort.add_or_update("SOW", Type="Acronym", Definition="Statement of Work"); app.effort.set_status(["SOW"], "Approved", "J. Smith")
    app.effort.add_or_update("PDQ", Type="Acronym", Definition="Pretty Darn Quick"); app.effort.set_status(["PDQ"], "Approved", "J. Smith")
    app._save_effort_list()
    pdf = os.path.join(tmp, "Vol 3 Export.pdf"); open(pdf, "wb").write(b"%PDF-1.4 export")
    warned = []
    messagebox.showwarning = lambda *a, **k: warned.append(a[1] if len(a) > 1 else "")
    filedialog.askopenfilenames = lambda **k: (v2, v1, pdf)     # picked out of order: natural sort puts Vol 2 first
    out["warned"] = warned
    app.check_volumes(); app.after(500, wait)


def wait():
    if app.btn_cancel.winfo_ismapped():
        app.after(500, wait); return
    r = app.volume_report
    print("order:", r["volumes"], "| PDF left out with the Word-only note:", bool(out["warned"]) and "PDF" in out["warned"][0])
    import effort_home as H
    out["qa_view"] = app.view_var.get() == H.VIEW_QA
    print("QA/QC view shown:", out["qa_view"])
    print("summary:", r["summary"])
    win = app._volwin
    print("tabs:", list(win._trees))
    tv, data = win._trees["First use"]
    sow = next(i for i, x in data.items() if x["term"] == "SOW" and x["volume"] == "Vol 2 Management.docx")
    tv.focus(sow); app._volume_jump(data[sow]); app.update()
    print("jump selected:", app.tree.selection(), "| preview location:", getattr(app.preview, "locs", [])[:1])
    xl = os.path.join(tmp, "check.xlsx")
    filedialog.asksaveasfilename = lambda **k: xl
    app.export_volume_report()
    filedialog.askdirectory = lambda **k: tmp
    app.export_volume_lists()
    lists = sorted(f for f in os.listdir(tmp) if f.endswith("_Acronym_List.docx"))
    print("excel:", os.path.isfile(xl), "| word lists:", lists)
    app.add_volume_missing()
    app.record_volume_use()
    L = E.EffortList(LIST).load()
    print("list rows:", {t: (r["Status"], r["Used in volumes"]) for t, r in L.rows.items()})
    if os.environ.get("AH_SHOT"):
        win.lift(); win.update(); app.after(300)
        from PIL import ImageGrab
        win.update()
        ImageGrab.grab(bbox=(win.winfo_rootx(), win.winfo_rooty(), win.winfo_rootx() + win.winfo_width(), win.winfo_rooty() + win.winfo_height())).save(os.environ["AH_SHOT"])
    # 2.22.0: the per-section rule adds a Section column to the report
    import volcheck as V
    rs = V.build({t: d for t, d in app.results.items() if not d.get("known")}, app.effort.rows, r["volumes"], "section",
                 file_of=A._file_of)
    app.show_volume_report(rs); app.update()
    stv, _sdata = app._volwin._trees["First use"]
    sec_cols = list(stv["columns"])
    print("section rule columns:", sec_cols[:3], "| rows:", len(rs["first_use"]))
    out["ok"] = out["qa_view"] and bool(out["warned"]) and sec_cols[:4] == ["check", "volume", "section", "term"] and (r["volumes"] == ["Vol 2 Management.docx", "Vol 10 Cost.docx"] and "GNX" in L.rows and L.rows["GNX"]["Status"] == "Proposed"
                 and L.rows["SOW"]["Used in volumes"] == "Vol 2 Management.docx; Vol 10 Cost.docx" and len(lists) == 3
                 and app.tree.selection() == ("SOW",) and r["summary"]["unused"] == 1)
    print("GUI VOLCHECK", "PASS" if out["ok"] else "FAIL")
    app.destroy()


app.after(1500, go); app.mainloop()
