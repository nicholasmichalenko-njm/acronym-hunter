"""2.55.0 Assign shows the document itself: every word of the customer document is on the page, in the document's order
(Word and PDF), with the review sentences laid over it; a list lead-in and a heading no sentence uses are there; a
sentence the reader left out goes into the review in its place; a sentence whose words differ from the document shows
the document's words with the differences marked; a sentence found nowhere is still shown; splitting by a click still
cuts the sentence at the word clicked."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, docview as DV, textcheck as T
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
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
files = [os.path.join(SRC, "Hard_RFP.docx"), os.path.join(SRC, "Hard_RFP.pdf")]
M.items = C.extract([(os.path.basename(p), A.rfp_chunks(p)) for p in files])
M.sources = [[os.path.basename(p), "", "", p] for p in files]
lost_text = next(it["text"] for it in M.items if it["file"] == "Hard_RFP.docx" and it["text"].startswith("The Program Manager"))
M.items = [it for it in M.items if not (it["file"] == "Hard_RFP.docx" and it["text"] == lost_text)]   # the reader "missed" it
bad = next(it for it in M.items if it["file"] == "Hard_RFP.pdf" and it["text"].startswith("Each volume shall"))
bad["text"] = "Each shall volume be bound"                                                            # words out of order
import setupdoc as SD
SD.setup_of(M)["complete_v"] = 1          # the once-on-open text check would add the line itself; the page must do it
M.save()
app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")


def page_words():
    t = app._cwin.cp_text
    out, i = [], "1.0"
    for tag in ("badge", "where", "lostlab"):
        pass
    txt = []
    idx = "1.0"
    while app._cwin.cp_text.compare(idx, "<", "end"):
        nxt = t.index(f"{idx} lineend")
        line_tags_text = []
        txt.append(t.get(idx, nxt))
        idx = t.index(f"{nxt} +1c")
    whole = "\n".join(txt)
    for tg in ("badge", "where", "lostlab"):          # labels the page adds are not document text
        r = t.tag_ranges(tg)
        for k in range(0, len(r), 2):
            seg = t.get(r[k], r[k + 1])
            whole = whole.replace(seg, " ", 1)
    return [w.lower() for w in DV.WORD.findall(whole)]


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    app.open_compliance(); app._c_load(M.path, quiet=True); app.update()
    app.shell_go("compliance", "decide"); app.update()
    for f in ("Hard_RFP.docx", "Hard_RFP.pdf"):
        app.cp_open_file(f); app.update(); app.update()
        win = app._cwin
        check(f"{f}: the page is the document itself", getattr(win, "cp_doc", False))
        doc = [w for _l, line in DV.doc_lines(os.path.join(SRC, f)) for w in [x.lower() for x in DV.WORD.findall(line)]]
        got = page_words()
        sm = __import__("difflib").SequenceMatcher(None, doc, got, autojunk=False)
        same = sum(b.size for b in sm.get_matching_blocks())
        check(f"{f}: every word of the document is on the page, in order", same == len(doc), (same, len(doc)))
        text = win.cp_text.get("1.0", "end")
        check(f"{f}: the list lead-in is there", "The Offeror shall address the following:" in text)
        check(f"{f}: a heading no sentence uses is there", "SECTION L - INSTRUCTIONS, CONDITIONS, AND NOTICES TO OFFERORS" in text)
    items = app.matrix.items
    back = [it for it in items if it["file"] == "Hard_RFP.docx" and it["text"].startswith("The Program Manager")]
    check("a sentence the reader left out is put in the review", len(back) == 1 and back[0].get("new") == "Added by the text check",
          [it["text"][:40] for it in back])
    docx_items = [it["text"] for it in items if it["file"] == "Hard_RFP.docx"]
    k = docx_items.index(back[0]["text"]) if back else -1
    check("in its place: after the sentence before it in the document", k > 0 and docx_items[k - 1].startswith("Key Personnel"),
          docx_items[k - 1:k + 2] if k > 0 else None)
    app.cp_open_file("Hard_RFP.pdf"); app.update(); app.update()
    win = app._cwin
    t = win.cp_text
    r = t.tag_ranges("r:" + bad["id"])
    shown = t.get(r[0], r[1]) if r else ""
    check("a sentence with words out of order shows the document's words", "Each volume shall be separately bound" in " ".join(shown.split()), shown)
    gaps = t.tag_ranges("gap")
    check("the differences are marked", bool(gaps) and "differ from the document" in win.cp_src.cget("text"), win.cp_src.cget("text")[-90:])
    it = next(x for x in app.matrix.items if x["file"] == "Hard_RFP.pdf" and x["text"].startswith("The technical volume shall not"))
    app._cp_select(it["id"]); app.update()
    r = t.tag_ranges("r:" + it["id"])
    seg = t.get(r[0], r[1])
    k = seg.index("shall")
    t.update_idletasks()
    t.see(f"{r[0]} +{k}c")
    bb = t.bbox(f"{r[0]} +{k}c")
    ev = type("E", (), {"x": bb[0] + 1, "y": bb[1] + 2})()
    app._cp_click(ev)
    app.compliance_split(); app.update()
    parts = [x["text"] for x in app.matrix.items if x["file"] == "Hard_RFP.pdf" and x["id"].startswith(it["id"])]
    check("a click splits the sentence at the word clicked", parts == ["The technical volume", "shall not exceed 50 pages."], parts)
    n = sum(checks)
    print(f"GUI DOCVIEW PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI DOCVIEW FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
