"""Watched folders (2.94.0): the effort's Customer Documents folder, and any folder added to the library, are checked
for what changed since the documents were read, subfolders included:

- New: a file no document has (by its contents), not set aside before. Offered to add (prefilled) or set aside
  ("Not these"; a set-aside file comes back only if its contents change).
- Changed: the file a document's latest version was read from now holds other contents. Offered as a new version.
- Missing: the file a document's latest version was read from is gone. The person decides: find it (point at where it
  went), keep the record without the original, or mark the document withdrawn. Until then it is reported every check.

Checked when the effort opens, when the library refreshes, and every few minutes. A file is fingerprinted again only
when its size or time changed. Nothing is added, removed or renamed by a check itself. The state lives in the
effort's app data (watch.json). Standard library plus the effort modules.
"""
import datetime, getpass, os

FILE = "watch.json"
KINDS = (".docx", ".pdf", ".pptx", ".xlsx", ".xls", ".doc", ".txt", ".csv", ".rtf", ".pptm", ".docm", ".xlsm", ".ppt",
         ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp")                         # 2.96.0: pictures


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _key(p):
    return os.path.normcase(os.path.abspath(p))


def load(data_dir):
    import workspace as W
    d = W.read_json(os.path.join(data_dir, FILE), None) or {}
    return {"folders": [f for f in d.get("folders", []) if isinstance(f, dict) and f.get("path")],
            "seen": d.get("seen", {}) if isinstance(d.get("seen"), dict) else {},
            "last": d.get("last", "")}


def save(data_dir, st):
    import workspace as W
    W.write_json(os.path.join(data_dir, FILE), st)


def add_folder(data_dir, path, category="customer", who=None):
    """Watch a folder (and its subfolders). False when it is already watched."""
    st = load(data_dir)
    if any(_key(f["path"]) == _key(path) for f in st["folders"]):
        return False
    st["folders"].append({"path": os.path.abspath(path), "category": category, "added": _now(), "by": who or getpass.getuser()})
    save(data_dir, st)
    return True


def remove_folder(data_dir, path):
    st = load(data_dir)
    n = len(st["folders"])
    st["folders"] = [f for f in st["folders"] if _key(f["path"]) != _key(path)]
    save(data_dir, st)
    return len(st["folders"]) < n


def folders(data_dir, customer_dir=""):
    """[(path, category, built in)]: the Customer Documents folder first, then the ones added."""
    out = []
    if customer_dir:
        out.append((os.path.abspath(customer_dir), "customer", True))
    for f in load(data_dir)["folders"]:
        if not any(_key(f["path"]) == _key(p) for p, _c, _b in out):
            out.append((f["path"], f.get("category", "customer"), False))
    return out


def _skip(name):
    return name.startswith("~$") or name.startswith(".") or name.lower().endswith((".tmp", ".part.pdf"))


def walk(folder, data_dir=""):
    """Every document under the folder, subfolders included; the app's own folders are left out."""
    out = []
    skip_dirs = {_key(data_dir)} if data_dir else set()
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".") and _key(os.path.join(root, d)) not in skip_dirs
                   and not d.endswith((" - app data", "- readable copy (Stationkeeper)")) and "readable copy" not in d.lower()]
        for f in files:
            if not _skip(f) and f.lower().endswith(KINDS):
                out.append(os.path.join(root, f))
    return sorted(out)


def _inside(p, roots):
    k = _key(p)
    return any(k == r or k.startswith(r + os.sep) for r in roots)


def check(lib, data_dir, customer_dir="", sha=None):
    """{"new": [(path, category)], "changed": [(path, doc, version)], "missing": [(doc, version, path)]} for the watched
    folders. Updates the size and time cache (so the next check fingerprints only what changed)."""
    import docversions as DV
    sha = sha or DV.sha256
    st = load(data_dir)
    seen = st["seen"]
    watched = folders(data_dir, customer_dir)
    roots = [_key(p) for p, _c, _b in watched if os.path.isdir(p)]
    shas = {v.get("sha256") for d in lib.all for v in d["versions"]}
    latest = {}                                   # file path -> (doc, version) of each document's latest version
    for d in lib.all:
        if d["versions"]:
            v = d["versions"][-1]
            p = lib.path_of(v)
            if p:
                latest[_key(p)] = (d, v)
    out = {"new": [], "changed": [], "missing": []}
    found = set()
    for folder, cat, _b in watched:
        if not os.path.isdir(folder):
            continue
        for p in walk(folder, data_dir):
            k = _key(p)
            if k in found:
                continue
            found.add(k)
            try:
                s = os.stat(p)
            except OSError:
                continue
            c = seen.get(k) or {}
            if c.get("size") == s.st_size and c.get("mtime") == int(s.st_mtime) and c.get("sha"):
                h = c["sha"]
            else:
                try:
                    h = sha(p)
                except OSError:
                    continue
            seen[k] = {"size": s.st_size, "mtime": int(s.st_mtime), "sha": h, "state": c.get("state", "") if c.get("sha") == h else ""}
            if k in latest:
                d, v = latest[k]
                if h != v.get("sha256") and h not in shas and seen[k]["state"] != "ignored":
                    out["changed"].append((p, d, v))
                continue
            if h in shas or seen[k]["state"] == "ignored":
                continue
            rel = os.path.relpath(os.path.dirname(p), folder).replace(os.sep, "/").strip("./")
            out["new"].append((p, cat or DV.guess_category(rel + "/" + os.path.basename(p), "customer")))
    for k, (d, v) in latest.items():
        if d.get("withdrawn") or v.get("missing_kept"):
            continue
        if k not in found and _inside(k, roots) and not os.path.isfile(k):
            out["missing"].append((d, v, lib.path_of(v)))
    for k in [k for k in seen if k not in found]:            # forget files that are gone (missing documents are in the library)
        seen.pop(k, None)
    st["last"] = _now()
    save(data_dir, st)
    return out


def set_aside(data_dir, paths):
    """'Not these': the files are not offered again unless their contents change."""
    st = load(data_dir)
    for p in paths:
        c = st["seen"].setdefault(_key(p), {})
        c["state"] = "ignored"
    save(data_dir, st)
    return len(paths)


def keep_without_original(lib, rec, doc_id, who=None):
    """The document stays, read text and all, with its original file gone; the check stops asking."""
    d = lib.doc(doc_id)
    if d is None or not d["versions"]:
        return False
    v = d["versions"][-1]
    v["missing_kept"] = {"when": _now(), "who": who or getpass.getuser()}
    lib.save()
    if rec is not None:
        rec.log("document", f"{d['name']}: original file gone; record kept without it", who=who, save=True)
    return True


def mark_withdrawn(lib, rec, doc_id, who=None):
    """The customer withdrew the document: it stays in the library, marked withdrawn, and stops building the matrix."""
    d = lib.doc(doc_id)
    if d is None:
        return False
    d["withdrawn"] = {"when": _now(), "who": who or getpass.getuser()}
    if d.get("role") == "matrix":
        d["role"] = "reference"
    lib.save()
    if rec is not None:
        rec.log("document", f"{d['name']}: marked withdrawn (its file is gone)", who=who, save=True)
    return True


def found_at(lib, rec, doc_id, path, who=None):
    """'Find it': the document's latest version is the file at path now. True when its contents match (the file only
    moved); False when they differ (then it is a new version, added the usual way)."""
    import docversions as DV
    d = lib.doc(doc_id)
    if d is None or not d["versions"] or not os.path.isfile(path):
        return False
    v = d["versions"][-1]
    if DV.sha256(path) != v.get("sha256"):
        return False
    v["path"] = os.path.abspath(path)
    v.pop("rel", None)
    rel = lib._rel(path)
    if rel:
        v["rel"] = rel
    v.pop("missing_kept", None)
    lib.save()
    if rec is not None:
        rec.log("document", f"{d['name']}: its file was found at a new place", who=who, save=True)
    return True


def relative_folders(found_paths, data_dir, customer_dir=""):
    """{path: its folder relative to the watched folder it is in} (the folder names become tags)."""
    roots = sorted((p for p, _c, _b in folders(data_dir, customer_dir)), key=len, reverse=True)
    out = {}
    for p in found_paths:
        for r in roots:
            if _key(p).startswith(_key(r) + os.sep):
                rel = os.path.relpath(os.path.dirname(p), r).replace(os.sep, "/")
                out[p] = "" if rel == "." else rel
                break
    return out


def summary(found):
    """One line for the notice."""
    parts = []
    if found["new"]:
        parts.append(f"{len(found['new'])} new file(s)")
    if found["changed"]:
        parts.append(f"{len(found['changed'])} changed file(s)")
    if found["missing"]:
        parts.append(f"{len(found['missing'])} document file(s) missing")
    return ", ".join(parts)
