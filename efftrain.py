"""The effort is the training packet (3.76.0): every fix made in the moment saves a training sample.

A misread fixed, a find that is not text, a part of a longer term, a term the scan missed: each quietly adds one line to
training_samples.json in the effort's working folder (the app data folder), so the samples travel with the effort's
folder, its package and Add to this effort. No one makes a training pack. The Training app's Learn from an effort...
reads them; the same sample twice counts once (each has an id from its content).
The samples hold the text read, the right text, the place it was found and when; the place names a customer document,
so they follow the handling of the effort's folder. Rules only (No AI); nothing leaves the PC."""
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


def add(s, kind, read, right="", places=(), crop=""):
    """One sample for the effort of session s (no effort: nothing is kept). Returns the sample or None."""
    root = _root(s)
    if not root or getattr(s, "effort", None) is None or kind not in KINDS:
        return None
    where = str((list(places) or [""])[0])
    x = {"id": sample_id(kind, read, right, where), "kind": kind, "read": read or "", "right": right or "", "where": where,
         "crop": crop or "", "when": datetime.datetime.now().isoformat(timespec="seconds")}
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


def learn(roots, have=()):
    """Learn from an effort: the samples of the effort folders in roots that are not in have (ids). Returns [sample]."""
    seen, out = set(have), []
    for root in roots:
        for x in load(root):
            if x.get("id") and x["id"] not in seen:
                seen.add(x["id"])
                out.append(dict(x, effort=os.path.basename(os.path.normpath(root))))
    return out
