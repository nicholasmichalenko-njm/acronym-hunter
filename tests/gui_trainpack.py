"""2.55.0 one training data pack: File > Send training data to the training team... lists each area with what is
waiting; Save stays greyed until the warning is acknowledged; sentence text is in only when ticked; no user or PC
name, no file names, no Customer information; new since the last send by default, everything as an option; Report
misreading leads with what is fixed now; Stationkeeper Training imports the pack and files each area where it belongs;
a changed pack is refused."""
import os, sys, tempfile, json, zipfile, getpass, platform
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, trainpack as TP, rfpoutline as RO
import secure, sensitivity
secure.EFFORT_LEVEL = sensitivity.CUI      # 2.97.0: training lines are kept for an effort at most CUI
import corrections as CR
from tkinter import messagebox
from PIL import Image
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
os.makedirs(A.CONFIG_DIR, exist_ok=True)
for n in ("showinfo", "showwarning"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
CR.set_dir(os.path.join(tmp, "user_td"))
img = Image.new("RGB", (80, 24), "white")
CR.save_sample(img, "RFP", "RFF", 0.5, "Secret_Program_Deck.pptx (Slide 2)", (0, 0, 80, 24))
A.write_ocr_fix_rows([["RFF", "RFP", "Report misreading (preview)"]])
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
M = C.Matrix(os.path.join(EDIR, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("Kestrel_Section_L.docx", [("Page 1", "Technical Approach\nThe Offeror shall describe the thermal design.\n"
                                                              "Thermal margins matter because of long eclipses.\nContact Jane Doe at jane@x.gov.")])])
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal")
M.save()
PACK1, PACK2, PACK3 = (os.path.join(tmp, f"p{i}{TP.EXT}") for i in (1, 2, 3))
app = A.AcronymAppGUI()
app.geometry("1300x860+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel")
    app.ws.set("compliance_path", M.path)
    app.open_compliance(); app._c_load(M.path, quiet=True); app.update()
    items = app.matrix.items
    by = lambda w: next(it for it in items if it["text"].startswith(w))
    app.c_mark_header(by("Technical")["id"], "", "Technical Approach", 1)
    req, sup = by("The Offeror shall describe"), by("Thermal margins")
    C.assign_requirement(items, [req], "1.1 Thermal")
    sup["decision"] = "Context"; sup["context_for"] = req["id"]
    app._c_save_now()
    m = A.tk.Menu(app); app.show_file_menu(m)
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) == "command"] if m.index("end") is not None else []
    check("File menu: Send training data to the training team", "Send training data to the training team..." in labels, labels[-4:])
    w = app.c_fix_text(sup["id"]); app.update()
    check("Fix the text opens with the sentence", "Thermal margins matter" in w._api["box"].get("1.0", "end"))
    w._api["box"].delete("1.0", "end"); w._api["box"].insert("1.0", "Thermal margins matter because of lengthy eclipses.")
    w._api["ok"](); app.update()
    check("the fix applies now and keeps what was read", sup["text"] == "Thermal margins matter because of lengthy eclipses."
          and sup["orig_text"].startswith("Thermal margins matter because of long"))
    app._c_save_now()
    M2 = C.Matrix(M.path).load()
    s2 = next(x for x in M2.items if x["id"] == sup["id"])
    check("both are kept with the matrix", "lengthy" in s2["text"] and "long eclipses" in s2["orig_text"])
    win = app.send_training_data(path=PACK1); app.update()
    api = win._api
    c = api["state"]["counts"]
    check("each area says what is waiting", c["reading"] == 1 and c["ocrfix"] == 2 and c["compliance"] >= 3, c)
    check("Save stays greyed until the warning is acknowledged", api["button"].cget("state") == "disabled" and api["save"]() is None
          and not os.path.isfile(PACK1))
    check("sentence text is off until ticked", api["text"].get() is False and not api["everything"].get())
    api["ack"].set(True); api["refresh"](); app.update()
    check("acknowledged: Save is on", api["button"].cget("state") == "normal")
    r = api["save"](); app.update()
    check("the pack is saved", r and os.path.isfile(PACK1), r)
    z = zipfile.ZipFile(PACK1); names = set(z.namelist())
    man = json.loads(z.read("manifest.json"))
    raw = b"".join(z.read(n) for n in names if n != "reading.zip")
    inner = zipfile.ZipFile(__import__("io").BytesIO(z.read("reading.zip")))
    raw_inner = b"".join(inner.read(n) for n in inner.namelist() if not n.endswith(".png"))
    user = getpass.getuser().encode(); pc = platform.node().encode()
    check("it holds each area", {"reading.zip", "ocr_fixes.csv", "compliance_records.jsonl", "compliance_learned.json",
                                 "compliance_outlines.json"} <= names, names)
    check("no sentence text without the box", b"thermal design" not in raw and b"Technical Approach" not in raw and b"eclipses" not in raw)
    check("no user or PC name, no customer file names, anywhere", user not in raw + raw_inner and (not pc or pc not in raw + raw_inner)
          and b"Kestrel_Section_L" not in raw and b"Secret_Program_Deck" not in raw + raw_inner)
    check("no Customer information", b"jane" not in raw.lower())
    tf = json.loads(z.read("text_fixes.json"))
    check("the text fix goes as word pairs, the sentences only with the text box", tf[0]["pairs"] == [["long", "lengthy"]]
          and "wrong" not in tf[0], tf)
    recs = [json.loads(l) for l in z.read("compliance_records.jsonl").decode().splitlines()]
    rr = next(x for x in recs if x["id"] == req["id"]); rs = next(x for x in recs if x["id"] == sup["id"])
    hd = next(x for x in recs if x["header"])
    check("decisions, support links, headers and levels, placements", rr["decision"] == "Keep" and rr["map_num"] == "1.1"
          and rs["support_for"] == req["id"] and hd["level"] == 1 and hd["section"] == "1", (rr, rs, hd))
    win2 = app.send_training_data(path=PACK2); app.update()
    check("new since the last send: nothing waiting now", sum(win2._api["state"]["counts"].values()) == 0, win2._api["state"]["counts"])
    win2._api["everything"].set(True); win2._api["text"].set(True); win2._api["ack"].set(True); win2._api["refresh"](); app.update()
    r2 = win2._api["save"](); app.update()
    z2 = zipfile.ZipFile(PACK2)
    raw2 = z2.read("compliance_records.jsonl")
    check("Everything and sentence text: the text is in", r2 and b"thermal design" in raw2 and json.loads(z2.read("manifest.json"))["text"])
    app.on_close()


app.after(500, go)
app.mainloop()

# ---- Stationkeeper Training imports it ----
import training_app as T
A.CONFIG_DIR = os.path.join(tmp, "team_config"); os.makedirs(A.CONFIG_DIR, exist_ok=True)
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
CR.set_dir(os.path.join(tmp, "team_td"))
tapp = T.TrainingApp()


def team():
    done, failed = tapp.import_packs([PACK1], ask=False)
    check("Training imports the pack", len(done) == 1 and not failed and "1 misread lines" in done[0] and "2 OCR fixes" in done[0], (done, failed))
    check("the misread line joins the training set", len(tapp.tv.get_children()) == 1)
    import complearn
    check("the compliance learning is merged", complearn.Learner(os.path.join(A.CONFIG_DIR, "compliance_learned.json")).summary()["decisions"] >= 1)
    check("the OCR fix is merged", any(r[0] == "RFF" for r in A.read_ocr_fix_rows()))
    bad = os.path.join(tmp, "bad" + TP.EXT)
    with zipfile.ZipFile(PACK1) as zi, zipfile.ZipFile(bad, "w") as zo:
        for n in zi.namelist():
            b = zi.read(n)
            zo.writestr(n, b + b"x" if n == "ocr_fixes.csv" else b)
    done, failed = tapp.import_packs([bad], ask=False)
    check("a changed pack is refused", failed and not done and "checksum" in failed[0], failed)
    n = sum(checks)
    print(f"GUI TRAINPACK PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI TRAINPACK FAIL ({n}/{len(checks)})")
    tapp.destroy()


tapp.after(1200, team)
tapp.mainloop()
