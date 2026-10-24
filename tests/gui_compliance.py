"""Compliance window: new matrix from the fictional RFP, triage with keys, accept suggestions, split, outline from
Section L headings, typed outline, suggestions, map, Word outline, autosave, reopen."""
import os, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, compliance as C
from tkinter import messagebox, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
said = []
messagebox.showinfo = lambda *a, **k: said.append(a[1] if len(a) > 1 else "")
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
OUT = os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx")
app = A.AcronymAppGUI()
res = {}


def go():
    win = app.open_compliance(); win.update()
    filedialog.askopenfilenames = lambda **k: tuple(os.path.join(RFP, f) for f in sorted(os.listdir(RFP)))
    filedialog.asksaveasfilename = lambda **k: OUT
    app.compliance_new()
    app.after(300, wait)


def wait():
    if app.matrix is None:
        app.after(300, wait); return
    win = app._cwin; tv = win.tv; win.update()
    M = app.matrix
    print("candidates:", len(M.items), "| shown:", len(tv.get_children()), "| saved:", os.path.isfile(OUT), "| said:", said[-1][:60])
    print("outline from L:", [C.outline_label(o) for o in M.outline])
    first = tv.get_children()[0]
    tv.selection_set(first); tv.focus(first); win.focus_force(); tv.focus_set(); win.update()
    tv.event_generate("<KeyPress-k>"); win.update()
    print("K on", first, "->", app._c_item(first)["decision"], "| moved to", tv.selection())
    win.f_sug.set("Drop"); app._c_fill()
    drops = list(tv.get_children())
    win.f_sug.set("All"); app._c_fill()
    app.compliance_accept()
    c = M.counts()
    print("after accept:", {k: c[k] for k in ("Keep", "Drop", "")}, "| drop suggestions:", len(drops))
    icd = next(it for it in M.items if it["text"].startswith("The Contractor shall deliver the Interface"))
    tv.selection_set(icd["id"]); win.update(); app.compliance_split(); win.update()
    parts = [it for it in M.items if it["id"].startswith(icd["id"]) and it["id"] != icd["id"]]
    print("split:", [(p["id"], p["text"][:45]) for p in parts])
    # outline: typed by the user, then suggestions for kept items
    win.o_text.delete("1.0", "end")
    win.o_text.insert("1.0", "Volume I - Technical\n1.1 Thermal Design\n1.2 Risk Management\n1.3 Verification\nVolume II - Management\n2.1 Schedule\n2.2 Past Performance")
    app.compliance_outline_apply(); app.compliance_suggest_all()
    mapped = {it["id"]: it["map"] for it in M.items if it["map"]}
    print("mapped:", len(mapped), "| thermal ->", next(v for k, v in mapped.items() if k.startswith("L.4.1-01")) if any(k.startswith("L.4.1-01") for k in mapped) else None)
    th = next(it for it in M.items if it["id"] == "L.4.1-01")
    tv.selection_set(th["id"]); win.update()
    win.d_map.set("1.1 Thermal Design"); app.compliance_map()
    win.fields["owner"].delete(0, "end"); win.fields["owner"].insert(0, "J. Smith"); app._c_field("owner", "J. Smith")
    p = os.path.join(tmp, "outline.docx"); filedialog.asksaveasfilename = lambda **k: p
    app.compliance_word()
    xml = zipfile.ZipFile(p).read("word/document.xml").decode()
    app._c_save_now()
    N = C.Matrix(OUT).load()
    t2 = next(it for it in N.items if it["id"] == "L.4.1-01")
    print("reopened:", len(N.items), "| thermal:", t2["decision"], t2["map"], t2["owner"], "| outline sections:", len(N.outline))
    res["ok"] = (len(M.items) == 28 and os.path.isfile(OUT) and app._c_item(first)["decision"] == "Keep" and len(parts) == 2
                 and t2["map"] == "1.1 Thermal Design" and t2["owner"] == "J. Smith" and "1.1 Thermal Design" in xml
                 and M.counts()[""] == 3 and len(drops) == 2 and not any(it["map"] == "Volume I - Technical" for it in M.items))
    # 2.10.0: learn, merge, source page, amendment changes
    app.compliance_learn()
    print("learn said:", said[-1][:90].replace("\n", " "))
    learned_ok = "Learned from" in said[-1] and os.path.isfile(os.path.join(A.CONFIG_DIR, "compliance_learned.json"))
    a_ = next(it for it in M.items if it["text"].startswith("(a) identify")); b_ = next(it for it in M.items if it["text"].startswith("(b) describe"))
    tv.selection_set((a_["id"], b_["id"])); win.update(); app.compliance_merge(); win.update()
    merged_ok = not any(it["id"] == b_["id"] for it in M.items) and "(b) describe" in a_["text"]
    poc = next(it for it in M.items if it["text"].startswith("identify a point of contact"))
    tv.selection_set(poc["id"]); win.update()
    before = len(win.winfo_children())
    app.compliance_show_page(); win.update()
    page_ok = any("page 2" in w.title() for w in win.winfo_children() if hasattr(w, "title"))
    for it in M.items:
        if it["text"].startswith("Proposals shall not exceed"):
            it["new"] = "Not in the latest read"
    M.items.append(dict(M.items[0], id="L.1-99", text="Proposals shall not exceed 40 pages, excluding the cover page and table of contents.",
                        new="New in latest read", decision=""))
    cw = app.compliance_changes(); cw.update()
    rows = list(cw._api["rows"].values())
    changes_ok = len(rows) == 1 and rows[0]["kind"] == "Changed" and "{+40+}" in rows[0]["diff"]
    print("learned:", learned_ok, "| merged:", merged_ok, "| page window:", page_ok, "| changes:", changes_ok)
    res["ok"] = res["ok"] and learned_ok and merged_ok and page_ok and changes_ok
    if os.environ.get("AH_SHOT"):
        win.tabs.set("Requirements"); tv.selection_set(th["id"]); tv.see(th["id"]); win.update(); app._c_show(); win.update()
        from PIL import ImageGrab
        ImageGrab.grab(bbox=(win.winfo_rootx(), win.winfo_rooty(), win.winfo_rootx() + win.winfo_width(), win.winfo_rooty() + win.winfo_height())).save(os.environ["AH_SHOT"])
        win.tabs.set("Outline"); win.update(); import time; time.sleep(0.5); win.update()
        ImageGrab.grab(bbox=(win.winfo_rootx(), win.winfo_rooty(), win.winfo_rootx() + win.winfo_width(), win.winfo_rooty() + win.winfo_height())).save(os.environ["AH_SHOT"].replace(".png", "_outline.png"))
    print("GUI COMPLIANCE", "PASS" if res["ok"] else "FAIL")
    app.destroy()


app.after(1500, go); app.mainloop()
