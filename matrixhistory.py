"""The compliance matrix saves itself, named and dated (4.2.0; claude/stationkeeper-fix-text-decisions-2026-11-10.md,
decision 4). The working file keeps its name ({Effort}_Compliance_Matrix.xlsx, by Settings > Folders and file names);
each day the matrix changes, a copy goes to "Matrix history" beside it as <name>_YYYY-MM-DD.xlsx (the day's last save
replaces that day's copy). Every copy is kept. Rules only (No AI); nothing leaves the PC."""
import datetime
import os
import shutil

FOLDER = "Matrix history"


def copy_path(path, day=None):
    day = day or datetime.date.today()
    stem, ext = os.path.splitext(os.path.basename(path))
    return os.path.join(os.path.dirname(os.path.abspath(path)), FOLDER, f"{stem}_{day.isoformat()}{ext}")


def keep(path, day=None):
    """After a save: the day's copy. Returns its path, or "" when there is nothing to copy."""
    if not path or not os.path.isfile(path):
        return ""
    dst = copy_path(path, day)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    shutil.copyfile(path, tmp)
    os.replace(tmp, dst)
    return dst


def copies(path):
    """[(day, path)] of the copies kept, oldest first."""
    d = os.path.join(os.path.dirname(os.path.abspath(path)), FOLDER)
    stem, ext = os.path.splitext(os.path.basename(path))
    out = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.startswith(stem + "_") and f.endswith(ext):
                day = f[len(stem) + 1:-len(ext)]
                try:
                    out.append((datetime.date.fromisoformat(day), os.path.join(d, f)))
                except ValueError:
                    continue
    return out
