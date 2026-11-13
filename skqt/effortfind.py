"""Find a moved effort and open an effort from its folder (3.68.0), for the main window. effortrelink holds the rules.

find_moved(win, name, folder=None) -> True when the effort was found and re-pointed (the window then opens it)
open_from_folder(win, path=None) -> the effort's name, or None
mark(win) writes the marker in the open effort's folder."""
import os

from PySide6.QtWidgets import QFileDialog, QMessageBox

import diag
import effortrelink as ER


def find_moved(win, name, folder=None):
    """The effort's Effort List is not where it was: say so, let the person pick the folder it is in now, re-point it.
    Nothing is made at the old place."""
    info = win.efforts.get(name) or {}
    old = info.get("path", "")
    if folder is None and os.environ.get("AH_TEST"):
        win.status(f"{name} was not opened: its folder was not found.")
        return False
    if folder is None:
        ask = QMessageBox(win)
        ask.setWindowTitle("Effort not found")
        ask.setText(f"{name}'s folder is not where Stationkeeper last saw it:\n{os.path.dirname(old)}\n\nIt may have been "
                    "moved or renamed, or the drive may be offline. Find its folder now? Nothing is changed until it is found.")
        find = ask.addButton("Find its folder...", QMessageBox.AcceptRole); ask.addButton("Not now", QMessageBox.RejectRole)
        ask.exec()
        if ask.clickedButton() is not find:
            win.status(f"{name} was not opened: its folder was not found.")
            return False
        folder = QFileDialog.getExistingDirectory(win, f"The folder {name} is in now")
        if not folder:
            return False
    lst = ER.find_list(folder)
    if not lst:
        win.status("No Effort List with its app data folder is in that folder.")
        return False
    got = ER.relink(lst, old)
    win.efforts.put(name, path=lst, customer_dir=_customer(lst))
    diag.activity("effort_relinked", n=got["repointed"])
    win.toast(f"{name} found: {got['repointed']} saved path(s) now point at its new place")
    return True


def open_from_folder(win, path=None):
    """Open an effort from its folder, its Effort List or its marker file: registered (or found again) and opened."""
    if path is None:
        path = QFileDialog.getExistingDirectory(win, "The effort's folder")
        if not path:
            return None
    lst = ER.find_list(path)
    if not lst:
        win.status("No Effort List with its app data folder was found there. Pick the folder that holds "
                   "<name>_Effort_List.xlsx and its app data folder.")
        return None
    same = next((n for n in win.efforts.names() if os.path.normcase(os.path.abspath((win.efforts.get(n) or {}).get("path") or ""))
                 == os.path.normcase(os.path.abspath(lst))), None)
    if same:
        win.open_effort(same)
        return same
    got = ER.relink(lst)
    name = got["name"] or "Effort"
    have = win.efforts.get(name)
    if have and not ER.missing(have):                 # another effort of that name is still where it was: keep both
        base, k = name, 2
        while win.efforts.get(f"{base} ({k})"):
            k += 1
        name = f"{base} ({k})"
    win.efforts.put(name, path=lst, customer_dir=_customer(lst))
    diag.activity("effort_opened_from_folder", n=got["repointed"])
    win.fill_efforts()
    win.open_effort(name)
    win.toast(f"{name} opened from its folder" + (f": {got['repointed']} saved path(s) re-pointed" if got["repointed"] else ""))
    return name


def mark(win):
    """The marker file in the open effort's folder, written when missing or out of date."""
    try:
        if win.ws is not None and win.effort_path:
            ER.write_marker(win.effort_path, win.effort_name)
    except Exception:  # noqa: BLE001  a read-only folder: the effort still opens
        diag.swallowed()


def ready(win, name, info):
    """Before an effort opens: its info when its folder is there (or was found again), else {}."""
    if not ER.missing(info):
        return info
    return (win.efforts.get(name) or {}) if find_moved(win, name, getattr(win, "find_folder", None)) else {}


def _customer(lst):
    """The effort's customer documents folder where it is now (4.24.0: by the team's tree, or the older folder)."""
    import effortfolders as EF
    return EF.folder(lst, "customer", make=False)
