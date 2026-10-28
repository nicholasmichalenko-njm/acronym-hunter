"""2.56.0 the morning's work, end to end, as a person does it: two customer documents (a Word Section L and a PDF
SOW, five pages) read into a new matrix; the response structure typed; Assign in Page view with the mouse and the keys:
requirements into sections (one in two sections), a list taken together by a drag, support for the last requirement
clicked, support for a section, the customer's, not used, a header marked with H; then the matrix and the Response
Setup exported together and checked: every assigned sentence is there, in the right section, support under its
requirement, the sentence in two sections in both. Each step is timed (nothing should feel slow)."""
import os, sys, tempfile, shutil, time, zipfile, subprocess
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, setupdoc as SD, office_pdf as OP, docview as DV
from tkinter import messagebox, filedialog
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
said = []
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, lambda *a, **k: said.append(a[1] if len(a) > 1 else ""))
messagebox.askyesno = lambda *a, **k: True
SHOTS = os.environ.get("AH_SHOTS", "")
checks, slow = [], []
SRC = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk")
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
CDIR = os.path.join(EDIR, "Customer documents"); os.makedirs(CDIR)


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def timed(label, f, *a, limit=1.5):
    t = time.time()
    r = f(*a)
    app.update(); app.update()
    dt = time.time() - t
    if dt > limit:
        slow.append((label, round(dt, 2)))
    return r


def shot(name):
    if SHOTS:
        app.update(); app.update()
        subprocess.run(["import", "-window", "root", os.path.join(SHOTS, name + ".png")])


app = A.AcronymAppGUI()
app.geometry("1500x1000+0+0")
ST = {}


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    app.sub_apply(app.sub_plan([os.path.join(SRC, "Section_L.docx"), os.path.join(SRC, "SOW.pdf")])); app.update()
    win = app.open_compliance(); win.update()
    filedialog.asksaveasfilename = lambda **k: os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx")
    app.compliance_new(paths=[p for _n, _l, p in app.c_effort_docs()])
    app.after(300, wait_read)


def wait_read():
    if app.matrix is None or not app.matrix.items:
        app.after(300, wait_read); return
    win = app._cwin
    M = app.matrix
    check("both documents read into a new matrix", {it["file"] for it in M.items} == {"Section_L.docx", "SOW.pdf"},
          sorted({it["file"] for it in M.items}))
    # the response structure, typed
    app.shell_go("compliance", "outline"); app.update()
    win.o_text.delete("1.0", "end")
    win.o_text.insert("1.0", "Volume I Technical\n1.1 Technical Approach\n1.2 Technical Risk\nVolume II Management\n"
                             "2.1 Schedule\n2.2 Key Personnel\nVolume III Cost\n3.1 Cost Breakdown")
    app.compliance_outline_apply(); app.update()
    # the Office copy of the Word file (on the PC, Word makes it; here LibreOffice stands in)
    src = app._cp_path("Section_L.docx")
    folder = app._pv_copies_dir(); os.makedirs(folder, exist_ok=True)
    if shutil.which("soffice"):
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, src], capture_output=True)
        shutil.copy2(os.path.join(tmp, "Section_L.pdf"), OP.copy_path(src, folder))
    else:                                            # on the build PC: Microsoft Word makes it, as for the team
        OP.make(src, folder)
    timed("open Assign", lambda: (app.shell_go("compliance", "decide"), app.cp_open_file("Section_L.docx")))
    app._pv_draw(); app.update()
    pv = win.pv
    check("Assign opens in Page view on the Word file (its PDF copy)", pv["on"] and pv["pdf"].endswith(".pdf"), pv.get("pdf"))
    shot("01_page_view")
    cv = win.pv_cv

    def box(text):
        it = next(x for x in app.matrix.items if x["file"] == pv["file"] and x["text"].startswith(text))
        n = pv["page_of"].get(it["id"])
        m = app._pv_map(n)
        b = next(x for x in m["items"] if x["id"] == it["id"])
        return it, n, b

    def click(text, shift=False):
        it, n, b = box(text)
        l, t, r, bb = b["rects"][0]
        s = pv["scale"]
        app.pv_follow(it); app._pv_draw(); app.update()
        x, y = 150 + (l + 3) * s, pv["tops"][n - 1] + (t + bb) / 2 * s
        timed("click " + text[:20], app.pv_click, x, y, shift)
        return it

    def key(k):
        cv.focus_set()
        timed("key " + k, lambda: cv.event_generate("<Key>", keysym=k))

    def target(label):
        win.cp_orows[label].invoke(); app.update()
    # 1. a requirement into 1.1, then its support with C
    target("1.1 Technical Approach")
    req = click("The Offeror shall describe its technical approach"); key("r")
    check("R puts the requirement in the target section", req["decision"] == "Keep" and req["map"] == "1.1 Technical Approach")
    sup = click("Thermal margins are of particular interest"); key("c")
    check("C: support for the requirement just made", sup["decision"] == "Context" and sup["context_for"] == req["id"], sup.get("context_for"))
    shot("02_req_and_support")
    # 2. the list: drag across (a) to (d), R
    a = box("thermal control design")
    d = box("integration and test flow")
    s = pv["scale"]
    la, ta = a[2]["rects"][0][:2]; ld = d[2]["rects"][-1]
    ids = timed("drag the list", app.pv_select_box, 150 + la * s - 4, pv["tops"][a[1] - 1] + ta * s - 2,
                150 + ld[2] * s + 4, pv["tops"][d[1] - 1] + ld[3] * s + 2)
    key("r")
    lst = [x for x in app.matrix.items if x["id"] in ids]
    check("a drag selects the list items and R makes them all requirements in 1.1", len(lst) == 4
          and all(x["decision"] == "Keep" and x["map"] == "1.1 Technical Approach" for x in lst), [(x["id"], x["decision"]) for x in lst])
    target("1.1 Technical Approach")                                     # target off
    # 3. risk into 1.2 with the section click while R waits
    rk = click("The Offeror shall identify the top five technical risks"); key("r")
    target("1.2 Technical Risk")
    check("R with no target waits for the section click", rk["decision"] == "Keep" and rk["map"] == "1.2 Technical Risk", rk.get("map"))
    tbl = click("Risks shall be presented in a table"); key("c")
    s_ = pv["scale"]
    check("C after it: support for that requirement", tbl["context_for"] == rk["id"], tbl.get("context_for"))
    # 4. the IMS in two sections
    target("2.1 Schedule")
    ims = click("The Offeror shall provide an Integrated Master Schedule"); key("r")
    target("2.1 Schedule"); target("1.1 Technical Approach")
    click("The Offeror shall provide an Integrated Master Schedule"); key("r")
    target("1.1 Technical Approach")
    check("the IMS is in two sections", SD.item_sections(app.matrix, ims) == ["2.1 Schedule", "1.1 Technical Approach"],
          SD.item_sections(app.matrix, ims))
    # 5. support for a section itself, from the checklist
    fmt = click("Resumes shall not exceed two pages")
    w = timed("open the support checklist", app.cp_support_picker)
    v = w._api["vars"][("sec", "2.2 Key Personnel")][1]
    v.set(True); w._api["toggle"]("sec", "2.2 Key Personnel", v); w.destroy(); app.update()
    check("support for a section (2.2) from the checklist", fmt["decision"] == "Context" and fmt["map"] == "2.2 Key Personnel"
          and not fmt.get("context_for"), (fmt.get("map"), fmt.get("context_for")))
    # 6. the customer's, not used, and a header
    gov = click("The Government intends to evaluate proposals"); key("g")
    check("G: the customer's", gov["decision"] == "Customer")
    el = click("Elaborate brochures"); key("x")
    check("X: not used", el["decision"] == "")
    # Ctrl+Z takes the last assignment back, then the one before
    gov_was = gov["decision"]
    cv.focus_set(); cv.event_generate("<Control-z>"); app.update()
    gv = next(x for x in app.matrix.items if x["id"] == gov["id"])
    cv.focus_set(); cv.event_generate("<Control-z>"); app.update()
    gv2 = next(x for x in app.matrix.items if x["id"] == gov["id"])
    check("Ctrl+Z undoes, step by step", gv["decision"] == "Customer" and gv2["decision"] == "", (gv["decision"], gv2["decision"]))
    click("The Government intends to evaluate proposals"); key("g")
    gov = next(x for x in app.matrix.items if x["id"] == gov["id"])
    shot("03_assigned")
    # 7. the SOW (PDF) the same way
    timed("open the SOW", app.cp_open_file, "SOW.pdf"); app._pv_draw(); app.update()
    check("the SOW opens in Page view", pv["on"] and pv["file"] == "SOW.pdf")
    target("1.1 Technical Approach")
    th = click("The Contractor shall maintain all components"); key("r")
    ec = click("The thermal design shall accommodate eclipse"); key("c")
    target("1.1 Technical Approach")
    check("SOW: requirement and its support", th["decision"] == "Keep" and ec["context_for"] == th["id"], ec.get("context_for"))
    shot("04_sow")
    # 8. export the matrix and the Response Setup together
    out = os.path.join(tmp, "out")
    res = timed("export together", app.compliance_export_together, out, limit=6)
    check("the matrix and the Response Setup are written together", res and len(res["files"]) >= 2, res)
    if os.environ.get("AH_KEEP_OUT") and res:
        os.makedirs(os.environ["AH_KEEP_OUT"], exist_ok=True)
        for p_ in res["files"]:
            shutil.copy2(p_, os.environ["AH_KEEP_OUT"])
    xl = next(p for p in res["files"] if p.endswith(".xlsx"))
    from openpyxl import load_workbook
    ws = load_workbook(xl)["Compliance Matrix"]
    rows = [[("" if c.value is None else str(c.value)) for c in r] for r in ws.iter_rows()]
    hdr = next(i for i, r in enumerate(rows) if "RFP content" in r)
    cols = rows[hdr]
    body = rows[hdr + 1:]
    ci = {h: k for k, h in enumerate(cols)}
    check("the matrix has the default columns", cols[:7] == ["Volume", "Response section no.", "Response section name", "RFP L No.",
                                                             "RFP content", "Author(s)", "Notes"], cols)
    ims_rows = [r for r in body if "Integrated Master Schedule" in r[ci["RFP content"]]]
    check("the IMS: one row per section", sorted(r[ci["Response section no."]] for r in ims_rows) == ["1.1", "2.1"], [r[:5] for r in ims_rows])
    k = next(i for i, r in enumerate(body) if r[ci["RFP content"]].startswith("The Offeror shall describe its technical approach"))
    check("support right under its requirement", "Thermal margins" in body[k + 1][ci["RFP content"]], body[k + 1][:5])
    check("RFP L No. is the RFP's section", body[k][ci["RFP L No."]].startswith("L.3.1"), body[k][ci["RFP L No."]])
    xml = "".join(zipfile.ZipFile(p).read("word/document.xml").decode("utf-8") for p in res["files"] if p.endswith(".docx"))
    import re
    plain = re.sub(r"<[^>]+>", "", xml)
    p11, p12, p21 = plain.find("Technical Approach"), plain.find("Technical Risk"), plain.find("Schedule")
    check("the setup prints the IMS in both sections", plain.count("Integrated Master Schedule (IMS)") >= 2)
    check("the setup has every assigned sentence", all(x in plain for x in ("describe its technical approach", "Thermal margins",
          "top five technical risks", "maintain all components", "Resumes shall not exceed")))
    check("the customer's sentence is not in the setup", "The Government intends to evaluate" not in plain)
    print("SLOW STEPS:", slow)
    check("no step took longer than it should", not slow, slow)
    n = sum(checks)
    print(f"GUI WALKTHROUGH PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI WALKTHROUGH FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
