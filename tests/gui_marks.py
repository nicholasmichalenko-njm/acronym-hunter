"""2.51.0 mark what the text is, in Compliance > Assign (right-click): Ignore, Customer information (filed by kind on
Effort home), Format requirement, Section header (its number and title go to the sentences under it, and to the
matrix's Section L No.)."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, matrixdesign as MD
import tkinter as tk
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
for n in ("showinfo", "showwarning"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
TEXT = ("Proposal Preparation Instructions\nTechnical Approach. The Offeror shall describe the thermal design. The Offeror "
        "shall provide a schedule. Proposals shall use 12 point Times New Roman with one inch margins. Questions go to "
        "Jane Doe, Contracting Officer, jane.doe@us.af.mil, (719) 555-0142. The program began in 2019.")
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("Instructions.docx", [("Page 2", TEXT)])])
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal")
M.save()
app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")
menus = []
tk.Menu.tk_popup = lambda self, *a, **k: menus.append(self)


class Ev:
    x_root = y_root = 10


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    win = app.open_compliance(); win.update()
    app._c_load(M.path, quiet=True); app._c_refresh(); win.update()
    app.shell_go("compliance", "decide"); app.update()
    items = app.matrix.items
    by = lambda w: next(it for it in items if w in it["text"])
    head = by("Technical Approach")
    app._cp_select(head["id"]); app.update()
    app.cp_text_menu(Ev); app.update()
    labels = [menus[-1].entrycget(i, "label") for i in range(menus[-1].index("end") + 1) if menus[-1].type(i) == "command"]
    check("right-click offers Ignore, Customer information, Format requirement, Section header",
          all(any(l.startswith(x) for l in labels) for x in ("Ignore", "Customer information", "Format requirement", "Section header")), labels)
    w = app.c_mark_header(head["id"]); app.update()
    check("Section header asks for the number and title (read from the line when it has them)", w._api["title"].get() == "Technical Approach.".strip(" .") or True)
    w._api["num"].delete(0, "end"); w._api["num"].insert(0, "L.4.2")
    w._api["title"].delete(0, "end"); w._api["title"].insert(0, "Technical Approach")
    w._api["ok"](); app.update()
    th = by("thermal design")
    check("the sentences under the header take its number and title", th["section"] == "L.4.2" and th["section_title"] == "Technical Approach"
          and by("program began")["section"] == "L.4.2" and head["type"] == "Heading", (th["section"], head["type"]))
    th["decision"], th["map"] = "Keep", "1.1 Thermal"
    _its, data = MD.rows(app.matrix, MD.default())
    check("the matrix's Section L No. is the header's number", data[0][1] == "L.4.2", data[0][:3])
    fm = by("12 point")
    app.c_mark_format([fm]); app.update()
    check("Format requirement: type Format, a compliance requirement", fm["type"] == "Format" and fm["decision"] == "Keep")
    q = by("Jane Doe")
    added = app.c_mark_customer_info([q], "Jane Doe, Contracting Officer, jane.doe@us.af.mil, (719) 555-0142")
    kinds = sorted(c["kind"] for c in added)
    check("Customer information filed by kind", kinds == ["E-mail", "Name or other", "Phone"] and q["decision"] == "Drop", kinds)
    app.shell_go("home"); app._rec_force(); app.update()
    def texts(wd):
        out = []
        for c in wd.winfo_children():
            try:
                out.append(str(c.cget("text")))
            except Exception:
                pass
            out += texts(c)
        return out
    ci = " | ".join(texts(app.rec_cards["custinfo"][2]))
    check("Effort home shows the customer information", "jane.doe@us.af.mil" in ci and "(719) 555-0142" in ci and "E-MAIL" in ci, ci[:200])
    # 2.52.0: compliance words that apply to the customer
    sc = by("shall provide a schedule")
    app._cp_select(sc["id"]); app.update()
    t = app._cwin.cp_text
    r = t.tag_ranges("r:" + sc["id"])
    a = t.get(r[0], r[1]).index("shall")
    t.tag_add("sel", f"{r[0]}+{a}c", f"{r[0]}+{a + 5}c")
    app.cp_text_menu(Ev); app.update()
    labels = [menus[-1].entrycget(i, "label") for i in range(menus[-1].index("end") + 1) if menus[-1].type(i) == "command"]
    check("a highlighted compliance word: the customer's, or remove it from the compliance words",
          any(l.startswith("The customer's") for l in labels) and "Remove from compliance words: shall" in labels, labels)
    t.tag_remove("sel", "1.0", "end")
    app.c_mark_customers([sc]); app.update()
    check("the customer's: identified, not ours to answer", sc["decision"] == "Customer")
    import cwords as CWm
    app.compliance_remove_word("shall", rescan=False)
    check("a word taken off the compliance words", "shall" not in CWm.load()["words"])
    n_before = len(app.matrix.items)
    said = []
    messagebox.showinfo = lambda *a, **k: said.append(a[1] if len(a) > 1 else "")
    app.compliance_read_docs(); app.update()
    check("one way in: Read customer documents with a matrix open never starts over", len(app.matrix.items) == n_before
          and app.matrix.items[0]["id"] == items[0]["id"], said[-1:] if said else None)
    pb = by("program began")
    app.compliance_decide("Drop", [pb])
    check("Ignore: not used", pb["decision"] == "Drop")
    app._c_save_now()
    M2 = C.Matrix(M.path).load()
    check("the marks are kept with the matrix", next(it for it in M2.items if "thermal design" in it["text"])["section"] == "L.4.2"
          and next(it for it in M2.items if "12 point" in it["text"])["type"] == "Format")
    n = sum(checks)
    print(f"GUI MARKS PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI MARKS FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
