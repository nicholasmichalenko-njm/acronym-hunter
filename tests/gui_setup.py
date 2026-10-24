"""2.13.0 Setup tab: accept suggestions, drag from the pool onto a section (and Shift+drag a copy), reorder by drag,
management direction and item notes, typed references and Fill down, reference format, plain export (purple and green,
one file per volume), export changes only, compare, autosave keeps the setup, resume remembers the tab."""
import os, sys, tempfile, zipfile, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, compliance as C, setupdoc as SD
from tkinter import messagebox, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
infos = []
messagebox.showinfo = lambda *a, **k: infos.append(a[1] if len(a) > 1 else "")
messagebox.showwarning = lambda *a, **k: print("WARNING BOX:", a[:2])
messagebox.showerror = lambda *a, **k: print("ERROR BOX:", a[:2])
messagebox.askyesno = lambda *a, **k: True
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
MATRIX = os.path.join(tmp, "Kestrel_Matrix.xlsx")
OUT = os.path.join(tmp, "setup_out"); os.makedirs(OUT)
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


def make_matrix():
    files = sorted(os.listdir(RFP))
    heads = []
    M = C.Matrix(MATRIX, "Kestrel")
    M.items = C.extract([(f, A.typed_chunks(os.path.join(RFP, f))) for f in files], heads)
    M.headings = heads
    M.sources = [[f, "", "2026-10-24", os.path.join(RFP, f)] for f in files]
    M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management\nVolume II Management\n2.1 Schedule\n2.2 Staffing")
    for it in M.items:
        it["decision"] = "Keep" if it["suggest"] != "Drop" else "Drop"
    M.save()


def drag(src, src_iid, dst, dst_iid, shift=False):
    """Real mouse events: press on a row, move, release over another row."""
    src.see(src_iid); dst.see(dst_iid); app.update()
    bx = src.bbox(src_iid); by = dst.bbox(dst_iid)
    x0, y0 = bx[0] + 20, bx[1] + bx[3] // 2
    x1, y1 = by[0] + 40, by[1] + by[3] // 2
    st = 1 if shift else 0
    src.event_generate("<ButtonPress-1>", x=x0, y=y0, rootx=src.winfo_rootx() + x0, rooty=src.winfo_rooty() + y0, state=st)
    src.event_generate("<Motion>", x=x0 + 30, y=y0 + 30, rootx=src.winfo_rootx() + x0 + 30, rooty=src.winfo_rooty() + y0 + 30,
                       state=st | 0x100)                       # 0x100: left button held, so Tk delivers it as B1-Motion
    src.event_generate("<ButtonRelease-1>", x=x0, y=y0, rootx=dst.winfo_rootx() + x1, rooty=dst.winfo_rooty() + y1, state=st | 0x100)
    app.update()


app = A.AcronymAppGUI()
app.geometry("1500x950+0+0")


def go():
    make_matrix()
    app.ws.set("compliance_path", MATRIX)
    cw = app.open_compliance(); cw.geometry("1600x900+0+0"); cw.tabs.set("Setup"); cw.update()
    M = app.matrix
    pool, out = cw.s_pool, cw.s_out
    n0 = len(pool.get_children())
    check("pool lists kept rows", n0 > 5, n0)
    check("outline shows every heading", len(out.get_children()) == len(M.outline), len(out.get_children()))
    app.setup_accept(); cw.update()
    placed = sum(len(v) for v in SD.placed_in(M).values())
    check("Accept suggestions places rows", placed > 0 and len(pool.get_children()) < n0, (placed, len(pool.get_children())))
    first = pool.get_children()[0]
    drag(pool, first, out, "S::2.1 Schedule")
    check("drag from pool onto a section", SD.by_id(M)[first]["map"] == "2.1 Schedule", SD.by_id(M)[first].get("map"))
    drag(out, f"I::2.1 Schedule::{first}", out, "S::2.2 Staffing", shift=True)
    P = SD.placed_in(M)
    check("Shift+drag adds a copy", first in P["2.2 Staffing"] and first in P["2.1 Schedule"], (P["2.1 Schedule"], P["2.2 Staffing"]))
    second = pool.get_children()[0]
    drag(pool, second, out, f"I::2.1 Schedule::{first}")
    o = SD.placed_in(M)["2.1 Schedule"]
    check("drop on a row inserts before it", o.index(second) == o.index(first) - 1, o)
    out.selection_set("S::2.1 Schedule"); app._s_show(); cw.update()
    cw.s_note.insert("1.0", "Use the IMS from the capture plan."); app._s_note_changed()
    check("management direction saved for the section", SD.setup_of(M)["mgmt"].get("2.1 Schedule") == "Use the IMS from the capture plan.")
    out.selection_set(f"I::2.1 Schedule::{second}"); app._s_show(); cw.update()
    cw.s_note.delete("1.0", "end"); cw.s_note.insert("1.0", "We exceed this."); app._s_note_changed()
    cw.s_ref.delete(0, "end"); cw.s_ref.insert(0, "L.9.9"); app.setup_set_ref()
    check("typed reference and item note", SD.ref_of(M, SD.by_id(M)[second]) == ("L.9.9", "Typed") and SD.setup_of(M)["notes"][second] == "We exceed this.")
    out.selection_set(f"I::2.1 Schedule::{second}", f"I::2.1 Schedule::{first}"); app.setup_fill_down()
    check("Fill down copies the first reference", SD.ref_of(M, SD.by_id(M)[first])[0] == "L.9.9")
    w = app.setup_references(); w.update(); w._api["fmt"].set("brackets"); w._api["save"]()
    check("reference format saved", SD.setup_of(M)["ref_format"] == "brackets")
    filedialog.askdirectory = lambda **k: OUT
    paths = app.setup_export()
    xml = zipfile.ZipFile(paths[0]).read("word/document.xml").decode("utf-8") if paths else ""
    check("export: one file per volume", paths and len(paths) == 2, paths)
    texts = [t for p in paths for t, _s, _l in SD.docx_paragraphs(p)]
    check("export: purple RFP text with the reference on the same line", "[L.9.9] " in " ".join(texts)
          and 'w:val="7030A0"' in zipfile.ZipFile(paths[1]).read("word/document.xml").decode("utf-8"))
    check("export: green direction and note", "Use the IMS from the capture plan." in texts and "We exceed this." in texts)
    check("export: every heading", all(C.outline_label(o) in texts for o in M.outline))
    app.setup_remove() if False else None
    out.selection_set(f"I::2.2 Staffing::{first}"); app.setup_remove()
    cp = os.path.join(tmp, "changes.docx")
    filedialog.asksaveasfilename = lambda **k: cp
    app.setup_export_changes()
    ct = [t for t, _s, _l in SD.docx_paragraphs(cp)] if os.path.isfile(cp) else []
    check("export changes only lists the removal", "2.2 Staffing" in ct and any("Removed" in t for t in ct), ct[:6])
    filedialog.askopenfilename = lambda **k: paths[1]
    cwin = app.setup_compare()
    check("compare finds the copy that was removed", any(r[2] == first and r[0] == "2.2 Staffing" and r[1].startswith("Not in the setup")
                                                          for r in cwin._rows), cwin._rows[:4])
    check("compare checks only the volume in the document", not any(r[0].startswith(("Volume I Technical", "1.1")) for r in cwin._rows))
    cwin.destroy()
    app._c_save_now()
    R = C.Matrix(MATRIX).load()
    check("autosave keeps the setup", SD.setup_of(R)["mgmt"].get("2.1 Schedule") and SD.placed_in(R)["2.1 Schedule"] == SD.placed_in(M)["2.1 Schedule"])
    app.save_resume_now()
    check("resume remembers the Setup tab", app.ws.load_resume().get("compliance", {}).get("tab") == "Setup")
    ok = all(checks.values())
    print("GUI SETUP", "PASS" if ok else "FAIL", f"({sum(checks.values())}/{len(checks)})")
    app.on_close()


app.after(1500, go)
app.mainloop()
