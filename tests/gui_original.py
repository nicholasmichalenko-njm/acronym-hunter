"""2.45.0 Compliance > Original layout on screen: Original layout (was Show page) opens the PDF page of the selected
sentence with every review sentence boxed; clicking a box selects that sentence in Assign; Assign moving to a sentence
on another page turns the page; a decision recolors its box; text not in the review is boxed in red and one click adds it
to the review; page buttons; a Word-only matrix explains that the view is for PDFs."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, compliance as C, layout as LY, pdfmini
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
said = []
messagebox.showinfo = lambda *a, **k: said.append(a[1] if len(a) > 1 else "")
messagebox.askyesno = lambda *a, **k: True
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
CDIR = os.path.join(tmp, "Kestrel", "Customer documents"); os.makedirs(CDIR)
PDF = pdfmini.write(os.path.join(CDIR, "RFP.pdf"), [
    ["SECTION L - INSTRUCTIONS TO OFFERORS", "L.4 TECHNICAL VOLUME", "The Offeror shall describe its thermal design approach.",
     "The Offeror shall provide a risk register as Attachment J-3.", "The Offeror should keep the volume under 30 pages."],
    ["L.5 MANAGEMENT VOLUME", "The Offeror shall provide an Integrated Master Schedule.", "The Offeror shall name a program manager."]])
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    heads = []
    mpath = os.path.join(tmp, "Kestrel", "Kestrel_Matrix.xlsx")
    M = C.Matrix(mpath, "Kestrel")
    M.items = C.extract([("RFP.pdf", A.typed_chunks(PDF))], heads)
    M.headings = heads
    M.sources = [["RFP.pdf", "", "2026-10-27", PDF]]
    M.items = [it for it in M.items if "risk register" not in it["text"]]       # one line never reached the review
    M.save()
    app.ws.set("compliance_path", mpath)
    app.open_compliance(show=False); app.update()
    app._c_load(mpath, quiet=True); app._c_refresh()
    app.shell_go("compliance", "decide"); app.update()
    first = app.matrix.items[0]
    app._cp_select(first["id"]); app.update()
    w = app.compliance_show_page(); app.update()
    for _ in range(5):
        app.update(); w.update()
    check("Original layout opens the selected sentence's PDF page", w is not None and w._file == "RFP.pdf" and w._page == 1
          and w._sel == first["id"] and w._base is not None, (getattr(w, "_file", None), getattr(w, "_page", None)))
    m = w._map
    on1 = [it["id"] for it in app.matrix.items if LY._page_of(it) == 1]
    check("every review sentence on the page is boxed", [x["id"] for x in m["items"]] == on1, ([x["id"] for x in m["items"]], on1))
    check("the line not in the review is boxed in red, and the window says so",
          [x["text"] for x in m["missing"]] == ["The Offeror shall provide a risk register as Attachment J-3"]
          and "1 line(s) of text not in the review" in w._info.cget("text"), w._info.cget("text"))
    # click the second sentence's box: Assign selects it
    second = m["items"][1]
    l, t, r, b = second["rects"][0]
    h = app.layout_pick((l + r) / 2, (t + b) / 2); app.update()
    sel = app._c_selected()
    check("clicking a box selects that sentence in Assign", h == ("item", second["id"]) and sel and sel[0]["id"] == second["id"]
          and app.shell_step == "decide", (h, sel and sel[0]["id"]))
    # a decision recolors its box
    app.compliance_decide("Keep"); app.update()
    app.layout_show("RFP.pdf", 1); app.update()      # Assign moved on to the next sentence (page 2); look back at page 1
    crop = w._img.crop((int(l * w._scale) - 3, int(t * w._scale) - 3, int(r * w._scale) + 3, int(b * w._scale) + 3))
    px = [sum(c) for c in zip(*crop.getdata())]
    check("a decision recolors the box (green for a compliance requirement)", px[1] > px[0] and px[1] > px[2], (px, app._c_selected()[0]["id"], w._sel))
    # Assign moves to a sentence on page 2: the layout follows
    p2 = next(it for it in app.matrix.items if LY._page_of(it) == 2)
    app._cp_select(p2["id"]); app.update()
    check("Assign moving to a sentence on page 2 turns the page", w._page == 2 and w._sel == p2["id"], (w._page, w._sel))
    app.layout_step(-1); app.update()
    check("the page buttons go back to page 1", w._page == 1 and w._pl.cget("text") == "Page 1 of 2", w._pl.cget("text"))
    # add the red line to the review
    n0 = len(app.matrix.items)
    ml, mt, mr, mb = w._map["missing"][0]["rects"][0]
    app.layout_pick((ml + mr) / 2, (mt + mb) / 2); app.update()
    added = [it for it in app.matrix.items if "risk register" in it["text"]]
    check("a click on the red line adds it to the review, on its page, and the page has no red left",
          len(app.matrix.items) == n0 + 1 and added and LY._page_of(added[0]) == 1 and not w._map["missing"]
          and w._sel == added[0]["id"], (len(app.matrix.items), added and added[0].get("loc"), w._map["missing"], w._sel, added and added[0]["id"], added and added[0].get("page")))
    w.destroy(); app._lay = None; app.update()
    # a matrix with no PDF: the view explains itself
    for it in app.matrix.items:
        it["file"] = "RFP.docx"
    said.clear()
    check("with no PDF file the view says it is for PDFs", app.compliance_layout() is None and any("PDF" in s for s in said), said)
    n = sum(checks)
    print(f"GUI ORIGINAL PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI ORIGINAL FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
