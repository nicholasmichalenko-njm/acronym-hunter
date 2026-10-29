"""Import an effort package in Qt (2.74.0): open a .skpkg someone handed over (Settings > Import effort package..., or
double-click the file now that Stationkeeper.exe is the Qt window) and continue where it was. When the effort is
already on this PC: use the package (this PC's saved work is backed up first) or keep both (the package opens as a
second effort). Same engine as the classic window (effortpkg); nothing leaves the PC.
"""
import datetime, os
from PySide6.QtWidgets import QFileDialog, QMessageBox
import diag
import effortpkg as P
import effortrec as RR
import workspace as W


def import_package(win, path=None, dest=None, mode=None):
    """win: the main window. mode when the effort already exists: "replace" or "both". Returns the unpacked paths with
    "name", or None."""
    if path is None:
        path, _ = QFileDialog.getOpenFileName(win, "Import effort package", "",
                                              "Stationkeeper effort package (" + " ".join("*" + e for e in P.EXTS) + ")")
        if not path:
            return None
    try:
        man = P.read_manifest(path)
    except P.PackageError as e:
        win.status(str(e))
        return None
    name = man.get("effort") or "Effort"
    desc = (f"{name}\nSaved by {man.get('saved_by', '?')} on {man.get('saved_at', '').replace('T', ' ')}"
            + (f"\nStage: {man['stage']}" if man.get("stage") else "") + f"\n{len(man.get('files', {}))} files")
    exists = name in win.efforts.names()
    if mode is None and exists:
        box = QMessageBox(win); box.setWindowTitle("Import effort package")
        box.setText(desc + f"\n\n'{name}' is already on this PC.")
        use = box.addButton("Use the package (back up this PC's copy first)", QMessageBox.AcceptRole)
        both = box.addButton("Keep both", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        if box.clickedButton() not in (use, both):
            return None
        mode = "replace" if box.clickedButton() is use else "both"
    elif mode is None and dest is None:
        if QMessageBox.question(win, "Import effort package", desc + "\n\nImport it?") != QMessageBox.Yes:
            return None
    new_name = name
    if exists and mode == "both":
        base = f"{name} (from {man.get('saved_by', 'package')})"
        new_name, k = base, 2
        while new_name in win.efforts.names():
            new_name, k = f"{base} {k}", k + 1
    if dest is None:
        dest = QFileDialog.getExistingDirectory(win, "Where should the effort's files go?")
        if not dest:
            return None
    folder = os.path.join(dest, new_name)
    if exists and mode == "replace":
        old = win.efforts.get(name) or {}
        try:
            if win.effort_name == name:
                win.close_effort()
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            od = W.data_dir_for(old.get("path", "")) if old.get("path") else ""
            if od and os.path.isdir(od):
                P.backup_folder(od, os.path.join(os.path.dirname(od), f"{name} - before import {stamp}.zip"))
        except Exception:
            diag.swallowed()
    try:
        got = P.unpack(path, folder, W.data_dir_for)
    except (P.PackageError, OSError) as e:
        diag.swallowed()
        win.status(str(e) if isinstance(e, P.PackageError) else f"The package could not be unpacked ({type(e).__name__}).")
        return None
    P.repoint(got["data"], got["customer_dir"], got["matrix"], got.get("moved"))
    inf = man.get("info", {})
    put = {k: inf.get(k) for k in ("first_use", "client", "solicitation", "internal_no", "list_format") if inf.get(k) is not None}
    win.efforts.put(new_name, path=got["list"], customer_dir=got["customer_dir"] or os.path.join(folder, "Customer documents"),
                    volumes_dir=got["volumes_dir"] or "", **put)
    os.makedirs(os.path.join(folder, "Customer documents"), exist_ok=True)
    diag.activity("package_imported", files=len(man.get("files", {})))
    if not win.open_effort(new_name):
        return got
    if new_name != name:                                 # keep both: the effort list says its new name too
        try:
            import effort as E
            L = E.EffortList(got["list"]).load()
            L.name = new_name
            L.pending = True
            L.save()
        except Exception:
            diag.swallowed()
    try:
        RR.Record(win.ws.root).log("effort", f"Effort package imported: saved by {man.get('saved_by', '?')} on "
                                             f"{man.get('saved_at', '').replace('T', ' ')}"
                                   + (f" at {man['stage']}" if man.get("stage") else ""), save=True)
    except Exception:
        diag.swallowed()
    win.go("home")
    win.toast(f"{new_name}: package imported")
    got["name"] = new_name
    return got
