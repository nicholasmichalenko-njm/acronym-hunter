"""Effort package (2.40.0): the whole effort in one file, so someone else can open it and continue where it was.

A .skpkg file (.ahpkg before 2.44.0, still opened) is a zip with:
- manifest.json: format, app version, effort name, who saved it and when, its stage, the effort's details, and every
  file with its SHA-256 fingerprint (checked on import);
- list/<effort list>.xlsx: the effort list;
- data/...: the effort's saved work (the app data folder: record, settings, customer document versions and their text
  copies, submission requirements, choices). Locks, backups and recovery files stay out;
- matrix/<matrix>.xlsx: the compliance matrix, when the effort has one;
- customer/...: the customer files themselves (optional);
- volumes/...: our volumes (optional).
- readable/...: the effort's readable copy (2.46.0): plain CSV and text files, so the package can be unzipped and read
  without Stationkeeper.

Import unpacks into a folder the person picks, points the paths at the new place, and registers the effort. Rules only
(No AI); nothing leaves the PC: the package goes where the person saves it (this PC or the approved SharePoint folder).
"""
import datetime, getpass, hashlib, json, os, shutil, zipfile

FORMAT = 1
EXT = ".skpkg"
EXTS = (".skpkg", ".ahpkg")             # 2.44.0: packages saved as Acronym Hunter still open
SKIP_DIRS = {"backups", "recovery", "__pycache__"}
SKIP_FILES = {"lock.json"}
DOC_TYPES = (".docx", ".pdf", ".pptx", ".xlsx", ".xls", ".doc", ".txt", ".csv", ".zip", ".mpp")


class PackageError(Exception):
    pass


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _files_in(folder, types=None):
    out = []
    if not folder or not os.path.isdir(folder):
        return out
    for dp, dns, fns in os.walk(folder):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            if f in SKIP_FILES or f.startswith("~$") or f.endswith(".tmp"):
                continue
            if types and not f.lower().endswith(types):
                continue
            out.append(os.path.join(dp, f))
    return sorted(out)


def plan(list_path, data_dir, matrix_path="", customer_dir="", volumes_dir="", customer=True, volumes=False, extra_files=(), readable_dir=""):
    """[(arcname, path)] of what a package would hold, and its total size in bytes. extra_files: other files the effort
    points to (a deliverable's working file outside the folders above), packed under files/ (2.41.0)."""
    items = [("list/" + os.path.basename(list_path), list_path)]
    for p in _files_in(data_dir):
        items.append(("data/" + os.path.relpath(p, data_dir).replace(os.sep, "/"), p))
    if matrix_path and os.path.isfile(matrix_path):
        items.append(("matrix/" + os.path.basename(matrix_path), matrix_path))
    if customer:
        for p in _files_in(customer_dir, DOC_TYPES):
            items.append(("customer/" + os.path.relpath(p, customer_dir).replace(os.sep, "/"), p))
    if volumes:
        for p in _files_in(volumes_dir, (".docx",)):
            items.append(("volumes/" + os.path.relpath(p, volumes_dir).replace(os.sep, "/"), p))
    for p in _files_in(readable_dir):
        items.append(("readable/" + os.path.relpath(p, readable_dir).replace(os.sep, "/"), p))
    have = {os.path.normcase(os.path.abspath(p)) for _a, p in items}
    for i, p in enumerate(extra_files or ()):
        if p and os.path.isfile(p) and os.path.normcase(os.path.abspath(p)) not in have:
            items.append((f"files/{i + 1}/{os.path.basename(p)}", p))
            have.add(os.path.normcase(os.path.abspath(p)))
    size = sum(os.path.getsize(p) for _a, p in items if os.path.isfile(p))
    return items, size


def save(out_path, effort_name, list_path, data_dir, info=None, matrix_path="", customer_dir="", volumes_dir="",
         customer=True, volumes=True, stage="", app_version="", who=None, when=None, extra_files=(), readable_dir=""):
    """Write the package. Returns the manifest."""
    if not out_path.lower().endswith(EXTS):
        out_path += EXT
    items, size = plan(list_path, data_dir, matrix_path, customer_dir, volumes_dir, customer, volumes, extra_files, readable_dir)
    man = {"format": FORMAT, "app": app_version, "effort": effort_name, "saved_by": who or getpass.getuser(),
           "saved_at": when or datetime.datetime.now().isoformat(timespec="minutes"), "stage": stage,
           "info": {k: v for k, v in (info or {}).items() if isinstance(v, (str, int, float, bool))},
           "has": {"customer": bool(customer and any(a.startswith("customer/") for a, _p in items)),
                   "volumes": bool(volumes and any(a.startswith("volumes/") for a, _p in items)),
                   "matrix": any(a.startswith("matrix/") for a, _p in items)},
           "files": {}, "origin": {}}
    tmp = out_path + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, p in items:
            if not os.path.isfile(p):
                continue
            man["files"][arc] = _sha(p)
            if not arc.startswith(("data/", "list/", "readable/")):
                man["origin"][arc] = os.path.abspath(p)          # where it was, so links to it can follow it
            z.write(p, arc)
        z.writestr("manifest.json", json.dumps(man, indent=1))
        if any(a.startswith("readable/") for a, _p in items):
            z.writestr("READ ME.txt", "Stationkeeper effort package: " + effort_name + "\r\n\r\nOpen it in Stationkeeper with File > Import "
                       "effort package. Without Stationkeeper, unzip it (rename .skpkg to .zip first if needed) and open the readable "
                       "folder: READ ME FIRST.txt explains every file.\r\n")
    os.replace(tmp, out_path)
    man["path"], man["bytes"] = out_path, size
    return man


def read_manifest(pkg_path):
    try:
        with zipfile.ZipFile(pkg_path) as z:
            man = json.loads(z.read("manifest.json").decode("utf-8"))
    except (KeyError, zipfile.BadZipFile, OSError, ValueError) as e:
        raise PackageError("This file is not a Stationkeeper effort package.") from e
    if man.get("format", 0) > FORMAT:
        raise PackageError("The package was saved by a newer Stationkeeper. Update this PC's copy, then open it.")
    return man


def _safe_arc(arc):
    parts = arc.replace("\\", "/").split("/")
    if not arc or arc.startswith("/") or any(p in ("", "..") or ":" in p for p in parts):
        raise PackageError("The package holds an unsafe file name.")
    return parts


def unpack(pkg_path, dest_folder, data_dir_for):
    """Unpack into dest_folder (list, matrix, Customer documents, Volumes) and the list's app data folder.
    data_dir_for: workspace.data_dir_for. Returns {"list", "data", "matrix", "customer_dir", "volumes_dir", "manifest"}.
    Every file is checked against the fingerprint in the manifest."""
    man = read_manifest(pkg_path)
    os.makedirs(dest_folder, exist_ok=True)
    out = {"list": "", "data": "", "matrix": "", "customer_dir": "", "volumes_dir": "", "manifest": man, "moved": {}}
    with zipfile.ZipFile(pkg_path) as z:
        names = [n for n in z.namelist() if n != "manifest.json" and not n.endswith("/")]
        lst = next((n for n in names if n.startswith("list/")), None)
        if lst is None:
            raise PackageError("The package has no effort list.")
        out["list"] = os.path.join(dest_folder, _safe_arc(lst)[-1])
        out["data"] = data_dir_for(out["list"])
        for n in names:
            parts = _safe_arc(n)
            top, rest = parts[0], parts[1:]
            if top == "list":
                target = out["list"]
            elif top == "data":
                target = os.path.join(out["data"], *rest)
            elif top == "matrix":
                target = out["matrix"] = os.path.join(dest_folder, *rest)
            elif top == "customer":
                out["customer_dir"] = os.path.join(dest_folder, "Customer documents")
                target = os.path.join(out["customer_dir"], *rest)
            elif top == "volumes":
                out["volumes_dir"] = os.path.join(dest_folder, "Volumes")
                target = os.path.join(out["volumes_dir"], *rest)
            elif top == "files":
                target = os.path.join(dest_folder, "Our files", *rest)
            elif top == "readable":
                import readable as RD
                out.setdefault("readable_dir", RD.folder_for(out["list"], man.get("effort", "")))
                target = os.path.join(out["readable_dir"], *rest)
            else:
                continue
            data = z.read(n)
            want = man.get("files", {}).get(n)
            if want and hashlib.sha256(data).hexdigest() != want:
                raise PackageError(f"A file in the package does not match its fingerprint: {n}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
            if n in man.get("origin", {}):
                out["moved"][os.path.normcase(man["origin"][n])] = target
    return out


def repoint(data_dir, customer_dir="", matrix_path="", moved=None):
    """After an import: point the saved work at the new place (the customer document versions' files, the matrix,
    and any file a deliverable points to: moved maps its old path to where it was unpacked)."""
    import workspace as W
    idx = os.path.join(data_dir, "documents", "index.json")
    d = W.read_json(idx, None)
    n = 0
    here = {}                                           # 2.52.0: customer files by name, in any subfolder
    for p in _files_in(customer_dir):
        here.setdefault(os.path.basename(p).lower(), p)

    def new_path(old, name=""):
        """Where a file that was at old (on the PC that saved the package) is now."""
        if old and moved and os.path.normcase(os.path.abspath(old)) in moved:
            return moved[os.path.normcase(os.path.abspath(old))]
        nm = (name or os.path.basename(old or "")).lower()
        return here.get(nm, "")
    if d and customer_dir:
        for doc in d.get("docs", []):
            for v in doc.get("versions", []):
                p = new_path(v.get("path", ""), v.get("file", ""))
                if p and os.path.isfile(p):
                    v["path"] = p
                    n += 1
        W.write_json(idx, d)
    if matrix_path and os.path.isfile(matrix_path):     # 2.52.0: the matrix's RFP files are the unpacked customer files
        try:
            import compliance as C
            M = C.Matrix(matrix_path).load()
            changed = False
            for src in M.sources:
                if len(src) > 3:
                    p = new_path(src[3], src[0])
                    if p and os.path.isfile(p) and src[3] != p:
                        src[3] = p
                        changed = True
                        n += 1
            if changed:
                M.save()
        except Exception:
            pass
    st = os.path.join(data_dir, "settings.json")
    s = W.read_json(st, None)
    if isinstance(s, dict) and matrix_path:
        s["compliance_path"] = matrix_path
        W.write_json(st, s)
    rp = os.path.join(data_dir, "record.json")
    rec = W.read_json(rp, None)
    if isinstance(rec, dict) and moved:
        for dl in rec.get("deliverables", []):
            f = dl.get("file")
            if f and os.path.normcase(os.path.abspath(f)) in moved:
                dl["file"] = moved[os.path.normcase(os.path.abspath(f))]
                n += 1
        W.write_json(rp, rec)
    for p in (os.path.join(data_dir, "lock.json"),):
        if os.path.exists(p):
            os.remove(p)
    return n


def backup_folder(folder, dest_zip):
    """Zip a folder (an effort's app data, before an import replaces it)."""
    if not os.path.isdir(folder):
        return None
    base = dest_zip[:-4] if dest_zip.lower().endswith(".zip") else dest_zip
    return shutil.make_archive(base, "zip", folder)
