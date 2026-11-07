"""The Effort Library's real folders on the Library page (3.78.0, split from librarypage): New folder..., Open the
Library folder, Move kept files into the Library folders.... Used as LibraryPage methods. Nothing leaves the PC."""
import os
from PySide6.QtWidgets import QInputDialog, QMessageBox
import diag


def new_folder(self, name=None):
    """3.78.0: a real folder under the selected category's folder (Graphics if none is selected)."""
    import effortlib as EL
    if self.lib is None:
        return ""
    cat = self.cat if self.cat not in ("all", "customer") else "graphics" if self.cat == "all" else "ours"
    if name is None:
        name, ok = QInputDialog.getText(self, "New folder", f"A folder in {EL.top(self.lib, cat)}" +
                                        (f" > {self.folder}" if self.folder else "") + ":")
        if not ok:
            return ""
    sub = EL.new_folder(self.lib, cat, self.folder if self.cat == cat else "", name)
    if sub:
        diag.activity("library_folder_made")
        self.fill_tree()
    return sub


def open_folder(self):
    import sys
    p = getattr(self.lib, "library_root", "") if self.lib else ""
    if p:
        os.makedirs(p, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(p)                     # noqa: S606  the effort's own folder
    return p


def move_into_folders(self, ok=None):
    """3.78.0: once, when asked: files kept in the app's working folder move into the Library folders, with a list."""
    import effortlib as EL
    if self.lib is None:
        return 0
    plan = EL.plan_moves(self.lib)
    if not plan:
        self.host.toast("Every file is already in the Library folders.")
        return 0
    if ok is None:
        ok = QMessageBox.question(self, "Move into the Library folders", f"{len(plan)} file(s) kept in the app's working folder "
                                  "move into the effort's Library folders (by category and folder). A list of every move is "
                                  "written to the effort's folder. Move them?") == QMessageBox.Yes
    if not ok:
        return 0
    n, note = EL.do_moves(self.lib, plan, self.host.effort_path)
    diag.activity("library_moved_into_folders", n=n)
    self.host.toast(f"{n} file(s) moved into the Library folders; the list is in {os.path.basename(note)}." if n else "Nothing moved.")
    self.refresh()
    return n
