"""Out of sight, not locked (4.30.1; Nicholas 2026-11-13 14:41 and 14:43). The folders a person works in stay plain to
see: the effort's numbered folders and its workbooks. The app's own working folders carry Windows' Hidden mark so nobody
edits, moves or tidies them by accident: each effort's "<list> - app data" folder, and the program's _local_sandbox.
The program's folder, its _internal and Stationkeeper Data are not hidden.

Hidden is not protection: File Explorer's "Hidden items" shows them. OneDrive syncs the files but not the mark, so the
mark is set again on each PC, every time the effort opens. Open the backups folder (Effort Record > More) reaches the
backups whatever Explorer shows. Only this app's own folders are touched; no Windows setting is changed.
Standard library only. Rules only (No AI); nothing leaves the PC."""
import os

HIDDEN = 0x2
# 4.30.3: _internal (the program's own files) is NOT hidden. The first build with it hidden stopped: the build lists the
# program's files, and a plain listing leaves a hidden folder out. A zip made the same way would leave the program out,
# so it stays in sight until that is settled with Nicholas.
PROGRAM_FOLDERS = ("_local_sandbox",)


def _attrs(path):
    import ctypes
    a = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    return None if a == 0xFFFFFFFF or a == -1 else a


def is_hidden(path):
    """True when the folder carries the Hidden mark (always False off Windows, where there is no such mark)."""
    if os.name != "nt" or not os.path.isdir(path):
        return False
    try:
        a = _attrs(path)
        return bool(a is not None and a & HIDDEN)
    except Exception:  # noqa: BLE001
        return False


def hide(path, setter=None):
    """Mark a folder Hidden. Returns True when it is hidden now. setter (tests): called with (path, attributes) in place
    of Windows. A folder that is not there, or a PC that is not Windows, is left alone."""
    if not path or not os.path.isdir(path):
        return False
    if setter is not None:
        return bool(setter(path, HIDDEN))
    if os.name != "nt":
        return False
    try:
        import ctypes
        a = _attrs(path)
        if a is None:
            return False
        if a & HIDDEN:
            return True
        return bool(ctypes.windll.kernel32.SetFileAttributesW(str(path), a | HIDDEN))
    except Exception:  # noqa: BLE001  the folder works the same shown or hidden
        return False


def program(base_dir, setter=None):
    """The program's own working folders, hidden: [paths hidden]. The program's folder itself is never touched."""
    return [p for p in (os.path.join(base_dir, n) for n in PROGRAM_FOLDERS) if hide(p, setter)]


def effort(data_dir, setter=None):
    """An effort's app data folder, hidden. Returns True when it is hidden now."""
    return hide(data_dir, setter)


def backups_folder(data_dir):
    """Where the effort's backups are kept (made if it is not there yet)."""
    d = os.path.join(data_dir, "backups")
    os.makedirs(d, exist_ok=True)
    return d
