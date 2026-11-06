"""Score the acronym scan against your acronym set (3.61.0) and log the numbers only.

    .\\venv\\Scripts\\python.exe tools\\acreval.py              (the set in %USERPROFILE%\\Stationkeeper Acronym Set,
                                                            or SK_ACRONYM_SET)
    .\\venv\\Scripts\\python.exe tools\\acreval.py --floor      (buildrel: exit 1 below tools\\acronym_floor.json)
    .\\venv\\Scripts\\python.exe tools\\acreval.py --opencv     (the same scan twice: our picture steps, then OpenCV's,
                                                            when OpenCV is in this venv; finds whether 3.47.0 lost terms)
    .\\venv\\Scripts\\python.exe tools\\acreval.py --show       (also lists the missed terms by file, on screen only)

The set stays on the PC, outside the repository. The history and floors hold numbers only, never a file's name or a term
(house rule 4); --show prints the missed terms to this console and nowhere else. Each file has its own floor, its first
recall, so a harder file added later never stops the build. The scan uses the fixed test database (as evaluate.py does),
so the score measures reading and finding; terms this PC's own Exclusion List would hold back are counted apart."""
import csv, datetime, glob, hashlib, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
args = sys.argv[1:]
flags = {a for a in args if a.startswith("--")}
args = [a for a in args if not a.startswith("--")]
import app_gui as A  # noqa: E402
import acreval as AE  # noqa: E402

folder = os.path.abspath(args[0]) if args else AE.default_folder()
FLOOR = os.path.join(ROOT, "tools", "acronym_floor.json")
HIST = os.path.join(ROOT, "tools", "acronym_history.csv")
rows = AE.read_key(folder) if os.path.isdir(folder) else []
files = sorted(f for f in glob.glob(os.path.join(folder, "*")) if os.path.splitext(f)[1].lower() in A.SUPPORTED_EXTS) \
    if os.path.isdir(folder) else []
if not rows or not files:
    print(f"ACRONYM_EVAL {len(files)} file(s), {'no' if not rows else len(rows)} answer key row(s): no score, no floor")
    sys.exit(0)

real_db = A.DB_FILE
own_ex = set()
try:
    _i, ex, ex_up = A.load_database()                        # this PC's Exclusion List, counted apart
    own_ex = {r["Term"] for r in rows if (r.get("Expect") or "").lower() == "found"
              and (A.fold(r["Term"]) in ex or r["Term"].upper() in ex_up)}
except Exception:  # noqa: BLE001
    pass
A.DB_FILE = os.path.join(ROOT, "test_samples", "test_database.csv")


def scan():
    t0 = time.time()
    res = A.analyze_batch(files, lambda m: None)
    return res, time.time() - t0


def use_opencv():
    """Our picture steps swapped for OpenCV's, for this run only (tools never ship)."""
    import numpy as np
    import cv2
    import imgops as IO
    modes = {"color": cv2.IMREAD_COLOR, "gray": cv2.IMREAD_GRAYSCALE, "unchanged": cv2.IMREAD_UNCHANGED}
    IO.imdecode = lambda data, mode="color": cv2.imdecode(np.frombuffer(bytes(data), np.uint8), modes[mode])
    IO.resize = lambda img, size=None, fx=None, fy=None, cubic=False: cv2.resize(
        img, tuple(int(v) for v in size) if size else None, fx=fx or 0, fy=(fy or fx) or 0,
        interpolation=cv2.INTER_CUBIC if cubic else cv2.INTER_LINEAR)
    IO.bgr2gray = lambda bgr: cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    IO.clahe = lambda gray, clip=2.0, tiles=(8, 8): cv2.createCLAHE(clipLimit=clip, tileGridSize=tiles).apply(gray)
    IO.adaptive_mean_inv = lambda gray, block=15, c=10: cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, c)
    IO.open_ = lambda img, kw, kh: cv2.morphologyEx(img, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh)))
    IO.dilate = lambda img, kw, kh: cv2.dilate(img, np.ones((kh, kw), np.uint8))
    IO.erode = lambda img, kw, kh: cv2.erode(img, np.ones((kh, kw), np.uint8))


def line(tag, r, secs):
    bw = r["by_where"]
    pic = f"{bw['picture']['recall']}% of {bw['picture']['expected']}" if bw["picture"]["expected"] else "none"
    print(f"{tag} {len(r['files'])} file(s), {r['expected']} expected terms: recall {r['recall']}% (typed {bw['typed']['recall']}%, "
          f"pictures {pic}); false alarms {r['alarms']} of {r['absent']}; {secs:.0f} s")


res, secs = scan()
r = AE.score(res, rows, files)
line("ACRONYM_EVAL", r, secs)
if own_ex:
    print(f"ACRONYM_OWN_EXCLUSIONS {len(own_ex)} expected term(s) are on this PC's Exclusion List (the app would hide them)")
if "--show" in flags:
    for m in r["missed"]:
        print(f"  missed: {m['Term']:<12} {m['File']}  ({m.get('Where') or 'typed'})")
if "--opencv" in flags:
    try:
        use_opencv()
        A._OCR_CACHE.clear()
        res2, secs2 = scan()
        r2 = AE.score(res2, rows, files)
        line("ACRONYM_EVAL_OPENCV", r2, secs2)
        lost = [m for m in r["missed"] if m not in r2["missed"]]
        print(f"ACRONYM_OPENCV_DIFF {len(lost)} term(s) found with OpenCV's steps and missed with ours; "
              f"{len([m for m in r2['missed'] if m not in r['missed']])} the other way")
        if "--show" in flags:
            for m in lost:
                print(f"  OpenCV only: {m['Term']:<12} {m['File']}")
    except ImportError:
        print("ACRONYM_EVAL_OPENCV OpenCV is not in this venv: no comparison (pip install opencv-python-headless in a "
              "separate venv to compare; it never ships)")
A.DB_FILE = real_db

new = not os.path.exists(HIST)
with open(HIST, "a", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    if new:
        w.writerow(["When", "Version", "Files", "Expected", "Recall", "TypedRecall", "PictureRecall", "Alarms", "Absent", "Seconds"])
    w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), A.APP_VERSION, len(r["files"]), r["expected"], r["recall"],
                r["by_where"]["typed"]["recall"], r["by_where"]["picture"]["recall"], r["alarms"], r["absent"], round(secs)])
try:
    fl = json.load(open(FLOOR, encoding="utf-8"))
except (OSError, ValueError):
    fl = {}
per = fl.setdefault("files", {})
below, added = [], 0
for f in r["files"]:
    if f["recall"] is None:
        continue
    k = hashlib.sha1(os.path.relpath(f["path"], folder).lower().encode()).hexdigest()[:12]
    if k not in per:
        per[k] = f["recall"]; added += 1
    elif f["recall"] < float(per[k]):
        below.append((per[k], f["recall"]))
fl["set"] = f"{len(per)} file floor(s), last set {A.APP_VERSION}"
with open(FLOOR, "w", encoding="utf-8") as fh:
    json.dump(fl, fh, indent=1)
if added:
    print(f"ACRONYM_FLOOR set for {added} new file(s)")
if "--floor" in flags and below:
    print(f"ACRONYM_BELOW_FLOOR {len(below)} file(s) read worse than before: " + "; ".join(f"{b}% (floor {a}%)" for a, b in below))
    sys.exit(1)
