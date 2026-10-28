"""2.52.0 carry an effort to a new PC or a new version: save the effort package, take the original folder away, import
the package into another folder, and continue exactly where it was: the record (team, tasks, customer information,
stage dates), the customer documents and their versions, the compliance matrix with every decision, mark, design and
its RFP files (repointed, so the text check and Read customer documents still work). Save all efforts writes one
package per effort and is greyed out with one effort."""
import os, sys, tempfile, shutil, zipfile, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"; os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, effort as E, matrixdesign as MD, office_pdf as OP
OP.available = lambda: False          # not a Page view test: Office must not convert files in a folder this test moves away
from tkinter import messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


SRC = os.path.join(os.path.dirname(HERE), "test_samples", "rfp_stress", "Stress_RFP.docx")
ORIG = os.path.join(tmp, "PC1", "Kestrel")
LIST = os.path.join(ORIG, "Kestrel_Effort_List.xlsx")
app = A.AcronymAppGUI()


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    cdir = os.path.join(ORIG, "Customer documents"); os.makedirs(cdir)
    app.efforts.put("Kestrel", path=LIST, customer_dir=cdir)
    app.open_effort("Kestrel"); app.update()
    app.sub_apply(app.sub_plan([SRC])); app.update()
    r = app.effrec()
    r.set_team([("J. Smith", "Volume lead"), ("K. Park", "Author")])
    r.add_customer_info("Jane Doe, jane.doe@us.af.mil")
    tid = r.add_task("Draft 1.1", owner="K. Park", due="2026-11-20")
    rows = [(s["id"], s["name"], s["planned"], s.get("planned_end", "")) for s in r.stages]
    rows[0] = (rows[0][0], rows[0][1], "2026-10-20", "2026-11-03")
    r.edit_stages(rows)
    win = app.open_compliance(); win.update()
    from tkinter import filedialog
    filedialog.asksaveasfilename = lambda **k: os.path.join(ORIG, "Kestrel_Compliance_Matrix.xlsx")
    app.compliance_new(paths=[p for _n, _l, p in app.c_effort_docs()])
    app.after(300, wait_read)


def wait_read():
    if app.matrix is None or not app.matrix.items:
        app.after(300, wait_read); return
    M = app.matrix
    keep = next(it for it in M.items if "thermal design" in it["text"])
    ctx = next(it for it in M.items if "Margins" in it["text"])
    keep["decision"] = "Keep"; ctx["decision"] = "Context"; ctx["context_for"] = keep["id"]
    M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal")
    keep["map"] = "1.1 Thermal"
    MD.set_matrix(M, dict(MD.default(), columns=MD.default()["columns"] + [{"key": "custom:Reviewer"}]))
    app._c_save_now()
    want = {it["id"]: (it["decision"], it.get("map", ""), it.get("context_for", "")) for it in M.items}
    pkg = os.path.join(tmp, "Kestrel_package.skpkg")
    man = app.pkg_save_dialog(path=pkg)
    check("the package is saved, with the matrix and the customer files", man and man["has"]["matrix"] and man["has"]["customer"])
    fl = app.menubar.nametowidget(app.menubar.entrycget(0, "menu")); app.show_file_menu(fl)
    st = next(fl.entrycget(i, "state") for i in range(fl.index("end") + 1) if fl.type(i) == "command" and fl.entrycget(i, "label").startswith("Save all efforts"))
    check("Save all efforts is greyed out with one effort", st == "disabled")
    # a new PC: the original folder is gone, the package is imported somewhere else
    app.leave_workspace() if hasattr(app, "leave_workspace") else None
    app.matrix = None
    if app._cwin is not None:
        try:
            app._cwin.destroy()
        except Exception:
            pass
        app._cwin = None
    shutil.move(os.path.join(tmp, "PC1"), os.path.join(tmp, "PC1 gone"))
    got = app.pkg_import_dialog(pkg, dest=os.path.join(tmp, "PC2"), mode="replace"); app.update()
    check("imported and opened", got is not None and app.effort is not None and app.effort.name == "Kestrel")
    r2 = app.effrec()
    check("the record carries on: team, customer information, tasks, stage dates", [m["name"] for m in r2.team()] == ["J. Smith", "K. Park"]
          and r2.customer_info() and any(t["title"] == "Draft 1.1" for t in r2.tasks()) and r2.stages[0].get("planned_end") == "2026-11-03")
    docs = app.c_effort_docs()
    check("the customer documents and versions are there, at the new place", docs and all(os.path.isfile(p) and "PC2" in p for _n, _l, p in docs), docs)
    win = app.open_compliance(); win.update()
    M2 = app.matrix
    check("the compliance matrix with every decision, link and section", M2 is not None and
          {it["id"]: (it["decision"], it.get("map", ""), it.get("context_for", "")) for it in M2.items if it["id"] in want} == want)
    check("its design came along", MD.of_matrix(M2) and MD.of_matrix(M2)["columns"][-1]["key"] == "custom:Reviewer")
    check("its RFP files point at the new place", all(os.path.isfile(src[3]) and "PC2" in src[3] for src in M2.sources), [s[3] for s in M2.sources])
    res = app.compliance_text_check(show=False)
    check("the text check works after the move (nothing missing, nothing gone)", res and not any(r.get("gone") for r in res)
          and sum(r["missing"] for r in res) == 0, [(r["file"], r.get("gone"), r["missing"]) for r in res])
    said = []
    messagebox.showinfo = lambda *a, **k: said.append(a[1] if len(a) > 1 else "")
    n0 = len(M2.items)
    app.compliance_read_docs(); app.update()
    check("Read customer documents knows they are all read (no duplicates)", len(M2.items) == n0 and said and "Every customer document" in said[-1])
    # Save all efforts: one package each
    L2 = E.EffortList(os.path.join(tmp, "PC2", "Osprey", "Osprey_Effort_List.xlsx"), "Osprey"); L2.pending = True; L2.save()
    app.efforts.put("Osprey", path=L2.path)
    out = app.pkg_save_all(os.path.join(tmp, "all"))
    check("Save all efforts: one package per effort", len(out) == 2 and all(os.path.isfile(p) for p in out), out)
    n = sum(checks)
    print(f"GUI PKG ROUNDTRIP PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI PKG ROUNDTRIP FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
