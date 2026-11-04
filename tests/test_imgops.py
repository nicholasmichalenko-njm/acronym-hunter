"""3.47.0 the picture steps that replaced OpenCV give OpenCV's answers.

1. imgops (NumPy and Pillow) against OpenCV's saved answers (tests/golden_img/imgops_v1.npz, made once by
   tools/make_imgops_golden.py while OpenCV was installed): every step exact; the 48-high enlargement within one grey
   level on a few pixels (OpenCV hands it to Intel's library).
2. imgcore (native/imgcore.c, compiled here when a C compiler is found) against imgops' NumPy steps on made-up
   pictures: exact, so the compiled steps and the reference never drift apart.
3. The program's reading code no longer imports OpenCV outside the legacy edition's noise removal."""
import glob, hashlib, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import numpy as np

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def build_core():
    """Compile native/imgcore.c into a temporary folder; None when no compiler is found."""
    names = ["gcc", "gcc.exe", os.path.join(os.environ.get("USERPROFILE", ""), "ah_toolchain", "msys64", "ucrt64", "bin", "gcc.exe")]
    gcc = next((p for p in (shutil.which(n) or (n if os.path.isfile(n) else None) for n in names) if p), None)
    if not gcc:
        return None
    out = tempfile.mkdtemp()
    lib = os.path.join(out, "imgcore.dll" if os.name == "nt" else "imgcore.so")
    cmd = [gcc, "-O3", "-ffp-contract=off", "-fno-fast-math", "-shared", "-o", lib, os.path.join(ROOT, "native", "imgcore.c")]
    cmd += ["-static-libgcc"] if os.name == "nt" else ["-fPIC", "-lm"]
    env = dict(os.environ, PATH=os.path.dirname(gcc) + os.pathsep + os.environ.get("PATH", ""))
    r = subprocess.run(cmd, capture_output=True, env=env)
    return out if r.returncode == 0 and os.path.isfile(lib) else None


core_dir = build_core()
os.environ["AH_IMGCORE_OFF"] = "1"                 # import with NumPy steps; the compiled ones are switched in below
import imgops as IO
del os.environ["AH_IMGCORE_OFF"]
core = None
if core_dir:
    os.environ["AH_IMGCORE_DIR"] = core_dir
    core = IO._load_core()
check("imgcore compiles and loads (skipped without a C compiler)", core is not None or core_dir is None, core_dir)


def h(a):
    a = np.ascontiguousarray(a)
    return hashlib.sha256(str(a.shape).encode() + a.tobytes()).digest()


def steps(bgr, jpg):
    H, W = bgr.shape[:2]
    out = {}
    out["dec_png_gray"] = IO.imdecode(IO.imencode_png(bgr), "gray")
    out["dec_jpg_color"] = IO.imdecode(jpg, "color")
    out["dec_jpg_gray"] = IO.imdecode(jpg, "gray")
    g = IO.bgr2gray(bgr)
    out["gray"] = g
    out["cubic2x"] = IO.resize(bgr, fx=2.0, fy=2.0, cubic=True)
    f = 48.0 / max(1, H // 3)
    out["cubic48"] = IO.resize(bgr[:max(2, H // 3)], fx=f, fy=f, cubic=True)
    s = 1024 / max(H, W)
    out["fit1024"] = IO.resize(bgr, size=(max(1, round(W * s)), max(1, round(H * s))))
    out["fit32"] = IO.resize(bgr, size=(max(1, min(128, round(32 * W / H))), 32))
    out["clahe"] = IO.clahe(g, 2.0, (8, 8))
    out["otsu"] = IO.otsu_inv(g)[1]
    bw = IO.adaptive_mean_inv(g, 15, 10)
    out["adaptive"] = bw
    m = np.bitwise_or(IO.open_(bw, max(30, W // 25), 1), IO.open_(bw, 1, max(30, H // 25)))
    out["lines"] = IO.dilate(m, 3, 3)
    out["open3"] = IO.open_((g < 128).astype(np.uint8), 3, 3)
    out["boxes"] = np.array(IO.outer_boxes(out["open3"]), np.int32).reshape(-1, 4)
    return out


gold = np.load(os.path.join(HERE, "golden_img", "imgops_v1.npz"))
keys = sorted({k.split("_", 1)[0] for k in gold.files})
for label, lib in (("NumPy", None), ("imgcore", core)):
    if label == "imgcore" and core is None:
        continue
    IO._C = lib
    bad, near = [], []
    for k in keys:
        got = steps(gold[k + "_bgr"], gold[k + "_jpgbytes"].tobytes())
        for step, a in got.items():
            g = gold[k + "_" + step]
            if step == "cubic48":
                d = np.abs(a.astype(np.int32) - g.astype(np.int32)) if a.shape == g.shape else None
                if d is None or d.max() > 1 or (d > 0).mean() > 0.002:
                    bad.append(f"{k} {step}")
                elif d.max():
                    near.append(k)
            elif h(a) != g.tobytes():
                bad.append(f"{k} {step}")
    check(f"{label}: every step gives OpenCV's answer on {len(keys)} pictures", not bad, bad[:8])
IO._C = None

# 2. compiled steps against the NumPy reference on made-up pictures
if core is not None:
    rng = np.random.default_rng(470)
    bad = []
    for t in range(60):
        hh, ww = int(rng.integers(1, 140)), int(rng.integers(1, 140))
        img = rng.integers(0, 256, (hh, ww, 3), dtype=np.uint8)
        if t % 3 == 0:
            img[:] = img[:1, :1]                      # flat
        g = img[:, :, 1].copy()
        bw = ((rng.random((hh, ww)) < rng.uniform(0.05, 0.95)) * 255).astype(np.uint8)
        bm = (bw > 0).astype(np.uint8)
        kx, ky = int(rng.integers(6, 50)), int(rng.integers(6, 50))
        jobs = {
            "gray": lambda: IO.bgr2gray(img),
            "cubic2x": lambda: IO.resize(img, fx=2.0, fy=2.0, cubic=True),
            "linear": lambda: IO.resize(img, size=(int(rng.integers(1, 200)), int(rng.integers(1, 200)))),
            "clahe": lambda: IO.clahe(g, 2.0) if hh >= 2 and ww >= 2 else g,
            "adaptive": lambda: IO.adaptive_mean_inv(g, 15, 10),
            "open h": lambda: IO.open_(bw, kx, 1),
            "open v": lambda: IO.open_(bw, 1, ky),
            "open3": lambda: IO.open_(bm, 3, 3),
            "dilate3": lambda: IO.dilate(bw, 3, 3),
            "boxes": lambda: np.array(IO.outer_boxes(bm), np.int32).reshape(-1, 4),
        }
        for name, job in jobs.items():
            state = rng.bit_generator.state
            IO._C = None
            a = job()
            rng.bit_generator.state = state
            IO._C = core
            b = job()
            IO._C = None
            if a.shape != b.shape or (a != b).any():
                bad.append(f"{name} {img.shape}")
    check("imgcore matches the NumPy steps exactly on 60 made-up pictures", not bad, bad[:8])

# 3. no OpenCV in the reading code, except the legacy edition's noise removal
uses = []
for f in ("app_gui.py", "pictures.py", "tess_train.py", "doctr_engine.py", "imgops.py"):
    for n, line in enumerate(open(os.path.join(ROOT, f), encoding="utf-8"), 1):
        pat = r"\bimport cv2\b" if f == "imgops.py" else r"\bimport cv2\b|\bcv2\."   # imgops' notes name the calls it matches
        if re.search(pat, line) and "fastNlMeansDenoising" not in line and "legacy edition only" not in line:
            uses.append(f"{f}:{n}")
check("the reading code uses no OpenCV (the legacy edition's noise removal aside)", not uses, uses)

n = sum(checks)
print(f"IMGOPS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
