"""2.22.0: what the math reader read is kept with the project or the effort workspace and put back after a rescan or
reopen, for unchanged files only (no math add-on needed: the reader's output is given directly)."""
import os, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
checks = {}


def check(name, ok, info=""):
    checks[name] = bool(ok)
    print(("PASS " if ok else "FAIL ") + name, info)


DOC = os.path.join(tmp, "Thermal Volume.docx")
open(DOC, "wb").write(b"stand-in file; only its size and date matter here")
LOC = "Thermal Volume.docx (Body, image 'Equation 3')"
KEY = "[equation picture] Thermal Volume.docx"


def fresh():
    return {KEY: {"category": "Equation (picture)", "count": 1, "locations": [LOC], "definitions": [], "in_db": False,
                  "excluded": False, "status": "CHECK EQUATION PICTURE", "selected_definition": "Math inside a picture."}}


app = A.AcronymAppGUI()


def go():
    app.scanned_paths["Thermal Volume.docx"] = DOC
    app.results = fresh()
    m = A.build_matcher()
    app.apply_math_result(KEY, LOC, [r"Q = \sigma A T^4"], m)
    check("read marks the picture", "READ BY MATH READER" in app.results[KEY]["status"], app.results[KEY]["status"])
    check("kept in the workspace", LOC in app.ws.get("math_reads", {}), list(app.ws.get("math_reads", {})))
    # a rescan rebuilds the results: the read comes back without the math reader
    app.results = fresh()
    n = app.reapply_math_reads()
    check("put back after a rescan", n == 1 and "READ BY MATH READER" in app.results[KEY]["status"]
          and any(d.get("math_reader") for d in app.results.values()), (n, app.results[KEY]["status"]))
    check("putting back twice adds nothing", app.reapply_math_reads() == 0)
    # the file changed: its saved read is not used
    time.sleep(1.1); open(DOC, "ab").write(b" edited")
    app.results = fresh()
    check("changed file drops the saved read", app.reapply_math_reads() == 0 and "CHECK" in app.results[KEY]["status"])
    # with AI and ML off nothing generative comes back
    app.results = fresh()
    app.apply_math_result(KEY, LOC, [r"E = m c^2"], m)
    app.results = fresh()
    A.set_ai_ml(False) if hasattr(A, "set_ai_ml") else None
    off = not A.ai_ml_on()
    n_off = app.reapply_math_reads()
    if hasattr(A, "set_ai_ml"):
        A.set_ai_ml(True)
    check("AI and ML off: nothing put back", (not off) or n_off == 0, (off, n_off))
    # a project keeps the reads in the .ahproj file and puts them back on reopen
    proj = A.Project(os.path.join(tmp, "Kestrel.ahproj")); proj.data = A.Project.new_data(); proj.save()
    app.project = proj
    app.results = fresh()
    app.apply_math_result(KEY, LOC, [r"P = I V"], m)
    p2 = A.Project(proj.path); p2.load()
    check("project file holds the read", LOC in p2.data.get("math", {}) and p2.data["math"][LOC]["formulas"] == [r"P = I V"],
          list(p2.data.get("math", {})))
    app.project = p2
    app.results = fresh()
    check("reopened project puts it back", app.reapply_math_reads() == 1 and "READ BY MATH READER" in app.results[KEY]["status"])
    app.project = None
    ok = all(checks.values())
    print(f"GUI MATHKEEP {'PASS' if ok else 'FAIL'} ({sum(checks.values())}/{len(checks)})")
    app.update(); app.after(300, app.destroy)


app.after(800, go)
app.mainloop()
