"""The Acronyms page and the Effort Library (3.78.0; acronym review decision 9, Effort Library decision 6).

Scan files... inside an effort offers to add the files to the Effort Library first (pictures to Graphics, the rest as
the library suggests), so files scanned ahead of any document stay with the effort. Scan the library... scans the
newest version of every file in the categories ticked (Customer Documents and Graphics at first).
Rules only; nothing leaves the PC."""
import os
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QMessageBox, QVBoxLayout
import diag
import app_gui as A
from . import design as D

FIRST = ("customer", "graphics")


def _lib(page):
    import docversions as DV
    if page.host.ws is None or getattr(page, "tool", False):
        return None
    return DV.Library(page.host.ws.p("documents")).load()


def add_first(page, paths, answer=None):
    """Offer to add files not yet in the library before they are scanned. Returns how many were added."""
    import docintake as DI
    import docversions as DV
    lib = _lib(page)
    if lib is None:
        return 0
    new = []
    for p in paths:
        try:
            if not lib.find_sha(DV.sha256(p)):
                new.append(p)
        except OSError:
            diag.swallowed()
    if not new:
        return 0
    if answer is None:
        answer = QMessageBox.question(page, "Add to the Effort Library", f"{len(new)} of these file(s) are not in the Effort "
                                      "Library. Add them first, so they stay with the effort? (Pictures go to Graphics.)") == QMessageBox.Yes
    if not answer:
        return 0
    try:
        plan = DI.plan(lib, new)
    except Exception:                                  # noqa: BLE001: a file marked above CUI stops the add, not the scan
        diag.swallowed()
        page.host.status("Not added to the Effort Library (one of the files could not be taken in). The scan goes on.")
        return 0
    for e in plan:
        if os.path.splitext(e["path"])[1].lower() in DV_PICTURES:
            e["category"] = "graphics"; e["role"] = "reference"
        elif e.get("category") == "customer" and not (e.get("folder") or ""):
            e["category"] = "ours"; e["role"] = "reference"      # no folder says it is the customer's: ours, to be moved
    cd = (page.host.efforts.get(page.host.effort_name) or {}).get("customer_dir", "") or ""
    made = DI.apply(lib, plan, cd)
    diag.activity("acronym_files_to_library", n=len(made))
    if made:
        page.host.toast(f"{len(made)} file(s) added to the Effort Library")
    return len(made)


DV_PICTURES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".svg")


def library_paths(lib, cats):
    out = []
    for d in lib.all:
        if d.get("category", "customer") not in cats:
            continue
        v = lib.latest(d)
        p = lib.path_of(v) if v else ""
        if p and os.path.isfile(p) and os.path.splitext(p)[1].lower() in A.SUPPORTED_EXTS:
            out.append(p)
    return out


def scan_library(page, cats=None, run=True):
    """Scan the library...: tick the categories, then scan their files. Returns the worker or None."""
    lib = _lib(page)
    if lib is None:
        return None
    if cats is None:
        dlg = QDialog(page); dlg.setWindowTitle("Scan the library")
        v = QVBoxLayout(dlg)
        v.addWidget(D.label("Scan the newest version of every file in the ticked folders of the Effort Library.", "muted"))
        boxes = {}
        counts = lib.counts_by_category()
        for k, n in lib.categories():
            cb = QCheckBox(f"{n} ({counts.get(k, 0)})"); cb.setChecked(k in FIRST); v.addWidget(cb); boxes[k] = cb
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Scan")
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        page._scan_lib_dialog = dlg
        if not run or dlg.exec() != QDialog.Accepted:
            return None
        cats = [k for k, cb in boxes.items() if cb.isChecked()]
    paths = library_paths(lib, set(cats))
    if not paths:
        page.host.status("No files in those folders of the Effort Library yet.")
        return None
    diag.activity("library_terms_scan", files=len(paths))
    return page.scan(paths)
