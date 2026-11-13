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
            "last": d.get("last", ""), "root_seen": bool(d.get("root_seen")), "cust_seen": bool(d.get("cust_seen"))}


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


def folders(data_dir, customer_dir="", effort_root=""):
    """[(path, category, built in)]: the Customer Documents folder first, then the ones added, then (4.25.1) the
    effort's own folder, whose new files are added by themselves."""
    out = []
    if customer_dir:
        out.append((os.path.abspath(customer_dir), "customer", True))
    for f in load(data_dir)["folders"]:
        if not any(_key(f["path"]) == _key(p) for p, _c, _b in out):
            out.append((f["path"], f.get("category", "customer"), False))
    if effort_root and not any(_key(effort_root) == _key(p) for p, _c, _b in out):
        out.append((os.path.abspath(effort_root), AUTO, True))
    return out


AUTO = "ours"            # 4.25.1: a file dropped into the effort's folder is one of our own documents, kept for reference
CUSTOMER = "customer"     # 4.29.2: a file dropped into the customer's folder, after its first check, is the customer's, For the shred
CUSTOMER_AUTO = True      # tests of the table (what a folder holds at its first check, a chosen folder) turn this off
AUTO_MOST = 25           # more new files than this at once are offered, not added by themselves
# In the effort's folder any kind of file is a document to keep (answer: "reference files of any type"), except what
# programs leave behind and Stationkeeper's own files.
NOT_DOCUMENTS = (".tmp", ".lnk", ".ini", ".db", ".url", ".skeffort", ".skpkg", ".skupdate", ".sktrain", ".skredline.json",
                 ".bak", ".crdownload", ".partial", ".ds_store", ".lock")


def _skip(name):
    return name.startswith("~$") or name.startswith(".") or name.lower().endswith((".tmp", ".part.pdf"))


def walk(folder, data_dir="", skip=(), any_kind=False, not_in=()):
    """Every document under the folder, subfolders included; the app's own folders are left out. 4.25.1: skip: folders
    left out with all they hold; any_kind: every kind of file but what programs leave behind; not_in: folders whose own
    files are left out (their subfolders are still walked)."""
    out = []
    skip_dirs = ({_key(data_dir)} if data_dir else set()) | {_key(x) for x in skip if x}
    own = {_key(x) for x in not_in if x}
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".") and _key(os.path.join(root, d)) not in skip_dirs
                   and not d.endswith((" - app data", "- readable copy (Stationkeeper)")) and "readable copy" not in d.lower()]
        if _key(root) in own:
            continue
        for f in files:
            if _skip(f):
                continue
            if f.lower().endswith(KINDS) or (any_kind and not f.lower().endswith(NOT_DOCUMENTS)):
                out.append(os.path.join(root, f))
    return sorted(out)


def _inside(p, roots):
    k = _key(p)
    return any(k == r or k.startswith(r + os.sep) for r in roots)


def check(lib, data_dir, customer_dir="", sha=None, effort_root="", skip=(), not_in=()):
    """{"new": [(path, category)], "changed": [(path, doc, version)], "missing": [(doc, version, path)], "auto":
    [(path, category)]} for the watched folders. Updates the size and time cache (so the next check fingerprints only
    what changed).

    4.25.1 (answer 9): effort_root is the effort's own folder. A file that appears in it, outside the customer's
    folder and the folders given in skip (our volumes, Response Setup, Exports, Redlines, Deleted), is in "auto": the
    window adds it by itself as one of our documents, for reference, where it sits. What was already in the folder of
    an effort that has documents, the first time it is checked, is left alone (it was never dropped in to be added), and more than AUTO_MOST
    new files at once are offered in "new" instead.

    4.29.2 (Nicholas 2026-11-13 answer 2): a file that appears in the customer's folder after that folder's first check
    is in "auto" too, as the customer's (CUSTOMER): the window adds it by itself, For the shred. What is in the folder
    at its first check is offered in "new", as before: those are read with the table, where each gets its type."""
    import docversions as DV
    sha = sha or DV.sha256
    st = load(data_dir)
    seen = st["seen"]
    watched = folders(data_dir, customer_dir, effort_root)
    roots = [_key(p) for p, _c, _b in watched if os.path.isdir(p)]
    er = _key(effort_root) if effort_root else ""
    first_root = bool(er) and not st.get("root_seen") and bool(lib.all)     # a new effort has nothing "from before"
    ck = _key(customer_dir) if customer_dir else ""
    cust_later = CUSTOMER_AUTO and bool(ck) and bool(st.get("cust_seen"))    # 4.29.2: after its first check, the customer's folder adds by itself
    auto = []
    shas = {v.get("sha256") for d in lib.all for v in d["versions"]}
    latest = {}                                   # file path -> (doc, version) of each document's latest version
    sources = {}                                  # 3.15.1: where a latest version came from, outside the effort
    for d in lib.all:
        if d["versions"]:
            v = d["versions"][-1]
            p = lib.path_of(v)
            if p:
                latest[_key(p)] = (d, v)
            if v.get("source") and not v.get("source_gone"):
                sources[_key(v["source"])] = (d, v)
    out = {"new": [], "changed": [], "missing": [], "auto": []}
    found = set()
    for folder, cat, _b in watched:
        if not os.path.isdir(folder):
            continue
        is_root = bool(er) and _key(folder) == er
        for p in (walk(folder, data_dir, skip, True, not_in) if is_root else walk(folder, data_dir)):
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
            if k in latest or k in sources:
                d, v = latest.get(k) or sources[k]
                if h != v.get("sha256") and h not in shas and seen[k]["state"] != "ignored":
                    out["changed"].append((p, d, v))
                continue
            if h in shas or seen[k]["state"] in ("ignored", "before"):
                continue
            if is_root:
                if first_root:
                    seen[k]["state"] = "before"      # here before the effort's folder was watched: left alone
                else:
                    auto.append((p, AUTO))
                continue
            rel = os.path.relpath(os.path.dirname(p), folder).replace(os.sep, "/").strip("./")
            if cust_later and _key(folder) == ck:
                auto.append((p, CUSTOMER))           # 4.29.2 (answer 2): added by itself, For the shred
                continue
            out["new"].append((p, cat or DV.guess_category(rel + "/" + os.path.basename(p), "customer")))
    for k, (d, v) in latest.items():
        if d.get("withdrawn") or v.get("missing_kept"):
            continue
        if k not in found and _inside(k, roots) and not os.path.isfile(k):
            out["missing"].append((d, v, lib.path_of(v)))
    for k, (d, v) in sources.items():             # 3.15.1: the file it came from left its watched folder
        if d.get("withdrawn") or v.get("missing_kept") or k in latest:
            continue
        if k not in found and _inside(k, roots) and not os.path.isfile(v["source"]):
            out["missing"].append((d, v, v["source"]))
    for k in [k for k in seen if k not in found]:            # forget files that are gone (missing documents are in the library)
        seen.pop(k, None)
    if er and os.path.isdir(effort_root):
        st["root_seen"] = True
    if ck and os.path.isdir(customer_dir):
        st["cust_seen"] = True
    out["auto" if len(auto) <= AUTO_MOST else "new"] += auto
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


def _source_only(lib, v, path):
    """3.15.1: the file gone is the one it was added from, and the effort's own copy is still here."""
    import docversions as DV
    return bool(path) and DV.same_path(path, v.get("source", "")) and lib.has_original(v)


def keep_without_original(lib, rec, doc_id, who=None, path=None):
    """The document stays, read text and all, with its original file gone; the check stops asking. 3.15.1: when only
    the file it came from is gone (the effort's copy is here), the check stops asking about that file."""
    d = lib.doc(doc_id)
    if d is None or not d["versions"]:
        return False
    v = d["versions"][-1]
    if _source_only(lib, v, path):
        v["source_gone"] = {"when": _now(), "who": who or getpass.getuser()}
        lib.save()
        if rec is not None:
            rec.log("document", f"{d['name']}: its file left the watched folder; the effort's copy is kept", who=who, save=True)
        return True
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


def found_at(lib, rec, doc_id, path, who=None, was=None):
    """'Find it': the document's latest version is the file at path now. True when its contents match (the file only
    moved); False when they differ (then it is a new version, added the usual way)."""
    import docversions as DV
    d = lib.doc(doc_id)
    if d is None or not d["versions"] or not os.path.isfile(path):
        return False
    v = d["versions"][-1]
    if DV.sha256(path) != v.get("sha256"):
        return False
    if _source_only(lib, v, was):                 # 3.15.1: it came from a watched folder: follow the file there
        v["source"] = os.path.abspath(path)
        v.pop("source_gone", None)
        lib.save()
        if rec is not None:
            rec.log("document", f"{d['name']}: the file it came from was found at a new place", who=who, save=True)
        return True
    import effortlib as EL                          # 3.78.0: rel and erel follow the file
    EL.set_path(lib, v, path)
    v.pop("missing_kept", None)
    lib.save()
    if rec is not None:
        rec.log("document", f"{d['name']}: its file was found at a new place", who=who, save=True)
    return True


def relative_folders(found_paths, data_dir, customer_dir="", effort_root=""):
    """{path: its folder relative to the watched folder it is in} (the folder names become tags)."""
    roots = sorted((p for p, _c, _b in folders(data_dir, customer_dir, effort_root)), key=len, reverse=True)
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
    if found.get("auto"):
        parts.append(f"{len(found['auto'])} file(s) came into the effort's folder")
    return ", ".join(parts)
