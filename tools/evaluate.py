"""Score Acronym Hunter against test_samples/ground_truth.csv and log the result.

Run from the project folder:
    .\\venv\\Scripts\\python.exe tools\\evaluate.py                         (scan test_samples)
    .\\venv\\Scripts\\python.exe tools\\evaluate.py --note "dpi 300 test"   (label this run in the history)
    .\\venv\\Scripts\\python.exe tools\\evaluate.py D:\\mydocs              (another folder with its own ground_truth.csv)

ground_truth.csv columns:
    File    file name, or * for any file in the folder
    Term    exact term as it should appear in the Term column
    Expect  found   = the app must report it from that file (counts toward RECALL)
            absent  = the app must NOT report it (noise; counts toward FALSE ALARMS)
    Note    free text
"""
import csv, datetime, glob, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
args = sys.argv[1:]
note = ""
if "--note" in args:
    i = args.index("--note")
    note = args[i + 1] if i + 1 < len(args) else ""
    del args[i:i + 2]
folder = os.path.abspath(args[0]) if args else os.path.join(ROOT, "test_samples")
sys.argv = [sys.argv[0]]
truth_path = os.path.join(folder, "ground_truth.csv")
if not os.path.exists(truth_path):
    sys.exit(f"No ground_truth.csv in {folder}")

import app_gui  # noqa: E402  (imports the real engine, same code the exe runs)
# Score against the fixed test database (test_samples\test_database.csv), not your working database, so scores
# stay comparable over time and real terms never affect them. A folder may bring its own test_database.csv.
_test_db = os.path.join(folder, "test_database.csv")
app_gui.DB_FILE = _test_db if os.path.exists(_test_db) else os.path.join(ROOT, "test_samples", "test_database.csv")
_test_fix = os.path.join(folder, "test_ocr_corrections.csv")
app_gui.OCR_FIXES_FILE = _test_fix if os.path.exists(_test_fix) else os.path.join(ROOT, "test_samples", "test_ocr_corrections.csv")

files = sorted(f for f in glob.glob(os.path.join(folder, "*"))
               if os.path.splitext(f)[1].lower() in app_gui.SUPPORTED_EXTS)
start = time.time()
res = app_gui.analyze_batch(files, lambda m: None)
seconds = time.time() - start

def reported(term, file_name):
    d = res.get(term)
    if not d or d.get("excluded"):
        return False
    return file_name == "*" or any(loc.startswith(file_name) for loc in d["locations"])

rows = list(csv.DictReader(open(truth_path, encoding="utf-8-sig")))
want = [r for r in rows if r["Expect"].strip().lower() == "found"]
avoid = [r for r in rows if r["Expect"].strip().lower() == "absent"]
missed = [r for r in want if not reported(r["Term"], r["File"])]
alarms = [r for r in avoid if reported(r["Term"], r["File"])]
recall = 100.0 * (len(want) - len(missed)) / max(1, len(want))
candidates = sum(1 for d in res.values() if d["status"].startswith("🔍"))
version = "dev"
try:
    vi = open(os.path.join(ROOT, "version_info.txt"), encoding="utf-8").read()
    version = vi.split("'FileVersion', '")[1].split("'")[0]
except Exception:
    pass

print(f"\nFolder:        {folder}")
print(f"OCR models:    {app_gui.OCR_MODEL_INFO}")
print(f"RECALL:        {recall:.1f}%  ({len(want) - len(missed)} of {len(want)} expected terms found)")
print(f"FALSE ALARMS:  {len(alarms)} of {len(avoid)} known-noise terms still reported")
print(f"New candidates to review: {candidates}   Total rows: {len(res)}   Scan time: {seconds:.0f} s")
if missed:
    print("\nMISSED (should be found):")
    for r in missed: print(f"  {r['Term']:<10} {r['File']:<36} {r.get('Note', '')}")
if alarms:
    print("\nFALSE ALARMS (should not be reported):")
    for r in alarms: print(f"  {r['Term']:<10} {r['File']:<36} {r.get('Note', '')}")

hist = os.path.join(ROOT, "tools", "eval_history.csv")
new = not os.path.exists(hist)
with open(hist, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if new:
        w.writerow(["Date", "Version", "Folder", "OCR models", "Recall %", "Missed", "False alarms", "New candidates", "Rows", "Seconds", "Note"])
    w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), version, os.path.basename(folder),
                app_gui.OCR_MODEL_INFO, f"{recall:.1f}", len(missed), len(alarms), candidates, len(res), f"{seconds:.0f}", note])
print(f"\nLogged to tools\\eval_history.csv")
