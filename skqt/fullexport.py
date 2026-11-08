"""The full effort export (3.12.0; 3.84.0 split from mainwin): a full copy of the effort and everything in it, as plain
files, in a dated folder. self is the main window. Nothing leaves the PC."""
import os

import diag


def export_full_effort(self, folder=None, open_it=True):
    """3.12.0: a full copy of the effort and everything in it, as plain files, in a dated folder named for the effort
    and the stage it was exported from (in the effort's Exports folder unless a folder is given)."""
    import datetime as _dt
    import shutil
    import effortfolders as EF
    import readable as RD
    if self.ws is None:
        self.status("Open an effort first.")
        return ""
    src = self.readable_now(overview=True)
    if not src or not os.path.isdir(src):
        self.status("The effort could not be written out just now. Try again after the next save.")
        return ""
    try:
        import effortrec as _R
        stage = (_R.Record(self.ws.root).stage() or {}).get("name", "")
    except Exception:
        stage = ""
    base = folder or EF.folder(self.effort_path, "exports") or os.path.dirname(src)
    name = RD._safe(" - ".join(x for x in (self.effort_name, stage, "full export " + _dt.datetime.now().strftime("%Y-%m-%d %H%M")) if x))
    dest = os.path.join(base, name)
    n = 2
    while os.path.exists(dest):
        dest = os.path.join(base, f"{name} ({n})"); n += 1
    try:
        os.makedirs(base, exist_ok=True)
        shutil.copytree(src, dest)
    except OSError:
        diag.swallowed()
        self.status("The full export could not be written there. Pick another folder.")
        return ""
    diag.activity("qt_full_effort_exported")
    self.toast("Full effort exported: " + os.path.basename(dest))
    if open_it and not os.environ.get("AH_TEST"):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
    return dest
