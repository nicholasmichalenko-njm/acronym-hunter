"""2.37.0 Submission, phase 1: the customer documents folder shows files not in the history yet; Add reads them,
suggests matches and records versions; a new amendment is matched to its document (strong match, preselected);
the same file twice is skipped; the history shows each version with its fingerprint; Compare lines up the two
versions with removed and added words marked; filters, jumping between changes, exports; Mark reviewed; the rail
status; Export all includes the version history."""
import os, sys, tempfile, shutil, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, docversions as DV
from tkinter import messagebox
from test_docversions import amend
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
CDIR = os.path.join(tmp, "Kestrel", "Customer documents"); os.makedirs(CDIR)
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
for f in os.listdir(RFP):
    shutil.copy2(os.path.join(RFP, f), CDIR)
INBOX = os.path.join(tmp, "inbox"); os.makedirs(INBOX)
AMD = amend(os.path.join(RFP, "Kestrel_RFP_Sections_C_L_M.docx"), os.path.join(INBOX, "Kestrel_RFP_Sections_C_L_M_Amd1.docx"),
            [("exceed 50 pages", "exceed 40 pages"), ("the five highest", "the ten highest")])
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    rail = [app._rail[k][0].cget("text") for k in app._rail]
    check("Submission sits second in the feature list", rail[1].endswith("Submission"), rail[:3])
    app.shell_go("submission"); app.update()
    pills = [w.cget("text").split("  ")[0] for w in app.strip_pills.winfo_children()]
    check("its steps: Documents, Compare, Export", pills == ["1 Documents", "2 Compare", "3 Export"], pills)
    check("files in the customer documents folder not in the history yet show in a banner",
          app.sub_banner.winfo_manager() and "2 customer document" in app.sub_banner_lbl.cget("text"), app.sub_banner_lbl.cget("text"))
    w = app.sub_add_dialog(app.sub_unadded()); w.update()
    plan = w._api["plan"]
    check("each file is read and offered as a new document", len(plan) == 2 and all(e["choice"] == "new" and e["sents"] for e in plan),
          [(os.path.basename(e["path"]), e["choice"]) for e in plan])
    made = w._api["add"](); app.update()
    lib = app.doclib()
    check("added: two documents, each with its Original version", len(made) == 2 and [len(d["versions"]) for d in lib.docs] == [1, 1]
          and all(v["label"] == "Original" for _d, v in made))
    check("the banner goes away", not app.sub_banner.winfo_manager())
    # an amendment arrives
    w = app.sub_add_dialog([AMD]); w.update()
    e = w._api["plan"][0]
    rfp = next(d for d in lib.docs if d["name"] == "Kestrel RFP Sections C L M")
    check("the amendment is matched to its document and preselected", e["choice"] == "version" and e["doc"] == rfp["id"]
          and DV.Library.band(e["best"][1]) == "strong", (e["choice"], e["best"] and e["best"][1:]))
    var, om, ids, names, lab, nm = w._api["rows"][0]
    check("named as the next version", lab.get() == "Amendment 1", lab.get())
    w._api["add"](); app.update()
    check("the amendment is a new version, copied into the customer documents folder",
          len(rfp["versions"]) == 2 and os.path.isfile(os.path.join(CDIR, os.path.basename(AMD))))
    w = app.sub_add_dialog([AMD]); w.update()
    check("the same file twice is skipped (same fingerprint)", w._api["plan"][0].get("dup") is not None)
    w.destroy()
    # the history
    app.sub_show(rfp["id"]); app.update()
    texts = []
    def walk(wd):
        for c in wd.winfo_children():
            try:
                texts.append(c.cget("text"))
            except Exception:
                pass
            walk(c)
    walk(app.sub_detail)
    joined = " | ".join(t for t in texts if isinstance(t, str))
    check("the history shows each version newest first, with its fingerprint and what changed",
          joined.index("Amendment 1") < joined.index("Original") and "Fingerprint (SHA-256)" in joined and "2 changed" in joined
          and "Not reviewed yet" in joined, joined[:300])
    check("the rail says a change waits for review", app.shell_status("submission") == "1 change to review", app.shell_status("submission"))
    # compare
    rows = app.sub_compare(rfp["id"]); app.update()
    check("Compare opens on the last two versions", app.shell_step == "compare" and app.cmp_from.get().startswith("Original")
          and app.cmp_to.get().startswith("Amendment 1"), (app.cmp_from.get(), app.cmp_to.get()))
    check("only the changes are listed, lined up", len(app.cmp_rows) == 2 and all(r["kind"] == "changed" for r in app.cmp_rows), len(app.cmp_rows))
    L_, R_ = app.cmp_panes
    dels = [L_.get(a, b) for a, b in zip(L_.tag_ranges("del")[0::2], L_.tag_ranges("del")[1::2])]
    ins = [R_.get(a, b) for a, b in zip(R_.tag_ranges("ins")[0::2], R_.tag_ranges("ins")[1::2])]
    check("removed words struck through on the left, added words on the right", "50 " in dels and "40 " in ins and "ten " in ins, (dels, ins))
    a0, b0 = L_.tag_ranges("row:1"), R_.tag_ranges("row:1")
    check("both sides line up row by row", L_.index(a0[0]).split(".")[0] == R_.index(b0[0]).split(".")[0])
    check("the page-limit change is marked as a submission requirement", any(r["submission"] for r in app.cmp_rows))
    app.cmp_subonly.set(True); app.cmp_refresh(); app.update()
    check("Only submission requirements narrows the list", len(app.cmp_rows) == 1 and "pages" in app.cmp_rows[0]["new"], len(app.cmp_rows))
    app.cmp_subonly.set(False); app.cmp_only.set(False); app.cmp_refresh(); app.update()
    check("all sentences when Only changes is off", len(app.cmp_rows) > 10)
    i1 = app.cmp_jump(1); i2 = app.cmp_jump(1)
    check("Down jumps from change to change", app.cmp_rows[i1]["kind"] == "changed" and app.cmp_rows[i2]["kind"] == "changed" and i2 > i1, (i1, i2))
    app.cmp_only.set(True); app.cmp_refresh()
    rp = app.cmp_export_redline(os.path.join(tmp, "redline.docx"))
    xp = app.cmp_export_list(os.path.join(tmp, "changes.xlsx"))
    x = zipfile.ZipFile(rp).read("word/document.xml").decode("utf-8")
    check("redline and change list written", "<w:strike/>" in x and os.path.isfile(xp))
    # review and export
    v2 = rfp["versions"][1]
    app.shell_go("submission", "documents"); app.update()
    check("Mark reviewed records who and when", app.sub_mark_reviewed(v2["id"]) and v2["reviewed"]
          and app.shell_status("submission") == "2 documents, 3 versions", app.shell_status("submission"))
    hp = app.sub_export_history(os.path.join(tmp, "history.xlsx"))
    from openpyxl import load_workbook
    wb = load_workbook(hp)
    check("the version history export has the trail and a sheet of changes", wb["Version history"].max_row == 4 and len(wb.worksheets) == 2)
    sub, files, probs = app.export_all(os.path.join(tmp, "out"), ["versions"])
    check("Export all includes the version history", any(f.endswith("_Customer_Document_Versions.xlsx") for f in files) and not probs, files)
    check("saved in the effort folder as it happens", os.path.isfile(os.path.join(app.ws.root, "documents", "index.json"))
          and DV.Library(os.path.join(app.ws.root, "documents")).load().counts()["versions"] == 3)
    print(f"GUI SUBMISSION {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
    app.after(200, app.on_close)


A.set_ai_ml(True)
app.after(900, go)
app.mainloop()
