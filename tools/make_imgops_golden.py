"""Save OpenCV's answers for every picture step the app uses, so tests/test_imgops.py can hold imgops (and imgcore)
to them without OpenCV installed. Run once, where OpenCV is still installed: python tools/make_imgops_golden.py
Pictures: small crops of the fictional Kestrel pictures plus made-up noise. Writes tests/golden_img/imgops_v1.npz."""
import glob, os, sys
import numpy as np
import cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pictures():
    rng = np.random.default_rng(347)
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "test_samples", "*.png")) + glob.glob(os.path.join(ROOT, "test_samples", "*.jpg"))):
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        for _ in range(2):
            ch, cw = min(h, int(rng.integers(90, 220))), min(w, int(rng.integers(100, 260)))
            y, x = int(rng.integers(0, h - ch + 1)), int(rng.integers(0, w - cw + 1))
            out.append(np.ascontiguousarray(img[y:y + ch, x:x + cw]))
    for _ in range(4):
        h, w = int(rng.integers(40, 180)), int(rng.integers(40, 220))
        n = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
        out.append(cv2.GaussianBlur(n, (5, 5), 0) if _ % 2 else n)
    return out


def main():
    data = {}
    for i, bgr in enumerate(pictures()):
        k = f"p{i:02d}_"
        h, w = bgr.shape[:2]
        data[k + "bgr"] = bgr
        data[k + "png"] = cv2.imencode(".png", bgr)[1]
        data[k + "jpg"] = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])[1]
        data[k + "jpgbytes"] = data[k + "jpg"].copy()       # JPEG bytes kept: another encoder would give other pixels
        data[k + "dec_png_gray"] = cv2.imdecode(data[k + "png"], cv2.IMREAD_GRAYSCALE)
        data[k + "dec_jpg_color"] = cv2.imdecode(data[k + "jpg"], cv2.IMREAD_COLOR)
        data[k + "dec_jpg_gray"] = cv2.imdecode(data[k + "jpg"], cv2.IMREAD_GRAYSCALE)
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        data[k + "gray"] = g
        data[k + "cubic2x"] = cv2.resize(bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        f = 48.0 / max(1, h // 3)
        data[k + "cubic48"] = cv2.resize(bgr[:max(2, h // 3)], None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        s = 1024 / max(h, w)
        data[k + "fit1024"] = cv2.resize(bgr, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_LINEAR)
        data[k + "fit32"] = cv2.resize(bgr, (max(1, min(128, round(32 * w / h))), 32), interpolation=cv2.INTER_LINEAR)
        data[k + "clahe"] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
        data[k + "otsu"] = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 10)
        data[k + "adaptive"] = bw
        kx, ky = max(30, w // 25), max(30, h // 25)
        m = cv2.bitwise_or(cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (kx, 1))),
                           cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, ky))))
        data[k + "lines"] = cv2.dilate(m, np.ones((3, 3), np.uint8))
        bitmap = (g < 128).astype(np.uint8)
        data[k + "open3"] = cv2.morphologyEx(bitmap, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        cs, _ = cv2.findContours(data[k + "open3"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        data[k + "boxes"] = np.array(sorted(tuple(int(v) for v in cv2.boundingRect(c)) for c in cs), np.int32).reshape(-1, 4)
    # outputs are kept as SHA-256 of their bytes (exact, and small); the 48-high enlargement is kept whole, since
    # OpenCV hands it to Intel's library and a pixel may differ by one grey level
    import hashlib
    for key in list(data):
        step = key.split("_", 1)[1]
        if step in ("bgr", "png", "jpg", "jpgbytes", "cubic48"):
            continue
        a = np.ascontiguousarray(data[key])
        data[key] = np.frombuffer(hashlib.sha256(str(a.shape).encode() + a.tobytes()).digest(), np.uint8)
    for key in [k for k in data if k.endswith(("_png", "_jpg"))]:
        del data[key]                                    # the test encodes the crops again with the same settings
    out = os.path.join(ROOT, "tests", "golden_img", "imgops_v1.npz")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez_compressed(out, **data)
    print(out, os.path.getsize(out), "bytes,", len([k for k in data if k.endswith("_bgr")]), "pictures")


if __name__ == "__main__":
    main()
