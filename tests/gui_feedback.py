import os, sys, zipfile, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"   # no first-start wizard during tests
import app_gui as A, feedback as FB
import tempfile as _tf
_t = _tf.mkdtemp(); A.CONFIG_DIR = os.path.join(_t, "config"); A.CHOICES_FILE = os.path.join(_t, "config", "choices.json")
from tkinter import filedialog
import tempfile; OUT = os.path.join(tempfile.gettempdir(), "fb_out.zip")
filedialog.asksaveasfilename = lambda **k: OUT
app = A.AcronymAppGUI()
def go():
    app.start_batch([os.path.join(A.BASE_DIR, "test_samples", f) for f in ("Kestrel_Technical_Volume.docx", "Kestrel_Compliance_Matrix.xlsx")])
    app.after(500, wait)
def wait():
    if app.btn_cancel.winfo_ismapped():
        app.after(500, wait); return
    w = FB.open_feedback(app); api = w._api
    tests = [("Preview is slow", "When I click SOW the preview takes long"),          # term from results
             ("Preview is slow", "The Kestrel volume did not show"),                   # file name piece
             ("Preview is slow", "It happened on Compliance_Matrix"),                 # file stem piece
             ("Preview is slow", "Clicking a row in the results table takes 5 seconds before the picture shows. Expected under 1 second.")]
    for title, text in tests:
        api["title"].delete(0, "end"); api["title"].insert(0, title)
        api["box"].delete("1.0", "end"); api["box"].insert("1.0", text)
        api["save"]()
        print(f"{text[:45]!r:50} -> {api['msg'].cget('text')[:60]}")
    d = FB.export_dialog(app)
    print("leaks:", d._api["leaks"])
    d._api["save_btn"].invoke()
    z = zipfile.ZipFile(OUT); names = z.namelist(); print("zip:", names)
    blob = "".join(z.read(n).decode() for n in names)
    for bad in ("Kestrel", "Compliance_Matrix", "Technical_Volume", "SOW", os.path.expanduser("~")):
        print(f"  contains {bad!r}: {bad in blob}")
    print(z.read("REPORT.md").decode()[:900])
    app.destroy()
app.after(1500, go); app.mainloop()
