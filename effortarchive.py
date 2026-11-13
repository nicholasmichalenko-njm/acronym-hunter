"""Archive and restore an effort (3.70.0; claude/stationkeeper-archive-merge-decisions-2026-11-06.md). Archiving is a
flag in the effort registry, with who and when: the effort leaves All Efforts, the effort picker, My Work and the other
lists (they already leave archived efforts out), and every file stays where it is. Restore clears the flag.

4.24.0 (Nicholas 2026-11-12 16:59): an archived effort can be deleted from Stationkeeper. That takes it off this PC's
list of efforts and nothing more, unless the person also ticks the box that sends its folder to the Recycle Bin. A
folder is only ever offered when it holds this effort's list and no other effort's.

archive(registry, name, who=None) -> True       restore(registry, name) -> True
archived(registry) -> [names]                    active(registry) -> [names]"""
import datetime, getpass


def archive(registry, name, who=None):
    if not registry.get(name):
        return False
    registry.put(name, archived=True, archived_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                 archived_by=who or getpass.getuser())
    if registry.current == name:
        try:
            registry.current = ""
        except OSError:
            pass
    return True


def restore(registry, name):
    if not registry.get(name):
        return False
    registry.put(name, archived=False)
    return True


def delete(registry, name):
    """Off this PC's list of efforts (archived ones only). The files are not touched here. True when it was taken off."""
    if not (registry.get(name) or {}).get("archived"):
        return False
    registry.forget(name)
    return True


def folder_to_remove(registry, name):
    """The effort's own folder, when it is safe to offer: it holds this effort's list, no other effort known to this PC
    keeps a file inside it, and it is not a drive's root or the person's home folder. "" otherwise."""
    import os
    info = registry.get(name) or {}
    path = info.get("path") or ""
    if not path or not os.path.isfile(path):
        return ""
    try:
        import effortfolders as EF
        root = os.path.abspath(EF.root(path))
    except Exception:  # noqa: BLE001
        root = os.path.abspath(os.path.dirname(path))
    key = os.path.normcase(root)
    if not os.path.isdir(root) or os.path.dirname(root) == root or key == os.path.normcase(os.path.expanduser("~")):
        return ""
    for other in registry.names():
        if other == name:
            continue
        op = os.path.normcase(os.path.abspath((registry.get(other) or {}).get("path") or ""))
        if op and (op == key or op.startswith(key + os.sep)):
            return ""
    return root


def can_recycle():
    import sys
    return sys.platform == "win32"


def recycle(folder):
    """Send a folder to the Windows Recycle Bin (it can be put back from there). False when it could not be sent."""
    import os
    if not can_recycle() or not folder or not os.path.isdir(folder):
        return False
    import ctypes
    from ctypes import wintypes

    class _OP(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL), ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", wintypes.LPCWSTR)]
    op = _OP(None, 3, os.path.abspath(folder) + "\0\0", None, 0x0040 | 0x0010 | 0x0004 | 0x0400, False, None, None)
    #        FO_DELETE          FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    got = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return got == 0 and not op.fAnyOperationsAborted and not os.path.isdir(folder)


def archived(registry):
    return [n for n in registry.names() if (registry.get(n) or {}).get("archived")]


def active(registry):
    return [n for n in registry.names() if not (registry.get(n) or {}).get("archived")]
