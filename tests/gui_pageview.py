"""2.56.0 Assign on the real page: Page view shows the PDF as it looks with every sentence boxed; a click selects a
sentence; a drag selects several; the keys assign as usual and the box recolors; REQ labels sit in the margin; a click
on a word of the selected sentence is where S splits it; Text view is one click away; a Word file shows through its PDF
copy (made by Office on the PC; here the copy is given), and without one the text view says why.
2.57.0: the sentences sit on the page's own words; the header and footer are not boxes, not red and not clickable;
Ctrl+click selects sentences that are not next to each other (Page view and Text view) and M combines them."""
import os, sys, tempfile, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import hangguard
hangguard.arm('GUI PAGEVIEW')
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, setupdoc as SD, office_pdf as OP
OP.available = lambda: False          # this test gives the copy itself; Office is not started (gui_walkthrough uses it)
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
for n in ("showinfo", "showwarning"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
checks = []
SRC = os.path.join(A.BASE_DIR, "test_samples", "rfp_hard")


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
PDF, DOCX = os.path.join(SRC, "Hard_RFP.pdf"), os.path.join(SRC, "Hard_RFP.docx")
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([(os.path.basename(p), A.rfp_chunks(p)) for p in (PDF, DOCX)])
M.sources = [[os.path.basename(p), "", "", p] for p in (PDF, DOCX)]
M.outline = C.parse_outline("1.1 Volumes\n1.2 Technical")
SD.setup_of(M)["complete_v"] = 1
M.save()
app = A.AcronymAppGUI()
app.geometry("1500x1000+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    app.open_compliance(); app._c_load(M.path, quiet=True); app.update()
    app.shell_go("compliance", "decide"); app.update()
    win = app._cwin
    app.cp_open_file("Hard_RFP.pdf"); app.update(); app.update()
    for _ in range(5):
        app.update(); win.update()
    pv = win.pv
    app._pv_draw(); app.update()
    check("Page view is on for a PDF, the page canvas shown", pv["on"] and win.pv_frame.winfo_manager() and not win.cp_text.winfo_manager())
    m = app._pv_map(1)
    check("every sentence on page 1 is boxed", len(m["items"]) >= 15, len(m["items"]))
    items = app.matrix.items
    by = lambda w: next(it for it in items if it["file"] == "Hard_RFP.pdf" and it["text"].startswith(w))
    tgt = by("The technical volume shall not")
    box = next(x for x in m["items"] if x["id"] == tgt["id"])
    s = pv["scale"]
    l, t, r, b = box["rects"][0]
    cx, cy = A_x = 150 + (l + r) / 2 * s, pv["tops"][0] + (t + b) / 2 * s
    h = app.pv_click(150 + (l + 2) * s, pv["tops"][0] + (t + b) / 2 * s); app.update()
    check("a click selects the sentence", h == ("item", tgt["id"]) and app._c_selected()[0]["id"] == tgt["id"], h)
    a1, a2 = by("The Offeror shall submit"), by("Each volume shall")
    b1 = next(x for x in m["items"] if x["id"] == a1["id"])["rects"][0]
    b2 = next(x for x in m["items"] if x["id"] == a2["id"])["rects"][-1]
    ids = app.pv_select_box(150 + b1[0] * s + 2, pv["tops"][0] + b1[1] * s + 2, 150 + b2[2] * s - 2, pv["tops"][0] + b2[3] * s - 2)
    check("a drag selects several sentences together", a1["id"] in ids and a2["id"] in ids and set(win.cp_range) >= {a1["id"], a2["id"]}, ids)
    app.cp_section_click("1.1 Volumes"); app.cp_req(); app.update(); app.cp_section_click("1.1 Volumes")
    check("R assigns them all", a1["decision"] == "Keep" and a2["decision"] == "Keep" and a1["map"] == "1.1 Volumes")
    app._pv_draw(); app.update()
    labels = [win.pv_cv.itemcget(i, "text") for i in win.pv_cv.find_all() if win.pv_cv.type(i) == "text"]
    check("REQ labels in the margin", any(x.startswith("REQ " + a1["id"]) for x in labels), [x for x in labels if x.startswith("REQ")][:3])
    app.pv_click(150 + (l + 2) * s, pv["tops"][0] + (t + b) / 2 * s); app.update()
    words = box["words"]
    k = 3                                                     # "The technical volume | shall ..."
    wl, wt, wr, wb = words[k]
    hit = app.pv_click(150 + (wl + wr) / 2 * s, pv["tops"][0] + (wt + wb) / 2 * s); app.update()
    app.compliance_split(); app.update()
    parts = [x["text"] for x in app.matrix.items if x["file"] == "Hard_RFP.pdf" and x["id"].startswith(tgt["id"])]
    check("a click on a word of the selected sentence: S splits it there", parts == ["The technical volume", "shall not exceed 50 pages."], (hit, parts))
    s0 = pv["scale"]
    app.pv_zoom(1.15); app._pv_draw(); app.update()
    s1 = pv["scale"]
    app.pv_zoom(None); app._pv_draw(); app.update()
    check("zoom in makes the pages bigger; Ctrl+0 fits the width again", s1 > s0 * 1.1 and abs(pv["scale"] - s0) < 0.02, (s0, s1, pv["scale"]))
    win.pv_switch.set("Text view"); app._pv_switch("Text view"); app.update()
    check("Text view is one click away", not pv["on"] and win.cp_text.winfo_manager())
    win.pv_switch.set("Page view"); app._pv_switch("Page view"); app.update()
    check("and back to Page view", pv["on"])
    # 2.57.0: sentences placed on the page's own words; headers and footers are furniture
    app._pv_draw(); app.update()
    m = app._pv_map(1)
    check("2.57.0: the sentences are placed on the page's words", pv.get("mode") == "page", pv.get("mode"))
    check("the header and footer are furniture: no box, not red", len(m.get("furniture", [])) == 2
          and not any("FA8811" in x["text"] or "CUI" in x["text"] for x in m["missing"]), (m.get("furniture"), m["missing"]))
    fl, ft, fr, fb = m["furniture"][0]
    before = app._c_selected()[0]["id"]
    h = app.pv_click(150 + (fl + fr) / 2 * pv["scale"], pv["tops"][0] + (ft + fb) / 2 * pv["scale"]); app.update()
    check("a click on the header selects nothing", h is None and app._c_selected()[0]["id"] == before, h)
    s = pv["scale"]
    rows = [it for it in app.matrix.items if it["file"] == "Hard_RFP.pdf" and it["decision"] != "Keep"]
    c1, c2 = rows[1], rows[5]
    def center(iid):
        x = next(x for x in app._pv_map(1)["items"] if x["id"] == iid)["rects"][0]
        return 150 + (x[0] + 2) * s, pv["tops"][0] + (x[1] + x[3]) / 2 * s
    app.cp_set_range([]); app.pv_click(*center(c1["id"])); app.update()
    h = app.pv_click(*center(c2["id"]), shift=True); app.update()
    check("Ctrl+click adds a sentence far from the first", h and h[0] == "range" and win.cp_range == [c1["id"], c2["id"]], (h, win.cp_range))
    t1, t2 = c1["text"], c2["text"]
    mid = app.cp_combine(); app.update()
    mi = app._c_item(mid)
    check("M combines them into one, each part keeping its place", mi is not None and mi["text"] == t1 + " " + t2
          and mi.get("place", "").count(";") >= 1, (mid, mi and mi.get("place")))
    app._pv_refresh(force=True); app._pv_draw(); app.update()
    xm = next((x for x in app._pv_map(1)["items"] if x["id"] == mid), None)
    check("the combined sentence is boxed in both places", xm is not None and len(xm["rects"]) >= 2, xm and len(xm["rects"]))
    win.pv_switch.set("Text view"); app._pv_switch("Text view"); app.update()
    t = win.cp_text
    rows = [it for it in app.matrix.items if it["file"] == "Hard_RFP.pdf" and t.tag_ranges("r:" + it["id"])]
    d1, d2 = rows[2], rows[6]
    app.cp_set_range([]); app._cp_select(d1["id"]); app.update()
    t.see(t.tag_ranges("r:" + d2["id"])[0]); app.update()
    bx = t.bbox(t.tag_ranges("r:" + d2["id"])[0])
    import types
    app._cp_click(types.SimpleNamespace(x=bx[0] + 2, y=bx[1] + 2, state=0x0004)); app.update()
    check("Text view: Ctrl+click adds a sentence that is not next to the selected one", win.cp_range == [d1["id"], d2["id"]], win.cp_range)
    app._cp_click(types.SimpleNamespace(x=bx[0] + 2, y=bx[1] + 2, state=0x0004)); app.update()
    check("and Ctrl+click again takes it out", not win.cp_range and app._c_selected()[0]["id"] == d1["id"], win.cp_range)
    app.cp_set_range([])
    win.pv_switch.set("Page view"); app._pv_switch("Page view"); app.update()
    app.cp_open_file("Hard_RFP.docx"); app.update(); app.update()
    for _ in range(30):
        app.update()
        if "copy" in win.pv_note.cget("text") or "Office" in win.pv_note.cget("text") or pv["on"]:
            break
    check("a Word file with no PDF copy (no Office here): the text view says why", not pv["on"]
          and ("PDF copy" in win.pv_note.cget("text") or "Office" in win.pv_note.cget("text")), win.pv_note.cget("text"))
    folder = app._pv_copies_dir()
    os.makedirs(folder, exist_ok=True)
    shutil.copy2(PDF, OP.copy_path(DOCX, folder))            # the copy Office makes on the PC
    pv["err"] = {}
    app._pv_refresh(force=True); app.update()
    for _ in range(5):
        app.update()
    check("a Word file shows through its PDF copy", pv["on"] and pv["pdf"].endswith(".pdf") and len(app._pv_map(1)["items"]) >= 10,
          (pv["on"], pv["pdf"]))
    n = sum(checks)
    print(f"GUI PAGEVIEW PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI PAGEVIEW FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
