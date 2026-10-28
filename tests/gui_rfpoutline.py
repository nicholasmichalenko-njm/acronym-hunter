"""2.54.0 the RFP's own sections and subsections: suggested headers (HEADER? to confirm), H marks a header with its
level, numbered by order when the RFP has no numbers; the sentences under it take its number; the RFP outline panel
lists the sections with what each holds; an RFP section maps to a proposal section (first suggestion); the response
structure can start from the RFP outline; a header can be taken back; a band shows the section's extent."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, rfpoutline as RO, matrixdesign as MD
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
LINES = ["Proposal Instructions", "The Offeror shall submit three volumes.", "Technical Approach",
         "The Offeror shall describe the thermal design.", "Thermal margins matter because of long eclipses.",
         "Test Program", "The Offeror shall provide a test plan.", "Management Approach", "The Offeror shall provide a schedule."]
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("Instructions.docx", [("Page 1", "\n".join(LINES))])])
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal\n1.2 Testing\nVolume II Management\n2.1 Schedule")
M.save()
app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    win = app.open_compliance(); win.update()
    app._c_load(M.path, quiet=True); app._c_refresh(); win.update()
    app.shell_go("compliance", "decide"); app.update()
    items = app.matrix.items
    by = lambda w: next(it for it in items if it["text"].startswith(w))
    tech, test, mgmt = by("Technical Approach"), by("Test Program"), by("Management Approach")
    cand = RO.candidates(app.matrix)
    check("unnumbered title lines are suggested as headers", tech["id"] in cand and test["id"] in cand and mgmt["id"] in cand
          and by("The Offeror shall describe")["id"] not in cand, [x for x in cand])
    whole = app._cwin.cp_text.get("1.0", "end").replace(" ", " ")
    check("2.56.0: no suggested headers in the text (H marks one)", "HEADER?" not in whole)
    app._cp_select(tech["id"]); app.update()
    w = app.c_mark_header(tech["id"]); app.update()
    check("H: a header the RFP did not number is numbered by its order", w._api["num"].get() == "1" or w._api["num"].get().isdigit(),
          w._api["num"].get())
    first = by("Proposal Instructions")
    app.c_mark_header(first["id"], "", "Proposal Instructions", 1); app.update()
    w = app.c_mark_header(tech["id"]); app.update()
    num_tech = w._api["num"].get()
    w._api["ok"](); app.update()
    check("the next Section is 2", num_tech == "2" and tech["section"] == "2", (num_tech, tech["section"]))
    w = app.c_mark_header(test["id"]); app.update()
    w._api["level"].set("Subsection"); w._api["level"].cget("command")("Subsection"); app.update()
    num_test = w._api["num"].get()
    w._api["ok"](); app.update()
    check("a Subsection under it is 2.1", num_test == "2.1", num_test)
    app.c_mark_header(mgmt["id"], "", "Management Approach", 1); app.update()
    check("the sentences under each header take its number and title", by("The Offeror shall describe")["section"] == "2"
          and by("The Offeror shall provide a test")["section"] == "2.1" and by("The Offeror shall provide a schedule")["section"] == "3"
          and by("The Offeror shall describe")["section_title"] == "Technical Approach")
    hs = RO.headers(app.matrix)
    check("the RFP outline: every header in order, with its level", [(h["num"], h["title"], h["level"]) for h in hs]
          == [("1", "Proposal Instructions", 1), ("2", "Technical Approach", 1), ("2.1", "Test Program", 2), ("3", "Management Approach", 1)],
          [(h["num"], h["title"], h["level"]) for h in hs])
    whole = app._cwin.cp_text.get("1.0", "end").replace(" ", " ")
    check("headers show their number in the text (§ 2, §§ 2.1)", "§ 2 " in whole and "§§ 2.1 " in whole, whole[:200])
    req = by("The Offeror shall describe")
    C.assign_requirement(items, [req], "1.1 Thermal"); app._c_changed(); app.update()
    panel = []
    def texts(w):
        out = []
        for c in w.winfo_children():
            try:
                out.append(str(c.cget("text")))
            except Exception:
                pass
            out += texts(c)
        return out
    app._cwin.cp_rfp_sig = None; app._cp_side(); app.update()
    panel = " | ".join(texts(app._cwin.cp_rfp))
    check("the RFP outline panel lists the sections and what each holds", "2  Technical Approach   1 req" in panel and "2.1  Test Program" in panel, panel[:300])
    app.cp_rfp_map("2.1", "1.2 Testing"); app.update()
    tp = by("The Offeror shall provide a test")
    check("an RFP section mapped to a proposal section: its sentences get it first", app._cp_suggestions(tp)[:1] == ["1.2 Testing"]
          and "-> 1.2 Testing" in " | ".join(texts(app._cwin.cp_rfp)))
    app._cp_select(req["id"]); app.update()
    band = app._cp_band(app._cwin.cp_gut, app._cwin.cp_text, req, max(1, app._cwin.cp_gut.winfo_height()))
    check("a band shows the extent of the section the sentence is in", band is not None and band[1] > band[0], band)
    out = app.compliance_outline_from_rfp_outline(); app.update()
    check("the response structure can start from the RFP outline", out and "2.1 Test Program" in app._cwin.o_text.get("1.0", "end"))
    app.c_unmark_header(test["id"]); app.update()
    check("Not a section header: its sentences go back under the header above it", tp["section"] == "2" and test["type"] != "Heading")
    app._c_save_now()
    M2 = C.Matrix(M.path).load()
    check("headers, levels and mappings are kept with the matrix", RO.headers(M2)[1]["num"] == "2" and RO.mapped(M2, "2.1") == "1.2 Testing",
          (app.matrix.path == M.path, [(h["num"], h["title"]) for h in RO.headers(M2)], getattr(M2, "setup", {}).get("rfp_map")))
    n = sum(checks)
    print(f"GUI RFPOUTLINE PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI RFPOUTLINE FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
