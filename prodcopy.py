"""The only way Stationkeeper changes an Office file (3.6.0): it never edits the original. It reads the original once,
writes an exact copy into the production output folder under a name that says what it is, checks the copy byte for
byte, and every fix then runs on that copy through the engine's guarded write.

    <name> - COPY - Stationkeeper 2026-10-31 1602.docx
    <name> - COPY - Stationkeeper 2026-10-31 1602 - report.xlsx

Rules, all enforced here and tested:
- The original is opened once, read-only, and never for writing; no lock is taken on it beyond Windows' plain read.
- A file someone has open is not copied: Word's owner file (~$name) beside it, an exclusive read probe that fails
  (another program holds it), or Word, Excel or PowerPoint on this PC listing it as open (also when it was opened
  from OneDrive or SharePoint, matched by file name). People editing it online from other PCs cannot be seen from
  here; for files in a OneDrive or SharePoint folder the copy is the last version synced to this PC, and the page
  says so.
- A file that changes while it is read (a save in progress, a sync) is not copied.
- The copy goes only into the output folder, never beside the original, never over another file.
- Every engine write is refused unless its target is a copy of this kind inside an output folder (WRITE_GUARD).
- Before and after a job the original's SHA-256, size and modified time are compared; a difference is reported as
  a change made by someone else (Stationkeeper never opened it for writing).
"""
import datetime, hashlib, io, os, re, subprocess, sys, zipfile

MARK = " - COPY - Stationkeeper "
WORD_EXT = (".docx", ".docm", ".dotx", ".dotm")
OFFICE_EXT = WORD_EXT + (".xlsx", ".xlsm", ".pptx", ".pptm")
_STAMP = re.compile(r" - COPY - Stationkeeper \d{4}-\d{2}-\d{2} \d{4}(?: \(\d+\))?$")


class Busy(Exception):
    """The original is in use or changing; nothing was copied."""


class NotAllowed(Exception):
    """A write outside the rules (not a Stationkeeper copy, not in an output folder)."""


# ------------------------------------------------------------------ output folder
def default_folder(data_dir):
    return os.path.join(data_dir, "Production Copies")


def output_folder(settings, data_dir):
    p = (settings or {}).get("prod_output_dir") or ""
    return p if p else default_folder(data_dir)


def effort_folder(base, effort=""):
    """The open effort's own folder inside the output folder (copies of one effort together); the output folder itself
    with no effort open. The name keeps only characters Windows allows in a folder name."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", effort or "")
    name = " ".join(name.split()).rstrip(". ")[:80]
    if name.upper() in ("CON", "PRN", "AUX", "NUL") or re.fullmatch(r"(?i)(COM|LPT)\d", name):
        name = "_" + name
    return os.path.join(base, name) if name else base


_ROOTS = set()


def allow_root(folder):
    """Register an output folder the engine may write copies into (the setting, or the default)."""
    _ROOTS.add(os.path.normcase(os.path.realpath(folder)))


def is_copy_name(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    return bool(_STAMP.search(stem))


def check_write(path):
    """WRITE_GUARD for the engine: only a Stationkeeper copy inside a registered output folder."""
    real = os.path.realpath(path)
    folder = os.path.normcase(os.path.dirname(real))       # Windows: the folder is compared without case...
    if not any(folder == r or folder.startswith(r + os.sep) for r in _ROOTS):
        raise NotAllowed("Stationkeeper writes only into the production output folder.")
    if not is_copy_name(real):                              # ...the name with its own case (normcase lowers it)
        raise NotAllowed("Stationkeeper writes only to its own dated copies.")


def install_guard():
    from prodengine.engine import safewrite
    safewrite.WRITE_GUARD = check_write
    safewrite.OPEN_CHECKS = copy_open_checks
    return safewrite


# ------------------------------------------------------------------ is someone in the file?
def owner_files(path):
    """Word and Excel make ~$name beside a file they have open (Word may trim the first one or two letters)."""
    d, f = os.path.split(os.path.abspath(path))
    cands = {"~$" + f, "~$" + f[1:], "~$" + f[2:]}
    try:
        return [os.path.join(d, n) for n in os.listdir(d) if n in cands]
    except OSError:
        return []


def exclusive_read_free(path):
    """True when no other program has the file open. Asks Windows for READ access with no sharing: it fails while any
    other handle is open. Never asks for write access, so the original cannot be changed by the probe."""
    if not sys.platform.startswith("win"):
        return True
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateFileW.restype = wintypes.HANDLE
    k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                              wintypes.DWORD, wintypes.HANDLE]
    GENERIC_READ, OPEN_EXISTING, INVALID = 0x80000000, 3, wintypes.HANDLE(-1).value
    for attempt in range(2):
        h = k.CreateFileW(str(path), GENERIC_READ, 0, None, OPEN_EXISTING, 0x80, None)
        if h and h != INVALID:
            k.CloseHandle(h)
            return True
        err = ctypes.get_last_error()
        if err in (32, 33) and attempt == 0:          # sharing or lock violation: try once more after a moment
            import time
            time.sleep(0.8)
            continue
        return err not in (32, 33)
    return False


_LIST_OPEN = r"""
$ErrorActionPreference = 'SilentlyContinue'
$out = @()
if (Get-Process WINWORD -ErrorAction SilentlyContinue) {
  try { $w = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application'); foreach ($d in $w.Documents) { $out += $d.FullName } } catch {} }
if (Get-Process EXCEL -ErrorAction SilentlyContinue) {
  try { $x = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application'); foreach ($b in $x.Workbooks) { $out += $b.FullName } } catch {} }
if (Get-Process POWERPNT -ErrorAction SilentlyContinue) {
  try { $p = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); foreach ($s in $p.Presentations) { $out += $s.FullName } } catch {} }
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$out -join "`n"
"""


def office_open_files(runner=None, timeout=20):
    """The files Word, Excel and PowerPoint on this PC have open (local paths or web addresses). Read-only: it only
    lists names. None when the list could not be read (treated as unknown, not as free)."""
    if runner is not None:
        return runner()
    if not sys.platform.startswith("win"):
        return []
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _LIST_OPEN], capture_output=True,
                           timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return [x.strip() for x in r.stdout.decode("utf-8", "replace").splitlines() if x.strip()]
    except (OSError, subprocess.SubprocessError):
        return None


def _same_file(name, path):
    import urllib.parse
    if name.lower().startswith(("http://", "https://")):
        tail = urllib.parse.unquote(name.split("?")[0].rstrip("/").rsplit("/", 1)[-1])
        return tail.lower() == os.path.basename(path).lower()
    return os.path.normcase(os.path.abspath(name)) == os.path.normcase(os.path.abspath(path))


def cloud_kind(path):
    """'OneDrive' or 'SharePoint' when the file sits in a folder OneDrive syncs, else ''."""
    p = os.path.normcase(os.path.abspath(path))
    for var in ("OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        root = os.environ.get(var)
        if root and p.startswith(os.path.normcase(os.path.abspath(root)) + os.sep):
            return "OneDrive"
    home = os.path.normcase(os.path.expanduser("~"))
    if p.startswith(home + os.sep):
        rel = p[len(home) + 1:].split(os.sep)[0]
        if rel.lower().startswith("onedrive"):
            return "OneDrive"
        if " - " in rel and os.path.isdir(os.path.join(home, rel)):     # "Company - Site" folders synced from SharePoint
            return "SharePoint"
    return ""


_ASK = object()


def in_use(path, open_list=_ASK):
    """[why, ...]: every sign that someone has the file open. Empty means none was found on this PC."""
    why = []
    if owner_files(path):
        why.append("Word or Excel has it open (its ~$ owner file is beside it). If nobody has it open, Office left that "
                   "file after a crash: delete the ~$ file and try again.")
    if not exclusive_read_free(path):
        why.append("Another program has it open.")
    names = office_open_files() if open_list is _ASK else open_list
    if names is None:
        why.append("Stationkeeper could not ask Office which files are open. Close Office and try again.")
    elif any(_same_file(n, path) for n in names):
        why.append("It is open in Word, Excel or PowerPoint on this PC" +
                   (" (from OneDrive or SharePoint)" if any(n.lower().startswith("http") and _same_file(n, path) for n in names) else "") + ".")
    return why


def copy_open_checks(path):
    """The engine's open checks for a copy Stationkeeper made (replaces checks that need pywin32)."""
    from prodengine.engine.pkg import Refused
    if not os.path.isfile(path):
        raise Refused("The copy is missing.")
    if owner_files(path):
        raise Refused("Someone opened the copy in Word. Close it and run the fixes again.")
    if not exclusive_read_free(path):
        raise Refused("Another program has the copy open. Close it and try again.")


# ------------------------------------------------------------------ the copy
def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def state(path):
    st = os.stat(path)
    return {"sha256": sha256_file(path), "size": st.st_size, "mtime_ns": st.st_mtime_ns}


def copy_name(original, when=None):
    stem, ext = os.path.splitext(os.path.basename(original))
    stem = _STAMP.sub("", stem)
    when = when or datetime.datetime.now()
    return f"{stem}{MARK}{when.strftime('%Y-%m-%d %H%M')}{ext}"


class Job:
    def __init__(self, original, copy, before, cloud):
        self.original, self.copy, self.before, self.cloud = original, copy, before, cloud
        self.steps = []          # [{"step", "changed", "report" or "refused"}]

    @property
    def report_path(self):
        return os.path.splitext(self.copy)[0] + " - report.xlsx"

    def original_unchanged(self):
        try:
            return state(self.original) == self.before
        except OSError:
            return False


def make_copy(original, folder, when=None, open_list=_ASK):
    """Read the original once, write the copy into folder, check it. Returns a Job. Raises Busy (nothing copied) or
    NotAllowed."""
    original = os.path.abspath(original)
    if not os.path.isfile(original):
        raise Busy("The file is not there.")
    if os.path.splitext(original)[1].lower() not in OFFICE_EXT:
        raise NotAllowed("Only Word, Excel and PowerPoint files (.docx, .xlsx, .pptx and their macro and template forms).")
    folder = os.path.abspath(folder)
    if os.path.normcase(os.path.dirname(original)) == os.path.normcase(folder) and not is_copy_name(original):
        raise NotAllowed("The output folder is the folder the original is in. Choose another output folder so copies "
                         "never sit beside originals.")
    why = in_use(original, open_list)
    if why:
        raise Busy(" ".join(why))
    st0 = os.stat(original)
    with open(original, "rb") as f:                 # the only time the original is opened: read-only
        data = f.read()
    st1 = os.stat(original)
    if (st0.st_size, st0.st_mtime_ns) != (st1.st_size, st1.st_mtime_ns) or len(data) != st1.st_size:
        raise Busy("The file changed while Stationkeeper read it (a save or a sync in progress). Try again in a moment.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            bad = z.testzip()
    except zipfile.BadZipFile:
        raise Busy("The file is not a complete Office file (damaged, still syncing, or protected with a password).")
    if bad:
        raise Busy("The file is damaged inside (a part fails its check). Open and save it in Office first.")
    before = {"sha256": sha256_bytes(data), "size": st1.st_size, "mtime_ns": st1.st_mtime_ns}
    os.makedirs(folder, exist_ok=True)
    allow_root(folder)
    name = copy_name(original, when)
    target = os.path.join(folder, name)
    stem, ext = os.path.splitext(name)
    n = 2
    while True:
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
            break
        except FileExistsError:
            target = os.path.join(folder, f"{stem} ({n}){ext}")
            n += 1
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        if sha256_file(target) != before["sha256"]:
            raise Busy("The copy did not match the original byte for byte. Nothing was changed.")
    except Exception:
        try:
            os.remove(target)
        except OSError:
            pass
        raise
    job = Job(original, target, before, cloud_kind(original))
    if not job.original_unchanged():
        os.remove(target)
        raise Busy("The file changed while Stationkeeper copied it. Try again in a moment.")
    return job


# ------------------------------------------------------------------ running fixes on the copy
def run_step(job, name, op, allowed, op_args=None):
    """One engine operation on the copy, through the guarded write. A refusal leaves the copy as it was."""
    sw = install_guard()
    from prodengine.engine.pkg import Refused
    try:
        r = sw.apply(job.copy, op, allowed=allowed, op_args=op_args or {}, snapshot=False)
        rec = {"step": name, "changed": bool(r.changed), "report": r.report, "seconds": round(r.seconds, 2)}
    except Refused as e:
        rec = {"step": name, "changed": False, "refused": str(e)}
    job.steps.append(rec)
    return rec


def mark_properties(job, made_by="Stationkeeper"):
    """Write a custom document property into the copy: what it is, from which file, when. Word shows it under
    File > Info > Properties > Advanced > Custom."""
    from lxml import etree
    from prodengine.engine.pkg import NS
    CP = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
    VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
    REL = "http://schemas.openxmlformats.org/package/2006/relationships"
    text = (f"Copy of {os.path.basename(job.original)} made by {made_by} on "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}. The original was not changed.")

    def op(pkg):
        name = "docProps/custom.xml"
        if pkg.has(name):
            root = pkg.tree(name)
            pkg.mark_part(name)
            pkg.dirty.add(name)
        else:
            root = etree.Element(f"{{{CP}}}Properties", nsmap={None: CP, "vt": VT})
            pkg.add_part(name, root, "application/vnd.openxmlformats-officedocument.custom-properties+xml")
            rels = pkg.tree("_rels/.rels")
            pkg.mark_part("_rels/.rels")
            ids = {r.get("Id") for r in rels}
            rid = next(f"rIdSK{i}" for i in range(1, 99) if f"rIdSK{i}" not in ids)
            r = etree.SubElement(rels, f"{{{REL}}}Relationship")
            r.set("Id", rid)
            r.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties")
            r.set("Target", "docProps/custom.xml")
            pkg.dirty.add("_rels/.rels")
        for p in list(root):
            if p.get("name") == "Stationkeeper copy":
                root.remove(p)
        pids = [int(p.get("pid") or 1) for p in root]
        p = etree.SubElement(root, f"{{{CP}}}property")
        p.set("fmtid", "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}")
        p.set("pid", str(max(pids + [1]) + 1))
        p.set("name", "Stationkeeper copy")
        etree.SubElement(p, f"{{{VT}}}lpwstr").text = text
        return {"property": "Stationkeeper copy"}

    return run_step(job, "Mark the copy", op, allowed=("package|parts",))
