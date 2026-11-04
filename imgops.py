"""Picture steps for reading, in NumPy and Pillow only (exploration: a stand-in for OpenCV, held to OpenCV's output).

Each function reproduces one OpenCV call the app makes, with OpenCV's arithmetic (rounding, borders, anchors), so the
pixels come out the same. Arrays follow OpenCV's layout: colour is BGR, uint8 unless said otherwise. Rules only."""
import io, os
import numpy as np
from PIL import Image

_POOL = []
_CPOOL = []


def _load_core():
    """imgcore (native/imgcore.c), our own compiled picture steps, when it sits beside this file, in the program
    folder or in vendor/imgcore. None when it is missing or AH_IMGCORE_OFF is set; then NumPy does every step."""
    if os.environ.get("AH_IMGCORE_OFF"):
        return None
    import ctypes, sys
    name = "imgcore.dll" if os.name == "nt" else "imgcore.so"
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.environ.get("AH_IMGCORE_DIR", ""), getattr(sys, "_MEIPASS", ""), here, os.path.join(here, "native"),
              os.path.join(here, "vendor", "imgcore")):
        f = os.path.join(d, name) if d else ""
        if f and os.path.isfile(f):
            try:
                lib = ctypes.CDLL(f)
                if lib.imgcore_version() == 2:
                    V, I, L = ctypes.c_void_p, ctypes.c_int, ctypes.c_int64
                    lib.gray_bgr.argtypes = [V, L, V]
                    lib.resize_fixed.argtypes = [V, I, I, I, V, I, I, I, V, V, V, V, I, I]
                    lib.clahe_blend.argtypes = [V, I, I, I, V, V, V, V, V, V, V, V, V, V]
                    lib.adaptive_mean_inv.argtypes = [V, I, I, I, V, V, I, I]
                    lib.open_line.argtypes = [V, I, I, I, I, ctypes.c_uint8, V, I, I]
                    lib.dilate3.argtypes = [V, I, I, ctypes.c_uint8, V, I, I]
                    lib.clahe_hist.argtypes = [V, I, I, I, I, I, I, I, V, I, I]
                    lib.erode3.argtypes = [V, I, I, ctypes.c_uint8, V, I, I]
                    lib.outer_boxes.argtypes = [V, I, I, V, I]
                    return lib
            except OSError:
                pass
    return None


_C = _load_core()


def _p(a):
    return a.ctypes.data


CPAR_MIN = 1_000_000                # values below which one thread does the job (thread start-up costs more)


def _cpar(fn, n, per_row):
    """fn(r0, r1) over row ranges covering 0..n. imgcore's calls let go of the interpreter lock (ctypes does), so on a
    big picture the bands run on several cores at once, as OpenCV's own steps do. Each band writes its own rows."""
    workers = max(1, min(16, os.cpu_count() or 1))
    if n * per_row < CPAR_MIN or workers == 1 or n < 2:
        if n > 0:
            fn(0, n)
        return
    if not _CPOOL:
        from concurrent.futures import ThreadPoolExecutor
        _CPOOL.append(ThreadPoolExecutor(max_workers=workers))
    step = max(1, -(-n // (workers * 2)))
    for f in [_CPOOL[0].submit(fn, r, min(n, r + step)) for r in range(0, n, step)]:
        f.result()


_THREADS = int(os.environ.get("AH_IMGOPS_THREADS", "0") or 0) or max(1, min(8, (os.cpu_count() or 1) // 2))
PAR_MIN = 3_000_000                 # values below which threads cost more than they give


def _par(fn, n, rows_per_chunk, work=0):
    """fn(r0, r1) over row ranges covering 0..n. Big jobs run on a few threads (NumPy lets go of the interpreter
    lock inside its loops, so row bands run side by side); each band writes its own rows, nothing is shared."""
    chunks = [(r, min(n, r + rows_per_chunk)) for r in range(0, n, max(1, rows_per_chunk))]
    if len(chunks) <= 1 or _THREADS <= 1 or work < PAR_MIN:
        for r0, r1 in chunks:
            fn(r0, r1)
        return
    if not _POOL:
        from concurrent.futures import ThreadPoolExecutor
        _POOL.append(ThreadPoolExecutor(max_workers=_THREADS))
    for f in [_POOL[0].submit(fn, r0, r1) for r0, r1 in chunks]:
        f.result()


# ---------------------------------------------------------------- opening and saving pictures
def _pil_to_cv(im, mode):
    """mode: "color" (BGR uint8), "gray" (uint8), "unchanged" (gray, BGR, BGRA, or 16-bit as stored)."""
    if mode == "gray":
        if im.mode in ("I;16", "I;16B", "I;16L", "I"):
            a = np.asarray(im, dtype=np.uint32 if im.mode == "I" else np.uint16)
            im = Image.fromarray((a >> 8).astype(np.uint8)) if a.dtype == np.uint16 else im.convert("L")
            return np.asarray(im)
        if im.mode in ("L", "1"):
            return np.asarray(im.convert("L")).copy()
        rgb = np.asarray(im.convert("RGB")).astype(np.uint32)
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        if im.format == "PNG":                      # libpng's own grey (OpenCV asks libpng for it): truncated
            y = (r * 9797 + g * 19234 + b * 3737) >> 15
            return np.where((r == g) & (g == b), r, y).astype(np.uint8)
        return ((b * 1868 + g * 9617 + r * 4899 + 8192) >> 14).astype(np.uint8)   # OpenCV's decoders' grey
    if mode == "color":
        if im.mode in ("I;16", "I;16B", "I;16L"):
            a = (np.asarray(im, dtype=np.uint16) >> 8).astype(np.uint8)
            return np.ascontiguousarray(np.repeat(a[:, :, None], 3, axis=2))
        if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            return np.ascontiguousarray(np.asarray(im)[:, :, 2::-1])   # OpenCV IMREAD_COLOR drops alpha
        im = im if im.mode == "RGB" else im.convert("RGB")
        return np.frombuffer(im.tobytes("raw", "BGR"), np.uint8).reshape(im.height, im.width, 3).copy()
    # unchanged
    if im.mode in ("I;16", "I;16B", "I;16L"):
        return np.asarray(im, dtype=np.uint16).copy()
    if im.mode == "L":
        return np.asarray(im).copy()
    if im.mode == "1":
        return (np.asarray(im).astype(np.uint8) * 255)
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        a = np.asarray(im.convert("RGBA"))
        return np.ascontiguousarray(a[:, :, [2, 1, 0, 3]])
    return np.ascontiguousarray(np.asarray(im.convert("RGB"))[:, :, ::-1])


def _open(data, orient=True):
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return None
    fmt = im.format
    if orient:                                  # OpenCV turns pictures by their EXIF orientation, except UNCHANGED
        try:
            from PIL import ImageOps
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass
    im.format = fmt
    return im


def imdecode(data, mode="color"):
    data = bytes(data)
    if mode == "gray" and data[:3] == b"\xff\xd8\xff":    # JPEG: libjpeg makes the grey itself, as OpenCV has it do
        try:
            im = Image.open(io.BytesIO(data))
            im.draft("L", im.size)
            im = im.convert("L")
            from PIL import ImageOps
            return np.asarray(ImageOps.exif_transpose(im)).copy()
        except Exception:
            return None
    im = _open(data, orient=mode != "unchanged")
    return None if im is None else _pil_to_cv(im, mode)


def imread(path, mode="color"):
    with open(path, "rb") as f:
        return imdecode(f.read(), mode)


def imencode_png(arr):
    """PNG bytes of a gray, BGR or BGRA array."""
    if arr.ndim == 3 and arr.shape[2] == 3:
        im = Image.fromarray(np.ascontiguousarray(arr[:, :, ::-1]))
    elif arr.ndim == 3 and arr.shape[2] == 4:
        im = Image.fromarray(np.ascontiguousarray(arr[:, :, [2, 1, 0, 3]]))
    else:
        im = Image.fromarray(arr)
    buf = io.BytesIO()
    im.save(buf, format="PNG", compress_level=1)
    return buf.getvalue()


def imwrite_png(path, arr):
    with open(path, "wb") as f:
        f.write(imencode_png(arr))
    return True

# ---------------------------------------------------------------- colour, borders, scaling
def bgr2gray(bgr):
    """OpenCV's fixed-point grey: (B*3735 + G*19235 + R*9798 + 16384) >> 15."""
    H = bgr.shape[0]
    out = np.empty(bgr.shape[:2], np.uint8)
    if _C is not None:
        src = np.ascontiguousarray(bgr)
        W = src.shape[1]
        _cpar(lambda r0, r1: _C.gray_bgr(_p(src) + r0 * W * 3, (r1 - r0) * W, _p(out) + r0 * W), H, W)
        return out

    def band(r0, r1):
        x = bgr[r0:r1].reshape(-1, 3)
        acc = np.empty(x.shape[0], np.uint32)
        tmp = np.empty_like(acc)
        np.multiply(x[:, 0], 3735, out=acc, dtype=np.uint32)
        np.multiply(x[:, 1], 19235, out=tmp, dtype=np.uint32)
        acc += tmp
        np.multiply(x[:, 2], 9798, out=tmp, dtype=np.uint32)
        acc += tmp
        acc += 16384
        acc >>= 15
        out[r0:r1] = acc.reshape(r1 - r0, -1)
    _par(band, H, max(8, 1_000_000 // max(1, bgr.shape[1])), bgr.size)
    return out


def rgb2gray(rgb):
    return bgr2gray(rgb[:, :, ::-1])


def gray2bgr(g):
    return np.ascontiguousarray(np.repeat(g[:, :, None], 3, axis=2))


def swap_rb(img):
    return np.ascontiguousarray(img[:, :, ::-1])


def border(img, n, value=255):
    """A constant border n pixels wide on every side (cv2.copyMakeBorder, BORDER_CONSTANT)."""
    pad = ((n, n), (n, n)) + (((0, 0),) if img.ndim == 3 else ())
    return np.pad(img, pad, mode="constant", constant_values=value)


def scale_abs(arr, alpha):
    """cv2.convertScaleAbs: |arr * alpha| rounded half to even, held to 0..255."""
    return np.clip(np.rint(np.abs(arr.astype(np.float64) * alpha)), 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- resizing (OpenCV's fixed-point arithmetic)
_COEF_BITS = 11
SIMD_LANES = 8          # OpenCV's 16-bit lanes in one vector (8 for 128-bit SSE builds)
_COEF_SCALE = 1 << _COEF_BITS


def _cubic_coeffs(x):
    A = np.float32(-0.75)
    x = x.astype(np.float32)
    one = np.float32(1)
    c0 = ((A * (x + one) - np.float32(5) * A) * (x + one) + np.float32(8) * A) * (x + one) - np.float32(4) * A
    c1 = ((A + np.float32(2)) * x - (A + np.float32(3))) * x * x + one
    c2 = ((A + np.float32(2)) * (one - x) - (A + np.float32(3))) * (one - x) * (one - x) + one
    c3 = one - c0 - c1 - c2
    return np.stack([c0, c1, c2, c3], axis=1)


def _axis_table(src_n, dst_n, scale, cubic, hold_ends=True):
    """For each output index: the source indices (border replicated) and the fixed-point weights."""
    d = np.arange(dst_n, dtype=np.float64)
    f = ((d + 0.5) * scale - 0.5).astype(np.float32)
    s = np.floor(f).astype(np.int64)
    f = (f - s.astype(np.float32)).astype(np.float32)
    if cubic:
        k, k2 = 4, 2
        w = _cubic_coeffs(f)
    else:
        k, k2 = 2, 1
        lo = (s < 0) & hold_ends          # OpenCV holds the ends this way across a row only, not down the columns
        f[lo], s[lo] = 0, 0
        hi = (s >= src_n - 1) & hold_ends
        f[hi], s[hi] = 0, src_n - 1
        w = np.stack([np.float32(1) - f, f], axis=1)
    idx = s[:, None] + np.arange(k)[None, :] - k2 + 1
    idx = np.clip(idx, 0, src_n - 1)
    iw = np.rint(w.astype(np.float32) * np.float32(_COEF_SCALE)).astype(np.int64)
    return idx, iw


def _hpass(a, xi, xw, w, nw, fx, dt=np.int32):
    """Horizontal pass: int32 sums of source pixels times fixed-point weights. Whole-number enlargements use the
    repeating pattern of weights (shifted slices); others gather columns."""
    k = xi.shape[1]
    p = int(round(fx)) if fx else 0
    if p >= 2 and abs(fx - p) < 1e-12 and nw == w * p and w >= 16:
        j0 = w // 2                           # a column far from both edges: its taps are not held to the edge
        off = np.stack([xi[p * j0 + ph] - j0 for ph in range(p)])
        L = int(max(0, -off.min()))
        R = int(max(0, off.max()))
        P = np.pad(a, ((0, 0), (L, R), (0, 0)), mode="edge")
        out = np.empty((a.shape[0], nw, a.shape[2]), dt)

        def band(r0, r1):
            src = P[r0:r1].astype(dt)
            acc = np.empty((r1 - r0, w, a.shape[2]), dt)
            tmp = np.empty_like(acc)
            for ph in range(p):
                for t in range(k):
                    o = int(off[ph, t]) + L
                    if t == 0:
                        np.multiply(src[:, o:o + w, :], dt(xw[ph, t]), out=acc)
                    else:
                        np.multiply(src[:, o:o + w, :], dt(xw[ph, t]), out=tmp)
                        acc += tmp
                out[r0:r1, ph::p, :] = acc
        _par(band, a.shape[0], max(8, 1_000_000 // max(1, w * a.shape[2])), out.size)
        return out
    hz = np.empty((a.shape[0], nw, a.shape[2]), dt)

    def band(r0, r1):
        acc = np.take(a[r0:r1], xi[:, 0], axis=1).astype(dt) * xw[None, :, 0, None].astype(dt)
        for t in range(1, k):
            acc += np.take(a[r0:r1], xi[:, t], axis=1).astype(dt) * xw[None, :, t, None].astype(dt)
        hz[r0:r1] = acc
    _par(band, a.shape[0], max(8, 1_000_000 // max(1, nw * a.shape[2])), hz.size)
    return hz


def _keys(t):
    t = np.abs(t)
    A = -0.75
    return np.where(t <= 1, ((A + 2) * t - (A + 3)) * t * t + 1, np.where(t < 2, ((A * t - 5 * A) * t + 8 * A) * t - 4 * A, 0.0))


def _cubic_float(img, fx, fy, nw, nh):
    """Enlarging or shrinking by a factor the sizes don't divide evenly: OpenCV hands this to Intel's library, which
    places pixels by the exact factor and sums in float. Same here: rows first, then columns, float32, rounded."""
    h, w = img.shape[:2]
    a = (img if img.ndim == 3 else img[:, :, None]).astype(np.float32)

    def tab(n_src, n_dst, f):
        x = (np.arange(n_dst, dtype=np.float64) + 0.5) / f - 0.5
        s = np.floor(x).astype(np.int64)
        fr = x - s
        idx = np.clip(s[:, None] + np.arange(-1, 3)[None, :], 0, n_src - 1)
        wts = np.stack([_keys(fr + 1), _keys(fr), _keys(1 - fr), _keys(2 - fr)], 1).astype(np.float32)
        return idx, wts
    xi, xw = tab(w, nw, fx)
    yi, yw = tab(h, nh, fy)
    hz = sum(np.take(a, xi[:, k], axis=1) * xw[None, :, k, None] for k in range(4))
    out = sum(np.take(hz, yi[:, k], axis=0) * yw[:, k, None, None] for k in range(4))
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return out[:, :, 0] if img.ndim == 2 else out


def _vcubic(hz, yi, yw, h, nh, nw, cn, fy):
    """OpenCV's cubic vertical step for uint8: its vector loop does the first (row width // SIMD_LANES) * SIMD_LANES
    values of each row in float (rounded half to even); the rest of the row takes the fixed-point path."""
    width = nw * cn
    n = (width // SIMD_LANES) * SIMD_LANES
    flat = hz.reshape(h, width)
    out = np.empty((nh, width), np.uint8)
    sc = np.float32(1.0 / (_COEF_SCALE * _COEF_SCALE))
    bf = (yw.astype(np.float32) * sc).astype(np.float32)
    if n:
        hf = flat[:, :n]
        p = int(round(fy)) if fy else 0
        if p >= 2 and abs(fy - p) < 1e-12 and nh == h * p and h >= 16:
            j0 = h // 2
            off = np.stack([yi[p * j0 + ph] - j0 for ph in range(p)])
            L, R = int(max(0, -off.min())), int(max(0, off.max()))
            P = np.pad(hf, ((L, R), (0, 0)), mode="edge")

            def band(r0, r1):
                acc = np.empty((r1 - r0, n), np.float32)
                tmp = np.empty_like(acc)
                for ph in range(p):
                    b = bf[p * j0 + ph]
                    o = [int(off[ph, t]) + L for t in range(4)]
                    np.multiply(P[o[3] + r0:o[3] + r1], b[3], out=acc)
                    for t in (2, 1, 0):
                        np.multiply(P[o[t] + r0:o[t] + r1], b[t], out=tmp)
                        np.add(tmp, acc, out=acc)
                    np.rint(acc, out=acc)
                    np.clip(acc, 0, 255, out=acc)
                    out[p * r0 + ph:p * r1:p, :n] = acc
            _par(band, h, max(8, 1_000_000 // max(1, n)), out.size)
        else:
            def band(r0, r1):
                acc = np.take(hf, yi[r0:r1, 3], axis=0) * bf[r0:r1, 3, None]
                for t in (2, 1, 0):
                    acc = np.take(hf, yi[r0:r1, t], axis=0) * bf[r0:r1, t, None] + acc
                out[r0:r1, :n] = np.clip(np.rint(acc), 0, 255)
            _par(band, nh, max(8, 1_000_000 // max(1, n)), out.size)
    if n < width:
        tail = flat[:, n:].astype(np.int32)
        acc = sum(np.take(tail, yi[:, t], axis=0) * yw[:, t, None].astype(np.int32) for t in range(4))
        out[:, n:] = np.clip((acc + np.int32(1 << (2 * _COEF_BITS - 1))) >> (2 * _COEF_BITS), 0, 255)
    return out.reshape(nh, nw, cn)


def resize(img, size=None, fx=None, fy=None, cubic=False):
    """cv2.resize with INTER_LINEAR (cubic=False) or INTER_CUBIC, uint8 in and out. size is (width, height)."""
    h, w = img.shape[:2]
    if size:
        nw, nh = int(size[0]), int(size[1])
        sx, sy = 1.0 / (nw / w), 1.0 / (nh / h)
        fxx = fyy = None
    else:
        fyy = fy or fx
        nw, nh = int(round(w * fx)), int(round(h * fyy))
        sx, sy = 1.0 / fx, 1.0 / fyy
        fxx = fx
    if nw == w and nh == h:
        return img.copy()
    if cubic and not (fxx and fxx == int(fxx) and fyy == fxx and nw == w * int(fxx) and nh == h * int(fxx)):
        return _cubic_float(img, fxx or nw / w, fyy or nh / h, nw, nh)   # OpenCV hands these to Intel's library
    xi, xw = _axis_table(w, nw, sx, cubic)
    yi, yw = _axis_table(h, nh, sy, cubic, hold_ends=False)
    a = img if img.ndim == 3 else img[:, :, None]
    cn = a.shape[2]
    if _C is not None:
        src = np.ascontiguousarray(a)
        out = np.empty((nh, nw, cn), np.uint8)
        t = [np.ascontiguousarray(v, dtype=np.int32) for v in (xi, xw, yi, yw)]
        k = xi.shape[1]
        bad = []

        def band(r0, r1):
            if _C.resize_fixed(_p(src), h, w, cn, _p(out) + r0 * nw * cn, r1 - r0, nw, k, _p(t[0]), _p(t[1]),
                               _p(t[2]) + r0 * k * 4, _p(t[3]) + r0 * k * 4, int(cubic), SIMD_LANES):
                bad.append(r0)
        _cpar(band, nh, nw * cn)
        if bad:
            raise MemoryError("resize")
        return out[:, :, 0] if img.ndim == 2 else out
    if nh < h:                                  # shrinking: only the source rows the output uses go through the row pass
        need, inv = np.unique(yi, return_inverse=True)
        a = a[need]
        yi = inv.reshape(yi.shape)
    hz = _hpass(a, xi, xw, w, nw, fxx, np.float32 if cubic else np.int32)   # float32 holds these sums exactly
    h = a.shape[0] if nh < h else h
    if cubic:
        out = _vcubic(hz, yi, yw, h, nh, nw, cn, fyy)
    else:
        out = np.empty((nh, nw, cn), np.uint8)

        def band(r0, r1):                      # OpenCV's linear vertical step: rows shifted by 4, high 16 bits kept
            b0 = yw[r0:r1, 0, None, None].astype(np.int32)
            b1 = yw[r0:r1, 1, None, None].astype(np.int32)
            s0 = np.take(hz, yi[r0:r1, 0], axis=0) >> 4
            s1 = np.take(hz, yi[r0:r1, 1], axis=0) >> 4
            out[r0:r1] = np.clip((((s0 * b0) >> 16) + ((s1 * b1) >> 16) + 2) >> 2, 0, 255)
        _par(band, nh, max(8, 1_000_000 // max(1, nw * cn)), out.size)
    return out[:, :, 0] if img.ndim == 2 else out

# ---------------------------------------------------------------- contrast (CLAHE, as OpenCV computes it)
def clahe(gray, clip=2.0, tiles=(8, 8)):
    tx, ty = tiles
    H, W = gray.shape
    if W % tx == 0 and H % ty == 0:
        Hp, Wp = H, W
    else:
        Hp, Wp = H + ty - H % ty, W + tx - W % tx            # OpenCV mirrors the picture out to whole tiles
    th, tw = Hp // ty, Wp // tx
    area = th * tw
    lut_scale = np.float32(255) / np.float32(area)
    limit = max(int(clip * area / 256), 1) if clip > 0 else 0
    if _C is not None:
        src = np.ascontiguousarray(gray)
        hist32 = np.empty((ty, tx, 256), np.int32)
        _cpar(lambda a, b: _C.clahe_hist(_p(src), H, W, Hp, Wp, th, tw, tx, _p(hist32), a, b), ty, th * Wp)
        hist = hist32.reshape(ty * tx, 256).astype(np.int64)
    else:
        ext = gray if (Hp, Wp) == (H, W) else np.pad(gray, ((0, Hp - H), (0, Wp - W)), mode="reflect")
        # every tile's histogram in one count: tile number * 256 + grey level
        tyi = (np.arange(Hp) // th)[:, None] * tx
        txi = (np.arange(Wp) // tw)[None, :]
        hist = np.bincount(((tyi + txi) * 256 + ext).ravel(), minlength=tx * ty * 256).reshape(ty * tx, 256).astype(np.int64)
    if limit > 0:
        clipped = np.maximum(hist - limit, 0).sum(axis=1)
        hist = np.minimum(hist, limit)
        batch, residual = clipped // 256, clipped % 256
        hist += batch[:, None]
        step = np.maximum(256 // np.maximum(residual, 1), 1)
        i = np.arange(256)[None, :]
        hist += ((i % step[:, None] == 0) & (i // step[:, None] < residual[:, None])).astype(np.int64)
    cs = np.cumsum(hist, axis=1).astype(np.float32)
    luts = np.clip(np.rint(cs * lut_scale), 0, 255).astype(np.float32).reshape(ty, tx, 256)
    inv_tw, inv_th = np.float32(1) / np.float32(tw), np.float32(1) / np.float32(th)
    xs = np.arange(W, dtype=np.float32) * inv_tw - np.float32(0.5)
    x1 = np.floor(xs).astype(np.int64)
    xa = (xs - x1.astype(np.float32)).astype(np.float32)
    xa1 = (np.float32(1) - xa).astype(np.float32)
    x2 = np.minimum(x1 + 1, tx - 1)
    x1 = np.maximum(x1, 0)
    ys = np.arange(H, dtype=np.float32) * inv_th - np.float32(0.5)
    y1 = np.floor(ys).astype(np.int64)
    ya = (ys - y1.astype(np.float32)).astype(np.float32)
    ya1 = (np.float32(1) - ya).astype(np.float32)
    y2 = np.minimum(y1 + 1, ty - 1)
    y1 = np.maximum(y1, 0)
    out = np.empty((H, W), np.uint8)
    if _C is not None:
        src = np.ascontiguousarray(gray)
        lt = np.ascontiguousarray(luts, dtype=np.float32)
        i32 = lambda v: np.ascontiguousarray(v, dtype=np.int32)
        f32 = lambda v: np.ascontiguousarray(v, dtype=np.float32)
        args = [i32(x1), i32(x2), f32(xa), f32(xa1), i32(y1), i32(y2), f32(ya), f32(ya1)]
        def band(r0, r1):
            _C.clahe_blend(_p(src) + r0 * W, r1 - r0, W, tx, _p(lt), _p(args[0]), _p(args[1]), _p(args[2]), _p(args[3]),
                           _p(args[4]) + r0 * 4, _p(args[5]) + r0 * 4, _p(args[6]) + r0 * 4, _p(args[7]) + r0 * 4,
                           _p(out) + r0 * W)
        _cpar(band, H, W)
        return out

    def groups(a1, a2):                    # runs of rows (or columns) that blend the same two tiles
        key = a1 * 1000 + a2
        cut = np.nonzero(np.diff(key))[0] + 1
        b = np.concatenate([[0], cut, [len(key)]])
        return [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1)]
    cols = groups(x1, x2)

    def band(g0, g1):
        for r0, r1 in rgroups[g0:g1]:
            Y1, Y2 = int(y1[r0]), int(y2[r0])
            wa1, wa = ya1[r0:r1, None], ya[r0:r1, None]
            for c0, c1 in cols:
                X1, X2 = int(x1[c0]), int(x2[c0])
                v = gray[r0:r1, c0:c1]
                xa1_, xa_ = xa1[None, c0:c1], xa[None, c0:c1]
                top = luts[Y1, X1].take(v) * xa1_ + luts[Y1, X2].take(v) * xa_
                bot = luts[Y2, X1].take(v) * xa1_ + luts[Y2, X2].take(v) * xa_
                res = top * wa1 + bot * wa
                np.rint(res, out=res)
                np.clip(res, 0, 255, out=res)
                out[r0:r1, c0:c1] = res
    rgroups = groups(y1, y2)
    _par(band, len(rgroups), 1, out.size)
    return out


# ---------------------------------------------------------------- thresholds
def otsu_inv(gray):
    """cv2.threshold(gray, 0, 255, THRESH_BINARY_INV + THRESH_OTSU): (threshold, ink mask 0/255)."""
    h = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    scale = 1.0 / gray.size
    mu = float((np.arange(256) * h).sum()) * scale
    mu1 = q1 = 0.0
    best, t = 0.0, 0
    eps = float(np.finfo(np.float32).eps)
    for i in range(256):
        p = h[i] * scale
        mu1 *= q1
        q1 += p
        q2 = 1.0 - q1
        if min(q1, q2) < eps or max(q1, q2) > 1.0 - eps:
            continue
        mu1 = (mu1 + i * p) / q1
        mu2 = (mu - q1 * mu1) / q2
        sigma = q1 * q2 * (mu1 - mu2) * (mu1 - mu2)
        if sigma > best:
            best, t = sigma, i
    return float(t), np.where(gray > t, 0, 255).astype(np.uint8)


def _box_mean(gray, k):
    """Mean over a k x k window, border replicated, rounded to uint8 (cv2.boxFilter on uint8)."""
    r = k // 2
    H, W = gray.shape
    p = np.pad(gray, r, mode="edge")
    c = np.zeros((p.shape[0], p.shape[1] + 1), np.int32)
    np.cumsum(p, axis=1, dtype=np.int32, out=c[:, 1:])
    rows = c[:, k:k + W] - c[:, 0:W]                      # k-wide sums along each row
    c2 = np.zeros((rows.shape[0] + 1, W), np.int32)
    np.cumsum(rows, axis=0, dtype=np.int32, out=c2[1:])
    s = c2[k:k + H] - c2[0:H]
    return np.rint(s * (1.0 / (k * k))).astype(np.int32)


def adaptive_mean_inv(gray, block=15, c=10):
    """cv2.adaptiveThreshold(gray, 255, ADAPTIVE_THRESH_MEAN_C, THRESH_BINARY_INV, block, c).
    OpenCV marks a pixel when pixel - round(window sum / block^2) <= -c. With n = pixel + c that is
    round(sum / area) >= n, which (no ties: area is odd) is 2 * sum >= area * (2n - 1): whole numbers only."""
    d = int(np.floor(c))
    k = block
    r = k // 2
    H, W = gray.shape
    area = k * k
    if _C is not None:
        src = np.ascontiguousarray(gray)
        out = np.empty((H, W), np.uint8)
        thr = np.ascontiguousarray(area * (np.arange(256, dtype=np.int64) + d) - (area - 1) // 2)
        bad = []
        _cpar(lambda r0, r1: _C.adaptive_mean_inv(_p(src), H, W, k, _p(thr), _p(out), r0, r1) and bad.append(r0), H, W)
        if bad:
            raise MemoryError("adaptive threshold")
        return out
    small = 255 * area < 65536          # window sums fit 16 bits: running sums may wrap, differences stay right
    dt = np.uint16 if small else np.int64
    p = np.pad(gray, r, mode="edge")
    c1 = np.zeros((p.shape[0], p.shape[1] + 1), dt)
    np.cumsum(p, axis=1, dtype=dt, out=c1[:, 1:])
    rows = c1[:, k:k + W] - c1[:, 0:W]
    cs = np.zeros((H + 2 * r + 1, W), dt)
    np.cumsum(rows, axis=0, dtype=dt, out=cs[1:])
    win = cs[k:k + H] - cs[0:H]
    # marked when round(win / area) >= g + c, that is win >= area * (g + c) - (area - 1) / 2 (area is odd: no ties)
    thr = np.clip(area * (np.arange(256) + d) - (area - 1) // 2, 0, 65535 if small else None).astype(dt)
    return (win >= thr.take(gray)).view(np.uint8) * np.uint8(255)


# ---------------------------------------------------------------- shapes (morphology on 0/non-zero pictures)
def _run_any(on, k, axis):
    """True where any of the k cells starting k//2 before (OpenCV's anchor) is on, along axis."""
    a = k // 2
    if k <= 5:                                            # small windows: shifted copies
        n = on.shape[axis]
        pad = [(0, 0), (0, 0)]
        pad[axis] = (a, k - 1 - a)
        p = np.pad(on, pad)
        out = np.zeros_like(on)
        for i in range(k):
            out |= p[i:i + n, :] if axis == 0 else p[:, i:i + n]
        return out
    n = on.shape[axis]
    shape = list(on.shape)
    shape[axis] = n + k
    c = np.zeros(shape, np.int32)
    pad = [(0, 0), (0, 0)]
    pad[axis] = (a, k - 1 - a)
    if axis == 0:
        np.cumsum(np.pad(on, pad), axis=0, dtype=np.int32, out=c[1:])
        return (c[k:k + n] - c[0:n]) > 0
    np.cumsum(np.pad(on, pad), axis=1, dtype=np.int32, out=c[:, 1:])
    return (c[:, k:k + n] - c[:, 0:n]) > 0


def erode(img, kw, kh):
    """cv2.erode with a kw x kh rectangle of a picture whose pixels are 0 or one other value."""
    if kw == 3 and kh == 3 and _C is not None and img.dtype == np.uint8 and img.ndim == 2:
        src = np.ascontiguousarray(img)
        out = np.empty_like(src)
        H, W = src.shape
        on = int(src.max()) if src.size else 0
        _cpar(lambda r0, r1: _C.erode3(_p(src), H, W, on, _p(out), r0, r1), H, W)
        return out
    on = img > 0
    off = ~on
    if kw > 1:
        off = _run_any(off, kw, 1)
    if kh > 1:
        off = _run_any(off, kh, 0)
    return np.where(off, 0, img.max() if img.size else 0).astype(img.dtype)


def dilate(img, kw, kh):
    if kw == 3 and kh == 3 and _C is not None and img.dtype == np.uint8 and img.ndim == 2:
        src = np.ascontiguousarray(img)
        out = np.empty_like(src)
        H, W = src.shape
        on = int(src.max()) if src.size else 0
        _cpar(lambda r0, r1: _C.dilate3(_p(src), H, W, on, _p(out), r0, r1), H, W)
        return out
    on = img > 0
    if kw > 1:
        on = _run_any(on, kw, 1)
    if kh > 1:
        on = _run_any(on, kh, 0)
    return np.where(on, img.max() if img.size else 0, 0).astype(img.dtype)


def _open_line(on, k, axis):
    """Opening by a straight k-cell line along axis (OpenCV's anchor k//2 for both steps, outside counted as on for
    the erosion and off for the dilation): keeps whole runs at least k long (k - k//2 when touching the start edge,
    k//2 + 1 when touching the end edge, any length when touching both); with an even k the kept run sits one
    cell further on, as OpenCV's leaves it."""
    m = on if axis == 1 else on.T
    H, W = m.shape
    r, s, e = _runs(m)
    a = k // 2
    ln = e - s
    need = np.full(ln.shape, k)
    at_start, at_end = s == 0, e == W
    need = np.where(at_start, k - a, need)
    need = np.where(at_end, a + 1, need)
    need = np.where(at_start & at_end, 0, need)
    keep = ln >= need
    sh = 2 * a - k + 1                                    # 0 for odd k; even k moves the kept run one cell on
    s2 = np.where(at_start, 0, np.minimum(s + sh, W))[keep]
    e2 = np.where(at_end, W, np.minimum(e + sh, W))[keep]
    d = np.zeros((H, W + 1), np.int8)
    d[r[keep], s2] = 1                                    # kept runs never share a start or an end cell
    d[r[keep], e2] = -1
    out = np.cumsum(d, axis=1, dtype=np.int8)[:, :W] > 0
    return out if axis == 1 else out.T


def open_(img, kw, kh):
    if (kh == 1 and kw > 5 or kw == 1 and kh > 5) and _C is not None:
        src = np.ascontiguousarray(img, dtype=np.uint8)
        out = np.empty_like(src)
        H, W = src.shape
        axis, on = (1 if kh == 1 else 0), (int(src.max()) if src.size else 0)
        _cpar(lambda l0, l1: _C.open_line(_p(src), H, W, kw if kh == 1 else kh, axis, on, _p(out), l0, l1),
              H if axis == 1 else W, W if axis == 1 else H)
        return out.astype(img.dtype, copy=False)
    if kh == 1 and kw > 5 or kw == 1 and kh > 5:          # a straight line: whole runs, no sliding window
        on = _open_line(img > 0, kw if kh == 1 else kh, 1 if kh == 1 else 0)
        return np.where(on, img.max() if img.size else 0, 0).astype(img.dtype)
    return dilate(erode(img, kw, kh), kw, kh)


# ---------------------------------------------------------------- outer shapes and their boxes (findContours + boundingRect)
def _runs(mask):
    """Runs of True in each row: arrays (row, start, end exclusive), row by row, left to right."""
    m = mask.astype(np.int8)
    p = np.zeros((m.shape[0], m.shape[1] + 2), np.int8)
    p[:, 1:-1] = m
    d = np.diff(p, axis=1)
    rs, cs = np.nonzero(d == 1)
    _re, ce = np.nonzero(d == -1)
    return rs, cs, ce


def _label_runs(rows, starts, ends, width, eight):
    """Component id for each run: runs touching between neighbouring rows join (8-connected when eight, else 4).
    Vectorised: the touching pairs come from sorted keys, then labels settle by taking minimums and jumping."""
    n = len(rows)
    if n == 0:
        return np.zeros(0, np.int64)
    g = 1 if eight else 0
    stride = width + 2
    S = rows * stride + starts
    E = rows * stride + ends
    lo = np.searchsorted(E, (rows - 1) * stride + starts - g, side="right")
    hi = np.searchsorted(S, (rows - 1) * stride + ends + g, side="left")
    cnt = np.maximum(hi - lo, 0)
    a = np.repeat(np.arange(n), cnt)
    b = np.repeat(lo, cnt) + (np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    lab = np.arange(n)
    while len(a):
        la, lb = lab[a], lab[b]
        diff = la != lb
        if not diff.any():
            break
        la, lb = la[diff], lb[diff]
        m = np.minimum(la, lb)
        np.minimum.at(lab, la, m)                             # each root joins the smaller root it touches
        np.minimum.at(lab, lb, m)
        while True:                                           # then every run jumps to its root
            nxt = lab[lab]
            if np.array_equal(nxt, lab):
                break
            lab = nxt
    return lab


def outer_boxes(mask):
    """(x, y, w, h) of every outer shape (8-connected) of a 0/non-zero picture, leaving out shapes that sit inside
    another shape's hole: what cv2.findContours(RETR_EXTERNAL) and cv2.boundingRect give, as a sorted list."""
    on = mask > 0
    H, W = on.shape
    if not on.any():
        return []
    if _C is not None:
        src = np.ascontiguousarray(on, dtype=np.uint8)
        cap = 4096
        while True:
            buf = np.empty((cap, 4), np.int32)
            n = _C.outer_boxes(_p(src), H, W, _p(buf), cap)
            if n == -2:
                cap *= 4
                continue
            if n < 0:
                raise MemoryError("outer boxes")
            return sorted(tuple(int(v) for v in b) for b in buf[:n])
    r, s, e = _runs(on)
    lab = _label_runs(r, s, e, W, eight=True)
    # background reachable from outside the picture (4-connected), with a one-pixel frame of background around it
    bg = np.ones((H + 2, W + 2), bool)
    bg[1:-1, 1:-1] = ~on
    br, bs, be = _runs(bg)
    blab = _label_runs(br, bs, be, W + 2, eight=False)
    keep = blab == blab[0]                                 # the first run is the top frame row
    d = np.zeros((H + 2, W + 3), np.int8)
    np.add.at(d, (br[keep], bs[keep]), 1)
    np.add.at(d, (br[keep], be[keep]), -1)
    out_mask = np.cumsum(d, axis=1)[:, :W + 2] > 0
    # a pixel touches the outside when the pixel straight above, below, left or right of it is outside
    touch = out_mask[:-2, 1:-1] | out_mask[2:, 1:-1] | out_mask[1:-1, :-2] | out_mask[1:-1, 2:]
    c = np.zeros((H, W + 1), np.int32)
    np.cumsum(touch, axis=1, dtype=np.int32, out=c[:, 1:])
    run_touch = (c[r, e] - c[r, s]) > 0
    n = lab.max() + 1
    x0 = np.full(n, W, np.int64); y0 = np.full(n, H, np.int64)
    x1 = np.full(n, -1, np.int64); y1 = np.full(n, -1, np.int64)
    np.minimum.at(x0, lab, s); np.maximum.at(x1, lab, e - 1)
    np.minimum.at(y0, lab, r); np.maximum.at(y1, lab, r)
    outer = np.zeros(n, bool)
    np.logical_or.at(outer, lab, run_touch)
    ids = np.nonzero(outer & (x1 >= 0))[0]
    return sorted((int(x0[i]), int(y0[i]), int(x1[i] - x0[i] + 1), int(y1[i] - y0[i] + 1)) for i in ids)
