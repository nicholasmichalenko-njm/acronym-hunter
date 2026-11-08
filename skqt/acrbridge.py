"""The Acronyms page and the Effort Library (3.78.0; acronym review decision 9, Effort Library decision 6).

Scan files... inside an effort offers to add the files to the Effort Library first, so files scanned ahead of any
document stay with the effort; 3.82.0 (form q17) asks each time which Library folder each file goes to (Graphics for a
picture and Our Documents for the rest at first, never guessed as a customer document). Scan the library... scans the
newest version of every file in the categories ticked (Customer Documents and Graphics at first).
Rules only; nothing leaves the PC."""
import os
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout
import diag
import app_gui as A
from . import design as D

FIRST = ("customer", "graphics")


def _lib(page):
    import docversions as DV
    if page.host.ws is None or getattr(page, "tool", False):
        return None
    return DV.Library(page.host.ws.p("documents")).load()


def first_folder(path):
    """The folder offered at first: Graphics for a picture, Our Documents for the rest."""
    return "graphics" if os.path.splitext(path)[1].lower() in DV_PICTURES else "ours"


class FolderDialog(QDialog):
    """Which Library folder each new file goes to (3.82.0). Add them is the main button; Scan without adding adds none."""

    def __init__(self, page, lib, paths):
        super().__init__(page)
        self.setWindowTitle("Add to the Effort Library")
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"{len(paths)} of these file(s) are not in the Effort Library. Add them first, so they stay with "
                            "the effort. Pick the Library folder for each.", "muted"))
        f = QFormLayout(); v.addLayout(f)
        self.boxes = {}
        for p in paths:
            cb = QComboBox()
            for k, name in lib.categories():
                cb.addItem(name, k)
            cb.setCurrentIndex(max(0, cb.findData(first_folder(p))))
            f.addRow(os.path.basename(p), cb)
            self.boxes[p] = cb
        bb = QDialogButtonBox()
        bb.addButton("Add them", QDialogButtonBox.AcceptRole).setDefault(True)
        bb.addButton("Scan without adding", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def choice(self):
        return {p: cb.currentData() for p, cb in self.boxes.items()}


def add_first(page, paths, answer=None):
    """Offer to add files not yet in the library before they are scanned, asking the folder for each. answer (tests):
    True takes the folders offered at first, a {path: category} sets them, False adds none. Returns how many were added."""
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
        dlg = FolderDialog(page, lib, new)
        page._folder_dialog = dlg
        answer = dlg.choice() if dlg.exec() == QDialog.Accepted else False
    if not answer:
        return 0
    where = answer if isinstance(answer, dict) else {p: first_folder(p) for p in new}
    keys = set(lib.category_keys())
    try:
        plan = DI.plan(lib, new)
    except Exception:                                  # noqa: BLE001: a file marked above CUI stops the add, not the scan
        diag.swallowed()
        page.host.status("Not added to the Effort Library (one of the files could not be taken in). The scan goes on.")
        return 0
    for e in plan:
        cat = where.get(e["path"]) or first_folder(e["path"])
        cat = cat if cat in keys else first_folder(e["path"])
        if cat != e.get("category"):
            e["folder"] = ""
            e["role"] = DV.suggest_role(cat, "") if cat == "customer" else "reference"
        elif cat != "customer":
            e["role"] = "reference"
        e["category"] = cat
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
