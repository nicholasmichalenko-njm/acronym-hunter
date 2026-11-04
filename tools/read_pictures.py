"""Read every test picture with this checkout's own reading code and save the text and the time each took.
Run in two checkouts and compare the files: python tools/read_pictures.py out.json [--hard] [--repeat N]
(3.47.0: how OpenCV's removal was proven; the hard set needs no OpenCV.)"""
import glob, io, json, os, sys, time, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import numpy as np
from PIL import Image, ImageFilter, ImageOps
import app_gui


def pictures(hard):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "test_samples", "**", "*"), recursive=True)):
        lf, name = f.lower(), os.path.relpath(f, ROOT).replace("\\", "/")
        if lf.endswith((".docx", ".pptx", ".xlsx")):
            try:
                z = zipfile.ZipFile(f)
            except Exception:
                continue
            out += [(f"{name}:{n}", z.read(n)) for n in z.namelist() if n.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff"))]
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
    if hard:                                   # made with Pillow only, so both checkouts get the same bytes
        more = []
        for name, data in out:
            try:
                im = Image.open(io.BytesIO(data)).convert("RGB")
            except Exception:
                continue
            if im.width < 25 or im.height < 15:
                continue
            rng = np.random.default_rng(len(name))
            noisy = np.clip(np.asarray(im).astype(np.int16) + rng.normal(0, 18, (im.height, im.width, 3)).astype(np.int16), 0, 255)
            var = {"dark": im.point(lambda v: int(v * 0.35)), "inverted": ImageOps.invert(im),
                   "small": im.resize((max(25, im.width // 3), max(15, im.height // 3)), Image.BOX), "turned": im.rotate(90, expand=True),
                   "noisy": Image.fromarray(noisy.astype(np.uint8)), "blurred": im.filter(ImageFilter.GaussianBlur(1.2))}
            for k, v in var.items():
                b = io.BytesIO()
                v.save(b, format="PNG")
                more.append((f"{name} {k}", b.getvalue()))
            b = io.BytesIO()
            im.save(b, format="JPEG", quality=40)
            more.append((f"{name} jpeg40", b.getvalue()))
        out += more
    return out


def main():
    out = sys.argv[1]
    repeat = int(sys.argv[sys.argv.index("--repeat") + 1]) if "--repeat" in sys.argv else 1
    rows = []
    for name, data in pictures("--hard" in sys.argv):
        times, txt = [], ""
        for _ in range(repeat):
            t = time.perf_counter()
            try:
                txt = app_gui._ocr_raw(data)
            except Exception as e:
                txt = f"ERROR {type(e).__name__}: {e}"
            times.append(time.perf_counter() - t)
        rows.append({"picture": name, "text": txt, "seconds": min(times)})
        print(f"{min(times):6.2f}s  {name}", flush=True)
    json.dump({"version": app_gui.APP_VERSION, "rows": rows}, open(out, "w"), indent=1)
    print(f"{len(rows)} pictures, {sum(r['seconds'] for r in rows):.1f} s")


if __name__ == "__main__":
    main()
