"""The effort is the training packet (3.76.0): every fix made in the moment saves a training sample.

A misread fixed, a find that is not text, a part of a longer term, a term the scan missed: each quietly adds one line to
training_samples.json in the effort's working folder (the app data folder), so the samples travel with the effort's
folder, its package and Add to this effort. No one makes a training pack. The Training app's Learn from an effort...
reads them; the same sample twice counts once (each has an id from its content).
The samples hold the text read, the right text, the place it was found and when, and (3.80.0) the picture's part
as a PNG in training_crops; the crops are customer content and follow the handling of the effort's folder. Rules only (No AI); nothing leaves the PC."""
import datetime, hashlib, os
import workspace as W

FILE = "training_samples.json"
FORMAT = 1
KINDS = ("misread", "not text", "part", "missed")


def path_of(root):
    return os.path.join(root, FILE)


def _root(s):
    ws = getattr(s, "ws", None)
    return getattr(ws, "root", "") if ws is not None else ""


def load(root):
    d = W.read_json(path_of(root), {}) if root else {}
    return list(d.get("samples", [])) if isinstance(d, dict) else []


def sample_id(kind, read, right, where):
    return hashlib.sha1("|".join([kind, read or "", right or "", where or ""]).encode("utf-8")).hexdigest()[:12]


CROPS = "training_crops"


def add(s, kind, read, right="", places=(), crop=None):
    """One sample for the effort of session s (no effort: nothing is kept). crop (3.80.0): the picture's part as a PIL
    image, kept as training_crops/<id>.png beside the samples. Returns the sample or None."""
    root = _root(s)
    if not root or getattr(s, "effort", None) is None or kind not in KINDS:
        return None
    where = str((list(places) or [""])[0])
    sid = sample_id(kind, read, right, where)
    name = ""
    if crop is not None and not isinstance(crop, str):
        try:
            os.makedirs(os.path.join(root, CROPS), exist_ok=True)
            name = f"{CROPS}/{sid}.png"
            crop.save(os.path.join(root, CROPS, f"{sid}.png"), format="PNG")
        except (OSError, ValueError, AttributeError):
            import diag
            diag.swallowed()
            name = ""
    x = {"id": sid, "kind": kind, "read": read or "", "right": right or "", "where": where,
         "crop": name or (crop if isinstance(crop, str) else ""), "when": datetime.datetime.now().isoformat(timespec="seconds")}
    rows = load(root)
    if any(r.get("id") == x["id"] for r in rows):
        return x
    rows.append(x)
    try:
        W.write_json(path_of(root), {"format": FORMAT, "samples": rows})
    except OSError:
        import diag
        diag.swallowed()
        return None
    return x


def learn(roots, have=(), crops_to=""):
    """Learn from an effort: the samples of the effort folders in roots that are not in have (ids). With crops_to, each
    sample's picture crop is copied there (3.80.0) and the sample names the copy. Returns [sample]."""
    import shutil
    seen, out = set(have), []
    for root in roots:
        for x in load(root):
            if x.get("id") and x["id"] not in seen:
                seen.add(x["id"])
                y = dict(x, effort=os.path.basename(os.path.normpath(root)))
                src = os.path.join(root, *x["crop"].split("/")) if x.get("crop") else ""
                if crops_to and src and os.path.isfile(src):
                    try:
                        os.makedirs(crops_to, exist_ok=True)
                        shutil.copy2(src, os.path.join(crops_to, os.path.basename(src)))
                        y["crop"] = os.path.basename(src)
                    except OSError:
                        import diag
                        diag.swallowed()
                out.append(y)
    return out
