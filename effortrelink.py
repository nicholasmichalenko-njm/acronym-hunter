"""Open an effort from its folder, and find an effort that moved (3.68.0). An effort is its Effort List workbook with
"<list> - app data" beside it (effortfolders). The app remembers the workbook's full path; when the folder is moved or
copied, this finds the workbook again and points the effort's saved paths at the new place: the customer document
versions, the compliance matrix and every deliverable's file, first by where each sat inside the old effort folder,
then by name anywhere in the new one (effortpkg.repoint, as a package import does).

A small marker file, "Open this effort.skeffort", sits in the effort's folder: it names the effort and its Effort List
relative to the folder, so opening the marker (or picking the folder) finds the effort wherever the folder now lives.

find_list(path) -> the Effort List path, or ""     (path: the effort's folder, its Effort List, or the marker)
relink(list_path, old_list_path="") -> {"list", "data", "name", "repointed", "old_root", "new_root"}
write_marker(list_path, name) -> marker path or ""; missing(info) -> True when the remembered list is gone.
Standard library and the app's own modules; nothing leaves the PC; nothing in the effort's folder is deleted."""
import json, os

import workspace as W

MARKER = "Open this effort.skeffort"
EXT = ".skeffort"
LIST_TAIL = "_Effort_List.xlsx"
DEPTH = 3


def _is_list(p):
    return p.lower().endswith(".xlsx") and os.path.isfile(p) and os.path.isdir(W.data_dir_for(p))


def find_list(path):
    """The Effort List for a folder, a workbook or a marker: the workbook with its app data folder beside it."""
    if not path:
        return ""
    path = os.path.abspath(path)
    if path.lower().endswith(EXT) and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                m = json.load(f) or {}
        except (OSError, ValueError):
            m = {}
        cand = os.path.join(os.path.dirname(path), m.get("list") or "")
        if m.get("list") and _is_list(cand):
            return os.path.abspath(cand)
        path = os.path.dirname(path)                  # the marker's folder: look there
    if os.path.isfile(path):
        return path if _is_list(path) else ""
    if not os.path.isdir(path):
        return ""
    found = []
    base = path.rstrip(os.sep).count(os.sep)
    for d, subs, files in os.walk(path):
        if d.count(os.sep) - base >= DEPTH:
            subs[:] = []
        subs[:] = [s for s in subs if not s.endswith(W.DATA_SUFFIX)]
        for f in files:
            p = os.path.join(d, f)
            if f.lower().endswith(".xlsx") and _is_list(p):
                found.append(p)
    found.sort(key=lambda p: (not p.endswith(LIST_TAIL), p.count(os.sep), p.lower()))
    return found[0] if found else ""


def _old_paths(data_dir):
    """Every file path the effort saved: the customer document versions, the matrix, the deliverables' files."""
    out = []
    idx = W.read_json(os.path.join(data_dir, "documents", "index.json"), None) or {}
    for doc in idx.get("docs", []) if isinstance(idx, dict) else []:
        out += [v.get("path", "") for v in doc.get("versions", []) if v.get("path")]
    s = W.read_json(os.path.join(data_dir, "settings.json"), None) or {}
    if isinstance(s, dict) and s.get("compliance_path"):
        out.append(s["compliance_path"])
    rec = W.read_json(os.path.join(data_dir, "record.json"), None) or {}
    out += [d.get("file") for d in (rec.get("deliverables") or []) if isinstance(rec, dict) and d.get("file")]
    return [p for p in out if p]


def _old_root(paths, old_list_path="", up=0):
    """The effort's old folder: where its list was (as many folders up as the effort keeps it), else the folder the
    saved paths share."""
    if old_list_path:
        d = os.path.dirname(os.path.abspath(old_list_path))
        for _ in range(up):
            d = os.path.dirname(d)
        return d
    if not paths:
        return ""
    try:
        return os.path.commonpath([os.path.dirname(os.path.abspath(p)) for p in paths])
    except ValueError:                                # paths on different drives
        return ""


def relink(list_path, old_list_path=""):
    """Points the effort's saved paths at its folder's new place. Returns what it did."""
    import effortpkg as P
    import effortfolders as EF
    data = W.data_dir_for(list_path)
    new_root = EF.root(list_path) or os.path.dirname(os.path.abspath(list_path))
    up = os.path.relpath(os.path.dirname(os.path.abspath(list_path)), new_root).count(os.sep) + 1 \
        if os.path.normcase(new_root) != os.path.normcase(os.path.dirname(os.path.abspath(list_path))) else 0
    olds = _old_paths(data)
    old_root = _old_root(olds, old_list_path, up)
    moved = {}
    for p in olds:
        if os.path.isfile(p):
            continue                                  # still there: nothing to do
        ap = os.path.abspath(p)
        if old_root and os.path.normcase(ap).startswith(os.path.normcase(old_root.rstrip(os.sep) + os.sep)):
            cand = os.path.join(new_root, os.path.relpath(ap, old_root))
            if os.path.isfile(cand):
                moved[os.path.normcase(ap)] = cand
    s = W.read_json(os.path.join(data, "settings.json"), None) or {}
    matrix = ""
    if isinstance(s, dict) and s.get("compliance_path"):
        m = s["compliance_path"]
        matrix = m if os.path.isfile(m) else moved.get(os.path.normcase(os.path.abspath(m)), "")
    if not matrix:
        here = os.path.dirname(os.path.abspath(list_path))
        matrix = next((os.path.join(d, f) for d in dict.fromkeys((here, new_root)) for f in sorted(os.listdir(d))
                       if f.lower().endswith("_compliance_matrix.xlsx")), "")
    n = P.repoint(data, new_root, matrix, moved)      # by old place first, then by name anywhere in the folder
    import effort as E
    try:
        name = E.EffortList(list_path).load().name
    except Exception:  # noqa: BLE001  an unreadable list: its file name
        name = os.path.splitext(os.path.basename(list_path))[0].replace("_Effort_List", "")
    return {"list": list_path, "data": data, "name": name, "repointed": n, "old_root": old_root, "new_root": new_root,
            "matrix": matrix}


def missing(info):
    """True when both the remembered Effort List and its app data folder are gone (the folder was moved, renamed or is
    offline). A new effort whose list is not saved yet, or whose app data folder is not made yet, is not missing."""
    p = (info or {}).get("path") or ""
    return bool(p) and not os.path.isfile(p) and not os.path.isdir(W.data_dir_for(p))


def write_marker(list_path, name):
    """The marker beside the effort's folder content: written when missing or out of date; never more."""
    import effortfolders as EF
    root = EF.root(list_path)
    if not root or not os.path.isdir(root):
        return ""
    path = os.path.join(root, MARKER)
    body = {"format": 1, "effort": name, "list": os.path.relpath(os.path.abspath(list_path), root),
            "about": "Open this file with Stationkeeper (or pick this folder in Efforts > Open an effort from its folder) "
                     "to open the effort, wherever the folder now lives."}
    try:
        with open(path, encoding="utf-8") as f:
            if json.load(f) == body:
                return path
    except (OSError, ValueError):
        pass
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=1)
    except OSError:
        return ""
    return path
