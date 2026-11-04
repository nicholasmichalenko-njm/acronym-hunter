"""Read every picture twice with the app's own reading code: once with OpenCV, once with OpenCV swapped out for
imgops (NumPy + Pillow). Compares the text read, line for line, and the time each way.

Usage (project folder, the app's venv):  python tools/ocr_side_by_side.py [--hard] [--out report.json]
Pictures: every picture inside test_samples documents, the standalone pictures, PDF pages rendered at 2x, and with
--hard the hard set (dark, inverted, small, turned, JPEG 40, noisy, odd sizes). Exploration tool; not shipped."""
import glob, io, json, os, sys, time, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import numpy as np
import cv2 as real_cv2
import cvshim
import app_gui
import doctr_engine

MODS = [app_gui, doctr_engine]


def use(mod):
    for m in MODS:
        m.cv2 = mod


def pictures(hard):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "test_samples", "**", "*"), recursive=True)):
        lf = f.lower()
        name = os.path.relpath(f, ROOT)
        if lf.endswith((".docx", ".pptx", ".xlsx")):
            try:
                z = zipfile.ZipFile(f)
            except Exception:
                continue
            for nm in z.namelist():
                if nm.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff")):
                    out.append((f"{name}:{nm}", z.read(nm)))
        elif lf.endswith((".png", ".jpg", ".jpeg")):
            out.append((name, open(f, "rb").read()))
        elif lf.endswith(".pdf"):
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(f)
                for i in range(min(len(doc), 6)):
                    buf = io.BytesIO()
                    doc[i].render(scale=2).to_pil().save(buf, format="PNG")
                    out.append((f"{name} page {i + 1}", buf.getvalue()))
            except Exception:
                pass
    if hard:
        from cv_compare import hard_set
        more = []
        for name, data in out:
            bgr = real_cv2.imdecode(np.frombuffer(data, np.uint8), real_cv2.IMREAD_COLOR)
            if bgr is None or bgr.shape[0] < 15 or bgr.shape[1] < 25:
                continue
            for hn, img in hard_set(bgr, name)[1:]:
                more.append((hn, real_cv2.imencode(".png", img)[1].tobytes()))
        out += more
    return out


def read(data):
    t = time.perf_counter()
    try:
        txt = app_gui._ocr_raw(data)
    except Exception as e:
        txt = f"ERROR {type(e).__name__}: {e}"
    return txt, time.perf_counter() - t


def main():
    hard = "--hard" in sys.argv
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    pics = pictures(hard)
    print(f"{len(pics)} pictures; reader: {app_gui.OCR_BACKEND}; docTR: {app_gui.doctr_active() if hasattr(app_gui, 'doctr_active') else '?'}", flush=True)
    rows = []
    t_cv = t_np = 0.0
    same = same_sorted = 0
    for i, (name, data) in enumerate(pics):
        order = ("cv", "np") if i % 2 == 0 else ("np", "cv")     # alternate who goes first
        got = {}
        for who in order:
            use(real_cv2 if who == "cv" else cvshim)
            got[who] = read(data)
        use(real_cv2)
        (a, ta), (b, tb) = got["cv"], got["np"]
        t_cv += ta; t_np += tb
        s1 = a == b
        s2 = sorted(a.splitlines()) == sorted(b.splitlines())
        same += s1; same_sorted += s2
        rows.append({"picture": name, "same": s1, "same_lines_any_order": s2, "opencv_s": round(ta, 3), "numpy_s": round(tb, 3),
                     "only_opencv": sorted(set(a.splitlines()) - set(b.splitlines()))[:10],
                     "only_numpy": sorted(set(b.splitlines()) - set(a.splitlines()))[:10]})
        print(f"{i + 1:4d}/{len(pics)} {'SAME' if s1 else ('SAME LINES' if s2 else 'DIFF')} cv {ta:6.2f}s np {tb:6.2f}s  {name}", flush=True)
    print(f"\nSAME TEXT {same}/{len(pics)}; same lines in any order {same_sorted}/{len(pics)}")
    print(f"TIME OpenCV {t_cv:.1f}s, NumPy {t_np:.1f}s ({(t_np / max(t_cv, 1e-9) - 1) * 100:+.1f}%)")
    if out:
        json.dump({"pictures": len(pics), "same": same, "same_any_order": same_sorted, "opencv_s": t_cv, "numpy_s": t_np,
                   "rows": rows}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
