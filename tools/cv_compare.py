"""Side by side: OpenCV vs imgops (NumPy + Pillow) on every picture step the app uses.

Usage: python tools/cv_compare.py PICTURE_FOLDER [--report out.json]
For each picture (plus a hard set made from it: dark, inverted, small, turned, JPEG, noisy, odd sizes) it runs each
step both ways and records: identical or not, the largest pixel difference, the share of pixels that differ, and the
time each way. Exploration tool; not shipped."""
import glob, io, json, os, sys, time
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import imgops as IO


def hard_set(bgr, name):
    out = [(name, bgr)]
    h, w = bgr.shape[:2]
    out.append((name + " dark", (bgr.astype(np.float32) * 0.35).astype(np.uint8)))
    out.append((name + " inverted", 255 - bgr))
    if min(h, w) > 60:
        out.append((name + " small", cv2.resize(bgr, (max(25, w // 3), max(15, h // 3)), interpolation=cv2.INTER_AREA)))
    out.append((name + " turned", np.ascontiguousarray(np.rot90(bgr))))
    ok, j = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 40])
    out.append((name + " jpeg40", cv2.imdecode(j, cv2.IMREAD_COLOR)))
    rng = np.random.default_rng(len(name))
    out.append((name + " noisy", np.clip(bgr.astype(np.int16) + rng.normal(0, 18, bgr.shape).astype(np.int16), 0, 255).astype(np.uint8)))
    out.append((name + " odd", np.ascontiguousarray(bgr[: max(15, h - 7), : max(25, w - 13)])))
    return out


def cmp(a, b):
    if a is None or b is None:
        return {"same": a is None and b is None, "max": None, "share": None}
    if a.shape != b.shape:
        return {"same": False, "max": None, "share": None, "shape": [list(a.shape), list(b.shape)]}
    d = np.abs(a.astype(np.int32) - b.astype(np.int32))
    return {"same": bool(d.max() == 0) if d.size else True, "max": int(d.max()) if d.size else 0,
            "share": float((d > 0).mean()) if d.size else 0.0}


def timed(f, *a, **k):
    t = time.perf_counter()
    r = f(*a, **k)
    return r, time.perf_counter() - t


def steps(bgr):
    """[(step, opencv result, imgops result, opencv seconds, imgops seconds)]"""
    res = []
    def add(name, fa, fb):
        (ra, ta), (rb, tb) = timed(fa), timed(fb)
        res.append((name, ra, rb, ta, tb))
        return ra
    png = cv2.imencode(".png", bgr)[1].tobytes()
    jpg = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes()
    add("decode png colour", lambda: cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR), lambda: IO.imdecode(png, "color"))
    add("decode jpeg colour", lambda: cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR), lambda: IO.imdecode(jpg, "color"))
    add("decode png grey", lambda: cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE), lambda: IO.imdecode(png, "gray"))
    add("encode png (round trip)", lambda: cv2.imdecode(cv2.imencode(".png", bgr)[1], cv2.IMREAD_UNCHANGED),
        lambda: IO.imdecode(IO.imencode_png(bgr), "unchanged"))
    gray = add("grey", lambda: cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), lambda: IO.bgr2gray(bgr))
    add("white border", lambda: cv2.copyMakeBorder(bgr, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=(255, 255, 255)),
        lambda: IO.border(bgr, 12, 255))
    add("enlarge 2x cubic", lambda: cv2.resize(bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC),
        lambda: IO.resize(bgr, fx=2.0, fy=2.0, cubic=True))
    f = 48.0 / max(1, bgr.shape[0] // 3)
    small = bgr[: max(2, bgr.shape[0] // 3)]
    add("enlarge to 48 high cubic", lambda: cv2.resize(small, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC),
        lambda: IO.resize(small, fx=f, fy=f, cubic=True))
    h, w = bgr.shape[:2]
    s = 1024 / max(h, w)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    add("fit 1024 linear (docTR finder)", lambda: cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR),
        lambda: IO.resize(bgr, size=(nw, nh)))
    nh2 = 32; nw2 = max(1, min(128, round(32 * w / h)))
    add("fit 32 high linear (docTR reader)", lambda: cv2.resize(bgr, (nw2, nh2), interpolation=cv2.INTER_LINEAR),
        lambda: IO.resize(bgr, size=(nw2, nh2)))
    add("contrast boost (CLAHE)", lambda: cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray), lambda: IO.clahe(gray, 2.0))
    add("ink threshold (Otsu)", lambda: cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
        lambda: IO.otsu_inv(gray)[1])
    if h >= 40 and w >= 40:
        bw = add("local threshold", lambda: cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 10),
                 lambda: IO.adaptive_mean_inv(gray, 15, 10))
        kx, ky = max(30, w // 25), max(30, h // 25)
        def cv_lines():
            hk = cv2.getStructuringElement(cv2.MORPH_RECT, (kx, 1)); vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, ky))
            m = cv2.bitwise_or(cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk), cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk))
            return cv2.dilate(m, np.ones((3, 3), np.uint8))
        def io_lines():
            m = np.maximum(IO.open_(bw, kx, 1), IO.open_(bw, 1, ky))
            return IO.dilate(m, 3, 3)
        add("line mask (table rules)", cv_lines, io_lines)
    bitmap = (gray < 128).astype(np.uint8)
    add("open 3x3 (docTR)", lambda: cv2.morphologyEx(bitmap, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), lambda: IO.open_(bitmap, 3, 3))
    def cv_boxes():
        cs, _ = cv2.findContours(bitmap, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return sorted(tuple(int(v) for v in cv2.boundingRect(c)) for c in cs)
    (ba, ta), (bb, tb) = timed(cv_boxes), timed(IO.outer_boxes, bitmap)
    res.append(("outer shape boxes (docTR)", ba, bb, ta, tb))
    return res


def main():
    folder = sys.argv[1]
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    pics = sorted(glob.glob(os.path.join(folder, "*")))
    agg = {}
    worst = {}
    n = 0
    for p in pics:
        bgr = cv2.imread(p, cv2.IMREAD_COLOR)
        if bgr is None or bgr.shape[0] < 15 or bgr.shape[1] < 25:
            continue
        for name, img in hard_set(bgr, os.path.basename(p)):
            n += 1
            for step, a, b, ta, tb in steps(img):
                g = agg.setdefault(step, {"runs": 0, "same": 0, "max": 0, "share_sum": 0.0, "cv_s": 0.0, "io_s": 0.0})
                g["runs"] += 1; g["cv_s"] += ta; g["io_s"] += tb
                if isinstance(a, list):
                    same = a == b
                    g["same"] += same
                    if not same:
                        worst.setdefault(step, []).append((name, len(a), len(b), len(set(a) ^ set(b))))
                    continue
                c = cmp(a, b)
                g["same"] += c["same"]
                if not c["same"]:
                    g["max"] = max(g["max"], c["max"] or 999)
                    g["share_sum"] += c["share"] or 1.0
                    worst.setdefault(step, []).append((name, c["max"], c["share"]))
    print(f"{n} pictures (from {len(pics)} files with the hard set)")
    print(f"{'step':36s} {'same':>9s} {'max diff':>8s} {'avg share':>9s} {'OpenCV s':>9s} {'NumPy s':>9s} {'ratio':>6s}")
    for step, g in agg.items():
        diff = g["runs"] - g["same"]
        print(f"{step:36s} {g['same']:4d}/{g['runs']:<4d} {g['max']:8d} {g['share_sum'] / max(1, diff):9.5f} "
              f"{g['cv_s']:9.3f} {g['io_s']:9.3f} {g['io_s'] / max(g['cv_s'], 1e-9):6.1f}")
    for step, w in worst.items():
        print("DIFF", step, w[:4])
    if report:
        json.dump({"pictures": n, "steps": agg, "diffs": {k: v[:20] for k, v in worst.items()}}, open(report, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
