"""The scan's readings of each picture, kept with the effort (3.80.0, acronym review decision 7: a faster preview).

Every picture the scan reads keeps its readings (each line's box in the picture's own pixels, the text, the confidence
and how it was read) in picture_readings.json in the effort's working folder, keyed by the picture's pixels (so the
same picture inside a Word file, a PowerPoint file or as an image file is one entry). The preview draws them instead of
reading the picture again, after a restart too. A picture the preview reads itself (a PDF page the scan read as typed
text) is added the same way. The readings are text read from customer documents and follow the handling of the
effort's folder.

use(folder)         the effort's working folder (the session sets it; None: nothing is kept)
key_of(pil)         a picture's key from its pixels
get(key) / put(key, readings) / flush()
Rules only (No AI); nothing leaves the PC."""
import hashlib, json, os, threading

FILE = "picture_readings.json"
FORMAT = 1
MOST = 4000                                  # pictures kept per effort; the oldest go first

_lock = threading.Lock()
_state = {"folder": None, "rows": None, "dirty": False}


def use(folder):
    """Readings are kept in folder from now on (flushing the effort before)."""
    with _lock:
        if _state["folder"] == folder:
            return
    flush()
    with _lock:
        _state.update(folder=folder, rows=None, dirty=False)


def active():
    return bool(_state["folder"])


def key_of(pil):
    im = pil.convert("RGB")
    h = hashlib.sha1(f"{im.width}x{im.height}:".encode())
    h.update(im.tobytes())
    return h.hexdigest()


def key_of_bytes(image_bytes):
    """The pixel key of encoded picture bytes; '' when they cannot be decoded here."""
    try:
        import io
        from PIL import Image
        return key_of(Image.open(io.BytesIO(image_bytes)))
    except Exception:                       # noqa: BLE001  not a picture PIL can open (the reader may still read it)
        return ""


def _load():
    if _state["rows"] is None:
        rows = {}
        p = os.path.join(_state["folder"], FILE) if _state["folder"] else ""
        if p and os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, dict) and int(d.get("format", 0)) <= FORMAT:
                    rows = dict(d.get("pictures") or {})
            except (OSError, ValueError):
                import diag
                diag.swallowed()
        _state["rows"] = rows
    return _state["rows"]


def get(key):
    """[((x0, y0, x1, y1), text, confidence, how)] or None."""
    if not key or not _state["folder"]:
        return None
    with _lock:
        r = _load().get(key)
    if r is None:
        return None
    return [((a[0], a[1], a[2], a[3]), a[4], float(a[5]), a[6] if len(a) > 6 else "read") for a in r]


def put(key, readings):
    if not key or not _state["folder"]:
        return False
    rows_ = [[round(float(b[0]), 1), round(float(b[1]), 1), round(float(b[2]), 1), round(float(b[3]), 1), str(t), round(float(c), 3),
              str(how)] for b, t, c, how in readings]
    with _lock:
        rows = _load()
        rows.pop(key, None)
        rows[key] = rows_
        while len(rows) > MOST:
            rows.pop(next(iter(rows)))
        _state["dirty"] = True
    return True


def flush():
    with _lock:
        if not _state["dirty"] or not _state["folder"] or _state["rows"] is None:
            return False
        p = os.path.join(_state["folder"], FILE)
        tmp = p + ".tmp"
        try:
            os.makedirs(_state["folder"], exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"format": FORMAT, "pictures": _state["rows"]}, f)
            os.replace(tmp, p)
            _state["dirty"] = False
            return True
        except OSError:
            import diag
            diag.swallowed()
            return False
