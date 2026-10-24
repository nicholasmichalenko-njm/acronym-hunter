"""Apply Choice must survive a fresh scan without a project (2.3.2)."""
import os, sys, tempfile, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
tmp = tempfile.mkdtemp()
A.DB_FILE = os.path.join(tmp, "db.csv")
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
with open(A.DB_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["Term", "Category", "Definition", "Action"])
    w.writerow(["SOW", "Acronym", "Statement of Work", "Include"]); w.writerow(["SOW", "Acronym", "Scope of Work", "Include"])
app = A.AcronymAppGUI()
files = [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")]
state = {"n": 0}
def go():
    app.start_batch(files); app.after(500, wait)
def wait():
  try:
    _wait()
  except Exception:
    import traceback; traceback.print_exc(); app.destroy()
def _wait():
    if app.btn_cancel.winfo_ismapped():
        app.after(500, wait); return
    d = app.results["SOW"]
    state["n"] += 1
    if state["n"] == 1:
        print("scan 1:", d["status"], "|", d["selected_definition"][:60])
        app.selected_term = "SOW"; app.combo.configure(state="normal", values=d["definitions"]); app.combo.set("Scope of Work")
        app.apply_choice()
        print("after Apply Choice:", app.results["SOW"]["selected_definition"])
        app.scan_again(); app.after(500, wait)
    else:
        print("scan 2 (Scan Again):", d["status"], "|", d["selected_definition"])
        assert d["selected_definition"] == "Scope of Work", "choice was not kept"
        print("PASS: choice kept across scans")
        app.destroy()
app.after(1500, go); app.mainloop()
