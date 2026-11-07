"""The Effort Library on disk (3.78.0, Effort Library decisions 1 to 4): real folders in the effort's folder.

    <effort>\\Library\\
      Bidders Library\\   Our Documents\\   Graphics\\   Q&A\\   <a category you add>\\
          <its folders>\\

A file added to the library (other than a customer document, which keeps the effort's Customer Documents folder) is
copied into its category's top folder, under its folders, so what the app shows is what is on disk and the effort's
folder holds everything. Versions, roles, tags and scan status follow the file's identity (its content), not its path.
A version keeps where it sits relative to the effort's folder, so the effort opens the same wherever it is moved.

attach(lib, effort_path)       tell a document library where its effort's Library folder is
root(effort_path)              <effort>\\Library (made when asked)
top(lib, category)             the top folder's name for a category
new_folder(lib, category, parent, name) -> the folder (on disk and as the documents' folder)
move_doc(lib, doc_id, category, folder) -> [(from, to)]: the document's files move on disk, and it changes category or folder
plan_moves(lib) / do_moves(lib, plan, effort_path): files kept in the app's working folder move into the Library's
    folders, once, when the person asks; a list of every move is written to the effort's folder.
Rules only; nothing leaves the PC."""
import datetime, os, re, shutil

TOPS = {"bidders": "Bidders Library", "ours": "Our Documents", "graphics": "Graphics", "qa": "Q&A"}
CUSTOMER = "Customer Documents"
PICTURES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".svg", ".emf", ".wmf")


def _safe(x):
    return re.sub(r'[<>:"|?*]', "_", x).strip() or "_"


def root(effort_path, make=True):
    import effortfolders as EF
    r = EF.root(effort_path)
    if not r:
        return ""
    p = os.path.join(r, "Library")
    if make:
        os.makedirs(p, exist_ok=True)
    return p


def attach(lib, effort_path):
    """The library learns its effort's folder: new files go into <effort>\\Library\\<top>\\<folders>."""
    if lib is None or not effort_path:
        return lib
    import effortfolders as EF
    lib.effort_root = EF.root(effort_path)
    lib.library_root = os.path.join(lib.effort_root, "Library")
    return lib


def top(lib, category):
    if category in TOPS:
        return TOPS[category]
    return _safe(lib.category_name(category) if lib is not None else category)


def clean_folder(lib, category, folder=""):
    """The folder under the category's top folder: a folder already named for its top folder starts under it
    ('Intake/Bidders Library/Standards' in Bidders Library is 'Standards')."""
    parts = [_safe(x) for x in (folder or "").replace("\\", "/").split("/") if x.strip() and x not in (".", "..")]
    t = top(lib, category).casefold()
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].casefold() in (t, CUSTOMER.casefold() if category == "customer" else t):
            parts = parts[i + 1:]
            break
    return "/".join(parts)


def folder_path(lib, category, folder=""):
    parts = [x for x in clean_folder(lib, category, folder).split("/") if x]
    base = getattr(lib, "library_root", "") or ""
    if not base:
        return ""
    return os.path.join(base, top(lib, category), *parts)


def new_folder(lib, category, parent, name):
    """A folder under a category's top folder (or under parent). Returns its folder text ('Team/Pricing') or ''."""
    name = " ".join((name or "").split()).strip("/\\")
    if not name or category == "customer":
        return ""
    sub = "/".join([x for x in ((parent or "").split("/") + [name]) if x])
    p = folder_path(lib, category, sub)
    if not p:
        return ""
    os.makedirs(p, exist_ok=True)
    folders = list(getattr(lib, "made_folders", []) or [])
    key = f"{category}:{sub}"
    if key not in folders:
        lib.made_folders = folders + [key]
    return sub


def disk_folders(lib, category):
    """The folders on disk under a category's top folder ('a', 'a/b'), so an empty folder shows too."""
    base = folder_path(lib, category, "")
    out = []
    if base and os.path.isdir(base):
        for dp, dn, _fn in os.walk(base):
            rel = os.path.relpath(dp, base)
            if rel != ".":
                out.append(rel.replace(os.sep, "/"))
    return sorted(out, key=str.lower)


def _unique(dest):
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(dest)
    return f"{base}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"


def move_doc(lib, doc_id, category, folder=""):
    """The document's kept files move into the category's folder on disk; the document takes the category and folder.
    A customer document's files stay in Customer Documents (only its folder tag changes). Returns [(from, to)]."""
    d = lib.doc(doc_id)
    if d is None:
        return []
    moves = []
    dest_dir = folder_path(lib, category, folder) if category != "customer" else ""
    for v in d.get("versions", []):
        src = lib.path_of(v)
        if not dest_dir or not src or not os.path.isfile(src):
            continue
        if os.path.normcase(os.path.dirname(os.path.abspath(src))) == os.path.normcase(os.path.abspath(dest_dir)):
            continue
        if not _ours(lib, src):                     # a file elsewhere on the PC is copied in, never moved
            continue
        os.makedirs(dest_dir, exist_ok=True)
        dest = _unique(os.path.join(dest_dir, os.path.basename(src)))
        shutil.move(src, dest)
        set_path(lib, v, dest)
        moves.append((src, dest))
    lib.set_category(doc_id, category, folder)
    return moves


def _ours(lib, path):
    """A file kept with the effort: in its working folder or its Library folder."""
    p = os.path.normcase(os.path.abspath(path))
    for base in (getattr(lib, "data_dir", ""), getattr(lib, "library_root", "")):
        if base and p.startswith(os.path.normcase(os.path.abspath(base)) + os.sep):
            return True
    return False


def set_path(lib, v, path):
    """A version's file is now at path: kept relative to the effort's folder when it is inside it."""
    v["path"] = os.path.abspath(path)
    v.pop("rel", None); v.pop("erel", None)
    rel = lib._rel(path)
    if rel:
        v["rel"] = rel
    erel = lib._erel(path)
    if erel:
        v["erel"] = erel


def plan_moves(lib):
    """Files kept in the app's working folder (before 3.78.0) and where each would go in the Library. [(doc, v, from, to)]"""
    out = []
    if not getattr(lib, "library_root", ""):
        return out
    for d in lib.all:
        if d.get("category") == "customer":
            continue
        for v in d.get("versions", []):
            src = lib.path_of(v)
            if not v.get("rel") or not src or not os.path.isfile(src):
                continue
            dest = os.path.join(folder_path(lib, d.get("category", "ours"), d.get("folder", "")), os.path.basename(src))
            out.append((d, v, src, dest))
    return out


def do_moves(lib, plan, effort_path):
    """Make the moves; write every one to 'Library moves <date>.txt' in the effort's folder. Returns (moved, list file)."""
    done = []
    for d, v, src, dest in plan:
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            dest = _unique(dest)
            shutil.move(src, dest)
            set_path(lib, v, dest)
            done.append((d.get("name", ""), src, dest))
        except OSError:
            import diag
            diag.swallowed()
    lib.save()
    note = ""
    if done:
        import effortfolders as EF
        note = os.path.join(EF.root(effort_path), f"Library moves {datetime.datetime.now().strftime('%Y-%m-%d %H%M')}.txt")
        with open(note, "w", encoding="utf-8") as f:
            f.write("Stationkeeper moved these files into the effort's Library folders:\r\n\r\n")
            for name, a, b in done:
                f.write(f"{name}\r\n  from {a}\r\n  to   {b}\r\n")
    return len(done), note
